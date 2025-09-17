# estimate_performance_analyzer_core.py
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from estimate_performance_client import EstimatePerformanceClient
from estimate_performance_models import (
    ProcessedEstimatePerformance,
    EstimatePerformanceSummary
)

logger = logging.getLogger(__name__)


class EstimatePerformanceAnalyzer:
    """추정실적 데이터를 분석하고 인사이트를 제공하는 클래스"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.client = EstimatePerformanceClient(config_path)

    def analyze_single_stock(self, symbol: str) -> Dict[str, Any]:
        """단일 종목의 추정실적을 종합 분석합니다."""
        logger.info(f"🔍 {symbol} 종목 추정실적 분석 시작")
        
        estimate_data = self.client.get_estimate_performance(symbol)
        
        if not estimate_data:
            logger.warning(f"⚠️ {symbol} 종목의 추정실적 데이터가 없습니다.")
            return {
                'symbol': symbol,
                'status': 'no_data',
                'message': '추정실적 데이터가 없습니다.'
            }
        
        summary = EstimatePerformanceSummary.from_processed_data(estimate_data)
        
        analysis = {
            'symbol': symbol,
            'status': 'success',
            'summary': summary,
            'detailed_analysis': self._perform_detailed_analysis(estimate_data),
            'trend_analysis': self._analyze_trends(estimate_data),
            'financial_health': self._analyze_financial_health(estimate_data),
            'valuation_analysis': self._analyze_valuation(estimate_data),
            'growth_analysis': self._analyze_growth(estimate_data),
            'quality_analysis': self._analyze_data_quality(estimate_data)
        }
        
        logger.info(f"✅ {symbol} 종목 분석 완료 (품질점수: {estimate_data.data_quality_score:.2f})")
        return analysis

    def analyze_multiple_stocks(self, symbols: List[str]) -> Dict[str, Any]:
        """여러 종목의 추정실적을 비교 분석합니다."""
        logger.info(f"🔍 {len(symbols)}개 종목 추정실적 비교 분석 시작")
        
        stock_analyses = {}
        for symbol in symbols:
            try:
                stock_analyses[symbol] = self.analyze_single_stock(symbol)
            except Exception as e:
                logger.error(f"❌ {symbol} 종목 분석 실패: {e}")
                stock_analyses[symbol] = {
                    'symbol': symbol,
                    'status': 'error',
                    'error': str(e)
                }
        
        comparison = self._perform_comparison_analysis(stock_analyses)
        
        return {
            'total_stocks': len(symbols),
            'successful_analyses': len([s for s in stock_analyses.values() if s.get('status') == 'success']),
            'stock_analyses': stock_analyses,
            'comparison_analysis': comparison
        }

    def analyze_high_quality_stocks(self, symbols: List[str], min_quality_score: float = 0.7) -> Dict[str, Any]:
        """데이터 품질이 높은 종목들만 분석합니다."""
        logger.info(f"🔍 고품질 추정실적 종목 분석 시작 (최소 품질점수: {min_quality_score})")
        
        high_quality_estimates = self.client.get_high_quality_estimates(symbols, min_quality_score)
        
        if not high_quality_estimates:
            return {
                'status': 'no_data',
                'message': f'품질점수 {min_quality_score} 이상인 종목이 없습니다.'
            }
        
        stock_analyses = {}
        for symbol, estimate_data in high_quality_estimates.items():
            try:
                stock_analyses[symbol] = self.analyze_single_stock(symbol)
            except Exception as e:
                logger.error(f"❌ {symbol} 종목 분석 실패: {e}")
        
        comparison = self._perform_comparison_analysis(stock_analyses)
        
        return {
            'total_stocks': len(symbols),
            'high_quality_stocks': len(high_quality_estimates),
            'min_quality_score': min_quality_score,
            'stock_analyses': stock_analyses,
            'comparison_analysis': comparison
        }

    def _perform_detailed_analysis(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """상세 분석을 수행합니다."""
        return {
            'data_completeness': self._calculate_data_completeness(estimate_data),
            'revenue_analysis': self._analyze_revenue_data(estimate_data),
            'profit_analysis': self._analyze_profit_data(estimate_data),
            'investment_metrics': self._analyze_investment_metrics(estimate_data),
            'settlement_periods': estimate_data.settlement_periods
        }

    def _analyze_trends(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """트렌드 분석을 수행합니다."""
        trends = {}
        
        if estimate_data.revenue_data:
            trends['revenue'] = self._calculate_comprehensive_trend(estimate_data.revenue_data)
        
        if estimate_data.operating_profit_data:
            trends['operating_profit'] = self._calculate_comprehensive_trend(estimate_data.operating_profit_data)
        
        if estimate_data.net_profit_data:
            trends['net_profit'] = self._calculate_comprehensive_trend(estimate_data.net_profit_data)
        
        if estimate_data.eps_data:
            trends['eps'] = self._calculate_comprehensive_trend(estimate_data.eps_data)
        
        if estimate_data.roe_data:
            trends['roe'] = self._calculate_comprehensive_trend(estimate_data.roe_data)
        
        return trends

    def _analyze_financial_health(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """재무건전성 분석을 수행합니다."""
        health_score = 0
        factors = []
        
        if estimate_data.roe_data:
            latest_roe = estimate_data.roe_data[0]
            if latest_roe > 15:
                health_score += 25
                factors.append(f"ROE 우수 ({latest_roe:.1f}%)")
            elif latest_roe > 10:
                health_score += 15
                factors.append(f"ROE 양호 ({latest_roe:.1f}%)")
            elif latest_roe > 5:
                health_score += 5
                factors.append(f"ROE 보통 ({latest_roe:.1f}%)")
            else:
                factors.append(f"ROE 낮음 ({latest_roe:.1f}%)")
        
        if estimate_data.debt_ratio_data:
            latest_debt_ratio = estimate_data.debt_ratio_data[0]
            if latest_debt_ratio < 30:
                health_score += 25
                factors.append(f"부채비율 우수 ({latest_debt_ratio:.1f}%)")
            elif latest_debt_ratio < 50:
                health_score += 15
                factors.append(f"부채비율 양호 ({latest_debt_ratio:.1f}%)")
            elif latest_debt_ratio < 100:
                health_score += 5
                factors.append(f"부채비율 보통 ({latest_debt_ratio:.1f}%)")
            else:
                factors.append(f"부채비율 높음 ({latest_debt_ratio:.1f}%)")
        
        if estimate_data.interest_coverage_data:
            latest_interest_coverage = estimate_data.interest_coverage_data[0]
            if latest_interest_coverage > 5:
                health_score += 25
                factors.append(f"이자보상배율 우수 ({latest_interest_coverage:.1f}배)")
            elif latest_interest_coverage > 3:
                health_score += 15
                factors.append(f"이자보상배율 양호 ({latest_interest_coverage:.1f}배)")
            elif latest_interest_coverage > 1:
                health_score += 5
                factors.append(f"이자보상배율 보통 ({latest_interest_coverage:.1f}배)")
            else:
                factors.append(f"이자보상배율 낮음 ({latest_interest_coverage:.1f}배)")
        
        return {
            'health_score': health_score,
            'health_grade': self._get_health_grade(health_score),
            'factors': factors,
            'max_score': 100
        }

    def _analyze_valuation(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """밸류에이션 분석을 수행합니다."""
        valuation = {}
        
        if estimate_data.per_data:
            latest_per = estimate_data.per_data[0]
            valuation['per'] = {
                'value': latest_per,
                'grade': self._get_per_grade(latest_per),
                'interpretation': self._interpret_per(latest_per)
            }
        
        if estimate_data.ev_ebitda_data:
            latest_ev_ebitda = estimate_data.ev_ebitda_data[0]
            valuation['ev_ebitda'] = {
                'value': latest_ev_ebitda,
                'grade': self._get_ev_ebitda_grade(latest_ev_ebitda),
                'interpretation': self._interpret_ev_ebitda(latest_ev_ebitda)
            }
        
        valuation_score = 0
        if 'per' in valuation:
            per_grade = valuation['per']['grade']
            if per_grade == 'A': valuation_score += 50
            elif per_grade == 'B': valuation_score += 35
            elif per_grade == 'C': valuation_score += 20
            else: valuation_score += 5
        
        if 'ev_ebitda' in valuation:
            ev_ebitda_grade = valuation['ev_ebitda']['grade']
            if ev_ebitda_grade == 'A': valuation_score += 50
            elif ev_ebitda_grade == 'B': valuation_score += 35
            elif ev_ebitda_grade == 'C': valuation_score += 20
            else: valuation_score += 5
        
        valuation['overall_score'] = valuation_score
        valuation['overall_grade'] = self._get_valuation_grade(valuation_score)
        
        return valuation

    def _analyze_growth(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """성장성 분석을 수행합니다."""
        growth = {}
        
        if estimate_data.revenue_growth_data:
            latest_revenue_growth = estimate_data.revenue_growth_data[0]
            growth['revenue_growth'] = {
                'value': latest_revenue_growth,
                'grade': self._get_growth_grade(latest_revenue_growth),
                'interpretation': self._interpret_growth(latest_revenue_growth)
            }
        
        if estimate_data.operating_profit_growth_data:
            latest_profit_growth = estimate_data.operating_profit_growth_data[0]
            growth['profit_growth'] = {
                'value': latest_profit_growth,
                'grade': self._get_growth_grade(latest_profit_growth),
                'interpretation': self._interpret_growth(latest_profit_growth)
            }
        
        if estimate_data.eps_growth_data:
            latest_eps_growth = estimate_data.eps_growth_data[0]
            growth['eps_growth'] = {
                'value': latest_eps_growth,
                'grade': self._get_growth_grade(latest_eps_growth),
                'interpretation': self._interpret_growth(latest_eps_growth)
            }
        
        return growth

    def _analyze_data_quality(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """데이터 품질 분석을 수행합니다."""
        return {
            'quality_score': estimate_data.data_quality_score,
            'quality_grade': self._get_quality_grade(estimate_data.data_quality_score),
            'completeness': self._calculate_data_completeness(estimate_data),
            'consistency': self._calculate_data_consistency(estimate_data),
            'latest_update': estimate_data.latest_update_date
        }

    def _calculate_data_completeness(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """데이터 완성도를 계산합니다."""
        indicators = [
            ('매출액', estimate_data.revenue_data),
            ('영업이익', estimate_data.operating_profit_data),
            ('순이익', estimate_data.net_profit_data),
            ('EPS', estimate_data.eps_data),
            ('PER', estimate_data.per_data),
            ('ROE', estimate_data.roe_data)
        ]
        
        total_indicators = len(indicators)
        available_indicators = 0
        
        for name, data in indicators:
            if data and any(val != 0 for val in data):
                available_indicators += 1
        
        completeness_rate = (available_indicators / total_indicators) * 100 if total_indicators > 0 else 0
        
        return {
            'rate': completeness_rate,
            'available_indicators': available_indicators,
            'total_indicators': total_indicators,
            'grade': self._get_completeness_grade(completeness_rate)
        }

    def _calculate_data_consistency(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """데이터 일관성을 계산합니다."""
        consistency_score = 1.0
        
        indicators = [
            estimate_data.revenue_data,
            estimate_data.operating_profit_data,
            estimate_data.net_profit_data,
            estimate_data.eps_data
        ]
        
        for data in indicators:
            if data and len(data) > 1:
                non_zero_values = [val for val in data if val != 0]
                if len(non_zero_values) > 1:
                    for i in range(1, len(non_zero_values)):
                        if non_zero_values[i-1] != 0:
                            change_ratio = abs(non_zero_values[i] / non_zero_values[i-1])
                            if change_ratio > 10:
                                consistency_score *= 0.9
        
        return {
            'score': consistency_score,
            'grade': self._get_consistency_grade(consistency_score)
        }

    def _perform_comparison_analysis(self, stock_analyses: Dict[str, Any]) -> Dict[str, Any]:
        """종목 간 비교 분석을 수행합니다."""
        successful_analyses = {k: v for k, v in stock_analyses.items() if v.get('status') == 'success'}
        
        if not successful_analyses:
            return {'status': 'no_data'}
        
        comparisons = {}
        
        per_values = {}
        for symbol, analysis in successful_analyses.items():
            if 'valuation_analysis' in analysis and 'per' in analysis['valuation_analysis']:
                per_values[symbol] = analysis['valuation_analysis']['per']['value']
        
        if per_values:
            comparisons['per_ranking'] = sorted(per_values.items(), key=lambda x: x[1])
        
        roe_values = {}
        for symbol, analysis in successful_analyses.items():
            summary = analysis.get('summary')
            if summary and summary.latest_roe:
                roe_values[symbol] = summary.latest_roe
        
        if roe_values:
            comparisons['roe_ranking'] = sorted(roe_values.items(), key=lambda x: x[1], reverse=True)
        
        return comparisons

    def _calculate_comprehensive_trend(self, data: List[float]) -> Dict[str, Any]:
        """포괄적인 트렌드 분석을 수행합니다."""
        if not data or len(data) < 2:
            return {'direction': '데이터부족', 'strength': 0, 'volatility': 0}
        
        valid_data = [val for val in data if val != 0]
        if len(valid_data) < 2:
            return {'direction': '데이터부족', 'strength': 0, 'volatility': 0}
        
        recent_3 = valid_data[:3] if len(valid_data) >= 3 else valid_data
        
        if len(recent_3) >= 2:
            if recent_3[0] > recent_3[1]:
                direction = "상승"
                if len(recent_3) >= 3 and recent_3[1] > recent_3[2]:
                    direction = "강한 상승"
            elif recent_3[0] < recent_3[1]:
                direction = "하락"
                if len(recent_3) >= 3 and recent_3[1] < recent_3[2]:
                    direction = "강한 하락"
            else:
                direction = "보합"
        else:
            direction = "보합"
        
        if len(valid_data) >= 2:
            max_val = max(valid_data)
            min_val = min(valid_data)
            if max_val > min_val:
                strength = ((recent_3[0] - min_val) / (max_val - min_val)) * 100
            else:
                strength = 50
        else:
            strength = 0
        
        if len(valid_data) > 1:
            mean_val = sum(valid_data) / len(valid_data)
            variance = sum((val - mean_val) ** 2 for val in valid_data) / len(valid_data)
            volatility = (variance ** 0.5) / abs(mean_val) * 100 if mean_val != 0 else 0
        else:
            volatility = 0
        
        return {
            'direction': direction,
            'strength': strength,
            'volatility': volatility,
            'data_points': len(valid_data)
        }

    # 등급 및 해석 메서드들
    def _get_health_grade(self, score: float) -> str:
        if score >= 80: return 'A'
        elif score >= 60: return 'B'
        elif score >= 40: return 'C'
        elif score >= 20: return 'D'
        else: return 'F'

    def _get_per_grade(self, per: float) -> str:
        if per <= 10: return 'A'
        elif per <= 15: return 'B'
        elif per <= 25: return 'C'
        elif per <= 50: return 'D'
        else: return 'F'

    def _get_ev_ebitda_grade(self, ev_ebitda: float) -> str:
        if ev_ebitda <= 8: return 'A'
        elif ev_ebitda <= 12: return 'B'
        elif ev_ebitda <= 20: return 'C'
        elif ev_ebitda <= 30: return 'D'
        else: return 'F'

    def _get_growth_grade(self, growth: float) -> str:
        if growth >= 20: return 'A'
        elif growth >= 10: return 'B'
        elif growth >= 0: return 'C'
        elif growth >= -10: return 'D'
        else: return 'F'

    def _get_quality_grade(self, score: float) -> str:
        if score >= 0.9: return 'A'
        elif score >= 0.7: return 'B'
        elif score >= 0.5: return 'C'
        elif score >= 0.3: return 'D'
        else: return 'F'

    def _get_completeness_grade(self, rate: float) -> str:
        if rate >= 90: return 'A'
        elif rate >= 70: return 'B'
        elif rate >= 50: return 'C'
        elif rate >= 30: return 'D'
        else: return 'F'

    def _get_consistency_grade(self, score: float) -> str:
        if score >= 0.9: return 'A'
        elif score >= 0.7: return 'B'
        elif score >= 0.5: return 'C'
        elif score >= 0.3: return 'D'
        else: return 'F'

    def _get_valuation_grade(self, score: float) -> str:
        if score >= 80: return 'A'
        elif score >= 60: return 'B'
        elif score >= 40: return 'C'
        elif score >= 20: return 'D'
        else: return 'F'

    def _interpret_per(self, per: float) -> str:
        if per <= 10: return "매우 저평가"
        elif per <= 15: return "저평가"
        elif per <= 25: return "적정가"
        elif per <= 50: return "고평가"
        else: return "매우 고평가"

    def _interpret_ev_ebitda(self, ev_ebitda: float) -> str:
        if ev_ebitda <= 8: return "매우 저평가"
        elif ev_ebitda <= 12: return "저평가"
        elif ev_ebitda <= 20: return "적정가"
        elif ev_ebitda <= 30: return "고평가"
        else: return "매우 고평가"

    def _interpret_growth(self, growth: float) -> str:
        if growth >= 20: return "매우 높은 성장"
        elif growth >= 10: return "높은 성장"
        elif growth >= 0: return "안정적 성장"
        elif growth >= -10: return "성장 둔화"
        else: return "성장 정체"

    def _analyze_revenue_data(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """매출액 데이터 분석"""
        return {
            'latest_value': estimate_data.revenue_data[0] if estimate_data.revenue_data else 0,
            'growth_rate': estimate_data.revenue_growth_data[0] if estimate_data.revenue_growth_data else 0,
            'data_points': len(estimate_data.revenue_data)
        }

    def _analyze_profit_data(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """이익 데이터 분석"""
        return {
            'operating_profit': estimate_data.operating_profit_data[0] if estimate_data.operating_profit_data else 0,
            'net_profit': estimate_data.net_profit_data[0] if estimate_data.net_profit_data else 0,
            'operating_growth': estimate_data.operating_profit_growth_data[0] if estimate_data.operating_profit_growth_data else 0,
            'net_growth': estimate_data.net_profit_growth_data[0] if estimate_data.net_profit_growth_data else 0
        }

    def _analyze_investment_metrics(self, estimate_data: ProcessedEstimatePerformance) -> Dict[str, Any]:
        """투자지표 분석"""
        return {
            'eps': estimate_data.eps_data[0] if estimate_data.eps_data else 0,
            'per': estimate_data.per_data[0] if estimate_data.per_data else 0,
            'roe': estimate_data.roe_data[0] if estimate_data.roe_data else 0,
            'ev_ebitda': estimate_data.ev_ebitda_data[0] if estimate_data.ev_ebitda_data else 0,
            'debt_ratio': estimate_data.debt_ratio_data[0] if estimate_data.debt_ratio_data else 0,
            'interest_coverage': estimate_data.interest_coverage_data[0] if estimate_data.interest_coverage_data else 0
        }

    def generate_report(self, analysis_result: Dict[str, Any], format: str = 'text') -> str:
        """분석 결과를 보고서 형태로 생성합니다."""
        if analysis_result.get('status') != 'success':
            return f"분석 실패: {analysis_result.get('message', '알 수 없는 오류')}"
        
        symbol = analysis_result['symbol']
        summary = analysis_result['summary']
        
        report = f"""
