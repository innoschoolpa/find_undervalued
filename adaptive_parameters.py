#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
적응형 파라미터 시스템
시장 상황에 따라 파라미터를 동적으로 조정합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging

class AdaptiveParameterSystem:
    """적응형 파라미터 시스템"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 기본 파라미터 템플릿
        self.base_templates = {
            'conservative': {
                'weights': {
                    'opinion_analysis': 15.0,
                    'estimate_analysis': 25.0,
                    'financial_ratios': 40.0,
                    'growth_analysis': 15.0,
                    'scale_analysis': 5.0
                },
                'financial_ratio_weights': {
                    'roe_score': 8,
                    'roa_score': 6,
                    'debt_ratio_score': 12,
                    'net_profit_margin_score': 6,
                    'current_ratio_score': 6,
                    'growth_score': 2
                }
            },
            'balanced': {
                'weights': {
                    'opinion_analysis': 20.0,
                    'estimate_analysis': 30.0,
                    'financial_ratios': 30.0,
                    'growth_analysis': 15.0,
                    'scale_analysis': 5.0
                },
                'financial_ratio_weights': {
                    'roe_score': 6,
                    'roa_score': 5,
                    'debt_ratio_score': 10,
                    'net_profit_margin_score': 4,
                    'current_ratio_score': 4,
                    'growth_score': 1
                }
            },
            'aggressive': {
                'weights': {
                    'opinion_analysis': 25.0,
                    'estimate_analysis': 35.0,
                    'financial_ratios': 20.0,
                    'growth_analysis': 15.0,
                    'scale_analysis': 5.0
                },
                'financial_ratio_weights': {
                    'roe_score': 4,
                    'roa_score': 3,
                    'debt_ratio_score': 8,
                    'net_profit_margin_score': 3,
                    'current_ratio_score': 3,
                    'growth_score': 3
                }
            }
        }
    
    def get_adaptive_parameters(self, 
                               market_condition: str,
                               volatility_level: float,
                               time_horizon: str) -> Dict[str, Any]:
        """시장 상황에 따른 적응형 파라미터 생성"""
        
        # 시장 상황에 따른 기본 템플릿 선택
        if market_condition == 'bear' or volatility_level > 0.7:
            base_template = self.base_templates['conservative']
        elif market_condition == 'bull' and volatility_level < 0.3:
            base_template = self.base_templates['aggressive']
        else:
            base_template = self.base_templates['balanced']
        
        # 시간 지평에 따른 조정
        adjusted_params = self._adjust_for_time_horizon(base_template, time_horizon)
        
        # 변동성에 따른 미세 조정
        final_params = self._adjust_for_volatility(adjusted_params, volatility_level)
        
        return final_params
    
    def _adjust_for_time_horizon(self, 
                                params: Dict[str, Any], 
                                time_horizon: str) -> Dict[str, Any]:
        """시간 지평에 따른 파라미터 조정"""
        
        adjusted = params.copy()
        
        if time_horizon == 'short':  # 3개월 이하
            # 단기: 추정실적과 투자의견에 더 의존
            adjusted['weights']['opinion_analysis'] *= 1.2
            adjusted['weights']['estimate_analysis'] *= 1.1
            adjusted['weights']['financial_ratios'] *= 0.9
            
        elif time_horizon == 'long':  # 12개월 이상
            # 장기: 재무비율과 성장성에 더 의존
            adjusted['weights']['financial_ratios'] *= 1.1
            adjusted['weights']['growth_analysis'] *= 1.2
            adjusted['weights']['opinion_analysis'] *= 0.9
        
        return adjusted
    
    def _adjust_for_volatility(self, 
                              params: Dict[str, Any], 
                              volatility_level: float) -> Dict[str, Any]:
        """변동성에 따른 파라미터 조정"""
        
        adjusted = params.copy()
        
        if volatility_level > 0.7:  # 고변동성
            # 안정성 중시: 재무비율 가중치 증가
            adjusted['financial_ratio_weights']['debt_ratio_score'] *= 1.2
            adjusted['financial_ratio_weights']['current_ratio_score'] *= 1.1
            
        elif volatility_level < 0.3:  # 저변동성
            # 성장성 중시: 성장 관련 가중치 증가
            adjusted['weights']['growth_analysis'] *= 1.1
            adjusted['financial_ratio_weights']['growth_score'] *= 1.2
        
        return adjusted
    
    def get_parameter_confidence(self, 
                                params: Dict[str, Any],
                                test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """파라미터 신뢰도 평가"""
        
        confidence = {
            'overall_confidence': 0.0,
            'stability_score': 0.0,
            'performance_score': 0.0,
            'risk_score': 0.0,
            'recommendations': []
        }
        
        if not test_results:
            return confidence
        
        # 안정성 점수 계산
        performances = [r.get('performance', 0) for r in test_results]
        stability_scores = [r.get('stability', 0) for r in test_results]
        
        confidence['stability_score'] = np.mean(stability_scores)
        confidence['performance_score'] = np.mean(performances)
        confidence['risk_score'] = 1 - confidence['stability_score']
        
        # 전체 신뢰도 계산
        confidence['overall_confidence'] = (
            confidence['stability_score'] * 0.4 +
            confidence['performance_score'] * 0.4 +
            (1 - confidence['risk_score']) * 0.2
        )
        
        # 권장사항 생성
        if confidence['overall_confidence'] < 0.6:
            confidence['recommendations'].append("파라미터 신뢰도가 낮습니다. 더 많은 검증이 필요합니다.")
        elif confidence['overall_confidence'] > 0.8:
            confidence['recommendations'].append("파라미터가 매우 신뢰할 수 있습니다.")
        
        return confidence

def main():
    """메인 함수"""
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 적응형 시스템 초기화
    adaptive_system = AdaptiveParameterSystem()
    
    # 다양한 시장 상황에서 파라미터 생성
    scenarios = [
        {'market_condition': 'bear', 'volatility_level': 0.8, 'time_horizon': 'short'},
        {'market_condition': 'bull', 'volatility_level': 0.2, 'time_horizon': 'long'},
        {'market_condition': 'neutral', 'volatility_level': 0.5, 'time_horizon': 'medium'}
    ]
    
    print("🔄 적응형 파라미터 시스템")
    print("=" * 50)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n시나리오 {i}: {scenario}")
        
        params = adaptive_system.get_adaptive_parameters(**scenario)
        
        print("생성된 파라미터:")
        for category, values in params.items():
            print(f"  {category}:")
            for key, value in values.items():
                print(f"    {key}: {value}")

if __name__ == "__main__":
    main()
