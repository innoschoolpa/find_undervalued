# caching_system.py
"""
고성능 캐싱 시스템
- 메모리 캐시 + 디스크 캐시
- TTL 기반 만료 관리
- LRU 캐시 정책
- 압축 및 직렬화 최적화
"""

import pickle
import json
import time
import hashlib
import os
import gzip
from typing import Any, Optional, Dict, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class CacheEntry:
    """캐시 엔트리 클래스"""
    
    def __init__(self, value: Any, ttl: float = 3600.0):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = time.time()
    
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """접근 시간 업데이트"""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def get_value(self) -> Any:
        """값 조회 (접근 시간 업데이트)"""
        self.touch()
        return self.value

class MemoryCache:
    """메모리 캐시 클래스 (LRU 정책)"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.lock = Lock()
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry.is_expired():
                    del self.cache[key]
                    self.miss_count += 1
                    return None
                
                # LRU 업데이트
                self.cache.move_to_end(key)
                self.hit_count += 1
                return entry.get_value()
            
            self.miss_count += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """캐시에 값 저장"""
        with self.lock:
            if ttl is None:
                ttl = self.default_ttl
            
            # 기존 엔트리 제거
            if key in self.cache:
                del self.cache[key]
            
            # 새 엔트리 추가
            self.cache[key] = CacheEntry(value, ttl)
            
            # 크기 제한 확인
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """캐시 전체 삭제"""
        with self.lock:
            self.cache.clear()
            self.hit_count = 0
            self.miss_count = 0
    
    def cleanup_expired(self) -> int:
        """만료된 엔트리 정리"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        with self.lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': hit_rate,
                'total_requests': total_requests
            }

class DiskCache:
    """디스크 캐시 클래스"""
    
    def __init__(self, cache_dir: str = "cache", compress: bool = True):
        self.cache_dir = cache_dir
        self.compress = compress
        self.lock = Lock()
        
        # 캐시 디렉토리 생성
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """캐시 파일 경로 생성"""
        # 키를 해시하여 파일명 생성
        key_hash = hashlib.md5(key.encode()).hexdigest()
        filename = f"{key_hash}.cache"
        return os.path.join(self.cache_dir, filename)
    
    def get(self, key: str) -> Optional[Any]:
        """디스크에서 값 조회"""
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with self.lock:
                with open(cache_path, 'rb') as f:
                    if self.compress:
                        data = gzip.decompress(f.read())
                    else:
                        data = f.read()
                    
                    # 메타데이터와 값 분리
                    metadata = json.loads(data[:data.find(b'\n')].decode())
                    value_data = data[data.find(b'\n') + 1:]
                    
                    # TTL 확인
                    if time.time() - metadata['created_at'] > metadata['ttl']:
                        os.remove(cache_path)
                        return None
                    
                    # 값 역직렬화
                    return pickle.loads(value_data)
        
        except Exception as e:
            logger.warning(f"디스크 캐시 읽기 실패 {key}: {e}")
            # 손상된 파일 삭제
            try:
                os.remove(cache_path)
            except:
                pass
            return None
    
    def set(self, key: str, value: Any, ttl: float = 3600.0) -> None:
        """디스크에 값 저장"""
        cache_path = self._get_cache_path(key)
        
        try:
            with self.lock:
                # 메타데이터 생성
                metadata = {
                    'created_at': time.time(),
                    'ttl': ttl,
                    'key': key
                }
                
                # 값 직렬화
                value_data = pickle.dumps(value)
                
                # 파일에 저장
                with open(cache_path, 'wb') as f:
                    if self.compress:
                        data = gzip.compress(
                            json.dumps(metadata).encode() + b'\n' + value_data
                        )
                    else:
                        data = json.dumps(metadata).encode() + b'\n' + value_data
                    
                    f.write(data)
        
        except Exception as e:
            logger.warning(f"디스크 캐시 쓰기 실패 {key}: {e}")
    
    def delete(self, key: str) -> bool:
        """디스크에서 값 삭제"""
        cache_path = self._get_cache_path(key)
        
        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
                return True
        except Exception as e:
            logger.warning(f"디스크 캐시 삭제 실패 {key}: {e}")
        
        return False
    
    def cleanup_expired(self) -> int:
        """만료된 파일 정리"""
        cleaned_count = 0
        
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    cache_path = os.path.join(self.cache_dir, filename)
                    
                    try:
                        with open(cache_path, 'rb') as f:
                            if self.compress:
                                data = gzip.decompress(f.read())
                            else:
                                data = f.read()
                            
                            metadata = json.loads(data[:data.find(b'\n')].decode())
                            
                            # TTL 확인
                            if time.time() - metadata['created_at'] > metadata['ttl']:
                                os.remove(cache_path)
                                cleaned_count += 1
                    
                    except Exception:
                        # 손상된 파일 삭제
                        try:
                            os.remove(cache_path)
                            cleaned_count += 1
                        except:
                            pass
        
        except Exception as e:
            logger.warning(f"디스크 캐시 정리 실패: {e}")
        
        return cleaned_count

