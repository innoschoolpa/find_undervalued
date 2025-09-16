#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
손익계산서 분석 모듈
KIS API 국내주식 손익계산서 API를 활용한 손익계산서 분석
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class IncomeStatementAnalyzer:
    """손익계산서 분석 클래스"""
    
    def __init__(self, provider):
        self.provider = provider
        self.last_request_time = 0
        self.request_interval = 0.1  # API 요청 간격 제어
    
    def _rate_limit(self):
        """API 요청 속도를 제어합니다."""
        elapsed_time = time.time() - self.last_request_time
        if elapsed_time < self.request_interval:
            time.sleep(self.request_interval - elapsed_time)
        self.last_request_time = time.time()
    
    def _to_float(self, value: Any, default: float = 0.0) -> float:
        """안전하게 float 타입으로 변환합니다."""
        if value is None or value == '' or str(value) == '99.99':
            return default
        try:
            # 쉼표 제거 후 float 변환
            return float(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return default
    
    def get_income_statement(self, symbol: str, period_type: str = "0") -> Optional[List[Dict[str, Any]]]:
        """
        종목의 손익계산서를 조회합니다.
        
        Args:
            symbol: 종목코드 (6자리)
            period_type: 분류 구분 코드 (0: 년, 1: 분기)
        
        Returns:
            손익계산서 데이터 리스트
        """
        self._rate_limit()
        
        path = "/uapi/domestic-stock/v1/finance/income-statement"
        params = {
            "FID_DIV_CLS_CODE": period_type,  # 0: 년, 1: 분기
            "fid_cond_mrkt_div_code": "J",    # 국내주식
            "fid_input_iscd": symbol
        }
        
        try:
            data = self.provider._send_request(path, "FHKST66430200", params)
            if data and 'output' in data:
                return self._parse_income_statement_data(data['output'])
            else:
                logger.warning(f"⚠️ {symbol} 손익계산서 조회 실패")
                return None
                
        except Exception as e:
            logger.error(f"❌ 손익계산서 API 호출 실패 ({symbol}): {e}")
            return None
    
    def _parse_income_statement_data(self, output_list: List[Dict]) -> List[Dict[str, Any]]:
        """손익계산서 응답 데이터를 파싱합니다."""
        parsed_data = []
        
        for item in output_list:
            parsed_item = {
                'period': item.get('stac_yymm', ''),
                'revenue': self._to_float(item.get('sale_account', 0)),
                'cost_of_sales': self._to_float(item.get('sale_cost', 0)),
                'gross_profit': self._to_float(item.get('sale_totl_prfi', 0)),
                'depreciation': self._to_float(item.get('depr_cost', 0)),
                'selling_admin_expenses': self._to_float(item.get('sell_mang', 0)),
                'operating_income': self._to_float(item.get('bsop_prti', 0)),
                'non_operating_income': self._to_float(item.get('bsop_non_ernn', 0)),
                'non_operating_expenses': self._to_float(item.get('bsop_non_expn', 0)),
                'ordinary_income': self._to_float(item.get('op_prfi', 0)),
                'special_income': self._to_float(item.get('spec_prfi', 0)),
                'special_loss': self._to_float(item.get('spec_loss', 0)),
                'net_income': self._to_float(item.get('thtr_ntin', 0))
            }
            
            # 계산된 지표
            parsed_item.update(self._calculate_ratios(parsed_item))
            parsed_data.append(parsed_item)
        
        return parsed_data
    
    def _calculate_ratios(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """수익성 비율을 계산합니다."""
        ratios = {}
        
        # 매출총이익률
        if data['revenue'] > 0:
            ratios['gross_profit_margin'] = (data['gross_profit'] / data['revenue']) * 100
        else:
            ratios['gross_profit_margin'] = 0
        
        # 영업이익률
        if data['revenue'] > 0:
            ratios['operating_margin'] = (data['operating_income'] / data['revenue']) * 100
        else:
            ratios['operating_margin'] = 0
        
        # 순이익률
        if data['revenue'] > 0:
            ratios['net_margin'] = (data['net_income'] / data['revenue']) * 100
        else:
            ratios['net_margin'] = 0
        
        # 경상이익률
        if data['revenue'] > 0:
            ratios['ordinary_margin'] = (data['ordinary_income'] / data['revenue']) * 100
        else:
            ratios['ordinary_margin'] = 0
        
        # 영업외수익률
        if data['revenue'] > 0:
            ratios['non_operating_ratio'] = ((data['non_operating_income'] - data['non_operating_expenses']) / data['revenue']) * 100
        else:
            ratios['non_operating_ratio'] = 0
        
        # 특별손익률
        if data['revenue'] > 0:
            ratios['special_ratio'] = ((data['special_income'] - data['special_loss']) / data['revenue']) * 100
        else:
            ratios['special_ratio'] = 0
        
        return ratios
    
    def analyze_income_statement_trend(self, income_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """손익계산서 추세를 분석합니다."""
        if len(income_data) < 2:
            return {"error": "분석을 위해 최소 2개 기간의 데이터가 필요합니다."}
        
        # 최신 데이터와 이전 데이터 비교
        latest = income_data[0]
        previous = income_data[1] if len(income_data) > 1 else latest
        
        analysis = {}
        
        # 매출 추세
        analysis['revenue_trend'] = {
            'revenue_change': self._calculate_change_rate(latest['revenue'], previous['revenue']),
            'gross_profit_change': self._calculate_change_rate(latest['gross_profit'], previous['gross_profit']),
            'operating_income_change': self._calculate_change_rate(latest['operating_income'], previous['operating_income']),
            'net_income_change': self._calculate_change_rate(latest['net_income'], previous['net_income'])
        }
        
        # 수익성 추세
        analysis['profitability_trend'] = {
            'gross_margin_change': latest['gross_profit_margin'] - previous['gross_profit_margin'],
            'operating_margin_change': latest['operating_margin'] - previous['operating_margin'],
            'net_margin_change': latest['net_margin'] - previous['net_margin']
        }
        
        # 수익성 평가
        analysis['profitability_assessment'] = self._evaluate_profitability(latest)
        
        return analysis
    
    def _calculate_change_rate(self, current: float, previous: float) -> float:
        """변화율을 계산합니다."""
        if previous == 0:
            return 0
        return ((current - previous) / previous) * 100
    
    def _evaluate_profitability(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """수익성을 평가합니다."""
        assessment = {}
        
        # 매출총이익률 평가
        gross_margin = data['gross_profit_margin']
        if gross_margin > 30:
            assessment['gross_margin_grade'] = "우수"
        elif gross_margin > 20:
            assessment['gross_margin_grade'] = "양호"
        elif gross_margin > 10:
            assessment['gross_margin_grade'] = "보통"
        else:
            assessment['gross_margin_grade'] = "우려"
        
        # 영업이익률 평가
        operating_margin = data['operating_margin']
        if operating_margin > 15:
            assessment['operating_margin_grade'] = "우수"
        elif operating_margin > 10:
            assessment['operating_margin_grade'] = "양호"
        elif operating_margin > 5:
            assessment['operating_margin_grade'] = "보통"
        else:
            assessment['operating_margin_grade'] = "우려"
        
        # 순이익률 평가
        net_margin = data['net_margin']
        if net_margin > 10:
            assessment['net_margin_grade'] = "우수"
        elif net_margin > 5:
            assessment['net_margin_grade'] = "양호"
        elif net_margin > 0:
            assessment['net_margin_grade'] = "보통"
        else:
            assessment['net_margin_grade'] = "우려"
        
        # 종합 평가
        grades = [assessment['gross_margin_grade'], assessment['operating_margin_grade'], assessment['net_margin_grade']]
        if grades.count("우수") >= 2:
            assessment['overall_grade'] = "우수"
        elif grades.count("우수") >= 1 or grades.count("양호") >= 2:
            assessment['overall_grade'] = "양호"
        elif grades.count("우려") <= 1:
            assessment['overall_grade'] = "보통"
        else:
            assessment['overall_grade'] = "우려"
        
        return assessment
    
    def get_multiple_income_statements(self, symbols: List[str], period_type: str = "0") -> Dict[str, List[Dict[str, Any]]]:
        """여러 종목의 손익계산서를 조회합니다."""
        results = {}
        
        for symbol in symbols:
            logger.info(f"🔍 {symbol} 손익계산서 조회 중...")
            income_statement = self.get_income_statement(symbol, period_type)
            if income_statement:
                results[symbol] = income_statement
            else:
                logger.warning(f"⚠️ {symbol} 손익계산서 조회 실패")
        
        return results
    
    def compare_income_statements(self, income_data: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
        """여러 종목의 손익계산서를 비교합니다."""
        comparison_data = []
        
        for symbol, data_list in income_data.items():
            if data_list:
                latest = data_list[0]  # 최신 데이터
                comparison_data.append({
                    'symbol': symbol,
                    'period': latest['period'],
                    'revenue': latest['revenue'],
                    'operating_income': latest['operating_income'],
                    'net_income': latest['net_income'],
                    'gross_profit_margin': latest['gross_profit_margin'],
                    'operating_margin': latest['operating_margin'],
                    'net_margin': latest['net_margin']
                })
        
        return pd.DataFrame(comparison_data)
    
    def analyze_growth_quality(self, income_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """성장 품질을 분석합니다."""
        if len(income_data) < 3:
            return {"error": "성장 품질 분석을 위해 최소 3개 기간의 데이터가 필요합니다."}
        
        # 최근 3개 기간 데이터
        recent_data = income_data[:3]
        
        analysis = {}
        
        # 매출 성장률
        revenue_growth_rates = []
        for i in range(len(recent_data) - 1):
            growth_rate = self._calculate_change_rate(recent_data[i]['revenue'], recent_data[i + 1]['revenue'])
            revenue_growth_rates.append(growth_rate)
        
        analysis['revenue_growth'] = {
            'latest_growth': revenue_growth_rates[0],
            'average_growth': sum(revenue_growth_rates) / len(revenue_growth_rates),
            'growth_consistency': self._calculate_consistency(revenue_growth_rates)
        }
        
        # 영업이익 성장률
        operating_growth_rates = []
        for i in range(len(recent_data) - 1):
            growth_rate = self._calculate_change_rate(recent_data[i]['operating_income'], recent_data[i + 1]['operating_income'])
            operating_growth_rates.append(growth_rate)
        
        analysis['operating_growth'] = {
            'latest_growth': operating_growth_rates[0],
            'average_growth': sum(operating_growth_rates) / len(operating_growth_rates),
            'growth_consistency': self._calculate_consistency(operating_growth_rates)
        }
        
        # 순이익 성장률
        net_growth_rates = []
        for i in range(len(recent_data) - 1):
            growth_rate = self._calculate_change_rate(recent_data[i]['net_income'], recent_data[i + 1]['net_income'])
            net_growth_rates.append(growth_rate)
        
        analysis['net_growth'] = {
            'latest_growth': net_growth_rates[0],
            'average_growth': sum(net_growth_rates) / len(net_growth_rates),
            'growth_consistency': self._calculate_consistency(net_growth_rates)
        }
        
        # 성장 품질 평가
        analysis['growth_quality'] = self._evaluate_growth_quality(analysis)
        
        return analysis
    
    def _calculate_consistency(self, growth_rates: List[float]) -> str:
        """성장률의 일관성을 평가합니다."""
        if len(growth_rates) < 2:
            return "평가불가"
        
        # 성장률의 표준편차 계산
        mean_growth = sum(growth_rates) / len(growth_rates)
        variance = sum((rate - mean_growth) ** 2 for rate in growth_rates) / len(growth_rates)
        std_dev = variance ** 0.5
        
        # 일관성 평가
        if std_dev < 5:
            return "매우 일관적"
        elif std_dev < 10:
            return "일관적"
        elif std_dev < 20:
            return "보통"
        else:
            return "불안정"
    
    def _evaluate_growth_quality(self, analysis: Dict[str, Any]) -> str:
        """성장 품질을 평가합니다."""
        revenue_growth = analysis['revenue_growth']['average_growth']
        operating_growth = analysis['operating_growth']['average_growth']
        net_growth = analysis['net_growth']['average_growth']
        
        # 성장률 기준
        if revenue_growth > 20 and operating_growth > 20 and net_growth > 20:
            return "우수"
        elif revenue_growth > 10 and operating_growth > 10 and net_growth > 10:
            return "양호"
        elif revenue_growth > 0 and operating_growth > 0 and net_growth > 0:
            return "보통"
        else:
            return "우려"

def main():
    """테스트 함수"""
    from kis_data_provider import KISDataProvider
    
    provider = KISDataProvider()
    analyzer = IncomeStatementAnalyzer(provider)
    
    # 삼성전자 손익계산서 조회 테스트
    samsung_is = analyzer.get_income_statement("005930")
    if samsung_is:
        print("📊 삼성전자 손익계산서 (최신 3개 기간):")
        for i, data in enumerate(samsung_is[:3]):
            print(f"\n📅 {data['period']} 기간:")
            print(f"  매출액: {data['revenue']:,.0f}원")
            print(f"  영업이익: {data['operating_income']:,.0f}원")
            print(f"  당기순이익: {data['net_income']:,.0f}원")
            print(f"  매출총이익률: {data['gross_profit_margin']:.1f}%")
            print(f"  영업이익률: {data['operating_margin']:.1f}%")
            print(f"  순이익률: {data['net_margin']:.1f}%")
        
        # 추세 분석
        trend_analysis = analyzer.analyze_income_statement_trend(samsung_is)
        print(f"\n📈 수익성 추세 분석:")
        print(f"  매출 변화: {trend_analysis['revenue_trend']['revenue_change']:+.1f}%")
        print(f"  영업이익 변화: {trend_analysis['revenue_trend']['operating_income_change']:+.1f}%")
        print(f"  순이익 변화: {trend_analysis['revenue_trend']['net_income_change']:+.1f}%")
        print(f"  수익성 평가: {trend_analysis['profitability_assessment']['overall_grade']}")
        
        # 성장 품질 분석
        growth_analysis = analyzer.analyze_growth_quality(samsung_is)
        print(f"\n🚀 성장 품질 분석:")
        print(f"  매출 성장률: {growth_analysis['revenue_growth']['average_growth']:+.1f}%")
        print(f"  영업이익 성장률: {growth_analysis['operating_growth']['average_growth']:+.1f}%")
        print(f"  순이익 성장률: {growth_analysis['net_growth']['average_growth']:+.1f}%")
        print(f"  성장 품질: {growth_analysis['growth_quality']}")
    else:
        print("❌ 삼성전자 손익계산서 조회 실패")

if __name__ == "__main__":
    main()
