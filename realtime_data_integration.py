#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 데이터 연동 시스템
시장 지수, 뉴스 감정, 경제 지표 등을 실시간으로 수집하고 분석
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
import websockets
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import time
import ssl
import urllib3

# SSL 문제 해결
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class MarketDataType(Enum):
    """시장 데이터 타입"""
    INDEX = "index"           # 시장 지수
    NEWS_SENTIMENT = "news"   # 뉴스 감정
    ECONOMIC_INDICATOR = "economic"  # 경제 지표
    ESG_SCORE = "esg"         # ESG 점수
    ANALYST_RATING = "rating" # 애널리스트 평가

@dataclass
class RealTimeMarketData:
    """실시간 시장 데이터"""
    data_type: MarketDataType
    symbol: str
    name: str
    value: float
    change: float
    change_percent: float
    timestamp: datetime
    source: str
    confidence: float  # 데이터 신뢰도 (0-1)

@dataclass
class NewsSentimentData:
    """뉴스 감정 데이터"""
    symbol: str
    sentiment_score: float  # -1 to 1
    sentiment_label: str    # positive, negative, neutral
    news_count: int
    confidence: float
    timestamp: datetime
    sources: List[str]

class RealTimeDataProvider:
    """실시간 데이터 제공자"""
    
    def __init__(self):
        self.session = None
        self.websocket_connections = {}
        self.data_cache = {}
        self.last_update = {}
        self.cache_duration = {
            MarketDataType.INDEX: timedelta(minutes=1),
            MarketDataType.NEWS_SENTIMENT: timedelta(minutes=5),
            MarketDataType.ECONOMIC_INDICATOR: timedelta(hours=1),
            MarketDataType.ESG_SCORE: timedelta(hours=6),
            MarketDataType.ANALYST_RATING: timedelta(hours=12)
        }
        
        # API 키 및 설정 (config.yaml에서 로드)
        self.api_keys = {
            'alpha_vantage': 'YOUR_ALPHA_VANTAGE_KEY',
            'news_api': 'YOUR_NEWS_API_KEY',
            'finnhub': 'YOUR_FINNHUB_KEY',
            'msci_esg': 'YOUR_MSCI_ESG_KEY'
        }
        
        # config.yaml에서 네이버 API 키 로드
        self._load_naver_api_keys()
        
        logger.info("🔄 실시간 데이터 제공자 초기화 완료")
    
    def _load_naver_api_keys(self):
        """config.yaml에서 네이버 API 키 로드"""
        try:
            import yaml
            import os
            
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                if 'api' in config and 'naver' in config['api']:
                    naver_config = config['api']['naver']
                    self.api_keys['naver_client_id'] = naver_config.get('client_id', '')
                    self.api_keys['naver_client_secret'] = naver_config.get('client_secret', '')
                    self.api_keys['naver_base_url'] = naver_config.get('base_url', 'https://openapi.naver.com/v1/search/news.json')
                    self.api_keys['naver_rate_limit'] = naver_config.get('rate_limit', 10)
                    self.api_keys['naver_max_results'] = naver_config.get('max_results', 100)
                    
                    logger.info("✅ 네이버 API 키 로드 완료")
                else:
                    logger.warning("⚠️ config.yaml에서 네이버 API 설정을 찾을 수 없습니다")
            else:
                logger.warning("⚠️ config.yaml 파일을 찾을 수 없습니다")
        
        except Exception as e:
            logger.error(f"❌ 네이버 API 키 로드 실패: {e}")
            # 기본값 설정
            self.api_keys['naver_client_id'] = ''
            self.api_keys['naver_client_secret'] = ''
    
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
        for ws in self.websocket_connections.values():
            await ws.close()
    
    async def get_market_index_data(self, indices: List[str] = None) -> List[RealTimeMarketData]:
        """실시간 시장 지수 데이터 조회"""
        if indices is None:
            indices = ['KOSPI', 'KOSDAQ', 'S&P500', 'NASDAQ', 'DOW']
        
        results = []
        tasks = []
        
        for index in indices:
            task = self._fetch_index_data(index)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"시장 지수 데이터 조회 오류: {result}")
            elif result:
                valid_results.append(result)
        
        return valid_results
    
    async def _fetch_index_data(self, index: str) -> Optional[RealTimeMarketData]:
        """개별 지수 데이터 조회"""
        try:
            # 캐시 확인
            cache_key = f"index_{index}"
            if self._is_cache_valid(cache_key, MarketDataType.INDEX):
                return self.data_cache.get(cache_key)
            
            # Yahoo Finance API 사용
            ticker_symbol = self._get_ticker_symbol(index)
            if not ticker_symbol:
                return None
            
            # 비동기로 데이터 조회
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                ticker = await loop.run_in_executor(executor, yf.Ticker, ticker_symbol)
                info = await loop.run_in_executor(executor, ticker.info)
                hist = await loop.run_in_executor(executor, ticker.history, "1d")
            
            if hist.empty or 'currentPrice' not in info:
                return None
            
            current_price = info.get('currentPrice', 0)
            previous_close = info.get('previousClose', current_price)
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close != 0 else 0
            
            data = RealTimeMarketData(
                data_type=MarketDataType.INDEX,
                symbol=index,
                name=self._get_index_name(index),
                value=current_price,
                change=change,
                change_percent=change_percent,
                timestamp=datetime.now(),
                source='yahoo_finance',
                confidence=0.9
            )
            
            # 캐시 저장
            self._cache_data(cache_key, data, MarketDataType.INDEX)
            
            logger.info(f"📈 {index}: {current_price:.2f} ({change_percent:+.2f}%)")
            return data
            
        except Exception as e:
            logger.error(f"❌ {index} 지수 데이터 조회 실패: {e}")
            return None
    
    def _get_ticker_symbol(self, index: str) -> str:
        """지수명을 티커 심볼로 변환"""
        symbol_map = {
            'KOSPI': '^KS11',
            'KOSDAQ': '^KQ11',
            'S&P500': '^GSPC',
            'NASDAQ': '^IXIC',
            'DOW': '^DJI',
            'VIX': '^VIX'
        }
        return symbol_map.get(index, index)
    
    def _get_index_name(self, index: str) -> str:
        """지수명 매핑"""
        name_map = {
            'KOSPI': 'KOSPI 종합주가지수',
            'KOSDAQ': 'KOSDAQ 종합주가지수',
            'S&P500': 'S&P 500 지수',
            'NASDAQ': '나스닥 종합지수',
            'DOW': '다우존스 산업평균지수',
            'VIX': '변동성 지수'
        }
        return name_map.get(index, index)
    
    async def get_news_sentiment_data(self, symbols: List[str]) -> List[NewsSentimentData]:
        """실시간 뉴스 감정 데이터 조회"""
        results = []
        tasks = []
        
        for symbol in symbols:
            task = self._fetch_news_sentiment(symbol)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"뉴스 감정 데이터 조회 오류: {result}")
            elif result:
                valid_results.append(result)
        
        return valid_results
    
    async def _fetch_news_sentiment(self, symbol: str) -> Optional[NewsSentimentData]:
        """개별 종목 뉴스 감정 분석"""
        try:
            # 캐시 확인
            cache_key = f"news_{symbol}"
            if self._is_cache_valid(cache_key, MarketDataType.NEWS_SENTIMENT):
                return self.data_cache.get(cache_key)
            
            # 뉴스 데이터 수집 (여러 소스)
            news_data = await self._collect_news_data(symbol)
            
            if not news_data:
                return None
            
            # 감정 분석 수행
            sentiment_result = self._analyze_sentiment(news_data)
            
            data = NewsSentimentData(
                symbol=symbol,
                sentiment_score=sentiment_result['score'],
                sentiment_label=sentiment_result['label'],
                news_count=len(news_data),
                confidence=sentiment_result['confidence'],
                timestamp=datetime.now(),
                sources=['news_api', 'naver_news', 'yahoo_finance']
            )
            
            # 캐시 저장
            self._cache_data(cache_key, data, MarketDataType.NEWS_SENTIMENT)
            
            logger.info(f"📰 {symbol} 뉴스 감정: {sentiment_result['label']} ({sentiment_result['score']:.2f})")
            return data
            
        except Exception as e:
            logger.error(f"❌ {symbol} 뉴스 감정 분석 실패: {e}")
            return None
    
    async def _collect_news_data(self, symbol: str) -> List[Dict[str, Any]]:
        """뉴스 데이터 수집"""
        news_data = []
        
        try:
            # NewsAPI 사용
            if self.api_keys.get('news_api'):
                news_data.extend(await self._fetch_news_api(symbol))
            
            # Yahoo Finance 뉴스
            news_data.extend(await self._fetch_yahoo_news(symbol))
            
            # Naver 뉴스 (한국 종목) - 항상 시도
            naver_news = await self._fetch_naver_news(symbol)
            news_data.extend(naver_news)
            
        except Exception as e:
            logger.error(f"뉴스 데이터 수집 실패 {symbol}: {e}")
        
        return news_data
    
    async def _fetch_news_api(self, symbol: str) -> List[Dict[str, Any]]:
        """NewsAPI에서 뉴스 조회"""
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f'"{symbol}" OR "{self._get_company_name(symbol)}"',
                'language': 'ko,en',
                'sortBy': 'publishedAt',
                'pageSize': 10,
                'apiKey': self.api_keys['news_api']
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('articles', [])
        
        except Exception as e:
            logger.error(f"NewsAPI 조회 실패 {symbol}: {e}")
        
        return []
    
    async def _fetch_yahoo_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Yahoo Finance 뉴스 조회"""
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                ticker = await loop.run_in_executor(executor, yf.Ticker, symbol)
                news = await loop.run_in_executor(executor, ticker.news)
            
            return news or []
        
        except Exception as e:
            logger.error(f"Yahoo Finance 뉴스 조회 실패 {symbol}: {e}")
            return []
    
    async def _fetch_naver_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Naver 뉴스 API를 사용한 뉴스 조회"""
        try:
            if not self.api_keys.get('naver_client_id') or not self.api_keys.get('naver_client_secret'):
                logger.warning("⚠️ 네이버 API 키가 설정되지 않았습니다")
                return []
            
            company_name = self._get_company_name(symbol)
            
            # 네이버 뉴스 API 호출
            headers = {
                'X-Naver-Client-Id': self.api_keys['naver_client_id'],
                'X-Naver-Client-Secret': self.api_keys['naver_client_secret']
            }
            
            # 검색 쿼리 (회사명 + 주식 관련 키워드)
            query = f'"{company_name}" 주식 OR "{company_name}" 실적 OR "{company_name}" 배당 OR "{company_name}" 투자'
            
            params = {
                'query': query,
                'display': min(10, self.api_keys.get('naver_max_results', 100)),  # 최대 10개
                'sort': 'date',  # 날짜순 정렬
                'start': 1
            }
            
            base_url = self.api_keys.get('naver_base_url', 'https://openapi.naver.com/v1/search/news.json')
            
            async with self.session.get(base_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    news_items = data.get('items', [])
                    
                    # 뉴스 데이터 정리
                    processed_news = []
                    for item in news_items:
                        processed_news.append({
                            'title': item.get('title', '').replace('<b>', '').replace('</b>', ''),
                            'description': item.get('description', '').replace('<b>', '').replace('</b>', ''),
                            'publishedAt': item.get('pubDate', ''),
                            'source': 'naver_news',
                            'link': item.get('link', ''),
                            'originallink': item.get('originallink', '')
                        })
                    
                    logger.info(f"📰 {symbol} 네이버 뉴스 {len(processed_news)}개 조회 완료")
                    return processed_news
                
                else:
                    logger.error(f"네이버 뉴스 API 오류 {symbol}: HTTP {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Naver 뉴스 조회 실패 {symbol}: {e}")
            return []
    
    def _analyze_sentiment(self, news_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """뉴스 감정 분석"""
        if not news_data:
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.0}
        
        # 간단한 감정 분석 (실제로는 더 정교한 NLP 모델 사용)
        positive_keywords = ['상승', '증가', '성장', '호재', '긍정', '개선', '상승세', 'rally', 'gain', 'growth']
        negative_keywords = ['하락', '감소', '악화', '악재', '부정', '우려', '하락세', 'fall', 'decline', 'concern']
        
        total_score = 0
        total_weight = 0
        
        for news in news_data:
            text = (news.get('title', '') + ' ' + news.get('description', '')).lower()
            
            positive_count = sum(1 for keyword in positive_keywords if keyword in text)
            negative_count = sum(1 for keyword in negative_keywords if keyword in text)
            
            # 가중치 계산 (제목이 더 중요)
            title_weight = 2
            content_weight = 1
            
            news_score = (positive_count - negative_count) / max(len(text.split()), 1)
            weight = title_weight if news.get('title') else content_weight
            
            total_score += news_score * weight
            total_weight += weight
        
        if total_weight == 0:
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.0}
        
        final_score = total_score / total_weight
        final_score = max(-1, min(1, final_score))  # -1 to 1 범위로 제한
        
        if final_score > 0.1:
            label = 'positive'
        elif final_score < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        confidence = min(1.0, len(news_data) * 0.1)  # 뉴스 개수에 따른 신뢰도
        
        return {
            'score': final_score,
            'label': label,
            'confidence': confidence
        }
    
    def _get_company_name(self, symbol: str) -> str:
        """심볼로부터 회사명 조회"""
        # 실제로는 데이터베이스나 API에서 조회
        name_map = {
            '005930': '삼성전자',
            '000660': 'SK하이닉스',
            '373220': 'LG에너지솔루션',
            '035420': 'NAVER',
            '005380': '현대차'
        }
        return name_map.get(symbol, f'Company_{symbol}')
    
    async def get_economic_indicators(self) -> List[RealTimeMarketData]:
        """실시간 경제 지표 조회"""
        indicators = []
        
        try:
            # 주요 경제 지표들
            economic_data = await asyncio.gather(
                self._fetch_interest_rate(),
                self._fetch_inflation_rate(),
                self._fetch_gdp_growth(),
                self._fetch_unemployment_rate(),
                return_exceptions=True
            )
            
            for data in economic_data:
                if isinstance(data, Exception):
                    logger.error(f"경제 지표 조회 오류: {data}")
                elif data:
                    indicators.append(data)
        
        except Exception as e:
            logger.error(f"경제 지표 조회 실패: {e}")
        
        return indicators
    
    async def _fetch_interest_rate(self) -> Optional[RealTimeMarketData]:
        """금리 데이터 조회"""
        try:
            # 실제로는 FRED API 또는 한국은행 API 사용
            # 여기서는 시뮬레이션
            return RealTimeMarketData(
                data_type=MarketDataType.ECONOMIC_INDICATOR,
                symbol='KOREA_IR',
                name='한국 기준금리',
                value=3.25,
                change=0.0,
                change_percent=0.0,
                timestamp=datetime.now(),
                source='bok_api',
                confidence=0.95
            )
        except Exception as e:
            logger.error(f"금리 데이터 조회 실패: {e}")
            return None
    
    async def _fetch_inflation_rate(self) -> Optional[RealTimeMarketData]:
        """인플레이션 데이터 조회"""
        try:
            return RealTimeMarketData(
                data_type=MarketDataType.ECONOMIC_INDICATOR,
                symbol='KOREA_INFLATION',
                name='한국 소비자물가상승률',
                value=2.8,
                change=-0.1,
                change_percent=-3.45,
                timestamp=datetime.now(),
                source='kostat_api',
                confidence=0.9
            )
        except Exception as e:
            logger.error(f"인플레이션 데이터 조회 실패: {e}")
            return None
    
    async def _fetch_gdp_growth(self) -> Optional[RealTimeMarketData]:
        """GDP 성장률 데이터 조회"""
        try:
            return RealTimeMarketData(
                data_type=MarketDataType.ECONOMIC_INDICATOR,
                symbol='KOREA_GDP',
                name='한국 GDP 성장률',
                value=1.2,
                change=0.1,
                change_percent=9.09,
                timestamp=datetime.now(),
                source='bok_api',
                confidence=0.85
            )
        except Exception as e:
            logger.error(f"GDP 성장률 데이터 조회 실패: {e}")
            return None
    
    async def _fetch_unemployment_rate(self) -> Optional[RealTimeMarketData]:
        """실업률 데이터 조회"""
        try:
            return RealTimeMarketData(
                data_type=MarketDataType.ECONOMIC_INDICATOR,
                symbol='KOREA_UNEMPLOYMENT',
                name='한국 실업률',
                value=2.6,
                change=-0.1,
                change_percent=-3.70,
                timestamp=datetime.now(),
                source='kostat_api',
                confidence=0.9
            )
        except Exception as e:
            logger.error(f"실업률 데이터 조회 실패: {e}")
            return None
    
    def _is_cache_valid(self, cache_key: str, data_type: MarketDataType) -> bool:
        """캐시 유효성 검사"""
        if cache_key not in self.data_cache:
            return False
        
        last_update = self.last_update.get(cache_key)
        if not last_update:
            return False
        
        cache_duration = self.cache_duration.get(data_type, timedelta(minutes=5))
        return datetime.now() - last_update < cache_duration
    
    def _cache_data(self, cache_key: str, data: Any, data_type: MarketDataType):
        """데이터 캐시 저장"""
        self.data_cache[cache_key] = data
        self.last_update[cache_key] = datetime.now()
    
    async def start_websocket_connection(self, symbols: List[str]):
        """WebSocket 연결 시작 (실시간 데이터 스트림)"""
        try:
            # Finnhub WebSocket 연결 예시
            url = f"wss://ws.finnhub.io?token={self.api_keys.get('finnhub')}"
            
            async with websockets.connect(url) as websocket:
                self.websocket_connections['finnhub'] = websocket
                
                # 구독 신청
                for symbol in symbols:
                    subscribe_msg = {"type": "subscribe", "symbol": symbol}
                    await websocket.send(json.dumps(subscribe_msg))
                
                logger.info(f"🔄 WebSocket 연결 시작: {len(symbols)}개 종목 구독")
                
                # 메시지 수신 루프
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_websocket_message(data)
                    except json.JSONDecodeError as e:
                        logger.error(f"WebSocket 메시지 파싱 오류: {e}")
                    except Exception as e:
                        logger.error(f"WebSocket 메시지 처리 오류: {e}")
        
        except Exception as e:
            logger.error(f"WebSocket 연결 실패: {e}")
    
    async def _handle_websocket_message(self, data: Dict[str, Any]):
        """WebSocket 메시지 처리"""
        try:
            if data.get('type') == 'trade':
                symbol = data.get('s')
                price = data.get('p')
                volume = data.get('v')
                timestamp = data.get('t')
                
                logger.info(f"📊 실시간 거래: {symbol} - {price} (거래량: {volume})")
                
                # 실시간 데이터를 캐시에 업데이트
                cache_key = f"realtime_{symbol}"
                realtime_data = RealTimeMarketData(
                    data_type=MarketDataType.INDEX,
                    symbol=symbol,
                    name=self._get_company_name(symbol),
                    value=price,
                    change=0,  # 이전 가격과 비교 필요
                    change_percent=0,
                    timestamp=datetime.fromtimestamp(timestamp / 1000),
                    source='websocket',
                    confidence=0.95
                )
                
                self._cache_data(cache_key, realtime_data, MarketDataType.INDEX)
        
        except Exception as e:
            logger.error(f"WebSocket 메시지 처리 실패: {e}")

