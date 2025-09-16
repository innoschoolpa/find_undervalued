#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성장성비율 분석 모듈
KIS API 국내주식 성장성비율 API를 활용한 성장성비율 분석
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class GrowthRatioAnalyzer:
    """성장성비율 분석 클래스"""
    
    def __init__(self, provider):
        self.provider = provider
        self.last_request_time = 0
        self.request_interval = 2.5  # API 요청 간격 제어 (2.5초)
    
    def _rate_limit(self):
        """API 요청 속도를 제어합니다."""
        elapsed_time = time.time() - self.last_request_time
        if elapsed_time < self.request_interval:
            time.sleep(self.request_interval - elapsed_time)
        self.last_request_time = time.time()
    
    def _to_float(self, value: Any, default: float = 0.0) -> float:
        """안전하게 float 타입으로 변환합니다."""
        if value is None or value == '' or str(value) == '0':
            return default
        try:
            # 쉼표 제거 후 float 변환
            return float(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return default
    
    def get_growth_ratios(self, symbol: str, period_type: str = "0") -> Optional[List[Dict[str, Any]]]:
        """
        종목의 성장성비율을 조회합니다.
        
        Args:
            symbol: 종목코드 (6자리)
            period_type: 분류 구분 코드 (0: 년, 1: 분기)
        
        Returns:
            성장성비율 데이터 리스트
        """
        self._rate_limit()
        
        path = "/uapi/domestic-stock/v1/finance/growth-ratio"
        params = {
            "fid_input_iscd": symbol,
            "fid_div_cls_code": period_type,  # 0: 년, 1: 분기
            "fid_cond_mrkt_div_code": "J"     # 국내주식
        }
        
        try:
            data = self.provider._send_request(path, "FHKST66430800", params)
            if data and 'output' in data:
                return self._parse_growth_ratio_data(data['output'])
            else:
                logger.warning(f"⚠️ {symbol} 성장성비율 조회 실패")
                return None
                
        except Exception as e:
            logger.error(f"❌ 성장성비율 API 호출 실패 ({symbol}): {e}")
            return None
    
    def _parse_growth_ratio_data(self, output_list: List[Dict]) -> List[Dict[str, Any]]:
        """성장성비율 응답 데이터를 파싱합니다."""
        parsed_data = []
        
        for item in output_list:
            parsed_item = {
                'period': item.get('stac_yymm', ''),
                'revenue_growth_rate': self._to_float(item.get('grs', 0)),  # 매출액 증가율
                'operating_income_growth_rate': self._to_float(item.get('bsop_prfi_inrt', 0)),  # 영업이익 증가율
                'equity_growth_rate': self._to_float(item.get('equt_inrt', 0)),  # 자기자본 증가율
                'total_asset_growth_rate': self._to_float(item.get('totl_aset_inrt', 0))  # 총자산 증가율
            }
            
            # 추가 계산 지표
            parsed_item.update(self._calculate_additional_metrics(parsed_item))
            parsed_data.append(parsed_item)
        
        return parsed_data
    
    def _calculate_additional_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """추가 성장성 지표를 계산합니다."""
        metrics = {}
        
        # 성장성 점수 계산
        metrics['growth_score'] = self._calculate_growth_score(data)
        
        # 성장성 등급 평가
        metrics['growth_grade'] = self._evaluate_growth_grade(data)
        
        # 성장성 안정성 평가
        metrics['growth_stability'] = self._evaluate_growth_stability(data)
        
        # 성장성 품질 평가
        metrics['growth_quality'] = self._evaluate_growth_quality(data)
        
        # 종합 성장성 점수
        metrics['total_growth_score'] = self._calculate_total_growth_score(data, metrics)
        
        return metrics
    
    def _calculate_growth_score(self, data: Dict[str, Any]) -> float:
        """성장성 점수를 계산합니다."""
        revenue_growth = data['revenue_growth_rate']
        operating_growth = data['operating_income_growth_rate']
        equity_growth = data['equity_growth_rate']
        asset_growth = data['total_asset_growth_rate']
        
        # 각 지표별 점수 계산 (0-100점)
        revenue_score = min(100, max(0, revenue_growth * 2))  # 매출 증가율 * 2
        operating_score = min(100, max(0, operating_growth * 2))  # 영업이익 증가율 * 2
        equity_score = min(100, max(0, equity_growth * 2))  # 자기자본 증가율 * 2
        asset_score = min(100, max(0, asset_growth * 2))  # 총자산 증가율 * 2
        
        # 가중평균 (매출 30%, 영업이익 40%, 자기자본 20%, 총자산 10%)
        return (revenue_score * 0.3 + operating_score * 0.4 + equity_score * 0.2 + asset_score * 0.1)
    
    def _evaluate_growth_grade(self, data: Dict[str, Any]) -> str:
        """성장성 등급을 평가합니다."""
        revenue_growth = data['revenue_growth_rate']
        operating_growth = data['operating_income_growth_rate']
        equity_growth = data['equity_growth_rate']
        asset_growth = data['total_asset_growth_rate']
        
        # 각 지표별 점수 계산
        scores = []
        
        # 매출 증가율 점수
        if revenue_growth > 20:
            scores.append(4)
        elif revenue_growth > 10:
            scores.append(3)
        elif revenue_growth > 0:
            scores.append(2)
        else:
            scores.append(1)
        
        # 영업이익 증가율 점수
        if operating_growth > 20:
            scores.append(4)
        elif operating_growth > 10:
            scores.append(3)
        elif operating_growth > 0:
            scores.append(2)
        else:
            scores.append(1)
        
        # 자기자본 증가율 점수
        if equity_growth > 15:
            scores.append(4)
        elif equity_growth > 10:
            scores.append(3)
        elif equity_growth > 0:
            scores.append(2)
        else:
            scores.append(1)
        
        # 총자산 증가율 점수
        if asset_growth > 15:
            scores.append(4)
        elif asset_growth > 10:
            scores.append(3)
        elif asset_growth > 0:
            scores.append(2)
        else:
            scores.append(1)
        
        # 종합 점수
        total_score = sum(scores)
        
        if total_score >= 14:
            return "매우 우수"
        elif total_score >= 10:
            return "우수"
        elif total_score >= 6:
            return "양호"
        else:
            return "우려"
    
    def _evaluate_growth_stability(self, data: Dict[str, Any]) -> str:
        """성장성 안정성을 평가합니다."""
        revenue_growth = data['revenue_growth_rate']
        operating_growth = data['operating_income_growth_rate']
        equity_growth = data['equity_growth_rate']
        asset_growth = data['total_asset_growth_rate']
        
        # 모든 지표가 양수인지 확인
        positive_indicators = sum([1 for x in [revenue_growth, operating_growth, equity_growth, asset_growth] if x > 0])
        
        if positive_indicators == 4:
            return "매우 안정"
        elif positive_indicators == 3:
            return "안정"
        elif positive_indicators == 2:
            return "보통"
        else:
            return "불안정"
    
    def _evaluate_growth_quality(self, data: Dict[str, Any]) -> str:
        """성장성 품질을 평가합니다."""
        revenue_growth = data['revenue_growth_rate']
        operating_growth = data['operating_income_growth_rate']
        equity_growth = data['equity_growth_rate']
        asset_growth = data['total_asset_growth_rate']
        
        # 영업이익 증가율이 매출 증가율보다 높은지 확인 (수익성 개선)
        profitability_improvement = operating_growth > revenue_growth
        
        # 자기자본 증가율이 총자산 증가율보다 높은지 확인 (자본 효율성)
        capital_efficiency = equity_growth > asset_growth
        
        # 성장성 품질 평가
        if profitability_improvement and capital_efficiency:
            return "매우 우수"
        elif profitability_improvement or capital_efficiency:
            return "우수"
        elif revenue_growth > 0 and operating_growth > 0:
            return "양호"
        else:
            return "우려"
    
    def _calculate_total_growth_score(self, data: Dict[str, Any], metrics: Dict[str, Any]) -> float:
        """종합 성장성 점수를 계산합니다."""
        # 기본 성장성 점수 (50%)
        base_score = metrics['growth_score'] * 0.5
        
        # 등급 점수 (30%)
        grade_score = 0
        if metrics['growth_grade'] == "매우 우수":
            grade_score = 100
        elif metrics['growth_grade'] == "우수":
            grade_score = 80
        elif metrics['growth_grade'] == "양호":
            grade_score = 60
        else:
            grade_score = 40
        grade_score *= 0.3
        
        # 품질 점수 (20%)
        quality_score = 0
        if metrics['growth_quality'] == "매우 우수":
            quality_score = 100
        elif metrics['growth_quality'] == "우수":
            quality_score = 80
        elif metrics['growth_quality'] == "양호":
            quality_score = 60
        else:
            quality_score = 40
        quality_score *= 0.2
        
        return base_score + grade_score + quality_score
    
    def analyze_growth_ratio_trend(self, ratio_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """성장성비율 추세를 분석합니다."""
        if len(ratio_data) < 2:
            return {"error": "분석을 위해 최소 2개 기간의 데이터가 필요합니다."}
        
        # 최신 데이터와 이전 데이터 비교
        latest = ratio_data[0]
        previous = ratio_data[1] if len(ratio_data) > 1 else latest
        
        analysis = {}
        
        # 성장성비율 추세
        analysis['growth_trend'] = {
            'revenue_growth_change': latest['revenue_growth_rate'] - previous['revenue_growth_rate'],
            'operating_growth_change': latest['operating_income_growth_rate'] - previous['operating_income_growth_rate'],
            'equity_growth_change': latest['equity_growth_rate'] - previous['equity_growth_rate'],
            'asset_growth_change': latest['total_asset_growth_rate'] - previous['total_asset_growth_rate']
        }
        
        # 성장성 개선도 평가
        analysis['improvement_assessment'] = self._assess_growth_improvement(analysis['growth_trend'])
        
        # 성장성 일관성 평가
        analysis['consistency_assessment'] = self._assess_growth_consistency(ratio_data)
        
        # 성장성 가속도 평가
        analysis['acceleration_assessment'] = self._assess_growth_acceleration(ratio_data)
        
        return analysis
    
    def _assess_growth_improvement(self, trend: Dict[str, Any]) -> str:
        """성장성 개선도를 평가합니다."""
        improvements = sum([1 for change in trend.values() if change > 0])
        total_indicators = len(trend)
        
        improvement_ratio = improvements / total_indicators
        
        if improvement_ratio >= 0.75:
            return "크게 개선"
        elif improvement_ratio >= 0.5:
            return "개선"
        elif improvement_ratio >= 0.25:
            return "소폭 개선"
        else:
            return "악화"
    
    def _assess_growth_consistency(self, ratio_data: List[Dict[str, Any]]) -> str:
        """성장성 일관성을 평가합니다."""
        if len(ratio_data) < 3:
            return "평가불가"
        
        # 최근 3개 기간의 매출 증가율 변동성 계산
        recent_revenue_growth = [data['revenue_growth_rate'] for data in ratio_data[:3]]
        revenue_mean = sum(recent_revenue_growth) / len(recent_revenue_growth)
        revenue_variance = sum((x - revenue_mean) ** 2 for x in recent_revenue_growth) / len(recent_revenue_growth)
        revenue_std = revenue_variance ** 0.5
        
        # 변동성 기준
        if revenue_std < 5:
            return "매우 일관적"
        elif revenue_std < 10:
            return "일관적"
        elif revenue_std < 20:
            return "보통"
        else:
            return "불안정"
    
    def _assess_growth_acceleration(self, ratio_data: List[Dict[str, Any]]) -> str:
        """성장성 가속도를 평가합니다."""
        if len(ratio_data) < 3:
            return "평가불가"
        
        # 최근 3개 기간의 매출 증가율 추세
        recent_growth = [data['revenue_growth_rate'] for data in ratio_data[:3]]
        
        # 가속도 계산 (2차 미분 근사)
        if len(recent_growth) >= 3:
            acceleration = recent_growth[0] - 2 * recent_growth[1] + recent_growth[2]
            
            if acceleration > 5:
                return "가속 성장"
            elif acceleration > 0:
                return "안정 성장"
            elif acceleration > -5:
                return "둔화"
            else:
                return "급격한 둔화"
        
        return "평가불가"
    
    def get_multiple_growth_ratios(self, symbols: List[str], period_type: str = "0") -> Dict[str, List[Dict[str, Any]]]:
        """여러 종목의 성장성비율을 조회합니다."""
        results = {}
        
        for symbol in symbols:
            logger.info(f"🔍 {symbol} 성장성비율 조회 중...")
            ratios = self.get_growth_ratios(symbol, period_type)
            if ratios:
                results[symbol] = ratios
            else:
                logger.warning(f"⚠️ {symbol} 성장성비율 조회 실패")
        
        return results
    
    def compare_growth_ratios(self, ratio_data: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
        """여러 종목의 성장성비율을 비교합니다."""
        comparison_data = []
        
        for symbol, data_list in ratio_data.items():
            if data_list:
                latest = data_list[0]  # 최신 데이터
                comparison_data.append({
                    'symbol': symbol,
                    'period': latest['period'],
                    'revenue_growth_rate': latest['revenue_growth_rate'],
                    'operating_income_growth_rate': latest['operating_income_growth_rate'],
                    'equity_growth_rate': latest['equity_growth_rate'],
                    'total_asset_growth_rate': latest['total_asset_growth_rate'],
                    'growth_score': latest['growth_score'],
                    'growth_grade': latest['growth_grade'],
                    'growth_stability': latest['growth_stability'],
                    'growth_quality': latest['growth_quality'],
                    'total_growth_score': latest['total_growth_score']
                })
        
        return pd.DataFrame(comparison_data)
    
    def analyze_investment_attractiveness(self, ratio_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """투자 매력도를 분석합니다."""
        if not ratio_data:
            return {"error": "분석할 데이터가 없습니다."}
        
        latest = ratio_data[0]
        
        analysis = {}
        
        # 성장성 평가
        analysis['growth_assessment'] = self._assess_investment_growth(latest)
        
        # 수익성 성장 평가
        analysis['profitability_growth_assessment'] = self._assess_investment_profitability_growth(latest)
        
        # 자본 효율성 평가
        analysis['capital_efficiency_assessment'] = self._assess_investment_capital_efficiency(latest)
        
        # 종합 투자 매력도
        analysis['overall_attractiveness'] = self._calculate_investment_attractiveness(analysis)
        
        return analysis
    
    def _assess_investment_growth(self, data: Dict[str, Any]) -> str:
        """투자 관점에서 성장성을 평가합니다."""
        revenue_growth = data['revenue_growth_rate']
        operating_growth = data['operating_income_growth_rate']
        
        if revenue_growth > 20 and operating_growth > 20:
            return "매우 우수"
        elif revenue_growth > 10 and operating_growth > 10:
            return "우수"
        elif revenue_growth > 0 and operating_growth > 0:
            return "양호"
        else:
            return "우려"
    
    def _assess_investment_profitability_growth(self, data: Dict[str, Any]) -> str:
        """투자 관점에서 수익성 성장을 평가합니다."""
        revenue_growth = data['revenue_growth_rate']
        operating_growth = data['operating_income_growth_rate']
        
        # 영업이익 증가율이 매출 증가율보다 높은지 확인
        if operating_growth > revenue_growth and operating_growth > 15:
            return "매우 우수"
        elif operating_growth > revenue_growth and operating_growth > 10:
            return "우수"
        elif operating_growth > revenue_growth:
            return "양호"
        else:
            return "우려"
    
    def _assess_investment_capital_efficiency(self, data: Dict[str, Any]) -> str:
        """투자 관점에서 자본 효율성을 평가합니다."""
        equity_growth = data['equity_growth_rate']
        asset_growth = data['total_asset_growth_rate']
        
        # 자기자본 증가율이 총자산 증가율보다 높은지 확인
        if equity_growth > asset_growth and equity_growth > 15:
            return "매우 우수"
        elif equity_growth > asset_growth and equity_growth > 10:
            return "우수"
        elif equity_growth > asset_growth:
            return "양호"
        else:
            return "우려"
    
    def _calculate_investment_attractiveness(self, analysis: Dict[str, Any]) -> str:
        """종합 투자 매력도를 계산합니다."""
        assessments = [
            analysis['growth_assessment'],
            analysis['profitability_growth_assessment'],
            analysis['capital_efficiency_assessment']
        ]
        
        # 매력도 점수 계산
        score = 0
        for assessment in assessments:
            if "매우 우수" in assessment:
                score += 4
            elif "우수" in assessment:
                score += 3
            elif "양호" in assessment:
                score += 2
            else:
                score += 1
        
        # 종합 평가
        if score >= 10:
            return "매우 매력적"
        elif score >= 7:
            return "매력적"
        elif score >= 4:
            return "보통"
        else:
            return "비매력적"

def main():
    """테스트 함수"""
    from kis_data_provider import KISDataProvider
    
    provider = KISDataProvider()
    analyzer = GrowthRatioAnalyzer(provider)
    
    # 삼성전자 성장성비율 조회 테스트
    samsung_ratios = analyzer.get_growth_ratios("005930")
    if samsung_ratios:
        print("📊 삼성전자 성장성비율 (최신 3개 기간):")
        for i, data in enumerate(samsung_ratios[:3]):
            print(f"\n📅 {data['period']} 기간:")
            print(f"  매출액 증가율: {data['revenue_growth_rate']:+.1f}%")
            print(f"  영업이익 증가율: {data['operating_income_growth_rate']:+.1f}%")
            print(f"  자기자본 증가율: {data['equity_growth_rate']:+.1f}%")
            print(f"  총자산 증가율: {data['total_asset_growth_rate']:+.1f}%")
            print(f"  성장성점수: {data['growth_score']:.1f}점")
            print(f"  성장성등급: {data['growth_grade']}")
            print(f"  성장성안정성: {data['growth_stability']}")
            print(f"  성장성품질: {data['growth_quality']}")
            print(f"  종합점수: {data['total_growth_score']:.1f}점")
        
        # 추세 분석
        trend_analysis = analyzer.analyze_growth_ratio_trend(samsung_ratios)
        print(f"\n📈 성장성비율 추세 분석:")
        print(f"  매출 증가율 변화: {trend_analysis['growth_trend']['revenue_growth_change']:+.1f}%p")
        print(f"  영업이익 증가율 변화: {trend_analysis['growth_trend']['operating_growth_change']:+.1f}%p")
        print(f"  자기자본 증가율 변화: {trend_analysis['growth_trend']['equity_growth_change']:+.1f}%p")
        print(f"  총자산 증가율 변화: {trend_analysis['growth_trend']['asset_growth_change']:+.1f}%p")
        print(f"  개선도: {trend_analysis['improvement_assessment']}")
        print(f"  일관성: {trend_analysis['consistency_assessment']}")
        print(f"  가속도: {trend_analysis['acceleration_assessment']}")
        
        # 투자 매력도 분석
        attractiveness = analyzer.analyze_investment_attractiveness(samsung_ratios)
        print(f"\n💎 투자 매력도 분석:")
        print(f"  성장성 평가: {attractiveness['growth_assessment']}")
        print(f"  수익성 성장 평가: {attractiveness['profitability_growth_assessment']}")
        print(f"  자본 효율성 평가: {attractiveness['capital_efficiency_assessment']}")
        print(f"  종합 매력도: {attractiveness['overall_attractiveness']}")
    else:
        print("❌ 삼성전자 성장성비율 조회 실패")

if __name__ == "__main__":
    main()
