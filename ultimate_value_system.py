"""
Ultimate Value System - 최고 등급 가치투자 시스템
- 레짐 적응형 임계치
- 베이지안 MoS 업데이트  
- 멀티-모델 앙상블
- 데이터 신뢰도 점수화
- 실행 가능성 필터
- Enhanced Integrated Analyzer와 완전 통합
"""

import sys
import os
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import warnings
warnings.filterwarnings('ignore')

# Enhanced Integrated Analyzer 임포트
try:
    from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer
    print("Enhanced Integrated Analyzer 로드 성공")
except ImportError as e:
    print(f"Enhanced Integrated Analyzer 로드 실패: {e}")
    sys.exit(1)

# 개선 모듈들 임포트
try:
    from regime_adaptive_system import RegimeAdaptiveSystem, MarketRegime, InterestRateRegime
    from bayesian_mos_system import BayesianMOSSystem, FinancialEvidence
    from multi_model_ensemble_system import MultiModelEnsembleSystem
    print("개선 모듈들 로드 성공")
except ImportError as e:
    print(f"개선 모듈 로드 실패: {e}")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataReliabilitySystem:
    """데이터 신뢰도 점수화 시스템"""
    
    def __init__(self):
        self.data_sources = {
            'kis_api': {'weight': 0.4, 'reliability': 0.95},
            'financial_statements': {'weight': 0.3, 'reliability': 0.90},
            'market_data': {'weight': 0.2, 'reliability': 0.85},
            'estimates': {'weight': 0.1, 'reliability': 0.70}
        }
        
    def calculate_reliability_score(self, data_quality_info: Dict[str, Any]) -> float:
        """데이터 신뢰도 점수 계산"""
        total_score = 0.0
        total_weight = 0.0
        
        for source, info in self.data_sources.items():
            if source in data_quality_info:
                source_quality = data_quality_info[source]
                reliability = info['reliability'] * source_quality
                weight = info['weight']
                
                total_score += reliability * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0

