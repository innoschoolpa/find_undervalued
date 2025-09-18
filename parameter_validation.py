#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파라미터 검증 시스템
다양한 조건에서 파라미터의 안정성을 검증합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging

class ParameterValidator:
    """파라미터 검증 클래스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def validate_parameter_stability(self, 
                                   base_params: Dict[str, Any],
                                   test_conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """파라미터 안정성 검증"""
        
        results = {
            'base_params': base_params,
            'test_results': [],
            'stability_score': 0.0,
            'recommendations': []
        }
        
        for i, condition in enumerate(test_conditions):
            self.logger.info(f"테스트 조건 {i+1}: {condition}")
            
            # 각 조건에서 파라미터 테스트
            test_result = self._test_parameter_condition(base_params, condition)
            results['test_results'].append(test_result)
            
        # 안정성 점수 계산
        results['stability_score'] = self._calculate_stability_score(results['test_results'])
        
        # 권장사항 생성
        results['recommendations'] = self._generate_recommendations(results)
        
        return results
    
    def _test_parameter_condition(self, 
                                 params: Dict[str, Any], 
                                 condition: Dict[str, Any]) -> Dict[str, Any]:
        """특정 조건에서 파라미터 테스트"""
        
        # 여기서는 간단한 시뮬레이션
        # 실제로는 백테스팅 엔진을 사용해야 함
        
        test_result = {
            'condition': condition,
            'performance': np.random.uniform(0.8, 1.2),  # 시뮬레이션
            'stability': np.random.uniform(0.7, 0.95),
            'risk_score': np.random.uniform(0.1, 0.4)
        }
        
        return test_result
    
    def _calculate_stability_score(self, test_results: List[Dict[str, Any]]) -> float:
        """안정성 점수 계산"""
        
        if not test_results:
            return 0.0
            
        # 성능의 일관성 계산
        performances = [r['performance'] for r in test_results]
        performance_std = np.std(performances)
        performance_mean = np.mean(performances)
        
        # 안정성 점수 계산 (낮은 표준편차 = 높은 안정성)
        stability_score = max(0, 1 - (performance_std / performance_mean))
        
        return stability_score
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """권장사항 생성"""
        
        recommendations = []
        
        if results['stability_score'] < 0.7:
            recommendations.append("파라미터 안정성이 낮습니다. 더 많은 데이터로 검증이 필요합니다.")
        
        if results['stability_score'] > 0.9:
            recommendations.append("파라미터가 매우 안정적입니다. 현재 설정을 유지하세요.")
        
        return recommendations

def main():
    """메인 함수"""
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 검증기 초기화
    validator = ParameterValidator()
    
    # 기본 파라미터 (현재 고정 파라미터)
    base_params = {
        'weights': {
            'opinion_analysis': 20.37,
            'estimate_analysis': 29.63,
            'financial_ratios': 33.33,
            'growth_analysis': 15.74,
            'scale_analysis': 0.93
        },
        'financial_ratio_weights': {
            'roe_score': 6,
            'roa_score': 5,
            'debt_ratio_score': 10,
            'net_profit_margin_score': 4,
            'current_ratio_score': 4,
            'growth_score': 1
        }
    }
    
    # 테스트 조건들
    test_conditions = [
        {'period': '3months', 'stocks': 3, 'market': 'bull'},
        {'period': '6months', 'stocks': 5, 'market': 'bear'},
        {'period': '12months', 'stocks': 10, 'market': 'volatile'},
        {'period': '3months', 'stocks': 30, 'market': 'stable'}
    ]
    
    # 검증 실행
    results = validator.validate_parameter_stability(base_params, test_conditions)
    
    # 결과 출력
    print("🔍 파라미터 안정성 검증 결과")
    print("=" * 50)
    print(f"안정성 점수: {results['stability_score']:.2f}")
    print("\n권장사항:")
    for rec in results['recommendations']:
        print(f"- {rec}")

if __name__ == "__main__":
    main()
