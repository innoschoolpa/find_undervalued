#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
종목추정실적 분석 모듈
KIS API 국내주식 종목추정실적 API를 활용한 추정실적 분석
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class EstimatePerformanceAnalyzer:
    """종목추정실적 분석 클래스"""
    
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
    
    def get_estimate_performance(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        종목의 추정실적을 조회합니다.
        
        Args:
            symbol: 종목코드 (6자리)
        
        Returns:
            추정실적 데이터
        """
        self._rate_limit()
        
        path = "/uapi/domestic-stock/v1/quotations/estimate-perform"
        params = {
            "SHT_CD": symbol
        }
        
        try:
            data = self.provider._send_request(path, "HHKST668300C0", params)
            if data and 'output1' in data:
                return self._parse_estimate_performance_data(data)
            else:
                logger.warning(f"⚠️ {symbol} 추정실적 조회 실패")
                return None
                
        except Exception as e:
            logger.error(f"❌ 추정실적 API 호출 실패 ({symbol}): {e}")
            return None
    
    def _parse_estimate_performance_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """추정실적 응답 데이터를 파싱합니다."""
        parsed_data = {}
        
        # 기본 정보 (output1)
        if 'output1' in data:
            output1 = data['output1']
            parsed_data['basic_info'] = {
                'symbol': output1.get('sht_cd', ''),
                'name': output1.get('item_kor_nm', ''),
                'current_price': self._to_float(output1.get('name1', 0)),
                'price_change': self._to_float(output1.get('name2', 0)),
                'price_change_sign': output1.get('estdate', ''),
                'price_change_rate': self._to_float(output1.get('rcmd_name', 0)),
                'volume': self._to_float(output1.get('capital', 0)),
                'strike_price': self._to_float(output1.get('forn_item_lmtrt', 0))
            }
        
        # 추정손익계산서 (output2) - 6개 array
        if 'output2' in data and data['output2']:
            parsed_data['income_statement'] = self._parse_income_statement_data(data['output2'])
        
        # 투자지표 (output3) - 8개 array
        if 'output3' in data and data['output3']:
            parsed_data['investment_metrics'] = self._parse_investment_metrics_data(data['output3'])
        
        # 결산년월 정보 (output4)
        if 'output4' in data and data['output4']:
            parsed_data['periods'] = [item.get('dt', '') for item in data['output4']]
        
        # 추가 분석 지표 계산
        if 'income_statement' in parsed_data and 'investment_metrics' in parsed_data:
            parsed_data['analysis'] = self._calculate_analysis_metrics(parsed_data)
        
        return parsed_data
    
    def _parse_income_statement_data(self, output2: List[Dict]) -> Dict[str, List[Dict[str, Any]]]:
        """추정손익계산서 데이터를 파싱합니다."""
        income_data = {}
        
        # 6개 array: 매출액, 매출액증감율, 영업이익, 영업이익증감율, 순이익, 순이익증감율
        metrics = ['revenue', 'revenue_growth_rate', 'operating_income', 'operating_income_growth_rate', 'net_income', 'net_income_growth_rate']
        
        for i, item in enumerate(output2):
            if i < len(metrics):
                metric_name = metrics[i]
                income_data[metric_name] = [
                    self._to_float(item.get('data1', 0)),
                    self._to_float(item.get('data2', 0)),
                    self._to_float(item.get('data3', 0)),
                    self._to_float(item.get('data4', 0)),
                    self._to_float(item.get('data5', 0))
                ]
        
        return income_data
    
    def _parse_investment_metrics_data(self, output3: List[Dict]) -> Dict[str, List[float]]:
        """투자지표 데이터를 파싱합니다."""
        metrics_data = {}
        
        # 8개 array: EBITDA, EPS, EPS증감율, PER, EV/EBITDA, ROE, 부채비율, 이자보상배율
        metrics = ['ebitda', 'eps', 'eps_growth_rate', 'per', 'ev_ebitda', 'roe', 'debt_ratio', 'interest_coverage_ratio']
        
        for i, item in enumerate(output3):
            if i < len(metrics):
                metric_name = metrics[i]
                metrics_data[metric_name] = [
                    self._to_float(item.get('data1', 0)),
                    self._to_float(item.get('data2', 0)),
                    self._to_float(item.get('data3', 0)),
                    self._to_float(item.get('data4', 0)),
                    self._to_float(item.get('data5', 0))
                ]
        
        return metrics_data
    
    def _calculate_analysis_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """추가 분석 지표를 계산합니다."""
        analysis = {}
        
        if 'income_statement' in data and 'investment_metrics' in data:
            income = data['income_statement']
            metrics = data['investment_metrics']
            
            # 성장성 분석
            analysis['growth_analysis'] = self._analyze_growth(income)
            
            # 수익성 분석
            analysis['profitability_analysis'] = self._analyze_profitability(income, metrics)
            
            # 가치 평가 분석
            analysis['valuation_analysis'] = self._analyze_valuation(metrics)
            
            # 안정성 분석
            analysis['stability_analysis'] = self._analyze_stability(metrics)
            
            # 종합 투자 매력도
            analysis['overall_attractiveness'] = self._calculate_overall_attractiveness(analysis)
        
        return analysis
    
    def _analyze_growth(self, income: Dict[str, List[float]]) -> Dict[str, Any]:
        """성장성 분석을 수행합니다."""
        analysis = {}
        
        # 매출 성장률 분석
        revenue_growth = income.get('revenue_growth_rate', [])
        if revenue_growth:
            latest_revenue_growth = revenue_growth[0]
            analysis['revenue_growth_trend'] = self._evaluate_growth_trend(revenue_growth)
            analysis['revenue_growth_grade'] = self._evaluate_growth_grade(latest_revenue_growth)
        
        # 영업이익 성장률 분석
        operating_growth = income.get('operating_income_growth_rate', [])
        if operating_growth:
            latest_operating_growth = operating_growth[0]
            analysis['operating_growth_trend'] = self._evaluate_growth_trend(operating_growth)
            analysis['operating_growth_grade'] = self._evaluate_growth_grade(latest_operating_growth)
        
        # 순이익 성장률 분석
        net_growth = income.get('net_income_growth_rate', [])
        if net_growth:
            latest_net_growth = net_growth[0]
            analysis['net_growth_trend'] = self._evaluate_growth_trend(net_growth)
            analysis['net_growth_grade'] = self._evaluate_growth_grade(latest_net_growth)
        
        return analysis
    
    def _analyze_profitability(self, income: Dict[str, List[float]], metrics: Dict[str, List[float]]) -> Dict[str, Any]:
        """수익성 분석을 수행합니다."""
        analysis = {}
        
        # ROE 분석
        roe_data = metrics.get('roe', [])
        if roe_data:
            latest_roe = roe_data[0]
            analysis['roe_grade'] = self._evaluate_roe_grade(latest_roe)
            analysis['roe_trend'] = self._evaluate_trend(roe_data)
        
        # EPS 분석
        eps_data = metrics.get('eps', [])
        if eps_data:
            latest_eps = eps_data[0]
            analysis['eps_grade'] = self._evaluate_eps_grade(latest_eps)
            analysis['eps_trend'] = self._evaluate_trend(eps_data)
        
        # EBITDA 분석
        ebitda_data = metrics.get('ebitda', [])
        if ebitda_data:
            latest_ebitda = ebitda_data[0]
            analysis['ebitda_grade'] = self._evaluate_ebitda_grade(latest_ebitda)
            analysis['ebitda_trend'] = self._evaluate_trend(ebitda_data)
        
        return analysis
    
    def _analyze_valuation(self, metrics: Dict[str, List[float]]) -> Dict[str, Any]:
        """가치 평가 분석을 수행합니다."""
        analysis = {}
        
        # PER 분석
        per_data = metrics.get('per', [])
        if per_data:
            latest_per = per_data[0]
            analysis['per_grade'] = self._evaluate_per_grade(latest_per)
            analysis['per_trend'] = self._evaluate_trend(per_data)
        
        # EV/EBITDA 분석
        ev_ebitda_data = metrics.get('ev_ebitda', [])
        if ev_ebitda_data:
            latest_ev_ebitda = ev_ebitda_data[0]
            analysis['ev_ebitda_grade'] = self._evaluate_ev_ebitda_grade(latest_ev_ebitda)
            analysis['ev_ebitda_trend'] = self._evaluate_trend(ev_ebitda_data)
        
        return analysis
    
    def _analyze_stability(self, metrics: Dict[str, List[float]]) -> Dict[str, Any]:
        """안정성 분석을 수행합니다."""
        analysis = {}
        
        # 부채비율 분석
        debt_ratio_data = metrics.get('debt_ratio', [])
        if debt_ratio_data:
            latest_debt_ratio = debt_ratio_data[0]
            analysis['debt_ratio_grade'] = self._evaluate_debt_ratio_grade(latest_debt_ratio)
            analysis['debt_ratio_trend'] = self._evaluate_trend(debt_ratio_data)
        
        # 이자보상배율 분석
        interest_coverage_data = metrics.get('interest_coverage_ratio', [])
        if interest_coverage_data:
            latest_interest_coverage = interest_coverage_data[0]
            analysis['interest_coverage_grade'] = self._evaluate_interest_coverage_grade(latest_interest_coverage)
            analysis['interest_coverage_trend'] = self._evaluate_trend(interest_coverage_data)
        
        return analysis
    
    def _evaluate_growth_trend(self, growth_rates: List[float]) -> str:
        """성장률 추세를 평가합니다."""
        if len(growth_rates) < 2:
            return "평가불가"
        
        # 최근 2개 기간 비교
        latest = growth_rates[0]
        previous = growth_rates[1]
        
        if latest > previous:
            return "가속"
        elif latest == previous:
            return "안정"
        else:
            return "둔화"
    
    def _evaluate_growth_grade(self, growth_rate: float) -> str:
        """성장률 등급을 평가합니다."""
        if growth_rate > 20:
            return "매우 우수"
        elif growth_rate > 10:
            return "우수"
        elif growth_rate > 0:
            return "양호"
        else:
            return "우려"
    
    def _evaluate_roe_grade(self, roe: float) -> str:
        """ROE 등급을 평가합니다."""
        if roe > 15:
            return "매우 우수"
        elif roe > 10:
            return "우수"
        elif roe > 5:
            return "양호"
        else:
            return "우려"
    
    def _evaluate_eps_grade(self, eps: float) -> str:
        """EPS 등급을 평가합니다."""
        if eps > 5000:
            return "매우 우수"
        elif eps > 2000:
            return "우수"
        elif eps > 0:
            return "양호"
        else:
            return "우려"
    
    def _evaluate_ebitda_grade(self, ebitda: float) -> str:
        """EBITDA 등급을 평가합니다."""
        if ebitda > 1000:  # 1000억원 이상
            return "매우 우수"
        elif ebitda > 500:
            return "우수"
        elif ebitda > 100:
            return "양호"
        else:
            return "우려"
    
    def _evaluate_per_grade(self, per: float) -> str:
        """PER 등급을 평가합니다."""
        if per < 10:
            return "매우 저평가"
        elif per < 15:
            return "저평가"
        elif per < 25:
            return "적정"
        else:
            return "고평가"
    
    def _evaluate_ev_ebitda_grade(self, ev_ebitda: float) -> str:
        """EV/EBITDA 등급을 평가합니다."""
        if ev_ebitda < 5:
            return "매우 저평가"
        elif ev_ebitda < 10:
            return "저평가"
        elif ev_ebitda < 15:
            return "적정"
        else:
            return "고평가"
    
    def _evaluate_debt_ratio_grade(self, debt_ratio: float) -> str:
        """부채비율 등급을 평가합니다."""
        if debt_ratio < 30:
            return "매우 우수"
        elif debt_ratio < 50:
            return "우수"
        elif debt_ratio < 70:
            return "양호"
        else:
            return "우려"
    
    def _evaluate_interest_coverage_grade(self, interest_coverage: float) -> str:
        """이자보상배율 등급을 평가합니다."""
        if interest_coverage > 10:
            return "매우 우수"
        elif interest_coverage > 5:
            return "우수"
        elif interest_coverage > 2:
            return "양호"
        else:
            return "우려"
    
    def _evaluate_trend(self, data: List[float]) -> str:
        """데이터 추세를 평가합니다."""
        if len(data) < 2:
            return "평가불가"
        
        latest = data[0]
        previous = data[1]
        
        if latest > previous:
            return "개선"
        elif latest == previous:
            return "안정"
        else:
            return "악화"
    
    def _calculate_overall_attractiveness(self, analysis: Dict[str, Any]) -> str:
        """종합 투자 매력도를 계산합니다."""
        scores = []
        
        # 성장성 점수
        if 'growth_analysis' in analysis:
            growth_scores = []
            for key, value in analysis['growth_analysis'].items():
                if 'grade' in key:
                    if "매우 우수" in str(value):
                        growth_scores.append(4)
                    elif "우수" in str(value):
                        growth_scores.append(3)
                    elif "양호" in str(value):
                        growth_scores.append(2)
                    else:
                        growth_scores.append(1)
            if growth_scores:
                scores.append(sum(growth_scores) / len(growth_scores))
        
        # 수익성 점수
        if 'profitability_analysis' in analysis:
            profit_scores = []
            for key, value in analysis['profitability_analysis'].items():
                if 'grade' in key:
                    if "매우 우수" in str(value):
                        profit_scores.append(4)
                    elif "우수" in str(value):
                        profit_scores.append(3)
                    elif "양호" in str(value):
                        profit_scores.append(2)
                    else:
                        profit_scores.append(1)
            if profit_scores:
                scores.append(sum(profit_scores) / len(profit_scores))
        
        # 가치 평가 점수
        if 'valuation_analysis' in analysis:
            valuation_scores = []
            for key, value in analysis['valuation_analysis'].items():
                if 'grade' in key:
                    if "매우 저평가" in str(value):
                        valuation_scores.append(4)
                    elif "저평가" in str(value):
                        valuation_scores.append(3)
                    elif "적정" in str(value):
                        valuation_scores.append(2)
                    else:
                        valuation_scores.append(1)
            if valuation_scores:
                scores.append(sum(valuation_scores) / len(valuation_scores))
        
        # 안정성 점수
        if 'stability_analysis' in analysis:
            stability_scores = []
            for key, value in analysis['stability_analysis'].items():
                if 'grade' in key:
                    if "매우 우수" in str(value):
                        stability_scores.append(4)
                    elif "우수" in str(value):
                        stability_scores.append(3)
                    elif "양호" in str(value):
                        stability_scores.append(2)
                    else:
                        stability_scores.append(1)
            if stability_scores:
                scores.append(sum(stability_scores) / len(stability_scores))
        
        if not scores:
            return "평가불가"
        
        avg_score = sum(scores) / len(scores)
        
        if avg_score >= 3.5:
            return "매우 매력적"
        elif avg_score >= 2.5:
            return "매력적"
        elif avg_score >= 1.5:
            return "보통"
        else:
            return "비매력적"
    
    def get_multiple_estimate_performance(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """여러 종목의 추정실적을 조회합니다."""
        results = {}
        
        for symbol in symbols:
            logger.info(f"🔍 {symbol} 추정실적 조회 중...")
            performance = self.get_estimate_performance(symbol)
            if performance:
                results[symbol] = performance
            else:
                logger.warning(f"⚠️ {symbol} 추정실적 조회 실패")
        
        return results
    
    def compare_estimate_performance(self, performance_data: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """여러 종목의 추정실적을 비교합니다."""
        comparison_data = []
        
        for symbol, data in performance_data.items():
            if 'basic_info' in data and 'investment_metrics' in data:
                basic = data['basic_info']
                metrics = data['investment_metrics']
                
                comparison_data.append({
                    'symbol': symbol,
                    'name': basic.get('name', ''),
                    'current_price': basic.get('current_price', 0),
                    'price_change_rate': basic.get('price_change_rate', 0),
                    'latest_roe': metrics.get('roe', [0])[0] if metrics.get('roe') else 0,
                    'latest_eps': metrics.get('eps', [0])[0] if metrics.get('eps') else 0,
                    'latest_per': metrics.get('per', [0])[0] if metrics.get('per') else 0,
                    'latest_ev_ebitda': metrics.get('ev_ebitda', [0])[0] if metrics.get('ev_ebitda') else 0,
                    'latest_debt_ratio': metrics.get('debt_ratio', [0])[0] if metrics.get('debt_ratio') else 0,
                    'overall_attractiveness': data.get('analysis', {}).get('overall_attractiveness', '평가불가')
                })
        
        return pd.DataFrame(comparison_data)

def main():
    """테스트 함수"""
    from kis_data_provider import KISDataProvider
    
    provider = KISDataProvider()
    analyzer = EstimatePerformanceAnalyzer(provider)
    
    # 삼성전자 추정실적 조회 테스트
    samsung_performance = analyzer.get_estimate_performance("005930")
    if samsung_performance:
        print("📊 삼성전자 추정실적 분석:")
        
        # 기본 정보
        if 'basic_info' in samsung_performance:
            basic = samsung_performance['basic_info']
            print(f"\n📈 기본 정보:")
            print(f"  종목명: {basic.get('name', '')}")
            print(f"  현재가: {basic.get('current_price', 0):,.0f}원")
            print(f"  전일대비: {basic.get('price_change', 0):+,.0f}원 ({basic.get('price_change_rate', 0):+.2f}%)")
            print(f"  거래량: {basic.get('volume', 0):,.0f}주")
        
        # 추정손익계산서
        if 'income_statement' in samsung_performance:
            income = samsung_performance['income_statement']
            print(f"\n💰 추정손익계산서 (최신 5개 기간):")
            periods = samsung_performance.get('periods', [''] * 5)
            
            for i in range(5):
                if i < len(periods):
                    print(f"\n  📅 {periods[i]} 기간:")
                    print(f"    매출액: {income.get('revenue', [0])[i]:,.0f}억원")
                    print(f"    매출증가율: {income.get('revenue_growth_rate', [0])[i]:+.1f}%")
                    print(f"    영업이익: {income.get('operating_income', [0])[i]:,.0f}억원")
                    print(f"    영업이익증가율: {income.get('operating_income_growth_rate', [0])[i]:+.1f}%")
                    print(f"    순이익: {income.get('net_income', [0])[i]:,.0f}억원")
                    print(f"    순이익증가율: {income.get('net_income_growth_rate', [0])[i]:+.1f}%")
        
        # 투자지표
        if 'investment_metrics' in samsung_performance:
            metrics = samsung_performance['investment_metrics']
            print(f"\n📊 투자지표 (최신 5개 기간):")
            periods = samsung_performance.get('periods', [''] * 5)
            
            for i in range(5):
                if i < len(periods):
                    print(f"\n  📅 {periods[i]} 기간:")
                    print(f"    EBITDA: {metrics.get('ebitda', [0])[i]:,.0f}억원")
                    print(f"    EPS: {metrics.get('eps', [0])[i]:,.0f}원")
                    print(f"    EPS증가율: {metrics.get('eps_growth_rate', [0])[i]:+.1f}%")
                    print(f"    PER: {metrics.get('per', [0])[i]:.1f}배")
                    print(f"    EV/EBITDA: {metrics.get('ev_ebitda', [0])[i]:.1f}배")
                    print(f"    ROE: {metrics.get('roe', [0])[i]:.1f}%")
                    print(f"    부채비율: {metrics.get('debt_ratio', [0])[i]:.1f}%")
                    print(f"    이자보상배율: {metrics.get('interest_coverage_ratio', [0])[i]:.1f}배")
        
        # 분석 결과
        if 'analysis' in samsung_performance:
            analysis = samsung_performance['analysis']
            print(f"\n🔍 분석 결과:")
            print(f"  종합 투자 매력도: {analysis.get('overall_attractiveness', '평가불가')}")
            
            if 'growth_analysis' in analysis:
                growth = analysis['growth_analysis']
                print(f"\n  📈 성장성 분석:")
                print(f"    매출 성장률 등급: {growth.get('revenue_growth_grade', '평가불가')}")
                print(f"    영업이익 성장률 등급: {growth.get('operating_growth_grade', '평가불가')}")
                print(f"    순이익 성장률 등급: {growth.get('net_growth_grade', '평가불가')}")
            
            if 'profitability_analysis' in analysis:
                profit = analysis['profitability_analysis']
                print(f"\n  💰 수익성 분석:")
                print(f"    ROE 등급: {profit.get('roe_grade', '평가불가')}")
                print(f"    EPS 등급: {profit.get('eps_grade', '평가불가')}")
                print(f"    EBITDA 등급: {profit.get('ebitda_grade', '평가불가')}")
            
            if 'valuation_analysis' in analysis:
                valuation = analysis['valuation_analysis']
                print(f"\n  💎 가치 평가 분석:")
                print(f"    PER 등급: {valuation.get('per_grade', '평가불가')}")
                print(f"    EV/EBITDA 등급: {valuation.get('ev_ebitda_grade', '평가불가')}")
            
            if 'stability_analysis' in analysis:
                stability = analysis['stability_analysis']
                print(f"\n  🛡️ 안정성 분석:")
                print(f"    부채비율 등급: {stability.get('debt_ratio_grade', '평가불가')}")
                print(f"    이자보상배율 등급: {stability.get('interest_coverage_grade', '평가불가')}")
    else:
        print("❌ 삼성전자 추정실적 조회 실패")

if __name__ == "__main__":
    main()
