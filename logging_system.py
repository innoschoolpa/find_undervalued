# logging_system.py
"""
향상된 로깅 시스템
- 구조화된 로깅
- 성능 모니터링
- 로그 분석 및 통계
- 중앙집중식 로그 관리
"""

import logging
import logging.handlers
import json
import time
import os
import sys
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
from collections import defaultdict, deque
import traceback

# =============================================================================
# 1. 로그 레벨 및 카테고리 정의
# =============================================================================

class LogLevel(Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory(Enum):
    """로그 카테고리"""
    SYSTEM = "system"
    API = "api"
    ANALYSIS = "analysis"
    CACHE = "cache"
    DATABASE = "database"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BUSINESS = "business"

@dataclass
class LogEntry:
    """로그 엔트리 데이터 클래스"""
    timestamp: str
    level: str
    category: str
    module: str
    function: str
    message: str
    data: Optional[Dict[str, Any]] = None
    exception: Optional[str] = None
    duration: Optional[float] = None
    thread_id: Optional[str] = None
    process_id: Optional[int] = None

# =============================================================================
# 2. 구조화된 로그 포매터
# =============================================================================

class StructuredFormatter(logging.Formatter):
    """구조화된 로그 포매터"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드 포맷팅"""
        # 기본 필드
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'message': record.getMessage(),
            'line': record.lineno,
            'thread_id': threading.get_ident(),
            'process_id': os.getpid()
        }
        
        # 카테고리 추가
        if hasattr(record, 'category'):
            log_entry['category'] = record.category
        else:
            log_entry['category'] = 'system'
        
        # 추가 데이터
        if self.include_extra and hasattr(record, 'data'):
            log_entry['data'] = record.data
        
        # 예외 정보
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # 실행 시간
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)

