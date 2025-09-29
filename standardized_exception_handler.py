#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standardized Exception Handler
- 통일된 예외 처리 시스템
- 자동 재시도 로직
- 구조화된 에러 로깅
- 복구 전략
"""

import time
import logging
import traceback
import functools
import threading
from typing import Any, Callable, Optional, Dict, List, Tuple, Type, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import random

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """에러 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """에러 카테고리"""
    API = "api"
    DATA = "data"
    NETWORK = "network"
    VALIDATION = "validation"
    SYSTEM = "system"
    BUSINESS = "business"

class RetryStrategy(Enum):
    """재시도 전략"""
    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"

@dataclass
class RetryConfig:
    """재시도 설정"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL

@dataclass
class ErrorContext:
    """에러 컨텍스트"""
    category: ErrorCategory
    severity: ErrorSeverity
    operation: str
    symbol: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ErrorRecord:
    """에러 기록"""
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    operation: str
    symbol: Optional[str]
    error_type: str
    error_message: str
    traceback: str
    retry_count: int = 0
    resolved: bool = False

class StandardizedExceptionHandler:
    """
    표준화된 예외 처리기
    - 통일된 에러 처리
    - 자동 재시도
    - 에러 통계
    - 복구 전략
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._error_history: List[ErrorRecord] = []
        self._error_counts: Dict[str, int] = {}
        self._max_history = 1000
        
        # 회로 차단기 (Circuit Breaker)
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # 전역 예외 핸들러 설정
        self._setup_global_handler()
    
    def _setup_global_handler(self):
        """전역 예외 핸들러 설정"""
        import sys
        
        def global_exception_handler(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            context = ErrorContext(
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                operation="global_exception"
            )
            
            self.handle_error(exc_value, context)
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        
        sys.excepthook = global_exception_handler
    
    def handle_error(self, error: Exception, context: ErrorContext) -> Optional[Any]:
        """에러 처리"""
        with self._lock:
            # 에러 기록
            error_record = ErrorRecord(
                timestamp=context.timestamp,
                category=context.category,
                severity=context.severity,
                operation=context.operation,
                symbol=context.symbol,
                error_type=type(error).__name__,
                error_message=str(error),
                traceback=traceback.format_exc()
            )
            
            self._error_history.append(error_record)
            
            # 히스토리 크기 제한
            if len(self._error_history) > self._max_history:
                self._error_history = self._error_history[-self._max_history:]
            
            # 에러 카운트 증가
            error_key = f"{context.category.value}:{type(error).__name__}"
            self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
            
            # 심각도별 로깅
            self._log_error(error, context, error_record)
            
            return None
    
    def _log_error(self, error: Exception, context: ErrorContext, record: ErrorRecord):
        """에러 로깅"""
        log_message = (f"[{context.category.value.upper()}] {context.operation}: {error}")
        
        if context.symbol:
            log_message += f" (symbol: {context.symbol})"
        
        if context.metadata:
            log_message += f" (metadata: {context.metadata})"
        
        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=True)
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(log_message, exc_info=True)
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def retry_with_backoff(self, 
                          func: Callable, 
                          retry_config: RetryConfig,
                          *args, **kwargs) -> Any:
        """백오프 재시도"""
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                if attempt == retry_config.max_attempts - 1:
                    # 마지막 시도에서도 실패
                    context = ErrorContext(
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.HIGH,
                        operation=func.__name__,
                        metadata={'retry_count': attempt + 1}
                    )
                    self.handle_error(e, context)
                    raise e
                
                # 재시도 대기
                delay = self._calculate_delay(attempt, retry_config)
                logger.warning(f"Retry {attempt + 1}/{retry_config.max_attempts} "
                             f"after {delay:.2f}s: {e}")
                time.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """재시도 지연 시간 계산"""
        if config.strategy == RetryStrategy.LINEAR:
            delay = config.base_delay * (attempt + 1)
        elif config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.base_delay * (config.backoff_multiplier ** attempt)
        elif config.strategy == RetryStrategy.FIBONACCI:
            delay = config.base_delay * self._fibonacci(attempt + 1)
        else:
            delay = config.base_delay
        
        # 최대 지연 시간 제한
        delay = min(delay, config.max_delay)
        
        # 지터 추가
        if config.jitter:
            delay += random.uniform(0, delay * 0.1)
        
        return delay
    
    def _fibonacci(self, n: int) -> int:
        """피보나치 수열"""
        if n <= 1:
            return n
        return self._fibonacci(n - 1) + self._fibonacci(n - 2)
    
    def circuit_breaker(self, 
                       operation: str,
                       max_failures: int = 5,
                       timeout: float = 60.0):
        """회로 차단기 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self._lock:
                    cb_key = f"{operation}:{func.__name__}"
                    
                    if cb_key not in self._circuit_breakers:
                        self._circuit_breakers[cb_key] = {
                            'failures': 0,
                            'last_failure': None,
                            'state': 'closed'  # closed, open, half-open
                        }
                    
                    cb = self._circuit_breakers[cb_key]
                    
                    # 회로가 열려있는지 확인
                    if cb['state'] == 'open':
                        if time.time() - cb['last_failure'] < timeout:
                            raise Exception(f"Circuit breaker open for {operation}")
                        else:
                            cb['state'] = 'half-open'
                    
                    try:
                        result = func(*args, **kwargs)
                        
                        # 성공 시 회로 닫기
                        if cb['state'] == 'half-open':
                            cb['state'] = 'closed'
                            cb['failures'] = 0
                        
                        return result
                    
                    except Exception as e:
                        cb['failures'] += 1
                        cb['last_failure'] = time.time()
                        
                        if cb['failures'] >= max_failures:
                            cb['state'] = 'open'
                            logger.error(f"Circuit breaker opened for {operation} "
                                       f"after {max_failures} failures")
                        
                        raise e
            
            return wrapper
        return decorator
    
    def get_error_stats(self) -> Dict[str, Any]:
        """에러 통계 반환"""
        with self._lock:
            total_errors = len(self._error_history)
            recent_errors = [e for e in self._error_history 
                           if (datetime.now() - e.timestamp).total_seconds() < 3600]
            
            severity_counts = {}
            category_counts = {}
            
            for error in self._error_history:
                severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
                category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            
            return {
                'total_errors': total_errors,
                'recent_errors_1h': len(recent_errors),
                'error_counts_by_type': self._error_counts,
                'severity_distribution': severity_counts,
                'category_distribution': category_counts,
                'recent_errors': [self._error_to_dict(e) for e in self._error_history[-10:]]
            }
    
    def _error_to_dict(self, error: ErrorRecord) -> Dict[str, Any]:
        """에러 레코드를 딕셔너리로 변환"""
        return {
            'timestamp': error.timestamp.isoformat(),
            'category': error.category.value,
            'severity': error.severity.value,
            'operation': error.operation,
            'symbol': error.symbol,
            'error_type': error.error_type,
            'error_message': error.error_message,
            'retry_count': error.retry_count,
            'resolved': error.resolved
        }
    
    def clear_history(self):
        """에러 히스토리 초기화"""
        with self._lock:
            self._error_history.clear()
            self._error_counts.clear()

# 전역 예외 처리기 인스턴스
_global_handler = None
_handler_lock = threading.Lock()

def get_global_handler() -> StandardizedExceptionHandler:
    """전역 예외 처리기 반환"""
    global _global_handler
    
    if _global_handler is None:
        with _handler_lock:
            if _global_handler is None:
                _global_handler = StandardizedExceptionHandler()
    
    return _global_handler

# 편의 함수들
def handle_errors(category: ErrorCategory, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 operation: str = None,
                 retry_config: Optional[RetryConfig] = None):
    """에러 처리 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_global_handler()
            context = ErrorContext(
                category=category,
                severity=severity,
                operation=operation or func.__name__
            )
            
            try:
                if retry_config:
                    return handler.retry_with_backoff(func, retry_config, *args, **kwargs)
                else:
                    return func(*args, **kwargs)
            
            except Exception as e:
                handler.handle_error(e, context)
                raise e
        
        return wrapper
    return decorator

def retry_on_failure(max_attempts: int = 3, 
                    base_delay: float = 1.0,
                    max_delay: float = 60.0,
                    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL):
    """재시도 데코레이터"""
    retry_config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=strategy
    )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_global_handler()
            return handler.retry_with_backoff(func, retry_config, *args, **kwargs)
        
        return wrapper
    return decorator

def circuit_breaker(operation: str, max_failures: int = 5, timeout: float = 60.0):
    """회로 차단기 데코레이터"""
    def decorator(func: Callable) -> Callable:
        handler = get_global_handler()
        return handler.circuit_breaker(operation, max_failures, timeout)(func)
    return decorator
