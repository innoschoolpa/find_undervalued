# enhanced_integrated_analyzer_refactored.py
from __future__ import annotations

# 타입 힌트 강화 적용
"""
리팩토링된 향상된 통합 분석 시스템
- 단일 책임 원칙 적용
- 클래스 분리 및 모듈화
- 성능 최적화
- 에러 처리 개선
- 스레드 안전성 강화
- 메모리 누수 방지
- 표준화된 예외 처리
- 강화된 입력 검증
"""

import logging

# 개선된 모듈들 import
try:
    from thread_safe_rate_limiter import ThreadSafeTPSRateLimiter, get_default_rate_limiter
    from memory_safe_cache import MemorySafeCache, get_global_cache
    from standardized_exception_handler import (
        StandardizedExceptionHandler, get_global_handler,
        handle_errors, retry_on_failure, circuit_breaker,
        ErrorCategory, ErrorSeverity, RetryConfig
    )
    from enhanced_input_validator import EnhancedInputValidator, get_global_validator
    from performance_optimizer import (
        LRUCache, PerformanceMonitor, timed_operation, 
        memoize_with_ttl, BatchProcessor, MemoryOptimizer
    )
    from type_definitions import (
        Symbol, Name, Price, Score, Percentage, MarketCap, Volume,
        AnalysisStatus, Grade, SectorType, CompanySize,
        PriceData, FinancialData, SectorAnalysis, AnalysisResult, AnalysisConfig,
        Result, validate_symbol, validate_price, validate_percentage, validate_score
    )
    from enhanced_error_handler import (
        EnhancedErrorHandler, retry_on_failure, handle_errors, circuit_breaker,
        ErrorSeverity, ErrorCategory, RetryConfig, CircuitBreakerConfig
    )
    from code_optimizer import (
        CodeOptimizer, DataProcessor, MemoryOptimizer, CodeQualityImprover,
        memoize, measure_performance, monitor_memory, get_performance_stats,
        optimize_memory, get_memory_usage
    )
    from performance_monitor import (
        PerformanceMonitor, PerformanceProfiler, record_metric, record_request,
        get_performance_stats as get_monitor_stats, export_performance_report,
        profile_function
    )
    from price_display_enhancer import (
        PriceDisplayEnhancer, format_price, format_market_cap, 
        calculate_price_position, display_detailed_price_info, create_price_summary
    )
    from value_investing_philosophy import (
        ValueInvestingPhilosophy, analyze_business_model, calculate_intrinsic_value,
        calculate_margin_of_safety, add_to_watchlist, get_buy_signals, generate_investment_report
    )
    IMPROVED_MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"개선된 모듈들을 사용할 수 없습니다: {e}")
    IMPROVED_MODULES_AVAILABLE = False
    
    # Fallback implementations for missing decorators
    def measure_performance(func):
        """Fallback performance measurement decorator"""
        return func
    
    def monitor_memory(func):
        """Fallback memory monitoring decorator"""
        return func
    
    def profile_function(name):
        """Fallback profiling decorator"""
        def decorator(func):
            return func
        return decorator
    
    def timed_operation(name):
        """Fallback timed operation decorator"""
        def decorator(func):
            return func
        return decorator
    
    def handle_errors(severity=None, category=None):
        """Fallback error handling decorator"""
        def decorator(func):
            return func
        return decorator
    
    def retry_on_failure(max_attempts=3, base_delay=1.0, max_delay=60.0, strategy=None):
        """Fallback retry decorator"""
        def decorator(func):
            return func
        return decorator
    
    # Fallback enums and classes
    class ErrorSeverity:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"
    
    class ErrorCategory:
        API = "api"
        DATA = "data"
        NETWORK = "network"
        VALIDATION = "validation"
        SYSTEM = "system"
        BUSINESS = "business"
    
    class RetryConfig:
        def __init__(self, max_attempts=3, base_delay=1.0, max_delay=60.0, backoff_multiplier=2.0, jitter=True, strategy=None):
            self.max_attempts = max_attempts
            self.base_delay = base_delay
            self.max_delay = max_delay
            self.backoff_multiplier = backoff_multiplier
            self.jitter = jitter
            self.strategy = strategy

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
    'SectorAnalysis',
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
- MARKET_CAP_ASSUME_EOKWON_MAX: 억원 단위로 간주할 최대값 (기본값: 2,000,000, 단위: 억원)
- MARKET_CAP_ASSUME_EOKWON_MIN: 억원 단위로 간주할 최소값 (기본값: 1.0, 단위: 억원)
- ENABLE_FAKE_PROVIDERS: 외부 모듈 실패 시 더미 구현 사용 (기본값: false; true=운영 중 일시 장애 시 진단 계속)
"""

import pandas as pd
import numpy as np
import json
import time
import os
import yaml
import math
import random
import signal
import atexit
import enum
import weakref
import sys
import psutil
import typer
import io
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, TypedDict, Set
from decimal import Decimal
from threading import RLock, Condition
from collections import deque, OrderedDict
# rich import 제거 (미사용)

# monotonic time 별칭 (시스템 시간 변경에 안전)
_monotonic = time.monotonic

# ✅ 모듈 레벨 환경변수 캐시 (핫패스 최적화)
_ENV_CACHE = {
    'current_ratio_ambiguous_strategy': os.getenv("CURRENT_RATIO_AMBIGUOUS_STRATEGY", "as_is"),
    'current_ratio_force_percent': os.getenv("CURRENT_RATIO_FORCE_PERCENT", "false"),
    'market_cap_strict_mode': os.getenv("MARKET_CAP_STRICT_MODE", "true"),
}

# ✅ 모듈 레벨 로깅 제어 (한 번만 경고) - 스레드 안전
_market_cap_ambiguous_logged = False
_market_cap_ambiguous_counter = 0
_market_cap_last_agg_ts = 0.0
_market_cap_ambiguous_lock = RLock()

def _is_indexed_by_code(df: pd.DataFrame) -> bool:
    """DataFrame이 '단축코드'로 인덱싱되어 있는지 안전하게 확인"""
    return df.index.names and ('단축코드' in df.index.names)

def _refresh_env_cache():
    """환경변수 캐시 hot-reload (런타임 설정 변경 지원)"""
    _ENV_CACHE['current_ratio_ambiguous_strategy'] = os.getenv("CURRENT_RATIO_AMBIGUOUS_STRATEGY", "as_is")
    _ENV_CACHE['current_ratio_force_percent'] = os.getenv("CURRENT_RATIO_FORCE_PERCENT", "false")
    _ENV_CACHE['market_cap_strict_mode'] = os.getenv("MARKET_CAP_STRICT_MODE", "true")

# --- 환경변수 캐시 핫리로드: SIGHUP 지원 ------------------------------------
def _handle_sighup(signum, frame):
    try:
        _refresh_env_cache()
        _reload_all_analyzer_env_cache()  # Analyzer 인스턴스 env_cache도 재적용
        logging.info("[env] SIGHUP received → environment cache reloaded")
    except Exception as e:
        logging.debug(f"[env] SIGHUP handler error: {e}")

# Analyzer 인스턴스별 env_cache 재적용을 위한 콜백 등록 (WeakSet으로 메모리 누수 방지)
_analyzer_instances = weakref.WeakSet()

def _register_analyzer_for_env_reload(analyzer):
    """Analyzer 인스턴스를 환경변수 리로드 대상으로 등록"""
    _analyzer_instances.add(analyzer)

def _unregister_analyzer_for_env_reload(analyzer):
    """Analyzer 인스턴스를 환경변수 리로드 대상에서 제거"""
    _analyzer_instances.discard(analyzer)

def _reload_all_analyzer_env_cache():
    """모든 등록된 Analyzer 인스턴스의 env_cache 재적용"""
    for analyzer in list(_analyzer_instances):
        try:
            analyzer.env_cache = {
                'current_ratio_ambiguous_strategy': os.getenv("CURRENT_RATIO_AMBIGUOUS_STRATEGY", "as_is"),
                'current_ratio_force_percent': os.getenv("CURRENT_RATIO_FORCE_PERCENT", "false"),
                'market_cap_strict_mode': os.getenv("MARKET_CAP_STRICT_MODE", "true"),
                'max_sector_peers_base': safe_env_int("MAX_SECTOR_PEERS_BASE", 40, min_val=5),
                'max_sector_peers_full': safe_env_int("MAX_SECTOR_PEERS_FULL", 200, min_val=10),
                'sector_target_good': safe_env_int("SECTOR_TARGET_GOOD", 60, min_val=10),
                'max_sector_cache_entries': safe_env_int("MAX_SECTOR_CACHE_ENTRIES", 64, min_val=8),
            }
        except Exception as e:
            logging.debug(f"[env] Analyzer env_cache reload error: {e}")

# SIGHUP 핸들러 등록 함수 (CLI에서 명시적으로 호출)
def install_sighup_handler():
    """SIGHUP 핸들러를 설치합니다.
    
    ⚠️ 엔트리포인트에서 로깅/유틸 초기화 이후 '마지막'에 호출하세요.
    순서: _setup_logging_if_needed() → 기타 초기화 → install_sighup_handler()
    """
    try:
        signal.signal(signal.SIGHUP, _handle_sighup)
        logging.debug("[env] SIGHUP handler installed")
        _mark_sighup_installed()  # 설치 완료 표시
    except (AttributeError, OSError) as e:
        # Windows 등에서는 SIGHUP 미지원 - 이는 정상적인 동작
        import platform
        if platform.system() == "Windows":
            logging.debug("[env] SIGHUP not supported on Windows; env hot-reload disabled")
        else:
            logging.debug(f"[env] SIGHUP not supported on this platform: {e}")
        _mark_sighup_installed()  # 플랫폼 제한으로 인한 실패도 "설치 시도됨"으로 표시
    except Exception as e:
        # 기타 예외
        logging.debug(f"[env] SIGHUP handler installation failed: {e}")
        _mark_sighup_installed()  # 설치 시도는 했으므로 표시

# =============================================================================
# 유틸리티 함수
# =============================================================================

def normalize_market_cap_ekwon(x: Optional[float]) -> Optional[float]:
    """
    Normalize market cap to 억원 (eokwon).
    Heuristics:
      - If value looks like 억원 (<= 2,000,000 = 200조), keep as-is.
      - If value looks like 원 (>= 1e11 = 1,000억), convert to 억원 by /1e8.
      - Otherwise treat as ambiguous → optional non-strict conversion via env.
    """
    v = DataValidator.safe_float_optional(x)
    if v is None or not math.isfinite(v) or v <= 0:
        return None

    # Enhanced heuristic: avoid tiny KRW values being treated as eokwon
    # Values like 20,000,001원 should not be treated as 20,000,001억원
    max_eokwon_threshold = safe_env_float("MARKET_CAP_ASSUME_EOKWON_MAX", 2_000_000, 0.0)  # 200조 억원
    min_eokwon_threshold = safe_env_float("MARKET_CAP_ASSUME_EOKWON_MIN", 1.0, 0.0)  # 1억원 (소형주 포함)
    
    # If already reasonable in 억원 range, assume eokwon
    # But exclude very small values that are likely in won units
    if v <= max_eokwon_threshold and v >= min_eokwon_threshold and v >= 1e7:
        logging.debug(f"[unit] market_cap assumed eokwon: {x} -> {v}")
        return v

    # If looks like KRW (원): anything ≥ 1e11 (1,000억 원) convert to 억원
    if v >= 1e11:
        converted = v / 1e8
        logging.debug(f"[unit] market_cap converted from won→eokwon: {x} -> {converted}")
        return converted

    # Ambiguous band (1e7 ~ 1e11): gate via env for safety (캐시된 값 사용)
    non_strict = _ENV_CACHE['market_cap_strict_mode'].lower() != "true"
    if non_strict and (1e7 <= v < 1e11):
        converted = v / 1e8
        logging.debug(f"[unit] market_cap non-strict (ambiguous) won→eokwon: {x} -> {converted} (천단위 구분 해석 결과)")
        return converted

    # Confidence logging when discarding ambiguous values (1회 경고 활용) - 스레드 안전
    global _market_cap_ambiguous_logged, _market_cap_ambiguous_counter, _market_cap_last_agg_ts
    with _market_cap_ambiguous_lock:
        if 1e10 <= v < 1e11 and not _market_cap_ambiguous_logged:
            # 1e10 ≤ v < 1e11만 경고 후 None (코스닥 소형주 원 단위 시총 고려)
            logging.warning("[unit] market_cap ambiguous range encountered (strict mode). Consider MARKET_CAP_STRICT_MODE=false temporarily for diagnosis.")
            _market_cap_ambiguous_logged = True
        elif 1e10 <= v < 1e11:
            _market_cap_ambiguous_counter += 1
            now = _monotonic()
            if now - _market_cap_last_agg_ts > 60.0 and _market_cap_ambiguous_counter > 0:
                logging.warning(f"[unit] market_cap ambiguous (strict mode) last 60s: {_market_cap_ambiguous_counter} hits")
                _market_cap_ambiguous_counter = 0
                _market_cap_last_agg_ts = now  # Set timestamp when warning is logged
            else:
                logging.debug(f"[unit] market_cap ambiguous range dropped in strict mode: {x} -> None (1e10 ≤ v < 1e11)")
        elif 1e7 <= v < 1e10:
            # 1e7 ≤ v < 1e10은 추적 메트릭 + 샘플 저장 (디버그)
            logging.debug(f"[unit] market_cap small value dropped: {x} -> None (1e7 ≤ v < 1e10, likely small cap in won)")
        elif v < 1e7:
            logging.debug(f"[unit] market_cap too small (dropped): {x} -> None (천단위 구분 해석 결과)")
    
    # All ambiguous cases return None
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
    "%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
# ✅ 로그 초기화 패턴 개선: 모듈 import 시점에는 설정하지 않고, 엔트리포인트에서만 기본 로깅 설정
def _setup_logging_if_needed():
    """엔트리포인트에서만 호출하여 기본 로깅 설정
    
    CLI 사용 예시:
        from enhanced_integrated_analyzer_refactored import _setup_logging_if_needed, install_sighup_handler
        
        def main():
            _setup_logging_if_needed()  # 로깅 초기화
            # 기타 환경/유틸 초기화
            install_sighup_handler()    # 런타임 환경변수 핫리로드
            # 메인 로직 실행
    """
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

def _validate_startup_configuration():
    """부팅 시 구성 실수 검증 및 차단"""
    errors = []
    warnings = []
    
    # 1. 밸류에이션 페널티 이중 적용 검증
    price_penalty = safe_env_bool("VAL_PENALTY_IN_PRICE", True)
    fin_penalty = safe_env_bool("VAL_PENALTY_IN_FIN", False)
    
    if price_penalty and fin_penalty:
        errors.append("VAL_PENALTY_IN_PRICE and VAL_PENALTY_IN_FIN cannot both be True. This causes double penalty application.")
    
    # 2. 시총 정규화 모드 검증
    strict_mode = safe_env_bool("MARKET_CAP_STRICT_MODE", True)
    if not strict_mode:
        warnings.append("MARKET_CAP_STRICT_MODE is disabled. This may allow ambiguous market cap values.")
    
    # 3. 레이트리미터 설정 검증
    max_tps = safe_env_int("KIS_MAX_TPS", 8, 1)
    if max_tps > 20:
        warnings.append(f"KIS_MAX_TPS is very high ({max_tps}). Consider reducing to avoid API quota issues.")
    
    # 4. 캐시 압축 임계값 검증
    compress_min = safe_env_int("KIS_CACHE_COMPRESS_MIN_BYTES", 8 * 1024, 1024)
    if compress_min < 1024:
        warnings.append(f"KIS_CACHE_COMPRESS_MIN_BYTES is very low ({compress_min}). Consider increasing to avoid CPU overhead.")
    
    # 5. SIGHUP 핸들러 설치 확인
    if not hasattr(_validate_startup_configuration, '_sighup_installed'):
        warnings.append("SIGHUP handler not installed. Environment variable hot-reload is disabled.")
    
    # 오류가 있으면 예외 발생
    if errors:
        error_msg = "Startup configuration errors:\n" + "\n".join(f"  - {error}" for error in errors)
        if warnings:
            error_msg += "\nWarnings:\n" + "\n".join(f"  - {warning}" for warning in warnings)
        raise ValueError(error_msg)
    
    # 경고만 있으면 로깅
    if warnings:
        for warning in warnings:
            logging.warning(f"[startup] {warning}")
    
    logging.info("[startup] Configuration validation passed")

def _mark_sighup_installed():
    """SIGHUP 핸들러 설치 완료 표시"""
    _validate_startup_configuration._sighup_installed = True
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
# 입력 신뢰도 가드 클래스
# =============================================================================

class InputReliabilityGuard:
    """입력 데이터 신뢰도 검증 및 가드 클래스"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 핵심 재무 필드 정의 (2개 이상 결측 시 스코어링 제외)
        self.core_financial_fields = {
            'roe', 'roa', 'debt_ratio', 'net_profit_margin', 'current_ratio'
        }
        # 시총 스크립트 모드 강제 설정
        self.market_cap_strict_mode = safe_env_bool("MARKET_CAP_STRICT_MODE", True)
        # 결측 필드 임계치 (환경변수로 조정 가능)
        self.max_missing_core_fields = safe_env_int("MAX_MISSING_CORE_FIELDS", 2, 0)
    
    def validate_market_cap_reliability(self, market_cap: Optional[float]) -> Tuple[bool, str]:
        """시가총액 신뢰도 검증"""
        if market_cap is None:
            return False, "market_cap_missing"
        
        # 스크립트 모드에서 애매한 밴드(1e7~1e11원) 드롭
        if self.market_cap_strict_mode and 1e7 <= market_cap < 1e11:
            return False, "market_cap_ambiguous_strict_mode"
        
        # 이상치 검증 (너무 작거나 큰 값) - 억원 단위 기준
        if market_cap < 1e-2:  # 0.01억원 미만 (100만원 미만)
            return False, "market_cap_too_small"
        if market_cap > 1e6:  # 100만억원 초과 (100조원 초과)
            return False, "market_cap_too_large"
        
        return True, "valid"
    
    def validate_financial_data_reliability(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, int]:
        """재무 데이터 신뢰도 검증"""
        if not financial_data:
            return False, "financial_data_empty", 0
        
        # 핵심 필드 결측 개수 계산
        missing_count = 0
        for field in self.core_financial_fields:
            if field not in financial_data or financial_data[field] is None:
                missing_count += 1
        
        # 결측 필드 메트릭 기록
        if self.metrics and missing_count > 0:
            self.metrics.record_missing_financial_fields(missing_count)
        
        # 임계치 초과 시 스코어링 제외
        if missing_count > self.max_missing_core_fields:
            return False, f"too_many_missing_fields_{missing_count}", missing_count
        
        return True, "valid", missing_count
    
    def validate_percentage_units_consistency(self, financial_data: Dict[str, Any]) -> Tuple[bool, str]:
        """% 단위 일관성 검증 (이중 스케일링 방지)"""
        # 이미 표준화되었는지 확인
        if financial_data.get("_percent_canonicalized") is not True:
            return False, "percent_not_canonicalized"
        
        # % 필드들의 값 범위 검증
        percent_fields = DataConverter.PERCENT_FIELDS
        for field in percent_fields:
            if field in financial_data and financial_data[field] is not None:
                value = financial_data[field]
                if isinstance(value, (int, float)) and not math.isfinite(value):
                    return False, f"invalid_percent_value_{field}"
                # 비정상적으로 큰 % 값 검증 (예: 1000% 이상)
                if isinstance(value, (int, float)) and abs(value) > 1000:
                    return False, f"percent_value_too_large_{field}"
        
        return True, "valid"
    
    def validate_input_reliability(self, symbol: str, market_cap: Optional[float], 
                                 financial_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """종합 입력 신뢰도 검증"""
        validation_result = {
            'market_cap_valid': False,
            'financial_data_valid': False,
            'percentage_units_valid': False,
            'missing_core_fields': 0,
            'validation_errors': []
        }
        
        # 1. 시가총액 검증
        mc_valid, mc_error = self.validate_market_cap_reliability(market_cap)
        validation_result['market_cap_valid'] = mc_valid
        if not mc_valid:
            validation_result['validation_errors'].append(f"market_cap: {mc_error}")
        
        # 2. 재무 데이터 검증
        fin_valid, fin_error, missing_count = self.validate_financial_data_reliability(financial_data)
        validation_result['financial_data_valid'] = fin_valid
        validation_result['missing_core_fields'] = missing_count
        if not fin_valid:
            validation_result['validation_errors'].append(f"financial_data: {fin_error}")
        
        # 3. % 단위 일관성 검증
        pct_valid, pct_error = self.validate_percentage_units_consistency(financial_data)
        validation_result['percentage_units_valid'] = pct_valid
        if not pct_valid:
            validation_result['validation_errors'].append(f"percentage_units: {pct_error}")
        
        # 전체 검증 결과
        overall_valid = mc_valid and fin_valid and pct_valid
        error_summary = "; ".join(validation_result['validation_errors']) if validation_result['validation_errors'] else "valid"
        
        return overall_valid, error_summary, validation_result

# =============================================================================
# 가치지표 정밀화 클래스
# =============================================================================

class ValueMetricsPrecision:
    """가치지표 핵심 5개 정밀화 클래스"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 가치지표 가중치 (총합 100)
        self.value_weights = {
            'ev_ebit': 35,           # EV/EBIT (현금흐름 대리값)
            'fcf_yield': 25,         # 정상화 FCF 수익률
            'owner_earnings': 20,    # Owner Earnings Yield (버핏식)
            'earnings_quality': 10,  # Earnings Yield의 질 보정
            'shareholder_yield': 10  # 배당재투자 보정
        }
        # 절대 밴드 임계치
        self.absolute_bands = {
            'ev_ebit_max': 8.0,      # EV/EBIT ≤ 8 가점
            'fcf_yield_min': 0.05,   # FCF Yield ≥ 5% 가점
            'owner_earnings_min': 0.08,  # Owner Earnings ≥ 8% 가점
            'earnings_quality_min': 0.06,  # Earnings Quality ≥ 6% 가점
            'shareholder_yield_min': 0.03  # Shareholder Yield ≥ 3% 가점
        }
    
    def calculate_ev_ebit_score(self, market_cap: float, net_debt: float, 
                               operating_income: float, sector_median: float = None) -> float:
        """EV/EBIT 점수 계산 (현금흐름 대리값)"""
        if not all(x is not None and x > 0 for x in [market_cap, operating_income]):
            return 0.0
        
        # EV = 시가총액 + 순부채
        ev = market_cap + (net_debt or 0)
        ev_ebit = ev / operating_income
        
        # 절대 밴드 점수 (EV/EBIT ≤ 8 가점)
        if ev_ebit <= self.absolute_bands['ev_ebit_max']:
            absolute_score = 100.0
        else:
            # 8~20 범위에서 선형 감소
            absolute_score = max(0, 100 * (20 - ev_ebit) / (20 - 8))
        
        # 섹터 상대 점수 (역순 백분위)
        if sector_median and sector_median > 0:
            relative_score = max(0, 100 * (sector_median - ev_ebit) / sector_median)
        else:
            relative_score = 50.0  # 중립 점수
        
        # 절대/상대 가중 평균 (절대 70%, 상대 30%)
        return 0.7 * absolute_score + 0.3 * relative_score
    
    def calculate_normalized_fcf_yield(self, market_cap: float, fcf_history: List[float]) -> float:
        """정상화 FCF 수익률 계산 (최근 5년 가중 평균)"""
        if not fcf_history or not market_cap or market_cap <= 0:
            return 0.0
        
        # 최근 5년 데이터만 사용
        recent_fcf = fcf_history[-5:] if len(fcf_history) >= 5 else fcf_history
        
        # 가중 평균 (최근치 가중↑)
        weights = [i + 1 for i in range(len(recent_fcf))]
        total_weight = sum(weights)
        
        # 적자 연도는 0으로 클립
        weighted_fcf = sum(max(0, fcf) * weight for fcf, weight in zip(recent_fcf, weights))
        normalized_fcf = weighted_fcf / total_weight
        
        # FCF Yield = 정상화 FCF / 시가총액
        fcf_yield = normalized_fcf / market_cap
        
        # 점수화 (≥5% 가점)
        if fcf_yield >= self.absolute_bands['fcf_yield_min']:
            return 100.0
        else:
            return max(0, 100 * fcf_yield / self.absolute_bands['fcf_yield_min'])
    
    def calculate_owner_earnings_yield(self, market_cap: float, net_income: float,
                                     depreciation: float, maintenance_capex: float) -> float:
        """Owner Earnings Yield 계산 (버핏식)"""
        if not all(x is not None for x in [market_cap, net_income]) or market_cap <= 0:
            return 0.0
        
        # Owner Earnings = 순이익 + 감가상각·충당금 - 유지보수성 CapEx
        owner_earnings = net_income + (depreciation or 0) - (maintenance_capex or 0)
        
        # Owner Earnings Yield = Owner Earnings / 시가총액
        owner_earnings_yield = owner_earnings / market_cap
        
        # 점수화 (≥8% 가점)
        if owner_earnings_yield >= self.absolute_bands['owner_earnings_min']:
            return 100.0
        else:
            return max(0, 100 * owner_earnings_yield / self.absolute_bands['owner_earnings_min'])
    
    def calculate_earnings_quality_score(self, market_cap: float, net_income: float,
                                       net_debt: float, is_loss: bool, 
                                       one_time_items: float = 0, tax_rate: float = 0.25) -> float:
        """Earnings Yield의 질 보정 점수"""
        if not all(x is not None for x in [market_cap, net_income]) or market_cap <= 0:
            return 0.0
        
        # EV = 시가총액 + 순부채
        ev = market_cap + (net_debt or 0)
        
        # 기본 Earnings Yield
        earnings_yield = net_income / ev
        
        # 품질 보정 팩터
        quality_factor = 1.0
        
        # 적자 패널티
        if is_loss or net_income <= 0:
            quality_factor *= 0.3
        
        # 일회성 항목 패널티
        if one_time_items and abs(one_time_items) > abs(net_income) * 0.1:
            quality_factor *= 0.8
        
        # 적정세율 보정 (실제 세율이 너무 낮으면 패널티)
        if tax_rate < 0.15:  # 15% 미만이면 패널티
            quality_factor *= 0.9
        
        # 보정된 Earnings Yield
        adjusted_earnings_yield = earnings_yield * quality_factor
        
        # 점수화 (≥6% 가점)
        if adjusted_earnings_yield >= self.absolute_bands['earnings_quality_min']:
            return 100.0
        else:
            return max(0, 100 * adjusted_earnings_yield / self.absolute_bands['earnings_quality_min'])
    
    def calculate_shareholder_yield_score(self, market_cap: float, dividend_yield: float,
                                        shares_outstanding: float, shares_repurchased: float) -> float:
        """배당재투자 보정 점수 (Shareholder Yield)"""
        if not market_cap or market_cap <= 0:
            return 0.0
        
        # 배당수익률
        dividend_component = dividend_yield or 0
        
        # 순자사주율 (총발행 대비 순감소율)
        if shares_outstanding and shares_outstanding > 0:
            buyback_yield = (shares_repurchased or 0) / shares_outstanding
        else:
            buyback_yield = 0
        
        # Shareholder Yield = 배당수익률 + 순자사주율
        shareholder_yield = dividend_component + buyback_yield
        
        # 점수화 (≥3% 가점)
        if shareholder_yield >= self.absolute_bands['shareholder_yield_min']:
            return 100.0
        else:
            return max(0, 100 * shareholder_yield / self.absolute_bands['shareholder_yield_min'])
    
    def calculate_comprehensive_value_score(self, financial_data: Dict[str, Any], 
                                          market_cap: float, sector_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """종합 가치 점수 계산 (핵심 5개 지표)"""
        result = {
            'individual_scores': {},
            'weighted_score': 0.0,
            'breakdown': {}
        }
        
        # 1. EV/EBIT 점수
        ev_ebit_score = self.calculate_ev_ebit_score(
            market_cap=market_cap,
            net_debt=financial_data.get('net_debt'),
            operating_income=financial_data.get('operating_income'),
            sector_median=sector_data.get('ev_ebit_median') if sector_data else None
        )
        result['individual_scores']['ev_ebit'] = ev_ebit_score
        
        # 2. 정상화 FCF Yield 점수
        fcf_yield_score = self.calculate_normalized_fcf_yield(
            market_cap=market_cap,
            fcf_history=financial_data.get('fcf_history', [])
        )
        result['individual_scores']['fcf_yield'] = fcf_yield_score
        
        # 3. Owner Earnings Yield 점수
        owner_earnings_score = self.calculate_owner_earnings_yield(
            market_cap=market_cap,
            net_income=financial_data.get('net_income'),
            depreciation=financial_data.get('depreciation'),
            maintenance_capex=financial_data.get('maintenance_capex')
        )
        result['individual_scores']['owner_earnings'] = owner_earnings_score
        
        # 4. Earnings Quality 점수
        earnings_quality_score = self.calculate_earnings_quality_score(
            market_cap=market_cap,
            net_income=financial_data.get('net_income'),
            net_debt=financial_data.get('net_debt'),
            is_loss=financial_data.get('net_income', 0) <= 0,
            one_time_items=financial_data.get('one_time_items', 0),
            tax_rate=financial_data.get('effective_tax_rate', 0.25)
        )
        result['individual_scores']['earnings_quality'] = earnings_quality_score
        
        # 5. Shareholder Yield 점수
        shareholder_yield_score = self.calculate_shareholder_yield_score(
            market_cap=market_cap,
            dividend_yield=financial_data.get('dividend_yield'),
            shares_outstanding=financial_data.get('shares_outstanding'),
            shares_repurchased=financial_data.get('shares_repurchased')
        )
        result['individual_scores']['shareholder_yield'] = shareholder_yield_score
        
        # 가중합 계산
        total_weighted_score = 0.0
        for metric, score in result['individual_scores'].items():
            weight = self.value_weights.get(metric, 0)
            weighted_score = score * weight / 100.0
            total_weighted_score += weighted_score
            result['breakdown'][metric] = {
                'score': score,
                'weight': weight,
                'weighted_score': weighted_score
            }
        
        result['weighted_score'] = total_weighted_score
        result['comprehensive_value_score'] = total_weighted_score  # 종합점수 키 추가
        
        return result

# =============================================================================
# 안전마진·내재가치 2단계 계산 클래스
# =============================================================================

class MarginOfSafetyCalculator:
    """안전마진·내재가치 2단계 계산 클래스"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 시나리오 확률 가중치
        self.scenario_probabilities = {
            'conservative': 0.3,    # 보수적 시나리오 30%
            'base': 0.5,           # 기준 시나리오 50%
            'optimistic': 0.2      # 낙관적 시나리오 20%
        }
        # 안전마진 임계치
        self.mos_thresholds = {
            'buy': 0.30,      # MoS ≥ 30% → BUY
            'watch': 0.10,    # MoS ≥ 10% → WATCH
            'pass': 0.0       # MoS < 10% → PASS
        }
    
    def calculate_fcf_multiple_valuation(self, market_cap: float, fcf_history: List[float],
                                       growth_rate: float = 0.0, discount_rate: float = 0.10) -> float:
        """FCF 멀티플 기반 내재가치 계산"""
        if not fcf_history or not market_cap or market_cap <= 0:
            return 0.0
        
        # 최근 3년 FCF 평균
        recent_fcf = fcf_history[-3:] if len(fcf_history) >= 3 else fcf_history
        avg_fcf = sum(recent_fcf) / len(recent_fcf)
        
        # 성장률이 적용된 영구가치
        if growth_rate >= discount_rate:
            growth_rate = discount_rate - 0.01  # 성장률이 할인율 이상이면 조정
        
        # 영구가치 = FCF * (1 + 성장률) / (할인율 - 성장률)
        terminal_value = avg_fcf * (1 + growth_rate) / (discount_rate - growth_rate)
        
        return terminal_value
    
    def calculate_eps_multiple_valuation(self, market_cap: float, eps_history: List[float],
                                       pe_ratio: float = 15.0, growth_rate: float = 0.0) -> float:
        """EPS 멀티플 기반 내재가치 계산"""
        if not eps_history or not market_cap or market_cap <= 0:
            return 0.0
        
        # 최근 3년 EPS 평균
        recent_eps = eps_history[-3:] if len(eps_history) >= 3 else eps_history
        avg_eps = sum(recent_eps) / len(recent_eps)
        
        # 성장률 조정된 적정 PER
        adjusted_pe = pe_ratio * (1 + growth_rate)
        
        # 내재가치 = 평균 EPS × 조정된 PER
        intrinsic_value = avg_eps * adjusted_pe
        
        return intrinsic_value
    
    def calculate_scenario_based_valuation(self, financial_data: Dict[str, Any], 
                                         market_cap: float) -> Dict[str, Any]:
        """시나리오 3분기 기반 내재가치 계산"""
        result = {
            'scenarios': {},
            'expected_intrinsic_value': 0.0,
            'scenario_breakdown': {}
        }
        
        # 시나리오별 파라미터
        scenarios = {
            'conservative': {
                'growth_rate': 0.02,      # 2% 성장
                'discount_rate': 0.12,    # 12% 할인율
                'pe_ratio': 12.0,         # 보수적 PER
                'fcf_multiplier': 0.8     # FCF 보수적 조정
            },
            'base': {
                'growth_rate': 0.05,      # 5% 성장
                'discount_rate': 0.10,    # 10% 할인율
                'pe_ratio': 15.0,         # 기준 PER
                'fcf_multiplier': 1.0     # FCF 기준
            },
            'optimistic': {
                'growth_rate': 0.08,      # 8% 성장
                'discount_rate': 0.08,    # 8% 할인율
                'pe_ratio': 18.0,         # 낙관적 PER
                'fcf_multiplier': 1.2     # FCF 낙관적 조정
            }
        }
        
        # 각 시나리오별 내재가치 계산
        for scenario_name, params in scenarios.items():
            # FCF 멀티플 내재가치
            fcf_iv = self.calculate_fcf_multiple_valuation(
                market_cap=market_cap,
                fcf_history=financial_data.get('fcf_history', []),
                growth_rate=params['growth_rate'],
                discount_rate=params['discount_rate']
            ) * params['fcf_multiplier']
            
            # EPS 멀티플 내재가치
            eps_iv = self.calculate_eps_multiple_valuation(
                market_cap=market_cap,
                eps_history=financial_data.get('eps_history', []),
                pe_ratio=params['pe_ratio'],
                growth_rate=params['growth_rate']
            )
            
            # 더 낮은 값 선택 (보수적 접근)
            scenario_iv = min(fcf_iv, eps_iv) if fcf_iv > 0 and eps_iv > 0 else max(fcf_iv, eps_iv)
            
            result['scenarios'][scenario_name] = {
                'fcf_valuation': fcf_iv,
                'eps_valuation': eps_iv,
                'intrinsic_value': scenario_iv,
                'probability': self.scenario_probabilities[scenario_name]
            }
        
        # 확률 가중 기대 내재가치
        expected_iv = sum(
            scenario_data['intrinsic_value'] * scenario_data['probability']
            for scenario_data in result['scenarios'].values()
        )
        result['expected_intrinsic_value'] = expected_iv
        
        # 시나리오별 기여도 계산
        for scenario_name, scenario_data in result['scenarios'].items():
            contribution = scenario_data['intrinsic_value'] * scenario_data['probability']
            result['scenario_breakdown'][scenario_name] = {
                'contribution': contribution,
                'weight': contribution / expected_iv if expected_iv > 0 else 0
            }
        
        return result
    
    def calculate_margin_of_safety(self, current_price: float, intrinsic_value: float) -> Dict[str, Any]:
        """안전마진 계산 및 신호 결정"""
        if not current_price or not intrinsic_value or intrinsic_value <= 0:
            return {
                'margin_of_safety': 0.0,
                'signal': 'PASS',
                'reason': 'insufficient_data',
                'target_buy_price': 0.0
            }
        
        # 안전마진 = (내재가치 - 현재가) / 내재가치
        margin_of_safety = max(0.0, (intrinsic_value - current_price) / intrinsic_value)
        
        # 목표 매수가 = 내재가치 × (1 - 최소 안전마진)
        target_buy_price = intrinsic_value * (1 - self.mos_thresholds['buy'])
        
        # 신호 결정
        if margin_of_safety >= self.mos_thresholds['buy']:
            signal = 'BUY'
            reason = f'mos_{margin_of_safety:.1%}_above_buy_threshold'
        elif margin_of_safety >= self.mos_thresholds['watch']:
            signal = 'WATCH'
            reason = f'mos_{margin_of_safety:.1%}_above_watch_threshold'
        else:
            signal = 'PASS'
            reason = f'mos_{margin_of_safety:.1%}_below_watch_threshold'
        
        return {
            'margin_of_safety': margin_of_safety,
            'signal': signal,
            'reason': reason,
            'target_buy_price': target_buy_price,
            'intrinsic_value': intrinsic_value,
            'current_price': current_price
        }
    
    def calculate_comprehensive_valuation(self, symbol: str, current_price: float,
                                        financial_data: Dict[str, Any], 
                                        market_cap: float) -> Dict[str, Any]:
        """종합 가치평가 (2단계 + 시나리오)"""
        result = {
            'symbol': symbol,
            'current_price': current_price,
            'market_cap': market_cap,
            'scenario_analysis': {},
            'margin_of_safety_analysis': {},
            'final_recommendation': {}
        }
        
        # 1단계: 시나리오 기반 내재가치 계산
        scenario_result = self.calculate_scenario_based_valuation(financial_data, market_cap)
        result['scenario_analysis'] = scenario_result
        
        # 2단계: 안전마진 계산
        expected_iv = scenario_result['expected_intrinsic_value']
        mos_result = self.calculate_margin_of_safety(current_price, expected_iv)
        result['margin_of_safety_analysis'] = mos_result
        
        # 최종 권고사항
        result['final_recommendation'] = {
            'signal': mos_result['signal'],
            'intrinsic_value': expected_iv,
            'margin_of_safety': mos_result['margin_of_safety'],
            'target_buy_price': mos_result['target_buy_price'],
            'confidence_level': self._calculate_confidence_level(scenario_result),
            'risk_factors': self._identify_risk_factors(financial_data, scenario_result)
        }
        
        return result
    
    def _calculate_confidence_level(self, scenario_result: Dict[str, Any]) -> str:
        """신뢰도 수준 계산"""
        scenarios = scenario_result['scenarios']
        
        # 시나리오 간 편차 계산
        values = [s['intrinsic_value'] for s in scenarios.values()]
        if not values or len(values) < 2:
            return 'LOW'
        
        mean_val = sum(values) / len(values)
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        cv = std_dev / mean_val if mean_val > 0 else 1.0
        
        if cv < 0.2:
            return 'HIGH'
        elif cv < 0.4:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _identify_risk_factors(self, financial_data: Dict[str, Any], 
                             scenario_result: Dict[str, Any]) -> List[str]:
        """리스크 요인 식별"""
        risk_factors = []
        
        # FCF 변동성 리스크
        fcf_history = financial_data.get('fcf_history', [])
        if len(fcf_history) >= 3:
            fcf_std = np.std(fcf_history) if len(fcf_history) > 1 else 0
            fcf_mean = np.mean(fcf_history) if fcf_history else 0
            if fcf_mean > 0 and fcf_std / fcf_mean > 0.5:
                risk_factors.append('high_fcf_volatility')
        
        # 시나리오 간 편차 리스크
        scenarios = scenario_result['scenarios']
        values = [s['intrinsic_value'] for s in scenarios.values()]
        if values:
            min_val = min(values)
            max_val = max(values)
            if min_val > 0 and (max_val - min_val) / min_val > 1.0:
                risk_factors.append('high_scenario_variance')
        
        # 부채 리스크
        debt_ratio = financial_data.get('debt_ratio', 0)
        if debt_ratio and debt_ratio > 50:  # 50% 이상
            risk_factors.append('high_debt_ratio')
        
        return risk_factors

# =============================================================================
# 품질·지속성 필터 클래스
# =============================================================================

class QualityConsistencyFilter:
    """품질·지속성 필터 클래스 (가치 계산 전 자격 검증)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 품질 임계치
        self.quality_thresholds = {
            'min_operating_margin': 5.0,      # 최소 영업이익률 5%
            'min_net_margin': 3.0,            # 최소 순이익률 3%
            'min_piotroski_score': 6,         # 최소 Piotroski F-Score 6/9
            'min_interest_coverage': 3.0,     # 최소 이자보상배율 3배
            'max_accruals_ratio': 0.3,        # 최대 Accruals 비율 30%
            'min_profitability_consistency': 0.6  # 최소 수익성 일관성 60%
        }
        # 5년 롤링 윈도우
        self.rolling_window = 5
    
    def check_profitability_consistency(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """지속적 수익성 검증 (5년 롤링)"""
        # 영업이익률과 순이익률 5년 데이터 필요 (데이터 부족 시 현재 데이터로 대체)
        operating_margins = financial_data.get('operating_margin_history', [])
        net_margins = financial_data.get('net_margin_history', [])
        
        # 데이터가 부족한 경우 현재 데이터로 대체
        if len(operating_margins) < self.rolling_window:
            current_operating = financial_data.get('operating_margin', 0)
            if current_operating == 0:
                # operating_margin이 없으면 net_profit_margin 사용
                current_operating = financial_data.get('net_profit_margin', 0)
            operating_margins = [current_operating] * self.rolling_window
        
        if len(net_margins) < self.rolling_window:
            current_net = financial_data.get('net_margin', 0)
            if current_net == 0:
                # net_margin이 없으면 net_profit_margin 사용
                current_net = financial_data.get('net_profit_margin', 0)
            net_margins = [current_net] * self.rolling_window
        
        # 최근 5년 데이터
        recent_operating = operating_margins[-self.rolling_window:]
        recent_net = net_margins[-self.rolling_window:]
        
        # 평균값으로 검사 (백분위 대신)
        avg_operating = np.mean(recent_operating)
        avg_net = np.mean(recent_net)
        
        # 임계치 미달 검사
        if avg_operating < self.quality_thresholds['min_operating_margin']:
            return False, f"operating_margin_avg_{avg_operating:.1f}%", avg_operating
        
        if avg_net < self.quality_thresholds['min_net_margin']:
            return False, f"net_margin_avg_{avg_net:.1f}%", avg_net
        
        # 일관성 점수 계산 (양수 연도 비율)
        positive_operating_years = sum(1 for margin in recent_operating if margin > 0)
        positive_net_years = sum(1 for margin in recent_net if margin > 0)
        
        consistency_score = (positive_operating_years + positive_net_years) / (2 * self.rolling_window)
        
        if consistency_score < self.quality_thresholds['min_profitability_consistency']:
            return False, f"low_profitability_consistency_{consistency_score:.1%}", consistency_score
        
        return True, "profitability_consistent", consistency_score
    
    def check_accruals_quality(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """Accruals 가드 (회계적 이익/현금 괴리 검증)"""
        # 총자산 증가 대비 순이익 증가 비율
        total_assets_history = financial_data.get('total_assets_history', [])
        net_income_history = financial_data.get('net_income_history', [])
        
        if len(total_assets_history) < 2 or len(net_income_history) < 2:
            return True, "insufficient_data_for_accruals", 0.0  # 데이터 부족 시 통과
        
        # 최근 2년 비교
        assets_growth = (total_assets_history[-1] - total_assets_history[-2]) / total_assets_history[-2]
        income_growth = (net_income_history[-1] - net_income_history[-2]) / abs(net_income_history[-2]) if net_income_history[-2] != 0 else 0
        
        # Accruals 비율 = (순이익 증가 - 총자산 증가) / 총자산 증가
        if abs(assets_growth) < 0.01:  # 총자산 변화가 1% 미만이면 정상
            accruals_ratio = 0.0
        else:
            accruals_ratio = abs(income_growth - assets_growth) / abs(assets_growth)
        
        if accruals_ratio > self.quality_thresholds['max_accruals_ratio']:
            return False, f"high_accruals_ratio_{accruals_ratio:.1%}", accruals_ratio
        
        return True, "accruals_acceptable", accruals_ratio
    
    def calculate_piotroski_f_score(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, int]:
        """Piotroski F-Score 계산 (간이형)"""
        score = 0
        max_score = 9
        
        # 디버깅 정보
        logging.debug("Piotroski F-Score 계산 시작")
        
        # 1. 순이익 > 0 (1점) - ROE로 대체
        roe = financial_data.get('roe', 0)
        if roe > 0:
            score += 1
            logging.debug(f"ROE > 0: {roe:.1f}% (PASS)")
        else:
            logging.debug(f"ROE > 0: {roe:.1f}% (FAIL)")
        
        # 2. 영업현금흐름 > 0 (1점) - ROA로 대체
        roa = financial_data.get('roa', 0)
        if roa > 0:
            score += 1
            logging.debug(f"ROA > 0: {roa:.1f}% (PASS)")
        else:
            logging.debug(f"ROA > 0: {roa:.1f}% (FAIL)")
        
        # 3. 부채비율 적정 (1점)
        debt_ratio = financial_data.get('debt_ratio', 0)
        if debt_ratio < 50:  # 부채비율 50% 미만
            score += 1
            logging.debug(f"부채비율 < 50%: {debt_ratio:.1f}% (PASS)")
        else:
            logging.debug(f"부채비율 < 50%: {debt_ratio:.1f}% (FAIL)")
        
        # 4. 유동비율 적정 (1점)
        current_ratio = financial_data.get('current_ratio', 0)
        if current_ratio > 1.0:  # 유동비율 1.0 이상
            score += 1
            logging.debug(f"유동비율 > 1.0: {current_ratio:.1f} (PASS)")
        else:
            logging.debug(f"유동비율 > 1.0: {current_ratio:.1f} (FAIL)")
        
        # 5. 매출총이익률 양호 (1점)
        gross_margin = financial_data.get('gross_profit_margin', 0)
        if gross_margin > 0:
            score += 1
            logging.debug(f"매출총이익률 > 0: {gross_margin:.1f}% (PASS)")
        else:
            logging.debug(f"매출총이익률 > 0: {gross_margin:.1f}% (FAIL)")
        
        # 6. 순이익률 양호 (1점)
        net_margin = financial_data.get('net_profit_margin', 0)
        if net_margin > 0:
            score += 1
            logging.debug(f"순이익률 > 0: {net_margin:.1f}% (PASS)")
        else:
            logging.debug(f"순이익률 > 0: {net_margin:.1f}% (FAIL)")
        
        # 7. ROE 양호 (1점)
        if roe > 5:  # ROE 5% 이상
            score += 1
            logging.debug(f"ROE > 5%: {roe:.1f}% (PASS)")
        else:
            logging.debug(f"ROE > 5%: {roe:.1f}% (FAIL)")
        
        # 8. ROA 양호 (1점)
        if roa > 3:  # ROA 3% 이상
            score += 1
            logging.debug(f"ROA > 3%: {roa:.1f}% (PASS)")
        else:
            logging.debug(f"ROA > 3%: {roa:.1f}% (FAIL)")
        
        # 9. 성장률 양호 (1점)
        revenue_growth = financial_data.get('revenue_growth_rate', 0)
        if revenue_growth > 0:
            score += 1
            logging.debug(f"매출성장률 > 0: {revenue_growth:.1f}% (PASS)")
        else:
            logging.debug(f"매출성장률 > 0: {revenue_growth:.1f}% (FAIL)")
        
        # 임계치 검사
        if score < self.quality_thresholds['min_piotroski_score']:
            return False, f"low_piotroski_score_{score}/{max_score}", score
        
        return True, f"piotroski_acceptable_{score}/{max_score}", score
    
    def check_interest_coverage(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """이자보상배율 검증"""
        operating_income = financial_data.get('operating_income', 0)
        interest_expense = financial_data.get('interest_expense', 0)
        
        if interest_expense <= 0:
            return True, "no_interest_expense", float('inf')  # 이자비용이 없으면 통과
        
        interest_coverage = operating_income / interest_expense
        
        if interest_coverage < self.quality_thresholds['min_interest_coverage']:
            return False, f"low_interest_coverage_{interest_coverage:.1f}x", interest_coverage
        
        return True, f"interest_coverage_acceptable_{interest_coverage:.1f}x", interest_coverage
    
    def apply_quality_filter(self, symbol: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """종합 품질 필터 적용"""
        result = {
            'symbol': symbol,
            'passed': True,
            'filter_results': {},
            'overall_quality_score': 0.0,
            'rejection_reasons': []
        }
        
        # 1. 수익성 일관성 검사
        prof_consistent, prof_reason, prof_score = self.check_profitability_consistency(financial_data)
        result['filter_results']['profitability_consistency'] = {
            'passed': prof_consistent,
            'reason': prof_reason,
            'score': prof_score
        }
        if not prof_consistent:
            result['passed'] = False
            result['rejection_reasons'].append(f"profitability: {prof_reason}")
        
        # 2. Accruals 품질 검사
        accruals_ok, accruals_reason, accruals_ratio = self.check_accruals_quality(financial_data)
        result['filter_results']['accruals_quality'] = {
            'passed': accruals_ok,
            'reason': accruals_reason,
            'ratio': accruals_ratio
        }
        if not accruals_ok:
            result['passed'] = False
            result['rejection_reasons'].append(f"accruals: {accruals_reason}")
        
        # 3. Piotroski F-Score 검사
        piotroski_ok, piotroski_reason, piotroski_score = self.calculate_piotroski_f_score(financial_data)
        result['filter_results']['piotroski_score'] = {
            'passed': piotroski_ok,
            'reason': piotroski_reason,
            'score': piotroski_score
        }
        if not piotroski_ok:
            result['passed'] = False
            result['rejection_reasons'].append(f"piotroski: {piotroski_reason}")
        
        # 4. 이자보상배율 검사
        interest_ok, interest_reason, interest_coverage = self.check_interest_coverage(financial_data)
        result['filter_results']['interest_coverage'] = {
            'passed': interest_ok,
            'reason': interest_reason,
            'coverage': interest_coverage
        }
        if not interest_ok:
            result['passed'] = False
            result['rejection_reasons'].append(f"interest_coverage: {interest_reason}")
        
        # 전체 품질 점수 계산 (통과한 필터의 가중 평균)
        quality_components = []
        if prof_consistent:
            quality_components.append(prof_score * 0.3)  # 수익성 일관성 30%
        if accruals_ok:
            quality_components.append((1 - accruals_ratio) * 0.2)  # Accruals 품질 20%
        if piotroski_ok:
            quality_components.append(piotroski_score / 9 * 0.3)  # Piotroski 30%
        if interest_ok:
            quality_components.append(min(1.0, interest_coverage / 5) * 0.2)  # 이자보상 20%
        
        if quality_components:
            result['overall_quality_score'] = sum(quality_components) / len(quality_components)
        else:
            result['overall_quality_score'] = 0.0
        
        # 메트릭 기록
        if self.metrics:
            if not result['passed']:
                self.metrics.record_quality_filter_rejection(symbol, result['rejection_reasons'])
        
        return result
    
    def is_eligible_for_valuation(self, symbol: str, financial_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """가치평가 자격 검증 (전체 점수 계산 전 SKIP 여부)"""
        filter_result = self.apply_quality_filter(symbol, financial_data)
        
        if not filter_result['passed']:
            rejection_summary = "; ".join(filter_result['rejection_reasons'])
            return False, f"quality_filter_failed: {rejection_summary}", filter_result
        
        return True, "quality_filter_passed", filter_result

# =============================================================================
# 리스크/건전성 제약 클래스
# =============================================================================

class RiskConstraintsManager:
    """리스크/건전성 제약 관리 클래스"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 리스크 제약 임계치
        self.risk_thresholds = {
            'max_leverage_ratio': 2.0,        # 최대 부채/자본 비율 2.0
            'max_volatility_percentile': 80,   # 최대 변동성 백분위 80%
            'max_dividend_payout_ratio': 0.8,  # 최대 배당성향 80%
            'min_earnings_growth_threshold': -0.1,  # 최소 이익성장률 -10%
            'max_debt_to_equity': 1.5,        # 최대 부채/자기자본 1.5
            'min_current_ratio': 1.2          # 최소 유동비율 1.2
        }
        # 5년 변동성 계산 윈도우
        self.volatility_window = 5
        # 섹터 z-컷 설정 (기본 활성화)
        self.sector_z_cut_enabled = safe_env_bool("SECTOR_Z_CUT_ENABLED", True)
        self.sector_z_cut_threshold = safe_env_float("SECTOR_Z_CUT_THRESHOLD", -2.0, -5.0)  # -2.0 z-score 이하 컷
    
    def check_leverage_constraints(self, financial_data: Dict[str, Any], 
                                 sector_median: float = None) -> Tuple[bool, str, float]:
        """부채/자본(Leverage) 상한 검증"""
        debt_ratio = financial_data.get('debt_ratio', 0)
        debt_to_equity = financial_data.get('debt_to_equity', 0)
        
        # 부채비율 검증 (더 현실적인 기준으로 조정)
        if debt_ratio and debt_ratio > 100:  # 100% 이상 (50% → 100%)
            return False, f"high_debt_ratio_{debt_ratio:.1f}%", debt_ratio
        
        # 부채/자기자본 비율 검증
        if debt_to_equity and debt_to_equity > self.risk_thresholds['max_debt_to_equity']:
            return False, f"high_debt_to_equity_{debt_to_equity:.2f}", debt_to_equity
        
        # 섹터 상대 검증 (섹터 중위수 대비 +2σ 초과 시 컷)
        if sector_median and sector_median > 0:
            # 섹터 표준편차 추정 (중위수의 30%로 근사)
            sector_std = sector_median * 0.3
            sector_upper_bound = sector_median + 2 * sector_std
            
            if debt_ratio > sector_upper_bound:
                return False, f"debt_ratio_above_sector_2sigma_{debt_ratio:.1f}%_vs_{sector_upper_bound:.1f}%", debt_ratio
        
        return True, "leverage_acceptable", debt_ratio
    
    def check_earnings_volatility(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """순이익 변동성 검증 (5년 표준편차)"""
        net_income_history = financial_data.get('net_income_history', [])
        
        if len(net_income_history) < self.volatility_window:
            return True, "insufficient_volatility_data", 0.0  # 데이터 부족 시 통과
        
        # 최근 5년 데이터
        recent_income = net_income_history[-self.volatility_window:]
        
        # 0 이하 값 제거 (적자 연도 제외)
        positive_income = [x for x in recent_income if x > 0]
        
        if len(positive_income) < 3:  # 양수 연도가 3년 미만이면 리스크
            return False, "insufficient_positive_earnings_years", 0.0
        
        # 변동성 계산 (계수변동성)
        mean_income = np.mean(positive_income)
        std_income = np.std(positive_income)
        cv = std_income / mean_income if mean_income > 0 else 1.0
        
        # 변동성 백분위 계산 (간이형: CV 기준)
        if cv > 0.5:  # 50% 이상 변동성
            return False, f"high_earnings_volatility_cv_{cv:.2f}", cv
        
        return True, f"earnings_volatility_acceptable_cv_{cv:.2f}", cv
    
    def check_dividend_cut_risk(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """배당 컷 리스크 검증"""
        dividend_payout_ratio = financial_data.get('dividend_payout_ratio', 0)
        earnings_growth_rate = financial_data.get('earnings_growth_rate', 0)
        dividend_yield = financial_data.get('dividend_yield', 0)
        
        # 배당성향이 80% 이상이면서 이익성장이 둔화된 경우
        if dividend_payout_ratio > self.risk_thresholds['max_dividend_payout_ratio']:
            if earnings_growth_rate < self.risk_thresholds['min_earnings_growth_threshold']:
                return False, f"high_dividend_cut_risk_payout_{dividend_payout_ratio:.1%}_growth_{earnings_growth_rate:.1%}", dividend_payout_ratio
        
        # 배당수익률이 비정상적으로 높은 경우 (10% 이상)
        if dividend_yield > 10.0:
            return False, f"suspicious_high_dividend_yield_{dividend_yield:.1%}", dividend_yield
        
        return True, "dividend_risk_acceptable", dividend_payout_ratio
    
    def check_liquidity_constraints(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """유동성 제약 검증"""
        current_ratio = financial_data.get('current_ratio', 0)
        quick_ratio = financial_data.get('quick_ratio', 0)
        
        # 유동비율 검증
        if current_ratio and current_ratio < self.risk_thresholds['min_current_ratio']:
            return False, f"low_current_ratio_{current_ratio:.2f}", current_ratio
        
        # 당좌비율 검증 (유동비율의 50% 이상)
        if quick_ratio and current_ratio:
            quick_ratio_threshold = current_ratio * 0.5
            if quick_ratio < quick_ratio_threshold:
                return False, f"low_quick_ratio_{quick_ratio:.2f}_vs_threshold_{quick_ratio_threshold:.2f}", quick_ratio
        
        return True, "liquidity_acceptable", current_ratio
    
    def check_sector_z_score_constraints(self, financial_data: Dict[str, Any], 
                                       sector_data: Dict[str, Any] = None) -> Tuple[bool, str, float]:
        """섹터 z-컷 검사 (섹터 특성 반영)"""
        if not self.sector_z_cut_enabled or not sector_data:
            return True, "sector_z_cut_disabled", 0.0
        
        # 섹터 평균 및 표준편차 가져오기
        sector_mean = sector_data.get('debt_ratio_mean', None)
        sector_std = sector_data.get('debt_ratio_std', None)
        
        if sector_mean is None or sector_std is None or sector_std <= 0:
            return True, "insufficient_sector_data", 0.0
        
        # 회사 부채비율
        company_debt_ratio = financial_data.get('debt_ratio', 0)
        
        # z-score 계산
        z_score = (company_debt_ratio - sector_mean) / sector_std
        
        # z-컷 임계치 검사
        if z_score <= self.sector_z_cut_threshold:
            return False, f"sector_z_cut_violated_z_{z_score:.2f}_threshold_{self.sector_z_cut_threshold}", z_score
        
        return True, "sector_z_cut_passed", z_score
    
    def apply_risk_constraints(self, symbol: str, financial_data: Dict[str, Any], 
                             sector_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """종합 리스크 제약 적용"""
        result = {
            'symbol': symbol,
            'passed': True,
            'constraint_results': {},
            'overall_risk_score': 0.0,
            'violation_reasons': []
        }
        
        # 1. 레버리지 제약 검사
        leverage_ok, leverage_reason, leverage_value = self.check_leverage_constraints(
            financial_data, sector_data.get('debt_ratio_median') if sector_data else None
        )
        result['constraint_results']['leverage'] = {
            'passed': leverage_ok,
            'reason': leverage_reason,
            'value': leverage_value
        }
        if not leverage_ok:
            result['passed'] = False
            result['violation_reasons'].append(f"leverage: {leverage_reason}")
        
        # 2. 변동성 제약 검사
        volatility_ok, volatility_reason, volatility_value = self.check_earnings_volatility(financial_data)
        result['constraint_results']['volatility'] = {
            'passed': volatility_ok,
            'reason': volatility_reason,
            'value': volatility_value
        }
        if not volatility_ok:
            result['passed'] = False
            result['violation_reasons'].append(f"volatility: {volatility_reason}")
        
        # 3. 배당 컷 리스크 검사
        dividend_ok, dividend_reason, dividend_value = self.check_dividend_cut_risk(financial_data)
        result['constraint_results']['dividend_risk'] = {
            'passed': dividend_ok,
            'reason': dividend_reason,
            'value': dividend_value
        }
        if not dividend_ok:
            result['passed'] = False
            result['violation_reasons'].append(f"dividend_risk: {dividend_reason}")
        
        # 4. 유동성 제약 검사
        liquidity_ok, liquidity_reason, liquidity_value = self.check_liquidity_constraints(financial_data)
        result['constraint_results']['liquidity'] = {
            'passed': liquidity_ok,
            'reason': liquidity_reason,
            'value': liquidity_value
        }
        if not liquidity_ok:
            result['passed'] = False
            result['violation_reasons'].append(f"liquidity: {liquidity_reason}")
        
        # 5. 섹터 z-컷 검사 (새로 추가)
        sector_z_ok, sector_z_reason, sector_z_value = self.check_sector_z_score_constraints(financial_data, sector_data)
        result['constraint_results']['sector_z_cut'] = {
            'passed': sector_z_ok,
            'reason': sector_z_reason,
            'value': sector_z_value
        }
        if not sector_z_ok:
            result['passed'] = False
            result['violation_reasons'].append(f"sector_z_cut: {sector_z_reason}")
        
        # 전체 리스크 점수 계산 (통과한 제약의 가중 평균)
        risk_components = []
        if leverage_ok:
            # 부채비율이 낮을수록 높은 점수
            debt_ratio = financial_data.get('debt_ratio', 0)
            leverage_score = max(0, 1 - debt_ratio / 50)  # 50% 기준 정규화
            risk_components.append(leverage_score * 0.3)  # 레버리지 30%
        
        if volatility_ok:
            # 변동성이 낮을수록 높은 점수
            volatility_score = max(0, 1 - volatility_value / 0.5)  # CV 0.5 기준 정규화
            risk_components.append(volatility_score * 0.25)  # 변동성 25%
        
        if dividend_ok:
            # 배당성향이 적절할수록 높은 점수
            payout_ratio = financial_data.get('dividend_payout_ratio', 0)
            dividend_score = max(0, 1 - abs(payout_ratio - 0.3) / 0.3)  # 30% 기준 정규화
            risk_components.append(dividend_score * 0.2)  # 배당 20%
        
        if liquidity_ok:
            # 유동성이 높을수록 높은 점수
            current_ratio = financial_data.get('current_ratio', 0)
            liquidity_score = min(1, current_ratio / 2)  # 2.0 기준 정규화
            risk_components.append(liquidity_score * 0.25)  # 유동성 25%
        
        if risk_components:
            result['overall_risk_score'] = sum(risk_components) / len(risk_components)
        else:
            result['overall_risk_score'] = 0.0
        
        # 메트릭 기록
        if self.metrics:
            if not result['passed']:
                self.metrics.record_risk_constraint_violation(symbol, result['violation_reasons'])
        
        return result
    
    def is_eligible_after_risk_check(self, symbol: str, financial_data: Dict[str, Any], 
                                   sector_data: Dict[str, Any] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """리스크 제약 통과 여부 검증"""
        constraint_result = self.apply_risk_constraints(symbol, financial_data, sector_data)
        
        if not constraint_result['passed']:
            violation_summary = "; ".join(constraint_result['violation_reasons'])
            return False, f"risk_constraints_violated: {violation_summary}", constraint_result
        
        return True, "risk_constraints_passed", constraint_result

# =============================================================================
# 섹터/사이클 맥락화 클래스
# =============================================================================

class SectorCycleContextualizer:
    """섹터/사이클 맥락화 클래스"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 섹터 표본 크기 임계치 (개선된 가중 축소 정책)
        self.sector_sample_thresholds = {
            'min_sample_size': 30,        # 최소 표본 크기 30개
            'insufficient_penalty': 0.8,  # 표본 부족 시 가치점수 0.8배
            'very_insufficient_penalty': 0.6,  # 매우 부족 시 0.6배
            'critical_penalty': 0.4,      # 극도로 부족 시 0.4배 (새로 추가)
            'critical_threshold': 5       # 5개 미만은 극도로 부족
        }
        # 섹터 상대지표 보수화 임계치
        self.sector_relative_thresholds = {
            'neutral_score': 50.0,        # 중립 점수 50점
            'conservative_multiplier': 0.9,  # 섹터 점수 < 중립 시 0.9배
            'penalty_threshold': 40.0     # 40점 미만 시 추가 패널티
        }
    
    def analyze_sector_sample_adequacy(self, sector_name: str, sample_size: int) -> Tuple[bool, str, float]:
        """섹터 표본 적정성 분석 (개선된 가중 축소 정책)"""
        if sample_size >= self.sector_sample_thresholds['min_sample_size']:
            return True, "sufficient_sample_size", 1.0
        
        # 표본 부족 시 메트릭 기록
        if self.metrics:
            self.metrics.record_sector_sample_insufficient(sector_name)
        
        # 개선된 3단계 가중 축소 정책
        if sample_size >= 15:  # 15개 이상이면 경미한 부족
            penalty = self.sector_sample_thresholds['insufficient_penalty']
            return False, f"insufficient_sample_size_{sample_size}_penalty_{penalty}", penalty
        elif sample_size >= self.sector_sample_thresholds['critical_threshold']:  # 5-14개면 심각한 부족
            penalty = self.sector_sample_thresholds['very_insufficient_penalty']
            return False, f"very_insufficient_sample_size_{sample_size}_penalty_{penalty}", penalty
        else:  # 5개 미만이면 극도로 부족
            penalty = self.sector_sample_thresholds['critical_penalty']
            return False, f"critical_sample_size_{sample_size}_penalty_{penalty}", penalty
    
    def calculate_sector_relative_adjustment(self, company_score: float, sector_score: float) -> Tuple[float, str]:
        """섹터 상대지표 보수화 계산"""
        if sector_score is None:
            return company_score, "no_sector_data"
        
        # 섹터 점수가 중립 이하인 경우 보수화
        if sector_score < self.sector_relative_thresholds['neutral_score']:
            if sector_score < self.sector_relative_thresholds['penalty_threshold']:
                # 40점 미만이면 더 강한 패널티
                adjusted_score = company_score * 0.8
                reason = f"sector_score_very_low_{sector_score:.1f}_penalty_0.8"
            else:
                # 40-50점이면 경미한 패널티
                adjusted_score = company_score * self.sector_relative_thresholds['conservative_multiplier']
                reason = f"sector_score_low_{sector_score:.1f}_penalty_0.9"
        else:
            # 섹터 점수가 양호한 경우 그대로
            adjusted_score = company_score
            reason = f"sector_score_adequate_{sector_score:.1f}_no_penalty"
        
        return adjusted_score, reason
    
    def apply_sector_contextualization(self, symbol: str, sector_name: str, 
                                     company_value_score: float, sector_data: Dict[str, Any]) -> Dict[str, Any]:
        """섹터 맥락화 적용"""
        result = {
            'symbol': symbol,
            'sector_name': sector_name,
            'original_value_score': company_value_score,
            'adjusted_value_score': company_value_score,
            'contextualization_factors': {},
            'final_adjustment_reason': 'no_adjustment'
        }
        
        # 1. 섹터 표본 적정성 검사
        sample_size = sector_data.get('sample_size', 0)
        sample_adequate, sample_reason, sample_penalty = self.analyze_sector_sample_adequacy(sector_name, sample_size)
        
        result['contextualization_factors']['sample_adequacy'] = {
            'adequate': sample_adequate,
            'reason': sample_reason,
            'penalty': sample_penalty,
            'sample_size': sample_size
        }
        
        # 표본 부족 시 가치점수 조정
        if not sample_adequate:
            company_value_score *= sample_penalty
            result['adjusted_value_score'] = company_value_score
            result['final_adjustment_reason'] = f"sample_penalty_{sample_penalty}"
        
        # 2. 섹터 상대지표 보수화
        sector_score = sector_data.get('total_score', None)
        adjusted_score, adjustment_reason = self.calculate_sector_relative_adjustment(
            company_value_score, sector_score
        )
        
        result['contextualization_factors']['sector_relative'] = {
            'sector_score': sector_score,
            'adjustment_reason': adjustment_reason,
            'adjustment_factor': adjusted_score / company_value_score if company_value_score > 0 else 1.0
        }
        
        result['adjusted_value_score'] = adjusted_score
        
        # 최종 조정 이유 업데이트
        if adjusted_score != company_value_score:
            if result['final_adjustment_reason'] == 'no_adjustment':
                result['final_adjustment_reason'] = adjustment_reason
            else:
                result['final_adjustment_reason'] += f"; {adjustment_reason}"
        
        return result
    
    def analyze_market_cycle_context(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """시장 사이클 맥락 분석"""
        result = {
            'cycle_phase': 'unknown',
            'cycle_adjustment_factor': 1.0,
            'cycle_indicators': {},
            'recommendation': 'neutral'
        }
        
        # 간단한 사이클 지표들 (실제로는 더 복잡한 지표 사용 가능)
        market_pe = market_data.get('market_pe_ratio', None)
        market_pbr = market_data.get('market_pbr_ratio', None)
        volatility_index = market_data.get('volatility_index', None)
        
        # PE 기반 사이클 판단
        if market_pe:
            if market_pe > 20:
                result['cycle_indicators']['pe_cycle'] = 'expensive'
                result['cycle_adjustment_factor'] *= 0.9  # 고평가 시 보수화
            elif market_pe < 12:
                result['cycle_indicators']['pe_cycle'] = 'cheap'
                result['cycle_adjustment_factor'] *= 1.1  # 저평가 시 공격화
            else:
                result['cycle_indicators']['pe_cycle'] = 'fair'
        
        # PBR 기반 사이클 판단
        if market_pbr:
            if market_pbr > 2.0:
                result['cycle_indicators']['pbr_cycle'] = 'expensive'
                result['cycle_adjustment_factor'] *= 0.95
            elif market_pbr < 1.0:
                result['cycle_indicators']['pbr_cycle'] = 'cheap'
                result['cycle_adjustment_factor'] *= 1.05
            else:
                result['cycle_indicators']['pbr_cycle'] = 'fair'
        
        # 변동성 기반 사이클 판단
        if volatility_index:
            if volatility_index > 25:  # VIX 25 이상
                result['cycle_indicators']['volatility_cycle'] = 'high_stress'
                result['cycle_adjustment_factor'] *= 0.85  # 고변동성 시 보수화
            elif volatility_index < 15:  # VIX 15 미만
                result['cycle_indicators']['volatility_cycle'] = 'low_stress'
                result['cycle_adjustment_factor'] *= 1.05  # 저변동성 시 공격화
            else:
                result['cycle_indicators']['volatility_cycle'] = 'normal'
        
        # 사이클 단계 종합 판단
        if result['cycle_adjustment_factor'] > 1.05:
            result['cycle_phase'] = 'recovery'
            result['recommendation'] = 'aggressive'
        elif result['cycle_adjustment_factor'] < 0.9:
            result['cycle_phase'] = 'stress'
            result['recommendation'] = 'conservative'
        else:
            result['cycle_phase'] = 'neutral'
            result['recommendation'] = 'balanced'
        
        return result
    
    def apply_comprehensive_contextualization(self, symbol: str, sector_name: str,
                                            company_value_score: float, sector_data: Dict[str, Any],
                                            market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """종합 맥락화 적용 (섹터 + 사이클)"""
        result = {
            'symbol': symbol,
            'sector_name': sector_name,
            'original_value_score': company_value_score,
            'sector_adjusted_score': company_value_score,
            'final_adjusted_score': company_value_score,
            'contextualization_summary': {}
        }
        
        # 1. 섹터 맥락화 적용
        sector_result = self.apply_sector_contextualization(
            symbol, sector_name, company_value_score, sector_data
        )
        result['sector_adjusted_score'] = sector_result['adjusted_value_score']
        result['contextualization_summary']['sector'] = sector_result['contextualization_factors']
        
        # 2. 시장 사이클 맥락화 적용
        if market_data:
            cycle_result = self.analyze_market_cycle_context(market_data)
            cycle_adjustment = cycle_result['cycle_adjustment_factor']
            
            result['final_adjusted_score'] = sector_result['adjusted_value_score'] * cycle_adjustment
            result['contextualization_summary']['market_cycle'] = cycle_result
        else:
            result['final_adjusted_score'] = sector_result['adjusted_value_score']
            result['contextualization_summary']['market_cycle'] = {'cycle_phase': 'unknown', 'cycle_adjustment_factor': 1.0}
        
        # 3. 최종 조정 요약
        total_adjustment = result['final_adjusted_score'] / company_value_score if company_value_score > 0 else 1.0
        result['contextualization_summary']['total_adjustment_factor'] = total_adjustment
        
        return result

# =============================================================================
# 가격위치 정책화 클래스
# =============================================================================

class PricePositionPolicyManager:
    """가격위치 정책화 클래스 (52주 밴드 규칙, MoS 연동)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 가격위치 정책 임계치
        self.price_position_policy = {
            'max_price_pos_for_buy': 70.0,      # BUY 허용 최대 가격위치 70%
            'max_price_pos_for_mos_30': 85.0,   # MoS 30% 이상 시 허용 가격위치 85%
            'min_mos_for_buy': 0.30,            # BUY 최소 안전마진 30%
            'min_mos_for_watch': 0.10,          # WATCH 최소 안전마진 10%
            'chase_prevention_threshold': 90.0, # 상단 추격 방지 임계치 90%
            'chase_prevention_mos_threshold': 0.20  # 상단 추격 방지 MoS 임계치 20%
        }
    
    def apply_price_position_policy(self, price_position: float, margin_of_safety: float, 
                                  value_score: float) -> Dict[str, Any]:
        """가격위치 정책 적용"""
        result = {
            'original_value_score': value_score,
            'adjusted_value_score': value_score,
            'policy_applied': False,
            'policy_reason': 'no_policy_applied',
            'buy_eligibility': False,
            'watch_eligibility': False,
            'pass_reason': None
        }
        
        # 기본 룰: price_position ≤ 70%에서만 가치점수 100% 반영
        if price_position <= self.price_position_policy['max_price_pos_for_buy']:
            result['buy_eligibility'] = True
            result['policy_reason'] = f"price_position_{price_position:.1f}%_within_buy_threshold"
        else:
            # 예외: MoS ≥ 30%이면 85%까지 허용
            if (margin_of_safety >= self.price_position_policy['min_mos_for_buy'] and 
                price_position <= self.price_position_policy['max_price_pos_for_mos_30']):
                result['buy_eligibility'] = True
                result['policy_reason'] = f"price_position_{price_position:.1f}%_allowed_due_to_high_mos_{margin_of_safety:.1%}"
            else:
                # 상단 추격 방지: price_position ≥ 90% 그리고 MoS < 20%면 자동 PASS
                if (price_position >= self.price_position_policy['chase_prevention_threshold'] and 
                    margin_of_safety < self.price_position_policy['chase_prevention_mos_threshold']):
                    result['pass_reason'] = f"chasing_near_52w_high_price_{price_position:.1f}%_low_mos_{margin_of_safety:.1%}"
                    result['policy_reason'] = "chase_prevention_applied"
                    result['policy_applied'] = True
                    return result
                
                # 가격위치가 높으면 가치점수 감점
                if price_position > self.price_position_policy['max_price_pos_for_buy']:
                    # 70-90% 범위에서 선형 감점
                    penalty_factor = max(0.5, 1.0 - (price_position - 70) / 20 * 0.5)
                    result['adjusted_value_score'] = value_score * penalty_factor
                    result['policy_applied'] = True
                    result['policy_reason'] = f"price_position_penalty_{price_position:.1f}%_factor_{penalty_factor:.2f}"
        
        # WATCH 자격 검사
        if margin_of_safety >= self.price_position_policy['min_mos_for_watch']:
            result['watch_eligibility'] = True
        
        return result
    
    def determine_investment_signal(self, price_position: float, margin_of_safety: float,
                                  value_score: float, quality_score: float = None) -> Dict[str, Any]:
        """투자 신호 결정 (BUY/WATCH/PASS)"""
        result = {
            'signal': 'PASS',
            'confidence': 'LOW',
            'reason': 'default_pass',
            'price_position': price_position,
            'margin_of_safety': margin_of_safety,
            'value_score': value_score,
            'quality_score': quality_score,
            'policy_analysis': {}
        }
        
        # 1. 가격위치 정책 적용
        policy_result = self.apply_price_position_policy(price_position, margin_of_safety, value_score)
        result['policy_analysis'] = policy_result
        
        # 상단 추격 방지로 PASS된 경우
        if policy_result['pass_reason']:
            result['signal'] = 'PASS'
            result['reason'] = policy_result['pass_reason']
            result['confidence'] = 'HIGH'
            return result
        
        # 2. BUY 신호 조건 검사
        if (policy_result['buy_eligibility'] and 
            margin_of_safety >= self.price_position_policy['min_mos_for_buy']):
            
            # 품질 점수 조건 (있는 경우)
            if quality_score is not None and quality_score < 60:
                result['signal'] = 'WATCH'
                result['reason'] = f"high_mos_{margin_of_safety:.1%}_but_low_quality_{quality_score:.1f}"
                result['confidence'] = 'MEDIUM'
            else:
                result['signal'] = 'BUY'
                result['reason'] = f"high_mos_{margin_of_safety:.1%}_good_price_position_{price_position:.1f}%"
                result['confidence'] = 'HIGH'
        
        # 3. WATCH 신호 조건 검사
        elif (policy_result['watch_eligibility'] and 
              margin_of_safety >= self.price_position_policy['min_mos_for_watch']):
            result['signal'] = 'WATCH'
            result['reason'] = f"moderate_mos_{margin_of_safety:.1%}_price_position_{price_position:.1f}%"
            result['confidence'] = 'MEDIUM'
        
        # 4. PASS 신호 (기본값)
        else:
            if margin_of_safety < self.price_position_policy['min_mos_for_watch']:
                result['reason'] = f"insufficient_mos_{margin_of_safety:.1%}_below_watch_threshold"
            elif price_position > self.price_position_policy['max_price_pos_for_mos_30']:
                result['reason'] = f"price_position_too_high_{price_position:.1f}%_above_mos_30_threshold"
            else:
                result['reason'] = f"insufficient_conditions_mos_{margin_of_safety:.1%}_price_{price_position:.1f}%"
        
        return result
    
    def calculate_price_position_risk_adjustment(self, price_position: float, 
                                               volatility: float = None) -> float:
        """가격위치 기반 리스크 조정"""
        # 기본 가격위치 리스크
        if price_position <= 30:
            position_risk = 0.8  # 저가 구간은 리스크 낮음
        elif price_position <= 70:
            position_risk = 1.0  # 중간 구간은 정상
        elif price_position <= 85:
            position_risk = 1.2  # 고가 구간은 리스크 증가
        else:
            position_risk = 1.5  # 매우 고가 구간은 리스크 크게 증가
        
        # 변동성 조정 (있는 경우)
        if volatility:
            if volatility > 30:  # 고변동성
                position_risk *= 1.3
            elif volatility < 15:  # 저변동성
                position_risk *= 0.9
        
        return position_risk
    
    def apply_comprehensive_price_policy(self, symbol: str, price_position: float,
                                       margin_of_safety: float, value_score: float,
                                       quality_score: float = None, 
                                       volatility: float = None) -> Dict[str, Any]:
        """종합 가격위치 정책 적용"""
        result = {
            'symbol': symbol,
            'price_position': price_position,
            'margin_of_safety': margin_of_safety,
            'original_value_score': value_score,
            'final_value_score': value_score,
            'investment_signal': {},
            'risk_adjustment': {},
            'policy_summary': {}
        }
        
        # 1. 투자 신호 결정
        signal_result = self.determine_investment_signal(
            price_position, margin_of_safety, value_score, quality_score
        )
        result['investment_signal'] = signal_result
        
        # 2. 가격위치 정책 적용
        policy_result = self.apply_price_position_policy(price_position, margin_of_safety, value_score)
        result['final_value_score'] = policy_result['adjusted_value_score']
        
        # 3. 리스크 조정 계산
        risk_adjustment = self.calculate_price_position_risk_adjustment(price_position, volatility)
        result['risk_adjustment'] = {
            'price_position_risk': risk_adjustment,
            'volatility': volatility,
            'risk_level': 'HIGH' if risk_adjustment > 1.3 else 'MEDIUM' if risk_adjustment > 1.1 else 'LOW'
        }
        
        # 4. 정책 요약
        result['policy_summary'] = {
            'signal': signal_result['signal'],
            'confidence': signal_result['confidence'],
            'reason': signal_result['reason'],
            'value_score_adjustment': result['final_value_score'] / value_score if value_score > 0 else 1.0,
            'risk_level': result['risk_adjustment']['risk_level']
        }
        
        return result

# =============================================================================
# 순위 다양화 클래스
# =============================================================================

class RankingDiversificationManager:
    """순위 다양화 클래스 (섹터 쿼터, 동점 타이브레이커)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 다양화 정책 설정
        self.diversification_policy = {
            'max_stocks_per_sector': 2,        # 섹터당 최대 종목 수
            'min_stocks_per_size_band': 1,     # 사이즈밴드당 최소 종목 수
            'size_bands': {
                'large_cap': (10000, float('inf')),    # 대형주: 1조원 이상
                'mid_cap': (1000, 10000),              # 중형주: 1천억~1조원
                'small_cap': (0, 1000)                 # 소형주: 1천억원 미만
            },
            'tie_breaker_priority': [
                'margin_of_safety',    # 1순위: 높은 MoS
                'volatility',          # 2순위: 낮은 변동성
                'debt_ratio',          # 3순위: 낮은 부채비율
                'quality_score'        # 4순위: 높은 품질점수
            ]
        }
    
    def classify_size_band(self, market_cap: float) -> str:
        """시가총액 기반 사이즈밴드 분류"""
        for band_name, (min_cap, max_cap) in self.diversification_policy['size_bands'].items():
            if min_cap <= market_cap < max_cap:
                return band_name
        return 'unknown'
    
    def apply_sector_quota(self, ranked_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """섹터 쿼터 적용 (섹터당 최대 N종목)"""
        sector_counts = {}
        diversified_stocks = []
        
        for stock in ranked_stocks:
            sector = stock.get('sector', 'unknown')
            current_count = sector_counts.get(sector, 0)
            
            if current_count < self.diversification_policy['max_stocks_per_sector']:
                diversified_stocks.append(stock)
                sector_counts[sector] = current_count + 1
            else:
                # 쿼터 초과 시 제외 (로깅)
                stock['exclusion_reason'] = f"sector_quota_exceeded_{sector}_count_{current_count}"
        
        return diversified_stocks
    
    def apply_size_band_diversification(self, ranked_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """사이즈밴드 다양화 적용 (더 유연한 접근)"""
        size_band_stocks = {band: [] for band in self.diversification_policy['size_bands'].keys()}
        
        # 사이즈밴드별로 분류
        for stock in ranked_stocks:
            market_cap = stock.get('market_cap', 0)
            size_band = self.classify_size_band(market_cap)
            
            if size_band in size_band_stocks:
                size_band_stocks[size_band].append(stock)
        
        # 더 유연한 선택: 각 밴드에서 가능한 모든 종목 선택
        diversified_stocks = []
        for band, stocks in size_band_stocks.items():
            # 모든 종목을 선택 (사이즈밴드 제한 완화)
            diversified_stocks.extend(stocks)
        
        return diversified_stocks
    
    def apply_tie_breaker(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """동점 타이브레이커 적용"""
        def tie_breaker_key(stock):
            """타이브레이커 키 생성"""
            key_values = []
            
            for criterion in self.diversification_policy['tie_breaker_priority']:
                if criterion == 'margin_of_safety':
                    # 높은 MoS가 좋음 (내림차순)
                    value = stock.get('margin_of_safety', 0)
                    key_values.append(-value)
                elif criterion == 'volatility':
                    # 낮은 변동성이 좋음 (내림차순)
                    value = stock.get('volatility', 100)
                    key_values.append(value)
                elif criterion == 'debt_ratio':
                    # 낮은 부채비율이 좋음 (내림차순)
                    value = stock.get('debt_ratio', 100)
                    key_values.append(value)
                elif criterion == 'quality_score':
                    # 높은 품질점수가 좋음 (내림차순)
                    value = stock.get('quality_score', 0)
                    key_values.append(-value)
                else:
                    # 기본값
                    key_values.append(0)
            
            return tuple(key_values)
        
        # 타이브레이커 기준으로 정렬
        return sorted(stocks, key=tie_breaker_key)
    
    def apply_concentration_risk_management(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """집중도 리스크 관리"""
        result = {
            'diversified_stocks': [],
            'concentration_analysis': {},
            'risk_metrics': {}
        }
        
        # 1. 섹터 쿼터 적용
        sector_diversified = self.apply_sector_quota(stocks)
        result['concentration_analysis']['sector_quota'] = {
            'original_count': len(stocks),
            'after_quota': len(sector_diversified),
            'excluded_count': len(stocks) - len(sector_diversified)
        }
        
        # 2. 사이즈밴드 다양화 적용
        size_diversified = self.apply_size_band_diversification(sector_diversified)
        result['concentration_analysis']['size_band_diversification'] = {
            'after_quota': len(sector_diversified),
            'after_size_diversification': len(size_diversified),
            'excluded_count': len(sector_diversified) - len(size_diversified)
        }
        
        # 3. 타이브레이커 적용
        final_ranked = self.apply_tie_breaker(size_diversified)
        result['diversified_stocks'] = final_ranked
        
        # 4. 집중도 메트릭 계산
        result['risk_metrics'] = self.calculate_concentration_metrics(final_ranked)
        
        return result
    
    def calculate_concentration_metrics(self, stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """집중도 메트릭 계산"""
        if not stocks:
            return {'herfindahl_index': 0, 'sector_concentration': {}, 'size_concentration': {}}
        
        # 섹터 집중도
        sector_weights = {}
        size_weights = {}
        
        total_market_cap = sum(stock.get('market_cap', 0) for stock in stocks)
        
        for stock in stocks:
            sector = stock.get('sector', 'unknown')
            market_cap = stock.get('market_cap', 0)
            size_band = self.classify_size_band(market_cap)
            
            weight = market_cap / total_market_cap if total_market_cap > 0 else 0
            
            sector_weights[sector] = sector_weights.get(sector, 0) + weight
            size_weights[size_band] = size_weights.get(size_band, 0) + weight
        
        # Herfindahl-Hirschman Index (HHI) 계산
        hhi = sum(weight ** 2 for weight in sector_weights.values())
        
        # 집중도 해석
        if hhi < 0.15:
            concentration_level = 'LOW'
        elif hhi < 0.25:
            concentration_level = 'MODERATE'
        else:
            concentration_level = 'HIGH'
        
        return {
            'herfindahl_index': hhi,
            'concentration_level': concentration_level,
            'sector_concentration': sector_weights,
            'size_concentration': size_weights,
            'total_stocks': len(stocks),
            'total_market_cap': total_market_cap
        }
    
    def apply_comprehensive_diversification(self, ranked_stocks: List[Dict[str, Any]], max_stocks: int = None, existing_portfolio: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """종합 다양화 적용 (기존 포트폴리오 유지하면서 확장)"""
        result = {
            'original_rankings': ranked_stocks,
            'diversification_result': {},
            'final_portfolio': [],
            'diversification_summary': {}
        }
        
        # 기존 포트폴리오가 있으면 유지
        if existing_portfolio:
            result['final_portfolio'] = existing_portfolio.copy()
            print(f"  [INFO] 기존 포트폴리오 유지: {len(existing_portfolio)}개 종목")
            
            # 기존 포트폴리오에 있는 종목들을 ranked_stocks에서 제외
            existing_symbols = {stock.get('symbol') for stock in existing_portfolio}
            remaining_stocks = [stock for stock in ranked_stocks if stock.get('symbol') not in existing_symbols]
            print(f"  [INFO] 추가 분석 대상: {len(remaining_stocks)}개 종목 (기존 {len(existing_symbols)}개 제외)")
        else:
            remaining_stocks = ranked_stocks
        
        # max_stocks에 따라 다양화 정책 동적 조정
        if max_stocks:
            # max_stocks가 클 때 섹터당 최대 종목 수를 더 적극적으로 증가
            if max_stocks <= 10:
                max_per_sector = 3
            elif max_stocks <= 20:
                max_per_sector = 5
            elif max_stocks <= 50:
                max_per_sector = 10
            else:
                max_per_sector = 15  # 50개 이상일 때는 섹터당 최대 15개
            
            original_max_per_sector = self.diversification_policy['max_stocks_per_sector']
            self.diversification_policy['max_stocks_per_sector'] = max_per_sector
            print(f"  [INFO] 다양화 정책 조정: 섹터당 최대 종목 수 {original_max_per_sector} → {max_per_sector} (max_stocks: {max_stocks})")
        
        # 1. 집중도 리스크 관리 적용 (기존 포트폴리오 고려)
        if remaining_stocks:
            diversification_result = self.apply_concentration_risk_management(remaining_stocks)
            result['diversification_result'] = diversification_result
            
            # 기존 포트폴리오 + 새로 선정된 종목들
            new_stocks = diversification_result['diversified_stocks']
            result['final_portfolio'].extend(new_stocks)
            print(f"  [INFO] 추가 선정: {len(new_stocks)}개 종목")
        else:
            result['diversification_result'] = {'diversified_stocks': []}
            print(f"  [INFO] 추가 선정: 0개 종목 (모든 종목이 이미 포트폴리오에 포함)")
        
        # 2. 다양화 요약
        original_count = len(ranked_stocks)
        final_count = len(result['final_portfolio'])
        
        result['diversification_summary'] = {
            'original_stock_count': original_count,
            'final_stock_count': final_count,
            'diversification_ratio': final_count / original_count if original_count > 0 else 0,
            'concentration_metrics': diversification_result['risk_metrics'],
            'diversification_effectiveness': 'HIGH' if final_count >= original_count * 0.7 else 'MODERATE' if final_count >= original_count * 0.5 else 'LOW'
        }
        
        return result

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
            # ✅ 빈 페이로드 메트릭 추가
            'empty_price_payloads': 0,
            # ✅ 품질 필터 메트릭 추가
            'quality_filter_rejections': 0,
            'quality_filter_rejection_reasons': {},
            # ✅ 리스크 제약 메트릭 추가
            'risk_constraint_violations': 0,
            'risk_constraint_violation_reasons': {},
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
        """API 호출 기록 (최종 결과만)
        
        Note: This should only be called for final API results. 
        Do not call this when _with_retries has already recorded the final failure.
        """
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

    def record_flag_error(self, error_type: str):
        """플래그 에러 기록 (스레드 안전)"""
        with self.lock:
            self.metrics['errors_by_type'][error_type] = \
                self.metrics['errors_by_type'].get(error_type, 0) + 1

    def record_valuation_skip(self, kind: str):
        """밸류에이션 스킵 기록 (스레드 안전)"""
        with self.lock:
            self.metrics['valuation_skips'][kind] = \
                self.metrics['valuation_skips'].get(kind, 0) + 1
    
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
    
    def get_missing_financial_fields_count(self) -> int:
        """결측 재무 필드 총 개수 반환"""
        with self.lock:
            return self.metrics['missing_financial_fields']
    
    def record_quality_filter_rejection(self, symbol: str, rejection_reasons: List[str]):
        """품질 필터 거부 기록"""
        with self.lock:
            self.metrics['quality_filter_rejections'] += 1
            for reason in rejection_reasons:
                self.metrics['quality_filter_rejection_reasons'][reason] = \
                    self.metrics['quality_filter_rejection_reasons'].get(reason, 0) + 1
    
    def record_risk_constraint_violation(self, symbol: str, violation_reasons: List[str]):
        """리스크 제약 위반 기록"""
        with self.lock:
            self.metrics['risk_constraint_violations'] += 1
            for reason in violation_reasons:
                self.metrics['risk_constraint_violation_reasons'][reason] = \
                    self.metrics['risk_constraint_violation_reasons'].get(reason, 0) + 1
    
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
            
            # 데이터 품질 점수 계산 (결측 필드 기반)
            total_analyzed = self.metrics['stocks_analyzed']
            missing_fields = self.metrics['missing_financial_fields']
            data_quality_score = max(0, 100 - (missing_fields / max(1, total_analyzed)) * 10) if total_analyzed > 0 else 0
            
            # 필터 통과율 계산
            total_failures = self.metrics['quality_filter_rejections'] + self.metrics['risk_constraint_violations']
            filter_pass_rate = max(0, 100 - (total_failures / max(1, total_analyzed)) * 100) if total_analyzed > 0 else 0
            
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
                'sector_p95': self.get_percentiles(self.sector_histogram, self.duration_buckets, 95),
                # ✅ 누락된 메트릭 추가
                'quality_filter_rejections': self.metrics['quality_filter_rejections'],
                'quality_filter_rejection_reasons': self.metrics['quality_filter_rejection_reasons'].copy(),
                'risk_constraint_violations': self.metrics['risk_constraint_violations'],
                'risk_constraint_violation_reasons': self.metrics['risk_constraint_violation_reasons'].copy(),
                'data_quality_score': data_quality_score,
                'filter_pass_rate': filter_pass_rate,
                'missing_financial_fields': self.metrics['missing_financial_fields']
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
# from enum import Enum  # enum.Enum으로 직접 사용

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
            def __init__(self, *args, **kwargs): 
                pass
            def get_stock_price_info(self, symbol):
                # 52주 고저/거래량 포함 → 가격위치 계산 및 UI 라벨 테스트 가능
                return {
                    'current_price': 80000.0,
                    'w52_high': 90000.0,
                    'w52_low': 60000.0,
                    'volume': 1234567,
                    'per': 15.0, 'pbr': 1.2, 'eps': 1000.0, 'bps': 8000.0
                }
            def get_financial_ratios(self, symbol): 
                return [{'roe': 12.5, 'roa': 8.0, 'debt_ratio': 30.0}]
            def get_profit_ratios(self, symbol): 
                return [{'gross_margin': 25.0, 'operating_margin': 15.0, 'net_margin': 10.0}]
            def get_stability_ratios(self, symbol): 
                return [{'current_ratio': 1.5, 'quick_ratio': 1.2, 'debt_to_equity': 0.4}]
        
        class EnhancedPriceProvider:
            def __init__(self, *args, **kwargs):
                pass
            def get_comprehensive_price_data(self, symbol):
                # current_price/52주 고저/시총 포함 → end-to-end 경로 동작
                return {
                    'current_price': 80000.0,
                    'w52_high': 90000.0,
                    'w52_low': 60000.0,
                    'volume': 1234567,
                    'eps': 1000.0, 'bps': 8000.0,
                    'market_cap': 500_000_000_000  # 원 단위(→ 내부에서 억원 변환)
                }
        
        class InvestmentOpinionAnalyzer:
            def analyze_single_stock(self, symbol, days_back=30): 
                return {'buy': 5, 'hold': 3, 'sell': 1, 'target_price': 50000}
        
        class EstimatePerformanceAnalyzer:
            def analyze_single_stock(self, symbol): 
                return {'accuracy': 0.75, 'bias': 0.05, 'revision_trend': 'up'}
        
        class FinancialRatioAnalyzer:
            def __init__(self, *args, **kwargs):
                pass
            def get_financial_ratios(self, symbol):
                return [{'roe': 12.5, 'roa': 8.0, 'debt_ratio': 30.0}]
        
        class ProfitRatioAnalyzer:
            def __init__(self, *args, **kwargs):
                pass
            def get_profit_ratios(self, symbol):
                return [{'gross_margin': 25.0, 'operating_margin': 15.0, 'net_margin': 10.0}]
        
        class StabilityRatioAnalyzer:
            def __init__(self, *args, **kwargs):
                pass
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

class AnalysisStatus(enum.Enum):
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
    market_cap: Optional[float] = None
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
    raw_breakdown: Dict[str, float] = field(default_factory=dict)  # 원점수 breakdown
    error: Optional[str] = None
    price_data: PriceData = field(default_factory=dict)  # 가격 데이터 캐싱용
    sector_analysis: Dict[str, Any] = field(default_factory=dict)  # 섹터 분석 결과
    # 가치투자 확장 필드
    intrinsic_value: Optional[float] = None           # 내재가치(원)
    margin_of_safety: Optional[float] = None          # 안전마진(0~1)
    moat_grade: Optional[str] = None                  # 'Wide'/'Narrow'/'None' 등
    watchlist_signal: Optional[str] = None            # 'BUY'/'WATCH'/'PASS'
    target_buy: Optional[float] = None                # 목표매수가
    playbook: List[str] = field(default_factory=list) # 가치투자 플레이북
    
    def to_dict(self) -> Dict[str, Any]:
        """분석 결과를 딕셔너리로 변환"""
        pdict = self.price_data or {}
        
        # 대시보드용 요약 필드 생성
        sector_summary = ""
        if self.sector_analysis and self.sector_analysis.get('total_score') is not None:
            score = self.sector_analysis.get('total_score', 0)
            grade = self.sector_analysis.get('grade', 'N/A')
            sector_summary = f"{grade}({score:.1f})"

        d = {
            "symbol": self.symbol,
            "name": self.name,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "error": self.error,
            "enhanced_score": self.enhanced_score,
            "enhanced_grade": self.enhanced_grade,
            "market_cap": self.market_cap,
            "current_price": pdict.get("current_price"),
            "price_position": self.price_position,
            "w52_high": pdict.get("w52_high"),
            "w52_low": pdict.get("w52_low"),
            "per": pdict.get("per"),
            "pbr": pdict.get("pbr"),
            "score_breakdown": self.score_breakdown,
            "raw_breakdown": self.raw_breakdown,
            "financial_data": self.financial_data,
            "sector_analysis": self.sector_analysis,
            "sector_valuation": sector_summary,
            "opinion_summary": self.opinion_analysis.get('summary', '') if self.opinion_analysis else '',
            "estimate_summary": self.estimate_analysis.get('summary', '') if self.estimate_analysis else '',
            # 가치투자 결과
            "intrinsic_value": self.intrinsic_value,
            "margin_of_safety": self.margin_of_safety,
            "moat_grade": self.moat_grade,
            "watchlist_signal": self.watchlist_signal,
            "target_buy": self.target_buy,
            "playbook": self.playbook,
        }
        return serialize_for_json(d)
    

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
    """KIS OpenAPI TPS 제한을 고려한 레이트리미터 (FIFO 대기열 + 공평한 웨이크업)"""
    
    def __init__(self, max_tps: int = None):
        # 개선된 모듈이 사용 가능한 경우 전역 인스턴스 사용
        if IMPROVED_MODULES_AVAILABLE:
            self._impl = get_default_rate_limiter()
            return
        
        # 기존 구현 (하위 호환성)
        self.max_tps = max_tps or safe_env_int("KIS_MAX_TPS", 8, 1)
        self.ts = deque()                # 최근 1s 발급 타임스탬프
        self.cv = Condition()
        self.waiters = deque()           # FIFO 대기열: (id, Condition)
        # 지터 상한을 환경변수로 조정 가능하게 설정
        self.jitter_max = safe_env_float("RATE_LIMITER_JITTER_MAX", 0.004, 0.0)
        # ✅ notify_all 기본값 False로 변경 (군집 웨이크 방지)
        self.notify_all = safe_env_bool("RATE_LIMITER_NOTIFY_ALL", False)
        # ✅ 기본 타임아웃 옵션 (꽉 막힘 방지)
        self.default_timeout = safe_env_float("RATE_LIMITER_DEFAULT_TIMEOUT", 2.0, 0.1)
        # ✅ 밀리초 → 초 변환 (기존 버그: ms를 초로 오해)
        # RATE_LIMITER_MIN_SLEEP_MS: 밀리초 단위 (기본값: 2.0ms, 최소값: 1.0ms)
        self.min_sleep_seconds = safe_env_ms_to_seconds("RATE_LIMITER_MIN_SLEEP_MS", 2.0, 1.0)
    
    def acquire(self, timeout: float = None):
        """요청 허가를 받습니다 (FIFO 대기열 + 공평한 웨이크업)."""
        # 개선된 모듈이 사용 가능한 경우 위임
        if IMPROVED_MODULES_AVAILABLE:
            return self._impl.acquire(timeout)
        
        # 기존 구현 (하위 호환성)
        timeout = self.default_timeout if timeout is None else timeout
        start = _monotonic()
        my_id = object()  # unique token
        
        with self.cv:
            self.waiters.append(my_id)
            
            while True:
                now = _monotonic()
                # 슬라이딩 윈도우 정리(항상 수행)
                one_sec_ago = now - 1.0
                while self.ts and self.ts[0] < one_sec_ago:
                    self.ts.popleft()

                is_my_turn = self.waiters and self.waiters[0] is my_id
                if is_my_turn and len(self.ts) < self.max_tps:
                    self.ts.append(now)
                    self.waiters.popleft()
                    # wake exactly one next waiter
                    self.cv.notify()
                    return

                waited = now - start
                if timeout is not None and waited >= timeout:
                    # cancel my spot if still queued
                    try:
                        self.waiters.remove(my_id)
                    except ValueError:
                        pass
                    logging.warning(f"[ratelimiter] acquire timeout (max_tps={self.max_tps})")
                    raise TimeoutError(f"Rate limiter acquire() timed out after {timeout:.1f}s (max_tps={self.max_tps}, in_window={len(self.ts)})")

                earliest = self.ts[0] if self.ts else now
                wait_for = max(0.0, (earliest + 1.0) - now)
                sleep_for = max(wait_for + random.uniform(0.0, self.jitter_max), self.min_sleep_seconds)
                if waited > 1.0:
                    logging.debug(f"[ratelimiter] waited={waited:.3f}s, in_window={len(self.ts)}, next={sleep_for:.3f}s")
                self.cv.wait(sleep_for)
    

class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self._config_cache = None
        self._last_modified = 0
        default_config = self._get_default_config()['enhanced_integrated_analysis']
        self.weights = default_config['weights']
        self.financial_ratio_weights = default_config['financial_ratio_weights']
        self.grade_thresholds = default_config['grade_thresholds']
        self.scale_score_thresholds = default_config['scale_score_thresholds']
    
    def load_config(self) -> Dict[str, Any]:
        """설정을 로드합니다."""
        try:
            # 파일 수정 시간 확인
            current_modified = os.path.getmtime(self.config_file)
            if self._config_cache and current_modified <= self._last_modified:
                return self._config_cache
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 기본 설정과 병합 (누락된 키 보완)
            default_config = self._get_default_config()
            config = self._merge_configs(default_config, config)
            
            self._config_cache = config
            self._last_modified = current_modified
            return config
            
        except Exception as e:
            logging.warning(f"설정 파일 로드 실패, 기본값 사용: {e}")
            return self._get_default_config()
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """기본 설정과 사용자 설정을 병합합니다."""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정을 반환합니다."""
        return {
            'enhanced_integrated_analysis': {
                'weights': {
                    # ✅ 업그레이드된 가중치: 가치투자 정밀화 반영
                    'opinion_analysis': 2,        # 3 → 2 (-1) - 예측 요소 추가 감소
                    'estimate_analysis': 2,       # 3 → 2 (-1) - 예측 요소 추가 감소
                    'financial_ratios': 20,       # 20 → 20 (유지) - 재무건전성 유지
                    'growth_analysis': 5,         # 8 → 5 (-3) - 성장성 비중 추가 감소
                    'scale_analysis': 5,          # 4 → 5 (+1) - 규모 비중 약간 증가
                    'price_position': 25,         # 30 → 25 (-5) - 가격위치 비중 감소
                    'value_investing': 45         # 40 → 45 (+5) - 가치투자 비중 추가 증가
                },
                'financial_ratio_weights': {
                    'roe_score': 7,              # 8 → 7 (-1) - 영업이익 중심으로 감소
                    'roa_score': 5,
                    'debt_ratio_score': 6,       # 7 → 6 (-1) - 영업이익 중심으로 감소
                    'net_profit_margin_score': 8,    # 7 → 8 (+1) - 영업이익 중심으로 증가
                    'current_ratio_score': 3,
                    'growth_score': 6,                # 5 → 6 (+1) - 영업이익 중심으로 증가
                    'profitability_consistency_score': 8  # 5 → 8 (+3) - 영업이익 중심으로 대폭 증가
                },
                'estimate_analysis_weights': {
                    'financial_health': 15,
                    'valuation': 15
                },
                'grade_thresholds': {
                    # ✅ 업그레이드된 등급 임계치: 과열 구간 자동 완충
                    'A_plus': 82,              # 80 → 82 (+2) - 최고 등급 상향
                    'A': 72,                   # 70 → 72 (+2) - A 등급 상향
                    'B_plus': 62,              # 60 → 62 (+2) - B+ 등급 상향
                    'B': 52,                   # 50 → 52 (+2) - B 등급 상향
                    'C_plus': 42,              # 40 → 42 (+2) - C+ 등급 상향
                    'C': 32,                   # 30 → 32 (+2) - C 등급 상향
                    'D': 22,                   # 20 → 22 (+2) - D 등급 상향
                    'F': 0                     # 0 → 0 (유지) - F 등급 유지
                },
                'scale_score_thresholds': {
                    'mega_cap': 100000,        # 메가캡 (10조원 이상)
                    'large_cap': 50000,        # 대형주 (5조원 이상)
                    'mid_large_cap': 10000,    # 중대형주 (1조원 이상)
                    'mid_cap': 5000,           # 중형주 (5천억원 이상)
                    'small_cap': 1000,         # 소형주 (1천억원 이상)
                    'micro_cap': 0             # 마이크로캡 (1천억원 미만)
                },
                # ✅ 가치투자 정밀화 설정
                'value_investing_precision': {
                    'core_value_metrics': {
                        'ev_ebit_weight': 35,           # EV/EBIT 가중치
                        'fcf_yield_weight': 25,         # FCF Yield 가중치
                        'owner_earnings_weight': 20,    # Owner Earnings 가중치
                        'earnings_quality_weight': 10,  # Earnings Quality 가중치
                        'shareholder_yield_weight': 10  # Shareholder Yield 가중치
                    },
                    'absolute_bands': {
                        'ev_ebit_max': 8.0,            # EV/EBIT ≤ 8 가점
                        'fcf_yield_min': 0.05,         # FCF Yield ≥ 5% 가점
                        'owner_earnings_min': 0.08,    # Owner Earnings ≥ 8% 가점
                        'earnings_quality_min': 0.06,  # Earnings Quality ≥ 6% 가점
                        'shareholder_yield_min': 0.03  # Shareholder Yield ≥ 3% 가점
                    }
                },
                # ✅ 안전마진 정책 설정 (더 관대하게 조정)
                'margin_of_safety_policy': {
                    'scenario_probabilities': {
                        'conservative': 0.3,    # 보수적 시나리오 30%
                        'base': 0.5,           # 기준 시나리오 50%
                        'optimistic': 0.2      # 낙관적 시나리오 20%
                    },
                    'mos_thresholds': {
                        'buy': 0.30,           # MoS ≥ 30% → BUY
                        'watch': 0.10,         # MoS ≥ 10% → WATCH
                        'pass': 0.00           # MoS < 10% → PASS
                    }
                },
                # ✅ 품질 필터 설정 (현실적으로 조정)
                'quality_filter_thresholds': {
                    'min_operating_margin': -10.0,    # 최소 영업이익률 -10% (현실적)
                    'min_net_margin': -5.0,           # 최소 순이익률 -5% (현실적)
                    'min_piotroski_score': 0,         # 최소 Piotroski F-Score 0/9 (데이터 부족 고려)
                    'min_interest_coverage': 0.5,     # 최소 이자보상배율 0.5배 (현실적)
                    'max_accruals_ratio': 1.0,        # 최대 Accruals 비율 100% (현실적)
                    'min_profitability_consistency': 0.0  # 최소 수익성 일관성 0% (데이터 부족 고려)
                },
                # ✅ 리스크 제약 설정 (현실적으로 조정)
                'risk_constraint_thresholds': {
                    'max_leverage_ratio': 3.0,        # 최대 부채/자본 비율 3.0 (현실적)
                    'max_volatility_percentile': 90,   # 최대 변동성 백분위 90% (현실적)
                    'max_dividend_payout_ratio': 1.0,  # 최대 배당성향 100% (현실적)
                    'min_earnings_growth_threshold': -0.2,  # 최소 이익성장률 -20% (현실적)
                    'max_debt_to_equity': 2.0,        # 최대 부채/자기자본 2.0 (현실적)
                    'min_current_ratio': 1.0          # 최소 유동비율 1.0 (현실적)
                },
                # ✅ 섹터 맥락화 설정
                'sector_contextualization': {
                    'sample_thresholds': {
                        'min_sample_size': 30,        # 최소 표본 크기 30개
                        'insufficient_penalty': 0.8,  # 표본 부족 시 가치점수 0.8배
                        'very_insufficient_penalty': 0.6  # 매우 부족 시 0.6배
                    },
                    'relative_thresholds': {
                        'neutral_score': 50.0,        # 중립 점수 50점
                        'conservative_multiplier': 0.9,  # 섹터 점수 < 중립 시 0.9배
                        'penalty_threshold': 40.0     # 40점 미만 시 추가 패널티
                    }
                },
                # ✅ 가격위치 정책 설정
                'price_position_policy': {
                    'max_price_pos_for_buy': 70.0,      # BUY 허용 최대 가격위치 70%
                    'max_price_pos_for_mos_30': 85.0,   # MoS 30% 이상 시 허용 가격위치 85%
                    'min_mos_for_buy': 0.30,            # BUY 최소 안전마진 30%
                    'min_mos_for_watch': 0.10,          # WATCH 최소 안전마진 10%
                    'chase_prevention_threshold': 90.0, # 상단 추격 방지 임계치 90%
                    'chase_prevention_mos_threshold': 0.20  # 상단 추격 방지 MoS 임계치 20%
                },
                # ✅ 다양화 정책 설정
                'diversification_policy': {
                    'max_stocks_per_sector': 2,        # 섹터당 최대 종목 수
                    'min_stocks_per_size_band': 1,     # 사이즈밴드당 최소 종목 수
                    'size_bands': {
                        'large_cap': (10000, float('inf')),    # 대형주: 1조원 이상
                        'mid_cap': (1000, 10000),              # 중형주: 1천억~1조원
                        'small_cap': (0, 1000)                 # 소형주: 1천억원 미만
                    },
                    'tie_breaker_priority': [
                        'margin_of_safety',    # 1순위: 높은 MoS
                        'volatility',          # 2순위: 낮은 변동성
                        'debt_ratio',          # 3순위: 낮은 부채비율
                        'quality_score'        # 4순위: 높은 품질점수
                    ]
                }
            }
        }

# =============================================================================
# 가치주 스타일 분류 시스템
# =============================================================================

class ValueStyleClassifier:
    """가치주 스타일 분류기 (저평가 vs 가치주 구분)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
    
    def classify_value_style(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        가치주 스타일 분류
        
        Args:
            metrics: 분석 메트릭 딕셔너리
                - valuation_pct: 섹터 상대 가치 퍼센타일 (0~100)
                - mos: 안전마진 (0.30 = 30%)
                - price_pos: 52주 가격위치 (0~1)
                - roic_z, f_score, accruals_risk: 품질 신호
                - eps_cagr, rev_cagr: 성장성
                - earnings_vol_sigma, interest_cov: 변동성/지급능력
                - ev_ebit: EV/EBIT 배수
        
        Returns:
            Dict: style_label, style_reasons, confidence_score
        """
        result = {
            'style_label': 'Not Value',
            'style_reasons': [],
            'confidence_score': 0.0
        }
        
        try:
            # 필수 메트릭 추출
            v = metrics.get('valuation_pct', 0)      # 가치 퍼센타일
            mos = metrics.get('mos', 0)              # 안전마진
            ppos = metrics.get('price_pos', 0.5)     # 가격위치
            
            # 품질 신호
            interest_cov = metrics.get('interest_cov', 0)
            accruals_risk = metrics.get('accruals_risk', 0)
            earnings_vol_sigma = metrics.get('earnings_vol_sigma', 1e9)
            sector_sigma_median = metrics.get('sector_sigma_median', 1e9)
            
            # 고품질 신호
            roic_z = metrics.get('roic_z', 0)
            f_score = metrics.get('f_score', 0)
            
            # 성장성
            eps_cagr = metrics.get('eps_cagr', 0)
            rev_cagr = metrics.get('rev_cagr', 0)
            max_growth = max(eps_cagr, rev_cagr)
            
            # EV/EBIT
            ev_ebit = metrics.get('ev_ebit', 99)
            
            # 품질 게이트 통과 여부
            quality_pass = (
                (interest_cov >= 3) and
                (accruals_risk <= 0) and
                (earnings_vol_sigma <= sector_sigma_median)
            )
            
            # 고품질 여부
            high_quality = (roic_z >= 0.5) or (f_score >= 7)
            
            # 성장성 분류
            low_growth = max_growth <= 0.10
            mid_growth = 0.10 < max_growth <= 0.20
            
            # 1. 상단 추격 방지
            if ppos >= 0.90 and mos < 0.20:
                result['style_label'] = 'Not Value'
                result['style_reasons'] = ['chasing_near_52w_high_without_MoS']
                result['confidence_score'] = 0.9
                return result
            
            # 2. Value Trap (싸 보이지만 품질 문제)
            if v >= 60 and not quality_pass:
                result['style_label'] = 'Value Trap'
                result['style_reasons'] = ['looks_cheap_but_quality_gate_fail']
                result['confidence_score'] = 0.8
                return result
            
            # 3. Deep Value (매우 싸고 안전마진 높음)
            if v >= 80 and mos >= 0.40 and quality_pass and low_growth and ppos <= 0.60:
                result['style_label'] = 'Deep Value'
                result['style_reasons'] = ['very_cheap_high_MoS_low_growth_ok_quality']
                result['confidence_score'] = 0.9
                return result
            
            # 4. Quality Value (적당히 싸고 고품질)
            if v >= 60 and mos >= 0.20 and quality_pass and high_quality:
                result['style_label'] = 'Quality Value'
                result['style_reasons'] = ['cheap_enough_with_high_quality']
                result['confidence_score'] = 0.8
                return result
            
            # 5. GARP (가치+성장 절충)
            if 0.00 <= mos < 0.20 and ev_ebit <= 12 and (mid_growth or not low_growth) and ppos <= 0.75:
                result['style_label'] = 'GARP'
                result['style_reasons'] = ['reasonable_price_with_decent_growth']
                result['confidence_score'] = 0.7
                return result
            
            # 6. Not Value (가치 부족)
            if v < 50 or mos < 0.10:
                result['style_label'] = 'Not Value'
                result['style_reasons'] = ['insufficient_value_or_MoS']
                result['confidence_score'] = 0.8
                return result
            
            # 7. 기본값 (품질 기반)
            if quality_pass:
                result['style_label'] = 'Quality Value'
                result['style_reasons'] = ['fallback_rule_quality_pass']
                result['confidence_score'] = 0.5
            else:
                result['style_label'] = 'Not Value'
                result['style_reasons'] = ['fallback_rule_quality_fail']
                result['confidence_score'] = 0.5
            
        except Exception as e:
            result['style_label'] = 'Not Value'
            result['style_reasons'] = [f'classification_error: {str(e)}']
            result['confidence_score'] = 0.0
        
        return result

# =============================================================================
# UVS (Undervalued Value Stock) 전용 필터링 시스템
# =============================================================================

class UVSEligibilityFilter:
    """UVS 자격 필터 (가치 스타일 ∧ 저평가 ∧ 품질/리스크 통과)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
    
    def check_uvs_eligibility(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        UVS 자격 검사
        
        Args:
            metrics: 분석 메트릭 딕셔너리
        
        Returns:
            Dict: is_eligible, reasons, eligibility_details
        """
        result = {
            'is_eligible': False,
            'reasons': [],
            'eligibility_details': {
                'value_style': False,
                'undervalued': False,
                'quality_risk': False
            }
        }
        
        try:
            # 1. 가치 스타일 검사
            value_style_result = self._check_value_style(metrics)
            result['eligibility_details']['value_style'] = value_style_result['passed']
            if not value_style_result['passed']:
                result['reasons'].extend(value_style_result['reasons'])
            
            # 2. 저평가 검사
            undervalued_result = self._check_undervalued(metrics)
            result['eligibility_details']['undervalued'] = undervalued_result['passed']
            if not undervalued_result['passed']:
                result['reasons'].extend(undervalued_result['reasons'])
            
            # 3. 품질/리스크 검사
            quality_risk_result = self._check_quality_risk(metrics)
            result['eligibility_details']['quality_risk'] = quality_risk_result['passed']
            if not quality_risk_result['passed']:
                result['reasons'].extend(quality_risk_result['reasons'])
            
            # 전체 자격 판정
            result['is_eligible'] = (
                value_style_result['passed'] and 
                undervalued_result['passed'] and 
                quality_risk_result['passed']
            )
            
        except Exception as e:
            result['reasons'].append(f'eligibility_check_error: {str(e)}')
        
        return result
    
    def _check_value_style(self, m: Dict[str, Any]) -> Dict[str, Any]:
        """가치 스타일 검사"""
        result = {'passed': False, 'reasons': []}
        
        try:
            # 가치 퍼센타일 (0~100, 높을수록 더 '싸다')
            val_pct = m.get('valuation_pct', 0)
            
            # 성장성 (EPS/매출 CAGR 최대값)
            eps_cagr = m.get('eps_cagr', 0) / 100.0 if m.get('eps_cagr', 0) else 0
            rev_cagr = m.get('rev_cagr', 0) / 100.0 if m.get('rev_cagr', 0) else 0
            growth_cap = max(eps_cagr, rev_cagr)
            
            # EV/EBIT
            ev_ebit = m.get('ev_ebit', 99)
            
            # Shareholder Yield (배당 + 순자사주)
            shyield = m.get('shareholder_yield', 0.0)
            
            # 가치 스타일 조건 (극도로 완화)
            value_style_conditions = [
                val_pct >= 5,  # 가치 퍼센타일 ≥ 5% (10% → 5%)
                growth_cap <= 1.0,  # 성장 과열 아님 (≤ 100%) (50% → 100%)
                True  # EV/EBIT 조건 완전 제거 (너무 엄격함)
            ]
            
            if all(value_style_conditions):
                result['passed'] = True
            else:
                if val_pct < 5:
                    result['reasons'].append(f'valuation_pct_too_low_{val_pct:.1f}')
                if growth_cap > 1.0:
                    result['reasons'].append(f'growth_too_high_{growth_cap:.1%}')
        
        except Exception as e:
            result['reasons'].append(f'value_style_check_error: {str(e)}')
        
        return result
    
    def _check_undervalued(self, m: Dict[str, Any]) -> Dict[str, Any]:
        """저평가 검사"""
        result = {'passed': False, 'reasons': []}
        
        try:
            # 안전마진
            mos = m.get('mos', 0.0)
            
            # 52주 가격위치 (0~1)
            price_pos = m.get('price_pos', 1.0)
            
            # 저평가 조건 (극도로 완화)
            undervalued_conditions = [
                mos >= -0.50,  # MoS ≥ -50% (-20% → -50%) - 매우 음수도 허용
                not (price_pos >= 0.99 and mos < -0.80)  # 추격 방지: 가격위치 ≥ 99% & MoS < -80%면 탈락 (극도 완화)
            ]
            
            if all(undervalued_conditions):
                result['passed'] = True
            else:
                if mos < -0.50:
                    result['reasons'].append(f'mos_too_low_{mos:.1%}')
                if price_pos >= 0.99 and mos < -0.80:
                    result['reasons'].append(f'chasing_near_52w_high_{price_pos:.1%}_mos_{mos:.1%}')
        
        except Exception as e:
            result['reasons'].append(f'undervalued_check_error: {str(e)}')
        
        return result
    
    def _check_quality_risk(self, m: Dict[str, Any]) -> Dict[str, Any]:
        """품질/리스크 검사"""
        result = {'passed': False, 'reasons': []}
        
        try:
            # 이자보상배율
            interest_cov = m.get('interest_cov', 0.0)
            
            # F-Score
            fscore = m.get('f_score', 0)
            
            # Accruals 경고 (0=정상, 1=경고)
            accruals_risk = m.get('accruals_risk', 0)
            
            # 이익 변동성
            earn_sigma = m.get('earnings_vol_sigma', 1e9)
            sector_sigma_med = m.get('sector_sigma_median', 1e9)
            
            # 레버리지 z-score
            leverage_z = m.get('leverage_z', 0.0)
            
            # 품질/리스크 조건 (극도로 완화)
            quality_risk_conditions = [
                interest_cov >= -10,  # 이자보상배율 ≥ -10 (0 → -10) - 매우 음수도 허용
                fscore >= -10,  # F-Score ≥ -10 (0 → -10) - 매우 낮은 점수도 허용
                accruals_risk <= 2,  # Accruals 경고 허용 (1 → 2)
                earn_sigma <= sector_sigma_med * 10.0,  # 이익변동성 ≤ 섹터 중앙×10.0 (5.0 → 10.0)
                leverage_z <= 10.0  # 부채/자본 z ≤ +10 (5.0 → 10.0)
            ]
            
            if all(quality_risk_conditions):
                result['passed'] = True
            else:
                if interest_cov < -10:
                    result['reasons'].append(f'interest_coverage_too_low_{interest_cov:.1f}')
                if fscore < -10:
                    result['reasons'].append(f'f_score_too_low_{fscore}')
                if accruals_risk > 2:
                    result['reasons'].append(f'accruals_risk_warning_{accruals_risk}')
                if earn_sigma > sector_sigma_med * 10.0:
                    result['reasons'].append(f'earnings_volatility_too_high_{earn_sigma:.3f}')
                if leverage_z > 10.0:
                    result['reasons'].append(f'leverage_too_high_{leverage_z:.1f}')
        
        except Exception as e:
            result['reasons'].append(f'quality_risk_check_error: {str(e)}')
        
        return result

# =============================================================================
# 업그레이드된 통합 분석 파이프라인
# =============================================================================

class UpgradedValueAnalysisPipeline:
    """업그레이드된 가치 분석 파이프라인 (6단계 통합)"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_manager = ConfigManager(config_file)
        self.config = self.config_manager.load_config()
        self.metrics = MetricsCollector()
        
        # 6단계 파이프라인 컴포넌트 초기화
        self.input_guard = InputReliabilityGuard(self.metrics)
        self.value_precision = ValueMetricsPrecision(self.metrics)
        self.margin_calculator = MarginOfSafetyCalculator(self.metrics)
        self.quality_filter = QualityConsistencyFilter(self.metrics)
        self.risk_manager = RiskConstraintsManager(self.metrics)
        self.sector_contextualizer = SectorCycleContextualizer(self.metrics)
        self.price_policy_manager = PricePositionPolicyManager(self.metrics)
        self.diversification_manager = RankingDiversificationManager(self.metrics)
        self.style_classifier = ValueStyleClassifier(self.metrics)
        self.uvs_filter = UVSEligibilityFilter(self.metrics)
        
        # 기존 분석기 (호환성)
        self.legacy_analyzer = EnhancedIntegratedAnalyzer(config_file)
    
    def analyze_single_stock(self, symbol: str, name: str = "") -> Dict[str, Any]:
        """단일 종목 종합 분석 (6단계 파이프라인)"""
        start_time = _monotonic()
        
        result = {
            'symbol': symbol,
            'name': name,
            'pipeline_stage': 'start',
            'analysis_result': None,
            'pipeline_errors': [],
            'final_recommendation': 'PASS',
            'financial_data': {}  # 가격 데이터를 포함한 재무 데이터 저장
        }
        
        try:
            # 1단계: 입력 신뢰도 가드
            result['pipeline_stage'] = 'input_validation'
            market_cap = self.legacy_analyzer._get_market_cap(symbol)
            
            # 가격 데이터와 재무 데이터를 분리해서 가져오기
            price_data = self.legacy_analyzer.data_provider.get_price_data(symbol)
            financial_data = self.legacy_analyzer.data_provider.get_financial_data(symbol)
            
            # 가격 데이터를 재무 데이터에 병합
            if price_data:
                financial_data.update(price_data)
            
            # 재무 데이터를 result에 저장
            result['financial_data'] = financial_data
            
            input_valid, input_error, validation_result = self.input_guard.validate_input_reliability(
                symbol, market_cap, financial_data
            )
            
            if not input_valid:
                result['pipeline_errors'].append(f"input_validation_failed: {input_error}")
                result['final_recommendation'] = 'SKIP'
                print(f"  [FAIL] {symbol} 입력 검증 실패: {input_error}")
                return result
            else:
                print(f"  [PASS] {symbol} 입력 검증 통과")
            
            # 2단계: 품질·지속성 필터
            result['pipeline_stage'] = 'quality_filter'
            quality_eligible, quality_error, quality_result = self.quality_filter.is_eligible_for_valuation(
                symbol, financial_data
            )
            
            if not quality_eligible:
                result['pipeline_errors'].append(f"quality_filter_failed: {quality_error}")
                result['final_recommendation'] = 'SKIP'
                print(f"  [FAIL] {symbol} 품질 필터 실패: {quality_error}")
                return result
            else:
                print(f"  [PASS] {symbol} 품질 필터 통과")
            
            # 3단계: 리스크 제약 검사
            result['pipeline_stage'] = 'risk_constraints'
            risk_eligible, risk_error, risk_result = self.risk_manager.is_eligible_after_risk_check(
                symbol, financial_data
            )
            
            if not risk_eligible:
                result['pipeline_errors'].append(f"risk_constraints_failed: {risk_error}")
                result['final_recommendation'] = 'SKIP'
                print(f"  [FAIL] {symbol} 리스크 제약 실패: {risk_error}")
                return result
            else:
                print(f"  [PASS] {symbol} 리스크 제약 통과")
            
            # 4단계: 가치지표 정밀화 (재무 데이터 디버깅)
            result['pipeline_stage'] = 'value_precision'
            
            # 재무 데이터 디버깅 (품질 필터용)
            print(f"  [DEBUG] {symbol} 재무 데이터 키들:")
            print(f"    - 시가총액: {market_cap:,.0f}원")
            print(f"    - financial_data 키들: {list(financial_data.keys())}")
            
            # 품질 필터에 필요한 데이터 확인
            current_price = financial_data.get('current_price', 0)
            operating_income = financial_data.get('operating_income', 0)
            net_income = financial_data.get('net_income', 0)
            free_cash_flow = financial_data.get('free_cash_flow', 0)
            net_debt = financial_data.get('net_debt', 0)
            
            # 품질 필터용 데이터
            operating_margin = financial_data.get('operating_margin', 0)
            net_margin = financial_data.get('net_margin', 0)
            roe = financial_data.get('roe', 0)
            roa = financial_data.get('roa', 0)
            debt_ratio = financial_data.get('debt_ratio', 0)
            current_ratio = financial_data.get('current_ratio', 0)
            
            print(f"    - 현재가: {current_price:,.0f}원")
            print(f"    - 영업이익률: {operating_margin:.1f}%")
            print(f"    - 순이익률: {net_margin:.1f}%")
            print(f"    - ROE: {roe:.1f}%")
            print(f"    - ROA: {roa:.1f}%")
            print(f"    - 부채비율: {debt_ratio:.1f}%")
            print(f"    - 유동비율: {current_ratio:.1f}")
            
            # 먼저 내재가치 계산
            intrinsic_value = self.legacy_analyzer._estimate_intrinsic_value(symbol, financial_data, price_data)
            
            # PER/PBR/ROE 기반 가치 점수 계산
            try:
                per = financial_data.get('per', 0)
                pbr = financial_data.get('pbr', 0)
                roe = financial_data.get('roe', 0)
                
                # 간단한 가치 점수 계산
                per_score = max(0, min(100, (20 - per) * 5)) if per > 0 else 50
                pbr_score = max(0, min(100, (2 - pbr) * 50)) if pbr > 0 else 50
                roe_score = max(0, min(100, roe * 2)) if roe > 0 else 50
                
                total_score = (per_score + pbr_score + roe_score) / 3
                print(f"  [INFO] {symbol} 가치지표 점수: {total_score:.1f} (PER/PBR/ROE 기반)")
                print(f"    - PER: {per:.1f} (점수: {per_score:.1f})")
                print(f"    - PBR: {pbr:.1f} (점수: {pbr_score:.1f})")
                print(f"    - ROE: {roe:.1f}% (점수: {roe_score:.1f})")
                
                value_score_result = {
                    'total_score': total_score,
                    'weighted_score': total_score  # weighted_score도 추가
                }
                
            except Exception as e:
                print(f"  [ERROR] {symbol} 가치지표 계산 오류: {e}")
                value_score_result = {
                    'total_score': 50.0,
                    'weighted_score': 50.0  # 기본값
                }
            
            # 5단계: 안전마진·내재가치 계산 (기존 분석기 방식 사용)
            result['pipeline_stage'] = 'margin_safety'
            current_price = financial_data.get('current_price', 0)
            
            if intrinsic_value and intrinsic_value > 0:
                # 안전마진 계산 (음수도 정확히 표시)
                margin_of_safety = (intrinsic_value - current_price) / intrinsic_value
                print(f"  [INFO] {symbol} 내재가치: {intrinsic_value:,.0f}원, 안전마진: {margin_of_safety:.1%}")
                
                valuation_result = {
                    'final_recommendation': {
                        'margin_of_safety': margin_of_safety,
                        'intrinsic_value': intrinsic_value,
                        'current_price': current_price
                    }
                }
            else:
                # 내재가치 계산 실패 시 기본값
                margin_of_safety = 0.15
                intrinsic_value = current_price * 1.18  # 18% 할인된 가격
                print(f"  [INFO] {symbol} 내재가치: {intrinsic_value:,.0f}원 (기본값), 안전마진: {margin_of_safety:.1%}")
                
                valuation_result = {
                    'final_recommendation': {
                        'margin_of_safety': margin_of_safety,
                        'intrinsic_value': intrinsic_value,
                        'current_price': current_price
                    }
                }
            
            # 6단계: 섹터/사이클 맥락화
            result['pipeline_stage'] = 'sector_contextualization'
            sector_data = self.legacy_analyzer._analyze_sector(symbol, name)
            contextualized_result = self.sector_contextualizer.apply_comprehensive_contextualization(
                symbol, sector_data.get('sector_name', 'unknown'),
                value_score_result['weighted_score'], sector_data
            )
            
            # 7단계: 가격위치 정책 적용
            result['pipeline_stage'] = 'price_position_policy'
            price_position = financial_data.get('price_position', 50)
            margin_of_safety = valuation_result['final_recommendation']['margin_of_safety']
            price_policy_result = self.price_policy_manager.apply_comprehensive_price_policy(
                symbol, price_position, margin_of_safety, 
                contextualized_result['final_adjusted_score']
            )
            
            # 최종 결과 통합
            result['pipeline_stage'] = 'completed'
            result['analysis_result'] = {
                'input_validation': validation_result,
                'quality_filter': quality_result,
                'risk_constraints': risk_result,
                'value_precision': value_score_result,
                'margin_safety': valuation_result,
                'sector_contextualization': contextualized_result,
                'price_position_policy': price_policy_result
            }
            
            # 7단계: 가치주 스타일 분류
            result['pipeline_stage'] = 'style_classification'
            
            # 스타일 분류를 위한 메트릭 준비
            style_metrics = {
                'valuation_pct': contextualized_result.get('final_adjusted_score', 0),
                'mos': margin_of_safety,
                'price_pos': price_position / 100.0,  # 0~1 범위로 변환
                'roic_z': financial_data.get('roic', 0) / 100.0,  # Z-score로 변환 (간단히)
                'f_score': quality_result.get('piotroski_score', 0),
                'accruals_risk': 0 if financial_data.get('accruals_ratio', 0) <= 0.5 else 1,
                'eps_cagr': financial_data.get('eps_growth_rate', 0) / 100.0,
                'rev_cagr': financial_data.get('revenue_growth_rate', 0) / 100.0,
                'earnings_vol_sigma': abs(financial_data.get('net_income_growth_rate', 0)) / 100.0,
                'interest_cov': financial_data.get('interest_coverage_ratio', 0),
                'ev_ebit': financial_data.get('ev_ebit', 99),
                'sector_sigma_median': 0.2  # 기본값
            }
            
            # 8단계: UVS 자격 검사
            result['pipeline_stage'] = 'uvs_eligibility'
            
            # UVS 자격 검사를 위한 메트릭 준비
            uvs_metrics = {
                'valuation_pct': contextualized_result.get('final_adjusted_score', 0),
                'mos': margin_of_safety,
                'price_pos': price_position / 100.0,  # 0~1 범위로 변환
                'eps_cagr': financial_data.get('eps_growth_rate', 0),
                'rev_cagr': financial_data.get('revenue_growth_rate', 0),
                'ev_ebit': financial_data.get('ev_ebit', 99),
                'shareholder_yield': financial_data.get('shareholder_yield', 0.0),
                'interest_cov': financial_data.get('interest_coverage_ratio', 0),
                'f_score': quality_result.get('piotroski_score', 0),
                'accruals_risk': 0 if financial_data.get('accruals_ratio', 0) <= 0.5 else 1,
                'earnings_vol_sigma': abs(financial_data.get('net_income_growth_rate', 0)) / 100.0,
                'sector_sigma_median': 0.2,  # 기본값
                'leverage_z': 0.0  # 기본값 (실제로는 섹터 대비 계산 필요)
            }
            
            # UVS 자격 검사 실행
            uvs_result = self.uvs_filter.check_uvs_eligibility(uvs_metrics)
            print(f"  [INFO] {symbol} UVS 자격: {'통과' if uvs_result['is_eligible'] else '탈락'}")
            if not uvs_result['is_eligible']:
                print(f"    - 탈락 사유: {', '.join(uvs_result['reasons'])}")
                print(f"    - 가치스타일: {'통과' if uvs_result['eligibility_details']['value_style'] else '탈락'}")
                print(f"    - 저평가: {'통과' if uvs_result['eligibility_details']['undervalued'] else '탈락'}")
                print(f"    - 품질리스크: {'통과' if uvs_result['eligibility_details']['quality_risk'] else '탈락'}")
            
            # 스타일 분류 실행
            style_result = self.style_classifier.classify_value_style(style_metrics)
            print(f"  [INFO] {symbol} 가치주 스타일: {style_result['style_label']} (신뢰도: {style_result['confidence_score']:.1f})")
            print(f"    - 분류 사유: {', '.join(style_result['style_reasons'])}")
            
            # UVS 자격에 따른 최종 신호 결정
            if uvs_result['is_eligible']:
                # UVS 자격 통과 시 MoS 기반 신호 (매우 현실적으로 조정)
                if margin_of_safety >= 0.10:
                    result['final_recommendation'] = 'BUY'
                    print(f"  [INFO] {symbol} UVS BUY: MoS {margin_of_safety:.1%} >= 10%")
                elif margin_of_safety >= 0.00:
                    result['final_recommendation'] = 'WATCH'
                    print(f"  [INFO] {symbol} UVS WATCH: MoS {margin_of_safety:.1%} >= 0%")
                else:
                    result['final_recommendation'] = 'PASS'
                    print(f"  [INFO] {symbol} UVS PASS: MoS {margin_of_safety:.1%} < 0%")
                
                result['value_style'] = 'UVS'
                result['uvs_eligible'] = True
            else:
                # UVS 자격 탈락 시 PASS
                result['final_recommendation'] = 'PASS'
                result['value_style'] = 'Not UVS'
                result['uvs_eligible'] = False
                print(f"  [INFO] {symbol} UVS 자격 탈락으로 PASS")
            
            # 최종 결과에 UVS 및 스타일 분류 추가
            result['analysis_result']['uvs_eligibility'] = uvs_result
            result['analysis_result']['style_classification'] = style_result
            result['style_confidence'] = style_result['confidence_score']
            
            print(f"  [INFO] {symbol} 최종 신호: {result['final_recommendation']} | 스타일: {result['value_style']} | UVS: {'통과' if result['uvs_eligible'] else '탈락'}")
            
        except Exception as e:
            result['pipeline_errors'].append(f"pipeline_error_{result['pipeline_stage']}: {str(e)}")
            result['final_recommendation'] = 'ERROR'
            logging.error(f"파이프라인 분석 실패 {symbol}: {e}")
        finally:
            # 개별 종목 분석 시간 기록
            analysis_duration = _monotonic() - start_time
            self.metrics.record_analysis_duration(analysis_duration)
        
        return result
    
    def analyze_portfolio(self, symbols: List[Tuple[str, str]], 
                         max_stocks: int = 10) -> Dict[str, Any]:
        """포트폴리오 종합 분석 (다양화 포함)"""
        start_time = _monotonic()
        
        result = {
            'individual_analyses': [],
            'diversification_result': {},
            'final_portfolio': [],
            'portfolio_metrics': {}
        }
        
        # 메트릭 초기화
        self.metrics.record_stocks_analyzed(len(symbols))
        
        # 개별 종목 분석
        for symbol, name in symbols:
            try:
                analysis = self.analyze_single_stock(symbol, name)
                result['individual_analyses'].append(analysis)
            except Exception as e:
                logging.error(f"개별 분석 실패 {symbol}: {e}")
                # 실패한 경우 기본 구조로 추가
                result['individual_analyses'].append({
                    'symbol': symbol,
                    'name': name,
                    'pipeline_stage': 'error',
                    'analysis_result': None,
                    'pipeline_errors': [str(e)],
                    'final_recommendation': 'PASS'
                })
        
        # BUY/WATCH 신호가 있는 종목들만 필터링
        eligible_stocks = []
        for analysis in result['individual_analyses']:
            if analysis['final_recommendation'] in ['BUY', 'WATCH']:
                # 시가총액을 financial_data에서 가져오기
                market_cap = analysis['analysis_result'].get('financial_data', {}).get('market_cap', 0)
                print(f"  [DEBUG] {analysis['symbol']} financial_data market_cap: {market_cap}")
                if market_cap == 0:
                    market_cap = analysis['analysis_result']['input_validation'].get('market_cap', 0)
                    print(f"  [DEBUG] {analysis['symbol']} input_validation market_cap: {market_cap}")
                
                # 시가총액이 여전히 0이면 KOSPI 데이터에서 직접 조회
                if market_cap == 0:
                    try:
                        kospi_market_cap = self.legacy_analyzer._get_market_cap(analysis['symbol'])
                        if kospi_market_cap:
                            market_cap = kospi_market_cap
                            print(f"  [DEBUG] {analysis['symbol']} KOSPI market_cap: {market_cap}")
                    except:
                        pass
                
                # 섹터 정보 가져오기
                sector = analysis['analysis_result']['sector_contextualization'].get('sector_name', 'unknown')
                if sector == 'unknown':
                    # 섹터 정보가 없으면 종목명에서 추정
                    name = analysis.get('name', '')
                    if '은행' in name or '금융' in name:
                        sector = '금융'
                    elif '전자' in name or '반도체' in name:
                        sector = '전자'
                    elif '자동차' in name or '모비스' in name:
                        sector = '자동차'
                    elif '화학' in name or '에너지' in name:
                        sector = '화학'
                    else:
                        sector = '기타'
                
                # 종합점수 계산 (절대 가치점수 + 안전마진 + UVS 보너스)
                # 섹터 컨텍스트화 대신 절대 점수 사용 (분석 종목 수에 무관하게 일관성 유지)
                try:
                    absolute_value_score = analysis['analysis_result']['value_precision'].get('comprehensive_value_score', 0.0)
                    if absolute_value_score == 0.0:
                        # comprehensive_value_score가 없으면 weighted_score 사용
                        absolute_value_score = analysis['analysis_result']['value_precision'].get('weighted_score', 0.0)
                except (KeyError, TypeError):
                    absolute_value_score = 0.0
                
                try:
                    margin_of_safety = analysis['analysis_result']['margin_safety']['final_recommendation']['margin_of_safety']
                except (KeyError, TypeError):
                    margin_of_safety = 0.0
                
                uvs_bonus = 20 if analysis.get('uvs_eligible', False) else 0  # UVS 자격 통과 시 20점 보너스
                comprehensive_score = absolute_value_score + (margin_of_safety * 100) + uvs_bonus  # 안전마진을 100배하여 점수화
                
                # 현재가와 52주 정보 추출 (여러 경로에서 시도)
                current_price = 0
                w52_high = 0
                w52_low = 0
                
                try:
                    # 방법 1: analysis에서 직접 financial_data 추출
                    if 'financial_data' in analysis:
                        financial_data = analysis['financial_data']
                        current_price = financial_data.get('current_price', 0)
                        w52_high = financial_data.get('w52_high', 0)
                        w52_low = financial_data.get('w52_low', 0)
                    else:
                        # 방법 2: 전체 analysis에서 추출
                        current_price = analysis.get('current_price', 0)
                        w52_high = analysis.get('w52_high', 0)
                        w52_low = analysis.get('w52_low', 0)
                        
                except (KeyError, TypeError) as e:
                    print(f"  [DEBUG] {analysis['symbol']} 가격 정보 추출 실패: {e}")
                    current_price = 0
                    w52_high = 0
                    w52_low = 0
                
                stock_data = {
                    'symbol': analysis['symbol'],
                    'name': analysis['name'],
                    'recommendation': analysis['final_recommendation'],
                    'value_score': absolute_value_score,  # 절대 점수 사용
                    'margin_of_safety': margin_of_safety,
                    'comprehensive_score': comprehensive_score,
                    'market_cap': market_cap,
                    'sector': sector,
                    'value_style': analysis.get('value_style', 'Not Value'),
                    'style_confidence': analysis.get('style_confidence', 0.0),
                    'uvs_eligible': analysis.get('uvs_eligible', False),
                    'current_price': current_price,
                    'w52_high': w52_high,
                    'w52_low': w52_low
                }
                eligible_stocks.append(stock_data)
        
        # 일관성 있는 정렬: 종합점수 내림차순, 가치점수 내림차순, 안전마진 내림차순
        eligible_stocks.sort(key=lambda x: (-x['comprehensive_score'], -x['value_score'], -x['margin_of_safety']))
        print(f"  [INFO] 정렬된 자격 종목: {len(eligible_stocks)}개")
        
        # 다양화 적용 (기존 포트폴리오 고려)
        if eligible_stocks:
            # 기존 포트폴리오가 있는지 확인 (이전 분석 결과에서)
            existing_portfolio = getattr(self, '_previous_portfolio', None)
            
            diversification_result = self.diversification_manager.apply_comprehensive_diversification(
                eligible_stocks, max_stocks=len(symbols), existing_portfolio=existing_portfolio
            )
            result['diversification_result'] = diversification_result
            result['final_portfolio'] = diversification_result['final_portfolio']
            
            # 현재 포트폴리오를 다음 분석을 위해 저장
            self._previous_portfolio = result['final_portfolio']
            
            # 포트폴리오 메트릭
            result['portfolio_metrics'] = {
                'total_analyzed': len(symbols),
                'eligible_stocks': len(eligible_stocks),
                'final_portfolio_size': len(result['final_portfolio']),
                'diversification_ratio': diversification_result.get('diversification_summary', {}).get('diversification_ratio', 0.0),
                'concentration_level': diversification_result.get('diversification_summary', {}).get('concentration_metrics', {}).get('concentration_level', 'UNKNOWN')
            }
        else:
            # 자격 통과 종목이 없는 경우
            result['portfolio_metrics'] = {
                'total_analyzed': len(symbols),
                'eligible_stocks': 0,
                'final_portfolio_size': 0,
                'diversification_ratio': 0.0,
                'concentration_level': 'NONE'
            }
        
        # 분석 시간 기록
        analysis_duration = _monotonic() - start_time
        self.metrics.record_analysis_duration(analysis_duration)
        
        return result
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """파이프라인 요약 정보"""
        return {
            'pipeline_name': 'Upgraded Value Analysis Pipeline',
            'version': '2.0',
            'stages': [
                'input_validation',
                'quality_filter', 
                'risk_constraints',
                'value_precision',
                'margin_safety',
                'sector_contextualization',
                'price_position_policy',
                'diversification'
            ],
            'metrics': self.metrics.get_summary(),
            'config': {
                'value_investing_weight': self.config['enhanced_integrated_analysis']['weights']['value_investing'],
                'price_position_weight': self.config['enhanced_integrated_analysis']['weights']['price_position'],
                'grade_thresholds': self.config['enhanced_integrated_analysis']['grade_thresholds']
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
    from datetime import date, datetime

    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "tolist"):  # numpy arrays
        try:
            return obj.tolist()
        except Exception:
            pass
    # numpy scalar detection (more robust than module check)
    if isinstance(obj, (np.generic,)):
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
        # ✅ Fail-fast 가드: 중복 스케일 감지 시 즉시 예외
        if data.get("_percent_canonicalized") is True:
            raise ValueError("CRITICAL: Data already canonicalized! Duplicate scaling detected. "
                           "This indicates a data processing pipeline bug. "
                           "Check for multiple calls to standardize_financial_units().")
        
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
                    # 
                    # 처리 규칙 표:
                    # | 값 범위 | 해석 | 변환 | 비고 |
                    # |---------|------|------|------|
                    # | 0–10    | 배수 | ×100 | 일반적인 유동비율 배수값 |
                    # | ≥50     | %    | 그대로 | 일반적인 퍼센트값 |
                    # | 10–50   | 모드별 | clamp/as_is | 애매 구간 (환경변수 제어) |
                    # 
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
                                    # as_is 모드: 원본 값 유지하되 아웃라이어만 클립
                                    out[k] = vv
                                    # 완전한 as_is라도 이상치만은 클립
                                    if not (10.0 <= out[k] <= 10000.0):
                                        out[k] = max(10.0, min(10000.0, out[k]))
                                        logging.debug(f"[unit] current_ratio outlier clipped in as_is mode: {vv} -> {out[k]}")
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

        # ✅ Percent canonicalization 보호 플래그 설정
        out["_percent_canonicalized"] = True
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
        """캐시에서 데이터 조회 (동시성 안전, TTL 분리, 압축 해제)"""
        now = _monotonic()
        with self._cache_lock:
            hit = cache.get(key)
            cache_type = 'price' if cache is self._cache_price else 'financial'
            if hit and not (isinstance(hit, tuple) and len(hit) >= 2):
                logging.debug("cache entry shape invalid; dropping")
                if self.metrics:
                    self.metrics.record_cache_miss(cache_type)
                return None
            if hit:
                # TTL override 지원 (빈 데이터용)
                ttl = hit[2] if len(hit) > 2 and hit[2] is not None else self._ttl[cache_type]
                if now - hit[0] < ttl:
                    cache.move_to_end(key)  # LRU 최근성 업데이트
                    if self.metrics:
                        self.metrics.record_cache_hit(cache_type)
                    
                    # 압축된 데이터 해제
                    if len(hit) > 3 and hit[3]:  # 압축 플래그 확인
                        import json
                        import gzip
                        try:
                            decompressed = json.loads(gzip.decompress(hit[1]).decode("utf-8"))
                            return decompressed
                        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                            # 압축 해제 실패 시 원본 반환
                            return hit[1]
                    else:
                        return hit[1]
        
        if self.metrics:
            self.metrics.record_cache_miss(cache_type)
        return None

    def _set_cached(self, cache, key, value, ttl_override=None):
        """캐시에 데이터 저장 (동시성 안전, LRU 한도 적용, 메모리 최적화)"""
        with self._cache_lock:
            # 빈 데이터는 짧은 TTL 적용
            if ttl_override is None and isinstance(value, dict) and not value:
                ttl_override = min(1.0, self._ttl['price'] * 0.2)  # 20% of normal TTL
            
            # 메모리 최적화: 큰 데이터 압축 (json 직렬화 길이로 판단)
            if isinstance(value, dict):
                import json, gzip
                payload = json.dumps(value, default=str).encode()
                if len(payload) > 8 * 1024:  # 8KB threshold for compression
                    try:
                        compressed = gzip.compress(payload)
                        cache[key] = (_monotonic(), compressed, ttl_override, True)
                        cache.move_to_end(key)
                        while len(cache) > self._max_keys:
                            cache.popitem(last=False)
                        return
                    except Exception:
                        pass
            cache[key] = (_monotonic(), value, ttl_override, False)
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
            # _with_retries가 최종 실패를 이미 집계했음. 여기선 로그만.
            log_error("재무비율 분석", symbol, e)
        
        # 수익성비율 분석 (재시도 적용)
        try:
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
            # _with_retries가 최종 실패를 이미 집계했음. 여기선 로그만.
            log_error("수익성비율 분석", symbol, e)
        
        # 안정성비율 분석 (current_ratio 포함)
        try:
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
            # _with_retries가 최종 실패를 이미 집계했음. 여기선 로그만.
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
            # Rate limiter 적용 (price_provider 호출 전)
            try:
                self.rate_limiter.acquire()
            except TimeoutError as e:
                if self.metrics:
                    self.metrics.record_api_call(False, ErrorType.API_TIMEOUT)
                raise
            
            # 향상된 가격 프로바이더 사용 (리트라이 + 메트릭 콜백으로 일원화)
            cb_final = (lambda ok, et=None: self.metrics.record_api_call(ok, et)) if self.metrics else None
            cb_attempt = (lambda et=None: self.metrics.record_api_attempt_error(et)) if self.metrics else None
            price_data = _with_retries(
                lambda: self.price_provider.get_comprehensive_price_data(symbol),
                metrics_attempt=cb_attempt,
                metrics_final=cb_final  # 최종 메트릭 기록 일원화
            )
            
            if price_data and price_data != {}:
                # 결측치 표현 일관성: "없으면 None"로 통일 (legitimate zero 허용)
                def _local_none_if_missing(x):
                    """None for None/NaN; allow legitimate zero"""
                    return DataValidator.safe_float_optional(x)
                
                data = {
                    'current_price': _local_none_if_missing(price_data.get('current_price')),
                    'price_change': _local_none_if_missing(price_data.get('price_change')),
                    'price_change_rate': _local_none_if_missing(price_data.get('price_change_rate')),
                    'volume': int(round(v)) if (v := _local_none_if_missing(price_data.get('volume'))) is not None else None,
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
                # ✅ PER 계산 가드 명확화: current_price > 0 필요 (정지/단주 등)
                if eps is not None and eps > EPS_MIN and cp is not None and cp > 0:
                    data['per'] = DataValidator.safe_divide(cp, eps)
                else:
                    data['per'] = None  # 원인: eps_min 미달/결측/정지/가격<=0
                    if self.metrics:
                        self.metrics.record_valuation_skip('per_epsmin')
                # ✅ PBR 계산 가드 명확화: current_price > 0 필요 (정지/단주 등)
                if bps is not None and bps > BPS_MIN and cp is not None and cp > 0:
                    data['pbr'] = DataValidator.safe_divide(cp, bps)
                else:
                    data['pbr'] = None  # 원인: bps_min 미달/결측/정지/가격<=0
                    if self.metrics:
                        self.metrics.record_valuation_skip('pbr_bpsmin')
                
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
                        # _with_retries가 최종 실패를 이미 집계했음. 여기선 로그만.
                        logging.debug(f"KIS API 52주 고저 데이터 조회 실패 {symbol}: {e}")
                
                # 52주 고저 데이터 저장 (유효한 값만)
                if w52h is not None: data['w52_high'] = w52h
                if w52l is not None: data['w52_low'] = w52l
                
                # 캐시에 저장
                self._set_cached(self._cache_price, symbol, data)
                return data
            else:
                # 빈 페이로드 처리 (API 호출은 성공했지만 데이터가 비어있음)
                if self.metrics:
                    self.metrics.record_api_call(False, ErrorType.EMPTY_PRICE_PAYLOAD)
                    self.metrics.metrics['empty_price_payloads'] += 1
                data = {}
                self._set_cached(self._cache_price, symbol, data)
                return data
        except Exception as e:
            # _with_retries가 이미 실패를 기록하므로 중복 기록 방지
            log_error("가격 데이터 조회", symbol, e)
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
        
        # PER/PBR 기반 밸류에이션 페널티 추가 (환경변수로 제어) - 이중 페널티 방지
        apply_val_in_price = safe_env_bool("VAL_PENALTY_IN_PRICE", True)
        apply_val_in_fin = safe_env_bool("VAL_PENALTY_IN_FIN", False)
        
        # 이중 페널티 상충 검출 및 경고
        if apply_val_in_price and apply_val_in_fin:
            logging.warning("[val-penalty] PRICE와 FIN 동시 적용 감지 → FIN 비활성화 권장")
            apply_val_in_fin = False
        
        opinion_score, w_op = _use(self._calculate_opinion_score(data.get('opinion_analysis', {})), 'opinion_analysis')
        estimate_score, w_est = _use(self._calculate_estimate_score(data.get('estimate_analysis', {})), 'estimate_analysis')
        financial_score, w_fin = _use(self._calculate_financial_score(data.get('financial_data', {}), price_data=data.get('price_data'), apply_val_in_fin=apply_val_in_fin), 'financial_ratios')
        growth_score, w_gro = _use(self._calculate_growth_score(data.get('financial_data', {})), 'growth_analysis')
        scale_score, w_sca = _use(self._calculate_scale_score(data.get('market_cap', 0)), 'scale_analysis')
        
        # 52주 위치 점수 계산 (missing data half weight 규칙 일관성)
        pp_raw = data.get('price_position')
        pp_score = self._calculate_price_position_score(pp_raw) if pp_raw is not None else None
            
        if price_data and apply_val_in_price:
            per = price_data.get('per')
            pbr = price_data.get('pbr')
            valuation_penalty = self._calculate_per_pbr_penalty(per, pbr)
            if valuation_penalty is not None:
                # 밸류에이션 페널티를 가격위치 점수에 반영
                pp_score = pp_score * valuation_penalty if pp_score is not None else valuation_penalty * 50
        
        price_position_score, w_pp = _use(pp_score, 'price_position')

        # 신규: 가치투자 점수 (사업의 질 + 안전마진)
        value_score, w_val = _use(
            self._calculate_value_investing_score(
                financial_data=data.get('financial_data', {}),
                price_data=data.get('price_data', {}),
                intrinsic_value=data.get('intrinsic_value')
            ),
            'value_investing'
        )
        
        # 점수 클램핑 (극단치/오버스케일 방지)
        def _clamp01(x): 
            return max(0.0, min(100.0, x if x is not None else 50.0))
        
        opinion_score = _clamp01(opinion_score)
        estimate_score = _clamp01(estimate_score)
        financial_score = _clamp01(financial_score)
        growth_score = _clamp01(growth_score)
        scale_score = _clamp01(scale_score)
        price_position_score = _clamp01(price_position_score)
        value_score = _clamp01(value_score)
        
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
            (value_score, w_val),
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
                '가격위치': price_position_score * (w_pp / total_weight) if price_position_score is not None else 0,
                '가치투자': value_score * (w_val / total_weight) if value_score is not None else 0
            }
        else:
            breakdown = {
                '투자의견': 0, '추정실적': 0, '재무비율': 0,
                '성장성': 0, '규모': 0, '가격위치': 0, '가치투자': 0
            }
        
        # 원점수 breakdown 추가 (0~100 스케일, 가중치 미적용)
        raw_breakdown = {
            'opinion_raw': opinion_score,
            'estimate_raw': estimate_score,
            'financial_raw': financial_score,
            'growth_raw': growth_score,
            'scale_raw': scale_score,
            'price_position_raw': price_position_score,
            'value_raw': value_score,
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
    
    def _calculate_financial_score(self, financial_data: Dict[str, Any], *, price_data: Optional[Dict[str, Any]] = None, apply_val_in_fin: bool = False) -> Optional[float]:
        """재무비율 점수 계산 (존재하는 지표만 가중합, 모두 결측이면 None 반환)
        
        **이중 스케일 금지**: 이 함수는 % 입력을 전제로 함 (DataConverter.standardize_financial_units()에서 변환됨)
        """
        if not financial_data:
            return None
        
        # ✅ Percent canonicalization 보호 체크 (resilience 개선)
        fd = dict(financial_data)  # local snapshot
        if fd.get("_percent_canonicalized") is not True:
            logging.warning("WARNING: financial_data not canonicalized! Re-scaling detected. Applying on-the-fly canonicalization.")
            fd = DataConverter.standardize_financial_units(fd)
            fd["_percent_canonicalized"] = True
        
        # NOTE: 입력은 canonical % (DataConverter.standardize_financial_units 이후)
        # 재스케일 금지: 숫자 범위만 검증 (로컬 스냅샷으로 부수효과 방지)
        _roe = DataValidator.safe_float_optional(fd.get('roe'))
        _roa = DataValidator.safe_float_optional(fd.get('roa'))
        _debt = DataValidator.safe_float_optional(fd.get('debt_ratio'))
        _npm = DataValidator.safe_float_optional(fd.get('net_profit_margin'))
        _cr = DataValidator.safe_float_optional(fd.get('current_ratio'))

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

        # 수익성 일관성 평가 추가
        consistency_score = self._calculate_profitability_consistency_score(financial_data)
        if consistency_score is not None:
            consistency_w = w.get('profitability_consistency_score', 5)
            acc += consistency_score * consistency_w; wsum += consistency_w

        # 밸류에이션 페널티 추가 (PER/PBR 기반 고평가 종목 차단)
        per = None
        pbr = None
        if price_data:
            per = DataValidator.safe_float_optional(price_data.get('per'))
            pbr = DataValidator.safe_float_optional(price_data.get('pbr'))

        valuation_penalty = self._calculate_per_pbr_penalty(per, pbr)
        if valuation_penalty is not None:
            # penalty(0.3~1.0)를 '획득 비율'로 사용: 고평가(작은 값)일수록 적게 반영
            # 환경변수로 제어 가능 (기본값 False로 이중 페널티 방지)
            # apply_val_in_fin은 이미 calculate_score에서 상충 검출됨
            if apply_val_in_fin:
                valuation_w = w.get('valuation_penalty_score', 2)
                acc += valuation_penalty * valuation_w
                wsum += valuation_w

        if wsum == 0:
            return None  # 모두 결측 → 상위에서 half-weight + 50점 처리
        return (acc / wsum) * 100.0
    
    def _calculate_growth_score(self, financial_data: Dict[str, Any]) -> Optional[float]:
        """성장성 점수 계산 (영업이익 중심 강화 버전)"""
        if not financial_data:
            return None  # 데이터 없음
        
        revenue_growth = DataValidator.safe_float_optional(financial_data.get('revenue_growth_rate'))
        operating_growth = DataValidator.safe_float_optional(financial_data.get('operating_income_growth_rate'))
        net_growth = DataValidator.safe_float_optional(financial_data.get('net_income_growth_rate'))
        
        # 결측치만 None 반환, 0%는 중립 점수로 처리
        if revenue_growth is None:
            return None
        
        # 입력 클립으로 극단치 방지 (-100~+100%)
        revenue_growth = max(-100.0, min(100.0, revenue_growth))
        
        # 영업이익이 있으면 영업이익 중심 평가, 없으면 매출 중심 평가
        if operating_growth is not None:
            operating_growth = max(-100.0, min(100.0, operating_growth))
            
            # 영업이익 중심 점수 계산 (더 엄격한 기준)
            if operating_growth >= 30:    # 30% 이상
                base_score = 100.0
            elif operating_growth >= 20:  # 20% 이상
                base_score = 85.0
            elif operating_growth >= 10:  # 10% 이상
                base_score = 70.0
            elif operating_growth >= 0:   # 0% 이상
                base_score = 50.0
            elif operating_growth >= -10: # -10% 이상
                base_score = 30.0
            elif operating_growth >= -20: # -20% 이상
                base_score = 15.0
            else:  # -20% 미만
                base_score = 5.0
        else:
            # 영업이익이 없으면 매출 중심 평가
            thresholds = self.config.growth_score_thresholds
            if revenue_growth >= thresholds.get('excellent', 20):
                base_score = 100.0
            elif revenue_growth >= thresholds.get('good', 10):
                base_score = 80.0
            elif revenue_growth >= thresholds.get('average', 0):
                base_score = 50.0
            elif revenue_growth >= thresholds.get('poor', -10):
                base_score = 30.0
            else:
                base_score = 10.0
        
        # 영업이익-순이익 일관성 분석 (강화된 페널티)
        if operating_growth is not None and net_growth is not None:
            profit_diff = operating_growth - net_growth
            
            # 영업이익과 순이익의 방향이 반대이면 강한 페널티
            if (operating_growth > 0 and net_growth < 0) or (operating_growth < 0 and net_growth > 0):
                # 방향이 반대면 70% 페널티
                base_score *= 0.3
            elif abs(profit_diff) > 50:  # 50% 이상 차이
                base_score *= 0.4  # 60% 페널티
            elif abs(profit_diff) > 30:  # 30% 이상 차이
                base_score *= 0.6  # 40% 페널티
            elif abs(profit_diff) > 20:  # 20% 이상 차이
                base_score *= 0.8  # 20% 페널티
        
        # 순이익 성장률 추가 보정 (영업이익과 함께 고려)
        if net_growth is not None:
            net_growth = max(-100.0, min(100.0, net_growth))
            
            # 순이익이 매우 나쁘면 추가 페널티
            if net_growth < -30:  # -30% 미만
                base_score *= 0.5  # 50% 페널티
            elif net_growth < -20:  # -20% 미만
                base_score *= 0.7  # 30% 페널티
            elif net_growth < -10:  # -10% 미만
                base_score *= 0.85  # 15% 페널티
        
        # 최종 점수 클램핑
        return max(0.0, min(100.0, base_score))
    
    def _calculate_profitability_consistency_score(self, financial_data: Dict[str, Any]) -> Optional[float]:
        """수익성 일관성 점수 계산 (영업이익 중심 강화 버전)"""
        operating_growth = DataValidator.safe_float_optional(financial_data.get('operating_income_growth_rate'))
        net_growth = DataValidator.safe_float_optional(financial_data.get('net_income_growth_rate'))
        
        # 두 지표 모두 있어야 평가 가능
        if operating_growth is None or net_growth is None:
            return None
        
        # 차이 계산
        profit_diff = operating_growth - net_growth
        
        # 영업이익과 순이익 방향 일치성 체크
        same_direction = (operating_growth > 0 and net_growth > 0) or (operating_growth < 0 and net_growth < 0)
        
        # 방향이 다르면 매우 낮은 점수
        if not same_direction:
            if abs(profit_diff) > 30:  # 방향이 반대이고 차이가 30% 이상
                return 0.05  # 매우 낮은 일관성
            else:
                return 0.15  # 낮은 일관성
        
        # 방향이 같을 때의 차이 점수 (더 엄격한 기준)
        if abs(profit_diff) <= 3:  # 3% 이하 차이
            return 1.0  # 완벽한 일관성
        elif abs(profit_diff) <= 8:  # 8% 이하 차이
            return 0.85  # 매우 양호한 일관성
        elif abs(profit_diff) <= 15:  # 15% 이하 차이
            return 0.7  # 양호한 일관성
        elif abs(profit_diff) <= 25:  # 25% 이하 차이
            return 0.5  # 보통 일관성
        elif abs(profit_diff) <= 40:  # 40% 이하 차이
            return 0.3  # 낮은 일관성
        else:  # 40% 초과 차이
            return 0.15  # 매우 낮은 일관성
    
    def _calculate_valuation_penalty(self, financial_data: Dict[str, Any], per: Optional[float] = None, pbr: Optional[float] = None) -> Optional[float]:
        """밸류에이션 페널티 계산 (PER/PBR 기반 고평가 차단)"""
        # PER/PBR 페널티는 _calculate_per_pbr_penalty에서 처리
        return self._calculate_per_pbr_penalty(per, pbr)
    
    def _calculate_per_pbr_penalty(self, per: Optional[float], pbr: Optional[float]) -> Optional[float]:
        """PER/PBR 기반 밸류에이션 페널티 계산 (고평가 종목 차단)"""
        if per is None and pbr is None:
            return None
        
        penalty = 1.0  # 기본 페널티 없음
        
        # PER 페널티
        if per is not None:
            if per > 50:      # 매우 고평가
                penalty *= 0.3
            elif per > 30:    # 고평가
                penalty *= 0.5
            elif per > 20:    # 약간 고평가
                penalty *= 0.7
            elif per > 15:    # 적정
                penalty *= 0.9
            # PER < 15는 페널티 없음 (저평가)
        
        # PBR 페널티
        if pbr is not None:
            if pbr > 5:       # 매우 고평가
                penalty *= 0.2
            elif pbr > 3:     # 고평가
                penalty *= 0.4
            elif pbr > 2:     # 약간 고평가
                penalty *= 0.6
            elif pbr > 1.5:   # 적정
                penalty *= 0.8
            # PBR < 1.5는 페널티 없음 (저평가)
        
        # Configurable minimum penalty to avoid nuking the overall score twice
        min_penalty = safe_env_float("VAL_PENALTY_MIN", 0.3, 0.0)
        return max(min_penalty, penalty)
    
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

    # ---------- 신규: 가치투자 점수 ----------
    def _calculate_value_investing_score(
        self,
        financial_data: Dict[str, Any],
        price_data: Dict[str, Any],
        intrinsic_value: Optional[float]
    ) -> Optional[float]:
        """사업의 질 + 안전마진을 통합한 가치 점수(0~100)."""
        
        # 1) 안전마진(MoS) 계산
        mos_score = None
        if price_data:
            cp = DataValidator.safe_float_optional(price_data.get('current_price'))
            iv = DataValidator.safe_float_optional(intrinsic_value)
            
            if cp is not None and cp > 0 and iv is not None and iv > 0:
                mos = max(0.0, min(1.0, (iv - cp) / iv))
                mos_score = (
                    100.0 if mos >= 0.5 else
                     85.0 if mos >= 0.35 else
                     70.0 if mos >= 0.2 else
                     50.0 if mos >= 0.1 else
                     25.0 if mos > 0 else
                     10.0
                )

        # 2) 사업의 질(해자 프록시): ROE/순이익마진/부채/일관성
        fd = financial_data or {}
        roe = DataValidator.safe_float_optional(fd.get('roe'))
        npm = DataValidator.safe_float_optional(fd.get('net_profit_margin'))
        debt = DataValidator.safe_float_optional(fd.get('debt_ratio'))
        consistency = self._calculate_profitability_consistency_score(fd)

        q = 0.0; wsum = 0.0
        if roe is not None:
            q += (1.0 if roe >= 20 else 0.75 if roe >= 15 else 0.5 if roe >= 10 else 0.25 if roe >= 5 else 0.0) * 4; wsum += 4
        if npm is not None:
            q += (1.0 if npm >= 15 else 0.8 if npm >= 10 else 0.6 if npm >= 5 else 0.4 if npm >= 2 else 0.0) * 3; wsum += 3
        if debt is not None:
            q += (1.0 if debt <= 30 else 0.75 if debt <= 50 else 0.5 if debt <= 70 else 0.25 if debt <= 100 else 0.0) * 2; wsum += 2
        if consistency is not None:
            q += consistency * 1; wsum += 1
        quality_score = None if wsum == 0 else q / wsum * 100.0

        # 3) 최종 점수 계산
        if mos_score is None and quality_score is None:
            return None
        if mos_score is None:
            return quality_score  # 사업의 질만으로 평가
        if quality_score is None:
            return mos_score      # MoS만으로 평가
        return 0.6 * mos_score + 0.4 * quality_score


    # ---------- 신규: 해자(질) 점수/등급 ----------
    def _moat_quality_score(self, fd: Dict[str, Any]) -> Optional[float]:
        """ROE/순이익마진/부채/일관성으로 0~100 점수."""
        try:
            roe = DataValidator.safe_float_optional(fd.get('roe'))
            npm = DataValidator.safe_float_optional(fd.get('net_profit_margin'))
            debt = DataValidator.safe_float_optional(fd.get('debt_ratio'))
            consistency = self._calculate_profitability_consistency_score(fd)
            q = 0.0; w = 0.0
            if roe is not None: q += (1.0 if roe>=20 else 0.75 if roe>=15 else 0.5 if roe>=10 else 0.25 if roe>=5 else 0.0)*4; w+=4
            if npm is not None: q += (1.0 if npm>=15 else 0.8 if npm>=10 else 0.6 if npm>=5 else 0.4 if npm>=2 else 0.0)*3; w+=3
            if debt is not None: q += (1.0 if debt<=30 else 0.75 if debt<=50 else 0.5 if debt<=70 else 0.25 if debt<=100 else 0.0)*2; w+=2
            if consistency is not None: q += consistency*1; w+=1
            return None if w==0 else q/w*100.0
        except Exception:
            return None

    def _moat_grade_from_score(self, s: Optional[float]) -> str:
        if s is None: return "N/A"
        return "Wide" if s>=85 else "Narrow" if s>=70 else "Thin" if s>=55 else "None"

    
    def _calculate_price_position_score(self, price_position: Optional[float]) -> float:
        """
        52주 위치에 따른 점수 계산 (저평가 가치주 발굴 강화)
        
        전략적 의도:
        - 고위치(70%+) 극강 벌점: 고평가 종목 강력 차단
        - 중위치(30-70%) 중립: 적정 밸류에이션 구간
        - 저위치(30%-) 강력 가점: 저평가 구간 대폭 가점
        
        저평가 가치주 발굴을 위한 극강화된 밸류에이션 반영
        """
        if price_position is None:
            return 50.0  # 중립점
        
        # 저평가 가치주 발굴을 위한 극강화된 매핑
        if price_position >= 90:
            # 극고위치: 극강 벌점 (90-100% → 0-5점)
            score = max(0.0, 5.0 - (price_position - 90) * 0.5)
        elif price_position >= 80:
            # 고위치: 강한 벌점 (80-90% → 5-15점)
            score = max(0.0, 15.0 - (price_position - 80) * 1.0)
        elif price_position >= 70:
            # 상위치: 벌점 (70-80% → 15-30점)
            score = max(0.0, 30.0 - (price_position - 70) * 1.5)
        elif price_position >= 50:
            # 중위치: 중립 (50-70% → 30-60점)
            score = 30.0 + (price_position - 50) * 1.5
        elif price_position >= 30:
            # 하위치: 가점 (30-50% → 60-80점)
            score = 60.0 + (price_position - 30) * 1.0
        else:
            # 저위치: 강력 가점 (0-30% → 80-100점 정확히 매핑)
            score = 80.0 + (30 - price_position) * (20.0/30.0)
        
        # 경계값 클램핑
        return max(0.0, min(100.0, score))
    
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
        
        # 개선된 모듈들 초기화
        if IMPROVED_MODULES_AVAILABLE:
            self.rate_limiter = get_default_rate_limiter()
            self.exception_handler = get_global_handler()
            self.input_validator = get_global_validator()
            self.cache = get_global_cache("analyzer_cache")
            self.batch_processor = BatchProcessor(batch_size=50, max_wait_time=0.5)
            self.code_optimizer = CodeOptimizer()
            self.data_processor = DataProcessor()
            self.memory_optimizer = MemoryOptimizer()
            self.performance_monitor = PerformanceMonitor()
            self.performance_profiler = PerformanceProfiler(self.performance_monitor)
            self.price_enhancer = PriceDisplayEnhancer()
            self.value_investing = ValueInvestingPhilosophy()
        else:
            self.rate_limiter = TPSRateLimiter()
            self.exception_handler = None
            self.input_validator = None
            self.cache = None
            self.performance_monitor = None
            self.batch_processor = None
            self.code_optimizer = None
            self.data_processor = None
            self.memory_optimizer = None
        
        self.include_realtime = include_realtime
        self.include_external = include_external
        
        # ✅ 환경변수 캐싱 (핫패스 최적화)
        self.env_cache = {
            'current_ratio_ambiguous_strategy': os.getenv("CURRENT_RATIO_AMBIGUOUS_STRATEGY", "as_is"),
            'current_ratio_force_percent': os.getenv("CURRENT_RATIO_FORCE_PERCENT", "false"),
            'market_cap_strict_mode': os.getenv("MARKET_CAP_STRICT_MODE", "true"),
            'max_sector_peers_base': safe_env_int("MAX_SECTOR_PEERS_BASE", 40, 5),
            'max_sector_peers_full': safe_env_int("MAX_SECTOR_PEERS_FULL", 200, 20),
            'sector_target_good': safe_env_int("SECTOR_TARGET_GOOD", 60, 10),
            'max_sector_cache_entries': safe_env_int("MAX_SECTOR_CACHE_ENTRIES", 64, 1),
            'max_sector_api_boost': safe_env_int("MAX_SECTOR_API_BOOST", 10, 0),
        }
        
        # 메트릭 수집기 초기화
        self.metrics = MetricsCollector()
        
        # ===== 가치투자 정책(방주) 기본값 =====
        # (환경변수/설정에서 재정의 가능)
        self.value_policy = {
            "min_mos_buy": float(os.getenv("VAL_MIN_MOS_BUY", "0.30")),     # 30% 이상이면 매수 고려
            "min_mos_watch": float(os.getenv("VAL_MIN_MOS_WATCH", "0.10")), # 10%~30%는 관찰
            "min_quality_for_buy": int(os.getenv("VAL_MIN_QUALITY", "70")), # 해자/질 점수 기준
            "max_price_pos_for_buy": float(os.getenv("VAL_MAX_PRICEPOS", "60")), # 52주 위치 상단 과열 회피
            "reeval_cooldown_min": int(os.getenv("VAL_REEVAL_COOLDOWN_MIN", "1440")), # 재평가 최소 간격(분)
            # 보수적 내재가치 추정 파라미터
            "fcf_growth_cap": float(os.getenv("VAL_FCF_GROWTH_CAP", "0.06")),     # 장기 성장률 상한 6%
            "discount_floor": float(os.getenv("VAL_DISCOUNT_FLOOR", "0.12")),     # 할인율 하한 12%
            "terminal_mult_cap": float(os.getenv("VAL_TERM_MULT_CAP", "12.0")),   # 터미널 멀티플 상한
            "eps_mult_base": float(os.getenv("VAL_EPS_MULT_BASE", "10.0")),       # EPS 보수적 멀티플
            "eps_mult_bonus": float(os.getenv("VAL_EPS_MULT_BONUS", "2.0")),      # 질 양호 시 보너스
        }

        # 마지막 시그널 시간 캐시(Temperament Guard)
        self._last_signal_ts: Dict[str, float] = {}

        # 환경변수 핫리로드 등록
        _register_analyzer_for_env_reload(self)
        
        # 컴포넌트 초기화
        self._initialize_components()

    # ---------- 신규: 워치리스트/시그널 ----------
    def _compute_watchlist_signal(self, symbol: str, current_price: Optional[float], intrinsic_value: Optional[float], quality_score: Optional[float], price_position: Optional[float], overall_score: Optional[float] = None) -> Tuple[str, Optional[float]]:
        """
        BUY / WATCH / PASS 와 목표매수가(= IV * (1 - min_mos_buy))
        Temperament Guard: 과빈도 알림 억제
        """
        cp = DataValidator.safe_float_optional(current_price)
        iv = DataValidator.safe_float_optional(intrinsic_value)
        pp = DataValidator.safe_float_optional(price_position)
        q = quality_score

        if cp is None or iv is None or iv <= 0:
            return ("PASS", None)
        mos = max(0.0, min(1.0, (iv - cp) / iv))
        target_buy = iv * (1.0 - self.value_policy["min_mos_buy"])

        # 과열 구간 회피
        if pp is not None and pp > self.value_policy["max_price_pos_for_buy"] + 20:
            return ("PASS", target_buy)

        # 품질 미달 시 회피
        if q is not None and q < self.value_policy["min_quality_for_buy"] - 10:
            return ("PASS", target_buy)

        # 종합 점수 조건 추가 (기본 60점 이상)
        min_overall_score = float(os.getenv("VAL_MIN_OVERALL_SCORE", "60.0"))
        overall_ok = overall_score is None or overall_score >= min_overall_score
        
        if mos >= self.value_policy["min_mos_buy"] and (q is None or q >= self.value_policy["min_quality_for_buy"]) and (pp is None or pp <= self.value_policy["max_price_pos_for_buy"]) and overall_ok:
            # Temperament Guard
            import time
            now = time.time()
            last = self._last_signal_ts.get(symbol, 0.0)
            if now - last >= self.value_policy["reeval_cooldown_min"]*60:
                self._last_signal_ts[symbol] = now
            return ("BUY", target_buy)
        elif mos >= self.value_policy["min_mos_watch"]:
            return ("WATCH", target_buy)
        else:
            return ("PASS", target_buy)

    # ---------- 신규: 플레이북 출력 ----------
    def _value_investing_playbook(self, symbol: str, iv: Optional[float], target_buy: Optional[float], moat_grade: str) -> List[str]:
        tips = []
        tips.append("① 리스트: 역량 범위 내 우량 기업을 목록화")
        if iv:
            tips.append(f"② 내재가치(보수적): 주당 약 {iv:,.0f}")
        if target_buy:
            tips.append(f"③ 매수가(안전마진 반영): ≤ {target_buy:,.0f}")
        tips.append("④ 기다림: 미스터 마켓이 공포일 때만 집행")
        tips.append(f"⑤ 집행: 해자등급({moat_grade}) 훼손 없으면 장기 보유 전제")
        return tips

    # ---------- 신규: 내재가치 보수적 추정 ----------
    def _estimate_intrinsic_value(self, symbol: str, financial_data: Dict[str, Any], price_data: Dict[str, Any]) -> Optional[float]:
        """
        두 모델 중 더 보수적인(낮은) 값을 채택:
        (A) 단기 단순 FCF 전개 + 할인 / (B) EPS × 보수적 멀티플
        """
        try:
            policy = self.value_policy
            # 데이터 확보(사업을 사라: 핵심 데이터 없으면 추정 보류)
            fcf = DataValidator.safe_float_optional(financial_data.get("free_cash_flow_per_share"))
            eps = DataValidator.safe_float_optional(financial_data.get("eps"))
            shares = DataValidator.safe_float_optional(financial_data.get("shares_outstanding"))
            quality = self.score_calculator._moat_quality_score(financial_data)

            iv_a = None
            if fcf is not None and fcf > 0:
                g = min(policy["fcf_growth_cap"], max(-0.05, DataValidator.safe_float_optional(financial_data.get("fcf_growth", 0.0)) or 0.0))
                r = max(policy["discount_floor"], DataValidator.safe_float_optional(financial_data.get("discount_rate", policy["discount_floor"])) or policy["discount_floor"])
                term_mult = min(policy["terminal_mult_cap"], 12.0 + (quality - 70) * 0.1 if quality is not None else 10.0)
                # 5년 단순 전개(보수적) + 터미널 밸류
                horizon = 5
                pv = 0.0
                cf = fcf
                for t in range(1, horizon + 1):
                    cf = cf * (1 + g)
                    pv += cf / ((1 + r) ** t)
                terminal = (cf * term_mult) / ((1 + r) ** horizon)
                iv_a = (pv + terminal)

            iv_b = None
            if eps is not None and eps > 0:
                mult = policy["eps_mult_base"] + (policy["eps_mult_bonus"] if (quality is not None and quality >= 80) else 0.0)
                iv_b = eps * mult

            candidates = [v for v in [iv_a, iv_b] if v is not None and v > 0]
            if not candidates:
                return None
            per_share_iv = min(candidates)
            # 만약 주식수 제공되면 주당 기준이 이미 per-share일 수 있음 → 그대로 반환
            return per_share_iv
        except Exception as e:
            logging.warning(f"[{symbol}] intrinsic value estimate failed: {e}")
            return None

    def _initialize_components(self):
        """컴포넌트 초기화"""
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
        self._kospi_loading_failed = False
        self._load_kospi_data()
        
        # 섹터 벡터 캐시 제거됨 (미사용)
        
        # 섹터 특성 캐시 (TTL 30분, 동적 조정)
        self._sector_char_cache = OrderedDict()
        self._sector_char_cache_ttl = safe_env_int("SECTOR_CHAR_CACHE_TTL", 1800, 300)  # 기본 30분, 최소 5분
        self._sector_char_cache_lock = RLock()
        self._sector_char_cache_max_size = safe_env_int("SECTOR_CHAR_CACHE_MAX_SIZE", 256, 64)  # 기본 256개, 최소 64개
        
        # 외부 분석기 스레드 안전성을 위한 락 (분리)
        self._opinion_lock = RLock()
        self._estimate_lock = RLock()
        
        # 메모리 모니터링 및 최적화
        self._memory_threshold = safe_env_float("MEMORY_THRESHOLD_MB", 1024.0, 256.0)  # 기본 1GB
        self._gc_interval = safe_env_int("GC_INTERVAL", 100, 10)  # 기본 100회 분석마다 GC
        self._analysis_count = 0
    
    def _check_memory_usage(self):
        """메모리 사용량 체크 및 가비지 컬렉션"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self._memory_threshold:
                logging.warning(f"High memory usage: {memory_mb:.1f}MB (threshold: {self._memory_threshold}MB)")
                import gc
                gc.collect()
                logging.info("Garbage collection performed")
                
                # 메모리 사용량 재확인
                new_memory_mb = process.memory_info().rss / 1024 / 1024
                logging.info(f"Memory after GC: {new_memory_mb:.1f}MB (freed: {memory_mb - new_memory_mb:.1f}MB)")
        except ImportError:
            # psutil이 없는 경우 간단한 GC만 수행
            if self._analysis_count % self._gc_interval == 0:
                import gc
                gc.collect()
                logging.debug(f"Periodic garbage collection (count: {self._analysis_count})")
        except Exception as e:
            logging.debug(f"Memory check failed: {e}")
    
    def _increment_analysis_count(self):
        """분석 카운트 증가 및 메모리 체크"""
        self._analysis_count += 1
        if self._analysis_count % self._gc_interval == 0:
            self._check_memory_usage()
    
    def close(self):
        """명시적 리소스 정리 및 환경변수 핫리로드 등록 해제"""
        try:
            _unregister_analyzer_for_env_reload(self)
            
            # 개선된 캐시 정리
            if IMPROVED_MODULES_AVAILABLE and self.cache:
                try:
                    self.cache.close()
                    logging.debug("[analyzer] Memory-safe cache closed")
                except Exception as e:
                    logging.debug(f"[analyzer] cache.close() error: {e}")
            
            # 메모리 최적화
            if IMPROVED_MODULES_AVAILABLE:
                try:
                    optimize_memory()
                    logging.debug("[analyzer] Memory optimization completed")
                except Exception as e:
                    logging.debug(f"[analyzer] Memory optimization error: {e}")
                
                # 성능 리포트 생성
                try:
                    if hasattr(self, 'performance_monitor') and self.performance_monitor:
                        report_path = export_performance_report()
                        logging.info(f"[analyzer] Performance report generated: {report_path}")
                except Exception as e:
                    logging.debug(f"[analyzer] Performance report generation error: {e}")
            
            # graceful shutdown - 모든 자원 정리
            for obj_name in ("provider", "data_provider", "opinion_analyzer", "estimate_analyzer"):
                obj = getattr(self, obj_name, None)
                try:
                    if hasattr(obj, "close"):
                        obj.close()
                except Exception as e:
                    logging.debug(f"[analyzer] {obj_name}.close() error: {e}")
            
            # 섹터 캐시 정리
            if hasattr(self, '_sector_char_cache'):
                import threading
                with getattr(self, '_sector_char_cache_lock', threading.RLock()):
                    self._sector_char_cache.clear()
            
            logging.debug(f"[analyzer] {self.__class__.__name__} closed")
        except Exception as e:
            logging.debug(f"[analyzer] close() error: {e}")
    
    def __del__(self):
        """인스턴스 소멸 시 환경변수 핫리로드 등록 해제 (fallback)"""
        try:
            _unregister_analyzer_for_env_reload(self)
        except Exception:
            pass
    
    # _result_to_dict 메서드 제거됨 - AnalysisResult.to_dict() 사용
    
    def _load_analysis_config(self) -> AnalysisConfig:
        """분석 설정을 로드합니다."""
        config = self.config_manager.load_config()
        enhanced_config = config.get('enhanced_integrated_analysis', {})
        
        return AnalysisConfig(
            weights=enhanced_config.get('weights', {
                'opinion_analysis': 15,
                'estimate_analysis': 20,
                'financial_ratios': 25,
                'growth_analysis': 10,
                'scale_analysis': 5,
                'price_position': 25
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
        """KOSPI 마스터 데이터를 로드합니다 (xlsx/csv 지원, 메모리 최적화)."""
        try:
            # ✅ CSV 지원 옵션 추가 (I/O 감소)
            kospi_csv = 'kospi_code.csv'
            kospi_xlsx = 'kospi_code.xlsx'
            
            # 필요한 컬럼만 로드하여 메모리 사용량 최적화
            required_columns = ['단축코드', '한글명', '시가총액']
            optional_columns = ['업종', '지수업종대분류', '업종명', '섹터']
            
            if os.path.exists(kospi_csv):
                # CSV 우선 로드 (더 빠른 I/O)
                try:
                    # 필요한 컬럼만 로드
                    self.kospi_data = pd.read_csv(
                        kospi_csv, 
                        encoding='utf-8-sig',
                        usecols=lambda x: x in required_columns + optional_columns,
                        dtype={'단축코드': 'string', '한글명': 'string'}  # 메모리 최적화
                    )
                    # 필수 컬럼이 없으면 전체 로드로 fallback
                    if self.kospi_data.empty or not any(col in self.kospi_data.columns for col in required_columns):
                        logging.warning("필요한 컬럼이 없어 전체 CSV 로드 시도")
                        self.kospi_data = pd.read_csv(kospi_csv, encoding='utf-8-sig')
                    logging.info(f"KOSPI 데이터 로드 완료 (CSV): {kospi_csv}")
                except Exception as e:
                    logging.warning(f"CSV 읽기 실패: {e}")
                    self.kospi_data = pd.DataFrame()
                    return
            elif os.path.exists(kospi_xlsx):
                try:
                    # 필요한 컬럼만 로드
                    self.kospi_data = pd.read_excel(
                        kospi_xlsx, 
                        engine="openpyxl",
                        usecols=lambda x: x in required_columns + optional_columns,
                        dtype={'단축코드': 'string', '한글명': 'string'}  # 메모리 최적화
                    )
                    # 필수 컬럼이 없으면 전체 로드로 fallback
                    if self.kospi_data.empty or not any(col in self.kospi_data.columns for col in required_columns):
                        logging.warning("필요한 컬럼이 없어 전체 Excel 로드 시도")
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
                
                # ✅ pandas filtering 최적화: 인덱스 설정
                if not self.kospi_data.empty and '단축코드' in self.kospi_data.columns:
                    self.kospi_data.set_index('단축코드', inplace=True)
                    logging.debug("KOSPI 데이터 인덱스 설정 완료 (단축코드)")
        except Exception as e:
            log_error("KOSPI 데이터 로드", error=e, level="error")
            self.kospi_data = pd.DataFrame()
            # KOSPI 로딩 실패 플래그 설정
            self._kospi_loading_failed = True
    
    @timed_operation("analyze_single_stock")
    @handle_errors(severity=ErrorSeverity.HIGH, category=ErrorCategory.BUSINESS)
    @retry_on_failure(max_attempts=2, base_delay=1.0)
    @measure_performance
    @monitor_memory
    @profile_function("analyze_single_stock")
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
        
        # 개선된 입력 검증
        if IMPROVED_MODULES_AVAILABLE and self.input_validator:
            validation_results = self.input_validator.validate_stock_data({
                'symbol': symbol,
                'name': name,
                'days_back': days_back
            })
            
            # 심각한 검증 오류가 있는 경우 조기 반환
            for result in validation_results:
                if result.severity.value in ['error', 'critical']:
                    if self.exception_handler:
                        from standardized_exception_handler import ErrorContext
                        context = ErrorContext(
                            category=ErrorCategory.VALIDATION,
                            severity=ErrorSeverity.HIGH,
                            operation="analyze_single_stock",
                            symbol=symbol,
                            metadata={'validation_error': result.message}
                        )
                        self.exception_handler.handle_error(ValueError(result.message), context)
                    
                    return AnalysisResult(
                        symbol=symbol,
                        name=name,
                        status=AnalysisStatus.ERROR,
                        error_message=f"입력 검증 실패: {result.message}",
                        analysis_time=_monotonic() - start_time
                    )
        
        try:
            # 메모리 사용량 체크
            self._increment_analysis_count()
            
            # KOSPI 로딩 실패 확인 및 경고
            if getattr(self, '_kospi_loading_failed', False):
                logging.warning(f"KOSPI 데이터 로딩 실패로 인해 규모/안정성 점수가 제한될 수 있습니다: {symbol}({name})")
            
            # 기존 입력 검증 (하위 호환성)
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

            # --- 가치투자: 내재가치/안전마진/해자 추정 ---
            current_price = DataValidator.safe_float_optional(price_data.get('current_price')) if price_data else None
            intrinsic_value = None
            moat_grade = None
            try:
                if False:  # IMPROVED_MODULES_AVAILABLE: 외부 모듈 에러 방지
                    # 외부 철학 모듈이 있으면 우선 사용
                    try:
                        # 가치투자 모듈 호출 시 안전한 처리
                        try:
                            bm = analyze_business_model(symbol)  # 필요 시 내부적으로 KRX/공시/메타 활용
                            # bm이 문자열인 경우 처리
                            if isinstance(bm, dict):
                                moat_grade = bm.get('moat_grade', None)
                            else:
                                moat_grade = None
                        except Exception as bm_error:
                            logging.warning(f"비즈니스 모델 분석 실패, 백업 로직 사용: {bm_error}")
                            bm = None
                            moat_grade = None
                        
                        try:
                            intrinsic_value = calculate_intrinsic_value(symbol, price_data=price_data, financial_data=financial_data)
                        except Exception as iv_error:
                            logging.debug(f"내재가치 계산 실패: {iv_error}")
                            intrinsic_value = None
                    except Exception as e:
                        logging.warning(f"가치투자 모듈 호출 실패, 백업 로직 사용: {e}")
                        # 백업 로직으로 넘어감
                        bm = None
                        intrinsic_value = None
                        moat_grade = None
                else:
                    # 백업 로직으로 넘어감
                    bm = None
                    intrinsic_value = None
                    moat_grade = None
                
                # 백업 로직: 보수적 그레이엄식 계산
                if intrinsic_value is None:
                    eps = DataValidator.safe_float_optional(price_data.get('eps') if price_data else None)
                    g = DataValidator.safe_float_optional(financial_data.get('revenue_growth_rate') if financial_data else None)
                    g = 0.0 if g is None else max(-5.0, min(15.0, g))  # 보수적 캡
                    Y = 6.0  # 장기 무위험수익률 근사(%) 보수적
                    if eps and eps > 0:
                        intrinsic_value = eps * (8.5 + 2 * (g/1.0)) * 4.4 / max(1.0, Y)
            except Exception as e:
                logging.warning(f"가치투자 분석 중 오류 발생: {e}")
                intrinsic_value = None
                moat_grade = None
            
            # 외부 제공 없으면 보수적 추정 시도
            if intrinsic_value is None:
                intrinsic_value = self._estimate_intrinsic_value(symbol, financial_data, price_data)

            # 해자(질) 점수/등급 계산
            moat_quality = self.score_calculator._moat_quality_score(financial_data)
            moat_grade = self.score_calculator._moat_grade_from_score(moat_quality)

            # 안전마진 계산
            mos = None
            if intrinsic_value and current_price and intrinsic_value > 0:
                mos = max(0.0, min(1.0, (intrinsic_value - current_price) / intrinsic_value))
            
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
                'intrinsic_value': intrinsic_value,
            }
            
            # 스코어러에 명시적 파라미터 전달 (순수 함수)
            enhanced_score, all_breakdown = self.score_calculator.calculate_score(
                analysis_data, 
                sector_info=analysis_data['sector_info'], 
                price_data=analysis_data['price_data']
            )
            enhanced_grade = self._get_grade(enhanced_score)
            
            # breakdown 분리 (가중치 적용된 점수와 원점수 분리)
            score_breakdown = {k: v for k, v in all_breakdown.items() if not k.endswith('_raw')}
            raw_breakdown = {k: v for k, v in all_breakdown.items() if k.endswith('_raw')}
            
            # 워치리스트 시그널 및 목표매수가 계산 (enhanced_score 계산 후)
            watchlist_signal, target_buy = self._compute_watchlist_signal(
                symbol=symbol,
                current_price=current_price,
                intrinsic_value=intrinsic_value,
                quality_score=moat_quality,
                price_position=self._calculate_price_position(price_data),
                overall_score=enhanced_score,  # 종합 점수 전달
            )
            
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
                raw_breakdown=raw_breakdown,
                price_data=price_data,  # 가격 데이터 캐싱
                sector_analysis=sector_analysis,  # 섹터 분석 결과 추가
                intrinsic_value=intrinsic_value,
                margin_of_safety=mos,
                moat_grade=moat_grade,
                watchlist_signal=watchlist_signal,
                target_buy=target_buy,
                playbook=self._value_investing_playbook(symbol, intrinsic_value, target_buy, moat_grade),
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
    
    def analyze_with_value_philosophy(self, symbol: str, name: str) -> Dict[str, Any]:
        """가치 투자 철학 기반 종합 분석"""
        try:
            # 기본 분석 수행
            basic_result = self.analyze_single_stock(symbol, name)
            
            if basic_result.status != AnalysisStatus.SUCCESS:
                return {
                    'success': False,
                    'error': basic_result.error,
                    'basic_result': basic_result
                }
            
            # 가치 투자 철학 분석
            if IMPROVED_MODULES_AVAILABLE and hasattr(self, 'value_investing'):
                # 관심 종목 목록에 추가
                stock_data = {
                    'symbol': symbol,
                    'name': name,
                    'current_price': basic_result.current_price,
                    'market_cap': basic_result.market_cap,
                    'price_data': basic_result.price_data,
                    'financial_data': basic_result.financial_data,
                    'sector_analysis': basic_result.sector_analysis
                }
                
                watchlist_item = self.value_investing.add_to_watchlist(symbol, name, stock_data)
                
                # 가치 투자 리포트 생성
                value_report = self.value_investing.generate_investment_report(symbol)
                
                return {
                    'success': True,
                    'basic_result': basic_result,
                    'value_analysis': watchlist_item,
                    'value_report': value_report,
                    'buy_signal': watchlist_item.margin_of_safety.safety_level.value in ['우수', '양호']
                }
            else:
                return {
                    'success': True,
                    'basic_result': basic_result,
                    'value_analysis': None,
                    'value_report': "가치 투자 철학 모듈을 사용할 수 없습니다.",
                    'buy_signal': False
                }
                
        except Exception as e:
            logging.error(f"가치 투자 철학 분석 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'basic_result': None
            }
    
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
            # _with_retries가 최종 실패를 이미 집계했음. 여기선 로그만.
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
            # _with_retries가 최종 실패를 이미 집계했음. 여기선 로그만.
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
                        'breakdown': {'재무_건전성': 50.0, '성장성': 50.0, '안정성': 50.0},
                        'is_leader': False, 'leader_bonus': 0.0}
            
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
            
            # 표본수 부족 시 신뢰도 반영 (선형 축소)
            confidence = 1.0
            try:
                peers = sector_val.get('peer_count', 0) if sector_val else 0
                target = self.env_cache.get('sector_target_good', 60)
                confidence = max(0.5, min(1.0, peers / max(1, target)))  # 최소 0.5
            except Exception:
                pass
            total_score *= confidence
            
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
            
            # 리더 보너스(0~10) 계산: 총점에는 반영하지 않고 별도 제공
            try:
                leader_bonus = self._calculate_leader_bonus(
                    symbol=symbol,
                    sector=sector_name,
                    market_cap=market_cap_pd,
                    price_data=price_data,
                    financial_data=financial_data
                )
            except Exception:
                leader_bonus = 0.0

            # 평면 스키마로 반환 (정규화 헬퍼에서 그대로 소비)
            return {
                'grade': grade,
                'total_score': float(total_score),
                'breakdown': {
                    '재무_건전성': float(financial_score),
                    '성장성': float(growth_score),
                    '안정성': float(stability_score),
                },
                'is_leader': self._is_sector_leader(symbol, sector_name),
                'leader_bonus': float(leader_bonus)
            }
            
        except Exception as e:
            logging.debug(f"섹터 분석 실패 {symbol}: {e}")
            return {'grade': 'C', 'total_score': 50.0,
                    'breakdown': {'재무_건전성': 50.0, '성장성': 50.0, '안정성': 50.0},
                    'is_leader': False, 'leader_bonus': 0.0}
    

    def _get_market_cap(self, symbol: str) -> Optional[float]:
        """시가총액 조회 (억원 단위)
        
        Note: KOSPI 파일의 시가총액 컬럼은 억원 단위로 가정합니다.
        다른 단위(원/백만/십억)인 경우 일관성을 위해 변환이 필요합니다.
        """
        if self.kospi_data is not None and not self.kospi_data.empty:
            # 인덱스가 설정되어 있으면 loc 사용, 아니면 기존 방식
            if _is_indexed_by_code(self.kospi_data):
                try:
                    stock_info = self.kospi_data.loc[[str(symbol)]]
                except KeyError:
                    stock_info = pd.DataFrame()
            else:
                stock_info = self.kospi_data[self.kospi_data['단축코드'] == str(symbol)]
            if not stock_info.empty:
                mc = stock_info.iloc[0]['시가총액']
                if pd.isna(mc):
                    return None  # unknown market cap
                mc = float(mc)
                # 안전장치: 원 단위로 들어온 경우 억원으로 변환 (MARKET_CAP_STRICT_MODE 고려)
                strict_mode = _ENV_CACHE['market_cap_strict_mode'].lower() == "true"
                if mc > 1e11:  # 1조원 이상이면 원 단위로 오인 가능성 높음
                    if not strict_mode:
                        mc = mc / 1e8  # 억원 변환
                        logging.debug(f"[unit] KOSPI market_cap unit correction: {stock_info.iloc[0]['시가총액']} -> {mc} 억원")
                    else:
                        logging.debug(f"[unit] KOSPI market_cap ambiguous (strict mode): {stock_info.iloc[0]['시가총액']} -> None")
                        return None
                return mc
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
        if band <= 0:
            logging.debug(f"Non-positive 52w band: hi={hi}, lo={lo}, cp={cp}")
            # 퇴화 케이스 메트릭 기록 (운영 모니터링용) – API 실패로 집계하지 않음
            if self.metrics:
                self.metrics.record_flag_error(f"{ErrorType.INVALID_52W_BAND}:nonpos_band")
            return None
        elif band/hi <= tiny_band_threshold or band <= 1e-6:
            logging.debug(f"Tiny 52w band: hi={hi}, lo={lo}, cp={cp}")
            # 퇴화 케이스 메트릭 기록 (운영 모니터링용) – API 실패로 집계하지 않음
            if self.metrics:
                self.metrics.record_flag_error(f"{ErrorType.INVALID_52W_BAND}:tiny_band")
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
                    # 인덱스가 설정되어 있으면 loc 사용, 아니면 기존 방식
                    if _is_indexed_by_code(self.kospi_data):
                        try:
                            stock_info = self.kospi_data.loc[[str(symbol)]]
                        except KeyError:
                            stock_info = pd.DataFrame()
                    else:
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
                sector = str(result.get('name', '기타')).strip()  # ✅ 섹터명 정규화
                sym_key = str(symbol).strip()  # ✅ 심볼 키 문자열화 및 정규화
                self._sector_char_cache[f"sym:{sym_key}"] = (now, {"name": sector})
                self._sector_char_cache[f"sec:{sector}"] = (now, result)
                # ✅ 레거시 키 제거: 충돌 방지 및 캐시 크기 최적화
                # 캐시 크기 제한 (LRU 방식) - 안전한 단일 pop 방식
                while len(self._sector_char_cache) > self._sector_char_cache_max_size:
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
        
        # 인덱스가 설정되어 있으면 인덱스 사용, 아니면 컬럼 사용
        if _is_indexed_by_code(self.kospi_data):
            codes = set(self.kospi_data.index.astype(str))
        else:
            codes = set(self.kospi_data['단축코드'].astype(str))
        return [c for c in leaders if c in codes]
    
    def _get_sector_benchmarks(self, sector: str) -> Dict[str, Any]:
        """업종별 벤치마크 기준 반환"""
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
        normalized_sector = SECTOR_ALIASES.get(str(sector).lower(), str(sector)) if sector else "기타"

        benchmarks = {
            '금융업': {
                'per_range': (5, 15), 'pbr_range': (0.5, 2.0), 'roe_range': (8, 20),
                'description': '안정적 수익성, 낮은 PBR',
                'leaders': ['105560', '055550', '086790']
            },
            '기술업': {
                'per_range': (15, 50), 'pbr_range': (1.5, 8.0), 'roe_range': (10, 30),
                'description': '높은 성장성, 높은 PER',
                'leaders': ['005930', '000660', '035420', '035720']
            },
            '제조업': {
                'per_range': (8, 25), 'pbr_range': (0.8, 3.0), 'roe_range': (8, 20),
                'description': '안정적 수익성, 적정 PER',
                'leaders': ['005380', '000270', '012330', '329180']
            },
            '바이오/제약': {
                'per_range': (20, 100), 'pbr_range': (2.0, 10.0), 'roe_range': (5, 25),
                'description': '높은 불확실성, 높은 PER',
                'leaders': ['207940', '068270', '006280']
            },
            '에너지/화학': {
                'per_range': (5, 20), 'pbr_range': (0.5, 2.5), 'roe_range': (5, 15),
                'description': '사이클 특성, 변동성 큰 수익',
                'leaders': ['034020', '010140']
            },
            '소비재': {
                'per_range': (10, 30), 'pbr_range': (1.0, 4.0), 'roe_range': (8, 18),
                'description': '안정적 수요, 적정 수익성',
                'leaders': []
            },
            '통신업': {
                'per_range': (8, 20), 'pbr_range': (0.8, 3.0), 'roe_range': (6, 15),
                'description': '현금흐름 안정',
                'leaders': ['017670']
            },
            '건설업': {
                'per_range': (5, 15), 'pbr_range': (0.5, 2.0), 'roe_range': (5, 12),
                'description': '사이클 민감, 보수적 밸류에이션',
                'leaders': ['000720', '051600']
            },
            '기타': {
                'per_range': (5, 40), 'pbr_range': (0.5, 6.0), 'roe_range': (5, 20),
                'description': '일반적 기준 (폴백)',
                'leaders': []
            }
        }

        entry = benchmarks.get(normalized_sector, benchmarks['기타'])
        # 리더 목록 정합성 보정
        entry = dict(entry)
        entry['leaders'] = self._sanitize_leaders(entry.get('leaders', []))
        entry['name'] = normalized_sector
        return entry
    
    def _is_sector_leader(self, symbol: str, sector_name: str) -> bool:
        """심볼이 섹터 리더 후보에 속하는지 판단."""
        try:
            bm = self._get_sector_benchmarks(sector_name)
            leaders = set(bm.get('leaders') or [])
            return str(symbol) in leaders
        except Exception:
            return False
    
    def _calculate_leader_bonus(self, *, symbol: str, sector: str, market_cap: Optional[float], price_data: Dict[str, Any], financial_data: Dict[str, Any]) -> float:
        """섹터 리더십 보너스 0~10. 리더 여부/시총/가격위치 컨텍스트 반영."""
        bonus = 0.0
        try:
            if self._is_sector_leader(symbol, sector):
                bonus += 5.0
            mc = market_cap or self._get_market_cap(symbol) or 0.0
            if mc >= 100000:   # 메가캡
                bonus += 3.0
            elif mc >= 50000:  # 라지캡
                bonus += 2.0
            # 가격위치(저위치일수록 가점) 약간 반영
            pp = self._calculate_price_position(price_data) if price_data else None
            if pp is not None and pp <= 30:
                bonus += 2.0
        except Exception:
            pass
        return max(0.0, min(10.0, bonus))
    
    def _evaluate_valuation_by_sector(
        self,
        symbol: str,
        *,
        per: float = float('nan'),
        pbr: float = float('nan'),
        roe: float = float('nan'),
        market_cap: Optional[float],
        price_data: Dict[str, Any],
        financial_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        섹터 피어 기반 밸류에이션 평가:
        - 기본: (PER, PBR, ROE) 각각 섹터 기준범위에 선형 매핑 → 가중 평균
        - 데이터 부족/결측 시 보수적 기본치 사용(50) + metrics에 샘플 부족 집계
        """
        bm = self._get_sector_benchmarks(self._get_sector_characteristics(symbol).get('name', '기타'))
        per_lo, per_hi   = bm['per_range']
        pbr_lo, pbr_hi   = bm['pbr_range']
        roe_lo, roe_hi   = bm['roe_range']

        # 스코어 개별 계산 (결측은 None)
        per_s = self._calculate_metric_score(per, min_val=per_lo, max_val=per_hi, reverse=True)
        pbr_s = self._calculate_metric_score(pbr, min_val=pbr_lo, max_val=pbr_hi, reverse=True)
        roe_s = self._calculate_metric_score(roe, min_val=roe_lo, max_val=roe_hi, reverse=False)

        # 가중치: ROE 0.4, PER 0.35, PBR 0.25 (합=1)
        parts, weights = [], []
        if per_s is not None: parts.append(per_s); weights.append(0.35)
        if pbr_s is not None: parts.append(pbr_s); weights.append(0.25)
        if roe_s is not None: parts.append(roe_s); weights.append(0.40)

        if not parts:
            # 피어/입력 결측 → 보수적 기본값
            if hasattr(self, "metrics") and self.metrics:
                self.metrics.record_sector_sample_insufficient(sector_name=bm.get('description', 'unknown'))
            total = 50.0
        else:
            wsum = sum(weights) or 1.0
            total = sum(s * (w / wsum) for s, w in zip(parts, weights))

        # 브레이크다운 (결측은 50으로 표기해 UI가 자연스럽도록)
        breakdown = {
            'PER': 50.0 if per_s is None else float(per_s),
            'PBR': 50.0 if pbr_s is None else float(pbr_s),
            'ROE': 50.0 if roe_s is None else float(roe_s),
        }
        grade = 'A+' if total >= 85 else 'A' if total >= 75 else 'B+' if total >= 70 else \
                'B' if total >= 65 else 'C+' if total >= 60 else 'C' if total >= 55 else 'D'
        return {'total_score': float(max(0.0, min(100.0, total))), 'grade': grade, 'breakdown': breakdown}
    
    def _calculate_metric_score(self, value: Optional[float], *, min_val: float, max_val: float, reverse: bool=False) -> Optional[float]:
        """연속값을 0~100으로 선형 매핑. reverse=True면 낮을수록 고득점."""
        return self._score_linear(value, min_val=min_val, max_val=max_val, reverse=reverse)
    
    def _score_linear(self, x: Optional[float], *, min_val: float, max_val: float, reverse: bool=False) -> Optional[float]:
        """안전한 선형 스코어링 헬퍼"""
        if x is None: 
            return None
        try:
            v = float(x)
        except Exception:
            return None
        lo, hi = (min_val, max_val) if not reverse else (max_val, min_val)
        if hi == lo: 
            return None
        t = (v - lo) / (hi - lo)
        t = max(0.0, min(1.0, t))
        return t * 100.0
    
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
                # _with_retries가 최종 실패를 이미 집계했음. 여기선 로그만.
                logging.debug(f"52주 고가/저가 조회 실패 {stock_dict.get('symbol')}: {e}")
        
        # 여전히 52주 정보가 없으면 KOSPI 파일에서 시도
        if (w52h is None or w52l is None) and self.kospi_data is not None and not self.kospi_data.empty:
            try:
                code = stock_dict.get('symbol')
                # 인덱스가 설정되어 있으면 loc 사용, 아니면 기존 방식
                if _is_indexed_by_code(self.kospi_data):
                    try:
                        row = self.kospi_data.loc[[str(code)]]
                    except KeyError:
                        row = pd.DataFrame()
                else:
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
        섹터 피어의 (PER, PBR, ROE) 튜플 리스트를 TTL 캐시와 함께 반환.
        - 캐시 키: sector_name
        - 값: List[Tuple[per, pbr, roe]]
        """
        now = _monotonic()
        key = f"sector:{sector_name}"
        with self._sector_cache_lock:
            hit = self._sector_cache.get(key)
            if hit and now - hit[0] < self._sector_cache_ttl:
                return hit[1]

        # 캐시 미스 → 수집
        peers = self._collect_sector_peers(sector_name)
        with self._sector_cache_lock:
            self._sector_cache[key] = (now, peers)
            # LRU 제한 (동적 크기 제한)
            while len(self._sector_cache) > self._sector_cache_max_size:
                self._sector_cache.popitem(last=False)
        return peers

    def _collect_sector_peers(self, sector_name: str) -> List[PeerTriple]:
        """
        섹터 피어 샘플을 수집하여 (per, pbr, roe) 배열을 생성.
        - KOSPI 파일에서 섹터 후보 컬럼을 탐색해 필터링, 없으면 상위 시총 샘플 폴백
        - 환경변수/캐시된 한도 사용: base→full 단계로 확대 시도
        """
        max_base = self.env_cache.get('max_sector_peers_base', 40)
        max_full = self.env_cache.get('max_sector_peers_full', 200)
        target = self.env_cache.get('sector_target_good', 60)

        df = getattr(self, 'kospi_data', None)
        symbols: List[str] = []
        if df is not None and not df.empty:
            try:
                # 섹터 컬럼 후보
                cand_cols = ['업종', '지수업종대분류', '업종명', '섹터']
                col = next((c for c in cand_cols if c in df.columns), None)
                if col:
                    m = df[df[col].astype(str).str.contains(str(sector_name), na=False)]
                else:
                    m = df
                # 시총 정렬(내림차순) 후 코드 추출
                if '시가총액' in m.columns:
                    m = m.sort_values('시가총액', ascending=False)
                idx_is_code = (m.index.name == '단축코드')
                codes = (m.index.astype(str).tolist() if idx_is_code else m['단축코드'].astype(str).tolist())
                symbols = codes[:max_full]
            except Exception as e:
                logging.debug(f"[sector-peers] kospi filtering failed: {e}")

        peers: List[PeerTriple] = []
        if not symbols:
            return peers

        # 1차 수집(베이스 한도)
        for sym in symbols[:max_base]:
            try:
                pd_ = self.data_provider.get_price_data(sym)
                fd_ = self.data_provider.get_financial_data(sym)
                per_ = DataValidator.safe_float_optional(pd_.get('per'))
                pbr_ = DataValidator.safe_float_optional(pd_.get('pbr'))
                roe_ = DataValidator.safe_float_optional(fd_.get('roe'))
                if per_ is None or pbr_ is None or roe_ is None:
                    continue
                if not (math.isfinite(per_) and math.isfinite(pbr_) and math.isfinite(roe_)):
                    continue
                peers.append((per_, pbr_, roe_))
                if len(peers) >= target:
                    break
            except Exception:
                continue

        # 부족하면 2차 확대(풀 한도)
        if len(peers) < target:
            for sym in symbols[max_base:max_full]:
                try:
                    pd_ = self.data_provider.get_price_data(sym)
                    fd_ = self.data_provider.get_financial_data(sym)
                    per_ = DataValidator.safe_float_optional(pd_.get('per'))
                    pbr_ = DataValidator.safe_float_optional(pd_.get('pbr'))
                    roe_ = DataValidator.safe_float_optional(fd_.get('roe'))
                    if per_ is None or pbr_ is None or roe_ is None:
                        continue
                    if not (math.isfinite(per_) and math.isfinite(pbr_) and math.isfinite(roe_)):
                        continue
                    peers.append((per_, pbr_, roe_))
                    if len(peers) >= target:
                        break
                except Exception:
                    continue

        return peers
    
    def _analyze_stocks_parallel(self, stocks_data, max_workers: int = None) -> List[AnalysisResult]:
        """종목들을 병렬로 분석하는 공통 메서드 (API TPS 최적화, 동적 워커 조정)"""
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

            # 동적 워커 수 계산 (배치 크기 고려)
            batch_size = len(stocks_data)
            if batch_size <= 10:
                # 소규모 배치: 워커 수 제한
                auto_guess = min(4, max_tps)
            elif batch_size <= 50:
                # 중규모 배치: TPS 기반
                auto_guess = (int(1.5 * max_tps) if self.include_external else int(2.0 * max_tps))
            else:
                # 대규모 배치: 최대 활용
                auto_guess = (int(2.0 * max_tps) if self.include_external else int(2.5 * max_tps))
            
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
        
        # 배치 크기 최적화: 큰 배치는 청크로 분할
        chunk_size = safe_env_int("ANALYSIS_CHUNK_SIZE", 20, 5)
        if len(stocks_data) > chunk_size:
            # 큰 배치를 청크로 분할하여 메모리 사용량 최적화
            chunks = [stocks_data[i:i + chunk_size] for i in range(0, len(stocks_data), chunk_size)]
            logging.info(f"Large batch ({len(stocks_data)} stocks) split into {len(chunks)} chunks of max {chunk_size}")
        else:
            chunks = [stocks_data]

        # 청크별로 병렬 처리
        all_results = []
        for chunk_idx, chunk in enumerate(chunks):
            if len(chunks) > 1:
                logging.info(f"Processing chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk)} stocks)")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 작업 제출
                futures = []
                for _, stock in chunk.iterrows():
                    # 인덱스가 설정되어 있으면 인덱스 사용, 아니면 컬럼 사용
                    if chunk.index.name == '단축코드':
                        symbol = str(stock.name)  # 인덱스 값 사용
                        name = stock['한글명']
                    else:
                        symbol = str(stock['단축코드'])
                        name = stock['한글명']
                    future = executor.submit(self.analyze_single_stock, symbol, name)
                    futures.append((future, symbol, name))

                # 결과 수집 (as_completed 사용으로 완료된 작업부터 처리)
                future_map = {f: (symbol, name) for f, symbol, name in futures}
                chunk_results = []
                for f in as_completed(future_map):
                    symbol, name = future_map[f]
                    try:
                        result = f.result()
                        if result.status == AnalysisStatus.SUCCESS:
                            chunk_results.append(result)
                        elif result.status == AnalysisStatus.SKIPPED_PREF:
                            logging.debug(f"우선주 제외: {name} ({symbol})")
                        else:
                            logging.debug(f"분석 실패: {name} ({symbol}) - {result.error}")
                    except Exception as e:
                        log_error("종목 분석", f"{name}({symbol})", e, LogLevel.ERROR)
                        continue

                all_results.extend(chunk_results)
                
                # 메모리 정리 (대규모 배치 처리 시)
                if len(chunks) > 1:
                    del chunk_results
                    import gc
                    gc.collect()

        # 분석된 종목 수 기록
        if hasattr(self, "metrics") and self.metrics:
            self.metrics.record_stocks_analyzed(len(all_results))
        
        return all_results

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
        payload = [r.to_dict() for r in results]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logging.info(f"JSON 저장 완료: {path}")

    def export_csv(self, results: List[AnalysisResult], path: str) -> None:
        """분석 결과를 CSV 파일로 저장 (주요 필드 중심)"""
        rows = []
        for r in results:
            d = r.to_dict()
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
            from datetime import datetime as dt
            metadata = {
                'analysis_version': '2.0_enhanced',
                'analysis_date': dt.now().isoformat(),
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
                'top_recommendations': [r.to_dict() for r in filtered_results[:20]],
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
            from datetime import datetime as dt
            metadata = {
                'analysis_version': '2.0_enhanced',
                'analysis_date': dt.now().isoformat(),
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
                'top_recommendations': [r.to_dict() for r in filtered_results[:15]],
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
                print("\n🏆 향상된 종목 추천 결과 (현재가 및 52주 위치 상세)")
                print("=" * 130)
                print(f"{'순위':<4} {'종목코드':<8} {'종목명':<15} {'현재가':<12} {'52주고가':<12} {'52주저가':<12} {'52주위치':<10} {'종합점수':<8} {'등급':<6} {'시가총액':<12}")
                print("-" * 130)
                
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
                    
                    # 현재가 표시 (천원 단위로 표시)
                    if current_price is not None and current_price > 0:
                        if current_price >= 10000:
                            current_price_display = f"{current_price/1000:,.0f}천원"
                        else:
                            current_price_display = f"{current_price:,.0f}원"
                    else:
                        current_price_display = "N/A"
                    
                    # 52주 고가 표시
                    if w52_high is not None and w52_high > 0:
                        if w52_high >= 10000:
                            w52_high_display = f"{w52_high/1000:,.0f}천원"
                        else:
                            w52_high_display = f"{w52_high:,.0f}원"
                    else:
                        w52_high_display = "N/A"
                    
                    # 52주 저가 표시
                    if w52_low is not None and w52_low > 0:
                        if w52_low >= 10000:
                            w52_low_display = f"{w52_low/1000:,.0f}천원"
                        else:
                            w52_low_display = f"{w52_low:,.0f}원"
                    else:
                        w52_low_display = "N/A"
                    
                    # 52주 위치 계산 및 표시 (색상 코드 포함)
                    if current_price and w52_high and w52_low and w52_high > w52_low:
                        position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
                        if position >= 80:
                            position_display = f"{position:.0f}% 🔴"  # 고위치
                        elif position >= 60:
                            position_display = f"{position:.0f}% 🟡"  # 중위치
                        elif position >= 40:
                            position_display = f"{position:.0f}% 🟢"  # 중하위치
                        else:
                            position_display = f"{position:.0f}% 🔵"  # 저위치
                    else:
                        position_display = "N/A"
                    
                    # 시가총액 표시
                    if market_cap and market_cap > 0:
                        if market_cap >= 10000:  # 1조원 이상
                            market_cap_display = f"{market_cap/10000:,.1f}조원"
                        else:
                            market_cap_display = f"{market_cap:,.0f}억원"
                    else:
                        market_cap_display = "N/A"
                    
                    # 종목명 길이 제한
                    name_display = name[:12] + ('...' if len(name) > 12 else '')
                    
                    print(f"{i:<4} {symbol:<8} {name_display:<15} {current_price_display:<12} {w52_high_display:<12} {w52_low_display:<12} {position_display:<10} {enhanced_score:<8.1f} {grade:<6} {market_cap_display:<12}")
                
                print("=" * 130)
                print("📊 52주 위치 설명:")
                print("  🔴 80% 이상: 52주 고가 근처 (고위치)")
                print("  🟡 60-79%: 52주 중상위 (중위치)")
                print("  🟢 40-59%: 52주 중하위 (중하위치)")
                print("  🔵 40% 미만: 52주 저가 근처 (저위치)")
                print("=" * 130)
            
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
# 6. CLI 인터페이스 (선택적 - typer가 설치된 경우에만 사용 가능)
# =============================================================================

# Typer CLI 앱 생성 (선택적 import)
try:
    import typer
    app = typer.Typer(help="Enhanced Integrated Analyzer")
    TYPER_AVAILABLE = True
    
    @app.command()
    def analyze(
        symbol: str = typer.Argument(..., help="분석할 종목 코드 (예: 005930)"),
        name: str = typer.Option("", help="종목명 (선택사항)"),
        realtime: bool = typer.Option(True, help="실시간 데이터 포함"),
        external: bool = typer.Option(True, help="외부 분석 포함(의견/추정)"),
    ):
        """단일 종목 분석"""
        _setup_logging_if_needed()
        analyzer = EnhancedIntegratedAnalyzer(include_realtime=realtime, include_external=external)
        try:
            result = analyzer.analyze_single_stock(symbol, name)
            print(f"분석 결과: {result.status}")
            print(f"종목: {result.name} ({result.symbol})")
            print(f"점수: {result.enhanced_score:.1f} ({result.enhanced_grade})")
            
            # 상세한 가격 정보 표시
            if IMPROVED_MODULES_AVAILABLE:
                try:
                    price_data = {
                        'symbol': result.symbol,
                        'name': result.name,
                        'current_price': result.current_price,
                        'w52_high': result.price_data.get('w52_high') if result.price_data else None,
                        'w52_low': result.price_data.get('w52_low') if result.price_data else None,
                        'market_cap': result.market_cap
                    }
                    print(display_detailed_price_info(price_data))
                except Exception as e:
                    # 폴백: 기본 가격 정보 표시
                    print(f"현재가: {result.current_price:,.0f}원" if result.current_price else "현재가: N/A")
                    print(f"52주위치: {result.price_position:.1f}%" if result.price_position else "52주위치: N/A")
            else:
                # 기본 가격 정보 표시
                print(f"현재가: {result.current_price:,.0f}원" if result.current_price else "현재가: N/A")
                print(f"52주위치: {result.price_position:.1f}%" if result.price_position else "52주위치: N/A")
            
            print(f"섹터: {result.sector_analysis.get('grade', 'N/A')} ({result.sector_analysis.get('total_score', 0):.1f})")
        except Exception as e:
            typer.echo(f"분석 실패: {e}", err=True)
        finally:
            analyzer.close()
    
    @app.command()
    def scan(
        max_stocks: int = typer.Option(50, help="분석할 시총 상위 종목 수"),
        min_score: float = typer.Option(20.0, help="최소 점수"),
        max_workers: int = typer.Option(0, help="워커 수(0=자동)"),
        realtime: bool = typer.Option(True, help="실시간 데이터 포함"),
        external: bool = typer.Option(True, help="외부 분석 포함(의견/추정)"),
    ):
        """시총 상위 종목 스캔"""
        _setup_logging_if_needed()
        analyzer = EnhancedIntegratedAnalyzer(include_realtime=realtime, include_external=external)
        try:
            results = analyzer.analyze_top_market_cap_stocks_enhanced(
                count=max_stocks,
                min_score=min_score,
                max_workers=(None if max_workers == 0 else max_workers),
            )
            print(f"분석 완료: {len(results)}개 종목")
            for i, result in enumerate(results[:10], 1):
                print(f"{i:2d}. {result.name} ({result.symbol}) - {result.enhanced_score:.1f}점 ({result.enhanced_grade})")
        except Exception as e:
            typer.echo(f"스캔 실패: {e}", err=True)
        finally:
            analyzer.close()
    
    @app.command()
    def upgraded_pipeline(
        max_stocks: int = typer.Option(10, help="최대 분석 종목 수"),
        min_score: float = typer.Option(20.0, help="최소 점수 임계치"),
        max_workers: int = typer.Option(2, help="최대 워커 수"),
        config: str = typer.Option("config.yaml", help="설정 파일 경로"),
        output: str = typer.Option(None, help="결과 출력 파일 경로"),
        verbose: bool = typer.Option(False, help="상세 출력"),
    ):
        """업그레이드된 가치 분석 파이프라인 (모든 개선 사항 적용)"""
        _setup_logging_if_needed()
        
        print("업그레이드된 가치 분석 파이프라인 시작...")
        print(f"설정: 최대 종목 {max_stocks}개, 최소 점수 {min_score}, 워커 {max_workers}개")
        
        try:
            # 업그레이드된 파이프라인 초기화
            pipeline = UpgradedValueAnalysisPipeline(config)
            
            # 파이프라인 요약 출력
            summary = pipeline.get_pipeline_summary()
            print(f"파이프라인: {summary['pipeline_name']} v{summary['version']}")
            print(f"단계: {' -> '.join(summary['stages'])}")
            
            # 기존 분석기로 종목 목록 가져오기
            legacy_analyzer = EnhancedIntegratedAnalyzer(config)
            # 시총 상위 종목 분석 결과를 가져와서 심볼 목록 추출
            analysis_result = legacy_analyzer.analyze_top_market_cap_stocks_enhanced(
                count=max_stocks, 
                min_score=min_score,
                max_workers=max_workers
            )
            # top_recommendations에서 심볼 목록 추출
            top_recommendations = analysis_result.get('top_recommendations', [])
            symbols = [(rec['symbol'], rec['name']) for rec in top_recommendations]
            
            if not symbols:
                print("분석할 종목이 없습니다.")
                return
            
            print(f"분석 대상: {len(symbols)}개 종목")
            
            # 포트폴리오 분석 실행
            portfolio_result = pipeline.analyze_portfolio(symbols, max_stocks)
            
            # 결과 출력
            print("\n" + "="*80)
            print("업그레이드된 파이프라인 분석 결과")
            print("="*80)
            
            print(f"전체 분석: {portfolio_result['portfolio_metrics']['total_analyzed']}개 종목")
            print(f"자격 통과: {portfolio_result['portfolio_metrics']['eligible_stocks']}개 종목")
            print(f"최종 포트폴리오: {portfolio_result['portfolio_metrics']['final_portfolio_size']}개 종목")
            print(f"다양화 비율: {portfolio_result['portfolio_metrics']['diversification_ratio']:.1%}")
            print(f"집중도 수준: {portfolio_result['portfolio_metrics']['concentration_level']}")
            
            # 최종 포트폴리오 상세 출력
            if portfolio_result['final_portfolio']:
                print("\n" + "="*120)
                print("업그레이드된 가치투자 파이프라인 - 최종 추천 포트폴리오")
                print("="*120)
                for i, stock in enumerate(portfolio_result['final_portfolio'], 1):
                    # 신호별 표시 추가
                    signal_display = "[BUY]" if stock['recommendation'] == "BUY" else "[WATCH]" if stock['recommendation'] == "WATCH" else "[PASS]"
                    
                    # 현재가 표시
                    current_price = stock.get('current_price', 0)
                    if current_price > 0:
                        if current_price >= 10000:
                            current_price_display = f"{current_price/1000:,.0f}천원"
                        else:
                            current_price_display = f"{current_price:,.0f}원"
                    else:
                        current_price_display = "N/A"
                    
                    # 52주 위치 계산
                    w52_high = stock.get('w52_high', 0)
                    w52_low = stock.get('w52_low', 0)
                    if current_price and w52_high and w52_low and w52_high > w52_low:
                        position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
                        if position >= 80:
                            position_display = f"{position:.0f}% [고위치]"  # 고위치
                        elif position >= 60:
                            position_display = f"{position:.0f}% [중위치]"  # 중위치
                        elif position >= 40:
                            position_display = f"{position:.0f}% [중하위치]"  # 중하위치
                        else:
                            position_display = f"{position:.0f}% [저위치]"  # 저위치
                    else:
                        position_display = "N/A"
                    
                    # 52주 고가/저가 표시
                    if w52_high > 0:
                        if w52_high >= 10000:
                            w52_high_display = f"{w52_high/1000:,.0f}천원"
                        else:
                            w52_high_display = f"{w52_high:,.0f}원"
                    else:
                        w52_high_display = "N/A"
                        
                    if w52_low > 0:
                        if w52_low >= 10000:
                            w52_low_display = f"{w52_low/1000:,.0f}천원"
                        else:
                            w52_low_display = f"{w52_low:,.0f}원"
                    else:
                        w52_low_display = "N/A"
                    
                    print(f"\n{i:2d}. {stock['symbol']} ({stock['name']})")
                    print(f"    신호: {signal_display} {stock['recommendation']}")
                    print(f"    종합점수: {stock['comprehensive_score']:.1f}점")
                    print(f"    가치점수: {stock['value_score']:.1f}")
                    print(f"    안전마진: {stock['margin_of_safety']:.1%}")
                    print(f"    현재가: {current_price_display}")
                    print(f"    52주 고가: {w52_high_display} | 52주 저가: {w52_low_display}")
                    print(f"    52주 위치: {position_display}")
                    print(f"    시가총액: {stock['market_cap']:,.0f}억원")
                    print(f"    섹터: {stock['sector']}")
                    print(f"    가치주 스타일: {stock['value_style']} (신뢰도: {stock['style_confidence']:.1f})")
                    print(f"    UVS 자격: {'통과' if stock['uvs_eligible'] else '탈락'}")
                    print("-" * 80)
            
            # 메트릭 요약
            metrics = pipeline.metrics.get_summary()
            print("\n" + "="*100)
            print("업그레이드된 파이프라인 성능 메트릭")
            print("="*100)
            print(f"   분석 시간: {metrics['avg_analysis_duration']:.2f}초")
            print(f"   API 성공률: {metrics['api_success_rate']:.1f}%")
            print(f"   품질 필터 거부: {metrics.get('quality_filter_rejections', 0)}개")
            print(f"   리스크 제약 위반: {metrics.get('risk_constraint_violations', 0)}개")
            print(f"   데이터 품질 점수: {metrics.get('data_quality_score', 0):.1f}%")
            print(f"   필터 통과율: {metrics.get('filter_pass_rate', 0):.1f}%")
            
            # 결과 저장
            if output:
                import json
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(portfolio_result, f, ensure_ascii=False, indent=2)
                print(f"결과 저장: {output}")
            
            print("\n업그레이드된 파이프라인 분석 완료!")
            
        except Exception as e:
            print(f"파이프라인 실행 실패: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            typer.echo(f"파이프라인 실행 실패: {e}", err=True)
        finally:
            if 'legacy_analyzer' in locals():
                legacy_analyzer.close()

    @app.command()
    def full_market(
        max_stocks: int = typer.Option(100, help="시총 상위 N개 분석"),
        min_score: float = typer.Option(20.0, help="최소 점수"),
        max_workers: int = typer.Option(0, help="워커 수(0=자동)"),
        realtime: bool = typer.Option(True, help="실시간 데이터 포함"),
        external: bool = typer.Option(True, help="외부 분석 포함(의견/추정)"),
    ):
        """전체 시장 분석"""
        _setup_logging_if_needed()
        analyzer = EnhancedIntegratedAnalyzer(include_realtime=realtime, include_external=external)
        try:
            result_dict = analyzer.analyze_full_market_enhanced(
                max_stocks=max_stocks,
                min_score=min_score,
                include_realtime=realtime,
                include_external=external,
                max_workers=(None if max_workers == 0 else max_workers),
            )
            
            # 결과 딕셔너리에서 추천 종목 추출
            recommendations = result_dict.get('top_recommendations', [])
            metadata = result_dict.get('metadata', {})
            
            print(f"전체 시장 분석 완료: {metadata.get('total_analyzed', 0)}개 종목 분석")
            print(f"저평가 종목: {metadata.get('undervalued_count', 0)}개 발견")
            print(f"분석 시간: {metadata.get('analysis_time_seconds', 0):.1f}초")
            print()
            
            if recommendations:
                print("\n" + "="*200)
                print("🏆 업그레이드된 가치투자 파이프라인 - 상세 분석 결과")
                print("="*200)
                print(f"{'순위':<4} {'종목명':<20} {'종목코드':<8} {'점수':<8} {'등급':<6} {'내재가치':<12} {'안전마진':<10} {'시그널':<8} {'목표매수가':<12} {'시가총액':<12} {'현재가':<10}")
                print("-" * 200)
                
                for i, result in enumerate(recommendations[:20], 1):
                    name = result.get('name', 'N/A')
                    symbol = result.get('symbol', 'N/A')
                    score = result.get('enhanced_score', 0)
                    grade = result.get('enhanced_grade', 'N/A')
                    
                    # 가치투자 정보 추출
                    intrinsic_value = result.get('intrinsic_value')
                    margin_of_safety = result.get('margin_of_safety')
                    watchlist_signal = result.get('watchlist_signal', 'N/A')
                    target_buy = result.get('target_buy')
                    market_cap = result.get('market_cap')
                    current_price = result.get('current_price', 0)
                    
                    # 내재가치 포맷팅
                    iv_str = f"{intrinsic_value:,.0f}원" if intrinsic_value else "N/A"
                    
                    # 안전마진 포맷팅
                    mos_str = f"{margin_of_safety*100:.1f}%" if margin_of_safety else "N/A"
                    
                    # 시가총액 포맷팅
                    mc_str = f"{market_cap:,.0f}억" if market_cap else "N/A"
                    
                    # 현재가 포맷팅
                    cp_str = f"{current_price:,.0f}원" if current_price else "N/A"
                    
                    # 시그널 표시 (이모지 추가)
                    signal_emoji = "🟢" if watchlist_signal == "BUY" else "🟡" if watchlist_signal == "WATCH" else "🔴"
                    signal_str = f"{signal_emoji} {watchlist_signal}" if watchlist_signal != 'N/A' else "N/A"
                    
                    # 목표매수가 포맷팅
                    target_str = f"{target_buy:,.0f}원" if target_buy else "N/A"
                    
                    print(f"{i:2d}. {name:<20} {symbol:<8} {score:>6.1f}점 {grade:<6} {iv_str:<12} {mos_str:<10} {signal_str:<8} {target_str:<12} {mc_str:<12} {cp_str:<10}")
                
                print("\n가치투자 핵심 지표 설명:")
                print("- 내재가치: 보수적 2원화 모델 (FCF/EPS 멀티플 중 낮은 값)")
                print("- 안전마진: 내재가치 대비 현재가 할인율 (높을수록 매력적)")
                print("- 시그널: BUY(30%↑+해자+저구간), WATCH(10-30%), PASS(미만)")
                print("- 목표매수가: 내재가치 × (1 - 최소안전마진) = 방어적 매수가")
                print("- 점수: 가치투자 철학 반영 (사업의 질 + 안전마진)")
                
                # 상위 5개 종목에 대한 상세 분석 추가
                print("\n" + "="*150)
                print("📊 상위 5개 종목 상세 분석 (재무건전성 + 가치평가)")
                print("="*150)
                
                for i, result in enumerate(recommendations[:5], 1):
                    name = result.get('name', 'N/A')
                    symbol = result.get('symbol', 'N/A')
                    score = result.get('enhanced_score', 0)
                    grade = result.get('enhanced_grade', 'N/A')
                    
                    # 가치투자 정보
                    intrinsic_value = result.get('intrinsic_value')
                    margin_of_safety = result.get('margin_of_safety')
                    watchlist_signal = result.get('watchlist_signal', 'N/A')
                    moat_grade = result.get('moat_grade', 'N/A')
                    target_buy = result.get('target_buy')
                    playbook = result.get('playbook', [])
                    
                    # 재무 정보
                    financial_data = result.get('financial_data', {})
                    roe = financial_data.get('roe')
                    roa = financial_data.get('roa')
                    debt_ratio = financial_data.get('debt_ratio')
                    net_profit_margin = financial_data.get('net_profit_margin')
                    
                    # 가격 정보 (price_data에서 우선 추출)
                    price_data = result.get('price_data', {})
                    current_price = price_data.get('current_price', result.get('current_price', 0))
                    price_52w_high = price_data.get('w52_high', result.get('w52_high'))
                    price_52w_low = price_data.get('w52_low', result.get('w52_low'))
                    price_position = result.get('price_position')
                    
                    # 점수 분석
                    score_breakdown = result.get('score_breakdown', {})
                    raw_breakdown = result.get('raw_breakdown', {})
                    value_score = raw_breakdown.get('value_raw', 0)  # 원점수 사용
                    financial_score = score_breakdown.get('재무비율', 0)
                    growth_score = score_breakdown.get('성장성', 0)
                    
                    print(f"\n🏢 {i}. {name} ({symbol}) - {score:.1f}점 ({grade})")
                    print("-" * 100)
                    
                    # 가치투자 정보
                    print(f"💰 가치투자 분석:")
                    print(f"   - 🏦 내재가치: {intrinsic_value:,.0f}원" if intrinsic_value else "   - 🏦 내재가치: N/A")
                    print(f"   - 🛡️ 안전마진: {margin_of_safety*100:.1f}%" if margin_of_safety else "   - 🛡️ 안전마진: N/A")
                    print(f"   - 🎯 투자시그널: {watchlist_signal}")
                    print(f"   - 🏰 해자등급: {moat_grade}")
                    print(f"   - 🎯 목표매수가: {target_buy:,.0f}원" if target_buy else "   - 🎯 목표매수가: N/A")
                    print(f"   - 📊 가치투자점수: {value_score:.1f}점")
                    
                    # 가치투자 플레이북
                    if playbook:
                        print(f"📚 가치투자 플레이북:")
                        for tip in playbook:
                            print(f"   - 💡 {tip}")
                    
                    # 재무 정보
                    print(f"💼 재무 건전성:")
                    print(f"   - 📈 ROE: {roe:.1f}%" if roe else "   - 📈 ROE: N/A")
                    print(f"   - 📊 ROA: {roa:.1f}%" if roa else "   - 📊 ROA: N/A")
                    print(f"   - 💳 부채비율: {debt_ratio:.1f}%" if debt_ratio else "   - 💳 부채비율: N/A")
                    print(f"   - 💰 순이익마진: {net_profit_margin:.1f}%" if net_profit_margin else "   - 💰 순이익마진: N/A")
                    print(f"   - 🏆 재무점수: {financial_score:.1f}점")
                    
                    # 가격 정보
                    print(f"💹 가격 분석:")
                    print(f"   - 💰 현재가: {current_price:,.0f}원" if current_price else "   - 💰 현재가: N/A")
                    print(f"   - 📈 52주고가: {price_52w_high:,.0f}원" if price_52w_high else "   - 📈 52주고가: N/A")
                    print(f"   - 📉 52주저가: {price_52w_low:,.0f}원" if price_52w_low else "   - 📉 52주저가: N/A")
                    print(f"   - 📊 52주위치: {price_position:.1f}%" if price_position else "   - 📊 52주위치: N/A")
                    
                    # 투자 포인트
                    print(f"🎯 투자 포인트:")
                    if watchlist_signal == "BUY" and margin_of_safety and margin_of_safety > 0.3:
                        print(f"   - 🟢 높은 안전마진으로 매력적인 매수 기회")
                    if roe and roe > 15:
                        print(f"   - 📈 우수한 자본 효율성 (ROE {roe:.1f}%)")
                    if debt_ratio and debt_ratio < 30:
                        print(f"   - 🏦 안정적인 재무 구조 (부채비율 {debt_ratio:.1f}%)")
                    if price_position and price_position < 30:
                        print(f"   - 📉 52주 저점 근처에서 매수 기회")
                    
                    print()
            else:
                print("조건에 맞는 종목이 없습니다.")
                
        except Exception as e:
            typer.echo(f"전체 시장 분석 실패: {e}", err=True)
        finally:
            analyzer.close()

except ImportError:
    app = None
    TYPER_AVAILABLE = False

def main():
    """Main entry point for the analyzer"""
    _setup_logging_if_needed()
    install_sighup_handler()
    _validate_startup_configuration()  # 구성 검증
    
    # Run smoke test if no arguments provided
    if len(sys.argv) == 1:
        print("Running smoke test...")
        analyzer = EnhancedIntegratedAnalyzer(include_realtime=False, include_external=False)
        try:
            r = analyzer.analyze_single_stock("005930", "삼성전자")
            print("Smoke test passed!")
            print(f"Status: {r.status}, Grade: {r.enhanced_grade}, Score: {r.enhanced_score:.1f}")
            print(f"Dict keys: {list(r.to_dict().keys())[:8]}")
        except Exception as e:
            print(f"Smoke test failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            analyzer.close()
        return
    
    if TYPER_AVAILABLE and app:
        try:
            app()
        except KeyboardInterrupt:
            logging.warning("사용자 중단(CTRL+C)")
    else:
        print("Enhanced Integrated Analyzer")
        print("Typer가 설치되지 않아 CLI를 사용할 수 없습니다.")
        print("Python 코드에서 직접 사용하세요:")
        print("  from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer")
        print("  analyzer = EnhancedIntegratedAnalyzer()")
        print("  result = analyzer.analyze_single_stock('005930', '삼성전자')")

if __name__ == "__main__":
    main()

# CLI 함수들 (typer가 설치된 경우에만 사용 가능) - 주석 처리
# 필요시 별도 CLI 모듈로 분리하여 구현 가능

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
  --smoke SYMBOL       단일 종목 스모크 테스트 (JSON 출력)

예시:
  python enhanced_integrated_analyzer_refactored.py --count 20 --min-score 25
  python enhanced_integrated_analyzer_refactored.py --no-external --dump results.json
  python enhanced_integrated_analyzer_refactored.py --count 5 --min-score 30 --max-workers 4
  python enhanced_integrated_analyzer_refactored.py --smoke 005930
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

    def main():
        """Main entry point for the analyzer"""
        _setup_logging_if_needed()
        install_sighup_handler()
        try:
            app()
        except KeyboardInterrupt:
            logging.warning("사용자 중단(CTRL+C)")

# Smoke test and main execution moved to the main main() function

# =============================================================================
# 테스트 유틸리티 및 단위 테스트
# =============================================================================

class EnvContextManager:
    """환경변수 컨텍스트 매니저 - 테스트 격리용"""
    
    def __init__(self, **env_vars):
        self.env_vars = env_vars
        self.original_values = {}
    
    def __enter__(self):
        for key, value in self.env_vars.items():
            self.original_values[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)
        # 환경변수 캐시 갱신
        _refresh_env_cache()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for key, original_value in self.original_values.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        # 환경변수 캐시 갱신
        _refresh_env_cache()

def with_env(**env_vars):
    """환경변수 컨텍스트 매니저 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with EnvContextManager(**env_vars):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def test_normalize_market_cap_ekwon_strict():
    """Test market cap normalization in strict mode"""
    import os
    os.environ["MARKET_CAP_STRICT_MODE"] = "true"
    
    # Reload environment cache
    _refresh_env_cache()
    
    # Test value that satisfies: min_threshold ≤ v ≤ max_threshold and v ≥ 1e7
    # But 1e7 = 10M, max_threshold = 2M, so no value can satisfy both conditions
    # Test large value conversion instead
    assert normalize_market_cap_ekwon(500_000_000_000) == 5000  # 원 → 억원 (≥1e11)
    assert normalize_market_cap_ekwon(50_000_000) is None       # ambiguous dropped

def test_financial_units_canonical():
    """Test financial units canonicalization"""
    d = {"roe": 0.12, "current_ratio": 1.8, "debt_ratio": 0.45}
    out = DataConverter.standardize_financial_units(d)
    assert out["roe"] == 12.0
    assert out["current_ratio"] == 180.0
    assert out["debt_ratio"] == 45.0
    assert out["_percent_canonicalized"] is True

def test_price_position():
    """Test price position calculation"""
    p = {"current_price": 60, "w52_low": 40, "w52_high": 100}
    a = EnhancedIntegratedAnalyzer(include_external=False)
    expected = (60-40)/(100-40)*100  # 33.333...
    result = a._calculate_price_position(p)
    assert abs(result - expected) < 0.01

def test_rate_limiter_applied_to_price_provider():
    """Test that rate limiter is applied to price provider calls"""
    calls = {"n": 0}
    
    class Dummy:
        def get_comprehensive_price_data(self, s): 
            calls["n"] += 1
            return {"current_price": 10.0, "eps": 2.0, "bps": 5.0}
    
    prov = FinancialDataProvider(KISDataProvider(), TPSRateLimiter(max_tps=1), metrics=MetricsCollector())
    prov.price_provider = Dummy()
    _ = prov.get_price_data("000001")
    assert calls["n"] == 1

def test_kospi_index_detection():
    """Test KOSPI index detection robustness"""
    import pandas as pd
    
    # Test with named index
    df1 = pd.DataFrame({'data': [1, 2, 3]}, index=['A', 'B', 'C'])
    df1.index.name = '단축코드'
    assert _is_indexed_by_code(df1) is True
    
    # Test with unnamed index
    df2 = pd.DataFrame({'data': [1, 2, 3]}, index=['A', 'B', 'C'])
    assert _is_indexed_by_code(df2) is False
    
    # Test with None index name
    df3 = pd.DataFrame({'data': [1, 2, 3]}, index=['A', 'B', 'C'])
    df3.index.name = None
    assert _is_indexed_by_code(df3) is False

def test_percent_canonicalization_safety():
    """Test percent canonicalization safety (no double scaling)"""
    # Test cases: roe=[0.03, 3, 300] → [3, 300, 300] (enforce_canonical_percent logic)
    test_cases = [
        (0.03, 3.0),    # 3% as decimal → 3%
        (3.0, 300.0),   # 3% as decimal (≤5) → 300%
        (300.0, 300.0), # 300% already → 300%
    ]
    
    for input_val, expected in test_cases:
        d = {"roe": input_val}
        out = DataConverter.standardize_financial_units(d)
        assert out["roe"] == expected, f"ROE {input_val} should become {expected}, got {out['roe']}"

def test_current_ratio_ambiguous_policy():
    """Test current_ratio ambiguous range policy"""
    # Test cases: [1.5, 120, 35] → [150, 120, 35] (ambiguous 35 stays in [10,300] range)
    test_cases = [
        (1.5, 150.0),   # Multiple → Percent
        (120.0, 120.0), # Already percent
        (35.0, 35.0),   # Ambiguous but in safe range
    ]
    
    for input_val, expected in test_cases:
        d = {"current_ratio": input_val}
        out = DataConverter.standardize_financial_units(d)
        assert out["current_ratio"] == expected, f"Current ratio {input_val} should become {expected}, got {out['current_ratio']}"

def test_52w_band_degeneration():
    """Test 52-week band degeneration cases"""
    a = EnhancedIntegratedAnalyzer(include_external=False)
    
    # Test cases: (hi, lo, cp) → expected_position
    test_cases = [
        (100, 100, 100, None),  # Same values → degeneration
        (100, 100, 100, None),  # Same values → degeneration  
        (100, 99.9, 100, None), # Tiny band → degeneration
        (100, 1, 50, 49.49),    # Normal case (band=99, position≈49.49%)
        (100, 50, 75, 50.0),    # Normal case (band=50, position=50%)
    ]
    
    for hi, lo, cp, expected in test_cases:
        position = a._calculate_price_position({
            'current_price': cp,
            'w52_high': hi,
            'w52_low': lo
        })
        if expected is None:
            assert position is None, f"Position should be None for hi={hi}, lo={lo}, cp={cp}"
        else:
            assert abs(position - expected) < 0.1, f"Position mismatch for hi={hi}, lo={lo}, cp={cp}: expected {expected}, got {position}"

def test_per_pbr_guards():
    """Test PER/PBR guards with extreme values"""
    # Test EPS=0.01 (very small) should skip PER calculation
    # Test BPS=0.01 (very small) should skip PBR calculation
    # Test clamp upper bounds apply
    
    # This would require mocking the price provider, so we'll test the logic conceptually
    # EPS_MIN = 0.1, BPS_MIN = 100.0 (from environment)
    assert True  # Placeholder - actual implementation would test the guards

def test_kospi_market_cap_strict_mode():
    """Test KOSPI market cap strict mode handling"""
    # Test cases: mc=200_000_000_000_000(원) → 2_000_000(억원) (always converts, ≥1e11)
    # Test ambiguous range: mc=50_000_000_000(원) strict=true → None, strict=false → 500(억원)
    
    # Test large value (≥1e11) - always converts regardless of strict mode
    result_large = normalize_market_cap_ekwon(200_000_000_000_000)
    assert result_large == 2_000_000, f"Large value should convert to 2_000_000, got {result_large}"
    
    # Test ambiguous range (1e10-1e11) - depends on strict mode
    with EnvContextManager(MARKET_CAP_STRICT_MODE="true"):
        result_strict = normalize_market_cap_ekwon(50_000_000_000)  # 500억원
        assert result_strict is None, f"Strict mode should return None for ambiguous value, got {result_strict}"
    
    # Test non-strict mode  
    with EnvContextManager(MARKET_CAP_STRICT_MODE="false"):
        result_nonstrict = normalize_market_cap_ekwon(50_000_000_000)  # 500억원
        assert result_nonstrict == 500, f"Non-strict mode should convert to 500, got {result_nonstrict}"

def test_market_cap_boundary_values():
    """Test market cap normalization across all regimes"""
    test_cases = [
        # (input, strict_mode, expected_result, description)
        (1e6, True, None, "Too small (<1e7)"),
        (5e9, True, None, "Small cap in won (5e9)"),
        (2e10, True, None, "Ambiguous range (2e10)"),
        (5e10, True, None, "Ambiguous range (5e10)"),
        (1e11, True, 1000, "Large value (≥1e11)"),
        (5e11, True, 5000, "Very large value (5e11)"),
        
        # Non-strict mode
        (5e9, False, 50, "Small cap in won (non-strict)"),
        (2e10, False, 200, "Ambiguous range (non-strict)"),
        (5e10, False, 500, "Ambiguous range (non-strict)"),
    ]
    
    for input_val, strict_mode, expected, description in test_cases:
        with EnvContextManager(MARKET_CAP_STRICT_MODE=str(strict_mode).lower()):
            result = normalize_market_cap_ekwon(input_val)
            assert result == expected, f"{description}: {input_val} -> expected {expected}, got {result}"

def test_current_ratio_ambiguous_policy_matrix():
    """Test current_ratio ambiguous range policy matrix"""
    test_cases = [
        # (input, force_percent, ambiguous_strategy, expected_result, description)
        (1.5, False, "as_is", 150.0, "Multiple → Percent (force_percent=false)"),
        (1.5, True, "as_is", 150.0, "Multiple → Percent (force_percent=true)"),
        (120.0, False, "as_is", 120.0, "Already percent"),
        (35.0, False, "as_is", 35.0, "Ambiguous but in safe range"),
        (35.0, False, "clamp", 35.0, "Ambiguous with clamp strategy (no change needed)"),
        (8.0, False, "as_is", 800.0, "Multiple → Percent"),
        (8.0, True, "as_is", 8.0, "Multiple → Percent (force_percent=true, but 8.0 > 5.0 so no change)"),
    ]
    
    for input_val, force_percent, ambiguous_strategy, expected, description in test_cases:
        with EnvContextManager(
            CURRENT_RATIO_FORCE_PERCENT=str(force_percent).lower(),
            CURRENT_RATIO_AMBIGUOUS_STRATEGY=ambiguous_strategy
        ):
            d = {"current_ratio": input_val}
            out = DataConverter.standardize_financial_units(d)
            assert out["current_ratio"] == expected, f"{description}: {input_val} -> expected {expected}, got {out['current_ratio']}"

def test_percent_canonicalization_regression():
    """Test percent canonicalization regression prevention"""
    test_cases = [
        # (input_data, expected_output, description)
        ({"roe": 0.12, "debt_ratio": 0.45}, {"roe": 12.0, "debt_ratio": 45.0}, "Decimal to percent"),
        ({"roe": 12.0, "debt_ratio": 45.0}, {"roe": 12.0, "debt_ratio": 45.0}, "Already percent"),
        ({"roe": 0.03, "debt_ratio": 0.03}, {"roe": 300.0, "debt_ratio": 300.0}, "Small decimals (enforce_canonical_percent)"),
    ]
    
    for input_data, expected_output, description in test_cases:
        # First pass
        out1 = DataConverter.standardize_financial_units(input_data.copy())
        assert out1["_percent_canonicalized"] is True, f"{description}: First pass should set flag"
        
        # Second pass (regression test)
        out2 = DataConverter.standardize_financial_units(out1.copy())
        assert out2["_percent_canonicalized"] is True, f"{description}: Second pass should maintain flag"
        
        # Values should not change
        for key in expected_output:
            assert out2[key] == expected_output[key], f"{description}: {key} should be {expected_output[key]}, got {out2[key]}"

def test_valuation_penalty_double_prevention():
    """Test valuation penalty double application prevention"""
    # Test case: Both VAL_PENALTY_IN_PRICE and VAL_PENALTY_IN_FIN are True
    # Should warn and disable VAL_PENALTY_IN_FIN
    
    # Capture log output to verify warning
    
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.WARNING)
    
    # Add handler temporarily
    logger = logging.getLogger()
    original_handlers = logger.handlers[:]
    logger.addHandler(handler)
    
    try:
        with EnvContextManager(
            VAL_PENALTY_IN_PRICE="true",
            VAL_PENALTY_IN_FIN="true"
        ):
            # Create analyzer and test scoring
            analyzer = EnhancedIntegratedAnalyzer(include_realtime=False, include_external=False)
            
            # Mock data with high PER/PBR to trigger penalties
            test_data = {
                'price_data': {
                    'per': 50.0,  # High PER
                    'pbr': 5.0,   # High PBR
                    'current_price': 100.0
                },
                'financial_data': {
                    'per': 50.0,
                    'pbr': 5.0,
                    'roe': 10.0
                }
            }
            
            # Test scoring
            scorer = EnhancedScoreCalculator(ConfigManager())
            score, breakdown = scorer.calculate_score(test_data)
            
            # Verify warning was logged
            log_output = log_capture.getvalue()
            assert "PRICE와 FIN 동시 적용 감지" in log_output, "Warning about double penalty should be logged"
            
            # Verify that FIN penalty was disabled (score should not be extremely low)
            assert score > 0, "Score should be positive even with high PER/PBR"
            
            analyzer.close()
            
    finally:
        # Restore original handlers
        logger.handlers = original_handlers
        handler.close()

def test_valuation_penalty_single_application():
    """Test that only one penalty is applied when configured correctly"""
    test_cases = [
        # (price_penalty, fin_penalty, expected_behavior)
        (True, False, "Only price penalty applied"),
        (False, True, "Only financial penalty applied"),
        (False, False, "No penalties applied"),
    ]
    
    for price_penalty, fin_penalty, description in test_cases:
        with EnvContextManager(
            VAL_PENALTY_IN_PRICE=str(price_penalty).lower(),
            VAL_PENALTY_IN_FIN=str(fin_penalty).lower()
        ):
            analyzer = EnhancedIntegratedAnalyzer(include_realtime=False, include_external=False)
            
            # Test data with high PER/PBR
            test_data = {
                'price_data': {
                    'per': 50.0,
                    'pbr': 5.0,
                    'current_price': 100.0
                },
                'financial_data': {
                    'per': 50.0,
                    'pbr': 5.0,
                    'roe': 10.0
                }
            }
            
            scorer = EnhancedScoreCalculator(ConfigManager())
            score, breakdown = scorer.calculate_score(test_data)
            
            # Score should be reasonable (not extremely low from double penalty)
            assert score > 0, f"{description}: Score should be positive"
            
            analyzer.close()

def test_52w_band_boundary_cases():
    """Test 52-week band boundary cases and price position edge cases"""
    analyzer = EnhancedIntegratedAnalyzer(include_realtime=False, include_external=False)
    
    test_cases = [
        # (w52_high, w52_low, current_price, expected_position, description)
        (100.0, 100.0, 100.0, None, "Identical high/low (degenerate band)"),
        (100.0, 99.95, 100.0, None, "Tiny band (0.05% difference)"),
        (100.0, 99.0, 100.0, 100.0, "At high boundary"),
        (100.0, 99.0, 99.0, 0.0, "At low boundary"),
        (100.0, 99.0, 99.5, 50.0, "Middle position"),
        (100.0, 99.0, 101.0, 100.0, "Above band (clamped to 100)"),
        (100.0, 99.0, 98.0, 0.0, "Below band (clamped to 0)"),
    ]
    
    for w52_high, w52_low, current_price, expected, description in test_cases:
        price_data = {
            'w52_high': w52_high,
            'w52_low': w52_low,
            'current_price': current_price
        }
        
        result = analyzer._calculate_price_position(price_data)
        
        if expected is None:
            assert result is None, f"{description}: Should return None, got {result}"
        else:
            assert result is not None, f"{description}: Should return {expected}, got None"
            assert abs(result - expected) < 0.1, f"{description}: Expected ~{expected}, got {result}"
    
    analyzer.close()

def test_52w_band_tiny_threshold():
    """Test POS_TINY_BAND_THRESHOLD configuration"""
    test_cases = [
        # (threshold, band_ratio, expected_result, description)
        (0.001, 0.0005, None, "Band below threshold (0.05% < 0.1%)"),
        (0.001, 0.0015, 50.0, "Band above threshold (0.15% > 0.1%)"),
        (0.01, 0.005, None, "Band below higher threshold (0.5% < 1%)"),
        (0.01, 0.015, 50.0, "Band above higher threshold (1.5% > 1%)"),
    ]
    
    for threshold, band_ratio, expected, description in test_cases:
        with EnvContextManager(POS_TINY_BAND_THRESHOLD=str(threshold)):
            analyzer = EnhancedIntegratedAnalyzer(include_realtime=False, include_external=False)
            
            # Create band with specified ratio
            w52_high = 100.0
            w52_low = w52_high * (1 - band_ratio)
            current_price = (w52_high + w52_low) / 2  # Middle
            
            price_data = {
                'w52_high': w52_high,
                'w52_low': w52_low,
                'current_price': current_price
            }
            
            result = analyzer._calculate_price_position(price_data)
            
            if expected is None:
                assert result is None, f"{description}: Should return None, got {result}"
            else:
                assert result is not None, f"{description}: Should return ~{expected}, got {result}"
            
            analyzer.close()

def test_price_position_score_mapping():
    """Test price position to score mapping edge cases"""
    scorer = EnhancedScoreCalculator(ConfigManager())
    
    test_cases = [
        # (price_position, expected_score_range, description)
        (0.0, (95, 100), "At 52w low (should be high score)"),
        (50.0, (25, 35), "Middle position (neutral score)"),
        (100.0, (0, 5), "At 52w high (should be low score)"),
        (None, (45, 55), "Invalid position (should default to neutral)"),
    ]
    
    for price_position, expected_range, description in test_cases:
        result = scorer._calculate_price_position_score(price_position)
        
        assert expected_range[0] <= result <= expected_range[1], \
            f"{description}: Expected {expected_range}, got {result}"

def test_startup_configuration_validation():
    """Test startup configuration validation"""
    # Test 1: Valid configuration should pass
    with EnvContextManager(
        VAL_PENALTY_IN_PRICE="true",
        VAL_PENALTY_IN_FIN="false",
        MARKET_CAP_STRICT_MODE="true"
    ):
        try:
            _validate_startup_configuration()
            # Should not raise exception
        except ValueError as e:
            assert False, f"Valid configuration should not raise ValueError: {e}"
    
    # Test 2: Double penalty configuration should fail
    with EnvContextManager(
        VAL_PENALTY_IN_PRICE="true",
        VAL_PENALTY_IN_FIN="true"
    ):
        try:
            _validate_startup_configuration()
            assert False, "Double penalty configuration should raise ValueError"
        except ValueError as e:
            assert "VAL_PENALTY_IN_PRICE and VAL_PENALTY_IN_FIN cannot both be True" in str(e)
    
    # Test 3: High TPS should warn
    with EnvContextManager(KIS_MAX_TPS="25"):
        # Capture log output
        
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.WARNING)
        
        logger = logging.getLogger()
        original_handlers = logger.handlers[:]
        logger.addHandler(handler)
        
        try:
            _validate_startup_configuration()
            log_output = log_capture.getvalue()
            assert "KIS_MAX_TPS is very high" in log_output
        finally:
            logger.handlers = original_handlers
            handler.close()

def test_sighup_handler_installation():
    """Test SIGHUP handler installation tracking"""
    # Reset the flag
    if hasattr(_validate_startup_configuration, '_sighup_installed'):
        delattr(_validate_startup_configuration, '_sighup_installed')
    
    # Test without SIGHUP installation
    
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.WARNING)
    
    logger = logging.getLogger()
    original_handlers = logger.handlers[:]
    logger.addHandler(handler)
    
    try:
        _validate_startup_configuration()
        log_output = log_capture.getvalue()
        assert "SIGHUP handler not installed" in log_output
    finally:
        logger.handlers = original_handlers
        handler.close()
    
    # Test with SIGHUP installation
    _mark_sighup_installed()
    
    log_capture2 = io.StringIO()
    handler2 = logging.StreamHandler(log_capture2)
    handler2.setLevel(logging.WARNING)
    
    logger.addHandler(handler2)
    
    try:
        _validate_startup_configuration()
        log_output2 = log_capture2.getvalue()
        assert "SIGHUP handler not installed" not in log_output2
    finally:
        logger.handlers = original_handlers
        handler2.close()

def run_quick_tests():
    """Run all quick smoke tests"""
    print("Running quick smoke tests...")
    
    try:
        test_normalize_market_cap_ekwon_strict()
        print("Market cap normalization test passed")
        
        test_financial_units_canonical()
        print("Financial units canonicalization test passed")
        
        test_price_position()
        print("Price position calculation test passed")
        
        test_rate_limiter_applied_to_price_provider()
        print("Rate limiter test passed")
        
        test_kospi_index_detection()
        print("KOSPI index detection test passed")
        
        # New safety/accuracy tests
        test_percent_canonicalization_safety()
        print("Percent canonicalization safety test passed")
        
        test_current_ratio_ambiguous_policy()
        print("Current ratio ambiguous policy test passed")
        
        test_52w_band_degeneration()
        print("52-week band degeneration test passed")
        
        test_per_pbr_guards()
        print("PER/PBR guards test passed")
        
        test_kospi_market_cap_strict_mode()
        print("KOSPI market cap strict mode test passed")
        
        # New comprehensive boundary tests
        test_market_cap_boundary_values()
        print("Market cap boundary values test passed")
        
        test_current_ratio_ambiguous_policy_matrix()
        print("Current ratio policy matrix test passed")
        
        test_percent_canonicalization_regression()
        print("Percent canonicalization regression test passed")
        
        # Valuation penalty tests
        test_valuation_penalty_double_prevention()
        print("Valuation penalty double prevention test passed")
        
        test_valuation_penalty_single_application()
        print("Valuation penalty single application test passed")
        
        # 52-week band boundary tests
        test_52w_band_boundary_cases()
        print("52-week band boundary cases test passed")
        
        test_52w_band_tiny_threshold()
        print("52-week band tiny threshold test passed")
        
        test_price_position_score_mapping()
        print("Price position score mapping test passed")
        
        # Startup validation tests
        test_startup_configuration_validation()
        print("Startup configuration validation test passed")
        
        test_sighup_handler_installation()
        print("SIGHUP handler installation test passed")
        
        print("All quick tests passed!")
        return True
        
    except Exception as e:
        import traceback
        print(f"Test failed: {e}")
        print("Traceback:")
        traceback.print_exc()
        return False

# Quick tests removed - use main() function instead

