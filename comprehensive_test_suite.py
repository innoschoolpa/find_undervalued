# comprehensive_test_suite.py
"""
포괄적인 테스트 스위트
- 단위 테스트
- 통합 테스트
- 성능 테스트
- 에러 처리 테스트
- 메모리 누수 테스트
"""

import unittest
import time
import threading
import gc
import sys
import os
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

# 테스트 대상 모듈들
try:
    from enhanced_integrated_analyzer_refactored import (
        EnhancedIntegratedAnalyzer, AnalysisResult, AnalysisStatus,
        normalize_market_cap_ekwon, serialize_for_json, fmt, fmt_pct
    )
    from performance_optimizer import (
        LRUCache, PerformanceMonitor, timed_operation, 
        memoize_with_ttl, BatchProcessor, MemoryOptimizer
    )
    from enhanced_error_handler import (
        EnhancedErrorHandler, CircuitBreaker, ErrorSeverity, ErrorCategory,
        retry_on_failure, handle_errors, circuit_breaker
    )
    from type_definitions import (
        PriceData, FinancialData, SectorAnalysis, validate_symbol,
        validate_price, validate_percentage, validate_score
    )
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some modules not available for testing: {e}")
    MODULES_AVAILABLE = False

class TestPerformanceOptimizer(unittest.TestCase):
    """성능 최적화 모듈 테스트"""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    def test_lru_cache_basic_operations(self):
        """LRU 캐시 기본 동작 테스트"""
        cache = LRUCache(max_size=3, ttl=1.0)
        
        # 기본 저장/조회
        cache.set("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")
        
        # 크기 제한 테스트
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # key1이 제거되어야 함
        
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.get("key4"), "value4")
    
    def test_lru_cache_ttl_expiration(self):
        """LRU 캐시 TTL 만료 테스트"""
        cache = LRUCache(max_size=10, ttl=0.1)  # 0.1초 TTL
        
        cache.set("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")
        
        time.sleep(0.2)  # TTL 초과
        self.assertIsNone(cache.get("key1"))
    
    def test_lru_cache_thread_safety(self):
        """LRU 캐시 스레드 안전성 테스트"""
        cache = LRUCache(max_size=100, ttl=10.0)
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(100):
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    cache.set(key, value)
                    retrieved = cache.get(key)
                    if retrieved != value:
                        errors.append(f"Mismatch: {retrieved} != {value}")
                results.append(f"Worker {worker_id} completed")
            except Exception as e:
                errors.append(f"Worker {worker_id} error: {e}")
        
        # 10개 스레드로 동시 작업
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")
        self.assertEqual(len(results), 10)
    
    def test_performance_monitor(self):
        """성능 모니터 테스트"""
        monitor = PerformanceMonitor()
        
        # 시간 기록
        monitor.record_time("test_operation", 1.5)
        monitor.record_time("test_operation", 2.0)
        monitor.record_time("test_operation", 0.5)
        
        stats = monitor.get_stats("test_operation")
        self.assertEqual(stats['count'], 3)
        self.assertAlmostEqual(stats['avg'], 1.33, places=1)
        self.assertEqual(stats['min'], 0.5)
        self.assertEqual(stats['max'], 2.0)
        self.assertEqual(stats['total'], 4.0)
    
    def test_timed_operation_decorator(self):
        """시간 측정 데코레이터 테스트"""
        monitor = PerformanceMonitor()
        
        @timed_operation("test_function")
        def test_function(delay=0.1):
            time.sleep(delay)
            return "success"
        
        result = test_function(0.1)
        self.assertEqual(result, "success")
        
        stats = monitor.get_stats("test_function")
        self.assertEqual(stats['count'], 1)
        self.assertGreater(stats['avg'], 0.1)
    
    def test_memoize_with_ttl(self):
        """TTL 메모이제이션 테스트"""
        call_count = 0
        
        @memoize_with_ttl(ttl=0.1, max_size=10)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # 첫 번째 호출
        result1 = expensive_function(5)
        self.assertEqual(result1, 10)
        self.assertEqual(call_count, 1)
        
        # 두 번째 호출 (캐시에서)
        result2 = expensive_function(5)
        self.assertEqual(result2, 10)
        self.assertEqual(call_count, 1)  # 호출되지 않음
        
        # TTL 만료 후
        time.sleep(0.2)
        result3 = expensive_function(5)
        self.assertEqual(result3, 10)
        self.assertEqual(call_count, 2)  # 다시 호출됨
    
    def test_batch_processor(self):
        """배치 프로세서 테스트"""
        processed_items = []
        
        def processor(items):
            processed_items.extend(items)
        
        batch_processor = BatchProcessor(batch_size=3, max_wait_time=0.1)
        batch_processor.set_processor(processor)
        
        # 아이템 추가
        for i in range(5):
            batch_processor.add_item(f"item_{i}")
        
        # 배치 크기 도달로 처리
        time.sleep(0.2)  # 대기 시간 초과
        batch_processor.flush()  # 남은 아이템 처리
        
        self.assertEqual(len(processed_items), 5)
        self.assertIn("item_0", processed_items)
        self.assertIn("item_4", processed_items)

