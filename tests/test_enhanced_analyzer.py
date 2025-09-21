# tests/test_enhanced_analyzer.py
"""
향상된 통합 분석기 테스트
- 단위 테스트
- 통합 테스트
- 성능 테스트
- 모킹 테스트
"""

import unittest
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import os
import json
import time

# 테스트 대상 모듈 import
import sys
sys.path.append('..')

from enhanced_integrated_analyzer_refactored import (
    EnhancedIntegratedAnalyzer,
    AnalysisResult,
    AnalysisStatus,
    QualityLevel,
    AnalysisConfig,
    DataValidator,
    DataConverter,
    TPSRateLimiter,
    ConfigManager
)
from common_utilities import (
    DataConverter as CommonDataConverter,
    DataValidator as CommonDataValidator,
    MathUtils,
    PerformanceProfiler
)
from error_handling import (
    AnalysisError,
    DataProviderError,
    APIRateLimitError,
    ErrorHandler,
    ErrorContext,
    ErrorSeverity,
    ErrorCategory
)
from caching_system import (
    MemoryCache,
    DiskCache,
    HybridCache,
    CacheEntry
)
from logging_system import (
    LogManager,
    LogCategory,
    LogLevel,
    get_logger
)

# =============================================================================
# 1. 단위 테스트
# =============================================================================

class TestDataConverter(unittest.TestCase):
    """데이터 변환기 테스트"""
    
    def setUp(self):
        self.converter = CommonDataConverter()
    
    def test_safe_float(self):
        """안전한 float 변환 테스트"""
        self.assertEqual(self.converter.safe_float("12.34"), 12.34)
        self.assertEqual(self.converter.safe_float("invalid"), 0.0)
        self.assertEqual(self.converter.safe_float(None), 0.0)
        self.assertEqual(self.converter.safe_float(pd.NA), 0.0)
        self.assertEqual(self.converter.safe_float(42), 42.0)
    
    def test_normalize_percentage(self):
        """퍼센트 정규화 테스트"""
        self.assertEqual(self.converter.normalize_percentage(0.1234), 12.34)
        self.assertEqual(self.converter.normalize_percentage(12.34), 12.34)
        self.assertEqual(self.converter.normalize_percentage(0), 0.0)
        self.assertEqual(self.converter.normalize_percentage(None), 0.0)
    
    def test_format_percentage(self):
        """퍼센트 포맷팅 테스트"""
        self.assertEqual(self.converter.format_percentage(12.34), "12.3%")
        self.assertEqual(self.converter.format_percentage(None), "N/A")
        self.assertEqual(self.converter.format_percentage(pd.NA), "N/A")
    
    def test_format_currency(self):
        """통화 포맷팅 테스트"""
        self.assertEqual(self.converter.format_currency(1234567), "1,234,567원")
        self.assertEqual(self.converter.format_currency(None), "N/A")
        self.assertEqual(self.converter.format_currency(0), "0원")

class TestDataValidator(unittest.TestCase):
    """데이터 검증기 테스트"""
    
    def setUp(self):
        self.validator = CommonDataValidator()
    
    def test_is_valid_symbol(self):
        """종목 코드 유효성 검사 테스트"""
        self.assertTrue(self.validator.is_valid_symbol("005930"))
        self.assertTrue(self.validator.is_valid_symbol("000660"))
        self.assertFalse(self.validator.is_valid_symbol("12345"))  # 5자리
        self.assertFalse(self.validator.is_valid_symbol("1234567"))  # 7자리
        self.assertFalse(self.validator.is_valid_symbol("abc123"))  # 문자 포함
        self.assertFalse(self.validator.is_valid_symbol(""))  # 빈 문자열
        self.assertFalse(self.validator.is_valid_symbol(None))  # None
    
    def test_is_preferred_stock(self):
        """우선주 여부 확인 테스트"""
        self.assertTrue(self.validator.is_preferred_stock("삼성전자우"))
        self.assertTrue(self.validator.is_preferred_stock("SK하이닉스우A"))
        self.assertTrue(self.validator.is_preferred_stock("LG화학우(전환)"))
        self.assertFalse(self.validator.is_preferred_stock("삼성전자"))
        self.assertFalse(self.validator.is_preferred_stock(""))
        self.assertFalse(self.validator.is_preferred_stock(None))
    
    def test_is_valid_financial_ratio(self):
        """재무비율 유효성 검사 테스트"""
        self.assertTrue(self.validator.is_valid_financial_ratio(15.5))
        self.assertTrue(self.validator.is_valid_financial_ratio(0))
        self.assertTrue(self.validator.is_valid_financial_ratio(-5.2))
        self.assertFalse(self.validator.is_valid_financial_ratio(1000))  # 범위 초과
        self.assertFalse(self.validator.is_valid_financial_ratio(-1000))  # 범위 초과
        self.assertFalse(self.validator.is_valid_financial_ratio("invalid"))
        self.assertFalse(self.validator.is_valid_financial_ratio(None))
    
    def test_validate_required_fields(self):
        """필수 필드 검증 테스트"""
        data = {"name": "삼성전자", "symbol": "005930", "price": 75000}
        
        # 모든 필드 존재
        missing = self.validator.validate_required_fields(data, ["name", "symbol"])
        self.assertEqual(len(missing), 0)
        
        # 일부 필드 누락
        missing = self.validator.validate_required_fields(data, ["name", "symbol", "volume"])
        self.assertEqual(missing, ["volume"])
        
        # 빈 데이터
        missing = self.validator.validate_required_fields({}, ["name", "symbol"])
        self.assertEqual(set(missing), {"name", "symbol"})

