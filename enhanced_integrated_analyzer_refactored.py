# enhanced_integrated_analyzer_refactored.py
"""
리팩토링된 향상된 통합 분석 시스템
- 단일 책임 원칙 적용
- 클래스 분리 및 모듈화
- 성능 최적화
- 에러 처리 개선
"""

import typer
import pandas as pd
import logging
import time
import os
import yaml
import math
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from threading import Lock, RLock
from collections import deque, OrderedDict

# monotonic time 별칭 (시스템 시간 변경에 안전)
_monotonic = time.monotonic

# =============================================================================
# 로깅 유틸리티
# =============================================================================

def log_error(operation: str, symbol: str = None, error: Exception = None, level: str = "warning"):
    """일관된 에러 로깅 포맷"""
    if symbol:
        message = f"{operation} 실패 {symbol}: {error}"
    else:
        message = f"{operation} 실패: {error}"
    
    if level == "error":
        logging.error(message)
    elif level == "warning":
        logging.warning(message)
    else:
        logging.info(message)

def log_success(operation: str, symbol: str = None, details: str = None):
    """일관된 성공 로깅 포맷"""
    if symbol and details:
        message = f"✅ {operation} 성공 {symbol}: {details}"
    elif symbol:
        message = f"✅ {operation} 성공 {symbol}"
    else:
        message = f"✅ {operation} 성공"
    
    logging.info(message)

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
            'start_time': time.time()
        }
        self.lock = RLock()
    
    def record_api_call(self, success: bool, error_type: str = None):
        """API 호출 기록"""
        with self.lock:
            self.metrics['api_calls']['total'] += 1
            if success:
                self.metrics['api_calls']['success'] += 1
            else:
                self.metrics['api_calls']['error'] += 1
                if error_type:
                    self.metrics['errors_by_type'][error_type] = self.metrics['errors_by_type'].get(error_type, 0) + 1
    
    def record_cache_hit(self, cache_type: str):
        """캐시 히트 기록"""
        with self.lock:
            self.metrics['cache_hits'][cache_type] = self.metrics['cache_hits'].get(cache_type, 0) + 1
    
    def record_cache_miss(self, cache_type: str):
        """캐시 미스 기록"""
        with self.lock:
            self.metrics['cache_misses'][cache_type] = self.metrics['cache_misses'].get(cache_type, 0) + 1
    
    def record_analysis_duration(self, duration: float):
        """분석 소요 시간 기록"""
        with self.lock:
            self.metrics['analysis_duration']['total'] += duration
            self.metrics['analysis_duration']['count'] += 1
            self.metrics['analysis_duration']['avg'] = (
                self.metrics['analysis_duration']['total'] / self.metrics['analysis_duration']['count']
            )
    
    def record_sector_evaluation(self, duration: float):
        """섹터 평가 소요 시간 기록"""
        with self.lock:
            self.metrics['sector_evaluation']['total'] += duration
            self.metrics['sector_evaluation']['count'] += 1
            self.metrics['sector_evaluation']['avg'] = (
                self.metrics['sector_evaluation']['total'] / self.metrics['sector_evaluation']['count']
            )
    
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
            return (hits / total * 100) if total > 0 else 0.0
    
    def get_api_success_rate(self) -> float:
        """API 성공률 계산"""
        with self.lock:
            total = self.metrics['api_calls']['total']
            success = self.metrics['api_calls']['success']
            return (success / total * 100) if total > 0 else 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """메트릭 요약 반환"""
        with self.lock:
            return {
                'runtime_seconds': time.time() - self.metrics['start_time'],
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
                'errors_by_type': self.metrics['errors_by_type'].copy()
            }

# API 재시도 유틸 (백오프+지터)
def _with_retries(call, tries=3, base=0.2, jitter=0.15):
    """API 호출 재시도 래퍼 (지수 백오프 + 지터)"""
    for i in range(tries):
        try:
            return call()
        except Exception as e:
            if i == tries - 1:
                raise
            sleep = base * (2 ** i) + random.uniform(0, jitter)
            time.sleep(sleep)
from concurrent.futures import ThreadPoolExecutor, as_completed

# 로깅 설정은 메인 실행부에서 초기화
from rich.console import Console
from rich.table import Table
from rich import box
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

# 기존 import들
from kis_data_provider import KISDataProvider
from enhanced_price_provider import EnhancedPriceProvider
from investment_opinion_analyzer import InvestmentOpinionAnalyzer
from estimate_performance_analyzer import EstimatePerformanceAnalyzer
from financial_ratio_analyzer import FinancialRatioAnalyzer
from profit_ratio_analyzer import ProfitRatioAnalyzer
from stability_ratio_analyzer import StabilityRatioAnalyzer
from test_integrated_analysis import create_integrated_analysis

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
    risk_score: Optional[float] = None
    financial_data: Dict[str, Any] = None
    opinion_analysis: Dict[str, Any] = None
    estimate_analysis: Dict[str, Any] = None
    integrated_analysis: Dict[str, Any] = None
    risk_analysis: Dict[str, Any] = None
    score_breakdown: Dict[str, float] = None
    error: Optional[str] = None
    price_data: Dict[str, Any] = None  # 가격 데이터 캐싱용
    sector_analysis: Dict[str, Any] = None  # 섹터 분석 결과
    
    def __post_init__(self):
        if self.financial_data is None:
            self.financial_data = {}
        if self.opinion_analysis is None:
            self.opinion_analysis = {}
        if self.estimate_analysis is None:
            self.estimate_analysis = {}
        if self.integrated_analysis is None:
            self.integrated_analysis = {}
        if self.risk_analysis is None:
            self.risk_analysis = {}
        if self.score_breakdown is None:
            self.score_breakdown = {}
        if self.price_data is None:
            self.price_data = {}
        if self.sector_analysis is None:
            self.sector_analysis = {}

