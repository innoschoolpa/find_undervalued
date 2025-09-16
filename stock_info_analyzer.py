#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주식 기본 정보 조회 모듈
KIS API 주식기본조회 API를 활용한 종목 상세 정보 분석
"""

import requests
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class StockInfoAnalyzer:
    """주식 기본 정보 분석 클래스"""
    
    def __init__(self, provider):
        self.provider = provider
        self.last_request_time = 0
        self.request_interval = 0.1  # API 요청 간격 제어
        
        # 시장 코드 매핑
        self.market_codes = {
            "STK": "유가증권",
            "KSQ": "코스닥", 
            "ETF": "ETF파생",
            "KNX": "코넥스"
        }
        
        # 증권 그룹 코드 매핑
        self.security_groups = {
            "ST": "주권",
            "EF": "ETF",
            "EN": "ETN",
            "EW": "ELW",
            "DR": "주식예탁증서",
            "BC": "수익증권",
            "MF": "투자회사",
            "RT": "부동산투자회사",
            "SC": "선박투자회사",
            "IF": "사회간접자본투융자회사",
            "IC": "투자계약증권",
            "TC": "신탁수익증권",
            "SR": "신주인수권증서",
            "SW": "신주인수권증권"
        }
        
        # 주식 종류 코드 매핑
        self.stock_types = {
            "000": "해당사항없음",
            "101": "보통주",
            "201": "우선주",
            "202": "2우선주",
            "203": "3우선주",
            "204": "4우선주",
            "205": "5우선주",
            "206": "6우선주",
            "207": "7우선주",
            "208": "8우선주",
            "209": "9우선주",
            "210": "10우선주",
            "211": "11우선주",
            "212": "12우선주",
            "213": "13우선주",
            "214": "14우선주",
            "215": "15우선주",
            "216": "16우선주",
            "217": "17우선주",
            "218": "18우선주",
            "219": "19우선주",
            "220": "20우선주",
            "301": "후배주",
            "401": "혼합주"
        }
    
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
    
    def _to_int(self, value: Any, default: int = 0) -> int:
        """안전하게 int 타입으로 변환합니다."""
        if value is None or value == '':
            return default
        try:
            # 쉼표 제거 후 int 변환
            return int(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return default
    
    def get_stock_basic_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        종목의 기본 정보를 조회합니다.
        
        Args:
            symbol: 종목코드 (6자리)
        
        Returns:
            종목 기본 정보 딕셔너리
        """
        self._rate_limit()
        
        path = "/uapi/domestic-stock/v1/quotations/search-stock-info"
        params = {
            "PRDT_TYPE_CD": "300",  # 주식, ETF, ETN, ELW
            "PDNO": symbol
        }
        
        try:
            data = self.provider._send_request(path, "CTPF1002R", params)
            if data and 'output' in data:
                return self._parse_basic_info(data['output'])
            else:
                logger.warning(f"⚠️ 종목 기본 정보 조회 실패: {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 종목 기본 정보 API 호출 실패 ({symbol}): {e}")
            return None
    
    def _parse_basic_info(self, output: Dict) -> Dict[str, Any]:
        """종목 기본 정보 응답 데이터를 파싱합니다."""
        parsed_data = {}
        
        # 기본 정보
        parsed_data['symbol'] = output.get('pdno', '')
        parsed_data['product_name'] = output.get('prdt_name', '')
        parsed_data['product_name_eng'] = output.get('prdt_eng_name', '')
        parsed_data['product_abrv_name'] = output.get('prdt_abrv_name', '')
        
        # 시장 정보
        parsed_data['market_id'] = output.get('mket_id_cd', '')
        parsed_data['market_name'] = self.market_codes.get(parsed_data['market_id'], parsed_data['market_id'])
        parsed_data['security_group_id'] = output.get('scty_grp_id_cd', '')
        parsed_data['security_group_name'] = self.security_groups.get(parsed_data['security_group_id'], parsed_data['security_group_id'])
        parsed_data['exchange_code'] = output.get('excg_dvsn_cd', '')
        
        # 주식 정보
        parsed_data['stock_type_code'] = output.get('stck_kind_cd', '')
        parsed_data['stock_type_name'] = self.stock_types.get(parsed_data['stock_type_code'], parsed_data['stock_type_code'])
        parsed_data['face_value'] = self._to_float(output.get('papr', 0))
        parsed_data['issue_price'] = self._to_float(output.get('issu_pric', 0))
        parsed_data['settlement_date'] = output.get('setl_mmdd', '')
        
        # 상장 정보
        parsed_data['listed_shares'] = self._to_int(output.get('lstg_stqt', 0))
        parsed_data['listed_capital'] = self._to_float(output.get('lstg_cptl_amt', 0))
        parsed_data['capital'] = self._to_float(output.get('cpta', 0))
        parsed_data['kospi200_item'] = output.get('kospi200_item_yn', 'N') == 'Y'
        
        # 상장 일자
        parsed_data['kospi_listing_date'] = output.get('scts_mket_lstg_dt', '')
        parsed_data['kospi_delisting_date'] = output.get('scts_mket_lstg_abol_dt', '')
        parsed_data['kosdaq_listing_date'] = output.get('kosdaq_mket_lstg_dt', '')
        parsed_data['kosdaq_delisting_date'] = output.get('kosdaq_mket_lstg_abol_dt', '')
        parsed_data['freeboard_listing_date'] = output.get('frbd_mket_lstg_dt', '')
        parsed_data['freeboard_delisting_date'] = output.get('frbd_mket_lstg_abol_dt', '')
        
        # 업종 분류
        parsed_data['industry_large_code'] = output.get('idx_bztp_lcls_cd', '')
        parsed_data['industry_large_name'] = output.get('idx_bztp_lcls_cd_name', '')
        parsed_data['industry_medium_code'] = output.get('idx_bztp_mcls_cd', '')
        parsed_data['industry_medium_name'] = output.get('idx_bztp_mcls_cd_name', '')
        parsed_data['industry_small_code'] = output.get('idx_bztp_scls_cd', '')
        parsed_data['industry_small_name'] = output.get('idx_bztp_scls_cd_name', '')
        parsed_data['standard_industry_code'] = output.get('std_idst_clsf_cd', '')
        parsed_data['standard_industry_name'] = output.get('std_idst_clsf_cd_name', '')
        
        # 거래 상태
        parsed_data['trading_stop'] = output.get('tr_stop_yn', 'N') == 'Y'
        parsed_data['admin_item'] = output.get('admn_item_yn', 'N') == 'Y'
        parsed_data['current_price'] = self._to_float(output.get('thdt_clpr', 0))
        parsed_data['prev_price'] = self._to_float(output.get('bfdy_clpr', 0))
        parsed_data['price_change_date'] = output.get('clpr_chng_dt', '')
        
        # ETF/ETN 정보
        parsed_data['etf_division_code'] = output.get('etf_dvsn_cd', '')
        parsed_data['etf_type_code'] = output.get('etf_type_cd', '')
        parsed_data['etf_cu_quantity'] = self._to_int(output.get('etf_cu_qty', 0))
        parsed_data['etf_tracking_rate'] = self._to_float(output.get('etf_chas_erng_rt_dbnb', 0))
        parsed_data['etf_etn_investment_warning'] = output.get('etf_etn_ivst_heed_item_yn', 'N') == 'Y'
        
        # 기타 정보
        parsed_data['substitute_price'] = self._to_float(output.get('sbst_pric', 0))
        parsed_data['company_substitute_price'] = self._to_float(output.get('thco_sbst_pric', 0))
        parsed_data['foreign_personal_limit_rate'] = self._to_float(output.get('frnr_psnl_lmt_rt', 0))
        parsed_data['electronic_security'] = output.get('elec_scty_yn', 'N') == 'Y'
        parsed_data['crowdfunding_item'] = output.get('crfd_item_yn', 'N') == 'Y'
        parsed_data['nxt_trading_possible'] = output.get('cptt_trad_tr_psbl_yn', 'N') == 'Y'
        parsed_data['nxt_trading_stop'] = output.get('nxt_tr_stop_yn', 'N') == 'Y'
        
        # 계산된 지표
        parsed_data['market_cap'] = parsed_data['current_price'] * parsed_data['listed_shares']
        parsed_data['price_to_face_ratio'] = parsed_data['current_price'] / parsed_data['face_value'] if parsed_data['face_value'] > 0 else 0
        parsed_data['price_to_issue_ratio'] = parsed_data['current_price'] / parsed_data['issue_price'] if parsed_data['issue_price'] > 0 else 0
        
        # 상장 상태 분석
        parsed_data['listing_status'] = self._analyze_listing_status(parsed_data)
        parsed_data['investment_grade'] = self._analyze_investment_grade(parsed_data)
        
        return parsed_data
    
    def _analyze_listing_status(self, data: Dict) -> str:
        """상장 상태를 분석합니다."""
        if data['trading_stop']:
            return "거래정지"
        elif data['admin_item']:
            return "관리종목"
        elif data['kospi200_item']:
            return "코스피200"
        elif data['market_id'] == 'STK':
            return "코스피"
        elif data['market_id'] == 'KSQ':
            return "코스닥"
        elif data['market_id'] == 'KNX':
            return "코넥스"
        else:
            return "기타"
    
    def _analyze_investment_grade(self, data: Dict) -> str:
        """투자 등급을 분석합니다."""
        score = 0
        
        # 시장 등급
        if data['market_id'] == 'STK':
            score += 30  # 코스피
        elif data['market_id'] == 'KSQ':
            score += 20  # 코스닥
        elif data['market_id'] == 'KNX':
            score += 10  # 코넥스
        
        # 코스피200 여부
        if data['kospi200_item']:
            score += 20
        
        # 거래 상태
        if data['trading_stop']:
            score -= 50
        elif data['admin_item']:
            score -= 30
        
        # 시가총액 등급
        market_cap = data['market_cap']
        if market_cap >= 1_000_000_000_000:  # 1조원 이상
            score += 20
        elif market_cap >= 500_000_000_000:  # 5천억원 이상
            score += 15
        elif market_cap >= 100_000_000_000:  # 1천억원 이상
            score += 10
        elif market_cap >= 50_000_000_000:   # 5백억원 이상
            score += 5
        
        # 투자 등급 결정
        if score >= 60:
            return "A등급"
        elif score >= 40:
            return "B등급"
        elif score >= 20:
            return "C등급"
        else:
            return "D등급"
    
    def get_multiple_stock_info(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """여러 종목의 기본 정보를 조회합니다."""
        results = {}
        
        for symbol in symbols:
            logger.info(f"🔍 {symbol} 종목 기본 정보 조회 중...")
            info = self.get_stock_basic_info(symbol)
            if info:
                results[symbol] = info
            else:
                logger.warning(f"⚠️ {symbol} 종목 정보 조회 실패")
        
        return results
    
    def analyze_stock_characteristics(self, stock_info: Dict[str, Any]) -> Dict[str, Any]:
        """종목의 특성을 분석합니다."""
        analysis = {}
        
        # 시장 특성
        analysis['market_characteristics'] = {
            'market_type': stock_info['market_name'],
            'security_type': stock_info['security_group_name'],
            'stock_type': stock_info['stock_type_name'],
            'listing_status': stock_info['listing_status']
        }
        
        # 규모 특성
        market_cap = stock_info['market_cap']
        if market_cap >= 10_000_000_000_000:  # 10조원 이상
            analysis['size_category'] = "초대형주"
        elif market_cap >= 1_000_000_000_000:  # 1조원 이상
            analysis['size_category'] = "대형주"
        elif market_cap >= 100_000_000_000:   # 1천억원 이상
            analysis['size_category'] = "중형주"
        elif market_cap >= 10_000_000_000:    # 1백억원 이상
            analysis['size_category'] = "소형주"
        else:
            analysis['size_category'] = "초소형주"
        
        # 업종 특성
        analysis['industry_characteristics'] = {
            'large_category': stock_info['industry_large_name'],
            'medium_category': stock_info['industry_medium_name'],
            'small_category': stock_info['industry_small_name'],
            'standard_industry': stock_info['standard_industry_name']
        }
        
        # 투자 특성
        analysis['investment_characteristics'] = {
            'investment_grade': stock_info['investment_grade'],
            'kospi200_included': stock_info['kospi200_item'],
            'foreign_limit_rate': stock_info['foreign_personal_limit_rate'],
            'electronic_security': stock_info['electronic_security']
        }
        
        # 거래 특성
        analysis['trading_characteristics'] = {
            'trading_stop': stock_info['trading_stop'],
            'admin_item': stock_info['admin_item'],
            'nxt_trading': stock_info['nxt_trading_possible'],
            'crowdfunding': stock_info['crowdfunding_item']
        }
        
        return analysis

def main():
    """테스트 함수"""
    from kis_data_provider import KISDataProvider
    
    provider = KISDataProvider()
    analyzer = StockInfoAnalyzer(provider)
    
    # 삼성전자 기본 정보 조회 테스트
    samsung_info = analyzer.get_stock_basic_info("005930")
    if samsung_info:
        print("📊 삼성전자 기본 정보:")
        print(f"  종목명: {samsung_info['product_name']}")
        print(f"  시장: {samsung_info['market_name']}")
        print(f"  주식종류: {samsung_info['stock_type_name']}")
        print(f"  상장주수: {samsung_info['listed_shares']:,}주")
        print(f"  시가총액: {samsung_info['market_cap']:,.0f}원")
        print(f"  액면가: {samsung_info['face_value']:,.0f}원")
        print(f"  업종: {samsung_info['industry_large_name']}")
        print(f"  상장상태: {samsung_info['listing_status']}")
        print(f"  투자등급: {samsung_info['investment_grade']}")
        
        # 특성 분석
        characteristics = analyzer.analyze_stock_characteristics(samsung_info)
        print(f"\n🔍 종목 특성 분석:")
        print(f"  규모: {characteristics['size_category']}")
        print(f"  시장특성: {characteristics['market_characteristics']}")
        print(f"  업종특성: {characteristics['industry_characteristics']}")
    else:
        print("❌ 삼성전자 기본 정보 조회 실패")

if __name__ == "__main__":
    main()
