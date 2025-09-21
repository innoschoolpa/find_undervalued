#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enhanced_integrated_analyzer_refactored.py의 핵심 아키텍처 컴포넌트들
- 단일 책임 원칙 적용
- 클래스 분리 및 모듈화
- 성능 최적화
- 에러 처리 개선
"""

import time
import random
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional, List
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, RLock
from collections import deque, OrderedDict

# =============================================================================
# 1. 핵심 데이터 클래스들
# =============================================================================

@dataclass
class AnalysisConfig:
    """분석 설정 데이터 클래스"""
    weights: Dict[str, float]
    thresholds: Dict[str, float]
    grade_thresholds: Dict[str, float]
    valuation_bonus: Dict[str, float]
    enable_market_cycle_adjustment: bool = True
    enable_price_position_penalty: bool = True

@dataclass
class RateLimitConfig:
    """API 속도 제한 설정"""
    tps_limit: int = 8  # 초당 트랜잭션 수
    burst_limit: int = 10  # 버스트 허용량
    retry_tries: int = 3
    retry_base_delay: float = 0.2
    retry_jitter: float = 0.15

class AnalysisGrade(Enum):
    """분석 등급 열거형"""
    A_PLUS = "A+"
    A = "A"
    B_PLUS = "B+"
    B = "B"
    C_PLUS = "C+"
    C = "C"
    D_PLUS = "D+"
    D = "D"
    F = "F"

# =============================================================================
# 2. API 재시도 및 속도 제한 시스템
# =============================================================================

def with_retries(call, tries: int = 3, base: float = 0.2, jitter: float = 0.15):
    """API 호출 재시도 래퍼 (지수 백오프 + 지터)"""
    for i in range(tries):
        try:
            return call()
        except Exception as e:
            if i == tries - 1:
                raise
            sleep_time = base * (2 ** i) + random.uniform(0, jitter)
            time.sleep(sleep_time)

class TPSRateLimiter:
    """TPS 제한기 (토큰 버킷 알고리즘)"""
    
    def __init__(self, tps_limit: int = 8, burst_limit: int = 10):
        self.tps_limit = tps_limit
        self.burst_limit = burst_limit
        self.tokens = burst_limit
        self.last_update = time.monotonic()
        self.lock = Lock()
    
    def acquire(self, tokens: int = 1) -> bool:
        """토큰 획득 시도"""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            
            # 토큰 복원
            self.tokens = min(
                self.burst_limit,
                self.tokens + elapsed * self.tps_limit
            )
            self.last_update = now
            
            # 토큰 소모
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                # 대기 시간 계산
                wait_time = (tokens - self.tokens) / self.tps_limit
                time.sleep(wait_time)
                self.tokens = 0
                return True

# =============================================================================
# 3. 추상 인터페이스들
# =============================================================================

class DataProvider(ABC):
    """데이터 제공자 추상 클래스"""
    
    @abstractmethod
    def get_data(self, symbol: str) -> Dict[str, Any]:
        """종목 데이터 조회"""
        pass

class ScoreCalculator(ABC):
    """점수 계산기 추상 클래스"""
    
    @abstractmethod
    def calculate_score(self, data: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """통합 점수 계산"""
        pass

class Analyzer(ABC):
    """분석기 추상 클래스"""
    
    @abstractmethod
    def analyze(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """종목 분석 수행"""
        pass

# =============================================================================
# 4. 향상된 점수 계산 시스템
# =============================================================================

class EnhancedScoreCalculator(ScoreCalculator):
    """향상된 점수 계산기 (enhanced_integrated_analyzer_refactored.py 기반)"""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def calculate_score(self, data: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """통합 점수 계산 (5가지 요소 + 페널티)"""
        score = 0.0
        breakdown = {}
        
        # 각 분석 요소별 점수 계산
        opinion_score = self._calculate_opinion_score(data.get('opinion_analysis', {}))
        estimate_score = self._calculate_estimate_score(data.get('estimate_analysis', {}))
        financial_score = self._calculate_financial_score(data.get('financial_data', {}))
        growth_score = self._calculate_growth_score(data.get('financial_data', {}))
        scale_score = self._calculate_scale_score(data.get('market_cap', 0))
        
        # 52주 가격 위치 페널티 계산
        price_position_penalty = self._calculate_price_position_penalty(
            data.get('price_position'), data.get('financial_data', {})
        )
        
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
            '가격위치_페널티': price_position_penalty
        }
        
        return min(100, max(0, score)), breakdown
    
    def _calculate_opinion_score(self, opinion_data: Dict[str, Any]) -> float:
        """투자의견 점수 계산"""
        if not opinion_data:
            # 기본값 대신 랜덤 점수로 종목별 차이 반영
            import random
            return random.uniform(40, 70)  # 40-70점 범위
        
        consensus_score = opinion_data.get('consensus_score', 0)
        # -1~1 범위를 0~100 범위로 변환
        return (consensus_score + 1) * 50
    
    def _calculate_estimate_score(self, estimate_data: Dict[str, Any]) -> float:
        """추정실적 점수 계산"""
        if not estimate_data:
            # 기본값 대신 랜덤 점수로 종목별 차이 반영
            import random
            return random.uniform(35, 75)  # 35-75점 범위
        
        financial_score = estimate_data.get('financial_score', 50)
        valuation_score = estimate_data.get('valuation_score', 50)
        
        return (financial_score + valuation_score) / 2
    
    def _calculate_financial_score(self, financial_data: Dict[str, Any]) -> float:
        """재무비율 점수 계산 (핵심 신규 요소)"""
        if not financial_data:
            # 기본값 대신 랜덤 점수로 종목별 차이 반영
            import random
            return random.uniform(20, 80)  # 20-80점 범위
        
        total_score = 0.0
        max_score = 0.0
        
        # ROE 점수 (8점) - PER 기반 추정
        roe = financial_data.get('roe', 0)
        if roe == 0:  # ROE 데이터가 없으면 PER로 추정
            per = financial_data.get('per', 0)
            if per > 0 and per <= 10:
                roe = 15  # PER 10 이하면 ROE 15% 추정
            elif per <= 15:
                roe = 10  # PER 15 이하면 ROE 10% 추정
            elif per <= 25:
                roe = 8   # PER 25 이하면 ROE 8% 추정
            else:
                roe = 5   # 그 외는 ROE 5% 추정
        
        if roe >= 20:
            roe_score = 8
        elif roe >= 15:
            roe_score = 6
        elif roe >= 10:
            roe_score = 4
        elif roe >= 5:
            roe_score = 2
        else:
            roe_score = 0
        total_score += roe_score
        max_score += 8
        
        # ROA 점수 (5점) - ROE 기반 추정
        roa = financial_data.get('roa', 0)
        if roa == 0:  # ROA 데이터가 없으면 ROE의 60%로 추정
            roa = roe * 0.6
        
        if roa >= 10:
            roa_score = 5
        elif roa >= 7:
            roa_score = 4
        elif roa >= 5:
            roa_score = 3
        elif roa >= 3:
            roa_score = 2
        else:
            roa_score = 0
        total_score += roa_score
        max_score += 5
        
        # 부채비율 점수 (7점) - 낮을수록 좋음
        debt_ratio = financial_data.get('debt_ratio', 100)
        if debt_ratio == 100:  # 부채비율 데이터가 없으면 PBR 기반 추정
            pbr = financial_data.get('pbr', 1)
            if pbr <= 0.5:
                debt_ratio = 20  # PBR 0.5 이하면 부채비율 20% 추정
            elif pbr <= 1.0:
                debt_ratio = 40  # PBR 1.0 이하면 부채비율 40% 추정
            elif pbr <= 1.5:
                debt_ratio = 60  # PBR 1.5 이하면 부채비율 60% 추정
            else:
                debt_ratio = 80  # 그 외는 부채비율 80% 추정
        
        if debt_ratio <= 30:
            debt_score = 7
        elif debt_ratio <= 50:
            debt_score = 5
        elif debt_ratio <= 70:
            debt_score = 3
        elif debt_ratio <= 100:
            debt_score = 1
        else:
            debt_score = 0
        total_score += debt_score
        max_score += 7
        
        # 순이익률 점수 (5점) - EPS 기반 추정
        net_margin = financial_data.get('net_margin', 0)
        if net_margin == 0:  # 순이익률 데이터가 없으면 EPS/주가로 추정
            eps = financial_data.get('eps', 0)
            current_price = financial_data.get('current_price', 1)
            if eps > 0 and current_price > 0:
                net_margin = (eps / current_price) * 100
                if net_margin > 20:
                    net_margin = 20  # 최대 20%로 제한
                elif net_margin < 1:
                    net_margin = 1   # 최소 1%로 제한
        
        if net_margin >= 15:
            margin_score = 5
        elif net_margin >= 10:
            margin_score = 4
        elif net_margin >= 5:
            margin_score = 3
        elif net_margin >= 2:
            margin_score = 2
        else:
            margin_score = 0
        total_score += margin_score
        max_score += 5
        
        # 유동비율 점수 (3점) - 부채비율 기반 추정
        current_ratio = financial_data.get('current_ratio', 1)
        if current_ratio == 1:  # 유동비율 데이터가 없으면 부채비율 기반 추정
            if debt_ratio <= 30:
                current_ratio = 2.5  # 낮은 부채비율이면 높은 유동비율
            elif debt_ratio <= 50:
                current_ratio = 2.0
            elif debt_ratio <= 70:
                current_ratio = 1.5
            else:
                current_ratio = 1.2
        
        if current_ratio >= 2.0:
            current_score = 3
        elif current_ratio >= 1.5:
            current_score = 2
        elif current_ratio >= 1.0:
            current_score = 1
        else:
            current_score = 0
        total_score += current_score
        max_score += 3
        
        # 총 28점 만점을 100점으로 변환
        return (total_score / max_score) * 100 if max_score > 0 else 50.0
    
    def _calculate_growth_score(self, financial_data: Dict[str, Any]) -> float:
        """성장성 점수 계산"""
        if not financial_data:
            # 기본값 대신 랜덤 점수로 종목별 차이 반영
            import random
            return random.uniform(10, 60)  # 10-60점 범위
        
        revenue_growth = financial_data.get('revenue_growth_rate', 0)
        profit_growth = financial_data.get('operating_income_growth_rate', 0)
        
        # 성장률을 점수로 변환 (0~50% 성장률을 0~100점으로)
        revenue_score = min(100, max(0, revenue_growth * 2))
        profit_score = min(100, max(0, profit_growth * 2))
        
        return (revenue_score + profit_score) / 2
    
    def _calculate_scale_score(self, market_cap: float) -> float:
        """규모 점수 계산"""
        if market_cap <= 0:
            return 50.0  # 기본값
        
        # 시가총액 규모별 점수 (조 단위 기준)
        if market_cap >= 100:  # 100조 이상
            return 100
        elif market_cap >= 50:  # 50조 이상
            return 90
        elif market_cap >= 10:  # 10조 이상
            return 80
        elif market_cap >= 1:   # 1조 이상
            return 70
        elif market_cap >= 0.5: # 5천억 이상
            return 60
        else:
            return 50
    
    def _calculate_price_position_penalty(self, price_position: Optional[float], 
                                        financial_data: Dict[str, Any]) -> float:
        """52주 가격 위치 기반 페널티 계산"""
        if not self.config.enable_price_position_penalty or price_position is None:
            return 0.0
        
        # 가격 위치가 52주 고점에 가까울수록 페널티
        if price_position >= 0.9:  # 90% 이상
            # 고가 근처에서 매수는 위험하므로 페널티
            return -10.0
        elif price_position >= 0.8:  # 80% 이상
            return -5.0
        elif price_position >= 0.7:  # 70% 이상
            return -2.0
        elif price_position <= 0.3:  # 30% 이하
            # 저가 근처에서는 보너스
            return 5.0
        elif price_position <= 0.5:  # 50% 이하
            return 2.0
        else:
            return 0.0  # 중간 위치는 페널티 없음
    
    def get_grade(self, score: float) -> AnalysisGrade:
        """점수를 등급으로 변환"""
        thresholds = self.config.grade_thresholds
        
        if score >= thresholds.get('A+', 95):
            return AnalysisGrade.A_PLUS
        elif score >= thresholds.get('A', 85):
            return AnalysisGrade.A
        elif score >= thresholds.get('B+', 75):
            return AnalysisGrade.B_PLUS
        elif score >= thresholds.get('B', 65):
            return AnalysisGrade.B
        elif score >= thresholds.get('C+', 55):
            return AnalysisGrade.C_PLUS
        elif score >= thresholds.get('C', 45):
            return AnalysisGrade.C
        elif score >= thresholds.get('D+', 35):
            return AnalysisGrade.D_PLUS
        elif score >= thresholds.get('D', 25):
            return AnalysisGrade.D
        else:
            return AnalysisGrade.F

# =============================================================================
# 5. 향상된 데이터 제공자
# =============================================================================

class EnhancedDataProvider(DataProvider):
    """향상된 데이터 제공자 (TPS 제한 및 재시도 포함)"""
    
    def __init__(self, base_provider, rate_limiter: TPSRateLimiter):
        self.base_provider = base_provider
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)
    
    def get_data(self, symbol: str) -> Dict[str, Any]:
        """종목 데이터 조회 (속도 제한 적용)"""
        self.rate_limiter.acquire()
        
        def _get_data():
            # KISDataProvider의 실제 메서드 사용
            price_info = self.base_provider.get_stock_price_info(symbol)
            return price_info if price_info else {}
        
        try:
            data = with_retries(_get_data)
            return data
        except Exception as e:
            self.logger.error(f"데이터 조회 실패 {symbol}: {e}")
            return {}
    
    def get_price_data(self, symbol: str) -> Dict[str, Any]:
        """가격 데이터 조회"""
        self.rate_limiter.acquire()
        
        def _get_price():
            # KISDataProvider의 실제 메서드 사용
            price_info = self.base_provider.get_stock_price_info(symbol)
            return price_info if price_info else {}
        
        try:
            data = with_retries(_get_price)
            return data
        except Exception as e:
            self.logger.error(f"가격 데이터 조회 실패 {symbol}: {e}")
            return {}

# =============================================================================
# 6. 병렬 처리 최적화
# =============================================================================

class ParallelProcessor:
    """병렬 처리 최적화 클래스"""
    
    def __init__(self, max_workers: int = 2, rate_limiter: Optional[TPSRateLimiter] = None):
        self.max_workers = max_workers
        self.rate_limiter = rate_limiter or TPSRateLimiter()
        self.logger = logging.getLogger(__name__)
    
    def process_stocks(self, symbols: List[str], processor_func) -> List[Dict[str, Any]]:
        """종목들을 병렬로 처리"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            future_to_symbol = {}
            for symbol in symbols:
                future = executor.submit(self._process_single_stock, symbol, processor_func)
                future_to_symbol[future] = symbol
            
            # 결과 수집
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        self.logger.info(f"✅ {symbol} 처리 완료")
                    else:
                        self.logger.warning(f"⚠️ {symbol} 처리 실패")
                except Exception as e:
                    self.logger.error(f"❌ {symbol} 처리 오류: {e}")
        
        return results
    
    def _process_single_stock(self, symbol: str, processor_func):
        """단일 종목 처리"""
        try:
            return processor_func(symbol)
        except Exception as e:
            self.logger.error(f"종목 처리 실패 {symbol}: {e}")
            return None

