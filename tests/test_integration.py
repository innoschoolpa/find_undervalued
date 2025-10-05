"""
통합 테스트

전체 시스템의 통합 기능을 테스트합니다.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer
from config_manager import ConfigManager
from metrics import MetricsCollector


class TestIntegration:
    """통합 테스트 클래스"""
    
    def setup_method(self):
        """테스트 설정"""
        self.config_manager = ConfigManager()
        self.metrics_collector = MetricsCollector()
        
        # 테스트용 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        
        # 테스트용 설정
        self.test_config = {
            'analysis_timeout': 60,
            'max_concurrent_analyses': 2,
            'min_data_quality_score': 50.0,
            'enable_metrics': True
        }
    
    def teardown_method(self):
        """테스트 정리"""
        # 임시 디렉토리 정리
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_analyzer_initialization(self):
        """분석기 초기화 테스트"""
        analyzer = EnhancedIntegratedAnalyzer()
        
        assert analyzer is not None
        assert analyzer.config_manager == self.config_manager
        assert analyzer.metrics_collector == self.metrics_collector
    
    def test_config_manager_integration(self):
        """설정 관리자 통합 테스트"""
        # 설정값 설정
        for key, value in self.test_config.items():
            self.config_manager.set(key, value)
        
        # 설정값 검증
        for key, expected_value in self.test_config.items():
            assert self.config_manager.get(key) == expected_value
        
        # 설정 유효성 확인
        assert self.config_manager.is_valid() == True
    
    def test_metrics_collector_integration(self):
        """메트릭 수집기 통합 테스트"""
        # 메트릭 기록
        self.metrics_collector.record_api_call(success=True)
        self.metrics_collector.record_api_call(success=False)
        self.metrics_collector.record_api_call(success=False)
        self.metrics_collector.record_analysis_duration(1.5)
        
        # 메트릭 조회
        stats = self.metrics_collector.get_summary()
        
        assert stats['api_calls']['total'] == 3
        assert stats['api_calls']['error'] == 2
        assert stats['api_calls']['success'] == 1
        assert stats['avg_analysis_duration'] == 1.5
    
    def test_end_to_end_analysis_flow(self):
        """엔드투엔드 분석 플로우 테스트"""
        # 모의 데이터 제공자 설정
        mock_provider = Mock()
        mock_provider.get_financial_data.return_value = {
            'revenue': 1000000000,
            'net_income': 100000000,
            'total_assets': 5000000000,
            'total_debt': 1000000000,
            'roe': 12.5,
            'roa': 8.0,
            'debt_ratio': 30.0
        }
        
        mock_provider.get_price_data.return_value = {
            'current_price': 1500,
            'market_cap': 15000000000,
            'volume': 1000000,
            'high_52w': 2000,
            'low_52w': 1200,
            'per': 15.0,
            'pbr': 1.5
        }
        
        # 분석기 초기화
        analyzer = EnhancedIntegratedAnalyzer()
        
        # 분석 실행 (모의 데이터 사용)
        with patch.object(analyzer, 'data_provider', mock_provider):
            result = analyzer.analyze_single_stock('TEST001')
        
        # 결과 검증
        assert result is not None
        assert 'symbol' in result
        assert 'status' in result
        assert 'enhanced_score' in result
        assert 'enhanced_grade' in result
    
    def test_error_handling_integration(self):
        """에러 처리 통합 테스트"""
        # 잘못된 설정으로 분석기 초기화
        invalid_config = ConfigManager()
        invalid_config.set('api_timeout', -1)  # 잘못된 값
        
        # 분석기는 여전히 초기화되어야 함 (에러 처리)
        analyzer = EnhancedIntegratedAnalyzer(
            config_manager=invalid_config,
            metrics_collector=self.metrics_collector
        )
        
        assert analyzer is not None
        
        # 잘못된 종목 코드로 분석 시도
        result = analyzer.analyze_single_stock('INVALID')
        
        # 에러가 발생해도 안전하게 처리되어야 함
        assert result is not None
        assert result.get('status') in ['error', 'failed']
    
    def test_concurrent_analysis(self):
        """동시 분석 테스트"""
        import threading
        import time
        
        analyzer = EnhancedIntegratedAnalyzer()
        
        results = []
        errors = []
        
        def analyze_stock(symbol):
            try:
                result = analyzer.analyze_single_stock(symbol)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # 동시 분석 실행
        threads = []
        symbols = ['TEST001', 'TEST002', 'TEST003']
        
        for symbol in symbols:
            thread = threading.Thread(target=analyze_stock, args=(symbol,))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 결과 검증
        assert len(results) == 3
        assert len(errors) == 0
        
        # 각 결과에 필요한 필드가 있는지 확인
        for result in results:
            assert 'symbol' in result
            assert 'status' in result
    
    def test_memory_usage(self):
        """메모리 사용량 테스트"""
        import psutil
        import gc
        
        # 초기 메모리 사용량
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # 여러 분석기 인스턴스 생성
        analyzers = []
        for i in range(10):
            analyzer = EnhancedIntegratedAnalyzer(
                config_manager=self.config_manager,
                metrics_collector=self.metrics_collector
            )
            analyzers.append(analyzer)
        
        # 메모리 사용량 확인
        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory
        
        # 메모리 증가량이 합리적인 범위 내에 있는지 확인
        assert memory_increase < 100 * 1024 * 1024  # 100MB 미만
        
        # 정리
        del analyzers
        gc.collect()
    
    def test_configuration_persistence(self):
        """설정 지속성 테스트"""
        # 설정 파일 경로
        config_file = os.path.join(self.temp_dir, 'test_config.json')
        
        # 설정 내보내기
        result = self.config_manager.export_config(config_file)
        assert result == True
        assert os.path.exists(config_file)
        
        # 새로운 ConfigManager로 설정 가져오기
        new_config_manager = ConfigManager()
        result = new_config_manager.import_config(config_file)
        assert result == True
        
        # 설정이 제대로 복원되었는지 확인
        assert new_config_manager.get('api_timeout') == self.config_manager.get('api_timeout')
        assert new_config_manager.get('max_tps') == self.config_manager.get('max_tps')
    
    def test_metrics_persistence(self):
        """메트릭 지속성 테스트"""
        # 메트릭 기록
        self.metrics_collector.record_api_calls(100)
        self.metrics_collector.record_api_errors(10)
        self.metrics_collector.record_data_processing_time(5.0)
        
        # 메트릭 저장
        metrics_file = os.path.join(self.temp_dir, 'metrics.json')
        self.metrics_collector.save_metrics(metrics_file)
        
        assert os.path.exists(metrics_file)
        
        # 메트릭 로드
        new_metrics_collector = MetricsCollector()
        new_metrics_collector.load_metrics(metrics_file)
        
        # 메트릭이 제대로 복원되었는지 확인
        stats = new_metrics_collector.get_stats()
        assert stats['api_calls']['total'] >= 100
        assert stats['api_calls']['error'] >= 10
        assert stats['data_processing_time']['total_time'] >= 5.0
    
    def test_performance_benchmark(self):
        """성능 벤치마크 테스트"""
        import time
        
        analyzer = EnhancedIntegratedAnalyzer()
        
        # 분석 시간 측정
        start_time = time.time()
        
        # 여러 종목 분석
        symbols = ['TEST001', 'TEST002', 'TEST003', 'TEST004', 'TEST005']
        results = []
        
        for symbol in symbols:
            result = analyzer.analyze_single_stock(symbol)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 성능 검증 (종목당 평균 1초 미만)
        avg_time_per_stock = total_time / len(symbols)
        assert avg_time_per_stock < 1.0
        
        # 결과 검증
        assert len(results) == len(symbols)
        for result in results:
            assert 'symbol' in result
            assert 'status' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
