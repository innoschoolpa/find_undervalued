"""
TPS Rate Limiter 모듈

API 호출 제한을 관리하는 TPSRateLimiter를 제공합니다.
"""

import logging
import time
from typing import Dict, Any


class TPSRateLimiter:
    """TPS Rate Limiter (API 호출 제한 관리)"""
    
    def __init__(self, max_tps: int = 10, burst_limit: int = 20):
        self.max_tps = max_tps
        self.burst_limit = burst_limit
        self.tokens = burst_limit
        self.last_update = time.time()
        self.lock = None
        
        # 통계
        self.stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'average_wait_time': 0.0,
            'peak_tps': 0.0
        }
        
        # 토큰 버킷 알고리즘 설정
        self.token_refill_rate = max_tps / 60.0  # 초당 토큰 보충률
        self.token_refill_interval = 1.0 / max_tps  # 토큰 간격 (초)
        
        logging.info(f"TPS Rate Limiter 초기화: max_tps={max_tps}, burst_limit={burst_limit}")
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        토큰 획득 시도
        
        Args:
            tokens: 필요한 토큰 수
        
        Returns:
            bool: 토큰 획득 성공 여부
        """
        try:
            current_time = time.time()
            
            # 토큰 보충
            self._refill_tokens(current_time)
            
            # 토큰 충분한지 확인
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.stats['total_requests'] += 1
                return True
            else:
                self.stats['blocked_requests'] += 1
                return False
                
        except Exception as e:
            logging.error(f"토큰 획득 실패: {e}")
            return False
    
    def acquire_with_wait(self, tokens: int = 1, max_wait_time: float = 60.0) -> bool:
        """
        토큰 획득 시도 (대기 포함)
        
        Args:
            tokens: 필요한 토큰 수
            max_wait_time: 최대 대기 시간 (초)
        
        Returns:
            bool: 토큰 획득 성공 여부
        """
        try:
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                if self.acquire(tokens):
                    wait_time = time.time() - start_time
                    self._update_average_wait_time(wait_time)
                    return True
                
                # 짧은 대기 후 재시도
                time.sleep(0.1)
            
            # 최대 대기 시간 초과
            logging.warning(f"토큰 획득 대기 시간 초과: {max_wait_time}초")
            return False
            
        except Exception as e:
            logging.error(f"토큰 획득 대기 실패: {e}")
            return False
    
    def _refill_tokens(self, current_time: float):
        """토큰 보충"""
        try:
            time_elapsed = current_time - self.last_update
            
            if time_elapsed > 0:
                # 토큰 보충
                tokens_to_add = time_elapsed * self.token_refill_rate
                self.tokens = min(self.burst_limit, self.tokens + tokens_to_add)
                self.last_update = current_time
                
        except Exception as e:
            logging.error(f"토큰 보충 실패: {e}")
    
    def _update_average_wait_time(self, wait_time: float):
        """평균 대기 시간 업데이트"""
        try:
            current_avg = self.stats['average_wait_time']
            total_requests = self.stats['total_requests']
            
            if total_requests > 0:
                # 이동 평균 계산
                self.stats['average_wait_time'] = (
                    (current_avg * (total_requests - 1) + wait_time) / total_requests
                )
            else:
                self.stats['average_wait_time'] = wait_time
                
        except Exception as e:
            logging.warning(f"평균 대기 시간 업데이트 실패: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        try:
            current_time = time.time()
            self._refill_tokens(current_time)
            
            # 현재 TPS 계산
            time_elapsed = current_time - self.last_update
            current_tps = self.token_refill_rate * 60.0  # 분당 TPS
            
            # 피크 TPS 업데이트
            if current_tps > self.stats['peak_tps']:
                self.stats['peak_tps'] = current_tps
            
            return {
                'max_tps': self.max_tps,
                'burst_limit': self.burst_limit,
                'current_tokens': self.tokens,
                'current_tps': current_tps,
                'peak_tps': self.stats['peak_tps'],
                'total_requests': self.stats['total_requests'],
                'blocked_requests': self.stats['blocked_requests'],
                'average_wait_time': self.stats['average_wait_time'],
                'block_rate': (
                    self.stats['blocked_requests'] / max(1, self.stats['total_requests']) * 100
                )
            }
            
        except Exception as e:
            logging.error(f"통계 조회 실패: {e}")
            return {}
    
    def reset_stats(self):
        """통계 초기화"""
        try:
            self.stats = {
                'total_requests': 0,
                'blocked_requests': 0,
                'average_wait_time': 0.0,
                'peak_tps': 0.0
            }
            logging.info("TPS Rate Limiter 통계 초기화 완료")
            
        except Exception as e:
            logging.error(f"통계 초기화 실패: {e}")
    
    def adjust_rate(self, new_max_tps: int):
        """TPS 제한 조정"""
        try:
            old_max_tps = self.max_tps
            self.max_tps = new_max_tps
            self.token_refill_rate = new_max_tps / 60.0
            self.token_refill_interval = 1.0 / new_max_tps
            
            logging.info(f"TPS 제한 조정: {old_max_tps} → {new_max_tps}")
            
        except Exception as e:
            logging.error(f"TPS 제한 조정 실패: {e}")
    
    def is_available(self, tokens: int = 1) -> bool:
        """토큰 사용 가능 여부 확인 (토큰 소모 없음)"""
        try:
            current_time = time.time()
            self._refill_tokens(current_time)
            
            return self.tokens >= tokens
            
        except Exception as e:
            logging.error(f"토큰 사용 가능 여부 확인 실패: {e}")
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """필요한 토큰을 위한 대기 시간 계산"""
        try:
            current_time = time.time()
            self._refill_tokens(current_time)
            
            if self.tokens >= tokens:
                return 0.0
            
            # 부족한 토큰 수
            needed_tokens = tokens - self.tokens
            
            # 필요한 시간 계산
            wait_time = needed_tokens / self.token_refill_rate
            
            return wait_time
            
        except Exception as e:
            logging.error(f"대기 시간 계산 실패: {e}")
            return float('inf')
    
    def __str__(self) -> str:
        """문자열 표현"""
        try:
            stats = self.get_stats()
            return (
                f"TPSRateLimiter(max_tps={stats['max_tps']}, "
                f"current_tokens={stats['current_tokens']:.1f}, "
                f"block_rate={stats['block_rate']:.1f}%)"
            )
        except:
            return f"TPSRateLimiter(max_tps={self.max_tps})"
    
    def __repr__(self) -> str:
        """개발자용 문자열 표현"""
        return self.__str__()













