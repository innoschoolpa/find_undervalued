#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory-Safe Cache System
- 메모리 누수 방지
- 자동 정리 및 크기 제한
- TTL 기반 만료
- 스레드 안전성 보장
"""

import time
import threading
import logging
import weakref
import gc
from collections import OrderedDict, deque
from typing import Any, Optional, Dict, Callable, Union
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    """캐시 설정"""
    max_size: int = 1000
    default_ttl: float = 3600.0  # 1시간
    cleanup_interval: float = 300.0  # 5분
    memory_threshold_mb: float = 512.0  # 512MB
    enable_compression: bool = True
    compression_threshold: int = 1024  # 1KB

class CacheEntry:
    """캐시 엔트리"""
    
    def __init__(self, value: Any, ttl: float, created_at: Optional[float] = None):
        self.value = value
        self.ttl = ttl
        self.created_at = created_at or time.time()
        self.access_count = 0
        self.last_access = self.created_at
        self.size_bytes = self._estimate_size(value)
    
    def _estimate_size(self, value: Any) -> int:
        """값의 크기 추정 (바이트)"""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, dict):
                return sum(self._estimate_size(v) for v in value.values()) + len(value) * 8
            elif isinstance(value, list):
                return sum(self._estimate_size(v) for v in value) + len(value) * 8
            else:
                return len(str(value).encode('utf-8'))
        except Exception:
            return 1024  # 기본값
    
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """접근 시간 업데이트"""
        self.access_count += 1
        self.last_access = time.time()
    
    def get_value(self) -> Any:
        """값 반환 (접근 시간 업데이트)"""
        self.touch()
        return self.value

class MemorySafeCache:
    """
    메모리 안전한 캐시
    - 자동 크기 제한
    - TTL 기반 만료
    - 메모리 사용량 모니터링
    - 스레드 안전성
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        
        # 스레드 안전성
        self._lock = threading.RLock()
        
        # 캐시 저장소
        self._cache = OrderedDict()
        
        # 통계
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0
        self._total_size_bytes = 0
        
        # 정리 스레드
        self._cleanup_thread = None
        self._shutdown_event = threading.Event()
        self._start_cleanup_thread()
        
        logger.info(f"MemorySafeCache initialized: max_size={self.config.max_size}, "
                   f"ttl={self.config.default_ttl}s")
    
    def _start_cleanup_thread(self):
        """정리 스레드 시작"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_worker,
                daemon=True,
                name="CacheCleanup"
            )
            self._cleanup_thread.start()
    
    def _cleanup_worker(self):
        """정리 워커 스레드"""
        while not self._shutdown_event.wait(self.config.cleanup_interval):
            try:
                self._cleanup_expired()
                self._check_memory_usage()
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                if entry.is_expired():
                    # 만료된 엔트리 제거
                    del self._cache[key]
                    self._total_size_bytes -= entry.size_bytes
                    self._miss_count += 1
                    return None
                
                # LRU 업데이트
                self._cache.move_to_end(key)
                self._hit_count += 1
                return entry.get_value()
            
            self._miss_count += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """캐시에 값 저장"""
        if ttl is None:
            ttl = self.config.default_ttl
        
        with self._lock:
            # 기존 엔트리 제거
            if key in self._cache:
                old_entry = self._cache[key]
                self._total_size_bytes -= old_entry.size_bytes
                del self._cache[key]
            
            # 새 엔트리 생성
            entry = CacheEntry(value, ttl)
            self._cache[key] = entry
            self._total_size_bytes += entry.size_bytes
            
            # 크기 제한 확인
            self._enforce_size_limit()
    
    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                self._total_size_bytes -= entry.size_bytes
                return True
            return False
    
    def clear(self) -> None:
        """캐시 전체 삭제"""
        with self._lock:
            self._cache.clear()
            self._total_size_bytes = 0
            self._hit_count = 0
            self._miss_count = 0
            self._eviction_count = 0
    
    def _enforce_size_limit(self):
        """크기 제한 강제 적용"""
        while len(self._cache) > self.config.max_size:
            # LRU 정책으로 가장 오래된 엔트리 제거
            key, entry = self._cache.popitem(last=False)
            self._total_size_bytes -= entry.size_bytes
            self._eviction_count += 1
    
    def _cleanup_expired(self) -> int:
        """만료된 엔트리 정리"""
        cleaned_count = 0
        
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                entry = self._cache[key]
                del self._cache[key]
                self._total_size_bytes -= entry.size_bytes
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.debug(f"Cleaned up {cleaned_count} expired cache entries")
        
        return cleaned_count
    
    def _check_memory_usage(self):
        """메모리 사용량 확인"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.config.memory_threshold_mb:
                logger.warning(f"High memory usage: {memory_mb:.1f}MB > {self.config.memory_threshold_mb}MB")
                
                # 강제 가비지 컬렉션
                gc.collect()
                
                # 캐시 크기 줄이기
                with self._lock:
                    target_size = len(self._cache) // 2
                    while len(self._cache) > target_size:
                        key, entry = self._cache.popitem(last=False)
                        self._total_size_bytes -= entry.size_bytes
                        self._eviction_count += 1
                
                logger.info(f"Reduced cache size to {len(self._cache)} entries")
        
        except ImportError:
            # psutil이 없는 경우 간단한 정리만 수행
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        with self._lock:
            total_requests = self._hit_count + self._miss_count
            hit_rate = (self._hit_count / total_requests * 100 
                       if total_requests > 0 else 0.0)
            
            return {
                'size': len(self._cache),
                'max_size': self.config.max_size,
                'total_size_bytes': self._total_size_bytes,
                'hit_count': self._hit_count,
                'miss_count': self._miss_count,
                'hit_rate_percent': hit_rate,
                'eviction_count': self._eviction_count,
                'config': {
                    'default_ttl': self.config.default_ttl,
                    'cleanup_interval': self.config.cleanup_interval,
                    'memory_threshold_mb': self.config.memory_threshold_mb
                }
            }
    
    def close(self):
        """캐시 종료"""
        self._shutdown_event.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5.0)
        
        with self._lock:
            self._cache.clear()
            self._total_size_bytes = 0
        
        logger.info("MemorySafeCache closed")

# 전역 캐시 인스턴스들
_global_caches: Dict[str, MemorySafeCache] = {}
_cache_lock = threading.Lock()

def get_global_cache(name: str, config: Optional[CacheConfig] = None) -> MemorySafeCache:
    """전역 캐시 인스턴스 반환"""
    with _cache_lock:
        if name not in _global_caches:
            _global_caches[name] = MemorySafeCache(config)
        return _global_caches[name]

def close_all_caches():
    """모든 전역 캐시 종료"""
    with _cache_lock:
        for cache in _global_caches.values():
            cache.close()
        _global_caches.clear()

# 하위 호환성을 위한 별칭
MemoryCache = MemorySafeCache
