"""
업그레이드된 가치 분석 파이프라인 모듈

6단계 통합 가치 분석 파이프라인을 제공합니다.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from metrics import MetricsCollector
from value_metrics import ValueMetricsPrecision
from margin_safety import MarginOfSafetyCalculator
from guards import InputReliabilityGuard
from quality_filter import QualityConsistencyFilter
from risk_constraints import RiskConstraintsManager
from data_models import AnalysisResult


def _monotonic() -> float:
    """Returns a monotonic time in seconds."""
    return time.monotonic()


class UpgradedValueAnalysisPipeline:
    """업그레이드된 가치 분석 파이프라인 (6단계 통합)"""
    
    def __init__(self, config_file: str = "config.yaml"):
        # Import here to avoid circular imports
        from enhanced_integrated_analyzer_refactored import (
            ConfigManager, SectorCycleContextualizer, PricePositionPolicyManager,
            RankingDiversificationManager, ValueStyleClassifier, UVSEligibilityFilter,
            EnhancedIntegratedAnalyzer
        )
        
        self.config_manager = ConfigManager(config_file)
        self.config = self.config_manager.load_config()
        self.metrics = MetricsCollector()
        
        # 6단계 파이프라인 컴포넌트 초기화
        self.input_guard = InputReliabilityGuard(self.metrics)
        self.value_precision = ValueMetricsPrecision(self.metrics)
        self.margin_calculator = MarginOfSafetyCalculator(self.metrics)
        self.quality_filter = QualityConsistencyFilter(self.metrics)
        self.risk_manager = RiskConstraintsManager(self.metrics)
        self.sector_contextualizer = SectorCycleContextualizer(self.metrics)
        self.price_policy_manager = PricePositionPolicyManager(self.metrics)
        self.diversification_manager = RankingDiversificationManager(self.metrics)
        self.style_classifier = ValueStyleClassifier(self.metrics)
        self.uvs_filter = UVSEligibilityFilter(self.metrics)
        
        # 기존 분석기 (호환성)
        self.legacy_analyzer = EnhancedIntegratedAnalyzer(config_file)
    
    def analyze_single_stock(self, symbol: str, name: str = "") -> Dict[str, Any]:
        """단일 종목 종합 분석 (6단계 파이프라인)"""
        start_time = _monotonic()
        
        result = {
            'symbol': symbol,
            'name': name,
            'pipeline_stage': 'start',
            'analysis_result': None,
            'pipeline_errors': [],
            'final_recommendation': 'PASS',
            'financial_data': {}  # 가격 데이터를 포함한 재무 데이터 저장
        }
        
        try:
            # 1단계: 입력 신뢰도 가드
            result['pipeline_stage'] = 'input_validation'
            market_cap = self.legacy_analyzer._get_market_cap(symbol)
            
            # 가격 데이터와 재무 데이터를 분리해서 가져오기
            price_data = self.legacy_analyzer.data_provider.get_price_data(symbol)
            financial_data = self.legacy_analyzer.data_provider.get_financial_data(symbol)
            
            # 가격 데이터를 재무 데이터에 병합
            if price_data:
                financial_data.update(price_data)
            
            result['financial_data'] = financial_data
            
            # 입력 신뢰도 검증
            is_reliable, error_msg, validation_result = self.input_guard.validate_input_reliability(
                symbol, market_cap, financial_data
            )
            
            if not is_reliable:
                result['pipeline_errors'].append(f"input_validation_failed: {error_msg}")
                result['final_recommendation'] = 'FAIL'
                return result
            
            # 2단계: 가치 지표 정밀화
            result['pipeline_stage'] = 'value_metrics'
            value_score_result = self.value_precision.calculate_comprehensive_value_score(
                financial_data, market_cap
            )
            
            if value_score_result['total_score'] < 30:  # 임계치 미달
                result['pipeline_errors'].append(f"low_value_score: {value_score_result['total_score']:.1f}")
                result['final_recommendation'] = 'FAIL'
                return result
            
            # 3단계: 안전마진 계산
            result['pipeline_stage'] = 'margin_safety'
            current_price = price_data.get('current_price', 0) if price_data else 0
            
            valuation_result = self.margin_calculator.calculate_comprehensive_valuation(
                symbol, current_price, financial_data, market_cap
            )
            
            # 4단계: 품질 필터
            result['pipeline_stage'] = 'quality_filter'
            quality_eligible, quality_reason, quality_result = self.quality_filter.is_eligible_for_valuation(
                symbol, financial_data
            )
            
            if not quality_eligible:
                result['pipeline_errors'].append(f"quality_filter_failed: {quality_reason}")
                result['final_recommendation'] = 'FAIL'
                return result
            
            # 5단계: 리스크 제약
            result['pipeline_stage'] = 'risk_constraints'
            risk_eligible, risk_reason, risk_result = self.risk_manager.is_eligible_after_risk_check(
                symbol, financial_data
            )
            
            if not risk_eligible:
                result['pipeline_errors'].append(f"risk_constraints_failed: {risk_reason}")
                result['final_recommendation'] = 'FAIL'
                return result
            
            # 6단계: 최종 종합 분석
            result['pipeline_stage'] = 'final_analysis'
            
            # 기존 분석기로 종합 분석 수행
            analysis_result = self.legacy_analyzer.analyze_single_stock(symbol, name)
            
            if analysis_result.status.value == 'success':
                # 가치 분석 결과 추가
                analysis_result.intrinsic_value = valuation_result.get('intrinsic_value')
                analysis_result.margin_of_safety = valuation_result.get('margin_of_safety')
                analysis_result.watchlist_signal = valuation_result.get('investment_signal')
                analysis_result.target_buy = valuation_result.get('target_buy_price')
                
                # 파이프라인 점수 계산
                pipeline_score = self._calculate_pipeline_score(
                    value_score_result, quality_result, risk_result, analysis_result
                )
                
                result['analysis_result'] = analysis_result
                result['pipeline_score'] = pipeline_score
                result['final_recommendation'] = 'BUY' if pipeline_score >= 70 else 'WATCH' if pipeline_score >= 50 else 'PASS'
            else:
                result['pipeline_errors'].append(f"legacy_analysis_failed: {analysis_result.error}")
                result['final_recommendation'] = 'FAIL'
            
        except Exception as e:
            result['pipeline_errors'].append(f"pipeline_exception: {str(e)}")
            result['final_recommendation'] = 'ERROR'
            logging.error(f"파이프라인 분석 중 예외 발생 {symbol}: {e}")
        
        finally:
            # 메트릭 기록
            duration = _monotonic() - start_time
            self.metrics.record_analysis_duration(duration)
            
            if result['final_recommendation'] in ['BUY', 'WATCH']:
                self.metrics.record_stocks_analyzed(1)
        
        return result
    
    def analyze_portfolio(self, symbols: List[Tuple[str, str]], 
                         max_stocks: int = 10) -> Dict[str, Any]:
        """포트폴리오 분석 (다중 종목)"""
        results = []
        
        for symbol, name in symbols[:max_stocks]:
            result = self.analyze_single_stock(symbol, name)
            results.append(result)
        
        # 포트폴리오 통계 계산
        portfolio_stats = self._calculate_portfolio_stats(results)
        
        return {
            'portfolio_results': results,
            'portfolio_stats': portfolio_stats,
            'total_analyzed': len(results),
            'successful_analyses': len([r for r in results if r['final_recommendation'] in ['BUY', 'WATCH']])
        }
    
    def run_pipeline(self, symbols: List[Tuple[str, str]], max_workers: int = 2, verbose: bool = False) -> List[Dict[str, Any]]:
        """파이프라인 실행 (병렬 처리)"""
        import concurrent.futures
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 각 종목에 대해 분석 작업 제출
            future_to_symbol = {
                executor.submit(self.analyze_single_stock, symbol, name): (symbol, name)
                for symbol, name in symbols
            }
            
            # 결과 수집
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol, name = future_to_symbol[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if verbose:
                        print(f"✅ {symbol} ({name}): {result['final_recommendation']} - {result.get('pipeline_score', 0):.1f}점")
                        
                except Exception as e:
                    logging.error(f"종목 분석 실패 {symbol}: {e}")
                    results.append({
                        'symbol': symbol,
                        'name': name,
                        'final_recommendation': 'ERROR',
                        'pipeline_errors': [str(e)]
                    })
        
        # 결과 정렬 (점수 순)
        results.sort(key=lambda x: x.get('pipeline_score', 0), reverse=True)
        
        return results
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """파이프라인 요약 정보"""
        return {
            'pipeline_name': 'Upgraded Value Analysis Pipeline',
            'version': '2.0',
            'stages': [
                'input_validation',
                'value_metrics',
                'margin_safety',
                'quality_filter',
                'risk_constraints',
                'final_analysis'
            ],
            'components': {
                'input_guard': 'InputReliabilityGuard',
                'value_precision': 'ValueMetricsPrecision',
                'margin_calculator': 'MarginOfSafetyCalculator',
                'quality_filter': 'QualityConsistencyFilter',
                'risk_manager': 'RiskConstraintsManager',
                'sector_contextualizer': 'SectorCycleContextualizer',
                'price_policy_manager': 'PricePositionPolicyManager',
                'diversification_manager': 'RankingDiversificationManager',
                'style_classifier': 'ValueStyleClassifier',
                'uvs_filter': 'UVSEligibilityFilter'
            }
        }
    
    def _calculate_pipeline_score(self, value_result: Dict[str, Any], quality_result: Dict[str, Any], 
                                 risk_result: Dict[str, Any], analysis_result: AnalysisResult) -> float:
        """파이프라인 종합 점수 계산"""
        # 가치 점수 (40%)
        value_score = value_result.get('total_score', 0) * 0.4
        
        # 품질 점수 (30%)
        quality_score = quality_result.get('overall_quality_score', 0) * 100 * 0.3
        
        # 리스크 점수 (20%)
        risk_score = risk_result.get('overall_risk_score', 0) * 100 * 0.2
        
        # 기존 분석 점수 (10%)
        legacy_score = analysis_result.enhanced_score * 0.1
        
        return value_score + quality_score + risk_score + legacy_score
    
    def _calculate_portfolio_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """포트폴리오 통계 계산"""
        total = len(results)
        successful = len([r for r in results if r['final_recommendation'] in ['BUY', 'WATCH']])
        buy_signals = len([r for r in results if r['final_recommendation'] == 'BUY'])
        watch_signals = len([r for r in results if r['final_recommendation'] == 'WATCH'])
        failed = len([r for r in results if r['final_recommendation'] == 'FAIL'])
        
        scores = [r.get('pipeline_score', 0) for r in results if r.get('pipeline_score') is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            'total_analyzed': total,
            'successful_analyses': successful,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'buy_signals': buy_signals,
            'watch_signals': watch_signals,
            'failed_analyses': failed,
            'average_score': avg_score,
            'score_distribution': {
                'excellent': len([s for s in scores if s >= 80]),
                'good': len([s for s in scores if 60 <= s < 80]),
                'fair': len([s for s in scores if 40 <= s < 60]),
                'poor': len([s for s in scores if s < 40])
            }
        }













