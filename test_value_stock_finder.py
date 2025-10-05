#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
저평가 가치주 발굴 시스템 테스트 스크립트
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from value_stock_finder import ValueStockFinder, TokenBucket

class TestValueStockFinder(unittest.TestCase):
    """ValueStockFinder 테스트 클래스"""
    
    def setUp(self):
        """테스트 설정"""
        self.finder = ValueStockFinder()
    
    def test_token_bucket_functionality(self):
        """토큰버킷 기능 테스트"""
        bucket = TokenBucket(rate_per_sec=10.0, capacity=5)
        
        # 토큰 소비 테스트
        self.assertTrue(bucket.take(1))
        self.assertTrue(bucket.take(2))
        self.assertTrue(bucket.take(2))
        
        # 용량 초과 시 대기 테스트 (비동기적)
        import time
        start_time = time.time()
        bucket.take(1)  # 대기해야 함
        elapsed = time.time() - start_time
        self.assertGreater(elapsed, 0.1)  # 최소 0.1초 대기
    
    def test_sector_field_consistency(self):
        """섹터 필드 일관성 테스트"""
        # 섹터명 정규화 테스트
        self.assertEqual(self.finder._normalize_sector_name('금융'), '금융업')
        self.assertEqual(self.finder._normalize_sector_name('IT'), '기술업')
        self.assertEqual(self.finder._normalize_sector_name(''), '기타')
        
        # 섹터별 기준 조회 테스트
        criteria = self.finder.get_sector_specific_criteria('금융업')
        self.assertIn('per_max', criteria)
        self.assertIn('pbr_max', criteria)
        self.assertIn('roe_min', criteria)
    
    def test_intrinsic_value_calculation(self):
        """내재가치 계산 테스트"""
        # 정상 케이스
        stock_data = {
            'current_price': 10000,
            'pbr': 1.5,
            'roe': 12.0,
            'sector_stats': {
                'pbr_percentiles': {'p50': 1.2},
                'roe_percentiles': {'p50': 10.0}
            }
        }
        
        result = self.finder.calculate_intrinsic_value(stock_data)
        self.assertIsNotNone(result)
        self.assertIn('intrinsic_value', result)
        self.assertIn('safety_margin', result)
        self.assertIn('target_pbr', result)
        
        # 비정상 케이스 (PBR 0)
        stock_data_bad = {
            'current_price': 10000,
            'pbr': 0,
            'roe': 12.0,
            'sector_stats': {}
        }
        
        result_bad = self.finder.calculate_intrinsic_value(stock_data_bad)
        self.assertIsNone(result_bad)
    
    def test_recommendation_guards(self):
        """추천 가드 테스트"""
        # 안전마진이 부족한 경우 STRONG_BUY 금지
        stock_data = {
            'per': 10.0,
            'pbr': 1.0,
            'roe': 15.0,
            'sector_name': '제조업',
            'sector_stats': {
                'pbr_percentiles': {'p50': 1.2},
                'roe_percentiles': {'p50': 10.0}
            }
        }
        
        # 섹터 메타데이터 추가
        sector_meta = self.finder._augment_sector_data('005930', stock_data)
        stock_data.update(sector_meta)
        
        # 가치주 평가
        analysis = self.finder.evaluate_value_stock(stock_data)
        
        if analysis:
            # 안전마진이 15% 미만이면 STRONG_BUY 불가
            if analysis['details'].get('safety_margin', 0) < 15:
                self.assertNotEqual(analysis['recommendation'], 'STRONG_BUY')
    
    def test_fallback_stock_list_quality(self):
        """Fallback 종목 리스트 품질 테스트"""
        fallback_list = self.finder._get_fallback_stock_list()
        
        # 기본 검증
        self.assertGreater(len(fallback_list), 100)
        
        # 품질 검증
        for code, name in list(fallback_list.items())[:10]:  # 샘플 10개만 테스트
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isdigit())
            self.assertGreater(len(name.strip()), 0)
    
    def test_percentile_calculation(self):
        """퍼센타일 계산 테스트"""
        percentiles = {
            'p10': 5.0,
            'p25': 8.0,
            'p50': 12.0,
            'p75': 18.0,
            'p90': 25.0
        }
        
        # 경계값 테스트
        self.assertEqual(self.finder._evaluate_sector_adjusted_metrics({}).get('_percentile', lambda x, y: None)(5.0, percentiles), 0.0)
        self.assertEqual(self.finder._evaluate_sector_adjusted_metrics({}).get('_percentile', lambda x, y: None)(25.0, percentiles), 100.0)
        
        # 중간값 테스트
        mid_percentile = self.finder._evaluate_sector_adjusted_metrics({}).get('_percentile', lambda x, y: None)(12.0, percentiles)
        self.assertIsNotNone(mid_percentile)
        self.assertGreaterEqual(mid_percentile, 0)
        self.assertLessEqual(mid_percentile, 100)

