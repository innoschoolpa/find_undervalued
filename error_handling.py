# error_handling.py
"""
향상된 에러 처리 시스템
- 구체적인 예외 클래스 정의
- 재시도 메커니즘
- 에러 복구 전략
- 구조화된 로깅
"""

import time
import logging
import traceback
from typing import Any, Callable, Optional, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass
from functools import wraps
import random

logger = logging.getLogger(__name__)

# =============================================================================
# 1. 커스텀 예외 클래스들
# =============================================================================

class AnalysisError(Exception):
    """분석 관련 기본 예외"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

class DataProviderError(AnalysisError):
    """데이터 제공자 관련 예외"""
    pass

class APIRateLimitError(DataProviderError):
    """API 호출 제한 예외"""
    def __init__(self, message: str, retry_after: float = None):
        super().__init__(message, "RATE_LIMIT")
        self.retry_after = retry_after

class APITimeoutError(DataProviderError):
    """API 타임아웃 예외"""
    def __init__(self, message: str, timeout: float = None):
        super().__init__(message, "TIMEOUT")
        self.timeout = timeout

class DataValidationError(AnalysisError):
    """데이터 검증 예외"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
        self.value = value

class ConfigurationError(AnalysisError):
    """설정 관련 예외"""
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, "CONFIG_ERROR")
        self.config_key = config_key

class CacheError(AnalysisError):
    """캐시 관련 예외"""
    def __init__(self, message: str, cache_key: str = None):
        super().__init__(message, "CACHE_ERROR")
        self.cache_key = cache_key

# =============================================================================
# 2. 에러 분류 및 심각도
# =============================================================================

class ErrorSeverity(Enum):
    """에러 심각도"""
    LOW = "low"           # 경고 수준, 계속 진행 가능
    MEDIUM = "medium"     # 중간 수준, 일부 기능 제한
    HIGH = "high"         # 높은 수준, 주요 기능 실패
    CRITICAL = "critical" # 치명적, 시스템 중단

class ErrorCategory(Enum):
    """에러 카테고리"""
    NETWORK = "network"
    DATA = "data"
    CONFIG = "config"
    BUSINESS = "business"
    SYSTEM = "system"

@dataclass
class ErrorContext:
    """에러 컨텍스트 정보"""
    category: ErrorCategory
    severity: ErrorSeverity
    operation: str
    symbol: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

# =============================================================================
# 3. 재시도 전략
# =============================================================================

class RetryStrategy:
    """재시도 전략 클래스"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """재시도 지연 시간 계산"""
        if attempt <= 0:
            return 0
        
        # 지수 백오프
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        # 지터 추가 (동시성 충돌 방지)
        if self.jitter:
            jitter_factor = random.uniform(0.5, 1.5)
            delay *= jitter_factor
        
        return delay

class RetryableError(Exception):
    """재시도 가능한 에러"""
    def __init__(self, message: str, retry_after: float = None):
        super().__init__(message)
        self.retry_after = retry_after

# =============================================================================
# 4. 에러 복구 전략
# =============================================================================

class ErrorRecoveryStrategy:
    """에러 복구 전략"""
    
    @staticmethod
    def retry_with_backoff(func: Callable, 
                          strategy: RetryStrategy,
                          *args, **kwargs) -> Any:
        """지수 백오프를 사용한 재시도"""
        last_exception = None
        
        for attempt in range(strategy.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except RetryableError as e:
                last_exception = e
                if attempt < strategy.max_retries:
                    delay = strategy.get_delay(attempt + 1)
                    if e.retry_after:
                        delay = max(delay, e.retry_after)
                    
                    logger.warning(f"재시도 {attempt + 1}/{strategy.max_retries} "
                                 f"({delay:.2f}초 후): {e}")
                    time.sleep(delay)
                else:
                    break
            except Exception as e:
                # 재시도 불가능한 에러
                raise e
        
        # 모든 재시도 실패
        raise last_exception or Exception("재시도 실패")
    
    @staticmethod
    def fallback_value(default_value: Any, 
                      error_types: Tuple[type, ...] = None) -> Callable:
        """폴백 값을 반환하는 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except error_types or Exception as e:
                    logger.warning(f"폴백 값 사용: {func.__name__} - {e}")
                    return default_value
            return wrapper
        return decorator
    
    @staticmethod
    def circuit_breaker(max_failures: int = 5, 
                       timeout: float = 60.0) -> Callable:
        """서킷 브레이커 패턴"""
        def decorator(func: Callable) -> Callable:
            failures = 0
            last_failure_time = 0
            state = "closed"  # closed, open, half-open
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                nonlocal failures, last_failure_time, state
                
                current_time = time.time()
                
                # 서킷이 열려있고 타임아웃이 지나지 않았으면 실패 반환
                if state == "open" and current_time - last_failure_time < timeout:
                    raise Exception("서킷 브레이커가 열려있음")
                
                # 서킷이 열려있고 타임아웃이 지났으면 반열림 상태로 전환
                if state == "open" and current_time - last_failure_time >= timeout:
                    state = "half-open"
                
                try:
                    result = func(*args, **kwargs)
                    
                    # 성공 시 서킷 닫기
                    if state == "half-open":
                        state = "closed"
                        failures = 0
                    
                    return result
                
                except Exception as e:
                    failures += 1
                    last_failure_time = current_time
                    
                    # 실패 횟수가 임계값을 초과하면 서킷 열기
                    if failures >= max_failures:
                        state = "open"
                        logger.error(f"서킷 브레이커 열림: {func.__name__} "
                                   f"({failures}회 연속 실패)")
                    
                    raise e
            
            return wrapper
        return decorator

