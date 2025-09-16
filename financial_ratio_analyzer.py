#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
재무비율 분석 모듈
KIS API 국내주식 재무비율 API를 활용한 재무비율 분석
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time
from parallel_utils import parallel_analyze_stocks, parallel_analyze_with_retry, batch_parallel_analyze

logger = logging.getLogger(__name__)

class FinancialRatioAnalyzer:
    """재무비율 분석 클래스"""
    
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
    
    def get_financial_ratios(self, symbol: str, period_type: str = "0", max_retries: int = 2) -> Optional[List[Dict[str, Any]]]:
        """
        종목의 재무비율을 조회합니다.
        
        Args:
            symbol: 종목코드 (6자리)
            period_type: 분류 구분 코드 (0: 년, 1: 분기)
            max_retries: 최대 재시도 횟수
        
        Returns:
            재무비율 데이터 리스트
        """
        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()
                
                path = "/uapi/domestic-stock/v1/finance/financial-ratio"
                params = {
                    "FID_DIV_CLS_CODE": period_type,  # 0: 년, 1: 분기
                    "fid_cond_mrkt_div_code": "J",    # 국내주식
                    "fid_input_iscd": symbol
                }
                
                data = self.provider._send_request(path, "FHKST66430300", params)
                if data and 'output' in data and data['output']:
                    return self._parse_financial_ratio_data(data['output'])
                else:
                    if attempt < max_retries:
                        logger.debug(f"🔄 {symbol} 재무비율 조회 재시도 중... ({attempt + 1}/{max_retries})")
                        time.sleep(0.5)
                        continue
                    else:
                        logger.debug(f"⚠️ {symbol} 재무비율 데이터 없음")
                        return None
                        
            except Exception as e:
                if attempt < max_retries:
                    logger.debug(f"🔄 {symbol} 재무비율 API 호출 재시도 중... ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(0.5)
                    continue
                else:
                    logger.debug(f"❌ {symbol} 재무비율 API 호출 실패: {e}")
                    return None
        
        return None
    
    def _parse_financial_ratio_data(self, output_list: List[Dict]) -> List[Dict[str, Any]]:
        """재무비율 응답 데이터를 파싱합니다."""
        parsed_data = []
        
        for item in output_list:
            parsed_item = {
                'period': item.get('stac_yymm', ''),
                'revenue_growth_rate': self._to_float(item.get('grs', 0)),
                'operating_income_growth_rate': self._to_float(item.get('bsop_prfi_inrt', 0)),
                'net_income_growth_rate': self._to_float(item.get('ntin_inrt', 0)),
                'roe': self._to_float(item.get('roe_val', 0)),
                'eps': self._to_float(item.get('eps', 0)),
                'sps': self._to_float(item.get('sps', 0)),  # 주당매출액
                'bps': self._to_float(item.get('bps', 0)),
                'retained_earnings_ratio': self._to_float(item.get('rsrv_rate', 0)),
                'debt_ratio': self._to_float(item.get('lblt_rate', 0))
            }
            
            # 추가 계산 지표
            parsed_item.update(self._calculate_additional_ratios(parsed_item))
            parsed_data.append(parsed_item)
        
        return parsed_data
    
    def _calculate_additional_ratios(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """추가 재무비율을 계산합니다."""
        ratios = {}
        
        # ROA (자산수익률) - ROE와 부채비율을 이용한 근사치
        if data['roe'] > 0 and data['debt_ratio'] > 0:
            # ROA ≈ ROE / (1 + 부채비율/100)
            ratios['roa'] = data['roe'] / (1 + data['debt_ratio'] / 100)
        else:
            ratios['roa'] = 0
        
        # 자기자본비율 (100 - 부채비율)
        ratios['equity_ratio'] = 100 - data['debt_ratio']
        
        # 성장성 점수 (매출, 영업이익, 순이익 성장률의 가중평균)
        growth_rates = [
            data['revenue_growth_rate'],
            data['operating_income_growth_rate'],
            data['net_income_growth_rate']
        ]
        # 0이 아닌 성장률만 평균 계산
        valid_growth_rates = [rate for rate in growth_rates if rate != 0]
        if valid_growth_rates:
            ratios['growth_score'] = sum(valid_growth_rates) / len(valid_growth_rates)
        else:
            ratios['growth_score'] = 0
        
        # 수익성 점수 (ROE, ROA의 가중평균)
        profitability_scores = []
        if data['roe'] > 0:
            profitability_scores.append(data['roe'])
        if ratios['roa'] > 0:
            profitability_scores.append(ratios['roa'])
        
        if profitability_scores:
            ratios['profitability_score'] = sum(profitability_scores) / len(profitability_scores)
        else:
            ratios['profitability_score'] = 0
        
        # 안정성 점수 (부채비율이 낮을수록 높은 점수)
        if data['debt_ratio'] <= 30:
            ratios['stability_score'] = 100
        elif data['debt_ratio'] <= 50:
            ratios['stability_score'] = 80
        elif data['debt_ratio'] <= 70:
            ratios['stability_score'] = 60
        elif data['debt_ratio'] <= 100:
            ratios['stability_score'] = 40
        else:
            ratios['stability_score'] = 20
        
        # 종합 점수 (성장성 30%, 수익성 40%, 안정성 30%)
        ratios['total_score'] = (
            ratios['growth_score'] * 0.3 +
            ratios['profitability_score'] * 0.4 +
            ratios['stability_score'] * 0.3
        )
        
        return ratios
    
    def analyze_financial_ratio_trend(self, ratio_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """재무비율 추세를 분석합니다."""
        if len(ratio_data) < 2:
            return {"error": "분석을 위해 최소 2개 기간의 데이터가 필요합니다."}
        
        # 최신 데이터와 이전 데이터 비교
        latest = ratio_data[0]
        previous = ratio_data[1] if len(ratio_data) > 1 else latest
        
        analysis = {}
        
        # 성장률 추세
        analysis['growth_trend'] = {
            'revenue_growth_change': latest['revenue_growth_rate'] - previous['revenue_growth_rate'],
            'operating_growth_change': latest['operating_income_growth_rate'] - previous['operating_income_growth_rate'],
            'net_growth_change': latest['net_income_growth_rate'] - previous['net_income_growth_rate']
        }
        
        # 수익성 추세
        analysis['profitability_trend'] = {
            'roe_change': latest['roe'] - previous['roe'],
            'roa_change': latest['roa'] - previous['roa'],
            'eps_change': latest['eps'] - previous['eps']
        }
        
        # 안정성 추세
        analysis['stability_trend'] = {
            'debt_ratio_change': latest['debt_ratio'] - previous['debt_ratio'],
            'equity_ratio_change': latest['equity_ratio'] - previous['equity_ratio']
        }
        
        # 종합 평가
        analysis['overall_assessment'] = self._evaluate_financial_health(latest)
        
        return analysis
    
    def _evaluate_financial_health(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """재무 건전성을 평가합니다."""
        assessment = {}
        
        # ROE 평가
        roe = data['roe']
        if roe > 15:
            assessment['roe_grade'] = "우수"
        elif roe > 10:
            assessment['roe_grade'] = "양호"
        elif roe > 5:
            assessment['roe_grade'] = "보통"
        else:
            assessment['roe_grade'] = "우려"
        
        # ROA 평가
        roa = data['roa']
        if roa > 10:
            assessment['roa_grade'] = "우수"
        elif roa > 5:
            assessment['roa_grade'] = "양호"
        elif roa > 2:
            assessment['roa_grade'] = "보통"
        else:
            assessment['roa_grade'] = "우려"
        
        # 부채비율 평가
        debt_ratio = data['debt_ratio']
        if debt_ratio < 30:
            assessment['debt_grade'] = "우수"
        elif debt_ratio < 50:
            assessment['debt_grade'] = "양호"
        elif debt_ratio < 70:
            assessment['debt_grade'] = "보통"
        else:
            assessment['debt_grade'] = "우려"
        
        # 성장성 평가
        growth_score = data['growth_score']
        if growth_score > 20:
            assessment['growth_grade'] = "우수"
        elif growth_score > 10:
            assessment['growth_grade'] = "양호"
        elif growth_score > 0:
            assessment['growth_grade'] = "보통"
        else:
            assessment['growth_grade'] = "우려"
        
        # 종합 등급
        grades = [assessment['roe_grade'], assessment['roa_grade'], assessment['debt_grade'], assessment['growth_grade']]
        if grades.count("우수") >= 3:
            assessment['overall_grade'] = "우수"
        elif grades.count("우수") >= 2 or grades.count("양호") >= 3:
            assessment['overall_grade'] = "양호"
        elif grades.count("우려") <= 1:
            assessment['overall_grade'] = "보통"
        else:
            assessment['overall_grade'] = "우려"
        
        return assessment
    
    def get_multiple_financial_ratios(self, symbols: List[str], period_type: str = "0") -> Dict[str, List[Dict[str, Any]]]:
        """여러 종목의 재무비율을 조회합니다."""
        results = {}
        
        for symbol in symbols:
            logger.info(f"🔍 {symbol} 재무비율 조회 중...")
            ratios = self.get_financial_ratios(symbol, period_type)
            if ratios:
                results[symbol] = ratios
            else:
                logger.warning(f"⚠️ {symbol} 재무비율 조회 실패")
        
        return results
    
    def compare_financial_ratios(self, ratio_data: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
        """여러 종목의 재무비율을 비교합니다."""
        comparison_data = []
        
        for symbol, data_list in ratio_data.items():
            if data_list:
                latest = data_list[0]  # 최신 데이터
                comparison_data.append({
                    'symbol': symbol,
                    'period': latest['period'],
                    'roe': latest['roe'],
                    'roa': latest['roa'],
                    'eps': latest['eps'],
                    'bps': latest['bps'],
                    'sps': latest['sps'],
                    'debt_ratio': latest['debt_ratio'],
                    'equity_ratio': latest['equity_ratio'],
                    'retained_earnings_ratio': latest['retained_earnings_ratio'],
                    'revenue_growth_rate': latest['revenue_growth_rate'],
                    'operating_growth_rate': latest['operating_income_growth_rate'],
                    'net_growth_rate': latest['net_income_growth_rate'],
                    'growth_score': latest['growth_score'],
                    'profitability_score': latest['profitability_score'],
                    'stability_score': latest['stability_score'],
                    'total_score': latest['total_score']
                })
        
        return pd.DataFrame(comparison_data)
    
    def analyze_investment_attractiveness(self, ratio_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """투자 매력도를 분석합니다."""
        if not ratio_data:
            return {"error": "분석할 데이터가 없습니다."}
        
        latest = ratio_data[0]
        
        analysis = {}
        
        # 가치 평가
        analysis['value_assessment'] = self._assess_value(latest)
        
        # 성장성 평가
        analysis['growth_assessment'] = self._assess_growth(latest)
        
        # 수익성 평가
        analysis['profitability_assessment'] = self._assess_profitability(latest)
        
        # 안정성 평가
        analysis['stability_assessment'] = self._assess_stability(latest)
        
        # 종합 투자 매력도
        analysis['overall_attractiveness'] = self._calculate_overall_attractiveness(analysis)
        
        return analysis
    
    def _assess_value(self, data: Dict[str, Any]) -> str:
        """가치 평가를 수행합니다."""
        # ROE와 성장률을 기반으로 가치 평가
        roe = data['roe']
        growth_rate = data['growth_score']
        
        if roe > 15 and growth_rate > 10:
            return "매우 매력적"
        elif roe > 10 and growth_rate > 5:
            return "매력적"
        elif roe > 5 and growth_rate > 0:
            return "보통"
        else:
            return "비매력적"
    
    def _assess_growth(self, data: Dict[str, Any]) -> str:
        """성장성 평가를 수행합니다."""
        growth_score = data['growth_score']
        
        if growth_score > 20:
            return "고성장"
        elif growth_score > 10:
            return "성장"
        elif growth_score > 0:
            return "안정"
        else:
            return "둔화"
    
    def _assess_profitability(self, data: Dict[str, Any]) -> str:
        """수익성 평가를 수행합니다."""
        roe = data['roe']
        roa = data['roa']
        
        if roe > 15 and roa > 10:
            return "우수"
        elif roe > 10 and roa > 5:
            return "양호"
        elif roe > 5 and roa > 2:
            return "보통"
        else:
            return "우려"
    
    def _assess_stability(self, data: Dict[str, Any]) -> str:
        """안정성 평가를 수행합니다."""
        debt_ratio = data['debt_ratio']
        equity_ratio = data['equity_ratio']
        
        if debt_ratio < 30 and equity_ratio > 70:
            return "매우 안정"
        elif debt_ratio < 50 and equity_ratio > 50:
            return "안정"
        elif debt_ratio < 70 and equity_ratio > 30:
            return "보통"
        else:
            return "불안정"
    
    def _calculate_overall_attractiveness(self, analysis: Dict[str, Any]) -> str:
        """종합 투자 매력도를 계산합니다."""
        assessments = [
            analysis['value_assessment'],
            analysis['growth_assessment'],
            analysis['profitability_assessment'],
            analysis['stability_assessment']
        ]
        
        # 매력도 점수 계산
        score = 0
        for assessment in assessments:
            if "매우" in assessment or "우수" in assessment or "고성장" in assessment or "매우 안정" in assessment:
                score += 4
            elif "매력적" in assessment or "양호" in assessment or "성장" in assessment or "안정" in assessment:
                score += 3
            elif "보통" in assessment or "안정" in assessment:
                score += 2
            else:
                score += 1
        
        # 종합 평가
        if score >= 14:
            return "매우 매력적"
        elif score >= 10:
            return "매력적"
        elif score >= 6:
            return "보통"
        else:
            return "비매력적"
    
    def parallel_compare_financial_ratios(self, symbols: List[str], period_type: str = "0", 
                                         max_workers: int = 3, use_retry: bool = True) -> Optional[pd.DataFrame]:
        """여러 종목의 재무비율을 병렬로 비교합니다."""
        if not symbols:
            return None
        
        # 종목 데이터 준비
        stocks_data = [{'symbol': symbol, 'period_type': period_type} for symbol in symbols]
        
        def analyze_single_stock(stock_data):
            """단일 종목 분석 함수"""
            symbol = stock_data['symbol']
            period_type = stock_data['period_type']
            
            ratios = self.get_financial_ratios(symbol, period_type)
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
                progress_description="재무비율 병렬 분석 중..."
            )
        else:
            results = parallel_analyze_stocks(
                stocks_data, 
                analyze_single_stock, 
                max_workers=max_workers,
                show_progress=True,
                progress_description="재무비율 병렬 분석 중..."
            )
        
        # 유효한 결과만 필터링
        valid_results = [r for r in results if r is not None and 'error' not in r]
        
        if not valid_results:
            return None
        
        return pd.DataFrame(valid_results)
    
    def batch_compare_financial_ratios(self, symbols: List[str], period_type: str = "0", 
                                      batch_size: int = 10, max_workers: int = 3) -> Optional[pd.DataFrame]:
        """여러 종목의 재무비율을 배치 단위로 병렬 비교합니다."""
        if not symbols:
            return None
        
        # 종목 데이터 준비
        stocks_data = [{'symbol': symbol, 'period_type': period_type} for symbol in symbols]
        
        def analyze_single_stock(stock_data):
            """단일 종목 분석 함수"""
            symbol = stock_data['symbol']
            period_type = stock_data['period_type']
            
            ratios = self.get_financial_ratios(symbol, period_type)
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
            progress_description="재무비율 배치 병렬 분석 중..."
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
    analyzer = FinancialRatioAnalyzer(provider)
    
    # 삼성전자 재무비율 조회 테스트
    samsung_ratios = analyzer.get_financial_ratios("005930")
    if samsung_ratios:
        print("📊 삼성전자 재무비율 (최신 3개 기간):")
        for i, data in enumerate(samsung_ratios[:3]):
            print(f"\n📅 {data['period']} 기간:")
            print(f"  ROE: {data['roe']:.2f}%")
            print(f"  ROA: {data['roa']:.2f}%")
            print(f"  EPS: {data['eps']:.0f}원")
            print(f"  BPS: {data['bps']:.0f}원")
            print(f"  부채비율: {data['debt_ratio']:.1f}%")
            print(f"  매출증가율: {data['revenue_growth_rate']:+.1f}%")
            print(f"  영업이익증가율: {data['operating_income_growth_rate']:+.1f}%")
            print(f"  순이익증가율: {data['net_income_growth_rate']:+.1f}%")
            print(f"  종합점수: {data['total_score']:.1f}점")
        
        # 추세 분석
        trend_analysis = analyzer.analyze_financial_ratio_trend(samsung_ratios)
        print(f"\n📈 재무비율 추세 분석:")
        print(f"  ROE 변화: {trend_analysis['profitability_trend']['roe_change']:+.2f}%p")
        print(f"  부채비율 변화: {trend_analysis['stability_trend']['debt_ratio_change']:+.1f}%p")
        print(f"  종합 등급: {trend_analysis['overall_assessment']['overall_grade']}")
        
        # 투자 매력도 분석
        attractiveness = analyzer.analyze_investment_attractiveness(samsung_ratios)
        print(f"\n💎 투자 매력도 분석:")
        print(f"  가치 평가: {attractiveness['value_assessment']}")
        print(f"  성장성 평가: {attractiveness['growth_assessment']}")
        print(f"  수익성 평가: {attractiveness['profitability_assessment']}")
        print(f"  안정성 평가: {attractiveness['stability_assessment']}")
        print(f"  종합 매력도: {attractiveness['overall_attractiveness']}")
    else:
        print("❌ 삼성전자 재무비율 조회 실패")

if __name__ == "__main__":
    main()
