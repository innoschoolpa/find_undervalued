#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
앙상블 파라미터 시스템
여러 파라미터 조합의 결과를 종합하여 최적의 파라미터를 결정합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging
from collections import defaultdict

class EnsembleParameterSystem:
    """앙상블 파라미터 시스템"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 다양한 파라미터 조합들
        self.parameter_combinations = [
            {
                'name': 'conservative_financial',
                'weights': {
                    'opinion_analysis': 15.0,
                    'estimate_analysis': 20.0,
                    'financial_ratios': 45.0,
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
            {
                'name': 'balanced_growth',
                'weights': {
                    'opinion_analysis': 20.0,
                    'estimate_analysis': 30.0,
                    'financial_ratios': 25.0,
                    'growth_analysis': 20.0,
                    'scale_analysis': 5.0
                },
                'financial_ratio_weights': {
                    'roe_score': 6,
                    'roa_score': 4,
                    'debt_ratio_score': 8,
                    'net_profit_margin_score': 4,
                    'current_ratio_score': 4,
                    'growth_score': 4
                }
            },
            {
                'name': 'aggressive_opinion',
                'weights': {
                    'opinion_analysis': 30.0,
                    'estimate_analysis': 35.0,
                    'financial_ratios': 20.0,
                    'growth_analysis': 10.0,
                    'scale_analysis': 5.0
                },
                'financial_ratio_weights': {
                    'roe_score': 4,
                    'roa_score': 3,
                    'debt_ratio_score': 6,
                    'net_profit_margin_score': 3,
                    'current_ratio_score': 3,
                    'growth_score': 3
                }
            },
            {
                'name': 'current_optimized',
                'weights': {
                    'opinion_analysis': 28.04,
                    'estimate_analysis': 33.64,
                    'financial_ratios': 22.43,
                    'growth_analysis': 4.67,
                    'scale_analysis': 11.21
                },
                'financial_ratio_weights': {
                    'roe_score': 9,
                    'roa_score': 3,
                    'debt_ratio_score': 6,
                    'net_profit_margin_score': 6,
                    'current_ratio_score': 5,
                    'growth_score': 1
                }
            }
        ]
    
    def evaluate_ensemble_performance(self, 
                                    test_conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """앙상블 성능 평가"""
        
        results = {
            'individual_performances': {},
            'ensemble_weights': {},
            'recommended_combination': None,
            'confidence_score': 0.0
        }
        
        # 각 파라미터 조합의 성능 평가
        for combo in self.parameter_combinations:
            combo_name = combo['name']
            performance_scores = []
            
            for condition in test_conditions:
                # 시뮬레이션된 성능 점수 (실제로는 백테스팅 필요)
                score = self._simulate_performance(combo, condition)
                performance_scores.append(score)
            
            results['individual_performances'][combo_name] = {
                'mean_score': np.mean(performance_scores),
                'std_score': np.std(performance_scores),
                'min_score': np.min(performance_scores),
                'max_score': np.max(performance_scores),
                'scores': performance_scores
            }
        
        # 앙상블 가중치 계산
        results['ensemble_weights'] = self._calculate_ensemble_weights(results['individual_performances'])
        
        # 권장 조합 선택
        results['recommended_combination'] = self._select_recommended_combination(results)
        
        # 신뢰도 점수 계산
        results['confidence_score'] = self._calculate_confidence_score(results)
        
        return results
    
    def _simulate_performance(self, 
                            combo: Dict[str, Any], 
                            condition: Dict[str, Any]) -> float:
        """파라미터 조합의 성능 시뮬레이션"""
        
        # 실제로는 백테스팅 엔진을 사용해야 함
        # 여기서는 시뮬레이션된 점수 반환
        
        base_score = 1.0
        
        # 시장 상황에 따른 조정
        if condition.get('market') == 'bull':
            base_score *= 1.1
        elif condition.get('market') == 'bear':
            base_score *= 0.9
        
        # 기간에 따른 조정
        if condition.get('period') == 'long':
            base_score *= 1.05
        elif condition.get('period') == 'short':
            base_score *= 0.95
        
        # 종목 수에 따른 조정
        if condition.get('stocks', 5) > 10:
            base_score *= 1.02
        
        # 랜덤 노이즈 추가
        noise = np.random.normal(0, 0.1)
        final_score = base_score + noise
        
        return max(0, final_score)  # 음수 방지
    
    def _calculate_ensemble_weights(self, 
                                  performances: Dict[str, Any]) -> Dict[str, float]:
        """앙상블 가중치 계산"""
        
        weights = {}
        total_score = 0
        
        for name, perf in performances.items():
            # 평균 성능과 안정성을 모두 고려
            score = perf['mean_score'] * (1 - perf['std_score'])
            weights[name] = score
            total_score += score
        
        # 정규화
        if total_score > 0:
            for name in weights:
                weights[name] /= total_score
        
        return weights
    
    def _select_recommended_combination(self, 
                                      results: Dict[str, Any]) -> str:
        """권장 조합 선택"""
        
        performances = results['individual_performances']
        
        # 평균 성능이 높고 안정성이 좋은 조합 선택
        best_combo = None
        best_score = -1
        
        for name, perf in performances.items():
            # 성능과 안정성을 종합한 점수
            score = perf['mean_score'] * (1 - perf['std_score'])
            
            if score > best_score:
                best_score = score
                best_combo = name
        
        return best_combo
    
    def _calculate_confidence_score(self, results: Dict[str, Any]) -> float:
        """신뢰도 점수 계산"""
        
        performances = results['individual_performances']
        
        if not performances:
            return 0.0
        
        # 모든 조합의 성능 분산 계산
        all_scores = []
        for perf in performances.values():
            all_scores.extend(perf['scores'])
        
        # 낮은 분산 = 높은 신뢰도
        variance = np.var(all_scores)
        confidence = max(0, 1 - variance)
        
        return confidence
    
    def get_ensemble_parameters(self, 
                               ensemble_weights: Dict[str, float]) -> Dict[str, Any]:
        """앙상블 가중치를 기반으로 최종 파라미터 생성"""
        
        # 가중 평균으로 최종 파라미터 계산
        final_weights = defaultdict(float)
        final_financial_weights = defaultdict(float)
        
        for combo in self.parameter_combinations:
            weight = ensemble_weights.get(combo['name'], 0)
            
            # weights 가중 평균
            for key, value in combo['weights'].items():
                final_weights[key] += value * weight
            
            # financial_ratio_weights 가중 평균
            for key, value in combo['financial_ratio_weights'].items():
                final_financial_weights[key] += value * weight
        
        # 정규화
        total_weight = sum(final_weights.values())
        if total_weight > 0:
            for key in final_weights:
                final_weights[key] /= total_weight
                final_weights[key] *= 100  # 백분율로 변환
        
        return {
            'weights': dict(final_weights),
            'financial_ratio_weights': dict(final_financial_weights)
        }

def main():
    """메인 함수"""
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 앙상블 시스템 초기화
    ensemble_system = EnsembleParameterSystem()
    
    # 테스트 조건들
    test_conditions = [
        {'period': '3months', 'stocks': 3, 'market': 'bull'},
        {'period': '6months', 'stocks': 5, 'market': 'bear'},
        {'period': '12months', 'stocks': 10, 'market': 'volatile'},
        {'period': '3months', 'stocks': 30, 'market': 'stable'}
    ]
    
    # 앙상블 성능 평가
    results = ensemble_system.evaluate_ensemble_performance(test_conditions)
    
    print("🎯 앙상블 파라미터 시스템 결과")
    print("=" * 50)
    
    print(f"신뢰도 점수: {results['confidence_score']:.3f}")
    print(f"권장 조합: {results['recommended_combination']}")
    
    print("\n개별 조합 성능:")
    for name, perf in results['individual_performances'].items():
        print(f"  {name}: 평균 {perf['mean_score']:.3f} (표준편차 {perf['std_score']:.3f})")
    
    print("\n앙상블 가중치:")
    for name, weight in results['ensemble_weights'].items():
        print(f"  {name}: {weight:.3f}")
    
    # 최종 앙상블 파라미터 생성
    final_params = ensemble_system.get_ensemble_parameters(results['ensemble_weights'])
    
    print("\n최종 앙상블 파라미터:")
    for category, values in final_params.items():
        print(f"  {category}:")
        for key, value in values.items():
            print(f"    {key}: {value:.2f}")

if __name__ == "__main__":
    main()