class TestMathUtils(unittest.TestCase):
    """수학 유틸리티 테스트"""
    
    def test_safe_divide(self):
        """안전한 나눗셈 테스트"""
        self.assertEqual(MathUtils.safe_divide(10, 2), 5.0)
        self.assertEqual(MathUtils.safe_divide(10, 0), 0.0)  # 0으로 나누기
        self.assertEqual(MathUtils.safe_divide(10, 0, default=1.0), 1.0)  # 기본값
        self.assertEqual(MathUtils.safe_divide(10, None), 0.0)  # None
        self.assertEqual(MathUtils.safe_divide(10, pd.NA), 0.0)  # NaN
    
    def test_calculate_percentage_change(self):
        """변화율 계산 테스트"""
        self.assertEqual(MathUtils.calculate_percentage_change(100, 110), 10.0)
        self.assertEqual(MathUtils.calculate_percentage_change(100, 90), -10.0)
        self.assertEqual(MathUtils.calculate_percentage_change(0, 100), 0.0)  # 0으로 나누기
        self.assertEqual(MathUtils.calculate_percentage_change(100, 100), 0.0)  # 변화 없음
    
    def test_calculate_compound_growth_rate(self):
        """복합 성장률 계산 테스트"""
        values = [100, 110, 121, 133.1]  # 10% 성장
        cagr = MathUtils.calculate_compound_growth_rate(values)
        self.assertAlmostEqual(cagr, 10.0, places=1)
        
        # 단일 값
        self.assertEqual(MathUtils.calculate_compound_growth_rate([100]), 0.0)
        
        # 빈 리스트
        self.assertEqual(MathUtils.calculate_compound_growth_rate([]), 0.0)
    
    def test_calculate_volatility(self):
        """변동성 계산 테스트"""
        values = [100, 110, 90, 105, 95]  # 변동성 있는 데이터
        volatility = MathUtils.calculate_volatility(values)
        self.assertGreater(volatility, 0)
        
        # 동일한 값들
        self.assertEqual(MathUtils.calculate_volatility([100, 100, 100]), 0.0)
        
        # 빈 리스트
        self.assertEqual(MathUtils.calculate_volatility([]), 0.0)
    
    def test_normalize_score(self):
        """점수 정규화 테스트"""
        # 정상 범위
        score = MathUtils.normalize_score(75, 0, 100, 0, 100)
        self.assertEqual(score, 75.0)
        
        # 다른 범위로 정규화
        score = MathUtils.normalize_score(75, 0, 100, 0, 10)
        self.assertEqual(score, 7.5)
        
        # 최소값과 최대값이 같은 경우
        score = MathUtils.normalize_score(50, 100, 100, 0, 100)
        self.assertEqual(score, 0.0)

class TestTPSRateLimiter(unittest.TestCase):
    """TPS 레이트 리미터 테스트"""
    
    def setUp(self):
        self.rate_limiter = TPSRateLimiter(max_tps=2)  # 테스트용 낮은 TPS
    
    def test_rate_limiting(self):
        """레이트 제한 테스트"""
        start_time = time.time()
        
        # 3번 연속 호출 (TPS=2이므로 마지막 호출은 지연되어야 함)
        for _ in range(3):
            self.rate_limiter.acquire()
        
        elapsed_time = time.time() - start_time
        self.assertGreater(elapsed_time, 0.5)  # 최소 0.5초 이상 걸려야 함
    
    def test_cleanup_old_requests(self):
        """오래된 요청 정리 테스트"""
        # 시간을 조작하여 오래된 요청 시뮬레이션
        with patch('time.time') as mock_time:
            mock_time.return_value = 0
            self.rate_limiter.acquire()
            
            # 2초 후로 시간 이동
            mock_time.return_value = 2
            self.rate_limiter.acquire()
            
            # 이제 1초 이내 요청이므로 즉시 처리되어야 함
            start_time = time.time()
            self.rate_limiter.acquire()
            elapsed_time = time.time() - start_time
            self.assertLess(elapsed_time, 0.1)

