# enhanced_error_handler.py
"""
향상된 에러 핸들러 모듈
- 기존 error_handling.py를 확장하여 enhanced_integrated_analyzer_refactored.py에서 요구하는 인터페이스 제공
- 표준화된 예외 처리
- 재시도 메커니즘
- 서킷 브레이커 패턴
"""

import time
import logging
import traceback
from typing import Any, Callable, Optional, Dict, List, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from functools import wraps
import random

# 기존 error_handling 모듈의 클래스들을 import
from error_handling import (
    AnalysisError, DataProviderError, APIRateLimitError, APITimeoutError,
    DataValidationError, ConfigurationError, CacheError,
    ErrorSeverity, ErrorCategory, ErrorContext, RetryStrategy,
    RetryableError, ErrorRecoveryStrategy, ErrorHandler,
    handle_errors as base_handle_errors, retry_on_failure as base_retry_on_failure
)

logger = logging.getLogger(__name__)

# =============================================================================
# 1. 향상된 에러 핸들러 클래스
# =============================================================================

class EnhancedErrorHandler(ErrorHandler):
    """향상된 에러 핸들러 - 기존 ErrorHandler를 확장"""
    
    def __init__(self):
        super().__init__()
        self.circuit_breakers = {}
        self.performance_metrics = {
            'total_errors': 0,
            'recovered_errors': 0,
            'circuit_breaker_trips': 0
        }
    
    def handle_error_with_recovery(self, 
                                 error: Exception, 
                                 context: ErrorContext,
                                 recovery_strategy: str = "retry") -> Optional[Any]:
        """복구 전략을 포함한 에러 처리"""
        self.performance_metrics['total_errors'] += 1
        
        # 기본 에러 처리
        result = self.handle_error(error, context)
        
        # 복구 전략 적용
        if recovery_strategy == "retry" and isinstance(error, RetryableError):
            self.performance_metrics['recovered_errors'] += 1
            logger.info(f"에러 복구 시도: {error}")
        
        return result
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """향상된 통계 정보"""
        base_stats = self.get_error_stats()
        base_stats.update(self.performance_metrics)
        return base_stats

# =============================================================================
# 2. 재시도 설정 클래스
# =============================================================================

@dataclass
class RetryConfig:
    """재시도 설정"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def to_retry_strategy(self) -> RetryStrategy:
        """RetryStrategy로 변환"""
        return RetryStrategy(
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            exponential_base=self.exponential_base,
            jitter=self.jitter
        )

# =============================================================================
# 3. 서킷 브레이커 설정 클래스
# =============================================================================

@dataclass
class CircuitBreakerConfig:
    """서킷 브레이커 설정"""
    max_failures: int = 5
    timeout: float = 60.0
    name: str = "default"

# =============================================================================
# 4. 향상된 데코레이터들
# =============================================================================

def retry_on_failure(max_retries: int = 3, 
                    max_attempts: int = None,  # Backward compatibility
                    base_delay: float = 1.0,
                    max_delay: float = 60.0,
                    exponential_base: float = 2.0,
                    jitter: bool = True):
    """향상된 재시도 데코레이터"""
    # Backward compatibility: max_attempts -> max_retries
    if max_attempts is not None:
        max_retries = max_attempts
    
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter
    )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            strategy = config.to_retry_strategy()
            return ErrorRecoveryStrategy.retry_with_backoff(
                func, strategy, *args, **kwargs
            )
        return wrapper
    return decorator

def handle_errors(category: ErrorCategory, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 operation: str = None,
                 retry_config: Optional[RetryConfig] = None):
    """향상된 에러 처리 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = EnhancedErrorHandler()
            context = ErrorContext(
                category=category,
                severity=severity,
                operation=operation or func.__name__
            )
            
            try:
                if retry_config:
                    strategy = retry_config.to_retry_strategy()
                    return ErrorRecoveryStrategy.retry_with_backoff(
                        func, strategy, *args, **kwargs
                    )
                else:
                    return func(*args, **kwargs)
            
            except Exception as e:
                # 에러 컨텍스트 업데이트
                if hasattr(e, 'symbol'):
                    context.symbol = e.symbol
                
                result = error_handler.handle_error_with_recovery(e, context)
                if result is not None:
                    return result
                else:
                    raise e
        
        return wrapper
    return decorator

