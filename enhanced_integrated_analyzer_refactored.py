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

# monotonic time 별칭 (시스템 시간 변경에 안전)
_monotonic = time.monotonic

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
from threading import Lock, RLock
from collections import deque, OrderedDict

# 로깅 설정은 메인 실행부에서 초기화
from rich.console import Console
from rich.table import Table
from typing import Dict, Any, Tuple, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

# 기존 import들
from kis_data_provider import KISDataProvider
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
                sleep_time = 1.0 - (now - self.ts[0])
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
                    'scale_analysis': 5
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
        """우선주 여부 확인 (확장된 정규식)"""
        if not name or not isinstance(name, str):
            return False
        import re
        # 더 포괄적인 우선주 패턴
        pref_pattern = r'(우선주$)|(\s*우(?:[ABC])?(?:\(.+?\))?\s*$)|(\(우\)\s*$)'
        return bool(re.search(pref_pattern, str(name)))

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
    
    def __init__(self, provider: KISDataProvider, rate_limiter: TPSRateLimiter, ttl: float = None):
        self.provider = provider
        self.rate_limiter = rate_limiter
        self.financial_ratio_analyzer = FinancialRatioAnalyzer(provider)
        self.profit_ratio_analyzer = ProfitRatioAnalyzer(provider)
        self.stability_ratio_analyzer = StabilityRatioAnalyzer(provider)
        self._cache_price: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()
        self._cache_fin: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()
        self._cache_lock = RLock()
        self._ttl = ttl if ttl is not None else float(os.getenv("KIS_CACHE_TTL", "15.0"))
        self._max_keys = int(os.getenv("KIS_CACHE_MAX_KEYS", "2000"))
    
    def _get_cached(self, cache, key):
        """캐시에서 데이터 조회 (동시성 안전)"""
        now = _monotonic()
        with self._cache_lock:
            hit = cache.get(key)
            if hit and now - hit[0] < self._ttl:
                return hit[1]
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
            logging.warning(f"재무비율 분석 실패 {symbol}: {e}")
        
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
            logging.warning(f"수익성비율 분석 실패 {symbol}: {e}")
        
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
            logging.warning(f"안정성비율 분석 실패 {symbol}: {e}")
        
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
            self.rate_limiter.acquire()
            price_info = _with_retries(lambda: self.provider.get_stock_price_info(symbol))
            if price_info:
                data = {
                    'current_price': DataValidator._finite(price_info.get('current_price')),
                    'w52_high': DataValidator._finite(price_info.get('w52_high')),
                    'w52_low': DataValidator._finite(price_info.get('w52_low')),
                    'per': DataValidator._finite(price_info.get('per')),
                    'pbr': DataValidator._finite(price_info.get('pbr')),
                    'eps': DataValidator._finite(price_info.get('eps')),
                    'bps': DataValidator._finite(price_info.get('bps'))
                }
                # 캐시에 저장
                self._set_cached(self._cache_price, symbol, data)
                return data
        except Exception as e:
            logging.warning(f"가격 데이터 조회 실패 {symbol}: {e}")
        
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
        
        # 52주 위치 페널티 계산
        price_position_penalty = self._calculate_price_position_penalty(data.get('price_position'))
        
        # 가중치 적용
        weights = self.config.weights
        score += opinion_score * weights.get('opinion_analysis', 0) / 100
        score += estimate_score * weights.get('estimate_analysis', 0) / 100
        score += financial_score * weights.get('financial_ratios', 0) / 100
        score += growth_score * weights.get('growth_analysis', 0) / 100
        score += scale_score * weights.get('scale_analysis', 0) / 100
        score += price_position_penalty  # 페널티 적용
        
        breakdown = {
            '투자의견': opinion_score * weights.get('opinion_analysis', 0) / 100,
            '추정실적': estimate_score * weights.get('estimate_analysis', 0) / 100,
            '재무비율': financial_score * weights.get('financial_ratios', 0) / 100,
            '성장성': growth_score * weights.get('growth_analysis', 0) / 100,
            '규모': scale_score * weights.get('scale_analysis', 0) / 100,
            '가격위치': price_position_penalty
        }
        
        return min(100, max(0, score)), breakdown
    
    def _calculate_opinion_score(self, opinion_data: Dict[str, Any]) -> float:
        """투자의견 점수 계산"""
        consensus_score = opinion_data.get('consensus_score')
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
    
    def _calculate_price_position_penalty(self, price_position: Optional[float]) -> float:
        """52주 위치에 따른 페널티 계산 (개선된 버전)"""
        if price_position is None:
            return 0.0
        
        # 52주 위치가 높을수록 페널티 증가 (하지만 덜 보수적으로)
        if price_position >= 95:  # 52주 최고가의 95% 이상 (매우 높은 위치)
            return -15.0  # 강한 페널티 (기존 -20에서 완화)
        elif price_position >= 90:  # 52주 최고가의 90% 이상
            return -10.0  # 중간 페널티 (기존 -15에서 완화)
        elif price_position >= 85:  # 52주 최고가의 85% 이상
            return -5.0   # 약한 페널티 (기존 -10에서 완화)
        elif price_position >= 80:  # 52주 최고가의 80% 이상
            return -2.0   # 매우 약한 페널티 (새로 추가)
        elif price_position <= 20:  # 52주 최저가의 20% 이하
            return 5.0    # 보너스 (저가 매수 기회)
        elif price_position <= 30:  # 52주 최저가의 30% 이하
            return 2.0    # 약간의 보너스
        else:
            return 0.0    # 중간 위치는 페널티 없음

