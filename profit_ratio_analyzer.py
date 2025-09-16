#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수익성비율 분석 모듈
KIS API 국내주식 수익성비율 API를 활용한 수익성비율 분석
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time
from parallel_utils import parallel_analyze_stocks, parallel_analyze_with_retry, batch_parallel_analyze

logger = logging.getLogger(__name__)

class ProfitRatioAnalyzer:
    """수익성비율 분석 클래스"""
    
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
    
    def get_profit_ratios(self, symbol: str, period_type: str = "0", max_retries: int = 5) -> Optional[List[Dict[str, Any]]]:
        """
        종목의 수익성비율을 조회합니다.
        
        Args:
            symbol: 종목코드 (6자리)
            period_type: 분류 구분 코드 (0: 년, 1: 분기)
            max_retries: 최대 재시도 횟수
        
        Returns:
            수익성비율 데이터 리스트
        """
        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()
                
                path = "/uapi/domestic-stock/v1/finance/profit-ratio"
                params = {
                    "fid_input_iscd": symbol,
                    "FID_DIV_CLS_CODE": period_type,  # 0: 년, 1: 분기
                    "fid_cond_mrkt_div_code": "J"     # 국내주식
                }
                
                data = self.provider._send_request(path, "FHKST66430400", params)
                if data and 'output' in data and data['output']:
                    return self._parse_profit_ratio_data(data['output'])
                else:
                    if attempt < max_retries:
                        logger.debug(f"🔄 {symbol} 수익성비율 조회 재시도 중... ({attempt + 1}/{max_retries})")
                        time.sleep(5.0)  # 재시도 전 대기 (5초)
                        continue
                    else:
                        logger.debug(f"⚠️ {symbol} 수익성비율 데이터 없음")
                        return None
                        
            except Exception as e:
                if attempt < max_retries:
                    logger.debug(f"🔄 {symbol} 수익성비율 API 호출 재시도 중... ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(5.0)  # 재시도 전 대기 (5초)
                    continue
                else:
                    logger.debug(f"❌ {symbol} 수익성비율 API 호출 실패: {e}")
                    return None
        
        return None
    
    def _parse_profit_ratio_data(self, output_list: List[Dict]) -> List[Dict[str, Any]]:
        """수익성비율 응답 데이터를 파싱합니다."""
        parsed_data = []
        
        for item in output_list:
            parsed_item = {
                'period': item.get('stac_yymm', ''),
                'roa': self._to_float(item.get('cptl_ntin_rate', 0)),  # 총자본 순이익율
                'roe': self._to_float(item.get('self_cptl_ntin_inrt', 0)),  # 자기자본 순이익율
                'net_profit_margin': self._to_float(item.get('sale_ntin_rate', 0)),  # 매출액 순이익율
                'gross_profit_margin': self._to_float(item.get('sale_totl_rate', 0))  # 매출액 총이익율
            }
            
            # 추가 계산 지표
            parsed_item.update(self._calculate_additional_metrics(parsed_item))
            parsed_data.append(parsed_item)
        
        return parsed_data
    
    def _calculate_additional_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """추가 수익성 지표를 계산합니다."""
        metrics = {}
        
        # 수익성 점수 (ROA, ROE, 순이익률의 가중평균)
        profitability_scores = []
        if data['roa'] > 0:
            profitability_scores.append(data['roa'])
        if data['roe'] > 0:
            profitability_scores.append(data['roe'])
        if data['net_profit_margin'] > 0:
            profitability_scores.append(data['net_profit_margin'])
        
        if profitability_scores:
            metrics['profitability_score'] = sum(profitability_scores) / len(profitability_scores)
        else:
            metrics['profitability_score'] = 0
        
        # 수익성 등급 평가
        metrics['profitability_grade'] = self._evaluate_profitability_grade(data)
        
        # 수익성 안정성 (변동성 기반)
        metrics['profitability_stability'] = self._evaluate_profitability_stability(data)
        
        # 종합 수익성 점수
        metrics['total_profitability_score'] = self._calculate_total_profitability_score(data, metrics)
        
        return metrics
    
    def _evaluate_profitability_grade(self, data: Dict[str, Any]) -> str:
        """수익성 등급을 평가합니다."""
        roa = data['roa']
        roe = data['roe']
        net_margin = data['net_profit_margin']
        
        # 각 지표별 점수 계산
        roa_score = 0
        if roa > 10:
            roa_score = 4
        elif roa > 5:
            roa_score = 3
        elif roa > 2:
            roa_score = 2
        elif roa > 0:
            roa_score = 1
        
        roe_score = 0
        if roe > 15:
            roe_score = 4
        elif roe > 10:
            roe_score = 3
        elif roe > 5:
            roe_score = 2
        elif roe > 0:
            roe_score = 1
        
        margin_score = 0
        if net_margin > 15:
            margin_score = 4
        elif net_margin > 10:
            margin_score = 3
        elif net_margin > 5:
            margin_score = 2
        elif net_margin > 0:
            margin_score = 1
        
        # 종합 점수
        total_score = roa_score + roe_score + margin_score
        
        if total_score >= 10:
            return "우수"
        elif total_score >= 7:
            return "양호"
        elif total_score >= 4:
            return "보통"
        else:
            return "우려"
    
    def _evaluate_profitability_stability(self, data: Dict[str, Any]) -> str:
        """수익성 안정성을 평가합니다."""
        roa = data['roa']
        roe = data['roe']
        net_margin = data['net_profit_margin']
        
        # 모든 지표가 양수인지 확인
        positive_indicators = sum([1 for x in [roa, roe, net_margin] if x > 0])
        
        if positive_indicators == 3:
            return "매우 안정"
        elif positive_indicators == 2:
            return "안정"
        elif positive_indicators == 1:
            return "불안정"
        else:
            return "위험"
    
    def _calculate_total_profitability_score(self, data: Dict[str, Any], metrics: Dict[str, Any]) -> float:
        """종합 수익성 점수를 계산합니다."""
        # 기본 수익성 점수 (40%)
        base_score = metrics['profitability_score'] * 0.4
        
        # 등급 점수 (30%)
        grade_score = 0
        if metrics['profitability_grade'] == "우수":
            grade_score = 100
        elif metrics['profitability_grade'] == "양호":
            grade_score = 75
        elif metrics['profitability_grade'] == "보통":
            grade_score = 50
        else:
            grade_score = 25
        grade_score *= 0.3
        
        # 안정성 점수 (30%)
        stability_score = 0
        if metrics['profitability_stability'] == "매우 안정":
            stability_score = 100
        elif metrics['profitability_stability'] == "안정":
            stability_score = 75
        elif metrics['profitability_stability'] == "불안정":
            stability_score = 50
        else:
            stability_score = 25
        stability_score *= 0.3
        
        return base_score + grade_score + stability_score
    
    def analyze_profit_ratio_trend(self, ratio_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """수익성비율 추세를 분석합니다."""
        if len(ratio_data) < 2:
            return {"error": "분석을 위해 최소 2개 기간의 데이터가 필요합니다."}
        
        # 최신 데이터와 이전 데이터 비교
        latest = ratio_data[0]
        previous = ratio_data[1] if len(ratio_data) > 1 else latest
        
        analysis = {}
        
        # 수익성비율 추세
        analysis['profit_trend'] = {
            'roa_change': latest['roa'] - previous['roa'],
            'roe_change': latest['roe'] - previous['roe'],
            'net_margin_change': latest['net_profit_margin'] - previous['net_profit_margin'],
            'gross_margin_change': latest['gross_profit_margin'] - previous['gross_profit_margin']
        }
        
        # 수익성 개선도 평가
        analysis['improvement_assessment'] = self._assess_profitability_improvement(analysis['profit_trend'])
        
        # 수익성 일관성 평가
        analysis['consistency_assessment'] = self._assess_profitability_consistency(ratio_data)
        
        return analysis
    
    def _assess_profitability_improvement(self, trend: Dict[str, Any]) -> str:
        """수익성 개선도를 평가합니다."""
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
    
    def _assess_profitability_consistency(self, ratio_data: List[Dict[str, Any]]) -> str:
        """수익성 일관성을 평가합니다."""
        if len(ratio_data) < 3:
            return "평가불가"
        
        # 최근 3개 기간의 ROE 변동성 계산
        recent_roe = [data['roe'] for data in ratio_data[:3]]
        roe_mean = sum(recent_roe) / len(recent_roe)
        roe_variance = sum((x - roe_mean) ** 2 for x in recent_roe) / len(recent_roe)
        roe_std = roe_variance ** 0.5
        
        # 변동성 기준
        if roe_std < 2:
            return "매우 일관적"
        elif roe_std < 5:
            return "일관적"
        elif roe_std < 10:
            return "보통"
        else:
            return "불안정"
    
    def get_multiple_profit_ratios(self, symbols: List[str], period_type: str = "0") -> Dict[str, List[Dict[str, Any]]]:
        """여러 종목의 수익성비율을 조회합니다."""
        results = {}
        
        for symbol in symbols:
            logger.info(f"🔍 {symbol} 수익성비율 조회 중...")
            ratios = self.get_profit_ratios(symbol, period_type)
            if ratios:
                results[symbol] = ratios
            else:
                logger.warning(f"⚠️ {symbol} 수익성비율 조회 실패")
        
        return results
    
    def compare_profit_ratios(self, ratio_data: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
        """여러 종목의 수익성비율을 비교합니다."""
        comparison_data = []
        
        for symbol, data_list in ratio_data.items():
            if data_list:
                latest = data_list[0]  # 최신 데이터
                comparison_data.append({
                    'symbol': symbol,
                    'period': latest['period'],
                    'roa': latest['roa'],
                    'roe': latest['roe'],
                    'net_profit_margin': latest['net_profit_margin'],
                    'gross_profit_margin': latest['gross_profit_margin'],
                    'profitability_score': latest['profitability_score'],
                    'profitability_grade': latest['profitability_grade'],
                    'profitability_stability': latest['profitability_stability'],
                    'total_profitability_score': latest['total_profitability_score']
                })
        
        return pd.DataFrame(comparison_data)
    
    def analyze_investment_attractiveness(self, ratio_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """투자 매력도를 분석합니다."""
        if not ratio_data:
            return {"error": "분석할 데이터가 없습니다."}
        
        latest = ratio_data[0]
        
        analysis = {}
        
        # 수익성 평가
        analysis['profitability_assessment'] = self._assess_investment_profitability(latest)
        
        # 성장성 평가 (과거 데이터와 비교)
        analysis['growth_assessment'] = self._assess_investment_growth(ratio_data)
        
        # 안정성 평가
        analysis['stability_assessment'] = self._assess_investment_stability(ratio_data)
        
        # 종합 투자 매력도
        analysis['overall_attractiveness'] = self._calculate_investment_attractiveness(analysis)
        
        return analysis
    
    def _assess_investment_profitability(self, data: Dict[str, Any]) -> str:
        """투자 관점에서 수익성을 평가합니다."""
        roa = data['roa']
        roe = data['roe']
        net_margin = data['net_profit_margin']
        
        # 높은 수익성 기준
        if roa > 10 and roe > 15 and net_margin > 10:
            return "매우 매력적"
        elif roa > 5 and roe > 10 and net_margin > 5:
            return "매력적"
        elif roa > 2 and roe > 5 and net_margin > 2:
            return "보통"
        else:
            return "비매력적"
    
    def _assess_investment_growth(self, ratio_data: List[Dict[str, Any]]) -> str:
        """투자 관점에서 성장성을 평가합니다."""
        if len(ratio_data) < 2:
            return "평가불가"
        
        # 최근 2개 기간의 ROE 변화
        recent_roe = [data['roe'] for data in ratio_data[:2]]
        roe_growth = recent_roe[0] - recent_roe[1]
        
        if roe_growth > 5:
            return "고성장"
        elif roe_growth > 0:
            return "성장"
        elif roe_growth > -5:
            return "안정"
        else:
            return "둔화"
    
    def _assess_investment_stability(self, ratio_data: List[Dict[str, Any]]) -> str:
        """투자 관점에서 안정성을 평가합니다."""
        if len(ratio_data) < 3:
            return "평가불가"
        
        # 최근 3개 기간의 수익성 일관성
        recent_roe = [data['roe'] for data in ratio_data[:3]]
        positive_periods = sum(1 for roe in recent_roe if roe > 0)
        
        if positive_periods == 3:
            return "매우 안정"
        elif positive_periods == 2:
            return "안정"
        elif positive_periods == 1:
            return "불안정"
        else:
            return "위험"
    
    def _calculate_investment_attractiveness(self, analysis: Dict[str, Any]) -> str:
        """종합 투자 매력도를 계산합니다."""
        assessments = [
            analysis['profitability_assessment'],
            analysis['growth_assessment'],
            analysis['stability_assessment']
        ]
        
        # 매력도 점수 계산
        score = 0
        for assessment in assessments:
            if "매우" in assessment or "고성장" in assessment:
                score += 4
            elif "매력적" in assessment or "성장" in assessment or "안정" in assessment:
                score += 3
            elif "보통" in assessment:
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
    
    def parallel_compare_profit_ratios(self, symbols: List[str], period_type: str = "0", 
                                     max_workers: int = 3, use_retry: bool = True) -> Optional[pd.DataFrame]:
        """여러 종목의 수익성비율을 병렬로 비교합니다."""
        if not symbols:
            return None
        
        # 종목 데이터 준비
        stocks_data = [{'symbol': symbol, 'period_type': period_type} for symbol in symbols]
        
        def analyze_single_stock(stock_data):
            """단일 종목 분석 함수"""
            symbol = stock_data['symbol']
            period_type = stock_data['period_type']
            
            ratios = self.get_profit_ratios(symbol, period_type)
            if ratios and len(ratios) > 0:
                latest_ratio = ratios[0]
                latest_ratio['symbol'] = symbol
                return latest_ratio
            return None
        
        # 병렬 분석 실행
        if use_retry:
            results = parallel_analyze_with_retry(
                stocks_data, 
                analyze_single_stock, 
                max_workers=max_workers,
                show_progress=True,
                progress_description="수익성비율 병렬 분석 중..."
            )
        else:
            results = parallel_analyze_stocks(
                stocks_data, 
                analyze_single_stock, 
                max_workers=max_workers,
                show_progress=True,
                progress_description="수익성비율 병렬 분석 중..."
            )
        
        # 유효한 결과만 필터링
        valid_results = [r for r in results if r is not None and 'error' not in r]
        
        if not valid_results:
            return None
        
        return pd.DataFrame(valid_results)
    
    def batch_compare_profit_ratios(self, symbols: List[str], period_type: str = "0", 
                                   batch_size: int = 10, max_workers: int = 3) -> Optional[pd.DataFrame]:
        """여러 종목의 수익성비율을 배치 단위로 병렬 비교합니다."""
        if not symbols:
            return None
        
        # 종목 데이터 준비
        stocks_data = [{'symbol': symbol, 'period_type': period_type} for symbol in symbols]
        
        def analyze_single_stock(stock_data):
            """단일 종목 분석 함수"""
            symbol = stock_data['symbol']
            period_type = stock_data['period_type']
            
            ratios = self.get_profit_ratios(symbol, period_type)
            if ratios and len(ratios) > 0:
                latest_ratio = ratios[0]
                latest_ratio['symbol'] = symbol
                return latest_ratio
            return None
        
        # 배치 병렬 분석 실행
        results = batch_parallel_analyze(
            stocks_data, 
            analyze_single_stock, 
            batch_size=batch_size,
            max_workers=max_workers,
            show_progress=True,
            progress_description="수익성비율 배치 병렬 분석 중..."
        )
        
        # 유효한 결과만 필터링
        valid_results = [r for r in results if r is not None and 'error' not in r]
        
        if not valid_results:
            return None
        
        return pd.DataFrame(valid_results)

def main():
    """테스트 함수"""
    from kis_data_provider import KISDataProvider
    
    provider = KISDataProvider()
    analyzer = ProfitRatioAnalyzer(provider)
    
    # 삼성전자 수익성비율 조회 테스트
    samsung_ratios = analyzer.get_profit_ratios("005930")
    if samsung_ratios:
        print("📊 삼성전자 수익성비율 (최신 3개 기간):")
        for i, data in enumerate(samsung_ratios[:3]):
            print(f"\n📅 {data['period']} 기간:")
            print(f"  ROA: {data['roa']:.2f}%")
            print(f"  ROE: {data['roe']:.2f}%")
            print(f"  순이익률: {data['net_profit_margin']:.2f}%")
            print(f"  총이익률: {data['gross_profit_margin']:.2f}%")
            print(f"  수익성점수: {data['profitability_score']:.1f}점")
            print(f"  수익성등급: {data['profitability_grade']}")
            print(f"  안정성: {data['profitability_stability']}")
            print(f"  종합점수: {data['total_profitability_score']:.1f}점")
        
        # 추세 분석
        trend_analysis = analyzer.analyze_profit_ratio_trend(samsung_ratios)
        print(f"\n📈 수익성비율 추세 분석:")
        print(f"  ROA 변화: {trend_analysis['profit_trend']['roa_change']:+.2f}%p")
        print(f"  ROE 변화: {trend_analysis['profit_trend']['roe_change']:+.2f}%p")
        print(f"  순이익률 변화: {trend_analysis['profit_trend']['net_margin_change']:+.2f}%p")
        print(f"  개선도: {trend_analysis['improvement_assessment']}")
        print(f"  일관성: {trend_analysis['consistency_assessment']}")
        
        # 투자 매력도 분석
        attractiveness = analyzer.analyze_investment_attractiveness(samsung_ratios)
        print(f"\n💎 투자 매력도 분석:")
        print(f"  수익성 평가: {attractiveness['profitability_assessment']}")
        print(f"  성장성 평가: {attractiveness['growth_assessment']}")
        print(f"  안정성 평가: {attractiveness['stability_assessment']}")
        print(f"  종합 매력도: {attractiveness['overall_attractiveness']}")
    else:
        print("❌ 삼성전자 수익성비율 조회 실패")

if __name__ == "__main__":
    main()