class ColoredFormatter(logging.Formatter):
    """컬러 로그 포매터 (콘솔용)"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # 청록색
        'INFO': '\033[32m',       # 녹색
        'WARNING': '\033[33m',    # 노란색
        'ERROR': '\033[31m',      # 빨간색
        'CRITICAL': '\033[35m',   # 자주색
        'RESET': '\033[0m'        # 리셋
    }
    
    def __init__(self, fmt: str = None):
        if fmt is None:
            fmt = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        super().__init__(fmt)
    
    def format(self, record: logging.LogRecord) -> str:
        """컬러 포맷팅"""
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

# =============================================================================
# 3. 로그 통계 및 분석
# =============================================================================

class LogAnalyzer:
    """로그 분석기 클래스"""
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.entries = deque(maxlen=max_entries)
        self.stats = defaultdict(int)
        self.error_patterns = defaultdict(int)
        self.performance_metrics = defaultdict(list)
        self.lock = threading.Lock()
    
    def add_entry(self, entry: LogEntry):
        """로그 엔트리 추가"""
        with self.lock:
            self.entries.append(entry)
            
            # 통계 업데이트
            self.stats[f"{entry.level}_{entry.category}"] += 1
            self.stats[f"total_{entry.category}"] += 1
            
            # 에러 패턴 분석
            if entry.level in ['ERROR', 'CRITICAL']:
                pattern = self._extract_error_pattern(entry.message)
                self.error_patterns[pattern] += 1
            
            # 성능 메트릭
            if entry.duration is not None:
                self.performance_metrics[entry.category].append(entry.duration)
    
    def _extract_error_pattern(self, message: str) -> str:
        """에러 패턴 추출"""
        # 간단한 패턴 추출 (실제로는 더 복잡한 패턴 매칭 가능)
        if "timeout" in message.lower():
            return "timeout"
        elif "connection" in message.lower():
            return "connection"
        elif "permission" in message.lower():
            return "permission"
        elif "not found" in message.lower():
            return "not_found"
        else:
            return "other"
    
    def get_stats(self) -> Dict[str, Any]:
        """로그 통계 조회"""
        with self.lock:
            total_entries = len(self.entries)
            if total_entries == 0:
                return {"total_entries": 0}
            
            # 레벨별 통계
            level_stats = {}
            for key, count in self.stats.items():
                if key.startswith('total_'):
                    continue
                level, category = key.split('_', 1)
                if level not in level_stats:
                    level_stats[level] = {}
                level_stats[level][category] = count
            
            # 카테고리별 통계
            category_stats = {}
            for key, count in self.stats.items():
                if key.startswith('total_'):
                    category = key[6:]  # 'total_' 제거
                    category_stats[category] = count
            
            # 성능 통계
            performance_stats = {}
            for category, durations in self.performance_metrics.items():
                if durations:
                    performance_stats[category] = {
                        'count': len(durations),
                        'avg_duration': sum(durations) / len(durations),
                        'min_duration': min(durations),
                        'max_duration': max(durations)
                    }
            
            return {
                'total_entries': total_entries,
                'level_stats': level_stats,
                'category_stats': category_stats,
                'error_patterns': dict(self.error_patterns),
                'performance_stats': performance_stats,
                'recent_errors': [entry for entry in list(self.entries)[-10:] 
                                if entry.level in ['ERROR', 'CRITICAL']]
            }
    
    def get_error_summary(self) -> Dict[str, Any]:
        """에러 요약"""
        with self.lock:
            error_entries = [entry for entry in self.entries 
                           if entry.level in ['ERROR', 'CRITICAL']]
            
            if not error_entries:
                return {"total_errors": 0}
            
            # 최근 에러들
            recent_errors = error_entries[-10:]
            
            # 에러 패턴별 빈도
            pattern_freq = dict(self.error_patterns)
            
            # 모듈별 에러 수
            module_errors = defaultdict(int)
            for entry in error_entries:
                module_errors[entry.module] += 1
            
            return {
                'total_errors': len(error_entries),
                'recent_errors': recent_errors,
                'error_patterns': pattern_freq,
                'module_errors': dict(module_errors)
            }

# =============================================================================
# 4. 로그 핸들러
# =============================================================================

class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """회전 파일 핸들러 (개선된 버전)"""
    
    def __init__(self, filename: str, max_bytes: int = 10*1024*1024, 
                 backup_count: int = 5, encoding: str = 'utf-8'):
        # 디렉토리 생성
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        super().__init__(filename, maxBytes=max_bytes, backupCount=backup_count, encoding=encoding)

class TimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """시간 기반 회전 파일 핸들러 (개선된 버전)"""
    
    def __init__(self, filename: str, when: str = 'midnight', 
                 interval: int = 1, backup_count: int = 30, encoding: str = 'utf-8'):
        # 디렉토리 생성
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        super().__init__(filename, when=when, interval=interval, 
                        backupCount=backup_count, encoding=encoding)

class DatabaseLogHandler(logging.Handler):
    """데이터베이스 로그 핸들러 (예시)"""
    
    def __init__(self, connection_string: str):
        super().__init__()
        self.connection_string = connection_string
        self.buffer = []
        self.buffer_size = 100
        self.lock = threading.Lock()
    
    def emit(self, record: logging.LogRecord):
        """로그 레코드 저장"""
        try:
            log_entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created).isoformat(),
                level=record.levelname,
                category=getattr(record, 'category', 'system'),
                module=record.module,
                function=record.funcName,
                message=record.getMessage(),
                data=getattr(record, 'data', None),
                exception=self.formatException(record.exc_info) if record.exc_info else None,
                duration=getattr(record, 'duration', None),
                thread_id=threading.get_ident(),
                process_id=os.getpid()
            )
            
            with self.lock:
                self.buffer.append(log_entry)
                
                if len(self.buffer) >= self.buffer_size:
                    self._flush_buffer()
        
        except Exception:
            self.handleError(record)
    
    def _flush_buffer(self):
        """버퍼 플러시 (실제 DB 저장 로직)"""
        # 실제 구현에서는 데이터베이스에 저장
        # self.buffer.clear()
        pass

# =============================================================================
# 5. 로그 매니저
# =============================================================================

class LogManager:
    """로그 매니저 클래스"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.analyzers = {}
        self.handlers = {}
        self.loggers = {}
        self._setup_logging()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정"""
        return {
            'level': 'INFO',
            'format': 'structured',
            'handlers': {
                'console': {
                    'enabled': True,
                    'level': 'INFO',
                    'colored': True
                },
                'file': {
                    'enabled': True,
                    'level': 'DEBUG',
                    'filename': 'logs/application.log',
                    'max_bytes': 10 * 1024 * 1024,  # 10MB
                    'backup_count': 5
                },
                'rotating_file': {
                    'enabled': True,
                    'level': 'INFO',
                    'filename': 'logs/application_{timestamp}.log',
                    'when': 'midnight',
                    'interval': 1,
                    'backup_count': 30
                }
            },
            'analyzers': {
                'enabled': True,
                'max_entries': 10000
            }
        }
    
    def _setup_logging(self):
        """로깅 설정"""
        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config['level']))
        
        # 기존 핸들러 제거
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 핸들러 설정
        self._setup_handlers()
        
        # 분석기 설정
        if self.config['analyzers']['enabled']:
            self._setup_analyzers()
    
    def _setup_handlers(self):
        """핸들러 설정"""
        handlers_config = self.config['handlers']
        
        # 콘솔 핸들러
        if handlers_config.get('console', {}).get('enabled', False):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, handlers_config['console']['level']))
            
            if handlers_config['console'].get('colored', False):
                formatter = ColoredFormatter()
            else:
                formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
            
            console_handler.setFormatter(formatter)
            logging.getLogger().addHandler(console_handler)
            self.handlers['console'] = console_handler
        
        # 파일 핸들러
        if handlers_config.get('file', {}).get('enabled', False):
            file_config = handlers_config['file']
            filename = file_config['filename']
            
            # 타임스탬프 치환
            if '{timestamp}' in filename:
                filename = filename.format(timestamp=datetime.now().strftime('%Y%m%d'))
            
            file_handler = RotatingFileHandler(
                filename=filename,
                max_bytes=file_config.get('max_bytes', 10*1024*1024),
                backup_count=file_config.get('backup_count', 5)
            )
            file_handler.setLevel(getattr(logging, file_config['level']))
            file_handler.setFormatter(StructuredFormatter())
            logging.getLogger().addHandler(file_handler)
            self.handlers['file'] = file_handler
        
        # 회전 파일 핸들러
        if handlers_config.get('rotating_file', {}).get('enabled', False):
            rotating_config = handlers_config['rotating_file']
            filename = rotating_config['filename']
            
            # 타임스탬프 치환
            if '{timestamp}' in filename:
                filename = filename.format(timestamp=datetime.now().strftime('%Y%m%d'))
            
            rotating_handler = TimedRotatingFileHandler(
                filename=filename,
                when=rotating_config.get('when', 'midnight'),
                interval=rotating_config.get('interval', 1),
                backup_count=rotating_config.get('backup_count', 30)
            )
            rotating_handler.setLevel(getattr(logging, rotating_config['level']))
            rotating_handler.setFormatter(StructuredFormatter())
            logging.getLogger().addHandler(rotating_handler)
            self.handlers['rotating_file'] = rotating_handler
    
    def _setup_analyzers(self):
        """분석기 설정"""
        analyzer_config = self.config['analyzers']
        self.analyzers['main'] = LogAnalyzer(
            max_entries=analyzer_config.get('max_entries', 10000)
        )
    
    def get_logger(self, name: str, category: LogCategory = LogCategory.SYSTEM) -> logging.Logger:
        """로거 반환"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            
            # 분석기 연결
            if 'main' in self.analyzers:
                handler = self._create_analyzer_handler(category)
                logger.addHandler(handler)
            
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def _create_analyzer_handler(self, category: LogCategory) -> logging.Handler:
        """분석기 핸들러 생성"""
        class AnalyzerHandler(logging.Handler):
            def __init__(self, analyzer, category):
                super().__init__()
                self.analyzer = analyzer
                self.category = category
            
            def emit(self, record):
                try:
                    log_entry = LogEntry(
                        timestamp=datetime.fromtimestamp(record.created).isoformat(),
                        level=record.levelname,
                        category=self.category.value,
                        module=record.module,
                        function=record.funcName,
                        message=record.getMessage(),
                        data=getattr(record, 'data', None),
                        exception=self.formatException(record.exc_info) if record.exc_info else None,
                        duration=getattr(record, 'duration', None),
                        thread_id=threading.get_ident(),
                        process_id=os.getpid()
                    )
                    self.analyzer.add_entry(log_entry)
                except Exception:
                    self.handleError(record)
        
        return AnalyzerHandler(self.analyzers['main'], category)
    
    def get_stats(self) -> Dict[str, Any]:
        """로그 통계 조회"""
        if 'main' in self.analyzers:
            return self.analyzers['main'].get_stats()
        return {}
    
    def get_error_summary(self) -> Dict[str, Any]:
        """에러 요약 조회"""
        if 'main' in self.analyzers:
            return self.analyzers['main'].get_error_summary()
        return {}
    
    def clear_logs(self):
        """로그 정리"""
        if 'main' in self.analyzers:
            self.analyzers['main'].entries.clear()
            self.analyzers['main'].stats.clear()
            self.analyzers['main'].error_patterns.clear()
            self.analyzers['main'].performance_metrics.clear()