class TestEnhancedErrorHandler(unittest.TestCase):
    """향상된 에러 핸들러 테스트"""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    def test_circuit_breaker_closed_state(self):
        """회로 차단기 CLOSED 상태 테스트"""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0)
        breaker = CircuitBreaker(config)
        
        def success_function():
            return "success"
        
        # 정상 동작
        result = breaker.call(success_function)
        self.assertEqual(result, "success")
        self.assertEqual(breaker.state, CircuitState.CLOSED)
    
    def test_circuit_breaker_open_state(self):
        """회로 차단기 OPEN 상태 테스트"""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
        breaker = CircuitBreaker(config)
        
        def failing_function():
            raise ValueError("Test error")
        
        # 실패로 인한 OPEN 상태
        for _ in range(3):
            try:
                breaker.call(failing_function)
            except ValueError:
                pass
        
        self.assertEqual(breaker.state, CircuitState.OPEN)
        
        # OPEN 상태에서 호출 시 예외 발생
        with self.assertRaises(Exception) as context:
            breaker.call(failing_function)
        self.assertIn("Circuit breaker is OPEN", str(context.exception))
    
    def test_circuit_breaker_half_open_state(self):
        """회로 차단기 HALF_OPEN 상태 테스트"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1, success_threshold=2)
        breaker = CircuitBreaker(config)
        
        def failing_function():
            raise ValueError("Test error")
        
        def success_function():
            return "success"
        
        # 실패로 OPEN 상태로 전환
        try:
            breaker.call(failing_function)
        except ValueError:
            pass
        
        self.assertEqual(breaker.state, CircuitState.OPEN)
        
        # 복구 시간 대기
        time.sleep(0.2)
        
        # HALF_OPEN 상태에서 성공
        result = breaker.call(success_function)
        self.assertEqual(result, "success")
        self.assertEqual(breaker.state, CircuitState.HALF_OPEN)
        
        # 성공 임계값 도달로 CLOSED 상태로 전환
        result = breaker.call(success_function)
        self.assertEqual(result, "success")
        self.assertEqual(breaker.state, CircuitState.CLOSED)
    
    def test_retry_decorator(self):
        """재시도 데코레이터 테스트"""
        call_count = 0
        
        @retry_on_failure(config=RetryConfig(max_retries=2, base_delay=0.01))
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = flaky_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_error_statistics(self):
        """에러 통계 테스트"""
        handler = EnhancedErrorHandler()
        
        # 에러 기록
        context1 = ErrorContext(
            operation="test_op1",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.API
        )
        context2 = ErrorContext(
            operation="test_op2",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.NETWORK
        )
        
        handler.handle_error(context1, ValueError("Test error 1"))
        handler.handle_error(context2, ConnectionError("Test error 2"))
        
        stats = handler.statistics.get_stats()
        self.assertGreater(stats['total_errors'], 0)
        self.assertIn('api_medium', stats['by_category_severity'])
        self.assertIn('network_high', stats['by_category_severity'])

class TestTypeDefinitions(unittest.TestCase):
    """타입 정의 테스트"""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    def test_price_data_validation(self):
        """PriceData 검증 테스트"""
        # 유효한 데이터
        price_data = PriceData(
            current_price=1000.0,
            w52_high=1200.0,
            w52_low=800.0,
            per=15.0,
            pbr=1.5
        )
        self.assertEqual(price_data.current_price, 1000.0)
        
        # 잘못된 데이터 (52주 고가 < 저가)
        with self.assertRaises(ValueError):
            PriceData(
                current_price=1000.0,
                w52_high=800.0,
                w52_low=1200.0
            )
    
    def test_financial_data_validation(self):
        """FinancialData 검증 테스트"""
        financial_data = FinancialData(
            roe=15.0,
            roa=10.0,
            debt_ratio=30.0
        )
        self.assertEqual(financial_data.roe, 15.0)
    
    def test_sector_analysis_validation(self):
        """SectorAnalysis 검증 테스트"""
        sector_analysis = SectorAnalysis(
            grade=Grade.A,
            total_score=85.0,
            is_leader=True
        )
        self.assertEqual(sector_analysis.grade, Grade.A)
        self.assertEqual(sector_analysis.total_score, 85.0)
    
    def test_validation_functions(self):
        """검증 함수 테스트"""
        # 종목 코드 검증
        self.assertTrue(validate_symbol("005930"))
        self.assertFalse(validate_symbol(""))
        self.assertFalse(validate_symbol("12345678901"))  # 너무 긴 코드
        
        # 가격 검증
        self.assertTrue(validate_price(1000.0))
        self.assertTrue(validate_price(0))
        self.assertFalse(validate_price(-100.0))
        self.assertTrue(validate_price(None))
        
        # 퍼센트 검증
        self.assertTrue(validate_percentage(50.0))
        self.assertTrue(validate_percentage(0))
        self.assertTrue(validate_percentage(100))
        self.assertFalse(validate_percentage(-10))
        self.assertFalse(validate_percentage(150))
        
        # 점수 검증
        self.assertTrue(validate_score(75.0))
        self.assertTrue(validate_score(0))
        self.assertTrue(validate_score(100))
        self.assertFalse(validate_score(-10))
        self.assertFalse(validate_score(150))

class TestMemoryOptimization(unittest.TestCase):
    """메모리 최적화 테스트"""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    def test_memory_usage_tracking(self):
        """메모리 사용량 추적 테스트"""
        memory_usage = MemoryOptimizer.get_memory_usage()
        
        self.assertIn('rss', memory_usage)
        self.assertIn('vms', memory_usage)
        self.assertIn('percent', memory_usage)
        self.assertGreater(memory_usage['rss'], 0)
        self.assertGreater(memory_usage['vms'], 0)
    
    def test_dataframe_memory_optimization(self):
        """DataFrame 메모리 최적화 테스트"""
        # 큰 DataFrame 생성
        df = pd.DataFrame({
            'int_col': np.random.randint(0, 1000, 10000),
            'float_col': np.random.random(10000),
            'str_col': [f'string_{i}' for i in range(10000)]
        })
        
        original_memory = df.memory_usage(deep=True).sum()
        
        # 메모리 최적화
        MemoryOptimizer.optimize_dataframe_memory(df)
        
        optimized_memory = df.memory_usage(deep=True).sum()
        
        # 메모리 사용량이 줄어들었는지 확인
        self.assertLessEqual(optimized_memory, original_memory)

class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    def test_analyzer_initialization(self):
        """분석기 초기화 테스트"""
        analyzer = EnhancedIntegratedAnalyzer()
        self.assertIsNotNone(analyzer)
        self.assertIsNotNone(analyzer.config_manager)
        
        # 정리
        analyzer.close()
    
    def test_analyzer_with_mock_data(self):
        """모의 데이터로 분석기 테스트"""
        analyzer = EnhancedIntegratedAnalyzer()
        
        # 모의 데이터로 단일 종목 분석 테스트
        with patch.object(analyzer, '_load_kospi_data'):
            result = analyzer.analyze_single_stock("005930", "삼성전자")
            
            self.assertIsInstance(result, AnalysisResult)
            self.assertEqual(result.symbol, "005930")
            self.assertEqual(result.name, "삼성전자")
        
        # 정리
        analyzer.close()
    
    def test_performance_under_load(self):
        """부하 상태에서의 성능 테스트"""
        analyzer = EnhancedIntegratedAnalyzer()
        
        start_time = time.time()
        
        # 여러 종목 동시 분석
        symbols = ["005930", "000660", "035420", "207940", "006400"]
        results = []
        
        for symbol in symbols:
            with patch.object(analyzer, '_load_kospi_data'):
                result = analyzer.analyze_single_stock(symbol, f"종목_{symbol}")
                results.append(result)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 성능 검증 (5개 종목이 10초 이내에 처리되어야 함)
        self.assertLess(duration, 10.0)
        self.assertEqual(len(results), 5)
        
        # 정리
        analyzer.close()

class TestMemoryLeaks(unittest.TestCase):
    """메모리 누수 테스트"""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    def test_cache_memory_cleanup(self):
        """캐시 메모리 정리 테스트"""
        cache = LRUCache(max_size=100, ttl=0.1)
        
        # 많은 데이터 추가
        for i in range(200):
            cache.set(f"key_{i}", f"value_{i}" * 100)
        
        # TTL 만료 대기
        time.sleep(0.2)
        
        # 캐시 정리
        cache.clear()
        
        # 메모리 정리 강제 실행
        gc.collect()
        
        # 캐시가 비어있는지 확인
        self.assertEqual(cache.size(), 0)
    
    def test_analyzer_memory_cleanup(self):
        """분석기 메모리 정리 테스트"""
        initial_objects = len(gc.get_objects())
        
        # 여러 분석기 인스턴스 생성/삭제
        for _ in range(10):
            analyzer = EnhancedIntegratedAnalyzer()
            analyzer.close()
            del analyzer
        
        # 가비지 컬렉션 강제 실행
        gc.collect()
        
        final_objects = len(gc.get_objects())
        
        # 객체 수가 크게 증가하지 않았는지 확인
        object_increase = final_objects - initial_objects
        self.assertLess(object_increase, 1000)  # 임계값 설정

def run_comprehensive_tests():
    """포괄적인 테스트 실행"""
    print("포괄적인 테스트 스위트 실행 중...")
    
    # 테스트 스위트 생성
    test_suite = unittest.TestSuite()
    
    # 테스트 클래스들 추가
    test_classes = [
        TestPerformanceOptimizer,
        TestEnhancedErrorHandler,
        TestTypeDefinitions,
        TestMemoryOptimization,
        TestIntegration,
        TestMemoryLeaks
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 결과 요약
    print(f"\n테스트 결과 요약:")
    print(f"   총 테스트: {result.testsRun}")
    print(f"   성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   실패: {len(result.failures)}")
    print(f"   오류: {len(result.errors)}")
    
    if result.failures:
        print(f"\n실패한 테스트:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print(f"\n오류가 발생한 테스트:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n성공률: {success_rate:.1f}%")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
