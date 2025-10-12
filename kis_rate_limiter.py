#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 전역 Rate Limiter
모든 KIS API 호출이 이 싱글톤 Rate Limiter를 공유
"""

import time
import random
import threading

class KISGlobalRateLimiter:
    """
    KIS API 전역 Rate Limiter (싱글톤)
    KISDataProvider와 MCPKISIntegration이 모두 이 클래스를 사용
    """
    
    # 클래스 레벨 변수 (모든 곳에서 공유)
    _lock = threading.Lock()
    _last_request_time = 0.0
    _request_interval = 0.5  # 기본 0.5초 (초당 2건)
    
    @classmethod
    def rate_limit(cls, interval: float = None):
        """
        API 호출 전에 이 메서드를 호출하여 Rate Limit 적용
        
        Args:
            interval: API 호출 간격 (None이면 기본값 사용)
        """
        if interval is None:
            interval = cls._request_interval
        
        with cls._lock:
            elapsed = time.time() - cls._last_request_time
            wait = interval - elapsed
            
            if wait > 0:
                # 약간의 지터 추가 (0-30ms)
                time.sleep(wait + random.uniform(0, 0.03))
            
            cls._last_request_time = time.time()
    
    @classmethod
    def set_interval(cls, interval: float):
        """
        전역 API 호출 간격 설정
        
        Args:
            interval: 초 단위 간격 (예: 0.5 = 초당 2건)
        """
        with cls._lock:
            cls._request_interval = max(0.1, interval)  # 최소 0.1초
    
    @classmethod
    def get_interval(cls) -> float:
        """현재 설정된 간격 반환"""
        return cls._request_interval
    
    @classmethod
    def get_last_request_time(cls) -> float:
        """마지막 요청 시각 반환"""
        return cls._last_request_time

# 전역 싱글톤 인스턴스 (import해서 사용)
rate_limiter = KISGlobalRateLimiter()

