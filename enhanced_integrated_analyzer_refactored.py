# enhanced_integrated_analyzer_refactored.py
# mypy: ignore-errors  # TODO: 핵심 공용 함수들부터 타입을 엄격히 하여 드리프트 방지
"""
리팩토링된 향상된 통합 분석 시스템
- 단일 책임 원칙 적용
- 클래스 분리 및 모듈화
- 성능 최적화
- 에러 처리 개선
"""

# Public API surface
__all__ = [
    # Main classes
    'EnhancedIntegratedAnalyzer',
    'AnalysisResult',
    'AnalysisStatus',
    'AnalysisConfig',
    
    # Data classes
    'PriceData',
    'FinancialData',
    'ErrorType',
    
    # Utilities
    'normalize_market_cap_ekwon',
    'serialize_for_json',
    'fmt',
    'fmt_pct',
    
    # Configuration
    'ConfigManager',
    'MetricsCollector',
]

"""
스레드 안전성 (Thread Safety):
- 내부 캐시 및 메트릭 수집은 RLock으로 보호됨
- 외부 데이터 프로바이더(KISDataProvider, EnhancedPriceProvider)는 
  스레드 안전하지 않을 수 있음. 병렬 처리 시 주의 필요.
- 레이트리미터는 스레드 안전하게 구현됨
- 권장사항: 프로바이더 내부에서 요청 단위 세션 생성 또는 락/큐 도입

환경변수 설정 (Environment Variables):
- KIS_MAX_TPS: API TPS 제한 (기본값: 8, 단위: 요청/초)
- MAX_WORKERS: 워커 수 강제 설정 (기본값: 0=자동, 단위: 개)
- EPS_MIN: EPS 최소치 (기본값: 0.1, 단위: 원)
- BPS_MIN: BPS 최소치 (기본값: 100.0, 단위: 원)
- POS_TINY_BAND_THRESHOLD: 52주 밴드 임계치 (기본값: 0.001, 단위: 0.1%)
- KIS_CACHE_TTL_PRICE: 가격 캐시 TTL (기본값: 5.0, 단위: 초)
- KIS_CACHE_TTL_FINANCIAL: 재무 캐시 TTL (기본값: 900.0, 단위: 초)
- KIS_CACHE_MAX_KEYS: 캐시 최대 엔트리 수 (기본값: 2000, 단위: 개)
- PREFERRED_STOCK_INCLUDE_WOORI: "우리" 시작 종목 우선주 간주 (기본값: false)
- PER_MAX_DEFAULT: PER 상한 클램프 (기본값: 500.0, 단위: 배)
- PBR_MAX_DEFAULT: PBR 상한 클램프 (기본값: 100.0, 단위: 배)
- SECTOR_TARGET_GOOD: 섹터 피어 목표 샘플 수 (기본값: 60, 단위: 개)
- RATE_LIMITER_DEFAULT_TIMEOUT: 레이트리미터 타임아웃 (기본값: 2.0, 단위: 초)
- RATE_LIMITER_NOTIFY_ALL: 레이트리미터 공정한 웨이크업 (기본값: false)
- MARKET_CAP_STRICT_MODE: 시총 단위 추정 엄격 모드 (기본값: true; true=애매 값 무시, false=완화 변환 허용)
- ENABLE_FAKE_PROVIDERS: 외부 모듈 실패 시 더미 구현 사용 (기본값: false; true=운영 중 일시 장애 시 진단 계속)
"""

import typer
import pandas as pd
import numpy as np
import logging
import json
import time
import os
import yaml
import math
import random
import signal
import atexit
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, TypedDict, Set
from decimal import Decimal
from threading import Lock, RLock, Condition
from collections import deque, OrderedDict
from rich.console import Console
from rich.table import Table
from rich.box import ROUNDED

# monotonic time 별칭 (시스템 시간 변경에 안전)
_monotonic = time.monotonic

# ✅ 모듈 레벨 환경변수 캐시 (핫패스 최적화)
_ENV_CACHE = {
    'current_ratio_ambiguous_strategy': os.getenv("CURRENT_RATIO_AMBIGUOUS_STRATEGY", "as_is"),
    'current_ratio_force_percent': os.getenv("CURRENT_RATIO_FORCE_PERCENT", "false"),
    'market_cap_strict_mode': os.getenv("MARKET_CAP_STRICT_MODE", "true"),
}

def _refresh_env_cache():
    """환경변수 캐시 hot-reload (런타임 설정 변경 지원)"""
    _ENV_CACHE['current_ratio_ambiguous_strategy'] = os.getenv("CURRENT_RATIO_AMBIGUOUS_STRATEGY", "as_is")
    _ENV_CACHE['current_ratio_force_percent'] = os.getenv("CURRENT_RATIO_FORCE_PERCENT", "false")
    _ENV_CACHE['market_cap_strict_mode'] = os.getenv("MARKET_CAP_STRICT_MODE", "true")

# --- 환경변수 캐시 핫리로드: SIGHUP 지원 ------------------------------------
def _handle_sighup(signum, frame):
    try:
        _refresh_env_cache()
        logging.info("[env] SIGHUP received → environment cache reloaded")
    except Exception as e:
        logging.debug(f"[env] SIGHUP handler error: {e}")

try:
    signal.signal(signal.SIGHUP, _handle_sighup)
except Exception:
    # 일부 플랫폼(Windows 등)에서는 SIGHUP 미지원
    pass

# =============================================================================
# 유틸리티 함수
# =============================================================================

def normalize_market_cap_ekwon(x: Optional[float]) -> Optional[float]:
    """
    Normalize market cap to 억원 (eokwon).
    Heuristics:
      - If value looks like 억원 (<= 20,000,000 = 2,000조), keep as-is.
      - If value looks like 원 (>= 1e11 = 1,000억), convert to 억원 by /1e8.
      - Otherwise treat as ambiguous → optional non-strict conversion via env.
    """
    v = DataValidator.safe_float_optional(x)
    if v is None or not math.isfinite(v) or v <= 0:
        return None

    # If already reasonable in 억원 (up to 2,000조), assume eokwon
    if v <= 20_000_000:  # 20,000,000 억 = 2,000조
        logging.debug(f"[unit] market_cap assumed eokwon: {x} -> {v}")
        return v

    # If looks like KRW (원): anything ≥ 1e11 (1,000억 원) convert to 억원
    if v >= 1e11:
        converted = v / 1e8
        logging.debug(f"[unit] market_cap converted from won→eokwon: {x} -> {converted}")
        return converted

    # Ambiguous band (1e7 ~ 1e11): gate via env for safety (캐시된 값 사용)
    non_strict = _ENV_CACHE['market_cap_strict_mode'].lower() != "true"
    if non_strict and v >= 1e7:
        converted = v / 1e8
        logging.debug(f"[unit] market_cap non-strict (ambiguous) won→eokwon: {x} -> {converted} (천단위 구분 해석 결과)")
        return converted

    # Confidence logging when discarding ambiguous values
    if v >= 1e7:  # Only warn for values in ambiguous range
        logging.warning(f"[unit] market_cap ambiguous range dropped in strict mode: {x} -> None (1e7 ≤ v < 1e11)")
    else:
        logging.debug(f"[unit] market_cap too small (dropped): {x} -> None (천단위 구분 해석 결과)")
    return None

# 타입 정의
JSONValue = Union[None, bool, int, float, str, List["JSONValue"], Dict[str, "JSONValue"]]
PeerTriple = Tuple[float, float, float]

# ✅ TypedDict 정의: 데이터 구조 드리프트 방지 및 에디터 힌트 개선
class PriceData(TypedDict, total=False):
    """가격 데이터 구조"""
    current_price: Optional[float]
    w52_high: Optional[float]
    w52_low: Optional[float]
    per: Optional[float]
    pbr: Optional[float]
    eps: Optional[float]
    bps: Optional[float]
    volume: Optional[int]
    market_cap: Optional[float]
    price_change: Optional[float]
    price_change_rate: Optional[float]

class FinancialData(TypedDict, total=False):
    """재무 데이터 구조"""
    roe: Optional[float]
    roa: Optional[float]
    debt_ratio: Optional[float]
    equity_ratio: Optional[float]
    revenue_growth_rate: Optional[float]
    operating_income_growth_rate: Optional[float]
    net_income_growth_rate: Optional[float]
    net_profit_margin: Optional[float]
    gross_profit_margin: Optional[float]
    current_ratio: Optional[float]
    profitability_grade: Optional[str]

class SectorAnalysis(TypedDict, total=False):
    """섹터 분석 결과 구조"""
    grade: str
    total_score: Optional[float]
    breakdown: Dict[str, float]
    is_leader: bool
    base_score: Optional[float]
    leader_bonus: float
    notes: List[str]

# =============================================================================
# 로깅 상수 및 유틸리티
# =============================================================================

# ---- 런타임 로깅 설정 (환경변수로 제어) ------------------------------------
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_FMT = os.getenv(
    "LOG_FORMAT",
    "[%(asctime)s] %(levelname)s %(message)s"
)
# ✅ 로그 초기화 패턴 개선: 모듈 import 시점에는 설정하지 않고, 엔트리포인트에서만 기본 로깅 설정
def _setup_logging_if_needed():
    """엔트리포인트에서만 호출하여 기본 로깅 설정"""
    root = logging.getLogger()
    if not root.handlers:
        try:
            logging.basicConfig(
                level=getattr(logging, _LOG_LEVEL, logging.INFO),
                format=_LOG_FMT,
                datefmt="%H:%M:%S",
            )
        except Exception:
            # 이미 다른 환경에서 핸들러가 있을 수 있으므로, 새 핸들러 추가는 건너뜀
            if not root.handlers:
                logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
            logging.warning("로그 설정 초기화 실패, 기존 설정으로 진행합니다.")
# ---------------------------------------------------------------------------

