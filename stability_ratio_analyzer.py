#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
안정성비율 분석 모듈
KIS API 국내주식 안정성비율 API를 활용한 안정성비율 분석
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class StabilityRatioAnalyzer:
    """안정성비율 분석 클래스"""
    
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
    
    def get_stability_ratios(self, symbol: str, period_type: str = "0") -> Optional[List[Dict[str, Any]]]:
        """
        종목의 안정성비율을 조회합니다.
        
        Args:
            symbol: 종목코드 (6자리)
            period_type: 분류 구분 코드 (0: 년, 1: 분기)
        
        Returns:
            안정성비율 데이터 리스트
        """
        self._rate_limit()
        
        path = "/uapi/domestic-stock/v1/finance/stability-ratio"
        params = {
            "fid_input_iscd": symbol,
            "fid_div_cls_code": period_type,  # 0: 년, 1: 분기
            "fid_cond_mrkt_div_code": "J"     # 국내주식
        }
        
        try:
            data = self.provider._send_request(path, "FHKST66430600", params)
            if data and 'output' in data:
                return self._parse_stability_ratio_data(data['output'])
            else:
                logger.warning(f"⚠️ {symbol} 안정성비율 조회 실패")
                return None
                
        except Exception as e:
            logger.error(f"❌ 안정성비율 API 호출 실패 ({symbol}): {e}")
            return None
    
    def _parse_stability_ratio_data(self, output_list: List[Dict]) -> List[Dict[str, Any]]:
        """안정성비율 응답 데이터를 파싱합니다."""
        parsed_data = []
        
        for item in output_list:
            parsed_item = {
                'period': item.get('stac_yymm', ''),
                'debt_ratio': self._to_float(item.get('lblt_rate', 0)),  # 부채비율
                'borrowing_dependency': self._to_float(item.get('bram_depn', 0)),  # 차입금 의존도
                'current_ratio': self._to_float(item.get('crnt_rate', 0)),  # 유동비율
                'quick_ratio': self._to_float(item.get('quck_rate', 0))  # 당좌비율
            }
            
            # 추가 계산 지표
            parsed_item.update(self._calculate_additional_metrics(parsed_item))
            parsed_data.append(parsed_item)
        
        return parsed_data
    
    def _calculate_additional_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """추가 안정성 지표를 계산합니다."""
        metrics = {}
        
        # 자기자본비율 (100 - 부채비율)
        metrics['equity_ratio'] = 100 - data['debt_ratio']
        
        # 안정성 점수 계산
        metrics['stability_score'] = self._calculate_stability_score(data)
        
        # 안정성 등급 평가
        metrics['stability_grade'] = self._evaluate_stability_grade(data)
        
        # 유동성 등급 평가
        metrics['liquidity_grade'] = self._evaluate_liquidity_grade(data)
        
        # 종합 안정성 점수
        metrics['total_stability_score'] = self._calculate_total_stability_score(data, metrics)
        
        return metrics
    
    def _calculate_stability_score(self, data: Dict[str, Any]) -> float:
        """안정성 점수를 계산합니다."""
        debt_ratio = data['debt_ratio']
        current_ratio = data['current_ratio']
        quick_ratio = data['quick_ratio']
        borrowing_dependency = data['borrowing_dependency']
        
        # 부채비율 점수 (낮을수록 좋음)
        if debt_ratio <= 30:
            debt_score = 100
        elif debt_ratio <= 50:
            debt_score = 80
        elif debt_ratio <= 70:
            debt_score = 60
        elif debt_ratio <= 100:
            debt_score = 40
        else:
            debt_score = 20
        
        # 유동비율 점수 (높을수록 좋음)
        if current_ratio >= 200:
            current_score = 100
        elif current_ratio >= 150:
            current_score = 80
        elif current_ratio >= 100:
            current_score = 60
        elif current_ratio >= 50:
            current_score = 40
        else:
            current_score = 20
        
        # 당좌비율 점수 (높을수록 좋음)
        if quick_ratio >= 100:
            quick_score = 100
        elif quick_ratio >= 80:
            quick_score = 80
        elif quick_ratio >= 50:
            quick_score = 60
        elif quick_ratio >= 30:
            quick_score = 40
        else:
            quick_score = 20
        
        # 차입금 의존도 점수 (낮을수록 좋음)
        if borrowing_dependency <= 20:
            borrowing_score = 100
        elif borrowing_dependency <= 40:
            borrowing_score = 80
        elif borrowing_dependency <= 60:
            borrowing_score = 60
        elif borrowing_dependency <= 80:
            borrowing_score = 40
        else:
            borrowing_score = 20
        
        # 가중평균 (부채비율 40%, 유동비율 30%, 당좌비율 20%, 차입금 의존도 10%)
        return (debt_score * 0.4 + current_score * 0.3 + quick_score * 0.2 + borrowing_score * 0.1)
    
    def _evaluate_stability_grade(self, data: Dict[str, Any]) -> str:
        """안정성 등급을 평가합니다."""
        debt_ratio = data['debt_ratio']
        equity_ratio = 100 - debt_ratio
        
        if debt_ratio <= 30 and equity_ratio >= 70:
            return "매우 안정"
        elif debt_ratio <= 50 and equity_ratio >= 50:
            return "안정"
        elif debt_ratio <= 70 and equity_ratio >= 30:
            return "보통"
        else:
            return "불안정"
    
    def _evaluate_liquidity_grade(self, data: Dict[str, Any]) -> str:
        """유동성 등급을 평가합니다."""
        current_ratio = data['current_ratio']
        quick_ratio = data['quick_ratio']
        
        # 유동비율과 당좌비율을 종합 평가
        if current_ratio >= 200 and quick_ratio >= 100:
            return "매우 우수"
        elif current_ratio >= 150 and quick_ratio >= 80:
            return "우수"
        elif current_ratio >= 100 and quick_ratio >= 50:
            return "양호"
        elif current_ratio >= 50 and quick_ratio >= 30:
            return "보통"
        else:
            return "우려"
    
    def _calculate_total_stability_score(self, data: Dict[str, Any], metrics: Dict[str, Any]) -> float:
        """종합 안정성 점수를 계산합니다."""
        # 기본 안정성 점수 (60%)
        base_score = metrics['stability_score'] * 0.6
        
        # 등급 점수 (40%)
        grade_score = 0
        if metrics['stability_grade'] == "매우 안정":
            grade_score = 100
        elif metrics['stability_grade'] == "안정":
            grade_score = 80
        elif metrics['stability_grade'] == "보통":
            grade_score = 60
        else:
            grade_score = 40
        grade_score *= 0.4
        
        return base_score + grade_score
    
    def analyze_stability_ratio_trend(self, ratio_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """안정성비율 추세를 분석합니다."""
        if len(ratio_data) < 2:
            return {"error": "분석을 위해 최소 2개 기간의 데이터가 필요합니다."}
        
        # 최신 데이터와 이전 데이터 비교
        latest = ratio_data[0]
        previous = ratio_data[1] if len(ratio_data) > 1 else latest
        
        analysis = {}
        
        # 안정성비율 추세
        analysis['stability_trend'] = {
            'debt_ratio_change': latest['debt_ratio'] - previous['debt_ratio'],
            'equity_ratio_change': latest['equity_ratio'] - previous['equity_ratio'],
            'current_ratio_change': latest['current_ratio'] - previous['current_ratio'],
            'quick_ratio_change': latest['quick_ratio'] - previous['quick_ratio'],
            'borrowing_dependency_change': latest['borrowing_dependency'] - previous['borrowing_dependency']
        }
        
        # 안정성 개선도 평가
        analysis['improvement_assessment'] = self._assess_stability_improvement(analysis['stability_trend'])
        
        # 안정성 일관성 평가
        analysis['consistency_assessment'] = self._assess_stability_consistency(ratio_data)
        
        return analysis
    
    def _assess_stability_improvement(self, trend: Dict[str, Any]) -> str:
        """안정성 개선도를 평가합니다."""
        # 부채비율 감소, 자기자본비율 증가, 유동비율 증가, 당좌비율 증가, 차입금 의존도 감소가 좋음
        improvements = 0
        total_indicators = 5
        
        if trend['debt_ratio_change'] < 0:  # 부채비율 감소
            improvements += 1
        if trend['equity_ratio_change'] > 0:  # 자기자본비율 증가
            improvements += 1
        if trend['current_ratio_change'] > 0:  # 유동비율 증가
            improvements += 1
        if trend['quick_ratio_change'] > 0:  # 당좌비율 증가
            improvements += 1
        if trend['borrowing_dependency_change'] < 0:  # 차입금 의존도 감소
            improvements += 1
        
        improvement_ratio = improvements / total_indicators
        
        if improvement_ratio >= 0.8:
            return "크게 개선"
        elif improvement_ratio >= 0.6:
            return "개선"
        elif improvement_ratio >= 0.4:
            return "소폭 개선"
        else:
            return "악화"
    
    def _assess_stability_consistency(self, ratio_data: List[Dict[str, Any]]) -> str:
        """안정성 일관성을 평가합니다."""
        if len(ratio_data) < 3:
            return "평가불가"
        
        # 최근 3개 기간의 부채비율 변동성 계산
        recent_debt_ratios = [data['debt_ratio'] for data in ratio_data[:3]]
        debt_mean = sum(recent_debt_ratios) / len(recent_debt_ratios)
        debt_variance = sum((x - debt_mean) ** 2 for x in recent_debt_ratios) / len(recent_debt_ratios)
        debt_std = debt_variance ** 0.5
        
        # 변동성 기준
        if debt_std < 5:
            return "매우 일관적"
        elif debt_std < 10:
            return "일관적"
        elif debt_std < 20:
            return "보통"
        else:
            return "불안정"
    
    def get_multiple_stability_ratios(self, symbols: List[str], period_type: str = "0") -> Dict[str, List[Dict[str, Any]]]:
        """여러 종목의 안정성비율을 조회합니다."""
        results = {}
        
        for symbol in symbols:
            logger.info(f"🔍 {symbol} 안정성비율 조회 중...")
            ratios = self.get_stability_ratios(symbol, period_type)
            if ratios:
                results[symbol] = ratios
            else:
                logger.warning(f"⚠️ {symbol} 안정성비율 조회 실패")
        
        return results
    
    def compare_stability_ratios(self, ratio_data: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
        """여러 종목의 안정성비율을 비교합니다."""
        comparison_data = []
        
        for symbol, data_list in ratio_data.items():
            if data_list:
                latest = data_list[0]  # 최신 데이터
                comparison_data.append({
                    'symbol': symbol,
                    'period': latest['period'],
                    'debt_ratio': latest['debt_ratio'],
                    'equity_ratio': latest['equity_ratio'],
                    'borrowing_dependency': latest['borrowing_dependency'],
                    'current_ratio': latest['current_ratio'],
                    'quick_ratio': latest['quick_ratio'],
                    'stability_score': latest['stability_score'],
                    'stability_grade': latest['stability_grade'],
                    'liquidity_grade': latest['liquidity_grade'],
                    'total_stability_score': latest['total_stability_score']
                })
        
        return pd.DataFrame(comparison_data)
    
    def analyze_investment_attractiveness(self, ratio_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """투자 매력도를 분석합니다."""
        if not ratio_data:
            return {"error": "분석할 데이터가 없습니다."}
        
        latest = ratio_data[0]
        
        analysis = {}
        
        # 안정성 평가
        analysis['stability_assessment'] = self._assess_investment_stability(latest)
        
        # 유동성 평가
        analysis['liquidity_assessment'] = self._assess_investment_liquidity(latest)
        
        # 부채 구조 평가
        analysis['debt_structure_assessment'] = self._assess_investment_debt_structure(latest)
        
        # 종합 투자 매력도
        analysis['overall_attractiveness'] = self._calculate_investment_attractiveness(analysis)
        
        return analysis
    
    def _assess_investment_stability(self, data: Dict[str, Any]) -> str:
        """투자 관점에서 안정성을 평가합니다."""
        debt_ratio = data['debt_ratio']
        equity_ratio = data['equity_ratio']
        
        if debt_ratio <= 30 and equity_ratio >= 70:
            return "매우 안정"
        elif debt_ratio <= 50 and equity_ratio >= 50:
            return "안정"
        elif debt_ratio <= 70 and equity_ratio >= 30:
            return "보통"
        else:
            return "불안정"
    
    def _assess_investment_liquidity(self, data: Dict[str, Any]) -> str:
        """투자 관점에서 유동성을 평가합니다."""
        current_ratio = data['current_ratio']
        quick_ratio = data['quick_ratio']
        
        if current_ratio >= 200 and quick_ratio >= 100:
            return "매우 우수"
        elif current_ratio >= 150 and quick_ratio >= 80:
            return "우수"
        elif current_ratio >= 100 and quick_ratio >= 50:
            return "양호"
        elif current_ratio >= 50 and quick_ratio >= 30:
            return "보통"
        else:
            return "우려"
    
    def _assess_investment_debt_structure(self, data: Dict[str, Any]) -> str:
        """투자 관점에서 부채 구조를 평가합니다."""
        debt_ratio = data['debt_ratio']
        borrowing_dependency = data['borrowing_dependency']
        
        if debt_ratio <= 30 and borrowing_dependency <= 20:
            return "매우 우수"
        elif debt_ratio <= 50 and borrowing_dependency <= 40:
            return "우수"
        elif debt_ratio <= 70 and borrowing_dependency <= 60:
            return "양호"
        elif debt_ratio <= 100 and borrowing_dependency <= 80:
            return "보통"
        else:
            return "우려"
    
    def _calculate_investment_attractiveness(self, analysis: Dict[str, Any]) -> str:
        """종합 투자 매력도를 계산합니다."""
        assessments = [
            analysis['stability_assessment'],
            analysis['liquidity_assessment'],
            analysis['debt_structure_assessment']
        ]
        
        # 매력도 점수 계산
        score = 0
        for assessment in assessments:
            if "매우" in assessment:
                score += 4
            elif "우수" in assessment or "안정" in assessment:
                score += 3
            elif "양호" in assessment or "보통" in assessment:
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
    analyzer = StabilityRatioAnalyzer(provider)
    
    # 삼성전자 안정성비율 조회 테스트
    samsung_ratios = analyzer.get_stability_ratios("005930")
    if samsung_ratios:
        print("📊 삼성전자 안정성비율 (최신 3개 기간):")
        for i, data in enumerate(samsung_ratios[:3]):
            print(f"\n📅 {data['period']} 기간:")
            print(f"  부채비율: {data['debt_ratio']:.1f}%")
            print(f"  자기자본비율: {data['equity_ratio']:.1f}%")
            print(f"  차입금 의존도: {data['borrowing_dependency']:.1f}%")
            print(f"  유동비율: {data['current_ratio']:.1f}%")
            print(f"  당좌비율: {data['quick_ratio']:.1f}%")
            print(f"  안정성점수: {data['stability_score']:.1f}점")
            print(f"  안정성등급: {data['stability_grade']}")
            print(f"  유동성등급: {data['liquidity_grade']}")
            print(f"  종합점수: {data['total_stability_score']:.1f}점")
        
        # 추세 분석
        trend_analysis = analyzer.analyze_stability_ratio_trend(samsung_ratios)
        print(f"\n📈 안정성비율 추세 분석:")
        print(f"  부채비율 변화: {trend_analysis['stability_trend']['debt_ratio_change']:+.1f}%p")
        print(f"  자기자본비율 변화: {trend_analysis['stability_trend']['equity_ratio_change']:+.1f}%p")
        print(f"  유동비율 변화: {trend_analysis['stability_trend']['current_ratio_change']:+.1f}%p")
        print(f"  당좌비율 변화: {trend_analysis['stability_trend']['quick_ratio_change']:+.1f}%p")
        print(f"  개선도: {trend_analysis['improvement_assessment']}")
        print(f"  일관성: {trend_analysis['consistency_assessment']}")
        
        # 투자 매력도 분석
        attractiveness = analyzer.analyze_investment_attractiveness(samsung_ratios)
        print(f"\n💎 투자 매력도 분석:")
        print(f"  안정성 평가: {attractiveness['stability_assessment']}")
        print(f"  유동성 평가: {attractiveness['liquidity_assessment']}")
        print(f"  부채구조 평가: {attractiveness['debt_structure_assessment']}")
        print(f"  종합 매력도: {attractiveness['overall_attractiveness']}")
    else:
        print("❌ 삼성전자 안정성비율 조회 실패")

if __name__ == "__main__":
    main()