📊 추정실적 분석 보고서
{'='*50}

📈 종목: {symbol} ({summary.name})
💰 현재가: {summary.current_price:,}원 ({summary.change_rate:+.2f}%)

📋 핵심 지표:
  • 매출액: {summary.latest_revenue:,.0f}원 (성장률: {summary.latest_revenue_growth:+.1f}%)
  • 영업이익: {summary.latest_operating_profit:,.0f}원 (성장률: {summary.latest_operating_profit_growth:+.1f}%)
  • 순이익: {summary.latest_net_profit:,.0f}원 (성장률: {summary.latest_net_profit_growth:+.1f}%)
  • EPS: {summary.latest_eps:,.0f}원
  • PER: {summary.latest_per:.1f}배
  • ROE: {summary.latest_roe:.1f}%
  • EV/EBITDA: {summary.latest_ev_ebitda:.1f}배

📈 트렌드:
  • 매출액: {summary.revenue_trend}
  • 영업이익: {summary.profit_trend}
  • EPS: {summary.eps_trend}

📊 데이터 품질: {summary.data_quality_score:.2f} ({self._get_quality_grade(summary.data_quality_score)}등급)
📅 최근 업데이트: {summary.latest_update_date}
"""
        
        return report

    def export_to_dataframe(self, analysis_result: Dict[str, Any]) -> pd.DataFrame:
        """분석 결과를 DataFrame으로 변환합니다."""
        if analysis_result.get('status') != 'success':
            return pd.DataFrame()
        
        summary = analysis_result['summary']
        
        data = {
            'symbol': [summary.symbol],
            'name': [summary.name],
            'current_price': [summary.current_price],
            'change_rate': [summary.change_rate],
            'latest_revenue': [summary.latest_revenue],
            'latest_revenue_growth': [summary.latest_revenue_growth],
            'latest_operating_profit': [summary.latest_operating_profit],
            'latest_operating_profit_growth': [summary.latest_operating_profit_growth],
            'latest_net_profit': [summary.latest_net_profit],
            'latest_net_profit_growth': [summary.latest_net_profit_growth],
            'latest_eps': [summary.latest_eps],
            'latest_per': [summary.latest_per],
            'latest_roe': [summary.latest_roe],
            'latest_ev_ebitda': [summary.latest_ev_ebitda],
            'revenue_trend': [summary.revenue_trend],
            'profit_trend': [summary.profit_trend],
            'eps_trend': [summary.eps_trend],
            'data_quality_score': [summary.data_quality_score],
            'latest_update_date': [summary.latest_update_date]
        }
        
        return pd.DataFrame(data)
