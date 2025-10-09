#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP KIS API 통합 모듈
실제 KIS API 호출을 MCP 스타일로 래핑
"""

import os
import re
import math
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional, List, Tuple
from collections import defaultdict, Counter

import requests

logger = logging.getLogger(__name__)

class MCPKISIntegration:
    """MCP 스타일의 KIS API 통합 클래스 (KISDataProvider 방식 사용)"""
    
    def __init__(self, oauth_manager):
        self.oauth_manager = oauth_manager
        self.base_url = "https://openapi.koreainvestment.com:9443"
        
        # OAuth 매니저 호환성 처리 (appkey/app_key 모두 지원)
        appkey = getattr(oauth_manager, 'appkey', None) or getattr(oauth_manager, 'app_key', None)
        appsecret = getattr(oauth_manager, 'appsecret', None) or getattr(oauth_manager, 'app_secret', None)
        
        # 기존 KISDataProvider와 동일한 헤더 구성
        self.headers = {
            "content-type": "application/json; charset=utf-8",
            "appkey": appkey,
            "appsecret": appsecret,
        }
        
        # 기존 KISDataProvider와 동일한 세션 설정
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # 직접 재시도 로직 구현
        )
        self.session.mount('https://', adapter)
        
        # 세션 헤더 설정
        self.session.headers.update({
            'User-Agent': 'KIS-API-Client/1.0',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        # ✅ 멀티스레드 안전성을 위한 Lock
        self._lock = threading.Lock()
        self._cache_lock = threading.Lock()
        
        # Rate limiting 설정
        # KIS API 제한: 실전 20건/초, 모의 2건/초
        # 안전하게 실전 10건/초 (0.1초 간격) 사용
        self.last_request_time = 0
        self.request_interval = 0.1  # 0.1초 간격 (초당 10건)
        self.consecutive_500_errors = 0
        self.max_consecutive_500_errors = 5  # ✅ 최대 연속 500 오류 횟수
        
        # 캐시 설정 (엔드포인트별 차등 TTL)
        self.cache = {}
        self.cache_ttl = {
            'default': 60,       # 기본 1분
            'quotations': 10,    # 현재가 10초 (실시간성)
            'ranking': 300,      # 순위 5분 (자주 변하지 않음)
            'financial': 3600,   # 재무 1시간 (거의 변하지 않음)
            'dividend': 7200     # 배당 2시간 (거의 변하지 않음)
        }
    
    def _rate_limit(self):
        """API 요청 속도를 제어합니다 (멀티스레드 안전)"""
        with self._lock:  # ✅ Lock으로 보호
            elapsed_time = time.time() - self.last_request_time
            if elapsed_time < self.request_interval:
                time.sleep(self.request_interval - elapsed_time)
            self.last_request_time = time.time()
    
    def _send_request(self, path: str, tr_id: str, params: dict, max_retries: int = 2) -> Optional[dict]:
        """
        KISDataProvider와 동일한 방식의 API 요청 메서드
        중앙 집중화된 API GET 요청 (재시도 로직 포함)
        """
        # ✅ 연속 500 오류가 너무 많으면 세션 재생성
        if self.consecutive_500_errors >= self.max_consecutive_500_errors:
            logger.error(f"❌ 연속 500 오류 {self.consecutive_500_errors}회 초과 - 세션 재생성")
            time.sleep(10)  # 10초 대기
            
            # 세션 재생성
            try:
                self.session.close()
                self.session = requests.Session()
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=10,
                    pool_maxsize=20,
                    max_retries=0
                )
                self.session.mount('https://', adapter)
                self.session.headers.update({
                    'User-Agent': 'KIS-API-Client/1.0',
                    'Connection': 'keep-alive',
                    'Accept-Encoding': 'gzip, deflate'
                })
                logger.info("✅ 세션 재생성 완료")
            except Exception as e:
                logger.error(f"❌ 세션 재생성 실패: {e}")
            
            self.consecutive_500_errors = 0
            return None
        
        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()
                
                # OAuth 매니저 호환성 처리 (get_rest_token/get_valid_token 모두 지원)
                if hasattr(self.oauth_manager, 'get_rest_token'):
                    token = self.oauth_manager.get_rest_token()
                elif hasattr(self.oauth_manager, 'get_valid_token'):
                    token = self.oauth_manager.get_valid_token()
                else:
                    logger.error("OAuth 매니저에서 토큰 가져오기 메서드를 찾을 수 없습니다")
                    return None
                
                if not token:
                    logger.error("OAuth 토큰을 가져올 수 없습니다")
                    return None
                
                # 헤더 구성 (KISDataProvider와 동일)
                headers = {
                    **self.headers, 
                    "authorization": f"Bearer {token}", 
                    "tr_id": tr_id
                }
                
                url = f"{self.base_url}{path}"
                
                # 타임아웃 설정: 연결 10초, 읽기 30초
                response = self.session.get(
                    url, 
                    headers=headers, 
                    params=params, 
                    timeout=(10, 30)
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get('rt_cd') != '0':
                    logger.warning(f"⚠️ API 오류 ({tr_id}|{params.get('FID_INPUT_ISCD')}): {data.get('msg1', '알 수 없는 오류')}")
                    return None
                
                # ✅ 페이징 지원: tr_cont 헤더를 body에 추가
                tr_cont = response.headers.get('tr_cont', '')
                if tr_cont:
                    data['tr_cont'] = tr_cont
                
                # 성공적인 요청 시 500 오류 카운터 리셋
                self.consecutive_500_errors = 0
                return data
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 500:
                    self.consecutive_500_errors += 1
                    if attempt < max_retries:
                        backoff = 0.5 * (2 ** attempt) + (0.1 * attempt)
                        logger.warning(f"⚠️ 서버 내부 오류 (500) - {backoff:.1f}초 후 재시도 ({attempt + 1}/{max_retries}) ({tr_id}): {e}")
                        time.sleep(backoff)
                        continue
                    else:
                        logger.error(f"❌ API 500 오류 (최대 재시도 초과) ({tr_id}): {e}")
                        return None
                else:
                    logger.error(f"❌ API HTTP 오류 ({tr_id}): {e}")
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries:
                    backoff = 0.3 * (2 ** attempt)
                    logger.debug(f"🔄 연결 오류 재시도 중... ({attempt + 1}/{max_retries}, {backoff:.1f}초 대기): {e}")
                    time.sleep(backoff)
                    continue
                else:
                    logger.error(f"❌ API 연결 실패 ({tr_id}): {e}")
                    return None
                    
            except requests.exceptions.Timeout as e:
                if attempt < max_retries:
                    backoff = 0.3 * (2 ** attempt)
                    logger.debug(f"🔄 타임아웃 재시도 중... ({attempt + 1}/{max_retries}, {backoff:.1f}초 대기): {e}")
                    time.sleep(backoff)
                    continue
                else:
                    logger.error(f"❌ API 타임아웃 ({tr_id}): {e}")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ API 요청 중 예상치 못한 오류 ({tr_id}): {e}")
                return None
        
        return None
    
    def _make_api_call(self, endpoint: str, params: Dict = None, tr_id: str = "", use_cache: bool = True) -> Optional[Dict]:
        """
        API 호출 래퍼 (캐시 지원, 엔드포인트별 차등 TTL)
        실제 호출은 _send_request 사용
        """
        # ✅ 엔드포인트 검증: 절대경로가 들어오면 안 됨
        assert not endpoint.startswith("/"), f"엔드포인트는 상대경로여야 합니다: {endpoint}"
        
        if endpoint.startswith("uapi/"):
            logger.error(f"❌ 엔드포인트 오류: 'uapi/' 접두사 제거 필요: {endpoint}")
            # 자동 수정 시도
            endpoint = endpoint.replace("uapi/domestic-stock/v1/", "")
            logger.warning(f"⚠️ 자동 수정: {endpoint}")
        
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        
        # 캐시 TTL 결정 (엔드포인트 종류별)
        if 'quotations' in endpoint:
            ttl = self.cache_ttl['quotations']
        elif 'ranking' in endpoint:
            ttl = self.cache_ttl['ranking']
        elif 'financial' in endpoint or 'finance' in endpoint:
            ttl = self.cache_ttl['financial']
        elif 'dividend' in endpoint:
            ttl = self.cache_ttl['dividend']
        else:
            ttl = self.cache_ttl['default']
        
        # ✅ 캐시 확인 (Lock으로 보호)
        if use_cache:
            with self._cache_lock:
                if cache_key in self.cache:
                    cached_data, timestamp = self.cache[cache_key]
                    if time.time() - timestamp < ttl:
                        logger.debug(f"✓ 캐시 사용: {endpoint} (TTL={ttl}초)")
                        return cached_data
        
        # KISDataProvider의 _send_request 방식 사용
        path = f"/uapi/domestic-stock/v1/{endpoint}"
        data = self._send_request(path, tr_id, params or {})
        
        # ✅ 캐시 저장 (Lock으로 보호)
        if data and use_cache:
            with self._cache_lock:
                self.cache[cache_key] = (data, time.time())
                logger.debug(f"💾 캐시 저장: {endpoint} (TTL={ttl}초)")
        
        return data
    
    # === 국내주식 기본시세 ===
    
    def get_current_price(self, symbol: str, market_type: str = "J") -> Optional[Dict]:
        """
        주식현재가 시세 조회
        
        Args:
            symbol: 종목코드
            market_type: 시장구분 (J:KRX, NX:NXT, UN:통합) - 신규 추가!
        """
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-price",
                params={
                    "FID_COND_MRKT_DIV_CODE": market_type,  # NX, UN 추가 지원
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST01010100"  # 주식현재가 시세 TR_ID
            )
            return data.get('output') if data else None
        except Exception as e:
            logger.error(f"현재가 조회 실패: {symbol}, {e}")
            return None
    
    def get_asking_price(self, symbol: str) -> Optional[Dict]:
        """주식현재가 호가/예상체결 조회"""
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-asking-price-exp-ccn",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST01010200"  # 주식호가 TR_ID
            )
            return data.get('output') if data else None
        except Exception as e:
            logger.error(f"호가 조회 실패: {symbol}, {e}")
            return None
    
    def get_chart_data(self, symbol: str, period: str = "D", days: int = 365) -> Optional[List[Dict]]:
        """차트 데이터 조회 (일/주/월봉)"""
        try:
            period_map = {
                "D": "D",  # 일봉
                "W": "W",  # 주봉
                "M": "M"   # 월봉
            }
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            data = self._make_api_call(
                endpoint="quotations/inquire-daily-itemchartprice",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
                    "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
                    "FID_PERIOD_DIV_CODE": period_map.get(period, "D"),
                    "FID_ORG_ADJ_PRC": "0"  # 0:수정주가, 1:원주가
                },
                tr_id="FHKST03010100"  # 국내주식 기간별 시세 TR_ID
            )
            
            return data.get('output2') if data else None
            
        except Exception as e:
            logger.error(f"차트 데이터 조회 실패: {symbol}, {e}")
            return None
    
    # === 종목정보 ===
    
    def get_stock_basic_info(self, symbol: str) -> Optional[Dict]:
        """주식기본조회 (종목명, 업종 등)"""
        try:
            data = self._make_api_call(
                endpoint="quotations/search-info",
                params={
                    "PDNO": symbol,
                    "PRDT_TYPE_CD": "300"  # 주식
                },
                tr_id="CTPF1604R"  # 종목정보 조회 TR_ID
            )
            if data and 'output' in data:
                output = data['output']
                if isinstance(output, list) and len(output) > 0:
                    return output[0]
                elif isinstance(output, dict):
                    return output
            return None
        except Exception as e:
            logger.error(f"종목 기본 정보 조회 실패: {symbol}, {e}")
            return None
    
    def get_financial_ratios(self, symbol: str) -> Optional[Dict]:
        """국내주식 재무비율 조회 (PER, PBR, ROE 등)"""
        try:
            data = self._make_api_call(
                endpoint="finance/financial-ratio",
                params={
                    "FID_DIV_CLS_CODE": "0",  # 0:년, 1:분기
                    "fid_cond_mrkt_div_code": "J",
                    "fid_input_iscd": symbol
                },
                tr_id="FHKST66430300"  # 재무비율 TR_ID
            )
            
            if data and 'output' in data:
                output = data['output']
                if isinstance(output, list) and len(output) > 0:
                    return output[0]  # 최신 데이터
                elif isinstance(output, dict):
                    return output
            return None
        except Exception as e:
            logger.error(f"재무비율 조회 실패: {symbol}, {e}")
            return None
    
    def get_income_statement(self, symbol: str) -> Optional[Dict]:
        """국내주식 손익계산서 조회"""
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-income-statement",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST66430200"  # 손익계산서 TR_ID
            )
            if data and 'output' in data:
                return data['output']
            return None
        except Exception as e:
            logger.error(f"손익계산서 조회 실패: {symbol}, {e}")
            return None
    
    def get_balance_sheet(self, symbol: str) -> Optional[Dict]:
        """국내주식 대차대조표 조회"""
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-balance-sheet",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST66430100"  # 대차대조표 TR_ID
            )
            if data and 'output' in data:
                return data['output']
            return None
        except Exception as e:
            logger.error(f"대차대조표 조회 실패: {symbol}, {e}")
            return None
    
    def get_daily_prices(self, symbol: str) -> Optional[Dict]:
        """일자별 시세 조회 (✅ 함수명 수정: dividend_info → daily_prices)"""
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-daily-price",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_PERIOD_DIV_CODE": "D",
                    "FID_ORG_ADJ_PRC": "0"
                },
                tr_id="FHKST01010400"  # 일자별 시세 TR_ID
            )
            if data and 'output' in data:
                return data['output']
            return None
        except Exception as e:
            logger.error(f"일자별 시세 조회 실패: {symbol}, {e}")
            return None
    
    # === 시세분석 ===
    
    def get_investor_trend(self, symbol: str, market_type: str = "J") -> Optional[Dict]:
        """
        투자자별 매매동향 조회 (실시간)
        
        Args:
            symbol: 종목코드
            market_type: 시장구분 (J:KRX, NX:NXT, UN:통합) - 신규 추가!
        """
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-investor",
                params={
                    "FID_COND_MRKT_DIV_CODE": market_type,  # NX, UN 추가 지원
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": "",  # 당일
                    "FID_INPUT_DATE_2": "",
                    "FID_PERIOD_DIV_CODE": "D"  # D:일, W:주, M:월
                },
                tr_id="FHKST01010900"  # 투자자별 매매동향 TR_ID
            )
            if data and 'output' in data:
                return data['output']
            return None
        except Exception as e:
            logger.error(f"투자자 동향 조회 실패: {symbol}, {e}")
            return None
    
    def get_investor_trend_daily(self, symbol: str, start_date: str = "", end_date: str = "") -> Optional[List[Dict]]:
        """
        종목별 투자자매매동향(일별) 조회 - 신규 API!
        HTS [0416] 종목별 일별동향 화면 기능
        
        Args:
            symbol: 종목코드 (6자리)
            start_date: 조회 시작일자 (YYYYMMDD, 미입력시 최근 30일)
            end_date: 조회 종료일자 (YYYYMMDD, 미입력시 당일)
            
        Returns:
            일자별 투자자 매매동향 리스트
        """
        try:
            # 날짜 기본값 설정
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            
            data = self._make_api_call(
                endpoint="quotations/inquire-daily-investorprice",  # ✅ 상대 경로만!
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": start_date,
                    "FID_INPUT_DATE_2": end_date,
                    "FID_PERIOD_DIV_CODE": "D"  # D:일별
                },
                tr_id="FHKST03010200"  # 종목별 투자자매매동향(일별) TR_ID
            )
            if data and 'output' in data:
                return data['output']
            return None
        except Exception as e:
            logger.error(f"종목별 투자자매매동향(일별) 조회 실패: {symbol}, {e}")
            return None
    
    def get_program_trade(self, symbol: str) -> Optional[Dict]:
        """프로그램매매 현황 조회"""
        try:
            data = self._make_api_call(
                endpoint="quotations/program-trade-by-stock",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": "",  # 당일
                    "FID_INPUT_DATE_2": ""
                },
                tr_id="FHKST01010600"  # 프로그램매매 종목별 TR_ID
            )
            if data and 'output' in data:
                return data['output']
            return None
        except Exception as e:
            logger.error(f"프로그램매매 조회 실패: {symbol}, {e}")
            return None
    
    def get_credit_balance(self, symbol: str) -> Optional[Dict]:
        """신용잔고 현황 조회"""
        try:
            data = self._make_api_call(
                endpoint="quotations/credit-balance",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": ""  # 당일
                },
                tr_id="FHKST133500200"  # 신용잔고 TR_ID  
            )
            if data and 'output' in data:
                return data['output']
            return None
        except Exception as e:
            logger.error(f"신용잔고 조회 실패: {symbol}, {e}")
            return None
            
    # === 순위분석 ===
    
    def get_market_cap_ranking(self, limit: int = 100, market_type: str = "J") -> Optional[List[Dict]]:
        """
        시가총액 순위 조회 (정식 KIS API 사용)
        
        Args:
            limit: 조회할 최대 종목 수 (기본 100개, 실제로는 50~100개 수준 반환)
            market_type: 시장구분 (J:코스피, Q:코스닥, NX:NXT) - 신규 추가!
            
        Note:
            KIS API는 일정 수량(50~100개 수준)만 반환
            엔드포인트: /uapi/domestic-stock/v1/quotations/inquire-market-cap
        """
        # ✅ 정식 엔드포인트 및 필수 파라미터 (KIS 고객센터 확인)
        data = self._make_api_call(
            endpoint="quotations/inquire-market-cap",  # 정식 엔드포인트
            params={
                "FID_COND_MRKT_DIV_CODE": market_type,  # J:코스피, Q:코스닥, NX:NXT
                "FID_INPUT_ISCD": "0000",  # 조회 조건 코드
                "FID_PERIOD_DIV_CODE": "0",  # 정렬 기준 (0: 시가총액) ⭐ 필수!
                "FID_ORG_ADJ_PRC": "0"  # 수정주가 반영 여부 (0: 미반영) ⭐ 필수!
            },
            tr_id="FHPST01740000"  # 시가총액 순위 TR_ID
        )
        
        if data and 'output' in data:
            results = data['output']
            logger.info(f"✅ 시가총액 API 성공: {len(results)}개")
            return results[:limit]
        
        # API 실패 시 KOSPI 마스터 파일 사용
        logger.warning(f"⚠️ 시가총액 API 실패 (404), KOSPI 마스터 파일로 대체...")
        
        try:
            import pandas as pd
            from pathlib import Path
            
            kospi_file = Path("kospi_code.xlsx")
            if kospi_file.exists():
                df = pd.read_excel(kospi_file)
                
                # 시가총액으로 정렬
                if '시가총액' in df.columns:
                    df = df.sort_values('시가총액', ascending=False).head(limit)
                    
                    results = []
                    for _, row in df.iterrows():
                        code = row.get('단축코드')
                        if code and isinstance(code, str) and len(code) == 6:
                            if not (code.startswith('F') or code.startswith('Q')):
                                market_cap = row.get('시가총액', 0)
                                if market_cap and market_cap > 0:
                                    # 종목명에서 "보통주" 제거, "우선주"는 "우"로 축약
                                    name = row.get('한글명', '')
                                    name = name.replace('보통주', '')
                                    if '우선주' in name:
                                        name = name.replace('우선주', '우')
                                    name = name.strip()
                                    
                                    results.append({
                                        'mksc_shrn_iscd': code,
                                        'hts_kor_isnm': name,  # ✨ 정리된 종목명
                                        'hts_avls': market_cap / 100_000_000.0,  # ✅ 항상 억원 단위
                                        'stck_prpr': row.get('기준가', 0),
                                        'acml_vol': row.get('전일거래량', 0),
                                        'prdy_ctrt': 0
                                    })
                    
                    logger.info(f"✅ KOSPI 마스터에서 시가총액 상위 {len(results)}개 조회")
                    return results
        except Exception as fallback_error:
            logger.error(f"KOSPI 마스터 파일도 실패: {fallback_error}")
        
        return None
    
    def get_volume_ranking(self, limit: int = 30, market_type: str = "J") -> Optional[List[Dict]]:
        """
        거래량 순위 조회
        
        Args:
            limit: 조회할 최대 종목 수 (기본 30개, 실제로도 약 30개만 반환)
            market_type: 시장구분 (J:KRX, NX:NXT) - 신규 추가!
            
        Note:
            KIS API는 약 30개만 반환 (페이징 미지원)
            더 많은 종목이 필요하면 여러 API를 조합해야 함
        """
        try:
            data = self._make_api_call(
                endpoint="quotations/volume-rank",  # 올바른 엔드포인트
                params={
                    "FID_COND_MRKT_DIV_CODE": market_type,  # NX 추가 지원
                    "FID_COND_SCR_DIV_CODE": "20171",
                    "FID_INPUT_ISCD": "0000",
                    "FID_DIV_CLS_CODE": "0",
                    "FID_BLNG_CLS_CODE": "0",
                    "FID_TRGT_CLS_CODE": "111111111",
                    "FID_TRGT_EXLS_CLS_CODE": "0000000000",
                    "FID_INPUT_PRICE_1": "",
                    "FID_INPUT_PRICE_2": "",
                    "FID_VOL_CNT": "",
                    "FID_INPUT_DATE_1": ""
                },
                tr_id="FHPST01710000"
            )
            
            if data and 'output' in data:
                results = data['output']
                logger.info(f"✅ 거래량 순위 조회 완료: {len(results)}개")
                return results[:limit]
            return None
            
        except Exception as e:
            logger.error(f"거래량 순위 조회 실패: {e}")
            return None
    
    def get_per_ranking(self, limit: int = 100, market_type: str = "J") -> Optional[List[Dict]]:
        """
        재무비율(PER/PBR/ROE) 순위 조회
        
        Args:
            limit: 조회할 최대 종목 수 (기본 100개, 실제로는 50~100개 수준 반환)
            market_type: 시장구분 (J:KRX, NX:NXT) - 신규 추가!
            
        Note:
            KIS API는 일정 수량(50~100개 수준)만 반환 (페이징 미지원)
            더 많은 종목이 필요하면 여러 API를 조합해야 함
        """
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-financial-ratio",  # 올바른 엔드포인트
                params={
                    "FID_COND_MRKT_DIV_CODE": market_type,  # NX 추가 지원
                    "FID_COND_SCR_DIV_CODE": "20172",  # PER (재무비율)
                    "FID_INPUT_ISCD": "0000",
                    "FID_DIV_CLS_CODE": "0",  # 전체
                    "FID_INPUT_PRICE_1": "",
                    "FID_INPUT_PRICE_2": "",
                    "FID_VOL_CNT": "",
                    "FID_INPUT_DATE_1": ""
                },
                tr_id="FHPST01750000"  # 재무비율 순위 TR_ID
            )
            
            if data and 'output' in data:
                results = data['output']
                logger.info(f"✅ 재무비율 순위 조회 완료: {len(results)}개")
                return results[:limit]
            return None
                
        except Exception as e:
            logger.error(f"재무비율 순위 조회 실패: {e}")
            return None
    
    def get_updown_ranking(self, limit: int = 100, updown_type: str = "0", market_type: str = "J") -> Optional[List[Dict]]:
        """
        등락률 순위 조회 - 신규 API!
        
        Args:
            limit: 조회할 종목 수 (기본 100개, 실제로는 50~100개 수준 반환)
            updown_type: 0:상승률, 1:하락률, 2:보합
            market_type: 시장구분 (J:KRX, NX:NXT) - 신규 추가!
            
        Note:
            KIS API는 일정 수량(50~100개 수준)만 반환
        """
        try:
            data = self._make_api_call(
                endpoint="ranking/fluctuation",
                params={
                    "FID_COND_MRKT_DIV_CODE": market_type,  # NX 추가 지원
                    "FID_COND_SCR_DIV_CODE": "20170",  # 등락률
                    "FID_INPUT_ISCD": "0000",
                    "FID_DIV_CLS_CODE": updown_type,  # 0:상승, 1:하락, 2:보합
                    "FID_INPUT_PRICE_1": "",
                    "FID_INPUT_PRICE_2": "",
                    "FID_VOL_CNT": "",
                    "FID_INPUT_DATE_1": ""
                },
                tr_id="FHPST01700000"  # 등락률 순위 TR_ID
            )
            
            if data and 'output' in data:
                return data['output'][:limit]
            return None
                
        except Exception as e:
            logger.error(f"등락률 순위 조회 실패: {e}")
            return None
    
    def get_asking_price_ranking(self, limit: int = 100, market_type: str = "J") -> Optional[List[Dict]]:
        """
        호가잔량 순위 조회 - 신규 API!
        
        Args:
            limit: 조회할 종목 수 (기본 100개, 실제로는 50~100개 수준 반환)
            market_type: 시장구분 (J:KRX, NX:NXT) - 신규 추가!
            
        Note:
            KIS API는 일정 수량(50~100개 수준)만 반환
        """
        try:
            data = self._make_api_call(
                endpoint="ranking/asking-price-volume",
                params={
                    "FID_COND_MRKT_DIV_CODE": market_type,  # NX 추가 지원
                    "FID_COND_SCR_DIV_CODE": "20173",  # 호가잔량
                    "FID_INPUT_ISCD": "0000",
                    "FID_DIV_CLS_CODE": "0",  # 전체
                    "FID_INPUT_PRICE_1": "",
                    "FID_INPUT_PRICE_2": "",
                    "FID_VOL_CNT": "",
                    "FID_INPUT_DATE_1": ""
                },
                tr_id="FHPST01720000"  # 호가잔량 순위 TR_ID
            )
            
            if data and 'output' in data:
                return data['output'][:limit]
            return None
                
        except Exception as e:
            logger.error(f"호가잔량 순위 조회 실패: {e}")
            return None
    
    def get_multiple_current_price(self, symbols: List[str], market_type: str = "J") -> Optional[List[Dict]]:
        """
        관심종목(멀티종목) 시세조회 - NX/UN 지원 추가!
        
        Args:
            symbols: 종목코드 리스트 (최대 30개)
            market_type: 시장구분 (J:KRX, NX:NXT, UN:통합) - 신규 추가!
        
        Returns:
            여러 종목의 현재가 정보 리스트
        """
        try:
            if not symbols or len(symbols) > 30:
                logger.warning(f"종목코드는 1~30개 사이여야 합니다. 현재: {len(symbols)}개")
                return None
            
            # 종목코드를 공백으로 구분된 문자열로 변환
            symbol_string = " ".join(symbols)
            
            data = self._make_api_call(
                endpoint="quotations/inquire-multi-price",
                params={
                    "FID_COND_MRKT_DIV_CODE": market_type,  # NX, UN 추가 지원
                    "FID_INPUT_ISCD": symbol_string
                },
                tr_id="FHKST11300006"  # 관심종목(멀티종목) 시세조회 TR_ID
            )
            
            if data and 'output' in data:
                return data['output']
            return None
                
        except Exception as e:
            logger.error(f"관심종목 시세 조회 실패: {e}")
            return None
    
    # === 업종/기타 ===
    
    def get_sector_index(self, sector_code: str) -> Optional[Dict]:
        """대형주 시세 정보 (실용적 대체 구현)"""
        try:
            # 주요 대형주 정보 제공 (실제로 유용한 정보)
            major_stocks = {
                "0001": [
                    ("005930", "삼성전자"),
                    ("000660", "SK하이닉스"),
                    ("005380", "현대차")
                ],
                "001": [
                    ("005930", "삼성전자"),
                    ("000660", "SK하이닉스"),
                    ("005380", "현대차")
                ],
                "1001": [
                    ("035420", "NAVER"),
                    ("035720", "카카오"),
                    ("051910", "LG화학")
                ],
                "002": [
                    ("035420", "NAVER"),
                    ("035720", "카카오"),
                    ("051910", "LG화학")
                ],
                "2001": [
                    ("005930", "삼성전자"),
                    ("000660", "SK하이닉스"),
                    ("005380", "현대차")
                ],
                "003": [
                    ("005930", "삼성전자"),
                    ("000660", "SK하이닉스"),
                    ("005380", "현대차")
                ]
            }
            
            stocks = major_stocks.get(sector_code, [("005930", "삼성전자")])
            index_name_map = {
                "0001": "코스피 주요종목",
                "001": "코스피 주요종목",
                "1001": "코스닥 주요종목",
                "002": "코스닥 주요종목",
                "2001": "코스피200 주요종목",
                "003": "코스피200 주요종목"
            }
            
            # 주요 종목들의 현재가 조회
            stock_info = []
            for stock_code, stock_name in stocks:
                stock_data = self.get_current_price(stock_code)
                if stock_data:
                    stock_info.append({
                        'code': stock_code,
                        'name': stock_name,
                        'price': stock_data.get('stck_prpr'),
                        'change': stock_data.get('prdy_vrss'),
                        'change_rate': stock_data.get('prdy_ctrt'),  # 수정: prdy_vrss_cttr → prdy_ctrt
                        'volume': stock_data.get('acml_vol')
                    })
            
            if stock_info:
                return {
                    'category': index_name_map.get(sector_code, f"주요종목{sector_code}"),
                    'stocks': stock_info,
                    'count': len(stock_info)
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"주요 종목 정보 조회 실패: {sector_code}, {e}")
            return None
    
    def get_market_status(self) -> Optional[Dict]:
        """시장 상태 정보 (시간 기반)"""
        try:
            from datetime import datetime
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            weekday = now.weekday()  # 0=월요일, 6=일요일
            
            # 주말 체크
            is_weekend = weekday >= 5
            
            # 장 운영 시간: 평일 09:00 ~ 15:30
            is_market_open = not is_weekend and ((9 <= hour < 15) or (hour == 15 and minute <= 30))
            
            # 장전 시간외: 08:30 ~ 08:59 (✅ 정확한 범위)
            is_pre_market = (not is_weekend) and (hour == 8 and 30 <= minute <= 59)
            
            # 장후 시간외: 15:40 ~ 16:00 (✅ 괄호로 명확화)
            is_after_market = (not is_weekend) and (
                (hour == 15 and minute >= 40) or (hour == 16 and minute == 0)
            )
            
            if is_weekend:
                status_text = "주말 휴장"
            elif is_market_open:
                status_text = "정규장 개장 중"
            elif is_pre_market:
                status_text = "장전 시간외"
            elif is_after_market:
                status_text = "장후 시간외"
            else:
                status_text = "장 마감"
            
            return {
                'status': status_text,
                'is_open': is_market_open,
                'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'weekday': ['월', '화', '수', '목', '금', '토', '일'][weekday],
                'market_hours': '09:00 ~ 15:30 (정규장)',
                'pre_market': '08:30 ~ 09:00 (장전 시간외)',
                'after_market': '15:40 ~ 16:00 (장후 시간외)'
            }
        except Exception as e:
            logger.error(f"시장 상태 조회 실패: {e}")
            return None
    
    def get_news_title(self) -> Optional[List[Dict]]:
        """종합 시황/공시 제목 조회"""
        try:
            data = self._make_api_call("quote/news-title", {
                "fid_cond_mrkt_div_code": "J"
            })
            return data.get('output') if data else None
        except Exception as e:
            logger.error(f"뉴스 제목 조회 실패: {e}")
            return None
    
    # === 실시간시세 ===
    
    def get_realtime_price(self, symbol: str) -> Optional[Dict]:
        """실시간 현재가 조회 (체결가)"""
        try:
            # 주의: 실시간은 웹소켓 권장, REST는 지연 시세
            data = self._make_api_call(
                endpoint="quotations/inquire-price",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST01010100",
                use_cache=False  # 실시간은 캐시 안 함
            )
            return data.get('output') if data else None
        except Exception as e:
            logger.error(f"실시간 가격 조회 실패: {symbol}, {e}")
            return None
    
    def get_realtime_asking_price(self, symbol: str) -> Optional[Dict]:
        """실시간 호가 조회"""
        try:
            # 주의: 실시간은 웹소켓 권장, REST는 지연 시세
            data = self._make_api_call(
                endpoint="quotations/inquire-asking-price-exp-ccn",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST01010200",
                use_cache=False  # 실시간은 캐시 안 함
            )
            return data.get('output') if data else None
        except Exception as e:
            logger.error(f"실시간 호가 조회 실패: {symbol}, {e}")
            return None
    
    # === 종합 분석 메서드 ===
    
    def analyze_stock_comprehensive(self, symbol: str) -> Optional[Dict]:
        """종합적인 종목 분석"""
        try:
            # 기본 정보 수집
            basic_info = self.get_stock_basic_info(symbol)
            current_price = self.get_current_price(symbol)
            financial_ratios = self.get_financial_ratios(symbol)
            investor_trend = self.get_investor_trend(symbol)
            chart_data = self.get_chart_data(symbol)
            
            if not basic_info or not current_price:
                return None
            
            # 분석 결과 구성
            # ✅ 재무지표 출처 일관화: financial_ratios 우선, 없으면 basic_info
            fin = financial_ratios or {}
            price_val = float(current_price.get('stck_prpr', 0))
            
            # PER, PBR 계산 (가능하면 financial_ratios의 eps/bps 사용)
            eps = float(fin.get('eps', 0) or 0)
            bps = float(fin.get('bps', 0) or 0)
            per = (price_val / eps) if eps > 0 else (float(basic_info.get('per', 0)) if basic_info.get('per') else None)
            pbr = (price_val / bps) if bps > 0 else (float(basic_info.get('pbr', 0)) if basic_info.get('pbr') else None)
            
            analysis = {
                'symbol': symbol,
                'name': basic_info.get('prdt_name', ''),
                'current_price': price_val,
                'change_rate': float(current_price.get('prdy_ctrt', 0)),  # ✅ prdy_ctrt 통일!
                'market_cap': float(basic_info.get('hts_avls', 0)) * 100000000,  # 억원
                'sector': basic_info.get('bstp_kor_isnm', ''),
                
                # ✅ 기본 지표 (financial_ratios 우선)
                'valuation_metrics': {
                    'per': per,
                    'pbr': pbr,
                    'roe': float(fin.get('roe_val', 0) or basic_info.get('roe', 0) or 0),
                    'roa': float(fin.get('roa_val', 0) or basic_info.get('roa', 0) or 0),
                    'debt_ratio': float(fin.get('debt_ratio', 0) or basic_info.get('debt_ratio', 0) or 0),
                    'current_ratio': float(fin.get('current_ratio', 0) or basic_info.get('current_ratio', 0) or 0),
                    'dividend_yield': float(basic_info.get('dvyd', 0)) if basic_info.get('dvyd') else None
                },
                
                # 거래 정보
                'trading_info': {
                    'volume': int(current_price.get('acml_vol', 0)),
                    'trading_value': int(current_price.get('acml_tr_pbmn', 0)),
                    'high_52w': float(current_price.get('w52_hgpr', 0)),
                    'low_52w': float(current_price.get('w52_lwpr', 0))
                },
                
                # 투자자 동향
                'investor_trend': self._analyze_investor_trend(investor_trend),
                
                # 기술적 분석
                'technical_analysis': self._analyze_technical(chart_data),
                
                # 종합 점수
                'comprehensive_score': self._calculate_comprehensive_score(
                    basic_info, current_price, financial_ratios, investor_trend, chart_data
                )
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"종합 분석 실패: {symbol}, {e}")
            return None
    
    def _analyze_investor_trend(self, investor_data: Optional[Dict]) -> Dict:
        """투자자 동향 분석"""
        if not investor_data:
            return {'sentiment': 'neutral', 'score': 50}
        
        try:
            # 기관/외국인/개인 순매수 수량 분석
            institutional = int(investor_data.get('ntby_qty', 0))
            foreign = int(investor_data.get('frgn_ntby_qty', 0))
            individual = int(investor_data.get('prsn_ntby_qty', 0))
            
            # 스마트머니 지표 (기관 + 외국인)
            smart_money = institutional + foreign
            
            # 감정 점수 계산 (0-100)
            if smart_money > 10000:  # 1만주 이상 순매수
                sentiment_score = min(100, 70 + min(20, smart_money / 5000))
                sentiment = 'positive'
            elif smart_money < -10000:  # 1만주 이상 순매도
                sentiment_score = max(0, 30 + max(-20, smart_money / 5000))
                sentiment = 'negative'
            else:
                sentiment_score = 50
                sentiment = 'neutral'
            
            # ✅ return을 else 블록 밖으로 이동!
            return {
                'sentiment': sentiment,
                'score': sentiment_score,
                'institutional_net': institutional,
                'foreign_net': foreign,
                'individual_net': individual,
                'smart_money': smart_money
            }
                
        except Exception as e:
            logger.error(f"투자자 동향 분석 실패: {e}")
            return {'sentiment': 'neutral', 'score': 50}
    
    def _analyze_technical(self, chart_data: Optional[List[Dict]]) -> Dict:
        """기술적 분석"""
        if not chart_data or len(chart_data) < 20:
            return {'trend': 'neutral', 'momentum': 'neutral', 'score': 50}
        
        try:
            # 최근 20일 데이터로 분석
            recent_data = chart_data[-20:]
            
            # 단순 이동평균 계산
            prices = [float(d.get('stck_clpr', 0)) for d in recent_data]
            sma_5 = sum(prices[-5:]) / 5
            sma_20 = sum(prices) / 20
            
            # 추세 분석
            if sma_5 > sma_20 * 1.02:
                trend = 'uptrend'
                trend_score = 70
            elif sma_5 < sma_20 * 0.98:
                trend = 'downtrend'
                trend_score = 30
            else:
                trend = 'sideways'
                trend_score = 50
            
            # 모멘텀 분석 (RSI 유사)
            gains = []
            losses = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            if avg_loss == 0:
                momentum_score = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                momentum_score = rsi
            
            # 종합 기술적 점수
            technical_score = (trend_score + momentum_score) / 2
            
            return {
                'trend': trend,
                'momentum': 'strong' if momentum_score > 70 else 'weak' if momentum_score < 30 else 'neutral',
                'score': technical_score,
                'sma_5': sma_5,
                'sma_20': sma_20,
                'rsi': momentum_score
                }
                
        except Exception as e:
            logger.error(f"기술적 분석 실패: {e}")
            return {'trend': 'neutral', 'momentum': 'neutral', 'score': 50}
    
    def _calculate_comprehensive_score(self, basic_info: Dict, current_price: Dict,
                                     financial_ratios: Optional[Dict],
                                     investor_trend: Optional[Dict],
                                     chart_data: Optional[List[Dict]]) -> Dict:
        """종합 점수 계산 (✅ 재무지표 출처 일관화: financial_ratios 우선)"""
        try:
            scores = {}
            weights = {
                'valuation': 0.3,      # 밸류에이션 30%
                'profitability': 0.25,  # 수익성 25%
                'stability': 0.2,       # 안정성 20%
                'growth': 0.15,         # 성장성 15%
                'sentiment': 0.1        # 투자자 감정 10%
            }
            
            # ✅ 재무지표 우선 사용
            fin = financial_ratios or {}
            price_val = float(current_price.get('stck_prpr', 0))
            
            # PER, PBR 계산 (financial_ratios 우선)
            eps = float(fin.get('eps', 0) or 0)
            bps = float(fin.get('bps', 0) or 0)
            per = (price_val / eps) if eps > 0 else (float(basic_info.get('per', 0)) if basic_info.get('per') else None)
            pbr = (price_val / bps) if bps > 0 else (float(basic_info.get('pbr', 0)) if basic_info.get('pbr') else None)
            
            # 밸류에이션 점수 (PER, PBR 기준)
            valuation_score = 50
            
            if per and per > 0:
                if per < 15:
                    valuation_score += 20
                elif per < 25:
                    valuation_score += 10
                elif per > 50:
                    valuation_score -= 20
            
            if pbr and pbr > 0:
                if pbr < 1.5:
                    valuation_score += 20
                elif pbr < 2.5:
                    valuation_score += 10
                elif pbr > 5:
                    valuation_score -= 20
            
            # 수익성 점수 (ROE, ROA 기준) - ✅ financial_ratios 우선
            profitability_score = 50
            roe = float(fin.get('roe_val', 0) or basic_info.get('roe', 0) or 0)
            roa = float(fin.get('roa_val', 0) or basic_info.get('roa', 0) or 0)
            
            if roe and roe > 0:
                if roe > 15:
                    profitability_score = 80
                elif roe > 10:
                    profitability_score = 70
                elif roe > 5:
                    profitability_score = 60
            else:
                profitability_score = 40
            
            # 안정성 점수 (부채비율, 유동비율 기준) - ✅ financial_ratios 우선
            stability_score = 50
            debt_ratio = float(fin.get('debt_ratio', 0) or basic_info.get('debt_ratio', 0) or 0)
            current_ratio = float(fin.get('current_ratio', 0) or basic_info.get('current_ratio', 0) or 0)
            
            if debt_ratio > 0:  # ✅ 데이터가 있을 때만
                if debt_ratio < 30:
                    stability_score = 80
                elif debt_ratio < 50:
                    stability_score = 70
                elif debt_ratio < 70:
                    stability_score = 60
                else:
                    stability_score = 40
            
            if current_ratio > 2:
                stability_score += 10
            elif current_ratio > 0 and current_ratio < 1:
                stability_score -= 20
            
            # 성장성 점수 (매출/영업이익 증가율)
            growth_score = 50  # 차트 데이터에서 계산 가능
            
            # 투자자 감정 점수
            sentiment_score = 50
            if investor_trend:
                sentiment_analysis = self._analyze_investor_trend(investor_trend)
                sentiment_score = sentiment_analysis['score']
            
            # 가중평균 계산
            total_score = (
                valuation_score * weights['valuation'] +
                profitability_score * weights['profitability'] +
                stability_score * weights['stability'] +
                growth_score * weights['growth'] +
                sentiment_score * weights['sentiment']
            )
            
            return {
                'total_score': round(total_score, 1),
                'component_scores': {
                    'valuation': valuation_score,
                    'profitability': profitability_score,
                    'stability': stability_score,
                    'growth': growth_score,
                    'sentiment': sentiment_score
                },
                'grade': self._get_grade(total_score),
                'recommendation': self._get_recommendation(total_score)
            }
            
        except Exception as e:
            logger.error(f"종합 점수 계산 실패: {e}")
            return {'total_score': 50, 'grade': 'C', 'recommendation': 'HOLD'}
    
    def _get_grade(self, score: float) -> str:
        """점수에 따른 등급 반환"""
        if score >= 80:
            return 'A+'
        elif score >= 70:
            return 'A'
        elif score >= 60:
            return 'B+'
        elif score >= 50:
            return 'B'
        elif score >= 40:
            return 'C+'
        elif score >= 30:
            return 'C'
        else:
            return 'D'
    
    def _get_recommendation(self, score: float) -> str:
        """점수에 따른 추천 반환"""
        if score >= 75:
            return 'STRONG_BUY'
        elif score >= 65:
            return 'BUY'
        elif score >= 55:
            return 'HOLD'
        elif score >= 45:
            return 'WEAK_HOLD'
        else:
            return 'SELL'
    
    def get_dividend_ranking(self, limit: int = 100) -> Optional[List[Dict]]:
        """배당률 상위 종목 조회 (가치주 발굴에 유용)"""
        try:
            from datetime import datetime, timedelta
            
            # 최근 1년 기준
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            # 실제 한도 제한 (API는 최대 100개 정도)
            actual_limit = min(limit, 100)
            
            data = self._make_api_call(
                endpoint="ranking/dividend-rate",
                params={
                    "CTS_AREA": " ",
                    "GB1": "0",  # 전체
                    "UPJONG": "0001",  # 코스피 종합
                    "GB2": "0",  # 전체
                    "GB3": "2",  # 현금배당
                    "F_DT": start_date.strftime("%Y%m%d"),
                    "T_DT": end_date.strftime("%Y%m%d"),
                    "GB4": "0"  # 전체
                },
                tr_id="HHKDB13470100",
                use_cache=True  # 캐싱 활성화 (배당률은 자주 변하지 않음)
            )
            
            if data and 'output' in data:
                results = data['output']
                logger.info(f"📊 배당률 순위 API 응답: {len(results)}개 (요청: {actual_limit}개)")
                return results[:actual_limit]
            
            logger.warning("⚠️ 배당률 순위 조회 실패: output 없음")
            return None
            
        except Exception as e:
            logger.error(f"❌ 배당률 순위 조회 실패: {e}")
            return None
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """종목 기본 정보 조회 (섹터 포함)"""
        try:
            data = self._make_api_call(
                endpoint="quotations/search-info",
                params={
                    "PDNO": symbol,
                    "PRDT_TYPE_CD": "300"  # 주식
                },
                tr_id="CTPF1604R"
            )
            
            if data and 'output' in data:
                output = data['output']
                if isinstance(output, list) and len(output) > 0:
                    return output[0]
                elif isinstance(output, dict):
                    return output
            return None
            
        except Exception as e:
            logger.error(f"종목 정보 조회 실패: {symbol}, {e}")
            return None
    
    def find_real_value_stocks(self, limit: int = 50, criteria: Dict = None, candidate_pool_size: int = 200, 
                              stock_universe: List[str] = None) -> Optional[List[Dict]]:
        """
        진짜 가치주 발굴 (PER, PBR, ROE 기준)
        
        Args:
            limit: 발굴할 최대 종목 수
            criteria: 가치주 기준 (per_max, pbr_max, roe_min, min_volume)
            candidate_pool_size: 후보군 크기 (기본 200개, 각 API는 30~100개씩 반환)
            stock_universe: 외부에서 제공하는 종목 리스트 (코드 리스트)
            
        Note:
            각 순위 API는 30~100개 수준만 반환하므로 여러 API를 조합해서 다양한 종목 확보
            - 거래량: 약 30개
            - 시가총액: 약 50~100개
            - PER: 약 50~100개
            - 배당: 약 100개
            → 총 200~300개 수준의 후보군 확보 가능
        """
        try:
            if criteria is None:
                criteria = {
                    'per_max': 18.0,   # ✅ 15 → 18 완화 (더 많은 종목 발견)
                    'pbr_max': 2.0,    # ✅ 1.5 → 2.0 완화
                    'roe_min': 8.0,    # ✅ 10 → 8 완화
                    'min_volume': 100000  # ✅ 100만 → 10만 완화 (유동성 기준)
                }
            
            logger.info("MCP 진짜 가치주 발굴 시작...")
            
            # 1단계: 후보 수집
            candidates = []
            
            # ✅ 외부 종목 리스트가 제공된 경우 (기존 시스템 활용!)
            if stock_universe and isinstance(stock_universe, list):
                logger.info(f"✅ 외부 종목 유니버스 사용: {len(stock_universe)}개")
                for symbol in stock_universe[:candidate_pool_size]:
                    candidates.append({
                        'mksc_shrn_iscd': symbol,
                        'hts_kor_isnm': '',  # 나중에 조회
                        'stck_prpr': '0',
                        'acml_vol': '0',
                        'prdy_ctrt': '0'
                    })
                logger.info(f"✅ 1단계 완료: {len(candidates)}개 후보 (외부 유니버스)")
            else:
                # 기존 방식: 순위 API 조합
                # 📌 각 API는 30~100개씩만 반환하므로 여러 API를 조합해서 다양한 종목 확보
                
                # 1-1. 거래량 상위 종목 (유동성) - 약 30개
                logger.info(f"1-1단계: 거래량 상위 종목 조회 (약 30개)...")
                volume_stocks = self.get_volume_ranking()
                if volume_stocks:
                    candidates.extend(volume_stocks)
                    logger.info(f"✅ 거래량 상위 {len(volume_stocks)}개 조회")
                else:
                    logger.warning("⚠️ 거래량 순위 조회 실패")
                
                # 1-2. 시가총액 상위 종목 (대형주) - 약 50~100개
                if len(candidates) < candidate_pool_size:
                    logger.info(f"1-2단계: 시가총액 상위 종목 조회 (약 50~100개)...")
                    market_cap_stocks = self.get_market_cap_ranking()
                    if market_cap_stocks:
                        for stock in market_cap_stocks:
                            symbol = stock.get('mksc_shrn_iscd', '')
                            if symbol and not any(c.get('mksc_shrn_iscd') == symbol for c in candidates):
                                candidates.append(stock)
                        logger.info(f"✅ 시가총액 상위 {len(market_cap_stocks)}개 추가 (중복 제외 후: {len(candidates)}개)")
                
                # 1-3. PER 순위 (저PER 가치주) - 약 50~100개
                if len(candidates) < candidate_pool_size:
                    logger.info(f"1-3단계: PER 순위 조회 (약 50~100개)...")
                    per_stocks = self.get_per_ranking()
                    if per_stocks:
                        for stock in per_stocks:
                            symbol = stock.get('mksc_shrn_iscd', '')
                            if symbol and not any(c.get('mksc_shrn_iscd') == symbol for c in candidates):
                                candidates.append(stock)
                        logger.info(f"✅ PER 순위 {len(per_stocks)}개 추가 (중복 제외 후: {len(candidates)}개)")
                
                # 1-4. 배당률 상위 종목 (가치주 특성) - 약 100개
                if len(candidates) < candidate_pool_size:
                    logger.info(f"1-4단계: 배당률 상위 종목 조회 (약 100개)...")
                    dividend_stocks = self.get_dividend_ranking(limit=100)
                    if dividend_stocks:
                        added = 0
                        for stock in dividend_stocks:
                            symbol = stock.get('stk_shrn_cd', '') or stock.get('mksc_shrn_iscd', '')
                            if symbol and len(symbol) == 6:
                                if not any(c.get('mksc_shrn_iscd') == symbol for c in candidates):
                                    candidates.append({
                                        'mksc_shrn_iscd': symbol,
                                        'hts_kor_isnm': stock.get('hts_kor_isnm', ''),
                                        'stck_prpr': stock.get('stck_prpr', '0'),
                                        'acml_vol': stock.get('acml_vol', '0'),
                                        'prdy_ctrt': stock.get('prdy_ctrt', '0')
                                    })
                                    added += 1
                        logger.info(f"✅ 배당주 {added}개 추가 (중복 제외 후: {len(candidates)}개)")
                
                logger.info(f"✅ 1단계 완료: 총 {len(candidates)}개 후보 종목 (목표: {candidate_pool_size}개)")
            
            # 2단계: 각 종목의 재무비율 조회 및 가치주 판별
            value_stocks = []
            checked_count = 0
            
            logger.info(f"2단계 시작: {len(candidates)}개 종목 재무 분석...")
            
            for stock in candidates:
                try:
                    symbol = stock.get('mksc_shrn_iscd', '')
                    if not symbol or len(symbol) != 6:
                        continue
                    
                    # ETF/ETN 제외
                    name = stock.get('hts_kor_isnm', '')
                    if symbol.startswith('Q') or any(keyword in name for keyword in ['KODEX', 'TIGER', 'ARIRANG', 'ETF', 'ETN']):
                        continue
                    
                    # 재무비율 조회 먼저 (거래량은 current_price에서 확인)
                    financial = self.get_financial_ratios(symbol)
                    checked_count += 1
                    
                    if not financial:
                        continue
                    
                    # 종목 기본 정보는 get_current_price에서 얻을 수 있는 정보 활용
                    # (API 호출 1회 절약!)
                    current_price_data = self.get_current_price(symbol)
                    
                    if not current_price_data:
                        continue
                    
                    # 거래량 확인 (current_price에서 확인)
                    volume = int(current_price_data.get('acml_vol', 0))
                    if volume < criteria.get('min_volume', 0):
                        continue
                    
                    # 섹터 정보 추출 (get_current_price에 업종명 포함)
                    sector = current_price_data.get('bstp_kor_isnm', '기타')
                    
                    # 종목명 가져오기 (우선순위: current_price → stock → basic_info)
                    stock_name = current_price_data.get('hts_kor_isnm', '') or name
                    if not stock_name:
                        # 종목명이 없으면 get_stock_basic_info 호출
                        basic_info = self.get_stock_basic_info(symbol)
                        if basic_info:
                            stock_name = basic_info.get('prdt_name', '') or basic_info.get('prdt_abrv_name', '')
                    if not stock_name:
                        stock_name = f"종목{symbol}"  # 최후의 수단
                    
                    # ✨ "보통주" 제거, "우선주"는 "우"로 축약
                    stock_name = stock_name.replace('보통주', '')
                    if '우선주' in stock_name:
                        stock_name = stock_name.replace('우선주', '우')
                    stock_name = stock_name.strip()
                    
                    market_cap_억 = float(current_price_data.get('hts_avls', 0))
                    
                    # PER, PBR, ROE 추출 및 계산
                    price = float(current_price_data.get('stck_prpr', 0))
                    eps = float(financial.get('eps', 0) or 0)
                    bps = float(financial.get('bps', 0) or 0)
                    roe = float(financial.get('roe_val', 0) or 0)
                    
                    # PER = 주가 / EPS
                    per = (price / eps) if eps > 0 else 999
                    
                    # PBR = 주가 / BPS  
                    pbr = (price / bps) if bps > 0 else 999
                    
                    # 가치주 기준 충족 확인 (섹터 고려)
                    is_value_stock = (
                        per > 0 and per <= criteria['per_max'] and
                        pbr > 0 and pbr <= criteria['pbr_max'] and
                        roe >= criteria['roe_min']
                    )
                    
                    if is_value_stock:
                        score = self._calculate_value_score(per, pbr, roe)
                        
                        # 섹터별 보너스 점수
                        sector_bonus = self._get_sector_bonus(sector, per, pbr)
                        final_score = min(100, score + sector_bonus)
                        
                        value_stocks.append({
                            'symbol': symbol,
                            'name': stock_name,  # current_price_data에서 가져온 이름
                            'price': price,  # ✨ 이미 계산한 price 변수 사용! (1439번 라인)
                            'per': per,
                            'pbr': pbr,
                            'roe': roe,
                            'volume': volume,
                            'change_rate': float(current_price_data.get('prdy_ctrt', 0)),  # ✨ current_price_data 사용!
                            'score': final_score,
                            'sector': sector,
                            'debt_ratio': float(financial.get('debt_ratio', 0) or 0),
                            'current_ratio': float(financial.get('current_ratio', 0) or 0),
                            'market_cap': market_cap_억 * 100000000  # 억원 → 원
                        })
                        
                        logger.info(f"✅ 가치주 발견: {stock_name} [{sector}] (PER={per:.1f}, PBR={pbr:.1f}, ROE={roe:.1f}%, 점수={final_score:.1f})")
                    
                    # 진행 상황 로깅
                    if checked_count % 20 == 0:
                        logger.info(f"진행: {checked_count}개 분석, {len(value_stocks)}개 가치주 발굴")
                    
                    # 충분한 종목 발굴 시 종료 (하지만 후보가 충분하면 계속)
                    if len(value_stocks) >= limit and checked_count >= 50:
                        logger.info(f"목표 달성: {len(value_stocks)}개 발굴 (조기 종료)")
                        break
                        
                except Exception as e:
                    logger.debug(f"종목 {symbol} 분석 실패: {e}")
                    continue
            
            # 점수순 정렬
            value_stocks.sort(key=lambda x: x['score'], reverse=True)
            
            # ✅ 섹터 다양성 확보: 금융 최대 30% 제한 (항상 적용)
            if len(value_stocks) >= 5:  # ✅ 5개 이상이면 다양성 적용
                diversified_stocks = []
                sector_count = {}
                target_limit = min(limit, len(value_stocks))  # 실제 발견된 수와 목표 중 작은 값
                max_per_sector = max(1, int(target_limit * 0.3))  # 섹터당 최대 30% (최소 1개)
                
                logger.info(f"📊 섹터 다양성 적용: 섹터당 최대 {max_per_sector}개 (30%), 목표: {target_limit}개")
                
                # 2-pass 방식: 먼저 제한 내에서 채우고, 부족하면 추가
                pass1_stocks = []
                pass1_count = {}
                
                # Pass 1: 섹터 최대치 엄수
                for stock in value_stocks:
                    sector = stock['sector']
                    if sector not in pass1_count:
                        pass1_count[sector] = 0
                    
                    if pass1_count[sector] < max_per_sector:
                        pass1_stocks.append(stock)
                        pass1_count[sector] += 1
                
                diversified_stocks = pass1_stocks
                sector_count = pass1_count.copy()
                
                # Pass 2: 목표 미달이면 남은 종목 추가 (✅ 최대치 미달 섹터 우선)
                if len(diversified_stocks) < target_limit:
                    remaining_stocks = [s for s in value_stocks if s not in diversified_stocks]
                    
                    # ✅ 최대치에 도달한 섹터 제외하고 추가
                    added = 0
                    for stock in remaining_stocks:
                        if len(diversified_stocks) >= target_limit:
                            break
                        
                        sector = stock['sector']
                        current_count = sector_count.get(sector, 0)
                        
                        # 섹터 최대치 미달인 경우만 추가
                        if current_count < max_per_sector:
                            diversified_stocks.append(stock)
                            sector_count[sector] = current_count + 1
                            added += 1
                            logger.debug(f"📊 Pass 2: {stock['name']} [{sector}] 추가 ({current_count+1}/{max_per_sector})")
                    
                    if added > 0:
                        logger.info(f"📊 Pass 2: {added}개 추가 (섹터 최대치 준수)")
                    else:
                        logger.warning(f"⚠️ Pass 2: 추가 불가 (모든 섹터가 최대치 도달)")
                
                # 섹터 분포 로깅
                logger.info(f"📊 최종 섹터 분포: {dict(sector_count)}")
                value_stocks = diversified_stocks
            
            logger.info(f"✅ MCP 가치주 발굴 완료: {len(value_stocks)}개 발굴 ({checked_count}개 분석)")
            return value_stocks[:limit]  # limit 적용
            
        except Exception as e:
            logger.error(f"가치주 발굴 실패: {e}")
            return None
    
    def _calculate_value_score(self, per: float, pbr: float, roe: float) -> float:
        """가치주 점수 계산"""
        try:
            score = 0.0
            
            # PER 점수 (낮을수록 좋음, 최대 40점)
            if per > 0:
                if per <= 8:
                    score += 40
                elif per <= 12:
                    score += 30
                elif per <= 15:
                    score += 20
                elif per <= 20:
                    score += 10
            
            # PBR 점수 (낮을수록 좋음, 최대 30점)
            if pbr > 0:
                if pbr <= 0.8:
                    score += 30
                elif pbr <= 1.0:
                    score += 25
                elif pbr <= 1.3:
                    score += 20
                elif pbr <= 1.5:
                    score += 10
            
            # ROE 점수 (높을수록 좋음, 최대 30점)
            if roe >= 20:
                score += 30
            elif roe >= 15:
                score += 25
            elif roe >= 12:
                score += 20
            elif roe >= 10:
                score += 15
            elif roe >= 7:
                score += 10
            
            return round(score, 1)
        except:
            return 0.0
    
    def _get_sector_bonus(self, sector: str, per: float, pbr: float) -> float:
        """
        섹터별 보너스 점수 (최대 10점)
        ✅ 균등 조정: 금융 편향 해소, 다양성 확보
        """
        try:
            bonus = 0.0
            
            # ✅ 금융주: 보너스 축소 (편향 해소)
            if '금융' in sector or '은행' in sector or '증권' in sector or '보험' in sector:
                if pbr < 0.5:  # 기준 강화 (0.7 → 0.5)
                    bonus += 5  # 축소 (10 → 5)
                elif pbr < 0.8:  # 기준 완화 (1.0 → 0.8)
                    bonus += 3  # 축소 (5 → 3)
            
            # ✅ IT/바이오: 보너스 증가 (성장주 중시)
            elif 'IT' in sector or '바이오' in sector or '제약' in sector or '서비스' in sector:
                if per < 20:  # 기준 강화 (25 → 20)
                    bonus += 8  # 증가 (5 → 8)
                elif per < 30:
                    bonus += 4
            
            # ✅ 제조업: 보너스 유지
            elif '제조' in sector or '화학' in sector or '철강' in sector:
                if per < 12 and pbr < 1.0:
                    bonus += 8  # 약간 축소 (10 → 8)
                elif per < 15:
                    bonus += 5
            
            # ✅ 유틸리티: 보너스 증가
            elif '전력' in sector or '가스' in sector or '에너지' in sector:
                if pbr < 1.0:
                    bonus += 8
                if per < 10:  # 추가 조건
                    bonus += 3
            
            # ✅ 통신: 신규 추가
            elif '통신' in sector:
                if pbr < 1.0 and per < 15:
                    bonus += 6
            
            # ✅ 운송/물류: 신규 추가
            elif '운송' in sector or '물류' in sector or '창고' in sector:
                if pbr < 1.0:
                    bonus += 5
                if per < 15:
                    bonus += 3
            
            # ✅ 전기·전자: 신규 추가
            elif '전기' in sector or '전자' in sector:
                if pbr < 1.0:
                    bonus += 6
                if per < 12:
                    bonus += 4
            
            return bonus
        except:
            return 0.0
    
    def clear_cache(self):
        """캐시 초기화 (멀티스레드 안전)"""
        with self._cache_lock:  # ✅ Lock으로 보호
            self.cache.clear()
        logger.info("KIS API 캐시 초기화 완료")