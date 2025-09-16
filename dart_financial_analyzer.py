#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART API를 활용한 재무 분석 모듈
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class DARTFinancialAnalyzer:
    """DART API를 활용한 재무 분석 클래스"""
    
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
    
    def get_financial_data(self, corp_code: str, year: int = None, report_code: str = "11011") -> Optional[Dict[str, Any]]:
        """
        DART API를 통해 재무 데이터를 조회합니다.
        
        Args:
            corp_code: 기업 고유번호 (8자리)
            year: 사업연도 (기본값: 현재년도)
            report_code: 보고서 코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서)
        
        Returns:
            재무 데이터 딕셔너리
        """
        if year is None:
            year = datetime.now().year
        
        self._rate_limit()
        
        url = f"{self.base_url}/fnlttSinglAcnt.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": report_code
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != '000':
                logger.warning(f"⚠️ DART API 오류 ({corp_code}): {data.get('message', '알 수 없는 오류')}")
                return None
            
            return self._parse_financial_data(data.get('list', []))
            
        except requests.RequestException as e:
            logger.error(f"❌ DART API 호출 실패 ({corp_code}): {e}")
            return None
    
    def _parse_financial_data(self, data_list: List[Dict]) -> Dict[str, Any]:
        """DART API 응답 데이터를 파싱하여 재무 비율을 계산합니다."""
        if not data_list:
            return {}
        
        # 연결재무제표 데이터만 사용 (CFS)
        cfs_data = [item for item in data_list if item.get('fs_div') == 'CFS']
        
        if not cfs_data:
            logger.warning("⚠️ 연결재무제표 데이터가 없습니다.")
            return {}
        
        # 재무상태표 데이터
        bs_data = {item['account_nm']: item for item in cfs_data if item.get('sj_div') == 'BS'}
        # 손익계산서 데이터
        is_data = {item['account_nm']: item for item in cfs_data if item.get('sj_div') == 'IS'}
        
        # 주요 재무 데이터 추출
        financial_data = {}
        
        # 자산총계
        if '자산총계' in bs_data:
            financial_data['total_assets'] = self._to_float(bs_data['자산총계']['thstrm_amount'])
            financial_data['total_assets_prev'] = self._to_float(bs_data['자산총계']['frmtrm_amount'])
        
        # 부채총계
        if '부채총계' in bs_data:
            financial_data['total_liabilities'] = self._to_float(bs_data['부채총계']['thstrm_amount'])
            financial_data['total_liabilities_prev'] = self._to_float(bs_data['부채총계']['frmtrm_amount'])
        
        # 자본총계
        if '자본총계' in bs_data:
            financial_data['total_equity'] = self._to_float(bs_data['자본총계']['thstrm_amount'])
            financial_data['total_equity_prev'] = self._to_float(bs_data['자본총계']['frmtrm_amount'])
        
        # 매출액
        if '매출액' in is_data:
            financial_data['revenue'] = self._to_float(is_data['매출액']['thstrm_amount'])
            financial_data['revenue_prev'] = self._to_float(is_data['매출액']['frmtrm_amount'])
        
        # 영업이익
        if '영업이익' in is_data:
            financial_data['operating_income'] = self._to_float(is_data['영업이익']['thstrm_amount'])
            financial_data['operating_income_prev'] = self._to_float(is_data['영업이익']['frmtrm_amount'])
        
        # 당기순이익
        if '당기순이익' in is_data:
            financial_data['net_income'] = self._to_float(is_data['당기순이익']['thstrm_amount'])
            financial_data['net_income_prev'] = self._to_float(is_data['당기순이익']['frmtrm_amount'])
        
        # 재무 비율 계산
        financial_ratios = self._calculate_financial_ratios(financial_data)
        
        return {**financial_data, **financial_ratios}
    
    def _calculate_financial_ratios(self, data: Dict[str, float]) -> Dict[str, float]:
        """재무 비율을 계산합니다."""
        ratios = {}
        
        # ROE (자기자본이익률) = 당기순이익 / 평균자본총계 * 100
        if data.get('net_income') and data.get('total_equity'):
            avg_equity = (data['total_equity'] + data.get('total_equity_prev', data['total_equity'])) / 2
            if avg_equity > 0:
                ratios['roe'] = (data['net_income'] / avg_equity) * 100
        
        # 부채비율 = 부채총계 / 자본총계 * 100
        if data.get('total_liabilities') and data.get('total_equity'):
            if data['total_equity'] > 0:
                ratios['debt_ratio'] = (data['total_liabilities'] / data['total_equity']) * 100
        
        # 영업이익률 = 영업이익 / 매출액 * 100
        if data.get('operating_income') and data.get('revenue'):
            if data['revenue'] > 0:
                ratios['operating_margin'] = (data['operating_income'] / data['revenue']) * 100
        
        # 순이익률 = 당기순이익 / 매출액 * 100
        if data.get('net_income') and data.get('revenue'):
            if data['revenue'] > 0:
                ratios['net_margin'] = (data['net_income'] / data['revenue']) * 100
        
        # 자산회전율 = 매출액 / 평균자산총계
        if data.get('revenue') and data.get('total_assets'):
            avg_assets = (data['total_assets'] + data.get('total_assets_prev', data['total_assets'])) / 2
            if avg_assets > 0:
                ratios['asset_turnover'] = data['revenue'] / avg_assets
        
        # ROA (총자산이익률) = 당기순이익 / 평균자산총계 * 100
        if data.get('net_income') and data.get('total_assets'):
            avg_assets = (data['total_assets'] + data.get('total_assets_prev', data['total_assets'])) / 2
            if avg_assets > 0:
                ratios['roa'] = (data['net_income'] / avg_assets) * 100
        
        # 매출증가율 = (당기매출액 - 전기매출액) / 전기매출액 * 100
        if data.get('revenue') and data.get('revenue_prev'):
            if data['revenue_prev'] > 0:
                ratios['revenue_growth'] = ((data['revenue'] - data['revenue_prev']) / data['revenue_prev']) * 100
        
        # 순이익증가율 = (당기순이익 - 전기순이익) / 전기순이익 * 100
        if data.get('net_income') and data.get('net_income_prev'):
            if data['net_income_prev'] > 0:
                ratios['net_income_growth'] = ((data['net_income'] - data['net_income_prev']) / data['net_income_prev']) * 100
        
        return ratios
    
    def get_multiple_companies_data(self, corp_codes: List[str], year: int = None, report_code: str = "11011") -> Dict[str, Dict[str, Any]]:
        """여러 기업의 재무 데이터를 일괄 조회합니다."""
        results = {}
        
        for corp_code in corp_codes:
            logger.info(f"🔍 재무 데이터 조회 중: {corp_code}")
            data = self.get_financial_data(corp_code, year, report_code)
            if data:
                results[corp_code] = data
            else:
                logger.warning(f"⚠️ {corp_code} 재무 데이터 조회 실패")
        
        return results

def main():
    """테스트 함수"""
    # DART API 키 (실제 사용시 config.yaml에서 로드)
    api_key = "881d7d29ca6d553ce02e78d22a1129c15a62ac47"
    
    analyzer = DARTFinancialAnalyzer(api_key)
    
    # 삼성전자 재무 데이터 조회 테스트
    corp_code = "00126380"  # 삼성전자 고유번호
    data = analyzer.get_financial_data(corp_code, 2023)
    
    if data:
        print("📊 삼성전자 재무 데이터:")
        for key, value in data.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    else:
        print("❌ 재무 데이터 조회 실패")

if __name__ == "__main__":
    main()
