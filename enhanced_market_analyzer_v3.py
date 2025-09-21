#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
향상된 시장 분석기 v3.0
실시간 데이터, 세밀한 업종 분류, 기업별 맞춤화, 외부 데이터 통합
"""

import asyncio
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import argparse
import sys
import os

# 기존 모듈들 import
from realtime_data_integration import RealTimeMarketAnalyzer, RealTimeDataProvider
from enhanced_sector_classification import EnhancedSectorClassifier, SectorLevel
from company_specific_analyzer import CompanySpecificAnalyzer, CompanyType
from external_data_integration import ExternalDataAnalyzer, ExternalDataProvider

# 기존 분석기들 import
from ultimate_enhanced_analyzer_v2 import UltimateEnhancedAnalyzerV2
from ultimate_market_analyzer_v2 import UltimateMarketAnalyzerV2

logger = logging.getLogger(__name__)

@dataclass
class EnhancedAnalysisResult:
    """향상된 분석 결과"""
    symbol: str
    name: str
    sector_classification: Dict[str, Any]
    company_profile: Dict[str, Any]
    realtime_sentiment: Dict[str, Any]
    external_data: Dict[str, Any]
    financial_analysis: Dict[str, Any]
    comprehensive_score: float
    investment_recommendation: str
    confidence_level: str
    risk_assessment: Dict[str, Any]
    growth_outlook: Dict[str, Any]
    timestamp: datetime

class EnhancedMarketAnalyzerV3:
    """향상된 시장 분석기 v3.0"""
    
    def __init__(self):
        # 각종 분석기 초기화
        self.realtime_analyzer = RealTimeMarketAnalyzer()
        self.sector_classifier = EnhancedSectorClassifier()
        self.company_analyzer = CompanySpecificAnalyzer()
        self.external_analyzer = ExternalDataAnalyzer()
        self.ultimate_analyzer = UltimateEnhancedAnalyzerV2()
        self.market_analyzer = UltimateMarketAnalyzerV2()
        
        # 성능 최적화를 위한 캐시
        self.analysis_cache = {}
        self.cache_duration = timedelta(minutes=30)
        
        # 병렬 처리 설정
        self.max_concurrent_analyses = 10
        
        logger.info("🚀 향상된 시장 분석기 v3.0 초기화 완료")
    
    async def analyze_market_comprehensive(self, symbols: List[str], 
                                         include_realtime: bool = True,
                                         include_external: bool = True,
                                         top_n: int = 50) -> List[EnhancedAnalysisResult]:
        """종합 시장 분석"""
        
        logger.info(f"🔍 종합 시장 분석 시작: {len(symbols)}개 종목")
        start_time = datetime.now()
        
        # 1. 기본 재무 분석 (기존 시스템 활용)
        logger.info("📊 1단계: 기본 재무 분석")
        basic_results = await self._perform_basic_analysis(symbols)
        
        # 2. 실시간 데이터 분석
        realtime_results = {}
        if include_realtime:
            logger.info("🔄 2단계: 실시간 데이터 분석")
            realtime_results = await self._perform_realtime_analysis(symbols)
        
        # 3. 업종별 세분화 분석
        logger.info("🏭 3단계: 업종별 세분화 분석")
        sector_results = await self._perform_sector_analysis(symbols)
        
        # 4. 기업별 맞춤화 분석
        logger.info("🏢 4단계: 기업별 맞춤화 분석")
        company_results = await self._perform_company_analysis(symbols)
        
        # 5. 외부 데이터 분석
        external_results = {}
        if include_external:
            logger.info("🌐 5단계: 외부 데이터 분석")
            external_results = await self._perform_external_analysis(symbols)
        
        # 6. 종합 분석 및 점수 계산
        logger.info("🎯 6단계: 종합 분석 및 점수 계산")
        enhanced_results = await self._perform_comprehensive_integration(
            basic_results, realtime_results, sector_results, 
            company_results, external_results
        )
        
        # 7. 결과 정렬 및 상위 N개 선택
        enhanced_results.sort(key=lambda x: x.comprehensive_score, reverse=True)
        top_results = enhanced_results[:top_n]
        
        analysis_time = datetime.now() - start_time
        logger.info(f"✅ 종합 분석 완료: {len(top_results)}개 종목, 소요시간: {analysis_time}")
        
        return top_results
    
    async def _perform_basic_analysis(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """기본 재무 분석 (기존 시스템 활용)"""
        try:
            # 기존 UltimateEnhancedAnalyzerV2 활용
            results = []
            for symbol in symbols:
                try:
                    # 캐시 확인
                    cache_key = f"basic_{symbol}"
                    if self._is_cache_valid(cache_key):
                        cached_result = self.analysis_cache[cache_key]
                        results.append(cached_result)
                        continue
                    
                    # 기본 분석 수행
                    company_name = self._get_company_name(symbol)
                    sector = self._get_sector_by_symbol(symbol)
                    analysis_result = await self.ultimate_analyzer.analyze_stock_ultimate(symbol, company_name, sector)
                    
                    if analysis_result:
                        basic_data = {
                            'symbol': symbol,
                            'name': getattr(analysis_result, 'name', f'Company_{symbol}'),
                            'financial_data': getattr(analysis_result, 'financial_data', {}),
                            'enhanced_score': getattr(analysis_result, 'enhanced_score', 0),
                            'ultimate_score': getattr(analysis_result, 'ultimate_score', 0),
                            'investment_recommendation': getattr(analysis_result, 'investment_recommendation', 'HOLD'),
                            'confidence_level': getattr(analysis_result, 'confidence_level', 'MEDIUM')
                        }
                        
                        # 캐시 저장
                        self._cache_data(cache_key, basic_data)
                        results.append(basic_data)
                
                except Exception as e:
                    logger.error(f"기본 분석 실패 {symbol}: {e}")
                    continue
            
            return results
        
        except Exception as e:
            logger.error(f"기본 분석 수행 실패: {e}")
            return []
    
    async def _perform_realtime_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """실시간 데이터 분석"""
        try:
            # 실시간 시장 감정 분석
            market_sentiment = await self.realtime_analyzer.analyze_market_sentiment(symbols)
            
            # 실시간 데이터를 종목별로 매핑
            realtime_results = {}
            for symbol in symbols:
                realtime_results[symbol] = {
                    'market_sentiment': market_sentiment.get('comprehensive_sentiment', 0),
                    'sentiment_level': market_sentiment.get('sentiment_level', 'neutral'),
                    'news_sentiment': self._extract_news_sentiment_for_symbol(symbol, market_sentiment),
                    'market_indicators': market_sentiment.get('market_indices', []),
                    'economic_indicators': market_sentiment.get('economic_indicators', []),
                    'confidence': market_sentiment.get('confidence', 0)
                }
            
            return realtime_results
        
        except Exception as e:
            logger.error(f"실시간 분석 수행 실패: {e}")
            return {}
    
    async def _perform_sector_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """업종별 세분화 분석"""
        try:
            sector_results = {}
            
            for symbol in symbols:
                try:
                    # 캐시 확인
                    cache_key = f"sector_{symbol}"
                    if self._is_cache_valid(cache_key):
                        sector_results[symbol] = self.analysis_cache[cache_key]
                        continue
                    
                    # 회사명 조회 (실제로는 데이터베이스에서 조회)
                    company_name = self._get_company_name(symbol)
                    
                    # 업종 분류
                    classifications = self.sector_classifier.classify_company(company_name)
                    
                    # 업종별 투자 기회 분석
                    sector_opportunities = {}
                    for classification in classifications[:3]:  # 상위 3개만
                        opportunity = self.sector_classifier.analyze_sector_opportunities(classification.code)
                        if opportunity:
                            sector_opportunities[classification.code] = opportunity
                    
                    # 업종 계층 구조
                    hierarchy = {}
                    if classifications:
                        hierarchy = self.sector_classifier.get_sector_hierarchy(classifications[0].code)
                    
                    sector_data = {
                        'classifications': [asdict(c) for c in classifications],
                        'sector_opportunities': sector_opportunities,
                        'hierarchy': hierarchy,
                        'primary_sector': classifications[0].name if classifications else 'Unknown'
                    }
                    
                    # 캐시 저장
                    self._cache_data(cache_key, sector_data)
                    sector_results[symbol] = sector_data
                
                except Exception as e:
                    logger.error(f"업종 분석 실패 {symbol}: {e}")
                    sector_results[symbol] = {}
            
            return sector_results
        
        except Exception as e:
            logger.error(f"업종 분석 수행 실패: {e}")
            return {}
    
    async def _perform_company_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """기업별 맞춤화 분석"""
        try:
            company_results = {}
            
            for symbol in symbols:
                try:
                    # 캐시 확인
                    cache_key = f"company_{symbol}"
                    if self._is_cache_valid(cache_key):
                        company_results[symbol] = self.analysis_cache[cache_key]
                        continue
                    
                    # 기본 재무 데이터 (기본 분석에서 가져오기)
                    basic_data = None
                    for result in await self._perform_basic_analysis([symbol]):
                        if result['symbol'] == symbol:
                            basic_data = result.get('financial_data', {})
                            break
                    
                    if not basic_data:
                        basic_data = {}
                    
                    # 기업별 맞춤 분석
                    company_analysis = self.company_analyzer.analyze_company_specific(symbol, basic_data)
                    
                    # 캐시 저장
                    self._cache_data(cache_key, company_analysis)
                    company_results[symbol] = company_analysis
                
                except Exception as e:
                    logger.error(f"기업별 분석 실패 {symbol}: {e}")
                    company_results[symbol] = {}
            
            return company_results
        
        except Exception as e:
            logger.error(f"기업별 분석 수행 실패: {e}")
            return {}
    
    async def _perform_external_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """외부 데이터 분석"""
        try:
            # 종합 외부 데이터 분석
            external_analysis = await self.external_analyzer.comprehensive_external_analysis(symbols)
            
            # 종목별로 데이터 분리
            external_results = {}
            for symbol in symbols:
                external_results[symbol] = {
                    'esg_data': self._extract_esg_data_for_symbol(symbol, external_analysis),
                    'credit_data': self._extract_credit_data_for_symbol(symbol, external_analysis),
                    'consensus_data': self._extract_consensus_data_for_symbol(symbol, external_analysis),
                    'overall_external_score': external_analysis.get('comprehensive_score', 50)
                }
            
            return external_results
        
        except Exception as e:
            logger.error(f"외부 데이터 분석 수행 실패: {e}")
            return {}
    
    async def _perform_comprehensive_integration(self, basic_results: List[Dict[str, Any]],
                                               realtime_results: Dict[str, Any],
                                               sector_results: Dict[str, Any],
                                               company_results: Dict[str, Any],
                                               external_results: Dict[str, Any]) -> List[EnhancedAnalysisResult]:
        """종합 통합 분석"""
        
        enhanced_results = []
        
        for basic_result in basic_results:
            symbol = basic_result['symbol']
            
            try:
                # 각 분석 결과 수집
                realtime_data = realtime_results.get(symbol, {})
                sector_data = sector_results.get(symbol, {})
                company_data = company_results.get(symbol, {})
                external_data = external_results.get(symbol, {})
                
                # 종합 점수 계산
                comprehensive_score = self._calculate_enhanced_comprehensive_score(
                    basic_result, realtime_data, sector_data, company_data, external_data
                )
                
                # 투자 추천 결정
                investment_recommendation = self._determine_investment_recommendation(comprehensive_score)
                
                # 신뢰도 결정
                confidence_level = self._determine_confidence_level(
                    basic_result, realtime_data, sector_data, company_data, external_data
                )
                
                # 리스크 평가
                risk_assessment = self._assess_comprehensive_risk(
                    basic_result, realtime_data, sector_data, company_data, external_data
                )
                
                # 성장 전망
                growth_outlook = self._assess_growth_outlook(
                    basic_result, realtime_data, sector_data, company_data, external_data
                )
                
                # 향상된 분석 결과 생성
                enhanced_result = EnhancedAnalysisResult(
                    symbol=symbol,
                    name=basic_result.get('name', f'Company_{symbol}'),
                    sector_classification=sector_data,
                    company_profile=company_data,
                    realtime_sentiment=realtime_data,
                    external_data=external_data,
                    financial_analysis=basic_result,
                    comprehensive_score=comprehensive_score,
                    investment_recommendation=investment_recommendation,
                    confidence_level=confidence_level,
                    risk_assessment=risk_assessment,
                    growth_outlook=growth_outlook,
                    timestamp=datetime.now()
                )
                
                enhanced_results.append(enhanced_result)
                
            except Exception as e:
                logger.error(f"종합 통합 분석 실패 {symbol}: {e}")
                continue
        
        return enhanced_results
    
    def _calculate_enhanced_comprehensive_score(self, basic_result: Dict[str, Any],
                                              realtime_data: Dict[str, Any],
                                              sector_data: Dict[str, Any],
                                              company_data: Dict[str, Any],
                                              external_data: Dict[str, Any]) -> float:
        """향상된 종합 점수 계산"""
        
        # 기본 점수 (40%)
        basic_score = basic_result.get('enhanced_score', 0)
        
        # 실시간 감정 점수 (15%)
        realtime_score = self._convert_sentiment_to_score(
            realtime_data.get('sentiment_level', 'neutral')
        )
        
        # 업종 기회 점수 (15%)
        sector_score = 50  # 기본값
        if sector_data and 'sector_opportunities' in sector_data:
            for opportunity in sector_data['sector_opportunities'].values():
                if 'total_score' in opportunity:
                    sector_score = max(sector_score, opportunity['total_score'])
                    break
        
        # 기업별 맞춤 점수 (15%)
        company_score = company_data.get('comprehensive_score', 50)
        
        # 외부 데이터 점수 (15%)
        external_score = external_data.get('overall_external_score', 50)
        
        # 가중 평균 계산
        weights = [0.40, 0.15, 0.15, 0.15, 0.15]
        scores = [basic_score, realtime_score, sector_score, company_score, external_score]
        
        comprehensive_score = sum(score * weight for score, weight in zip(scores, weights))
        
        return max(0, min(100, comprehensive_score))
    
    def _convert_sentiment_to_score(self, sentiment_level: str) -> float:
        """감정 레벨을 점수로 변환"""
        sentiment_scores = {
            'very_positive': 90,
            'positive': 75,
            'neutral': 50,
            'negative': 25,
            'very_negative': 10
        }
        return sentiment_scores.get(sentiment_level, 50)
    
    def _determine_investment_recommendation(self, score: float) -> str:
        """투자 추천 결정"""
        if score >= 80:
            return 'STRONG_BUY'
        elif score >= 70:
            return 'BUY'
        elif score >= 60:
            return 'HOLD'
        elif score >= 50:
            return 'SELL'
        else:
            return 'STRONG_SELL'
    
    def _determine_confidence_level(self, basic_result: Dict[str, Any],
                                  realtime_data: Dict[str, Any],
                                  sector_data: Dict[str, Any],
                                  company_data: Dict[str, Any],
                                  external_data: Dict[str, Any]) -> str:
        """신뢰도 레벨 결정"""
        
        # 각 분석의 신뢰도 점수 계산
        confidence_scores = []
        
        # 기본 분석 신뢰도
        basic_confidence = basic_result.get('confidence_level', 'MEDIUM')
        basic_score = {'HIGH': 90, 'MEDIUM': 70, 'LOW': 50}.get(basic_confidence, 50)
        confidence_scores.append(basic_score)
        
        # 실시간 데이터 신뢰도
        realtime_confidence = realtime_data.get('confidence', 0) * 100
        confidence_scores.append(realtime_confidence)
        
        # 업종 분석 신뢰도 (데이터 존재 여부)
        sector_confidence = 80 if sector_data and sector_data.get('classifications') else 30
        confidence_scores.append(sector_confidence)
        
        # 기업별 분석 신뢰도
        company_confidence = 85 if company_data and company_data.get('comprehensive_score') else 40
        confidence_scores.append(company_confidence)
        
        # 외부 데이터 신뢰도
        external_confidence = 75 if external_data and external_data.get('overall_external_score') else 35
        confidence_scores.append(external_confidence)
        
        # 평균 신뢰도 계산
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        if avg_confidence >= 80:
            return 'HIGH'
        elif avg_confidence >= 60:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _assess_comprehensive_risk(self, basic_result: Dict[str, Any],
                                 realtime_data: Dict[str, Any],
                                 sector_data: Dict[str, Any],
                                 company_data: Dict[str, Any],
                                 external_data: Dict[str, Any]) -> Dict[str, Any]:
        """종합 리스크 평가"""
        
        risk_factors = []
        risk_score = 50  # 기본값
        
        # 시장 리스크
        market_sentiment = realtime_data.get('sentiment_level', 'neutral')
        if market_sentiment in ['negative', 'very_negative']:
            risk_factors.append('시장 감정 부정적')
            risk_score += 20
        
        # 업종 리스크
        if sector_data and 'sector_opportunities' in sector_data:
            for opportunity in sector_data['sector_opportunities'].values():
                if 'risk_factors' in opportunity:
                    risk_factors.extend(opportunity['risk_factors'][:2])  # 상위 2개만
                    break
        
        # 기업별 리스크
        if company_data and 'risk_analysis' in company_data:
            risk_analysis = company_data['risk_analysis']
            if 'risk_level' in risk_analysis:
                risk_level = risk_analysis['risk_level']
                if risk_level in ['high', 'very_high']:
                    risk_score += 15
        
        # 신용 리스크
        if external_data and 'credit_data' in external_data:
            credit_data = external_data['credit_data']
            if credit_data and 'rating' in credit_data:
                rating = credit_data['rating']
                if rating in ['BB', 'B', 'CCC', 'CC', 'C', 'D']:
                    risk_factors.append('신용등급 하위')
                    risk_score += 10
        
        risk_score = min(100, max(0, risk_score))
        
        # 리스크 레벨 결정
        if risk_score >= 80:
            risk_level = 'very_high'
        elif risk_score >= 60:
            risk_level = 'high'
        elif risk_score >= 40:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors[:5],  # 상위 5개만
            'risk_summary': f'{len(risk_factors)}개 주요 리스크 요인 식별'
        }
    
    def _assess_growth_outlook(self, basic_result: Dict[str, Any],
                             realtime_data: Dict[str, Any],
                             sector_data: Dict[str, Any],
                             company_data: Dict[str, Any],
                             external_data: Dict[str, Any]) -> Dict[str, Any]:
        """성장 전망 평가"""
        
        growth_drivers = []
        growth_score = 50  # 기본값
        
        # 업종 성장 동력
        if sector_data and 'sector_opportunities' in sector_data:
            for opportunity in sector_data['sector_opportunities'].values():
                if 'growth_drivers' in opportunity:
                    growth_drivers.extend(opportunity['growth_drivers'][:3])  # 상위 3개만
                    growth_score = max(growth_score, opportunity.get('total_score', 50))
                    break
        
        # 기업별 성장 동력
        if company_data and 'growth_analysis' in company_data:
            growth_analysis = company_data['growth_analysis']
            if 'growth_drivers' in growth_analysis:
                for driver_data in growth_analysis['growth_drivers'].values():
                    if 'description' in driver_data:
                        growth_drivers.append(driver_data['description'])
        
        # 시장 감정 기반 성장 전망
        market_sentiment = realtime_data.get('sentiment_level', 'neutral')
        if market_sentiment in ['positive', 'very_positive']:
            growth_score += 10
            growth_drivers.append('긍정적 시장 감정')
        
        growth_score = min(100, max(0, growth_score))
        
        # 성장 레벨 결정
        if growth_score >= 80:
            growth_level = 'very_high'
        elif growth_score >= 70:
            growth_level = 'high'
        elif growth_score >= 60:
            growth_level = 'medium'
        elif growth_score >= 50:
            growth_level = 'low'
        else:
            growth_level = 'very_low'
        
        return {
            'growth_score': growth_score,
            'growth_level': growth_level,
            'growth_drivers': growth_drivers[:5],  # 상위 5개만
            'growth_summary': f'{len(growth_drivers)}개 성장 동력 식별'
        }
    
    # 헬퍼 메서드들
    def _extract_news_sentiment_for_symbol(self, symbol: str, market_sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """특정 종목의 뉴스 감정 추출"""
        # 실제로는 더 정교한 매핑 필요
        return {
            'sentiment_score': market_sentiment.get('news_sentiment', 0),
            'sentiment_label': 'neutral',
            'confidence': market_sentiment.get('confidence', 0)
        }
    
    def _extract_esg_data_for_symbol(self, symbol: str, external_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """특정 종목의 ESG 데이터 추출"""
        if 'esg_analysis' in external_analysis and 'esg_scores' in external_analysis['esg_analysis']:
            for esg_score in external_analysis['esg_analysis']['esg_scores']:
                if esg_score.get('symbol') == symbol:
                    return esg_score
        return {}
    
    def _extract_credit_data_for_symbol(self, symbol: str, external_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """특정 종목의 신용 데이터 추출"""
        if 'credit_analysis' in external_analysis and 'credit_ratings' in external_analysis['credit_analysis']:
            for credit_rating in external_analysis['credit_analysis']['credit_ratings']:
                if credit_rating.get('symbol') == symbol:
                    return credit_rating
        return {}
    
    def _extract_consensus_data_for_symbol(self, symbol: str, external_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """특정 종목의 애널리스트 합의 데이터 추출"""
        if 'consensus_analysis' in external_analysis and 'consensus_data' in external_analysis['consensus_analysis']:
            for consensus in external_analysis['consensus_analysis']['consensus_data']:
                if consensus.get('symbol') == symbol:
                    return consensus
        return {}
    
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
    
    def _get_sector_by_symbol(self, symbol: str) -> str:
        """심볼로부터 업종 조회"""
        sector_map = {
            '005930': '반도체',
            '000660': '반도체',
            '035420': '소프트웨어',
            '035720': '소프트웨어',
            '005380': '자동차',
            '000270': '자동차',
            '068270': '바이오',
            '207940': '바이오'
        }
        return sector_map.get(symbol, '기타')
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 검사"""
        if cache_key not in self.analysis_cache:
            return False
        
        cache_data = self.analysis_cache[cache_key]
        if not isinstance(cache_data, dict) or 'timestamp' not in cache_data:
            return False
        
        cache_time = cache_data['timestamp']
        if isinstance(cache_time, str):
            cache_time = datetime.fromisoformat(cache_time.replace('Z', '+00:00'))
        
        return datetime.now() - cache_time < self.cache_duration
    
    def _cache_data(self, cache_key: str, data: Any):
        """데이터 캐시 저장"""
        if isinstance(data, dict):
            data['timestamp'] = datetime.now().isoformat()
        self.analysis_cache[cache_key] = data
    
    async def export_analysis_results(self, results: List[EnhancedAnalysisResult], 
                                    filename: str = None) -> str:
        """분석 결과 내보내기"""
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'enhanced_market_analysis_v3_{timestamp}.json'
        
        # 결과를 JSON 직렬화 가능한 형태로 변환
        export_data = {
            'metadata': {
                'analysis_version': '3.0',
                'analysis_date': datetime.now().isoformat(),
                'total_stocks': len(results),
                'features': [
                    'realtime_data',
                    'enhanced_sector_classification',
                    'company_specific_analysis',
                    'external_data_integration'
                ]
            },
            'results': []
        }
        
        for result in results:
            result_dict = asdict(result)
            # datetime 객체를 ISO 형식으로 변환
            if 'timestamp' in result_dict:
                result_dict['timestamp'] = result_dict['timestamp'].isoformat()
            
            export_data['results'].append(result_dict)
        
        # JSON 파일로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"💾 향상된 분석 결과 내보내기 완료: {filename}")
        return filename
    
    def generate_analysis_report(self, results: List[EnhancedAnalysisResult]) -> str:
        """분석 보고서 생성"""
        
        report = []
        report.append("🚀 향상된 시장 분석기 v3.0 - 종합 분석 보고서")
        report.append("=" * 80)
        report.append(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"분석 종목 수: {len(results)}개")
        report.append("")
        
        # 상위 10개 종목 요약
        report.append("📊 상위 10개 종목 요약")
        report.append("-" * 80)
        for i, result in enumerate(results[:10], 1):
            report.append(f"{i:2d}. {result.name} ({result.symbol})")
            report.append(f"    종합점수: {result.comprehensive_score:.1f}점")
            report.append(f"    투자추천: {result.investment_recommendation}")
            report.append(f"    신뢰도: {result.confidence_level}")
            
            # 업종 정보
            if result.sector_classification and 'primary_sector' in result.sector_classification:
                report.append(f"    주요업종: {result.sector_classification['primary_sector']}")
            
            # 리스크 정보
            if result.risk_assessment:
                report.append(f"    리스크레벨: {result.risk_assessment.get('risk_level', 'unknown')}")
            
            # 성장 전망
            if result.growth_outlook:
                report.append(f"    성장전망: {result.growth_outlook.get('growth_level', 'unknown')}")
            
            report.append("")
        
        # 투자 추천별 분포
        report.append("📈 투자 추천별 분포")
        report.append("-" * 40)
        recommendation_counts = {}
        for result in results:
            rec = result.investment_recommendation
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
        
        for rec, count in sorted(recommendation_counts.items()):
            percentage = (count / len(results)) * 100
            report.append(f"{rec:12s}: {count:3d}개 ({percentage:5.1f}%)")
        
        report.append("")
        
        # 신뢰도별 분포
        report.append("🎯 신뢰도별 분포")
        report.append("-" * 40)
        confidence_counts = {}
        for result in results:
            conf = result.confidence_level
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
        
        for conf, count in sorted(confidence_counts.items()):
            percentage = (count / len(results)) * 100
            report.append(f"{conf:12s}: {count:3d}개 ({percentage:5.1f}%)")
        
        report.append("")
        
        # 업종별 분포
        report.append("🏭 업종별 분포")
        report.append("-" * 40)
        sector_counts = {}
        for result in results:
            if result.sector_classification and 'primary_sector' in result.sector_classification:
                sector = result.sector_classification['primary_sector']
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(results)) * 100
            report.append(f"{sector:20s}: {count:3d}개 ({percentage:5.1f}%)")
        
        report.append("")
        report.append("✅ 향상된 시장 분석기 v3.0 분석 완료")
        
        return "\n".join(report)

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='향상된 시장 분석기 v3.0')
    parser.add_argument('--symbols', nargs='+', default=['005930', '000660', '035420', '005380'],
                       help='분석할 종목 심볼들')
    parser.add_argument('--top-n', type=int, default=10,
                       help='상위 N개 종목 선택')
    parser.add_argument('--no-realtime', action='store_true',
                       help='실시간 데이터 분석 제외')
    parser.add_argument('--no-external', action='store_true',
                       help='외부 데이터 분석 제외')
    parser.add_argument('--export', action='store_true',
                       help='결과를 JSON 파일로 내보내기')
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 향상된 분석기 초기화
    analyzer = EnhancedMarketAnalyzerV3()
    
    print("🚀 향상된 시장 분석기 v3.0 시작")
    print(f"분석 종목: {', '.join(args.symbols)}")
    print(f"상위 {args.top_n}개 종목 선택")
    print("=" * 80)
    
    try:
        # 종합 분석 수행
        results = await analyzer.analyze_market_comprehensive(
            symbols=args.symbols,
            include_realtime=not args.no_realtime,
            include_external=not args.no_external,
            top_n=args.top_n
        )
        
        if not results:
            print("❌ 분석 결과가 없습니다.")
            return
        
        # 분석 보고서 생성 및 출력
        report = analyzer.generate_analysis_report(results)
        print(report)
        
        # 결과 내보내기
        if args.export:
            filename = await analyzer.export_analysis_results(results)
            print(f"\n💾 분석 결과가 {filename} 파일로 저장되었습니다.")
        
        # 상위 종목 상세 정보
        print("\n🔍 상위 5개 종목 상세 분석:")
        print("=" * 80)
        
        for i, result in enumerate(results[:5], 1):
            print(f"\n{i}. {result.name} ({result.symbol})")
            print(f"   종합점수: {result.comprehensive_score:.1f}점")
            print(f"   투자추천: {result.investment_recommendation}")
            print(f"   신뢰도: {result.confidence_level}")
            
            # 업종 정보
            if result.sector_classification and 'primary_sector' in result.sector_classification:
                print(f"   주요업종: {result.sector_classification['primary_sector']}")
            
            # 리스크 평가
            if result.risk_assessment:
                risk_level = result.risk_assessment.get('risk_level', 'unknown')
                risk_factors = result.risk_assessment.get('risk_factors', [])
                print(f"   리스크레벨: {risk_level}")
                if risk_factors:
                    print(f"   주요리스크: {', '.join(risk_factors[:2])}")
            
            # 성장 전망
            if result.growth_outlook:
                growth_level = result.growth_outlook.get('growth_level', 'unknown')
                growth_drivers = result.growth_outlook.get('growth_drivers', [])
                print(f"   성장전망: {growth_level}")
                if growth_drivers:
                    print(f"   성장동력: {', '.join(growth_drivers[:2])}")
        
        print("\n✅ 향상된 시장 분석기 v3.0 분석 완료!")
        
    except Exception as e:
        logger.error(f"분석 수행 중 오류 발생: {e}")
        print(f"❌ 분석 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())