class RealTimeMarketAnalyzer:
    """실시간 시장 분석기"""
    
    def __init__(self):
        self.data_provider = RealTimeDataProvider()
        self.market_sentiment_cache = {}
        
    async def analyze_market_sentiment(self, symbols: List[str]) -> Dict[str, Any]:
        """시장 감정 종합 분석"""
        try:
            async with self.data_provider as provider:
                # 다양한 데이터 수집
                market_indices = await provider.get_market_index_data()
                news_sentiments = await provider.get_news_sentiment_data(symbols)
                economic_indicators = await provider.get_economic_indicators()
                
                # 종합 감정 점수 계산
                sentiment_analysis = self._calculate_comprehensive_sentiment(
                    market_indices, news_sentiments, economic_indicators
                )
                
                return sentiment_analysis
        
        except Exception as e:
            logger.error(f"시장 감정 분석 실패: {e}")
            return {}
    
    def _calculate_comprehensive_sentiment(self, 
                                         market_indices: List[RealTimeMarketData],
                                         news_sentiments: List[NewsSentimentData],
                                         economic_indicators: List[RealTimeMarketData]) -> Dict[str, Any]:
        """종합 감정 점수 계산"""
        
        # 시장 지수 감정 (가중평균)
        market_sentiment = 0
        if market_indices:
            total_weight = 0
            for index in market_indices:
                weight = 1.0
                if index.symbol in ['KOSPI', 'KOSDAQ']:
                    weight = 2.0  # 한국 지수에 더 높은 가중치
                
                market_sentiment += index.change_percent * weight
                total_weight += weight
            
            market_sentiment = market_sentiment / total_weight if total_weight > 0 else 0
        
        # 뉴스 감정 (가중평균)
        news_sentiment = 0
        if news_sentiments:
            total_weight = 0
            for news in news_sentiments:
                weight = news.confidence * news.news_count
                news_sentiment += news.sentiment_score * weight
                total_weight += weight
            
            news_sentiment = news_sentiment / total_weight if total_weight > 0 else 0
        
        # 경제 지표 감정
        economic_sentiment = 0
        if economic_indicators:
            for indicator in economic_indicators:
                if 'IR' in indicator.symbol:  # 금리
                    economic_sentiment += -indicator.change * 0.5  # 금리 상승은 부정적
                elif 'INFLATION' in indicator.symbol:  # 인플레이션
                    economic_sentiment += -indicator.change * 0.3
                elif 'GDP' in indicator.symbol:  # GDP
                    economic_sentiment += indicator.change * 0.4
                elif 'UNEMPLOYMENT' in indicator.symbol:  # 실업률
                    economic_sentiment += -indicator.change * 0.3
        
        # 최종 종합 점수 (가중평균)
        final_sentiment = (
            market_sentiment * 0.4 +      # 시장 지수 40%
            news_sentiment * 0.4 +        # 뉴스 감정 40%
            economic_sentiment * 0.2      # 경제 지표 20%
        )
        
        # 감정 레벨 결정
        if final_sentiment > 0.5:
            sentiment_level = 'very_positive'
        elif final_sentiment > 0.1:
            sentiment_level = 'positive'
        elif final_sentiment > -0.1:
            sentiment_level = 'neutral'
        elif final_sentiment > -0.5:
            sentiment_level = 'negative'
        else:
            sentiment_level = 'very_negative'
        
        return {
            'comprehensive_sentiment': final_sentiment,
            'sentiment_level': sentiment_level,
            'market_sentiment': market_sentiment,
            'news_sentiment': news_sentiment,
            'economic_sentiment': economic_sentiment,
            'market_indices': [asdict(index) for index in market_indices],
            'news_sentiments': [asdict(news) for news in news_sentiments],
            'economic_indicators': [asdict(indicator) for indicator in economic_indicators],
            'timestamp': datetime.now().isoformat(),
            'confidence': self._calculate_confidence(market_indices, news_sentiments, economic_indicators)
        }
    
    def _calculate_confidence(self, 
                            market_indices: List[RealTimeMarketData],
                            news_sentiments: List[NewsSentimentData],
                            economic_indicators: List[RealTimeMarketData]) -> float:
        """종합 신뢰도 계산"""
        
        total_confidence = 0
        total_weight = 0
        
        # 시장 지수 신뢰도
        if market_indices:
            avg_confidence = np.mean([index.confidence for index in market_indices])
            total_confidence += avg_confidence * len(market_indices)
            total_weight += len(market_indices)
        
        # 뉴스 감정 신뢰도
        if news_sentiments:
            avg_confidence = np.mean([news.confidence for news in news_sentiments])
            total_confidence += avg_confidence * len(news_sentiments)
            total_weight += len(news_sentiments)
        
        # 경제 지표 신뢰도
        if economic_indicators:
            avg_confidence = np.mean([indicator.confidence for indicator in economic_indicators])
            total_confidence += avg_confidence * len(economic_indicators)
            total_weight += len(economic_indicators)
        
        return total_confidence / total_weight if total_weight > 0 else 0.0