# =============================================================================
# 5. 메인 분석 클래스
# =============================================================================

class EnhancedIntegratedAnalyzer:
    """리팩토링된 향상된 통합 분석 클래스"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_manager = ConfigManager(config_file)
        self.rate_limiter = TPSRateLimiter()
        
        # 분석기 초기화
        self.opinion_analyzer = InvestmentOpinionAnalyzer()
        self.estimate_analyzer = EstimatePerformanceAnalyzer()
        self.provider = KISDataProvider()
        self.data_provider = FinancialDataProvider(self.provider, self.rate_limiter)
        
        # 설정 로드
        self.config = self._load_analysis_config()
        self.score_calculator = EnhancedScoreCalculator(self.config)
        
        # KOSPI 데이터 로드
        self.kospi_data = None
        self._load_kospi_data()
    
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
                'scale_analysis': 5
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
            logging.error(f"KOSPI 데이터 로드 실패: {e}")
            self.kospi_data = pd.DataFrame()
    
    def analyze_single_stock(self, symbol: str, name: str, days_back: int = 30) -> AnalysisResult:
        """단일 종목 분석을 수행합니다."""
        try:
            # 우선주 확인
            if self._is_preferred_stock(name):
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
            
            # 통합 점수 계산
            analysis_data = {
                'opinion_analysis': opinion_analysis,
                'estimate_analysis': estimate_analysis,
                'financial_data': financial_data,
                'market_cap': market_cap,
                'current_price': price_data.get('current_price', 0),
                'price_position': self._calculate_price_position(price_data)
            }
            
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
                price_data=price_data  # 가격 데이터 캐싱
            )
            
        except Exception as e:
            logging.error(f"분석 실패 {name} ({symbol}): {e}")
            return AnalysisResult(
                symbol=symbol,
                name=name,
                status=AnalysisStatus.ERROR,
                error=str(e)
            )
    
    def _is_preferred_stock(self, name: str) -> bool:
        """우선주 여부 확인"""
        return DataValidator.is_preferred_stock(name)
    
    def _analyze_opinion(self, symbol: str, days_back: int, name: str = "") -> Dict[str, Any]:
        """투자의견 분석 (컨텍스트 보강)"""
        try:
            return self.opinion_analyzer.analyze_single_stock(symbol, days_back=days_back)
        except Exception as e:
            logging.warning(f"투자의견 분석 실패 {symbol}({name}): {e}")
            return {}
    
    def _analyze_estimate(self, symbol: str, name: str = "") -> Dict[str, Any]:
        """추정실적 분석 (컨텍스트 보강)"""
        try:
            return self.estimate_analyzer.analyze_single_stock(symbol)
        except Exception as e:
            logging.warning(f"추정실적 분석 실패 {symbol}({name}): {e}")
            return {}
    
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
            logging.warning(f"이익률 추세 분석 실패: {e}")
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
            logging.warning(f"업종 특성 분석 실패 {symbol}: {e}")
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
            
            # 시가총액 기반 가산점 (대장주일 경우)
            if market_cap >= 1000000:  # 100조원 이상 (초대형)
                return 15.0
            elif market_cap >= 500000:  # 50조원 이상 (대형)
                return 12.0
            elif market_cap >= 100000:  # 10조원 이상 (중대형)
                return 10.0
            elif market_cap >= 50000:   # 5조원 이상 (중형)
                return 8.0
            else:  # 5조원 미만 (소형)
                return 5.0
                
        except Exception as e:
            logging.warning(f"대장주 가산점 계산 실패 {symbol}: {e}")
            return 0.0
    
    def _evaluate_valuation_by_sector(self, symbol: str, per: float, pbr: float, roe: float, market_cap: float = 0) -> Dict[str, Any]:
        """업종별 특성을 고려한 밸류에이션 평가"""
        try:
            sector_info = self._get_sector_characteristics(symbol)
            
            # 업종별 기준 범위
            per_min, per_max = sector_info['per_range']
            pbr_min, pbr_max = sector_info['pbr_range']
            roe_min, roe_max = sector_info['roe_range']
            
            # 점수 계산 (0-100점)
            per_score = self._calculate_metric_score(per, per_min, per_max, reverse=True)  # PER은 낮을수록 좋음
            pbr_score = self._calculate_metric_score(pbr, pbr_min, pbr_max, reverse=True)  # PBR은 낮을수록 좋음
            roe_score = self._calculate_metric_score(roe, roe_min, roe_max, reverse=False)  # ROE는 높을수록 좋음
            
            # 기본 종합 점수
            base_score = (per_score + pbr_score + roe_score) / 3
            
            # 업종별 대장주 가산점 계산 (간소화)
            actual_sector = sector_info.get('name', '기타')
            leader_bonus = self._calculate_leader_bonus(symbol, actual_sector, market_cap)
            
            # 최종 점수 (가산점 반영)
            total_score = min(100, base_score + leader_bonus)
            
            # 등급 결정
            if total_score >= 80:
                grade = "A+"
                description = "업종 대비 매우 우수"
            elif total_score >= 70:
                grade = "A"
                description = "업종 대비 우수"
            elif total_score >= 60:
                grade = "B+"
                description = "업종 대비 양호"
            elif total_score >= 50:
                grade = "B"
                description = "업종 대비 보통"
            elif total_score >= 40:
                grade = "C"
                description = "업종 대비 미흡"
            else:
                grade = "D"
                description = "업종 대비 부족"
            
            # 대장주 여부 확인
            is_leader = self._is_sector_leader(symbol, actual_sector)
            
            return {
                'total_score': total_score,
                'base_score': base_score,
                'leader_bonus': leader_bonus,
                'is_leader': is_leader,
                'grade': grade,
                'description': description,
                'per_score': per_score,
                'pbr_score': pbr_score,
                'roe_score': roe_score,
                'sector_info': sector_info
            }
            
        except Exception as e:
            logging.warning(f"업종별 밸류에이션 평가 실패 {symbol}: {e}")
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
    
    def _calculate_metric_score(self, value: float, min_val: float, max_val: float, reverse: bool = False) -> float:
        """지표별 점수 계산 (분모 0 방어)"""
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

# =============================================================================
# 6. CLI 인터페이스 (기존과 동일)
# =============================================================================

# Typer CLI 앱 생성
app = typer.Typer(help="리팩토링된 향상된 통합 분석 시스템")

@app.command()
def test_enhanced_analysis(
    count: int = typer.Option(15, help="분석할 종목 수"),
    min_score: float = typer.Option(50, help="최소 점수"),
    max_workers: int = typer.Option(int(os.getenv("MAX_WORKERS", "2")), help="병렬 워커 수"),
    export: Optional[str] = typer.Option(None, help="CSV 경로 저장(예: result.csv)")
):
    """향상된 분석 테스트"""
    analyzer = EnhancedIntegratedAnalyzer()
    
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
    
    # 결과 필터링 및 정렬
    filtered_results = [
        r for r in results 
        if r.status == AnalysisStatus.SUCCESS and r.enhanced_score >= min_score
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
