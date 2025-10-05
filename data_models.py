"""
데이터 모델 정의 모듈

분석에 사용되는 데이터 구조와 타입을 정의합니다.
"""

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict

from utils.data_utils import serialize_for_json


class PriceData(TypedDict, total=False):
    """가격 데이터 구조"""
    current_price: Optional[float]
    w52_high: Optional[float]
    w52_low: Optional[float]
    per: Optional[float]
    pbr: Optional[float]
    eps: Optional[float]
    bps: Optional[float]
    volume: Optional[int]
    market_cap: Optional[float]
    price_change: Optional[float]
    price_change_rate: Optional[float]


class FinancialData(TypedDict, total=False):
    """재무 데이터 구조"""
    roe: Optional[float]
    roa: Optional[float]
    debt_ratio: Optional[float]
    equity_ratio: Optional[float]
    revenue_growth_rate: Optional[float]
    operating_income_growth_rate: Optional[float]
    net_income_growth_rate: Optional[float]
    net_profit_margin: Optional[float]
    gross_profit_margin: Optional[float]
    current_ratio: Optional[float]
    profitability_grade: Optional[str]


class SectorAnalysis(TypedDict, total=False):
    """섹터 분석 결과 구조"""
    grade: str
    total_score: Optional[float]
    breakdown: Dict[str, float]
    is_leader: bool
    base_score: Optional[float]
    leader_bonus: float
    notes: List[str]


class AnalysisStatus(enum.Enum):
    """분석 상태 열거형"""
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED_PREF = "skipped_pref"
    NO_DATA = "no_data"


@dataclass
class AnalysisResult:
    """분석 결과 데이터 클래스"""
    symbol: str
    name: str
    status: AnalysisStatus
    enhanced_score: float = 0.0
    enhanced_grade: str = 'F'
    market_cap: Optional[float] = None
    current_price: float = 0.0
    price_position: Optional[float] = None
    price_band_outside: bool = False  # 52주 밴드 밖 여부 플래그
    risk_score: Optional[float] = None
    financial_data: FinancialData = field(default_factory=dict)
    opinion_analysis: Dict[str, Any] = field(default_factory=dict)
    estimate_analysis: Dict[str, Any] = field(default_factory=dict)
    integrated_analysis: Dict[str, Any] = field(default_factory=dict)
    risk_analysis: Dict[str, Any] = field(default_factory=dict)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    raw_breakdown: Dict[str, float] = field(default_factory=dict)  # 원점수 breakdown
    error: Optional[str] = None
    price_data: PriceData = field(default_factory=dict)  # 가격 데이터 캐싱용
    sector_analysis: Dict[str, Any] = field(default_factory=dict)  # 섹터 분석 결과
    # 가치투자 확장 필드
    intrinsic_value: Optional[float] = None           # 내재가치(원)
    margin_of_safety: Optional[float] = None          # 안전마진(0~1)
    moat_grade: Optional[str] = None                  # 'Wide'/'Narrow'/'None' 등
    watchlist_signal: Optional[str] = None            # 'BUY'/'WATCH'/'PASS'
    target_buy: Optional[float] = None                # 목표매수가
    playbook: List[str] = field(default_factory=list) # 가치투자 플레이북
    
    def to_dict(self) -> Dict[str, Any]:
        """분석 결과를 딕셔너리로 변환"""
        pdict = self.price_data or {}
        
        # 대시보드용 요약 필드 생성
        sector_summary = ""
        if self.sector_analysis and self.sector_analysis.get('total_score') is not None:
            score = self.sector_analysis.get('total_score', 0)
            grade = self.sector_analysis.get('grade', 'N/A')
            sector_summary = f"{grade}({score:.1f})"

        d = {
            "symbol": self.symbol,
            "name": self.name,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "error": self.error,
            "enhanced_score": self.enhanced_score,
            "enhanced_grade": self.enhanced_grade,
            "market_cap": self.market_cap,
            "current_price": pdict.get("current_price"),
            "price_position": self.price_position,
            "w52_high": pdict.get("w52_high"),
            "w52_low": pdict.get("w52_low"),
            "per": pdict.get("per"),
            "pbr": pdict.get("pbr"),
            "score_breakdown": self.score_breakdown,
            "raw_breakdown": self.raw_breakdown,
            "financial_data": self.financial_data,
            "sector_analysis": self.sector_analysis,
            "sector_valuation": sector_summary,
            "opinion_summary": self.opinion_analysis.get('summary', '') if self.opinion_analysis else '',
            "estimate_summary": self.estimate_analysis.get('summary', '') if self.estimate_analysis else '',
            # 가치투자 결과
            "intrinsic_value": self.intrinsic_value,
            "margin_of_safety": self.margin_of_safety,
            "moat_grade": self.moat_grade,
            "watchlist_signal": self.watchlist_signal,
            "target_buy": self.target_buy,
            "playbook": self.playbook,
        }
        return serialize_for_json(d)


@dataclass(frozen=True)
class AnalysisConfig:
    """분석 설정 데이터 클래스 (불변)"""
    weights: Dict[str, float]
    financial_ratio_weights: Dict[str, float]
    estimate_analysis_weights: Dict[str, float]
    grade_thresholds: Dict[str, float]
    growth_score_thresholds: Dict[str, float]
    scale_score_thresholds: Dict[str, float]













