"""
섹터/사이클 맥락화 모듈

섹터 특성과 시장 사이클을 고려한 맥락화 분석을 제공합니다.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from metrics import MetricsCollector


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
                return adjusted_score, f"sector_penalty_40_below_adjusted_{adjusted_score:.1f}"
            else:
                # 40-50점이면 경미한 패널티
                adjusted_score = company_score * self.sector_relative_thresholds['conservative_multiplier']
                return adjusted_score, f"sector_conservative_adjusted_{adjusted_score:.1f}"
        else:
            # 섹터 점수가 양호한 경우 그대로 유지
            return company_score, "sector_positive_no_adjustment"
    
    def apply_sector_contextualization(self, symbol: str, sector_name: str, 
                                     company_value_score: float, sector_data: Dict[str, Any]) -> Dict[str, Any]:
        """섹터 맥락화 적용"""
        start_time = time.monotonic()
        
        result = {
            'symbol': symbol,
            'sector_name': sector_name,
            'original_score': company_value_score,
            'adjusted_score': company_value_score,
            'contextualization_applied': False,
            'adjustment_reason': 'none',
            'sector_sample_adequate': True,
            'sector_sample_penalty': 1.0
        }
        
        try:
            # 1. 섹터 표본 적정성 분석
            sample_size = sector_data.get('sample_size', 0)
            is_adequate, adequacy_reason, sample_penalty = self.analyze_sector_sample_adequacy(sector_name, sample_size)
            
            result['sector_sample_adequate'] = is_adequate
            result['sector_sample_penalty'] = sample_penalty
            result['sample_adequacy_reason'] = adequacy_reason
            
            # 2. 섹터 상대지표 보수화
            sector_score = sector_data.get('average_score', None)
            adjusted_score, adjustment_reason = self.calculate_sector_relative_adjustment(
                company_value_score, sector_score
            )
            
            # 3. 최종 점수 계산 (표본 패널티와 상대지표 보정 모두 적용)
            final_score = adjusted_score * sample_penalty
            
            result['adjusted_score'] = final_score
            result['contextualization_applied'] = True
            result['adjustment_reason'] = adjustment_reason
            result['sector_score'] = sector_score
            result['total_adjustment_factor'] = sample_penalty * (adjusted_score / company_value_score if company_value_score > 0 else 1.0)
            
            # 메트릭 기록
            if self.metrics:
                duration = time.monotonic() - start_time
                self.metrics.record_sector_evaluation(duration)
            
        except Exception as e:
            logging.warning(f"섹터 맥락화 실패 {symbol}: {e}")
            result['contextualization_error'] = str(e)
        
        return result
    
    def analyze_market_cycle_context(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """시장 사이클 맥락 분석"""
        try:
            # 간단한 시장 사이클 분석 (실제로는 더 복잡한 로직 필요)
            kospi_index = market_data.get('kospi_index', 0)
            market_volatility = market_data.get('volatility', 0)
            market_pe_ratio = market_data.get('pe_ratio', 0)
            
            cycle_context = {
                'market_phase': 'neutral',
                'cycle_adjustment_factor': 1.0,
                'risk_level': 'medium',
                'recommendation': 'balanced'
            }
            
            # 시장 단계 판단 (간단한 로직)
            if market_pe_ratio > 20:
                cycle_context['market_phase'] = 'overvalued'
                cycle_context['cycle_adjustment_factor'] = 0.9
                cycle_context['risk_level'] = 'high'
                cycle_context['recommendation'] = 'conservative'
            elif market_pe_ratio < 12:
                cycle_context['market_phase'] = 'undervalued'
                cycle_context['cycle_adjustment_factor'] = 1.1
                cycle_context['risk_level'] = 'low'
                cycle_context['recommendation'] = 'aggressive'
            
            # 변동성 고려
            if market_volatility > 0.3:
                cycle_context['risk_level'] = 'high'
                cycle_context['cycle_adjustment_factor'] *= 0.95
            
            return cycle_context
            
        except Exception as e:
            logging.warning(f"시장 사이클 분석 실패: {e}")
            return {
                'market_phase': 'unknown',
                'cycle_adjustment_factor': 1.0,
                'risk_level': 'unknown',
                'recommendation': 'neutral'
            }
    
    def apply_comprehensive_contextualization(self, symbol: str, sector_name: str,
                                            company_value_score: float, sector_data: Dict[str, Any],
                                            market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """종합 맥락화 적용 (섹터 + 시장 사이클)"""
        try:
            # 1. 섹터 맥락화
            sector_result = self.apply_sector_contextualization(
                symbol, sector_name, company_value_score, sector_data
            )
            
            # 2. 시장 사이클 맥락화
            cycle_context = self.analyze_market_cycle_context(market_data or {})
            
            # 3. 종합 조정
            final_score = sector_result['adjusted_score'] * cycle_context['cycle_adjustment_factor']
            
            return {
                **sector_result,
                'final_contextualized_score': final_score,
                'market_cycle_context': cycle_context,
                'comprehensive_adjustment_factor': sector_result.get('total_adjustment_factor', 1.0) * cycle_context['cycle_adjustment_factor']
            }
            
        except Exception as e:
            logging.error(f"종합 맥락화 실패 {symbol}: {e}")
            return {
                'symbol': symbol,
                'original_score': company_value_score,
                'final_contextualized_score': company_value_score,
                'contextualization_error': str(e)
            }













