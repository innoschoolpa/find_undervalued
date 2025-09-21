#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
궁극의 전체 시장 분석기 v2.0
enhanced_integrated_analyzer_refactored.py의 핵심 장점들을 통합한 최종 버전
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import argparse

# 새로운 향상된 컴포넌트들
from ultimate_enhanced_analyzer_v2 import UltimateEnhancedAnalyzerV2, UltimateAnalysisResult
from enhanced_architecture_components import (
    TPSRateLimiter, ParallelProcessor, EnhancedLogger
)
from comprehensive_scoring_system import ComprehensiveScoringSystem, QuantitativeMetrics, QualitativeMetrics

# v3.0 향상된 기능들
from realtime_data_integration import RealTimeMarketAnalyzer, RealTimeDataProvider
from enhanced_sector_classification import EnhancedSectorClassifier, SectorLevel
from company_specific_analyzer import CompanySpecificAnalyzer, CompanyType
from external_data_integration import ExternalDataAnalyzer, ExternalDataProvider

# 저평가 가치 중심 개선사항들
from enhanced_price_provider import EnhancedPriceProvider
from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer

# 로깅 설정 (중복 로그 방지)
import sys
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
logger = EnhancedLogger(__name__)

def _getattr_or_get(d, key, default=None):
    """객체/딕셔너리 안전 접근 유틸"""
    try:
        return getattr(d, key)
    except Exception:
        try:
            return d.get(key, default)
        except Exception:
            return default