# =============================================================================
# 5. 에러 핸들러
# =============================================================================

class ErrorHandler:
    """에러 핸들러 클래스"""
    
    def __init__(self):
        self.error_counts = {}
        self.error_history = []
        self.max_history = 1000
    
    def handle_error(self, 
                    error: Exception, 
                    context: ErrorContext) -> Optional[Any]:
        """에러 처리"""
        # 에러 카운트 증가
        error_key = f"{context.category.value}:{type(error).__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # 에러 히스토리 저장
        self.error_history.append({
            'timestamp': context.timestamp,
            'category': context.category.value,
            'severity': context.severity.value,
            'operation': context.operation,
            'symbol': context.symbol,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        })
        
        # 히스토리 크기 제한
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
        
        # 심각도별 처리
        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"치명적 에러: {error} (컨텍스트: {context})")
            return None
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(f"높은 심각도 에러: {error} (컨텍스트: {context})")
            return None
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"중간 심각도 에러: {error} (컨텍스트: {context})")
            return None
        else:
            logger.info(f"낮은 심각도 에러: {error} (컨텍스트: {context})")
            return None
    
    def get_error_stats(self) -> Dict[str, Any]:
        """에러 통계 조회"""
        total_errors = sum(self.error_counts.values())
        
        # 카테고리별 에러 수
        category_counts = {}
        for entry in self.error_history:
            category = entry['category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # 심각도별 에러 수
        severity_counts = {}
        for entry in self.error_history:
            severity = entry['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_errors': total_errors,
            'error_counts': self.error_counts,
            'category_counts': category_counts,
            'severity_counts': severity_counts,
            'recent_errors': self.error_history[-10:]  # 최근 10개 에러
        }

# =============================================================================
# 6. 에러 처리 데코레이터
# =============================================================================

def handle_errors(category: ErrorCategory, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 operation: str = None,
                 retry_strategy: RetryStrategy = None):
    """에러 처리 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            context = ErrorContext(
                category=category,
                severity=severity,
                operation=operation or func.__name__
            )
            
            try:
                if retry_strategy:
                    return ErrorRecoveryStrategy.retry_with_backoff(
                        func, retry_strategy, *args, **kwargs
                    )
                else:
                    return func(*args, **kwargs)
            
            except Exception as e:
                # 에러 컨텍스트 업데이트
                if hasattr(e, 'symbol'):
                    context.symbol = e.symbol
                
                result = error_handler.handle_error(e, context)
                if result is not None:
                    return result
                else:
                    raise e
        
        return wrapper
    return decorator

def retry_on_failure(max_retries: int = 3, 
                    base_delay: float = 1.0,
                    max_delay: float = 60.0):
    """재시도 데코레이터"""
    strategy = RetryStrategy(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay
    )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return ErrorRecoveryStrategy.retry_with_backoff(
                func, strategy, *args, **kwargs
            )
        return wrapper
    return decorator

# =============================================================================
# 7. 전역 에러 핸들러
# =============================================================================

# 전역 에러 핸들러 인스턴스
GLOBAL_ERROR_HANDLER = ErrorHandler()

def setup_global_error_handling():
    """전역 에러 핸들링 설정"""
    import sys
    
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        """전역 예외 핸들러"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        context = ErrorContext(
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            operation="global_exception"
        )
        
        GLOBAL_ERROR_HANDLER.handle_error(exc_value, context)
        
        # 기본 핸들러도 호출
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = global_exception_handler

# =============================================================================
# 8. 사용 예시
# =============================================================================

if __name__ == "__main__":
    # 전역 에러 핸들링 설정
    setup_global_error_handling()
    
    # 예시: API 호출 함수
    @handle_errors(
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.MEDIUM,
        operation="api_call"
    )
    @retry_on_failure(max_retries=3, base_delay=1.0)
    def api_call_example(symbol: str) -> Dict[str, Any]:
        """API 호출 예시"""
        # 실제 API 호출 로직
        if random.random() < 0.3:  # 30% 확률로 실패
            raise APIRateLimitError("API 호출 제한", retry_after=5.0)
        
        return {"symbol": symbol, "data": "success"}
    
    # 예시: 데이터 검증 함수
    @handle_errors(
        category=ErrorCategory.DATA,
        severity=ErrorSeverity.LOW,
        operation="data_validation"
    )
    def validate_data(data: Dict[str, Any]) -> bool:
        """데이터 검증 예시"""
        if not data or 'symbol' not in data:
            raise DataValidationError("필수 필드 누락", field="symbol")
        
        return True
    
    # 테스트
    try:
        result = api_call_example("005930")
        print(f"API 호출 성공: {result}")
    except Exception as e:
        print(f"API 호출 실패: {e}")
    
    # 에러 통계 출력
    stats = GLOBAL_ERROR_HANDLER.get_error_stats()
    print(f"에러 통계: {stats}")

