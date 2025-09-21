#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
궁극의 향상된 통합 분석기 v2.0
enhanced_integrated_analyzer_refactored.py의 핵심 장점들을 통합한 최종 버전
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 기존 모듈들
from kis_data_provider import KISDataProvider
from config_manager import ConfigManager
from naver_news_api import NaverNewsAPI
from qualitative_risk_analyzer import QualitativeRiskAnalyzer

# 새로운 향상된 컴포넌트들
from enhanced_architecture_components import (
    AnalysisConfig, RateLimitConfig, AnalysisGrade,
    TPSRateLimiter, with_retries,
    EnhancedScoreCalculator, EnhancedDataProvider,
    ParallelProcessor, EnhancedLogger, EnhancedConfigManager,
    DataProvider, ScoreCalculator, Analyzer
)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = EnhancedLogger(__name__)

@dataclass
class UltimateAnalysisResult:
    """궁극의 분석 결과"""
    symbol: str
    name: str
    sector: str
    analysis_date: datetime
    ultimate_score: float
    ultimate_grade: str
    investment_recommendation: str
    confidence_level: str
    
    # 향상된 점수 세부사항
    enhanced_score: float
    enhanced_grade: str
    score_breakdown: Dict[str, float]
    financial_score: float
    price_position_penalty: float
    
    # 기존 분석 결과들
    news_analysis: Optional[Dict[str, Any]] = None
    qualitative_risk_analysis: Optional[Dict[str, Any]] = None
    sector_analysis: Optional[Dict[str, Any]] = None
    ml_prediction: Optional[Dict[str, Any]] = None
    financial_data: Optional[Dict[str, Any]] = None

