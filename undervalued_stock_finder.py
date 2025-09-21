#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
저평가 가치주 발굴 시스템
전체 KOSPI 종목을 분석하여 저평가 가치주를 추천
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import yaml

# 기존 모듈들
from ultimate_enhanced_analyzer import UltimateEnhancedAnalyzer, UltimateAnalysisResult
from kis_data_provider import KISDataProvider
from config_manager import ConfigManager

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UndervaluedStockFinder:
    """저평가 가치주 발굴기"""
    
    def __init__(self, config_file: str = "config.yaml"):
        # 설정 파일 경로 수정
        if config_file == "config.yaml":
            config_file = "./config.yaml"
        
        self.analyzer = UltimateEnhancedAnalyzer(config_file)
        self.kospi_data = None
        self.analysis_results = []
        
        # KOSPI 데이터 로드
        self._load_kospi_data()
        
        logger.info("🔍 저평가 가치주 발굴기 초기화 완료")
    
    def _load_kospi_data(self):
        """KOSPI 마스터 데이터 로드"""
        try:
            kospi_file = 'kospi_code.xlsx'
            import os
            if os.path.exists(kospi_file):
                self.kospi_data = pd.read_excel(kospi_file)
                # 컬럼명 확인 및 표준화
                if '단축코드' in self.kospi_data.columns:
                    self.kospi_data['단축코드'] = self.kospi_data['단축코드'].astype(str).str.zfill(6)
                elif 'code' in self.kospi_data.columns:
                    self.kospi_data['단축코드'] = self.kospi_data['code'].astype(str).str.zfill(6)
                
                # 회사명 컬럼 찾기
                name_columns = ['회사명', 'company_name', 'name', '종목명']
                for col in name_columns:
                    if col in self.kospi_data.columns:
                        self.kospi_data['회사명'] = self.kospi_data[col]
                        break
                else:
                    self.kospi_data['회사명'] = 'Unknown'
                
                # 업종 컬럼 찾기
                sector_columns = ['업종', 'sector', 'industry']
                for col in sector_columns:
                    if col in self.kospi_data.columns:
                        self.kospi_data['업종'] = self.kospi_data[col]
                        break
                else:
                    self.kospi_data['업종'] = 'Unknown'
                
                logger.info(f"📊 KOSPI 데이터 로드 완료: {len(self.kospi_data)}개 종목")
                logger.info(f"📊 컬럼명: {list(self.kospi_data.columns)}")
            else:
                logger.warning("KOSPI 마스터 파일이 없습니다. 기본 종목 리스트를 사용합니다.")
                self._create_default_stock_list()
        except Exception as e:
            logger.error(f"KOSPI 데이터 로드 실패: {e}")
            self._create_default_stock_list()
        
        # 회사명이 Unknown인 경우 기본 종목 리스트로 교체
        if '회사명' in self.kospi_data.columns:
            unknown_count = (self.kospi_data['회사명'] == 'Unknown').sum()
            if unknown_count > 0:
                logger.warning(f"Unknown 종목 {unknown_count}개 발견. 기본 종목 리스트를 사용합니다.")
                self._create_default_stock_list()
    
    def _create_default_stock_list(self):
        """기본 종목 리스트 생성"""
        default_stocks = [
            {'단축코드': '005930', '회사명': '삼성전자', '업종': '반도체'},
            {'단축코드': '000270', '회사명': '기아', '업종': '자동차'},
            {'단축코드': '035420', '회사명': 'NAVER', '업종': '인터넷'},
            {'단축코드': '012330', '회사명': '현대모비스', '업종': '자동차부품'},
            {'단축코드': '066570', '회사명': 'LG전자', '업종': '전자제품'},
            {'단축코드': '051910', '회사명': 'LG화학', '업종': '화학'},
            {'단축코드': '035720', '회사명': '카카오', '업종': '인터넷'},
            {'단축코드': '207940', '회사명': '삼성바이오로직스', '업종': '바이오'},
            {'단축코드': '068270', '회사명': '셀트리온', '업종': '바이오'},
            {'단축코드': '003550', '회사명': 'LG생활건강', '업종': '화장품'},
            {'단축코드': '000810', '회사명': '삼성화재', '업종': '보험'},
            {'단축코드': '015760', '회사명': '한국전력', '업종': '전력'},
            {'단축코드': '096770', '회사명': 'SK이노베이션', '업종': '에너지'},
            {'단축코드': '017670', '회사명': 'SK텔레콤', '업종': '통신'},
            {'단축코드': '028260', '회사명': '삼성물산', '업종': '건설'},
            {'단축코드': '011200', '회사명': 'HMM', '업종': '해운'},
            {'단축코드': '005380', '회사명': '현대차', '업종': '자동차'},
            {'단축코드': '373220', '회사명': 'LG에너지솔루션', '업종': '배터리'},
            {'단축코드': '006400', '회사명': '삼성SDI', '업종': '배터리'},
            {'단축코드': '000720', '회사명': '현대건설', '업종': '건설'}
        ]
        
        self.kospi_data = pd.DataFrame(default_stocks)
        logger.info(f"📊 기본 종목 리스트 생성: {len(self.kospi_data)}개 종목")
    
    async def analyze_stocks(self, max_stocks: int = 50, parallel_workers: int = 5) -> List[UltimateAnalysisResult]:
        """종목들 분석"""
        logger.info(f"🔍 {max_stocks}개 종목 분석 시작 (병렬 처리: {parallel_workers}개)")
        
        # 분석할 종목 선택 (시가총액 기준 상위 종목들)
        stocks_to_analyze = self.kospi_data.head(max_stocks)
        
        results = []
        
        # 순차 처리로 변경 (비동기 처리 복잡성 해결)
        completed = 0
        for _, stock in stocks_to_analyze.iterrows():
            symbol = stock['단축코드']
            name = stock['회사명']
            sector = stock['업종']
            
            try:
                result = await self._analyze_single_stock(symbol, name, sector)
                if result:
                    results.append(result)
                    logger.info(f"✅ {name}({symbol}) 분석 완료: {result.ultimate_score:.1f}점 ({result.ultimate_grade})")
                else:
                    logger.warning(f"⚠️ {name}({symbol}) 분석 실패")
            except Exception as e:
                logger.error(f"❌ {name}({symbol}) 분석 오류: {e}")
            
            completed += 1
            if completed % 5 == 0:
                logger.info(f"📊 진행률: {completed}/{max_stocks} ({completed/max_stocks*100:.1f}%)")
        
        self.analysis_results = results
        logger.info(f"🎯 분석 완료: {len(results)}개 종목")
        return results
    
    async def _analyze_single_stock(self, symbol: str, name: str, sector: str) -> Optional[UltimateAnalysisResult]:
        """단일 종목 분석"""
        try:
            result = await self.analyzer.analyze_stock_ultimate(symbol, name, sector)
            return result
        except Exception as e:
            logger.error(f"종목 분석 실패 {symbol}: {e}")
            return None
    
    def find_undervalued_stocks(self, 
                              min_score: float = 70.0,
                              max_stocks: int = 20,
                              sort_by: str = 'ultimate_score') -> List[Dict[str, Any]]:
        """저평가 가치주 발굴"""
        if not self.analysis_results:
            logger.warning("분석 결과가 없습니다. 먼저 analyze_stocks()를 실행하세요.")
            return []
        
        logger.info(f"🔍 저평가 가치주 발굴 시작 (최소 점수: {min_score}, 최대 개수: {max_stocks})")
        
        # 조건에 맞는 종목 필터링
        undervalued_stocks = []
        
        for result in self.analysis_results:
            # 기본 조건 확인 (조건 완화)
            if (result.ultimate_score >= min_score and 
                result.investment_recommendation in ['BUY', 'STRONG_BUY', 'HOLD'] and
                result.confidence_level in ['MEDIUM', 'HIGH', 'LOW']):
                
                # 추가 필터링 조건
                financial_data = result.financial_data
                
                # PER이 너무 높지 않음 (50 이하)
                per = financial_data.get('per', 999)
                if per > 50:
                    continue
                
                # PBR이 적정 범위 (3 이하)
                pbr = financial_data.get('pbr', 999)
                if pbr > 3:
                    continue
                
                # 부채비율이 너무 높지 않음 (200% 이하)
                debt_ratio = financial_data.get('debt_ratio', 999)
                if debt_ratio > 200:
                    continue
                
                # ROE가 양수
                roe = financial_data.get('roe', -999)
                if roe <= 0:
                    continue
                
                stock_info = {
                    'symbol': result.symbol,
                    'name': result.name,
                    'sector': result.sector,
                    'ultimate_score': result.ultimate_score,
                    'ultimate_grade': result.ultimate_grade,
                    'investment_recommendation': result.investment_recommendation,
                    'confidence_level': result.confidence_level,
                    'enhanced_score': result.enhanced_score,
                    'enhanced_grade': result.enhanced_grade,
                    'financial_data': {
                        'current_price': financial_data.get('current_price', 0),
                        'per': per,
                        'pbr': pbr,
                        'roe': roe,
                        'debt_ratio': debt_ratio,
                        'revenue_growth_rate': financial_data.get('revenue_growth_rate', 0),
                        'operating_income_growth_rate': financial_data.get('operating_income_growth_rate', 0),
                        'net_income_growth_rate': financial_data.get('net_income_growth_rate', 0)
                    },
                    'news_analysis': result.news_analysis,
                    'qualitative_risk_analysis': result.qualitative_risk_analysis,
                    'sector_analysis': result.sector_analysis,
                    'ml_prediction': result.ml_prediction
                }
                
                undervalued_stocks.append(stock_info)
        
        # 정렬
        if sort_by == 'ultimate_score':
            undervalued_stocks.sort(key=lambda x: x['ultimate_score'], reverse=True)
        elif sort_by == 'per':
            undervalued_stocks.sort(key=lambda x: x['financial_data']['per'])
        elif sort_by == 'pbr':
            undervalued_stocks.sort(key=lambda x: x['financial_data']['pbr'])
        elif sort_by == 'roe':
            undervalued_stocks.sort(key=lambda x: x['financial_data']['roe'], reverse=True)
        
        # 상위 N개 선택
        top_undervalued = undervalued_stocks[:max_stocks]
        
        logger.info(f"🎯 저평가 가치주 발굴 완료: {len(top_undervalued)}개 종목")
        return top_undervalued
    
    def generate_recommendation_report(self, undervalued_stocks: List[Dict[str, Any]]) -> str:
        """추천 보고서 생성"""
        if not undervalued_stocks:
            return "❌ 조건에 맞는 저평가 가치주가 없습니다."
        
        report = []
        report.append("=" * 80)
        report.append("🎯 저평가 가치주 추천 보고서")
        report.append("=" * 80)
        report.append(f"📅 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📊 추천 종목 수: {len(undervalued_stocks)}개")
        report.append("")
        
        for i, stock in enumerate(undervalued_stocks, 1):
            report.append(f"🏆 {i}. {stock['name']} ({stock['symbol']})")
            report.append(f"   업종: {stock['sector']}")
            report.append(f"   궁극의 점수: {stock['ultimate_score']:.1f}점 ({stock['ultimate_grade']})")
            report.append(f"   투자 추천: {stock['investment_recommendation']}")
            report.append(f"   신뢰도: {stock['confidence_level']}")
            
            financial = stock['financial_data']
            report.append(f"   💰 주요 지표:")
            report.append(f"     - 현재가: {financial['current_price']:,}원")
            report.append(f"     - PER: {financial['per']:.1f}배")
            report.append(f"     - PBR: {financial['pbr']:.2f}배")
            report.append(f"     - ROE: {financial['roe']:.1f}%")
            report.append(f"     - 부채비율: {financial['debt_ratio']:.1f}%")
            report.append(f"     - 매출증가율: {financial['revenue_growth_rate']:.1f}%")
            report.append(f"     - 영업이익증가율: {financial['operating_income_growth_rate']:.1f}%")
            
            # 뉴스 분석 결과
            if stock['news_analysis']:
                news = stock['news_analysis']
                report.append(f"   📰 뉴스 분석:")
                report.append(f"     - 총 뉴스: {news.get('total_news', 0)}건")
                report.append(f"     - 감정 트렌드: {news.get('sentiment_trend', 'neutral')}")
                report.append(f"     - 평균 감정: {news.get('avg_sentiment', 0):.3f}")
            
            # 정성적 리스크
            if stock['qualitative_risk_analysis']:
                risk = stock['qualitative_risk_analysis']
                report.append(f"   ⚠️ 정성적 리스크:")
                report.append(f"     - 종합 리스크: {risk.get('comprehensive_risk_score', 0):.1f}점")
            
            # 머신러닝 예측
            if stock['ml_prediction']:
                ml = stock['ml_prediction']
                report.append(f"   🤖 AI 예측:")
                report.append(f"     - 예측 수익률: {ml.get('ensemble_prediction', 0):.3f}")
                report.append(f"     - 예측 신뢰도: {ml.get('ensemble_confidence', 0):.3f}")
            
            report.append("")
        
        # 요약 통계
        report.append("📊 요약 통계")
        report.append("-" * 40)
        
        scores = [s['ultimate_score'] for s in undervalued_stocks]
        pers = [s['financial_data']['per'] for s in undervalued_stocks]
        pbrs = [s['financial_data']['pbr'] for s in undervalued_stocks]
        roes = [s['financial_data']['roe'] for s in undervalued_stocks]
        
        report.append(f"평균 궁극의 점수: {np.mean(scores):.1f}점")
        report.append(f"평균 PER: {np.mean(pers):.1f}배")
        report.append(f"평균 PBR: {np.mean(pbrs):.2f}배")
        report.append(f"평균 ROE: {np.mean(roes):.1f}%")
        
        # 투자 추천 분포
        recommendations = [s['investment_recommendation'] for s in undervalued_stocks]
        rec_counts = {}
        for rec in recommendations:
            rec_counts[rec] = rec_counts.get(rec, 0) + 1
        
        report.append(f"투자 추천 분포:")
        for rec, count in rec_counts.items():
            report.append(f"  - {rec}: {count}개")
        
        report.append("")
        report.append("⚠️ 투자 주의사항:")
        report.append("- 이 분석은 참고용이며, 투자 결정은 개인의 책임입니다.")
        report.append("- 시장 상황과 개인적 위험 감수 능력을 고려하세요.")
        report.append("- 분산 투자를 통해 리스크를 관리하세요.")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_results(self, undervalued_stocks: List[Dict[str, Any]], filename: str = None):
        """결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"undervalued_stocks_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(undervalued_stocks, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 저평가 가치주 결과 저장: {filename}")
            return filename
        except Exception as e:
            logger.error(f"결과 저장 실패: {e}")
            return None

async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🎯 저평가 가치주 발굴 시스템")
    print("=" * 80)
    
    # 발굴기 초기화
    finder = UndervaluedStockFinder()
    
    # 종목 분석 (전체 KOSPI 종목 분석)
    print(f"\n🔍 종목 분석 시작...")
    results = await finder.analyze_stocks(max_stocks=100, parallel_workers=5)  # 100개 종목, 5개 병렬 처리
    
    if not results:
        print("❌ 분석할 종목이 없습니다.")
        return
    
    # 저평가 가치주 발굴
    print(f"\n🎯 저평가 가치주 발굴...")
    undervalued_stocks = finder.find_undervalued_stocks(
        min_score=40.0,  # 최소 점수 40점 (기준 완화)
        max_stocks=10,   # 상위 10개
        sort_by='ultimate_score'  # 궁극의 점수 기준 정렬
    )
    
    # 추천 보고서 생성
    print(f"\n📊 추천 보고서 생성...")
    report = finder.generate_recommendation_report(undervalued_stocks)
    print(report)
    
    # 결과 저장
    filename = finder.save_results(undervalued_stocks)
    if filename:
        print(f"\n💾 결과 저장: {filename}")
    
    # 보고서도 파일로 저장
    report_filename = f"undervalued_stocks_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 보고서 저장: {report_filename}")
    
    print(f"\n" + "=" * 80)
    print("✅ 저평가 가치주 발굴 완료")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
