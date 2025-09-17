# estimate_performance_models.py
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EstimatePerformanceRequest:
    """국내주식 종목추정실적 API 요청 데이터 클래스"""
    
    # Header 정보
    content_type: str = "application/json; charset=utf-8"
    authorization: str = ""  # Bearer 토큰
    appkey: str = ""
    appsecret: str = ""
    personalseckey: Optional[str] = None  # 고객식별키 (법인 필수)
    tr_id: str = "HHKST668300C0"
    tr_cont: Optional[str] = None  # 연속 거래 여부
    custtype: str = "P"  # B: 법인, P: 개인
    seq_no: Optional[str] = None  # 일련번호 (법인 필수)
    mac_address: Optional[str] = None  # 맥주소
    phone_number: Optional[str] = None  # 핸드폰번호 (법인 필수)
    ip_addr: Optional[str] = None  # 접속 단말 공인 IP (법인 필수)
    gt_uid: Optional[str] = None  # Global UID (법인 전용)
    
    # Query Parameter 정보
    SHT_CD: str = ""  # 종목코드


@dataclass
class EstimatePerformanceResponseHeader:
    """국내주식 종목추정실적 API 응답 헤더"""
    content_type: str
    tr_id: str
    tr_cont: Optional[str] = None
    gt_uid: Optional[str] = None


@dataclass
class StockBasicInfo:
    """주식 기본 정보"""
    sht_cd: str  # ELW단축종목코드
    item_kor_nm: str  # HTS한글종목명
    name1: str  # ELW현재가
    name2: str  # 전일대비
    estdate: str  # 전일대비부호
    rcmd_name: str  # 전일대비율
    capital: str  # 누적거래량
    forn_item_lmtrt: str  # 행사가


@dataclass
class FinancialData:
    """재무 데이터 (6개월 배열)"""
    data1: str  # DATA1
    data2: str  # DATA2
    data3: str  # DATA3
    data4: str  # DATA4
    data5: str  # DATA5


@dataclass
class InvestmentIndicator:
    """투자지표 (8개월 배열)"""
    data1: str  # DATA1
    data2: str  # DATA2
    data3: str  # DATA3
    data4: str  # DATA4
    data5: str  # DATA5


@dataclass
class SettlementInfo:
    """결산 정보"""
    dt: str  # 결산년월


@dataclass
class EstimatePerformanceResponse:
    """국내주식 종목추정실적 API 응답 데이터 클래스"""
    rt_cd: str  # 성공 실패 여부
    msg_cd: str  # 응답코드
    msg1: str  # 응답메세지
    output1: StockBasicInfo  # 주식 기본 정보
    output2: List[FinancialData] = field(default_factory=list)  # 추정손익계산서 (6개월)
    output3: List[InvestmentIndicator] = field(default_factory=list)  # 투자지표 (8개월)
    output4: List[SettlementInfo] = field(default_factory=list)  # 결산년월 정보


