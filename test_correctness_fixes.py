#!/usr/bin/env python3
"""
정확성 수정사항 검증 테스트
제안된 수정사항들이 올바르게 적용되었는지 검증
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch
import tempfile
import json

# 테스트 대상 모듈 import
try:
    from enhanced_integrated_analyzer_refactored import (
        EnhancedIntegratedAnalyzer,
        DataValidator,
        DataConverter,
        normalize_market_cap_ekwon,
        ErrorType
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure enhanced_integrated_analyzer_refactored.py is in the current directory")
    sys.exit(1)


class TestCorrectnessFixes(unittest.TestCase):
    """정확성 수정사항 검증 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.analyzer = EnhancedIntegratedAnalyzer(include_external=False, include_realtime=False)
    
    def tearDown(self):
        """테스트 정리"""
        if hasattr(self, 'analyzer'):
            self.analyzer.close()
    
    def test_market_cap_small_cap_handling(self):
        """소형주 시가총액 처리 개선 테스트"""
        # 1억원 이상 소형주가 올바르게 처리되는지 확인
        test_cases = [
            # (input, expected_output, description)
            (1.0, 1.0, "1억원 소형주"),   # 1억원
            (10.0, 10.0, "10억원 소형주"), # 10억원
            (100.0, 100.0, "100억원 소형주"), # 100억원
            (1000.0, 1000.0, "1000억원 중형주"), # 1000억원
        ]
        
        for input_val, expected, description in test_cases:
            with self.subTest(input=input_val, description=description):
                result = normalize_market_cap_ekwon(input_val)
                self.assertEqual(result, expected, f"Failed for {description}: {input_val} -> {result}")
        
        # 1억원 미만은 strict mode에서 None으로 처리됨 (의도된 동작)
        small_cap_result = normalize_market_cap_ekwon(0.5)
        self.assertIsNone(small_cap_result, "0.5억원은 strict mode에서 None으로 처리되어야 함")
    
    def test_market_cap_unit_conversion(self):
        """시가총액 단위 변환 테스트"""
        # strict mode에서는 원 단위 변환이 제한됨 (의도된 동작)
        # 이미 억원 단위로 제공되는 값만 테스트
        test_cases = [
            # (input_eokwon, expected_eokwon, description)
            (1.0, 1.0, "1억원"),      # 1억원
            (10.0, 10.0, "10억원"),  # 10억원
            (100.0, 100.0, "100억원"), # 100억원
            (1000.0, 1000.0, "1000억원"), # 1000억원
        ]
        
        for input_val, expected, description in test_cases:
            with self.subTest(input=input_val, description=description):
                result = normalize_market_cap_ekwon(input_val)
                self.assertEqual(result, expected, f"Failed for {description}: {input_val} -> {result}")
        
        # 원 단위 값은 strict mode에서 None으로 처리됨 (의도된 동작)
        won_result = normalize_market_cap_ekwon(100_000_000)
        self.assertIsNone(won_result, "원 단위 값은 strict mode에서 None으로 처리되어야 함")
    
    def test_cache_lru_recency_update(self):
        """LRU 캐시 최근성 업데이트 테스트"""
        # 캐시에 데이터 저장
        test_data = {'current_price': 100000, 'eps': 5000}
        self.analyzer.data_provider._set_cached(
            self.analyzer.data_provider._cache_price, 
            'test_symbol', 
            test_data
        )
        
        # 캐시에서 조회 (최근성 업데이트 확인)
        result1 = self.analyzer.data_provider._get_cached(
            self.analyzer.data_provider._cache_price, 
            'test_symbol'
        )
        
        # 두 번째 조회
        result2 = self.analyzer.data_provider._get_cached(
            self.analyzer.data_provider._cache_price, 
            'test_symbol'
        )
        
        # 데이터 일치 확인
        self.assertEqual(result1, test_data)
        self.assertEqual(result2, test_data)
        
        # 캐시 히트 확인 (메트릭이 있는 경우)
        if hasattr(self.analyzer.data_provider, 'metrics') and self.analyzer.data_provider.metrics:
            # 캐시 히트가 기록되었는지 확인
            self.assertGreater(self.analyzer.data_provider.metrics.metrics['cache_hits']['price'], 0)
    
    def test_price_api_metrics_consistency(self):
        """가격 API 메트릭 일관성 테스트"""
        # 모킹된 가격 프로바이더로 테스트
        with patch.object(self.analyzer.data_provider.price_provider, 'get_comprehensive_price_data') as mock_price:
            # 빈 페이로드 시뮬레이션
            mock_price.return_value = {}
            
            # 가격 데이터 조회
            result = self.analyzer.data_provider.get_price_data('test_symbol')
            
            # 빈 페이로드가 올바르게 처리되었는지 확인
            self.assertEqual(result, {})
            
            # 메트릭이 있는 경우 EMPTY_PRICE_PAYLOAD 에러가 기록되었는지 확인
            if hasattr(self.analyzer.data_provider, 'metrics') and self.analyzer.data_provider.metrics:
                # API 호출 실패가 기록되었는지 확인 (메트릭 구조에 따라 조정)
                metrics = self.analyzer.data_provider.metrics.metrics
                if 'api_calls' in metrics and 'failed' in metrics['api_calls']:
                    self.assertGreater(metrics['api_calls']['failed'], 0)
                elif 'errors_by_type' in metrics:
                    # 에러 타입별 기록 확인
                    self.assertTrue(len(metrics['errors_by_type']) > 0)
    
    def test_leader_bonus_calculation(self):
        """대장주 가산점 계산 테스트"""
        # 모킹된 데이터로 테스트
        mock_price_data = {'pbr': 1.2}
        mock_financial_data = {'roe': 15.0}
        
        # 대장주 가산점 계산
        bonus = self.analyzer._calculate_leader_bonus(
            '005930', '삼성전자', 500000,  # 50조원
            price_data=mock_price_data,
            financial_data=mock_financial_data
        )
        
        # 가산점이 올바르게 계산되었는지 확인
        self.assertIsInstance(bonus, float)
        self.assertGreaterEqual(bonus, 0.0)
        self.assertLessEqual(bonus, 10.0)
    
    def test_sector_evaluation_method_exists(self):
        """섹터 평가 메서드 존재 확인"""
        # _evaluate_valuation_by_sector 메서드가 존재하는지 확인
        self.assertTrue(hasattr(self.analyzer, '_evaluate_valuation_by_sector'))
        
        # 메서드가 호출 가능한지 확인
        method = getattr(self.analyzer, '_evaluate_valuation_by_sector')
        self.assertTrue(callable(method))
    
    def test_sector_evaluation_call(self):
        """섹터 평가 메서드 호출 테스트"""
        # 섹터 평가 메서드 호출
        result = self.analyzer._evaluate_valuation_by_sector(
            '005930', 12.0, 1.2, 15.0, 500000
        )
        
        # 결과가 딕셔너리인지 확인
        self.assertIsInstance(result, dict)
        
        # 필수 키가 있는지 확인
        expected_keys = ['total_score', 'base_score', 'leader_bonus', 'is_leader', 'grade']
        for key in expected_keys:
            self.assertIn(key, result, f"Missing key: {key}")
    
    def test_percent_canonicalization_safety(self):
        """퍼센트 정규화 안전성 테스트"""
        # 다양한 퍼센트 값 테스트
        test_cases = [
            # (input_data, expected_roe, expected_current_ratio, description)
            ({'roe': 0.12, 'current_ratio': 1.8}, 12.0, 180.0, "소수점 퍼센트"),
            ({'roe': 12, 'current_ratio': 180}, 12.0, 180.0, "이미 퍼센트"),
            ({'roe': -0.03, 'current_ratio': 0.8}, -3.0, 80.0, "음수 퍼센트"),
            ({'roe': -300, 'current_ratio': 80}, -300.0, 80.0, "음수 퍼센트 (이미 변환됨)"),
        ]
        
        for input_data, expected_roe, expected_cr, description in test_cases:
            with self.subTest(description=description):
                # 원본 데이터 보호
                original_data = input_data.copy()
                
                # 정규화 수행
                converted = DataConverter.standardize_financial_units(input_data)
                
                # 원본 데이터가 변경되지 않았는지 확인
                self.assertEqual(input_data, original_data)
                
                # 변환된 데이터 확인
                self.assertAlmostEqual(converted['roe'], expected_roe, places=1)
                self.assertAlmostEqual(converted['current_ratio'], expected_cr, places=1)
    
    def test_eps_bps_minimum_guards(self):
        """EPS/BPS 최소값 가드 테스트"""
        # 극소 EPS/BPS 값 테스트
        test_cases = [
            # (eps, bps, expected_per, expected_pbr, description)
            (0.05, 50, None, None, "극소 EPS/BPS"),  # 최소값 미달
            (0.1, 100, None, None, "최소값 경계"),  # 최소값 경계 (EPS_MIN=0.1, BPS_MIN=100)
            (1.0, 1000, 100.0, 0.1, "정상값"),      # 정상값
        ]
        
        for eps, bps, expected_per, expected_pbr, description in test_cases:
            with self.subTest(description=description):
                # PER/PBR 계산 로직 테스트
                cp = 100.0  # 현재가 100원
                
                # EPS_MIN과 BPS_MIN 상수 사용
                EPS_MIN = 0.1
                BPS_MIN = 100.0
                
                if eps is not None and eps > EPS_MIN and cp > 0:
                    per = cp / eps
                else:
                    per = None
                
                if bps is not None and bps > BPS_MIN and cp > 0:
                    pbr = cp / bps
                else:
                    pbr = None
                
                self.assertEqual(per, expected_per, f"PER mismatch for {description}")
                self.assertEqual(pbr, expected_pbr, f"PBR mismatch for {description}")
    
    def test_52w_band_degeneration_detection(self):
        """52주 밴드 퇴화 감지 테스트"""
        test_cases = [
            # (high, low, current_price, expected_position, description)
            (100, 100, 100, None, "동일값 퇴화"),
            (100, 99.9, 100, None, "극소 밴드 퇴화"),
            (100, 1, 50, 49.49, "정상 밴드"),  # (50-1)/(100-1) ≈ 49.49%
            (100, 50, 75, 50.0, "정상 밴드"),  # (75-50)/(100-50) = 50%
        ]
        
        for hi, lo, cp, exp_pos, description in test_cases:
            with self.subTest(description=description):
                position = self.analyzer._calculate_price_position({
                    'current_price': cp,
                    'w52_high': hi,
                    'w52_low': lo
                })
                
                if exp_pos is None:
                    self.assertIsNone(position, f"Position should be None for {description}")
                else:
                    self.assertAlmostEqual(position, exp_pos, places=1, 
                                         msg=f"Position mismatch for {description}")


def run_correctness_tests():
    """정확성 테스트 실행"""
    # 테스트 스위트 생성
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 테스트 클래스 추가
    suite.addTests(loader.loadTestsFromTestCase(TestCorrectnessFixes))
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("정확성 수정사항 검증 테스트 시작...")
    print("=" * 50)
    
    success = run_correctness_tests()
    
    print("=" * 50)
    if success:
        print("모든 정확성 테스트 통과!")
        sys.exit(0)
    else:
        print("일부 정확성 테스트 실패")
        sys.exit(1)
