"""
ConfigManager 단위 테스트

설정 관리자의 기능을 테스트합니다.
"""

import pytest
import os
from unittest.mock import patch, mock_open
from config_manager import ConfigManager


class TestConfigManager:
    """ConfigManager 테스트 클래스"""
    
    def setup_method(self):
        """테스트 설정"""
        self.config_manager = ConfigManager()
    
    def test_default_config_loading(self):
        """기본 설정 로딩 테스트"""
        # 기본값들이 제대로 설정되었는지 확인
        assert self.config_manager.get('kis_api_base_url') == 'https://openapi.koreainvestment.com:9443'
        assert self.config_manager.get('api_timeout') == 30
        assert self.config_manager.get('cache_ttl_seconds') == 3600
        assert self.config_manager.get('max_tps') == 10
        assert self.config_manager.get('log_level') == 'INFO'
        assert self.config_manager.get('min_data_quality_score') == 70.0
    
    def test_get_set_operations(self):
        """설정값 조회/설정 테스트"""
        # 설정값 설정
        assert self.config_manager.set('test_key', 'test_value') == True
        assert self.config_manager.get('test_key') == 'test_value'
        
        # 기본값과 함께 조회
        assert self.config_manager.get('nonexistent_key', 'default') == 'default'
        
        # None 조회
        assert self.config_manager.get('nonexistent_key') == None
    
    def test_type_conversion(self):
        """타입 변환 테스트"""
        # 정수 변환
        self.config_manager.set('int_value', 42)
        assert self.config_manager.get('int_value') == 42
        assert isinstance(self.config_manager.get('int_value'), int)
        
        # 실수 변환
        self.config_manager.set('float_value', 3.14)
        assert self.config_manager.get('float_value') == 3.14
        assert isinstance(self.config_manager.get('float_value'), float)
        
        # 불린 변환
        self.config_manager.set('bool_value', True)
        assert self.config_manager.get('bool_value') == True
        assert isinstance(self.config_manager.get('bool_value'), bool)
        
        # 문자열 변환
        self.config_manager.set('str_value', 'hello')
        assert self.config_manager.get('str_value') == 'hello'
        assert isinstance(self.config_manager.get('str_value'), str)
    
    def test_validation(self):
        """설정값 검증 테스트"""
        # 유효한 값들
        assert self.config_manager.set('api_timeout', 60) == True
        assert self.config_manager.set('max_tps', 20) == True
        assert self.config_manager.set('log_level', 'DEBUG') == True
        assert self.config_manager.set('min_data_quality_score', 80.0) == True
        
        # 유효하지 않은 값들
        assert self.config_manager.set('api_timeout', -1) == False  # 음수
        assert self.config_manager.set('max_tps', 2000) == False    # 범위 초과
        assert self.config_manager.set('log_level', 'INVALID') == False  # 잘못된 레벨
        assert self.config_manager.set('min_data_quality_score', 150.0) == False  # 범위 초과
    
    def test_config_sections(self):
        """설정 섹션별 조회 테스트"""
        # API 설정
        api_config = self.config_manager.get_api_config()
        assert 'kis_api_base_url' in api_config
        assert 'api_timeout' in api_config
        assert 'api_retry_count' in api_config
        
        # 캐시 설정
        cache_config = self.config_manager.get_cache_config()
        assert 'cache_ttl_seconds' in cache_config
        assert 'cache_max_size' in cache_config
        assert 'cache_enabled' in cache_config
        
        # 로깅 설정
        logging_config = self.config_manager.get_logging_config()
        assert 'log_level' in logging_config
        assert 'log_format' in logging_config
        assert 'log_file' in logging_config
    
    def test_validation_all(self):
        """전체 설정 검증 테스트"""
        validation_results = self.config_manager.validate_all()
        
        # 모든 설정이 유효해야 함
        for key, is_valid in validation_results.items():
            assert is_valid == True, f"설정 {key}가 유효하지 않음"
        
        # 전체 유효성 확인
        assert self.config_manager.is_valid() == True
        assert len(self.config_manager.get_invalid_configs()) == 0
    
    def test_invalid_config_detection(self):
        """잘못된 설정 탐지 테스트"""
        # 잘못된 값 설정 시도 (실제로는 거부됨)
        result = self.config_manager.set('api_timeout', -1)  # 검증 실패
        assert result == False  # 설정이 실패해야 함
        
        # 원래 값이 유지되어야 함
        assert self.config_manager.get('api_timeout') == 30  # 기본값 유지
        
        # 검증은 여전히 통과해야 함 (잘못된 값이 설정되지 않았으므로)
        validation_results = self.config_manager.validate_all()
        assert validation_results.get('api_timeout') == True
        
        assert self.config_manager.is_valid() == True
        assert len(self.config_manager.get_invalid_configs()) == 0
    
    def test_reset_to_defaults(self):
        """기본값으로 초기화 테스트"""
        # 사용자 정의 값 설정
        self.config_manager.set('api_timeout', 120)
        self.config_manager.set('max_tps', 50)
        
        # 기본값으로 초기화
        self.config_manager.reset_to_defaults()
        
        # 기본값으로 복원되었는지 확인
        assert self.config_manager.get('api_timeout') == 30
        assert self.config_manager.get('max_tps') == 10
    
    def test_config_summary(self):
        """설정 요약 테스트"""
        summary = self.config_manager.get_config_summary()
        
        assert 'total_configs' in summary
        assert 'default_configs' in summary
        assert 'validators' in summary
        assert 'is_valid' in summary
        assert 'invalid_configs' in summary
        assert 'api_config_count' in summary
        assert 'cache_config_count' in summary
        assert 'logging_config_count' in summary
        
        assert summary['total_configs'] > 0
        assert summary['is_valid'] == True
        assert len(summary['invalid_configs']) == 0
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_export_config(self, mock_json_dump, mock_file):
        """설정 내보내기 테스트"""
        result = self.config_manager.export_config('test_config.json')
        
        assert result == True
        mock_file.assert_called_once_with('test_config.json', 'w', encoding='utf-8')
        mock_json_dump.assert_called_once()
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"api_timeout": 60, "max_tps": 20}')
    @patch('json.load')
    def test_import_config(self, mock_json_load, mock_file):
        """설정 가져오기 테스트"""
        mock_json_load.return_value = {'api_timeout': 60, 'max_tps': 20}
        
        result = self.config_manager.import_config('test_config.json')
        
        assert result == True
        mock_file.assert_called_once_with('test_config.json', 'r', encoding='utf-8')
        mock_json_load.assert_called_once()
        
        # 가져온 설정이 적용되었는지 확인
        assert self.config_manager.get('api_timeout') == 60
        assert self.config_manager.get('max_tps') == 20
    
    @patch.dict(os.environ, {'API_TIMEOUT': '120', 'MAX_TPS': '25', 'LOG_LEVEL': 'DEBUG'})
    def test_environment_variable_loading(self):
        """환경변수 로딩 테스트"""
        # 새로운 ConfigManager 인스턴스 생성 (환경변수 반영)
        config_manager = ConfigManager()
        
        assert config_manager.get('api_timeout') == 120
        assert config_manager.get('max_tps') == 25
        assert config_manager.get('log_level') == 'DEBUG'
    
    def test_string_representation(self):
        """문자열 표현 테스트"""
        str_repr = str(self.config_manager)
        assert 'ConfigManager' in str_repr
        assert 'configs=' in str_repr
        assert 'valid=' in str_repr
        
        repr_str = repr(self.config_manager)
        assert 'ConfigManager' in repr_str
    
    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        # None 값 설정
        assert self.config_manager.set('none_value', None) == True
        assert self.config_manager.get('none_value') == None
        
        # 빈 문자열
        assert self.config_manager.set('empty_string', '') == True
        assert self.config_manager.get('empty_string') == ''
        
        # 0 값
        assert self.config_manager.set('zero_value', 0) == True
        assert self.config_manager.get('zero_value') == 0
        
        # False 값
        assert self.config_manager.set('false_value', False) == True
        assert self.config_manager.get('false_value') == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