class LogLevel:
    """로깅 레벨 상수"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

class ErrorType:
    """에러 타입 분류 상수 (메트릭스 집계용)"""
    API_TIMEOUT = "api_timeout"
    API_CONNECTION = "api_connection"
    API_RATE_LIMIT = "api_rate_limit"
    DATA_PARSE = "data_parse"
    SECTOR_PEER_DATA = "sector_peer_data_error"
    FINANCIAL_DATA = "financial_data_error"
    PRICE_DATA = "price_data_error"
    STABILITY_RATIO = "stability_ratio_error"
    # ✅ 추가된 에러타입 상수들
    OPINION = "opinion_analysis_error"
    ESTIMATE = "estimate_analysis_error"
    EMPTY_PRICE_PAYLOAD = "empty_price_payload"
    INVALID_52W_BAND = "invalid_52w_band"  # 52주 밴드 빈약/퇴화
    HTTP_4XX = "http_4xx"
    HTTP_5XX = "http_5xx"
    UNKNOWN = "unknown_error"
    
    # 상위 카테고리 매핑 (SRE 대시보드용)
    CATEGORY_MAP = {
        API_TIMEOUT: "네트워크",
        API_CONNECTION: "네트워크", 
        API_RATE_LIMIT: "HTTP",
        HTTP_4XX: "HTTP",
        HTTP_5XX: "HTTP",
        DATA_PARSE: "데이터",
        FINANCIAL_DATA: "데이터",
        PRICE_DATA: "데이터",
        EMPTY_PRICE_PAYLOAD: "데이터",
        INVALID_52W_BAND: "데이터",
        SECTOR_PEER_DATA: "분석",
        STABILITY_RATIO: "분석",
        OPINION: "분석",
        ESTIMATE: "분석",
        UNKNOWN: "기타"
    }
    
    @classmethod
    def get_category(cls, error_type: str) -> str:
        """에러 타입을 상위 카테고리로 매핑"""
        return cls.CATEGORY_MAP.get(error_type, "기타")

def log_error(operation: str, symbol: str = None, error: Exception = None, level: str = LogLevel.WARNING):
    """일관된 에러 로깅 포맷 (운영 로그 grep 친화적)"""
    if symbol:
        message = f"{operation} 실패 | symbol={symbol} | err={error}"
    else:
        message = f"{operation} 실패 | err={error}"
    
    # ✅ LogLevel 값 일관성 개선: 레벨 매핑 사용
    LEVEL_MAP = {
        LogLevel.ERROR: logging.error,
        LogLevel.WARNING: logging.warning,
        LogLevel.INFO: logging.info,
        LogLevel.DEBUG: logging.debug
    }
    LEVEL_MAP.get(level, logging.warning)(message)

def log_success(operation: str, symbol: str = None, details: str = None):
    """일관된 성공 로깅 포맷"""
    if symbol and details:
        message = f"✅ {operation} 성공 {symbol}: {details}"
    elif symbol:
        message = f"✅ {operation} 성공 {symbol}"
    else:
        message = f"✅ {operation} 성공"
    
    logging.info(message)

def safe_env_int(key: str, default: int, min_val: Optional[int] = None) -> int:
    """안전한 환경변수 정수 파싱 (0=auto 설정 허용)"""
    try:
        value = int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        value = default
    if min_val is None:
        return value
    return max(min_val, value)

def safe_env_float(key: str, default: float, min_val: float = 0.0) -> float:
    """안전한 환경변수 실수 파싱 (음수 방어)"""
    try:
        value = float(os.getenv(key, str(default)))
        return max(min_val, value)  # 최소값 보장
    except (ValueError, TypeError):
        return max(min_val, default)

def safe_env_bool(key: str, default: bool = False) -> bool:
    """안전한 환경변수 불린 파싱 (robust parser)"""
    v = os.getenv(key)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y", "on"}

def safe_env_ms_to_seconds(key: str, default_ms: float, min_ms: float = 0.0) -> float:
    """
    밀리초(ms) 환경변수를 초(second)로 변환하여 반환.
    RATE_LIMITER_MIN_SLEEP_MS 같은 키를 초 단위로 잘못 사용하는 버그 방지.
    """
    try:
        ms = float(os.getenv(key, str(default_ms)))
        ms = max(min_ms, ms)
    except (ValueError, TypeError):
        ms = max(min_ms, default_ms)
    return ms / 1000.0

# =============================================================================
# 메트릭 수집 클래스
# =============================================================================

class MetricsCollector:
    """시스템 메트릭 수집 및 관리"""
    
    def __init__(self):
        self.metrics = {
            'api_calls': {'total': 0, 'success': 0, 'error': 0},
            'cache_hits': {'price': 0, 'financial': 0, 'sector': 0},
            'cache_misses': {'price': 0, 'financial': 0, 'sector': 0},
            'analysis_duration': {'total': 0, 'count': 0, 'avg': 0},
            'sector_evaluation': {'total': 0, 'count': 0, 'avg': 0},
            'stocks_analyzed': 0,
            'errors_by_type': {},
            # ✅ 섹터 피어 샘플 크기 메트릭 추가
            'sector_sample_insufficient': 0,
            # ✅ 메트릭 개선: missing 필드 카운터 추가
            'missing_financial_fields': 0,
            # ✅ API 재시도 중간 실패 카운터 추가 (이중 집계 방지)
            'api_retry_attempt_errors': 0,
            # ✅ PER/PBR 스킵 메트릭 추가
            'valuation_skips': {'per_epsmin': 0, 'pbr_bpsmin': 0},
            'start_time': _monotonic()
        }
        # Histogram buckets for duration analysis (seconds)
        # ✅ 메트릭 개선: p95 백분위 추가 (SRE가 주로 사용)
        # 운영 기준: p90이 5초, p95가 10초 넘으면 경고 (SLO)
        self.duration_buckets = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        self.analysis_histogram = [0] * (len(self.duration_buckets) + 1)  # +1 for overflow
        self.sector_histogram = [0] * (len(self.duration_buckets) + 1)
        self.lock = RLock()
    
    def record_api_call(self, success: bool, error_type: str = None):
        """API 호출 기록 (최종 결과만)"""
        with self.lock:
            self.metrics['api_calls']['total'] += 1
            if success:
                self.metrics['api_calls']['success'] += 1
            else:
                self.metrics['api_calls']['error'] += 1
                if error_type:
                    self.metrics['errors_by_type'][error_type] = self.metrics['errors_by_type'].get(error_type, 0) + 1

    def record_api_attempt_error(self, error_type: str = None):
        """API 재시도 중간 실패 기록 (이중 집계 방지)"""
        with self.lock:
            self.metrics['api_retry_attempt_errors'] += 1
            if error_type:
                self.metrics['errors_by_type'][error_type] = self.metrics['errors_by_type'].get(error_type, 0) + 1
    
    def record_cache_hit(self, cache_type: str):
        """캐시 히트 기록"""
        with self.lock:
            self.metrics['cache_hits'].setdefault(cache_type, 0)
            self.metrics['cache_hits'][cache_type] += 1
    
    def record_cache_miss(self, cache_type: str):
        """캐시 미스 기록"""
        with self.lock:
            self.metrics['cache_misses'].setdefault(cache_type, 0)
            self.metrics['cache_misses'][cache_type] += 1
    
    def record_analysis_duration(self, duration: float):
        """분석 소요 시간 기록"""
        with self.lock:
            self.metrics['analysis_duration']['total'] += duration
            self.metrics['analysis_duration']['count'] += 1
            self.metrics['analysis_duration']['avg'] = (
                self.metrics['analysis_duration']['total'] / self.metrics['analysis_duration']['count']
            )
            # Record in histogram
            bucket_idx = self._find_bucket(duration, self.duration_buckets)
            self.analysis_histogram[bucket_idx] += 1
    
    def record_sector_evaluation(self, duration: float):
        """섹터 평가 소요 시간 기록"""
        with self.lock:
            self.metrics['sector_evaluation']['total'] += duration
            self.metrics['sector_evaluation']['count'] += 1
            self.metrics['sector_evaluation']['avg'] = (
                self.metrics['sector_evaluation']['total'] / self.metrics['sector_evaluation']['count']
            )
            # Record in histogram
            bucket_idx = self._find_bucket(duration, self.duration_buckets)
            self.sector_histogram[bucket_idx] += 1
    
    def record_sector_sample_insufficient(self, sector_name: str = None):
        """섹터 피어 표본 부족 기록"""
        with self.lock:
            self.metrics['sector_sample_insufficient'] += 1
            if sector_name:
                if 'sector_sample_insufficient_by_sector' not in self.metrics:
                    self.metrics['sector_sample_insufficient_by_sector'] = {}
                self.metrics['sector_sample_insufficient_by_sector'][sector_name] = \
                    self.metrics['sector_sample_insufficient_by_sector'].get(sector_name, 0) + 1
    
    def record_missing_financial_fields(self, count: int = 1):
        """✅ missing 재무 필드 카운터: 데이터 품질 드리프트 모니터링"""
        with self.lock:
            self.metrics['missing_financial_fields'] += count
    
    def record_stocks_analyzed(self, count: int):
        """분석된 종목 수 기록"""
        with self.lock:
            self.metrics['stocks_analyzed'] += count
    
    def get_cache_hit_rate(self, cache_type: str) -> float:
        """캐시 히트율 계산"""
        with self.lock:
            hits = self.metrics['cache_hits'].get(cache_type, 0)
            misses = self.metrics['cache_misses'].get(cache_type, 0)
            total = hits + misses
            return (hits / total * 100.0) if total > 0 else 0.0
    
    def get_api_success_rate(self) -> float:
        """API 성공률 계산"""
        with self.lock:
            total = self.metrics['api_calls']['total']
            success = self.metrics['api_calls']['success']
            return (success / total * 100) if total > 0 else 0.0
    
    def _find_bucket(self, value: float, buckets: List[float]) -> int:
        """Find histogram bucket index for a value"""
        for i, bucket in enumerate(buckets):
            if value <= bucket:
                return i
        return len(buckets)  # Overflow bucket
    
    def get_percentiles(self, histogram: List[int], buckets: List[float], percentile: float) -> float:
        """Calculate percentile from histogram"""
        total = sum(histogram)
        if total == 0:
            return 0.0
        
        target = total * (percentile / 100.0)
        cumulative = 0
        
        for i, count in enumerate(histogram):
            cumulative += count
            if cumulative >= target:
                if i < len(buckets):
                    return buckets[i]
                else:
                    return buckets[-1] * 2  # Estimate for overflow
        return buckets[-1] * 2
    
    def get_summary(self) -> Dict[str, Any]:
        """메트릭 요약 반환"""
        with self.lock:
            # SLO 경고 체크
            p90 = self.get_percentiles(self.analysis_histogram, self.duration_buckets, 90)
            p95 = self.get_percentiles(self.analysis_histogram, self.duration_buckets, 95)
            if p90 > 5.0:
                logging.warning(f"[SLO] 분석 p90 {p90:.1f}s > 5s")
            if p95 > 10.0:
                logging.warning(f"[SLO] 분석 p95 {p95:.1f}s > 10s")
            
            # 상위 카테고리별 에러 집계 (SRE 대시보드용)
            errors_by_category = {}
            for error_type, count in self.metrics['errors_by_type'].items():
                category = ErrorType.get_category(error_type)
                errors_by_category[category] = errors_by_category.get(category, 0) + count
            
            return {
                'runtime_seconds': _monotonic() - self.metrics['start_time'],
                'stocks_analyzed': self.metrics['stocks_analyzed'],
                'api_calls': self.metrics['api_calls'].copy(),
                'api_success_rate': self.get_api_success_rate(),
                'cache_hit_rates': {
                    'price': self.get_cache_hit_rate('price'),
                    'financial': self.get_cache_hit_rate('financial'),
                    'sector': self.get_cache_hit_rate('sector')
                },
                'avg_analysis_duration': self.metrics['analysis_duration']['avg'],
                'avg_sector_evaluation': self.metrics['sector_evaluation']['avg'],
                'errors_by_type': self.metrics['errors_by_type'].copy(),
                'errors_by_category': errors_by_category,  # SRE 대시보드용 상위 카테고리
                'sector_sample_insufficient': self.metrics['sector_sample_insufficient'],
                'sector_sample_insufficient_by_sector': self.metrics.get('sector_sample_insufficient_by_sector', {}),
                'analysis_p50': self.get_percentiles(self.analysis_histogram, self.duration_buckets, 50),
                'analysis_p90': p90,
                'analysis_p95': p95,
                'sector_p50': self.get_percentiles(self.sector_histogram, self.duration_buckets, 50),
                'sector_p90': self.get_percentiles(self.sector_histogram, self.duration_buckets, 90),
                'sector_p95': self.get_percentiles(self.sector_histogram, self.duration_buckets, 95)
            }

# Safer price/52w checks
def _none_if_missing_strict(x):
    """Return None if value is truly missing, keep 0.0 if provider returns it"""
    v = DataValidator.safe_float_optional(x)
    return v  # keep 0.0 if provider truly returns it

# Safe formatter for consistent number display
def fmt(x, suffix='', nd=1):
    """Centralized number formatter that handles None/NaN consistently"""
    try:
        if x is None or not math.isfinite(float(x)):
            return "N/A"
        return f"{float(x):.{nd}f}{suffix}"
    except Exception:
        return "N/A"

def fmt_pct(x, nd=1):
    """Percentage formatter that avoids N/A%"""
    v = DataValidator.safe_float_optional(x)
    return f"{v:.{nd}f}%" if v is not None else "N/A"


# API 재시도 유틸 (백오프+지터) - expanded transient error handling
try:
    from requests.exceptions import Timeout as ReqTimeout, ReadTimeout, ConnectTimeout, ConnectionError as ReqConnErr, HTTPError
except ImportError:
    class ReqTimeout(Exception): ...
    class ReadTimeout(Exception): ...
    class ConnectTimeout(Exception): ...
    class ReqConnErr(Exception): ...
    class HTTPError(Exception): ...

import socket

def _classify_http_error(e: Exception) -> Tuple[bool, str, Optional[int]]:
    """HTTPError를 재시도 여부/에러타입/상태코드로 분류"""
    status = None
    if isinstance(e, HTTPError) and getattr(e, "response", None) is not None:
        try:
            status = e.response.status_code
        except Exception:
            status = None
    # 429: 레이트리밋 → 재시도
    if status == 429:
        return True, ErrorType.API_RATE_LIMIT, status
    # 게이트웨이/서버 계열 → 재시도
    if status in (500, 502, 503, 504):
        return True, ErrorType.HTTP_5XX, status
    # 나머지 4xx는 클라이언트 오류 → 재시도 금지
    if status is not None and 400 <= status < 500:
        return False, ErrorType.HTTP_4XX, status
    # 상태코드 불명: 재시도 비결정 → 일반 네트워크 분류에 위임
    # 로깅에 상태코드가 없다는 점을 명확히 남기면 운영 분석이 편함
    if status is None:
        logging.debug(f"[retry] HTTPError with status=None, treating as UNKNOWN for retry decision")
    return True, ErrorType.UNKNOWN, status

TRANSIENT_ERRORS = (TimeoutError, ReqTimeout, ReadTimeout, ConnectTimeout, ReqConnErr, socket.timeout, HTTPError)
def _with_retries(call, tries=5, base=0.5, jitter=0.3, retry_on=TRANSIENT_ERRORS, max_total_sleep=15.0, metrics_attempt=None, metrics_final=None):
    """API 호출 재시도 래퍼 (선별적 재시도 + 총 소요 상한)"""
    slept = 0.0
    for i in range(tries):
        try:
            result = call()
            # 성공 시에는 최종 결과만 기록 (이중 집계 방지)
            if metrics_final:
                try:
                    metrics_final(success=True, error_type=None)
                except Exception:
                    pass
            return result
        except Exception as e:
            # HTTP 오류 정교 분류
            et = ErrorType.UNKNOWN
            if isinstance(e, (ReqTimeout, ReadTimeout, ConnectTimeout, TimeoutError, socket.timeout)):
                et = ErrorType.API_TIMEOUT
            elif isinstance(e, ReqConnErr):
                et = ErrorType.API_CONNECTION
            elif isinstance(e, HTTPError):
                should_retry, et_http, status = _classify_http_error(e)
                et = et_http
                if not should_retry:
                    # HTTP 4xx 등 재시도 금지 오류는 즉시 final 기록 후 종료
                    if metrics_final:
                        try: metrics_final(success=False, error_type=et)
                        except Exception: pass
                    raise  # ← 여기서 바로 탈출하므로 retry_on 경로와 격리됨
                # HTTP 5xx/429 등 재시도 가능한 오류는 아래 retry_on 경로로 계속
            
            # 실패했으나 재시도할 경우에만 attempt 기록 (HTTP 4xx는 위에서 이미 처리됨)
            if i < tries - 1 and isinstance(e, retry_on):
                if metrics_attempt:
                    try:
                        metrics_attempt(error_type=et)  # ← record_api_attempt_error만 호출
                    except Exception:
                        pass
            else:
                # 최종 실패는 final만 기록 (attempt 미기록 보장)
                if metrics_final:
                    try:
                        metrics_final(success=False, error_type=et)
                    except Exception:
                        pass
                raise

            backoff = base * (2 ** i) + random.uniform(0, jitter)
            if slept + backoff > max_total_sleep:
                backoff = max(0.0, max_total_sleep - slept)
            if backoff > 0:
                time.sleep(backoff)
                slept += backoff
from concurrent.futures import ThreadPoolExecutor, as_completed

# 로깅 설정은 메인 실행부에서 초기화
# rich import 제거 (미사용)
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

# 기존 import들 (친절한 에러 메시지 포함)
try:
    from kis_data_provider import KISDataProvider
    from enhanced_price_provider import EnhancedPriceProvider
    from investment_opinion_analyzer import InvestmentOpinionAnalyzer
    from estimate_performance_analyzer import EstimatePerformanceAnalyzer
    from financial_ratio_analyzer import FinancialRatioAnalyzer
    from profit_ratio_analyzer import ProfitRatioAnalyzer
    from stability_ratio_analyzer import StabilityRatioAnalyzer
    from test_integrated_analysis import create_integrated_analysis
except ImportError as e:
    logging.error(f"❌ 필수 모듈 import 실패: {e}")
    if safe_env_bool("ENABLE_FAKE_PROVIDERS", False):
        logging.warning("ENABLE_FAKE_PROVIDERS=true → 더미 구현으로 폴백합니다.")
        class KISDataProvider:
            def __init__(self): pass
            def get_stock_price_info(self, symbol): 
                return {'per': 15.0, 'pbr': 1.2, 'eps': 1000.0, 'bps': 8000.0}
            def get_financial_ratios(self, symbol): 
                return [{'roe': 12.5, 'roa': 8.0, 'debt_ratio': 30.0}]
            def get_profit_ratios(self, symbol): 
                return [{'gross_margin': 25.0, 'operating_margin': 15.0, 'net_margin': 10.0}]
            def get_stability_ratios(self, symbol): 
                return [{'current_ratio': 1.5, 'quick_ratio': 1.2, 'debt_to_equity': 0.4}]
        
        class EnhancedPriceProvider:
            def get_comprehensive_price_data(self, symbol): 
                return {'per': 15.0, 'pbr': 1.2, 'eps': 1000.0, 'bps': 8000.0, 'market_cap': 500000000000}
        
        class InvestmentOpinionAnalyzer:
            def analyze_single_stock(self, symbol, days_back=30): 
                return {'buy': 5, 'hold': 3, 'sell': 1, 'target_price': 50000}
        
        class EstimatePerformanceAnalyzer:
            def analyze_single_stock(self, symbol): 
                return {'accuracy': 0.75, 'bias': 0.05, 'revision_trend': 'up'}
        
        class FinancialRatioAnalyzer:
            def get_financial_ratios(self, symbol): 
                return [{'roe': 12.5, 'roa': 8.0, 'debt_ratio': 30.0}]
        
        class ProfitRatioAnalyzer:
            def get_profit_ratios(self, symbol): 
                return [{'gross_margin': 25.0, 'operating_margin': 15.0, 'net_margin': 10.0}]
        
        class StabilityRatioAnalyzer:
            def get_stability_ratios(self, symbol): 
                return [{'current_ratio': 1.5, 'quick_ratio': 1.2, 'debt_to_equity': 0.4}]
        
        def create_integrated_analysis(opinion, estimate): 
            return {'score': 75.0, 'recommendation': 'BUY', 'confidence': 0.8}
    else:
        logging.error("💡 해결: 모듈 경로/설치 확인 또는 ENABLE_FAKE_PROVIDERS=true")
        raise

# =============================================================================
# 1. 데이터 클래스 및 열거형
# =============================================================================

class AnalysisStatus(Enum):
    """분석 상태 열거형"""
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED_PREF = "skipped_pref"
    NO_DATA = "no_data"


@dataclass
class AnalysisResult:
    """분석 결과 데이터 클래스"""
    symbol: str
    name: str
    status: AnalysisStatus
    enhanced_score: float = 0.0
    enhanced_grade: str = 'F'
    market_cap: float = 0.0
    current_price: float = 0.0
    price_position: Optional[float] = None
    price_band_outside: bool = False  # 52주 밴드 밖 여부 플래그
    risk_score: Optional[float] = None
    financial_data: FinancialData = field(default_factory=dict)
    opinion_analysis: Dict[str, Any] = field(default_factory=dict)
    estimate_analysis: Dict[str, Any] = field(default_factory=dict)
    integrated_analysis: Dict[str, Any] = field(default_factory=dict)
    risk_analysis: Dict[str, Any] = field(default_factory=dict)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None
    price_data: PriceData = field(default_factory=dict)  # 가격 데이터 캐싱용
    sector_analysis: Dict[str, Any] = field(default_factory=dict)  # 섹터 분석 결과
    

@dataclass(frozen=True)
class AnalysisConfig:
    """분석 설정 데이터 클래스 (불변)"""
    weights: Dict[str, float]
    financial_ratio_weights: Dict[str, float]
    estimate_analysis_weights: Dict[str, float]
    grade_thresholds: Dict[str, float]
    growth_score_thresholds: Dict[str, float]
    scale_score_thresholds: Dict[str, float]

# =============================================================================
# 2. 추상 클래스 및 인터페이스
# =============================================================================

class DataProvider(ABC):
    """데이터 제공자 인터페이스"""
    
    @abstractmethod
    def get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """재무 데이터 조회"""
        pass
    
    @abstractmethod
    def get_price_data(self, symbol: str) -> Dict[str, Any]:
        """가격 데이터 조회"""
        pass

class ScoreCalculator(ABC):
    """점수 계산기 인터페이스"""
    
    @abstractmethod
    def calculate_score(self, data: Dict[str, Any], **kwargs) -> Tuple[float, Dict[str, float]]:
        """점수 계산"""
        pass

# =============================================================================
# 3. 유틸리티 클래스들
# =============================================================================

class TPSRateLimiter:
    """KIS OpenAPI TPS 제한을 고려한 레이트리미터 (Condition 기반 개선)"""
    
    def __init__(self, max_tps: int = None):
        self.max_tps = max_tps or safe_env_int("KIS_MAX_TPS", 8, 1)
        self.ts = deque()
        self.cv = Condition()
        # 지터 상한을 환경변수로 조정 가능하게 설정
        self.jitter_max = safe_env_float("RATE_LIMITER_JITTER_MAX", 0.004, 0.0)
        # ✅ notify_all 토글 옵션 (고TPS 환경에서 공평한 웨이크업)
        self.notify_all = safe_env_bool("RATE_LIMITER_NOTIFY_ALL", False)
        # ✅ 기본 타임아웃 옵션 (꽉 막힘 방지)
        self.default_timeout = safe_env_float("RATE_LIMITER_DEFAULT_TIMEOUT", 2.0, 0.1)
        # ✅ 밀리초 → 초 변환 (기존 버그: ms를 초로 오해)
        # RATE_LIMITER_MIN_SLEEP_MS: 밀리초 단위 (기본값: 2.0ms, 최소값: 1.0ms)
        self.min_sleep_seconds = safe_env_ms_to_seconds("RATE_LIMITER_MIN_SLEEP_MS", 2.0, 1.0)
    
    def acquire(self, timeout: float = None):
        """요청 허가를 받습니다 (타임아웃 지원)."""
        timeout = self.default_timeout if timeout is None else timeout
        start = _monotonic()
        with self.cv:
            while True:
                now = _monotonic()
                # 슬라이딩 윈도우 정리(항상 수행)
                one_sec_ago = now - 1.0
                old_count = len(self.ts)
                while self.ts and self.ts[0] < one_sec_ago:
                    self.ts.popleft()
                # 오래된 타임스탬프 제거 후 대기자들에게 알림
                if len(self.ts) < old_count:
                    if self.notify_all:
                        self.cv.notify_all()
                    else:
                        self.cv.notify()

                if len(self.ts) < self.max_tps:
                    self.ts.append(now)
                    # 토큰 획득 후 대기자들에게 알림
                    if self.notify_all:
                        self.cv.notify_all()
                    else:
                        self.cv.notify()
                    break

                waited = now - start
                if timeout is not None and waited >= timeout:
                    logging.warning(f"[ratelimiter] acquire timeout (max_tps={self.max_tps})")
                    raise TimeoutError(f"Rate limiter acquire() timed out after {timeout:.1f}s (max_tps={self.max_tps}, in_window={len(self.ts)})")

                # 다음 해제 시점까지 기다림 (정확한 대기 + 스핀 방지)
                earliest = self.ts[0]
                wait_for = max(0.0, (earliest + 1.0) - now)
                # 고TPS 환경에서 컨텍스트 스위칭/스핀 감소: ms 설정을 초로 변환해 사용
                min_sleep = self.min_sleep_seconds  # e.g., 2ms → 0.002s
                sleep_for = max(wait_for + random.uniform(0.0, self.jitter_max), min_sleep)
                if waited > 1.0:
                    logging.debug(f"[ratelimiter] waited={waited:.3f}s, in_window={len(self.ts)}, next={sleep_for:.3f}s")
                self.cv.wait(sleep_for)
    

class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self._config_cache = None
        self._last_modified = 0
    
    def load_config(self) -> Dict[str, Any]:
        """설정을 로드합니다."""
        try:
            # 파일 수정 시간 확인
            current_modified = os.path.getmtime(self.config_file)
            if self._config_cache and current_modified <= self._last_modified:
                return self._config_cache
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self._config_cache = config
            self._last_modified = current_modified
            return config
            
        except Exception as e:
            logging.warning(f"설정 파일 로드 실패, 기본값 사용: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정을 반환합니다."""
        return {
            'enhanced_integrated_analysis': {
                'weights': {
                    'opinion_analysis': 25,
                    'estimate_analysis': 30,
                    'financial_ratios': 30,
                    'growth_analysis': 10,
                    'scale_analysis': 5,
                    'price_position': 5
                },
                'financial_ratio_weights': {
                    'roe_score': 8,
                    'roa_score': 5,
                    'debt_ratio_score': 7,
                    'net_profit_margin_score': 5,
                    'current_ratio_score': 3,
                    'growth_score': 2
                },
                'estimate_analysis_weights': {
                    'financial_health': 15,
                    'valuation': 15
                },
                'grade_thresholds': {
                    'A_plus': 80,
                    'A': 70,
                    'B_plus': 60,
                    'B': 50,
                    'C_plus': 40,
                    'C': 30,
                    'D_plus': 20,
                    'D': 10,
                    'F': 0
                },
                'growth_score_thresholds': {
                    'excellent': 20,
                    'good': 10,
                    'average': 0,
                    'poor': -10
                },
                'scale_score_thresholds': {
                    'mega_cap': 100000,
                    'large_cap': 50000,
                    'mid_large_cap': 10000,
                    'mid_cap': 5000,
                    'small_cap': 1000
                }
            }
        }

class DataValidator:
    """데이터 검증 클래스"""
    
    @staticmethod
    def _finite(val: Any, default: float = 0.0) -> float:
        """NaN/Inf 클린업 유틸"""
        try:
            x = float(val)
            if math.isfinite(x):
                return x
        except Exception:
            pass
        return default
    
    @staticmethod
    def safe_divide(numerator: Any, denominator: Any, default: float = None, allow_negative_den: bool = False) -> Optional[float]:
        """안전한 나눗셈 - NaN/Inf 방지.
        Note: 분모<=0 인 경우 default 반환 (PER/PBR처럼 음수/0값이 무의미한 지표에 맞춤)."""
        try:
            num = DataValidator._finite(numerator)
            den = DataValidator._finite(denominator)
            
            # 분모가 0이거나 (음수 허용하지 않으면) 음수면 default 반환
            if den == 0 or (den < 0 and not allow_negative_den):
                return default
            
            result = num / den
            if math.isfinite(result):
                return result
            else:
                return default
        except Exception:
            return default
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """안전하게 float로 변환 (천 단위 구분자 지원)"""
        try:
            if value is None or pd.isna(value):
                return default
            if isinstance(value, str):
                v = value.strip().replace(',', '')
                if v == '':
                    return default
                return float(v)
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_float_optional(value: Any) -> Optional[float]:
        """안전하게 float로 변환하되 결측치는 None으로 보존 (천 단위 구분자 지원)"""
        try:
            if value is None or pd.isna(value):
                return None
            if isinstance(value, float):
                return value if math.isfinite(value) else None
            if isinstance(value, str):
                v = value.strip().replace(',', '')
                if v == '':
                    return None
                x = float(v)
                return x if math.isfinite(x) else None
            x = float(value)
            return x if math.isfinite(x) else None
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def is_valid_symbol(symbol: str) -> bool:
        """종목 코드 유효성 검사"""
        if not symbol or not isinstance(symbol, str):
            return False
        import re
        return bool(re.match(r'^\d{6}$', symbol.strip()))
    
    @staticmethod
    def is_preferred_stock(name: str) -> bool:
        """우선주 여부 확인 (강화된 정규식)"""
        if not name or not isinstance(name, str):
            return False
        s = name.strip()
        
        # ✅ 환경변수로 "우리" 시작 종목을 우선주로 간주할지 제어 (기본값: False = 간주 안함)
        if safe_env_bool("PREFERRED_STOCK_INCLUDE_WOORI", False) and s.startswith("우리"):
            return True
            
        import re
        # KRX 스타일 접미사와 명시적 키워드 (띄어쓰기/특수문자 변형 허용)
        # 더 엄격한 패턴: 괄호 표기, 명시적 키워드, 우선주 접미사만 허용
        pat = re.compile(r"(?:\((?:우|우B|우C)\)|\b우선주\b|(?:\s|^)우(?:B|C)?$)")
        return bool(pat.search(s))
    
    @staticmethod
    def _getattr_or_get(d, key, default=None):
        """객체/딕셔너리 안전 접근 유틸"""
        try:
            return getattr(d, key)
        except Exception:
            try:
                return d.get(key, default)
            except Exception:
                return default

