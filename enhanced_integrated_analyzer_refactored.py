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
import os
import pandas as pd
from importlib import import_module

# 로깅 유틸리티 import
from logging_utils import LogLevel, ErrorType, log_error, log_success

# 메트릭 수집기 import
from metrics import MetricsCollector

# 가드 및 필터 클래스 import
from guards import InputReliabilityGuard
from quality_filter import QualityConsistencyFilter
from risk_constraints import RiskConstraintsManager

# CLI 인터페이스 import
try:
    from cli import create_app, main as cli_main
    CLI_AVAILABLE = True
except ImportError:
    CLI_AVAILABLE = False

# --- legacy analyzer bridge --------------------------------------------------
# NOTE: avoid importing enhanced_analyzer at module import time to prevent
# circular references. Instead resolve lazily when needed.

_LEGACY_ANALYZER_CLASS = None


def _get_legacy_analyzer_class():
    """Lazy import of the legacy EnhancedIntegratedAnalyzer class."""

    global _LEGACY_ANALYZER_CLASS
    if _LEGACY_ANALYZER_CLASS is None:
        module = import_module("enhanced_analyzer")
        _LEGACY_ANALYZER_CLASS = getattr(module, "EnhancedIntegratedAnalyzer")
    return _LEGACY_ANALYZER_CLASS


def EnhancedIntegratedAnalyzer(*args, **kwargs):
    """Compatibility wrapper returning the legacy analyzer implementation."""

    analyzer_cls = _get_legacy_analyzer_class()
    return analyzer_cls(*args, **kwargs)


# 국가별 마스터 데이터 로더는 내부에서 지연 임포트한다.


def _load_kospi_data_impl():
    """`enhanced_analyzer` 등 레거시 코드가 기대하는 마스터 로더.

    순환 임포트를 방지하기 위해 함수 내부에서 필요한 모듈을 로드한다.
    기본적으로 `enhanced_analyzer` 구현에 있는 `_load_kospi_data_impl`을
    재사용하며, 실패 시 간단한 기본 로더로 폴백한다.
    """

    try:  # pragma: no cover - 단순 위임
        from enhanced_analyzer import _load_kospi_data_impl as legacy_loader
        return legacy_loader()
    except ImportError:
        logging.info("enhanced_analyzer._load_kospi_data_impl을 찾을 수 없습니다. 내장 로더를 사용합니다.")
    except Exception as exc:
        logging.warning(f"KOSPI 데이터 로드 실패 (legacy): {exc}")

    # 간단한 기본 로더: 캐시/데이터 폴더에서 파일 탐색
    candidate_paths = [
        'kospi_master.parquet',
        'data/kospi_master.parquet',
        'cache/kospi_master.parquet',
        'kospi_code.xlsx',
        'data/kospi_code.xlsx',
        'cache/kospi_code.xlsx',
        'kospi_code.csv',
        'data/kospi_code.csv',
        'cache/kospi_code.csv',
    ]

    for path in candidate_paths:
        try:
            if not os.path.exists(path):
                continue

            if path.lower().endswith('.parquet'):
                df = pd.read_parquet(path)
            elif path.lower().endswith('.xlsx'):
                df = pd.read_excel(path)
            else:
                df = pd.read_csv(path)

            if df is not None and not df.empty:
                logging.info(f"KOSPI 기본 데이터 로드: {path} (행 {len(df)})")
                return df
        except Exception as exc:
            logging.debug(f"KOSPI 기본 데이터 로드 실패({path}): {exc}")

    logging.warning("KOSPI 데이터 파일을 찾을 수 없습니다. 분석은 계속 진행되지만 일부 기능이 제한될 수 있습니다.")
    return None

# 추가 모듈 import
from value_metrics import ValueMetricsPrecision
from margin_safety import MarginOfSafetyCalculator
from data_models import PriceData, FinancialData, SectorAnalysis, AnalysisStatus, AnalysisResult, AnalysisConfig
from sector_contextualizer import SectorCycleContextualizer
from price_policy import PricePositionPolicyManager
from ranking_diversification import RankingDiversificationManager
from value_style_classifier import ValueStyleClassifier
from uvs_eligibility_filter import UVSEligibilityFilter
from financial_data_provider import FinancialDataProvider
from enhanced_score_calculator import EnhancedScoreCalculator
from tps_rate_limiter import TPSRateLimiter
from config_manager import ConfigManager
from interfaces import DataProvider, ScoreCalculator
from analysis_models import AnalysisStatus, AnalysisResult, AnalysisConfig

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
# 데이터 모델들은 data_models.py로 분리됨

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

# 로깅 관련 유틸리티는 logging_utils.py로 분리됨

# =============================================================================
# 입력 신뢰도 가드 클래스 (moved to utils.guards)
# =============================================================================
from utils.data_utils import DataValidator, DataConverter, serialize_for_json
from utils.env_utils import safe_env_int, safe_env_float, safe_env_bool, safe_env_ms_to_seconds, _refresh_env_cache
from utils.metrics import MetricsCollector
from utils.guards import InputReliabilityGuard
from utils.risk_constraints import RiskConstraintsManager

# InputReliabilityGuard class moved to utils.guards module

# =============================================================================
# CLI 실행 부분
# =============================================================================

def main():
    """메인 실행 함수"""
    print("Enhanced Integrated Analyzer 시작")
    print("=" * 50)
    
    # 설정 검증
    try:
        _validate_startup_configuration()
        print("설정 검증 완료")
    except Exception as e:
        print(f"설정 검증 실패: {e}")
        return
    
    # CLI 사용 가능 여부 확인
    if CLI_AVAILABLE:
        print("CLI 인터페이스 사용 가능")
        try:
            cli_main()
        except Exception as e:
            print(f"CLI 실행 오류: {e}")
    else:
        print("CLI 인터페이스 사용 불가")
        print("사용 가능한 기능:")
        print("- EnhancedIntegratedAnalyzer 클래스 직접 사용")
        print("- 모듈별 개별 기능 사용")
        print("- 웹 대시보드: streamlit run web_dashboard.py")

if __name__ == "__main__":
    main()