@dataclass
class AnalysisConfig:
    """분석 설정 데이터 클래스"""
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
    def calculate_score(self, data: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """점수 계산"""
        pass

# =============================================================================
# 3. 유틸리티 클래스들
# =============================================================================

class TPSRateLimiter:
    """KIS OpenAPI TPS 제한을 고려한 레이트리미터 (개선된 버전)"""
    
    def __init__(self, max_tps: int = None):
        self.max_tps = max_tps or int(os.getenv("KIS_MAX_TPS", "8"))
        self.ts = deque()
        self.lock = Lock()
        self._last_cleanup = _monotonic()
    
    def acquire(self):
        """요청 허가를 받습니다."""
        while True:
            with self.lock:
                now = _monotonic()
                if now - self._last_cleanup > 1.0:
                    self._cleanup_old_requests(now)
                    self._last_cleanup = now

                if len(self.ts) < self.max_tps:
                    self.ts.append(now)
                    # jitter는 잠금 해제 후에
                    break

                # 초과면 필요한 대기시간 계산만 하고, 바로 lock을 풀고 잔다
                sleep_time = max(0.0, 1.0 - (now - self.ts[0]))
            if sleep_time > 0:
                time.sleep(sleep_time + random.uniform(0.01, 0.08))

        time.sleep(random.uniform(0.0, 0.004))
    
    def _cleanup_old_requests(self, now: float):
        """1초 이전 요청들을 정리합니다."""
        one_sec_ago = now - 1.0
        while self.ts and self.ts[0] < one_sec_ago:
            self.ts.popleft()

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
                    'D': 20,
                    'F': 0
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
    def safe_float(value: Any, default: float = 0.0) -> float:
        """안전하게 float로 변환"""
        try:
            if value is None or pd.isna(value):
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
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
        import re
        # 강화된 우선주 패턴 - 끝-anchor 위주로 정확성 향상
        pref_pattern = r'(^.+?우$|우B$|우C$|\(우\)$|우선주$)'
        return bool(re.search(pref_pattern, str(name).strip()))
    
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

class DataConverter:
    """데이터 변환 유틸리티 클래스"""
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """안전하게 float로 변환"""
        if value is None or pd.isna(value):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def normalize_percentage(value: Any, assume_ratio_if_abs_lt_1: bool = True) -> float:
        """퍼센트 값을 정규화 (0.12 → 12.0)"""
        try:
            v = float(value)
            if pd.isna(v):
                return 0.0
            return v * 100.0 if assume_ratio_if_abs_lt_1 and -1.0 <= v <= 1.0 else v
        except Exception:
            return 0.0
    
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
    def as_percent_maybe_ratio(x: Any) -> float:
        """%/배수 혼재 정규화 (0<값≤5 → ×100 규칙)"""
        v = DataValidator.safe_float(x, 0.0)
        if v <= 0:
            return 0.0
        return v * 100.0 if v <= 5.0 else v

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
        self._ttl = ttl if ttl is not None else float(os.getenv("KIS_CACHE_TTL", "15.0"))
        self._max_keys = int(os.getenv("KIS_CACHE_MAX_KEYS", "2000"))
        self.metrics = metrics
    
    def _get_cached(self, cache, key):
        """캐시에서 데이터 조회 (동시성 안전)"""
        now = _monotonic()
        with self._cache_lock:
            hit = cache.get(key)
            if hit and now - hit[0] < self._ttl:
                if self.metrics:
                    self.metrics.record_cache_hit('price' if cache is self._cache_price else 'financial')
                return hit[1]
        
        if self.metrics:
            self.metrics.record_cache_miss('price' if cache is self._cache_price else 'financial')
        return None

    def _set_cached(self, cache, key, value):
        """캐시에 데이터 저장 (동시성 안전, LRU 한도 적용)"""
        with self._cache_lock:
            cache[key] = (_monotonic(), value)
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
            self.rate_limiter.acquire()
            financial_ratios = _with_retries(lambda: self.financial_ratio_analyzer.get_financial_ratios(symbol))
            if financial_ratios and len(financial_ratios) > 0:
                latest_ratios = financial_ratios[0]
                financial_data.update({
                    'roe': DataValidator.safe_float(latest_ratios.get('roe')),
                    'roa': DataValidator.safe_float(latest_ratios.get('roa')),
                    'debt_ratio': DataValidator.safe_float(latest_ratios.get('debt_ratio')),
                    'equity_ratio': DataValidator.safe_float(latest_ratios.get('equity_ratio')),
                    'revenue_growth_rate': DataValidator.safe_float(latest_ratios.get('revenue_growth_rate')),
                    'operating_income_growth_rate': DataValidator.safe_float(latest_ratios.get('operating_income_growth_rate')),
                    'net_income_growth_rate': DataValidator.safe_float(latest_ratios.get('net_income_growth_rate'))
                })
        except Exception as e:
            log_error("재무비율 분석", symbol, e)
        
        # 수익성비율 분석 (재시도 적용)
        try:
            self.rate_limiter.acquire()
            profit_ratios = _with_retries(lambda: self.profit_ratio_analyzer.get_profit_ratios(symbol))
            if profit_ratios and len(profit_ratios) > 0:
                latest_profit = profit_ratios[0]
                financial_data.update({
                    'net_profit_margin': DataValidator.safe_float(latest_profit.get('net_profit_margin')),
                    'gross_profit_margin': DataValidator.safe_float(latest_profit.get('gross_profit_margin')),
                    'profitability_grade': latest_profit.get('profitability_grade', '평가불가')
                })
        except Exception as e:
            log_error("수익성비율 분석", symbol, e)
        
        # 안정성비율 분석 (current_ratio 포함)
        try:
            self.rate_limiter.acquire()
            stability = _with_retries(lambda: self.stability_ratio_analyzer.get_stability_ratios(symbol))
            if stability and len(stability) > 0:
                latest_stab = stability[0]
                financial_data.update({
                    'current_ratio': DataConverter.as_percent_maybe_ratio(latest_stab.get('current_ratio'))
                })
        except Exception as e:
            log_error("안정성비율 분석", symbol, e)
        
        # 혼재 단위 정규화 일괄 적용
        for key in ('debt_ratio', 'equity_ratio', 'revenue_growth_rate',
                    'operating_income_growth_rate', 'net_income_growth_rate',
                    'net_profit_margin', 'gross_profit_margin'):
            if key in financial_data:
                financial_data[key] = DataConverter.as_percent_maybe_ratio(financial_data[key])
        
        # ROE/ROA 단위 일관성 보장
        for key in ('roe', 'roa'):
            if key in financial_data:
                v = financial_data[key]
                # 0<x<=5면 %로 오인 가능: ×100
                financial_data[key] = v * 100.0 if 0 < v <= 5.0 else v
        
        # 현재가 기반 PER/PBR 추가 계산 (일관성 확보)
        try:
            price_data = self.get_price_data(symbol)
            current_price = price_data.get('current_price', 0)
            
            if current_price and current_price > 0:
                # EPS/BPS가 있으면 PER/PBR 계산
                eps = price_data.get('eps', 0)
                bps = price_data.get('bps', 0)
                
                if eps and eps > 0:
                    financial_data['per'] = current_price / eps
                if bps and bps > 0:
                    financial_data['pbr'] = current_price / bps
                    
        except Exception as e:
            logging.debug(f"현재가 기반 재무지표 계산 실패 {symbol}: {e}")
        
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
            # 향상된 가격 프로바이더 사용
            price_data = self.price_provider.get_comprehensive_price_data(symbol)
            if price_data:
                if self.metrics:
                    self.metrics.record_api_call(True)
            else:
                if self.metrics:
                    self.metrics.record_api_call(False, "empty_price_payload")
            
            if price_data:
                current_price = DataValidator._finite(price_data.get('current_price'))
                
                data = {
                    'current_price': current_price,
                    'price_change': DataValidator._finite(price_data.get('price_change')),
                    'price_change_rate': DataValidator._finite(price_data.get('price_change_rate')),
                    'volume': DataValidator._finite(price_data.get('volume')),
                    'eps': DataValidator._finite(price_data.get('eps')),
                    'bps': DataValidator._finite(price_data.get('bps')),
                    'market_cap': DataValidator._finite(price_data.get('market_cap'))
                }
                
                # PER/PBR을 현재가 기반으로 실시간 계산
                if current_price and current_price > 0:
                    # EPS/BPS가 있으면 PER/PBR 계산
                    eps = DataValidator._finite(price_data.get('eps'))
                    bps = DataValidator._finite(price_data.get('bps'))
                    
                    if eps and eps > 0:
                        data['per'] = current_price / eps
                    else:
                        data['per'] = DataValidator._finite(price_data.get('per'))
                    
                    if bps and bps > 0:
                        data['pbr'] = current_price / bps
                    else:
                        data['pbr'] = DataValidator._finite(price_data.get('pbr'))
                else:
                    # 현재가가 없으면 기존 값 사용
                    data['per'] = DataValidator._finite(price_data.get('per'))
                    data['pbr'] = DataValidator._finite(price_data.get('pbr'))
                
                # 52주 고저 정보 조회 (실시간 플래그에 따라)
                w52_high = DataValidator._finite(price_data.get('w52_high'))
                w52_low = DataValidator._finite(price_data.get('w52_low'))
                
                if getattr(self, 'include_realtime', True) and (not w52_high or not w52_low):
                    # KIS API에서 추가 조회
                    try:
                        self.rate_limiter.acquire()
                        price_info = _with_retries(lambda: self.provider.get_stock_price_info(symbol))
                        if price_info:
                            w52_high = DataValidator._finite(price_info.get('w52_high')) or w52_high
                            w52_low = DataValidator._finite(price_info.get('w52_low')) or w52_low
                    except Exception as e:
                        logging.debug(f"KIS API 52주 고저 데이터 조회 실패 {symbol}: {e}")
                    
                    # 두 번째 재호출은 생략(초기 호출에서 대부분 커버됨)
                    # 정말 필요한 경우에만 플래그로 허용 가능
                
                # 여전히 없으면 기본값 설정 (0이 아닌 None으로)
                if w52_high and w52_high > 0:
                    data['w52_high'] = w52_high
                if w52_low and w52_low > 0:
                    data['w52_low'] = w52_low
                
                # 캐시에 저장
                self._set_cached(self._cache_price, symbol, data)
                return data
        except Exception as e:
            if self.metrics:
                self.metrics.record_api_call(False, "price_data_error")
            log_error("가격 데이터 조회", symbol, e)
        
        data = {}
        self._set_cached(self._cache_price, symbol, data)
        return data

class EnhancedScoreCalculator(ScoreCalculator):
    """향상된 점수 계산기"""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
    
    def calculate_score(self, data: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """통합 점수를 계산합니다."""
        score = 0.0
        breakdown = {}
        
        # 각 분석 요소별 점수 계산
        opinion_score = self._calculate_opinion_score(data.get('opinion_analysis', {}))
        estimate_score = self._calculate_estimate_score(data.get('estimate_analysis', {}))
        financial_score = self._calculate_financial_score(data.get('financial_data', {}))
        growth_score = self._calculate_growth_score(data.get('financial_data', {}))
        scale_score = self._calculate_scale_score(data.get('market_cap', 0))
        
        # 52주 위치 점수 계산 (0~100 정규화)
        price_position_score = self._calculate_price_position_score(data.get('price_position'))
        
        # 가중치 적용 (외부 신호 가중치 0으로 고정)
        weights = self.config.weights.copy()
        weights['external_signal'] = 0  # 실데이터 미반영 항목은 0으로 고정
        
        # 결측 데이터 감지 및 가중치 조정
        available_weights = {}
        total_weight = 0
        
        # 각 요소별 가용성 확인 및 가중치 조정
        if opinion_score > 0:  # 데이터가 있는 경우
            available_weights['opinion_analysis'] = weights.get('opinion_analysis', 0)
        else:  # 데이터가 없는 경우 중립점 적용
            opinion_score = 50.0  # 중립점
            available_weights['opinion_analysis'] = weights.get('opinion_analysis', 0) * 0.5  # 가중치 절반
        
        if estimate_score > 0:
            available_weights['estimate_analysis'] = weights.get('estimate_analysis', 0)
        else:
            estimate_score = 50.0
            available_weights['estimate_analysis'] = weights.get('estimate_analysis', 0) * 0.5
        
        if financial_score > 0:
            available_weights['financial_ratios'] = weights.get('financial_ratios', 0)
        else:
            financial_score = 50.0
            available_weights['financial_ratios'] = weights.get('financial_ratios', 0) * 0.5
        
        if growth_score > 0:
            available_weights['growth_analysis'] = weights.get('growth_analysis', 0)
        else:
            growth_score = 50.0
            available_weights['growth_analysis'] = weights.get('growth_analysis', 0) * 0.5
        
        if scale_score > 0:
            available_weights['scale_analysis'] = weights.get('scale_analysis', 0)
        else:
            scale_score = 50.0
            available_weights['scale_analysis'] = weights.get('scale_analysis', 0) * 0.5
        
        # 가격위치는 항상 적용 (None이면 중립점)
        available_weights['price_position'] = weights.get('price_position', 0)
        
        # 총 가중치 계산
        total_weight = sum(available_weights.values())
        
        # 가중치 정규화 (총합이 100이 되도록)
        if total_weight > 0:
            for key in available_weights:
                available_weights[key] = (available_weights[key] / total_weight) * 100
        
        score += opinion_score * available_weights.get('opinion_analysis', 0) / 100
        score += estimate_score * available_weights.get('estimate_analysis', 0) / 100
        score += financial_score * available_weights.get('financial_ratios', 0) / 100
        score += growth_score * available_weights.get('growth_analysis', 0) / 100
        score += scale_score * available_weights.get('scale_analysis', 0) / 100
        score += price_position_score * available_weights.get('price_position', 0) / 100
        
        breakdown = {
            '투자의견': opinion_score * available_weights.get('opinion_analysis', 0) / 100,
            '추정실적': estimate_score * available_weights.get('estimate_analysis', 0) / 100,
            '재무비율': financial_score * available_weights.get('financial_ratios', 0) / 100,
            '성장성': growth_score * available_weights.get('growth_analysis', 0) / 100,
            '규모': scale_score * available_weights.get('scale_analysis', 0) / 100,
            '가격위치': price_position_score * available_weights.get('price_position', 0) / 100
        }
        
        
        return min(100, max(0, score)), breakdown
    
    def _calculate_opinion_score(self, opinion_data: Dict[str, Any]) -> float:
        """투자의견 점수 계산"""
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
        return 0.0
    
    def _calculate_estimate_score(self, estimate_data: Dict[str, Any]) -> float:
        """추정실적 점수 계산 (가중치 반영, 0~100 스케일링 수정)"""
        w = self.config.estimate_analysis_weights
        fh = DataValidator.safe_float(estimate_data.get('financial_health_score', 0))  # 0~15
        val = DataValidator.safe_float(estimate_data.get('valuation_score', 0))        # 0~15
        total_weight = w['financial_health'] + w['valuation']
        # 0~15를 가중 평균 → 0~15 → 0~100
        weighted_raw = (fh * w['financial_health'] + val * w['valuation']) / total_weight  # 0~15
        return (weighted_raw / 15.0) * 100.0
    
    def _calculate_financial_score(self, financial_data: Dict[str, Any]) -> float:
        """재무비율 점수 계산 (가중치 반영, config 안전성 강화)"""
        w = self.config.financial_ratio_weights
        
        # 가중치 안전성 강화 (기본값 제공)
        roe_w = w.get('roe_score', 8)
        roa_w = w.get('roa_score', 5)
        debt_w = w.get('debt_ratio_score', 7)
        npm_w = w.get('net_profit_margin_score', 5)
        cr_w = w.get('current_ratio_score', 3)
        
        # 각 항목을 0~1로 스코어링
        roe = DataValidator.safe_float(financial_data.get('roe', 0))
        roe_point = 1.0 if roe >= 20 else 0.75 if roe >= 15 else 0.5 if roe >= 10 else 0.25 if roe >= 5 else 0.0

        roa = DataValidator.safe_float(financial_data.get('roa', 0))
        roa_point = 1.0 if roa >= 10 else 0.8 if roa >= 7 else 0.6 if roa >= 5 else 0.4 if roa >= 3 else 0.0

        debt_ratio = DataValidator.safe_float(financial_data.get('debt_ratio', 999))
        debt_point = 1.0 if debt_ratio <= 30 else 0.75 if debt_ratio <= 50 else 0.5 if debt_ratio <= 70 else 0.25 if debt_ratio <= 100 else 0.0

        npm = DataValidator.safe_float(financial_data.get('net_profit_margin', 0))
        npm_point = 1.0 if npm >= 15 else 0.8 if npm >= 10 else 0.6 if npm >= 5 else 0.4 if npm >= 2 else 0.0

        cr = DataValidator.safe_float(financial_data.get('current_ratio', 0))
        cr_point = 1.0 if cr >= 200 else 0.67 if cr >= 150 else 0.33 if cr >= 100 else 0.0

        # 가중합 → 0~1 → 0~100
        total_weight = roe_w + roa_w + debt_w + npm_w + cr_w
        weighted = (
            roe_point * roe_w +
            roa_point * roa_w +
            debt_point * debt_w +
            npm_point * npm_w +
            cr_point * cr_w
        ) / total_weight
        return weighted * 100.0
    
    def _calculate_growth_score(self, financial_data: Dict[str, Any]) -> float:
        """성장성 점수 계산"""
        revenue_growth = DataValidator.safe_float(financial_data.get('revenue_growth_rate', 0))
        if revenue_growth >= 20:
            return 100
        elif revenue_growth >= 10:
            return 80
        elif revenue_growth >= 0:
            return 50
        elif revenue_growth >= -10:
            return 30
        else:
            return 0
    
    def _calculate_scale_score(self, market_cap: float) -> float:
        """규모 점수 계산"""
        if market_cap >= 100000:  # 메가캡
            return 100
        elif market_cap >= 50000:  # 대형주
            return 80
        elif market_cap >= 10000:  # 중대형주
            return 60
        elif market_cap >= 5000:   # 중형주
            return 40
        elif market_cap >= 1000:   # 소형주
            return 20
        else:
            return 0
    
    def _calculate_price_position_score(self, price_position: Optional[float]) -> float:
        """52주 위치에 따른 점수 계산 (0~100 정규화)"""
        if price_position is None:
            return 50.0  # 중립점
        
        # 52주 위치에 따른 점수 (0~100)
        if price_position >= 95:  # 52주 최고가의 95% 이상 (매우 높은 위치)
            return 10.0  # 매우 낮은 점수
        elif price_position >= 90:  # 52주 최고가의 90% 이상
            return 25.0  # 낮은 점수
        elif price_position >= 85:  # 52주 최고가의 85% 이상
            return 40.0  # 약간 낮은 점수
        elif price_position >= 80:  # 52주 최고가의 80% 이상
            return 48.0  # 약간 낮은 점수
        elif price_position <= 20:  # 52주 최저가의 20% 이하
            return 85.0  # 높은 점수 (저가 매수 기회)
        elif price_position <= 30:  # 52주 최저가의 30% 이하
            return 70.0  # 약간 높은 점수
        else:
            return 50.0  # 중간 위치 (중립점)
    
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
        self.config_manager = ConfigManager(config_file)
        self.rate_limiter = TPSRateLimiter()
        self.include_realtime = include_realtime
        self.include_external = include_external
        
        # 메트릭 수집기 초기화
        self.metrics = MetricsCollector()
        
        # 분석기 초기화
        self.opinion_analyzer = InvestmentOpinionAnalyzer()
        self.estimate_analyzer = EstimatePerformanceAnalyzer()
        self.provider = KISDataProvider()
        self.enhanced_price_provider = EnhancedPriceProvider()
        self.data_provider = FinancialDataProvider(self.provider, self.rate_limiter, metrics=self.metrics)
        # 플래그 전달
        self.data_provider.include_realtime = self.include_realtime
        
        # 설정 로드
        self.config = self._load_analysis_config()
        self.score_calculator = EnhancedScoreCalculator(self.config)
        
        # KOSPI 데이터 로드
        self.kospi_data = None
        self._load_kospi_data()
        
        # 섹터 벡터 캐시 (TTL 10분)
        self._sector_cache = OrderedDict()
        self._sector_cache_ttl = 600  # 10분
        self._sector_cache_lock = RLock()
        
        # 외부 분석기 스레드 안전성을 위한 락
        self._ext_lock = RLock()
    
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
                'D': 20,
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
    
    def _load_kospi_data(self):
        """KOSPI 마스터 데이터를 로드합니다."""
        try:
            kospi_file = 'kospi_code.xlsx'
            if os.path.exists(kospi_file):
                try:
                    self.kospi_data = pd.read_excel(kospi_file, engine="openpyxl")
                except Exception:
                    self.kospi_data = pd.read_excel(kospi_file)  # fallback
                self.kospi_data['단축코드'] = (
                    self.kospi_data['단축코드']
                        .astype(str)
                        .str.replace(r'\.0$', '', regex=True)
                        .str.zfill(6)
                )
                
                # 스키마 검증
                required_cols = {"단축코드", "한글명", "시가총액"}
                if not required_cols.issubset(self.kospi_data.columns):
                    raise ValueError(f"KOSPI 스키마 불일치: 필요컬럼 {required_cols}, 실제 {set(self.kospi_data.columns)}")
                
                logging.info(f"KOSPI 마스터 데이터 로드 완료: {len(self.kospi_data)}개 종목")
            else:
                logging.warning(f"{kospi_file} 파일을 찾을 수 없습니다.")
                self.kospi_data = pd.DataFrame()
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
        start_time = time.time()
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
                    enhanced_grade='F'
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
            
            # 섹터 분석 수행
            sector_analysis = self._analyze_sector(symbol, name)
            
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
            
            # 스코어러에 컨텍스트 주입
            self.score_calculator._ctx_sector = analysis_data['sector_info']
            self.score_calculator._ctx_price = analysis_data['price_data']
            
            enhanced_score, score_breakdown = self.score_calculator.calculate_score(analysis_data)
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
                self.metrics.record_analysis_duration(time.time() - start_time)
    
    def _is_preferred_stock(self, name: str) -> bool:
        """우선주 여부 확인"""
        return DataValidator.is_preferred_stock(name)
    
    def _analyze_opinion(self, symbol: str, days_back: int, name: str = "") -> Dict[str, Any]:
        """투자의견 분석 (컨텍스트 보강)"""
        if not self.include_external:
            return {}
        try:
            with self._ext_lock:
                return self.opinion_analyzer.analyze_single_stock(symbol, days_back=days_back)
        except Exception as e:
            log_error("투자의견 분석", f"{symbol}({name})", e)
            return {}
    
    def _analyze_estimate(self, symbol: str, name: str = "") -> Dict[str, Any]:
        """추정실적 분석 (컨텍스트 보강)"""
        if not self.include_external:
            return {}
        try:
            with self._ext_lock:
                return self.estimate_analyzer.analyze_single_stock(symbol)
        except Exception as e:
            log_error("추정실적 분석", f"{symbol}({name})", e)
            return {}
    
    def _analyze_sector(self, symbol: str, name: str = "") -> Dict[str, Any]:
        """섹터 분석 수행"""
        try:
            # 기본 섹터 정보 가져오기
            sector_info = self._get_sector_characteristics(symbol)
            sector_name = sector_info.get('sector_name', '기타')
            
            # 간단한 섹터 점수 계산 (PER, PBR, ROE 기반)
            price_data = self.data_provider.get_price_data(symbol)
            financial_data = self.data_provider.get_financial_data(symbol)
            
            if not price_data or not financial_data:
                return {
                    'sector_analysis': {
                        'sector_grade': 'C',
                        'total_score': 50.0,
                        'breakdown': {
                            '재무_건전성': 50.0,
                            '성장성': 50.0,
                            '안정성': 50.0
                        }
                    }
                }
            
            # PER, PBR, ROE 기반 점수 계산
            per = price_data.get('per', 0)
            pbr = price_data.get('pbr', 0)
            roe = financial_data.get('roe', 0)
            
            # 점수 계산 (간단한 로직)
            financial_score = 50.0
            growth_score = 50.0
            stability_score = 50.0
            
            if per > 0 and per < 20:
                financial_score += 20
            elif per > 0 and per < 30:
                financial_score += 10
            
            if pbr > 0 and pbr < 2:
                financial_score += 15
            elif pbr > 0 and pbr < 3:
                financial_score += 10
            
            if roe > 15:
                growth_score += 25
            elif roe > 10:
                growth_score += 15
            elif roe > 5:
                growth_score += 10
            
            # 안정성 점수 (시가총액 기반)
            market_cap = self._get_market_cap(symbol)
            if market_cap > 100000:  # 1조 이상
                stability_score += 20
            elif market_cap > 50000:  # 5000억 이상
                stability_score += 10
            
            # 최종 점수 계산
            total_score = (financial_score + growth_score + stability_score) / 3
            
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
            
            return {
                'sector_analysis': {
                    'sector_grade': grade,
                    'total_score': total_score,
                    'breakdown': {
                        '재무_건전성': financial_score,
                        '성장성': growth_score,
                        '안정성': stability_score
                    }
                }
            }
            
        except Exception as e:
            logging.debug(f"섹터 분석 실패 {symbol}: {e}")
            return {
                'sector_analysis': {
                    'sector_grade': 'C',
                    'total_score': 50.0,
                    'breakdown': {
                        '재무_건전성': 50.0,
                        '성장성': 50.0,
                        '안정성': 50.0
                    }
                }
            }
    
    def _get_market_cap(self, symbol: str) -> float:
        """시가총액 조회"""
        if self.kospi_data is not None and not self.kospi_data.empty:
            stock_info = self.kospi_data[self.kospi_data['단축코드'] == str(symbol)]
            if not stock_info.empty:
                return DataValidator.safe_float(stock_info.iloc[0]['시가총액'])
        return 0.0
    
    def _calculate_price_position(self, price_data: Dict[str, Any]) -> Optional[float]:
        """52주 위치 계산 (NaN/0-division 방지, 0~100 클램프)"""
        current_price = DataValidator.safe_float(price_data.get('current_price', 0))
        w52_high = DataValidator.safe_float(price_data.get('w52_high', 0))
        w52_low = DataValidator.safe_float(price_data.get('w52_low', 0))
        
        if current_price > 0 and w52_high > w52_low > 0:
            raw = ((current_price - w52_low) / (w52_high - w52_low)) * 100.0
            if not math.isnan(raw) and math.isfinite(raw):
                return max(0.0, min(100.0, raw))
        return None
    
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
        """업종별 특성 정보 반환"""
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
            
            # 하드코딩된 매핑에서 먼저 찾기
            if str(symbol) in sector_mapping:
                sector = sector_mapping[str(symbol)]
                return self._get_sector_benchmarks(sector)
            
            # KOSPI 데이터에서 업종 정보 가져오기 (여러 컬럼 후보 확인)
            if hasattr(self, 'kospi_data') and not self.kospi_data.empty:
                stock_info = self.kospi_data[self.kospi_data['단축코드'] == str(symbol)]
                if not stock_info.empty:
                    for col in ('업종', '지수업종대분류', '업종명', '섹터'):
                        if col in stock_info.columns:
                            sector = str(stock_info.iloc[0].get(col) or '기타')
                            if sector and sector != '기타':
                                return self._get_sector_benchmarks(sector)
            
            return self._get_sector_benchmarks('기타')
        except Exception as e:
            log_error("업종 특성 분석", symbol, e)
            return self._get_sector_benchmarks('기타')
    
    def _sanitize_leaders(self, leaders):
        """섹터 리더 목록 정합성 검증 (KOSPI 데이터 기준)"""
        if self.kospi_data is None or self.kospi_data.empty:
            return leaders
        codes = set(self.kospi_data['단축코드'].astype(str))
        return [c for c in leaders if c in codes]
    
    def _get_sector_benchmarks(self, sector: str) -> Dict[str, Any]:
        """업종별 벤치마크 기준 반환"""
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
                'leaders': ['207940', '068270', '006280', '161890']  # 삼성바이오로직스, 셀트리온, 녹십자, 코스모신소재
            },
            '에너지': {
                'per_range': (5, 20),
                'pbr_range': (0.5, 2.5),
                'roe_range': (5, 15),
                'description': '사이클 특성, 변동성 큰 수익',
                'leaders': ['034020', '042660', '010140', '015760']  # 두산에너빌리티, 한화오션, 삼성중공업, 동서
            },
            '소비재': {
                'per_range': (10, 30),
                'pbr_range': (1.0, 4.0),
                'roe_range': (8, 18),
                'description': '안정적 수요, 적정 수익성',
                'leaders': ['028260', '017670', '003550', '000720']  # 삼성물산, SK텔레콤, LG, 현대건설
            },
            '기타': {
                'per_range': (8, 25),
                'pbr_range': (0.8, 3.0),
                'roe_range': (8, 20),
                'description': '일반적 기준',
                'leaders': []
            }
        }
        
        # 업종명 매칭
        sector_key = '기타'
        s = str(sector).strip().lower()
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
    
    def _calculate_leader_bonus(self, symbol: str, sector: str, market_cap: float) -> float:
        """업종별 대장주 가산점 계산"""
        try:
            # 대장주 여부 확인
            is_leader = self._is_sector_leader(symbol, sector)
            if not is_leader:
                return 0.0
            
            # 품질 조건 추가: ROE >= 8 & PBR <= 섹터 상단
            price = self.data_provider.get_price_data(symbol)
            fin = self.data_provider.get_financial_data(symbol)
            pbr = DataValidator.safe_float(price.get('pbr'), 0)
            roe = DataValidator.safe_float(fin.get('roe'), 0)
            sec = self._get_sector_benchmarks(sector)
            
            # 품질 컷: ROE < 8 또는 PBR > 섹터 상단 시 보너스 없음
            if roe < 8 or (sec and pbr > sec['pbr_range'][1]):
                return 0.0
            
            # 강도 축소: 캡 5점
            if market_cap >= 1000000:  # 100조원 이상 (초대형)
                return 5.0
            elif market_cap >= 500000:  # 50조원 이상 (대형)
                return 4.0
            elif market_cap >= 100000:  # 10조원 이상 (중대형)
                return 3.5
            elif market_cap >= 50000:   # 5조원 이상 (중형)
                return 3.0
            else:  # 5조원 미만 (소형)
                return 2.5
                
        except Exception as e:
            log_error("대장주 가산점 계산", symbol, e)
            return 0.0
    
    def _evaluate_valuation_by_sector(self, symbol: str, per: float, pbr: float, roe: float, market_cap: float = 0) -> Dict[str, Any]:
        """섹터 내부 백분위 기반 밸류에이션 평가"""
        start_time = time.time()
        try:
            import math
            import numpy as np
            
            sector_info = self._get_sector_characteristics(symbol)
            sector_name = sector_info.get('name', '기타')
            
            # 섹터 동종군 샘플링 + 캐시 사용
            vals = self._get_sector_peers_snapshot(sector_name)
            
            # 백분위 계산
            if len(vals) == 0:
                return {'total_score': 50, 'base_score': 50, 'leader_bonus': 0, 'is_leader': False, 'grade': 'C', 'description': '평가 불가 - 데이터 부족', 'per_score': 50, 'pbr_score': 50, 'roe_score': 50, 'sector_info': sector_info}
            
            arr = np.array(vals)
            if arr.ndim == 1:  # 1차원 배열인 경우 2차원으로 변환
                arr = arr.reshape(-1, 3)
            
            def pct_rank(x, col):
                if arr.shape[1] <= col:
                    return 0.5
                colv = arr[:, col]
                colv = colv[~np.isnan(colv)]
                if len(colv) < 10 or not math.isfinite(x):  # 최소 10개 데이터 필요
                    return 0.5
                return (colv < x).mean()  # 0~1
            
            per_p = pct_rank(per, 0)   # 낮을수록 좋음 → score = 1 - per_p
            pbr_p = pct_rank(pbr, 1)   # 낮을수록 좋음 → score = 1 - pbr_p
            roe_p = pct_rank(roe, 2)   # 높을수록 좋음 → score = roe_p
            
            # 기본 점수 계산
            base_score = ((1-per_p) + (1-pbr_p) + roe_p) / 3 * 100.0
            
            # 리더 보너스(축소 후) 적용
            leader_bonus = self._calculate_leader_bonus(symbol, sector_name, market_cap)
            total_score = min(100, max(0, base_score + leader_bonus))
            
            # 등급 결정
            grade = "A+" if total_score>=80 else "A" if total_score>=70 else "B+" if total_score>=60 else "B" if total_score>=50 else "C" if total_score>=40 else "D"
            
            # 대장주 여부 확인
            is_leader = self._is_sector_leader(symbol, sector_name)
            
            return {
                'total_score': total_score,
                'base_score': base_score,
                'leader_bonus': leader_bonus,
                'is_leader': is_leader,
                'grade': grade,
                'description': '섹터 백분위 기반 점수',
                'per_score': (1-per_p)*100,
                'pbr_score': (1-pbr_p)*100,
                'roe_score': (roe_p)*100,
                'sector_info': sector_info
            }
            
        except Exception as e:
            log_error("업종별 밸류에이션 평가", symbol, e)
            return {
                'total_score': 50,
                'base_score': 50,
                'leader_bonus': 0,
                'is_leader': False,
                'grade': 'C',
                'description': '평가 불가',
                'per_score': 50,
                'pbr_score': 50,
                'roe_score': 50,
                'sector_info': {'description': '기타'}
            }
        finally:
            # 섹터 평가 소요 시간 기록
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.record_sector_evaluation(duration)
    
    def _calculate_metric_score(self, value: float, min_val: float, max_val: float, reverse: bool = False) -> float:
        """지표별 점수 계산 (분모 0 방어) - 미사용 헬퍼(보관)"""
        if value <= 0:
            return 0
        
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
        elif score >= thresholds.get('D', 20):
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
        p = _pick_price(stock_dict.get('enhanced_result')) or _pick_price(stock_dict.get('basic_result'))
        current = p.get('current_price')
        w52h, w52l = p.get('w52_high'), p.get('w52_low')
        
        # 현재가가 없으면 (옵션 허용 시) 실시간 조회
        if not current and self.include_realtime:
            try:
                current = self.enhanced_price_provider.get_current_price(stock_dict.get('symbol'))
            except: 
                pass
        
        # 52주 고가/저가가 없으면 (옵션 허용 시) 실시간 조회 (KIS + 재시도 + 레이트리미터)
        if (not w52h or not w52l) and self.include_realtime:
            try:
                symbol = stock_dict.get('symbol')
                if symbol:
                    self.rate_limiter.acquire()
                    price_info = _with_retries(lambda: self.provider.get_stock_price_info(symbol))
                    if price_info:
                        w52h = price_info.get('w52_high') or w52h
                        w52l = price_info.get('w52_low') or w52l
            except Exception as e:
                logging.debug(f"52주 고가/저가 조회 실패 {stock_dict.get('symbol')}: {e}")
        
        # 여전히 52주 정보가 없으면 KOSPI 파일에서 시도
        if (not w52h or not w52l) and self.kospi_data is not None and not self.kospi_data.empty:
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
        
        # 52주 위치 계산
        position = None
        try:
            if current and w52h and w52l and w52h > w52l:
                position = max(0, min(100, (float(current)-float(w52l))/(float(w52h)-float(w52l))*100))
                logging.debug(f"52주 위치 계산 성공 {stock_dict.get('symbol')}: current={current}, w52h={w52h}, w52l={w52l}, position={position:.1f}%")
            else:
                logging.debug(f"52주 위치 계산 불가 {stock_dict.get('symbol')}: current={current}, w52h={w52h}, w52l={w52l}")
        except Exception as e:
            logging.debug(f"52주 위치 계산 실패 {stock_dict.get('symbol')}: {e}")
        
        return current, position
    
    def _position_label(self, pos: Optional[float]) -> str:
        """52주 위치에 따른 라벨을 반환합니다."""
        if pos is None:
            return "N/A"
        if pos >= 95:
            return f"{pos:.1f}% 🔴 과열/추세"
        if pos >= 85:
            return f"{pos:.1f}% 🟡 상단"
        if pos <= 30:
            return f"{pos:.1f}% 🟢 저가구간(할인)"
        return f"{pos:.1f}% 중립"
    
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
            sector = None
            if isinstance(ar, AnalysisResult):
                sector = ar.sector_analysis or {}
            if not sector:
                # 혹시 상위 dict에 직접 실려오는 경우 대비
                sector = stock.get("sector_analysis", {})

            # 중첩 구조와 평면 구조 모두 대응
            node = sector.get("sector_analysis", sector)
            grade = node.get("sector_grade") or node.get("grade")
            total = node.get("total_score")

            if grade is None or total is None:
                return "N/A"
            return f"{grade}({float(total):.1f})"
        except Exception:
            return "N/A"

    def _get_sector_valuation_score(self, stock: Dict[str, Any]) -> str:
        """섹터 상대 밸류 점수를 반환합니다."""
        try:
            # 섹터 평가 점수 추출 (중첩된 구조 확인)
            sector_analysis = stock.get('sector_analysis', {})
            if sector_analysis:
                # 중첩된 sector_analysis 구조 확인
                nested_sector = sector_analysis.get('sector_analysis', {})
                if nested_sector:
                    grade = nested_sector.get('sector_grade', 'F')
                    total_score = nested_sector.get('total_score', 0)
                    return f"{grade}({total_score:.1f})"
                else:
                    # 직접적인 구조
                    grade = sector_analysis.get('grade', 'F')
                    total_score = sector_analysis.get('total_score', 0)
                    return f"{grade}({total_score:.1f})"
            else:
                return "N/A"
        except Exception as e:
            logging.debug(f"섹터 밸류 점수 계산 실패 {stock.get('symbol')}: {e}")
            return "N/A"
    
    def _get_basket_type(self, stock: Dict[str, Any]) -> str:
        """종목의 52주 위치를 기반으로 바스켓 타입을 반환합니다."""
        try:
            current_price, price_position = self._resolve_price_and_position(stock)
            return self._classify_bucket(price_position)
        except Exception as e:
            logging.debug(f"바스켓 분류 실패 {stock.get('symbol')}: {e}")
            return "분류불가"
    
    def _get_sector_peers_snapshot(self, sector_name: str):
        """섹터 동종군 샘플링 + 캐시 (TTL 10분)"""
        with self._sector_cache_lock:
            now = time.monotonic()
            hit = self._sector_cache.get(sector_name)
            if hit and now - hit[0] < self._sector_cache_ttl:
                if self.metrics:
                    self.metrics.record_cache_hit('sector')
                return hit[1]
            
            if self.metrics:
                self.metrics.record_cache_miss('sector')
            
            # 동종군 찾기
            peers = self.kospi_data.copy()
            for col in ('업종', '지수업종대분류', '업종명', '섹터'):
                if col in peers.columns:
                    colseries = peers[col].astype(str)
                    exact = peers[colseries == sector_name]
                    peers = exact if not exact.empty else peers[colseries.str.contains(sector_name, na=False)]
                    break
            
            # 샘플링 (최대 200개)
            codes = peers['단축코드'].astype(str).tolist()
            import random
            random.shuffle(codes)
            codes = codes[:200]
            
            vals = []
            for code in codes:
                try:
                    pr = self.data_provider.get_price_data(code)
                    fn = self.data_provider.get_financial_data(code)
                    vals.append((
                        DataValidator.safe_float(pr.get('per'), float('nan')),
                        DataValidator.safe_float(pr.get('pbr'), float('nan')),
                        DataValidator.safe_float(fn.get('roe'), float('nan')),
                    ))
                except Exception:
                    continue
            
            snapshot = vals
            self._sector_cache[sector_name] = (now, snapshot)
            
            # LRU 관리 (최대 32개 섹터)
            while len(self._sector_cache) > 32:
                self._sector_cache.popitem(last=False)
            
            return snapshot
    
    def _analyze_stocks_parallel(self, stocks_data, max_workers: int = None) -> List[AnalysisResult]:
        """종목들을 병렬로 분석하는 공통 메서드"""
        results = []
        if max_workers is None:
            max_workers = min(4, os.cpu_count() or 1)

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
                        logging.warning(f"분석 실패: {name} ({symbol}) - {result.error}")
                except Exception as e:
                    log_error("종목 분석", f"{name}({symbol})", e)
                    continue

        # 분석된 종목 수 기록
        if hasattr(self, "metrics") and self.metrics:
            self.metrics.record_stocks_analyzed(len(results))
        
        return results
    
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
            start_time = time.time()
            
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
            analysis_time = time.time() - start_time
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
                'top_recommendations': [
                    {
                        'symbol': r.symbol,
                        'name': r.name,
                        'enhanced_score': r.enhanced_score,
                        'enhanced_grade': r.enhanced_grade,
                        'market_cap': r.market_cap,
                        'current_price': r.current_price,
                        'price_position': r.price_position,
                        'breakdown': r.score_breakdown,
                        'basic_result': r,
                        'enhanced_result': r
                    }
                    for r in filtered_results[:20]  # 상위 20개만
                ],
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
    
    def analyze_top_market_cap_stocks_enhanced(self, count: int = 50, min_score: float = 20.0, 
                                             max_workers: Optional[int] = None) -> Dict[str, Any]:
        """
        시가총액 상위 종목 향상된 분석
        
        Note: 실제 로직은 인스턴스 플래그(self.include_realtime, self.include_external)를 사용합니다.
        """
        try:
            start_time = time.time()
            
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
            analysis_time = time.time() - start_time
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
                'top_recommendations': [
                    {
                        'symbol': r.symbol,
                        'name': r.name,
                        'enhanced_score': r.enhanced_score,
                        'enhanced_grade': r.enhanced_grade,
                        'market_cap': r.market_cap,
                        'current_price': r.current_price,
                        'price_position': r.price_position,
                        'breakdown': r.score_breakdown,
                        'basic_result': r,
                        'enhanced_result': r
                    }
                    for r in filtered_results[:15]  # 상위 15개만
                ],
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
        """향상된 업종별 분포 분석"""
        try:
            sector_distribution = {}
            
            for result in results:
                # 업종 정보 추출 (간단한 하드코딩 방식)
                sector = self._get_sector_characteristics(result.symbol).get('name', '기타')
                
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
            console = Console()
            
            # 메타데이터 출력
            metadata = results.get('metadata', {})
            console.print(f"\n🚀 [bold blue]향상된 통합 분석 결과 v{metadata.get('analysis_version', '2.0_enhanced')}[/bold blue]")
            console.print(f"📅 분석 일시: {metadata.get('analysis_date', 'Unknown')}")
            console.print(f"⏱️ 분석 시간: {metadata.get('analysis_time_seconds', 0):.1f}초")
            total = metadata.get('total_analyzed', metadata.get('total_stocks_analyzed', 0))
            console.print(f"📊 총 분석 종목: {total}개")
            console.print(f"🎯 추천 종목: {metadata.get('undervalued_count', 0)}개")
            
            # 활성화된 기능 표시
            features = metadata.get('features_enabled', {})
            enabled_features = [k for k, v in features.items() if v]
            if enabled_features:
                console.print(f"✨ 활성화된 기능: {', '.join(enabled_features)}")
            
            # 상위 추천 종목 표
            top_recommendations = results.get('top_recommendations', [])
            if top_recommendations:
                table = Table(title="🏆 향상된 종목 추천 결과", box=box.ROUNDED)
                
                # 컬럼 추가
                table.add_column("순위", style="cyan", width=4)
                table.add_column("종목코드", style="magenta", width=8)
                table.add_column("종목명", style="green", width=15)
                table.add_column("현재가", style="white", width=10)
                table.add_column("종합점수", style="yellow", width=8)
                table.add_column("등급", style="red", width=6)
                table.add_column("시가총액", style="blue", width=12)
                table.add_column("52주위치", style="magenta", width=20, no_wrap=True)
                table.add_column("바스켓", style="bright_blue", width=12)
                table.add_column("포지션", style="bright_yellow", width=8)
                table.add_column("손익비", style="bright_red", width=12)
                table.add_column("섹터밸류", style="bright_cyan", width=10)
                table.add_column("투자의견", style="cyan", width=8)
                table.add_column("재무비율", style="green", width=8)
                table.add_column("가격위치", style="yellow", width=8)
                
                # 필터링된 추천 종목 (리스크관리 바스켓용)
                filtered_recommendations = []
                for stock in top_recommendations[:10]:
                    current_price, price_position = self._resolve_price_and_position(stock)
                    basket_type = self._classify_bucket(price_position)
                    
                    # 리스크관리 바스켓에서는 ≥85% 종목 제외
                    if basket_type == "밸류/리스크관리" and price_position is not None and price_position >= 85:
                        continue
                    
                    filtered_recommendations.append(stock)
                
                for i, stock in enumerate(filtered_recommendations, 1):
                    # 가격/위치 정보 해결
                    current_price, price_position = self._resolve_price_and_position(stock)
                    
                    # 현재가 표시
                    current_price_display = f"{current_price:,.0f}원" if current_price else "N/A"
                    
                    # 52주 위치 표시 (새로운 함수 사용)
                    position_text = self._position_label(price_position)
                    
                    # 바스켓 분류 로직 (새로운 함수 사용)
                    basket_type = self._classify_bucket(price_position)
                    basket_style = "green" if basket_type == "밸류/리스크관리" else "red" if basket_type == "모멘텀/브레이크아웃" else "yellow"
                    
                    # 포지션 사이징 계산
                    position_sizing = self._get_position_sizing(price_position, basket_type)
                    
                    # 손익비 기준 계산
                    risk_reward = self._get_risk_reward_ratio(price_position, basket_type)
                    
                    # 섹터 밸류 점수 계산
                    sector_valuation = self._extract_sector_valuation_text(stock)
                    
                    # breakdown 정보 추출
                    breakdown = {}
                    if isinstance(stock, dict):
                        # enhanced_result에서 breakdown 추출
                        enhanced_result = stock.get('enhanced_result')
                        if enhanced_result and hasattr(enhanced_result, 'score_breakdown'):
                            breakdown = enhanced_result.score_breakdown or {}
                        else:
                            breakdown = stock.get('score_breakdown', {})
                    else:
                        breakdown = getattr(stock, 'score_breakdown', {})
                    
                    opinion_score = breakdown.get('투자의견', 0)
                    financial_score = breakdown.get('재무비율', 0)
                    price_position_score = breakdown.get('가격위치', 0)

                    # 색상/라벨
                    if isinstance(stock, dict):
                        grade = stock.get('enhanced_grade', 'F')
                    else:
                        grade = getattr(stock, 'enhanced_grade', 'F')
                    grade_style = "green" if grade in ['A+','A','B+','B'] else "yellow" if grade in ['C+','C','D+','D'] else "red"
                    
                    # stock이 딕셔너리인지 객체인지 확인
                    if isinstance(stock, dict):
                        symbol = stock.get('symbol', 'N/A')
                        name = stock.get('name', 'N/A')
                        enhanced_score = stock.get('enhanced_score', 0)
                        market_cap = stock.get('market_cap', 0)
                    else:
                        symbol = getattr(stock, 'symbol', 'N/A')
                        name = getattr(stock, 'name', 'N/A')
                        enhanced_score = getattr(stock, 'enhanced_score', 0)
                        market_cap = getattr(stock, 'market_cap', 0)
                    
                    table.add_row(
                        str(i),
                        symbol,
                        name[:12] + ('...' if len(name)>12 else ''),
                        current_price_display,
                        f"{enhanced_score:.1f}",
                        f"[{grade_style}]{grade}[/{grade_style}]",
                        f"{market_cap:,.0f}억",
                        position_text,
                        f"[{basket_style}]{basket_type}[/{basket_style}]",
                        f"{position_sizing:.1f}x",
                        risk_reward,
                        sector_valuation,
                        f"{opinion_score:.1f}",
                        f"{financial_score:.1f}",
                        f"{price_position_score:.1f}"
                    )
                
                console.print(table)
                
                # 바스켓별 요약 정보 (필터링된 결과 기준)
                console.print(f"\n📊 [bold blue]바스켓별 분류 요약[/bold blue]")
                value_basket = [stock for stock in filtered_recommendations if self._get_basket_type(stock) == "밸류/리스크관리"]
                momentum_basket = [stock for stock in top_recommendations[:10] if self._get_basket_type(stock) == "모멘텀/브레이크아웃"]
                
                if value_basket:
                    console.print(f"🟢 [green]밸류/리스크관리 바스켓 ({len(value_basket)}개)[/green]")
                    for stock in value_basket:
                        current_price, price_position = self._resolve_price_and_position(stock)
                        position_display = f"{price_position:.1f}%" if price_position else "N/A"
                        console.print(f"  • {stock.get('name', 'N/A')}({stock.get('symbol', 'N/A')}) - {position_display}")
                
                if momentum_basket:
                    console.print(f"🔴 [red]모멘텀/브레이크아웃 바스켓 ({len(momentum_basket)}개) - 🔴 과열/추세 라벨[/red]")
                    for stock in momentum_basket:
                        current_price, price_position = self._resolve_price_and_position(stock)
                        position_display = f"{price_position:.1f}%" if price_position else "N/A"
                        console.print(f"  • {stock.get('name', 'N/A')}({stock.get('symbol', 'N/A')}) - {position_display} 🔴")
            
            # 업종별 분석 결과
            sector_analysis = results.get('sector_analysis', {})
            if sector_analysis:
                console.print(f"\n📊 [bold green]업종별 분석 결과[/bold green]")
                for sector, data in sector_analysis.items():
                    console.print(f"  {sector}: {data['count']}개 종목, 평균점수 {data['avg_score']:.1f}")
            
            # 시장 통계
            market_stats = results.get('market_statistics', {})
            if market_stats:
                console.print(f"\n📈 [bold blue]시장 통계[/bold blue]")
                console.print(f"  평균 점수: {market_stats.get('avg_score', 0):.1f}")
                console.print(f"  최고 점수: {market_stats.get('max_score', 0):.1f}")
                console.print(f"  최저 점수: {market_stats.get('min_score', 0):.1f}")
                
                score_dist = market_stats.get('score_distribution', {})
                if score_dist:
                    console.print(f"  점수 분포: A+({score_dist.get('A+', 0)}) A({score_dist.get('A', 0)}) B+({score_dist.get('B+', 0)}) B({score_dist.get('B', 0)})")
            
            # 메트릭 표시
            if hasattr(self, 'metrics'):
                metrics_summary = self.metrics.get_summary()
                console.print(f"\n📊 [bold blue]시스템 메트릭[/bold blue]")
                console.print(f"  API 성공률: {metrics_summary['api_success_rate']:.1f}%")
                console.print(f"  캐시 히트율: 가격({metrics_summary['cache_hit_rates']['price']:.1f}%) 재무({metrics_summary['cache_hit_rates']['financial']:.1f}%) 섹터({metrics_summary['cache_hit_rates']['sector']:.1f}%)")
                console.print(f"  평균 분석 시간: {metrics_summary['avg_analysis_duration']:.2f}초")
                console.print(f"  평균 섹터 평가: {metrics_summary['avg_sector_evaluation']:.2f}초")
                if metrics_summary['errors_by_type']:
                    console.print(f"  오류 유형: {', '.join([f'{k}({v}건)' for k, v in metrics_summary['errors_by_type'].items()])}")
            
        except Exception as e:
            log_error("결과 표시", error=e, level="error")
            print(f"❌ 결과 표시 중 오류 발생: {e}")

