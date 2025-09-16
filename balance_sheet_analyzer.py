#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
대차대조표 분석 모듈
KIS API 국내주식 대차대조표 API를 활용한 재무상태표 분석
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class BalanceSheetAnalyzer:
    """대차대조표 분석 클래스"""
    
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
        if value is None or value == '':
            return default
        try:
            # 쉼표 제거 후 float 변환
            return float(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return default
    
    def get_balance_sheet(self, symbol: str, period_type: str = "0") -> Optional[List[Dict[str, Any]]]:
        """
        종목의 대차대조표를 조회합니다.
        
        Args:
            symbol: 종목코드 (6자리)
            period_type: 분류 구분 코드 (0: 년, 1: 분기)
        
        Returns:
            대차대조표 데이터 리스트
        """
        self._rate_limit()
        
        path = "/uapi/domestic-stock/v1/finance/balance-sheet"
        params = {
            "FID_DIV_CLS_CODE": period_type,  # 0: 년, 1: 분기
            "fid_cond_mrkt_div_code": "J",    # 국내주식
            "fid_input_iscd": symbol
        }
        
        try:
            data = self.provider._send_request(path, "FHKST66430100", params)
            if data and 'output' in data:
                return self._parse_balance_sheet_data(data['output'])
            else:
                logger.warning(f"⚠️ {symbol} 대차대조표 조회 실패")
                return None
                
        except Exception as e:
            logger.error(f"❌ 대차대조표 API 호출 실패 ({symbol}): {e}")
            return None
    
    def _parse_balance_sheet_data(self, output_list: List[Dict]) -> List[Dict[str, Any]]:
        """대차대조표 응답 데이터를 파싱합니다."""
        parsed_data = []
        
        for item in output_list:
            parsed_item = {
                'period': item.get('stac_yymm', ''),
                'current_assets': self._to_float(item.get('cras', 0)),
                'fixed_assets': self._to_float(item.get('fxas', 0)),
                'total_assets': self._to_float(item.get('total_aset', 0)),
                'current_liabilities': self._to_float(item.get('flow_lblt', 0)),
                'fixed_liabilities': self._to_float(item.get('fix_lblt', 0)),
                'total_liabilities': self._to_float(item.get('total_lblt', 0)),
                'capital': self._to_float(item.get('cpfn', 0)),
                'capital_surplus': self._to_float(item.get('cfp_surp', 0)),
                'retained_earnings': self._to_float(item.get('prfi_surp', 0)),
                'total_equity': self._to_float(item.get('total_cptl', 0))
            }
            
            # 계산된 지표
            parsed_item.update(self._calculate_ratios(parsed_item))
            parsed_data.append(parsed_item)
        
        return parsed_data
    
    def _calculate_ratios(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """재무 비율을 계산합니다."""
        ratios = {}
        
        # 자산 구조 비율
        if data['total_assets'] > 0:
            ratios['current_assets_ratio'] = (data['current_assets'] / data['total_assets']) * 100
            ratios['fixed_assets_ratio'] = (data['fixed_assets'] / data['total_assets']) * 100
        else:
            ratios['current_assets_ratio'] = 0
            ratios['fixed_assets_ratio'] = 0
        
        # 부채 구조 비율
        if data['total_liabilities'] > 0:
            ratios['current_liabilities_ratio'] = (data['current_liabilities'] / data['total_liabilities']) * 100
            ratios['fixed_liabilities_ratio'] = (data['fixed_liabilities'] / data['total_liabilities']) * 100
        else:
            ratios['current_liabilities_ratio'] = 0
            ratios['fixed_liabilities_ratio'] = 0
        
        # 부채비율
        if data['total_equity'] > 0:
            ratios['debt_ratio'] = (data['total_liabilities'] / data['total_equity']) * 100
        else:
            ratios['debt_ratio'] = 0
        
        # 자기자본비율
        if data['total_assets'] > 0:
            ratios['equity_ratio'] = (data['total_equity'] / data['total_assets']) * 100
        else:
            ratios['equity_ratio'] = 0
        
        # 유동비율
        if data['current_liabilities'] > 0:
            ratios['current_ratio'] = (data['current_assets'] / data['current_liabilities']) * 100
        else:
            ratios['current_ratio'] = 0
        
        # 자본금 비율
        if data['total_equity'] > 0:
            ratios['capital_ratio'] = (data['capital'] / data['total_equity']) * 100
        else:
            ratios['capital_ratio'] = 0
        
        return ratios
    
    def analyze_balance_sheet_trend(self, balance_sheet_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """대차대조표 추세를 분석합니다."""
        if len(balance_sheet_data) < 2:
            return {"error": "분석을 위해 최소 2개 기간의 데이터가 필요합니다."}
        
        # 최신 데이터와 이전 데이터 비교
        latest = balance_sheet_data[0]
        previous = balance_sheet_data[1] if len(balance_sheet_data) > 1 else latest
        
        analysis = {}
        
        # 자산 추세
        analysis['assets_trend'] = {
            'total_assets_change': self._calculate_change_rate(latest['total_assets'], previous['total_assets']),
            'current_assets_change': self._calculate_change_rate(latest['current_assets'], previous['current_assets']),
            'fixed_assets_change': self._calculate_change_rate(latest['fixed_assets'], previous['fixed_assets'])
        }
        
        # 부채 추세
        analysis['liabilities_trend'] = {
            'total_liabilities_change': self._calculate_change_rate(latest['total_liabilities'], previous['total_liabilities']),
            'current_liabilities_change': self._calculate_change_rate(latest['current_liabilities'], previous['current_liabilities']),
            'fixed_liabilities_change': self._calculate_change_rate(latest['fixed_liabilities'], previous['fixed_liabilities'])
        }
        
        # 자본 추세
        analysis['equity_trend'] = {
            'total_equity_change': self._calculate_change_rate(latest['total_equity'], previous['total_equity']),
            'capital_change': self._calculate_change_rate(latest['capital'], previous['capital']),
            'retained_earnings_change': self._calculate_change_rate(latest['retained_earnings'], previous['retained_earnings'])
        }
        
        # 재무 안정성 평가
        analysis['financial_stability'] = self._evaluate_financial_stability(latest)
        
        return analysis
    
    def _calculate_change_rate(self, current: float, previous: float) -> float:
        """변화율을 계산합니다."""
        if previous == 0:
            return 0
        return ((current - previous) / previous) * 100
    
    def _evaluate_financial_stability(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """재무 안정성을 평가합니다."""
        stability = {}
        
        # 부채비율 평가
        debt_ratio = data['debt_ratio']
        if debt_ratio < 50:
            stability['debt_ratio_grade'] = "우수"
        elif debt_ratio < 100:
            stability['debt_ratio_grade'] = "양호"
        elif debt_ratio < 200:
            stability['debt_ratio_grade'] = "보통"
        else:
            stability['debt_ratio_grade'] = "우려"
        
        # 자기자본비율 평가
        equity_ratio = data['equity_ratio']
        if equity_ratio > 50:
            stability['equity_ratio_grade'] = "우수"
        elif equity_ratio > 30:
            stability['equity_ratio_grade'] = "양호"
        elif equity_ratio > 20:
            stability['equity_ratio_grade'] = "보통"
        else:
            stability['equity_ratio_grade'] = "우려"
        
        # 유동비율 평가
        current_ratio = data['current_ratio']
        if current_ratio > 200:
            stability['current_ratio_grade'] = "우수"
        elif current_ratio > 150:
            stability['current_ratio_grade'] = "양호"
        elif current_ratio > 100:
            stability['current_ratio_grade'] = "보통"
        else:
            stability['current_ratio_grade'] = "우려"
        
        # 종합 평가
        grades = [stability['debt_ratio_grade'], stability['equity_ratio_grade'], stability['current_ratio_grade']]
        if grades.count("우수") >= 2:
            stability['overall_grade'] = "우수"
        elif grades.count("우수") >= 1 or grades.count("양호") >= 2:
            stability['overall_grade'] = "양호"
        elif grades.count("우려") <= 1:
            stability['overall_grade'] = "보통"
        else:
            stability['overall_grade'] = "우려"
        
        return stability
    
    def get_multiple_balance_sheets(self, symbols: List[str], period_type: str = "0") -> Dict[str, List[Dict[str, Any]]]:
        """여러 종목의 대차대조표를 조회합니다."""
        results = {}
        
        for symbol in symbols:
            logger.info(f"🔍 {symbol} 대차대조표 조회 중...")
            balance_sheet = self.get_balance_sheet(symbol, period_type)
            if balance_sheet:
                results[symbol] = balance_sheet
            else:
                logger.warning(f"⚠️ {symbol} 대차대조표 조회 실패")
        
        return results
    
    def compare_balance_sheets(self, balance_sheet_data: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
        """여러 종목의 대차대조표를 비교합니다."""
        comparison_data = []
        
        for symbol, data_list in balance_sheet_data.items():
            if data_list:
                latest = data_list[0]  # 최신 데이터
                comparison_data.append({
                    'symbol': symbol,
                    'period': latest['period'],
                    'total_assets': latest['total_assets'],
                    'total_liabilities': latest['total_liabilities'],
                    'total_equity': latest['total_equity'],
                    'debt_ratio': latest['debt_ratio'],
                    'equity_ratio': latest['equity_ratio'],
                    'current_ratio': latest['current_ratio']
                })
        
        return pd.DataFrame(comparison_data)

def main():
    """테스트 함수"""
    from kis_data_provider import KISDataProvider
    
    provider = KISDataProvider()
    analyzer = BalanceSheetAnalyzer(provider)
    
    # 삼성전자 대차대조표 조회 테스트
    samsung_bs = analyzer.get_balance_sheet("005930")
    if samsung_bs:
        print("📊 삼성전자 대차대조표 (최신 3개 기간):")
        for i, data in enumerate(samsung_bs[:3]):
            print(f"\n📅 {data['period']} 기간:")
            print(f"  자산총계: {data['total_assets']:,.0f}원")
            print(f"  부채총계: {data['total_liabilities']:,.0f}원")
            print(f"  자본총계: {data['total_equity']:,.0f}원")
            print(f"  부채비율: {data['debt_ratio']:.1f}%")
            print(f"  자기자본비율: {data['equity_ratio']:.1f}%")
            print(f"  유동비율: {data['current_ratio']:.1f}%")
        
        # 추세 분석
        trend_analysis = analyzer.analyze_balance_sheet_trend(samsung_bs)
        print(f"\n📈 재무 추세 분석:")
        print(f"  자산 변화: {trend_analysis['assets_trend']['total_assets_change']:+.1f}%")
        print(f"  부채 변화: {trend_analysis['liabilities_trend']['total_liabilities_change']:+.1f}%")
        print(f"  자본 변화: {trend_analysis['equity_trend']['total_equity_change']:+.1f}%")
        print(f"  재무안정성: {trend_analysis['financial_stability']['overall_grade']}")
    else:
        print("❌ 삼성전자 대차대조표 조회 실패")

if __name__ == "__main__":
    main()
