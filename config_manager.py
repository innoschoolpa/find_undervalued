"""
설정 관리자 모듈

애플리케이션 설정을 관리하는 ConfigManager를 제공합니다.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


class ConfigManager:
    """설정 관리자 (환경변수, 기본값, 검증)"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config: Dict[str, Any] = {}
        self.defaults = {}
        self.validators = {}
        self.config_file = config_file

        if not yaml:
            logging.warning("PyYAML이 설치되어 있지 않습니다. config.yaml 파일을 로드할 수 없습니다.")

        # 기본 설정값 정의
        self._setup_defaults()

        # 설정 검증기 정의
        self._setup_validators()

        # 환경변수에서 설정 로드
        self._load_from_env()

        # 구성 파일에서 설정 로드 (환경 변수보다 우선)
        self._load_from_file()

        logging.info("ConfigManager 초기화 완료")
    
    def _setup_defaults(self):
        """기본 설정값 정의"""
        self.defaults = {
            # API 설정
            'kis_api_base_url': 'https://openapi.koreainvestment.com:9443',
            'kis_api_key': '',
            'kis_api_secret': '',
            'api_timeout': 30,
            'api_retry_count': 3,
            
            # 캐시 설정
            'cache_ttl_seconds': 3600,  # 1시간
            'cache_max_size': 1000,
            'cache_enabled': True,
            
            # Rate Limiting 설정
            'max_tps': 10,
            'burst_limit': 20,
            'rate_limit_enabled': True,
            
            # 로깅 설정
            'log_level': 'INFO',
            'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'log_file': 'app.log',
            'log_max_size': 10485760,  # 10MB
            'log_backup_count': 5,
            
            # 분석 설정
            'analysis_timeout': 300,  # 5분
            'max_concurrent_analyses': 5,
            'analysis_retry_count': 2,
            
            # 데이터 품질 설정
            'min_data_quality_score': 70.0,
            'data_validation_enabled': True,
            'data_freshness_hours': 24,
            
            # 성능 설정
            'enable_metrics': True,
            'metrics_interval': 60,  # 1분
            'performance_monitoring': True,
            
            # 보안 설정
            'enable_ssl_verification': True,
            'request_timeout': 30,
            'max_redirects': 5
        }
    
    def _setup_validators(self):
        """설정 검증기 정의"""
        self.validators = {
            'api_timeout': lambda x: isinstance(x, int) and 1 <= x <= 300,
            'api_retry_count': lambda x: isinstance(x, int) and 0 <= x <= 10,
            'cache_ttl_seconds': lambda x: isinstance(x, int) and x > 0,
            'cache_max_size': lambda x: isinstance(x, int) and x > 0,
            'max_tps': lambda x: isinstance(x, int) and 1 <= x <= 1000,
            'burst_limit': lambda x: isinstance(x, int) and x > 0,
            'log_level': lambda x: x in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            'min_data_quality_score': lambda x: isinstance(x, (int, float)) and 0 <= x <= 100,
            'data_freshness_hours': lambda x: isinstance(x, int) and x > 0,
            'analysis_timeout': lambda x: isinstance(x, int) and x > 0,
            'max_concurrent_analyses': lambda x: isinstance(x, int) and 1 <= x <= 50
        }
    
    def _load_from_env(self):
        """환경변수에서 설정 로드"""
        try:
            for key, default_value in self.defaults.items():
                env_key = key.upper()
                env_value = os.getenv(env_key)
                
                if env_value is not None:
                    # 타입 변환 시도
                    converted_value = self._convert_value(env_value, type(default_value))
                    self.config[key] = converted_value
                else:
                    self.config[key] = default_value
            
            logging.info(f"환경변수에서 {len(self.config)}개 설정 로드 완료")
            
        except Exception as e:
            logging.error(f"환경변수 로드 실패: {e}")
    
    def _load_from_file(self):
        """config.yaml 파일에서 설정 로드"""
        if not yaml:
            return

        candidate_files = []

        if self.config_file:
            explicit_path = Path(self.config_file)
            if explicit_path.is_dir():
                explicit_path = explicit_path / "config.yaml"
            candidate_files.append(explicit_path)
        else:
            candidate_files.extend([
                Path("config.yaml"),
                Path("./config/config.yaml"),
                Path(os.getenv("CONFIG_FILE", "")).expanduser() if os.getenv("CONFIG_FILE") else None,
            ])

        for file_path in candidate_files:
            if not file_path or not file_path.exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f) or {}

                self._apply_nested_config(file_config)
                logging.info("설정 파일 로드 완료: %s", file_path)
                # 현재 파일 경로를 유지
                self.config_file = str(file_path)
                break
            except Exception as exc:  # pragma: no cover
                logging.warning("설정 파일 로드 실패 (%s): %s", file_path, exc)

    def _apply_nested_config(self, config_data: Dict[str, Any], prefix: Optional[str] = None) -> None:
        """중첩된 설정 값을 평탄화하여 저장"""
        for key, value in config_data.items():
            current_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                self._apply_nested_config(value, current_key)
            else:
                self._set_config_value(current_key, value)

    def _set_config_value(self, path: str, value: Any) -> None:
        """설정 키를 적절히 매핑하여 저장"""
        normalized_path = path.replace('-', '_')

        # config.yaml의 주요 매핑 (예: kis_api.app_key → kis_api_key)
        direct_mappings = {
            'kis_api.app_key': 'kis_api_key',
            'kis_api.app_secret': 'kis_api_secret',
            'kis_api.base_url': 'kis_api_base_url',
            'kis.app_key': 'kis_api_key',
            'kis.app_secret': 'kis_api_secret',
            'kis.base_url': 'kis_api_base_url',
        }

        target_key = direct_mappings.get(normalized_path)
        if target_key:
            self.config[target_key] = value
            self.config[normalized_path] = value
            normalized_key = target_key
        else:
            normalized_key = normalized_path.replace('.', '_')

        if normalized_key in self.defaults:
            self.config[normalized_key] = value

        if normalized_path not in self.config:
            self.config[normalized_path] = value
    
    def _convert_value(self, value: str, target_type: type) -> Any:
        """값 타입 변환"""
        try:
            if target_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif target_type == int:
                return int(value)
            elif target_type == float:
                return float(value)
            else:
                return value
                
        except (ValueError, TypeError) as e:
            logging.warning(f"값 변환 실패: {value} → {target_type.__name__}, {e}")
            return value
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        if key in self.config:
            return self.config[key]

        # 점 표기법/언더스코어 표기법 호환성 확보
        variants = set()
        if '.' in key:
            flattened = key.replace('.', '_')
            variants.update({flattened, flattened.replace('__', '_')})
        if '_' in key:
            dotted = key.replace('_', '.')
            variants.add(dotted)
        variants.add(key)

        for variant in variants:
            if variant in self.config:
                return self.config[variant]

        return default
    
    def set(self, key: str, value: Any) -> bool:
        """설정값 설정"""
        try:
            # 검증
            if key in self.validators:
                if not self.validators[key](value):
                    logging.error(f"설정값 검증 실패: {key}={value}")
                    return False
            
            # 타입 검증
            if key in self.defaults:
                expected_type = type(self.defaults[key])
                if not isinstance(value, expected_type):
                    logging.warning(f"설정값 타입 불일치: {key}, 예상={expected_type.__name__}, 실제={type(value).__name__}")
            
            self.config[key] = value
            logging.debug(f"설정값 설정: {key}={value}")
            return True
            
        except Exception as e:
            logging.error(f"설정값 설정 실패: {key}={value}, {e}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """모든 설정값 조회"""
        return self.config.copy()
    
    def get_api_config(self) -> Dict[str, Any]:
        """API 관련 설정만 조회"""
        api_keys = [k for k in self.config.keys() if k.startswith(('api_', 'kis_'))]
        return {k: self.config[k] for k in api_keys}
    
    def get_cache_config(self) -> Dict[str, Any]:
        """캐시 관련 설정만 조회"""
        cache_keys = [k for k in self.config.keys() if k.startswith('cache_')]
        return {k: self.config[k] for k in cache_keys}
    
    def get_logging_config(self) -> Dict[str, Any]:
        """로깅 관련 설정만 조회"""
        log_keys = [k for k in self.config.keys() if k.startswith('log_')]
        return {k: self.config[k] for k in log_keys}
    
    def validate_all(self) -> Dict[str, bool]:
        """모든 설정값 검증"""
        validation_results = {}
        
        for key, validator in self.validators.items():
            try:
                value = self.config.get(key)
                validation_results[key] = validator(value) if value is not None else True
            except Exception as e:
                logging.error(f"설정 검증 실패: {key}, {e}")
                validation_results[key] = False
        
        return validation_results
    
    def is_valid(self) -> bool:
        """설정 유효성 확인"""
        validation_results = self.validate_all()
        return all(validation_results.values())
    
    def get_invalid_configs(self) -> list:
        """유효하지 않은 설정 목록"""
        validation_results = self.validate_all()
        return [key for key, is_valid in validation_results.items() if not is_valid]
    
    def reload_from_env(self):
        """환경변수에서 설정 재로드"""
        try:
            self._load_from_env()
            logging.info("환경변수에서 설정 재로드 완료")
        except Exception as e:
            logging.error(f"설정 재로드 실패: {e}")
    
    def reset_to_defaults(self):
        """기본값으로 설정 초기화"""
        try:
            self.config = self.defaults.copy()
            logging.info("설정을 기본값으로 초기화 완료")
        except Exception as e:
            logging.error(f"설정 초기화 실패: {e}")
    
    def export_config(self, file_path: str) -> bool:
        """설정을 파일로 내보내기"""
        try:
            import json
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logging.info(f"설정 내보내기 완료: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"설정 내보내기 실패: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """파일에서 설정 가져오기"""
        try:
            import json
            
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 검증 후 적용
            for key, value in imported_config.items():
                if self.set(key, value):
                    continue
                else:
                    logging.warning(f"설정 가져오기 실패: {key}={value}")
            
            logging.info(f"설정 가져오기 완료: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"설정 가져오기 실패: {e}")
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """설정 요약 정보"""
        try:
            return {
                'total_configs': len(self.config),
                'default_configs': len(self.defaults),
                'validators': len(self.validators),
                'is_valid': self.is_valid(),
                'invalid_configs': self.get_invalid_configs(),
                'api_config_count': len(self.get_api_config()),
                'cache_config_count': len(self.get_cache_config()),
                'logging_config_count': len(self.get_logging_config())
            }
        except Exception as e:
            logging.error(f"설정 요약 생성 실패: {e}")
            return {}
    
    def __str__(self) -> str:
        """문자열 표현"""
        try:
            summary = self.get_config_summary()
            return f"ConfigManager(configs={summary['total_configs']}, valid={summary['is_valid']})"
        except:
            return "ConfigManager()"
    
    def __repr__(self) -> str:
        """개발자용 문자열 표현"""
        return self.__str__()