#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 고도화 기능 모듈
KIS API의 다양한 데이터를 활용한 고급 가치주 분석 기능
"""

import os
import re
import math
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional, List, Tuple
from collections import defaultdict, Counter

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

@dataclass
class MCPStockData:
    """MCP를 통해 수집한 종목 데이터"""
    symbol: str
    name: str
    current_price: float
    market_cap: float
    sector: str
    
    # 기본 지표
    per: Optional[float] = None
    pbr: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    
    # 거래 정보
    volume: Optional[int] = None
    trading_value: Optional[float] = None
    volatility: Optional[float] = None
    
    # 투자자 동향
    institutional_net: Optional[float] = None
    foreign_net: Optional[float] = None
    individual_net: Optional[float] = None
    
    # 섹터 정보
    sector_performance: Optional[float] = None
    relative_performance: Optional[float] = None
    
    # 배당/권리 정보
    dividend_amount: Optional[float] = None
    ex_dividend_date: Optional[str] = None
    rights_info: Optional[Dict] = None

@dataclass
class MCPSectorAnalysis:
    """MCP를 통한 섹터 분석 결과"""
    sector_name: str
    sector_index: float
    sector_change: float
    sector_volume: int
    
    # 섹터 내 상대 성과
    top_performers: List[str]
    underperformers: List[str]
    
    # 투자자 동향
    net_inflow: float
    foreign_participation: float

class MCPAdvancedAnalyzer:
    """MCP를 활용한 고급 가치주 분석기"""
    
    def __init__(self, oauth_manager):
        self.oauth_manager = oauth_manager
        self.session = self._create_session()
        self.cache = {}
        self.cache_ttl = 300  # 5분 캐시
        
    def _create_session(self):
        """재시도 가능한 requests 세션 생성"""
        session = requests.Session()
        retry_kwargs = dict(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504)
        )
        try:
            retry = Retry(**retry_kwargs, allowed_methods=frozenset({"GET", "POST"}))
        except TypeError:
            retry = Retry(**retry_kwargs, method_whitelist=frozenset({"GET", "POST"}))
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """인증 헤더 반환"""
        return self.oauth_manager.get_auth_headers()
    
    def _make_api_call(self, endpoint: str, params: Dict = None, use_cache: bool = True) -> Optional[Dict]:
        """MCP API 호출 (캐시 지원)"""
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        
        # 캐시 확인
        if use_cache and cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"MCP API 캐시 사용: {endpoint}")
                return cached_data
        
        try:
            url = f"{self.oauth_manager.base_url}/uapi/domestic-stock/v1/{endpoint}"
            headers = self._get_auth_headers()
            
            response = self.session.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 캐시 저장
                if use_cache:
                    self.cache[cache_key] = (data, time.time())
                
                return data
            else:
                logger.warning(f"MCP API 호출 실패: {endpoint}, 상태코드: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"MCP API 호출 오류: {endpoint}, {e}")
            return None
    
    @lru_cache(maxsize=100)
    def get_stock_basic_info(self, symbol: str) -> Optional[MCPStockData]:
        """종목 기본 정보 조회"""
        try:
            # 주식기본조회
            data = self._make_api_call("search/info", {"prdt_type_cd": "300", "pdno": symbol})
            if not data or 'output' not in data:
                return None
            
            output = data['output']
            
            # 기본 시세 정보도 함께 조회
            price_data = self.get_current_price(symbol)
            
            return MCPStockData(
                symbol=symbol,
                name=output.get('prdt_name', ''),
                current_price=price_data.get('stck_prpr', 0) if price_data else 0,
                market_cap=output.get('hts_avls', 0) * 100000000,  # 억원 단위
                sector=output.get('bstp_kor_isnm', ''),
                per=output.get('per'),
                pbr=output.get('pbr'),
                roe=output.get('roe'),
                roa=output.get('roa'),
                debt_ratio=output.get('debt_ratio'),
                current_ratio=output.get('current_ratio'),
                dividend_yield=output.get('dvyd')
            )
            
        except Exception as e:
            logger.error(f"종목 기본 정보 조회 실패: {symbol}, {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[Dict]:
        """현재가 시세 조회"""
        try:
            data = self._make_api_call("quote/inquire-price", {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol
            })
            return data.get('output') if data else None
        except Exception as e:
            logger.error(f"현재가 조회 실패: {symbol}, {e}")
            return None
    
    def get_financial_ratios(self, symbol: str) -> Optional[Dict]:
        """재무비율 상세 조회"""
        try:
            data = self._make_api_call("finance/financial-ratio", {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol
            })
            return data.get('output') if data else None
        except Exception as e:
            logger.error(f"재무비율 조회 실패: {symbol}, {e}")
            return None
    
    def get_sector_index(self, sector_code: str) -> Optional[Dict]:
        """업종별 지수 조회"""
        try:
            data = self._make_api_call("quote/inquire-index-price", {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": sector_code
            })
            return data.get('output') if data else None
        except Exception as e:
            logger.error(f"업종 지수 조회 실패: {sector_code}, {e}")
            return None
    
    def get_investor_trend(self, symbol: str, period: str = "1D") -> Optional[Dict]:
        """투자자별 매매동향 조회"""
        try:
            data = self._make_api_call("quote/inquire-investor", {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol,
                "fid_trgt_cls_code": "0" if period == "1D" else "1"
            })
            return data.get('output') if data else None
        except Exception as e:
            logger.error(f"투자자 동향 조회 실패: {symbol}, {e}")
            return None
    
    def get_dividend_info(self, symbol: str) -> Optional[Dict]:
        """배당 정보 조회"""
        try:
            data = self._make_api_call("quote/ksdinfo-dividend", {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol
            })
            return data.get('output') if data else None
        except Exception as e:
            logger.error(f"배당 정보 조회 실패: {symbol}, {e}")
            return None
    
    def get_chart_data(self, symbol: str, period: str = "D") -> Optional[List[Dict]]:
        """차트 데이터 조회 (일봉/주봉/월봉)"""
        try:
            period_map = {
                "D": "D",  # 일봉
                "W": "W",  # 주봉
                "M": "M"   # 월봉
            }
            
            data = self._make_api_call("quote/inquire-daily-itemchartprice", {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol,
                "fid_input_date_1": (datetime.now() - timedelta(days=365)).strftime("%Y%m%d"),
                "fid_input_date_2": datetime.now().strftime("%Y%m%d"),
                "fid_period_div_code": period_map.get(period, "D")
            })
            
            return data.get('output2') if data else None
            
        except Exception as e:
            logger.error(f"차트 데이터 조회 실패: {symbol}, {e}")
            return None
    
    def analyze_stock_comprehensive(self, symbol: str) -> Optional[Dict]:
        """종합적인 종목 분석"""
        try:
            # 기본 정보 수집
            basic_info = self.get_stock_basic_info(symbol)
            if not basic_info:
                return None
            
            # 추가 데이터 수집
            financial_ratios = self.get_financial_ratios(symbol)
            investor_trend = self.get_investor_trend(symbol)
            dividend_info = self.get_dividend_info(symbol)
            chart_data = self.get_chart_data(symbol)
            
            # 분석 결과 구성
            analysis = {
                'symbol': symbol,
                'name': basic_info.name,
                'current_price': basic_info.current_price,
                'market_cap': basic_info.market_cap,
                'sector': basic_info.sector,
                
                # 기본 지표
                'valuation_metrics': {
                    'per': basic_info.per,
                    'pbr': basic_info.pbr,
                    'roe': basic_info.roe,
                    'roa': basic_info.roa,
                    'debt_ratio': basic_info.debt_ratio,
                    'current_ratio': basic_info.current_ratio,
                    'dividend_yield': basic_info.dividend_yield
                },
                
                # 투자자 동향
                'investor_sentiment': self._analyze_investor_trend(investor_trend),
                
                # 배당 정보
                'dividend_analysis': self._analyze_dividend(dividend_info),
                
                # 기술적 분석
                'technical_analysis': self._analyze_technical(chart_data),
                
                # 종합 점수
                'comprehensive_score': self._calculate_comprehensive_score(
                    basic_info, financial_ratios, investor_trend, chart_data
                )
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"종합 분석 실패: {symbol}, {e}")
            return None
    
    def _analyze_investor_trend(self, investor_data: Optional[Dict]) -> Dict:
        """투자자 동향 분석"""
        if not investor_data:
            return {'sentiment': 'neutral', 'score': 50}
        
        try:
            # 기관/외국인/개인 순매수 금액 분석
            institutional = investor_data.get('ntby_qty', 0)
            foreign = investor_data.get('frgn_ntby_qty', 0)
            individual = investor_data.get('prsn_ntby_qty', 0)
            
            # 스마트머니 지표 (기관 + 외국인)
            smart_money = institutional + foreign
            
            # 감정 점수 계산 (0-100)
            if smart_money > 0:
                sentiment_score = min(100, 70 + (smart_money / 1000000) * 10)
                sentiment = 'positive'
            elif smart_money < 0:
                sentiment_score = max(0, 30 + (smart_money / 1000000) * 10)
                sentiment = 'negative'
            else:
                sentiment_score = 50
                sentiment = 'neutral'
            
            return {
                'sentiment': sentiment,
                'score': sentiment_score,
                'institutional_net': institutional,
                'foreign_net': foreign,
                'individual_net': individual,
                'smart_money': smart_money
            }
            
        except Exception as e:
            logger.error(f"투자자 동향 분석 실패: {e}")
            return {'sentiment': 'neutral', 'score': 50}
    
    def _analyze_dividend(self, dividend_data: Optional[Dict]) -> Dict:
        """배당 분석"""
        if not dividend_data:
            return {'yield': 0, 'consistency': 'unknown', 'score': 0}
        
        try:
            # 최근 배당 정보 추출
            recent_dividends = dividend_data.get('output1', [])
            if not recent_dividends:
                return {'yield': 0, 'consistency': 'unknown', 'score': 0}
            
            # 배당 수익률 계산
            total_dividend = sum(float(d.get('dvdn_amt', 0)) for d in recent_dividends[-4:])  # 최근 4회
            current_price = 50000  # 임시 가격 (실제로는 현재가 사용)
            dividend_yield = (total_dividend / current_price) * 100 if current_price > 0 else 0
            
            # 배당 일관성 평가
            dividend_amounts = [float(d.get('dvdn_amt', 0)) for d in recent_dividends[-4:]]
            if len(dividend_amounts) >= 2:
                consistency = 'stable' if max(dividend_amounts) - min(dividend_amounts) < max(dividend_amounts) * 0.2 else 'volatile'
            else:
                consistency = 'unknown'
            
            # 배당 점수 계산
            dividend_score = min(100, dividend_yield * 10)  # 1% = 10점
            
            return {
                'yield': dividend_yield,
                'consistency': consistency,
                'score': dividend_score,
                'recent_dividends': recent_dividends[-4:]
            }
            
        except Exception as e:
            logger.error(f"배당 분석 실패: {e}")
            return {'yield': 0, 'consistency': 'unknown', 'score': 0}
    
    def _analyze_technical(self, chart_data: Optional[List[Dict]]) -> Dict:
        """기술적 분석"""
        if not chart_data or len(chart_data) < 20:
            return {'trend': 'neutral', 'momentum': 'neutral', 'score': 50}
        
        try:
            # 최근 20일 데이터로 분석
            recent_data = chart_data[-20:]
            
            # 단순 이동평균 계산
            prices = [float(d.get('stck_clpr', 0)) for d in recent_data]
            sma_5 = sum(prices[-5:]) / 5
            sma_20 = sum(prices) / 20
            
            # 추세 분석
            if sma_5 > sma_20 * 1.02:
                trend = 'uptrend'
                trend_score = 70
            elif sma_5 < sma_20 * 0.98:
                trend = 'downtrend'
                trend_score = 30
            else:
                trend = 'sideways'
                trend_score = 50
            
            # 모멘텀 분석 (RSI 유사)
            gains = []
            losses = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            if avg_loss == 0:
                momentum_score = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                momentum_score = rsi
            
            # 종합 기술적 점수
            technical_score = (trend_score + momentum_score) / 2
            
            return {
                'trend': trend,
                'momentum': 'strong' if momentum_score > 70 else 'weak' if momentum_score < 30 else 'neutral',
                'score': technical_score,
                'sma_5': sma_5,
                'sma_20': sma_20,
                'rsi': momentum_score
            }
            
        except Exception as e:
            logger.error(f"기술적 분석 실패: {e}")
            return {'trend': 'neutral', 'momentum': 'neutral', 'score': 50}
    
    def _calculate_comprehensive_score(self, basic_info: MCPStockData, 
                                     financial_ratios: Optional[Dict],
                                     investor_trend: Optional[Dict],
                                     chart_data: Optional[List[Dict]]) -> Dict:
        """종합 점수 계산"""
        try:
            scores = {}
            weights = {
                'valuation': 0.3,      # 밸류에이션 30%
                'profitability': 0.25,  # 수익성 25%
                'stability': 0.2,       # 안정성 20%
                'growth': 0.15,         # 성장성 15%
                'sentiment': 0.1        # 투자자 감정 10%
            }
            
            # 밸류에이션 점수 (PER, PBR 기준)
            valuation_score = 50
            if basic_info.per and basic_info.pbr:
                if basic_info.per > 0 and basic_info.per < 15:
                    valuation_score += 20
                elif basic_info.per >= 15 and basic_info.per < 25:
                    valuation_score += 10
                
                if basic_info.pbr > 0 and basic_info.pbr < 1.5:
                    valuation_score += 20
                elif basic_info.pbr >= 1.5 and basic_info.pbr < 2.5:
                    valuation_score += 10
            
            # 수익성 점수 (ROE, ROA 기준)
            profitability_score = 50
            if basic_info.roe and basic_info.roe > 0:
                if basic_info.roe > 15:
                    profitability_score = 80
                elif basic_info.roe > 10:
                    profitability_score = 70
                elif basic_info.roe > 5:
                    profitability_score = 60
            
            # 안정성 점수 (부채비율, 유동비율 기준)
            stability_score = 50
            if basic_info.debt_ratio is not None:
                if basic_info.debt_ratio < 30:
                    stability_score = 80
                elif basic_info.debt_ratio < 50:
                    stability_score = 70
                elif basic_info.debt_ratio < 70:
                    stability_score = 60
            
            if basic_info.current_ratio and basic_info.current_ratio > 2:
                stability_score += 10
            
            # 성장성 점수 (매출/영업이익 증가율)
            growth_score = 50  # 차트 데이터에서 계산 가능
            
            # 투자자 감정 점수
            sentiment_score = 50
            if investor_trend:
                sentiment_analysis = self._analyze_investor_trend(investor_trend)
                sentiment_score = sentiment_analysis['score']
            
            # 가중평균 계산
            total_score = (
                valuation_score * weights['valuation'] +
                profitability_score * weights['profitability'] +
                stability_score * weights['stability'] +
                growth_score * weights['growth'] +
                sentiment_score * weights['sentiment']
            )
            
            return {
                'total_score': round(total_score, 1),
                'component_scores': {
                    'valuation': valuation_score,
                    'profitability': profitability_score,
                    'stability': stability_score,
                    'growth': growth_score,
                    'sentiment': sentiment_score
                },
                'grade': self._get_grade(total_score),
                'recommendation': self._get_recommendation(total_score)
            }
            
        except Exception as e:
            logger.error(f"종합 점수 계산 실패: {e}")
            return {'total_score': 50, 'grade': 'C', 'recommendation': 'HOLD'}
    
    def _get_grade(self, score: float) -> str:
        """점수에 따른 등급 반환"""
        if score >= 80:
            return 'A+'
        elif score >= 70:
            return 'A'
        elif score >= 60:
            return 'B+'
        elif score >= 50:
            return 'B'
        elif score >= 40:
            return 'C+'
        elif score >= 30:
            return 'C'
        else:
            return 'D'
    
    def _get_recommendation(self, score: float) -> str:
        """점수에 따른 추천 반환"""
        if score >= 75:
            return 'STRONG_BUY'
        elif score >= 65:
            return 'BUY'
        elif score >= 55:
            return 'HOLD'
        elif score >= 45:
            return 'WEAK_HOLD'
        else:
            return 'SELL'
    
    def analyze_sector_comprehensive(self, sector_code: str) -> Optional[MCPSectorAnalysis]:
        """섹터 종합 분석"""
        try:
            # 섹터 지수 조회
            sector_data = self.get_sector_index(sector_code)
            if not sector_data:
                return None
            
            # 섹터 내 주요 종목들의 투자자 동향 분석
            # (실제로는 섹터 내 상위 종목들을 조회해야 함)
            
            return MCPSectorAnalysis(
                sector_name=sector_data.get('hts_kor_isnm', ''),
                sector_index=float(sector_data.get('bstp_nmix_prpr', 0)),
                sector_change=float(sector_data.get('prdy_vrss', 0)),
                sector_volume=int(sector_data.get('acml_vol', 0)),
                top_performers=[],  # 구현 필요
                underperformers=[],  # 구현 필요
                net_inflow=0,  # 구현 필요
                foreign_participation=0  # 구현 필요
            )
            
        except Exception as e:
            logger.error(f"섹터 분석 실패: {sector_code}, {e}")
            return None
    
    def get_top_value_stocks(self, limit: int = 20, criteria: Dict = None) -> List[Dict]:
        """MCP를 활용한 가치주 발굴 (실용적 구현)"""
        try:
            # 주요 대형주 목록 (실제로 분석할 가치가 있는 종목들)
            major_stocks = [
                # 대형주 (시가총액 상위)
                ("005930", "삼성전자"),
                ("000660", "SK하이닉스"),
                ("005380", "현대차"),
                ("035420", "NAVER"),
                ("051910", "LG화학"),
                ("006400", "삼성SDI"),
                ("035720", "카카오"),
                ("000270", "기아"),
                ("068270", "셀트리온"),
                ("207940", "삼성바이오로직스"),
                ("005490", "POSCO홀딩스"),
                ("012330", "현대모비스"),
                ("028260", "삼성물산"),
                ("066570", "LG전자"),
                ("003670", "포스코퓨처엠"),
                ("096770", "SK이노베이션"),
                ("017670", "SK텔레콤"),
                ("009150", "삼성전기"),
                ("034730", "SK"),
                ("018260", "삼성에스디에스"),
                ("033780", "KT&G"),
                ("015760", "한국전력"),
                ("032830", "삼성생명"),
                ("003550", "LG"),
                ("010130", "고려아연"),
                ("055550", "신한지주"),
                ("086790", "하나금융지주"),
                ("105560", "KB금융"),
                ("000810", "삼성화재"),
                ("316140", "우리금융지주")
            ]
            
            # 가치주 기준 (기본값)
            if criteria is None:
                criteria = {
                    'per_max': 15.0,
                    'pbr_max': 1.5,
                    'roe_min': 10.0,
                    'score_min': 60.0
                }
            
            value_stocks = []
            logger.info(f"가치주 발굴 시작: {len(major_stocks)}개 종목 분석 중...")
            
            for i, (symbol, name) in enumerate(major_stocks[:limit]):
                try:
                    # 개별 종목 분석
                    stock_info = self.get_stock_basic_info(symbol)
                    if not stock_info:
                        continue
                    
                    # 가치주 필터링
                    per = stock_info.per or 999
                    pbr = stock_info.pbr or 999
                    roe = stock_info.roe or 0
                    
                    # 기준 충족 여부 확인
                    is_value_stock = (
                        per > 0 and per <= criteria['per_max'] and
                        pbr > 0 and pbr <= criteria['pbr_max'] and
                        roe >= criteria['roe_min']
                    )
                    
                    if is_value_stock:
                        value_stocks.append({
                            'symbol': symbol,
                            'name': name,
                            'per': per,
                            'pbr': pbr,
                            'roe': roe,
                            'current_price': stock_info.current_price,
                            'market_cap': stock_info.market_cap,
                            'sector': stock_info.sector,
                            'score': self._calculate_value_score(per, pbr, roe)
                        })
                    
                    if (i + 1) % 5 == 0:
                        logger.info(f"진행: {i + 1}/{min(limit, len(major_stocks))} 종목 분석 완료")
                        
                except Exception as e:
                    logger.warning(f"종목 {symbol} 분석 실패: {e}")
                    continue
            
            # 점수순 정렬
            value_stocks.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"가치주 발굴 완료: {len(value_stocks)}개 발굴")
            return value_stocks
            
        except Exception as e:
            logger.error(f"가치주 발굴 실패: {e}")
            return []
    
    def _calculate_value_score(self, per: float, pbr: float, roe: float) -> float:
        """가치주 점수 계산"""
        try:
            score = 0.0
            
            # PER 점수 (낮을수록 좋음)
            if per > 0 and per <= 10:
                score += 40
            elif per <= 15:
                score += 30
            elif per <= 20:
                score += 20
            
            # PBR 점수 (낮을수록 좋음)
            if pbr > 0 and pbr <= 1.0:
                score += 30
            elif pbr <= 1.5:
                score += 20
            elif pbr <= 2.0:
                score += 10
            
            # ROE 점수 (높을수록 좋음)
            if roe >= 15:
                score += 30
            elif roe >= 10:
                score += 20
            elif roe >= 5:
                score += 10
            
            return round(score, 1)
        except:
            return 0.0
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
        logger.info("MCP 캐시 초기화 완료")