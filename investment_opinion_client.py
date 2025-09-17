# investment_opinion_client.py
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from kis_token_manager import KISTokenManager
from investment_opinion_models import (
    InvestmentOpinionRequest,
    InvestmentOpinionResponse,
    InvestmentOpinionData,
    ProcessedInvestmentOpinion
)

logger = logging.getLogger(__name__)


class InvestmentOpinionClient:
    """KIS API를 통해 국내주식 종목투자의견 데이터를 수집하는 클래스"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.token_manager = KISTokenManager(config_path)
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.session = requests.Session()
        self.last_request_time = 0
        self.request_interval = 0.12  # API TPS 제한 준수

    def _rate_limit(self):
        """API 요청 속도를 제어합니다."""
        elapsed_time = time.time() - self.last_request_time
        if elapsed_time < self.request_interval:
            time.sleep(self.request_interval - elapsed_time)
        self.last_request_time = time.time()

    def _send_request(self, request_data: InvestmentOpinionRequest) -> Optional[InvestmentOpinionResponse]:
        """투자의견 API 요청을 전송합니다."""
        self._rate_limit()
        
        # 헤더 구성
        token = self.token_manager.get_valid_token()
        headers = {
            "content-type": request_data.content_type,
            "authorization": f"Bearer {token}",
            "appkey": request_data.appkey,
            "appsecret": request_data.appsecret,
            "tr_id": request_data.tr_id,
            "custtype": request_data.custtype
        }
        
        # 선택적 헤더 추가
        if request_data.personalseckey:
            headers["personalseckey"] = request_data.personalseckey
        if request_data.tr_cont:
            headers["tr_cont"] = request_data.tr_cont
        if request_data.seq_no:
            headers["seq_no"] = request_data.seq_no
        if request_data.mac_address:
            headers["mac_address"] = request_data.mac_address
        if request_data.phone_number:
            headers["phone_number"] = request_data.phone_number
        if request_data.ip_addr:
            headers["ip_addr"] = request_data.ip_addr
        if request_data.gt_uid:
            headers["gt_uid"] = request_data.gt_uid

        # 쿼리 파라미터 구성
        params = {
            "FID_COND_MRKT_DIV_CODE": request_data.FID_COND_MRKT_DIV_CODE,
            "FID_COND_SCR_DIV_CODE": request_data.FID_COND_SCR_DIV_CODE,
            "FID_INPUT_ISCD": request_data.FID_INPUT_ISCD,
            "FID_INPUT_DATE_1": request_data.FID_INPUT_DATE_1,
            "FID_INPUT_DATE_2": request_data.FID_INPUT_DATE_2
        }

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/invest-opinion"
        
        try:
            logger.info(f"🔍 투자의견 API 요청: {request_data.FID_INPUT_ISCD}, 기간: {request_data.FID_INPUT_DATE_1} ~ {request_data.FID_INPUT_DATE_2}")
            
            response = self.session.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # API 응답 검증
            if data.get('rt_cd') != '0':
                logger.warning(f"⚠️ API 오류 ({request_data.tr_id}|{request_data.FID_INPUT_ISCD}): {data.get('msg1', '알 수 없는 오류')}")
                return None
            
            # 응답 데이터 파싱
            output_data = []
            if 'output' in data and data['output']:
                for item in data['output']:
                    output_data.append(InvestmentOpinionData(
                        stck_bsop_date=item.get('stck_bsop_date', ''),
                        invt_opnn=item.get('invt_opnn', ''),
                        invt_opnn_cls_code=item.get('invt_opnn_cls_code', ''),
                        rgbf_invt_opnn=item.get('rgbf_invt_opnn', ''),
                        rgbf_invt_opnn_cls_code=item.get('rgbf_invt_opnn_cls_code', ''),
                        mbcr_name=item.get('mbcr_name', ''),
                        hts_goal_prc=item.get('hts_goal_prc', ''),
                        stck_prdy_clpr=item.get('stck_prdy_clpr', ''),
                        stck_nday_esdg=item.get('stck_nday_esdg', ''),
                        nday_dprt=item.get('nday_dprt', ''),
                        stft_esdg=item.get('stft_esdg', ''),
                        dprt=item.get('dprt', '')
                    ))
            
            return InvestmentOpinionResponse(
                rt_cd=data.get('rt_cd', ''),
                msg_cd=data.get('msg_cd', ''),
                msg1=data.get('msg1', ''),
                output=output_data
            )
            
        except requests.RequestException as e:
            logger.error(f"❌ API 호출 실패 ({request_data.tr_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 데이터 파싱 오류: {e}")
            return None

    def get_investment_opinions(
        self, 
        symbol: str, 
        start_date: str = None, 
        end_date: str = None,
        days_back: int = 30
    ) -> List[ProcessedInvestmentOpinion]:
        """
        특정 종목의 투자의견 데이터를 조회합니다.
        
        Args:
            symbol: 종목코드 (예: "005930")
            start_date: 시작일 (YYYYMMDD 형식, None이면 days_back 사용)
            end_date: 종료일 (YYYYMMDD 형식, None이면 오늘)
            days_back: 과거 몇 일까지 조회할지 (start_date가 None일 때만 사용)
            
        Returns:
            ProcessedInvestmentOpinion 리스트
        """
        # 날짜 설정
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        if start_date is None:
            start_date_obj = datetime.now() - timedelta(days=days_back)
            start_date = start_date_obj.strftime('%Y%m%d')
        
        # 요청 데이터 생성
        request_data = InvestmentOpinionRequest(
            authorization=f"Bearer {self.token_manager.get_valid_token()}",
            appkey=self.token_manager.app_key,
            appsecret=self.token_manager.app_secret,
            FID_INPUT_ISCD=symbol,
            FID_INPUT_DATE_1=start_date,
            FID_INPUT_DATE_2=end_date
        )
        
        # API 호출
        response = self._send_request(request_data)
        
        if not response or not response.output:
            logger.warning(f"⚠️ {symbol} 종목의 투자의견 데이터가 없습니다.")
            return []
        
        # 데이터 변환
        processed_opinions = []
        for raw_data in response.output:
            processed_opinions.append(
                ProcessedInvestmentOpinion.from_raw_data(symbol, raw_data)
            )
        
        logger.info(f"✅ {symbol} 종목 투자의견 {len(processed_opinions)}건 조회 완료")
        return processed_opinions

    def get_multiple_stocks_opinions(
        self, 
        symbols: List[str], 
        start_date: str = None, 
        end_date: str = None,
        days_back: int = 30
    ) -> Dict[str, List[ProcessedInvestmentOpinion]]:
        """
        여러 종목의 투자의견 데이터를 일괄 조회합니다.
        
        Args:
            symbols: 종목코드 리스트
            start_date: 시작일 (YYYYMMDD 형식)
            end_date: 종료일 (YYYYMMDD 형식)
            days_back: 과거 몇 일까지 조회할지
            
        Returns:
            {종목코드: ProcessedInvestmentOpinion 리스트} 딕셔너리
        """
        results = {}
        
        for symbol in symbols:
            try:
                opinions = self.get_investment_opinions(symbol, start_date, end_date, days_back)
                results[symbol] = opinions
                time.sleep(0.2)  # API 호출 간격 조절
            except Exception as e:
                logger.error(f"❌ {symbol} 종목 투자의견 조회 실패: {e}")
                results[symbol] = []
        
        return results

    def get_recent_opinions(
        self, 
        symbol: str, 
        limit: int = 10
    ) -> List[ProcessedInvestmentOpinion]:
        """
        최근 투자의견만 조회합니다.
        
        Args:
            symbol: 종목코드
            limit: 조회할 의견 수
            
        Returns:
            최근 투자의견 리스트
        """
        opinions = self.get_investment_opinions(symbol, days_back=90)  # 3개월간 조회
        
        # 날짜순 정렬 후 최근 것만 반환
        opinions.sort(key=lambda x: x.business_date, reverse=True)
        return opinions[:limit]

    def get_opinion_changes(
        self, 
        symbol: str, 
        days_back: int = 30
    ) -> List[ProcessedInvestmentOpinion]:
        """
        투자의견이 변경된 경우만 조회합니다.
        
        Args:
            symbol: 종목코드
            days_back: 과거 몇 일까지 조회할지
            
        Returns:
            의견이 변경된 투자의견 리스트
        """
        all_opinions = self.get_investment_opinions(symbol, days_back=days_back)
        
        # 의견이 변경된 것만 필터링
        changed_opinions = [
            opinion for opinion in all_opinions 
            if opinion.opinion_change == "변경"
        ]
        
        return changed_opinions

    def get_brokerage_summary(
        self, 
        symbol: str, 
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        증권사별 투자의견 요약을 조회합니다.
        
        Args:
            symbol: 종목코드
            days_back: 과거 몇 일까지 조회할지
            
        Returns:
            증권사별 요약 정보
        """
        opinions = self.get_investment_opinions(symbol, days_back=days_back)
        
        if not opinions:
            return {}
        
        # 증권사별 그룹화
        brokerage_summary = {}
        
        for opinion in opinions:
            firm = opinion.brokerage_firm
            if firm not in brokerage_summary:
                brokerage_summary[firm] = {
                    'count': 0,
                    'latest_opinion': '',
                    'latest_date': '',
                    'target_prices': [],
                    'opinions': []
                }
            
            summary = brokerage_summary[firm]
            summary['count'] += 1
            summary['opinions'].append(opinion.current_opinion)
            
            if opinion.business_date > summary['latest_date']:
                summary['latest_date'] = opinion.business_date
                summary['latest_opinion'] = opinion.current_opinion
            
            if opinion.target_price > 0:
                summary['target_prices'].append(opinion.target_price)
        
        # 평균 목표가 계산
        for firm, summary in brokerage_summary.items():
            if summary['target_prices']:
                summary['avg_target_price'] = sum(summary['target_prices']) / len(summary['target_prices'])
            else:
                summary['avg_target_price'] = 0
        
        return brokerage_summary