# =============================================================================
# 6. CLI 인터페이스 (기존과 동일)
# =============================================================================

# Typer CLI 앱 생성
app = typer.Typer(help="리팩토링된 향상된 통합 분석 시스템")

@app.command()
def test_enhanced_analysis(
    count: int = typer.Option(15, help="분석할 종목 수"),
    min_score: float = typer.Option(20, help="최소 점수"),
    max_workers: int = typer.Option(int(os.getenv("MAX_WORKERS", "2")), help="병렬 워커 수"),
    export: Optional[str] = typer.Option(None, help="CSV 경로 저장(예: result.csv)"),
    include_realtime: bool = typer.Option(True, help="실시간 데이터 포함"),
    include_external: bool = typer.Option(True, help="외부 데이터 포함")
):
    """향상된 분석 테스트"""
    analyzer = EnhancedIntegratedAnalyzer(include_realtime=include_realtime, include_external=include_external)
    
    # 시가총액 상위 종목 선별
    if analyzer.kospi_data is None or analyzer.kospi_data.empty:
        print("❌ KOSPI 데이터를 로드할 수 없습니다.")
        return
    
    top_stocks = analyzer.kospi_data.nlargest(count, '시가총액')
    
    # 병렬 분석 수행 (예외 안전성 및 취소 처리)
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(analyzer.analyze_single_stock, str(s['단축코드']), s['한글명']) for _, s in top_stocks.iterrows()]
        try:
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    logging.exception(f"워커 예외: {e}")
        except KeyboardInterrupt:
            logging.warning("사용자 중단: 남은 작업 취소")
            for f in futures:
                f.cancel()
            raise
    
    # 품질 하드필터 함수 (현실적 버전)
    def pass_quality(r: AnalysisResult) -> bool:
        """최소 품질 기준 통과 여부 확인 (현실적 버전)"""
        f = r.financial_data or {}
        roe = DataValidator.safe_float(f.get('roe'), 0)
        debt = DataValidator.safe_float(f.get('debt_ratio'), 999)
        npm = DataValidator.safe_float(f.get('net_profit_margin'), -999)
        # 현실적 컷: ROE≥3, 부채비율≤400, 순이익률≥-10
        return (roe >= 3) and (debt <= 400) and (npm >= -10)
    
    # 결과 필터링 전 통계 (선택적)
    if len(results) > 0:
        success_count = sum(1 for r in results if r.status == AnalysisStatus.SUCCESS)
        logging.info(f"분석 완료: {success_count}개 종목 성공 / {len(results)}개 전체")
    
    # 결과 필터링 및 정렬 (품질 필터 활성화)
    filtered_results = [
        r for r in results 
        if r.status == AnalysisStatus.SUCCESS 
        and r.enhanced_score >= min_score
        and pass_quality(r)  # 품질 필터 활성화
    ]
    
    # 고위치 차단형 룰 (85% 이하로 설정)
    filtered_results = [
        r for r in filtered_results
        if (r.price_position is None) or (r.price_position <= 85)  # 85% 이하만 허용
    ]
    
    filtered_results.sort(key=lambda x: (x.enhanced_score, x.market_cap), reverse=True)
    
    # 결과 출력
    logging.info(f"분석 완료: {len(filtered_results)}개 종목 추천 (최소점수: {min_score})")
    console = Console()
    table = Table(title=f"향상된 분석 결과 TOP {len(filtered_results)} (업종별 특성 반영)")
    table.add_column("순위", style="cyan")
    table.add_column("종목코드", style="white")
    table.add_column("종목명", style="white")
    table.add_column("점수", style="green", header_style="bold green")  # 클램프 후
    table.add_column("등급", style="yellow")
    table.add_column("현재가", style="blue")
    table.add_column("PER", style="cyan")
    table.add_column("PBR", style="cyan")
    table.add_column("ROE", style="cyan")
    table.add_column("업종평가", style="magenta")
    table.add_column("52주위치", style="magenta")
    table.add_column("이익률추세", style="yellow")
    table.add_column("시가총액", style="blue")
    
    for i, result in enumerate(filtered_results[:10], 1):
        # 가격 데이터 재활용 (재호출 없음)
        price_data = result.price_data
        price_position = result.price_position
        current_price = price_data.get('current_price', 0) if price_data else 0
        per = price_data.get('per', 0) if price_data else 0
        pbr = price_data.get('pbr', 0) if price_data else 0
        
        # 재무 지표 정보 가져오기
        financial_data = result.financial_data
        roe = financial_data.get('roe', 0) if financial_data else 0
        
        # PER, PBR, ROE 포맷팅
        # PER, PBR, ROE 정보 (일관된 N/A 표기)
        def _fmt(x, fmt="{:.1f}"):
            return fmt.format(x) if isinstance(x, (int, float)) and x > 0 else "N/A"
        
        per_text = _fmt(per)
        pbr_text = _fmt(pbr)
        roe_text = _fmt(roe, "{:.1f}%")
        
        # 업종별 밸류에이션 평가 (시가총액 포함)
        sector_evaluation = analyzer._evaluate_valuation_by_sector(result.symbol, per, pbr, roe, result.market_cap)
        sector_grade = sector_evaluation['grade']
        sector_score = sector_evaluation['total_score']
        is_leader = sector_evaluation['is_leader']
        
        # 업종 평가 포맷팅 (대장주 표시 포함)
        if is_leader:
            if sector_score >= 80:
                sector_text = f"{sector_grade} 🟢👑"
            elif sector_score >= 60:
                sector_text = f"{sector_grade} 🟡👑"
            else:
                sector_text = f"{sector_grade} 🔴👑"
        else:
            if sector_score >= 80:
                sector_text = f"{sector_grade} 🟢"
            elif sector_score >= 60:
                sector_text = f"{sector_grade} 🟡"
            else:
                sector_text = f"{sector_grade} 🔴"
        
        # 52주 위치 포맷팅 (NaN 방지)
        if price_position is not None and isinstance(price_position, (int, float)) and not math.isnan(price_position):
            if price_position >= 95:
                position_text = f"{price_position:.1f}% 🔴"
            elif price_position >= 90:
                position_text = f"{price_position:.1f}% 🟠"
            elif price_position >= 80:
                position_text = f"{price_position:.1f}% 🟡"
            elif price_position <= 20:
                position_text = f"{price_position:.1f}% 🟢"
            elif price_position <= 30:
                position_text = f"{price_position:.1f}% 🔵"
            else:
                position_text = f"{price_position:.1f}%"
        else:
            position_text = "N/A"
        
        # 이익률 추세 분석 (중복 API 호출 제거)
        profit_trend = analyzer._analyze_profit_trend(result.financial_data)
        if profit_trend == "improving":
            trend_text = "📈 개선"
        elif profit_trend == "declining":
            trend_text = "📉 감소"
        elif profit_trend == "stable":
            trend_text = "➡️ 안정"
        else:
            trend_text = "❓ 미분류"
        
        # 점수 안전성 강화 (0~100 클램프)
        safe_score = max(0.0, min(100.0, result.enhanced_score))
        
        table.add_row(
            str(i),
            result.symbol,
            result.name[:6] + "..." if len(result.name) > 6 else result.name,
            f"{safe_score:.1f}",
            result.enhanced_grade,
            f"{current_price:,.0f}원",
            per_text,
            pbr_text,
            roe_text,
            sector_text,
            position_text,
            trend_text,
            f"{result.market_cap:,.0f}억"
        )
    
    console.print(table)
    logging.info(f"분석 결과 출력 완료")
    
    # CSV 저장 (운영 편의, 빈 결과 가드, 경로 보장)
    if export:
        import csv
        os.makedirs(os.path.dirname(export) or ".", exist_ok=True)
        rows = [{
            "symbol": r.symbol,
            "name": r.name,
            "score": f"{r.enhanced_score:.1f}",
            "grade": r.enhanced_grade,
            "market_cap": int(r.market_cap),
            "current_price": int(r.current_price or 0),
        } for r in filtered_results]

        if not rows:
            logging.info(f"저장할 추천 결과가 없습니다: {export} 미생성")
        else:
            with open(export, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            logging.info(f"결과 저장: {export}")

@app.command()
def analyze_full_market(
    max_stocks: int = typer.Option(100, help="최대 분석 종목 수"),
    min_score: float = typer.Option(20, help="최소 점수"),
    include_realtime: bool = typer.Option(True, help="실시간 데이터 포함"),
    include_external: bool = typer.Option(True, help="외부 데이터 포함"),
    max_workers: Optional[int] = typer.Option(None, help="병렬 처리 워커 수 (기본값: CPU 코어 수)"),
    export: Optional[str] = typer.Option(None, help="JSON 결과 저장 경로")
):
    """향상된 전체 시장 분석"""
    analyzer = EnhancedIntegratedAnalyzer(include_realtime=include_realtime, include_external=include_external)
    
    # 전체 시장 분석 수행
    results = analyzer.analyze_full_market_enhanced(
        max_stocks=max_stocks, 
        min_score=min_score,
        include_realtime=include_realtime, 
        include_external=include_external,
        max_workers=max_workers
    )
    
    # 결과 표시
    analyzer._display_enhanced_results_table(results)
    
    # JSON 저장
    if export:
        try:
            import json
            os.makedirs(os.path.dirname(export) or ".", exist_ok=True)
            with open(export, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            logging.info(f"결과 저장: {export}")
        except Exception as e:
            log_error("결과 저장", error=e, level="error")

@app.command()
def analyze_top_market_cap(
    count: int = typer.Option(50, help="분석할 종목 수"),
    min_score: float = typer.Option(20, help="최소 점수"),
    include_realtime: bool = typer.Option(True, help="실시간 데이터 포함"),
    include_external: bool = typer.Option(True, help="외부 분석 포함"),
    max_workers: Optional[int] = typer.Option(None, help="병렬 처리 워커 수 (기본값: CPU 코어 수)"),
    export: Optional[str] = typer.Option(None, help="JSON 결과 저장 경로")
):
    """시가총액 상위 종목 향상된 분석"""
    analyzer = EnhancedIntegratedAnalyzer(include_realtime=include_realtime, include_external=include_external)
    
    # 시가총액 상위 종목 분석 수행
    results = analyzer.analyze_top_market_cap_stocks_enhanced(
        count=count, 
        min_score=min_score,
        max_workers=max_workers
    )
    
    # 결과 표시
    analyzer._display_enhanced_results_table(results)
    
    # JSON 저장
    if export:
        try:
            import json
            os.makedirs(os.path.dirname(export) or ".", exist_ok=True)
            with open(export, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            logging.info(f"결과 저장: {export}")
        except Exception as e:
            log_error("결과 저장", error=e, level="error")

if __name__ == "__main__":
    # 로깅 설정 (개선된 포맷터)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    try:
        app()
    except KeyboardInterrupt:
        logging.warning("프로그램이 사용자에 의해 중단되었습니다.")
        exit(0)