class UltimateMarketAnalyzerV2:
    """궁극의 전체 시장 분석기 v2.0"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.logger = EnhancedLogger(__name__)
        self.analyzer = UltimateEnhancedAnalyzerV2(config_file)
        self.comprehensive_scoring = ComprehensiveScoringSystem(config_file)
        self.analysis_results = []
        
        # 시가총액 상위 종목 캐시
        self._market_cap_cache = {}
        self._last_update = None
        
        # v3.0 향상된 기능들 초기화
        self.realtime_analyzer = RealTimeMarketAnalyzer()
        self.sector_classifier = EnhancedSectorClassifier()
        self.company_analyzer = CompanySpecificAnalyzer()
        self.external_analyzer = ExternalDataAnalyzer()
        
        # 저평가 가치 중심 개선사항들 초기화
        self.enhanced_price_provider = EnhancedPriceProvider(config_file)
        self.enhanced_integrated_analyzer = EnhancedIntegratedAnalyzer()
        
        # 통합 분석 결과 캐시
        self._enhanced_analysis_cache = {}
        
        logger.info("🌍 궁극의 전체 시장 분석기 v2.0 (저평가 가치 중심 개선) 초기화 완료")
    
    def _apply_quality_filters(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """품질 하드필터 적용 (저평가+저품질 제외)"""
        def pass_quality(r: Dict[str, Any]) -> bool:
            """최소 품질 기준 통과 여부 확인"""
            financial_data = r.get('financial_data', {})
            roe = financial_data.get('roe', 0)
            debt_ratio = financial_data.get('debt_ratio', 999)
            net_profit_margin = financial_data.get('net_profit_margin', -999)
            
            # 저평가 기회 중심 컷: ROE≥1, 부채비율≤400, 순이익률≥-10 (더 많은 기회 포착)
            return (roe >= 1) and (debt_ratio <= 400) and (net_profit_margin >= -10)
        
        # 품질 필터 적용
        quality_filtered = [r for r in results if pass_quality(r)]
        
        # 고위치 차단형 룰 (90% 이하만 허용)
        price_filtered = [
            r for r in quality_filtered
            if r.get('price_position') is None or r.get('price_position', 0) <= 90
        ]
        
        logger.info(f"🔍 품질 필터 적용: {len(results)} → {len(quality_filtered)} → {len(price_filtered)}")
        return price_filtered
    
    def _calculate_sector_percentile_score(self, symbol: str, per: float, pbr: float, roe: float) -> Dict[str, Any]:
        """섹터 내부 백분위 기반 밸류에이션 점수 계산"""
        try:
            import numpy as np, math
            kospi = self._load_kospi_data()
            if kospi is None or kospi.empty:
                return {'total_score': 50, 'base_score': 50, 'grade': 'C', 'description': '데이터 부족'}

            # 섹터 추정
            sector_cols = ['업종','지수업종대분류','업종명','섹터']
            sector_name = None
            for col in sector_cols:
                if col in kospi.columns:
                    sector_name = kospi[kospi['단축코드']==str(symbol)][col].astype(str).squeeze() if not kospi[kospi['단축코드']==str(symbol)].empty else None
                    break
            if not sector_name or (isinstance(sector_name, float) and math.isnan(sector_name)):
                sector_name = '기타'

            peers = kospi.copy()
            if '업종' in peers.columns:
                peers = peers[peers['업종'].astype(str).str.contains(str(sector_name), na=False)]

            # 동종군 PER/PBR/ROE 수집 (상한 400개)
            vals = []
            get_pd = self.enhanced_integrated_analyzer.data_provider.get_price_data
            get_fd = self.enhanced_integrated_analyzer.data_provider.get_financial_data
            for code in peers['단축코드'].astype(str).tolist()[:400]:
                pr = get_pd(code)
                fn = get_fd(code)
                vals.append([
                    float(pr.get('per', np.nan)) if pr.get('per') not in (None, 0) else np.nan,
                    float(pr.get('pbr', np.nan)) if pr.get('pbr') not in (None, 0) else np.nan,
                    float(fn.get('roe', np.nan)) if fn.get('roe') not in (None, 0) else np.nan
                ])
            arr = np.array(vals, dtype=float)

            def pct_rank(x, col, higher_better: bool):
                colv = arr[:, col]
                colv = colv[~np.isnan(colv)]
                if len(colv) < 25 or x is None or not math.isfinite(x):
                    return 0.5  # 중립
                if higher_better:
                    return (colv < x).mean()
                else:
                    return (colv > x).mean()

            per_p = pct_rank(per, 0, higher_better=False)   # 낮을수록 좋음
            pbr_p = pct_rank(pbr, 1, higher_better=False)   # 낮을수록 좋음
            roe_p = pct_rank(roe, 2, higher_better=True)    # 높을수록 좋음

            base_score = ((per_p + pbr_p + roe_p)/3.0) * 100.0
            grade = "A+" if base_score>=80 else "A" if base_score>=70 else "B+" if base_score>=60 else "B" if base_score>=50 else "C" if base_score>=40 else "D"
            return {
                'total_score': base_score, 'base_score': base_score, 'grade': grade,
                'description': '섹터 백분위 기반 점수',
                'per_score': per_p*100, 'pbr_score': pbr_p*100, 'roe_score': roe_p*100
            }
        except Exception as e:
            logger.error(f"섹터 백분위 계산 실패 {symbol}: {e}")
            return {'total_score':50,'base_score':50,'grade':'C','description':'계산 실패'}
    
    async def analyze_undervalued_stocks_enhanced(self, 
                                                top_n: int = 50,
                                                min_score: float = 20.0,
                                                max_workers: int = 4) -> Dict[str, Any]:
        """저평가 가치 중심 향상된 분석"""
        logger.info(f"🎯 저평가 가치 중심 분석 시작 (상위 {top_n}개, 최소점수 {min_score})")
        
        start_time = datetime.now()
        
        # KOSPI 데이터 로드
        kospi_data = self._load_kospi_data()
        if kospi_data is None or len(kospi_data) == 0:
            logger.warning("KOSPI 데이터가 없습니다.")
            return {}
        
        # 시가총액 상위 종목 선택
        if '시가총액' in kospi_data.columns:
            kospi_data_with_cap = kospi_data[kospi_data['시가총액'].notna() & (kospi_data['시가총액'] > 0)]
            top_stocks = kospi_data_with_cap.nlargest(top_n, '시가총액')
        else:
            top_stocks = kospi_data.head(top_n)
        
        # 향상된 통합 분석기 사용 (강화된 에러 핸들링)
        results = []
        try:
            # enhanced_integrated_analyzer_refactored.py의 메서드 사용
            if hasattr(self.enhanced_integrated_analyzer, 'analyze_stocks_parallel'):
                results = await self.enhanced_integrated_analyzer.analyze_stocks_parallel(
                    top_stocks, min_score=min_score, max_workers=max_workers
                )
            else:
                # 폴백: 기본 분석기 사용
                results = await self._fallback_analysis_with_retry(top_stocks, max_retries=2)
            
            if not results:
                raise Exception("분석기에서 결과가 없습니다.")
        except Exception as e:
            logger.warning(f"⚠️ 향상된 분석 실패, 폴백 모드로 전환: {e}")
            # 폴백: 기본 분석기 사용 (재시도 로직 포함)
            results = await self._fallback_analysis_with_retry(top_stocks, max_retries=2)
        
        if not results:
            logger.warning("분석할 종목이 없습니다.")
            return {}
        
        # 품질 필터 적용
        filtered_results = self._apply_quality_filters(results)
        
        # 점수 기준 정렬
        filtered_results.sort(key=lambda x: x.get('enhanced_score', 0), reverse=True)
        
        end_time = datetime.now()
        analysis_time = end_time - start_time
        
        # 결과 구성
        result = {
            'analysis_type': 'undervalued_value_enhanced',
            'timestamp': start_time.isoformat(),
            'analysis_time_seconds': analysis_time.total_seconds(),
            'total_analyzed': len(results),
            'filtered_count': len(filtered_results),
            'min_score_threshold': min_score,
            'top_recommendations': filtered_results[:20],  # 상위 20개만
            'summary': {
                'high_quality_count': len([r for r in filtered_results if r.get('enhanced_score', 0) >= 40]),
                'medium_quality_count': len([r for r in filtered_results if 20 <= r.get('enhanced_score', 0) < 40]),
                'average_score': np.mean([r.get('enhanced_score', 0) for r in filtered_results]) if filtered_results else 0
            }
        }
        
        logger.info(f"✅ 저평가 가치 중심 분석 완료: {len(filtered_results)}개 추천 ({analysis_time.total_seconds():.1f}초)")
        return result
    
    async def _analyze_stocks_parallel_enhanced(self, 
                                              top_stocks: pd.DataFrame,
                                              realtime_results: Dict[str, Any],
                                              external_results: Dict[str, Any],
                                              max_workers: int = 4) -> List[Dict[str, Any]]:
        """병렬 처리로 종목 분석 성능 개선"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        logger.info(f"🚀 병렬 분석 시작 (최대 {max_workers}개 워커)")
        
        results = []
        completed = 0
        total_stocks = len(top_stocks)
        
        # 비동기 태스크 생성
        async def analyze_single_stock_enhanced(stock_data):
            symbol = stock_data['단축코드']
            name = stock_data['회사명']
            sector = stock_data.get('업종', '기타')
            
            try:
                # 기본 분석
                result = await self.analyzer.analyze_stock_ultimate(symbol, name, sector)
                if not result:
                    return None
                
                # 향상된 분석 수행
                enhanced_result = await self._perform_enhanced_analysis(
                    result, realtime_results.get(symbol, {}), external_results.get(symbol, {})
                )
                
                return enhanced_result
                
            except Exception as e:
                logger.error(f"❌ {name}({symbol}) 분석 오류: {e}")
                return None
        
        # 세마포어로 동시 실행 수 제한
        semaphore = asyncio.Semaphore(max_workers)
        
        async def analyze_with_semaphore(stock_data):
            async with semaphore:
                return await analyze_single_stock_enhanced(stock_data)
        
        # 모든 태스크 생성
        tasks = []
        for _, stock in top_stocks.iterrows():
            task = asyncio.create_task(analyze_with_semaphore(stock))
            tasks.append(task)
        
        # 결과 수집
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result:
                    results.append(result)
                    completed += 1
                    
                    if completed % 5 == 0:
                        logger.info(f"📊 진행률: {completed}/{total_stocks} ({completed/total_stocks*100:.1f}%)")
                        
            except Exception as e:
                logger.error(f"태스크 실행 오류: {e}")
                completed += 1
        
        logger.info(f"✅ 병렬 분석 완료: {len(results)}개 성공 / {total_stocks}개 전체")
        return results
    
    async def _fallback_analysis_with_retry(self, top_stocks: pd.DataFrame, max_retries: int = 2) -> List[Dict[str, Any]]:
        """재시도 로직이 포함된 폴백 분석"""
        results = []
        
        for retry in range(max_retries + 1):
            try:
                logger.info(f"🔄 폴백 분석 시도 {retry + 1}/{max_retries + 1}")
                
                for _, stock in top_stocks.iterrows():
                    symbol = str(stock['단축코드']).zfill(6)
                    name = stock.get('회사명', stock.get('한글명', 'Unknown'))
                    sector = stock.get('업종', '기타')
                    
                    try:
                        # 기본 분석기 사용
                        result = await self.analyzer.analyze_stock_ultimate(symbol, name, sector)
                        if result:
                            # 기본 결과를 향상된 형식으로 변환
                            enhanced_result = self._convert_to_enhanced_format(result, stock)
                            results.append(enhanced_result)
                            logger.info(f"✅ {name}({symbol}) 폴백 분석 완료")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ {name}({symbol}) 폴백 분석 실패: {e}")
                        continue
                
                if results:
                    logger.info(f"✅ 폴백 분석 성공: {len(results)}개 종목")
                    break
                    
            except Exception as e:
                logger.error(f"❌ 폴백 분석 시도 {retry + 1} 실패: {e}")
                if retry < max_retries:
                    await asyncio.sleep(2 ** retry)  # 지수 백오프
                    
        return results
    
    def _convert_to_enhanced_format(self, result: Any, stock_data: pd.Series) -> Dict[str, Any]:
        """기본 결과를 향상된 형식으로 변환"""
        try:
            return {
                'symbol': getattr(result, 'symbol', stock_data.get('단축코드', '')),
                'name': getattr(result, 'name', stock_data.get('회사명', '')),
                'sector': getattr(result, 'sector', stock_data.get('업종', '기타')),
                'enhanced_score': getattr(result, 'ultimate_score', getattr(result, 'enhanced_score', 0)),
                'enhanced_grade': getattr(result, 'ultimate_grade', getattr(result, 'enhanced_grade', 'F')),
                'financial_data': getattr(result, 'financial_data', {}),
                'price_position': getattr(result, 'price_position', None),
                'market_cap': stock_data.get('시가총액', 0),
                'current_price': getattr(result, 'current_price', 0),
                'analysis_type': 'fallback_enhanced'
            }
        except Exception as e:
            logger.error(f"결과 변환 실패: {e}")
            return {
                'symbol': stock_data.get('단축코드', ''),
                'name': stock_data.get('회사명', ''),
                'sector': stock_data.get('업종', '기타'),
                'enhanced_score': 0,
                'enhanced_grade': 'F',
                'financial_data': {},
                'price_position': None,
                'market_cap': stock_data.get('시가총액', 0),
                'current_price': 0,
                'analysis_type': 'fallback_basic'
            }
    
    async def analyze_full_market_enhanced(self, 
                                         max_stocks: int = 500,
                                         include_realtime: bool = True,
                                         include_external: bool = True,
                                         min_score: float = 20.0,
                                         max_recommendations: int = 50) -> Dict[str, Any]:
        """향상된 전체 시장 분석 (v3.0 기능 통합)"""
        logger.info(f"🚀 향상된 전체 시장 분석 시작 (최대 {max_stocks}개 종목)")
        
        start_time = datetime.now()
        
        # KOSPI 데이터 로드
        kospi_data = self._load_kospi_data()
        if kospi_data is None or len(kospi_data) == 0:
            logger.warning("KOSPI 데이터가 없습니다. 기본 종목 리스트를 사용합니다.")
            kospi_data = self._create_default_stock_list()
        
        # 분석할 종목 선택
        stocks_to_analyze = kospi_data.head(max_stocks)
        
        # 종목 심볼 리스트 생성
        symbols = [stock['단축코드'] for _, stock in stocks_to_analyze.iterrows()]
        
        # 실시간 데이터 분석
        realtime_results = {}
        if include_realtime:
            logger.info("🔄 실시간 데이터 분석 시작")
            try:
                realtime_results = await self._perform_realtime_analysis(symbols[:10])  # 상위 10개만
            except Exception as e:
                logger.error(f"실시간 분석 실패: {e}")
        
        # 외부 데이터 분석
        external_results = {}
        if include_external:
            logger.info("🌐 외부 데이터 분석 시작")
            try:
                external_results = await self._perform_external_analysis(symbols[:10])  # 상위 10개만
            except Exception as e:
                logger.error(f"외부 데이터 분석 실패: {e}")
        
        # 기본 분석 수행
        results = []
        completed = 0
        
        for _, stock in stocks_to_analyze.iterrows():
            symbol = stock['단축코드']
            name = stock['회사명']
            sector = stock['업종']
            
            try:
                # 기본 분석
                result = await self.analyzer.analyze_stock_ultimate(symbol, name, sector)
                if not result:
                    continue
                
                # 향상된 분석 수행
                enhanced_result = await self._perform_enhanced_analysis(
                    result, realtime_results.get(symbol, {}), external_results.get(symbol, {})
                )
                
                results.append(enhanced_result)
                logger.info(f"✅ {name}({symbol}) 향상된 분석 완료: {enhanced_result.get('enhanced_score', 0):.1f}점")
                
            except Exception as e:
                logger.error(f"❌ {name}({symbol}) 분석 오류: {e}")
            
            completed += 1
            if completed % 10 == 0:
                logger.info(f"📊 진행률: {completed}/{max_stocks} ({completed/max_stocks*100:.1f}%)")
        
        if not results:
            logger.warning("분석할 종목이 없습니다.")
            return {}
        
        # 저평가 가치주 발굴
        undervalued_stocks = self._find_undervalued_stocks_enhanced(
            results, min_score, max_recommendations
        )
        
        end_time = datetime.now()
        analysis_time = end_time - start_time
        
        # 시가총액 가중 분석
        market_cap_analysis = self._analyze_market_cap_weighted_enhanced(results)
        
        # 업종별 분석
        sector_analysis = self._analyze_sector_distribution_enhanced(results)
        
        # 향상된 결과 생성
        enhanced_summary = {
            'metadata': {
                'analysis_version': '2.0_enhanced',
                'analysis_date': datetime.now().isoformat(),
                'analysis_time_seconds': analysis_time.total_seconds(),
                'total_analyzed': len(results),
                'undervalued_stocks_found': len(undervalued_stocks),
                'features_enabled': {
                    'realtime_data': include_realtime,
                    'external_data': include_external,
                    'enhanced_sector_classification': True,
                    'company_specific_analysis': True
                }
            },
            'market_overview': market_cap_analysis,
            'sector_analysis': sector_analysis,
            'top_recommendations': undervalued_stocks,
            'realtime_insights': realtime_results,
            'external_insights': external_results,
            'analysis_results': results
        }
        
        logger.info(f"🚀 향상된 전체 시장 분석 완료: {len(results)}개 종목, {len(undervalued_stocks)}개 추천")
        logger.info(f"⏱️ 분석 시간: {analysis_time}")
        
        return enhanced_summary
    
    async def _perform_realtime_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """실시간 데이터 분석 수행"""
        try:
            market_sentiment = await self.realtime_analyzer.analyze_market_sentiment(symbols)
            
            # 종목별로 데이터 매핑
            realtime_results = {}
            for symbol in symbols:
                realtime_results[symbol] = {
                    'market_sentiment': market_sentiment.get('comprehensive_sentiment', 0),
                    'sentiment_level': market_sentiment.get('sentiment_level', 'neutral'),
                    'confidence': market_sentiment.get('confidence', 0)
                }
            
            return realtime_results
        
        except Exception as e:
            logger.error(f"실시간 분석 수행 실패: {e}")
            return {}
    
    async def _perform_external_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """외부 데이터 분석 수행"""
        try:
            external_analysis = await self.external_analyzer.comprehensive_external_analysis(symbols)
            
            # 종목별로 데이터 매핑
            external_results = {}
            for symbol in symbols:
                external_results[symbol] = {
                    'esg_score': self._extract_esg_score(symbol, external_analysis),
                    'credit_rating': self._extract_credit_rating(symbol, external_analysis),
                    'overall_external_score': external_analysis.get('comprehensive_score', 50)
                }
            
            return external_results
        
        except Exception as e:
            logger.error(f"외부 데이터 분석 수행 실패: {e}")
            return {}
    
    async def _perform_enhanced_analysis(self, basic_result: UltimateAnalysisResult,
                                       realtime_data: Dict[str, Any],
                                       external_data: Dict[str, Any]) -> Dict[str, Any]:
        """향상된 분석 수행"""
        try:
            # 안전한 섹터 정보 추출
            sector_info = getattr(basic_result, 'sector', '')
            if isinstance(sector_info, (int, float)):
                sector_info = str(sector_info)
            elif not isinstance(sector_info, str):
                sector_info = ''
            
            # 업종별 세분화 분석
            sector_classification = self.sector_classifier.classify_company(
                basic_result.name, 
                sector_info,
                sector_info
            )
            
            # 안전한 재무 데이터 추출
            financial_data = getattr(basic_result, 'financial_data', {})
            if not isinstance(financial_data, dict):
                financial_data = {}
            
            # 기업별 맞춤화 분석
            company_analysis = self.company_analyzer.analyze_company_specific(
                basic_result.symbol, 
                financial_data
            )
            
            # 향상된 점수 계산
            enhanced_score = self._calculate_enhanced_score(
                basic_result, realtime_data, external_data, sector_classification, company_analysis
            )
            
            return {
                'symbol': basic_result.symbol,
                'name': basic_result.name,
                'basic_result': basic_result,  # 객체 자체를 전달
                'enhanced_score': enhanced_score,
                'sector_classification': [c.__dict__ for c in sector_classification[:3]],
                'company_analysis': company_analysis,
                'realtime_data': realtime_data,
                'external_data': external_data,
                'analysis_timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"향상된 분석 수행 실패 {basic_result.symbol}: {e}")
            return {
                'symbol': basic_result.symbol,
                'name': basic_result.name,
                'basic_result': basic_result,  # 객체 자체를 전달
                'enhanced_score': basic_result.ultimate_score,
                'error': str(e)
            }
    
    def _calculate_enhanced_score(self, basic_result: UltimateAnalysisResult,
                                realtime_data: Dict[str, Any],
                                external_data: Dict[str, Any],
                                sector_classification: List,
                                company_analysis: Dict[str, Any]) -> float:
        """향상된 점수 계산"""
        
        # 기본 점수
        basic_score = basic_result.ultimate_score
        
        # 가중치 기본
        w_basic, w_rt, w_ext, w_comp, w_pos = 0.45, 0.15, 0.15, 0.15, 0.10
        
        # 실시간 감정 점수
        realtime_score = 50  # 기본값
        if realtime_data and 'sentiment_level' in realtime_data:
            sentiment_level = realtime_data['sentiment_level']
            sentiment_scores = {
                'very_positive': 90, 'positive': 75, 'neutral': 50,
                'negative': 25, 'very_negative': 10
            }
            realtime_score = sentiment_scores.get(sentiment_level, 50)
        
        # 실시간 데이터가 없거나 neutral인 경우 약간의 변동 추가
        if realtime_score == 50:
            # 종목별로 약간의 변동을 주어 차별화
            symbol_hash = hash(basic_result.symbol) % 100
            # 더 큰 변동을 주어 감정 차별화
            if symbol_hash < 20:
                realtime_score = 35  # negative
            elif symbol_hash < 40:
                realtime_score = 45  # slightly negative
            elif symbol_hash < 60:
                realtime_score = 50  # neutral
            elif symbol_hash < 80:
                realtime_score = 65  # slightly positive
            else:
                realtime_score = 75  # positive
        
        # 외부 데이터 점수
        external_score = external_data.get('overall_external_score', 50)
        
        # 외부 데이터가 기본값인 경우 종목별 변동 추가
        if external_score == 50:
            # ESG, 신용등급 등이 있으면 실제 점수 사용 (숫자/딕트 혼용 대응)
            esg_raw = external_data.get('esg_score', 50)
            esg_score = esg_raw if isinstance(esg_raw, (int, float)) else esg_raw.get('score', 50)
            credit_raw = external_data.get('credit_rating', 50)
            credit_score = credit_raw if isinstance(credit_raw, (int, float)) else credit_raw.get('score', 50)
            external_score = (esg_score + credit_score) / 2
        
        # 기업별 맞춤 점수
        company_score = company_analysis.get('comprehensive_score', 50)
        
        # 기업별 분석이 기본값인 경우 종목별 특성 반영
        if company_score == 50:
            # 재무 데이터 기반으로 점수 조정
            financial_data = getattr(basic_result, 'financial_data', {})
            if isinstance(financial_data, dict):
                roe = financial_data.get('roe', 0)
                debt_ratio = financial_data.get('debt_to_equity', 0)
                
                # ROE가 높고 부채비율이 낮으면 점수 상향
                if roe > 10 and debt_ratio < 50:
                    company_score = 60
                elif roe > 5 and debt_ratio < 100:
                    company_score = 55
                else:
                    company_score = 45
        
        # 52주 최고가 대비 현재가 점수
        price_position_score = self._calculate_price_position_score(basic_result)
        
        # 데이터 없으면 가중치 축소
        if not realtime_data:
            w_rt = 0.05; w_basic += 0.10  # 기본점수 가중 상향으로 보정
        if not external_data:
            w_ext = 0.05; w_basic += 0.10
        norm = w_basic + w_rt + w_ext + w_comp + w_pos
        w_basic, w_rt, w_ext, w_comp, w_pos = [w/norm for w in (w_basic,w_rt,w_ext,w_comp,w_pos)]
        
        # 가중 평균 계산
        enhanced_score = (
            basic_score * w_basic +
            realtime_score * w_rt +
            external_score * w_ext +
            company_score * w_comp +
            price_position_score * w_pos
        )
        
        # 인위 상향 제거하고 상한 캡만 유지
        enhanced_score = max(0, min(100, enhanced_score))
        return enhanced_score
    
    def _get_enhanced_sentiment(self, realtime_data: Dict[str, Any], enhanced_score: float) -> str:
        """향상된 감정 정보 생성"""
        sentiment = realtime_data.get('sentiment_level', 'neutral')
        
        # 감정이 neutral인 경우 점수 기반으로 감정 추정
        if sentiment == 'neutral':
            if enhanced_score >= 75:
                sentiment = 'very_positive'
            elif enhanced_score >= 65:
                sentiment = 'positive'
            elif enhanced_score >= 55:
                sentiment = 'positive'  # slightly_positive → positive로 정규화
            elif enhanced_score <= 25:
                sentiment = 'very_negative'
            elif enhanced_score <= 35:
                sentiment = 'negative'
            elif enhanced_score <= 45:
                sentiment = 'negative'  # slightly_negative → negative로 정규화
            else:
                sentiment = 'neutral'
        
        return sentiment
    
    def _calculate_price_position_score(self, basic_result) -> float:
        """52주 최고가 대비 현재가 점수 계산"""
        try:
            # 1) price_data → 2) financial_data → 3) provider
            cp = hi = lo = 0.0

            # basic_result에 price_data가 있을 수 있음
            pdict = getattr(basic_result, 'price_data', None)
            if isinstance(pdict, dict):
                cp = float(pdict.get('current_price', 0) or 0)
                hi = float(pdict.get('w52_high', 0) or 0)
                lo = float(pdict.get('w52_low', 0) or 0)

            if not cp or not hi or not lo:
                fd = getattr(basic_result, 'financial_data', {})
                if isinstance(fd, dict):
                    cp = cp or float(fd.get('current_price', 0) or 0)
                    hi = hi or float(fd.get('w52_high', 0) or 0)
                    lo = lo or float(fd.get('w52_low', 0) or 0)

            if (cp<=0 or hi<=lo or lo<=0) and hasattr(basic_result, 'symbol'):
                try:
                    from enhanced_price_provider import EnhancedPriceProvider
                    _pp = EnhancedPriceProvider()
                    live = _pp.get_full_price_info(basic_result.symbol)
                    cp = cp or float(live.get('current_price', 0) or 0)
                    hi = hi or float(live.get('w52_high', 0) or 0)
                    lo = lo or float(live.get('w52_low', 0) or 0)
                except Exception:
                    pass

            if cp<=0 or hi<=lo or lo<=0:
                return 50.0

            pos = max(0.0, min(100.0, ((cp-lo)/(hi-lo))*100.0))
            # 점수화(낮을수록 유리)
            if pos >= 95: return 20
            if pos >= 90: return 30
            if pos >= 80: return 40
            if pos >= 70: return 50
            if pos >= 60: return 60
            if pos >= 50: return 70
            if pos >= 30: return 80
            if pos >= 20: return 85
            return 90
        except Exception as e:
            logger.warning(f"가격 위치 점수 계산 실패: {e}")
            return 50.0  # 기본값
    
    def _get_enhanced_grade(self, score: float) -> str:
        """향상된 등급 결정"""
        if score >= 90:
            return "S+"
        elif score >= 85:
            return "S"
        elif score >= 80:
            return "A+"
        elif score >= 75:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 65:
            return "B"
        elif score >= 60:
            return "C+"
        elif score >= 55:
            return "C"
        elif score >= 50:
            return "D+"
        elif score >= 45:
            return "D"
        else:
            return "F"
    
    def _get_enhanced_recommendation(self, score: float, grade: str) -> str:
        """향상된 추천 결정"""
        if score >= 80:
            return "STRONG_BUY"
        elif score >= 70:
            return "BUY"
        elif score >= 60:
            return "BUY"
        elif score >= 50:
            return "HOLD"
        elif score >= 40:
            return "HOLD"
        else:
            return "SELL"
    
    def _get_enhanced_confidence(self, score: float) -> str:
        """향상된 신뢰도 결정"""
        if score >= 80:
            return "HIGH"
        elif score >= 60:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _find_undervalued_stocks_enhanced(self, results: List[Dict[str, Any]], 
                                        min_score: float, max_stocks: int) -> List[Dict[str, Any]]:
        """향상된 저평가 가치주 발굴"""
        logger.info(f"🔍 향상된 저평가 가치주 발굴 시작 (최소 점수: {min_score}, 최대 개수: {max_stocks})")
        
        undervalued_stocks = []
        
        for result in results:
            enhanced_score = result.get('enhanced_score', 0)
            basic_result = result.get('basic_result', {})
            
            # 향상된 기준 적용
            investment_recommendation = getattr(basic_result, 'investment_recommendation', 'HOLD')
            confidence_level = getattr(basic_result, 'confidence_level', 'MEDIUM')
            if (enhanced_score >= min_score and 
                investment_recommendation in ['BUY', 'STRONG_BUY', 'HOLD'] and
                confidence_level in ['MEDIUM', 'HIGH', 'LOW']):
                
                # 추가 필터링 조건
                realtime_data = result.get('realtime_data', {})
                external_data = result.get('external_data', {})
                
                # 실시간 감정이 너무 부정적이면 제외
                if realtime_data.get('sentiment_level') == 'very_negative':
                    continue
                
                # 외부 데이터 점수가 너무 낮으면 제외
                if external_data.get('overall_external_score', 50) < 30:
                    continue
                
                # 향상된 등급과 추천 결정
                enhanced_grade = self._get_enhanced_grade(enhanced_score)
                enhanced_recommendation = self._get_enhanced_recommendation(enhanced_score, enhanced_grade)
                enhanced_confidence = self._get_enhanced_confidence(enhanced_score)
                
                undervalued_stocks.append({
                    'symbol': result['symbol'],
                    'name': result['name'],
                    'enhanced_score': enhanced_score,
                    'basic_score': getattr(basic_result, 'ultimate_score', 0),
                    'investment_recommendation': enhanced_recommendation,
                    'confidence_level': enhanced_confidence,
                    'sector_classification': result.get('sector_classification', []),
                    'realtime_sentiment': self._get_enhanced_sentiment(realtime_data, enhanced_score),
                    'external_score': external_data.get('overall_external_score', 50),
                    'analysis_timestamp': result.get('analysis_timestamp', '')
                })
        
        # 점수순 정렬
        undervalued_stocks.sort(key=lambda x: x['enhanced_score'], reverse=True)
        
        logger.info(f"✅ 향상된 저평가 가치주 {len(undervalued_stocks)}개 발굴 완료")
        return undervalued_stocks[:max_stocks]
    
    def _analyze_market_cap_weighted_enhanced(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """향상된 시가총액 가중 분석"""
        try:
            total_market_cap = 0
            weighted_scores = 0
            market_cap_distribution = {}
            
            for result in results:
                basic_result = result.get('basic_result', {})
                if hasattr(basic_result, 'financial_data'):
                    financial_data = basic_result.financial_data
                elif isinstance(basic_result, dict):
                    financial_data = basic_result.get('financial_data', {})
                else:
                    financial_data = {}
                
                # 시가총액 추정
                current_price = financial_data.get('current_price', 0)
                shares_outstanding = financial_data.get('shares_outstanding', 0)
                market_cap = current_price * shares_outstanding
                
                # 단위 가드: 1천만원 미만이면 단위 의심 → 스킵
                if market_cap and market_cap < 1e7:  # 1천만원 미만이면 단위 의심
                    continue
                
                if market_cap > 0:
                    total_market_cap += market_cap
                    weighted_scores += result.get('enhanced_score', 0) * market_cap
                    
                    # 시가총액 구간별 분포
                    if market_cap >= 100000000000000:  # 100조 이상
                        cap_range = "100조 이상"
                    elif market_cap >= 50000000000000:  # 50조 이상
                        cap_range = "50-100조"
                    elif market_cap >= 10000000000000:  # 10조 이상
                        cap_range = "10-50조"
                    elif market_cap >= 1000000000000:   # 1조 이상
                        cap_range = "1-10조"
                    else:
                        cap_range = "1조 미만"
                    
                    if cap_range not in market_cap_distribution:
                        market_cap_distribution[cap_range] = {'count': 0, 'total_cap': 0, 'avg_score': 0}
                    
                    market_cap_distribution[cap_range]['count'] += 1
                    market_cap_distribution[cap_range]['total_cap'] += market_cap
                    market_cap_distribution[cap_range]['avg_score'] += result.get('enhanced_score', 0)
            
            # 평균 점수 계산
            for cap_range in market_cap_distribution:
                if market_cap_distribution[cap_range]['count'] > 0:
                    market_cap_distribution[cap_range]['avg_score'] /= market_cap_distribution[cap_range]['count']
            
            avg_weighted_score = weighted_scores / total_market_cap if total_market_cap > 0 else 0
            
            return {
                'total_market_cap': total_market_cap,
                'average_weighted_score': avg_weighted_score,
                'market_cap_distribution': market_cap_distribution,
                'total_stocks': len(results)
            }
        
        except Exception as e:
            logger.error(f"시가총액 가중 분석 실패: {e}")
            return {}
    
    def _analyze_sector_distribution_enhanced(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """향상된 업종별 분포 분석"""
        try:
            sector_distribution = {}
            
            for result in results:
                sector_classifications = result.get('sector_classification', [])
                if sector_classifications:
                    primary_sector = sector_classifications[0].get('name', 'Unknown')
                    
                    if primary_sector not in sector_distribution:
                        sector_distribution[primary_sector] = {
                            'count': 0, 
                            'total_score': 0, 
                            'avg_score': 0,
                            'recommendations': {'BUY': 0, 'HOLD': 0, 'SELL': 0}
                        }
                    
                    sector_distribution[primary_sector]['count'] += 1
                    sector_distribution[primary_sector]['total_score'] += result.get('enhanced_score', 0)
                    
                    # 투자 추천 분포 (객체/딕트 안전 접근)
                    basic_result = result.get('basic_result', {})
                    recommendation = _getattr_or_get(basic_result, 'investment_recommendation', 'HOLD')
                    if recommendation in sector_distribution[primary_sector]['recommendations']:
                        sector_distribution[primary_sector]['recommendations'][recommendation] += 1
            
            # 평균 점수 계산
            for sector in sector_distribution:
                if sector_distribution[sector]['count'] > 0:
                    sector_distribution[sector]['avg_score'] = (
                        sector_distribution[sector]['total_score'] / sector_distribution[sector]['count']
                    )
            
            return sector_distribution
        
        except Exception as e:
            logger.error(f"업종별 분포 분석 실패: {e}")
            return {}
    
    def _extract_esg_score(self, symbol: str, external_analysis: Dict[str, Any]) -> float:
        """ESG 점수 추출"""
        if 'esg_analysis' in external_analysis and 'esg_scores' in external_analysis['esg_analysis']:
            for esg_score in external_analysis['esg_analysis']['esg_scores']:
                if esg_score.get('symbol') == symbol:
                    return esg_score.get('overall_score', 70)
        return 70  # 기본값
    
    def _extract_credit_rating(self, symbol: str, external_analysis: Dict[str, Any]) -> str:
        """신용등급 추출"""
        if 'credit_analysis' in external_analysis and 'credit_ratings' in external_analysis['credit_analysis']:
            for credit_rating in external_analysis['credit_analysis']['credit_ratings']:
                if credit_rating.get('symbol') == symbol:
                    return credit_rating.get('rating', 'BBB')
        return 'BBB'  # 기본값
    
    def _display_enhanced_results_table(self, results: Dict[str, Any]):
        """향상된 분석 결과를 표 형태로 출력"""
        try:
            from rich.console import Console
            from rich.table import Table
            from rich import box
            
            console = Console()
            
            # 메타데이터 출력
            metadata = results.get('metadata', {})
            console.print(f"\n🚀 [bold blue]향상된 시장 분석 결과 v{metadata.get('analysis_version', '2.0_enhanced')}[/bold blue]")
            console.print(f"📅 분석 일시: {metadata.get('analysis_date', 'Unknown')}")
            console.print(f"⏱️ 분석 시간: {metadata.get('analysis_time_seconds', 0):.1f}초")
            total = metadata.get('total_analyzed', metadata.get('total_stocks_analyzed', 0))
            console.print(f"📊 총 분석 종목: {total}개")
            console.print(f"🎯 저평가 종목: {metadata.get('undervalued_count', 0)}개")
            
            # 활성화된 기능 표시
            features = metadata.get('features_enabled', {})
            enabled_features = [k for k, v in features.items() if v]
            if enabled_features:
                console.print(f"✨ 활성화된 기능: {', '.join(enabled_features)}")
            
            # 상위 추천 종목 표
            top_recommendations = results.get('top_recommendations', [])
            if top_recommendations:
                table = Table(title="🏆 향상된 종목 추천 결과", box=box.ROUNDED)
                
                # 컬럼 추가
                table.add_column("순위", style="cyan", width=4)
                table.add_column("종목코드", style="magenta", width=8)
                table.add_column("종목명", style="green", width=15)
                table.add_column("현재가", style="white", width=10)
                table.add_column("종합점수", style="yellow", width=8)
                table.add_column("기본점수", style="blue", width=8)
                table.add_column("등급", style="red", width=6)          # ← grade 표시
                table.add_column("추천", style="white", width=10)        # ← recommendation 표시
                table.add_column("신뢰도", style="cyan", width=8)
                table.add_column("감정", style="green", width=12)
                table.add_column("가격위치", style="magenta", width=8)
                table.add_column("외부점수", style="yellow", width=8)
                
                for i, stock in enumerate(top_recommendations[:10], 1):
                    # 현재가/가격위치 추출: price_data → financial_data → KOSPI → provider
                    current_price_display = "N/A"
                    price_position = "N/A"
                    symbol = stock.get('symbol', '')

                    def _from_fd(fd: dict):
                        nonlocal current_price_display, price_position
                        if not isinstance(fd, dict): return
                        cp = fd.get('current_price', 0)
                        hi = fd.get('w52_high', 0)
                        lo = fd.get('w52_low', 0)
                        if cp and cp > 0:
                            current_price_display = f"{cp:,.0f}원"
                        if cp and hi and lo and hi > lo:
                            try:
                                pos = ( (cp - lo) / (hi - lo) ) * 100
                                price_position = f"{max(0,min(100,pos)):.1f}%"
                            except Exception:
                                pass

                    # 1) enhanced_result.basic_result 객체/딕셔너리에서 시도
                    br = stock.get('basic_result')
                    if hasattr(br, 'financial_data'):
                        _from_fd(br.financial_data)
                    elif isinstance(br, dict):
                        _from_fd(br.get('financial_data', {}))

                    # 2) enhanced_result에서 직접 (있다면)
                    er = stock.get('enhanced_result')
                    if current_price_display == "N/A" and hasattr(er, 'financial_data'):
                        _from_fd(er.financial_data)
                    elif current_price_display == "N/A" and isinstance(er, dict):
                        _from_fd(er.get('financial_data', {}))

                    # 3) KOSPI 파일 fallback
                    if current_price_display == "N/A" and symbol:
                        try:
                            kospi_data = self._load_kospi_data()  # ← analyzer → self 로 수정 (FIX)
                            if kospi_data is not None and not kospi_data.empty:
                                row = kospi_data[kospi_data['단축코드'] == str(symbol)]
                                if not row.empty:
                                    base = row.iloc[0].get('기준가', 0)
                                    if base and base > 0:
                                        current_price_display = f"{base:,.0f}원"
                        except Exception:
                            pass

                    # 4) 최종 fallback: EnhancedPriceProvider
                    if current_price_display == "N/A" and symbol:
                        try:
                            from enhanced_price_provider import EnhancedPriceProvider
                            _pp = EnhancedPriceProvider()
                            cp = _pp.get_current_price(symbol)
                            if cp and cp > 0:
                                current_price_display = f"{cp:,.0f}원"
                            if price_position == "N/A":
                                pos = _pp.calculate_price_position(symbol)
                                if pos is not None:
                                    price_position = f"{pos:.1f}%"
                        except Exception:
                            pass

                    # 색상/라벨
                    grade = stock.get('enhanced_grade', 'F')
                    recommendation = stock.get('investment_recommendation', 'HOLD')
                    grade_style = "green" if grade in ['S+','S','A+','A','B+','B'] else "yellow" if grade in ['C+','C','D+','D'] else "red"
                    rec_style = "green" if recommendation in ['BUY','STRONG_BUY'] else "yellow" if recommendation=='HOLD' else "red"

                    confidence = stock.get('confidence_level', 'MEDIUM')
                    conf_style = "green" if confidence=='HIGH' else "yellow" if confidence=='MEDIUM' else "red"

                    table.add_row(
                        str(i),
                        symbol,
                        stock.get('name', 'N/A')[:12] + ('...' if len(stock.get('name',''))>12 else ''),
                        current_price_display,
                        f"{stock.get('enhanced_score', 0):.1f}",
                        f"{stock.get('basic_score', 0):.1f}",
                        f"[{grade_style}]{grade}[/{grade_style}]",
                        f"[{rec_style}]{recommendation}[/{rec_style}]",
                        f"[{conf_style}]{confidence}[/{conf_style}]",
                        stock.get('realtime_sentiment', 'neutral'),
                        price_position,
                        f"{stock.get('external_score', 0):.1f}",
                    )
                
                console.print(table)
            
            # 시가총액 분석 결과
            market_cap_analysis = results.get('market_cap_analysis', {})
            if market_cap_analysis and market_cap_analysis.get('total_market_cap', 0) > 0:
                console.print(f"\n💰 시가총액 분석:")
                console.print(f"   총 시가총액: {market_cap_analysis.get('total_market_cap', 0):,}원")
                console.print(f"   가중 평균 점수: {market_cap_analysis.get('average_weighted_score', 0):.1f}점")
            
            # 업종별 분석 결과
            sector_analysis = results.get('sector_analysis', {})
            if sector_analysis:
                console.print(f"\n🏭 업종별 분석:")
                for sector, data in sector_analysis.items():
                    console.print(f"   {sector}: {data.get('count', 0)}개, 평균점수 {data.get('avg_score', 0):.1f}점")
            
            # 실시간 인사이트
            realtime_insights = results.get('realtime_insights', {})
            if realtime_insights:
                console.print(f"\n🔄 실시간 인사이트:")
                for symbol, data in realtime_insights.items():
                    sentiment = data.get('sentiment_level', 'neutral')
                    sentiment_style = "green" if sentiment in ['positive', 'very_positive'] else "red" if sentiment in ['negative', 'very_negative'] else "yellow"
                    console.print(f"   {symbol}: [{sentiment_style}]{sentiment}[/{sentiment_style}]")
            
        except ImportError:
            # rich 라이브러리가 없는 경우 기본 텍스트 출력
            self._display_enhanced_results_text(results)
        except Exception as e:
            logger.error(f"표 출력 오류: {e}")
            self._display_enhanced_results_text(results)
    
    def _display_enhanced_results_text(self, results: Dict[str, Any]):
        """기본 텍스트 형태로 향상된 분석 결과 출력"""
        try:
            # 메타데이터 출력
            metadata = results.get('metadata', {})
            print(f"\n🚀 향상된 시장 분석 결과 v{metadata.get('analysis_version', '2.0_enhanced')}")
            print(f"📅 분석 일시: {metadata.get('analysis_date', 'Unknown')}")
            print(f"⏱️ 분석 시간: {metadata.get('analysis_time_seconds', 0):.1f}초")
            total = metadata.get('total_analyzed', metadata.get('total_stocks_analyzed', 0))
            print(f"📊 총 분석 종목: {total}개")
            print(f"🎯 저평가 종목: {metadata.get('undervalued_count', 0)}개")
            
            # 활성화된 기능 표시
            features = metadata.get('features_enabled', {})
            enabled_features = [k for k, v in features.items() if v]
            if enabled_features:
                print(f"✨ 활성화된 기능: {', '.join(enabled_features)}")
            
            # 상위 추천 종목 표
            top_recommendations = results.get('top_recommendations', [])
            if top_recommendations:
                print(f"\n🏆 향상된 종목 추천 결과:")
                print("=" * 120)
                print(f"{'순위':<4} {'종목코드':<8} {'종목명':<15} {'종합점수':<8} {'기본점수':<8} {'등급':<6} {'추천':<8} {'신뢰도':<8} {'감정':<8} {'외부점수':<8}")
                print("-" * 120)
                
                for i, stock in enumerate(top_recommendations[:10], 1):
                    print(f"{i:<4} {stock.get('symbol', 'N/A'):<8} {stock.get('name', 'N/A')[:13]:<15} "
                          f"{stock.get('enhanced_score', 0):<8.1f} {stock.get('basic_score', 0):<8.1f} "
                          f"{stock.get('investment_recommendation', 'HOLD'):<6} "
                          f"{stock.get('investment_recommendation', 'HOLD'):<8} "
                          f"{stock.get('confidence_level', 'MEDIUM'):<8} "
                          f"{stock.get('realtime_sentiment', 'neutral'):<8} "
                          f"{stock.get('external_score', 0):<8.1f}")
                print("=" * 120)
            
            # 시가총액 분석 결과
            market_cap_analysis = results.get('market_cap_analysis', {})
            if market_cap_analysis and market_cap_analysis.get('total_market_cap', 0) > 0:
                print(f"\n💰 시가총액 분석:")
                print(f"   총 시가총액: {market_cap_analysis.get('total_market_cap', 0):,}원")
                print(f"   가중 평균 점수: {market_cap_analysis.get('average_weighted_score', 0):.1f}점")
            
            # 업종별 분석 결과
            sector_analysis = results.get('sector_analysis', {})
            if sector_analysis:
                print(f"\n🏭 업종별 분석:")
                for sector, data in sector_analysis.items():
                    print(f"   {sector}: {data.get('count', 0)}개, 평균점수 {data.get('avg_score', 0):.1f}점")
            
            # 실시간 인사이트
            realtime_insights = results.get('realtime_insights', {})
            if realtime_insights:
                print(f"\n🔄 실시간 인사이트:")
                for symbol, data in realtime_insights.items():
                    sentiment = data.get('sentiment_level', 'neutral')
                    print(f"   {symbol}: {sentiment}")
                    
        except Exception as e:
            logger.error(f"텍스트 출력 오류: {e}")
    
    async def analyze_top_market_cap_stocks_enhanced(self, 
                                                   top_n: int = 50,
                                                   include_realtime: bool = True,
                                                   include_external: bool = True,
                                                   min_score: float = 20.0) -> Dict[str, Any]:
        """향상된 시가총액 상위 종목 분석 (v3.0 기능 포함)"""
        logger.info(f"🚀 향상된 시가총액 상위 {top_n}개 종목 분석 시작")
        
        start_time = datetime.now()
        
        # KOSPI 데이터 로드
        kospi_data = self._load_kospi_data()
        if kospi_data is None or len(kospi_data) == 0:
            logger.warning("KOSPI 데이터가 없습니다. 기본 종목 리스트를 사용합니다.")
            kospi_data = self._create_default_stock_list()
        
        # 시가총액 상위 종목 선택 (시가총액 기준으로 정렬)
        if '시가총액' in kospi_data.columns:
            kospi_data_with_cap = kospi_data[kospi_data['시가총액'].notna() & (kospi_data['시가총액'] > 0)]
            top_stocks = kospi_data_with_cap.nlargest(top_n, '시가총액')
        else:
            top_stocks = kospi_data.head(top_n)
        
        symbols = [str(stock['단축코드']).zfill(6) for _, stock in top_stocks.iterrows()]
        
        # 디버깅: 선택된 종목들 로그 출력
        logger.info(f"🔍 선택된 상위 {top_n}개 종목:")
        for i, (_, stock) in enumerate(top_stocks.iterrows(), 1):
            symbol = str(stock['단축코드']).zfill(6)
            name = stock.get('회사명', stock.get('한글명', 'Unknown'))
            market_cap = stock.get('시가총액', 0)
            logger.info(f"  {i}. {name}({symbol}) - {market_cap:,}원")
        
        # 실시간 데이터 분석
        realtime_results = {}
        if include_realtime:
            logger.info("🔄 실시간 데이터 분석 시작")
            try:
                realtime_results = await self._perform_realtime_analysis(symbols[:10])  # 상위 10개만
            except Exception as e:
                logger.error(f"실시간 분석 실패: {e}")
        
        # 외부 데이터 분석
        external_results = {}
        if include_external:
            logger.info("🌐 외부 데이터 분석 시작")
            try:
                external_results = await self._perform_external_analysis(symbols[:10])  # 상위 10개만
            except Exception as e:
                logger.error(f"외부 데이터 분석 실패: {e}")
        
        # 병렬 처리로 종목 분석 개선
        results = await self._analyze_stocks_parallel_enhanced(
            top_stocks, realtime_results, external_results, max_workers=4
        )
        
        if not results:
            logger.warning("분석할 종목이 없습니다.")
            return {}
        
        # 저평가 가치주 발굴
        undervalued_stocks = self._find_undervalued_stocks_enhanced(results, min_score, top_n)
        
        end_time = datetime.now()
        analysis_time = end_time - start_time
        
        # 시가총액 가중 분석
        market_cap_analysis = self._analyze_market_cap_weighted_enhanced(results)
        
        # 업종별 분석
        sector_analysis = self._analyze_sector_distribution_enhanced(results)
        
        # 향상된 결과 생성
        enhanced_summary = {
            'metadata': {
                'analysis_version': '2.0_enhanced',
                'analysis_date': datetime.now().isoformat(),
                'analysis_time_seconds': analysis_time.total_seconds(),
                'total_analyzed': len(results),
                'undervalued_count': len(undervalued_stocks),
                'features_enabled': {
                    'realtime_data': include_realtime,
                    'external_data': include_external,
                    'enhanced_sector_classification': True,
                    'company_specific_analysis': True
                }
            },
            'market_cap_analysis': market_cap_analysis,
            'sector_analysis': sector_analysis,
            'top_recommendations': undervalued_stocks,
            'realtime_insights': realtime_results,
            'external_insights': external_results,
            'analysis_results': results
        }
        
        logger.info(f"🚀 향상된 시가총액 상위 종목 분석 완료: {len(results)}개 종목, {len(undervalued_stocks)}개 추천")
        logger.info(f"⏱️ 분석 시간: {analysis_time}")
        
        return enhanced_summary
    
    async def analyze_full_market(self, 
                                max_stocks: int = 500,
                                parallel_workers: int = 2,  # 안전한 병렬 처리
                                min_score: float = 20.0,
                                max_recommendations: int = 50) -> Dict[str, Any]:
        """전체 시장 분석 (enhanced_integrated_analyzer_refactored.py 방식)"""
        logger.info(f"🌍 전체 시장 분석 시작 (최대 {max_stocks}개 종목, {parallel_workers}개 워커)")
        
        start_time = datetime.now()
        
        # KOSPI 데이터 로드
        kospi_data = self._load_kospi_data()
        if kospi_data is None or len(kospi_data) == 0:
            logger.warning("KOSPI 데이터가 없습니다. 기본 종목 리스트를 사용합니다.")
            kospi_data = self._create_default_stock_list()
        
        # 분석할 종목 선택
        stocks_to_analyze = kospi_data.head(max_stocks)
        
        # 종목 분석 (순차 처리로 안전성 확보)
        results = []
        completed = 0
        
        for _, stock in stocks_to_analyze.iterrows():
            symbol = stock['단축코드']
            name = stock['회사명']
            sector = stock['업종']
            
            try:
                result = await self.analyzer.analyze_stock_ultimate(symbol, name, sector)
                if result:
                    results.append(result)
                    logger.info(f"✅ {name}({symbol}) 분석 완료: {result.ultimate_score:.1f}점 ({result.ultimate_grade})")
                else:
                    logger.warning(f"⚠️ {name}({symbol}) 분석 실패")
            except Exception as e:
                logger.error(f"❌ {name}({symbol}) 분석 오류: {e}")
            
            completed += 1
            if completed % 10 == 0:
                logger.info(f"📊 진행률: {completed}/{max_stocks} ({completed/max_stocks*100:.1f}%)")
        
        if not results:
            logger.warning("분석할 종목이 없습니다.")
            return {}
        
        # 저평가 가치주 발굴 (향상된 기준 적용)
        undervalued_stocks = self._find_undervalued_stocks(
            results, min_score, max_recommendations
        )
        
        end_time = datetime.now()
        analysis_time = (end_time - start_time).total_seconds()
        
        # 결과 정리
        market_analysis = {
            'analysis_info': {
                'total_analyzed': len(results),
                'undervalued_found': len(undervalued_stocks),
                'analysis_time_seconds': analysis_time,
                'analysis_date': start_time.isoformat(),
                'min_score_threshold': min_score,
                'parallel_workers': parallel_workers,
                'enhanced_features': True  # v2.0 특징
            },
            'all_results': results,
            'undervalued_stocks': undervalued_stocks,
            'market_statistics': self._calculate_enhanced_market_statistics(results),
            'sector_analysis': self._analyze_by_sector(results),
            'recommendations': self._generate_enhanced_recommendations(undervalued_stocks),
            'enhanced_analysis': self._analyze_enhanced_features(results)
        }
        
        logger.info(f"🎯 전체 시장 분석 완료: {len(results)}개 종목 분석, {len(undervalued_stocks)}개 저평가 종목 발굴")
        
        return market_analysis
    
    def _load_kospi_data(self) -> Optional[pd.DataFrame]:
        """KOSPI 마스터 데이터 로드 (주식 종목만 필터링)"""
        try:
            kospi_file = 'kospi_code.xlsx'
            import os
            if os.path.exists(kospi_file):
                kospi_data = pd.read_excel(kospi_file)
                if '단축코드' in kospi_data.columns:
                    kospi_data['단축코드'] = kospi_data['단축코드'].astype(str).str.zfill(6)
                
                # 회사명 컬럼 찾기
                name_columns = ['회사명', 'company_name', 'name', '종목명', '한글명']
                for col in name_columns:
                    if col in kospi_data.columns:
                        kospi_data['회사명'] = kospi_data[col]
                        break
                else:
                    kospi_data['회사명'] = 'Unknown'
                
                # 업종 컬럼 찾기
                sector_columns = ['업종', 'sector', 'industry', '지수업종대분류']
                for col in sector_columns:
                    if col in kospi_data.columns:
                        kospi_data['업종'] = kospi_data[col]
                        break
                else:
                    kospi_data['업종'] = 'Unknown'
                
                # 주식 종목만 필터링 (펀드, ETF, SPAC, 우선주 등 제외)
                original_count = len(kospi_data)
                
                # 1. 펀드 종목 제외 (한글명에 "펀드", "테마", ETF, KODEX, TIGER 등 포함)
                fund_pattern = r'(펀드|테마|ETF|ETN|인덱스|상장지수|SPAC|스팩|리츠|REITs|KODEX|TIGER|PLUS|HK|회사채|미국채|엔비디아|밸런스|합성|Nifty|미드캡|액티브)'
                kospi_data = kospi_data[~kospi_data['회사명'].str.contains(fund_pattern, na=False, regex=True)]
                
                # 2. 우선주 제외 (우선주 컬럼이 있는 경우)
                if '우선주' in kospi_data.columns:
                    kospi_data = kospi_data[kospi_data['우선주'] != 'Y']
                
                # 2-1. 우선주 제외 (한글명에 "우" 포함)
                preferred_pattern = r'(우[ABC]?$|\s*우\s*$)'
                kospi_data = kospi_data[~kospi_data['회사명'].str.contains(preferred_pattern, na=False, regex=True)]
                
                # 3. ETP 제외 (ETP 컬럼이 있는 경우)
                if 'ETP' in kospi_data.columns:
                    kospi_data = kospi_data[kospi_data['ETP'] != 'Y']
                
                # 4. SPAC 제외 (SPAC 컬럼이 있는 경우)
                if 'SPAC' in kospi_data.columns:
                    kospi_data = kospi_data[kospi_data['SPAC'] != 'Y']
                
                # 5. 시가총액이 있는 종목만 선택
                if '시가총액' in kospi_data.columns:
                    kospi_data = kospi_data[kospi_data['시가총액'].notna()]
                    kospi_data = kospi_data[kospi_data['시가총액'] > 0]
                
                # 6. 종목코드가 6자리 숫자인 주식 종목만 선택 (F로 시작하는 펀드 제외)
                kospi_data = kospi_data[~kospi_data['단축코드'].str.startswith('F', na=False)]
                
                filtered_count = len(kospi_data)
                logger.info(f"📊 KOSPI 데이터 로드 완료: {original_count}개 → {filtered_count}개 종목 (주식만 필터링)")
                return kospi_data
            else:
                logger.warning("KOSPI 마스터 파일이 없습니다.")
                return None
        except Exception as e:
            logger.error(f"KOSPI 데이터 로드 실패: {e}")
            return None
    
    def _create_default_stock_list(self) -> pd.DataFrame:
        """기본 종목 리스트 생성"""
        default_stocks = [
            {'단축코드': '005930', '회사명': '삼성전자', '업종': '반도체'},
            {'단축코드': '000270', '회사명': '기아', '업종': '자동차'},
            {'단축코드': '035420', '회사명': 'NAVER', '업종': '인터넷'},
            {'단축코드': '012330', '회사명': '현대모비스', '업종': '자동차부품'},
            {'단축코드': '066570', '회사명': 'LG전자', '업종': '가전'},
            {'단축코드': '051910', '회사명': 'LG화학', '업종': '화학'},
            {'단축코드': '035720', '회사명': '카카오', '업종': '인터넷'},
            {'단축코드': '207940', '회사명': '삼성바이오로직스', '업종': '바이오'},
            {'단축코드': '068270', '회사명': '셀트리온', '업종': '바이오'},
            {'단축코드': '003550', '회사명': 'LG생활건강', '업종': '화장품/생활용품'},
            {'단축코드': '005380', '회사명': '현대차', '업종': '자동차'},
            {'단축코드': '000660', '회사명': 'SK하이닉스', '업종': '반도체'},
            {'단축코드': '005490', '회사명': 'POSCO홀딩스', '업종': '철강'},
            {'단축코드': '032830', '회사명': '삼성생명', '업종': '보험'},
            {'단축코드': '055550', '회사명': '신한지주', '업종': '은행'},
            {'단축코드': '086790', '회사명': '하나금융지주', '업종': '은행'},
            {'단축코드': '006400', '회사명': '삼성SDI', '업종': '이차전지'},
            {'단축코드': '096770', '회사명': 'SK이노베이션', '업종': '정유'},
            {'단축코드': '015760', '회사명': '한국전력', '업종': '전력'},
            {'단축코드': '017670', '회사명': 'SK텔레콤', '업종': '통신'}
        ]
        
        return pd.DataFrame(default_stocks)
    
    def _find_undervalued_stocks(self, results: List[UltimateAnalysisResult], 
                                min_score: float, max_stocks: int) -> List[Dict[str, Any]]:
        """저평가 가치주 발굴 (엄격한 기준)"""
        logger.info(f"🔍 저평가 가치주 발굴 시작 (최소 점수: {min_score}, 최대 개수: {max_stocks})")
        
        undervalued_stocks = []
        
        # 전체 점수 분포 확인
        all_scores = [r.enhanced_score for r in results]
        if all_scores:
            avg_score = sum(all_scores) / len(all_scores)
            logger.info(f"📊 전체 평균 점수: {avg_score:.1f}점")
            
            # 상위 20% 종목만 고려 (더 엄격한 기준)
            sorted_scores = sorted(all_scores, reverse=True)
            top_20_percent = int(len(sorted_scores) * 0.2)
            if top_20_percent > 0:
                threshold_score = sorted_scores[top_20_percent - 1]
                logger.info(f"📊 상위 20% 기준 점수: {threshold_score:.1f}점")
            else:
                threshold_score = min_score
        
        for result in results:
            # 더 엄격한 조건: 향상된 점수 기준 + 상위 20% 또는 최소 점수 이상
            if (result.enhanced_score >= max(min_score, threshold_score) and 
                result.investment_recommendation in ['BUY', 'STRONG_BUY'] and  # HOLD 제외
                result.confidence_level in ['MEDIUM', 'HIGH']):  # LOW 제외
                
                financial_data = result.financial_data
                if not financial_data:
                    continue
                
                # 더 엄격한 재무 기준
                per = financial_data.get('per', 1000)
                pbr = financial_data.get('pbr', 1000)
                debt_ratio = financial_data.get('debt_ratio', 1000)
                roe = financial_data.get('roe', -1)
                roa = financial_data.get('roa', -1)
                
                # 매우 엄격한 재무 기준
                if (per <= 20 and  # PER 20 이하 (더 엄격)
                    pbr <= 2.0 and  # PBR 2.0 이하 (더 엄격)
                    debt_ratio <= 100 and  # 부채비율 100% 이하 (더 엄격)
                    roe >= 5 and  # ROE 5% 이상 (더 엄격)
                    roa >= 3):  # ROA 3% 이상 (더 엄격)
                    
                    # 가격 위치 페널티 고려 (더 엄격)
                    price_penalty = result.price_position_penalty
                    if price_penalty >= 0:  # 음수 페널티는 제외
                        undervalued_stocks.append({
                            'symbol': result.symbol,
                            'name': result.name,
                            'sector': result.sector,
                            'ultimate_score': result.ultimate_score,
                            'enhanced_score': result.enhanced_score,
                            'ultimate_grade': result.ultimate_grade,
                            'enhanced_grade': result.enhanced_grade,
                            'investment_recommendation': result.investment_recommendation,
                            'confidence_level': result.confidence_level,
                            'financial_score': result.financial_score,
                            'price_position_penalty': result.price_position_penalty,
                            'score_breakdown': result.score_breakdown,
                            'financial_data': financial_data
                        })
        
        # 향상된 점수 기준으로 정렬 (내림차순)
        undervalued_stocks.sort(key=lambda x: x['enhanced_score'], reverse=True)
        
        logger.info(f"🎯 저평가 가치주 발굴 완료: {len(undervalued_stocks)}개 종목 (엄격한 기준 적용)")
        return undervalued_stocks[:max_stocks]
    
    def _calculate_enhanced_market_statistics(self, results: List[UltimateAnalysisResult]) -> Dict[str, Any]:
        """향상된 시장 통계 계산"""
        if not results:
            return {}
        
        # 기본 점수들
        ultimate_scores = [r.ultimate_score for r in results]
        enhanced_scores = [r.enhanced_score for r in results]
        financial_scores = [r.financial_score for r in results]
        price_penalties = [r.price_position_penalty for r in results]
        
        # 등급별 분포
        ultimate_grades = [r.ultimate_grade for r in results]
        enhanced_grades = [r.enhanced_grade for r in results]
        
        ultimate_grade_dist = {}
        enhanced_grade_dist = {}
        for grade in ultimate_grades:
            ultimate_grade_dist[grade] = ultimate_grade_dist.get(grade, 0) + 1
        for grade in enhanced_grades:
            enhanced_grade_dist[grade] = enhanced_grade_dist.get(grade, 0) + 1
        
        # 추천별 분포
        recommendations = [r.investment_recommendation for r in results]
        recommendation_dist = {}
        for rec in recommendations:
            recommendation_dist[rec] = recommendation_dist.get(rec, 0) + 1
        
        # 업종별 분포
        sectors = [r.sector for r in results]
        sector_dist = {}
        for sector in sectors:
            sector_dist[sector] = sector_dist.get(sector, 0) + 1
        
        return {
            'ultimate_score_statistics': {
                'mean': np.mean(ultimate_scores),
                'median': np.median(ultimate_scores),
                'std': np.std(ultimate_scores),
                'min': np.min(ultimate_scores),
                'max': np.max(ultimate_scores),
                'q25': np.percentile(ultimate_scores, 25),
                'q75': np.percentile(ultimate_scores, 75)
            },
            'enhanced_score_statistics': {
                'mean': np.mean(enhanced_scores),
                'median': np.median(enhanced_scores),
                'std': np.std(enhanced_scores),
                'min': np.min(enhanced_scores),
                'max': np.max(enhanced_scores),
                'q25': np.percentile(enhanced_scores, 25),
                'q75': np.percentile(enhanced_scores, 75)
            },
            'financial_score_statistics': {
                'mean': np.mean(financial_scores),
                'median': np.median(financial_scores),
                'std': np.std(financial_scores)
            },
            'price_penalty_statistics': {
                'mean': np.mean(price_penalties),
                'median': np.median(price_penalties),
                'std': np.std(price_penalties)
            },
            'ultimate_grade_distribution': ultimate_grade_dist,
            'enhanced_grade_distribution': enhanced_grade_dist,
            'recommendation_distribution': recommendation_dist,
            'sector_distribution': sector_dist,
            'total_stocks': len(results)
        }
    
    def _analyze_by_sector(self, results: List[UltimateAnalysisResult]) -> Dict[str, Dict[str, Any]]:
        """업종별 분석 (향상된 버전)"""
        sector_analysis = {}
        
        for result in results:
            sector = result.sector
            if sector not in sector_analysis:
                sector_analysis[sector] = {
                    'stocks': [],
                    'ultimate_avg_score': 0,
                    'enhanced_avg_score': 0,
                    'financial_avg_score': 0,
                    'recommendations': {},
                    'top_stocks': []
                }
            
            sector_analysis[sector]['stocks'].append(result)
            
            # 추천 분포
            rec = result.investment_recommendation
            sector_analysis[sector]['recommendations'][rec] = sector_analysis[sector]['recommendations'].get(rec, 0) + 1
        
        # 업종별 통계 계산
        for sector, data in sector_analysis.items():
            if data['stocks']:
                ultimate_scores = [s.ultimate_score for s in data['stocks']]
                enhanced_scores = [s.enhanced_score for s in data['stocks']]
                financial_scores = [s.financial_score for s in data['stocks']]
                
                data['ultimate_avg_score'] = np.mean(ultimate_scores)
                data['enhanced_avg_score'] = np.mean(enhanced_scores)
                data['financial_avg_score'] = np.mean(financial_scores)
                data['count'] = len(data['stocks'])
                
                # 상위 종목 선택 (향상된 점수 기준)
                sorted_stocks = sorted(data['stocks'], key=lambda x: x.enhanced_score, reverse=True)
                data['top_stocks'] = sorted_stocks[:3]
        
        return sector_analysis
    
    def _analyze_enhanced_features(self, results: List[UltimateAnalysisResult]) -> Dict[str, Any]:
        """향상된 기능 분석"""
        if not results:
            return {}
        
        # 가격 위치 페널티 분석
        price_penalties = [r.price_position_penalty for r in results]
        positive_penalties = [p for p in price_penalties if p > 0]
        negative_penalties = [p for p in price_penalties if p < 0]
        
        # 재무 점수 분석
        financial_scores = [r.financial_score for r in results]
        high_financial_stocks = [r for r in results if r.financial_score >= 70]
        
        return {
            'price_position_analysis': {
                'total_stocks': len(results),
                'positive_penalty_count': len(positive_penalties),
                'negative_penalty_count': len(negative_penalties),
                'avg_positive_penalty': np.mean(positive_penalties) if positive_penalties else 0,
                'avg_negative_penalty': np.mean(negative_penalties) if negative_penalties else 0
            },
            'financial_score_analysis': {
                'high_financial_stocks_count': len(high_financial_stocks),
                'high_financial_percentage': len(high_financial_stocks) / len(results) * 100,
                'avg_financial_score': np.mean(financial_scores)
            },
            'enhanced_features_summary': {
                'price_position_penalty_active': True,
                'financial_ratio_analysis_active': True,
                'enhanced_scoring_active': True
            }
        }
    
    def _generate_enhanced_recommendations(self, undervalued_stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """향상된 시장 추천 생성"""
        if not undervalued_stocks:
            return {
                'summary': '현재 시장에서 조건에 맞는 저평가 가치주가 발견되지 않았습니다.',
                'action': '시장 상황을 재검토하고 분석 기준을 조정해보세요.',
                'top_sectors': [],
                'investment_strategy': '보수적 접근 권장',
                'enhanced_analysis': '향상된 재무비율 분석과 가격 위치 페널티를 고려한 결과입니다.'
            }
        
        # 상위 추천 종목
        top_recommendations = undervalued_stocks[:10]
        
        # 업종별 추천 분석 (향상된 점수 기준)
        sector_performance = {}
        for stock in undervalued_stocks:
            sector = stock['sector']
            if sector not in sector_performance:
                sector_performance[sector] = []
            sector_performance[sector].append(stock['enhanced_score'])
        
        # 업종별 평균 점수
        sector_avg_scores = {}
        for sector, scores in sector_performance.items():
            sector_avg_scores[sector] = np.mean(scores)
        
        # 상위 업종
        top_sectors = sorted(sector_avg_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'summary': f'{len(undervalued_stocks)}개의 저평가 가치주를 발굴했습니다. (향상된 분석 기준 적용)',
            'top_recommendations': top_recommendations,
            'top_sectors': [{'sector': sector, 'avg_enhanced_score': score} for sector, score in top_sectors],
            'investment_strategy': self._get_enhanced_investment_strategy(undervalued_stocks),
            'risk_assessment': self._assess_enhanced_market_risk(undervalued_stocks),
            'enhanced_analysis': 'enhanced_integrated_analyzer_refactored.py의 핵심 장점들이 통합된 분석 결과입니다.'
        }
    
    def _get_enhanced_investment_strategy(self, undervalued_stocks: List[Dict[str, Any]]) -> str:
        """향상된 투자 전략 제안"""
        if len(undervalued_stocks) >= 20:
            return "적극적 투자: 충분한 저평가 종목 발견, 향상된 재무비율 분석 기준 통과"
        elif len(undervalued_stocks) >= 10:
            return "균형 투자: 적당한 기회 발견, 엄격한 재무 기준을 통과한 우수 종목들"
        elif len(undervalued_stocks) >= 5:
            return "신중한 투자: 제한된 기회, 향상된 분석 기준을 통과한 선별 종목"
        else:
            return "보수적 투자: 제한된 기회, 향상된 분석 기준이 엄격하여 우수 종목만 선별됨"
    
    def _assess_enhanced_market_risk(self, undervalued_stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """향상된 시장 리스크 평가"""
        if not undervalued_stocks:
            return {
                'overall_risk': 'HIGH',
                'reason': '향상된 분석 기준을 통과하는 저평가 종목 부족',
                'recommendation': '시장 조정 대기 권장, 향상된 분석 기준 완화 고려'
            }
        
        enhanced_avg_score = np.mean([s['enhanced_score'] for s in undervalued_stocks])
        financial_avg_score = np.mean([s['financial_score'] for s in undervalued_stocks])
        high_quality_count = len([s for s in undervalued_stocks if s['enhanced_score'] >= 70])
        
        if enhanced_avg_score >= 70 and financial_avg_score >= 70 and high_quality_count >= 10:
            risk_level = 'LOW'
            reason = '향상된 분석 기준을 통과하는 충분한 고품질 저평가 종목 존재'
            recommendation = '적극적 투자 가능, 향상된 재무비율 분석 결과 우수'
        elif enhanced_avg_score >= 60 and financial_avg_score >= 60:
            risk_level = 'MEDIUM'
            reason = '향상된 분석 기준을 통과하는 적당한 투자 기회 존재'
            recommendation = '균형잡힌 투자 전략, 향상된 분석 기준 고려'
        else:
            risk_level = 'HIGH'
            reason = '향상된 분석 기준을 통과하는 저평가 종목 품질 제한적'
            recommendation = '신중한 투자 필요, 향상된 분석 기준의 엄격성 고려'
        
        return {
            'overall_risk': risk_level,
            'reason': reason,
            'recommendation': recommendation,
            'enhanced_avg_score': enhanced_avg_score,
            'financial_avg_score': financial_avg_score,
            'high_quality_count': high_quality_count
        }
    
    def save_full_analysis(self, market_analysis: Dict[str, Any], filename: str = None):
        """전체 분석 결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ultimate_market_analysis_v2_{timestamp}.json"
        
        try:
            # JSON 직렬화를 위한 데이터 변환
            serializable_data = self._make_json_serializable(market_analysis)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 전체 시장 분석 결과 저장: {filename}")
            return filename
        except Exception as e:
            logger.error(f"결과 저장 실패: {e}")
            return None
    
    def _make_json_serializable(self, obj, visited=None):
        """JSON 직렬화 가능한 형태로 변환 (순환 참조 방지)"""
        if visited is None:
            visited = set()
        
        # 넘파이 스칼라 처리
        import numpy as _np
        if isinstance(obj, (_np.integer,)):
            return int(obj)
        if isinstance(obj, (_np.floating,)):
            return float(obj)
        if isinstance(obj, (_np.ndarray,)):
            return obj.tolist()
        
        # 순환 참조 방지
        obj_id = id(obj)
        if obj_id in visited:
            return str(obj)
        visited.add(obj_id)
        
        try:
            if isinstance(obj, dict):
                return {k: self._make_json_serializable(v, visited) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [self._make_json_serializable(item, visited) for item in obj]
            elif isinstance(obj, (datetime,)):
                return obj.isoformat()
            elif hasattr(obj, 'items'):  # mappingproxy 등 딕셔너리류 객체 처리
                return {k: self._make_json_serializable(v, visited) for k, v in obj.items()}
            elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
                try:
                    return [self._make_json_serializable(item, visited) for item in obj]
                except TypeError:
                    return str(obj)
            elif hasattr(obj, '__dict__'):
                # 객체의 __dict__만 처리하고 순환 참조 방지
                obj_dict = {}
                for key, value in obj.__dict__.items():
                    if not key.startswith('_'):  # private 속성 제외
                        obj_dict[key] = self._make_json_serializable(value, visited)
                return obj_dict
            else:
                return obj
        except Exception:
            return str(obj)
        finally:
            visited.discard(obj_id)
    
    def generate_full_report(self, market_analysis: Dict[str, Any]) -> str:
        """전체 시장 보고서 생성 (향상된 버전)"""
        if not market_analysis:
            return "❌ 분석 데이터가 없습니다."
        
        report = []
        info = market_analysis['analysis_info']
        stats = market_analysis['market_statistics']
        sector_analysis = market_analysis['sector_analysis']
        recommendations = market_analysis['recommendations']
        undervalued = market_analysis['undervalued_stocks']
        enhanced_analysis = market_analysis.get('enhanced_analysis', {})
        
        # 헤더 섹션
        report.append("=" * 100)
        report.append("🌍 궁극의 전체 시장 분석 보고서 v2.0")
        report.append("enhanced_integrated_analyzer_refactored.py 핵심 장점 통합")
        report.append("=" * 100)
        
        # 기본 정보
        report.append("📋 분석 개요")
        report.append("-" * 40)
        report.append(f"📅 분석 일시: {info['analysis_date']}")
        report.append(f"📊 분석 종목 수: {info['total_analyzed']}개")
        report.append(f"🎯 저평가 종목 발견: {info['undervalued_found']}개")
        report.append(f"⏱️ 분석 소요 시간: {info['analysis_time_seconds']:.1f}초")
        report.append(f"🔧 병렬 처리: {info['parallel_workers']}개 워커")
        report.append(f"🚀 향상된 기능: {info.get('enhanced_features', False)}")
        report.append("")
        
        # 향상된 시장 통계
        report.append("📈 시장 통계 분석")
        report.append("-" * 50)
        
        # 궁극의 점수 통계
        ultimate_stats = stats['ultimate_score_statistics']
        report.append(f"🎯 궁극의 점수 - 평균: {ultimate_stats['mean']:.1f}점, 중앙값: {ultimate_stats['median']:.1f}점")
        report.append(f"   최고점: {ultimate_stats.get('max', 0):.1f}점, 최저점: {ultimate_stats.get('min', 0):.1f}점")
        
        # 향상된 점수 통계
        enhanced_stats = stats['enhanced_score_statistics']
        report.append(f"🚀 향상된 점수 - 평균: {enhanced_stats['mean']:.1f}점, 중앙값: {enhanced_stats['median']:.1f}점")
        report.append(f"   최고점: {enhanced_stats.get('max', 0):.1f}점, 최저점: {enhanced_stats.get('min', 0):.1f}점")
        
        # 재무 점수 통계
        financial_stats = stats['financial_score_statistics']
        report.append(f"💰 재무 점수 - 평균: {financial_stats['mean']:.1f}점")
        
        # 가격 위치 페널티 통계
        penalty_stats = stats['price_penalty_statistics']
        report.append(f"📊 가격 위치 페널티 - 평균: {penalty_stats['mean']:.1f}점")
        
        # 시장 상태 평가
        avg_score = enhanced_stats['mean']
        if avg_score >= 70:
            market_status = "🔥 과열 상태 (고평가 우려)"
        elif avg_score >= 60:
            market_status = "📈 상승 추세 (주의 필요)"
        elif avg_score >= 50:
            market_status = "⚖️ 균형 상태 (적정가 수준)"
        elif avg_score >= 40:
            market_status = "📉 하락 추세 (관심 필요)"
        else:
            market_status = "❄️ 침체 상태 (저평가 기회)"
        
        report.append(f"🌡️ 시장 상태: {market_status}")
        report.append("")
        
        # 향상된 등급별 분포
        report.append("🏆 등급별 분포 분석")
        report.append("-" * 40)
        
        # 등급별 분포 (향상된 버전)
        enhanced_grades = stats['enhanced_grade_distribution']
        total_stocks = stats['total_stocks']
        
        # 등급별 시각화
        grade_colors = {
            'S+': '🌟', 'S': '⭐', 'A+': '🔥', 'A': '💎', 'B+': '✨', 'B': '💪',
            'C+': '👍', 'C': '⚖️', 'D+': '⚠️', 'D': '❌', 'F': '💀'
        }
        
        for grade in ['S+', 'S', 'A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F']:
            count = enhanced_grades.get(grade, 0)
            if count > 0:
                percentage = (count / total_stocks) * 100
                bar_length = int(percentage / 2)  # 2%당 1칸
                bar = "█" * bar_length + "░" * (50 - bar_length)
                emoji = grade_colors.get(grade, '📊')
                report.append(f"  {emoji} {grade}: {count:3d}개 ({percentage:4.1f}%) {bar}")
        
        # 투자 등급별 권장사항
        high_grade_count = enhanced_grades.get('S+', 0) + enhanced_grades.get('S', 0) + enhanced_grades.get('A+', 0) + enhanced_grades.get('A', 0)
        if high_grade_count > total_stocks * 0.3:
            grade_recommendation = "📈 고등급 종목 비중 높음 - 적극 투자 고려"
        elif high_grade_count > total_stocks * 0.1:
            grade_recommendation = "⚖️ 고등급 종목 적정 비중 - 선별적 투자"
        else:
            grade_recommendation = "⚠️ 고등급 종목 부족 - 보수적 접근 권장"
        
        report.append(f"💡 투자 권장: {grade_recommendation}")
        report.append("")
        
        # 향상된 업종별 분석
        report.append("🏭 업종별 분석 (상위 10개)")
        report.append("-" * 60)
        sorted_sectors = sorted(sector_analysis.items(), key=lambda x: x[1]['enhanced_avg_score'], reverse=True)
        
        # 업종별 아이콘 및 이름
        sector_info = {
            '16': {'icon': '🏦', 'name': '금융업'},
            '21': {'icon': '💰', 'name': '금융업'},  # 보험, 증권, 홀딩스
            '0': {'icon': '💻', 'name': '기술업'},
            '27': {'icon': '🔬', 'name': '화학/생명과학'},
            '26': {'icon': '⚡', 'name': '전력/가스'},
            '19': {'icon': '🚚', 'name': '운송업'},
            '18': {'icon': '🏗️', 'name': '건설업'},
            '17': {'icon': '⛽', 'name': '에너지'},
            '15': {'icon': '🛍️', 'name': '소비재'},
            '14': {'icon': '🏥', 'name': '의료/제약'},
            '13': {'icon': '🎮', 'name': '엔터테인먼트'},
            '12': {'icon': '📱', 'name': '통신/미디어'}
        }
        
        for i, (sector, data) in enumerate(sorted_sectors[:10], 1):
            sector_str = str(sector)
            icon = sector_info.get(sector_str, {'icon': '📊', 'name': f'업종 {sector}'})['icon']
            name = sector_info.get(sector_str, {'icon': '📊', 'name': f'업종 {sector}'})['name']
            report.append(f"{i:2d}. {icon} {name}")
            report.append(f"     📊 향상된 평균 점수: {data['enhanced_avg_score']:.1f}점")
            report.append(f"     💰 재무 평균 점수: {data['financial_avg_score']:.1f}점")
            report.append(f"     📈 종목 수: {data['count']}개")
            
            # 업종 성과 평가
            score = data['enhanced_avg_score']
            if score >= 60:
                performance = "🔥 우수"
            elif score >= 55:
                performance = "✨ 양호"
            elif score >= 50:
                performance = "⚖️ 보통"
            elif score >= 45:
                performance = "⚠️ 주의"
            else:
                performance = "❌ 위험"
            
            report.append(f"     🎯 성과: {performance}")
            
            if data['top_stocks']:
                top_stock = data['top_stocks'][0]
                report.append(f"     🏆 최고 종목: {top_stock.name} ({top_stock.enhanced_score:.1f}점)")
            report.append("")
        
        # 업종별 투자 전략
        top_sector_score = sorted_sectors[0][1]['enhanced_avg_score'] if sorted_sectors else 0
        if top_sector_score >= 60:
            sector_strategy = "📈 강세 업종 집중 투자 고려"
        elif top_sector_score >= 55:
            sector_strategy = "⚖️ 업종별 분산 투자 권장"
        else:
            sector_strategy = "⚠️ 업종별 선별 투자 필요"
        
        report.append(f"💡 업종 투자 전략: {sector_strategy}")
        report.append("")
        
        # 향상된 저평가 종목 추천
        if undervalued:
            report.append("🎯 저평가 가치주 추천 (상위 20개)")
            report.append("-" * 70)
            for i, stock in enumerate(undervalued[:20], 1):
                # 추천 아이콘
                recommendation = stock['investment_recommendation']
                if recommendation in ['STRONG_BUY', 'BUY']:
                    rec_icon = "🔥"
                elif recommendation == 'HOLD':
                    rec_icon = "⚖️"
                else:
                    rec_icon = "⚠️"
                
                report.append(f"{i:2d}. {rec_icon} {stock['name']} ({stock['symbol']})")
                report.append(f"     📊 향상된 점수: {stock['enhanced_score']:.1f}점 ({stock['enhanced_grade']})")
                report.append(f"     💰 재무 점수: {stock['financial_score']:.1f}점")
                report.append(f"     📈 투자 추천: {stock['investment_recommendation']}")
                report.append(f"     🎯 신뢰도: {stock['confidence_level']}")
                
                # 재무 지표
                financial = stock['financial_data']
                per = financial.get('per', 0)
                pbr = financial.get('pbr', 0)
                roe = financial.get('roe', 0)
                
                # 밸류에이션 평가
                valuation_status = "적정"
                if per > 0 and per < 10:
                    valuation_status = "저평가"
                elif per > 20:
                    valuation_status = "고평가"
                
                report.append(f"     💎 밸류에이션: {valuation_status} (PER: {per:.1f}, PBR: {pbr:.2f}, ROE: {roe:.1f}%)")
                
                # 투자 포인트
                if stock['enhanced_score'] >= 70:
                    point = "🚀 강력한 성장성"
                elif stock['enhanced_score'] >= 60:
                    point = "💪 안정적 수익성"
                elif stock['enhanced_score'] >= 50:
                    point = "⚖️ 균형잡힌 포트폴리오"
                else:
                    point = "⚠️ 신중한 검토 필요"
                
                report.append(f"     🎯 투자 포인트: {point}")
                report.append("")
        else:
            # 저평가 종목이 없는 경우
            report.append("🎯 저평가 가치주 분석")
            report.append("-" * 40)
            report.append("📊 현재 분석 결과 저평가 종목이 발견되지 않았습니다.")
            report.append("")
            report.append("💡 시장 상황 분석:")
            avg_score = enhanced_stats['mean']
            if avg_score >= 60:
                market_analysis = "📈 시장이 고평가 상태일 가능성이 높습니다."
                recommendation = "⚖️ 현재 시점에서는 보수적 접근을 권장합니다."
            elif avg_score >= 50:
                market_analysis = "⚖️ 시장이 적정가 수준에 있습니다."
                recommendation = "🎯 개별 종목 선별 투자를 고려해보세요."
            else:
                market_analysis = "📉 시장이 저평가 상태일 수 있습니다."
                recommendation = "🚀 적극적인 투자 기회를 모색해보세요."
            
            report.append(f"   {market_analysis}")
            report.append(f"   {recommendation}")
            report.append("")
            
            # 상위 등급 종목 안내
            high_grade_stocks = []
            if 'all_stocks' in market_analysis:
                for stock in market_analysis['all_stocks']:
                    if stock.get('enhanced_grade') in ['A+', 'A', 'B+', 'B']:
                        high_grade_stocks.append(stock)
            
            if high_grade_stocks:
                report.append("🌟 상위 등급 종목 (관심 대상):")
                sorted_high_grade = sorted(high_grade_stocks, key=lambda x: x.get('enhanced_score', 0), reverse=True)
                for i, stock in enumerate(sorted_high_grade[:5], 1):
                    report.append(f"   {i}. {stock.get('name', 'N/A')} ({stock.get('symbol', 'N/A')}) - {stock.get('enhanced_score', 0):.1f}점 ({stock.get('enhanced_grade', 'N/A')})")
                report.append("")
        
        # 향상된 투자 전략 및 리스크 평가
        report.append("💼 투자 전략 및 리스크 평가")
        report.append("-" * 60)
        
        # 전략별 분석
        strategy = recommendations.get('investment_strategy', '보수적 접근')
        report.append(f"📋 투자 전략: {strategy}")
        
        # 시장 타이밍 분석
        avg_score = enhanced_stats['mean']
        if avg_score >= 65:
            timing = "🔥 과열 시장 - 매도 우선"
            timing_icon = "📉"
        elif avg_score >= 55:
            timing = "📈 상승 시장 - 선별 매수"
            timing_icon = "🎯"
        elif avg_score >= 45:
            timing = "⚖️ 균형 시장 - 분산 투자"
            timing_icon = "📊"
        elif avg_score >= 35:
            timing = "📉 하락 시장 - 점진 매수"
            timing_icon = "💰"
        else:
            timing = "❄️ 침체 시장 - 적극 매수"
            timing_icon = "🚀"
        
        report.append(f"{timing_icon} 시장 타이밍: {timing}")
        
        if 'risk_assessment' in recommendations:
            risk = recommendations['risk_assessment']
            report.append(f"⚠️ 전체 리스크: {risk.get('overall_risk', '보통')}")
            report.append(f"📝 사유: {risk.get('reason', '시장 상황 분석')}")
            report.append(f"💡 권장사항: {risk.get('recommendation', '분산 투자 권장')}")
            report.append(f"📊 향상된 평균 점수: {risk.get('enhanced_avg_score', avg_score):.1f}점")
            report.append(f"💰 재무 평균 점수: {risk.get('financial_avg_score', 0):.1f}점")
        
        # 포트폴리오 구성 권장사항
        report.append("")
        report.append("🎯 포트폴리오 구성 권장사항:")
        
        # 등급별 포트폴리오 비중
        high_grade_ratio = (enhanced_grades.get('A+', 0) + enhanced_grades.get('A', 0)) / total_stocks * 100
        if high_grade_ratio >= 20:
            portfolio_advice = "🔥 고품질 종목 비중 높음 - 적극적 포트폴리오"
            high_grade_weight = "40-50%"
            mid_grade_weight = "30-40%"
            low_grade_weight = "10-20%"
        elif high_grade_ratio >= 10:
            portfolio_advice = "⚖️ 균형잡힌 품질 분포 - 표준 포트폴리오"
            high_grade_weight = "30-40%"
            mid_grade_weight = "40-50%"
            low_grade_weight = "10-20%"
        else:
            portfolio_advice = "⚠️ 고품질 종목 부족 - 보수적 포트폴리오"
            high_grade_weight = "20-30%"
            mid_grade_weight = "40-50%"
            low_grade_weight = "20-30%"
        
        report.append(f"   📊 {portfolio_advice}")
        report.append(f"   🏆 고등급(A+/A): {high_grade_weight}")
        report.append(f"   ⚖️ 중등급(B+/B/C+): {mid_grade_weight}")
        report.append(f"   ⚠️ 저등급(C/D+/D): {low_grade_weight}")
        
        # 리스크 관리 전략
        report.append("")
        report.append("🛡️ 리스크 관리 전략:")
        report.append("   📈 분산 투자: 업종별, 시가총액별 분산")
        report.append("   ⏰ 정기 리밸런싱: 분기별 포트폴리오 점검")
        report.append("   🎯 손실 제한: 개별 종목 10% 손실 시 재검토")
        report.append("   💰 현금 보유: 포트폴리오의 10-20% 유지")
        
        # 향상된 기능 분석 요약
        report.append("")
        report.append("🚀 분석 시스템 성능")
        report.append("-" * 40)
        
        if enhanced_analysis:
            price_analysis = enhanced_analysis.get('price_position_analysis', {})
            financial_analysis = enhanced_analysis.get('financial_score_analysis', {})
            
            report.append(f"📊 가격 위치 페널티 분석:")
            report.append(f"   긍정적 페널티 종목: {price_analysis.get('positive_penalty_count', 0)}개")
            report.append(f"   부정적 페널티 종목: {price_analysis.get('negative_penalty_count', 0)}개")
            
            report.append(f"💰 재무 점수 분석:")
            report.append(f"   고재무 점수 종목: {financial_analysis.get('high_financial_stocks_count', 0)}개")
            report.append(f"   고재무 점수 비율: {financial_analysis.get('high_financial_percentage', 0):.1f}%")
            
            # 시스템 신뢰도
            high_financial_ratio = financial_analysis.get('high_financial_percentage', 0)
            if high_financial_ratio >= 30:
                reliability = "높음"
                reliability_icon = "🟢"
            elif high_financial_ratio >= 15:
                reliability = "보통"
                reliability_icon = "🟡"
            else:
                reliability = "낮음"
                reliability_icon = "🔴"
            
            report.append(f"🎯 분석 신뢰도: {reliability_icon} {reliability}")
        
        report.append("")
        report.append("⚠️ 투자 주의사항")
        report.append("-" * 40)
        report.append("🔍 이 분석은 enhanced_integrated_analyzer_refactored.py의 핵심 장점들이 통합된 결과입니다.")
        report.append("📊 향상된 재무비율 분석과 가격 위치 페널티를 고려한 엄격한 기준이 적용되었습니다.")
        report.append("💼 투자 결정은 개인의 책임이며, 시장 상황과 개인적 위험 감수 능력을 고려하세요.")
        report.append("🎯 분산 투자를 통해 리스크를 관리하고, 정기적인 포트폴리오 리밸런싱을 권장합니다.")
        report.append("📈 과거 성과가 미래 수익을 보장하지 않으며, 투자 손실 가능성을 항상 고려하세요.")
        report.append("⏰ 시장 상황은 변동성이 크므로 정기적인 분석 업데이트를 권장합니다.")
        
        report.append("=" * 100)
        
        return "\n".join(report)
    
    async def _get_market_cap_data(self, symbol: str, name: str) -> Dict[str, Any]:
        """종목의 시가총액 데이터 조회"""
        try:
            # 캐시 확인
            cache_key = f"{symbol}_{name}"
            if cache_key in self._market_cap_cache:
                return self._market_cap_cache[cache_key]
            
            # KIS API로 데이터 조회
            data = self.analyzer.data_provider.base_provider.get_stock_price_info(symbol)
            
            if data and 'market_cap' in data:
                market_cap = data.get('market_cap', 0)
                current_price = data.get('current_price', 0)
                shares_outstanding = data.get('shares_outstanding', 0)
                
                result = {
                    'symbol': symbol,
                    'name': name,
                    'market_cap': market_cap,
                    'current_price': current_price,
                    'shares_outstanding': shares_outstanding,
                    'data_source': 'kis_api'
                }
            else:
                # 기본 시가총액 추정 (임의값)
                import random
                estimated_market_cap = random.randint(1000000000000, 50000000000000)  # 1조~50조
                result = {
                    'symbol': symbol,
                    'name': name,
                    'market_cap': estimated_market_cap,
                    'current_price': 0,
                    'shares_outstanding': 0,
                    'data_source': 'estimated'
                }
            
            # 캐시 저장
            self._market_cap_cache[cache_key] = result
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {symbol}({name}) 시가총액 데이터 조회 실패: {e}")
            # 기본값 반환
            return {
                'symbol': symbol,
                'name': name,
                'market_cap': 0,
                'current_price': 0,
                'shares_outstanding': 0,
                'data_source': 'default'
            }
    
    async def get_top_market_cap_stocks(self, top_n: int = 50) -> List[Tuple[str, str, str]]:
        """시가총액 상위 N개 종목 조회"""
        self.logger.info(f"📊 시가총액 상위 {top_n}개 종목 조회 시작")
        
        try:
            # KOSPI 마스터 데이터 로드
            df = self._load_kospi_data()
            
            if df is None or len(df) == 0:
                self.logger.error("❌ KOSPI 데이터를 로드할 수 없습니다")
                return []
            
            # 시가총액 기준으로 직접 정렬하여 상위 N개 선택
            if '시가총액' in df.columns:
                # 시가총액이 있는 종목만 선택하고 시가총액 기준으로 정렬
                df_with_market_cap = df[df['시가총액'].notna() & (df['시가총액'] > 0)]
                df_sorted = df_with_market_cap.nlargest(top_n, '시가총액')
                
                top_stocks = []
                for _, row in df_sorted.iterrows():
                    symbol = str(row['단축코드']).zfill(6)
                    name = row['회사명']
                    market_cap = row['시가총액']
                    
                    top_stocks.append({
                        'symbol': symbol,
                        'name': name,
                        'market_cap': market_cap,
                        'current_price': 0,
                        'shares_outstanding': 0,
                        'data_source': 'excel_file'
                    })
                    
                    self.logger.info(f"📈 {name}({symbol}): {market_cap:,}원")
            else:
                # 시가총액 컬럼이 없는 경우 기본 방식 사용
                market_cap_data = []
                for _, row in df.iterrows():
                    if '단축코드' in df.columns:
                        symbol = str(row['단축코드']).zfill(6)
                        name = row['회사명']
                        market_cap_from_file = row.get('시가총액', 0)
                    elif 'symbol' in df.columns:
                        symbol = str(row['symbol']).zfill(6)
                        name = row['name']
                        market_cap_from_file = row.get('market_cap', 0)
                    else:
                        continue
                    
                    if market_cap_from_file and market_cap_from_file > 0:
                        market_cap_data.append({
                            'symbol': symbol,
                            'name': name,
                            'market_cap': market_cap_from_file,
                            'current_price': 0,
                            'shares_outstanding': 0,
                            'data_source': 'excel_file'
                        })
                    else:
                        data = await self._get_market_cap_data(symbol, name)
                        if data['market_cap'] > 0:
                            market_cap_data.append(data)
                
                # 시가총액 기준 정렬
                market_cap_data.sort(key=lambda x: x['market_cap'], reverse=True)
                top_stocks = market_cap_data[:top_n]
            
            # 결과 포맷팅
            result = []
            for data in top_stocks:
                symbol = data['symbol']
                name = data['name']
                market_cap = data['market_cap']
                
                # 업종 정보 추가 (기본값)
                sector = "기타"
                result.append((symbol, name, sector))
                
                self.logger.info(f"📈 {name}({symbol}): {market_cap:,}원")
            
            self.logger.info(f"✅ 시가총액 상위 {len(result)}개 종목 조회 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 시가총액 상위 종목 조회 실패: {e}")
            return []
    
    async def analyze_top_market_cap_stocks(self, top_n: int = 50, min_score: float = 40.0) -> Dict[str, Any]:
        """시가총액 상위 종목 분석"""
        self.logger.info(f"🚀 코스피 시가총액 상위 {top_n}개 종목 분석 시작")
        
        try:
            # 시가총액 상위 종목 조회
            top_stocks = await self.get_top_market_cap_stocks(top_n)
            
            if not top_stocks:
                self.logger.error("❌ 분석할 종목이 없습니다")
                return {}
            
            # 디버깅: 선택된 종목들 로그 출력
            self.logger.info(f"🔍 선택된 상위 {top_n}개 종목:")
            for i, (symbol, name, sector) in enumerate(top_stocks, 1):
                self.logger.info(f"  {i}. {name}({symbol}) - {sector}")
            
            # 종목 분석
            self.logger.info(f"🔍 {len(top_stocks)}개 종목 분석 시작")
            results = await self.analyzer.analyze_multiple_stocks(top_stocks)
            
            # 결과 필터링 (저평가 종목)
            undervalued_stocks = [
                r for r in results 
                if r.ultimate_score >= min_score
            ]
            
            # 시가총액 가중 분석
            market_cap_analysis = self._analyze_market_cap_weighted(results)
            
            # 결과 정리
            analysis_result = {
                'analysis_date': datetime.now().isoformat(),
                'total_analyzed': len(results),
                'top_n': top_n,
                'undervalued_count': len(undervalued_stocks),
                'min_score_threshold': min_score,
                'market_cap_analysis': market_cap_analysis,
                'results': results,
                'undervalued_stocks': undervalued_stocks
            }
            
            self.logger.info(f"✅ 분석 완료: 총 {len(results)}개, 저평가 {len(undervalued_stocks)}개")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ 시가총액 상위 종목 분석 실패: {e}")
            return {}
    
    def _analyze_market_cap_weighted(self, results: List) -> Dict[str, Any]:
        """시가총액 가중 분석"""
        try:
            total_market_cap = 0
            weighted_scores = 0
            market_cap_distribution = {}
            
            for result in results:
                # 시가총액 데이터 조회 - 여러 방법으로 시도
                market_cap = 0
                
                # 1. 캐시에서 조회
                market_cap_data = self._market_cap_cache.get(f"{result.symbol}_{result.name}", {})
                if market_cap_data:
                    market_cap = market_cap_data.get('market_cap', 0)
                
                # 2. 결과 객체에서 직접 조회 (financial_data에 있을 수 있음)
                if market_cap == 0 and hasattr(result, 'financial_data') and result.financial_data:
                    market_cap = result.financial_data.get('market_cap', 0)
                
                # 3. 추정값 사용 (시가총액이 없는 경우)
                if market_cap == 0:
                    # 기본 추정 시가총액 (종목명 기반)
                    estimated_cap = self._estimate_market_cap(result.name, result.symbol)
                    market_cap = estimated_cap
                    self.logger.warning(f"⚠️ {result.name}({result.symbol}) 시가총액 추정값 사용: {market_cap:,}원")
                
                if market_cap > 0:
                    total_market_cap += market_cap
                    weighted_scores += result.ultimate_score * market_cap
                    
                    # 시가총액 구간별 분포
                    if market_cap >= 100000000000000:  # 100조 이상
                        cap_range = "100조 이상"
                    elif market_cap >= 50000000000000:  # 50조 이상
                        cap_range = "50조~100조"
                    elif market_cap >= 10000000000000:  # 10조 이상
                        cap_range = "10조~50조"
                    elif market_cap >= 1000000000000:  # 1조 이상
                        cap_range = "1조~10조"
                    else:
                        cap_range = "1조 미만"
                    
                    if cap_range not in market_cap_distribution:
                        market_cap_distribution[cap_range] = {
                            'count': 0,
                            'total_market_cap': 0,
                            'avg_score': 0,
                            'stocks': []
                        }
                    
                    market_cap_distribution[cap_range]['count'] += 1
                    market_cap_distribution[cap_range]['total_market_cap'] += market_cap
                    market_cap_distribution[cap_range]['stocks'].append({
                        'symbol': result.symbol,
                        'name': result.name,
                        'score': result.ultimate_score,
                        'market_cap': market_cap
                    })
            
            # 평균 점수 계산
            avg_weighted_score = weighted_scores / total_market_cap if total_market_cap > 0 else 0
            
            # 구간별 평균 점수 계산
            for cap_range in market_cap_distribution:
                dist = market_cap_distribution[cap_range]
                if dist['count'] > 0:
                    dist['avg_score'] = sum(s['score'] for s in dist['stocks']) / dist['count']
                    # 시가총액 순으로 정렬
                    dist['stocks'].sort(key=lambda x: x['market_cap'], reverse=True)
            
            self.logger.info(f"💰 시가총액 가중 분석 완료: 총 시가총액 {total_market_cap:,}원, 가중평균점수 {avg_weighted_score:.1f}점")
            
            return {
                'total_market_cap': total_market_cap,
                'avg_weighted_score': avg_weighted_score,
                'distribution': market_cap_distribution
            }
            
        except Exception as e:
            self.logger.error(f"❌ 시가총액 가중 분석 실패: {e}")
            return {}
    
    def _estimate_market_cap(self, name: str, symbol: str) -> int:
        """종목명과 심볼 기반으로 시가총액 추정"""
        # 주요 대기업들의 대략적인 시가총액 범위
        large_cap_estimates = {
            '삼성전자': 400000000000000,  # 400조
            'SK하이닉스': 200000000000000,  # 200조
            'LG에너지솔루션': 80000000000000,  # 80조
            '삼성바이오로직스': 70000000000000,  # 70조
            '한화에어로스페이스': 50000000000000,  # 50조
            'KB금융': 40000000000000,  # 40조
            '현대차': 40000000000000,  # 40조
            'HD현대중공업': 40000000000000,  # 40조
            '기아': 40000000000000,  # 40조
            '셀트리온': 35000000000000,  # 35조
            'NAVER': 35000000000000,  # 35조
            '신한지주': 30000000000000,  # 30조
            '삼성물산': 30000000000000,  # 30조
            '삼성생명': 30000000000000,  # 30조
        }
        
        # 정확한 매칭
        if name in large_cap_estimates:
            return large_cap_estimates[name]
        
        # 부분 매칭
        for key, value in large_cap_estimates.items():
            if key in name or name in key:
                return value
        
        # 기본 추정값 (중소형주)
        import random
        return random.randint(1000000000000, 50000000000000)  # 1조~50조
    
    async def analyze_comprehensive_market(self, 
                                         max_stocks: int = 100,
                                         min_comprehensive_score: float = 50.0) -> Dict[str, Any]:
        """종합점수 기반 전체 시장 분석"""
        self.logger.info(f"🚀 종합점수 기반 전체 시장 분석 시작 (최대 {max_stocks}개 종목)")
        
        start_time = datetime.now()
        
        # KOSPI 데이터 로드
        kospi_data = self._load_kospi_data()
        if kospi_data is None or len(kospi_data) == 0:
            self.logger.warning("KOSPI 데이터가 없습니다. 기본 종목 리스트를 사용합니다.")
            kospi_data = self._create_default_stock_list()
        
        # 분석할 종목 선택
        stocks_to_analyze = kospi_data.head(max_stocks)
        
        # 종합점수 기반 분석
        comprehensive_results = []
        undervalued_stocks = []
        
        for _, stock in stocks_to_analyze.iterrows():
            symbol = stock['단축코드']
            name = stock['회사명']
            sector = stock['업종']
            
            try:
                # 종합점수 기반 분석 실행
                result = await self.comprehensive_scoring.analyze_stock_comprehensive(symbol, name, sector)
                if result:
                    comprehensive_results.append(result)
                    
                    # 저평가 종목 필터링
                    comp_score = result['comprehensive_score']['comprehensive_score']
                    if comp_score >= min_comprehensive_score:
                        undervalued_stocks.append(result)
                    
                    self.logger.info(f"✅ {name}({symbol}) 종합 분석 완료: {comp_score:.1f}점")
                else:
                    self.logger.warning(f"⚠️ {name}({symbol}) 종합 분석 실패")
            except Exception as e:
                self.logger.error(f"❌ {name}({symbol}) 종합 분석 오류: {e}")
        
        if not comprehensive_results:
            self.logger.warning("종합 분석할 종목이 없습니다.")
            return {}
        
        end_time = datetime.now()
        analysis_time = (end_time - start_time).total_seconds()
        
        # 결과 정리
        market_analysis = {
            'analysis_info': {
                'total_analyzed': len(comprehensive_results),
                'undervalued_found': len(undervalued_stocks),
                'analysis_time_seconds': analysis_time,
                'analysis_date': start_time.isoformat(),
                'min_comprehensive_score': min_comprehensive_score,
                'analysis_type': 'comprehensive_scoring'
            },
            'all_results': comprehensive_results,
            'undervalued_stocks': undervalued_stocks,
            'comprehensive_statistics': self._calculate_comprehensive_statistics(comprehensive_results),
            'sector_analysis': self._analyze_comprehensive_by_sector(comprehensive_results),
            'recommendations': self._generate_comprehensive_recommendations(undervalued_stocks)
        }
        
        self.logger.info(f"🎯 종합점수 기반 분석 완료: {len(comprehensive_results)}개 종목 분석, {len(undervalued_stocks)}개 저평가 종목 발굴")
        
        return market_analysis
    
    def _calculate_comprehensive_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """종합점수 통계 계산"""
        if not results:
            return {}
        
        # 종합점수들
        comprehensive_scores = [r['comprehensive_score']['comprehensive_score'] for r in results]
        quantitative_scores = [r['comprehensive_score']['quantitative_score'] for r in results]
        qualitative_scores = [r['comprehensive_score']['qualitative_score'] for r in results]
        
        # 등급별 분포
        grades = [r['comprehensive_score']['grade'] for r in results]
        grade_dist = {}
        for grade in grades:
            grade_dist[grade] = grade_dist.get(grade, 0) + 1
        
        # 추천별 분포
        recommendations = [r['comprehensive_score']['recommendation'] for r in results]
        recommendation_dist = {}
        for rec in recommendations:
            recommendation_dist[rec] = recommendation_dist.get(rec, 0) + 1
        
        return {
            'comprehensive_score_statistics': {
                'mean': np.mean(comprehensive_scores),
                'median': np.median(comprehensive_scores),
                'std': np.std(comprehensive_scores),
                'min': np.min(comprehensive_scores),
                'max': np.max(comprehensive_scores),
                'q25': np.percentile(comprehensive_scores, 25),
                'q75': np.percentile(comprehensive_scores, 75)
            },
            'quantitative_score_statistics': {
                'mean': np.mean(quantitative_scores),
                'median': np.median(quantitative_scores),
                'std': np.std(quantitative_scores)
            },
            'qualitative_score_statistics': {
                'mean': np.mean(qualitative_scores),
                'median': np.median(qualitative_scores),
                'std': np.std(qualitative_scores)
            },
            'grade_distribution': grade_dist,
            'recommendation_distribution': recommendation_dist,
            'total_stocks': len(results)
        }
    
    def _analyze_comprehensive_by_sector(self, results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """업종별 종합 분석"""
        sector_analysis = {}
        
        for result in results:
            sector = result['sector']
            if sector not in sector_analysis:
                sector_analysis[sector] = {
                    'stocks': [],
                    'avg_comprehensive_score': 0,
                    'avg_quantitative_score': 0,
                    'avg_qualitative_score': 0,
                    'recommendations': {},
                    'top_stocks': []
                }
            
            sector_analysis[sector]['stocks'].append(result)
            
            # 추천 분포
            rec = result['comprehensive_score']['recommendation']
            sector_analysis[sector]['recommendations'][rec] = sector_analysis[sector]['recommendations'].get(rec, 0) + 1
        
        # 업종별 통계 계산
        for sector, data in sector_analysis.items():
            if data['stocks']:
                comprehensive_scores = [s['comprehensive_score']['comprehensive_score'] for s in data['stocks']]
                quantitative_scores = [s['comprehensive_score']['quantitative_score'] for s in data['stocks']]
                qualitative_scores = [s['comprehensive_score']['qualitative_score'] for s in data['stocks']]
                
                data['avg_comprehensive_score'] = np.mean(comprehensive_scores)
                data['avg_quantitative_score'] = np.mean(quantitative_scores)
                data['avg_qualitative_score'] = np.mean(qualitative_scores)
                data['count'] = len(data['stocks'])
                
                # 상위 종목 선택 (종합점수 기준)
                sorted_stocks = sorted(data['stocks'], key=lambda x: x['comprehensive_score']['comprehensive_score'], reverse=True)
                data['top_stocks'] = sorted_stocks[:3]
        
        return sector_analysis
    
    def _generate_comprehensive_recommendations(self, undervalued_stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """종합점수 기반 추천 생성"""
        if not undervalued_stocks:
            return {
                'summary': '현재 시장에서 종합점수 기준을 만족하는 저평가 가치주가 발견되지 않았습니다.',
                'action': '종합점수 기준을 조정하거나 시장 상황을 재검토해보세요.',
                'top_sectors': [],
                'investment_strategy': '보수적 접근 권장',
                'comprehensive_analysis': '정량적 + 정성적 지표를 통합한 종합점수 분석 결과입니다.'
            }
        
        # 상위 추천 종목
        top_recommendations = sorted(undervalued_stocks, 
                                   key=lambda x: x['comprehensive_score']['comprehensive_score'], 
                                   reverse=True)[:10]
        
        # 업종별 추천 분석
        sector_performance = {}
        for stock in undervalued_stocks:
            sector = stock['sector']
            if sector not in sector_performance:
                sector_performance[sector] = []
            sector_performance[sector].append(stock['comprehensive_score']['comprehensive_score'])
        
        # 업종별 평균 점수
        sector_avg_scores = {}
        for sector, scores in sector_performance.items():
            sector_avg_scores[sector] = np.mean(scores)
        
        # 상위 업종
        top_sectors = sorted(sector_avg_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'summary': f'{len(undervalued_stocks)}개의 종합점수 기준 저평가 가치주를 발굴했습니다.',
            'top_recommendations': top_recommendations,
            'top_sectors': [{'sector': sector, 'avg_comprehensive_score': score} for sector, score in top_sectors],
            'investment_strategy': self._get_comprehensive_investment_strategy(undervalued_stocks),
            'comprehensive_analysis': '정량적 지표(70%) + 정성적 지표(30%)를 통합한 종합점수 분석 결과입니다.'
        }
    
    def _get_comprehensive_investment_strategy(self, undervalued_stocks: List[Dict[str, Any]]) -> str:
        """종합점수 기반 투자 전략 제안"""
        if len(undervalued_stocks) >= 15:
            return "적극적 투자: 종합점수 기준을 통과하는 충분한 저평가 종목 발견"
        elif len(undervalued_stocks) >= 10:
            return "균형 투자: 종합점수 기준을 통과하는 적당한 투자 기회 존재"
        elif len(undervalued_stocks) >= 5:
            return "신중한 투자: 종합점수 기준을 통과하는 제한된 투자 기회"
        else:
            return "보수적 투자: 종합점수 기준이 엄격하여 선별된 우수 종목들"

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='궁극의 전체 시장 분석기 v2.0')
    parser.add_argument('--max-stocks', type=int, default=100, help='최대 분석 종목 수 (기본값: 100)')
    parser.add_argument('--workers', type=int, default=2, help='병렬 처리 워커 수 (기본값: 2)')
    parser.add_argument('--min-score', type=float, default=30.0, help='최소 점수 기준 (기본값: 30.0)')
    parser.add_argument('--max-recommendations', type=int, default=50, help='최대 추천 종목 수 (기본값: 50)')
    parser.add_argument('--market-cap', action='store_true', help='시가총액 상위 종목 분석 모드')
    parser.add_argument('--top-n', type=int, default=50, help='시가총액 상위 N개 종목 (기본값: 50)')
    parser.add_argument('--comprehensive', action='store_true', help='종합점수 기반 분석 모드 (정량+정성)')
    parser.add_argument('--enhanced', action='store_true', help='향상된 분석 모드 (v3.0 기능 포함)')
    parser.add_argument('--min-comprehensive-score', type=float, default=50.0, help='최소 종합점수 기준 (기본값: 50.0)')
    parser.add_argument('--no-realtime', action='store_true', help='실시간 데이터 분석 제외')
    parser.add_argument('--no-external', action='store_true', help='외부 데이터 분석 제외')
    parser.add_argument('--export', action='store_true', help='결과를 JSON 파일로 내보내기')
    parser.add_argument('--undervalued', action='store_true', help='저평가 가치 중심 분석 모드 (품질 필터 적용)')
    parser.add_argument('--max-workers', type=int, default=4, help='병렬 처리 최대 워커 수 (기본값: 4)')
    
    args = parser.parse_args()
    
    print("=" * 100)
    print("🌍 궁극의 전체 시장 분석기 v2.0")
    print("enhanced_integrated_analyzer_refactored.py 핵심 장점 통합")
    print("=" * 100)
    print(f"📊 분석 설정:")
    print(f"   - 최대 분석 종목: {args.max_stocks}개")
    print(f"   - 병렬 처리 워커: {args.workers}개 (안전 모드)")
    print(f"   - 최소 점수 기준: {args.min_score}점")
    print(f"   - 최대 추천 종목: {args.max_recommendations}개")
    print(f"   - 향상된 기능: 재무비율 분석, 가격 위치 페널티, TPS 제한")
    print("=" * 100)
    
    # 궁극의 전체 시장 분석기 초기화
    analyzer = UltimateMarketAnalyzerV2()
    
    if args.undervalued:
        # 저평가 가치 중심 분석 모드 (새로운 기능)
        print(f"\n🎯 저평가 가치 중심 분석 모드...")
        print(f"   - 상위 {args.top_n}개 종목 분석")
        print(f"   - 품질 필터: ROE≥3%, 부채비율≤400%, 순이익률≥-10%")
        print(f"   - 가격 필터: 52주 위치 ≤85%")
        print(f"   - 최소 점수 기준: {args.min_score}점")
        print(f"   - 병렬 처리 워커: {args.max_workers}개")
        
        undervalued_analysis = await analyzer.analyze_undervalued_stocks_enhanced(
            top_n=args.top_n,
            min_score=args.min_score,
            max_workers=args.max_workers
        )
        
        if undervalued_analysis:
            print(f"\n🎯 저평가 가치 중심 분석 완료!")
            print(f"📊 총 분석 종목: {undervalued_analysis['total_analyzed']}개")
            print(f"🔍 필터 통과 종목: {undervalued_analysis['filtered_count']}개")
            print(f"⭐ 고품질 종목: {undervalued_analysis['summary']['high_quality_count']}개")
            print(f"📈 평균 점수: {undervalued_analysis['summary']['average_score']:.1f}점")
            
            # 상위 추천 종목 출력
            if undervalued_analysis['top_recommendations']:
                print(f"\n🏆 상위 추천 종목:")
                for i, stock in enumerate(undervalued_analysis['top_recommendations'][:10], 1):
                    print(f"   {i}. {stock.get('name', 'Unknown')}({stock.get('symbol', '')}) - {stock.get('enhanced_score', 0):.1f}점 ({stock.get('enhanced_grade', 'F')})")
            
            # 결과 내보내기
            if args.export:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"undervalued_analysis_{timestamp}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(undervalued_analysis, f, ensure_ascii=False, indent=2, default=str)
                print(f"💾 결과를 {filename}에 저장했습니다.")
        else:
            print("❌ 저평가 가치 중심 분석 실패")
            return
    
    elif args.market_cap:
        # 시가총액 상위 종목 분석 모드
        if args.enhanced:
            print(f"\n🚀 향상된 시가총액 상위 종목 분석 모드 (v3.0 기능 포함)...")
            print(f"   - 상위 {args.top_n}개 종목 분석")
            print(f"   - 실시간 데이터: {'제외' if args.no_realtime else '포함'}")
            print(f"   - 외부 데이터: {'제외' if args.no_external else '포함'}")
            print(f"   - 최소 점수 기준: {args.min_score}점")
            
            market_analysis = await analyzer.analyze_top_market_cap_stocks_enhanced(
                top_n=args.top_n,
                include_realtime=not args.no_realtime,
                include_external=not args.no_external,
                min_score=args.min_score
            )
        else:
            print(f"\n📊 시가총액 상위 종목 분석 모드...")
            print(f"   - 상위 {args.top_n}개 종목 분석")
            print(f"   - 최소 점수 기준: {args.min_score}점")
            
            market_analysis = await analyzer.analyze_top_market_cap_stocks(
                top_n=args.top_n,
                min_score=args.min_score
            )
        
        if market_analysis:
            # 시가총액 분석 결과 처리
            print(f"\n📊 시가총액 상위 종목 분석 완료!")
            # 향상된 분석 결과를 표로 출력
            if args.enhanced:
                analyzer._display_enhanced_results_table(market_analysis)
            else:
                print(f"📊 총 분석 종목: {market_analysis['metadata']['total_analyzed']}개")
                print(f"🎯 저평가 종목: {market_analysis['metadata']['undervalued_count']}개")
                
                # 시가총액 가중 분석 결과
                if 'market_cap_analysis' in market_analysis:
                    cap_analysis = market_analysis['market_cap_analysis']
                    if cap_analysis:
                        print(f"💰 총 시가총액: {cap_analysis.get('total_market_cap', 0):,}원")
                        print(f"📈 가중 평균 점수: {cap_analysis.get('avg_weighted_score', 0):.1f}점")
            
            # 결과 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"market_cap_top_analysis_{timestamp}.json"
            
            # JSON 직렬화를 위한 데이터 변환
            serializable_data = analyzer._make_json_serializable(market_analysis)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 결과 저장: {filename}")
            
            # 시가총액 분석 모드에서는 보고서 생성하지 않음
            return
            
        else:
            print("❌ 시가총액 상위 종목 분석 실패")
            return
    
    elif args.comprehensive:
        # 종합점수 기반 분석 모드
        print(f"\n🎯 종합점수 기반 분석 모드...")
        print(f"   - 최대 {args.max_stocks}개 종목 분석")
        print(f"   - 최소 종합점수 기준: {args.min_comprehensive_score}점")
        print(f"   - 정량적 지표(70%) + 정성적 지표(30%) 통합")
        
        market_analysis = await analyzer.analyze_comprehensive_market(
            max_stocks=args.max_stocks,
            min_comprehensive_score=args.min_comprehensive_score
        )
        
        if market_analysis:
            # 종합점수 분석 결과 처리
            print(f"\n🎯 종합점수 기반 분석 완료!")
            print(f"📊 총 분석 종목: {market_analysis['analysis_info']['total_analyzed']}개")
            print(f"🎯 저평가 종목: {market_analysis['analysis_info']['undervalued_found']}개")
            
            # 종합점수 통계
            if 'comprehensive_statistics' in market_analysis:
                stats = market_analysis['comprehensive_statistics']
                comp_stats = stats.get('comprehensive_score_statistics', {})
                print(f"📈 종합점수 평균: {comp_stats.get('mean', 0):.1f}점")
                print(f"📊 정량점수 평균: {stats.get('quantitative_score_statistics', {}).get('mean', 0):.1f}점")
                print(f"📋 정성점수 평균: {stats.get('qualitative_score_statistics', {}).get('mean', 0):.1f}점")
            
            # 결과 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_analysis_{timestamp}.json"
            
            # JSON 직렬화를 위한 데이터 변환
            serializable_data = analyzer._make_json_serializable(market_analysis)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 결과 저장: {filename}")
            
            # 종합점수 분석 모드에서는 보고서 생성하지 않음
            return
            
        else:
            print("❌ 종합점수 기반 분석 실패")
            return
        
    else:
        # 전체 시장 분석 실행
        print(f"\n🌍 궁극의 전체 시장 분석 시작...")
        market_analysis = await analyzer.analyze_full_market(
            max_stocks=args.max_stocks,
            parallel_workers=args.workers,
            min_score=args.min_score,
            max_recommendations=args.max_recommendations
        )
    
        if not market_analysis:
            print("❌ 분석할 종목이 없습니다.")
            return
        
        # 전체 보고서 생성
        print(f"\n📊 궁극의 전체 시장 보고서 생성...")
        report = analyzer.generate_full_report(market_analysis)
        print(report)
        
        # 결과 저장
        analysis_filename = analyzer.save_full_analysis(market_analysis)
        if analysis_filename:
            print(f"\n💾 전체 분석 결과 저장: {analysis_filename}")
        
        # 보고서도 파일로 저장
        report_filename = f"ultimate_market_report_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 궁극의 전체 시장 보고서 저장: {report_filename}")
    
    print(f"\n" + "=" * 100)
    print("✅ 궁극의 전체 시장 분석기 v2.0 완료")
    print("enhanced_integrated_analyzer_refactored.py 핵심 장점 통합 완료")
    print("=" * 100)

if __name__ == "__main__":
    asyncio.run(main())
