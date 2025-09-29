#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선사항 테스트
- 스레드 안전성 테스트
- 메모리 누수 방지 테스트
- 예외 처리 표준화 테스트
- 입력 검증 강화 테스트
"""

import unittest
import threading
import time
import gc
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

# 개선된 모듈들 import
try:
    from thread_safe_rate_limiter import ThreadSafeTPSRateLimiter, RateLimitConfig
    from memory_safe_cache import MemorySafeCache, CacheConfig
    from standardized_exception_handler import (
        StandardizedExceptionHandler, ErrorCategory, ErrorSeverity, RetryConfig
    )
    from enhanced_input_validator import EnhancedInputValidator
    IMPROVED_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"개선된 모듈들을 사용할 수 없습니다: {e}")
    IMPROVED_MODULES_AVAILABLE = False

class TestThreadSafety(unittest.TestCase):
    """스레드 안전성 테스트"""
    
    def setUp(self):
        if not IMPROVED_MODULES_AVAILABLE:
            self.skipTest("개선된 모듈들을 사용할 수 없습니다")
    
    def test_rate_limiter_thread_safety(self):
        """Rate Limiter 스레드 안전성 테스트"""
        config = RateLimitConfig(max_tps=10, timeout=5.0)
        rate_limiter = ThreadSafeTPSRateLimiter(config)
        
        results = []
        errors = []
        
        def worker(worker_id: int):
            try:
                for i in range(5):
                    with rate_limiter.acquire():
                        results.append(f"worker_{worker_id}_request_{i}")
                        time.sleep(0.01)  # 짧은 작업 시뮬레이션
            except Exception as e:
                errors.append(f"worker_{worker_id}: {e}")
        
        # 10개 스레드로 동시 실행
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join(timeout=10)
        
        # 결과 검증
        self.assertEqual(len(errors), 0, f"스레드 안전성 오류: {errors}")
        self.assertEqual(len(results), 50, f"예상 결과 수와 다름: {len(results)}")
        
        # 통계 확인
        stats = rate_limiter.get_stats()
        self.assertGreater(stats['total_requests'], 0)
        self.assertLessEqual(stats['current_window_size'], config.max_tps)
    
    def test_cache_thread_safety(self):
        """Cache 스레드 안전성 테스트"""
        config = CacheConfig(max_size=100, default_ttl=60.0)
        cache = MemorySafeCache(config)
        
        results = []
        errors = []
        
        def writer(worker_id: int):
            try:
                for i in range(20):
                    key = f"key_{worker_id}_{i}"
                    value = f"value_{worker_id}_{i}"
                    cache.set(key, value)
                    results.append(f"write_{key}")
            except Exception as e:
                errors.append(f"writer_{worker_id}: {e}")
        
        def reader(worker_id: int):
            try:
                for i in range(20):
                    key = f"key_{worker_id}_{i}"
                    value = cache.get(key)
                    if value:
                        results.append(f"read_{key}")
            except Exception as e:
                errors.append(f"reader_{worker_id}: {e}")
        
        # 5개 쓰기 스레드, 5개 읽기 스레드
        threads = []
        for i in range(5):
            thread = threading.Thread(target=writer, args=(i,))
            threads.append(thread)
            thread.start()
        
        for i in range(5):
            thread = threading.Thread(target=reader, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join(timeout=10)
        
        # 결과 검증
        self.assertEqual(len(errors), 0, f"캐시 스레드 안전성 오류: {errors}")
        
        # 캐시 통계 확인
        stats = cache.get_stats()
        self.assertGreater(stats['size'], 0)
        self.assertLessEqual(stats['size'], config.max_size)

class TestMemorySafety(unittest.TestCase):
    """메모리 안전성 테스트"""
    
    def setUp(self):
        if not IMPROVED_MODULES_AVAILABLE:
            self.skipTest("개선된 모듈들을 사용할 수 없습니다")
    
    def test_cache_memory_limits(self):
        """캐시 메모리 제한 테스트"""
        config = CacheConfig(max_size=10, default_ttl=1.0)  # 1초 TTL
        cache = MemorySafeCache(config)
        
        # 캐시 크기 초과 테스트
        for i in range(15):
            cache.set(f"key_{i}", f"value_{i}")
        
        # 크기 제한 확인
        stats = cache.get_stats()
        self.assertLessEqual(stats['size'], config.max_size)
        
        # TTL 만료 테스트
        time.sleep(1.1)
        cache._cleanup_expired()
        
        # 만료된 엔트리 정리 확인
        stats_after = cache.get_stats()
        self.assertLessEqual(stats_after['size'], stats['size'])
    
    def test_memory_cleanup(self):
        """메모리 정리 테스트"""
        config = CacheConfig(max_size=1000, default_ttl=3600.0)
        cache = MemorySafeCache(config)
        
        # 대량 데이터 추가
        large_data = []
        for i in range(100):
            data = {'id': i, 'data': 'x' * 1000}  # 1KB 데이터
            cache.set(f"large_key_{i}", data)
            large_data.append(data)
        
        # 메모리 사용량 확인
        stats = cache.get_stats()
        self.assertGreater(stats['total_size_bytes'], 0)
        
        # 캐시 정리
        cache.clear()
        
        # 정리 후 확인
        stats_after = cache.get_stats()
        self.assertEqual(stats_after['size'], 0)
        self.assertEqual(stats_after['total_size_bytes'], 0)

class TestExceptionHandling(unittest.TestCase):
    """예외 처리 표준화 테스트"""
    
    def setUp(self):
        if not IMPROVED_MODULES_AVAILABLE:
            self.skipTest("개선된 모듈들을 사용할 수 없습니다")
    
    def test_exception_handler(self):
        """예외 처리기 테스트"""
        from standardized_exception_handler import ErrorContext
        handler = StandardizedExceptionHandler()
        
        # 테스트 예외 발생
        test_error = ValueError("테스트 오류")
        context = ErrorContext(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            operation="test_operation",
            symbol="005930"
        )
        
        # 예외 처리
        result = handler.handle_error(test_error, context)
        self.assertIsNone(result)
        
        # 통계 확인
        stats = handler.get_error_stats()
        self.assertGreater(stats['total_errors'], 0)
        self.assertIn('validation:ValueError', stats['error_counts_by_type'])
    
    def test_retry_mechanism(self):
        """재시도 메커니즘 테스트"""
        handler = StandardizedExceptionHandler()
        
        call_count = 0
        
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("연결 실패")
            return "성공"
        
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1)
        
        # 재시도 실행
        result = handler.retry_with_backoff(failing_function, retry_config)
        
        # 결과 확인
        self.assertEqual(result, "성공")
        self.assertEqual(call_count, 3)
    
    def test_circuit_breaker(self):
        """회로 차단기 테스트"""
        handler = StandardizedExceptionHandler()
        
        @handler.circuit_breaker("test_operation", max_failures=3, timeout=1.0)
        def failing_function():
            raise ConnectionError("연결 실패")
        
        # 연속 실패로 회로 차단기 트리거
        for i in range(5):
            try:
                failing_function()
            except Exception:
                pass
        
        # 회로 차단기 상태 확인
        self.assertIn("test_operation:failing_function", handler._circuit_breakers)
        cb = handler._circuit_breakers["test_operation:failing_function"]
        self.assertEqual(cb['state'], 'open')

class TestInputValidation(unittest.TestCase):
    """입력 검증 강화 테스트"""
    
    def setUp(self):
        if not IMPROVED_MODULES_AVAILABLE:
            self.skipTest("개선된 모듈들을 사용할 수 없습니다")
    
    def test_stock_data_validation(self):
        """주식 데이터 검증 테스트"""
        validator = EnhancedInputValidator()
        
        # 유효한 데이터
        valid_data = {
            'symbol': '005930',
            'name': '삼성전자',
            'current_price': 80000.0,
            'market_cap': 500000000000000,
            'per': 15.5,
            'roe': 12.5
        }
        
        results = validator.validate_stock_data(valid_data)
        error_results = [r for r in results if not r.is_valid and r.severity.value in ['error', 'critical']]
        # 종목 코드 검증 오류가 있는 경우 디버깅 정보 출력
        if error_results:
            print(f"검증 결과: {[r.message for r in results]}")
        self.assertEqual(len(error_results), 0, f"유효한 데이터 검증 실패: {error_results}")
        
        # 무효한 데이터
        invalid_data = {
            'symbol': 'invalid',
            'name': '',
            'current_price': -1000.0,
            'market_cap': -500000000000000,
            'per': -5.0,
            'roe': 150.0
        }
        
        results = validator.validate_stock_data(invalid_data)
        error_results = [r for r in results if not r.is_valid and r.severity.value in ['error', 'critical']]
        self.assertGreater(len(error_results), 0, "무효한 데이터가 검증을 통과했습니다")
    
    def test_api_config_validation(self):
        """API 설정 검증 테스트"""
        validator = EnhancedInputValidator()
        
        # 유효한 설정
        valid_config = {
            'api_key': 'valid_api_key_12345',
            'base_url': 'https://api.example.com',
            'timeout': 30.0
        }
        
        results = validator.validate_api_config(valid_config)
        error_results = [r for r in results if not r.is_valid and r.severity.value in ['error', 'critical']]
        self.assertEqual(len(error_results), 0, f"유효한 API 설정 검증 실패: {error_results}")
        
        # 무효한 설정
        invalid_config = {
            'api_key': 'test_key',  # 너무 짧음
            'base_url': 'invalid_url',
            'timeout': -5.0
        }
        
        results = validator.validate_api_config(invalid_config)
        error_results = [r for r in results if not r.is_valid and r.severity.value in ['error', 'critical']]
        self.assertGreater(len(error_results), 0, "무효한 API 설정이 검증을 통과했습니다")
    
    def test_security_validation(self):
        """보안 검증 테스트"""
        validator = EnhancedInputValidator()
        
        # SQL 인젝션 시도
        malicious_input = "'; DROP TABLE users; --"
        result = validator.security_validator.validate_input_safety(malicious_input)
        self.assertFalse(result.is_valid, "SQL 인젝션 패턴이 감지되지 않았습니다")
        
        # XSS 시도
        xss_input = "<script>alert('xss')</script>"
        result = validator.security_validator.validate_input_safety(xss_input)
        self.assertFalse(result.is_valid, "XSS 패턴이 감지되지 않았습니다")

class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def setUp(self):
        if not IMPROVED_MODULES_AVAILABLE:
            self.skipTest("개선된 모듈들을 사용할 수 없습니다")
    
    def test_analyzer_integration(self):
        """분석기 통합 테스트"""
        try:
            from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer
            
            # 분석기 초기화
            analyzer = EnhancedIntegratedAnalyzer()
            
            # 개선된 모듈들이 사용되는지 확인
            self.assertTrue(hasattr(analyzer, 'exception_handler'))
            self.assertTrue(hasattr(analyzer, 'input_validator'))
            self.assertTrue(hasattr(analyzer, 'cache'))
            
            # 리소스 정리
            analyzer.close()
            
        except ImportError:
            self.skipTest("enhanced_integrated_analyzer_refactored를 import할 수 없습니다")
    
    def test_performance_improvement(self):
        """성능 개선 테스트"""
        config = RateLimitConfig(max_tps=20, timeout=5.0)
        rate_limiter = ThreadSafeTPSRateLimiter(config)
        
        start_time = time.time()
        
        # 병렬 요청 처리
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(50):
                future = executor.submit(self._make_request, rate_limiter, i)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"요청 실패: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 성능 확인
        self.assertGreater(len(results), 40, "너무 많은 요청이 실패했습니다")
        self.assertLess(total_time, 10.0, "처리 시간이 너무 깁니다")
        
        # 통계 확인
        stats = rate_limiter.get_stats()
        self.assertGreater(stats['total_requests'], 0)
    
    def _make_request(self, rate_limiter, request_id):
        """요청 시뮬레이션"""
        with rate_limiter.acquire():
            time.sleep(0.01)  # 짧은 작업 시뮬레이션
            return f"request_{request_id}_completed"

def run_improvement_tests():
    """개선사항 테스트 실행"""
    if not IMPROVED_MODULES_AVAILABLE:
        print("개선된 모듈들을 사용할 수 없습니다.")
        print("다음 모듈들이 필요합니다:")
        print("- thread_safe_rate_limiter.py")
        print("- memory_safe_cache.py")
        print("- standardized_exception_handler.py")
        print("- enhanced_input_validator.py")
        return False
    
    print("개선사항 테스트 시작...")
    
    # 테스트 스위트 생성
    test_suite = unittest.TestSuite()
    
    # 테스트 클래스들 추가
    test_classes = [
        TestThreadSafety,
        TestMemorySafety,
        TestExceptionHandling,
        TestInputValidation,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 결과 요약
    print("\n" + "="*50)
    print("테스트 결과 요약")
    print("="*50)
    print(f"총 테스트: {result.testsRun}")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"실패: {len(result.failures)}")
    print(f"오류: {len(result.errors)}")
    
    if result.failures:
        print("\n실패한 테스트:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print("\n오류가 발생한 테스트:")
        for test, traceback in result.errors:
            lines = traceback.split('\\n')
            error_line = lines[-2] if len(lines) > 1 else "알 수 없는 오류"
            print(f"- {test}: {error_line}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\n성공률: {success_rate:.1f}%")
    
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == "__main__":
    success = run_improvement_tests()
    sys.exit(0 if success else 1)
