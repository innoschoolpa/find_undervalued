#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thread-Safe Rate Limiter
- 통합된 TPS 제한기 구현
- 스레드 안전성 보장
- 공정한 FIFO 대기열
- 메모리 효율적인 슬라이딩 윈도우
"""

import time
import random
import logging
import threading
from collections import deque
from typing import Optional, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Rate Limiter 설정"""
    max_tps: int = 8
    burst_limit: int = 10
    min_sleep_ms: float = 2.0
    jitter_max: float = 0.1
    timeout: float = 30.0
    notify_all: bool = True

class ThreadSafeTPSRateLimiter:
    """
    스레드 안전한 TPS 제한기
    - FIFO 대기열로 공정성 보장
    - 슬라이딩 윈도우로 정확한 TPS 제한
    - 메모리 효율적인 구현
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        
        # 스레드 안전성을 위한 락
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        
        # 슬라이딩 윈도우 (타임스탬프 큐)
        self._timestamps = deque()
        
        # FIFO 대기열
        self._waiters = deque()
        
        # 통계
        self._total_requests = 0
        self._total_wait_time = 0.0
        self._max_wait_time = 0.0
        
        logger.info(f"RateLimiter initialized: max_tps={self.config.max_tps}, "
                   f"burst_limit={self.config.burst_limit}")
    
    @contextmanager
    def acquire(self, timeout: Optional[float] = None):
        """
        Rate limit 허가를 받는 컨텍스트 매니저
        사용법:
            with rate_limiter.acquire():
                # API 호출
                pass
        """
        start_time = time.monotonic()
        timeout = timeout or self.config.timeout
        
        try:
            self._wait_for_permission(start_time, timeout)
            yield
        finally:
            # 통계 업데이트
            wait_time = time.monotonic() - start_time
            self._update_stats(wait_time)
    
    def _wait_for_permission(self, start_time: float, timeout: float):
        """권한 획득을 위한 대기"""
        my_token = object()  # 고유 토큰
        
        with self._condition:
            # 대기열에 추가
            self._waiters.append(my_token)
            
            while True:
                now = time.monotonic()
                
                # 슬라이딩 윈도우 정리
                self._cleanup_old_timestamps(now)
                
                # 내 차례인지 확인
                is_my_turn = (self._waiters and self._waiters[0] is my_token)
                
                # TPS 제한 확인
                if is_my_turn and len(self._timestamps) < self.config.max_tps:
                    # 권한 획득
                    self._timestamps.append(now)
                    self._waiters.popleft()
                    
                    # 다음 대기자에게 알림
                    if self._waiters:
                        if self.config.notify_all:
                            self._condition.notify_all()
                        else:
                            self._condition.notify()
                    return
                
                # 타임아웃 확인
                elapsed = now - start_time
                if elapsed >= timeout:
                    # 대기열에서 제거
                    try:
                        self._waiters.remove(my_token)
                    except ValueError:
                        pass
                    
                    logger.warning(f"Rate limiter timeout after {timeout:.1f}s")
                    raise TimeoutError(f"Rate limiter timeout after {timeout:.1f}s")
                
                # 대기 시간 계산
                wait_time = self._calculate_wait_time(now)
                sleep_time = max(wait_time + random.uniform(0, self.config.jitter_max), 
                               self.config.min_sleep_ms / 1000.0)
                
                if elapsed > 1.0:  # 1초 이상 대기한 경우에만 로그
                    logger.debug(f"Rate limiter waiting: {elapsed:.3f}s, "
                               f"in_window={len(self._timestamps)}, "
                               f"next_sleep={sleep_time:.3f}s")
                
                self._condition.wait(sleep_time)
    
    def _cleanup_old_timestamps(self, now: float):
        """1초 이전 타임스탬프 제거"""
        cutoff = now - 1.0
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
    
    def _calculate_wait_time(self, now: float) -> float:
        """다음 요청까지 대기 시간 계산"""
        if not self._timestamps:
            return 0.0
        
        # 가장 오래된 요청이 1초가 지날 때까지 대기
        oldest = self._timestamps[0]
        return max(0.0, (oldest + 1.0) - now)
    
    def _update_stats(self, wait_time: float):
        """통계 업데이트"""
        with self._lock:
            self._total_requests += 1
            self._total_wait_time += wait_time
            self._max_wait_time = max(self._max_wait_time, wait_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """현재 통계 반환"""
        with self._lock:
            avg_wait = (self._total_wait_time / self._total_requests 
                       if self._total_requests > 0 else 0.0)
            
            return {
                'total_requests': self._total_requests,
                'average_wait_time': avg_wait,
                'max_wait_time': self._max_wait_time,
                'current_window_size': len(self._timestamps),
                'waiters_count': len(self._waiters),
                'config': {
                    'max_tps': self.config.max_tps,
                    'burst_limit': self.config.burst_limit,
                    'timeout': self.config.timeout
                }
            }
    
    def reset_stats(self):
        """통계 초기화"""
        with self._lock:
            self._total_requests = 0
            self._total_wait_time = 0.0
            self._max_wait_time = 0.0
    
    def adjust_config(self, **kwargs):
        """설정 동적 조정"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    logger.info(f"Rate limiter config updated: {key}={value}")

# 전역 인스턴스 (기본 설정)
_default_rate_limiter = None
_default_lock = threading.Lock()

def get_default_rate_limiter() -> ThreadSafeTPSRateLimiter:
    """기본 Rate Limiter 인스턴스 반환"""
    global _default_rate_limiter
    
    if _default_rate_limiter is None:
        with _default_lock:
            if _default_rate_limiter is None:
                _default_rate_limiter = ThreadSafeTPSRateLimiter()
    
    return _default_rate_limiter

def create_rate_limiter(config: Optional[RateLimitConfig] = None) -> ThreadSafeTPSRateLimiter:
    """새로운 Rate Limiter 인스턴스 생성"""
    return ThreadSafeTPSRateLimiter(config)

# 하위 호환성을 위한 별칭
TPSRateLimiter = ThreadSafeTPSRateLimiter
