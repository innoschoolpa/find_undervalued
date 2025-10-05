"""
안전마진 및 내재가치 계산 모듈

가치 투자 분석을 위한 안전마진과 내재가치를 계산하는 클래스를 제공합니다.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from metrics import MetricsCollector


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
        
        # 내재가치 = EPS × 적정 PER
        intrinsic_value = avg_eps * adjusted_pe
        
        return intrinsic_value
    
    def calculate_scenario_based_valuation(self, financial_data: Dict[str, Any], 
                                         market_cap: float) -> Dict[str, Any]:
        """시나리오 기반 내재가치 계산 (보수/기준/낙관)"""
        result = {
            'scenarios': {},
            'weighted_intrinsic_value': 0.0,
            'confidence_level': 'low'
        }
        
        # 보수적 시나리오 (낮은 성장률, 높은 할인율)
        conservative_iv = self._calculate_scenario_valuation(
            financial_data, market_cap, growth_rate=0.02, discount_rate=0.12, pe_ratio=12.0
        )
        result['scenarios']['conservative'] = {
            'intrinsic_value': conservative_iv,
            'probability': self.scenario_probabilities['conservative']
        }
        
        # 기준 시나리오 (중간 성장률, 중간 할인율)
        base_iv = self._calculate_scenario_valuation(
            financial_data, market_cap, growth_rate=0.05, discount_rate=0.10, pe_ratio=15.0
        )
        result['scenarios']['base'] = {
            'intrinsic_value': base_iv,
            'probability': self.scenario_probabilities['base']
        }
        
        # 낙관적 시나리오 (높은 성장률, 낮은 할인율)
        optimistic_iv = self._calculate_scenario_valuation(
            financial_data, market_cap, growth_rate=0.08, discount_rate=0.08, pe_ratio=18.0
        )
        result['scenarios']['optimistic'] = {
            'intrinsic_value': optimistic_iv,
            'probability': self.scenario_probabilities['optimistic']
        }
        
        # 가중 평균 내재가치 계산
        weighted_sum = 0.0
        for scenario_data in result['scenarios'].values():
            weighted_sum += scenario_data['intrinsic_value'] * scenario_data['probability']
        
        result['weighted_intrinsic_value'] = weighted_sum
        result['confidence_level'] = self._calculate_confidence_level(result['scenarios'])
        
        return result
    
    def _calculate_scenario_valuation(self, financial_data: Dict[str, Any], market_cap: float,
                                    growth_rate: float, discount_rate: float, pe_ratio: float) -> float:
        """개별 시나리오 내재가치 계산"""
        fcf_history = financial_data.get('fcf_history', [])
        eps_history = financial_data.get('eps_history', [])
        
        # FCF 기반 계산
        fcf_iv = self.calculate_fcf_multiple_valuation(market_cap, fcf_history, growth_rate, discount_rate)
        
        # EPS 기반 계산
        eps_iv = self.calculate_eps_multiple_valuation(market_cap, eps_history, pe_ratio, growth_rate)
        
        # 두 방법의 평균 (더 안정적)
        if fcf_iv > 0 and eps_iv > 0:
            return (fcf_iv + eps_iv) / 2
        elif fcf_iv > 0:
            return fcf_iv
        elif eps_iv > 0:
            return eps_iv
        else:
            return 0.0
    
    def calculate_margin_of_safety(self, current_price: float, intrinsic_value: float) -> Dict[str, Any]:
        """안전마진 계산"""
        if not current_price or not intrinsic_value or intrinsic_value <= 0:
            return {
                'margin_of_safety': None,
                'signal': 'PASS',
                'reason': 'insufficient_data'
            }
        
        # MoS = (내재가치 - 현재가) / 내재가치
        mos = (intrinsic_value - current_price) / intrinsic_value
        
        # 투자 신호 결정
        if mos >= self.mos_thresholds['buy']:
            signal = 'BUY'
        elif mos >= self.mos_thresholds['watch']:
            signal = 'WATCH'
        else:
            signal = 'PASS'
        
        return {
            'margin_of_safety': mos,
            'signal': signal,
            'current_price': current_price,
            'intrinsic_value': intrinsic_value,
            'target_buy_price': intrinsic_value * 0.7  # 30% MoS 목표가
        }
    
    def calculate_comprehensive_valuation(self, symbol: str, current_price: float,
                                        financial_data: Dict[str, Any], 
                                        market_cap: float) -> Dict[str, Any]:
        """종합 내재가치 및 안전마진 계산"""
        result = {
            'symbol': symbol,
            'current_price': current_price,
            'market_cap': market_cap,
            'intrinsic_value': None,
            'margin_of_safety': None,
            'investment_signal': 'PASS',
            'target_buy_price': None,
            'confidence_level': 'low',
            'risk_factors': []
        }
        
        # 시나리오 기반 내재가치 계산
        scenario_result = self.calculate_scenario_based_valuation(financial_data, market_cap)
        intrinsic_value = scenario_result['weighted_intrinsic_value']
        
        result['intrinsic_value'] = intrinsic_value
        result['confidence_level'] = scenario_result['confidence_level']
        
        # 안전마진 계산
        if intrinsic_value and intrinsic_value > 0:
            mos_result = self.calculate_margin_of_safety(current_price, intrinsic_value)
            result.update(mos_result)
            
            # 리스크 요인 식별
            result['risk_factors'] = self._identify_risk_factors(financial_data, scenario_result)
        
        return result
    
    def _calculate_confidence_level(self, scenario_result: Dict[str, Any]) -> str:
        """신뢰도 수준 계산"""
        values = [scenario['intrinsic_value'] for scenario in scenario_result.values()]
        
        if not values or all(v == 0 for v in values):
            return 'low'
        
        # 값의 분산으로 신뢰도 판단
        mean_val = sum(values) / len(values)
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        cv = (variance ** 0.5) / mean_val if mean_val > 0 else 1.0
        
        if cv < 0.2:
            return 'high'
        elif cv < 0.5:
            return 'medium'
        else:
            return 'low'
    
    def _identify_risk_factors(self, financial_data: Dict[str, Any], 
                             scenario_result: Dict[str, Any]) -> List[str]:
        """리스크 요인 식별"""
        risk_factors = []
        
        # 재무 건전성 리스크
        debt_ratio = financial_data.get('debt_ratio', 0)
        if debt_ratio and debt_ratio > 50:  # 50% 이상
            risk_factors.append('high_debt_ratio')
        
        # 수익성 리스크
        roe = financial_data.get('roe', 0)
        if roe and roe < 5:  # 5% 미만
            risk_factors.append('low_roe')
        
        # 성장성 리스크
        revenue_growth = financial_data.get('revenue_growth_rate', 0)
        if revenue_growth and revenue_growth < 0:  # 음의 성장
            risk_factors.append('negative_growth')
        
        # 시나리오 분산 리스크
        values = [scenario['intrinsic_value'] for scenario in scenario_result.values()]
        if values and max(values) / min(values) > 3:  # 3배 이상 차이
            risk_factors.append('high_valuation_uncertainty')
        
        return risk_factors