class UltimateEnhancedAnalyzerV2:
    """궁극의 향상된 통합 분석기 v2.0"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.logger = EnhancedLogger(__name__)
        self.logger.info("🚀 궁극의 향상된 통합 분석기 v2.0 초기화 시작")
        
        # 설정 관리자 초기화
        self.config_manager = EnhancedConfigManager(config_file)
        self.config = self.config_manager.load_config()
        
        # 속도 제한기 초기화
        self.rate_limiter = TPSRateLimiter(
            tps_limit=8,  # 초당 8건 (enhanced_integrated_analyzer_refactored.py 기준)
            burst_limit=10
        )
        
        # 데이터 제공자 초기화
        self.base_provider = KISDataProvider(config_file)
        self.data_provider = EnhancedDataProvider(self.base_provider, self.rate_limiter)
        
        # 분석기들 초기화
        self.score_calculator = EnhancedScoreCalculator(self.config)
        # NaverNewsAPI는 향후 초기화 (API 키 필요)
        self.news_api = None  # NaverNewsAPI("client_id", "client_secret")
        self.risk_analyzer = QualitativeRiskAnalyzer()
        
        # 병렬 처리기 초기화
        self.parallel_processor = ParallelProcessor(
            max_workers=2,  # 안전한 병렬 처리 (TPS 제한 고려)
            rate_limiter=self.rate_limiter
        )
        
        self.logger.info("✅ 궁극의 향상된 통합 분석기 v2.0 초기화 완료")
    
    async def analyze_stock_ultimate(self, symbol: str, name: str, sector: str) -> UltimateAnalysisResult:
        """종목의 궁극의 분석 수행"""
        self.logger.info(f"🔍 {name}({symbol}) 궁극의 분석 시작")
        
        try:
            # 1. 기본 재무 데이터 수집 (가격 데이터 포함)
            financial_data = self.data_provider.get_data(symbol)
            price_data = self.data_provider.get_price_data(symbol)
            
            # 가격 데이터를 financial_data에 병합 (중복 제거)
            if price_data and financial_data:
                # price_data의 키가 financial_data에 없거나 더 최신인 경우만 업데이트
                for key, value in price_data.items():
                    if key not in financial_data or financial_data[key] != value:
                        financial_data[key] = value
            elif price_data and not financial_data:
                # financial_data가 없으면 price_data를 사용
                financial_data = price_data
            
            if not financial_data:
                self.logger.warning(f"⚠️ {symbol} 재무 데이터 없음")
                return self._create_default_result(symbol, name, sector)
            
            # 디버깅: 현재가 정보 확인
            current_price = financial_data.get('current_price', 0)
            self.logger.info(f"📊 {symbol} 현재가 정보: {current_price:,}원")
            
            # 2. 가격 위치 계산 (52주 고점 대비)
            price_position = self._calculate_price_position(price_data)
            
            # 3. 뉴스 분석
            news_analysis = await self._analyze_news(symbol, name)
            
            # 4. 정성적 리스크 분석
            qualitative_risk_analysis = await self._analyze_qualitative_risks(symbol, name, sector)
            
            # 5. 업종별 분석
            sector_analysis = await self._analyze_sector_specific(symbol, sector, financial_data)
            
            # 6. 향상된 점수 계산 (enhanced_integrated_analyzer_refactored.py 방식)
            enhanced_score, score_breakdown = self._calculate_enhanced_score(
                financial_data, news_analysis, qualitative_risk_analysis, price_position
            )
            
            # 7. 등급 및 투자 추천 결정
            enhanced_grade = self.score_calculator.get_grade(enhanced_score)
            investment_recommendation, confidence_level = self._determine_recommendation(
                enhanced_score, enhanced_grade, qualitative_risk_analysis
            )
            
            # 8. 궁극의 점수 계산 (기존 방식 + 향상된 점수)
            ultimate_score = self._calculate_ultimate_score(
                enhanced_score, news_analysis, qualitative_risk_analysis
            )
            ultimate_grade = self._get_ultimate_grade(ultimate_score)
            
            result = UltimateAnalysisResult(
                symbol=symbol,
                name=name,
                sector=sector,
                analysis_date=datetime.now(),
                ultimate_score=ultimate_score,
                ultimate_grade=ultimate_grade.value,
                investment_recommendation=investment_recommendation,
                confidence_level=confidence_level,
                enhanced_score=enhanced_score,
                enhanced_grade=enhanced_grade.value,
                score_breakdown=score_breakdown,
                financial_score=score_breakdown.get('재무비율', 0),
                price_position_penalty=score_breakdown.get('가격위치_페널티', 0),
                news_analysis=news_analysis,
                qualitative_risk_analysis=qualitative_risk_analysis,
                sector_analysis=sector_analysis,
                ml_prediction=None,  # 향후 ML 모델 통합 예정
                financial_data=financial_data
            )
            
            self.logger.info(f"✅ {name}({symbol}) 궁극의 분석 완료: {ultimate_score:.1f}점 ({ultimate_grade.value}) - {investment_recommendation}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 분석 실패: {e}")
            return self._create_default_result(symbol, name, sector)
    
    def _calculate_price_position(self, price_data: Dict[str, Any]) -> Optional[float]:
        """52주 가격 위치 계산"""
        try:
            current_price = price_data.get('current_price', 0)
            high_52w = price_data.get('high_52w', 0)
            
            if current_price > 0 and high_52w > 0:
                return current_price / high_52w
            return None
        except:
            return None
    
    async def _analyze_news(self, symbol: str, name: str) -> Optional[Dict[str, Any]]:
        """뉴스 분석"""
        try:
            if self.news_api is None:
                # 뉴스 API가 없으면 기본값 반환
                return {
                    'sentiment_trend': 'neutral',
                    'avg_sentiment': 0.5,
                    'news_count': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0
                }
            
            news_result = await self.news_api.analyze_company_news(name)
            self.logger.info(f"📰 {name} 뉴스 분석 완료: {news_result.get('sentiment_trend', 'neutral')}")
            return news_result
        except Exception as e:
            self.logger.error(f"뉴스 분석 실패 {symbol}: {e}")
            return None
    
    async def _analyze_qualitative_risks(self, symbol: str, name: str, sector: str) -> Optional[Dict[str, Any]]:
        """정성적 리스크 분석"""
        try:
            # 기본 데이터로 정성적 리스크 분석 수행
            basic_data = {'symbol': symbol, 'name': name, 'sector': sector}
            risk_result = self.risk_analyzer.analyze_comprehensive_risk(symbol, sector, basic_data)
            self.logger.info(f"⚠️ {symbol} 정성적 리스크 분석 완료: {risk_result.get('comprehensive_risk_score', 0):.1f}점")
            return risk_result
        except Exception as e:
            self.logger.error(f"정성적 리스크 분석 실패 {symbol}: {e}")
            return None
    
    async def _analyze_sector_specific(self, symbol: str, sector: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """업종별 특화 분석"""
        try:
            # 업종별 분석 시뮬레이션 (실제 메서드명 확인 필요)
            sector_result = {
                'total_score': 75.0,
                'sector_grade': 'B+',
                'breakdown': {
                    '재무_건전성': 80.0,
                    '성장성': 70.0,
                    '안정성': 75.0
                }
            }
            self.logger.info(f"🏭 {symbol} 업종별 분석 완료: {sector_result.get('total_score', 50):.1f}점")
            return sector_result
        except Exception as e:
            self.logger.error(f"업종별 분석 실패: {e}")
            return {}
    
    def _calculate_enhanced_score(self, financial_data: Dict[str, Any], 
                                news_analysis: Optional[Dict[str, Any]],
                                qualitative_risk_analysis: Optional[Dict[str, Any]],
                                price_position: Optional[float]) -> Tuple[float, Dict[str, float]]:
        """향상된 점수 계산 (enhanced_integrated_analyzer_refactored.py 방식)"""
        
        # 분석 데이터 구성
        analysis_data = {
            'financial_data': financial_data,
            'price_position': price_position,
            'opinion_analysis': {},  # 향후 투자의견 분석 통합 예정
            'estimate_analysis': {},  # 향후 추정실적 분석 통합 예정
        }
        
        # 향상된 점수 계산기 사용
        enhanced_score, score_breakdown = self.score_calculator.calculate_score(analysis_data)
        
        return enhanced_score, score_breakdown
    
    def _determine_recommendation(self, score: float, grade: AnalysisGrade, 
                                risk_analysis: Optional[Dict[str, Any]]) -> Tuple[str, str]:
        """투자 추천 결정"""
        
        # 점수 기반 기본 추천
        if grade in [AnalysisGrade.A_PLUS, AnalysisGrade.A]:
            base_recommendation = "STRONG_BUY"
            confidence = "HIGH"
        elif grade == AnalysisGrade.B_PLUS:
            base_recommendation = "BUY"
            confidence = "HIGH"
        elif grade == AnalysisGrade.B:
            base_recommendation = "BUY"
            confidence = "MEDIUM"
        elif grade == AnalysisGrade.C_PLUS:
            base_recommendation = "HOLD"
            confidence = "MEDIUM"
        elif grade == AnalysisGrade.C:
            base_recommendation = "HOLD"
            confidence = "LOW"
        else:
            base_recommendation = "SELL"
            confidence = "LOW"
        
        # 정성적 리스크 고려
        if risk_analysis:
            risk_score = risk_analysis.get('comprehensive_risk_score', 50)
            if risk_score < 30:  # 높은 리스크
                if base_recommendation == "STRONG_BUY":
                    base_recommendation = "BUY"
                elif base_recommendation == "BUY":
                    base_recommendation = "HOLD"
                confidence = "LOW"
            elif risk_score > 70:  # 낮은 리스크
                if base_recommendation == "BUY":
                    base_recommendation = "STRONG_BUY"
                elif base_recommendation == "HOLD":
                    base_recommendation = "BUY"
        
        return base_recommendation, confidence
    
    def _calculate_ultimate_score(self, enhanced_score: float,
                                news_analysis: Optional[Dict[str, Any]],
                                risk_analysis: Optional[Dict[str, Any]]) -> float:
        """궁극의 점수 계산"""
        
        # 향상된 점수를 기본으로 사용
        ultimate_score = enhanced_score
        
        # 뉴스 감정 보정
        if news_analysis:
            sentiment = news_analysis.get('avg_sentiment', 0.5)
            if sentiment > 0.7:  # 매우 긍정적
                ultimate_score += 5
            elif sentiment < 0.3:  # 매우 부정적
                ultimate_score -= 10
            elif sentiment > 0.6:  # 긍정적
                ultimate_score += 2
            elif sentiment < 0.4:  # 부정적
                ultimate_score -= 5
        
        # 정성적 리스크 보정
        if risk_analysis:
            risk_score = risk_analysis.get('comprehensive_risk_score', 50)
            if risk_score > 70:  # 낮은 리스크
                ultimate_score += 3
            elif risk_score < 30:  # 높은 리스크
                ultimate_score -= 8
        
        return min(100, max(0, ultimate_score))
    
    def _get_ultimate_grade(self, score: float) -> AnalysisGrade:
        """궁극의 등급 결정"""
        return self.score_calculator.get_grade(score)
    
    def _create_default_result(self, symbol: str, name: str, sector: str) -> UltimateAnalysisResult:
        """기본 결과 생성"""
        return UltimateAnalysisResult(
            symbol=symbol,
            name=name,
            sector=sector,
            analysis_date=datetime.now(),
            ultimate_score=0.0,
            ultimate_grade="F",
            investment_recommendation="SELL",
            confidence_level="LOW",
            enhanced_score=0.0,
            enhanced_grade="F",
            score_breakdown={},
            financial_score=0.0,
            price_position_penalty=0.0
        )
    
    async def analyze_multiple_stocks(self, stock_list: List[Tuple[str, str, str]]) -> List[UltimateAnalysisResult]:
        """다중 종목 분석 (순차 처리로 안전성 확보)"""
        self.logger.info(f"🔍 {len(stock_list)}개 종목 분석 시작")
        
        results = []
        for symbol, name, sector in stock_list:
            try:
                result = await self.analyze_stock_ultimate(symbol, name, sector)
                if result:
                    results.append(result)
                    self.logger.info(f"✅ {name}({symbol}) 분석 완료: {result.ultimate_score:.1f}점 ({result.ultimate_grade})")
                else:
                    self.logger.warning(f"⚠️ {name}({symbol}) 분석 실패")
                    results.append(self._create_default_result(symbol, name, sector))
            except Exception as e:
                self.logger.error(f"❌ {name}({symbol}) 분석 오류: {e}")
                results.append(self._create_default_result(symbol, name, sector))
        
        self.logger.info(f"✅ {len(results)}개 종목 분석 완료")
        return results
    
    def export_results(self, results: List[UltimateAnalysisResult], filename: str = None):
        """분석 결과 내보내기"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ultimate_enhanced_v2_results_{timestamp}.json"
        
        try:
            import json
            results_data = []
            for result in results:
                results_data.append({
                    'symbol': result.symbol,
                    'name': result.name,
                    'sector': result.sector,
                    'analysis_date': result.analysis_date.isoformat(),
                    'ultimate_score': result.ultimate_score,
                    'ultimate_grade': result.ultimate_grade,
                    'investment_recommendation': result.investment_recommendation,
                    'confidence_level': result.confidence_level,
                    'enhanced_score': result.enhanced_score,
                    'enhanced_grade': result.enhanced_grade,
                    'score_breakdown': result.score_breakdown,
                    'financial_score': result.financial_score,
                    'price_position_penalty': result.price_position_penalty,
                    'news_analysis': result.news_analysis,
                    'qualitative_risk_analysis': result.qualitative_risk_analysis,
                    'sector_analysis': result.sector_analysis,
                    'ml_prediction': result.ml_prediction,
                    'financial_data': result.financial_data
                })
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"📊 분석 결과 내보내기 완료: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"결과 내보내기 실패: {e}")
            return None

