# performance_optimizer.py
"""
성능 최적화 유틸리티 모듈
- 중복 코드 제거
- 메모리 효율성 개선
- 캐싱 전략 최적화
- 병렬 처리 개선
"""

import functools
import time
import threading
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class LRUCache(Generic[T]):
    """스레드 안전한 LRU 캐시 구현"""
    
    def __init__(self, max_size: int = 1000, ttl: float = 3600.0):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, tuple[T, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._last_cleanup = time.time()
    
    def get(self, key: str) -> Optional[T]:
        """캐시에서 값 조회"""
        with self._lock:
            self._cleanup_expired()
            
            if key in self._cache:
                value, timestamp = self._cache.pop(key)
                # TTL 체크
                if time.time() - timestamp < self.ttl:
                    self._cache[key] = (value, timestamp)
                    return value
                else:
                    # 만료된 항목 제거
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: T) -> None:
        """캐시에 값 저장"""
        with self._lock:
            self._cleanup_expired()
            
            # 기존 항목이 있으면 제거
            if key in self._cache:
                del self._cache[key]
            
            # 새 항목 추가
            self._cache[key] = (value, time.time())
            
            # 크기 제한 확인
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
    
    def _cleanup_expired(self) -> None:
        """만료된 항목들 정리"""
        current_time = time.time()
        if current_time - self._last_cleanup < 60:  # 1분마다 정리
            return
        
        expired_keys = []
        for key, (_, timestamp) in self._cache.items():
            if current_time - timestamp >= self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        self._last_cleanup = current_time
    
    def clear(self) -> None:
        """캐시 전체 삭제"""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """현재 캐시 크기"""
        with self._lock:
            return len(self._cache)

class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
        self._lock = threading.RLock()
    
    def record_time(self, operation: str, duration: float) -> None:
        """작업 시간 기록"""
        with self._lock:
            if operation not in self._metrics:
                self._metrics[operation] = []
            self._metrics[operation].append(duration)
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """통계 정보 조회"""
        with self._lock:
            if operation not in self._metrics or not self._metrics[operation]:
                return {}
            
            times = self._metrics[operation]
            return {
                'count': len(times),
                'avg': sum(times) / len(times),
                'min': min(times),
                'max': max(times),
                'total': sum(times)
            }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """모든 작업의 통계 정보"""
        with self._lock:
            return {op: self.get_stats(op) for op in self._metrics.keys()}

def timed_operation(operation_name: str = None):
    """작업 시간 측정 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                monitor.record_time(name, duration)
                if duration > 1.0:  # 1초 이상 걸리는 작업 로깅
                    logger.warning(f"Slow operation: {name} took {duration:.2f}s")
        return wrapper
    return decorator

def memoize_with_ttl(ttl: float = 3600.0, max_size: int = 1000):
    """TTL이 있는 메모이제이션 데코레이터"""
    def decorator(func: Callable) -> Callable:
        cache = LRUCache(max_size=max_size, ttl=ttl)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 캐시에서 조회
            result = cache.get(key)
            if result is not None:
                return result
            
            # 캐시에 없으면 실행
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        wrapper.cache_clear = cache.clear
        wrapper.cache_size = cache.size
        return wrapper
    return decorator

class BatchProcessor:
    """배치 처리 최적화 클래스"""
    
    def __init__(self, batch_size: int = 100, max_wait_time: float = 1.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self._pending_items: List[Any] = []
        self._last_batch_time = time.time()
        self._lock = threading.RLock()
        self._processor: Optional[Callable] = None
    
    def set_processor(self, processor: Callable[[List[Any]], None]) -> None:
        """배치 처리 함수 설정"""
        self._processor = processor
    
    def add_item(self, item: Any) -> None:
        """아이템 추가"""
        with self._lock:
            self._pending_items.append(item)
            
            # 배치 크기 또는 시간 조건 확인
            current_time = time.time()
            should_process = (
                len(self._pending_items) >= self.batch_size or
                (self._pending_items and current_time - self._last_batch_time >= self.max_wait_time)
            )
            
            if should_process and self._processor:
                self._process_batch()
    
    def _process_batch(self) -> None:
        """배치 처리 실행"""
        if not self._pending_items or not self._processor:
            return
        
        items_to_process = self._pending_items.copy()
        self._pending_items.clear()
        self._last_batch_time = time.time()
        
        try:
            self._processor(items_to_process)
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            # 실패한 아이템들을 다시 추가
            self._pending_items.extend(items_to_process)
    
    def flush(self) -> None:
        """대기 중인 모든 아이템 처리"""
        with self._lock:
            if self._pending_items and self._processor:
                self._process_batch()

class MemoryOptimizer:
    """메모리 사용량 최적화 클래스"""
    
    @staticmethod
    def optimize_dataframe_memory(df) -> None:
        """DataFrame 메모리 사용량 최적화"""
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
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """현재 메모리 사용량 조회"""
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }

# 전역 인스턴스들
monitor = PerformanceMonitor()
global_cache = LRUCache(max_size=2000, ttl=3600.0)

# 편의 함수들
def get_performance_stats() -> Dict[str, Dict[str, float]]:
    """성능 통계 조회"""
    return monitor.get_all_stats()

def clear_global_cache() -> None:
    """전역 캐시 삭제"""
    global_cache.clear()

def get_cache_stats() -> Dict[str, int]:
    """캐시 통계 조회"""
    return {
        'size': global_cache.size(),
        'max_size': global_cache.max_size
    }
