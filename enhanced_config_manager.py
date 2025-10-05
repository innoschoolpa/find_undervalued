#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
향상된 설정 관리자 모듈

성능 최적화를 위한 환경변수 설정 관리 기능을 제공합니다.
"""

import os
import logging
import json
import yaml
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import psutil

@dataclass
class PerformanceConfig:
    """성능 최적화 설정 데이터 클래스"""
    # CPU/메모리 설정
    max_workers: int = 0  # 0 = 자동
    memory_limit_gb: float = 8.0
    cpu_limit_percent: float = 80.0
    
    # 캐시 설정
    cache_enabled: bool = True
    cache_size_mb: int = 512
    cache_ttl_seconds: int = 3600
    
    # API 설정
    api_timeout: int = 30
    api_retry_count: int = 3
    api_rate_limit: int = 10
    
    # 분석 설정
    analysis_batch_size: int = 100
    analysis_timeout: int = 300
    max_concurrent_analyses: int = 5
    
    # 데이터 처리 설정
    chunk_size: int = 1000
    compression_enabled: bool = True
    parallel_processing: bool = True

@dataclass
class SystemInfo:
    """시스템 정보 데이터 클래스"""
    cpu_count: int
    memory_gb: float
    available_memory_gb: float
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float

class EnhancedConfigManager:
    """향상된 설정 관리자 클래스"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        self.config = {}
        self.performance_config = PerformanceConfig()
        self.system_info = self._get_system_info()
        
        # 설정 로드
        self._load_config()
        self._optimize_performance_settings()
        
        self.logger.info("향상된 설정 관리자 초기화 완료")
    
    def _get_system_info(self) -> SystemInfo:
        """시스템 정보 수집"""
        try:
            # CPU 정보
            cpu_count = psutil.cpu_count(logical=True)
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 정보
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            available_memory_gb = memory.available / (1024**3)
            memory_percent = memory.percent
            
            # 디스크 정보
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            
            return SystemInfo(
                cpu_count=cpu_count,
                memory_gb=memory_gb,
                available_memory_gb=available_memory_gb,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent
            )
        except Exception as e:
            self.logger.warning(f"시스템 정보 수집 실패: {e}")
            return SystemInfo(4, 8.0, 4.0, 50.0, 50.0, 50.0)  # 기본값
    
    def _load_config(self) -> None:
        """설정 로드"""
        # 환경변수에서 기본 설정 로드
        self._load_from_env()
        
        # 설정 파일이 있으면 로드
        if self.config_file and Path(self.config_file).exists():
            self._load_from_file()
        
        # 설정 검증 및 최적화
        self._validate_config()
    
    def _load_from_env(self) -> None:
        """환경변수에서 설정 로드"""
        env_mappings = {
            # KIS API 설정
            'KIS_API_KEY': 'kis.api_key',
            'KIS_API_SECRET': 'kis.api_secret',
            'KIS_API_BASE_URL': 'kis.base_url',
            'KIS_MAX_TPS': 'kis.max_tps',
            'KIS_CACHE_TTL_PRICE': 'kis.cache_ttl_price',
            'KIS_CACHE_TTL_FINANCIAL': 'kis.cache_ttl_financial',
            'KIS_CACHE_MAX_KEYS': 'kis.cache_max_keys',
            
            # 성능 설정
            'MAX_WORKERS': 'performance.max_workers',
            'EPS_MIN': 'analysis.eps_min',
            'BPS_MIN': 'analysis.bps_min',
            'POS_TINY_BAND_THRESHOLD': 'analysis.pos_tiny_band_threshold',
            'PER_MAX_DEFAULT': 'analysis.per_max_default',
            'PBR_MAX_DEFAULT': 'analysis.pbr_max_default',
            'SECTOR_TARGET_GOOD': 'analysis.sector_target_good',
            
            # Rate Limiting 설정
            'RATE_LIMITER_DEFAULT_TIMEOUT': 'rate_limiter.timeout',
            'RATE_LIMITER_NOTIFY_ALL': 'rate_limiter.notify_all',
            
            # 시장 데이터 설정
            'MARKET_CAP_STRICT_MODE': 'market.strict_mode',
            'MARKET_CAP_ASSUME_EOKWON_MAX': 'market.assume_eokwon_max',
            'MARKET_CAP_ASSUME_EOKWON_MIN': 'market.assume_eokwon_min',
            'ENABLE_FAKE_PROVIDERS': 'system.enable_fake_providers',
            
            # 로깅 설정
            'LOG_LEVEL': 'logging.level',
            'LOG_FORMAT': 'logging.format',
            
            # 분석 설정
            'ANALYSIS_TIMEOUT': 'analysis.timeout',
            'MAX_CONCURRENT_ANALYSES': 'analysis.max_concurrent',
            'MIN_DATA_QUALITY_SCORE': 'analysis.min_data_quality',
            'DATA_FRESHNESS_HOURS': 'analysis.data_freshness_hours',
            
            # 백테스팅 설정
            'BACKTEST_START_DATE': 'backtest.start_date',
            'BACKTEST_END_DATE': 'backtest.end_date',
            'BACKTEST_INITIAL_CAPITAL': 'backtest.initial_capital',
            'BACKTEST_TRANSACTION_COST': 'backtest.transaction_cost',
            
            # 포트폴리오 설정
            'PORTFOLIO_MAX_STOCKS': 'portfolio.max_stocks',
            'PORTFOLIO_MIN_WEIGHT': 'portfolio.min_weight',
            'PORTFOLIO_MAX_WEIGHT': 'portfolio.max_weight',
            'PORTFOLIO_REBALANCE_FREQUENCY': 'portfolio.rebalance_frequency',
            'PORTFOLIO_RISK_TARGET': 'portfolio.risk_target'
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_config(config_path, self._convert_value(value))
    
    def _load_from_file(self) -> None:
        """설정 파일에서 로드"""
        try:
            file_path = Path(self.config_file)
            
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
            elif file_path.suffix.lower() in ['.yml', '.yaml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
            else:
                self.logger.warning(f"지원하지 않는 설정 파일 형식: {file_path.suffix}")
                return
            
            # 중첩된 딕셔너리 병합
            self._merge_config(file_config)
            self.logger.info(f"설정 파일 로드 완료: {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"설정 파일 로드 실패: {e}")
    
    def _merge_config(self, new_config: Dict[str, Any], base_path: str = "") -> None:
        """설정 병합"""
        for key, value in new_config.items():
            current_path = f"{base_path}.{key}" if base_path else key
            
            if isinstance(value, dict):
                self._merge_config(value, current_path)
            else:
                self._set_nested_config(current_path, value)
    
    def _set_nested_config(self, path: str, value: Any) -> None:
        """중첩된 설정 값 설정"""
        keys = path.split('.')
        current = self.config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _get_nested_config(self, path: str, default: Any = None) -> Any:
        """중첩된 설정 값 조회"""
        keys = path.split('.')
        current = self.config
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def _convert_value(self, value: str) -> Any:
        """문자열 값을 적절한 타입으로 변환"""
        # 불린 값
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 숫자 값
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # 문자열 값
        return value
    
    def _validate_config(self) -> None:
        """설정 검증"""
        warnings = []
        
        # 필수 설정 확인
        required_settings = [
            ('kis.api_key', 'KIS API 키'),
            ('kis.api_secret', 'KIS API 시크릿')
        ]
        
        for setting_path, description in required_settings:
            if not self._get_nested_config(setting_path):
                warnings.append(f"{description}이 설정되지 않았습니다")
        
        # 성능 설정 검증
        max_workers = self._get_nested_config('performance.max_workers', 0)
        if max_workers > self.system_info.cpu_count * 2:
            warnings.append(f"MAX_WORKERS({max_workers})가 권장값({self.system_info.cpu_count})을 초과합니다")
        
        # 메모리 설정 검증
        memory_limit = self._get_nested_config('performance.memory_limit_gb', 8.0)
        if memory_limit > self.system_info.available_memory_gb:
            warnings.append(f"메모리 제한({memory_limit}GB)이 사용 가능한 메모리({self.system_info.available_memory_gb:.1f}GB)를 초과합니다")
        
        # 경고 출력
        for warning in warnings:
            self.logger.warning(f"설정 검증 경고: {warning}")
    
    def _optimize_performance_settings(self) -> None:
        """성능 설정 최적화"""
        # CPU 코어 수 기반 워커 수 최적화
        if self._get_nested_config('performance.max_workers', 0) == 0:
            optimal_workers = min(self.system_info.cpu_count, 8)  # 최대 8개
            self._set_nested_config('performance.max_workers', optimal_workers)
            self.logger.info(f"최적화된 워커 수: {optimal_workers}")
        
        # 메모리 기반 캐시 크기 최적화
        available_memory_gb = self.system_info.available_memory_gb
        optimal_cache_size = min(int(available_memory_gb * 0.1), 1024)  # 사용 가능 메모리의 10%, 최대 1GB
        self._set_nested_config('performance.cache_size_mb', optimal_cache_size)
        
        # API Rate Limit 최적화
        if self.system_info.cpu_count >= 8:
            self._set_nested_config('performance.api_rate_limit', 20)
        elif self.system_info.cpu_count >= 4:
            self._set_nested_config('performance.api_rate_limit', 15)
        else:
            self._set_nested_config('performance.api_rate_limit', 10)
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정 값 조회"""
        return self._get_nested_config(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """설정 값 설정"""
        try:
            self._set_nested_config(key, value)
            self.logger.debug(f"설정 업데이트: {key} = {value}")
            return True
        except Exception as e:
            self.logger.error(f"설정 업데이트 실패 ({key}): {e}")
            return False
    
    def get_performance_config(self) -> PerformanceConfig:
        """성능 설정 반환"""
        return PerformanceConfig(
            max_workers=self.get('performance.max_workers', 0),
            memory_limit_gb=self.get('performance.memory_limit_gb', 8.0),
            cpu_limit_percent=self.get('performance.cpu_limit_percent', 80.0),
            cache_enabled=self.get('performance.cache_enabled', True),
            cache_size_mb=self.get('performance.cache_size_mb', 512),
            cache_ttl_seconds=self.get('performance.cache_ttl_seconds', 3600),
            api_timeout=self.get('performance.api_timeout', 30),
            api_retry_count=self.get('performance.api_retry_count', 3),
            api_rate_limit=self.get('performance.api_rate_limit', 10),
            analysis_batch_size=self.get('performance.analysis_batch_size', 100),
            analysis_timeout=self.get('performance.analysis_timeout', 300),
            max_concurrent_analyses=self.get('performance.max_concurrent_analyses', 5),
            chunk_size=self.get('performance.chunk_size', 1000),
            compression_enabled=self.get('performance.compression_enabled', True),
            parallel_processing=self.get('performance.parallel_processing', True)
        )
    
    def get_system_info(self) -> SystemInfo:
        """시스템 정보 반환"""
        return self.system_info
    
    def save_config(self, filename: Optional[str] = None) -> str:
        """설정 저장"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"enhanced_config_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"설정 저장 완료: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"설정 저장 실패: {e}")
            raise
    
    def export_env_file(self, filename: str = "optimized_config.env") -> str:
        """환경변수 파일로 내보내기"""
        env_mappings = {
            'performance.max_workers': 'MAX_WORKERS',
            'performance.cache_size_mb': 'CACHE_SIZE_MB',
            'performance.api_rate_limit': 'API_RATE_LIMIT',
            'kis.max_tps': 'KIS_MAX_TPS',
            'analysis.timeout': 'ANALYSIS_TIMEOUT',
            'analysis.max_concurrent': 'MAX_CONCURRENT_ANALYSES',
            'logging.level': 'LOG_LEVEL'
        }
        
        env_lines = ["# 최적화된 환경변수 설정\n"]
        
        for config_path, env_var in env_mappings.items():
            value = self.get(config_path)
            if value is not None:
                env_lines.append(f"{env_var}={value}")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(env_lines))
            
            self.logger.info(f"환경변수 파일 생성: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"환경변수 파일 생성 실패: {e}")
            raise
    
    def get_config_summary(self) -> Dict[str, Any]:
        """설정 요약 반환"""
        return {
            'system_info': {
                'cpu_count': self.system_info.cpu_count,
                'memory_gb': self.system_info.memory_gb,
                'available_memory_gb': self.system_info.available_memory_gb,
                'cpu_percent': self.system_info.cpu_percent,
                'memory_percent': self.system_info.memory_percent
            },
            'performance_config': self.get_performance_config().__dict__,
            'kis_api_configured': bool(self.get('kis.api_key') and self.get('kis.api_secret')),
            'optimization_applied': True,
            'config_file': self.config_file
        }

def create_enhanced_config_manager(config_file: Optional[str] = None) -> EnhancedConfigManager:
    """향상된 설정 관리자 인스턴스 생성"""
    return EnhancedConfigManager(config_file)

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # 설정 관리자 생성
    config_manager = create_enhanced_config_manager()
    
    # 설정 요약 출력
    summary = config_manager.get_config_summary()
    
    print("향상된 설정 관리자 상태:")
    print("=" * 50)
    
    print(f"시스템 정보:")
    for key, value in summary['system_info'].items():
        print(f"  {key}: {value}")
    
    print(f"\n성능 설정:")
    for key, value in summary['performance_config'].items():
        print(f"  {key}: {value}")
    
    print(f"\n기타 설정:")
    print(f"  KIS API 설정됨: {summary['kis_api_configured']}")
    print(f"  최적화 적용됨: {summary['optimization_applied']}")
    
    # 환경변수 파일 생성
    env_file = config_manager.export_env_file()
    print(f"\n환경변수 파일 생성: {env_file}")










