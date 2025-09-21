# config_manager.py
"""
향상된 설정 관리 시스템
- 환경별 설정 지원
- 설정 검증 및 기본값 관리
- 동적 설정 업데이트
- 설정 스키마 검증
"""

import os
import yaml
import json
import logging
from typing import Any, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import jsonschema
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)

# =============================================================================
# 1. 설정 스키마 정의
# =============================================================================

class Environment(Enum):
    """환경 타입"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class ConfigSchema:
    """설정 스키마 정의"""
    name: str
    type: str
    required: bool = False
    default: Any = None
    description: str = ""
    validation: Optional[Callable] = None
    choices: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None

# =============================================================================
# 2. 설정 검증기
# =============================================================================

class ConfigValidator:
    """설정 검증기 클래스"""
    
    def __init__(self):
        self.schemas = {}
        self._register_default_schemas()
    
    def _register_default_schemas(self):
        """기본 스키마 등록"""
        # API 설정 스키마
        self.schemas['api'] = {
            "type": "object",
            "properties": {
                "kis_api_key": {"type": "string", "minLength": 1},
                "kis_secret_key": {"type": "string", "minLength": 1},
                "dart_api_key": {"type": "string", "minLength": 1},
                "base_url": {"type": "string", "format": "uri"},
                "timeout": {"type": "number", "minimum": 1, "maximum": 300},
                "max_retries": {"type": "integer", "minimum": 0, "maximum": 10}
            },
            "required": ["kis_api_key", "kis_secret_key", "dart_api_key"]
        }
        
        # 분석 설정 스키마
        self.schemas['analysis'] = {
            "type": "object",
            "properties": {
                "weights": {
                    "type": "object",
                    "properties": {
                        "opinion_analysis": {"type": "number", "minimum": 0, "maximum": 100},
                        "estimate_analysis": {"type": "number", "minimum": 0, "maximum": 100},
                        "financial_ratios": {"type": "number", "minimum": 0, "maximum": 100},
                        "growth_analysis": {"type": "number", "minimum": 0, "maximum": 100},
                        "scale_analysis": {"type": "number", "minimum": 0, "maximum": 100}
                    }
                },
                "grade_thresholds": {
                    "type": "object",
                    "properties": {
                        "A_plus": {"type": "number", "minimum": 0, "maximum": 100},
                        "A": {"type": "number", "minimum": 0, "maximum": 100},
                        "B_plus": {"type": "number", "minimum": 0, "maximum": 100},
                        "B": {"type": "number", "minimum": 0, "maximum": 100},
                        "C_plus": {"type": "number", "minimum": 0, "maximum": 100},
                        "C": {"type": "number", "minimum": 0, "maximum": 100},
                        "D": {"type": "number", "minimum": 0, "maximum": 100},
                        "F": {"type": "number", "minimum": 0, "maximum": 100}
                    }
                }
            }
        }
        
        # 캐시 설정 스키마
        self.schemas['cache'] = {
            "type": "object",
            "properties": {
                "memory_max_size": {"type": "integer", "minimum": 1, "maximum": 10000},
                "memory_ttl": {"type": "number", "minimum": 60, "maximum": 86400},
                "disk_ttl": {"type": "number", "minimum": 3600, "maximum": 604800},
                "compress": {"type": "boolean"}
            }
        }
    
    def validate_config(self, config: Dict[str, Any], schema_name: str) -> List[str]:
        """설정 검증"""
        errors = []
        
        if schema_name not in self.schemas:
            errors.append(f"알 수 없는 스키마: {schema_name}")
            return errors
        
        try:
            validate(instance=config, schema=self.schemas[schema_name])
        except ValidationError as e:
            errors.append(f"스키마 검증 실패: {e.message}")
        except Exception as e:
            errors.append(f"검증 중 오류 발생: {e}")
        
        return errors
    
    def register_schema(self, name: str, schema: Dict[str, Any]):
        """새 스키마 등록"""
        self.schemas[name] = schema

# =============================================================================
# 3. 설정 로더
# =============================================================================

class ConfigLoader:
    """설정 로더 클래스"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.cache = {}
        self.last_modified = {}
    
    def load_config(self, 
                   config_name: str = "config",
                   environment: Environment = Environment.DEVELOPMENT,
                   use_cache: bool = True) -> Dict[str, Any]:
        """설정 로드"""
        config_key = f"{config_name}_{environment.value}"
        
        # 캐시 확인
        if use_cache and config_key in self.cache:
            if self._is_config_modified(config_name, environment):
                del self.cache[config_key]
            else:
                return self.cache[config_key]
        
        # 설정 파일 경로들
        config_paths = [
            self.config_dir / f"{config_name}_{environment.value}.yaml",
            self.config_dir / f"{config_name}_{environment.value}.yml",
            self.config_dir / f"{config_name}.yaml",
            self.config_dir / f"{config_name}.yml",
            Path(f"{config_name}.yaml"),
            Path(f"{config_name}.yml")
        ]
        
        config = {}
        
        # 설정 파일 로드
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        if config_path.suffix in ['.yaml', '.yml']:
                            file_config = yaml.safe_load(f)
                        else:
                            file_config = json.load(f)
                    
                    # 중첩 딕셔너리 병합
                    config = self._merge_configs(config, file_config)
                    logger.info(f"설정 파일 로드: {config_path}")
                    break
                
                except Exception as e:
                    logger.warning(f"설정 파일 로드 실패 {config_path}: {e}")
                    continue
        
        # 환경 변수 오버라이드
        config = self._apply_env_overrides(config)
        
        # 기본값 적용
        config = self._apply_defaults(config)
        
        # 캐시 저장
        if use_cache:
            self.cache[config_key] = config
            self.last_modified[config_key] = time.time()
        
        return config
    
    def _is_config_modified(self, config_name: str, environment: Environment) -> bool:
        """설정 파일 수정 여부 확인"""
        config_paths = [
            self.config_dir / f"{config_name}_{environment.value}.yaml",
            self.config_dir / f"{config_name}_{environment.value}.yml",
            self.config_dir / f"{config_name}.yaml",
            self.config_dir / f"{config_name}.yml"
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    mtime = config_path.stat().st_mtime
                    cache_key = f"{config_name}_{environment.value}"
                    if cache_key in self.last_modified:
                        return mtime > self.last_modified[cache_key]
                except Exception:
                    pass
        
        return False
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """설정 딕셔너리 병합"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """환경 변수 오버라이드 적용"""
        env_mappings = {
            'KIS_API_KEY': ['api', 'kis_api_key'],
            'KIS_SECRET_KEY': ['api', 'kis_secret_key'],
            'DART_API_KEY': ['api', 'dart_api_key'],
            'LOG_LEVEL': ['logging', 'level'],
            'CACHE_TTL': ['cache', 'memory_ttl'],
            'MAX_WORKERS': ['analysis', 'max_workers']
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                self._set_nested_value(config, config_path, env_value)
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], path: List[str], value: Any):
        """중첩된 딕셔너리에 값 설정"""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """기본값 적용"""
        defaults = self._get_default_config()
        return self._merge_configs(defaults, config)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            'api': {
                'kis_api_key': '',
                'kis_secret_key': '',
                'dart_api_key': '',
                'base_url': 'https://openapi.koreainvestment.com:9443',
                'timeout': 30,
                'max_retries': 3
            },
            'analysis': {
                'weights': {
                    'opinion_analysis': 25,
                    'estimate_analysis': 30,
                    'financial_ratios': 30,
                    'growth_analysis': 10,
                    'scale_analysis': 5
                },
                'grade_thresholds': {
                    'A_plus': 80,
                    'A': 70,
                    'B_plus': 60,
                    'B': 50,
                    'C_plus': 40,
                    'C': 30,
                    'D': 20,
                    'F': 0
                },
                'max_workers': 2,
                'min_market_cap': 1000
            },
            'cache': {
                'memory_max_size': 1000,
                'memory_ttl': 3600,
                'disk_ttl': 86400,
                'compress': True
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                'file': None
            }
        }

# =============================================================================
# 4. 설정 관리자
# =============================================================================

class ConfigManager:
    """설정 관리자 클래스"""
    
    def __init__(self, config_dir: str = "config"):
        self.loader = ConfigLoader(config_dir)
        self.validator = ConfigValidator()
        self.current_config = {}
        self.current_environment = Environment.DEVELOPMENT
        self.watchers = []
    
    def load(self, 
             config_name: str = "config",
             environment: Environment = Environment.DEVELOPMENT,
             validate: bool = True) -> Dict[str, Any]:
        """설정 로드"""
        self.current_config = self.loader.load_config(config_name, environment)
        self.current_environment = environment
        
        if validate:
            self.validate_all()
        
        # 설정 변경 알림
        self._notify_watchers()
        
        return self.current_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정 값 조회 (점 표기법 지원)"""
        keys = key.split('.')
        value = self.current_config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """설정 값 설정 (점 표기법 지원)"""
        keys = key.split('.')
        current = self.current_config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        
        # 설정 변경 알림
        self._notify_watchers()
    
    def validate_all(self) -> List[str]:
        """모든 설정 검증"""
        all_errors = []
        
        # API 설정 검증
        api_config = self.get('api', {})
        if api_config:
            errors = self.validator.validate_config(api_config, 'api')
            all_errors.extend([f"API 설정: {e}" for e in errors])
        
        # 분석 설정 검증
        analysis_config = self.get('analysis', {})
        if analysis_config:
            errors = self.validator.validate_config(analysis_config, 'analysis')
            all_errors.extend([f"분석 설정: {e}" for e in errors])
        
        # 캐시 설정 검증
        cache_config = self.get('cache', {})
        if cache_config:
            errors = self.validator.validate_config(cache_config, 'cache')
            all_errors.extend([f"캐시 설정: {e}" for e in errors])
        
        if all_errors:
            logger.warning(f"설정 검증 실패: {all_errors}")
        
        return all_errors
    
    def add_watcher(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """설정 변경 감시자 추가"""
        self.watchers.append(callback)
    
    def remove_watcher(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """설정 변경 감시자 제거"""
        if callback in self.watchers:
            self.watchers.remove(callback)
    
    def _notify_watchers(self) -> None:
        """감시자들에게 설정 변경 알림"""
        for callback in self.watchers:
            try:
                callback(self.current_config)
            except Exception as e:
                logger.error(f"설정 변경 알림 실패: {e}")
    
    def save_config(self, 
                   config_name: str = "config",
                   environment: Environment = None,
                   format: str = "yaml") -> bool:
        """설정 저장"""
        if environment is None:
            environment = self.current_environment
        
        config_path = self.loader.config_dir / f"{config_name}_{environment.value}.{format}"
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                if format in ['yaml', 'yml']:
                    yaml.dump(self.current_config, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(self.current_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"설정 저장 완료: {config_path}")
            return True
        
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            return False
    
    def reload(self) -> Dict[str, Any]:
        """설정 재로드"""
        return self.load(validate=True)
    
    def get_environment_config(self, environment: Environment) -> Dict[str, Any]:
        """특정 환경의 설정 조회"""
        return self.loader.load_config(environment=environment, validate=False)
    
    def list_environments(self) -> List[Environment]:
        """사용 가능한 환경 목록"""
        environments = []
        for env in Environment:
            config_paths = [
                self.loader.config_dir / f"config_{env.value}.yaml",
                self.loader.config_dir / f"config_{env.value}.yml"
            ]
            if any(path.exists() for path in config_paths):
                environments.append(env)
        return environments

# =============================================================================
# 5. 설정 팩토리
# =============================================================================

class ConfigFactory:
    """설정 팩토리 클래스"""
    
    _instances = {}
    
    @classmethod
    def get_manager(cls, config_dir: str = "config") -> ConfigManager:
        """설정 관리자 인스턴스 반환 (싱글톤)"""
        if config_dir not in cls._instances:
            cls._instances[config_dir] = ConfigManager(config_dir)
        return cls._instances[config_dir]
    
    @classmethod
    def create_environment_config(cls, 
                                 environment: Environment,
                                 config_dir: str = "config") -> Dict[str, Any]:
        """환경별 설정 생성"""
        manager = cls.get_manager(config_dir)
        return manager.get_environment_config(environment)
    
    @classmethod
    def create_merged_config(cls,
                            base_config: Dict[str, Any],
                            override_config: Dict[str, Any]) -> Dict[str, Any]:
        """설정 병합"""
        loader = ConfigLoader()
        return loader._merge_configs(base_config, override_config)

# =============================================================================
# 6. 사용 예시
# =============================================================================

if __name__ == "__main__":
    # 설정 관리자 생성
    config_manager = ConfigFactory.get_manager()
    
    # 개발 환경 설정 로드
    config = config_manager.load(environment=Environment.DEVELOPMENT)
    print("개발 환경 설정:", json.dumps(config, indent=2, ensure_ascii=False))
    
    # 설정 값 조회
    api_key = config_manager.get('api.kis_api_key')
    print(f"KIS API 키: {api_key}")
    
    # 설정 값 설정
    config_manager.set('analysis.max_workers', 4)
    print(f"최대 워커 수: {config_manager.get('analysis.max_workers')}")
    
    # 설정 검증
    errors = config_manager.validate_all()
    if errors:
        print("설정 검증 오류:", errors)
    else:
        print("설정 검증 통과")
    
    # 설정 저장
    config_manager.save_config(environment=Environment.DEVELOPMENT)
    
    # 사용 가능한 환경 목록
    environments = config_manager.list_environments()
    print(f"사용 가능한 환경: {[env.value for env in environments]}")