class HybridCache:
    """하이브리드 캐시 (메모리 + 디스크)"""
    
    def __init__(self, 
                 memory_max_size: int = 1000,
                 memory_ttl: float = 3600.0,
                 disk_cache_dir: str = "cache",
                 disk_ttl: float = 86400.0,  # 24시간
                 compress: bool = True):
        
        self.memory_cache = MemoryCache(memory_max_size, memory_ttl)
        self.disk_cache = DiskCache(disk_cache_dir, compress)
        self.disk_ttl = disk_ttl
        self.lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회 (메모리 → 디스크 순)"""
        # 1. 메모리 캐시에서 조회
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # 2. 디스크 캐시에서 조회
        value = self.disk_cache.get(key)
        if value is not None:
            # 메모리 캐시에 다시 저장
            self.memory_cache.set(key, value)
            return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """캐시에 값 저장 (메모리 + 디스크)"""
        if ttl is None:
            ttl = self.memory_cache.default_ttl
        
        # 메모리 캐시에 저장
        self.memory_cache.set(key, value, ttl)
        
        # 디스크 캐시에도 저장 (더 긴 TTL)
        self.disk_cache.set(key, value, self.disk_ttl)
    
    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        memory_deleted = self.memory_cache.delete(key)
        disk_deleted = self.disk_cache.delete(key)
        return memory_deleted or disk_deleted
    
    def clear(self) -> None:
        """캐시 전체 삭제"""
        self.memory_cache.clear()
        # 디스크 캐시는 개별 파일이므로 전체 삭제하지 않음
    
    def cleanup(self) -> Dict[str, int]:
        """만료된 엔트리 정리"""
        memory_cleaned = self.memory_cache.cleanup_expired()
        disk_cleaned = self.disk_cache.cleanup_expired()
        
        return {
            'memory_cleaned': memory_cleaned,
            'disk_cleaned': disk_cleaned,
            'total_cleaned': memory_cleaned + disk_cleaned
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        memory_stats = self.memory_cache.get_stats()
        disk_stats = {
            'cache_dir': self.disk_cache.cache_dir,
            'compress': self.disk_cache.compress
        }
        
        return {
            'memory': memory_stats,
            'disk': disk_stats
        }

# =============================================================================
# 캐시 데코레이터
# =============================================================================

def cached(cache: HybridCache, ttl: float = 3600.0, key_prefix: str = ""):
    """캐시 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 캐시에서 조회
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # 함수 실행
            result = func(*args, **kwargs)
            
            # 캐시에 저장
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

# =============================================================================
# 전역 캐시 인스턴스
# =============================================================================

# 기본 캐시 설정
DEFAULT_CACHE = HybridCache(
    memory_max_size=1000,
    memory_ttl=3600.0,  # 1시간
    disk_cache_dir="cache",
    disk_ttl=86400.0,   # 24시간
    compress=True
)

# 캐시 정리 스케줄러
def start_cache_cleanup_scheduler(interval: int = 300):  # 5분마다
    """캐시 정리 스케줄러 시작"""
    import threading
    
    def cleanup_worker():
        while True:
            try:
                cleaned = DEFAULT_CACHE.cleanup()
                if cleaned['total_cleaned'] > 0:
                    logger.info(f"캐시 정리 완료: {cleaned}")
                time.sleep(interval)
            except Exception as e:
                logger.error(f"캐시 정리 스케줄러 오류: {e}")
                time.sleep(interval)
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    return cleanup_thread

