#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업종별 시장 분석 모듈
KIS API 국내업종 현재지수 API를 활용한 업종별 시장 분석
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class SectorAnalyzer:
    """업종별 시장 분석 클래스"""
    
    def __init__(self, provider):
        self.provider = provider
        self.sector_codes = {
            "0001": "코스피",
            "1001": "코스닥", 
            "2001": "코스피200"
        }
        self.last_request_time = 0
        self.request_interval = 0.1  # API 요청 간격 제어
    
    def _rate_limit(self):
        """API 요청 속도를 제어합니다."""
        elapsed_time = time.time() - self.last_request_time
        if elapsed_time < self.request_interval:
            time.sleep(self.request_interval - elapsed_time)
        self.last_request_time = time.time()
    
    def _to_float(self, value: Any, default: float = 0.0) -> float:
        """안전하게 float 타입으로 변환합니다."""
        if value is None or value == '':
            return default
        try:
            # 쉼표 제거 후 float 변환
            return float(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return default
    
    def get_sector_index_data(self, market_code: str = "0001") -> Optional[Dict[str, Any]]:
        """
        업종 현재지수 데이터를 조회합니다.
        
        Args:
            market_code: 시장 코드 (0001: 코스피, 1001: 코스닥, 2001: 코스피200)
        
        Returns:
            업종 지수 데이터 딕셔너리
        """
        self._rate_limit()
        
        path = "/uapi/domestic-stock/v1/quotations/inquire-index-price"
        params = {
            "FID_COND_MRKT_DIV_CODE": "U",  # 업종
            "FID_INPUT_ISCD": market_code
        }
        
        try:
            data = self.provider._send_request(path, "FHPUP02100000", params)
            if data and 'output' in data:
                return self._parse_sector_data(data['output'])
            else:
                logger.warning(f"⚠️ 업종 지수 데이터 조회 실패: {market_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 업종 지수 API 호출 실패 ({market_code}): {e}")
            return None
    
    def _parse_sector_data(self, output: Dict) -> Dict[str, Any]:
        """업종 지수 응답 데이터를 파싱합니다."""
        parsed_data = {}
        
        # 기본 지수 정보
        parsed_data['current_price'] = self._to_float(output.get('bstp_nmix_prpr', 0))
        parsed_data['change_amount'] = self._to_float(output.get('bstp_nmix_prdy_vrss', 0))
        parsed_data['change_sign'] = output.get('prdy_vrss_sign', '0')
        parsed_data['change_rate'] = self._to_float(output.get('bstp_nmix_prdy_ctrt', 0))
        
        # 거래량 정보
        parsed_data['volume'] = self._to_float(output.get('acml_vol', 0))
        parsed_data['prev_volume'] = self._to_float(output.get('prdy_vol', 0))
        parsed_data['trading_value'] = self._to_float(output.get('acml_tr_pbmn', 0))
        parsed_data['prev_trading_value'] = self._to_float(output.get('prdy_tr_pbmn', 0))
        
        # 가격 정보
        parsed_data['open_price'] = self._to_float(output.get('bstp_nmix_oprc', 0))
        parsed_data['high_price'] = self._to_float(output.get('bstp_nmix_hgpr', 0))
        parsed_data['low_price'] = self._to_float(output.get('bstp_nmix_lwpr', 0))
        
        # 종목 수 정보
        parsed_data['ascending_count'] = int(output.get('ascn_issu_cnt', 0))
        parsed_data['upper_limit_count'] = int(output.get('uplm_issu_cnt', 0))
        parsed_data['unchanged_count'] = int(output.get('stnr_issu_cnt', 0))
        parsed_data['declining_count'] = int(output.get('down_issu_cnt', 0))
        parsed_data['lower_limit_count'] = int(output.get('lslm_issu_cnt', 0))
        
        # 연중 최고/최저가
        parsed_data['year_high'] = self._to_float(output.get('dryy_bstp_nmix_hgpr', 0))
        parsed_data['year_high_rate'] = self._to_float(output.get('dryy_hgpr_vrss_prpr_rate', 0))
        parsed_data['year_high_date'] = output.get('dryy_bstp_nmix_hgpr_date', '')
        parsed_data['year_low'] = self._to_float(output.get('dryy_bstp_nmix_lwpr', 0))
        parsed_data['year_low_rate'] = self._to_float(output.get('dryy_lwpr_vrss_prpr_rate', 0))
        parsed_data['year_low_date'] = output.get('dryy_bstp_nmix_lwpr_date', '')
        
        # 호가 정보
        parsed_data['total_ask_volume'] = self._to_float(output.get('total_askp_rsqn', 0))
        parsed_data['total_bid_volume'] = self._to_float(output.get('total_bidp_rsqn', 0))
        parsed_data['ask_volume_rate'] = self._to_float(output.get('seln_rsqn_rate', 0))
        parsed_data['bid_volume_rate'] = self._to_float(output.get('shnu_rsqn_rate', 0))
        parsed_data['net_buy_volume'] = self._to_float(output.get('ntby_rsqn', 0))
        
        # 계산된 지표
        total_stocks = (parsed_data['ascending_count'] + parsed_data['unchanged_count'] + 
                       parsed_data['declining_count'])
        if total_stocks > 0:
            parsed_data['advance_decline_ratio'] = parsed_data['ascending_count'] / total_stocks
            parsed_data['market_sentiment'] = self._calculate_market_sentiment(parsed_data)
        else:
            parsed_data['advance_decline_ratio'] = 0
            parsed_data['market_sentiment'] = "중립"
        
        return parsed_data
    
    def _calculate_market_sentiment(self, data: Dict) -> str:
        """시장 심리를 계산합니다."""
        advance_ratio = data['advance_decline_ratio']
        change_rate = data['change_rate']
        
        if advance_ratio >= 0.7 and change_rate > 1:
            return "매우 강세"
        elif advance_ratio >= 0.6 and change_rate > 0:
            return "강세"
        elif advance_ratio >= 0.4:
            return "중립"
        elif advance_ratio >= 0.3:
            return "약세"
        else:
            return "매우 약세"
    
    def get_all_sector_data(self) -> Dict[str, Dict[str, Any]]:
        """모든 시장의 업종 지수 데이터를 조회합니다."""
        all_data = {}
        
        for market_code, market_name in self.sector_codes.items():
            logger.info(f"🔍 {market_name} 업종 지수 조회 중...")
            data = self.get_sector_index_data(market_code)
            if data:
                data['market_name'] = market_name
                data['market_code'] = market_code
                all_data[market_code] = data
            else:
                logger.warning(f"⚠️ {market_name} 데이터 조회 실패")
        
        return all_data
    
    def analyze_sector_performance(self, sector_data: Dict[str, Any]) -> Dict[str, Any]:
        """업종 성과를 분석합니다."""
        analysis = {}
        
        # 기본 성과 지표
        analysis['performance_score'] = self._calculate_performance_score(sector_data)
        analysis['volatility_score'] = self._calculate_volatility_score(sector_data)
        analysis['liquidity_score'] = self._calculate_liquidity_score(sector_data)
        analysis['sentiment_score'] = self._calculate_sentiment_score(sector_data)
        
        # 종합 점수
        analysis['total_score'] = (
            analysis['performance_score'] * 0.4 +
            analysis['volatility_score'] * 0.2 +
            analysis['liquidity_score'] * 0.2 +
            analysis['sentiment_score'] * 0.2
        )
        
        # 투자 추천
        analysis['recommendation'] = self._get_investment_recommendation(analysis['total_score'])
        
        return analysis
    
    def _calculate_performance_score(self, data: Dict) -> float:
        """성과 점수를 계산합니다."""
        change_rate = data['change_rate']
        year_high_rate = data['year_high_rate']
        
        # 등락률 기반 점수 (0-50점)
        if change_rate > 5:
            performance_score = 50
        elif change_rate > 2:
            performance_score = 40
        elif change_rate > 0:
            performance_score = 30
        elif change_rate > -2:
            performance_score = 20
        elif change_rate > -5:
            performance_score = 10
        else:
            performance_score = 0
        
        # 연중 최고가 대비 점수 (0-50점)
        if year_high_rate > 0.95:
            performance_score += 50
        elif year_high_rate > 0.9:
            performance_score += 40
        elif year_high_rate > 0.8:
            performance_score += 30
        elif year_high_rate > 0.7:
            performance_score += 20
        else:
            performance_score += 10
        
        return min(performance_score, 100)
    
    def _calculate_volatility_score(self, data: Dict) -> float:
        """변동성 점수를 계산합니다."""
        high_price = data['high_price']
        low_price = data['low_price']
        current_price = data['current_price']
        
        if current_price > 0:
            daily_range = (high_price - low_price) / current_price * 100
        else:
            daily_range = 0
        
        # 변동성이 적을수록 높은 점수
        if daily_range < 1:
            return 100
        elif daily_range < 2:
            return 80
        elif daily_range < 3:
            return 60
        elif daily_range < 5:
            return 40
        else:
            return 20
    
    def _calculate_liquidity_score(self, data: Dict) -> float:
        """유동성 점수를 계산합니다."""
        volume = data['volume']
        trading_value = data['trading_value']
        
        # 거래량과 거래대금을 종합하여 유동성 점수 계산
        volume_score = min(volume / 1000000, 50)  # 100만주 이상이면 50점
        value_score = min(trading_value / 1000000000000, 50)  # 1조원 이상이면 50점
        
        return volume_score + value_score
    
    def _calculate_sentiment_score(self, data: Dict) -> float:
        """시장 심리 점수를 계산합니다."""
        advance_ratio = data['advance_decline_ratio']
        net_buy_volume = data['net_buy_volume']
        
        # 상승 종목 비율 기반 점수
        sentiment_score = advance_ratio * 50
        
        # 순매수 잔량 기반 추가 점수
        if net_buy_volume > 0:
            sentiment_score += 25
        elif net_buy_volume < 0:
            sentiment_score -= 25
        
        return max(0, min(sentiment_score, 100))
    
    def _get_investment_recommendation(self, total_score: float) -> str:
        """투자 추천을 결정합니다."""
        if total_score >= 80:
            return "매우 강력 추천"
        elif total_score >= 70:
            return "강력 추천"
        elif total_score >= 60:
            return "추천"
        elif total_score >= 50:
            return "중립"
        elif total_score >= 40:
            return "신중"
        else:
            return "비추천"

def main():
    """테스트 함수"""
    from kis_data_provider import KISDataProvider
    
    provider = KISDataProvider()
    analyzer = SectorAnalyzer(provider)
    
    # 코스피 업종 지수 조회 테스트
    kospi_data = analyzer.get_sector_index_data("0001")
    if kospi_data:
        print("📊 코스피 업종 지수 분석:")
        print(f"  현재가: {kospi_data['current_price']:,.2f}")
        print(f"  등락률: {kospi_data['change_rate']:+.2f}%")
        print(f"  거래량: {kospi_data['volume']:,.0f}주")
        print(f"  상승종목: {kospi_data['ascending_count']}개")
        print(f"  하락종목: {kospi_data['declining_count']}개")
        print(f"  시장심리: {kospi_data['market_sentiment']}")
        
        # 성과 분석
        analysis = analyzer.analyze_sector_performance(kospi_data)
        print(f"\n📈 성과 분석:")
        print(f"  종합점수: {analysis['total_score']:.1f}점")
        print(f"  투자추천: {analysis['recommendation']}")
    else:
        print("❌ 코스피 업종 지수 데이터 조회 실패")

if __name__ == "__main__":
    main()
