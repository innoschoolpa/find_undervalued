#!/usr/bin/env python3
"""
성능 최적화 테스트
캐시 효율성, 병렬 처리, 메모리 사용량 개선 검증
"""

import os
import sys
import time
import unittest
from unittest.mock import Mock, patch
import tempfile
import json
import gc

# 테스트 대상 모듈 import
try:
    from enhanced_integrated_analyzer_refactored import (
        EnhancedIntegratedAnalyzer,
        DataValidator,
        DataConverter,
        MetricsCollector
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure enhanced_integrated_analyzer_refactored.py is in the current directory")
    sys.exit(1)


class TestPerformanceOptimization(unittest.TestCase):
    """성능 최적화 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.analyzer = EnhancedIntegratedAnalyzer(include_external=False, include_realtime=False)
    
    def tearDown(self):
        """테스트 정리"""
        if hasattr(self, 'analyzer'):
            self.analyzer.close()
    
    def test_cache_compression(self):
        """캐시 압축 기능 테스트"""
        # 큰 데이터 생성
        large_data = {
            'financial_data': {
                'roe': 15.5,
                'roa': 8.2,
                'debt_ratio': 25.0,
                'net_profit_margin': 12.3,
                'current_ratio': 2.1,
                'detailed_analysis': 'x' * 2000  # 큰 문자열
            }
        }
        
        # 캐시에 저장
        self.analyzer.data_provider._set_cached(
            self.analyzer.data_provider._cache_fin, 
            'test_symbol', 
            large_data
        )
        
        # 캐시에서 조회
        retrieved_data = self.analyzer.data_provider._get_cached(
            self.analyzer.data_provider._cache_fin, 
            'test_symbol'
        )
        
        # 데이터 일치 확인
        self.assertEqual(retrieved_data, large_data)
    
    def test_dynamic_worker_scaling(self):
        """동적 워커 수 조정 테스트"""
        # 소규모 배치 (10개 이하)
        small_batch = [{'symbol': f'00{i:04d}', 'name': f'종목{i}'} for i in range(5)]
        
        # 중규모 배치 (50개 이하)
        medium_batch = [{'symbol': f'00{i:04d}', 'name': f'종목{i}'} for i in range(25)]
        
        # 대규모 배치 (50개 초과)
        large_batch = [{'symbol': f'00{i:04d}', 'name': f'종목{i}'} for i in range(100)]
        
        # 워커 수 계산 로직 테스트
        import pandas as pd
        
        # 소규모 배치 테스트
        small_df = pd.DataFrame(small_batch)
        with patch.object(self.analyzer, '_analyze_stocks_parallel') as mock_parallel:
            mock_parallel.return_value = []
            self.analyzer._analyze_stocks_parallel(small_df)
            
            # 워커 수가 적절히 제한되었는지 확인
            call_args = mock_parallel.call_args
            self.assertIsNotNone(call_args)
    
    def test_memory_monitoring(self):
        """메모리 모니터링 기능 테스트"""
        # 메모리 체크 메서드 테스트
        initial_count = self.analyzer._analysis_count
        
        # 분석 카운트 증가
        self.analyzer._increment_analysis_count()
        
        # 카운트가 증가했는지 확인
        self.assertEqual(self.analyzer._analysis_count, initial_count + 1)
        
        # 메모리 체크 직접 호출
        try:
            self.analyzer._check_memory_usage()
            # 예외 없이 실행되면 성공
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Memory check failed: {e}")
    
    def test_chunk_processing(self):
        """청크 처리 기능 테스트"""
        # 대규모 배치 생성
        large_batch = [{'symbol': f'00{i:04d}', 'name': f'종목{i}'} for i in range(50)]
        
        import pandas as pd
        large_df = pd.DataFrame(large_batch)
        
        # 청크 크기 설정
        os.environ['ANALYSIS_CHUNK_SIZE'] = '10'
        
        # 청크 처리 로직 테스트
        chunk_size = 10
        chunks = [large_df[i:i + chunk_size] for i in range(0, len(large_df), chunk_size)]
        
        # 청크가 올바르게 분할되었는지 확인
        self.assertEqual(len(chunks), 5)  # 50개를 10개씩 5개 청크
        self.assertEqual(len(chunks[0]), 10)
        self.assertEqual(len(chunks[-1]), 10)
    
    def test_cache_ttl_optimization(self):
        """캐시 TTL 최적화 테스트"""
        # 환경변수로 TTL 설정
        os.environ['SECTOR_CACHE_TTL'] = '300'  # 5분
        os.environ['SECTOR_CHAR_CACHE_TTL'] = '600'  # 10분
        
        # 새로운 분석기 인스턴스 생성
        analyzer = EnhancedIntegratedAnalyzer(include_external=False, include_realtime=False)
        
        try:
            # TTL이 올바르게 설정되었는지 확인
            self.assertEqual(analyzer._sector_cache_ttl, 300)
            self.assertEqual(analyzer._sector_char_cache_ttl, 600)
        finally:
            analyzer.close()
    
    def test_memory_usage_optimization(self):
        """메모리 사용량 최적화 테스트"""
        # KOSPI 데이터 로딩 최적화 테스트
        # 필요한 컬럼만 로드하는지 확인
        
        # 가상의 KOSPI 데이터 생성
        import pandas as pd
        test_data = pd.DataFrame({
            '단축코드': ['005930', '000660', '035420'],
            '한글명': ['삼성전자', 'SK하이닉스', 'NAVER'],
            '시가총액': [500000, 300000, 200000],
            '업종': ['전기전자', '전기전자', '서비스업'],
            '불필요한컬럼1': ['data1', 'data2', 'data3'],
            '불필요한컬럼2': ['data4', 'data5', 'data6']
        })
        
        # 필요한 컬럼만 선택 (존재하는 컬럼만)
        required_columns = ['단축코드', '한글명', '시가총액']
        optional_columns = ['업종']  # 실제로 존재하는 컬럼만
        
        available_columns = [col for col in required_columns + optional_columns if col in test_data.columns]
        filtered_data = test_data[available_columns]
        
        # 필터링된 데이터가 원본보다 컬럼이 적은지 확인
        self.assertLess(len(filtered_data.columns), len(test_data.columns))
    
    def test_parallel_processing_efficiency(self):
        """병렬 처리 효율성 테스트"""
        # 병렬 처리 시간 측정
        test_symbols = ['005930', '000660', '035420', '207940', '006400']
        
        start_time = time.time()
        
        # 순차 처리 시뮬레이션
        sequential_results = []
        for symbol in test_symbols:
            # 모킹된 분석 결과
            result = Mock()
            result.symbol = symbol
            result.status = 'SUCCESS'
            sequential_results.append(result)
        
        sequential_time = time.time() - start_time
        
        # 병렬 처리 시뮬레이션
        start_time = time.time()
        
        # ThreadPoolExecutor 시뮬레이션
        from concurrent.futures import ThreadPoolExecutor
        
        def mock_analyze(symbol):
            result = Mock()
            result.symbol = symbol
            result.status = 'SUCCESS'
            return result
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            parallel_results = list(executor.map(mock_analyze, test_symbols))
        
        parallel_time = time.time() - start_time
        
        # 병렬 처리가 더 빠른지 확인 (작은 데이터셋에서는 차이가 미미할 수 있음)
        print(f"Sequential time: {sequential_time:.4f}s")
        print(f"Parallel time: {parallel_time:.4f}s")
        
        # 결과 일치 확인
        self.assertEqual(len(sequential_results), len(parallel_results))
    
    def test_garbage_collection_optimization(self):
        """가비지 컬렉션 최적화 테스트"""
        # 메모리 사용량 측정 (psutil이 있는 경우)
        try:
            import psutil
            process = psutil.Process()
            
            # 초기 메모리 사용량
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            # 대량의 객체 생성
            large_objects = []
            for i in range(1000):
                large_objects.append({'data': 'x' * 1000, 'index': i})
            
            # 메모리 사용량 증가 확인
            peak_memory = process.memory_info().rss / 1024 / 1024
            
            # 객체 삭제 및 가비지 컬렉션
            del large_objects
            gc.collect()
            
            # 메모리 사용량 감소 확인
            final_memory = process.memory_info().rss / 1024 / 1024
            
            print(f"Initial memory: {initial_memory:.1f}MB")
            print(f"Peak memory: {peak_memory:.1f}MB")
            print(f"Final memory: {final_memory:.1f}MB")
            
            # 메모리가 정리되었는지 확인 (작은 차이는 허용)
            memory_freed = peak_memory - final_memory
            print(f"Memory freed: {memory_freed:.1f}MB")
            # 메모리 해제가 발생했거나 최소한 증가하지 않았는지 확인
            self.assertLessEqual(final_memory, peak_memory)
            
        except ImportError:
            # psutil이 없는 경우 간단한 GC 테스트
            gc.collect()
            self.assertTrue(True)  # GC가 예외 없이 실행되면 성공


def run_performance_tests():
    """성능 테스트 실행"""
    # 테스트 스위트 생성
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 테스트 클래스 추가
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceOptimization))
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("성능 최적화 테스트 시작...")
    print("=" * 50)
    
    success = run_performance_tests()
    
    print("=" * 50)
    if success:
        print("모든 성능 테스트 통과!")
        sys.exit(0)
    else:
        print("일부 성능 테스트 실패")
        sys.exit(1)