@dataclass
class ProcessedEstimatePerformance:
    """처리된 추정실적 데이터 (분석용)"""
    symbol: str
    name: str
    current_price: float
    change_price: float
    change_rate: float
    volume: float
    
    # 추정손익계산서 (6개월)
    revenue_data: List[float]  # 매출액
    revenue_growth_data: List[float]  # 매출액증감율
    operating_profit_data: List[float]  # 영업이익
    operating_profit_growth_data: List[float]  # 영업이익증감율
    net_profit_data: List[float]  # 순이익
    net_profit_growth_data: List[float]  # 순이익증감율
    
    # 투자지표 (8개월)
    ebitda_data: List[float]  # EBITDA(십억원)
    eps_data: List[float]  # EPS(원)
    eps_growth_data: List[float]  # EPS 증감율(0.1%)
    per_data: List[float]  # PER(배, 0.1%)
    ev_ebitda_data: List[float]  # EV/EBITDA(배, 0.1)
    roe_data: List[float]  # ROE(0.1%)
    debt_ratio_data: List[float]  # 부채비율(0.1%)
    interest_coverage_data: List[float]  # 이자보상배율(0.1%)
    
    # 결산년월 정보
    settlement_periods: List[str]
    
    # 분석용 메타데이터
    data_quality_score: float  # 데이터 품질 점수 (0-1)
    latest_update_date: str  # 최근 업데이트 날짜

    @classmethod
    def from_raw_data(cls, raw_response: EstimatePerformanceResponse) -> 'ProcessedEstimatePerformance':
        """원시 데이터로부터 처리된 추정실적 객체를 생성합니다."""
        
        def safe_float(value: str, default: float = 0.0) -> float:
            """안전하게 float으로 변환"""
            try:
                return float(str(value).replace(',', '')) if value and value != '' else default
            except (ValueError, TypeError):
                return default
        
        def safe_float_list(data_list: List[str]) -> List[float]:
            """문자열 리스트를 float 리스트로 변환"""
            return [safe_float(item) for item in data_list]
        
        # 기본 정보 처리
        basic_info = raw_response.output1
        symbol = basic_info.sht_cd
        name = basic_info.item_kor_nm
        current_price = safe_float(basic_info.name1)
        change_price = safe_float(basic_info.name2)
        change_rate = safe_float(basic_info.rcmd_name)
        volume = safe_float(basic_info.capital)
        
        # 추정손익계산서 데이터 처리 (output2 - 6개월)
        revenue_data = []
        revenue_growth_data = []
        operating_profit_data = []
        operating_profit_growth_data = []
        net_profit_data = []
        net_profit_growth_data = []
        
        if raw_response.output2:
            # 6개월 데이터를 각 지표별로 분리
            for i, data in enumerate(raw_response.output2[:6]):  # 최대 6개월
                data_list = [data.data1, data.data2, data.data3, data.data4, data.data5]
                
                if i == 0:  # 매출액
                    revenue_data = safe_float_list(data_list)
                elif i == 1:  # 매출액증감율
                    revenue_growth_data = safe_float_list(data_list)
                elif i == 2:  # 영업이익
                    operating_profit_data = safe_float_list(data_list)
                elif i == 3:  # 영업이익증감율
                    operating_profit_growth_data = safe_float_list(data_list)
                elif i == 4:  # 순이익
                    net_profit_data = safe_float_list(data_list)
                elif i == 5:  # 순이익증감율
                    net_profit_growth_data = safe_float_list(data_list)
        
        # 투자지표 데이터 처리 (output3 - 8개월)
        ebitda_data = []
        eps_data = []
        eps_growth_data = []
        per_data = []
        ev_ebitda_data = []
        roe_data = []
        debt_ratio_data = []
        interest_coverage_data = []
        
        if raw_response.output3:
            # 8개월 데이터를 각 지표별로 분리
            for i, data in enumerate(raw_response.output3[:8]):  # 최대 8개월
                data_list = [data.data1, data.data2, data.data3, data.data4, data.data5]
                
                if i == 0:  # EBITDA(십억원)
                    ebitda_data = safe_float_list(data_list)
                elif i == 1:  # EPS(원)
                    eps_data = safe_float_list(data_list)
                elif i == 2:  # EPS 증감율(0.1%)
                    eps_growth_data = safe_float_list(data_list)
                elif i == 3:  # PER(배, 0.1%)
                    per_data = safe_float_list(data_list)
                elif i == 4:  # EV/EBITDA(배, 0.1)
                    ev_ebitda_data = safe_float_list(data_list)
                elif i == 5:  # ROE(0.1%)
                    roe_data = safe_float_list(data_list)
                elif i == 6:  # 부채비율(0.1%)
                    debt_ratio_data = safe_float_list(data_list)
                elif i == 7:  # 이자보상배율(0.1%)
                    interest_coverage_data = safe_float_list(data_list)
        
        # 결산년월 정보
        settlement_periods = [info.dt for info in raw_response.output4] if raw_response.output4 else []
        
        # 데이터 품질 점수 계산
        data_quality_score = cls._calculate_data_quality(
            revenue_data, operating_profit_data, net_profit_data,
            eps_data, per_data, roe_data
        )
        
        # 최근 업데이트 날짜
        latest_update_date = settlement_periods[0] if settlement_periods else ""
        
        return cls(
            symbol=symbol,
            name=name,
            current_price=current_price,
            change_price=change_price,
            change_rate=change_rate,
            volume=volume,
            revenue_data=revenue_data,
            revenue_growth_data=revenue_growth_data,
            operating_profit_data=operating_profit_data,
            operating_profit_growth_data=operating_profit_growth_data,
            net_profit_data=net_profit_data,
            net_profit_growth_data=net_profit_growth_data,
            ebitda_data=ebitda_data,
            eps_data=eps_data,
            eps_growth_data=eps_growth_data,
            per_data=per_data,
            ev_ebitda_data=ev_ebitda_data,
            roe_data=roe_data,
            debt_ratio_data=debt_ratio_data,
            interest_coverage_data=interest_coverage_data,
            settlement_periods=settlement_periods,
            data_quality_score=data_quality_score,
            latest_update_date=latest_update_date
        )
    
    @staticmethod
    def _calculate_data_quality(
        revenue_data: List[float],
        operating_profit_data: List[float],
        net_profit_data: List[float],
        eps_data: List[float],
        per_data: List[float],
        roe_data: List[float]
    ) -> float:
        """데이터 품질 점수를 계산합니다 (0-1)."""
        
        # 각 지표별 데이터 존재 여부 확인
        indicators = [
            revenue_data, operating_profit_data, net_profit_data,
            eps_data, per_data, roe_data
        ]
        
        total_indicators = len(indicators)
        valid_indicators = 0
        
        for indicator_data in indicators:
            # 데이터가 존재하고 0이 아닌 값이 있는지 확인
            if indicator_data and any(val != 0 for val in indicator_data):
                valid_indicators += 1
        
        # 데이터 완성도 계산
        completion_score = valid_indicators / total_indicators if total_indicators > 0 else 0
        
        # 데이터 일관성 확인 (극단적인 값이 있는지)
        consistency_score = 1.0
        for indicator_data in indicators:
            if indicator_data and len(indicator_data) > 1:
                # 극단적인 값 체크 (예: 0이 아닌데 갑자기 매우 큰 값)
                non_zero_values = [val for val in indicator_data if val != 0]
                if len(non_zero_values) > 1:
                    max_val = max(non_zero_values)
                    min_val = min(non_zero_values)
                    if max_val > 0 and min_val > 0:
                        ratio = max_val / min_val
                        if ratio > 1000:  # 극단적인 비율
                            consistency_score *= 0.8
        
        return (completion_score * 0.7 + consistency_score * 0.3)


