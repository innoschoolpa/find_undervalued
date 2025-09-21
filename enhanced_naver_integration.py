#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 뉴스 API가 통합된 향상된 분석 시스템
"""

import logging
from datetime import datetime
from typing import Dict, List, Any
from naver_news_api import NaverNewsAPI, NewsAnalyzer
from enhanced_qualitative_integrated_analyzer import EnhancedQualitativeIntegratedAnalyzer
from config_manager import ConfigManager

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedNaverIntegratedAnalyzer:
    """네이버 뉴스 API가 통합된 향상된 분석기"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = ConfigManager()
        
        # 네이버 API 키 설정 (실제 환경에서는 환경변수 사용)
        self.naver_client_id = "ZFrT7e9RJ9JcosG30dUV"
        self.naver_client_secret = "YsUytWqqLQ"
        
        # API 클라이언트 초기화
        self.naver_api = NaverNewsAPI(self.naver_client_id, self.naver_client_secret)
        self.news_analyzer = NewsAnalyzer(self.naver_api)
        
        # 기존 분석기 초기화
        self.qualitative_analyzer = EnhancedQualitativeIntegratedAnalyzer(config_path)
        
        logger.info("🚀 네이버 뉴스 API 통합 분석기 초기화 완료")
    
    def analyze_stock_comprehensive(self, symbol: str, name: str, sector: str, 
                                  financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """종목에 대한 종합 분석 수행"""
        logger.info(f"🔍 {name}({symbol}) 종합 분석 시작")
        
        analysis_result = {
            'symbol': symbol,
            'name': name,
            'sector': sector,
            'analysis_date': datetime.now().isoformat(),
            'financial_analysis': financial_data,
            'news_analysis': {},
            'qualitative_analysis': {},
            'integrated_score': 0.0,
            'investment_recommendation': 'HOLD'
        }
        
        try:
            # 1. 뉴스 감정 분석
            logger.info(f"📰 {name} 뉴스 감정 분석 시작")
            news_analysis = self.news_analyzer.analyze_company_sentiment(name)
            analysis_result['news_analysis'] = news_analysis
            
            # 2. 정성적 리스크 분석
            logger.info(f"⚠️ {name} 정성적 리스크 분석 시작")
            qualitative_analysis = self.qualitative_analyzer.qualitative_risk_analyzer.analyze_comprehensive_risk(
                symbol, sector, financial_data
            )
            analysis_result['qualitative_analysis'] = qualitative_analysis
            
            # 3. 통합 점수 계산
            integrated_score = self._calculate_integrated_score(
                financial_data, news_analysis, qualitative_analysis
            )
            analysis_result['integrated_score'] = integrated_score
            
            # 4. 투자 추천 결정
            recommendation = self._get_investment_recommendation(integrated_score, news_analysis, qualitative_analysis)
            analysis_result['investment_recommendation'] = recommendation
            
            logger.info(f"✅ {name}({symbol}) 종합 분석 완료: {integrated_score:.1f}점 ({recommendation})")
            
        except Exception as e:
            logger.error(f"❌ {name}({symbol}) 분석 실패: {e}")
        
        return analysis_result
    
    def _calculate_integrated_score(self, financial_data: Dict[str, Any], 
                                  news_analysis: Dict[str, Any], 
                                  qualitative_analysis: Dict[str, Any]) -> float:
        """통합 점수 계산"""
        try:
            # 기본 재무 점수 (50점 만점)
            financial_score = self._calculate_financial_score(financial_data)
            
            # 뉴스 감정 점수 (25점 만점)
            news_score = self._calculate_news_score(news_analysis)
            
            # 정성적 리스크 점수 (25점 만점, 리스크가 낮을수록 높은 점수)
            qualitative_score = self._calculate_qualitative_score(qualitative_analysis)
            
            # 가중치 적용
            integrated_score = (
                financial_score * 0.5 +
                news_score * 0.25 +
                qualitative_score * 0.25
            )
            
            return min(100, max(0, integrated_score))
            
        except Exception as e:
            logger.error(f"통합 점수 계산 실패: {e}")
            return 50.0
    
    def _calculate_financial_score(self, financial_data: Dict[str, Any]) -> float:
        """재무 점수 계산"""
        score = 0.0
        
        # PER 평가
        per = financial_data.get('per', 20)
        if per <= 10:
            score += 15
        elif per <= 15:
            score += 12
        elif per <= 20:
            score += 8
        elif per <= 25:
            score += 5
        
        # PBR 평가
        pbr = financial_data.get('pbr', 2)
        if pbr <= 1.0:
            score += 15
        elif pbr <= 1.5:
            score += 12
        elif pbr <= 2.0:
            score += 8
        elif pbr <= 2.5:
            score += 5
        
        # ROE 평가
        roe = financial_data.get('roe', 10)
        if roe >= 15:
            score += 10
        elif roe >= 10:
            score += 8
        elif roe >= 5:
            score += 5
        
        # 성장성 평가
        revenue_growth = financial_data.get('revenue_growth_rate', 0)
        if revenue_growth >= 10:
            score += 10
        elif revenue_growth >= 5:
            score += 7
        elif revenue_growth >= 0:
            score += 3
        
        return min(50, score)
    
    def _calculate_news_score(self, news_analysis: Dict[str, Any]) -> float:
        """뉴스 감정 점수 계산"""
        if not news_analysis:
            return 12.5  # 중립 점수
        
        avg_sentiment = news_analysis.get('avg_sentiment', 0)
        total_news = news_analysis.get('total_news', 0)
        
        # 감정 점수 (0-20점)
        sentiment_score = (avg_sentiment + 1) * 10  # -1~1을 0~20으로 변환
        
        # 뉴스 수 보너스 (0-5점)
        news_bonus = min(5, total_news / 10)  # 10건당 1점, 최대 5점
        
        return min(25, sentiment_score + news_bonus)
    
    def _calculate_qualitative_score(self, qualitative_analysis: Dict[str, Any]) -> float:
        """정성적 리스크 점수 계산 (리스크가 낮을수록 높은 점수)"""
        if not qualitative_analysis:
            return 12.5  # 중립 점수
        
        risk_score = qualitative_analysis.get('comprehensive_risk_score', 50)
        # 리스크 점수를 반전 (낮은 리스크 = 높은 점수)
        qualitative_score = 25 - (risk_score * 0.25)
        
        return max(0, min(25, qualitative_score))
    
    def _get_investment_recommendation(self, integrated_score: float, 
                                    news_analysis: Dict[str, Any], 
                                    qualitative_analysis: Dict[str, Any]) -> str:
        """투자 추천 결정"""
        # 기본 점수 기반 추천
        if integrated_score >= 80:
            base_recommendation = "STRONG_BUY"
        elif integrated_score >= 70:
            base_recommendation = "BUY"
        elif integrated_score >= 60:
            base_recommendation = "HOLD"
        elif integrated_score >= 50:
            base_recommendation = "HOLD"
        else:
            base_recommendation = "SELL"
        
        # 뉴스 감정 조정
        if news_analysis:
            sentiment_trend = news_analysis.get('sentiment_trend', 'neutral')
            if sentiment_trend == 'positive' and base_recommendation in ['HOLD', 'BUY']:
                if base_recommendation == 'HOLD':
                    base_recommendation = 'BUY'
                elif base_recommendation == 'BUY':
                    base_recommendation = 'STRONG_BUY'
            elif sentiment_trend == 'negative' and base_recommendation in ['HOLD', 'BUY']:
                if base_recommendation == 'BUY':
                    base_recommendation = 'HOLD'
                elif base_recommendation == 'STRONG_BUY':
                    base_recommendation = 'BUY'
        
        # 정성적 리스크 조정
        if qualitative_analysis:
            risk_level = qualitative_analysis.get('comprehensive_risk_level', 'MEDIUM')
            if risk_level == 'HIGH' and base_recommendation in ['STRONG_BUY', 'BUY']:
                if base_recommendation == 'STRONG_BUY':
                    base_recommendation = 'BUY'
                elif base_recommendation == 'BUY':
                    base_recommendation = 'HOLD'
            elif risk_level == 'LOW' and base_recommendation in ['HOLD', 'BUY']:
                if base_recommendation == 'HOLD':
                    base_recommendation = 'BUY'
                elif base_recommendation == 'BUY':
                    base_recommendation = 'STRONG_BUY'
        
        return base_recommendation

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🚀 네이버 뉴스 API 통합 분석 시스템")
    print("=" * 80)
    
    # 분석기 초기화
    analyzer = EnhancedNaverIntegratedAnalyzer()
    
    # LG생활건강 분석
    lg_financial_data = {
        'symbol': '003550',
        'current_price': 75300,
        'market_cap': 118750,
        'per': 21.0,
        'pbr': 0.44,
        'roe': 5.79,
        'debt_ratio': 10.18,
        'revenue_growth_rate': 8.3,
        'operating_income_growth_rate': 24.98,
        'net_income_growth_rate': 29.43,
        'net_profit_margin': 22.84,
        'current_ratio': 255.4
    }
    
    print(f"\n📊 LG생활건강 종합 분석")
    analysis_result = analyzer.analyze_stock_comprehensive(
        "003550", "LG생활건강", "화장품/생활용품", lg_financial_data
    )
    
    # 결과 출력
    print(f"\n📈 분석 결과")
    print(f"통합 점수: {analysis_result['integrated_score']:.1f}점")
    print(f"투자 추천: {analysis_result['investment_recommendation']}")
    
    # 뉴스 분석 결과
    news_analysis = analysis_result['news_analysis']
    if news_analysis:
        print(f"\n📰 뉴스 분석")
        print(f"총 뉴스 수: {news_analysis['total_news']}건")
        print(f"평균 감정 점수: {news_analysis['avg_sentiment']:.3f}")
        print(f"감정 트렌드: {news_analysis['sentiment_trend']}")
        print(f"최근 7일 감정: {news_analysis['recent_sentiment']:.3f}")
        
        print(f"\n📊 감정 분포")
        sentiment_dist = news_analysis['sentiment_distribution']
        print(f"긍정: {sentiment_dist['positive']}건")
        print(f"중립: {sentiment_dist['neutral']}건")
        print(f"부정: {sentiment_dist['negative']}건")
    
    # 정성적 리스크 분석 결과
    qualitative_analysis = analysis_result['qualitative_analysis']
    if qualitative_analysis:
        print(f"\n⚠️ 정성적 리스크 분석")
        risk_score = qualitative_analysis.get('comprehensive_risk_score', 0)
        risk_level = qualitative_analysis.get('comprehensive_risk_level', 'MEDIUM')
        print(f"종합 리스크 점수: {risk_score:.1f}점")
        print(f"리스크 레벨: {risk_level}")
    
    print(f"\n" + "=" * 80)
    print("✅ 종합 분석 완료")
    print("=" * 80)

if __name__ == "__main__":
    main()
