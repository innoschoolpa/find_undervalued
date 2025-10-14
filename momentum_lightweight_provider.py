#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모멘텀 경량화 제공자 (차트 REST 500 회피)
차트 API 대신 멀티/랭킹 API를 활용한 모멘텀 점수 계산
"""

import logging
import time
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)

class MomentumLightweightProvider:
    """차트 API 500 오류를 회피하는 경량화된 모멘텀 제공자"""
    
    def __init__(self, kis_provider):
        """
        Args:
            kis_provider: KISDataProvider 또는 MCPKISIntegration 인스턴스
        """
        self.kis_provider = kis_provider
        self.cache = {}  # 간단한 메모리 캐시
        self.cache_ttl = 300  # 5분 캐시
        
    def get_momentum_score_lightweight(self, symbol: str, lookback_days: int = 60) -> float:
        """
        경량화된 모멘텀 점수 계산 (차트 API 대신 현재가/거래대금 랭킹 활용)
        
        Args:
            symbol: 종목코드
            lookback_days: 모멘텀 기간 (기본 60일)
            
        Returns:
            모멘텀 점수 (0-100, 높을수록 좋음)
        """
        try:
            # 캐시 확인
            cache_key = f"{symbol}_{lookback_days}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if time.time() - cached_time < self.cache_ttl:
                    return cached_data
            
            # 1. 현재가 기반 모멘텀 (52주 고가 대비)
            current_momentum = self._get_current_price_momentum(symbol)
            
            # 2. 거래대금 기반 모멘텀 (평균 대비)
            volume_momentum = self._get_volume_momentum(symbol)
            
            # 3. 등락률 기반 모멘텀 (최근 변동성)
            change_momentum = self._get_change_momentum(symbol)
            
            # 4. 종합 모멘텀 점수 (가중평균)
            momentum_score = (
                current_momentum * 0.4 +      # 현재가 모멘텀 40%
                volume_momentum * 0.3 +       # 거래량 모멘텀 30%
                change_momentum * 0.3         # 등락률 모멘텀 30%
            )
            
            # 점수 정규화 (0-100)
            momentum_score = max(0, min(100, momentum_score))
            
            # 캐시 저장
            self.cache[cache_key] = (momentum_score, time.time())
            
            logger.debug(f"📈 {symbol} 모멘텀 점수: {momentum_score:.1f} (현재가:{current_momentum:.1f}, 거래량:{volume_momentum:.1f}, 등락률:{change_momentum:.1f})")
            
            return momentum_score
            
        except Exception as e:
            logger.warning(f"⚠️ {symbol} 모멘텀 점수 계산 실패: {e}")
            return 50.0  # 중립 점수 반환
    
    def _get_current_price_momentum(self, symbol: str) -> float:
        """현재가 기반 모멘텀 (52주 고가 대비)"""
        try:
            # 현재가 정보 조회
            stock_info = self.kis_provider.get_stock_price_info(symbol)
            if not stock_info:
                return 50.0
            
            current_price = stock_info.get('current_price', 0)
            w52_high = stock_info.get('w52_high', 0)
            w52_low = stock_info.get('w52_low', 0)
            
            if w52_high <= 0 or w52_low <= 0:
                return 50.0
            
            # 52주 범위 내에서의 위치 (0-100)
            if w52_high == w52_low:
                return 50.0
            
            position_ratio = (current_price - w52_low) / (w52_high - w52_low)
            momentum = position_ratio * 100
            
            return max(0, min(100, momentum))
            
        except Exception as e:
            logger.debug(f"현재가 모멘텀 계산 실패 {symbol}: {e}")
            return 50.0
    
    def _get_volume_momentum(self, symbol: str) -> float:
        """거래량 기반 모멘텀 (평균 대비)"""
        try:
            stock_info = self.kis_provider.get_stock_price_info(symbol)
            if not stock_info:
                return 50.0
            
            current_volume = stock_info.get('volume', 0)
            trading_value = stock_info.get('trading_value', 0)
            
            if current_volume <= 0:
                return 50.0
            
            # 거래량 회전율 활용 (있는 경우)
            vol_turnover = stock_info.get('vol_turnover', 0)
            if vol_turnover > 0:
                # 회전율이 높을수록 좋은 모멘텀
                momentum = min(100, vol_turnover * 10)  # 회전율 * 10으로 스케일링
                return momentum
            
            # 거래대금 기반 추정
            if trading_value > 0:
                # 거래대금이 클수록 좋은 모멘텀 (로그 스케일)
                import math
                momentum = min(100, math.log10(trading_value / 1000000) * 20)  # 억원 단위로 변환
                return max(0, momentum)
            
            return 50.0
            
        except Exception as e:
            logger.debug(f"거래량 모멘텀 계산 실패 {symbol}: {e}")
            return 50.0
    
    def _get_change_momentum(self, symbol: str) -> float:
        """등락률 기반 모멘텀 (최근 변동성)"""
        try:
            stock_info = self.kis_provider.get_stock_price_info(symbol)
            if not stock_info:
                return 50.0
            
            change_rate = stock_info.get('change_rate', 0)
            
            if change_rate == 0:
                return 50.0
            
            # 등락률을 모멘텀 점수로 변환
            # 상승률이 높을수록 좋은 점수, 하락률이 높을수록 낮은 점수
            momentum = 50 + (change_rate * 2)  # 등락률 * 2로 스케일링
            
            return max(0, min(100, momentum))
            
        except Exception as e:
            logger.debug(f"등락률 모멘텀 계산 실패 {symbol}: {e}")
            return 50.0
    
    def get_batch_momentum_scores(self, symbols: List[str], lookback_days: int = 60) -> Dict[str, float]:
        """
        배치 모멘텀 점수 계산 (여러 종목 동시 처리)
        
        Args:
            symbols: 종목코드 리스트
            lookback_days: 모멘텀 기간
            
        Returns:
            {종목코드: 모멘텀점수} 딕셔너리
        """
        results = {}
        
        for symbol in symbols:
            try:
                score = self.get_momentum_score_lightweight(symbol, lookback_days)
                results[symbol] = score
                
                # API 호출 간격 조절 (차단 방지)
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"⚠️ {symbol} 배치 모멘텀 계산 실패: {e}")
                results[symbol] = 50.0
        
        return results
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
        logger.info("🧹 모멘텀 캐시 초기화 완료")


class MomentumRankingProvider:
    """랭킹 API 기반 모멘텀 제공자 (더욱 경량화)"""
    
    def __init__(self, mcp_kis_integration):
        """
        Args:
            mcp_kis_integration: MCPKISIntegration 인스턴스
        """
        self.mcp_kis = mcp_kis_integration
        self.cache = {}
        self.cache_ttl = 600  # 10분 캐시 (랭킹 데이터는 더 오래 캐시)
        
    def get_momentum_from_ranking(self, symbol: str) -> float:
        """
        랭킹 API에서 모멘텀 점수 추출
        
        Args:
            symbol: 종목코드
            
        Returns:
            모멘텀 점수 (0-100)
        """
        try:
            # 캐시 확인
            if symbol in self.cache:
                cached_data, cached_time = self.cache[symbol]
                if time.time() - cached_time < self.cache_ttl:
                    return cached_data
            
            # 1. 등락률 순위에서 모멘텀 추출
            updown_rank = self._get_updown_ranking(symbol)
            
            # 2. 거래량 순위에서 모멘텀 추출
            volume_rank = self._get_volume_ranking(symbol)
            
            # 3. 종합 모멘텀 점수
            momentum_score = (updown_rank + volume_rank) / 2
            
            # 캐시 저장
            self.cache[symbol] = (momentum_score, time.time())
            
            return momentum_score
            
        except Exception as e:
            logger.warning(f"⚠️ {symbol} 랭킹 모멘텀 계산 실패: {e}")
            return 50.0
    
    def _get_updown_ranking(self, symbol: str) -> float:
        """등락률 순위에서 모멘텀 점수 추출"""
        try:
            # 등락률 순위 조회 (상위 100개)
            ranking_data = self.mcp_kis.get_updown_ranking(limit=100)
            
            if not ranking_data:
                return 50.0
            
            # 해당 종목의 순위 찾기
            for i, item in enumerate(ranking_data):
                if item.get('stock_code') == symbol:
                    # 상위권일수록 높은 점수 (1위=100점, 100위=1점)
                    rank_score = max(1, 101 - i)
                    return rank_score
            
            # 순위에 없으면 중간 점수
            return 50.0
            
        except Exception as e:
            logger.debug(f"등락률 순위 조회 실패 {symbol}: {e}")
            return 50.0
    
    def _get_volume_ranking(self, symbol: str) -> float:
        """거래량 순위에서 모멘텀 점수 추출"""
        try:
            # 거래량 순위 조회 (상위 100개)
            ranking_data = self.mcp_kis.get_volume_ranking(limit=100)
            
            if not ranking_data:
                return 50.0
            
            # 해당 종목의 순위 찾기
            for i, item in enumerate(ranking_data):
                if item.get('stock_code') == symbol:
                    # 상위권일수록 높은 점수
                    rank_score = max(1, 101 - i)
                    return rank_score
            
            return 50.0
            
        except Exception as e:
            logger.debug(f"거래량 순위 조회 실패 {symbol}: {e}")
            return 50.0


def create_momentum_provider(kis_provider, strategy: str = "lightweight"):
    """
    모멘텀 제공자 팩토리 함수
    
    Args:
        kis_provider: KIS 데이터 제공자
        strategy: 전략 ("lightweight" 또는 "ranking")
        
    Returns:
        모멘텀 제공자 인스턴스
    """
    if strategy == "lightweight":
        return MomentumLightweightProvider(kis_provider)
    elif strategy == "ranking":
        return MomentumRankingProvider(kis_provider)
    else:
        raise ValueError(f"지원하지 않는 전략: {strategy}")


# 사용 예시
if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # KIS 데이터 제공자 초기화 (실제 환경에서는 적절히 초기화)
    # kis_provider = KISDataProvider()
    
    # 경량화 모멘텀 제공자 생성
    # momentum_provider = create_momentum_provider(kis_provider, "lightweight")
    
    # 모멘텀 점수 계산
    # score = momentum_provider.get_momentum_score_lightweight("005930")  # 삼성전자
    # print(f"삼성전자 모멘텀 점수: {score}")