# =============================================================================
# 6. 로깅 데코레이터
# =============================================================================

def log_function(category: LogCategory = LogCategory.SYSTEM, 
                level: LogLevel = LogLevel.INFO,
                include_args: bool = False,
                include_result: bool = False):
    """함수 로깅 데코레이터"""
    def decorator(func):
        logger = logging.getLogger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 함수 시작 로그
            log_data = {
                'function': func.__name__,
                'category': category.value,
                'start_time': datetime.now().isoformat()
            }
            
            if include_args:
                log_data['args'] = str(args)[:200]  # 길이 제한
                log_data['kwargs'] = str(kwargs)[:200]
            
            logger.log(getattr(logging, level.value), 
                      f"함수 시작: {func.__name__}", 
                      extra={'category': category.value, 'data': log_data})
            
            try:
                result = func(*args, **kwargs)
                
                # 함수 완료 로그
                duration = time.time() - start_time
                log_data.update({
                    'end_time': datetime.now().isoformat(),
                    'duration': duration,
                    'status': 'success'
                })
                
                if include_result:
                    log_data['result'] = str(result)[:200]
                
                logger.log(getattr(logging, level.value), 
                          f"함수 완료: {func.__name__} ({duration:.3f}초)", 
                          extra={'category': category.value, 'data': log_data, 'duration': duration})
                
                return result
            
            except Exception as e:
                # 함수 실패 로그
                duration = time.time() - start_time
                log_data.update({
                    'end_time': datetime.now().isoformat(),
                    'duration': duration,
                    'status': 'error',
                    'error': str(e)
                })
                
                logger.error(f"함수 실패: {func.__name__} - {e}", 
                           extra={'category': category.value, 'data': log_data, 'duration': duration})
                raise
        
        return wrapper
    return decorator

