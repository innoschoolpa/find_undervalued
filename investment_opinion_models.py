# investment_opinion_models.py
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class InvestmentOpinionRequest:
    """국내주식 종목투자의견 API 요청 데이터 클래스"""
    
    # Header 정보
    content_type: str = "application/json; charset=utf-8"
    authorization: str = ""  # Bearer 토큰
    appkey: str = ""
    appsecret: str = ""
    personalseckey: Optional[str] = None  # 고객식별키 (법인 필수)
    tr_id: str = "FHKST663300C0"
    tr_cont: Optional[str] = None  # 연속 거래 여부
    custtype: str = "P"  # B: 법인, P: 개인
    seq_no: Optional[str] = None  # 일련번호 (법인 필수)
    mac_address: Optional[str] = None  # 맥주소
    phone_number: Optional[str] = None  # 핸드폰번호 (법인 필수)
    ip_addr: Optional[str] = None  # 접속 단말 공인 IP (법인 필수)
    gt_uid: Optional[str] = None  # Global UID (법인 전용)
    
    # Query Parameter 정보
    FID_COND_MRKT_DIV_CODE: str = "J"  # 조건시장분류코드
    FID_COND_SCR_DIV_CODE: str = "16633"  # 조건화면분류코드 (Primary key)
    FID_INPUT_ISCD: str = ""  # 입력종목코드
    FID_INPUT_DATE_1: str = ""  # 입력날짜1 (이후 ~)
    FID_INPUT_DATE_2: str = ""  # 입력날짜2 (~ 이전)


@dataclass
class InvestmentOpinionResponseHeader:
    """국내주식 종목투자의견 API 응답 헤더"""
    content_type: str
    tr_id: str
    tr_cont: Optional[str] = None
    gt_uid: Optional[str] = None


@dataclass
class InvestmentOpinionData:
    """개별 투자의견 데이터"""
    stck_bsop_date: str  # 주식영업일자
    invt_opnn: str  # 투자의견
    invt_opnn_cls_code: str  # 투자의견구분코드
    rgbf_invt_opnn: str  # 직전투자의견
    rgbf_invt_opnn_cls_code: str  # 직전투자의견구분코드
    mbcr_name: str  # 회원사명
    hts_goal_prc: str  # HTS목표가격
    stck_prdy_clpr: str  # 주식전일종가
    stck_nday_esdg: str  # 주식N일괴리도
    nday_dprt: str  # N일괴리율
    stft_esdg: str  # 주식선물괴리도
    dprt: str  # 괴리율


@dataclass
class InvestmentOpinionResponse:
    """국내주식 종목투자의견 API 응답 데이터 클래스"""
    rt_cd: str  # 성공 실패 여부
    msg_cd: str  # 응답코드
    msg1: str  # 응답메세지
    output: List[InvestmentOpinionData] = field(default_factory=list)  # 응답상세