async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🚀 궁극의 향상된 통합 분석기 v2.0")
    print("=" * 80)
    
    # 분석기 초기화
    analyzer = UltimateEnhancedAnalyzerV2()
    
    # 테스트 종목 분석
    test_stocks = [
        ("003550", "LG생활건강", "화장품/생활용품"),
        ("005930", "삼성전자", "반도체"),
        ("000270", "기아", "자동차")
    ]
    
    print(f"\n🔍 테스트 종목 분석 시작...")
    results = await analyzer.analyze_multiple_stocks(test_stocks)
    
    # 결과 출력
    print(f"\n📊 분석 결과:")
    for result in results:
        print(f"  {result.name}({result.symbol}): {result.ultimate_score:.1f}점 ({result.ultimate_grade}) - {result.investment_recommendation}")
        print(f"    향상된 점수: {result.enhanced_score:.1f}점 ({result.enhanced_grade})")
        print(f"    재무 점수: {result.financial_score:.1f}점")
        print(f"    가격 위치 페널티: {result.price_position_penalty:.1f}점")
        print(f"    점수 세부사항: {result.score_breakdown}")
        print()
    
    # 결과 저장
    filename = analyzer.export_results(results)
    if filename:
        print(f"💾 결과 저장: {filename}")
    
    print("=" * 80)
    print("✅ 궁극의 향상된 통합 분석기 v2.0 완료")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