# =============================================================================
# 7. 전역 로그 매니저
# =============================================================================

# 전역 로그 매니저 인스턴스
GLOBAL_LOG_MANAGER = LogManager()

def get_logger(name: str, category: LogCategory = LogCategory.SYSTEM) -> logging.Logger:
    """전역 로거 반환"""
    return GLOBAL_LOG_MANAGER.get_logger(name, category)

def get_log_stats() -> Dict[str, Any]:
    """전역 로그 통계 조회"""
    return GLOBAL_LOG_MANAGER.get_stats()

def get_error_summary() -> Dict[str, Any]:
    """전역 에러 요약 조회"""
    return GLOBAL_LOG_MANAGER.get_error_summary()

# =============================================================================
# 8. 사용 예시
# =============================================================================

if __name__ == "__main__":
    # 로거 생성
    logger = get_logger(__name__, LogCategory.SYSTEM)
    
    # 기본 로깅
    logger.info("시스템 시작")
    logger.warning("경고 메시지")
    logger.error("에러 메시지")
    
    # 구조화된 로깅
    logger.info("API 호출", extra={
        'category': LogCategory.API.value,
        'data': {
            'endpoint': '/api/stocks',
            'method': 'GET',
            'status_code': 200,
            'response_time': 0.5
        }
    })
    
    # 함수 로깅 데코레이터 사용
    @log_function(LogCategory.ANALYSIS, LogLevel.INFO, include_args=True)
    def analyze_stock(symbol: str, days: int = 30):
        """주식 분석 함수"""
        time.sleep(0.1)  # 시뮬레이션
        return {"symbol": symbol, "score": 85.5}
    
    # 함수 실행
    result = analyze_stock("005930", 30)
    print(f"분석 결과: {result}")
    
    # 로그 통계 출력
    stats = get_log_stats()
    print(f"로그 통계: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    # 에러 요약 출력
    error_summary = get_error_summary()
    print(f"에러 요약: {json.dumps(error_summary, indent=2, ensure_ascii=False)}")
