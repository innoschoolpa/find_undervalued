#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
외부 데이터 통합 시스템
MSCI ESG, 전문 기관 데이터, 글로벌 시장 데이터 등 외부 데이터 활용
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import time
import ssl
import urllib3

# SSL 문제 해결
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class DataSource(Enum):
    """데이터 소스"""
    MSCI_ESG = "msci_esg"
    S_P_GLOBAL = "sp_global"
    MOODY_S = "moodys"
    REFINITIV = "refinitiv"
    BLOOMBERG = "bloomberg"
    FRED = "fred"
    WORLD_BANK = "world_bank"
    IMF = "imf"
    OECD = "oecd"

@dataclass
class ESGScore:
    """ESG 점수"""
    symbol: str
    company_name: str
    environmental_score: float
    social_score: float
    governance_score: float
    overall_score: float
    esg_rating: str
    data_source: str
    last_updated: datetime
    peer_ranking: int
    industry_avg: float

@dataclass
class CreditRating:
    """신용등급"""
    symbol: str
    company_name: str
    rating: str
    outlook: str
    data_source: str
    last_updated: datetime
    previous_rating: Optional[str] = None

@dataclass
class AnalystConsensus:
    """애널리스트 합의"""
    symbol: str
    company_name: str
    target_price: float
    current_price: float
    recommendation: str
    num_analysts: int
    data_source: str
    last_updated: datetime
    price_change: float = 0.0

@dataclass
class EconomicIndicator:
    """경제 지표"""
    indicator_name: str
    value: float
    unit: str
    period: str
    data_source: str
    last_updated: datetime
    previous_value: Optional[float] = None
    change_percent: Optional[float] = None

