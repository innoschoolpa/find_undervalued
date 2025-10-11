#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 실용적 분석 모듈
실제로 작동하는 KIS API만 사용하여 가치주 분석
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class StockInfo:
    """종목 정보"""
    symbol: str
    name: str
    current_price: float
    per: Optional[float] = None
    pbr: Optional[float] = None
    roe: Optional[float] = None
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    volume: Optional[int] = None
    change_rate: Optional[float] = None


class MCPPracticalAnalyzer:
    """실용적 MCP 분석기 (작동하는 API만 사용)"""
    
    def __init__(self, oauth_manager):
        self.oauth_manager = oauth_manager
    
    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """종목 기본 정보 조회 (기존 시스템 활용)"""
        try:
            from kis_data_provider import KISDataProvider
            
            provider = KISDataProvider(self.oauth_manager)
            
            # 현재가 및 기본 정보 조회
            price_data = provider.get_current_price(symbol)
            if not price_data:
                return None
            
            # 종목 기본 정보 (PER, PBR, ROE 등)
            basic_info = provider.get_stock_basic_info(symbol)
            
            return StockInfo(
                symbol=symbol,
                name=basic_info.get('종목명', '') if basic_info else '',
                current_price=float(price_data.get('stck_prpr', 0)),
                per=basic_info.get('PER') if basic_info else None,
                pbr=basic_info.get('PBR') if basic_info else None,
                roe=basic_info.get('ROE') if basic_info else None,
                market_cap=basic_info.get('시가총액') if basic_info else None,
                sector=basic_info.get('업종', '') if basic_info else '',
                volume=int(price_data.get('acml_vol', 0)),
                change_rate=float(price_data.get('prdy_vrss_cttr', 0))
            )
            
        except Exception as e:
            logger.error(f"종목 정보 조회 실패: {symbol}, {e}")
            return None
    
    def find_value_stocks(self, symbols: List[str], criteria: Dict = None) -> List[Dict]:
        """가치주 발굴 (실제로 작동)"""
        try:
            if criteria is None:
                criteria = {
                    'per_max': 15.0,
                    'pbr_max': 1.5,
                    'roe_min': 10.0
                }
            
            value_stocks = []
            
            for symbol in symbols:
                try:
                    stock_info = self.get_stock_info(symbol)
                    if not stock_info:
                        continue
                    
                    # 가치주 필터링
                    per = stock_info.per or 999
                    pbr = stock_info.pbr or 999
                    roe = stock_info.roe or 0
                    
                    # 기준 충족 확인
                    is_value = (
                        per > 0 and per <= criteria['per_max'] and
                        pbr > 0 and pbr <= criteria['pbr_max'] and
                        roe >= criteria['roe_min']
                    )
                    
                    if is_value:
                        score = self._calculate_value_score(per, pbr, roe)
                        value_stocks.append({
                            'symbol': symbol,
                            'name': stock_info.name,
                            'per': per,
                            'pbr': pbr,
                            'roe': roe,
                            'current_price': stock_info.current_price,
                            'market_cap': stock_info.market_cap,
                            'sector': stock_info.sector,
                            'volume': stock_info.volume,
                            'change_rate': stock_info.change_rate,
                            'score': score
                        })
                        
                except Exception as e:
                    logger.warning(f"종목 {symbol} 분석 실패: {e}")
                    continue
            
            # 점수순 정렬
            value_stocks.sort(key=lambda x: x['score'], reverse=True)
            
            return value_stocks
            
        except Exception as e:
            logger.error(f"가치주 발굴 실패: {e}")
            return []
    
    def _calculate_value_score(self, per: float, pbr: float, roe: float) -> float:
        """가치주 점수 계산"""
        try:
            score = 0.0
            
            # PER 점수 (낮을수록 좋음, 최대 40점)
            if per > 0:
                if per <= 5:
                    score += 40
                elif per <= 10:
                    score += 35
                elif per <= 15:
                    score += 25
                elif per <= 20:
                    score += 15
            
            # PBR 점수 (낮을수록 좋음, 최대 30점)
            if pbr > 0:
                if pbr <= 0.8:
                    score += 30
                elif pbr <= 1.0:
                    score += 25
                elif pbr <= 1.5:
                    score += 15
                elif pbr <= 2.0:
                    score += 5
            
            # ROE 점수 (높을수록 좋음, 최대 30점)
            if roe >= 20:
                score += 30
            elif roe >= 15:
                score += 25
            elif roe >= 10:
                score += 15
            elif roe >= 5:
                score += 5
            
            return round(score, 1)
        except:
            return 0.0
    
    def get_market_summary(self) -> Dict:
        """시장 요약 정보 (작동하는 API 기반)"""
        try:
            from datetime import datetime
            
            # 주요 지수 대표 종목 조회
            kospi = self.get_stock_info("005930")  # 삼성전자
            kosdaq = self.get_stock_info("035420")  # 네이버
            
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            weekday = now.weekday()
            
            is_weekend = weekday >= 5
            is_market_open = not is_weekend and ((9 <= hour < 15) or (hour == 15 and minute <= 30))
            
            if is_weekend:
                status = "🔴 주말 휴장"
            elif is_market_open:
                status = "🟢 정규장 개장 중"
            else:
                status = "🔴 장 마감"
            
            return {
                'market_status': status,
                'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'weekday': ['월', '화', '수', '목', '금', '토', '일'][weekday],
                'kospi_sample': {
                    'name': kospi.name if kospi else 'N/A',
                    'price': kospi.current_price if kospi else 0,
                    'change_rate': kospi.change_rate if kospi else 0
                } if kospi else None,
                'kosdaq_sample': {
                    'name': kosdaq.name if kosdaq else 'N/A',
                    'price': kosdaq.current_price if kosdaq else 0,
                    'change_rate': kosdaq.change_rate if kosdaq else 0
                } if kosdaq else None
            }
            
        except Exception as e:
            logger.error(f"시장 요약 조회 실패: {e}")
            return None


