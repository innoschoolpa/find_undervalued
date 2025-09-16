#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART API 전체 재무제표 분석 모듈
단일회사 전체 재무제표 API를 활용한 포괄적 재무 분석
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class DARTComprehensiveAnalyzer:
    """DART API 전체 재무제표 분석 클래스"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://opendart.fss.or.kr/api"
        self.session = requests.Session()
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
    
    def get_comprehensive_financial_data(self, corp_code: str, year: int = None, 
                                       report_code: str = "11011", fs_div: str = "CFS") -> Optional[Dict[str, Any]]:
        """
        DART API를 통해 전체 재무제표 데이터를 조회합니다.
        
        Args:
            corp_code: 기업 고유번호 (8자리)
            year: 사업연도 (기본값: 현재년도)
            report_code: 보고서 코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서)
            fs_div: 개별/연결구분 (OFS: 재무제표, CFS: 연결재무제표)
        
        Returns:
            포괄적 재무 데이터 딕셔너리
        """
        if year is None:
            year = datetime.now().year
        
        self._rate_limit()
        
        url = f"{self.base_url}/fnlttSinglAcntAll.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": report_code,
            "fs_div": fs_div
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != '000':
                logger.warning(f"⚠️ DART API 오류 ({corp_code}): {data.get('message', '알 수 없는 오류')}")
                return None
            
            return self._parse_comprehensive_financial_data(data.get('list', []))
            
        except requests.RequestException as e:
            logger.error(f"❌ DART API 호출 실패 ({corp_code}): {e}")
            return None
    
    def _parse_comprehensive_financial_data(self, data_list: List[Dict]) -> Dict[str, Any]:
        """DART API 전체 재무제표 응답 데이터를 파싱하여 포괄적 재무 분석을 수행합니다."""
        if not data_list:
            return {}
        
        # 재무제표별로 데이터 분류
        bs_data = {}  # 재무상태표 (Balance Sheet)
        is_data = {}  # 손익계산서 (Income Statement)
        cf_data = {}  # 현금흐름표 (Cash Flow)
        cis_data = {} # 포괄손익계산서 (Comprehensive Income Statement)
        sce_data = {} # 자본변동표 (Statement of Changes in Equity)
        
        for item in data_list:
            sj_div = item.get('sj_div', '')
            account_nm = item.get('account_nm', '')
            
            if sj_div == 'BS':
                bs_data[account_nm] = item
            elif sj_div == 'IS':
                is_data[account_nm] = item
            elif sj_div == 'CF':
                cf_data[account_nm] = item
            elif sj_div == 'CIS':
                cis_data[account_nm] = item
            elif sj_div == 'SCE':
                sce_data[account_nm] = item
        
        
        # 포괄적 재무 분석 수행
        financial_analysis = self._perform_comprehensive_analysis(bs_data, is_data, cf_data, cis_data, sce_data)
        
        return financial_analysis
    
    def _perform_comprehensive_analysis(self, bs_data: Dict, is_data: Dict, cf_data: Dict, 
                                      cis_data: Dict, sce_data: Dict) -> Dict[str, Any]:
        """포괄적 재무 분석을 수행합니다."""
        analysis = {}
        
        # 1. 재무상태표 분석
        bs_analysis = self._analyze_balance_sheet(bs_data)
        analysis.update(bs_analysis)
        
        # 2. 손익계산서 분석
        is_analysis = self._analyze_income_statement(is_data)
        analysis.update(is_analysis)
        
        # 3. 현금흐름표 분석
        cf_analysis = self._analyze_cash_flow(cf_data)
        analysis.update(cf_analysis)
        
        # 4. 포괄손익계산서 분석
        cis_analysis = self._analyze_comprehensive_income(cis_data)
        analysis.update(cis_analysis)
        
        # 5. 자본변동표 분석
        sce_analysis = self._analyze_equity_changes(sce_data)
        analysis.update(sce_analysis)
        
        # 6. 종합 재무 비율 계산
        comprehensive_ratios = self._calculate_comprehensive_ratios(analysis)
        analysis.update(comprehensive_ratios)
        
        return analysis
    
    def _analyze_balance_sheet(self, bs_data: Dict) -> Dict[str, Any]:
        """재무상태표 분석"""
        analysis = {}
        
        # 자산 분석
        analysis['total_assets'] = self._to_float(bs_data.get('자산총계', {}).get('thstrm_amount', 0))
        analysis['total_assets_prev'] = self._to_float(bs_data.get('자산총계', {}).get('frmtrm_amount', 0))
        analysis['current_assets'] = self._to_float(bs_data.get('유동자산', {}).get('thstrm_amount', 0))
        analysis['non_current_assets'] = self._to_float(bs_data.get('비유동자산', {}).get('thstrm_amount', 0))
        
        # 부채 분석
        analysis['total_liabilities'] = self._to_float(bs_data.get('부채총계', {}).get('thstrm_amount', 0))
        analysis['total_liabilities_prev'] = self._to_float(bs_data.get('부채총계', {}).get('frmtrm_amount', 0))
        analysis['current_liabilities'] = self._to_float(bs_data.get('유동부채', {}).get('thstrm_amount', 0))
        analysis['non_current_liabilities'] = self._to_float(bs_data.get('비유동부채', {}).get('thstrm_amount', 0))
        
        # 자본 분석
        analysis['total_equity'] = self._to_float(bs_data.get('자본총계', {}).get('thstrm_amount', 0))
        analysis['total_equity_prev'] = self._to_float(bs_data.get('자본총계', {}).get('frmtrm_amount', 0))
        analysis['capital_stock'] = self._to_float(bs_data.get('자본금', {}).get('thstrm_amount', 0))
        analysis['retained_earnings'] = self._to_float(bs_data.get('이익잉여금', {}).get('thstrm_amount', 0))
        
        # 현금 및 현금성자산
        analysis['cash_and_equivalents'] = self._to_float(bs_data.get('현금및현금성자산', {}).get('thstrm_amount', 0))
        
        return analysis
    
    def _analyze_income_statement(self, is_data: Dict) -> Dict[str, Any]:
        """손익계산서 분석"""
        analysis = {}
        
        # 매출 및 수익 분석
        analysis['revenue'] = self._to_float(is_data.get('영업수익', {}).get('thstrm_amount', 0))
        analysis['revenue_prev'] = self._to_float(is_data.get('영업수익', {}).get('frmtrm_amount', 0))
        analysis['cost_of_sales'] = self._to_float(is_data.get('매출원가', {}).get('thstrm_amount', 0))
        analysis['gross_profit'] = self._to_float(is_data.get('매출총이익', {}).get('thstrm_amount', 0))
        
        # 비용 분석
        analysis['sga_expenses'] = self._to_float(is_data.get('판매비와관리비', {}).get('thstrm_amount', 0))
        
        # 이익 분석
        analysis['operating_income'] = self._to_float(is_data.get('영업이익', {}).get('thstrm_amount', 0))
        analysis['operating_income_prev'] = self._to_float(is_data.get('영업이익', {}).get('frmtrm_amount', 0))
        analysis['other_income'] = self._to_float(is_data.get('기타수익', {}).get('thstrm_amount', 0))
        analysis['other_expenses'] = self._to_float(is_data.get('기타비용', {}).get('thstrm_amount', 0))
        analysis['financial_income'] = self._to_float(is_data.get('금융수익', {}).get('thstrm_amount', 0))
        analysis['financial_costs'] = self._to_float(is_data.get('금융비용', {}).get('thstrm_amount', 0))
        
        # 세전/세후 이익
        analysis['profit_before_tax'] = self._to_float(is_data.get('법인세비용차감전순이익(손실)', {}).get('thstrm_amount', 0))
        analysis['income_tax_expense'] = self._to_float(is_data.get('법인세비용', {}).get('thstrm_amount', 0))
        # 당기순이익
        net_income_data = is_data.get('당기순이익', {})
        analysis['net_income'] = self._to_float(net_income_data.get('thstrm_amount', 0))
        analysis['net_income_prev'] = self._to_float(net_income_data.get('frmtrm_amount', 0))
        
        # 주당이익
        analysis['basic_eps'] = self._to_float(is_data.get('기본주당이익(손실)', {}).get('thstrm_amount', 0))
        analysis['diluted_eps'] = self._to_float(is_data.get('희석주당이익(손실)', {}).get('thstrm_amount', 0))
        
        return analysis
    
    def _analyze_cash_flow(self, cf_data: Dict) -> Dict[str, Any]:
        """현금흐름표 분석"""
        analysis = {}
        
        # 영업활동 현금흐름
        analysis['operating_cash_flow'] = self._to_float(cf_data.get('영업활동 현금흐름', {}).get('thstrm_amount', 0))
        analysis['operating_cash_flow_prev'] = self._to_float(cf_data.get('영업활동 현금흐름', {}).get('frmtrm_amount', 0))
        
        # 투자활동 현금흐름
        analysis['investing_cash_flow'] = self._to_float(cf_data.get('투자활동 현금흐름', {}).get('thstrm_amount', 0))
        analysis['investing_cash_flow_prev'] = self._to_float(cf_data.get('투자활동 현금흐름', {}).get('frmtrm_amount', 0))
        
        # 재무활동 현금흐름
        analysis['financing_cash_flow'] = self._to_float(cf_data.get('재무활동 현금흐름', {}).get('thstrm_amount', 0))
        analysis['financing_cash_flow_prev'] = self._to_float(cf_data.get('재무활동 현금흐름', {}).get('frmtrm_amount', 0))
        
        # 현금 증가/감소
        analysis['cash_increase'] = self._to_float(cf_data.get('현금 및 현금성자산의 증가(감소)', {}).get('thstrm_amount', 0))
        analysis['cash_beginning'] = self._to_float(cf_data.get('기초 현금 및 현금성자산', {}).get('thstrm_amount', 0))
        analysis['cash_ending'] = self._to_float(cf_data.get('기말 현금 및 현금성자산', {}).get('thstrm_amount', 0))
        
        return analysis
    
    def _analyze_comprehensive_income(self, cis_data: Dict) -> Dict[str, Any]:
        """포괄손익계산서 분석"""
        analysis = {}
        
        # 당기순이익
        analysis['net_income_cis'] = self._to_float(cis_data.get('당기순이익(손실)', {}).get('thstrm_amount', 0))
        
        # 기타포괄손익
        analysis['other_comprehensive_income'] = self._to_float(cis_data.get('기타포괄손익', {}).get('thstrm_amount', 0))
        
        # 총포괄손익
        analysis['total_comprehensive_income'] = self._to_float(cis_data.get('총포괄손익', {}).get('thstrm_amount', 0))
        
        return analysis
    
    def _analyze_equity_changes(self, sce_data: Dict) -> Dict[str, Any]:
        """자본변동표 분석"""
        analysis = {}
        
        # 기초/기말 자본
        analysis['equity_beginning'] = self._to_float(sce_data.get('기초자본', {}).get('thstrm_amount', 0))
        analysis['equity_ending'] = self._to_float(sce_data.get('기말자본', {}).get('thstrm_amount', 0))
        
        return analysis
    
    def _calculate_comprehensive_ratios(self, analysis: Dict) -> Dict[str, float]:
        """종합 재무 비율을 계산합니다."""
        ratios = {}
        
        # 수익성 비율
        if analysis.get('revenue', 0) > 0:
            ratios['gross_margin'] = (analysis.get('gross_profit', 0) / analysis['revenue']) * 100
            ratios['operating_margin'] = (analysis.get('operating_income', 0) / analysis['revenue']) * 100
            ratios['net_margin'] = (analysis.get('net_income', 0) / analysis['revenue']) * 100
        
        # ROE (자기자본이익률)
        avg_equity = (analysis.get('total_equity', 0) + analysis.get('total_equity_prev', 0)) / 2
        net_income = analysis.get('net_income', 0)
        if avg_equity > 0:
            ratios['roe'] = (net_income / avg_equity) * 100
        
        # ROA (총자산이익률)
        avg_assets = (analysis.get('total_assets', 0) + analysis.get('total_assets_prev', 0)) / 2
        if avg_assets > 0:
            ratios['roa'] = (analysis.get('net_income', 0) / avg_assets) * 100
        
        # 부채비율
        if analysis.get('total_equity', 0) > 0:
            ratios['debt_ratio'] = (analysis.get('total_liabilities', 0) / analysis['total_equity']) * 100
        
        # 유동비율
        if analysis.get('current_liabilities', 0) > 0:
            ratios['current_ratio'] = analysis.get('current_assets', 0) / analysis['current_liabilities']
        
        # 자산회전율
        if avg_assets > 0:
            ratios['asset_turnover'] = analysis.get('revenue', 0) / avg_assets
        
        # 성장률
        if analysis.get('revenue_prev', 0) > 0:
            ratios['revenue_growth'] = ((analysis.get('revenue', 0) - analysis['revenue_prev']) / analysis['revenue_prev']) * 100
        
        if analysis.get('net_income_prev', 0) > 0:
            ratios['net_income_growth'] = ((analysis.get('net_income', 0) - analysis['net_income_prev']) / analysis['net_income_prev']) * 100
        
        # 현금흐름 비율
        if analysis.get('operating_income', 0) > 0:
            ratios['cash_flow_quality'] = analysis.get('operating_cash_flow', 0) / analysis['operating_income']
        
        # 배당성향 (배당금 지급액이 있는 경우)
        if analysis.get('net_income', 0) > 0:
            # 배당금 지급액은 현금흐름표에서 가져와야 함
            ratios['payout_ratio'] = 0  # 추후 구현
        
        return ratios
    
    def get_multiple_companies_comprehensive_data(self, corp_codes: List[str], year: int = None, 
                                                report_code: str = "11011", fs_div: str = "CFS") -> Dict[str, Dict[str, Any]]:
        """여러 기업의 포괄적 재무 데이터를 일괄 조회합니다."""
        results = {}
        
        for corp_code in corp_codes:
            logger.info(f"🔍 포괄적 재무 데이터 조회 중: {corp_code}")
            data = self.get_comprehensive_financial_data(corp_code, year, report_code, fs_div)
            if data:
                results[corp_code] = data
            else:
                logger.warning(f"⚠️ {corp_code} 포괄적 재무 데이터 조회 실패")
        
        return results

def main():
    """테스트 함수"""
    # DART API 키
    api_key = "881d7d29ca6d553ce02e78d22a1129c15a62ac47"
    
    analyzer = DARTComprehensiveAnalyzer(api_key)
    
    # 삼성전자 포괄적 재무 데이터 조회 테스트
    corp_code = "00126380"  # 삼성전자 고유번호
    data = analyzer.get_comprehensive_financial_data(corp_code, 2023)
    
    if data:
        print("📊 삼성전자 포괄적 재무 분석:")
        print(f"  자산총계: {data.get('total_assets', 0):,.0f}원")
        print(f"  부채총계: {data.get('total_liabilities', 0):,.0f}원")
        print(f"  자본총계: {data.get('total_equity', 0):,.0f}원")
        print(f"  매출액: {data.get('revenue', 0):,.0f}원")
        print(f"  영업이익: {data.get('operating_income', 0):,.0f}원")
        print(f"  당기순이익: {data.get('net_income', 0):,.0f}원")
        print(f"  ROE: {data.get('roe', 0):.2f}%")
        print(f"  ROA: {data.get('roa', 0):.2f}%")
        print(f"  부채비율: {data.get('debt_ratio', 0):.2f}%")
        print(f"  영업이익률: {data.get('operating_margin', 0):.2f}%")
        print(f"  순이익률: {data.get('net_margin', 0):.2f}%")
        print(f"  매출증가율: {data.get('revenue_growth', 0):.2f}%")
        print(f"  순이익증가율: {data.get('net_income_growth', 0):.2f}%")
    else:
        print("❌ 포괄적 재무 데이터 조회 실패")

if __name__ == "__main__":
    main()