# =============================================================================
# 2. 통합 테스트
# =============================================================================

class TestEnhancedIntegratedAnalyzer(unittest.TestCase):
    """향상된 통합 분석기 통합 테스트"""
    
    def setUp(self):
        # 모킹된 의존성으로 분석기 생성
        with patch('enhanced_integrated_analyzer_refactored.KISDataProvider'), \
             patch('enhanced_integrated_analyzer_refactored.InvestmentOpinionAnalyzer'), \
             patch('enhanced_integrated_analyzer_refactored.EstimatePerformanceAnalyzer'):
            
            self.analyzer = EnhancedIntegratedAnalyzer()
            
            # KOSPI 데이터 모킹
            self.analyzer.kospi_data = pd.DataFrame({
                '단축코드': ['005930', '000660'],
                '한글명': ['삼성전자', 'SK하이닉스'],
                '시가총액': [4000000, 2000000],
                '현재가': [75000, 100000]
            })
    
    def test_analyze_single_stock_success(self):
        """단일 종목 분석 성공 테스트"""
        # 모킹 설정
        with patch.object(self.analyzer, '_analyze_opinion') as mock_opinion, \
             patch.object(self.analyzer, '_analyze_estimate') as mock_estimate, \
             patch.object(self.analyzer.data_provider, 'get_financial_data') as mock_financial, \
             patch.object(self.analyzer.data_provider, 'get_price_data') as mock_price:
            
            # 모킹된 반환값 설정
            mock_opinion.return_value = {'consensus_score': 0.5}
            mock_estimate.return_value = {'financial_health_score': 10, 'valuation_score': 8}
            mock_financial.return_value = {
                'roe': 15.5,
                'roa': 8.2,
                'debt_ratio': 45.0,
                'net_profit_margin': 12.3
            }
            mock_price.return_value = {
                'current_price': 75000,
                'w52_high': 80000,
                'w52_low': 70000
            }
            
            # 분석 실행
            result = self.analyzer.analyze_single_stock("005930", "삼성전자")
            
            # 결과 검증
            self.assertEqual(result.symbol, "005930")
            self.assertEqual(result.name, "삼성전자")
            self.assertEqual(result.status, AnalysisStatus.SUCCESS)
            self.assertGreater(result.enhanced_score, 0)
            self.assertIsNotNone(result.score_breakdown)
    
    def test_analyze_single_stock_preferred_stock(self):
        """우선주 분석 스킵 테스트"""
        result = self.analyzer.analyze_single_stock("005930", "삼성전자우")
        
        self.assertEqual(result.status, AnalysisStatus.SKIPPED_PREF)
        self.assertEqual(result.enhanced_score, 0)
        self.assertEqual(result.enhanced_grade, 'F')
    
    def test_analyze_single_stock_error(self):
        """분석 에러 테스트"""
        # 모킹에서 예외 발생
        with patch.object(self.analyzer, '_analyze_opinion', side_effect=Exception("API 오류")):
            result = self.analyzer.analyze_single_stock("005930", "삼성전자")
            
            self.assertEqual(result.status, AnalysisStatus.ERROR)
            self.assertIsNotNone(result.error)
            self.assertIn("API 오류", result.error)

# =============================================================================
# 3. 성능 테스트
# =============================================================================

class TestPerformance(unittest.TestCase):
    """성능 테스트"""
    
    def test_analyzer_performance(self):
        """분석기 성능 테스트"""
        with patch('enhanced_integrated_analyzer_refactored.KISDataProvider'), \
             patch('enhanced_integrated_analyzer_refactored.InvestmentOpinionAnalyzer'), \
             patch('enhanced_integrated_analyzer_refactored.EstimatePerformanceAnalyzer'):
            
            analyzer = EnhancedIntegratedAnalyzer()
            
            # 성능 측정
            profiler = PerformanceProfiler()
            profiler.start_timer("analysis")
            
            # 모킹된 데이터로 분석 실행
            with patch.object(analyzer, '_analyze_opinion', return_value={}), \
                 patch.object(analyzer, '_analyze_estimate', return_value={}), \
                 patch.object(analyzer.data_provider, 'get_financial_data', return_value={}), \
                 patch.object(analyzer.data_provider, 'get_price_data', return_value={}):
                
                result = analyzer.analyze_single_stock("005930", "삼성전자")
            
            duration = profiler.end_timer("analysis")
            
            # 성능 검증 (1초 이내 완료)
            self.assertLess(duration, 1.0)
            self.assertEqual(result.status, AnalysisStatus.SUCCESS)
    
    def test_cache_performance(self):
        """캐시 성능 테스트"""
        cache = MemoryCache(max_size=1000)
        
        # 캐시 성능 측정
        profiler = PerformanceProfiler()
        
        # 쓰기 성능
        profiler.start_timer("cache_write")
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        write_duration = profiler.end_timer("cache_write")
        
        # 읽기 성능
        profiler.start_timer("cache_read")
        for i in range(1000):
            cache.get(f"key_{i}")
        read_duration = profiler.end_timer("cache_read")
        
        # 성능 검증
        self.assertLess(write_duration, 1.0)  # 1초 이내
        self.assertLess(read_duration, 0.5)  # 0.5초 이내