def circuit_breaker(max_failures: int = 5, 
                   timeout: float = 60.0,
                   name: str = "default"):
    """향상된 서킷 브레이커 데코레이터"""
    config = CircuitBreakerConfig(
        max_failures=max_failures,
        timeout=timeout,
        name=name
    )
    
    def decorator(func: Callable) -> Callable:
        failures = 0
        last_failure_time = 0
        state = "closed"  # closed, open, half-open
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal failures, last_failure_time, state
            
            current_time = time.time()
            
            # 서킷이 열려있고 타임아웃이 지나지 않았으면 실패 반환
            if state == "open" and current_time - last_failure_time < config.timeout:
                raise Exception(f"서킷 브레이커 '{config.name}'가 열려있음")
            
            # 서킷이 열려있고 타임아웃이 지났으면 반열림 상태로 전환
            if state == "open" and current_time - last_failure_time >= config.timeout:
                state = "half-open"
                logger.info(f"서킷 브레이커 '{config.name}' 반열림 상태로 전환")
            
            try:
                result = func(*args, **kwargs)
                
                # 성공 시 서킷 닫기
                if state == "half-open":
                    state = "closed"
                    failures = 0
                    logger.info(f"서킷 브레이커 '{config.name}' 닫힘")
                
                return result
            
            except Exception as e:
                failures += 1
                last_failure_time = current_time
                
                # 실패 횟수가 임계값을 초과하면 서킷 열기
                if failures >= config.max_failures:
                    state = "open"
                    logger.error(f"서킷 브레이커 '{config.name}' 열림 "
                               f"({failures}회 연속 실패)")
                
                raise e
        
        return wrapper
    return decorator

# =============================================================================
# 5. 전역 인스턴스 및 유틸리티 함수
# =============================================================================

# 전역 향상된 에러 핸들러
GLOBAL_ENHANCED_ERROR_HANDLER = EnhancedErrorHandler()

def get_global_handler() -> EnhancedErrorHandler:
    """전역 에러 핸들러 반환"""
    return GLOBAL_ENHANCED_ERROR_HANDLER

def setup_enhanced_error_handling():
    """향상된 에러 핸들링 설정"""
    import sys
    
    def enhanced_exception_handler(exc_type, exc_value, exc_traceback):
        """향상된 전역 예외 핸들러"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        context = ErrorContext(
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            operation="global_exception"
        )
        
        GLOBAL_ENHANCED_ERROR_HANDLER.handle_error_with_recovery(exc_value, context)
        
        # 기본 핸들러도 호출
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = enhanced_exception_handler

# =============================================================================
# 6. 편의 함수들
# =============================================================================

def safe_execute(func: Callable, 
                default_value: Any = None,
                error_category: ErrorCategory = ErrorCategory.SYSTEM,
                error_severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> Any:
    """안전한 함수 실행"""
    try:
        return func()
    except Exception as e:
        context = ErrorContext(
            category=error_category,
            severity=error_severity,
            operation=func.__name__
        )
        GLOBAL_ENHANCED_ERROR_HANDLER.handle_error(e, context)
        return default_value

def log_error(error: Exception, 
              operation: str = "unknown",
              symbol: str = None,
              category: ErrorCategory = ErrorCategory.SYSTEM,
              severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """에러 로깅"""
    context = ErrorContext(
        category=category,
        severity=severity,
        operation=operation,
        symbol=symbol
    )
    GLOBAL_ENHANCED_ERROR_HANDLER.handle_error(error, context)

# =============================================================================
# 7. 사용 예시 및 테스트
# =============================================================================

if __name__ == "__main__":
    # 향상된 에러 핸들링 설정
    setup_enhanced_error_handling()
    
    # 예시: 향상된 API 호출 함수
    @handle_errors(
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.MEDIUM,
        operation="enhanced_api_call",
        retry_config=RetryConfig(max_retries=5, base_delay=0.5)
    )
    @circuit_breaker(max_failures=3, timeout=30.0, name="api_circuit")
    def enhanced_api_call(symbol: str) -> Dict[str, Any]:
        """향상된 API 호출 예시"""
        if random.random() < 0.4:  # 40% 확률로 실패
            raise APIRateLimitError("API 호출 제한", retry_after=2.0)
        
        return {"symbol": symbol, "data": "success", "timestamp": time.time()}
    
    # 테스트
    try:
        result = enhanced_api_call("005930")
        print(f"향상된 API 호출 성공: {result}")
    except Exception as e:
        print(f"향상된 API 호출 실패: {e}")
    
    # 향상된 에러 통계 출력
    stats = GLOBAL_ENHANCED_ERROR_HANDLER.get_enhanced_stats()
    print(f"향상된 에러 통계: {stats}")