@dataclass
class ProcessedInvestmentOpinion:
    """처리된 투자의견 데이터 (분석용)"""
    symbol: str
    business_date: str  # 영업일자
    current_opinion: str  # 현재 투자의견
    previous_opinion: str  # 직전 투자의견
    opinion_change: str  # 의견 변경 여부
    brokerage_firm: str  # 증권사명
    target_price: float  # 목표가격
    previous_close: float  # 전일종가
    price_target_upside: float  # 목표가 대비 상승률
    n_day_deviation: float  # N일 괴리도
    n_day_deviation_rate: float  # N일 괴리율
    futures_deviation: float  # 선물괴리도
    deviation_rate: float  # 괴리율
    opinion_code: str  # 투자의견구분코드
    previous_opinion_code: str  # 직전투자의견구분코드

    @classmethod
    def from_raw_data(cls, symbol: str, raw_data: InvestmentOpinionData) -> 'ProcessedInvestmentOpinion':
        """원시 데이터로부터 처리된 투자의견 객체를 생성합니다."""
        
        def safe_float(value: str, default: float = 0.0) -> float:
            """안전하게 float으로 변환"""
            try:
                return float(str(value).replace(',', '')) if value and value != '' else default
            except (ValueError, TypeError):
                return default
        
        target_price = safe_float(raw_data.hts_goal_prc)
        previous_close = safe_float(raw_data.stck_prdy_clpr)
        
        # 목표가 대비 상승률 계산
        price_target_upside = ((target_price - previous_close) / previous_close * 100) if previous_close > 0 else 0
        
        # 의견 변경 여부 판단
        opinion_change = "변경" if raw_data.invt_opnn != raw_data.rgbf_invt_opnn else "유지"
        
        return cls(
            symbol=symbol,
            business_date=raw_data.stck_bsop_date,
            current_opinion=raw_data.invt_opnn,
            previous_opinion=raw_data.rgbf_invt_opnn,
            opinion_change=opinion_change,
            brokerage_firm=raw_data.mbcr_name,
            target_price=target_price,
            previous_close=previous_close,
            price_target_upside=price_target_upside,
            n_day_deviation=safe_float(raw_data.stck_nday_esdg),
            n_day_deviation_rate=safe_float(raw_data.nday_dprt),
            futures_deviation=safe_float(raw_data.stft_esdg),
            deviation_rate=safe_float(raw_data.dprt),
            opinion_code=raw_data.invt_opnn_cls_code,
            previous_opinion_code=raw_data.rgbf_invt_opnn_cls_code
        )


@dataclass
class InvestmentOpinionSummary:
    """투자의견 요약 정보"""
    symbol: str
    total_opinions: int  # 총 의견 수
    buy_opinions: int  # 매수 의견 수
    hold_opinions: int  # 보유 의견 수
    sell_opinions: int  # 매도 의견 수
    avg_target_price: float  # 평균 목표가
    max_target_price: float  # 최고 목표가
    min_target_price: float  # 최저 목표가
    avg_upside: float  # 평균 상승률
    most_recent_date: str  # 최근 의견 날짜
    opinion_trend: str  # 의견 트렌드 (상향/하향/보합)
    
    @classmethod
    def from_opinions(cls, symbol: str, opinions: List[ProcessedInvestmentOpinion]) -> 'InvestmentOpinionSummary':
        """투자의견 리스트로부터 요약 정보를 생성합니다."""
        if not opinions:
            return cls(
                symbol=symbol,
                total_opinions=0,
                buy_opinions=0,
                hold_opinions=0,
                sell_opinions=0,
                avg_target_price=0,
                max_target_price=0,
                min_target_price=0,
                avg_upside=0,
                most_recent_date="",
                opinion_trend="없음"
            )
        
        # 의견 분류
        buy_count = sum(1 for op in opinions if any(keyword in op.current_opinion for keyword in ['매수', 'BUY', 'Strong Buy']))
        sell_count = sum(1 for op in opinions if any(keyword in op.current_opinion for keyword in ['매도', 'SELL', 'Strong Sell']))
        hold_count = len(opinions) - buy_count - sell_count
        
        # 목표가 관련 계산
        target_prices = [op.target_price for op in opinions if op.target_price > 0]
        upsides = [op.price_target_upside for op in opinions if op.price_target_upside != 0]
        
        avg_target = sum(target_prices) / len(target_prices) if target_prices else 0
        max_target = max(target_prices) if target_prices else 0
        min_target = min(target_prices) if target_prices else 0
        avg_upside = sum(upsides) / len(upsides) if upsides else 0
        
        # 최근 날짜
        most_recent = max(opinions, key=lambda x: x.business_date).business_date
        
        # 트렌드 판단 (간단한 로직)
        if buy_count > sell_count:
            trend = "상향"
        elif sell_count > buy_count:
            trend = "하향"
        else:
            trend = "보합"
        
        return cls(
            symbol=symbol,
            total_opinions=len(opinions),
            buy_opinions=buy_count,
            hold_opinions=hold_count,
            sell_opinions=sell_count,
            avg_target_price=round(avg_target, 2),
            max_target_price=max_target,
            min_target_price=min_target,
            avg_upside=round(avg_upside, 2),
            most_recent_date=most_recent,
            opinion_trend=trend
        )