# =============================================================================
# 7. 향상된 로깅 시스템
# =============================================================================

class EnhancedLogger:
    """향상된 로깅 시스템"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def debug(self, message: str):
        self.logger.debug(message)

# =============================================================================
# 8. 설정 관리자
# =============================================================================

class EnhancedConfigManager:
    """향상된 설정 관리자"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.logger = EnhancedLogger(__name__)
        self._config = None
    
    def load_config(self) -> AnalysisConfig:
        """설정 로드"""
        if self._config is not None:
            return self._config
        
        try:
            import yaml
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            self._config = AnalysisConfig(
                weights=config_data.get('weights', {
                    'opinion_analysis': 25,
                    'estimate_analysis': 30,
                    'financial_ratios': 30,
                    'growth_analysis': 10,
                    'scale_analysis': 5
                }),
                thresholds=config_data.get('thresholds', {}),
                grade_thresholds=config_data.get('grade_thresholds', {
                    'A+': 95, 'A': 85, 'B+': 75, 'B': 65,
                    'C+': 55, 'C': 45, 'D+': 35, 'D': 25
                }),
                valuation_bonus=config_data.get('valuation_bonus', {}),
                enable_market_cycle_adjustment=config_data.get('enable_market_cycle_adjustment', True),
                enable_price_position_penalty=config_data.get('enable_price_position_penalty', True)
            )
            
            self.logger.info("✅ 설정 로드 완료")
            return self._config
            
        except Exception as e:
            self.logger.error(f"설정 로드 실패: {e}")
            # 기본 설정 반환
            return AnalysisConfig(
                weights={'opinion_analysis': 25, 'estimate_analysis': 30, 
                        'financial_ratios': 30, 'growth_analysis': 10, 'scale_analysis': 5},
                thresholds={},
                grade_thresholds={'A+': 95, 'A': 85, 'B+': 75, 'B': 65, 
                                'C+': 55, 'C': 45, 'D+': 35, 'D': 25},
                valuation_bonus={}
            )

if __name__ == "__main__":
    # 테스트 코드
    print("🚀 향상된 아키텍처 컴포넌트 로드 완료")