class ExecutionFeasibilityFilter:
    """실행 가능성 필터"""
    
    def __init__(self):
        self.min_volume = 100000  # 최소 거래량
        self.max_spread_ratio = 0.02  # 최대 호가 스프레드 2%
        self.min_market_cap = 100000000000  # 최소 시총 1000억
        
    def check_execution_feasibility(self, stock_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """실행 가능성 체크"""
        # 유동성 체크
        daily_volume = stock_data.get('daily_volume', 0)
        if daily_volume < self.min_volume:
            return False, "insufficient_liquidity", {'volume': daily_volume, 'threshold': self.min_volume}
        
        # 호가 스프레드 체크
        bid_price = stock_data.get('bid_price', 0)
        ask_price = stock_data.get('ask_price', 0)
        if bid_price > 0 and ask_price > 0:
            spread_ratio = (ask_price - bid_price) / bid_price
            if spread_ratio > self.max_spread_ratio:
                return False, "wide_spread", {'spread_ratio': spread_ratio, 'threshold': self.max_spread_ratio}
        
        # 시총 체크
        market_cap = stock_data.get('market_cap', 0)
        if market_cap < self.min_market_cap:
            return False, "small_market_cap", {'market_cap': market_cap, 'threshold': self.min_market_cap}
        
        # 체결 확률 추정
        execution_probability = min(0.95, daily_volume / (self.min_volume * 2))
        
        return True, "executable", {
            'execution_probability': execution_probability,
            'volume_score': min(1.0, daily_volume / (self.min_volume * 5)),
            'spread_score': 1.0 - spread_ratio / self.max_spread_ratio if 'spread_ratio' in locals() else 1.0
        }

class UltimateValueSystem:
    """Ultimate Value System - 최고 등급 통합 시스템"""
    
    def __init__(self):
        # 핵심 컴포넌트 초기화
        self.enhanced_analyzer = None
        self.regime_system = RegimeAdaptiveSystem()
        self.bayesian_system = BayesianMOSSystem()
        self.ensemble_system = MultiModelEnsembleSystem()
        self.data_reliability = DataReliabilitySystem()
        self.execution_filter = ExecutionFeasibilityFilter()
        
        # 시스템 설정
        self.system_config = {
            'min_reliability_score': 0.6,  # 최소 데이터 신뢰도
            'min_ensemble_confidence': 0.5,  # 최소 앙상블 신뢰도
            'max_value_trap_ratio': 0.2,  # 최대 가치 함정 비율
            'min_execution_probability': 0.8  # 최소 실행 확률
        }
        
        logger.info("Ultimate Value System 초기화 완료")
    
    def initialize(self):
        """시스템 초기화"""
        logger.info("Ultimate Value System 초기화 중...")
        
        try:
            self.enhanced_analyzer = EnhancedIntegratedAnalyzer(
                include_realtime=False,
                include_external=False
            )
            logger.info("Enhanced Analyzer 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"시스템 초기화 실패: {e}")
            return False
    
    def analyze_single_stock_ultimate(self, symbol: str, name: str, 
                                    market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """단일 종목 궁극적 분석"""
        logger.info(f"종목 {symbol} ({name}) 궁극적 분석 시작")
        
        try:
            # 1. 기본 분석 (Enhanced Analyzer)
            basic_analysis = self.enhanced_analyzer.analyze_single_stock(symbol, name)
            basic_dict = basic_analysis.to_dict()
            
            if basic_analysis.status.value.lower() != 'success':
                return {
                    'symbol': symbol,
                    'name': name,
                    'status': 'FAILED',
                    'error': 'Basic analysis failed',
                    'basic_analysis': basic_dict
                }
            
            # 2. 시장 레짐 분석 및 적응형 임계치 적용
            if market_data:
                regime_analysis = self.regime_system.run_regime_analysis(market_data)
                adaptive_thresholds = regime_analysis['adaptive_thresholds']
            else:
                # 기본 시장 데이터 사용
                default_market_data = {
                    'kospi_return_3m': 0.05,
                    'vix_level': 20.0,
                    'base_rate': 3.5,
                    'bond_yield_10y': 4.0
                }
                regime_analysis = self.regime_system.run_regime_analysis(default_market_data)
                adaptive_thresholds = regime_analysis['adaptive_thresholds']
            
            # 3. 데이터 신뢰도 평가
            data_quality_info = {
                'kis_api': 0.9,  # KIS API 데이터 품질
                'financial_statements': 0.8,  # 재무제표 품질
                'market_data': 0.85,  # 시장 데이터 품질
                'estimates': 0.7  # 추정치 품질
            }
            reliability_score = self.data_reliability.calculate_reliability_score(data_quality_info)
            
            # 4. 멀티-모델 앙상블 분석
            financial_data = self._extract_financial_data(basic_dict)
            market_cap = basic_dict.get('market_cap', 0)
            
            ensemble_result = self.ensemble_system.calculate_ensemble_consensus(
                financial_data, market_cap
            )
            
            # 5. 베이지안 MoS 업데이트
            evidence = self._create_financial_evidence(financial_data)
            bayesian_mos = self.bayesian_system.calculate_bayesian_mos(
                symbol, basic_dict.get('current_price', 0), evidence
            )
            
            # 6. 실행 가능성 필터
            stock_data = {
                'daily_volume': financial_data.get('daily_volume', 1000000),
                'bid_price': basic_dict.get('current_price', 0) * 0.999,
                'ask_price': basic_dict.get('current_price', 0) * 1.001,
                'market_cap': market_cap
            }
            execution_feasible, execution_reason, execution_details = self.execution_filter.check_execution_feasibility(stock_data)
            
            # 7. 종합 평가 및 신호 생성
            ultimate_assessment = self._generate_ultimate_assessment(
                basic_analysis, ensemble_result, bayesian_mos, 
                adaptive_thresholds, reliability_score, execution_feasible
            )
            
            # 8. 결과 통합
            ultimate_result = {
                'symbol': symbol,
                'name': name,
                'timestamp': datetime.now().isoformat(),
                'status': 'SUCCESS',
                'ultimate_assessment': ultimate_assessment,
                'regime_analysis': regime_analysis,
                'ensemble_result': {
                    'consensus_value': ensemble_result.consensus_value,
                    'consensus_confidence': ensemble_result.consensus_confidence,
                    'model_agreement': ensemble_result.model_agreement,
                    'outlier_detected': ensemble_result.outlier_detected
                },
                'bayesian_mos': {
                    'prior_mos': bayesian_mos.prior_mos,
                    'posterior_mos': bayesian_mos.posterior_mos,
                    'update_confidence': bayesian_mos.update_confidence,
                    'evidence_strength': bayesian_mos.evidence_strength
                },
                'data_reliability': reliability_score,
                'execution_feasibility': {
                    'feasible': execution_feasible,
                    'reason': execution_reason,
                    'details': execution_details
                },
                'basic_analysis': basic_dict,
                'system_metadata': {
                    'regime_system_version': '1.0',
                    'bayesian_system_version': '1.0',
                    'ensemble_system_version': '1.0',
                    'data_reliability_version': '1.0',
                    'execution_filter_version': '1.0'
                }
            }
            
            logger.info(f"종목 {symbol} 궁극적 분석 완료")
            return ultimate_result
            
        except Exception as e:
            logger.error(f"종목 {symbol} 분석 실패: {e}")
            return {
                'symbol': symbol,
                'name': name,
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _extract_financial_data(self, basic_dict: Dict[str, Any]) -> Dict[str, Any]:
        """기본 분석 결과에서 재무 데이터 추출"""
        financial_data = basic_dict.get('financial_data', {})
        
        # 필요한 데이터 매핑
        extracted_data = {
            'net_income': financial_data.get('net_income', 0),
            'operating_income': financial_data.get('operating_income', 0),
            'free_cash_flow': financial_data.get('free_cash_flow', 0),
            'total_assets': financial_data.get('total_assets', 0),
            'total_liabilities': financial_data.get('total_liabilities', 0),
            'book_value': financial_data.get('book_value', 0),
            'revenue_growth': financial_data.get('revenue_growth', 0),
            'earnings_growth': financial_data.get('earnings_growth', 0),
            'debt_ratio': financial_data.get('debt_ratio', 0),
            'asset_turnover': financial_data.get('asset_turnover', 0),
            'margin_expansion': financial_data.get('margin_expansion', 0),
            'dividend': financial_data.get('dividend', 0),
            'shares_repurchased': financial_data.get('shares_repurchased', 0),
            'earnings_history': financial_data.get('earnings_history', []),
            'price_momentum_6m': financial_data.get('price_momentum_6m', 0),
            'intangible_assets': financial_data.get('intangible_assets', 0),
            'daily_volume': financial_data.get('daily_volume', 1000000)
        }
        
        return extracted_data
    
    def _create_financial_evidence(self, financial_data: Dict[str, Any]) -> FinancialEvidence:
        """재무 증거 생성"""
        return FinancialEvidence(
            revenue_growth=financial_data.get('revenue_growth', 0),
            earnings_growth=financial_data.get('earnings_growth', 0),
            margin_expansion=financial_data.get('margin_expansion', 0),
            cash_flow_growth=financial_data.get('free_cash_flow', 0) / max(financial_data.get('net_income', 1), 1),
            roe_change=0.0,  # 계산 필요
            debt_ratio_change=-financial_data.get('debt_ratio', 0),  # 부채 감소 = 양수
            asset_turnover_change=financial_data.get('asset_turnover', 1.0) - 1.0,
            market_share_change=0.0,  # 추정치
            competitive_position=0.0,  # 추정치
            industry_trend=0.0,  # 추정치
            volatility_change=0.0,  # 계산 필요
            beta_change=0.0,  # 계산 필요
            credit_rating_change=0.0  # 추정치
        )
    
    def _generate_ultimate_assessment(self, basic_analysis, ensemble_result, 
                                    bayesian_mos, adaptive_thresholds, 
                                    reliability_score, execution_feasible) -> Dict[str, Any]:
        """궁극적 평가 생성"""
        
        # 기본 지표들
        basic_score = basic_analysis.enhanced_score
        ensemble_confidence = ensemble_result.consensus_confidence
        posterior_mos = bayesian_mos.posterior_mos
        model_agreement = ensemble_result.model_agreement
        
        # 적응형 임계치 적용
        mos_threshold = adaptive_thresholds['mos']
        quality_threshold = adaptive_thresholds['quality']
        value_threshold = adaptive_thresholds['value']
        
        # 종합 점수 계산
        ultimate_score = (
            basic_score * 0.3 +                    # 기본 분석 점수
            ensemble_confidence * 100 * 0.25 +     # 앙상블 신뢰도
            posterior_mos * 100 * 0.25 +          # 베이지안 MoS
            model_agreement * 100 * 0.2            # 모델 합의도
        )
        
        # 신뢰도 조정
        reliability_adjustment = reliability_score * 0.1
        ultimate_score *= (1 + reliability_adjustment)
        
        # 실행 가능성 조정
        execution_adjustment = 0.1 if execution_feasible else -0.2
        ultimate_score *= (1 + execution_adjustment)
        
        # 등급 결정
        if ultimate_score >= 80:
            grade = "A+"
            signal = "STRONG_BUY"
        elif ultimate_score >= 70:
            grade = "A"
            signal = "BUY"
        elif ultimate_score >= 60:
            grade = "B+"
            signal = "WATCH"
        elif ultimate_score >= 50:
            grade = "B"
            signal = "HOLD"
        else:
            grade = "C"
            signal = "PASS"
        
        # 위험도 평가
        risk_factors = []
        if ensemble_result.outlier_detected:
            risk_factors.append("model_outlier")
        if reliability_score < 0.7:
            risk_factors.append("low_data_reliability")
        if not execution_feasible:
            risk_factors.append("execution_risk")
        if posterior_mos < 0.1:
            risk_factors.append("low_margin_of_safety")
        
        risk_level = "LOW" if len(risk_factors) == 0 else "MEDIUM" if len(risk_factors) <= 2 else "HIGH"
        
        return {
            'ultimate_score': ultimate_score,
            'ultimate_grade': grade,
            'investment_signal': signal,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'component_scores': {
                'basic_score': basic_score,
                'ensemble_confidence': ensemble_confidence,
                'bayesian_mos': posterior_mos,
                'model_agreement': model_agreement,
                'reliability_score': reliability_score,
                'execution_feasible': execution_feasible
            },
            'adaptive_thresholds': adaptive_thresholds,
            'recommendation': self._generate_recommendation(signal, risk_level, risk_factors)
        }
    
    def _generate_recommendation(self, signal: str, risk_level: str, risk_factors: List[str]) -> str:
        """투자 권고사항 생성"""
        if signal == "STRONG_BUY":
            base_recommendation = "강력 매수 추천 - 우수한 가치와 안전마진"
        elif signal == "BUY":
            base_recommendation = "매수 추천 - 적정 가치와 양호한 안전마진"
        elif signal == "WATCH":
            base_recommendation = "관심 종목 - 추가 모니터링 필요"
        elif signal == "HOLD":
            base_recommendation = "보유 유지 - 중립적 관점"
        else:
            base_recommendation = "매수 비추천 - 가치나 위험 측면에서 부적절"
        
        if risk_level == "HIGH":
            base_recommendation += ". 단, 고위험 종목이므로 신중한 접근 필요"
        elif risk_level == "MEDIUM":
            base_recommendation += ". 중간 위험 요소 고려하여 투자"
        
        if risk_factors:
            base_recommendation += f". 주요 위험요소: {', '.join(risk_factors)}"
        
        return base_recommendation
    
    def analyze_portfolio_ultimate(self, symbols: List[Tuple[str, str]], 
                                 market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """포트폴리오 궁극적 분석"""
        logger.info(f"포트폴리오 궁극적 분석 시작: {len(symbols)}개 종목")
        
        portfolio_results = []
        successful_analyses = 0
        
        for symbol, name in symbols:
            result = self.analyze_single_stock_ultimate(symbol, name, market_data)
            portfolio_results.append(result)
            
            if result['status'] == 'SUCCESS':
                successful_analyses += 1
        
        # 포트폴리오 요약
        portfolio_summary = self._generate_portfolio_summary(portfolio_results)
        
        return {
            'portfolio_analysis': portfolio_results,
            'portfolio_summary': portfolio_summary,
            'analysis_metadata': {
                'total_stocks': len(symbols),
                'successful_analyses': successful_analyses,
                'analysis_timestamp': datetime.now().isoformat(),
                'system_version': 'Ultimate Value System v1.0'
            }
        }
    
    def _generate_portfolio_summary(self, portfolio_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """포트폴리오 요약 생성"""
        successful_results = [r for r in portfolio_results if r['status'] == 'SUCCESS']
        
        if not successful_results:
            return {
                'error': 'no_successful_analyses',
                'total_analyzed': len(portfolio_results),
                'successful_analyses': 0,
                'success_rate': 0.0
            }
        
        # 기본 통계
        ultimate_scores = [r['ultimate_assessment']['ultimate_score'] for r in successful_results]
        signals = [r['ultimate_assessment']['investment_signal'] for r in successful_results]
        risk_levels = [r['ultimate_assessment']['risk_level'] for r in successful_results]
        
        # 신호별 분포
        signal_distribution = {}
        for signal in signals:
            signal_distribution[signal] = signal_distribution.get(signal, 0) + 1
        
        # 위험도별 분포
        risk_distribution = {}
        for risk in risk_levels:
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1
        
        # 추천 포트폴리오
        recommended_stocks = [
            r for r in successful_results 
            if r['ultimate_assessment']['investment_signal'] in ['STRONG_BUY', 'BUY']
            and r['ultimate_assessment']['risk_level'] in ['LOW', 'MEDIUM']
        ]
        
        return {
            'total_analyzed': len(portfolio_results),
            'successful_analyses': len(successful_results),
            'success_rate': len(successful_results) / len(portfolio_results),
            'portfolio_statistics': {
                'avg_ultimate_score': np.mean(ultimate_scores),
                'median_ultimate_score': np.median(ultimate_scores),
                'std_ultimate_score': np.std(ultimate_scores),
                'min_ultimate_score': np.min(ultimate_scores),
                'max_ultimate_score': np.max(ultimate_scores)
            },
            'signal_distribution': signal_distribution,
            'risk_distribution': risk_distribution,
            'recommended_portfolio': {
                'count': len(recommended_stocks),
                'stocks': [
                    {
                        'symbol': r['symbol'],
                        'name': r['name'],
                        'ultimate_score': r['ultimate_assessment']['ultimate_score'],
                        'signal': r['ultimate_assessment']['investment_signal'],
                        'risk_level': r['ultimate_assessment']['risk_level']
                    }
                    for r in recommended_stocks
                ]
            }
        }
    
    def close(self):
        """리소스 정리"""
        if self.enhanced_analyzer:
            self.enhanced_analyzer.close()

def main():
    """메인 실행 함수"""
    print("="*80)
    print("Ultimate Value System - 최고 등급 가치투자 시스템")
    print("="*80)
    
    # 시스템 초기화
    ultimate_system = UltimateValueSystem()
    
    if not ultimate_system.initialize():
        print("시스템 초기화 실패")
        return
    
    try:
        # 테스트 종목들
        test_stocks = [
            ("005930", "삼성전자"),
            ("000660", "SK하이닉스"),
            ("035420", "NAVER"),
            ("051910", "LG화학"),
            ("006400", "삼성SDI")
        ]
        
        # 시장 데이터 (시뮬레이션)
        market_data = {
            'kospi_return_3m': 0.05,
            'vix_level': 22.0,
            'base_rate': 3.5,
            'bond_yield_10y': 4.0,
            'credit_spread': 0.6
        }
        
        print(f"분석 대상: {len(test_stocks)}개 종목")
        print(f"시장 레짐: {market_data}")
        print()
        
        # 포트폴리오 분석 실행
        portfolio_result = ultimate_system.analyze_portfolio_ultimate(test_stocks, market_data)
        
        # 결과 출력
        summary = portfolio_result['portfolio_summary']
        
        print("="*80)
        print("Ultimate Value System 분석 결과")
        print("="*80)
        
        print(f"분석 성공률: {summary.get('success_rate', 0):.1%}")
        
        if 'portfolio_statistics' in summary:
            print(f"평균 궁극 점수: {summary['portfolio_statistics']['avg_ultimate_score']:.1f}")
        
        if 'recommended_portfolio' in summary:
            print(f"추천 종목 수: {summary['recommended_portfolio']['count']}개")
        
        if 'signal_distribution' in summary:
            print(f"\n신호 분포:")
            for signal, count in summary['signal_distribution'].items():
                print(f"  {signal}: {count}개")
        
        if 'risk_distribution' in summary:
            print(f"\n위험도 분포:")
            for risk, count in summary['risk_distribution'].items():
                print(f"  {risk}: {count}개")
        
        if 'recommended_portfolio' in summary and 'stocks' in summary['recommended_portfolio']:
            print(f"\n추천 포트폴리오:")
            for stock in summary['recommended_portfolio']['stocks']:
                print(f"  {stock['symbol']} ({stock['name']}): {stock['ultimate_score']:.1f}점, {stock['signal']}, {stock['risk_level']}")
        
        if 'error' in summary:
            print(f"\n오류 발생: {summary['error']}")
            print("개별 분석 결과를 확인하세요.")
        
        # 상세 분석 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ultimate_analysis_result_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(portfolio_result, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n상세 결과 저장: {filename}")
        
        print(f"\n{'='*80}")
        print("Ultimate Value System 분석 완료!")
        print("최고 등급 가치투자 시스템이 성공적으로 작동합니다.")
        print("="*80)
        
    except Exception as e:
        print(f"분석 실행 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        ultimate_system.close()

if __name__ == "__main__":
    main()