async def main():
    """메인 실행 함수"""
    analyzer = RealTimeMarketAnalyzer()
    
    symbols = ['005930', '000660', '035420', '005380']
    
    print("🔄 실시간 시장 감정 분석 시작...")
    sentiment_analysis = await analyzer.analyze_market_sentiment(symbols)
    
    if sentiment_analysis:
        print("\n📊 종합 시장 감정 분석 결과:")
        print(f"종합 감정 점수: {sentiment_analysis['comprehensive_sentiment']:.3f}")
        print(f"감정 레벨: {sentiment_analysis['sentiment_level']}")
        print(f"시장 감정: {sentiment_analysis['market_sentiment']:.3f}")
        print(f"뉴스 감정: {sentiment_analysis['news_sentiment']:.3f}")
        print(f"경제 감정: {sentiment_analysis['economic_sentiment']:.3f}")
        print(f"종합 신뢰도: {sentiment_analysis['confidence']:.3f}")
        
        # 결과를 JSON 파일로 저장
        with open(f'realtime_sentiment_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
            json.dump(sentiment_analysis, f, ensure_ascii=False, indent=2, default=str)
        
        print("\n💾 실시간 감정 분석 결과가 JSON 파일로 저장되었습니다.")
    else:
        print("❌ 실시간 시장 감정 분석 실패")

if __name__ == "__main__":
    asyncio.run(main())