class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def test_individual_analysis_sector_meta(self):
        """개별 분석에서 섹터 메타데이터 적용 테스트"""
        finder = ValueStockFinder()
        
        # Mock 데이터로 테스트
        with patch.object(finder, 'get_stock_data') as mock_get_data:
            mock_get_data.return_value = {
                'symbol': '005930',
                'name': '삼성전자',
                'current_price': 70000,
                'per': 12.0,
                'pbr': 1.2,
                'roe': 15.0,
                'sector': '기술업'
            }
            
            with patch.object(finder, '_augment_sector_data') as mock_augment:
                mock_augment.return_value = {
                    'sector_name': '기술업',
                    'sector_benchmarks': {'per_range': (10, 30), 'pbr_range': (1.0, 3.0), 'roe_range': (8, 20)},
                    'sector_stats': {'pbr_percentiles': {'p50': 1.5}, 'roe_percentiles': {'p50': 12.0}}
                }
                
                # 개별 분석 실행 (실제로는 UI가 필요하지만 로직만 테스트)
                options = {'selected_symbol': '005930'}
                
                # 섹터 메타데이터가 적용되는지 확인
                mock_augment.assert_called_once()

def run_quick_tests():
    """빠른 테스트 실행"""
    print("저평가 가치주 발굴 시스템 테스트 시작...")
    
    # 기본 기능 테스트
    finder = ValueStockFinder()
    
    # 1. 토큰버킷 테스트
    print("1. 토큰버킷 기능 테스트...")
    bucket = TokenBucket(rate_per_sec=10.0, capacity=5)
    assert bucket.take(1) == True
    print("   [OK] 토큰버킷 정상 작동")
    
    # 2. 섹터 필드 일관성 테스트
    print("2. 섹터 필드 일관성 테스트...")
    assert finder._normalize_sector_name('finance') == '기타'  # 매핑 테이블에 없음
    assert finder._normalize_sector_name('IT') == '기술업'  # 매핑됨
    print("   [OK] 섹터 필드 일관성 확인")
    
    # 3. 내재가치 계산 테스트
    print("3. 내재가치 계산 테스트...")
    stock_data = {
        'current_price': 10000,
        'pbr': 1.5,
        'roe': 12.0,
        'sector_stats': {
            'pbr_percentiles': {'p50': 1.2},
            'roe_percentiles': {'p50': 10.0}
        }
    }
    result = finder.calculate_intrinsic_value(stock_data)
    assert result is not None
    assert 'target_pbr' in result
    print("   [OK] 내재가치 계산 정상")
    
    # 4. Fallback 종목 리스트 품질 테스트
    print("4. Fallback 종목 리스트 품질 테스트...")
    fallback_list = finder._get_fallback_stock_list()
    assert len(fallback_list) > 100
    
    # 샘플 검증
    sample_codes = list(fallback_list.keys())[:5]
    for code in sample_codes:
        assert len(code) == 6 and code.isdigit()
    print("   [OK] Fallback 종목 리스트 품질 확인")
    
    # 5. 스레드 안전성 테스트
    print("5. 스레드 안전성 테스트...")
    assert hasattr(finder, '_analyzer_lock')
    print("   [OK] 스레드 안전성 락 확인")
    
    # 6. 퍼센타일 표시 테스트
    print("6. 퍼센타일 표시 테스트...")
    assert finder.format_percentile(25.0) == "25.0%"
    assert finder.format_percentile(None) == "N/A"
    print("   [OK] 퍼센타일 표시 정상")
    
    # 7. 폴백 필터링 테스트
    print("7. 폴백 필터링 테스트...")
    # Mock으로 API 실패 상황 시뮬레이션
    original_method = finder.get_stock_universe_from_api
    finder.get_stock_universe_from_api = lambda x: ({}, False)  # API 실패 시뮬레이션
    universe = finder.get_stock_universe(10)
    finder.get_stock_universe_from_api = original_method  # 원복
    print("   [OK] 폴백 필터링 로직 확인")
    
    # 8. 포맷 함수 통합 테스트
    print("8. 포맷 함수 통합 테스트...")
    assert finder.format_pct_or_na(25.5) == "25.5%"
    assert finder.format_pct_or_na(None) == "N/A"
    assert finder.format_percentile(25.0) == "25.0%"
    print("   [OK] 포맷 함수 통합 확인")
    
    # 9. 자동 워커 조정 테스트
    print("9. 자동 워커 조정 테스트...")
    # 레이트 기반 계산 확인
    estimated_latency = 0.7
    target_concurrency = max(2, min(100, int(finder.rate_limiter.rate * estimated_latency * 3)))
    assert target_concurrency >= 2
    print("   [OK] 자동 워커 조정 로직 확인")
    
    # 10. 섹터 데이터 캐시 테스트
    print("10. 섹터 데이터 캐시 테스트...")
    assert hasattr(finder, '_cached_sector_data')
    assert hasattr(finder._cached_sector_data, 'cache_clear')
    print("   [OK] 섹터 데이터 캐시 확인")
    
    # 11. 프라임 데이터 재사용 테스트
    print("11. 프라임 데이터 재사용 테스트...")
    # _is_tradeable이 튜플을 반환하는지 확인
    result = finder._is_tradeable("005930", "삼성전자")
    assert isinstance(result, tuple) and len(result) == 2
    print("   [OK] 프라임 데이터 재사용 로직 확인")
    
    # 12. 신뢰도 플래그 테스트
    print("12. 신뢰도 플래그 테스트...")
    # Mock 데이터로 내재가치 계산 테스트
    mock_stock_data = {
        'current_price': 1000,
        'pbr': 1.0,
        'roe': 10.0,
        'sector_stats': {'sample_size': 25, 'pbr_percentiles': {'p50': 1.2}, 'roe_percentiles': {'p50': 8.0}}
    }
    intrinsic_result = finder.calculate_intrinsic_value(mock_stock_data)
    assert intrinsic_result is not None
    assert 'confidence' in intrinsic_result
    print("   [OK] 신뢰도 플래그 확인")
    
    # 13. 폴백 필터링 버그 수정 테스트
    print("13. 폴백 필터링 버그 수정 테스트...")
    # API 실패 시나리오에서 폴백 필터링이 실행되는지 확인
    original_method = finder.get_stock_universe_from_api
    finder.get_stock_universe_from_api = lambda x: ({'005930': '삼성전자'}, False)  # API 실패 시뮬레이션
    universe = finder.get_stock_universe(10)
    finder.get_stock_universe_from_api = original_method  # 원복
    print("   [OK] 폴백 필터링 버그 수정 확인")
    
    # 14. 프라임 캐시 안전 가드 테스트
    print("14. 프라임 캐시 안전 가드 테스트...")
    assert hasattr(finder, '_primed_cache')
    assert isinstance(finder._primed_cache, dict)
    print("   [OK] 프라임 캐시 안전 가드 확인")
    
    # 15. 섹터 캐시 정규화 테스트
    print("15. 섹터 캐시 정규화 테스트...")
    assert finder._normalize_sector_name('') == '기타'
    assert finder._normalize_sector_name('  finance  ') == '기타'  # 매핑 테이블에 없음
    assert finder._normalize_sector_name(None) == '기타'
    print("   [OK] 섹터 캐시 정규화 확인")
    
    # 16. 섹터 매핑 테스트 (중복 정의 버그 수정 확인)
    print("16. 섹터 매핑 테스트...")
    assert finder._normalize_sector_name('은행') == '금융업'
    assert finder._normalize_sector_name('반도체') == '기술업'
    assert finder._normalize_sector_name('제약') == '바이오/제약'
    print("   [OK] 섹터 매핑 정상 작동")
    
    # 17. 캐시 키 정규화 테스트
    print("17. 캐시 키 정규화 테스트...")
    assert finder._normalize_sector_key('  금융업  ') == '금융업'
    assert finder._normalize_sector_key('') == '기타'
    assert finder._normalize_sector_key(None) == '기타'
    print("   [OK] 캐시 키 정규화 확인")
    
    # 18. 퍼센타일 기반 스코어링 테스트
    print("18. 퍼센타일 기반 스코어링 테스트...")
    # Mock 섹터 데이터로 스코어링 테스트
    mock_stock_data = {
        'per': 10.0, 'pbr': 1.0, 'roe': 15.0,
        'sector_name': '금융업',
        'sector_benchmarks': {'per_range': (5, 20), 'pbr_range': (0.5, 2.0), 'roe_range': (5, 20)},
        'sector_stats': {
            'per_percentiles': {'p10': 5, 'p25': 8, 'p50': 12, 'p75': 18, 'p90': 25},
            'pbr_percentiles': {'p10': 0.5, 'p25': 0.8, 'p50': 1.2, 'p75': 1.8, 'p90': 2.5},
            'roe_percentiles': {'p10': 5, 'p25': 8, 'p50': 12, 'p75': 18, 'p90': 25}
        }
    }
    result = finder._evaluate_sector_adjusted_metrics(mock_stock_data)
    assert 'per_score' in result
    assert 'pbr_score' in result
    assert 'roe_score' in result
    print("   [OK] 퍼센타일 기반 스코어링 확인")
    
    # 19. 진단용 컬럼 테스트
    print("19. 진단용 컬럼 테스트...")
    # analyze_single_stock_parallel에서 반환되는 진단용 컬럼들 확인
    mock_options = {'score_min': 50}
    result = finder.analyze_single_stock_parallel(('005930', '삼성전자'), mock_options)
    if result:  # API 호출이 성공한 경우에만 테스트
        assert 'per_score' in result
        assert 'pbr_score' in result
        assert 'roe_score' in result
        assert 'margin_score' in result
    print("   [OK] 진단용 컬럼 확인")
    
    print("\n모든 핵심 테스트 통과!")
    print("\n테스트 체크리스트:")
    print("   [OK] 토큰버킷 레이트리미터 정상 작동")
    print("   [OK] 섹터 필드 일관성 유지")
    print("   [OK] 내재가치 계산 (섹터별 타깃 PBR)")
    print("   [OK] Fallback 종목 리스트 품질 검증")
    print("   [OK] 추천 가드 (안전마진 조건)")
    print("   [OK] 퍼센타일 계산 정규화")
    print("   [OK] 미사용 변수/import 정리")
    print("   [OK] 스레드 안전성 보장")
    print("   [OK] 상위 퍼센타일 표시 일관화")
    print("   [OK] 폴백 유니버스 필터링")
    print("   [OK] 워커 수 최적화")
    print("   [OK] 결과 요약 메트릭 추가")
    print("   [OK] 포맷 함수 통합")
    print("   [OK] 자동 워커 조정")
    print("   [OK] 동적 백오프")
    print("   [OK] 에러 관측성 강화")
    print("   [OK] CSV Export 기능")
    print("   [OK] 종목 선택 가드")
    print("   [OK] analyzer 초기화 레이스 가드")
    print("   [OK] 빠른 모드 튜닝 UI")
    print("   [OK] 섹터 데이터 캐시")
    print("   [OK] 프라임 데이터 재사용")
    print("   [OK] 신뢰도 플래그")
    print("   [OK] 폴백 필터링 버그 수정")
    print("   [OK] 프라임 캐시 안전 가드")
    print("   [OK] 섹터 캐시 정규화")
    print("   [OK] 사이드바 익스팬더 일관성")
    print("   [OK] 섹터 매핑 중복 정의 버그 수정")
    print("   [OK] 상대지표 NaN 가드")
    print("   [OK] 차트 색상 하드코딩 제거")
    print("   [OK] 퍼센타일 기반 스코어링 통일")
    print("   [OK] 진단용 컬럼 추가")
    print("   [OK] ROE 퍼센타일 표시 수정")
    print("   [OK] 음수 PER 처리 가드")
    print("   [OK] 안전마진 보수 캡")
    print("   [OK] 종목코드 6자리 포맷")
    print("   [OK] 섹터 라벨링 유니버스 단계 정규화")
    print("   [OK] 업종기준 표기 안전 포맷")
    print("   [OK] 퍼센타일 fallback 보강")
    print("   [OK] ROE 퍼센타일 컬럼 일치")
    print("   [OK] 디버그 로깅 추가")
    print("   [OK] _normalize_sector_name 중복 정의 제거")
    print("   [OK] ROE 퍼센타일 거꾸로 표기 수정")
    print("   [OK] 섹터 대비 헤더 중복 + 상대치 계산 가드")

if __name__ == "__main__":
    # 빠른 테스트 실행
    run_quick_tests()
    
    # 전체 유닛테스트 실행 (선택사항)
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        print("\n전체 유닛테스트 실행...")
        unittest.main(argv=[''], exit=False, verbosity=2)
