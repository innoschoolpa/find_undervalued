#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
정량적 지표와 정성적 지표를 통합한 종합점수 시스템
"""

import asyncio
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# 기존 시스템 import
from ultimate_enhanced_analyzer_v2 import UltimateEnhancedAnalyzerV2
from enhanced_architecture_components import EnhancedLogger


class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SectorCycle(Enum):
    GROWTH = "GROWTH"
    MATURE = "MATURE"
    DECLINE = "DECLINE"
    RECOVERY = "RECOVERY"


@dataclass
class QuantitativeMetrics:
    """정량적 지표"""
    per: float = 0.0
    pbr: float = 0.0
    roe: float = 0.0
    roa: float = 0.0
    debt_ratio: float = 0.0
    current_ratio: float = 0.0
    net_profit_margin: float = 0.0
    revenue_growth: float = 0.0
    profit_growth: float = 0.0
    market_cap: float = 0.0
    dividend_yield: float = 0.0


@dataclass
class QualitativeMetrics:
    """정성적 지표"""
    sector_outlook: float = 0.0  # 업종 전망 점수
    market_cycle_position: float = 0.0  # 시장 사이클 위치
    competitive_advantage: float = 0.0  # 경쟁우위
    management_quality: float = 0.0  # 경영진 품질
    esg_score: float = 0.0  # ESG 점수
    news_sentiment: float = 0.0  # 뉴스 감정
    analyst_consensus: float = 0.0  # 애널리스트 합의
    risk_level: RiskLevel = RiskLevel.MEDIUM


@dataclass
class ComprehensiveScore:
    """종합점수"""
    quantitative_score: float = 0.0
    qualitative_score: float = 0.0
    comprehensive_score: float = 0.0
    grade: str = "F"
    recommendation: str = "SELL"
    confidence: float = 0.0


class ComprehensiveScoringSystem:
    """정량적 + 정성적 지표 통합 점수 시스템"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.logger = EnhancedLogger("ComprehensiveScoringSystem")
        self.analyzer = UltimateEnhancedAnalyzerV2(config_file)
        
        # 가중치 설정
        self.quantitative_weights = {
            'valuation': 0.25,      # 밸류에이션 (PER, PBR)
            'profitability': 0.25,  # 수익성 (ROE, ROA, 순이익률)
            'stability': 0.20,      # 안정성 (부채비율, 유동비율)
            'growth': 0.15,         # 성장성 (매출성장률, 이익성장률)
            'dividend': 0.15        # 배당 (배당수익률)
        }
        
        self.qualitative_weights = {
            'sector_outlook': 0.20,      # 업종 전망
            'market_cycle': 0.20,        # 시장 사이클
            'competitive_advantage': 0.15, # 경쟁우위
            'management_quality': 0.15,   # 경영진 품질
            'esg_score': 0.10,           # ESG
            'news_sentiment': 0.10,      # 뉴스 감정
            'analyst_consensus': 0.10    # 애널리스트 합의
        }
        
        # 종합 가중치 (정량 70%, 정성 30%)
        self.comprehensive_weights = {
            'quantitative': 0.70,
            'qualitative': 0.30
        }
        
        self.logger.info("✅ 종합 점수 시스템 초기화 완료")
    
    def calculate_quantitative_score(self, metrics: QuantitativeMetrics) -> float:
        """정량적 점수 계산"""
        scores = {}
        
        # 1. 밸류에이션 점수 (PER, PBR)
        per_score = self._score_per(metrics.per)
        pbr_score = self._score_pbr(metrics.pbr)
        scores['valuation'] = (per_score + pbr_score) / 2
        
        # 2. 수익성 점수 (ROE, ROA, 순이익률)
        roe_score = self._score_roe(metrics.roe)
        roa_score = self._score_roa(metrics.roa)
        margin_score = self._score_profit_margin(metrics.net_profit_margin)
        scores['profitability'] = (roe_score + roa_score + margin_score) / 3
        
        # 3. 안정성 점수 (부채비율, 유동비율)
        debt_score = self._score_debt_ratio(metrics.debt_ratio)
        current_score = self._score_current_ratio(metrics.current_ratio)
        scores['stability'] = (debt_score + current_score) / 2
        
        # 4. 성장성 점수 (매출성장률, 이익성장률)
        revenue_score = self._score_growth_rate(metrics.revenue_growth)
        profit_score = self._score_growth_rate(metrics.profit_growth)
        scores['growth'] = (revenue_score + profit_score) / 2
        
        # 5. 배당 점수
        scores['dividend'] = self._score_dividend_yield(metrics.dividend_yield)
        
        # 가중 평균 계산
        total_score = 0.0
        total_weight = 0.0
        
        for category, score in scores.items():
            weight = self.quantitative_weights.get(category, 0.0)
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def calculate_qualitative_score(self, metrics: QualitativeMetrics) -> float:
        """정성적 점수 계산"""
        scores = {
            'sector_outlook': metrics.sector_outlook,
            'market_cycle': metrics.market_cycle_position,
            'competitive_advantage': metrics.competitive_advantage,
            'management_quality': metrics.management_quality,
            'esg_score': metrics.esg_score,
            'news_sentiment': metrics.news_sentiment,
            'analyst_consensus': metrics.analyst_consensus
        }
        
        # 가중 평균 계산
        total_score = 0.0
        total_weight = 0.0
        
        for category, score in scores.items():
            weight = self.qualitative_weights.get(category, 0.0)
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def calculate_comprehensive_score(self, quant_metrics: QuantitativeMetrics, 
                                    qual_metrics: QualitativeMetrics) -> ComprehensiveScore:
        """종합점수 계산"""
        # 정량적 점수
        quant_score = self.calculate_quantitative_score(quant_metrics)
        
        # 정성적 점수
        qual_score = self.calculate_qualitative_score(qual_metrics)
        
        # 종합점수 (정량 70%, 정성 30%)
        comprehensive_score = (quant_score * self.comprehensive_weights['quantitative'] + 
                             qual_score * self.comprehensive_weights['qualitative'])
        
        # 등급 및 추천 결정
        grade, recommendation, confidence = self._determine_grade_and_recommendation(
            comprehensive_score, quant_score, qual_score
        )
        
        return ComprehensiveScore(
            quantitative_score=quant_score,
            qualitative_score=qual_score,
            comprehensive_score=comprehensive_score,
            grade=grade,
            recommendation=recommendation,
            confidence=confidence
        )
    
    def _score_per(self, per: float) -> float:
        """PER 점수 (낮을수록 좋음)"""
        if per <= 0:
            return 0.0
        elif per <= 10:
            return 100.0
        elif per <= 15:
            return 80.0
        elif per <= 20:
            return 60.0
        elif per <= 25:
            return 40.0
        elif per <= 30:
            return 20.0
        else:
            return 0.0
    
    def _score_pbr(self, pbr: float) -> float:
        """PBR 점수 (낮을수록 좋음)"""
        if pbr <= 0:
            return 0.0
        elif pbr <= 0.5:
            return 100.0
        elif pbr <= 1.0:
            return 80.0
        elif pbr <= 1.5:
            return 60.0
        elif pbr <= 2.0:
            return 40.0
        elif pbr <= 2.5:
            return 20.0
        else:
            return 0.0
    
    def _score_roe(self, roe: float) -> float:
        """ROE 점수 (높을수록 좋음)"""
        if roe >= 20:
            return 100.0
        elif roe >= 15:
            return 80.0
        elif roe >= 10:
            return 60.0
        elif roe >= 5:
            return 40.0
        elif roe > 0:
            return 20.0
        else:
            return 0.0
    
    def _score_roa(self, roa: float) -> float:
        """ROA 점수 (높을수록 좋음)"""
        if roa >= 10:
            return 100.0
        elif roa >= 7:
            return 80.0
        elif roa >= 5:
            return 60.0
        elif roa >= 3:
            return 40.0
        elif roa > 0:
            return 20.0
        else:
            return 0.0
    
    def _score_profit_margin(self, margin: float) -> float:
        """순이익률 점수 (높을수록 좋음)"""
        if margin >= 15:
            return 100.0
        elif margin >= 10:
            return 80.0
        elif margin >= 5:
            return 60.0
        elif margin >= 2:
            return 40.0
        elif margin > 0:
            return 20.0
        else:
            return 0.0
    
    def _score_debt_ratio(self, debt_ratio: float) -> float:
        """부채비율 점수 (낮을수록 좋음)"""
        if debt_ratio <= 30:
            return 100.0
        elif debt_ratio <= 50:
            return 80.0
        elif debt_ratio <= 70:
            return 60.0
        elif debt_ratio <= 100:
            return 40.0
        elif debt_ratio <= 150:
            return 20.0
        else:
            return 0.0
    
    def _score_current_ratio(self, current_ratio: float) -> float:
        """유동비율 점수 (적정 범위가 좋음)"""
        if 1.5 <= current_ratio <= 3.0:
            return 100.0
        elif 1.2 <= current_ratio <= 3.5:
            return 80.0
        elif 1.0 <= current_ratio <= 4.0:
            return 60.0
        elif 0.8 <= current_ratio <= 5.0:
            return 40.0
        else:
            return 20.0
    
    def _score_growth_rate(self, growth_rate: float) -> float:
        """성장률 점수 (적정 범위가 좋음)"""
        if 10 <= growth_rate <= 30:
            return 100.0
        elif 5 <= growth_rate <= 40:
            return 80.0
        elif 0 <= growth_rate <= 50:
            return 60.0
        elif -10 <= growth_rate <= 60:
            return 40.0
        else:
            return 20.0
    
    def _score_dividend_yield(self, dividend_yield: float) -> float:
        """배당수익률 점수 (적정 범위가 좋음)"""
        if 3 <= dividend_yield <= 6:
            return 100.0
        elif 2 <= dividend_yield <= 8:
            return 80.0
        elif 1 <= dividend_yield <= 10:
            return 60.0
        elif 0.5 <= dividend_yield <= 15:
            return 40.0
        else:
            return 20.0
    
    def _determine_grade_and_recommendation(self, comprehensive_score: float, 
                                          quant_score: float, qual_score: float) -> Tuple[str, str, float]:
        """등급 및 추천 결정"""
        # 등급 결정
        if comprehensive_score >= 90:
            grade = "A+"
        elif comprehensive_score >= 80:
            grade = "A"
        elif comprehensive_score >= 70:
            grade = "B+"
        elif comprehensive_score >= 60:
            grade = "B"
        elif comprehensive_score >= 50:
            grade = "C+"
        elif comprehensive_score >= 40:
            grade = "C"
        elif comprehensive_score >= 30:
            grade = "D+"
        elif comprehensive_score >= 20:
            grade = "D"
        else:
            grade = "F"
        
        # 추천 결정
        if comprehensive_score >= 70 and quant_score >= 60 and qual_score >= 60:
            recommendation = "STRONG_BUY"
            confidence = 0.9
        elif comprehensive_score >= 60 and quant_score >= 50 and qual_score >= 50:
            recommendation = "BUY"
            confidence = 0.8
        elif comprehensive_score >= 50:
            recommendation = "HOLD"
            confidence = 0.6
        elif comprehensive_score >= 40:
            recommendation = "HOLD"
            confidence = 0.4
        else:
            recommendation = "SELL"
            confidence = 0.2
        
        return grade, recommendation, confidence
    
    async def analyze_stock_comprehensive(self, symbol: str, name: str, sector: str) -> Dict[str, Any]:
        """종합 분석 실행"""
        try:
            self.logger.info(f"🔍 {name}({symbol}) 종합 분석 시작")
            
            # 기존 분석 실행
            basic_result = await self.analyzer.analyze_stock_ultimate(symbol, name, sector)
            if not basic_result:
                return None
            
            # 정량적 지표 추출
            financial_data = basic_result.financial_data
            quant_metrics = QuantitativeMetrics(
                per=financial_data.get('per', 0),
                pbr=financial_data.get('pbr', 0),
                roe=financial_data.get('roe', 0),
                roa=financial_data.get('roa', 0),
                debt_ratio=financial_data.get('debt_ratio', 0),
                current_ratio=financial_data.get('current_ratio', 0),
                net_profit_margin=financial_data.get('net_margin', 0),
                revenue_growth=financial_data.get('revenue_growth_rate', 0),
                profit_growth=financial_data.get('operating_income_growth_rate', 0),
                market_cap=financial_data.get('market_cap', 0),
                dividend_yield=financial_data.get('dividend_yield', 0)
            )
            
            # 정성적 지표 계산
            qual_metrics = await self._calculate_qualitative_metrics(symbol, name, sector, basic_result)
            
            # 종합점수 계산
            comprehensive_score = self.calculate_comprehensive_score(quant_metrics, qual_metrics)
            
            # 결과 정리
            result = {
                'symbol': symbol,
                'name': name,
                'sector': sector,
                'analysis_date': datetime.now().isoformat(),
                'quantitative_metrics': quant_metrics.__dict__,
                'qualitative_metrics': {
                    'sector_outlook': qual_metrics.sector_outlook,
                    'market_cycle_position': qual_metrics.market_cycle_position,
                    'competitive_advantage': qual_metrics.competitive_advantage,
                    'management_quality': qual_metrics.management_quality,
                    'esg_score': qual_metrics.esg_score,
                    'news_sentiment': qual_metrics.news_sentiment,
                    'analyst_consensus': qual_metrics.analyst_consensus,
                    'risk_level': qual_metrics.risk_level.value  # Enum을 문자열로 변환
                },
                'comprehensive_score': comprehensive_score.__dict__,
                'basic_analysis': {
                    'ultimate_score': basic_result.ultimate_score,
                    'enhanced_score': basic_result.enhanced_score,
                    'financial_score': basic_result.financial_score
                }
            }
            
            self.logger.info(f"✅ {name}({symbol}) 종합 분석 완료: {comprehensive_score.comprehensive_score:.1f}점 ({comprehensive_score.grade})")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {name}({symbol}) 종합 분석 실패: {e}")
            return None
    
    async def _calculate_qualitative_metrics(self, symbol: str, name: str, sector: str, 
                                           basic_result) -> QualitativeMetrics:
        """정성적 지표 계산"""
        try:
            # 업종 전망 점수
            sector_outlook = self._get_sector_outlook_score(sector)
            
            # 시장 사이클 위치
            market_cycle = self._get_market_cycle_score()
            
            # 경쟁우위 점수
            competitive_advantage = self._get_competitive_advantage_score(symbol, sector)
            
            # 경영진 품질 점수
            management_quality = self._get_management_quality_score(symbol)
            
            # ESG 점수
            esg_score = self._get_esg_score(symbol)
            
            # 뉴스 감정 점수
            news_sentiment = self._get_news_sentiment_score(basic_result)
            
            # 애널리스트 합의 점수
            analyst_consensus = self._get_analyst_consensus_score(basic_result)
            
            # 리스크 레벨 결정
            risk_level = self._determine_risk_level(sector_outlook, market_cycle, competitive_advantage)
            
            return QualitativeMetrics(
                sector_outlook=sector_outlook,
                market_cycle_position=market_cycle,
                competitive_advantage=competitive_advantage,
                management_quality=management_quality,
                esg_score=esg_score,
                news_sentiment=news_sentiment,
                analyst_consensus=analyst_consensus,
                risk_level=risk_level
            )
            
        except Exception as e:
            self.logger.error(f"❌ 정성적 지표 계산 실패 {symbol}: {e}")
            # 기본값 반환
            return QualitativeMetrics()
    
    def _get_sector_outlook_score(self, sector: str) -> float:
        """업종 전망 점수"""
        sector_scores = {
            '반도체': 75.0,
            '자동차': 70.0,
            '바이오': 80.0,
            '화학': 65.0,
            '금융': 60.0,
            '통신': 55.0,
            '철강': 50.0,
            '정유': 45.0,
            '전력': 40.0
        }
        return sector_scores.get(sector, 60.0)
    
    def _get_market_cycle_score(self) -> float:
        """시장 사이클 점수"""
        # 현재 시장 상황에 따른 점수 (실제로는 시장 데이터 기반으로 계산)
        return 65.0  # 중간 정도
    
    def _get_competitive_advantage_score(self, symbol: str, sector: str) -> float:
        """경쟁우위 점수"""
        # 대형주는 높은 점수
        large_caps = ['005930', '000660', '035420', '051910', '035720']
        if symbol in large_caps:
            return 80.0
        
        # 업종별 기본 점수
        sector_scores = {
            '반도체': 75.0,
            '자동차': 70.0,
            '바이오': 65.0,
            '화학': 60.0,
            '금융': 55.0
        }
        return sector_scores.get(sector, 60.0)
    
    def _get_management_quality_score(self, symbol: str) -> float:
        """경영진 품질 점수"""
        # 대기업은 높은 점수
        blue_chips = ['005930', '000660', '035420', '051910', '035720', '005380', '000270']
        if symbol in blue_chips:
            return 75.0
        return 60.0  # 기본값
    
    def _get_esg_score(self, symbol: str) -> float:
        """ESG 점수"""
        # ESG 우수 기업 점수
        esg_leading = ['005930', '051910', '035420']
        if symbol in esg_leading:
            return 80.0
        return 65.0  # 기본값
    
    def _get_news_sentiment_score(self, basic_result) -> float:
        """뉴스 감정 점수"""
        # 기본 결과에서 뉴스 분석 데이터 추출
        if hasattr(basic_result, 'news_analysis') and basic_result.news_analysis:
            sentiment = basic_result.news_analysis.get('avg_sentiment', 0.5)
            return sentiment * 100  # 0-1 범위를 0-100으로 변환
        return 60.0  # 기본값
    
    def _get_analyst_consensus_score(self, basic_result) -> float:
        """애널리스트 합의 점수"""
        # 기본 결과에서 투자 의견 점수 추출
        if hasattr(basic_result, 'investment_recommendation'):
            rec = basic_result.investment_recommendation
            if rec == 'STRONG_BUY':
                return 90.0
            elif rec == 'BUY':
                return 75.0
            elif rec == 'HOLD':
                return 60.0
            elif rec == 'SELL':
                return 30.0
        return 60.0  # 기본값
    
    def _determine_risk_level(self, sector_outlook: float, market_cycle: float, 
                            competitive_advantage: float) -> RiskLevel:
        """리스크 레벨 결정"""
        avg_score = (sector_outlook + market_cycle + competitive_advantage) / 3
        
        if avg_score >= 75:
            return RiskLevel.LOW
        elif avg_score >= 60:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH


