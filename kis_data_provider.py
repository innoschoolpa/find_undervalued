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
        # KIS API 제한: 실전 20건/초, 모의 2건/초
        # 안전하게 실전 10건/초 (0.1초 간격) 사용
        self.request_interval = 0.1  # 0.1초 간격 (초당 10건)
        self.consecutive_500_errors = 0  # 연속 500 오류 카운터

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
                
                # 성공적인 요청 시 500 오류 카운터 리셋
                self.consecutive_500_errors = 0
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
                    self.consecutive_500_errors += 1
                    
                    # 연속 500 오류가 많으면 더 긴 대기
                    if self.consecutive_500_errors > 5:
                        logger.warning(f"⚠️ 연속 500 오류 {self.consecutive_500_errors}회 - 10초 대기")
                        time.sleep(10)
                        self.consecutive_500_errors = 0  # 리셋
                        return None  # 재시도하지 않고 포기
                    
                    if attempt < max_retries:
                        # 500 오류 시 더 긴 백오프 (3초, 6초, 12초)
                        backoff = 3.0 * (2 ** attempt) + random.uniform(0, 2.0)
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

    def get_kospi_stock_list(self, max_count: int = 300, use_dart_integration: bool = False) -> List[Dict[str, Any]]:
        """KOSPI 종목 리스트를 API로 동적으로 가져옵니다 (시가총액순)"""
        try:
            # DART API 통합 사용 여부 확인
            if use_dart_integration:
                try:
                    from integrated_market_cap_provider import IntegratedMarketCapProvider
                    logger.info(f"🔍 DART API 통합 방식으로 {max_count}개 종목 조회 시도")
                    
                    integrated_provider = IntegratedMarketCapProvider()
                    stocks = integrated_provider.get_top_stocks_by_market_cap(max_count)
                    
                    if stocks and len(stocks) >= max_count * 0.5:  # 50% 이상 성공시 (완화)
                        logger.info(f"✅ DART API 통합으로 {len(stocks)}개 종목 수집 완료")
                        return stocks
                    else:
                        logger.warning("DART API 통합 결과 부족, KIS API 단독 사용")
                except ImportError as e:
                    logger.warning(f"DART API 통합 모듈을 찾을 수 없음: {e}, KIS API 단독 사용")
                except Exception as e:
                    logger.warning(f"DART API 통합 실패: {e}, KIS API 단독 사용")
            
            # KIS API 단독 사용
            logger.info(f"🔍 KIS API 단독으로 {max_count}개 종목 조회")
            stocks = self._get_market_cap_ranked_stocks(max_count)
            
            if not stocks:
                logger.warning("API로 종목 목록을 가져오지 못했습니다. 폴백 리스트를 사용합니다.")
                return self._get_fallback_stock_list()
            
            logger.info(f"✅ KIS API로 {len(stocks)}개 종목을 가져왔습니다. (요청: {max_count}개)")
            
            # KIS API 한계로 인한 부족분 안내
            if len(stocks) < max_count:
                logger.warning(f"⚠️ KIS API 한계: {len(stocks)}/{max_count}개만 반환됨")
                logger.info("💡 해결 방안: DART API 통합 또는 외부 데이터 소스 활용 필요")
            
            return stocks
                
        except Exception as e:
            logger.error(f"KOSPI 종목 리스트 조회 중 오류: {e}")
            return self._get_fallback_stock_list()
    
    def _get_market_cap_ranked_stocks(self, max_count: int) -> List[Dict[str, Any]]:
        """시가총액 순으로 종목 목록을 조회합니다 (단순화된 접근)"""
        try:
            logger.info(f"🔍 단순화된 방식으로 {max_count}개 종목 수집 시작")
            
            # 복잡한 범위별 요청 대신 단순한 개별 조회 방식 사용
            return self._get_market_cap_ranked_stocks_fallback(max_count)
            
        except Exception as e:
            logger.error(f"종목 수집 실패: {e}")
            return []
    
    
    def _get_market_cap_ranked_stocks_fallback(self, max_count: int) -> List[Dict[str, Any]]:
        """KOSPI 마스터 파일에서 시가총액 순으로 종목 조회"""
        try:
            logger.info(f"🔍 KOSPI 마스터 파일에서 {max_count}개 종목 수집 시작")
            
            # ✨ KOSPI 마스터 파일 사용 (하드코딩 대신)
            import pandas as pd
            from pathlib import Path
            
            kospi_file = Path("kospi_code.xlsx")
            
            if not kospi_file.exists():
                logger.error(f"❌ KOSPI 마스터 파일을 찾을 수 없습니다: {kospi_file}")
                logger.info("💡 하드코딩된 폴백 리스트 사용")
                return self._get_hardcoded_fallback_stocks(max_count)
            
            # 엑셀 파일 읽기
            df = pd.read_excel(kospi_file)
            logger.info(f"✅ KOSPI 마스터 파일 로드: {len(df)}개 종목")
            
            # 시가총액으로 정렬 (내림차순)
            if '시가총액' in df.columns:
                df = df.sort_values('시가총액', ascending=False)
            else:
                logger.warning("⚠️ 시가총액 컬럼 없음, 원본 순서 사용")
            
            # 상위 max_count개 + 여유분 (일부 실패 대비)
            buffer_size = int(max_count * 1.5)  # 50% 여유
            df = df.head(buffer_size)
            
            # 종목코드 및 종목명 추출 (ETF/ETN 제외)
            major_stocks = []  # 종목코드 리스트
            stock_names = {}   # 종목코드 -> 종목명 매핑
            
            for _, row in df.iterrows():
                code = row.get('단축코드')
                if code and isinstance(code, str) and len(code) == 6:
                    # ETF/ETN 제외 (F로 시작)
                    if not (code.startswith('F') or code.startswith('Q')):
                        major_stocks.append(code)
                        name = row.get('한글명', '')
                        stock_names[code] = name  # 종목명 매핑 저장
                        
                        # 상위 3개 디버깅
                        if len(major_stocks) <= 3:
                            logger.debug(f"📝 {code}: '{name}' (타입: {type(name)})")
            
            logger.info(f"✅ 시가총액 순으로 {len(major_stocks)}개 종목코드 추출 (ETF/ETN 제외)")
            logger.debug(f"📝 stock_names 샘플: {dict(list(stock_names.items())[:3])}")
            
            # 중복 제거
            unique_stocks = list(dict.fromkeys(major_stocks))
            logger.info(f"🔍 중복 제거 후 종목 수: {len(unique_stocks)}개")
            
            # 이미 충분한 종목이 있으므로 추가 생성 불필요
            # KOSPI 마스터 파일에서 buffer_size만큼 가져왔으므로
            # max_count보다 많은 종목이 확보되어 있음
            
            stocks = []
            successful_count = 0
            target_count = min(max_count, len(unique_stocks))  # 실제 종목 수와 max_count 중 작은 값 사용
            
            # 500 오류 연속 발생 시 조기 중단을 위한 카운터
            consecutive_failures = 0
            max_consecutive_failures = 10  # 연속 10회 실패 시 중단
            
            for i, symbol in enumerate(unique_stocks):
                if successful_count >= target_count:
                    break
                
                # 무한루프 방지: max_count 초과 시 중단
                if len(stocks) >= max_count:
                    logger.info(f"🔍 max_count({max_count}) 도달로 종목 수집 중단")
                    break
                    
                # 연속 실패가 너무 많으면 조기 중단
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning(f"⚠️ 연속 {consecutive_failures}회 실패로 조기 중단. 현재까지 {successful_count}개 수집")
                    break
                    
                try:
                    self._rate_limit()
                    
                    # 개별 종목 정보 조회
                    stock_info = self.get_stock_price_info(symbol)
                    if stock_info and stock_info.get('market_cap', 0) > 0:
                        # 종목명 우선순위: 마스터 파일 → API → 종목코드
                        # (API가 종목코드를 반환하는 경우가 있으므로 마스터 파일 우선!)
                        api_name = stock_info.get('name', '')
                        master_name = stock_names.get(symbol, '')
                        
                        # API 종목명이 종목코드와 같으면 무시
                        if api_name == symbol:
                            api_name = ''
                        
                        # 우선순위: 마스터 파일 > API > 폴백
                        stock_name = master_name or api_name or f'종목{symbol}'
                        
                        # 디버깅 (상위 3개)
                        if successful_count < 3:
                            logger.debug(f"📝 {symbol}: API='{stock_info.get('name', '')}' 마스터='{master_name}' 최종='{stock_name}'")
                        
                        stocks.append({
                            'code': symbol,
                            'name': stock_name,  # ✨ 마스터 파일에서 종목명 가져오기!
                            'current_price': stock_info.get('current_price', 0),
                            'change_rate': stock_info.get('change_rate', 0),
                            'volume': stock_info.get('volume', 0),
                            'market_cap': stock_info.get('market_cap', 0),
                            'per': stock_info.get('per', 0),
                            'pbr': stock_info.get('pbr', 0),
                            'roe': stock_info.get('eps', 0) / stock_info.get('bps', 1) * 100 if stock_info.get('bps', 0) > 0 else 0,
                            'sector': stock_info.get('sector', '')
                        })
                        successful_count += 1
                        consecutive_failures = 0  # 성공 시 실패 카운터 리셋
                    
                    # 진행 상황 로그 (매 25개마다)
                    if (i + 1) % 25 == 0:
                        logger.info(f"🔍 진행률: {successful_count}/{target_count} ({successful_count/target_count*100:.1f}%)")
                        
                except Exception as e:
                    consecutive_failures += 1
                    logger.debug(f"종목 {symbol} 정보 조회 실패: {e}")
                    continue
            
            logger.info(f"🔍 최종 수집된 종목 수: {len(stocks)}")
            
            # 시가총액순으로 정렬
            stocks.sort(key=lambda x: x.get('market_cap', 0), reverse=True)
            
            return stocks
            
        except Exception as e:
            logger.error(f"시가총액 순 종목 목록 조회 중 오류: {e}")
            return []
    
    def _get_hardcoded_fallback_stocks(self, max_count: int) -> List[str]:
        """
        하드코딩된 주요 대형주 리스트 (최후의 폴백)
        KOSPI 마스터 파일도 없을 때만 사용
        """
        logger.warning(f"⚠️ 최후의 폴백: 하드코딩된 대형주 {max_count}개 사용")
        
        # 시가총액 상위 50개 대형주만 (최소한으로 제한)
        major_stocks = [
            '005930', '000660', '035420', '005380', '035720', '051910', '006400', '068270', '207940', '066570',
            '017670', '030200', '086280', '000810', '032830', '323410', '105560', '003670', '000270', '096770',
            '015760', '000720', '003550', '018260', '259960', '012330', '003490', '000990', '034730', '028260',
            '161890', '251270', '011200', '024110', '009150', '016360', '021240', '017940', '047050', '006260',
            '302440', '034220', '267250', '000100', '035250', '003520', '011070', '128940', '036570', '000120'
        ]
        
        return major_stocks[:max_count]
    
    def _get_fallback_stock_list(self) -> List[Dict[str, Any]]:
        """API 실패 시 사용할 기본 종목 리스트"""
        # 주요 대형주만 포함한 최소한의 폴백 리스트
        fallback_stocks = [
            {'code': '005930', 'name': '삼성전자', 'current_price': 0, 'market_cap': 0, 'per': 0, 'pbr': 0, 'roe': 0, 'sector': ''},
            {'code': '000660', 'name': 'SK하이닉스', 'current_price': 0, 'market_cap': 0, 'per': 0, 'pbr': 0, 'roe': 0, 'sector': ''},
            {'code': '035420', 'name': 'NAVER', 'current_price': 0, 'market_cap': 0, 'per': 0, 'pbr': 0, 'roe': 0, 'sector': ''},
            {'code': '005380', 'name': '현대차', 'current_price': 0, 'market_cap': 0, 'per': 0, 'pbr': 0, 'roe': 0, 'sector': ''},
            {'code': '035720', 'name': '카카오', 'current_price': 0, 'market_cap': 0, 'per': 0, 'pbr': 0, 'roe': 0, 'sector': ''},
            {'code': '051910', 'name': 'LG화학', 'current_price': 0, 'market_cap': 0, 'per': 0, 'pbr': 0, 'roe': 0, 'sector': ''},
            {'code': '006400', 'name': '삼성SDI', 'current_price': 0, 'market_cap': 0, 'per': 0, 'pbr': 0, 'roe': 0, 'sector': ''},
            {'code': '068270', 'name': '셀트리온', 'current_price': 0, 'market_cap': 0, 'per': 0, 'pbr': 0, 'roe': 0, 'sector': ''},
            {'code': '207940', 'name': '삼성바이오로직스', 'current_price': 0, 'market_cap': 0, 'per': 0, 'pbr': 0, 'roe': 0, 'sector': ''},
            {'code': '066570', 'name': 'LG전자', 'current_price': 0, 'market_cap': 0, 'per': 0, 'pbr': 0, 'roe': 0, 'sector': ''},
        ]
        return fallback_stocks
    
    def get_stock_price_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """주식 현재가 및 주요 투자지표를 조회합니다."""
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol}
        data = self._send_request(path, "FHKST01010100", params)
        
        if data and 'output' in data:
            output = data['output']
            # 종목명과 섹터명을 올바르게 분리
            stock_name = output.get('hts_kor_isnm', '')  # 종목명
            sector_name = output.get('bstp_kor_isnm', '')  # 업종명
            
            # 디버깅 로그 (처음 3개 종목만)
            if symbol in ['005930', '000660', '035420']:  # 주요 종목들만 로그
                logger.info(f"🔍 종목 {symbol}: 종목명='{stock_name}', 섹터명='{sector_name}'")
            
            # 종목명이 없으면 종목코드로 대체 (하지만 더 깔끔하게)
            if not stock_name or stock_name.strip() == '':
                # 주요 대형주 종목명 매핑 (정확한 종목명 제공)
                stock_name_mapping = {
                    '005930': '삼성전자', '000660': 'SK하이닉스', '035420': 'NAVER', '005380': '현대차', '035720': '카카오',
                    '051910': 'LG화학', '006400': '삼성SDI', '068270': '셀트리온', '207940': '삼성바이오로직스', '066570': 'LG전자',
                    '017670': 'SK텔레콤', '030200': 'KT', '086280': '현대글로비스', '000810': '삼성화재', '032830': '삼성생명',
                    '323410': '카카오뱅크', '105560': 'KB금융', '003670': '포스코홀딩스', '000270': '기아', '096770': 'SK이노베이션',
                    '015760': '한국전력', '000720': '현대건설', '003550': 'LG생활건강', '018260': '삼성에스디에스', '259960': '크래프톤',
                    '012330': '현대모비스', '003490': '대한항공', '000990': 'DB하이텍', '034730': 'SK', '028260': '삼성물산',
                    '161890': '한국전력공사', '251270': '넷마블', '011200': 'HMM', '024110': '기업은행', '009150': '삼성전기',
                    '016360': '삼성증권', '021240': '코웨이', '017940': 'E1', '047050': '포스코인터내셔널', '006260': 'LS',
                    '302440': 'SK바이오팜', '034220': 'LG디스플레이', '267250': 'HD현대', '000100': '유한양행', '035250': '강원랜드',
                    '003520': '영진약품', '011070': 'LG이노텍', '128940': '한미반도체', '036570': '엔씨소프트', '000120': 'CJ대한통운',
                    '011790': 'SKC', '090430': '아모레퍼시픽', '042660': '한화시스템', '139480': '이마트', '064350': '현대로템',
                    '009540': 'HD한국조선해양', '010130': '고려아연', '012450': '한화에어로스페이스', '009680': '모토닉', '004170': '신세계',
                    '006360': 'GS건설', '066970': '엘앤에프', '003410': '쌍용양회', '000060': '메리츠종금증권', '078930': 'GS',
                    '010950': 'S-Oil', '018880': '한온시스템', '003300': '하나투어', '004020': '현대제철', '001570': '금양',
                    '010140': '삼성전자', '004250': '삼성물산', '008770': '호텔신라', '010620': '현대미포조선', '004540': '깨끗한나라',
                    '000150': '두산에너빌리티', '001040': 'CJ', '012750': '에스원', '002790': '아모레퍼시픽',
                    '011780': '금호석유', '009200': '무림P&P', '010060': 'OCI', '000680': 'LS네트웍스', '010780': '아이에스동서',
                    '002380': '한독', '006800': '미래에셋대우', '001450': '현대해상', '003460': '유화', '003650': '미래에셋대우',
                    '004800': '효성', '005490': 'POSCO', '006840': 'AK홀딩스', '007070': 'GS리테일', '007340': '디티알유',
                    '008490': '서흥', '009780': '엘지전자', '010040': '한국내화', '010960': '한국조선해양', '014280': '금호석유',
                    '014820': '동원시스템즈', '016580': '동원산업', '017810': '풀무원', '018470': '조일알미늄', '019170': '신풍제약',
                    '024720': '콜마홀딩스', '025820': '이화전기', '026890': '디스플레이텍', '028050': '삼성엔지니어링', '036460': '한국가스공사',
                    '038540': '메리츠금융지주', '052690': '한전기술', '055550': '신한지주', '058470': '리노공업'
                }
                
                # 매핑에서 찾거나 종목코드 사용
                stock_name = stock_name_mapping.get(symbol, symbol)
            
            return {
                'symbol': symbol,
                'name': stock_name,  # 순수한 종목명만 사용
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
                'sector': sector_name,  # 업종명 (섹터명과 분리)
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