@dataclass
class EstimatePerformanceSummary:
    """추정실적 요약 정보"""
    symbol: str
    name: str
    current_price: float
    change_rate: float
    
    # 최신 추정 데이터
    latest_revenue: float
    latest_revenue_growth: float
    latest_operating_profit: float
    latest_operating_profit_growth: float
    latest_net_profit: float
    latest_net_profit_growth: float
    
    # 투자지표
    latest_eps: float
    latest_per: float
    latest_roe: float
    latest_ev_ebitda: float
    
    # 트렌드 분석
    revenue_trend: str  # 상승/하락/보합
    profit_trend: str  # 상승/하락/보합
    eps_trend: str  # 상승/하락/보합
    
    # 데이터 품질
    data_quality_score: float
    latest_update_date: str
    
    @classmethod
    def from_processed_data(cls, processed_data: ProcessedEstimatePerformance) -> 'EstimatePerformanceSummary':
        """처리된 데이터로부터 요약 정보를 생성합니다."""
        
        # 최신 데이터 추출 (첫 번째 데이터가 최신)
        latest_revenue = processed_data.revenue_data[0] if processed_data.revenue_data else 0
        latest_revenue_growth = processed_data.revenue_growth_data[0] if processed_data.revenue_growth_data else 0
        latest_operating_profit = processed_data.operating_profit_data[0] if processed_data.operating_profit_data else 0
        latest_operating_profit_growth = processed_data.operating_profit_growth_data[0] if processed_data.operating_profit_growth_data else 0
        latest_net_profit = processed_data.net_profit_data[0] if processed_data.net_profit_data else 0
        latest_net_profit_growth = processed_data.net_profit_growth_data[0] if processed_data.net_profit_growth_data else 0
        latest_eps = processed_data.eps_data[0] if processed_data.eps_data else 0
        latest_per = processed_data.per_data[0] if processed_data.per_data else 0
        latest_roe = processed_data.roe_data[0] if processed_data.roe_data else 0
        latest_ev_ebitda = processed_data.ev_ebitda_data[0] if processed_data.ev_ebitda_data else 0
        
        # 트렌드 분석
        revenue_trend = cls._analyze_trend(processed_data.revenue_data)
        profit_trend = cls._analyze_trend(processed_data.operating_profit_data)
        eps_trend = cls._analyze_trend(processed_data.eps_data)
        
        return cls(
            symbol=processed_data.symbol,
            name=processed_data.name,
            current_price=processed_data.current_price,
            change_rate=processed_data.change_rate,
            latest_revenue=latest_revenue,
            latest_revenue_growth=latest_revenue_growth,
            latest_operating_profit=latest_operating_profit,
            latest_operating_profit_growth=latest_operating_profit_growth,
            latest_net_profit=latest_net_profit,
            latest_net_profit_growth=latest_net_profit_growth,
            latest_eps=latest_eps,
            latest_per=latest_per,
            latest_roe=latest_roe,
            latest_ev_ebitda=latest_ev_ebitda,
            revenue_trend=revenue_trend,
            profit_trend=profit_trend,
            eps_trend=eps_trend,
            data_quality_score=processed_data.data_quality_score,
            latest_update_date=processed_data.latest_update_date
        )
    
    @staticmethod
    def _analyze_trend(data: List[float]) -> str:
        """데이터 트렌드를 분석합니다."""
        if not data or len(data) < 2:
            return "데이터부족"
        
        # 0이 아닌 값들만 추출
        valid_data = [val for val in data if val != 0]
        if len(valid_data) < 2:
            return "데이터부족"
        
        # 최신 2개 값으로 트렌드 판단
        recent_2 = valid_data[:2]
        if recent_2[0] > recent_2[1]:
            return "상승"
        elif recent_2[0] < recent_2[1]:
            return "하락"
        else:
            return "보합"