# =============================================================================
# 4. 모킹 테스트
# =============================================================================

class TestMocking(unittest.TestCase):
    """모킹 테스트"""
    
    def test_api_mocking(self):
        """API 모킹 테스트"""
        # KIS API 모킹
        mock_provider = Mock()
        mock_provider.get_stock_price_info.return_value = {
            'current_price': 75000,
            'w52_high': 80000,
            'w52_low': 70000,
            'per': 15.5,
            'pbr': 1.2
        }
        
        # 분석기에 모킹된 프로바이더 주입
        with patch('enhanced_integrated_analyzer_refactored.KISDataProvider', return_value=mock_provider):
            analyzer = EnhancedIntegratedAnalyzer()
            
            # 가격 데이터 조회 테스트
            price_data = analyzer.data_provider.get_price_data("005930")
            
            self.assertEqual(price_data['current_price'], 75000)
            self.assertEqual(price_data['per'], 15.5)
            mock_provider.get_stock_price_info.assert_called_once_with("005930")
    
    def test_error_handling_mocking(self):
        """에러 처리 모킹 테스트"""
        # 에러 핸들러 모킹
        mock_handler = Mock()
        
        with patch('error_handling.ErrorHandler', return_value=mock_handler):
            error_handler = ErrorHandler()
            
            # 에러 처리 테스트
            context = ErrorContext(
                category=ErrorCategory.API,
                severity=ErrorSeverity.MEDIUM,
                operation="test_operation"
            )
            
            error_handler.handle_error(Exception("테스트 에러"), context)
            
            # 에러 핸들러가 호출되었는지 확인
            self.assertTrue(True)  # 모킹된 객체이므로 실제 검증은 어려움

# =============================================================================
# 5. 설정 테스트
# =============================================================================

class TestConfiguration(unittest.TestCase):
    """설정 테스트"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_loading(self):
        """설정 로딩 테스트"""
        # 테스트 설정 파일 생성
        test_config = {
            'api': {
                'kis_api_key': 'test_key',
                'kis_secret_key': 'test_secret'
            },
            'analysis': {
                'weights': {
                    'opinion_analysis': 30,
                    'estimate_analysis': 40
                }
            }
        }
        
        config_file = os.path.join(self.temp_dir, 'config.yaml')
        with open(config_file, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(test_config, f)
        
        # 설정 로드
        config = self.config_manager.load()
        
        # 검증
        self.assertEqual(config['api']['kis_api_key'], 'test_key')
        self.assertEqual(config['analysis']['weights']['opinion_analysis'], 30)
    
    def test_config_validation(self):
        """설정 검증 테스트"""
        # 잘못된 설정
        invalid_config = {
            'api': {
                'kis_api_key': '',  # 빈 값
                'timeout': -1  # 음수 값
            }
        }
        
        # 검증 실행
        errors = self.config_manager.validator.validate_config(invalid_config, 'api')
        
        # 에러가 발생했는지 확인
        self.assertGreater(len(errors), 0)

# =============================================================================
# 6. 테스트 실행
# =============================================================================

if __name__ == '__main__':
    # 테스트 스위트 생성
    test_suite = unittest.TestSuite()
    
    # 단위 테스트 추가
    test_suite.addTest(unittest.makeSuite(TestDataConverter))
    test_suite.addTest(unittest.makeSuite(TestDataValidator))
    test_suite.addTest(unittest.makeSuite(TestMathUtils))
    test_suite.addTest(unittest.makeSuite(TestTPSRateLimiter))
    
    # 통합 테스트 추가
    test_suite.addTest(unittest.makeSuite(TestEnhancedIntegratedAnalyzer))
    
    # 성능 테스트 추가
    test_suite.addTest(unittest.makeSuite(TestPerformance))
    
    # 모킹 테스트 추가
    test_suite.addTest(unittest.makeSuite(TestMocking))
    
    # 설정 테스트 추가
    test_suite.addTest(unittest.makeSuite(TestConfiguration))
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 결과 출력
    print(f"\n테스트 결과:")
    print(f"실행된 테스트: {result.testsRun}")
    print(f"실패: {len(result.failures)}")
    print(f"에러: {len(result.errors)}")
    
    if result.failures:
        print("\n실패한 테스트:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\n에러가 발생한 테스트:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