class ExternalDataProvider:
    """외부 데이터 제공자"""
    
    def __init__(self):
        self.session = None
        self.api_keys = {
            'msci_esg': 'YOUR_MSCI_ESG_KEY',
            'sp_global': 'YOUR_SP_GLOBAL_KEY',
            'fred': 'YOUR_FRED_KEY',
            'world_bank': 'YOUR_WORLD_BANK_KEY',
            'alpha_vantage': 'YOUR_ALPHA_VANTAGE_KEY'
        }
        self.cache = {}
        self.cache_duration = {
            DataSource.MSCI_ESG: timedelta(days=1),
            DataSource.S_P_GLOBAL: timedelta(days=1),
            DataSource.FRED: timedelta(hours=6),
            DataSource.WORLD_BANK: timedelta(days=7)
        }
        
        logger.info("🌐 외부 데이터 제공자 초기화 완료")
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        # SSL 검증 비활성화된 컨텍스트 생성
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    async def get_esg_scores(self, symbols: List[str]) -> List[ESGScore]:
        """ESG 점수 조회"""
        esg_scores = []
        tasks = []
        
        for symbol in symbols:
            task = self._fetch_esg_score(symbol)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"ESG 점수 조회 오류: {result}")
            elif result:
                esg_scores.append(result)
        
        return esg_scores
    
    async def _fetch_esg_score(self, symbol: str) -> Optional[ESGScore]:
        """개별 ESG 점수 조회"""
        try:
            # 캐시 확인
            cache_key = f"esg_{symbol}"
            if self._is_cache_valid(cache_key, DataSource.MSCI_ESG):
                return self.cache.get(cache_key)
            
            # MSCI ESG API 호출 (시뮬레이션)
            esg_data = await self._call_msci_esg_api(symbol)
            
            if not esg_data:
                return None
            
            esg_score = ESGScore(
                symbol=symbol,
                company_name=esg_data['company_name'],
                environmental_score=esg_data['environmental_score'],
                social_score=esg_data['social_score'],
                governance_score=esg_data['governance_score'],
                overall_score=esg_data['overall_score'],
                esg_rating=esg_data['esg_rating'],
                data_source='MSCI_ESG',
                last_updated=datetime.now(),
                peer_ranking=esg_data['peer_ranking'],
                industry_avg=esg_data['industry_avg']
            )
            
            # 캐시 저장
            self._cache_data(cache_key, esg_score, DataSource.MSCI_ESG)
            
            logger.info(f"🌱 {symbol} ESG 점수: {esg_score.overall_score:.1f} ({esg_score.esg_rating})")
            return esg_score
            
        except Exception as e:
            logger.error(f"❌ {symbol} ESG 점수 조회 실패: {e}")
            return None
    
    async def _call_msci_esg_api(self, symbol: str) -> Optional[Dict[str, Any]]:
        """MSCI ESG API 호출 (시뮬레이션)"""
        try:
            # 실제 API 호출 대신 시뮬레이션 데이터 반환
            company_name = self._get_company_name(symbol)
            
            # 업종별 ESG 점수 시뮬레이션
            esg_scores_by_sector = {
                'TECH': {'e': 75, 's': 80, 'g': 85, 'rating': 'A'},
                'FINANCE': {'e': 70, 's': 75, 'g': 80, 'rating': 'A-'},
                'MANUFACTURING': {'e': 65, 's': 70, 'g': 75, 'rating': 'B+'},
                'HEALTHCARE': {'e': 80, 's': 85, 'g': 80, 'rating': 'A'},
                'CONSUMER': {'e': 70, 's': 75, 'g': 70, 'rating': 'B+'}
            }
            
            # 심볼별 기본 업종 매핑
            sector_mapping = {
                '005930': 'TECH',
                '000660': 'TECH',
                '035420': 'TECH',
                '035720': 'TECH',
                '005380': 'MANUFACTURING',
                '000270': 'MANUFACTURING',
                '068270': 'HEALTHCARE',
                '207940': 'HEALTHCARE'
            }
            
            sector = sector_mapping.get(symbol, 'TECH')
            base_scores = esg_scores_by_sector.get(sector, {'e': 70, 's': 75, 'g': 80, 'rating': 'B+'})
            
            # 약간의 랜덤 변동 추가
            import random
            e_score = base_scores['e'] + random.randint(-5, 5)
            s_score = base_scores['s'] + random.randint(-5, 5)
            g_score = base_scores['g'] + random.randint(-5, 5)
            
            overall_score = (e_score + s_score + g_score) / 3
            
            return {
                'company_name': company_name,
                'environmental_score': max(0, min(100, e_score)),
                'social_score': max(0, min(100, s_score)),
                'governance_score': max(0, min(100, g_score)),
                'overall_score': max(0, min(100, overall_score)),
                'esg_rating': base_scores['rating'],
                'peer_ranking': random.randint(1, 100),
                'industry_avg': overall_score + random.randint(-10, 10)
            }
            
        except Exception as e:
            logger.error(f"MSCI ESG API 호출 실패 {symbol}: {e}")
            return None
    
    async def get_credit_ratings(self, symbols: List[str]) -> List[CreditRating]:
        """신용등급 조회"""
        credit_ratings = []
        tasks = []
        
        for symbol in symbols:
            task = self._fetch_credit_rating(symbol)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"신용등급 조회 오류: {result}")
            elif result:
                credit_ratings.append(result)
        
        return credit_ratings
    
    async def _fetch_credit_rating(self, symbol: str) -> Optional[CreditRating]:
        """개별 신용등급 조회"""
        try:
            # 캐시 확인
            cache_key = f"credit_{symbol}"
            if self._is_cache_valid(cache_key, DataSource.S_P_GLOBAL):
                return self.cache.get(cache_key)
            
            # S&P Global API 호출 (시뮬레이션)
            credit_data = await self._call_sp_global_api(symbol)
            
            if not credit_data:
                return None
            
            credit_rating = CreditRating(
                symbol=symbol,
                company_name=credit_data['company_name'],
                rating=credit_data['rating'],
                outlook=credit_data['outlook'],
                data_source='S&P_Global',
                last_updated=datetime.now(),
                previous_rating=credit_data.get('previous_rating')
            )
            
            # 캐시 저장
            self._cache_data(cache_key, credit_rating, DataSource.S_P_GLOBAL)
            
            logger.info(f"🏦 {symbol} 신용등급: {credit_rating.rating} ({credit_rating.outlook})")
            return credit_rating
            
        except Exception as e:
            logger.error(f"❌ {symbol} 신용등급 조회 실패: {e}")
            return None
    
    async def _call_sp_global_api(self, symbol: str) -> Optional[Dict[str, Any]]:
        """S&P Global API 호출 (시뮬레이션)"""
        try:
            company_name = self._get_company_name(symbol)
            
            # 회사 규모별 신용등급 시뮬레이션
            credit_ratings_by_size = {
                'large_cap': ['AAA', 'AA+', 'AA', 'AA-', 'A+'],
                'mid_cap': ['A', 'A-', 'BBB+', 'BBB', 'BBB-'],
                'small_cap': ['BBB-', 'BB+', 'BB', 'BB-', 'B+']
            }
            
            # 회사별 규모 매핑
            size_mapping = {
                '005930': 'large_cap',
                '000660': 'large_cap',
                '035420': 'large_cap',
                '035720': 'large_cap',
                '005380': 'large_cap',
                '000270': 'large_cap'
            }
            
            company_size = size_mapping.get(symbol, 'mid_cap')
            possible_ratings = credit_ratings_by_size.get(company_size, ['BBB', 'BBB-', 'BB+'])
            
            # 랜덤 선택
            import random
            rating = random.choice(possible_ratings)
            outlook = random.choice(['Positive', 'Stable', 'Negative'])
            
            return {
                'company_name': company_name,
                'rating': rating,
                'outlook': outlook,
                'previous_rating': None  # 이전 등급은 구현 생략
            }
            
        except Exception as e:
            logger.error(f"S&P Global API 호출 실패 {symbol}: {e}")
            return None
    
    async def get_analyst_consensus(self, symbols: List[str]) -> List[AnalystConsensus]:
        """애널리스트 합의 조회"""
        consensus_data = []
        tasks = []
        
        for symbol in symbols:
            task = self._fetch_analyst_consensus(symbol)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"애널리스트 합의 조회 오류: {result}")
            elif result:
                consensus_data.append(result)
        
        return consensus_data
    
    async def _fetch_analyst_consensus(self, symbol: str) -> Optional[AnalystConsensus]:
        """개별 애널리스트 합의 조회"""
        try:
            # Yahoo Finance에서 애널리스트 데이터 조회
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                ticker = await loop.run_in_executor(executor, yf.Ticker, symbol)
                info = await loop.run_in_executor(executor, ticker.info)
            
            if not info:
                return None
            
            # 애널리스트 데이터 추출
            target_price = info.get('targetMeanPrice', info.get('currentPrice', 0))
            current_price = info.get('currentPrice', 0)
            recommendation = info.get('recommendationKey', 'hold')
            num_analysts = info.get('numberOfAnalystOpinions', 0)
            
            # 추천 등급 변환
            recommendation_map = {
                'buy': 'BUY',
                'strong_buy': 'STRONG_BUY',
                'hold': 'HOLD',
                'sell': 'SELL',
                'strong_sell': 'STRONG_SELL'
            }
            
            recommendation = recommendation_map.get(recommendation, 'HOLD')
            
            price_change = ((target_price - current_price) / current_price * 100) if current_price > 0 else 0
            
            consensus = AnalystConsensus(
                symbol=symbol,
                company_name=self._get_company_name(symbol),
                target_price=target_price,
                current_price=current_price,
                recommendation=recommendation,
                num_analysts=num_analysts,
                data_source='Yahoo_Finance',
                last_updated=datetime.now(),
                price_change=price_change
            )
            
            logger.info(f"📈 {symbol} 애널리스트 합의: {recommendation} (목표가: {target_price:.0f})")
            return consensus
            
        except Exception as e:
            logger.error(f"❌ {symbol} 애널리스트 합의 조회 실패: {e}")
            return None
    
    async def get_economic_indicators(self, indicators: List[str] = None) -> List[EconomicIndicator]:
        """경제 지표 조회"""
        if indicators is None:
            indicators = [
                'KOREA_IR',      # 한국 기준금리
                'KOREA_GDP',     # 한국 GDP
                'KOREA_INFLATION',  # 한국 인플레이션
                'KOREA_UNEMPLOYMENT',  # 한국 실업률
                'US_IR',         # 미국 기준금리
                'US_GDP',        # 미국 GDP
                'US_INFLATION',  # 미국 인플레이션
                'GLOBAL_OIL'     # 국제유가
            ]
        
        economic_data = []
        tasks = []
        
        for indicator in indicators:
            task = self._fetch_economic_indicator(indicator)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"경제 지표 조회 오류: {result}")
            elif result:
                economic_data.append(result)
        
        return economic_data
    
    async def _fetch_economic_indicator(self, indicator: str) -> Optional[EconomicIndicator]:
        """개별 경제 지표 조회"""
        try:
            # 캐시 확인
            cache_key = f"economic_{indicator}"
            if self._is_cache_valid(cache_key, DataSource.FRED):
                return self.cache.get(cache_key)
            
            # FRED API 호출 (시뮬레이션)
            economic_data = await self._call_fred_api(indicator)
            
            if not economic_data:
                return None
            
            economic_indicator = EconomicIndicator(
                indicator_name=economic_data['name'],
                value=economic_data['value'],
                unit=economic_data['unit'],
                period=economic_data['period'],
                data_source='FRED',
                last_updated=datetime.now(),
                previous_value=economic_data.get('previous_value'),
                change_percent=economic_data.get('change_percent')
            )
            
            # 캐시 저장
            self._cache_data(cache_key, economic_indicator, DataSource.FRED)
            
            logger.info(f"📊 {indicator}: {economic_indicator.value} {economic_indicator.unit}")
            return economic_indicator
            
        except Exception as e:
            logger.error(f"❌ {indicator} 경제 지표 조회 실패: {e}")
            return None
    
    async def _call_fred_api(self, indicator: str) -> Optional[Dict[str, Any]]:
        """FRED API 호출 (시뮬레이션)"""
        try:
            # 경제 지표별 시뮬레이션 데이터
            indicator_data = {
                'KOREA_IR': {'name': '한국 기준금리', 'value': 3.25, 'unit': '%', 'period': '2024-01'},
                'KOREA_GDP': {'name': '한국 GDP', 'value': 1.8, 'unit': '%', 'period': '2024-Q3'},
                'KOREA_INFLATION': {'name': '한국 인플레이션', 'value': 2.8, 'unit': '%', 'period': '2024-12'},
                'KOREA_UNEMPLOYMENT': {'name': '한국 실업률', 'value': 2.6, 'unit': '%', 'period': '2024-12'},
                'US_IR': {'name': '미국 기준금리', 'value': 5.25, 'unit': '%', 'period': '2024-01'},
                'US_GDP': {'name': '미국 GDP', 'value': 2.5, 'unit': '%', 'period': '2024-Q3'},
                'US_INFLATION': {'name': '미국 인플레이션', 'value': 3.2, 'unit': '%', 'period': '2024-12'},
                'GLOBAL_OIL': {'name': '국제유가(WTI)', 'value': 75.5, 'unit': 'USD/배럴', 'period': '2024-12'}
            }
            
            return indicator_data.get(indicator)
            
        except Exception as e:
            logger.error(f"FRED API 호출 실패 {indicator}: {e}")
            return None
    
    async def get_global_market_data(self, markets: List[str] = None) -> Dict[str, Any]:
        """글로벌 시장 데이터 조회"""
        if markets is None:
            markets = ['^GSPC', '^IXIC', '^DJI', '^VIX', '^KS11', '^KQ11']
        
        market_data = {}
        tasks = []
        
        for market in markets:
            task = self._fetch_market_data(market)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"시장 데이터 조회 오류 {markets[i]}: {result}")
            elif result:
                market_data[markets[i]] = result
        
        return market_data
    
    async def _fetch_market_data(self, market: str) -> Optional[Dict[str, Any]]:
        """개별 시장 데이터 조회"""
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                ticker = await loop.run_in_executor(executor, yf.Ticker, market)
                info = await loop.run_in_executor(executor, ticker.info)
                hist = await loop.run_in_executor(executor, ticker.history, "1d")
            
            if not info or hist.empty:
                return None
            
            current_price = info.get('currentPrice', 0)
            previous_close = info.get('previousClose', current_price)
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close != 0 else 0
            
            return {
                'current_price': current_price,
                'previous_close': previous_close,
                'change': change,
                'change_percent': change_percent,
                'volume': info.get('volume', 0),
                'market_cap': info.get('marketCap', 0),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ {market} 시장 데이터 조회 실패: {e}")
            return None
    
    def _get_company_name(self, symbol: str) -> str:
        """심볼로부터 회사명 조회"""
        name_map = {
            '005930': '삼성전자',
            '000660': 'SK하이닉스',
            '035420': 'NAVER',
            '035720': '카카오',
            '005380': '현대차',
            '000270': '기아',
            '068270': '셀트리온',
            '207940': '삼성바이오로직스'
        }
        return name_map.get(symbol, f'Company_{symbol}')
    
    def _is_cache_valid(self, cache_key: str, data_source: DataSource) -> bool:
        """캐시 유효성 검사"""
        if cache_key not in self.cache:
            return False
        
        cache_data = self.cache[cache_key]
        if not hasattr(cache_data, 'last_updated'):
            return False
        
        cache_duration = self.cache_duration.get(data_source, timedelta(hours=1))
        return datetime.now() - cache_data.last_updated < cache_duration
    
    def _cache_data(self, cache_key: str, data: Any, data_source: DataSource):
        """데이터 캐시 저장"""
        self.cache[cache_key] = data

class ExternalDataAnalyzer:
    """외부 데이터 분석기"""
    
    def __init__(self):
        self.data_provider = ExternalDataProvider()
        
    async def comprehensive_external_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """종합 외부 데이터 분석"""
        try:
            async with self.data_provider as provider:
                # 다양한 외부 데이터 수집
                esg_scores = await provider.get_esg_scores(symbols)
                credit_ratings = await provider.get_credit_ratings(symbols)
                analyst_consensus = await provider.get_analyst_consensus(symbols)
                economic_indicators = await provider.get_economic_indicators()
                global_market_data = await provider.get_global_market_data()
                
                # 종합 분석 수행
                analysis = self._perform_comprehensive_analysis(
                    esg_scores, credit_ratings, analyst_consensus,
                    economic_indicators, global_market_data
                )
                
                return analysis
        
        except Exception as e:
            logger.error(f"종합 외부 데이터 분석 실패: {e}")
            return {}
    
    def _perform_comprehensive_analysis(self, esg_scores: List[ESGScore],
                                      credit_ratings: List[CreditRating],
                                      analyst_consensus: List[AnalystConsensus],
                                      economic_indicators: List[EconomicIndicator],
                                      global_market_data: Dict[str, Any]) -> Dict[str, Any]:
        """종합 분석 수행"""
        
        # ESG 분석
        esg_analysis = self._analyze_esg_data(esg_scores)
        
        # 신용등급 분석
        credit_analysis = self._analyze_credit_data(credit_ratings)
        
        # 애널리스트 합의 분석
        consensus_analysis = self._analyze_consensus_data(analyst_consensus)
        
        # 경제 환경 분석
        economic_analysis = self._analyze_economic_data(economic_indicators)
        
        # 글로벌 시장 분석
        market_analysis = self._analyze_market_data(global_market_data)
        
        # 종합 점수 계산
        comprehensive_score = self._calculate_comprehensive_score(
            esg_analysis, credit_analysis, consensus_analysis,
            economic_analysis, market_analysis
        )
        
        return {
            'comprehensive_score': comprehensive_score,
            'esg_analysis': esg_analysis,
            'credit_analysis': credit_analysis,
            'consensus_analysis': consensus_analysis,
            'economic_analysis': economic_analysis,
            'market_analysis': market_analysis,
            'analysis_date': datetime.now().isoformat()
        }
    
    def _analyze_esg_data(self, esg_scores: List[ESGScore]) -> Dict[str, Any]:
        """ESG 데이터 분석"""
        if not esg_scores:
            return {}
        
        # 평균 ESG 점수
        avg_esg = np.mean([score.overall_score for score in esg_scores])
        
        # ESG 등급 분포
        rating_distribution = {}
        for score in esg_scores:
            rating = score.esg_rating
            rating_distribution[rating] = rating_distribution.get(rating, 0) + 1
        
        # 업종별 ESG 점수
        sector_esg = {}
        for score in esg_scores:
            sector = self._get_sector_by_symbol(score.symbol)
            if sector not in sector_esg:
                sector_esg[sector] = []
            sector_esg[sector].append(score.overall_score)
        
        for sector in sector_esg:
            sector_esg[sector] = np.mean(sector_esg[sector])
        
        return {
            'average_esg_score': avg_esg,
            'rating_distribution': rating_distribution,
            'sector_esg_scores': sector_esg,
            'esg_scores': [asdict(score) for score in esg_scores]
        }
    
    def _analyze_credit_data(self, credit_ratings: List[CreditRating]) -> Dict[str, Any]:
        """신용등급 데이터 분석"""
        if not credit_ratings:
            return {}
        
        # 신용등급 분포
        rating_distribution = {}
        outlook_distribution = {}
        
        for rating in credit_ratings:
            # 등급 분포
            rating_distribution[rating.rating] = rating_distribution.get(rating.rating, 0) + 1
            # 전망 분포
            outlook_distribution[rating.outlook] = outlook_distribution.get(rating.outlook, 0) + 1
        
        # 평균 신용등급 점수 (숫자로 변환)
        rating_scores = []
        for rating in credit_ratings:
            score = self._convert_rating_to_score(rating.rating)
            rating_scores.append(score)
        
        avg_credit_score = np.mean(rating_scores) if rating_scores else 0
        
        return {
            'average_credit_score': avg_credit_score,
            'rating_distribution': rating_distribution,
            'outlook_distribution': outlook_distribution,
            'credit_ratings': [asdict(rating) for rating in credit_ratings]
        }
    
    def _analyze_consensus_data(self, analyst_consensus: List[AnalystConsensus]) -> Dict[str, Any]:
        """애널리스트 합의 데이터 분석"""
        if not analyst_consensus:
            return {}
        
        # 추천 분포
        recommendation_distribution = {}
        for consensus in analyst_consensus:
            rec = consensus.recommendation
            recommendation_distribution[rec] = recommendation_distribution.get(rec, 0) + 1
        
        # 평균 목표가 상승률
        price_changes = [consensus.price_change for consensus in analyst_consensus]
        avg_price_change = np.mean(price_changes) if price_changes else 0
        
        # 총 애널리스트 수
        total_analysts = sum([consensus.num_analysts for consensus in analyst_consensus])
        
        return {
            'recommendation_distribution': recommendation_distribution,
            'average_price_change': avg_price_change,
            'total_analysts': total_analysts,
            'consensus_data': [asdict(consensus) for consensus in analyst_consensus]
        }
    
    def _analyze_economic_data(self, economic_indicators: List[EconomicIndicator]) -> Dict[str, Any]:
        """경제 데이터 분석"""
        if not economic_indicators:
            return {}
        
        # 국가별 경제 지표
        country_indicators = {'KOREA': [], 'US': [], 'GLOBAL': []}
        
        for indicator in economic_indicators:
            if 'KOREA' in indicator.indicator_name:
                country_indicators['KOREA'].append(asdict(indicator))
            elif 'US' in indicator.indicator_name:
                country_indicators['US'].append(asdict(indicator))
            else:
                country_indicators['GLOBAL'].append(asdict(indicator))
        
        # 경제 환경 점수 (간단한 시뮬레이션)
        economic_score = self._calculate_economic_score(economic_indicators)
        
        return {
            'economic_score': economic_score,
            'country_indicators': country_indicators,
            'all_indicators': [asdict(indicator) for indicator in economic_indicators]
        }
    
    def _analyze_market_data(self, global_market_data: Dict[str, Any]) -> Dict[str, Any]:
        """시장 데이터 분석"""
        if not global_market_data:
            return {}
        
        # 시장별 성과
        market_performance = {}
        for market, data in global_market_data.items():
            market_performance[market] = {
                'change_percent': data['change_percent'],
                'current_price': data['current_price']
            }
        
        # 전반적 시장 상황
        changes = [data['change_percent'] for data in global_market_data.values()]
        avg_market_change = np.mean(changes) if changes else 0
        
        # 시장 변동성 (VIX 기준)
        vix_data = global_market_data.get('^VIX')
        market_volatility = vix_data['current_price'] if vix_data else 20
        
        return {
            'market_performance': market_performance,
            'average_market_change': avg_market_change,
            'market_volatility': market_volatility,
            'market_sentiment': self._determine_market_sentiment(avg_market_change, market_volatility)
        }
    
    def _calculate_comprehensive_score(self, *analyses) -> float:
        """종합 점수 계산"""
        weights = {
            'esg': 0.20,
            'credit': 0.25,
            'consensus': 0.30,
            'economic': 0.15,
            'market': 0.10
        }
        
        total_score = 0
        total_weight = 0
        
        for analysis in analyses:
            if analysis:
                analysis_type = None
                for key in weights.keys():
                    if key in str(analysis):
                        analysis_type = key
                        break
                
                if analysis_type and f'{analysis_type}_score' in analysis:
                    weight = weights[analysis_type]
                    score = analysis[f'{analysis_type}_score']
                    total_score += score * weight
                    total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    # 헬퍼 메서드들
    def _get_sector_by_symbol(self, symbol: str) -> str:
        """심볼로부터 업종 조회"""
        sector_mapping = {
            '005930': 'TECH',
            '000660': 'TECH',
            '035420': 'TECH',
            '035720': 'TECH',
            '005380': 'MANUFACTURING',
            '000270': 'MANUFACTURING',
            '068270': 'HEALTHCARE',
            '207940': 'HEALTHCARE'
        }
        return sector_mapping.get(symbol, 'UNKNOWN')
    
    def _convert_rating_to_score(self, rating: str) -> float:
        """신용등급을 점수로 변환"""
        rating_scores = {
            'AAA': 95, 'AA+': 90, 'AA': 85, 'AA-': 80,
            'A+': 75, 'A': 70, 'A-': 65,
            'BBB+': 60, 'BBB': 55, 'BBB-': 50,
            'BB+': 45, 'BB': 40, 'BB-': 35,
            'B+': 30, 'B': 25, 'B-': 20,
            'CCC+': 15, 'CCC': 10, 'CCC-': 5,
            'CC': 2, 'C': 1, 'D': 0
        }
        return rating_scores.get(rating, 50)
    
    def _calculate_economic_score(self, indicators: List[EconomicIndicator]) -> float:
        """경제 점수 계산"""
        # 간단한 경제 점수 계산 (실제로는 더 정교한 모델 필요)
        score = 70  # 기본 점수
        
        for indicator in indicators:
            if 'IR' in indicator.indicator_name:  # 금리
                if indicator.value < 5:
                    score += 5  # 낮은 금리는 긍정적
                else:
                    score -= 5
            elif 'GDP' in indicator.indicator_name:  # GDP
                if indicator.value > 2:
                    score += 10  # 높은 성장률은 긍정적
                else:
                    score -= 10
            elif 'INFLATION' in indicator.indicator_name:  # 인플레이션
                if 2 <= indicator.value <= 3:
                    score += 5  # 적정 인플레이션
                else:
                    score -= 5
        
        return max(0, min(100, score))
    
    def _determine_market_sentiment(self, avg_change: float, volatility: float) -> str:
        """시장 감정 결정"""
        if avg_change > 2 and volatility < 25:
            return 'very_positive'
        elif avg_change > 1 and volatility < 30:
            return 'positive'
        elif avg_change > -1 and volatility < 35:
            return 'neutral'
        elif avg_change > -2 and volatility < 40:
            return 'negative'
        else:
            return 'very_negative'

async def main():
    """메인 실행 함수"""
    analyzer = ExternalDataAnalyzer()
    
    symbols = ['005930', '000660', '035420', '005380']
    
    print("🌐 외부 데이터 종합 분석 시작...")
    analysis = await analyzer.comprehensive_external_analysis(symbols)
    
    if analysis:
        print("\n📊 외부 데이터 종합 분석 결과:")
        print(f"종합 점수: {analysis['comprehensive_score']:.1f}점")
        
        if 'esg_analysis' in analysis and analysis['esg_analysis']:
            print(f"평균 ESG 점수: {analysis['esg_analysis']['average_esg_score']:.1f}점")
        
        if 'consensus_analysis' in analysis and analysis['consensus_analysis']:
            print(f"평균 목표가 상승률: {analysis['consensus_analysis']['average_price_change']:.1f}%")
        
        if 'market_analysis' in analysis and analysis['market_analysis']:
            print(f"시장 감정: {analysis['market_analysis']['market_sentiment']}")
        
        # 결과를 JSON 파일로 저장
        with open(f'external_data_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
        
        print("\n💾 외부 데이터 분석 결과가 JSON 파일로 저장되었습니다.")
    else:
        print("❌ 외부 데이터 분석 실패")

if __name__ == "__main__":
    asyncio.run(main())