# =============================================================================
# JSON 직렬화 유틸 (NumPy/Datetime/Decimal 안전)
# =============================================================================
def serialize_for_json(obj: Any) -> JSONValue:
    """
    Convert various Python/NumPy/Decimal/Datetime containers to JSON-serializable.
    - Handles: dict/list/tuple/set, numpy scalars/arrays, Decimal, datetime/date, objects with __dict__
    """
    import numpy as np
    from datetime import date, datetime

    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "tolist"):  # numpy arrays
        try:
            return obj.tolist()
        except Exception:
            pass
    # numpy scalar heuristic
    if obj.__class__.__module__ == "numpy":
        try:
            return obj.item()
        except Exception:
            pass
    if isinstance(obj, dict):
        return {serialize_for_json(k): serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [serialize_for_json(x) for x in obj]
    if hasattr(obj, "__dict__"):
        return {k: serialize_for_json(v) for k, v in obj.__dict__.items()}
    return str(obj)


class DataConverter:
    """데이터 변환 유틸리티 클래스"""
    
    # 퍼센트성 지표 필드 정의 (이중 스케일링 방지)
    PERCENT_FIELDS = {
        "roe", "roa", "revenue_growth_rate", "operating_income_growth_rate",
        "net_income_growth_rate", "net_profit_margin", "gross_profit_margin",
        "debt_ratio", "equity_ratio", "current_ratio"
    }
    
    
    @staticmethod
    def to_percent(x: Any) -> float:
        """퍼센트 단위로 강제 변환 (이중 스케일링 방지, 부호 보존)"""
        v = DataValidator.safe_float(x, 0.0)
        # |v|<=5면 비율로 보고 ×100, 부호 유지
        return v * 100.0 if abs(v) <= 5.0 else v
    
    @staticmethod
    def normalize_percentage(value: Any, assume_ratio_if_abs_lt_1: bool = True) -> Optional[float]:
        """퍼센트 값을 정규화 (0.12 → 12.0)"""
        try:
            v = float(value)
            if pd.isna(v):
                return None
            return v * 100.0 if assume_ratio_if_abs_lt_1 and -1.0 <= v <= 1.0 else v
        except Exception:
            return None
    
    @staticmethod
    def format_percentage(value: Any, decimal_places: int = 1) -> str:
        """퍼센트 값 포맷팅"""
        try:
            if value is None or pd.isna(value):
                return "N/A"
            v = float(value)
            return f"{v:.{decimal_places}f}%"
        except Exception:
            return "N/A"
    
    @staticmethod
    def standardize_financial_units(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        재무 데이터 단위 표준화 (퍼센트성 지표 % 단위 통일)
        - 결측치는 None으로 보존하여 이후 스코어러에서 '부분 결측 가중치 재정규화'가 가능하도록 함
        
        ⚠️ 중요: % 단위는 이 함수에서만 변환됩니다. 이후 파이프라인에서 같은 필드에 추가 변환 금지.
        
        # DO NOT convert % units again after this point.
        # Any additional scaling will create double-scaling bugs (e.g., 0.03 -> 3 -> 300).
        """
        # 환경변수 기반 정책이 바뀌었을 수 있으므로 진입 시점에 캐시를 갱신
        try:
            _refresh_env_cache()
        except Exception:
            pass
        out = data.copy()

        # 1) 퍼센트 필드는 비율형(<=5) → %로 변환, 결측은 None 유지
        for k in DataConverter.PERCENT_FIELDS:
            if k in out:
                v = out[k]
                if v is None or (isinstance(v, float) and (not math.isfinite(v))):
                    out[k] = None
                else:
                    # ✅ current_ratio 퍼센트 해석 고정: 공급원이 퍼센트/배수 혼재 가능 → 보수적 가드
                    if k == "current_ratio":
                        vv = DataValidator.safe_float_optional(v)
                        if vv is None:
                            out[k] = None
                        else:
                            # 환경변수 가드: 강제 % 해석 모드 (캐시된 값 사용)
                            force_percent = _ENV_CACHE['current_ratio_force_percent'].lower() == "true"
                            
                            if force_percent:
                                # 강제 % 모드: 0~5는 배수로 보고 %로 변환, 나머지는 %로 간주
                                out[k] = vv * 100.0 if 0.0 <= vv <= 5.0 else vv
                                logging.debug(f"[unit] current_ratio force percent mode: {v} -> {out[k]} (0-5 range check applied)")
                            elif 0.0 <= vv <= 10.0:
                                out[k] = vv * 100.0
                                logging.debug(f"[unit] current_ratio treated as multiple: {v} -> {vv*100}")
                            elif vv >= 50.0:
                                out[k] = vv
                                logging.debug(f"[unit] current_ratio assumed as percent: {v} -> {vv}")
                            else:
                                # 10~50 사이 애매 구간 처리 전략 (캐시된 값 사용)
                                ambiguous_strategy = _ENV_CACHE['current_ratio_ambiguous_strategy'].lower()
                                if ambiguous_strategy == "clamp":
                                    # 클램프 모드: 합리적 범위로 제한 [10, 300]
                                    clamped = max(10.0, min(300.0, vv))
                                    out[k] = clamped
                                    logging.debug(f"[unit] current_ratio ambiguous range (clamped): {v} -> {clamped} (treated as %)")
                                else:  # as_is
                                    # as_is 모드: 원본 값 유지 (outlier 가드만)
                                    out[k] = vv
                                    if not (0.0 <= vv <= 10000.0):
                                        logging.debug(f"[unit] current_ratio outlier left as-is: {vv}")
                    else:
                        out[k] = DataConverter.enforce_canonical_percent(v, field_name=k)
                    # 필드별 클램프 상한 분리 (극단값 방지)
                    if out[k] is not None:
                        if k in ["roe", "roa"]:
                            # 수익성 지표: 5,000% 상한
                            if abs(out[k]) > 5000.0:
                                out[k] = math.copysign(5000.0, out[k])
                        elif k in ["revenue_growth_rate", "operating_income_growth_rate", "net_income_growth_rate"]:
                            # 성장률: 1,000% 상한
                            if abs(out[k]) > 1000.0:
                                out[k] = math.copysign(1000.0, out[k])
                        else:
                            # 기타: 10,000% 상한
                            if abs(out[k]) > 10000.0:
                                out[k] = math.copysign(10000.0, out[k])

        # 2) 나머지 스칼라도 결측은 None으로, 수치/문자 수치만 안전 변환
        for k, v in list(out.items()):
            if k in DataConverter.PERCENT_FIELDS:
                continue
            if isinstance(v, (int, float)):
                out[k] = v if math.isfinite(float(v)) else None
            elif isinstance(v, str):
                out[k] = DataValidator.safe_float_optional(v)  # 수치형 문자열만 float, 아니면 None
            elif v is None:
                out[k] = None
            # dict/list 등 복합형은 그대로 둠(필요 시 상위 로직에서 처리)

        return out
    
    @staticmethod
    def as_percent_maybe_ratio(x: Any) -> float:
        """%/배수 혼재 정규화 (0<값≤5 → ×100 규칙)
        
        NOTE: 현 시점엔 ingest에서 모두 %로 표준화되니 추가 스케일 금지.
        standardize_financial_units()에서 모든 퍼센트성 지표를 %로 통일하므로
        이 함수는 레거시 호환용이며, 중복 스케일 방지가 주목적입니다.
        """
        v = DataValidator.safe_float(x, 0.0)
        if v <= 0:
            return 0.0
        return v * 100.0 if v <= 5.0 else v
    
    @staticmethod
    def enforce_canonical_percent(x: Any, field_name: str = "unknown") -> Optional[float]:
        """Enforce canonical percentage units for consistent scoring
        
        Args:
            x: Input value (could be ratio or percentage)
            field_name: Field name for logging/debugging
            
        Returns:
            Value normalized to percentage (preserves sign), None if missing
        """
        # ← 추가: 결측 보존
        x_opt = DataValidator.safe_float_optional(x)
        if x_opt is None:
            return None
        v = float(x_opt)
        if not math.isfinite(v):
            return None
        # convert likely ratios to %
        if -5.0 <= v <= 5.0:
            v = v * 100.0
        # clamp extreme outliers but DO NOT kill sign
        if abs(v) > 10000.0:
            logging.debug(f"[percent-clamp] {field_name}={v} -> {math.copysign(10000.0, v)}")
            v = math.copysign(10000.0, v)
        return v

# =============================================================================
# 4. 핵심 분석 클래스들
# =============================================================================

class FinancialDataProvider(DataProvider):
    """재무 데이터 제공자"""
    
    def __init__(self, provider: KISDataProvider, rate_limiter: TPSRateLimiter, ttl: float = None, metrics: MetricsCollector = None):
        self.provider = provider
        self.price_provider = EnhancedPriceProvider()
        self.rate_limiter = rate_limiter
        self.financial_ratio_analyzer = FinancialRatioAnalyzer(provider)
        self.profit_ratio_analyzer = ProfitRatioAnalyzer(provider)
        self.stability_ratio_analyzer = StabilityRatioAnalyzer(provider)
        self._cache_price: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()
        self._cache_fin: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()
        self._cache_lock = RLock()
        # TTL 분리: 가격 데이터는 짧게, 재무 데이터는 길게
        self._ttl = {
            'price': safe_env_float("KIS_CACHE_TTL_PRICE", 5.0, 0.1),
            'financial': safe_env_float("KIS_CACHE_TTL_FINANCIAL", 900.0, 1.0),
        }
        self._max_keys = safe_env_int("KIS_CACHE_MAX_KEYS", 2000, 100)
        self.metrics = metrics
    
    
    def _get_cached(self, cache, key):
        """캐시에서 데이터 조회 (동시성 안전, TTL 분리)"""
        now = _monotonic()
        with self._cache_lock:
            hit = cache.get(key)
            cache_type = 'price' if cache is self._cache_price else 'financial'
            if hit:
                # TTL override 지원 (빈 데이터용)
                ttl = hit[2] if len(hit) > 2 and hit[2] is not None else self._ttl[cache_type]
                if now - hit[0] < ttl:
                    if self.metrics:
                        self.metrics.record_cache_hit(cache_type)
                    return hit[1]
        
        if self.metrics:
            self.metrics.record_cache_miss(cache_type)
        return None

    def _set_cached(self, cache, key, value, ttl_override=None):
        """캐시에 데이터 저장 (동시성 안전, LRU 한도 적용)"""
        with self._cache_lock:
            # 빈 데이터는 짧은 TTL 적용
            if ttl_override is None and isinstance(value, dict) and not value:
                ttl_override = min(1.0, self._ttl['price'] * 0.2)  # 20% of normal TTL
            cache[key] = (_monotonic(), value, ttl_override)
            cache.move_to_end(key)
            while len(cache) > self._max_keys:
                cache.popitem(last=False)  # 가장 오래된 항목 제거
    
    def get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """재무 데이터를 조회합니다 (TTL 캐시 적용)."""
        # 캐시 확인
        hit = self._get_cached(self._cache_fin, symbol)
        if hit is not None:
            return hit
        
        financial_data = {}
        
        # 재무비율 분석 (재시도 적용)
        try:
            cb = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
            # rate_limiter 예외만 바깥에서 집계
            try:
                self.rate_limiter.acquire()
            except TimeoutError as e:
                if self.metrics:
                    self.metrics.record_api_call(False, ErrorType.API_TIMEOUT)
                raise
            
            # 실제 API는 _with_retries가 집계
            cb_final = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
            cb_attempt = (lambda et=None: self.metrics.record_api_attempt_error(et)) if self.metrics else None
            financial_ratios = _with_retries(
                lambda: self.financial_ratio_analyzer.get_financial_ratios(symbol),
                metrics_attempt=cb_attempt,
                metrics_final=cb_final
            )
            if financial_ratios and len(financial_ratios) > 0:
                latest_ratios = financial_ratios[0]
                financial_data.update({
                    'roe': DataValidator.safe_float_optional(latest_ratios.get('roe')),
                    'roa': DataValidator.safe_float_optional(latest_ratios.get('roa')),
                    'debt_ratio': DataValidator.safe_float_optional(latest_ratios.get('debt_ratio')),
                    'equity_ratio': DataValidator.safe_float_optional(latest_ratios.get('equity_ratio')),
                    'revenue_growth_rate': DataValidator.safe_float_optional(latest_ratios.get('revenue_growth_rate')),
                    'operating_income_growth_rate': DataValidator.safe_float_optional(latest_ratios.get('operating_income_growth_rate')),
                    'net_income_growth_rate': DataValidator.safe_float_optional(latest_ratios.get('net_income_growth_rate'))
                })
        except Exception as e:
            if self.metrics:
                self.metrics.record_api_call(False, ErrorType.FINANCIAL_DATA)
            log_error("재무비율 분석", symbol, e)
        
        # 수익성비율 분석 (재시도 적용)
        try:
            cb = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
            # rate_limiter 예외만 바깥에서 집계
            try:
                self.rate_limiter.acquire()
            except TimeoutError as e:
                if self.metrics:
                    self.metrics.record_api_call(False, ErrorType.API_TIMEOUT)
                raise
            
            # 실제 API는 _with_retries가 집계
            cb_final = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
            cb_attempt = (lambda et=None: self.metrics.record_api_attempt_error(et)) if self.metrics else None
            profit_ratios = _with_retries(
                lambda: self.profit_ratio_analyzer.get_profit_ratios(symbol),
                metrics_attempt=cb_attempt,
                metrics_final=cb_final
            )
            if profit_ratios and len(profit_ratios) > 0:
                latest_profit = profit_ratios[0]
                financial_data.update({
                    'net_profit_margin': DataValidator.safe_float_optional(latest_profit.get('net_profit_margin')),
                    'gross_profit_margin': DataValidator.safe_float_optional(latest_profit.get('gross_profit_margin')),
                    'profitability_grade': latest_profit.get('profitability_grade', '평가불가')
                })
        except Exception as e:
            if self.metrics:
                self.metrics.record_api_call(False, ErrorType.FINANCIAL_DATA)
            log_error("수익성비율 분석", symbol, e)
        
        # 안정성비율 분석 (current_ratio 포함)
        try:
            cb = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
            # rate_limiter 예외만 바깥에서 집계
            try:
                self.rate_limiter.acquire()
            except TimeoutError as e:
                if self.metrics:
                    self.metrics.record_api_call(False, ErrorType.API_TIMEOUT)
                raise
            
            # 실제 API는 _with_retries가 집계
            cb_final = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
            cb_attempt = (lambda et=None: self.metrics.record_api_attempt_error(et)) if self.metrics else None
            stability = _with_retries(
                lambda: self.stability_ratio_analyzer.get_stability_ratios(symbol),
                metrics_attempt=cb_attempt,
                metrics_final=cb_final
            )
            if stability and len(stability) > 0:
                latest_stab = stability[0]
                financial_data.update({
                    'current_ratio': DataValidator.safe_float_optional(latest_stab.get('current_ratio'))  # 원시값만 저장, 단위 표준화는 standardize_financial_units에서만
                })
        except Exception as e:
            if self.metrics:
                self.metrics.record_api_call(False, ErrorType.STABILITY_RATIO)
            log_error("안정성비율 분석", symbol, e)
        
        # 단위 표준화 일괄 적용 (새로운 표준화 함수 사용)
        financial_data = DataConverter.standardize_financial_units(financial_data)
        # ✅ Percent canonicalization 보호 플래그 설정
        financial_data["_percent_canonicalized"] = True
        
        # 기존 혼재 단위 정규화도 유지 (호환성) - standardize_financial_units()에서 통일 처리
        # debt_ratio, equity_ratio는 PERCENT_FIELDS에 포함되어 자동 처리됨

        # ⚠️ FIX: ROE/ROA는 이미 standardize_financial_units에서 스케일 통일됨.
        #       여기서 재차 0<x<=5 배율 보정을 하면 0.03→3.0→300.0처럼 이중 곱셈 버그가 발생.
        #       따라서 추가 보정 루프를 제거하여 이중 스케일링을 근본 차단.
        
        # PER/PBR는 get_price_data()에서 단일 소스로 계산됨 (중복 제거)
        
        # 캐시에 저장
        self._set_cached(self._cache_fin, symbol, financial_data)
        return financial_data
    
    def get_price_data(self, symbol: str) -> Dict[str, Any]:
        """가격 데이터를 조회합니다 (TTL 캐시 적용)."""
        # 캐시 확인
        hit = self._get_cached(self._cache_price, symbol)
        if hit is not None:
            return hit
            
        try:
            # 향상된 가격 프로바이더 사용 (리트라이 + 메트릭 콜백으로 일원화)
            cb_final = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
            cb_attempt = (lambda et=None: self.metrics.record_api_attempt_error(et)) if self.metrics else None
            price_data = _with_retries(
                lambda: self.price_provider.get_comprehensive_price_data(symbol),
                metrics_attempt=cb_attempt,
                metrics_final=cb_final
            )
            # 빈 페이로드 추가 집계
            
            if price_data:
                # 결측치 표현 일관성: "없으면 None"로 통일 (legitimate zero 허용)
                def _local_none_if_missing(x):
                    """None for None/NaN; allow legitimate zero"""
                    return DataValidator.safe_float_optional(x)
                
                data = {
                    'current_price': _local_none_if_missing(price_data.get('current_price')),
                    'price_change': _local_none_if_missing(price_data.get('price_change')),
                    'price_change_rate': _local_none_if_missing(price_data.get('price_change_rate')),
                    'volume': int(v) if (v := _local_none_if_missing(price_data.get('volume'))) is not None else None,
                    'eps': _local_none_if_missing(price_data.get('eps')),
                    'bps': _local_none_if_missing(price_data.get('bps')),
                    'market_cap': normalize_market_cap_ekwon(_local_none_if_missing(price_data.get('market_cap')))
                }
                
                # PER/PBR 계산 (EPS/BPS가 양수일 때만, 0원 주가 방어)
                cp = DataValidator.safe_float_optional(price_data.get('current_price'))
                eps = DataValidator.safe_float_optional(price_data.get('eps'))
                bps = DataValidator.safe_float_optional(price_data.get('bps'))
                
                # PER/PBR 계산 가드: 현실적 디폴트(환경변수로 조절 가능): 극소 EPS/BPS에서 PER/PBR 폭주 방지
                EPS_MIN = safe_env_float("EPS_MIN", 0.1, 0.0)  # 0.1원 이상만 PER 계산 (완화)
                BPS_MIN = safe_env_float("BPS_MIN", 100.0, 0.0)  # 100원 이상만 PBR 계산 (완화)
                
                # 단위 검증 로깅 (1회만, 디버깅용)
                if eps is not None and eps > 0:
                    logging.debug(f"[unit-check] EPS={eps:.2f} for {symbol} (단위: 원)")
                if bps is not None and bps > 0:
                    logging.debug(f"[unit-check] BPS={bps:.2f} for {symbol} (단위: 원)")
                # ✅ PER 계산 가드 명확화: current_price가 None이거나 0이면 스킵 (정지/단주 등)
                if eps is not None and eps > EPS_MIN and cp is not None:
                    data['per'] = DataValidator.safe_divide(cp, eps)
                else:
                    data['per'] = None  # 원인: eps_min 미달/결측/정지
                    if self.metrics:
                        self.metrics.metrics['valuation_skips']['per_epsmin'] += 1
                # ✅ PBR 계산 가드 명확화: current_price가 None이거나 0이면 스킵 (정지/단주 등)
                if bps is not None and bps > BPS_MIN and cp is not None:
                    data['pbr'] = DataValidator.safe_divide(cp, bps)
                else:
                    data['pbr'] = None  # 원인: bps_min 미달/결측/정지
                    if self.metrics:
                        self.metrics.metrics['valuation_skips']['pbr_bpsmin'] += 1
                
                # ✅ PER/PBR 상한 클램프 환경변수화: 운영 중 튜닝 가능
                PER_MAX = safe_env_float("PER_MAX_DEFAULT", 500.0, 100.0)
                PBR_MAX = safe_env_float("PBR_MAX_DEFAULT", 100.0, 10.0)
                if data['per'] is not None:
                    data['per'] = min(data['per'], PER_MAX)  # 상한 클램프
                if data['pbr'] is not None:
                    data['pbr'] = min(data['pbr'], PBR_MAX)  # 상한 클램프
                
                # 52주 고저 정보 조회 (실시간 플래그에 따라)
                w52h = _none_if_missing_strict(price_data.get('w52_high'))
                w52l = _none_if_missing_strict(price_data.get('w52_low'))
                
                if getattr(self, 'include_realtime', True) and (w52h is None or w52l is None):
                    # KIS API에서 추가 조회
                    try:
                        self.rate_limiter.acquire()
                        cb_final = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
                        cb_attempt = (lambda et=None: self.metrics.record_api_attempt_error(et)) if self.metrics else None
                        price_info = _with_retries(
                            lambda: self.provider.get_stock_price_info(symbol),
                            metrics_attempt=cb_attempt,
                            metrics_final=cb_final
                        )
                        if price_info:
                            w52h = _none_if_missing_strict(price_info.get('w52_high')) if w52h is None else w52h
                            w52l = _none_if_missing_strict(price_info.get('w52_low')) if w52l is None else w52l
                    except Exception as e:
                        if self.metrics:
                            self.metrics.record_api_call(False, ErrorType.PRICE_DATA)
                        logging.debug(f"KIS API 52주 고저 데이터 조회 실패 {symbol}: {e}")
                
                # 52주 고저 데이터 저장 (유효한 값만)
                if w52h is not None: data['w52_high'] = w52h
                if w52l is not None: data['w52_low'] = w52l
                
                # 캐시에 저장
                self._set_cached(self._cache_price, symbol, data)
                return data
        except Exception as e:
            # _with_retries가 이미 실패를 기록하므로 중복 기록 방지
            log_error("가격 데이터 조회", symbol, e)
        
        if self.metrics:
            self.metrics.record_api_call(False, ErrorType.EMPTY_PRICE_PAYLOAD)
        data = {}
        self._set_cached(self._cache_price, symbol, data)
        return data

class EnhancedScoreCalculator(ScoreCalculator):
    """향상된 점수 계산기"""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
    
    def calculate_score(self, data: Dict[str, Any], *, sector_info: Optional[Dict[str, Any]] = None, price_data: Optional[Dict[str, Any]] = None) -> Tuple[float, Dict[str, float]]:
        """통합 점수를 계산합니다 (순수 함수).
        
        가중치 처리 정책:
        - 결측 데이터는 중립점(50) 적용 후 가중치를 절반으로 줄임
        - 가중치 재정규화로 총합이 100이 되도록 조정
        - 이는 중립 편향 전략으로 안정적인 점수 산출을 보장
        """
        score = 0.0
        breakdown = {}
        
        # 각 분석 요소별 점수 계산 (None = 데이터 없음)
        def _use(score, key):
            if score is None:
                return 50.0, self.config.weights.get(key, 0) * 0.5
            return score, self.config.weights.get(key, 0)
        
        opinion_score, w_op = _use(self._calculate_opinion_score(data.get('opinion_analysis', {})), 'opinion_analysis')
        estimate_score, w_est = _use(self._calculate_estimate_score(data.get('estimate_analysis', {})), 'estimate_analysis')
        financial_score, w_fin = _use(self._calculate_financial_score(data.get('financial_data', {})), 'financial_ratios')
        growth_score, w_gro = _use(self._calculate_growth_score(data.get('financial_data', {})), 'growth_analysis')
        scale_score, w_sca = _use(self._calculate_scale_score(data.get('market_cap', 0)), 'scale_analysis')
        
        # 52주 위치 점수 계산 (missing data half weight 규칙 일관성)
        pp_raw = data.get('price_position')
        pp_score = self._calculate_price_position_score(pp_raw) if pp_raw is not None else None
        price_position_score, w_pp = _use(pp_score, 'price_position')
        
        # 점수 클램핑 (극단치/오버스케일 방지)
        def _clamp01(x): 
            return max(0.0, min(100.0, x if x is not None else 50.0))
        
        opinion_score = _clamp01(opinion_score)
        estimate_score = _clamp01(estimate_score)
        financial_score = _clamp01(financial_score)
        growth_score = _clamp01(growth_score)
        scale_score = _clamp01(scale_score)
        price_position_score = _clamp01(price_position_score)
        
        # 가중치 재정규화 (결측 데이터는 50점 + half-weight로 항상 포함)
        valid_scores = []
        weights_for_norm = []
        for s, w in [
            (opinion_score, w_op),
            (estimate_score, w_est),
            (financial_score, w_fin),
            (growth_score, w_gro),
            (scale_score, w_sca),
            (price_position_score, w_pp),
        ]:
            # _use() already returned (score_or_50, adjusted_weight)
            # So at this point s is never None; keep as-is for clarity.
            valid_scores.append((s, w))
            weights_for_norm.append(w)
        
        total_weight = sum(weights_for_norm)
        if total_weight > 0:
            score = sum(s * (w / total_weight) for s, w in valid_scores)
        else:
            score = 50.0
        
        if total_weight > 0:
            breakdown = {
                '투자의견': opinion_score * (w_op / total_weight) if opinion_score is not None else 0,
                '추정실적': estimate_score * (w_est / total_weight) if estimate_score is not None else 0,
                '재무비율': financial_score * (w_fin / total_weight) if financial_score is not None else 0,
                '성장성': growth_score * (w_gro / total_weight) if growth_score is not None else 0,
                '규모': scale_score * (w_sca / total_weight) if scale_score is not None else 0,
                '가격위치': price_position_score * (w_pp / total_weight) if price_position_score is not None else 0
            }
        else:
            breakdown = {
                '투자의견': 0, '추정실적': 0, '재무비율': 0,
                '성장성': 0, '규모': 0, '가격위치': 0
            }
        
        # 원점수 breakdown 추가 (0~100 스케일, 가중치 미적용)
        raw_breakdown = {
            'opinion_raw': opinion_score,
            'estimate_raw': estimate_score,
            'financial_raw': financial_score,
            'growth_raw': growth_score,
            'scale_raw': scale_score,
            'price_position_raw': price_position_score,
        }
        
        return min(100, max(0, score)), {**breakdown, **raw_breakdown}
    
    def _calculate_opinion_score(self, opinion_data: Dict[str, Any]) -> Optional[float]:
        """투자의견 점수 계산 (데이터 없으면 None 반환)"""
        # consensus_score를 여러 위치에서 찾기
        consensus_score = None
        if 'consensus_score' in opinion_data:
            consensus_score = opinion_data.get('consensus_score')
        elif 'consensus_analysis' in opinion_data:
            consensus_score = opinion_data.get('consensus_analysis', {}).get('consensus_score')
        
        if consensus_score is not None:
            try:
                cs = max(-1.0, min(1.0, float(consensus_score)))
                return (cs + 1.0) * 50.0  # -1~1 → 0~100
            except Exception:
                pass
        return None  # 데이터 없음
    
    def _calculate_estimate_score(self, estimate_data: Dict[str, Any]) -> Optional[float]:
        """추정실적 점수 계산 (데이터 없으면 None 반환)"""
        if not estimate_data:
            return None  # 데이터 없음
        
        w = self.config.estimate_analysis_weights
        fh = DataValidator.safe_float(estimate_data.get('financial_health_score', 0))  # 0~15
        val = DataValidator.safe_float(estimate_data.get('valuation_score', 0))        # 0~15
        
        # 둘 다 0이면 데이터 없음으로 간주
        if fh == 0 and val == 0:
            return None
        
        total_weight = w['financial_health'] + w['valuation']
        # 0~15를 가중 평균 → 0~15 → 0~100
        weighted_raw = (fh * w['financial_health'] + val * w['valuation']) / total_weight  # 0~15
        return (weighted_raw / 15.0) * 100.0
    
    def _calculate_financial_score(self, financial_data: Dict[str, Any]) -> Optional[float]:
        """재무비율 점수 계산 (존재하는 지표만 가중합, 모두 결측이면 None 반환)
        
        **이중 스케일 금지**: 이 함수는 % 입력을 전제로 함 (DataConverter.standardize_financial_units()에서 변환됨)
        """
        if not financial_data:
            return None
        
        # ✅ Percent canonicalization 보호 체크 (resilience 개선)
        if financial_data.get("_percent_canonicalized") is not True:
            logging.warning("WARNING: financial_data not canonicalized! Re-scaling detected. Applying on-the-fly canonicalization.")
            financial_data = DataConverter.standardize_financial_units(financial_data)
            financial_data["_percent_canonicalized"] = True
        
        # NOTE: 입력은 canonical % (DataConverter.standardize_financial_units 이후)
        # 재스케일 금지: 숫자 범위만 검증 (로컬 스냅샷으로 부수효과 방지)
        _roe = DataValidator.safe_float_optional(financial_data.get('roe'))
        _roa = DataValidator.safe_float_optional(financial_data.get('roa'))
        _debt = DataValidator.safe_float_optional(financial_data.get('debt_ratio'))
        _npm = DataValidator.safe_float_optional(financial_data.get('net_profit_margin'))
        _cr = DataValidator.safe_float_optional(financial_data.get('current_ratio'))

        w = self.config.financial_ratio_weights
        roe_w = w.get('roe_score', 8)
        roa_w = w.get('roa_score', 5)
        debt_w = w.get('debt_ratio_score', 7)
        npm_w = w.get('net_profit_margin_score', 5)
        cr_w = w.get('current_ratio_score', 3)

        # 로컬 스냅샷 사용 (financial_data 수정 금지)
        roe = _roe
        roa = _roa
        debt_ratio = _debt
        npm = _npm
        cr = _cr
        # Current ratio units: now fully canonicalized in standardize_financial_units

        acc = 0.0
        wsum = 0.0

        if roe is not None:
            roe_point = 1.0 if roe >= 20 else 0.75 if roe >= 15 else 0.5 if roe >= 10 else 0.25 if roe >= 5 else 0.0
            acc += roe_point * roe_w; wsum += roe_w
        if roa is not None:
            roa_point = 1.0 if roa >= 10 else 0.8 if roa >= 7 else 0.6 if roa >= 5 else 0.4 if roa >= 3 else 0.0
            acc += roa_point * roa_w; wsum += roa_w
        if debt_ratio is not None:
            debt_point = 1.0 if debt_ratio <= 30 else 0.75 if debt_ratio <= 50 else 0.5 if debt_ratio <= 70 else 0.25 if debt_ratio <= 100 else 0.0
            acc += debt_point * debt_w; wsum += debt_w
        if npm is not None:
            npm_point = 1.0 if npm >= 15 else 0.8 if npm >= 10 else 0.6 if npm >= 5 else 0.4 if npm >= 2 else 0.0
            acc += npm_point * npm_w; wsum += npm_w
        if cr is not None:
            cr_point = 1.0 if cr >= 200 else 0.67 if cr >= 150 else 0.33 if cr >= 100 else 0.0
            acc += cr_point * cr_w; wsum += cr_w

        if wsum == 0:
            return None  # 모두 결측 → 상위에서 half-weight + 50점 처리
        return (acc / wsum) * 100.0
    
    def _calculate_growth_score(self, financial_data: Dict[str, Any]) -> Optional[float]:
        """성장성 점수 계산 (데이터 없으면 None 반환)"""
        if not financial_data:
            return None  # 데이터 없음
        
        revenue_growth = DataValidator.safe_float_optional(financial_data.get('revenue_growth_rate'))
        
        # 결측치만 None 반환, 0%는 중립 점수로 처리
        if revenue_growth is None:
            return None
        
        # 입력 클립으로 극단치 방지 (-100~+100%)
        revenue_growth = max(-100.0, min(100.0, revenue_growth))
        
        thresholds = self.config.growth_score_thresholds
        
        if revenue_growth >= thresholds.get('excellent', 20):
            return 100.0
        elif revenue_growth >= thresholds.get('good', 10):
            return 80.0
        elif revenue_growth >= thresholds.get('average', 0):
            return 50.0  # 0%는 중립 점수
        elif revenue_growth >= thresholds.get('poor', -10):
            return 30.0
        elif revenue_growth >= thresholds.get('very_poor', -100):
            return 10.0
        else:
            return 0.0
    
    def _calculate_scale_score(self, market_cap: Optional[float]) -> float:
        """규모 점수 계산 (설정값 사용)"""
        if market_cap is None:
            return 50.0  # default for unknown market cap
        t = self.config.scale_score_thresholds
        if market_cap >= t.get('mega_cap', 100000):
            return 100
        elif market_cap >= t.get('large_cap', 50000):
            return 80
        elif market_cap >= t.get('mid_large_cap', 10000):
            return 60
        elif market_cap >= t.get('mid_cap', 5000):
            return 40
        elif market_cap >= t.get('small_cap', 1000):
            return 20
        else:
            return 0
    
    def _calculate_price_position_score(self, price_position: Optional[float]) -> float:
        """
        52주 위치에 따른 점수 계산 (선형화)
        
        전략적 의도:
        - 고위치(90%+) 벌점: 상단일수록 낮은 점수 (100 - position)
        - 저위치(10%-) 가점: 하단일수록 높은 점수
        - 추천 필터에서 >=85% 고위치 차단과 중복으로 이중 안전장치 역할
        
        Note: 추천 단계에서 이미 고위치 필터링이 있으므로, 
        점수와 필터가 중복으로 고위치 벌점을 주는 의도적 설계입니다.
        """
        if price_position is None:
            return 50.0  # 중립점
        
        # 선형 매핑: 고위치 벌점(상단일수록 낮은 점수), 저위치 가점
        # 0~100 → 0~100으로 매끄럽게 (100 - position)
        linear_score = 100.0 - price_position
        
        # 경계값 클램핑
        return max(0.0, min(100.0, linear_score))
    
    def _calculate_price_position_penalty(self, price_position: Optional[float]) -> float:
        """52주 위치에 따른 페널티 계산 (기존 호환성 유지)"""
        # 새로운 정규화된 점수 시스템으로 전환
        return self._calculate_price_position_score(price_position)

# =============================================================================
# 5. 메인 분석 클래스
# =============================================================================

class EnhancedIntegratedAnalyzer:
    """
    리팩토링된 향상된 통합 분석 클래스
    
    이 클래스는 다음과 같은 기능을 제공합니다:
    - 단일 종목 분석 (투자의견, 추정실적, 재무비율 통합)
    - 전체 시장 분석 (병렬 처리 지원)
    - 시가총액 상위 종목 분석
    - 업종별 분포 분석
    - 향상된 점수 계산 및 등급 평가
    
    주요 특징:
    - 안전한 데이터 접근 (객체/딕셔너리 혼용 대응)
    - 병렬 처리로 성능 최적화
    - 포괄적인 에러 처리
    - TTL 캐싱 시스템
    - 실시간 데이터 통합
    """
    
    def __init__(self, config_file: str = "config.yaml", include_realtime: bool = True, include_external: bool = True):
        # 로깅/환경 캐시 준비
        _refresh_env_cache()
        self.config_manager = ConfigManager(config_file)
        self.rate_limiter = TPSRateLimiter()
        self.include_realtime = include_realtime
        self.include_external = include_external
        
        # ✅ 환경변수 캐싱 (핫패스 최적화)
        self.env_cache = {
            'current_ratio_ambiguous_strategy': os.getenv("CURRENT_RATIO_AMBIGUOUS_STRATEGY", "as_is"),
            'current_ratio_force_percent': os.getenv("CURRENT_RATIO_FORCE_PERCENT", "false"),
            'market_cap_strict_mode': os.getenv("MARKET_CAP_STRICT_MODE", "true"),
            'sector_target_good': safe_env_int("SECTOR_TARGET_GOOD", 60, 10),
            'max_sector_peers_base': safe_env_int("MAX_SECTOR_PEERS_BASE", 40, 5),
            'max_sector_peers_full': safe_env_int("MAX_SECTOR_PEERS_FULL", 200, 20),
            'max_sector_cache_entries': safe_env_int("MAX_SECTOR_CACHE_ENTRIES", 64, 1),
            'max_sector_api_boost': safe_env_int("MAX_SECTOR_API_BOOST", 10, 0),
        }
        
        # 메트릭 수집기 초기화
        self.metrics = MetricsCollector()
        
        # 분석기 초기화
        self.opinion_analyzer = InvestmentOpinionAnalyzer()
        self.estimate_analyzer = EstimatePerformanceAnalyzer()
        self.provider = KISDataProvider()
        self.data_provider = FinancialDataProvider(self.provider, self.rate_limiter, metrics=self.metrics)
        # 플래그 전달
        self.data_provider.include_realtime = self.include_realtime
        
        # 설정 로드
        self.config = self._load_analysis_config()
        self.score_calculator = EnhancedScoreCalculator(self.config)
        self._validate_config()
        
        # ✅ 스레드 안전성을 위한 락 추가
        self._sector_warned_lock = RLock()
        self._sector_warned: Set[str] = set()
        
        # KOSPI 데이터 로드
        self.kospi_data = None
        self._load_kospi_data()
        
        # 섹터 벡터 캐시 (TTL 10분)
        self._sector_cache = OrderedDict()
        self._sector_cache_ttl = 600  # 10분
        self._sector_cache_lock = RLock()
        
        # 섹터 특성 캐시 (TTL 30분)
        self._sector_char_cache = OrderedDict()
        self._sector_char_cache_ttl = 1800  # 30분
        self._sector_char_cache_lock = RLock()
        
        # 외부 분석기 스레드 안전성을 위한 락 (분리)
        self._opinion_lock = RLock()
        self._estimate_lock = RLock()
    
    def _result_to_dict(self, r: AnalysisResult) -> Dict[str, Any]:
        """Convert AnalysisResult to serializable dict for JSON export"""
        pdict = r.price_data or {}
        
        # 대시보드용 요약 필드 생성
        sector_summary = ""
        if r.sector_analysis and r.sector_analysis.get('total_score') is not None:
            score = r.sector_analysis.get('total_score', 0)
            grade = r.sector_analysis.get('grade', 'N/A')
            sector_summary = f"{grade}({score:.1f})"
        
        d = {
            "symbol": r.symbol,
            "name": r.name,
            "enhanced_score": r.enhanced_score,
            "enhanced_grade": r.enhanced_grade,
            "market_cap": r.market_cap,
            "current_price": pdict.get("current_price"),
            "price_position": r.price_position,
            "w52_high": pdict.get("w52_high"),
            "w52_low": pdict.get("w52_low"),
            "per": pdict.get("per"),
            "pbr": pdict.get("pbr"),
            "score_breakdown": r.score_breakdown,
            "financial_data": r.financial_data,
            "sector_analysis": r.sector_analysis,
            # 대시보드용 요약 필드
            "sector_valuation": sector_summary,
            "opinion_summary": r.opinion_analysis.get('summary', '') if r.opinion_analysis else '',
            "estimate_summary": r.estimate_analysis.get('summary', '') if r.estimate_analysis else '',
        }
        # ✅ 직렬화 안전성 강화: 넘파이 스칼라 등 처리
        return serialize_for_json(d)
    
    def _load_analysis_config(self) -> AnalysisConfig:
        """분석 설정을 로드합니다."""
        config = self.config_manager.load_config()
        enhanced_config = config.get('enhanced_integrated_analysis', {})
        
        return AnalysisConfig(
            weights=enhanced_config.get('weights', {
                'opinion_analysis': 25,
                'estimate_analysis': 30,
                'financial_ratios': 30,
                'growth_analysis': 10,
                'scale_analysis': 5,
                'price_position': 5
            }),
            financial_ratio_weights=enhanced_config.get('financial_ratio_weights', {
                'roe_score': 8,
                'roa_score': 5,
                'debt_ratio_score': 7,
                'net_profit_margin_score': 5,
                'current_ratio_score': 3,
                'growth_score': 2
            }),
            estimate_analysis_weights=enhanced_config.get('estimate_analysis_weights', {
                'financial_health': 15,
                'valuation': 15
            }),
            grade_thresholds=enhanced_config.get('grade_thresholds', {
                'A_plus': 80,
                'A': 70,
                'B_plus': 60,
                'B': 50,
                'C_plus': 40,
                'C': 30,
                'D_plus': 20,
                'D': 10,
                'F': 0
            }),
            growth_score_thresholds=enhanced_config.get('growth_score_thresholds', {
                'excellent': 20,
                'good': 10,
                'average': 0,
                'poor': -10,
                'very_poor': -100
            }),
            scale_score_thresholds=enhanced_config.get('scale_score_thresholds', {
                'mega_cap': 100000,
                'large_cap': 50000,
                'mid_large_cap': 10000,
                'mid_cap': 5000,
                'small_cap': 1000,
                'micro_cap': 0
            }),
        )
    
    def _validate_config(self) -> None:
        """설정 가중치/임계값 sanity-check (경고만)"""
        try:
            w = self.config.weights
            total = sum(float(w.get(k,0)) for k in w)
            if total <= 0:
                logging.warning("[config] weights 합이 0 이하입니다. 기본 가중치 권장")
            for name, thr in self.config.scale_score_thresholds.items():
                if not isinstance(thr, (int,float)):
                    logging.warning(f"[config] scale threshold '{name}'이 숫자가 아님")
        except Exception as e:
            logging.debug(f"[config] validate 실패: {e}")
    
    def _load_kospi_data(self):
        """KOSPI 마스터 데이터를 로드합니다 (xlsx/csv 지원)."""
        try:
            # ✅ CSV 지원 옵션 추가 (I/O 감소)
            kospi_csv = 'kospi_code.csv'
            kospi_xlsx = 'kospi_code.xlsx'
            
            if os.path.exists(kospi_csv):
                # CSV 우선 로드 (더 빠른 I/O)
                try:
                    self.kospi_data = pd.read_csv(kospi_csv, encoding='utf-8-sig')
                    logging.info(f"KOSPI 데이터 로드 완료 (CSV): {kospi_csv}")
                except Exception as e:
                    logging.warning(f"CSV 읽기 실패: {e}")
                    self.kospi_data = pd.DataFrame()
                    return
            elif os.path.exists(kospi_xlsx):
                try:
                    self.kospi_data = pd.read_excel(kospi_xlsx, engine="openpyxl")
                    logging.info(f"KOSPI 데이터 로드 완료 (Excel): {kospi_xlsx}")
                except ImportError:
                    try:
                        self.kospi_data = pd.read_excel(kospi_xlsx)  # 판다스 기본 엔진 시도
                    except Exception as e:
                        logging.warning(f"xlsx 읽기 실패: openpyxl 설치 권장. 원인: {e}")
                        self.kospi_data = pd.DataFrame()
                        return
            else:
                logging.warning("KOSPI 마스터 파일을 찾을 수 없습니다. (kospi_code.csv 또는 kospi_code.xlsx)")
                self.kospi_data = pd.DataFrame()
                return
            
            # 공통 데이터 처리 (CSV/Excel 공통)
            if not self.kospi_data.empty:
                # ✅ KOSPI 스키마 별칭 지원 (다양한 환경 대응)
                column_aliases = {
                    '종목명': '한글명',
                    '종목코드': '단축코드',
                    '코드': '단축코드',
                    '시총': '시가총액',
                    'market_cap': '시가총액',
                    'name': '한글명',
                    'symbol': '단축코드'
                }
                
                # 별칭 적용
                for alias, standard in column_aliases.items():
                    if alias in self.kospi_data.columns and standard not in self.kospi_data.columns:
                        self.kospi_data[standard] = self.kospi_data[alias]
                        logging.info(f"컬럼 별칭 적용: '{alias}' → '{standard}'")
                
                self.kospi_data['단축코드'] = (
                    self.kospi_data['단축코드']
                        .astype(str)
                        .str.replace(r'\.0$', '', regex=True)
                        .str.zfill(6)
                )
                
                # 스키마 검증
                required_cols = {"단축코드", "한글명", "시가총액"}
                if not required_cols.issubset(self.kospi_data.columns):
                    # 스키마 정보 로깅 (운영 지원)
                    detected_cols = list(self.kospi_data.columns)[:10]  # 처음 10개 컬럼만
                    logging.error(f"KOSPI 스키마 불일치: 필요컬럼 {required_cols}, 감지된 컬럼 {detected_cols}")
                    raise ValueError(f"KOSPI 스키마 불일치: 필요컬럼 {required_cols}, 실제 {set(self.kospi_data.columns)}")
                
                # 시가총액 컬럼 정리 (혼합 타입 처리)
                if '시가총액' in self.kospi_data.columns:
                    self.kospi_data['시가총액'] = pd.to_numeric(
                        self.kospi_data['시가총액'].astype(str).str.replace(',', ''), errors='coerce'
                    )  # no fillna - keep NaN for unknown market caps
                
                # 유효한 6자리 종목 코드만 필터링
                original_count = len(self.kospi_data)
                self.kospi_data = self.kospi_data[
                    self.kospi_data['단축코드'].str.match(r'^\d{6}$', na=False)
                ]
                filtered_count = len(self.kospi_data)
                
                logging.info(f"KOSPI 마스터 데이터 로드 완료: {original_count}개 → {filtered_count}개 유효 종목")
                
                # ✅ pandas filtering 최적화: 인덱스 설정 (임시 비활성화)
                # if not self.kospi_data.empty and '단축코드' in self.kospi_data.columns:
                #     self.kospi_data = self.kospi_data.set_index('단축코드')
                #     logging.debug("KOSPI 데이터 인덱스 설정 완료 (단축코드)")
        except Exception as e:
            log_error("KOSPI 데이터 로드", error=e, level="error")
            self.kospi_data = pd.DataFrame()
    
    def analyze_single_stock(self, symbol: str, name: str, days_back: int = 30) -> AnalysisResult:
        """
        단일 종목 분석을 수행합니다.
        
        Args:
            symbol (str): 종목 코드 (6자리 숫자)
            name (str): 종목명
            days_back (int): 투자의견 분석 기간 (일)
            
        Returns:
            AnalysisResult: 분석 결과 객체
            
        Raises:
            ValueError: 종목 코드가 유효하지 않은 경우
            ValueError: 종목명이 없는 경우
        """
        start_time = _monotonic()
        try:
            # 입력 검증
            if not DataValidator.is_valid_symbol(symbol):
                return AnalysisResult(
                    symbol=symbol,
                    name=name,
                    status=AnalysisStatus.ERROR,
                    error=f"유효하지 않은 종목 코드: {symbol}"
                )
            
            if not name or not isinstance(name, str):
                return AnalysisResult(
                    symbol=symbol,
                    name=name or "Unknown",
                    status=AnalysisStatus.ERROR,
                    error="종목명이 없거나 유효하지 않음"
                )
            
            # 우선주 확인
            if self._is_preferred_stock(name):
                logging.info(f"우선주 제외: {name} ({symbol})")
                return AnalysisResult(
                    symbol=symbol,
                    name=name,
                    status=AnalysisStatus.SKIPPED_PREF,
                    enhanced_score=0,
                    enhanced_grade='F',
                    error="preferred stock filtered"
                )
            
            # 각 분석 수행
            opinion_analysis = self._analyze_opinion(symbol, days_back, name=name)
            estimate_analysis = self._analyze_estimate(symbol, name=name)
            financial_data = self.data_provider.get_financial_data(symbol)
            price_data = self.data_provider.get_price_data(symbol)
            
            # 데이터 부족 상태 확인
            if not financial_data and not price_data:
                return AnalysisResult(
                    symbol=symbol,
                    name=name,
                    status=AnalysisStatus.NO_DATA,
                    error="no price & financial data"
                )
            
            # 시가총액 조회
            market_cap = self._get_market_cap(symbol)
            
            # 섹터 분석 수행 (중복 페치 방지)
            sector_analysis = self._analyze_sector(symbol, name, price_data=price_data, financial_data=financial_data)
            
            # 통합 점수 계산
            analysis_data = {
                'opinion_analysis': opinion_analysis,
                'estimate_analysis': estimate_analysis,
                'financial_data': financial_data,
                'market_cap': market_cap,
                'current_price': price_data.get('current_price', 0),
                'price_position': self._calculate_price_position(price_data),
                'sector_info': self._get_sector_characteristics(symbol),
                'sector_analysis': sector_analysis,
                'price_data': price_data,
            }
            
            # 스코어러에 명시적 파라미터 전달 (순수 함수)
            enhanced_score, score_breakdown = self.score_calculator.calculate_score(
                analysis_data, 
                sector_info=analysis_data['sector_info'], 
                price_data=analysis_data['price_data']
            )
            enhanced_grade = self._get_grade(enhanced_score)
            
            # 기존 통합 분석
            integrated_analysis = create_integrated_analysis(opinion_analysis, estimate_analysis)
            
            return AnalysisResult(
                symbol=symbol,
                name=name,
                status=AnalysisStatus.SUCCESS,
                enhanced_score=enhanced_score,
                enhanced_grade=enhanced_grade,
                market_cap=market_cap,
                current_price=price_data.get('current_price', 0),
                price_position=analysis_data['price_position'],
                price_band_outside=self._is_price_outside_52w_band(price_data),  # 52주 밴드 밖 여부
                financial_data=financial_data,
                opinion_analysis=opinion_analysis,
                estimate_analysis=estimate_analysis,
                integrated_analysis=integrated_analysis,
                score_breakdown=score_breakdown,
                price_data=price_data,  # 가격 데이터 캐싱
                sector_analysis=sector_analysis  # 섹터 분석 결과 추가
            )
            
        except Exception as e:
            log_error("종목 분석", f"{name}({symbol})", e, "error")
            return AnalysisResult(
                symbol=symbol,
                name=name,
                status=AnalysisStatus.ERROR,
                error=str(e)
            )
        finally:
            # 분석 소요 시간 기록
            if hasattr(self, "metrics") and self.metrics:
                self.metrics.record_analysis_duration(_monotonic() - start_time)
    
    def _is_preferred_stock(self, name: str) -> bool:
        """우선주 여부 확인"""
        return DataValidator.is_preferred_stock(name)
    
    def _analyze_opinion(self, symbol: str, days_back: int, name: str = "") -> Dict[str, Any]:
        """투자의견 분석 (컨텍스트 보강)"""
        if not self.include_external:
            return {}
        try:
            with self._opinion_lock:
                cb_final = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
                cb_attempt = (lambda et=None: self.metrics.record_api_attempt_error(et)) if self.metrics else None
                return _with_retries(
                    lambda: self.opinion_analyzer.analyze_single_stock(symbol, days_back=days_back),
                    metrics_attempt=cb_attempt,
                    metrics_final=cb_final
                )
        except Exception as e:
            if self.metrics:
                self.metrics.record_api_call(False, ErrorType.OPINION)
            log_error("투자의견 분석", f"{symbol}({name})", e)
            return {}
    
    def _analyze_estimate(self, symbol: str, name: str = "") -> Dict[str, Any]:
        """추정실적 분석 (컨텍스트 보강)"""
        if not self.include_external:
            return {}
        try:
            with self._estimate_lock:
                cb_final = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
                cb_attempt = (lambda et=None: self.metrics.record_api_attempt_error(et)) if self.metrics else None
                return _with_retries(
                    lambda: self.estimate_analyzer.analyze_single_stock(symbol),
                    metrics_attempt=cb_attempt,
                    metrics_final=cb_final
                )
        except Exception as e:
            if self.metrics:
                self.metrics.record_api_call(False, ErrorType.ESTIMATE)
            log_error("추정실적 분석", f"{symbol}({name})", e)
            return {}
    
    def _analyze_sector(self, symbol: str, name: str = "", *, price_data: Dict[str, Any] = None, financial_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """섹터 분석 수행 (중복 페치 방지)"""
        try:
            # --- 공용 헬퍼를 함수 상단에 정의 (스코프 버그 방지) ---
            def _delta(score_0_100, weight):
                # 0~100 → -50~+50 로 바꾼 뒤 weight%를 곱해서 가/감점
                s = 0.0 if score_0_100 is None else max(0.0, min(100.0, float(score_0_100)))
                return (s - 50.0) * (weight / 100.0)
            # --------------------------------------------------------------------

            # 기본 섹터 정보 가져오기
            sector_info = self._get_sector_characteristics(symbol)
            sector_name = sector_info.get('name', '기타')
            
            # 전달받은 데이터 사용 또는 새로 페치
            price_data = price_data or self.data_provider.get_price_data(symbol)
            financial_data = financial_data or self.data_provider.get_financial_data(symbol)
            
            if not price_data or not financial_data:
                return {'grade': 'C', 'total_score': 50.0,
                        'breakdown': {'재무_건전성': 50.0, '성장성': 50.0, '안정성': 50.0}}
            
            # PER, PBR, ROE 기반 점수 계산 (결측=0으로 오염 방지: safe_float_optional 사용)
            per = DataValidator.safe_float_optional(price_data.get('per'))
            pbr = DataValidator.safe_float_optional(price_data.get('pbr'))
            roe = DataValidator.safe_float_optional(financial_data.get('roe'))
            market_cap_pd = normalize_market_cap_ekwon(DataValidator.safe_float_optional(price_data.get('market_cap', 0)))
            
            # 섹터 백분위 기반 스코어를 우선 사용하고, 없으면 기존 선형 매핑 사용
            sector_val = self._evaluate_valuation_by_sector(
                symbol,
                per=per if per is not None else float('nan'),
                pbr=pbr if pbr is not None else float('nan'),
                roe=roe if roe is not None else float('nan'),
                market_cap=market_cap_pd,
                price_data=price_data,
                financial_data=financial_data
            )
            
            # 재무_건전성 점수
            if sector_val and sector_val.get('total_score') is not None:
                financial_score = float(sector_val['total_score'])
            else:
                # 섹터 데이터 없으면 None으로 반환하여 상위 half-weight 로직 한 번만 적용
                financial_score = None

            # 성장성 점수 (ROE 기반 가/감점)
            growth_score = 50.0
            if roe is not None and roe > 0:
                roe_score = self._calculate_metric_score(roe, min_val=5, max_val=20, reverse=False)
                if roe_score is not None:
                    growth_score += _delta(roe_score, 25)

            # 안정성 점수 (시총 기반 가/감점)
            stability_score = 50.0
            market_cap_file = self._get_market_cap(symbol)  # 억원 단위(파일 기준)
            mc = market_cap_file if market_cap_file else (market_cap_pd or 0)
            if mc > 100000: stability_score += 20
            elif mc > 50000: stability_score += 10

            # 각 스코어/최종 클램프 (None 안전 처리)
            def _clamp_0_100(x, default=50.0):
                """값을 0-100 범위로 클램프하되, None이면 기본값 반환"""
                if x is None:
                    return default
                try:
                    return max(0.0, min(100.0, float(x)))
                except (ValueError, TypeError):
                    return default
            
            financial_score = _clamp_0_100(financial_score, 50.0)
            growth_score    = _clamp_0_100(growth_score, 50.0)
            stability_score = _clamp_0_100(stability_score, 50.0)
            total_score     = _clamp_0_100((financial_score + growth_score + stability_score) / 3.0, 50.0)
            
            # 등급 결정
            if total_score >= 80:
                grade = 'A+'
            elif total_score >= 75:
                grade = 'A'
            elif total_score >= 70:
                grade = 'B+'
            elif total_score >= 65:
                grade = 'B'
            elif total_score >= 60:
                grade = 'C+'
            elif total_score >= 55:
                grade = 'C'
            else:
                grade = 'D'
            
            # 평면 스키마로 반환 (정규화 헬퍼에서 그대로 소비)
            return {
                'grade': grade,
                'total_score': float(total_score),
                'breakdown': {
                    '재무_건전성': float(financial_score),
                    '성장성': float(growth_score),
                    '안정성': float(stability_score),
                },
                'is_leader': self._is_sector_leader(symbol, sector_name)
            }
            
        except Exception as e:
            logging.debug(f"섹터 분석 실패 {symbol}: {e}")
            return {'grade': 'C', 'total_score': 50.0,
                    'breakdown': {'재무_건전성': 50.0, '성장성': 50.0, '안정성': 50.0}}
    

    def _get_market_cap(self, symbol: str) -> Optional[float]:
        """시가총액 조회 (억원 단위)
        
        Note: KOSPI 파일의 시가총액 컬럼은 억원 단위로 가정합니다.
        다른 단위(원/백만/십억)인 경우 일관성을 위해 변환이 필요합니다.
        """
        if self.kospi_data is not None and not self.kospi_data.empty:
            stock_info = self.kospi_data[self.kospi_data['단축코드'] == str(symbol)]
            if not stock_info.empty:
                mc = stock_info.iloc[0]['시가총액']
                if pd.isna(mc):
                    return None  # unknown market cap
                return float(mc)
        return None
    
    def _calculate_price_position(self, price_data: Dict[str, Any]) -> Optional[float]:
        """52주 위치 계산 (NaN/0-division 방지, 밴드 밖도 클램프)"""
        cp = DataValidator.safe_float_optional(price_data.get('current_price'))
        hi = DataValidator.safe_float_optional(price_data.get('w52_high'))
        lo = DataValidator.safe_float_optional(price_data.get('w52_low'))
        
        if cp is None or hi is None or lo is None:
            logging.debug("Missing 52w inputs for price position")
            return None
        if not (cp > 0 and hi > 0 and lo > 0):
            return None
        band = hi - lo
        # ✅ 52주 밴드 임계치 환경변수화 (기본 0.1%)
        tiny_band_threshold = safe_env_float("POS_TINY_BAND_THRESHOLD", 0.001, 0.0)  # 0.1%
        
        # 상대·절대 동시 체크로 float 오차 및 극미/퇴화 케이스 방지
        if band <= 0 or band/hi <= tiny_band_threshold or band <= 1e-6:
            logging.debug(f"Tiny/degenerate 52w band: hi={hi}, lo={lo}, cp={cp}")
            # 퇴화 케이스 메트릭 기록 (운영 모니터링용) – API 실패로 집계하지 않음
            if hasattr(self, 'metrics') and self.metrics:
                self.metrics.metrics['errors_by_type'][ErrorType.INVALID_52W_BAND] = \
                    self.metrics.metrics['errors_by_type'].get(ErrorType.INVALID_52W_BAND, 0) + 1
            return None
        
        raw = (cp - lo) / band * 100.0
        return max(0.0, min(100.0, raw))
    
    def _is_price_outside_52w_band(self, price_data: Dict[str, Any]) -> bool:
        """현재가가 52주 밴드 밖인지 확인 (UI 경고용)"""
        cp = DataValidator.safe_float_optional(price_data.get('current_price'))
        hi = DataValidator.safe_float_optional(price_data.get('w52_high'))
        lo = DataValidator.safe_float_optional(price_data.get('w52_low'))
        
        if cp is None or hi is None or lo is None or not (cp > 0 and hi > 0 and lo > 0):
            return False
        return cp < lo or cp > hi
    
    def _analyze_profit_trend(self, financial_data: Dict[str, Any]) -> str:
        """이익률 추세 분석 (중복 API 호출 제거)"""
        try:
            if not financial_data:
                return "unknown"
            current_roe = DataValidator.safe_float(financial_data.get('roe', 0))
            if current_roe <= 0:
                return "unknown"
            return "stable"
        except Exception as e:
            log_error("이익률 추세 분석", error=e)
            return "unknown"
    
    def _get_sector_characteristics(self, symbol: str) -> Dict[str, Any]:
        """업종별 특성 정보 반환 (캐시 적용)"""
        now = _monotonic()
        
        # 캐시 확인 (섹터명 기준 캐시 우선 시도)
        with self._sector_char_cache_lock:
            # 1) 심볼→섹터명 캐시 (얕은 캐시) - 일관성을 위해 str(symbol) 사용
            sym_hit = self._sector_char_cache.get(f"sym:{str(symbol)}")
            if sym_hit and now - sym_hit[0] < self._sector_char_cache_ttl:
                sector = sym_hit[1]['name']
                sec_hit = self._sector_char_cache.get(f"sec:{sector}")
                if sec_hit and now - sec_hit[0] < self._sector_char_cache_ttl:
                    return sec_hit[1]
            
            # 레거시 키 경로 제거: 모든 캐시는 'sym:'/'sec:' 접두 사용
        
        try:
            # 하드코딩된 업종 매핑 (우선 적용)
            sector_mapping = {
                '005930': '기술업',  # 삼성전자
                '000660': '기술업',  # SK하이닉스
                '207940': '바이오/제약',  # 삼성바이오로직스
                '000270': '제조업',  # 기아
                '329180': '제조업',  # HD현대중공업
                '105560': '금융업',  # KB금융
                '005380': '제조업',  # 현대차
                '012330': '제조업',  # 현대모비스
                '035420': '기술업',  # NAVER
                '035720': '기술업',  # 카카오
            }
            
            result = None
            
            # 하드코딩된 매핑에서 먼저 찾기
            if str(symbol) in sector_mapping:
                sector = sector_mapping[str(symbol)]
                result = self._get_sector_benchmarks(sector)
            else:
                # KOSPI 데이터에서 업종 정보 가져오기 (여러 컬럼 후보 확인)
                if hasattr(self, 'kospi_data') and not self.kospi_data.empty:
                    stock_info = self.kospi_data[self.kospi_data['단축코드'] == str(symbol)]
                    if not stock_info.empty:
                        for col in ('업종', '지수업종대분류', '업종명', '섹터'):
                            if col in stock_info.columns:
                                sector = str(stock_info.iloc[0].get(col) or '기타')
                                if sector and sector != '기타':
                                    result = self._get_sector_benchmarks(sector)
                                    break
                
                if result is None:
                    # 운영 안전을 위한 강제 폴백 옵션
                    force_fallback = os.getenv("SECTOR_FORCE_FALLBACK", "false").lower() == "true"
                    if force_fallback:
                        logging.warning(f"섹터 정보 없음, 강제 폴백 적용: {symbol}")
                    result = self._get_sector_benchmarks('기타')
            
            # 캐시에 저장 (섹터명 기준 캐시 + 심볼→섹터명 매핑)
            with self._sector_char_cache_lock:
                sector = result.get('name', '기타')
                sym_key = str(symbol)  # ✅ 심볼 키 문자열화: 타입 안전성 보장 (sym:, sec: 키만 사용)
                self._sector_char_cache[f"sym:{sym_key}"] = (now, {"name": sector})
                self._sector_char_cache[f"sec:{sector}"] = (now, result)
                # ✅ 레거시 키 제거: 충돌 방지 및 캐시 크기 최적화
                # 캐시 크기 제한 (LRU 방식) - sym:/sec: 쌍 삽입 고려하여 2회 pop
                while len(self._sector_char_cache) > 512:
                    self._sector_char_cache.popitem(last=False)
                    # 쌍으로 삽입되므로 한 번 더 pop
                    if len(self._sector_char_cache) > 512:
                        self._sector_char_cache.popitem(last=False)
            
            return result
            
        except Exception as e:
            log_error("업종 특성 분석", symbol, e)
            result = self._get_sector_benchmarks('기타')
            # 에러 케이스도 캐시에 저장 (짧은 TTL 유사 효과를 위해 'now' 보정)
            now = _monotonic()
            with self._sector_char_cache_lock:
                sector = result.get('name', '기타')
                sym_key = str(symbol)  # ✅ 심볼 키 문자열화: 타입 안전성 보장 (sym:, sec: 키만 사용)
                self._sector_char_cache[f"sym:{sym_key}"] = (now, {"name": sector})
                self._sector_char_cache[f"sec:{sector}"] = (now, result)
                # ✅ 레거시 키 제거: 충돌 방지 및 캐시 크기 최적화
            return result
    
    def _sanitize_leaders(self, leaders):
        """섹터 리더 목록 정합성 검증 (KOSPI 데이터 기준)"""
        if self.kospi_data is None or self.kospi_data.empty:
            return leaders
        codes = set(self.kospi_data['단축코드'].astype(str))
        return [c for c in leaders if c in codes]
    
    def _get_sector_benchmarks(self, sector: str) -> Dict[str, Any]:
        """업종별 벤치마크 기준 반환"""
        # 섹터명 동의어 매핑
        SECTOR_ALIASES = {
            'it': '기술업', '정보기술': '기술업', '소프트웨어': '기술업',
            '바이오': '바이오/제약', '제약': '바이오/제약', '생명과학': '바이오/제약',
            '자동차': '제조업', '전자': '제조업', '화학': '제조업',
            '은행': '금융업', '증권': '금융업', '보험': '금융업',
            '건설': '건설업', '부동산': '건설업',
            '유통': '소비재', '식품': '소비재', '의류': '소비재',
            '에너지': '에너지/화학', '석유': '에너지/화학',
            '통신': '통신업', '미디어': '통신업'
        }
        
        # ✅ 섹터 동의어 처리 가드 강화 (None/비문자 처리)
        normalized_sector = SECTOR_ALIASES.get(str(sector).lower(), str(sector)) if sector else "기타"
        
        benchmarks = {
            '금융업': {
                'per_range': (5, 15),
                'pbr_range': (0.5, 2.0),
                'roe_range': (8, 20),
                'description': '안정적 수익성, 낮은 PBR',
                'leaders': ['105560', '055550', '086790']  # KB금융, 신한지주, 하나금융
            },
            '기술업': {
                'per_range': (15, 50),
                'pbr_range': (1.5, 8.0),
                'roe_range': (10, 30),
                'description': '높은 성장성, 높은 PER',
                'leaders': ['005930', '000660', '035420', '035720']  # 삼성전자, SK하이닉스, NAVER, 카카오
            },
            '제조업': {
                'per_range': (8, 25),
                'pbr_range': (0.8, 3.0),
                'roe_range': (8, 20),
                'description': '안정적 수익성, 적정 PER',
                'leaders': ['005380', '000270', '012330', '329180']  # 현대차, 기아, 현대모비스, HD현대중공업
            },
            '바이오/제약': {
                'per_range': (20, 100),
                'pbr_range': (2.0, 10.0),
                'roe_range': (5, 25),
                'description': '높은 불확실성, 높은 PER',
                'leaders': ['207940', '068270', '006280']  # 보수적으로 유지: 삼성바이오로직스, 셀트리온, 녹십자
            },
            '에너지/화학': {
                'per_range': (5, 20),
                'pbr_range': (0.5, 2.5),
                'roe_range': (5, 15),
                'description': '사이클 특성, 변동성 큰 수익',
                'leaders': ['034020', '010140']  # 두산에너빌리티(에너지), 삼성중공업(조선/제조) 포함: 참고용
            },
            '소비재': {
                'per_range': (10, 30),
                'pbr_range': (1.0, 4.0),
                'roe_range': (8, 18),
                'description': '안정적 수요, 적정 수익성',
                'leaders': []  # 업종과 안 맞는 항목 제거 (SK텔레콤은 통신업, 현대건설은 건설업)
            },
            '통신업': {
                'per_range': (8, 20),
                'pbr_range': (0.8, 3.0),
                'roe_range': (6, 15),
                'description': '현금흐름 안정',
                'leaders': ['017670']  # SK텔레콤 등 통신업 리더
            },
            '건설업': {
                'per_range': (5, 15),
                'pbr_range': (0.5, 2.0),
                'roe_range': (5, 12),
                'description': '프로젝트 사이클 영향',
                'leaders': ['000720']  # 현대건설 등 건설업 리더
            },
            '기타': {
                'per_range': (8, 25),
                'pbr_range': (0.8, 3.0),
                'roe_range': (8, 20),
                'description': '일반적 기준',
                'leaders': []
            }
        }
        
        # 정규화된 섹터명으로 매칭
        sector_key = '기타'
        s = str(normalized_sector).strip().lower()
        for key in benchmarks.keys():
            if s == key.lower():
                sector_key = key
                break
        else:
            for key in benchmarks.keys():
                if key.lower() in s or s in key.lower():
                    sector_key = key
                    break
        
        ret = benchmarks.get(sector_key, benchmarks['기타']).copy()
        ret['name'] = sector_key
        ret['leaders'] = self._sanitize_leaders(ret.get('leaders', []))
        return ret
    
    def _is_sector_leader(self, symbol: str, sector: str) -> bool:
        """업종별 대장주 여부 확인"""
        try:
            sector_info = self._get_sector_benchmarks(sector)
            leaders = sector_info.get('leaders', [])
            return str(symbol) in leaders
        except Exception:
            return False
    
    def _calculate_leader_bonus(self, symbol: str, sector: str, market_cap: float,
                                price_data: Dict[str, Any] = None, financial_data: Dict[str, Any] = None) -> float:
        """업종별 대장주 가산점 계산
        
        Args:
            symbol: 종목 코드
            sector: 업종명
            market_cap: 시가총액 (억원 단위)
            price_data: 가격 데이터
            financial_data: 재무 데이터
            
        Returns:
            대장주 가산점 (0.0 ~ 10.0)
        """
        try:
            # 섹터 정보 검증 - 매핑 실패 시 보너스 0
            sector_info = self._get_sector_benchmarks(sector)
            if not sector_info or sector_info.get('name') == '기타':
                return 0.0
            
            # 대장주 여부 확인
            is_leader = self._is_sector_leader(symbol, sector)
            if not is_leader:
                return 0.0
            
            # 품질 조건 추가: ROE >= 8 & PBR <= 섹터 상단
            price = price_data or self.data_provider.get_price_data(symbol)
            fin = financial_data or self.data_provider.get_financial_data(symbol)
            pbr = DataValidator.safe_float_optional(price.get('pbr'))
            roe = DataValidator.safe_float_optional(fin.get('roe'))
            
            # 결측값은 보너스 0으로 엄격 처리
            if pbr is None or roe is None:
                return 0.0
            
            # 품질 컷: ROE < 8 또는 PBR > 섹터 상단 시 보너스 없음 (PBR 유연화)
            pbr_upper = sector_info['pbr_range'][1] * safe_env_float("LEADER_PBR_TOL", 1.1, 1.0)
            if roe < 8 or pbr > pbr_upper:
                return 0.0
            
            # 강도 축소: 캡 5점 (억원 기준)
            if market_cap >= 1_000_000:  # 100조원 이상
                return 5.0
            elif market_cap >= 500_000:  # 50조원 이상
                return 4.0
            elif market_cap >= 100_000:  # 10조원 이상
                return 3.5
            elif market_cap >= 50_000:   # 5조원 이상
                return 3.0
            else:  # 5조원 미만
                return 2.5
                
        except Exception as e:
            log_error("대장주 가산점 계산", symbol, e)
            return 0.0
    
    def _evaluate_valuation_by_sector(self, symbol: str, per: float, pbr: float, roe: float, market_cap: float = 0,
                                      price_data: Dict[str, Any] = None, financial_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """섹터 내부 백분위 기반 밸류에이션 평가"""
        start_time = _monotonic()
        try:
            
            sector_info = self._get_sector_characteristics(symbol)
            sector_name = sector_info.get('name', '기타')
            
            # 섹터 동종군 샘플링 + 캐시 사용
            vals = self._get_sector_peers_snapshot(sector_name)
            
            # 백분위 계산
            if len(vals) == 0:
                return {
                    'total_score': None,   # ← None으로 올려 half-weight 규칙 적용 가능
                    'base_score': None,
                    'leader_bonus': 0.0,
                    'is_leader': False,
                    'grade': 'N/A',
                    'description': '데이터 부족',
                    'per_score': None, 'pbr_score': None, 'roe_score': None,
                    'sector_info': sector_info,
                    'notes': ['insufficient_peers']
                }
            
            arr = np.array(vals, dtype=float)
            if arr.ndim == 1:  # 1차원 배열인 경우 2차원으로 변환
                arr = arr.reshape(-1, 3)
            
            notes = []
            
            def pct_rank(x, col):
                if x is None or not isinstance(x, (int, float)) or not math.isfinite(x):
                    return None  # 결측치로 처리하여 가중치 제외
                if arr.shape[1] <= col:
                    return None
                colv = np.asarray(arr[:, col], dtype=float)
                colv = colv[~np.isnan(colv)]
                if colv.size == 0:
                    return None
                if len(colv) < 10:
                    # ✅ 표본 부족 시 해당 지표 가중치 제외 (None 반환) + 메트릭 기록
                    if self.metrics:
                        self.metrics.record_sector_sample_insufficient(sector_name)
                    col_names = ['per', 'pbr', 'roe']
                    col_name = col_names[col] if col < len(col_names) else f'col_{col}'
                    notes.append(f"insufficient_peers_{col_name}")
                    
                    # ✅ 스레드 안전한 스로틀링된 로깅: 첫 번째는 WARN, 이후는 DEBUG
                    key = f"{sector_name}:{col_name}"
                    with self._sector_warned_lock:
                        if key not in self._sector_warned:
                            logging.warning(f"[sector-percentile] insufficient peers for {col_name} in sector='{sector_name}' (<10 samples)")
                            self._sector_warned.add(key)
                        else:
                            logging.debug(f"[sector-percentile] insufficient peers for {col_name} in sector='{sector_name}' (<10 samples)")
                    logging.debug(f"Sector percentile skipped (insufficient peers<10) col={col} sector={sector_name}")
                    return None
                # guard: if all values are identical, avoid 0/0 weirdness later
                if np.all(colv == colv[0]):
                    # 모든 피어 동일값: 백분위 중립 0.5로 처리 (저/고 선호 지표 모두 중립)
                    return 0.5
                return float((colv < x).mean())
            
            per_p = pct_rank(per, 0)   # 낮을수록 좋음 → score = 1 - per_p
            pbr_p = pct_rank(pbr, 1)   # 낮을수록 좋음 → score = 1 - pbr_p
            roe_p = pct_rank(roe, 2)   # 높을수록 좋음 → score = roe_p
            
            # 기본 점수 계산 (존재하는 지표만 가중합)
            scores = []
            if per_p is not None:
                scores.append(1 - per_p)  # 낮을수록 좋음
            if pbr_p is not None:
                scores.append(1 - pbr_p)  # 낮을수록 좋음
            if roe_p is not None:
                scores.append(roe_p)      # 높을수록 좋음
            
            if not scores:
                # 모든 지표가 결측인 경우 중립 점수
                base_score = 50.0
                notes.append('all_metrics_skipped')
                # ✅ 메트릭 이중 집계 방지: 컬럼별로 이미 기록했으므로 여기서는 제외
            else:
                base_score = sum(scores) / len(scores) * 100.0
            
            # 리더 보너스(축소 후) 적용 (억원 단위로 정규화)
            market_cap_ek = normalize_market_cap_ekwon(market_cap)
            leader_bonus = self._calculate_leader_bonus(symbol, sector_name, market_cap_ek or 0.0, 
                                                       price_data, financial_data)
            
            # 섹터 표본 부족 시 리더 보너스 캡 적용 (점수 부풀림 방지)
            if not scores:
                # 모든 지표가 제외된 경우 leader_bonus를 0으로 고정 (과보정 방지)
                leader_bonus = 0.0
                logging.debug(f"[sector] All metrics excluded, leader_bonus set to 0.0 to prevent over-correction")
            
            # 섹터 총 표본 수에 따른 연속 감쇠 (과잉 보정 방지)
            sector_sample_count = len(vals) if 'vals' in locals() else 0
            if sector_sample_count < 30:
                # 표본 크기에 따른 연속 감쇠 (0.5~1.0 사이)
                factor = max(0.5, sector_sample_count / 30.0)
                leader_bonus *= factor
                logging.debug(f"[sector] Sample size ({sector_sample_count}), leader bonus factor: {factor:.2f}")
            
            total_score = min(100, max(0, base_score + leader_bonus))
            
            # 등급 결정
            grade = "A+" if total_score>=80 else "A" if total_score>=70 else "B+" if total_score>=60 else "B" if total_score>=50 else "C" if total_score>=40 else "D"
            
            # 대장주 여부 확인
            is_leader = self._is_sector_leader(symbol, sector_name)
            
            # 개별 지표 점수 계산 (None 가드)
            per_score = (100*(1-per_p)) if per_p is not None else None
            pbr_score = (100*(1-pbr_p)) if pbr_p is not None else None
            roe_score = (100*roe_p) if roe_p is not None else None
            
            return {
                'total_score': float(total_score),
                'base_score': float(base_score),
                'leader_bonus': float(leader_bonus),
                'is_leader': is_leader,
                'grade': grade,
                'description': '섹터 백분위 기반 점수',
                'per_score': per_score,
                'pbr_score': pbr_score,
                'roe_score': roe_score,
                'sector_info': sector_info,
                'notes': list(set(notes)) if notes else []
            }
            
        except Exception as e:
            log_error("업종별 밸류에이션 평가", symbol, e)
            return {
                'total_score': 50.0, 'base_score': 50.0, 'leader_bonus': 0.0,
                'is_leader': False, 'grade': 'C', 'description': '평가 불가',
                'per_score': 50.0, 'pbr_score': 50.0, 'roe_score': 50.0,
                'sector_info': {'description': '기타'}
            }
        finally:
            # 섹터 평가 소요 시간 기록
            duration = _monotonic() - start_time
            if self.metrics:
                self.metrics.record_sector_evaluation(duration)
    
    def _calculate_metric_score(self, value: float, min_val: float, max_val: float, reverse: bool = False) -> Optional[float]:
        """지표별 점수 계산 (PER/PBR/ROE 등 선형 매핑 헬퍼)"""
        # ✅ _calculate_metric_score 가드 강화: NaN 및 무한값 처리
        if value is None or not math.isfinite(value) or value <= 0:
            return None  # 상위에서 half-weight+50점으로 처리
        
        if max_val <= min_val:
            return 50.0  # 안전한 중립값 반환
        
        # 정규화 (0-100점)
        if reverse:
            # 낮을수록 좋은 지표 (PER, PBR)
            if value <= min_val:
                return 100
            elif value >= max_val:
                return 0
            else:
                return 100 - ((value - min_val) / (max_val - min_val)) * 100
        else:
            # 높을수록 좋은 지표 (ROE)
            if value >= max_val:
                return 100
            elif value <= min_val:
                return 0
            else:
                return ((value - min_val) / (max_val - min_val)) * 100
    
    def _get_grade(self, score: float) -> str:
        """점수를 등급으로 변환"""
        thresholds = self.config.grade_thresholds
        
        if score >= thresholds.get('A_plus', 80):
            return 'A+'
        elif score >= thresholds.get('A', 70):
            return 'A'
        elif score >= thresholds.get('B_plus', 60):
            return 'B+'
        elif score >= thresholds.get('B', 50):
            return 'B'
        elif score >= thresholds.get('C_plus', 40):
            return 'C+'
        elif score >= thresholds.get('C', 30):
            return 'C'
        elif score >= thresholds.get('D_plus', 20):
            return 'D+'
        elif score >= thresholds.get('D', 10):
            return 'D'
        else:
            return 'F'
    
    def _resolve_price_and_position(self, stock_dict):
        """가격·52주 정보 계산 경로 통합 헬퍼"""
        def _pick_price(d):
            if not d:
                return {}
            # dict이면 그대로, 객체이면 price_data 우선 접근
            if isinstance(d, dict):
                return d.get('price_data', d) or {}
            return getattr(d, 'price_data', {}) or {}
        
        # 1) enhanced(price_data) -> 2) basic(price_data) -> 3) (필요 시) 실시간/엑셀
        p = _pick_price(stock_dict.get('enhanced_result') or {}) \
            or _pick_price(stock_dict.get('basic_result') or {})  # legacy
        current = p.get('current_price')
        w52h, w52l = p.get('w52_high'), p.get('w52_low')
        
        # 현재가가 없으면 (옵션 허용 시) 중앙화된 프로바이더 사용
        if current is None and self.include_realtime:
            try:
                # prefer centralized provider (uses TTL cache + retries)
                p2 = self.data_provider.get_price_data(stock_dict.get('symbol'))
                current = p2.get('current_price') or current
                w52h = w52h or p2.get('w52_high')
                w52l = w52l or p2.get('w52_low')
            except Exception:
                pass
        
        # 52주 고가/저가가 없으면 (옵션 허용 시) 실시간 조회 (KIS + 재시도 + 레이트리미터)
        if (w52h is None or w52l is None) and self.include_realtime:
            try:
                symbol = stock_dict.get('symbol')
                if symbol:
                    self.rate_limiter.acquire()
                    cb_final = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
                    cb_attempt = (lambda et=None: self.metrics.record_api_attempt_error(et)) if self.metrics else None
                    price_info = _with_retries(
                        lambda: self.provider.get_stock_price_info(symbol),
                        metrics_attempt=cb_attempt,
                        metrics_final=cb_final
                    )
                    if price_info:
                        w52h = price_info.get('w52_high') or w52h
                        w52l = price_info.get('w52_low') or w52l
            except Exception as e:
                if self.metrics:
                    self.metrics.record_api_call(False, ErrorType.PRICE_DATA)
                logging.debug(f"52주 고가/저가 조회 실패 {stock_dict.get('symbol')}: {e}")
        
        # 여전히 52주 정보가 없으면 KOSPI 파일에서 시도
        if (w52h is None or w52l is None) and self.kospi_data is not None and not self.kospi_data.empty:
            try:
                code = stock_dict.get('symbol')
                row = self.kospi_data[self.kospi_data['단축코드'] == str(code)]
                if not row.empty:
                    # KOSPI 파일에서 52주 정보가 있다면 사용
                    if '52주최고가' in row.columns:
                        w52h = row.iloc[0].get('52주최고가') or w52h
                    if '52주최저가' in row.columns:
                        w52l = row.iloc[0].get('52주최저가') or w52l
            except Exception as e:
                logging.debug(f"KOSPI 파일 52주 정보 조회 실패 {stock_dict.get('symbol')}: {e}")
        
        # 위치 계산은 단일 진입점 함수로 통일
        position = self._calculate_price_position({'current_price': current, 'w52_high': w52h, 'w52_low': w52l})
        return current, position
    
    def _position_label(self, pos: Optional[float], is_outside_band: bool = False) -> str:
        """52주 위치에 따른 라벨을 반환합니다."""
        # ✅ 가드 3: NaN/비정상 값 안전 처리
        try:
            if pos is None:
                return "N/A"
            v = float(pos)
            if not math.isfinite(v):
                return "N/A"
            pos = max(0.0, min(100.0, v))
        except Exception:
            return "N/A"
        base_text = fmt(pos, '%')
        warning = " ⚠️ 밴드밖" if is_outside_band else ""
        
        if pos >= 95:
            return f"{base_text} 🔴 과열/추세{warning}"
        if pos >= 85:
            return f"{base_text} 🟡 상단{warning}"
        if pos <= 30:
            return f"{base_text} 🟢 저가구간(할인){warning}"
        return f"{base_text} 중립{warning}"
    
    def _classify_bucket(self, pos: Optional[float]) -> str:
        """52주 위치를 기반으로 바스켓을 분류합니다."""
        if pos is None:
            return "밸류/리스크관리"
        return "모멘텀/브레이크아웃" if pos >= 85 else "밸류/리스크관리"
    
    def _get_position_sizing(self, pos: Optional[float], bucket_type: str) -> float:
        """포지션 사이징을 계산합니다."""
        if pos is None:
            return 1.0
        
        if bucket_type == "밸류/리스크관리":
            if pos <= 30:  # 딥밸류
                return 1.2
            elif pos <= 70:  # 중립
                return 1.0
            else:
                return 0.8
        else:  # 모멘텀/브레이크아웃
            if pos >= 95:
                return 0.5
            else:
                return 0.7
    
    def _get_risk_reward_ratio(self, pos: Optional[float], bucket_type: str) -> str:
        """손익비 기준을 반환합니다."""
        if bucket_type == "모멘텀/브레이크아웃" and pos is not None:
            if pos >= 95:
                return "손절7% 목표1.8R"
            elif pos >= 85:
                return "손절8% 목표1.8R"
            else:
                return "손절8% 목표1.8R"
        else:
            return "N/A"
    
    def _extract_sector_valuation_text(self, stock: dict) -> str:
        """dict → AnalysisResult(enhanced_result) → sector_analysis에서 섹터 밸류 점수를 안전하게 추출합니다."""
        try:
            # dict → AnalysisResult(enhanced_result) → sector_analysis
            ar = stock.get("enhanced_result")
            raw = {}
            if isinstance(ar, AnalysisResult):
                raw = ar.sector_analysis or {}
            if not raw:
                raw = stock.get("sector_analysis", {})
            norm = self._normalize_sector_analysis(raw)
            if norm['grade'] == 'N/A' or norm['total_score'] is None:
                return "N/A"
            return f"{norm['grade']}({norm['total_score']:.1f})"
        except Exception:
            return "N/A"

    def _get_sector_valuation_score(self, stock: Dict[str, Any]) -> str:
        """섹터 상대 밸류 점수를 반환합니다."""
        try:
            norm = self._normalize_sector_analysis(stock.get('sector_analysis', {}))
            if norm['total_score'] is None:
                return "N/A"
            return f"{norm['grade']}({norm['total_score']:.1f})"
        except Exception as e:
            logging.debug(f"섹터 밸류 점수 계산 실패 {stock.get('symbol')}: {e}")
            return "N/A"
    
    def _get_basket_type(self, stock: Dict[str, Any]) -> str:
        """종목의 52주 위치를 기반으로 바스켓 타입을 반환합니다."""
        try:
            # 원본 데이터만 사용 (추가 API 호출 금지)
            price_position = stock.get("price_position")
            if price_position is None:
                current_price = stock.get("current_price")
                w52h = stock.get("w52_high")
                w52l = stock.get("w52_low")
                if current_price is not None and w52h is not None and w52l is not None:
                    price_position = self._calculate_price_position({
                        'current_price': current_price,
                        'w52_high': w52h,
                        'w52_low': w52l
                    })
            return self._classify_bucket(price_position)
        except Exception as e:
            logging.debug(f"바스켓 분류 실패 {stock.get('symbol')}: {e}")
            return "분류불가"
    
    # --- 섹터 분석 스키마 정규화 헬퍼 ---
    def _normalize_sector_analysis(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        다양한 형태(중첩/평면)의 섹터 분석 결과를 평면 스키마로 정규화.
        반환 스키마: {'grade': str, 'total_score': float}
        """
        if not node:
            return {'grade': 'N/A', 'total_score': None}
        # 중첩된 {'sector_analysis': {...}} 형태 수용
        if 'sector_analysis' in node and isinstance(node['sector_analysis'], dict):
            node = node['sector_analysis']
        # 키 변형 수용
        grade = node.get('grade') or node.get('sector_grade') or 'N/A'
        total = node.get('total_score')
        try:
            total = float(total) if total is not None else None
        except Exception:
            total = None
        return {'grade': grade, 'total_score': total}
    
    def _nan_if_nonpos(self, x, zero_is_nan: bool = True):
        """
        0 이상이고 유한한 값만 반환, 그 외는 NaN
        
        정책:
        - PER/PBR: 0 이상만 통과 (음수는 영업적자로 제외)
        - ROE: 0 이상만 통과 (음수는 손실로 제외, 0은 포함)
        - zero_is_nan=True: 0도 NaN으로 처리 (더 엄격한 필터링)
        """
        v = DataValidator.safe_float(x, float('nan'))
        if not (isinstance(v, (int, float, np.floating)) and math.isfinite(float(v))):
            return float('nan')
        if v < 0: 
            return float('nan')
        if zero_is_nan and v == 0: 
            return float('nan')
        return float(v)
    
    def _nan_if_negative(self, x):
        """
        음수만 NaN으로 처리, 0과 양수는 유지 (ROE=0 케이스 포함)
        """
        x = DataValidator.safe_float(x, float('nan'))
        if isinstance(x, (int, float, np.floating)) and math.isfinite(float(x)) and float(x) >= 0:
            return float(x)
        return float('nan')

    def _get_sector_peers_snapshot(self, sector_name: str) -> List[PeerTriple]:
        """
        주어진 섹터의 피어들에 대한 (PER, PBR, ROE) 스냅샷을 반환합니다.
        - 반환: [(per, pbr, roe), ...]  (모두 유효한 비음수가 있는 케이스만 채택)
        - 10분 TTL 캐시(_sector_cache) 적용
        """
        now = _monotonic()

        # 1) 캐시 조회
        with self._sector_cache_lock:
            hit = self._sector_cache.get(sector_name)
            if hit and now - hit[0] < self._sector_cache_ttl:
                return hit[1]

        # 2) KOSPI 없으면 빈 리스트
        if self.kospi_data is None or self.kospi_data.empty:
            with self._sector_cache_lock:
                self._sector_cache[sector_name] = (now, [])
            return []

        # 3) 섹터 컬럼 후보에서 동종군 추출
        sector_cols = ('업종', '지수업종대분류', '업종명', '섹터')
        df = self.kospi_data
        peers_df = None
        s_lower = str(sector_name).strip().lower()

        for col in sector_cols:
            if col in df.columns:
                tmp = df[df[col].astype(str).str.strip().str.lower() == s_lower]
                if not tmp.empty:
                    peers_df = tmp
                    break
        if peers_df is None or peers_df.empty:
            # 섹터명이 애매하면 부분매칭(contains)로 한 번 더 시도
            for col in sector_cols:
                if col in df.columns:
                    tmp = df[df[col].astype(str).str.strip().str.lower().str.contains(s_lower, na=False)]
                    if not tmp.empty:
                        peers_df = tmp
                        break

        if peers_df is None or peers_df.empty:
            with self._sector_cache_lock:
                self._sector_cache[sector_name] = (now, [])
            return []

        # 4) 동종군 코드 수집 (문자 6자리)
        codes = (
            peers_df.get('단축코드', pd.Series(dtype=str))
            .astype(str)
            .str.replace(r'\.0$', '', regex=True)
            .str.zfill(6)
            .tolist()
        )

        # 5) 표본 수 제한: base/full
        max_full = self.env_cache.get('max_sector_peers_full', 200)
        if len(codes) > max_full:
            # 랜덤 샘플링(섹터 평균을 왜곡하지 않도록 넓게 고르게)
            random.shuffle(codes)
            codes = codes[:max_full]

        # 6) 동시 수집
        results: List[PeerTriple] = []
        max_workers = safe_env_int("MAX_WORKERS", 0, min_val=None) or min(32, max(4, os.cpu_count() or 8))

        def fetch_tuple(code: str) -> Optional[PeerTriple]:
            try:
                # 캐시된 프로바이더 사용: 내부 TTL + 재시도 처리
                pdict = self.data_provider.get_price_data(code) or {}
                fdict = self.data_provider.get_financial_data(code) or {}

                per = self._nan_if_nonpos(pdict.get('per'), zero_is_nan=True)
                pbr = self._nan_if_nonpos(pdict.get('pbr'), zero_is_nan=True)
                roe = self._nan_if_negative(fdict.get('roe'))  # ROE는 0 허용, 음수 제외

                if not (math.isfinite(per) and math.isfinite(pbr) and math.isfinite(roe)):
                    return None
                return (per, pbr, roe)
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for tup in ex.map(fetch_tuple, codes):
                if tup is not None:
                    results.append(tup)

        # 7) 결과 캐시 + LRU 축소
        with self._sector_cache_lock:
            self._sector_cache[sector_name] = (now, results)
            # LRU: 오래된 섹터 제거
            while len(self._sector_cache) > self.env_cache.get('max_sector_cache_entries', 64):
                try:
                    self._sector_cache.popitem(last=False)
                except Exception:
                    break

        return results
    
    def _analyze_stocks_parallel(self, stocks_data, max_workers: int = None) -> List[AnalysisResult]:
        """종목들을 병렬로 분석하는 공통 메서드 (API TPS 최적화)"""
        results = []
        if max_workers is None:
            # ✅ 워커 수 자동 추정 개선: TPS, 코어 수, 외부 분석 사용 여부 고려
            cpu_cores = os.cpu_count() or 1
            max_tps = safe_env_int("KIS_MAX_TPS", 8, 1)
            
            # ✅ MAX_WORKERS=0 의미 불일치 수정: 0이면 자동 추정
            env_mw_raw = os.getenv("MAX_WORKERS", "")
            env_mw = None
            try:
                env_mw = int(env_mw_raw)
            except Exception:
                env_mw = None

            auto_guess = (int(1.5 * max_tps) if self.include_external else int(2.0 * max_tps))
            # I/O 바운드 환경을 고려하여 코어*4까지 여유를 둠 (환경에 따라 튜닝 가능)
            auto_cap   = (cpu_cores * 3 if self.include_external else cpu_cores * 4)
            auto_val   = min(auto_guess, auto_cap)

            if env_mw is None or env_mw == 0:
                max_workers = max(1, auto_val)
            else:
                # 사용자가 강제 지정한 경우, 과도한 값은 캡
                max_workers = max(1, min(env_mw, auto_cap))
        
        # Guard against negative/zero workers
        max_workers = max(1, max_workers or 1)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 작업 제출
            futures = []
            for _, stock in stocks_data.iterrows():
                symbol = str(stock['단축코드'])
                name = stock['한글명']
                future = executor.submit(self.analyze_single_stock, symbol, name)
                futures.append((future, symbol, name))

            # 결과 수집 (as_completed 사용으로 완료된 작업부터 처리)
            future_map = {f: (symbol, name) for f, symbol, name in futures}
            for f in as_completed(future_map):
                symbol, name = future_map[f]
                try:
                    result = f.result()
                    if result.status == AnalysisStatus.SUCCESS:
                        results.append(result)
                    elif result.status == AnalysisStatus.SKIPPED_PREF:
                        logging.debug(f"우선주 제외: {name} ({symbol})")
                    else:
                        logging.debug(f"분석 실패: {name} ({symbol}) - {result.error}")
                except Exception as e:
                    log_error("종목 분석", f"{name}({symbol})", e, LogLevel.ERROR)
                    continue

        # 분석된 종목 수 기록
        if hasattr(self, "metrics") and self.metrics:
            self.metrics.record_stocks_analyzed(len(results))
        
        return results

    # -----------------------------
    # 실행 유틸/엔트리포인트 보강
    # -----------------------------
    def run_universe(self, limit: int = 100) -> List[AnalysisResult]:
        """
        KOSPI 마스터에서 우선주 제외 후 시총 상위 limit개를 병렬 분석.
        """
        if self.kospi_data is None or self.kospi_data.empty:
            logging.error("KOSPI 마스터 데이터가 없습니다. kospi_code.csv/xlsx를 확인하세요.")
            return []

        df = self.kospi_data.copy()

        # 우선주 제외
        if "한글명" in df.columns:
            df = df[~df["한글명"].astype(str).apply(DataValidator.is_preferred_stock)]

        # 시총 정렬 후 상위 limit
        if "시가총액" in df.columns:
            df = df.sort_values("시가총액", ascending=False)
        if limit and limit > 0:
            df = df.head(limit)

        results = self._analyze_stocks_parallel(df)
        
        # 투자 매력도(종합점수) 순으로 정렬
        results.sort(key=lambda x: x.enhanced_score, reverse=True)
        
        return results

    def export_json(self, results: List[AnalysisResult], path: str) -> None:
        """분석 결과를 JSON 파일로 저장"""
        payload = [self._result_to_dict(r) for r in results]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logging.info(f"JSON 저장 완료: {path}")

    def export_csv(self, results: List[AnalysisResult], path: str) -> None:
        """분석 결과를 CSV 파일로 저장 (주요 필드 중심)"""
        rows = []
        for r in results:
            d = self._result_to_dict(r)
            rows.append({
                "symbol": d.get("symbol"),
                "name": d.get("name"),
                "grade": d.get("enhanced_grade"),
                "score": d.get("enhanced_score"),
                "market_cap_억": d.get("market_cap"),
                "current_price": d.get("current_price"),
                "price_position": d.get("price_position"),
                "per": d.get("per"),
                "pbr": d.get("pbr"),
                "sector_valuation": d.get("sector_valuation"),
            })
        pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
        logging.info(f"CSV 저장 완료: {path}")
    
    def analyze_full_market_enhanced(self, max_stocks: int = 100, min_score: float = 20.0, 
                                   include_realtime: bool = True, include_external: bool = True,
                                   max_workers: Optional[int] = None) -> Dict[str, Any]:
        """
        향상된 전체 시장 분석을 수행합니다.
        
        시가총액 상위 종목들을 병렬로 분석하여 저평가 종목을 찾습니다.
        
        Note: include_realtime, include_external 파라미터는 메타데이터 표시용입니다.
              실제 로직은 인스턴스 플래그(self.include_realtime, self.include_external)를 사용합니다.
        
        Args:
            max_stocks (int): 최대 분석 종목 수 (기본값: 100)
            min_score (float): 최소 점수 필터 (기본값: 20.0)
            include_realtime (bool): 실시간 데이터 포함 여부 (기본값: True)
            include_external (bool): 외부 데이터 포함 여부 (기본값: True)
            
        Returns:
            Dict[str, Any]: 분석 결과 딕셔너리
                - metadata: 분석 메타데이터
                - top_recommendations: 상위 추천 종목 리스트
                - sector_analysis: 업종별 분석 결과
                - market_statistics: 시장 통계
                
        Note:
            병렬 처리를 사용하여 성능을 최적화합니다.
            CPU 코어 수에 맞춰 워커 수를 자동 조정합니다.
        """
        try:
            # ✅ 엔트리포인트에서 로그 초기화
            _setup_logging_if_needed()
            
            start_time = _monotonic()
            
            # KOSPI 데이터 확인
            if self.kospi_data is None or self.kospi_data.empty:
                raise ValueError("KOSPI 데이터를 로드할 수 없습니다.")
            
            # 시가총액 상위 종목 선별
            top_stocks = self.kospi_data.nlargest(max_stocks, '시가총액')
            
            # 병렬 처리로 성능 최적화
            results = self._analyze_stocks_parallel(top_stocks, max_workers=max_workers)
            
            # 결과 정렬 및 필터링
            filtered_results = [
                r for r in results 
                if r.enhanced_score >= min_score
            ]
            filtered_results.sort(key=lambda x: x.enhanced_score, reverse=True)
            
            # 메타데이터 생성
            analysis_time = _monotonic() - start_time
            metadata = {
                'analysis_version': '2.0_enhanced',
                'analysis_date': datetime.now().isoformat(),
                'analysis_time_seconds': analysis_time,
                'total_analyzed': len(results),
                'total_stocks_analyzed': len(results),
                'undervalued_count': len(filtered_results),
                'features_enabled': {
                    'realtime_data': self.include_realtime,
                    'external_data': self.include_external,
                    'enhanced_scoring': True
                }
            }
            
            return {
                'metadata': metadata,
                'top_recommendations': [self._result_to_dict(r) for r in filtered_results[:20]],
                'sector_analysis': self._analyze_sector_distribution_enhanced(results),
                'market_statistics': self._calculate_enhanced_market_statistics(results)
            }
            
        except Exception as e:
            log_error("전체 시장 분석", error=e, level="error")
            return {
                'metadata': {'error': str(e)},
                'top_recommendations': [],
                'sector_analysis': {},
                'market_statistics': {}
            }
        finally:
            try:
                summ = self.metrics.get_summary() if hasattr(self, "metrics") and self.metrics else {}
                # 타임스탬프를 포함한 파일명으로 겹침 방지
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                metrics_filename = f"metrics_summary_{timestamp}.json"
                with open(metrics_filename, "w", encoding="utf-8") as f:
                    json.dump(serialize_for_json(summ), f, ensure_ascii=False, indent=2)
                logging.info(f"메트릭 요약 저장: {metrics_filename}")
            except Exception as _e:
                logging.warning(f"메트릭 요약 저장 실패: {_e}")
    
    def analyze_top_market_cap_stocks_enhanced(self, count: int = 50, min_score: float = 20.0, 
                                             max_workers: Optional[int] = None) -> Dict[str, Any]:
        """
        시가총액 상위 종목 향상된 분석
        
        Note: 실제 로직은 인스턴스 플래그(self.include_realtime, self.include_external)를 사용합니다.
        """
        try:
            start_time = _monotonic()
            
            if self.kospi_data is None or self.kospi_data.empty:
                raise ValueError("KOSPI 데이터를 로드할 수 없습니다.")
            
            # 시가총액 상위 종목 선별
            top_stocks = self.kospi_data.nlargest(count, '시가총액')
            
            # 병렬 처리로 성능 최적화
            results = self._analyze_stocks_parallel(top_stocks, max_workers=max_workers)
            
            # 결과 필터링 및 정렬
            filtered_results = [
                r for r in results 
                if r.enhanced_score >= min_score
            ]
            filtered_results.sort(key=lambda x: x.enhanced_score, reverse=True)
            
            # 메타데이터 생성
            analysis_time = _monotonic() - start_time
            metadata = {
                'analysis_version': '2.0_enhanced',
                'analysis_date': datetime.now().isoformat(),
                'analysis_time_seconds': analysis_time,
                'total_analyzed': len(results),
                'total_stocks_analyzed': len(results),
                'undervalued_count': len(filtered_results),
                'features_enabled': {
                    'realtime_data': self.include_realtime,
                    'external_data': self.include_external,
                    'enhanced_scoring': True
                }
            }
            
            return {
                'metadata': metadata,
                'top_recommendations': [self._result_to_dict(r) for r in filtered_results[:15]],
                'sector_analysis': self._analyze_sector_distribution_enhanced(results),
                'market_statistics': self._calculate_enhanced_market_statistics(results)
            }
            
        except Exception as e:
            log_error("시가총액 상위 종목 분석", error=e, level="error")
            return {
                'metadata': {'error': str(e)},
                'top_recommendations': [],
                'sector_analysis': {},
                'market_statistics': {}
            }
    
    def _analyze_sector_distribution_enhanced(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        """향상된 업종별 분포 분석 (중복 섹터조회 제거)"""
        try:
            sector_distribution = {}
            
            # 심볼→섹터 매핑을 한 번만 구하여 중복 조회 제거
            sector_map = {}
            for result in results:
                sym = result.symbol
                if sym not in sector_map:
                    sector_map[sym] = self._get_sector_characteristics(sym).get('name', '기타')
                sector = sector_map[sym]
                
                if sector not in sector_distribution:
                    sector_distribution[sector] = {
                        'count': 0,
                        'total_score': 0,
                        'avg_score': 0,
                        'recommendations': {'BUY': 0, 'HOLD': 0, 'SELL': 0}
                    }
                
                sector_distribution[sector]['count'] += 1
                sector_distribution[sector]['total_score'] += result.enhanced_score
                
                # 투자 추천 분포 (안전 접근)
                recommendation = DataValidator._getattr_or_get(result, 'investment_recommendation', 'HOLD')
                if recommendation in sector_distribution[sector]['recommendations']:
                    sector_distribution[sector]['recommendations'][recommendation] += 1
            
            # 평균 점수 계산
            for sector in sector_distribution:
                if sector_distribution[sector]['count'] > 0:
                    sector_distribution[sector]['avg_score'] = (
                        sector_distribution[sector]['total_score'] / sector_distribution[sector]['count']
                    )
            
            return sector_distribution
            
        except Exception as e:
            log_error("업종별 분포 분석", error=e, level="error")
            return {}
    
    def _calculate_enhanced_market_statistics(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        """향상된 시장 통계 계산"""
        try:
            if not results:
                return {}
            
            scores = [r.enhanced_score for r in results if r.enhanced_score > 0]
            market_caps = [r.market_cap for r in results if r.market_cap > 0]
            
            if not scores:
                return {}
            
            return {
                'total_analyzed': len(results),
                'avg_score': sum(scores) / len(scores),
                'max_score': max(scores),
                'min_score': min(scores),
                'score_distribution': {
                    'A+': len([s for s in scores if s >= 80]),
                    'A': len([s for s in scores if 70 <= s < 80]),
                    'B+': len([s for s in scores if 60 <= s < 70]),
                    'B': len([s for s in scores if 50 <= s < 60]),
                    'C': len([s for s in scores if 40 <= s < 50]),
                    'D': len([s for s in scores if 20 <= s < 40]),
                    'F': len([s for s in scores if s < 20])
                },
                'market_cap_stats': {
                    'total_market_cap': sum(market_caps),
                    'avg_market_cap': sum(market_caps) / len(market_caps) if market_caps else 0,
                    'max_market_cap': max(market_caps) if market_caps else 0,
                    'min_market_cap': min(market_caps) if market_caps else 0
                }
            }
            
        except Exception as e:
            log_error("시장 통계 계산", error=e, level="error")
            return {}
    
    def _display_enhanced_results_table(self, results: Dict[str, Any]):
        """향상된 분석 결과를 표 형태로 출력"""
        try:
            metadata = results.get('metadata', {})
            print(f"\n🚀 향상된 통합 분석 결과 v{metadata.get('analysis_version', '2.0_enhanced')}")
            print(f"📅 분석 일시: {metadata.get('analysis_date', 'Unknown')}")
            print(f"⏱️ 분석 시간: {metadata.get('analysis_time_seconds', 0):.1f}초")
            total = metadata.get('total_analyzed', metadata.get('total_stocks_analyzed', 0))
            print(f"📊 총 분석 종목: {total}개")
            print(f"🎯 추천 종목: {metadata.get('undervalued_count', 0)}개")
            
            # 상위 추천 종목 표
            top_recommendations = results.get('top_recommendations', [])
            if top_recommendations:
                print("\n🏆 향상된 종목 추천 결과")
                print("=" * 100)
                print(f"{'순위':<4} {'종목코드':<8} {'종목명':<15} {'현재가':<10} {'52주위치':<8} {'종합점수':<8} {'등급':<6} {'시가총액':<12}")
                print("-" * 100)
                
                for i, stock in enumerate(top_recommendations[:10], 1):
                    # stock이 딕셔너리인지 객체인지 확인
                    if isinstance(stock, dict):
                        symbol = stock.get('symbol', 'N/A')
                        name = stock.get('name', 'N/A')
                        enhanced_score = stock.get('enhanced_score', 0)
                        market_cap = stock.get('market_cap', 0)
                        current_price = stock.get('current_price', 0)
                        grade = stock.get('enhanced_grade', 'F')
                        w52_high = stock.get('w52_high', 0)
                        w52_low = stock.get('w52_low', 0)
                    else:
                        symbol = getattr(stock, 'symbol', 'N/A')
                        name = getattr(stock, 'name', 'N/A')
                        enhanced_score = getattr(stock, 'enhanced_score', 0)
                        market_cap = getattr(stock, 'market_cap', 0)
                        current_price = getattr(stock, 'current_price', 0)
                        grade = getattr(stock, 'enhanced_grade', 'F')
                        w52_high = getattr(stock, 'w52_high', 0)
                        w52_low = getattr(stock, 'w52_low', 0)
                    
                    # 현재가 표시
                    current_price_display = f"{current_price:,.0f}원" if current_price is not None else "N/A"
                    
                    # 52주 위치 계산 및 표시
                    if current_price and w52_high and w52_low and w52_high > w52_low:
                        position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
                        position_display = f"{position:.0f}%"
                    else:
                        position_display = "N/A"
                    
                    # 시가총액 표시
                    market_cap_display = f"{market_cap:,.0f}억" if market_cap else "N/A"
                    
                    # 종목명 길이 제한
                    name_display = name[:12] + ('...' if len(name) > 12 else '')
                    
                    print(f"{i:<4} {symbol:<8} {name_display:<15} {current_price_display:<10} {position_display:<8} {enhanced_score:<8.1f} {grade:<6} {market_cap_display:<12}")
                
                print("=" * 100)
            
            # 업종별 분석 결과
            sector_analysis = results.get('sector_analysis', {})
            if sector_analysis:
                print(f"\n📊 업종별 분석 결과")
                for sector, data in sector_analysis.items():
                    print(f"  {sector}: {data['count']}개 종목, 평균점수 {data['avg_score']:.1f}")
            
            # 시장 통계
            market_stats = results.get('market_statistics', {})
            if market_stats:
                print(f"\n📈 시장 통계")
                print(f"  평균 점수: {market_stats.get('avg_score', 0):.1f}")
                print(f"  최고 점수: {market_stats.get('max_score', 0):.1f}")
                print(f"  최저 점수: {market_stats.get('min_score', 0):.1f}")
                
                score_dist = market_stats.get('score_distribution', {})
                if score_dist:
                    print(f"  점수 분포: A+({score_dist.get('A+', 0)}) A({score_dist.get('A', 0)}) B+({score_dist.get('B+', 0)}) B({score_dist.get('B', 0)})")
            
        except Exception as e:
            log_error("결과 테이블 출력", error=e, level="error")
            pass

# =============================================================================
# 6. CLI 인터페이스 (기존과 동일)
# =============================================================================

# Typer CLI 앱 생성
app = typer.Typer(help="Enhanced Integrated Analyzer")

@app.command()
def test_enhanced_analysis(
    count: int = typer.Option(15, help="분석할 종목 수"),
    min_score: float = typer.Option(20.0, help="최소 점수"),
    max_workers: int = typer.Option(safe_env_int("MAX_WORKERS", 0, min_val=None), help="워커 수(0=자동)"),
    realtime: bool = typer.Option(True, help="실시간 데이터 포함"),
    external: bool = typer.Option(True, help="외부 분석 포함(의견/추정)"),
):
    """
    간단 실행: 시가총액 상위 종목을 분석하여 표 출력
    """
    # ✅ 로깅 부트스트랩 호출
    _setup_logging_if_needed()
    
    analyzer = EnhancedIntegratedAnalyzer(include_realtime=realtime, include_external=external)
    
    # ✅ 전역 인스턴스 설정 (메트릭 덤프용)
    global _global_analyzer_instance
    _global_analyzer_instance = analyzer
    
    results = analyzer.analyze_top_market_cap_stocks_enhanced(
        count=count,
        min_score=min_score,
        max_workers=(None if max_workers == 0 else max_workers),
    )
    analyzer._display_enhanced_results_table(results)

@app.command()
def full_market(
    max_stocks: int = typer.Option(100, help="시총 상위 N개 분석"),
    min_score: float = typer.Option(20.0, help="최소 점수"),
    max_workers: int = typer.Option(safe_env_int("MAX_WORKERS", 0, min_val=None), help="워커 수(0=자동)"),
    realtime: bool = typer.Option(True, help="실시간 데이터 포함"),
    external: bool = typer.Option(True, help="외부 분석 포함(의견/추정)"),
):
    """
    전체 시장(시총 상위 max_stocks) 분석 실행
    """
    # ✅ 로깅 부트스트랩 호출
    _setup_logging_if_needed()
    
    analyzer = EnhancedIntegratedAnalyzer(include_realtime=realtime, include_external=external)
    
    # ✅ 전역 인스턴스 설정 (메트릭 덤프용)
    global _global_analyzer_instance
    _global_analyzer_instance = analyzer
    
    results = analyzer.analyze_full_market_enhanced(
        max_stocks=max_stocks,
        min_score=min_score,
        include_realtime=realtime,
        include_external=external,
        max_workers=(None if max_workers == 0 else max_workers),
    )
    analyzer._display_enhanced_results_table(results)

@app.command()
def analyze(
    symbol: str,
    name: str = "",
    days_back: int = 30,
    realtime: bool = True,
    external: bool = True,
):
    """단일 종목 분석"""
    # ✅ 로깅 부트스트랩 호출
    _setup_logging_if_needed()
    
    ai = EnhancedIntegratedAnalyzer(include_realtime=realtime, include_external=external)
    
    # ✅ 전역 인스턴스 설정 (메트릭 덤프용)
    global _global_analyzer_instance
    _global_analyzer_instance = ai
    
    try:
        res = ai.analyze_single_stock(symbol, name, days_back)
        # JSON 출력 (CLI 친화적)
        import json
        result_dict = ai._result_to_dict(res)
        typer.echo(json.dumps(result_dict, ensure_ascii=False, indent=2))
    except Exception as e:
        typer.echo(f"❌ 분석 실패: {e}", err=True)

@app.command()
def scan(
    max_stocks: int = 100,
    min_score: float = 20.0,
    realtime: bool = True,
    external: bool = True,
):
    """간단한 전체 시장 스캔"""
    a = EnhancedIntegratedAnalyzer(include_realtime=realtime, include_external=external)
    
    # ✅ 전역 인스턴스 설정 (메트릭 덤프용)
    global _global_analyzer_instance
    _global_analyzer_instance = a
    
    res = a.analyze_full_market_enhanced(max_stocks=max_stocks, min_score=min_score)
    a._display_enhanced_results_table(res)

@app.command(help="KOSPI 시총 상위 N개 종목을 분석하고 결과 파일로 저장합니다.")
def run(
    limit: int = typer.Option(50, help="분석할 시총 상위 종목 수"),
    config: str = typer.Option("config.yaml", help="설정 파일 경로"),
    include_realtime: bool = typer.Option(True, help="실시간/추가 가격 정보 포함"),
    include_external: bool = typer.Option(True, help="외부(의견/추정) 분석 포함"),
    out_json: str = typer.Option("results.json", help="JSON 결과 파일"),
    out_csv: str = typer.Option("results.csv", help="CSV 결과 파일"),
    log_level: str = typer.Option(os.getenv("LOG_LEVEL", "INFO"), help="로그 레벨 (DEBUG/INFO/WARN/ERROR)"),
):
    """KOSPI 시총 상위 N개 종목을 분석하고 결과 파일로 저장합니다."""
    _setup_logging_if_needed()
    logging.getLogger().setLevel(getattr(logging, log_level.upper(), logging.INFO))

    analyzer = EnhancedIntegratedAnalyzer(
        include_realtime=include_realtime,
        include_external=include_external,
    )

    # ✅ 전역 인스턴스 설정 (메트릭 덤프용)
    global _global_analyzer_instance
    _global_analyzer_instance = analyzer

    start = _monotonic()
    results = analyzer.run_universe(limit=limit)
    elapsed = _monotonic() - start

    # 저장
    analyzer.export_json(results, out_json)
    analyzer.export_csv(results, out_csv)

    # 결과 표 출력 (Rich 테이블)
    if results:
        console = Console()
        console.print(f"\n🚀 [bold blue]종목 분석 결과 (상위 {len(results)}개)[/bold blue]")
        
        # Rich 테이블 생성
        table = Table(title="🏆 종목 분석 결과", box=ROUNDED)
        
        # 컬럼 추가
        table.add_column("순위", style="cyan", width=4, justify="center")
        table.add_column("종목코드", style="magenta", width=8)
        table.add_column("종목명", style="green", width=15)
        table.add_column("현재가", style="white", width=12)
        table.add_column("52주위치", style="bright_magenta", width=8, justify="center")
        table.add_column("종합점수", style="yellow", width=8, justify="center")
        table.add_column("등급", style="red", width=6, justify="center")
        table.add_column("시가총액", style="blue", width=12)
        
        for i, result in enumerate(results[:10], 1):
            # 현재가 표시
            current_price_display = f"{result.current_price:,.0f}원" if result.current_price else "N/A"
            
            # 52주 위치 표시 (색상 코딩)
            if result.price_position is not None:
                if result.price_position >= 90:
                    position_display = f"[red]{result.price_position:.0f}%[/red]"
                elif result.price_position >= 70:
                    position_display = f"[yellow]{result.price_position:.0f}%[/yellow]"
                elif result.price_position <= 30:
                    position_display = f"[green]{result.price_position:.0f}%[/green]"
                else:
                    position_display = f"{result.price_position:.0f}%"
            else:
                position_display = "N/A"
            
            # 시가총액 표시
            market_cap_display = f"{result.market_cap:,.0f}억" if result.market_cap else "N/A"
            
            # 종목명 길이 제한
            name_display = result.name[:12] + ('...' if len(result.name) > 12 else '')
            
            # 등급 색상 코딩
            if result.enhanced_grade in ['A+', 'A']:
                grade_display = f"[green]{result.enhanced_grade}[/green]"
            elif result.enhanced_grade in ['B+', 'B']:
                grade_display = f"[yellow]{result.enhanced_grade}[/yellow]"
            else:
                grade_display = f"[red]{result.enhanced_grade}[/red]"
            
            # 행 추가
            table.add_row(
                str(i),
                result.symbol,
                name_display,
                current_price_display,
                position_display,
                f"{result.enhanced_score:.1f}",
                grade_display,
                market_cap_display
            )
        
        console.print(table)
        
        # 요약 통계
        if len(results) > 1:
            avg_score = sum(r.enhanced_score for r in results) / len(results)
            max_score = max(r.enhanced_score for r in results)
            min_score = min(r.enhanced_score for r in results)
            console.print(f"\n📈 [bold green]분석 요약:[/bold green]")
            console.print(f"• 총 분석 종목: {len(results)}개")
            console.print(f"• 평균 점수: {avg_score:.1f}점")
            console.print(f"• 최고 점수: {max_score:.1f}점")
            console.print(f"• 최저 점수: {min_score:.1f}점")

    # 메트릭 요약 출력
    summary = analyzer.metrics.get_summary()
    logging.info(f"분석 완료: {len(results)}개, {elapsed:.2f}s")
    logging.info(f"API 성공률: {summary['api_success_rate']:.1f}% / 가격 캐시 히트: {summary['cache_hit_rates']['price']:.1f}%")

# =============================================================================
# Graceful Shutdown & Metrics Dump
# =============================================================================

_global_analyzer_instance = None

def _dump_metrics_on_exit():
    """프로그램 종료 시 메트릭 덤프 (간소화)"""
    try:
        if _global_analyzer_instance and getattr(_global_analyzer_instance, "metrics", None):
            m = _global_analyzer_instance.metrics.get_summary()
            logging.info(
                "[METRICS] api_succ_rate=%.1f%% price_hit=%.1f%% fin_hit=%.1f%% sector_hit=%.1f%% "
                "avg_analysis=%.2fs avg_sector=%.2fs errors=%s",
                m.get('api_success_rate', 0.0),
                m['cache_hit_rates'].get('price', 0.0),
                m['cache_hit_rates'].get('financial', 0.0),
                m['cache_hit_rates'].get('sector', 0.0),
                m.get('avg_analysis_duration', 0.0),
                m.get('avg_sector_evaluation', 0.0),
                m.get('errors_by_type', {})
            )
    except Exception:
        pass

# 전역 메트릭 덤프 훅 등록
atexit.register(_dump_metrics_on_exit)

def _install_signals():
    """깔끔한 종료(메트릭 집계 후)를 위한 시그널 핸들러 설치"""
    def _graceful_exit(signum, frame):
        logging.info("신호 수신: 종료합니다.")
        raise SystemExit(0)
    try:
        signal.signal(signal.SIGINT, _graceful_exit)
        signal.signal(signal.SIGTERM, _graceful_exit)
    except Exception:
        pass

def show_help():
    """도움말 표시"""
    print("""
🚀 향상된 통합 분석 시스템 v2.0

사용법:
  python enhanced_integrated_analyzer_refactored.py [옵션]

옵션:
  --help, -h           이 도움말 표시
  --count N            분석할 종목 수 (기본값: 10)
  --min-score N        최소 점수 필터 (기본값: 15.0)
  --max-workers N      워커 수 (기본값: 0=자동)
  --no-external        외부 데이터(투자의견/추정실적) 비활성화
  --no-realtime        실시간 데이터(가격/52주) 비활성화
  --dump PATH          결과를 JSON 파일로 저장

예시:
  python enhanced_integrated_analyzer_refactored.py --count 20 --min-score 25
  python enhanced_integrated_analyzer_refactored.py --no-external --dump results.json
  python enhanced_integrated_analyzer_refactored.py --count 5 --min-score 30 --max-workers 4
    """)

def parse_args():
    """명령행 인수 파싱"""
    import sys
    
    # 기본값
    count = 10
    min_score = 15.0
    max_workers = 0
    include_external = True
    include_realtime = True
    dump_path = None
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg in ['--help', '-h', 'help']:
            show_help()
            sys.exit(0)
        elif arg == '--count' and i + 1 < len(sys.argv):
            count = int(sys.argv[i + 1])
            i += 2
        elif arg == '--min-score' and i + 1 < len(sys.argv):
            min_score = float(sys.argv[i + 1])
            i += 2
        elif arg == '--max-workers' and i + 1 < len(sys.argv):
            max_workers = int(sys.argv[i + 1])
            i += 2
        elif arg == '--no-external':
            include_external = False
            i += 1
        elif arg == '--no-realtime':
            include_realtime = False
            i += 1
        elif arg == '--dump' and i + 1 < len(sys.argv):
            dump_path = sys.argv[i + 1]
            i += 2
        else:
            print(f"❌ 알 수 없는 옵션: {arg}")
            print("💡 --help를 사용하여 사용법을 확인하세요.")
            sys.exit(1)
    
    return {
        'count': count,
        'min_score': min_score,
        'max_workers': max_workers if max_workers > 0 else None,
        'include_external': include_external,
        'include_realtime': include_realtime,
        'dump_path': dump_path
    }

if __name__ == "__main__":
    # ✅ 엔트리포인트에서 로깅 부트스트랩 호출
    _setup_logging_if_needed()
    try:
        app()
    except KeyboardInterrupt:
        logging.warning("사용자 중단(CTRL+C)")
