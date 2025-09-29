# code_optimizer.py
"""
코드 최적화 유틸리티 모듈
- 중복 코드 제거
- 성능 최적화
- 메모리 효율성 개선
- 코드 품질 향상
"""

import functools
import time
import threading
from typing import Any, Dict, List, Optional, Callable, TypeVar, Union
from collections import defaultdict, OrderedDict
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CodeOptimizer:
    """코드 최적화 클래스"""
    
    def __init__(self):
        self._cache = {}
        self._lock = threading.RLock()
        self._performance_stats = defaultdict(list)
    
    def memoize(self, func: Callable) -> Callable:
        """메모이제이션 데코레이터"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            with self._lock:
                if key in self._cache:
                    return self._cache[key]
                
                result = func(*args, **kwargs)
                self._cache[key] = result
                return result
        
        wrapper.cache_clear = lambda: self._cache.clear()
        return wrapper
    
    def batch_process(self, items: List[Any], batch_size: int = 100, 
                     processor: Callable = None) -> List[Any]:
        """배치 처리 최적화"""
        if not processor:
            return items
        
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_result = processor(batch)
            results.extend(batch_result)
        
        return results
    
    def parallel_process(self, items: List[Any], processor: Callable, 
                        max_workers: int = None) -> List[Any]:
        """병렬 처리 최적화"""
        import concurrent.futures
        
        if max_workers is None:
            max_workers = min(len(items), 4)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(processor, item) for item in items]
            results = [future.result() for future in futures]
        
        return results
    
    def measure_performance(self, func: Callable) -> Callable:
        """성능 측정 데코레이터"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            with self._lock:
                self._performance_stats[func.__name__].append(duration)
            
            if duration > 1.0:  # 1초 이상 걸리는 작업 로깅
                logger.warning(f"Slow operation: {func.__name__} took {duration:.2f}s")
            
            return result
        
        return wrapper
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """성능 통계 조회"""
        with self._lock:
            stats = {}
            for func_name, durations in self._performance_stats.items():
                if durations:
                    stats[func_name] = {
                        'count': len(durations),
                        'avg': sum(durations) / len(durations),
                        'min': min(durations),
                        'max': max(durations),
                        'total': sum(durations)
                    }
            return stats

class DataProcessor:
    """데이터 처리 최적화 클래스"""
    
    @staticmethod
    def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """DataFrame 최적화"""
        # 메모리 사용량 최적화
        for col in df.columns:
            col_type = df[col].dtype
            
            if col_type != 'object':
                c_min = df[col].min()
                c_max = df[col].max()
                
                if str(col_type)[:3] == 'int':
                    if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                        df[col] = df[col].astype(np.int8)
                    elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                        df[col] = df[col].astype(np.int16)
                    elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                        df[col] = df[col].astype(np.int32)
                    elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max:
                        df[col] = df[col].astype(np.int64)
                else:
                    if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                        df[col] = df[col].astype(np.float16)
                    elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                        df[col] = df[col].astype(np.float32)
                    else:
                        df[col] = df[col].astype(np.float64)
        
        return df
    
    @staticmethod
    def chunked_processing(data: List[Any], chunk_size: int = 1000, 
                          processor: Callable = None) -> List[Any]:
        """청크 단위 처리"""
        if not processor:
            return data
        
        results = []
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            chunk_result = processor(chunk)
            results.extend(chunk_result)
        
        return results
    
    @staticmethod
    def safe_divide(numerator: Any, denominator: Any, default: float = 0.0) -> float:
        """안전한 나눗셈"""
        try:
            if denominator == 0 or denominator is None:
                return default
            return float(numerator) / float(denominator)
        except (ValueError, TypeError, ZeroDivisionError):
            return default
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """안전한 float 변환"""
        if value is None or pd.isna(value):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

class MemoryOptimizer:
    """메모리 최적화 클래스"""
    
    @staticmethod
    def optimize_memory_usage():
        """메모리 사용량 최적화"""
        import gc
        gc.collect()
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """메모리 사용량 조회"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss': memory_info.rss / 1024 / 1024,  # MB
                'vms': memory_info.vms / 1024 / 1024,  # MB
                'percent': process.memory_percent()
            }
        except ImportError:
            return {'rss': 0, 'vms': 0, 'percent': 0}
    
    @staticmethod
    def monitor_memory(func: Callable) -> Callable:
        """메모리 모니터링 데코레이터"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            before = MemoryOptimizer.get_memory_usage()
            result = func(*args, **kwargs)
            after = MemoryOptimizer.get_memory_usage()
            
            memory_diff = after['rss'] - before['rss']
            if memory_diff > 100:  # 100MB 이상 증가 시 로깅
                logger.warning(f"Memory usage increased by {memory_diff:.1f}MB in {func.__name__}")
            
            return result
        
        return wrapper

class CodeQualityImprover:
    """코드 품질 개선 클래스"""
    
    @staticmethod
    def validate_input(value: Any, expected_type: type, default: Any = None) -> Any:
        """입력 검증"""
        if value is None:
            return default
        
        try:
            if isinstance(value, expected_type):
                return value
            else:
                return expected_type(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
        """안전한 딕셔너리 접근"""
        try:
            return dictionary.get(key, default)
        except (AttributeError, TypeError):
            return default
    
    @staticmethod
    def retry_on_failure(max_retries: int = 3, delay: float = 1.0, 
                        backoff: float = 2.0) -> Callable:
        """재시도 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries:
                            logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                            time.sleep(current_delay)
                            current_delay *= backoff
                        else:
                            logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                
                raise last_exception
            
            return wrapper
        return decorator

# 전역 인스턴스
optimizer = CodeOptimizer()

# 편의 함수들
def memoize(func: Callable) -> Callable:
    """메모이제이션 데코레이터"""
    return optimizer.memoize(func)

def measure_performance(func: Callable) -> Callable:
    """성능 측정 데코레이터"""
    return optimizer.measure_performance(func)

def monitor_memory(func: Callable) -> Callable:
    """메모리 모니터링 데코레이터"""
    return MemoryOptimizer.monitor_memory(func)

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0) -> Callable:
    """재시도 데코레이터"""
    return CodeQualityImprover.retry_on_failure(max_retries, delay, backoff)

def get_performance_stats() -> Dict[str, Dict[str, float]]:
    """성능 통계 조회"""
    return optimizer.get_performance_stats()

def optimize_memory():
    """메모리 최적화"""
    MemoryOptimizer.optimize_memory_usage()

def get_memory_usage() -> Dict[str, float]:
    """메모리 사용량 조회"""
    return MemoryOptimizer.get_memory_usage()

