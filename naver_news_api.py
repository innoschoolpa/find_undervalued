#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 뉴스 API 연동 모듈
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import urllib.parse

logger = logging.getLogger(__name__)

@dataclass
class NewsItem:
    """뉴스 아이템 데이터 구조"""
    title: str
    description: str
    link: str
    pub_date: datetime
    source: str
    sentiment_score: float = 0.0
    relevance_score: float = 0.0

class NaverNewsAPI:
    """네이버 뉴스 API 클라이언트"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://openapi.naver.com/v1/search/news.json"
        self.headers = {
            'X-Naver-Client-Id': client_id,
            'X-Naver-Client-Secret': client_secret
        }
    
    def search_news(self, query: str, display: int = 10, start: int = 1, 
                   sort: str = 'sim') -> Dict[str, Any]:
        """
        네이버 뉴스 검색
        
        Args:
            query: 검색어
            display: 검색 결과 출력 건수 (1-100)
            start: 검색 시작 위치 (1-1000)
            sort: 정렬 옵션 ('sim': 정확도순, 'date': 날짜순)
        """
        try:
            params = {
                'query': query,
                'display': min(display, 100),
                'start': min(start, 1000),
                'sort': sort
            }
            
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"📰 네이버 뉴스 검색 성공: {query} - {len(data.get('items', []))}건")
                return data
            else:
                logger.error(f"❌ 네이버 뉴스 API 오류: {response.status_code} - {response.text}")
                return {'items': [], 'total': 0}
                
        except Exception as e:
            logger.error(f"❌ 네이버 뉴스 검색 실패: {e}")
            return {'items': [], 'total': 0}
    
    def get_company_news(self, company_name: str, days: int = 30) -> List[NewsItem]:
        """특정 회사 관련 뉴스 수집"""
        try:
            # 검색어 설정 (회사명 + 주식 관련 키워드)
            search_queries = [
                f"{company_name} 주가",
                f"{company_name} 실적",
                f"{company_name} 배당",
                f"{company_name} 투자",
                f"{company_name} 전망"
            ]
            
            all_news = []
            
            for query in search_queries:
                # 각 검색어별로 뉴스 수집
                for start in range(1, 51, 10):  # 최대 5페이지 (50건)
                    data = self.search_news(query, display=10, start=start, sort='date')
                    
                    if not data.get('items'):
                        break
                    
                    for item in data['items']:
                        news_item = self._parse_news_item(item, company_name)
                        if news_item:
                            all_news.append(news_item)
            
            # 중복 제거 (링크 기준)
            unique_news = {}
            for news in all_news:
                if news.link not in unique_news:
                    unique_news[news.link] = news
            
            # 날짜순 정렬
            sorted_news = sorted(unique_news.values(), key=lambda x: x.pub_date, reverse=True)
            
            logger.info(f"📰 {company_name} 관련 뉴스 수집 완료: {len(sorted_news)}건")
            return sorted_news
            
        except Exception as e:
            logger.error(f"❌ {company_name} 뉴스 수집 실패: {e}")
            return []
    
    def _parse_news_item(self, item: Dict[str, Any], company_name: str) -> Optional[NewsItem]:
        """뉴스 아이템 파싱"""
        try:
            # HTML 태그 제거
            title = self._clean_html(item.get('title', ''))
            description = self._clean_html(item.get('description', ''))
            link = item.get('link', '')
            pub_date_str = item.get('pubDate', '')
            
            # 날짜 파싱
            try:
                pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            except:
                # 타임존 정보가 없는 경우 현재 시간으로 설정
                pub_date = datetime.now()
                pub_date = pub_date.replace(tzinfo=None)
            
            # 출처 추출
            source = item.get('originallink', link)
            if 'naver.com' in source:
                source = '네이버뉴스'
            elif 'daum.net' in source:
                source = '다음뉴스'
            elif 'chosun.com' in source:
                source = '조선일보'
            elif 'joongang.co.kr' in source:
                source = '중앙일보'
            elif 'donga.com' in source:
                source = '동아일보'
            else:
                source = '기타'
            
            # 감정 점수 계산
            sentiment_score = self._calculate_sentiment(title + ' ' + description)
            
            # 관련성 점수 계산
            relevance_score = self._calculate_relevance(title + ' ' + description, company_name)
            
            return NewsItem(
                title=title,
                description=description,
                link=link,
                pub_date=pub_date,
                source=source,
                sentiment_score=sentiment_score,
                relevance_score=relevance_score
            )
            
        except Exception as e:
            logger.error(f"❌ 뉴스 아이템 파싱 실패: {e}")
            return None
    
    def _clean_html(self, text: str) -> str:
        """HTML 태그 제거"""
        import re
        # HTML 태그 제거
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', text)
        # HTML 엔티티 디코딩
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        return text.strip()
    
    def _calculate_sentiment(self, text: str) -> float:
        """간단한 감정 분석"""
        positive_words = [
            '상승', '증가', '성장', '개선', '우수', '긍정', '호재', '매수',
            '투자', '전망', '기대', '성공', '돌파', '급등', '강세'
        ]
        negative_words = [
            '하락', '감소', '악화', '부정', '위험', '문제', '악재', '매도',
            '우려', '실망', '실패', '급락', '약세', '부진', '침체'
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count + negative_count == 0:
            return 0.0
        
        sentiment = (positive_count - negative_count) / (positive_count + negative_count)
        return max(-1, min(1, sentiment))
    
    def _calculate_relevance(self, text: str, company_name: str) -> float:
        """관련성 점수 계산"""
        relevance_score = 0.0
        
        # 회사명 포함 여부
        if company_name in text:
            relevance_score += 0.5
        
        # 주식 관련 키워드
        stock_keywords = ['주가', '주식', '투자', '실적', '배당', '전망', '분석', '추천']
        for keyword in stock_keywords:
            if keyword in text:
                relevance_score += 0.1
        
        return min(1.0, relevance_score)

class NewsAnalyzer:
    """뉴스 분석기"""
    
    def __init__(self, naver_api: NaverNewsAPI):
        self.naver_api = naver_api
    
    def analyze_company_sentiment(self, company_name: str) -> Dict[str, Any]:
        """회사별 뉴스 감정 분석"""
        try:
            # 뉴스 수집
            news_items = self.naver_api.get_company_news(company_name)
            
            if not news_items:
                return {
                    'total_news': 0,
                    'avg_sentiment': 0.0,
                    'sentiment_trend': 'neutral',
                    'recent_sentiment': 0.0,
                    'news_by_source': {},
                    'sentiment_distribution': {}
                }
            
            # 감정 점수 계산
            sentiment_scores = [news.sentiment_score for news in news_items]
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            
            # 최근 7일 감정 분석
            recent_date = datetime.now() - timedelta(days=7)
            # 타임존 정보 통일
            if recent_date.tzinfo is None:
                recent_date = recent_date.replace(tzinfo=None)
            recent_news = [news for news in news_items if news.pub_date.replace(tzinfo=None) >= recent_date]
            recent_sentiment = 0.0
            if recent_news:
                recent_sentiment = sum([news.sentiment_score for news in recent_news]) / len(recent_news)
            
            # 출처별 뉴스 수
            news_by_source = {}
            for news in news_items:
                source = news.source
                if source not in news_by_source:
                    news_by_source[source] = 0
                news_by_source[source] += 1
            
            # 감정 분포
            sentiment_distribution = {
                'positive': len([s for s in sentiment_scores if s > 0.2]),
                'neutral': len([s for s in sentiment_scores if -0.2 <= s <= 0.2]),
                'negative': len([s for s in sentiment_scores if s < -0.2])
            }
            
            # 감정 트렌드 결정
            if avg_sentiment > 0.2:
                sentiment_trend = 'positive'
            elif avg_sentiment < -0.2:
                sentiment_trend = 'negative'
            else:
                sentiment_trend = 'neutral'
            
            result = {
                'total_news': len(news_items),
                'avg_sentiment': avg_sentiment,
                'sentiment_trend': sentiment_trend,
                'recent_sentiment': recent_sentiment,
                'news_by_source': news_by_source,
                'sentiment_distribution': sentiment_distribution,
                'recent_news_count': len(recent_news)
            }
            
            logger.info(f"📊 {company_name} 감정 분석 완료: {sentiment_trend} ({avg_sentiment:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ {company_name} 감정 분석 실패: {e}")
            return {}

def main():
    """테스트 실행"""
    # API 키 설정 (실제 사용 시 환경변수에서 가져오기)
    CLIENT_ID = "ZFrT7e9RJ9JcosG30dUV"
    CLIENT_SECRET = "YsUytWqqLQ"
    
    # 네이버 뉴스 API 초기화
    naver_api = NaverNewsAPI(CLIENT_ID, CLIENT_SECRET)
    analyzer = NewsAnalyzer(naver_api)
    
    # LG생활건강 뉴스 분석
    print("=" * 60)
    print("📰 LG생활건강 뉴스 감정 분석")
    print("=" * 60)
    
    result = analyzer.analyze_company_sentiment("LG생활건강")
    
    if result:
        print(f"📊 총 뉴스 수: {result['total_news']}건")
        print(f"📈 평균 감정 점수: {result['avg_sentiment']:.3f}")
        print(f"🎯 감정 트렌드: {result['sentiment_trend']}")
        print(f"📅 최근 7일 감정: {result['recent_sentiment']:.3f}")
        print(f"📰 최근 뉴스 수: {result['recent_news_count']}건")
        
        print(f"\n📋 출처별 뉴스 분포:")
        for source, count in result['news_by_source'].items():
            print(f"  - {source}: {count}건")
        
        print(f"\n📊 감정 분포:")
        print(f"  - 긍정: {result['sentiment_distribution']['positive']}건")
        print(f"  - 중립: {result['sentiment_distribution']['neutral']}건")
        print(f"  - 부정: {result['sentiment_distribution']['negative']}건")
    
    print(f"\n" + "=" * 60)
    print("✅ 뉴스 분석 완료")
    print("=" * 60)

if __name__ == "__main__":
    main()