async def main():
    """테스트 실행"""
    print("=" * 100)
    print("📊 정량적 + 정성적 지표 통합 종합점수 시스템")
    print("=" * 100)
    
    # 시스템 초기화
    scoring_system = ComprehensiveScoringSystem()
    
    # 테스트 종목들
    test_stocks = [
        ('005930', '삼성전자', '반도체'),
        ('000660', 'SK하이닉스', '반도체'),
        ('005380', '현대차', '자동차'),
        ('000270', '기아', '자동차'),
        ('003550', 'LG생활건강', '화장품/생활용품')
    ]
    
    results = []
    
    for symbol, name, sector in test_stocks:
        result = await scoring_system.analyze_stock_comprehensive(symbol, name, sector)
        if result:
            results.append(result)
    
    # 결과 출력
    print(f"\n📊 종합 분석 결과 ({len(results)}개 종목)")
    print("-" * 80)
    
    for result in results:
        comp_score = result['comprehensive_score']
        print(f"{result['name']}({result['symbol']}): {comp_score['comprehensive_score']:.1f}점 ({comp_score['grade']}) - {comp_score['recommendation']}")
        print(f"  정량: {comp_score['quantitative_score']:.1f}점, 정성: {comp_score['qualitative_score']:.1f}점")
        print(f"  신뢰도: {comp_score['confidence']:.1%}")
        print()
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comprehensive_scoring_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"💾 결과 저장: {filename}")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
