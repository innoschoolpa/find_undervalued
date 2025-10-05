"""
가치 지표 정밀화 모듈

가치 투자 분석을 위한 핵심 가치 지표들을 계산하고 정밀화하는 클래스를 제공합니다.
"""

import math
from typing import Any, Dict, List, Optional

from metrics import MetricsCollector


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
        """Earnings Quality 점수 계산 (회계적 이익의 질 평가)"""
        if not all(x is not None for x in [market_cap, net_income]) or market_cap <= 0:
            return 0.0
        
        if is_loss:
            return 0.0  # 적자는 품질 점수 0
        
        # Earnings Quality = (순이익 - 일회성 항목) / 시가총액
        quality_earnings = net_income - (one_time_items or 0)
        earnings_quality_yield = quality_earnings / market_cap
        
        # 점수화 (≥6% 가점)
        if earnings_quality_yield >= self.absolute_bands['earnings_quality_min']:
            return 100.0
        else:
            return max(0, 100 * earnings_quality_yield / self.absolute_bands['earnings_quality_min'])
    
    def calculate_shareholder_yield_score(self, market_cap: float, dividend_yield: float,
                                        shares_outstanding: float, shares_repurchased: float) -> float:
        """Shareholder Yield 점수 계산 (배당 + 자기주식매입)"""
        if not market_cap or market_cap <= 0:
            return 0.0
        
        # 배당 수익률
        dividend_component = dividend_yield or 0
        
        # 자기주식매입 수익률 (연간 매입액 / 시가총액)
        buyback_yield = 0
        if shares_repurchased and shares_outstanding:
            # 연간 매입액 추정 (매입 주식 수 × 평균 주가)
            estimated_buyback_amount = shares_repurchased * (market_cap / shares_outstanding)
            buyback_yield = estimated_buyback_amount / market_cap
        
        # Total Shareholder Yield
        total_yield = dividend_component + buyback_yield
        
        # 점수화 (≥3% 가점)
        if total_yield >= self.absolute_bands['shareholder_yield_min']:
            return 100.0
        else:
            return max(0, 100 * total_yield / self.absolute_bands['shareholder_yield_min'])
    
    def calculate_comprehensive_value_score(self, financial_data: Dict[str, Any], 
                                          market_cap: float, sector_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """종합 가치 점수 계산 (5개 지표 가중 평균)"""
        result = {
            'total_score': 0.0,
            'component_scores': {},
            'weights': self.value_weights.copy(),
            'absolute_bands': self.absolute_bands.copy()
        }
        
        # 1. EV/EBIT 점수
        ev_ebit_score = self.calculate_ev_ebit_score(
            market_cap=market_cap,
            net_debt=financial_data.get('net_debt'),
            operating_income=financial_data.get('operating_income'),
            sector_median=sector_data.get('ev_ebit_median') if sector_data else None
        )
        result['component_scores']['ev_ebit'] = ev_ebit_score
        
        # 2. FCF Yield 점수
        fcf_yield_score = self.calculate_normalized_fcf_yield(
            market_cap=market_cap,
            fcf_history=financial_data.get('fcf_history', [])
        )
        result['component_scores']['fcf_yield'] = fcf_yield_score
        
        # 3. Owner Earnings Yield 점수
        owner_earnings_score = self.calculate_owner_earnings_yield(
            market_cap=market_cap,
            net_income=financial_data.get('net_income'),
            depreciation=financial_data.get('depreciation'),
            maintenance_capex=financial_data.get('maintenance_capex')
        )
        result['component_scores']['owner_earnings'] = owner_earnings_score
        
        # 4. Earnings Quality 점수
        earnings_quality_score = self.calculate_earnings_quality_score(
            market_cap=market_cap,
            net_income=financial_data.get('net_income'),
            net_debt=financial_data.get('net_debt'),
            is_loss=financial_data.get('net_income', 0) < 0,
            one_time_items=financial_data.get('one_time_items'),
            tax_rate=financial_data.get('tax_rate', 0.25)
        )
        result['component_scores']['earnings_quality'] = earnings_quality_score
        
        # 5. Shareholder Yield 점수
        shareholder_yield_score = self.calculate_shareholder_yield_score(
            market_cap=market_cap,
            dividend_yield=financial_data.get('dividend_yield'),
            shares_outstanding=financial_data.get('shares_outstanding'),
            shares_repurchased=financial_data.get('shares_repurchased')
        )
        result['component_scores']['shareholder_yield'] = shareholder_yield_score
        
        # 가중 평균 계산
        weighted_sum = 0.0
        total_weight = 0.0
        
        for component, score in result['component_scores'].items():
            weight = self.value_weights[component]
            weighted_sum += score * weight
            total_weight += weight
        
        result['total_score'] = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        return result





