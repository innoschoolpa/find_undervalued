"""
가격위치 정책화 모듈

52주 밴드 규칙과 안전마진을 연동한 가격위치 정책을 제공합니다.
"""

import logging
from typing import Any, Dict, Optional

from metrics import MetricsCollector


class PricePositionPolicyManager:
    """가격위치 정책화 클래스 (52주 밴드 규칙, MoS 연동)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 52주 밴드 정책 임계치
        self.price_position_thresholds = {
            'excellent_buy': 20.0,      # 20% 이하 → 우수 매수
            'good_buy': 40.0,           # 40% 이하 → 좋은 매수
            'watch_zone': 60.0,         # 60% 이하 → 관심 구간
            'caution_zone': 80.0,       # 80% 이하 → 주의 구간
            'avoid_zone': 100.0         # 80% 초과 → 회피 구간
        }
        # 안전마진 연동 정책
        self.mos_integration = {
            'high_mos_threshold': 0.30,  # 30% 이상 MoS
            'medium_mos_threshold': 0.15, # 15% 이상 MoS
            'low_mos_threshold': 0.05    # 5% 이상 MoS
        }
    
    def apply_price_position_policy(self, price_position: float, margin_of_safety: float, 
                                  value_score: float) -> Dict[str, Any]:
        """가격위치 정책 적용"""
        result = {
            'price_position': price_position,
            'margin_of_safety': margin_of_safety,
            'value_score': value_score,
            'policy_decision': 'PASS',
            'policy_reason': '',
            'risk_level': 'medium',
            'position_sizing': 0.0,
            'risk_reward_ratio': 'neutral'
        }
        
        try:
            # 1. 가격위치 기반 기본 정책
            if price_position <= self.price_position_thresholds['excellent_buy']:
                result['policy_decision'] = 'BUY'
                result['policy_reason'] = 'excellent_price_position'
                result['risk_level'] = 'low'
                result['position_sizing'] = 1.0
                result['risk_reward_ratio'] = 'excellent'
            elif price_position <= self.price_position_thresholds['good_buy']:
                result['policy_decision'] = 'BUY'
                result['policy_reason'] = 'good_price_position'
                result['risk_level'] = 'low'
                result['position_sizing'] = 0.8
                result['risk_reward_ratio'] = 'good'
            elif price_position <= self.price_position_thresholds['watch_zone']:
                result['policy_decision'] = 'WATCH'
                result['policy_reason'] = 'watch_zone'
                result['risk_level'] = 'medium'
                result['position_sizing'] = 0.5
                result['risk_reward_ratio'] = 'fair'
            elif price_position <= self.price_position_thresholds['caution_zone']:
                result['policy_decision'] = 'CAUTION'
                result['policy_reason'] = 'caution_zone'
                result['risk_level'] = 'high'
                result['position_sizing'] = 0.2
                result['risk_reward_ratio'] = 'poor'
            else:
                result['policy_decision'] = 'AVOID'
                result['policy_reason'] = 'avoid_zone'
                result['risk_level'] = 'very_high'
                result['position_sizing'] = 0.0
                result['risk_reward_ratio'] = 'very_poor'
            
            # 2. 안전마진 연동 조정
            if margin_of_safety >= self.mos_integration['high_mos_threshold']:
                # 높은 MoS → 더 적극적
                if result['policy_decision'] == 'WATCH':
                    result['policy_decision'] = 'BUY'
                    result['policy_reason'] += '_high_mos_boost'
                result['position_sizing'] = min(1.0, result['position_sizing'] * 1.2)
                result['risk_level'] = 'low'
            elif margin_of_safety >= self.mos_integration['medium_mos_threshold']:
                # 중간 MoS → 보통
                result['position_sizing'] = result['position_sizing']
            elif margin_of_safety >= self.mos_integration['low_mos_threshold']:
                # 낮은 MoS → 보수적
                result['position_sizing'] *= 0.8
                if result['risk_level'] == 'low':
                    result['risk_level'] = 'medium'
            else:
                # 매우 낮은 MoS → 매우 보수적
                result['position_sizing'] *= 0.5
                result['risk_level'] = 'high'
                if result['policy_decision'] == 'BUY':
                    result['policy_decision'] = 'WATCH'
                    result['policy_reason'] += '_low_mos_penalty'
            
            # 3. 가치 점수 연동 조정
            if value_score >= 80:
                # 높은 가치 점수 → 더 적극적
                if result['policy_decision'] in ['WATCH', 'CAUTION']:
                    result['policy_decision'] = 'BUY'
                    result['policy_reason'] += '_high_value_boost'
                result['position_sizing'] = min(1.0, result['position_sizing'] * 1.1)
            elif value_score >= 60:
                # 보통 가치 점수 → 그대로
                pass
            else:
                # 낮은 가치 점수 → 보수적
                result['position_sizing'] *= 0.9
                if result['policy_decision'] == 'BUY':
                    result['policy_decision'] = 'WATCH'
                    result['policy_reason'] += '_low_value_penalty'
            
            # 4. 최종 포지션 사이징 조정
            result['position_sizing'] = max(0.0, min(1.0, result['position_sizing']))
            
        except Exception as e:
            logging.warning(f"가격위치 정책 적용 실패: {e}")
            result['policy_error'] = str(e)
        
        return result
    
    def determine_investment_signal(self, price_position: float, margin_of_safety: float,
                                  value_score: float, quality_score: float = None) -> Dict[str, Any]:
        """투자 신호 결정 (종합적 판단)"""
        try:
            # 기본 정책 적용
            policy_result = self.apply_price_position_policy(price_position, margin_of_safety, value_score)
            
            # 품질 점수 고려 (있는 경우)
            if quality_score is not None:
                if quality_score >= 80:
                    # 높은 품질 → 더 적극적
                    if policy_result['policy_decision'] == 'WATCH':
                        policy_result['policy_decision'] = 'BUY'
                        policy_result['policy_reason'] += '_high_quality_boost'
                    policy_result['position_sizing'] = min(1.0, policy_result['position_sizing'] * 1.15)
                elif quality_score < 50:
                    # 낮은 품질 → 보수적
                    policy_result['position_sizing'] *= 0.8
                    if policy_result['policy_decision'] == 'BUY':
                        policy_result['policy_decision'] = 'WATCH'
                        policy_result['policy_reason'] += '_low_quality_penalty'
                
                policy_result['quality_score'] = quality_score
            
            # 최종 신호 결정
            final_signal = self._determine_final_signal(policy_result)
            policy_result['final_investment_signal'] = final_signal
            
            return policy_result
            
        except Exception as e:
            logging.error(f"투자 신호 결정 실패: {e}")
            return {
                'final_investment_signal': 'ERROR',
                'policy_error': str(e),
                'price_position': price_position,
                'margin_of_safety': margin_of_safety,
                'value_score': value_score
            }
    
    def calculate_price_position_risk_adjustment(self, price_position: float, 
                                               volatility: float = None) -> float:
        """가격위치 기반 리스크 조정 팩터"""
        try:
            # 기본 리스크 팩터
            if price_position <= 20:
                risk_factor = 0.8  # 20% 이하 → 낮은 리스크
            elif price_position <= 40:
                risk_factor = 0.9  # 40% 이하 → 약간 낮은 리스크
            elif price_position <= 60:
                risk_factor = 1.0  # 60% 이하 → 보통 리스크
            elif price_position <= 80:
                risk_factor = 1.1  # 80% 이하 → 약간 높은 리스크
            else:
                risk_factor = 1.3  # 80% 초과 → 높은 리스크
            
            # 변동성 고려 (있는 경우)
            if volatility is not None:
                if volatility > 0.3:  # 30% 이상 변동성
                    risk_factor *= 1.2
                elif volatility > 0.2:  # 20% 이상 변동성
                    risk_factor *= 1.1
                elif volatility < 0.1:  # 10% 미만 변동성
                    risk_factor *= 0.9
            
            return risk_factor
            
        except Exception as e:
            logging.warning(f"가격위치 리스크 조정 계산 실패: {e}")
            return 1.0
    
    def apply_comprehensive_price_policy(self, symbol: str, price_position: float,
                                       margin_of_safety: float, value_score: float,
                                       quality_score: float = None, 
                                       volatility: float = None) -> Dict[str, Any]:
        """종합 가격 정책 적용"""
        try:
            # 기본 투자 신호 결정
            signal_result = self.determine_investment_signal(
                price_position, margin_of_safety, value_score, quality_score
            )
            
            # 리스크 조정 팩터 계산
            risk_adjustment = self.calculate_price_position_risk_adjustment(price_position, volatility)
            
            # 최종 결과 조합
            result = {
                **signal_result,
                'symbol': symbol,
                'risk_adjustment_factor': risk_adjustment,
                'adjusted_position_sizing': signal_result.get('position_sizing', 0) / risk_adjustment,
                'volatility': volatility,
                'comprehensive_score': self._calculate_comprehensive_score(
                    price_position, margin_of_safety, value_score, quality_score
                )
            }
            
            return result
            
        except Exception as e:
            logging.error(f"종합 가격 정책 적용 실패 {symbol}: {e}")
            return {
                'symbol': symbol,
                'final_investment_signal': 'ERROR',
                'policy_error': str(e)
            }
    
    def _determine_final_signal(self, policy_result: Dict[str, Any]) -> str:
        """최종 투자 신호 결정"""
        decision = policy_result.get('policy_decision', 'PASS')
        position_sizing = policy_result.get('position_sizing', 0)
        
        # 포지션 사이징이 너무 작으면 PASS로 조정
        if position_sizing < 0.1:
            return 'PASS'
        
        return decision
    
    def _calculate_comprehensive_score(self, price_position: float, margin_of_safety: float,
                                     value_score: float, quality_score: float = None) -> float:
        """종합 점수 계산"""
        try:
            # 가격위치 점수 (낮을수록 좋음)
            position_score = max(0, 100 - price_position)
            
            # 안전마진 점수
            mos_score = min(100, margin_of_safety * 200)  # 50% MoS = 100점
            
            # 가치 점수
            value_component = value_score or 50
            
            # 품질 점수 (있는 경우)
            quality_component = quality_score if quality_score is not None else 50
            
            # 가중 평균 (가격 40%, MoS 30%, 가치 20%, 품질 10%)
            comprehensive_score = (
                position_score * 0.4 +
                mos_score * 0.3 +
                value_component * 0.2 +
                quality_component * 0.1
            )
            
            return comprehensive_score
            
        except Exception as e:
            logging.warning(f"종합 점수 계산 실패: {e}")
            return 50.0  # 기본값













