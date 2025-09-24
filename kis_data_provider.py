# kis_data_provider.py
import requests
import time
import random
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from kis_token_manager import KISTokenManager

logger = logging.getLogger(__name__)

class KISDataProvider:
    """KIS API를 통해 주식 데이터를 수집하는 클래스"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.token_manager = KISTokenManager(config_path)
        self.base_url = "https://openapi.koreainvestment.com:9443"
        
        self.headers = {
            "content-type": "application/json; charset=utf-8",
            "appkey": self.token_manager.app_key,
            "appsecret": self.token_manager.app_secret,
        }
        # 세션 설정 개선 (연결 재사용 및 안정성 향상)
        self.session = requests.Session()
        
        # 연결 풀 설정
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # 우리가 직접 재시도 로직 구현
        )
        self.session.mount('https://', adapter)
        
        # 세션 헤더 설정
        self.session.headers.update({
            'User-Agent': 'KIS-API-Client/1.0',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        self.last_request_time = 0
        self.request_interval = 0.12  # API TPS 20회/초 제한 준수 (50ms + 여유)

    def _rate_limit(self):
        """API 요청 속도를 제어합니다."""
        elapsed_time = time.time() - self.last_request_time
        if elapsed_time < self.request_interval:
            time.sleep(self.request_interval - elapsed_time)
        self.last_request_time = time.time()

    def _send_request(self, path: str, tr_id: str, params: dict, max_retries: int = 2) -> Optional[dict]:
        """중앙 집중화된 API GET 요청 메서드 (재시도 로직 포함)"""
        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()
                token = self.token_manager.get_valid_token()
                headers = {**self.headers, "authorization": f"Bearer {token}", "tr_id": tr_id}
                
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
                return data
                
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries:
                    # 지수형 백오프: 0.3 → 0.6 → 1.2초 + 지터
                    backoff = 0.3 * (2 ** attempt) + random.uniform(0, 0.2)
                    logger.debug(f"🔄 연결 오류 재시도 중... ({attempt + 1}/{max_retries}, {backoff:.1f}초 대기): {e}")
                    time.sleep(backoff)
                    continue
                else:
                    logger.error(f"❌ API 연결 실패 ({tr_id}): {e}")
                    return None
            except requests.exceptions.Timeout as e:
                if attempt < max_retries:
                    # 지수형 백오프: 0.3 → 0.6 → 1.2초 + 지터
                    backoff = 0.3 * (2 ** attempt) + random.uniform(0, 0.2)
                    logger.debug(f"🔄 타임아웃 재시도 중... ({attempt + 1}/{max_retries}, {backoff:.1f}초 대기): {e}")
                    time.sleep(backoff)
                    continue
                else:
                    logger.error(f"❌ API 타임아웃 ({tr_id}): {e}")
                    return None
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 500:
                    if attempt < max_retries:
                        backoff = 0.3 * (2 ** attempt) + random.uniform(0, 0.2)
                        logger.warning(f"⚠️ 서버 내부 오류 (500) - {backoff:.1f}초 후 재시도 ({attempt + 1}/{max_retries}) ({tr_id}): {e}")
                        time.sleep(backoff)
                        continue
                    else:
                        logger.error(f"❌ 서버 내부 오류 (500) - 최대 재시도 횟수 초과 ({tr_id}): {e}")
                        return None
                elif e.response.status_code == 429:
                    if attempt < max_retries:
                        backoff = 5 * (attempt + 1)  # 5초, 10초, 15초
                        logger.warning(f"⚠️ API 호출 한도 초과 (429) - {backoff}초 후 재시도 ({attempt + 1}/{max_retries}) ({tr_id}): {e}")
                        time.sleep(backoff)
                        continue
                    else:
                        logger.error(f"❌ API 호출 한도 초과 (429) - 최대 재시도 횟수 초과 ({tr_id}): {e}")
                        return None
                else:
                    logger.error(f"❌ HTTP 오류 ({e.response.status_code}) ({tr_id}): {e}")
                    return None
            except requests.RequestException as e:
                logger.error(f"❌ API 호출 실패 ({tr_id}): {e}")
                return None
        
        return None

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        """안전하게 float 타입으로 변환합니다."""
        if value is None or value == '': return default
        try:
            return float(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return default

    def get_stock_price_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """주식 현재가 및 주요 투자지표를 조회합니다."""
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol}
        data = self._send_request(path, "FHKST01010100", params)
        
        if data and 'output' in data:
            output = data['output']
            return {
                'symbol': symbol,
                'name': output.get('bstp_kor_isnm', f'종목코드: {symbol}'),
                'current_price': self._to_float(output.get('stck_prpr')),
                'volume': self._to_float(output.get('acml_vol')),
                'market_cap': self._to_float(output.get('hts_avls')) * 1_0000_0000, # 억원 -> 원
                'per': self._to_float(output.get('per')),
                'pbr': self._to_float(output.get('pbr')),
                'eps': self._to_float(output.get('eps')),
                'bps': self._to_float(output.get('bps')),
                'dividend_yield': self._to_float(output.get('yld_rat')),
                # 추가 데이터
                'open_price': self._to_float(output.get('stck_oprc')),
                'high_price': self._to_float(output.get('stck_hgpr')),
                'low_price': self._to_float(output.get('stck_lwpr')),
                'prev_close': self._to_float(output.get('stck_sdpr')),
                'change_price': self._to_float(output.get('prdy_vrss')),
                'change_rate': self._to_float(output.get('prdy_ctrt')),
                'trading_value': self._to_float(output.get('acml_tr_pbmn')), # 거래대금
                'listed_shares': self._to_float(output.get('lstn_stcn')), # 상장주수
                'foreign_holdings': self._to_float(output.get('frgn_hldn_qty')), # 외국인 보유수량
                'foreign_net_buy': self._to_float(output.get('frgn_ntby_qty')), # 외국인 순매수
                'program_net_buy': self._to_float(output.get('pgtr_ntby_qty')), # 프로그램매매 순매수
                'w52_high': self._to_float(output.get('w52_hgpr')), # 52주 최고가
                'w52_low': self._to_float(output.get('w52_lwpr')), # 52주 최저가
                'd250_high': self._to_float(output.get('d250_hgpr')), # 250일 최고가
                'd250_low': self._to_float(output.get('d250_lwpr')), # 250일 최저가
                'vol_turnover': self._to_float(output.get('vol_tnrt')), # 거래량 회전율
                'sector': output.get('bstp_kor_isnm', ''), # 업종명
                'market_status': output.get('iscd_stat_cls_code', ''), # 종목상태
                'margin_rate': output.get('marg_rate', ''), # 증거금비율
                'credit_available': output.get('crdt_able_yn', ''), # 신용가능여부
                'short_selling': output.get('ssts_yn', ''), # 공매도가능여부
                'investment_caution': output.get('invt_caful_yn', ''), # 투자유의여부
                'market_warning': output.get('mrkt_warn_cls_code', ''), # 시장경고코드
                'short_overheating': output.get('short_over_yn', ''), # 단기과열여부
                'management_stock': output.get('mang_issu_cls_code', ''), # 관리종목여부
            }
        return None

    def get_daily_price_history(self, symbol: str, days: int = 252) -> pd.DataFrame:
        """지정한 기간 동안의 일봉 데이터를 조회합니다."""
        path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 1.5) # 주말/휴일 감안하여 넉넉하게 조회
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
            "FID_INPUT_DATE_1": start_date.strftime('%Y%m%d'),
            "FID_INPUT_DATE_2": end_date.strftime('%Y%m%d'),
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "1" # 수정주가 반영
        }
        logger.info(f"🔍 일봉 데이터 요청: {symbol}, 기간: {start_date.strftime('%Y%m%d')} ~ {end_date.strftime('%Y%m%d')}")
        data = self._send_request(path, "FHKST01010400", params)
        
        if data:
            logger.info(f"📊 API 응답 키: {list(data.keys())}")
            # KIS API 일봉 데이터는 'output' 키에 들어있습니다
            if 'output' in data:
                price_list = data['output']
                logger.info(f"📈 일봉 데이터 개수: {len(price_list) if price_list else 0}")
                if not price_list: 
                    logger.warning("⚠️ 일봉 데이터가 비어있습니다.")
                    return pd.DataFrame()
                
                df = pd.DataFrame(price_list)
                logger.info(f"📋 일봉 데이터 컬럼: {list(df.columns)}")
                
                # 필요한 컬럼이 있는지 확인
                required_cols = ['stck_bsop_date', 'stck_clpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'acml_vol']
                available_cols = [col for col in required_cols if col in df.columns]
                logger.info(f"📋 사용 가능한 컬럼: {available_cols}")
                
                if len(available_cols) >= 6:
                    df = df[available_cols]
                    df.columns = ['date', 'close', 'open', 'high', 'low', 'volume']
                    
                    # 데이터 타입 변환
                    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
                    for col in ['close', 'open', 'high', 'low', 'volume']:
                        df[col] = pd.to_numeric(df[col])
                    
                    result = df.sort_values('date', ascending=False).head(days).reset_index(drop=True)
                    logger.info(f"✅ 일봉 데이터 처리 완료: {len(result)}개 행")
                    return result
                else:
                    logger.warning(f"⚠️ 필요한 컬럼이 부족합니다. 필요: {required_cols}, 사용가능: {available_cols}")
            else:
                logger.warning(f"⚠️ output 키가 없습니다. 사용 가능한 키: {list(data.keys())}")
        else:
            logger.error("❌ API 응답이 None입니다.")
        return pd.DataFrame()