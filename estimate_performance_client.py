# estimate_performance_client.py
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from kis_token_manager import KISTokenManager
from estimate_performance_models import (
    EstimatePerformanceRequest,
    EstimatePerformanceResponse,
    StockBasicInfo,
    FinancialData,
    InvestmentIndicator,
    SettlementInfo,
    ProcessedEstimatePerformance
)

logger = logging.getLogger(__name__)


class EstimatePerformanceClient:
    """KIS API를 통해 국내주식 종목추정실적 데이터를 수집하는 클래스"""

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

    def _send_request(self, request_data: EstimatePerformanceRequest) -> Optional[EstimatePerformanceResponse]:
        """추정실적 API 요청을 전송합니다."""
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
            "SHT_CD": request_data.SHT_CD
        }

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/estimate-perform"
        
        try:
            logger.info(f"🔍 추정실적 API 요청: {request_data.SHT_CD}")
            
            response = self.session.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # API 응답 검증
            if data.get('rt_cd') != '0':
                logger.warning(f"⚠️ API 오류 ({request_data.tr_id}|{request_data.SHT_CD}): {data.get('msg1', '알 수 없는 오류')}")
                return None
            
            # 응답 데이터 파싱
            output1_data = data.get('output1', {})
            stock_basic_info = StockBasicInfo(
                sht_cd=output1_data.get('sht_cd', ''),
                item_kor_nm=output1_data.get('item_kor_nm', ''),
                name1=output1_data.get('name1', ''),
                name2=output1_data.get('name2', ''),
                estdate=output1_data.get('estdate', ''),
                rcmd_name=output1_data.get('rcmd_name', ''),
                capital=output1_data.get('capital', ''),
                forn_item_lmtrt=output1_data.get('forn_item_lmtrt', '')
            )
            
            # 추정손익계산서 데이터 (output2 - 6개월)
            output2_data = data.get('output2', [])
            financial_data_list = []
            for item in output2_data:
                financial_data_list.append(FinancialData(
                    data1=item.get('data1', ''),
                    data2=item.get('data2', ''),
                    data3=item.get('data3', ''),
                    data4=item.get('data4', ''),
                    data5=item.get('data5', '')
                ))
            
            # 투자지표 데이터 (output3 - 8개월)
            output3_data = data.get('output3', [])
            investment_indicator_list = []
            for item in output3_data:
                investment_indicator_list.append(InvestmentIndicator(
                    data1=item.get('data1', ''),
                    data2=item.get('data2', ''),
                    data3=item.get('data3', ''),
                    data4=item.get('data4', ''),
                    data5=item.get('data5', '')
                ))
            
            # 결산년월 정보 (output4)
            output4_data = data.get('output4', [])
            settlement_info_list = []
            for item in output4_data:
                settlement_info_list.append(SettlementInfo(
                    dt=item.get('dt', '')
                ))
            
            return EstimatePerformanceResponse(
                rt_cd=data.get('rt_cd', ''),
                msg_cd=data.get('msg_cd', ''),
                msg1=data.get('msg1', ''),
                output1=stock_basic_info,
                output2=financial_data_list,
                output3=investment_indicator_list,
                output4=settlement_info_list
            )
            
        except requests.RequestException as e:
            logger.error(f"❌ API 호출 실패 ({request_data.tr_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 데이터 파싱 오류: {e}")
            return None

    def get_estimate_performance(self, symbol: str) -> Optional[ProcessedEstimatePerformance]:
        """
        특정 종목의 추정실적 데이터를 조회합니다.
        
        Args:
            symbol: 종목코드 (예: "005930")
            
        Returns:
            ProcessedEstimatePerformance 객체 또는 None
        """
        # 요청 데이터 생성
        request_data = EstimatePerformanceRequest(
            authorization=f"Bearer {self.token_manager.get_valid_token()}",
            appkey=self.token_manager.app_key,
            appsecret=self.token_manager.app_secret,
            SHT_CD=symbol
        )
        
        # API 호출
        response = self._send_request(request_data)
        
        if not response:
            logger.warning(f"⚠️ {symbol} 종목의 추정실적 데이터가 없습니다.")
            return None
        
        # 데이터 변환
        try:
            processed_data = ProcessedEstimatePerformance.from_raw_data(response)
            logger.info(f"✅ {symbol} 종목 추정실적 데이터 조회 완료 (품질점수: {processed_data.data_quality_score:.2f})")
            return processed_data
        except Exception as e:
            logger.error(f"❌ {symbol} 종목 데이터 처리 실패: {e}")
            return None

    def get_multiple_stocks_estimates(self, symbols: List[str]) -> Dict[str, ProcessedEstimatePerformance]:
        """
        여러 종목의 추정실적 데이터를 일괄 조회합니다.
        
        Args:
            symbols: 종목코드 리스트
            
        Returns:
            {종목코드: ProcessedEstimatePerformance} 딕셔너리
        """
        results = {}
        
        for symbol in symbols:
            try:
                estimate_data = self.get_estimate_performance(symbol)
                results[symbol] = estimate_data
                time.sleep(0.2)  # API 호출 간격 조절
            except Exception as e:
                logger.error(f"❌ {symbol} 종목 추정실적 조회 실패: {e}")
                results[symbol] = None
        
        return results

    def get_estimate_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        특정 종목의 추정실적 요약 정보를 조회합니다.
        
        Args:
            symbol: 종목코드
            
        Returns:
            요약 정보 딕셔너리 또는 None
        """
        processed_data = self.get_estimate_performance(symbol)
        
        if not processed_data:
            return None
        
        from estimate_performance_models import EstimatePerformanceSummary
        summary = EstimatePerformanceSummary.from_processed_data(processed_data)
        
        return {
            'symbol': summary.symbol,
            'name': summary.name,
            'current_price': summary.current_price,
            'change_rate': summary.change_rate,
            'latest_revenue': summary.latest_revenue,
            'latest_revenue_growth': summary.latest_revenue_growth,
            'latest_operating_profit': summary.latest_operating_profit,
            'latest_operating_profit_growth': summary.latest_operating_profit_growth,
            'latest_net_profit': summary.latest_net_profit,
            'latest_net_profit_growth': summary.latest_net_profit_growth,
            'latest_eps': summary.latest_eps,
            'latest_per': summary.latest_per,
            'latest_roe': summary.latest_roe,
            'latest_ev_ebitda': summary.latest_ev_ebitda,
            'revenue_trend': summary.revenue_trend,
            'profit_trend': summary.profit_trend,
            'eps_trend': summary.eps_trend,
            'data_quality_score': summary.data_quality_score,
            'latest_update_date': summary.latest_update_date
        }

    def get_high_quality_estimates(
        self, 
        symbols: List[str], 
        min_quality_score: float = 0.7
    ) -> Dict[str, ProcessedEstimatePerformance]:
        """
        데이터 품질이 높은 추정실적 데이터만 조회합니다.
        
        Args:
            symbols: 종목코드 리스트
            min_quality_score: 최소 품질 점수 (0-1)
            
        Returns:
            품질이 높은 추정실적 데이터 딕셔너리
        """
        all_estimates = self.get_multiple_stocks_estimates(symbols)
        
        high_quality_estimates = {}
        for symbol, estimate_data in all_estimates.items():
            if estimate_data and estimate_data.data_quality_score >= min_quality_score:
                high_quality_estimates[symbol] = estimate_data
        
        logger.info(f"✅ 고품질 추정실적 데이터: {len(high_quality_estimates)}/{len(symbols)}개 종목")
        return high_quality_estimates

    def get_estimate_trends(
        self, 
        symbol: str, 
        periods: int = 6
    ) -> Optional[Dict[str, Any]]:
        """
        특정 종목의 추정실적 트렌드를 분석합니다.
        
        Args:
            symbol: 종목코드
            periods: 분석할 기간 수
            
        Returns:
            트렌드 분석 결과 또는 None
        """
        processed_data = self.get_estimate_performance(symbol)
        
        if not processed_data:
            return None
        
        # 각 지표별 트렌드 분석
        trends = {}
        
        # 매출액 트렌드
        if processed_data.revenue_data:
            revenue_trend = self._calculate_trend(processed_data.revenue_data[:periods])
            trends['revenue'] = revenue_trend
        
        # 영업이익 트렌드
        if processed_data.operating_profit_data:
            profit_trend = self._calculate_trend(processed_data.operating_profit_data[:periods])
            trends['operating_profit'] = profit_trend
        
        # 순이익 트렌드
        if processed_data.net_profit_data:
            net_profit_trend = self._calculate_trend(processed_data.net_profit_data[:periods])
            trends['net_profit'] = net_profit_trend
        
        # EPS 트렌드
        if processed_data.eps_data:
            eps_trend = self._calculate_trend(processed_data.eps_data[:periods])
            trends['eps'] = eps_trend
        
        # ROE 트렌드
        if processed_data.roe_data:
            roe_trend = self._calculate_trend(processed_data.roe_data[:periods])
            trends['roe'] = roe_trend
        
        return {
            'symbol': symbol,
            'name': processed_data.name,
            'trends': trends,
            'data_quality_score': processed_data.data_quality_score,
            'analysis_periods': periods
        }

    def _calculate_trend(self, data: List[float]) -> Dict[str, Any]:
        """데이터 트렌드를 계산합니다."""
        if not data or len(data) < 2:
            return {'direction': '데이터부족', 'slope': 0, 'volatility': 0}
        
        # 0이 아닌 값들만 추출
        valid_data = [val for val in data if val != 0]
        if len(valid_data) < 2:
            return {'direction': '데이터부족', 'slope': 0, 'volatility': 0}
        
        # 최신 2개 값으로 방향 판단
        recent_2 = valid_data[:2]
        if recent_2[0] > recent_2[1]:
            direction = "상승"
        elif recent_2[0] < recent_2[1]:
            direction = "하락"
        else:
            direction = "보합"
        
        # 기울기 계산 (간단한 선형 회귀)
        n = len(valid_data)
        if n >= 2:
            x_values = list(range(n))
            y_values = valid_data
            
            # 기울기 계산
            sum_x = sum(x_values)
            sum_y = sum(y_values)
            sum_xy = sum(x * y for x, y in zip(x_values, y_values))
            sum_x2 = sum(x * x for x in x_values)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
        else:
            slope = 0
        
        # 변동성 계산 (표준편차)
        if len(valid_data) > 1:
            mean_val = sum(valid_data) / len(valid_data)
            variance = sum((val - mean_val) ** 2 for val in valid_data) / len(valid_data)
            volatility = variance ** 0.5
        else:
            volatility = 0
        
        return {
            'direction': direction,
            'slope': slope,
            'volatility': volatility,
            'data_points': len(valid_data)
        }
