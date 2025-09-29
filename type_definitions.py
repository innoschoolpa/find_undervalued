# type_definitions.py
"""
강화된 타입 정의 모듈
- 엄격한 타입 힌트
- 데이터 검증
- 타입 안전성 보장
"""

from typing import Dict, List, Optional, Union, Any, Tuple, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from decimal import Decimal

# 기본 타입 별칭
Symbol = str
Name = str
Price = float
Score = float
Percentage = float
MarketCap = float
Volume = int

# 제약된 타입들
class PositiveFloat(float):
    """양수만 허용하는 float"""
    def __new__(cls, value: float) -> 'PositiveFloat':
        if value < 0:
            raise ValueError(f"Value must be positive, got {value}")
        return super().__new__(cls, value)

class NonNegativeFloat(float):
    """0 이상의 값만 허용하는 float"""
    def __new__(cls, value: float) -> 'NonNegativeFloat':
        if value < 0:
            raise ValueError(f"Value must be non-negative, got {value}")
        return super().__new__(cls, value)

class ScoreRange(float):
    """0-100 범위의 점수"""
    def __new__(cls, value: float) -> 'ScoreRange':
        if not 0 <= value <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {value}")
        return super().__new__(cls, value)

class PercentageRange(float):
    """0-100 범위의 퍼센트"""
    def __new__(cls, value: float) -> 'PercentageRange':
        if not 0 <= value <= 100:
            raise ValueError(f"Percentage must be between 0 and 100, got {value}")
        return super().__new__(cls, value)

# 열거형들
class AnalysisStatus(Enum):
    """분석 상태"""
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED_PREF = "skipped_pref"
    NO_DATA = "no_data"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"

class Grade(Enum):
    """등급"""
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    C_MINUS = "C-"
    D_PLUS = "D+"
    D = "D"
    D_MINUS = "D-"
    F = "F"

class SectorType(Enum):
    """섹터 타입"""
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    INDUSTRIAL = "industrial"
    CONSUMER = "consumer"
    ENERGY = "energy"
    MATERIALS = "materials"
    UTILITIES = "utilities"
    REAL_ESTATE = "real_estate"
    COMMUNICATION = "communication"
    UNKNOWN = "unknown"

class CompanySize(Enum):
    """회사 규모"""
    LARGE_CAP = "large_cap"      # 대형주
    MID_CAP = "mid_cap"          # 중형주
    SMALL_CAP = "small_cap"      # 소형주
    MICRO_CAP = "micro_cap"      # 초소형주

# 데이터 클래스들
@dataclass(frozen=True)
class PriceData:
    """가격 데이터 (불변)"""
    current_price: Optional[Price] = None
    w52_high: Optional[Price] = None
    w52_low: Optional[Price] = None
    per: Optional[float] = None
    pbr: Optional[float] = None
    eps: Optional[Price] = None
    bps: Optional[Price] = None
    volume: Optional[Volume] = None
    market_cap: Optional[MarketCap] = None
    price_change: Optional[Price] = None
    price_change_rate: Optional[Percentage] = None
    
    def __post_init__(self):
        """데이터 검증"""
        if self.current_price is not None and self.current_price < 0:
            raise ValueError("Current price cannot be negative")
        if self.w52_high is not None and self.w52_low is not None:
            if self.w52_high < self.w52_low:
                raise ValueError("52-week high cannot be lower than 52-week low")

@dataclass(frozen=True)
class FinancialData:
    """재무 데이터 (불변)"""
    roe: Optional[Percentage] = None
    roa: Optional[Percentage] = None
    debt_ratio: Optional[Percentage] = None
    equity_ratio: Optional[Percentage] = None
    revenue_growth_rate: Optional[Percentage] = None
    operating_income_growth_rate: Optional[Percentage] = None
    net_income_growth_rate: Optional[Percentage] = None
    net_profit_margin: Optional[Percentage] = None
    gross_profit_margin: Optional[Percentage] = None
    current_ratio: Optional[float] = None
    profitability_grade: Optional[Grade] = None

@dataclass(frozen=True)
class SectorAnalysis:
    """섹터 분석 결과 (불변)"""
    grade: Grade
    total_score: ScoreRange
    breakdown: Dict[str, float] = field(default_factory=dict)
    is_leader: bool = False
    base_score: Optional[ScoreRange] = None
    leader_bonus: float = 0.0
    notes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """데이터 검증"""
        if not isinstance(self.grade, Grade):
            raise ValueError("Grade must be a Grade enum")
        if not 0 <= self.total_score <= 100:
            raise ValueError("Total score must be between 0 and 100")

@dataclass(frozen=True)
class AnalysisResult:
    """분석 결과 (불변)"""
    symbol: Symbol
    name: Name
    status: AnalysisStatus
    enhanced_score: ScoreRange = 0.0
    enhanced_grade: Grade = Grade.F
    market_cap: Optional[MarketCap] = None
    current_price: Price = 0.0
    price_position: Optional[Percentage] = None
    price_band_outside: bool = False
    risk_score: Optional[ScoreRange] = None
    financial_data: FinancialData = field(default_factory=FinancialData)
    price_data: PriceData = field(default_factory=PriceData)
    sector_analysis: SectorAnalysis = field(default_factory=lambda: SectorAnalysis(
        grade=Grade.F, total_score=0.0
    ))
    error: Optional[str] = None
    
    def __post_init__(self):
        """데이터 검증"""
        if not self.symbol or len(self.symbol) < 1:
            raise ValueError("Symbol cannot be empty")
        if not self.name or len(self.name) < 1:
            raise ValueError("Name cannot be empty")
        if not isinstance(self.status, AnalysisStatus):
            raise ValueError("Status must be an AnalysisStatus enum")
        if not isinstance(self.enhanced_grade, Grade):
            raise ValueError("Enhanced grade must be a Grade enum")

@dataclass(frozen=True)
class AnalysisConfig:
    """분석 설정 (불변)"""
    weights: Dict[str, float]
    financial_ratio_weights: Dict[str, float]
    estimate_analysis_weights: Dict[str, float]
    grade_thresholds: Dict[str, float]
    growth_score_thresholds: Dict[str, float]
    scale_score_thresholds: Dict[str, float]
    
    def __post_init__(self):
        """설정 검증"""
        # 가중치 합이 1.0에 가까운지 확인
        total_weight = sum(self.weights.values())
        if not 0.95 <= total_weight <= 1.05:
            raise ValueError(f"Weights must sum to approximately 1.0, got {total_weight}")

# 제네릭 타입들
T = TypeVar('T')
U = TypeVar('U')

@dataclass
class Result(Generic[T]):
    """결과 래퍼 클래스"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    
    @classmethod
    def ok(cls, data: T) -> 'Result[T]':
        """성공 결과 생성"""
        return cls(success=True, data=data)
    
    @classmethod
    def error(cls, error: str) -> 'Result[T]':
        """에러 결과 생성"""
        return cls(success=False, error=error)
    
    def is_ok(self) -> bool:
        """성공 여부 확인"""
        return self.success
    
    def is_error(self) -> bool:
        """에러 여부 확인"""
        return not self.success
    
    def unwrap(self) -> T:
        """데이터 추출 (에러 시 예외 발생)"""
        if self.success:
            return self.data
        raise ValueError(f"Result is error: {self.error}")

# 함수 타입들
DataProcessor = Callable[[Dict[str, Any]], Result[Dict[str, Any]]]
ScoreCalculator = Callable[[Dict[str, Any]], ScoreRange]
Validator = Callable[[Any], bool]
Transformer = Callable[[T], U]

# 유틸리티 타입들
StringDict = Dict[str, str]
NumberDict = Dict[str, Union[int, float]]
AnyDict = Dict[str, Any]
StringList = List[str]
NumberList = List[Union[int, float]]

# 검증 함수들
def validate_symbol(symbol: Any) -> bool:
    """종목 코드 검증"""
    if not isinstance(symbol, str):
        return False
    if len(symbol) < 1 or len(symbol) > 10:
        return False
    return symbol.isalnum()

def validate_price(price: Any) -> bool:
    """가격 검증"""
    if price is None:
        return True
    if not isinstance(price, (int, float)):
        return False
    return price >= 0

def validate_percentage(percentage: Any) -> bool:
    """퍼센트 검증"""
    if percentage is None:
        return True
    if not isinstance(percentage, (int, float)):
        return False
    return 0 <= percentage <= 100

def validate_score(score: Any) -> bool:
    """점수 검증"""
    if not isinstance(score, (int, float)):
        return False
    return 0 <= score <= 100

# 타입 변환 함수들
def safe_float(value: Any, default: float = 0.0) -> float:
    """안전한 float 변환"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """안전한 int 변환"""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default

def safe_str(value: Any, default: str = "") -> str:
    """안전한 str 변환"""
    if value is None:
        return default
    try:
        return str(value).strip()
    except (ValueError, TypeError):
        return default

# 타입 체크 함수들
def is_valid_price_data(data: Any) -> bool:
    """PriceData 타입 검증"""
    if not isinstance(data, PriceData):
        return False
    return validate_price(data.current_price)

def is_valid_financial_data(data: Any) -> bool:
    """FinancialData 타입 검증"""
    if not isinstance(data, FinancialData):
        return False
    return validate_percentage(data.roe)

def is_valid_analysis_result(data: Any) -> bool:
    """AnalysisResult 타입 검증"""
    if not isinstance(data, AnalysisResult):
        return False
    return validate_symbol(data.symbol) and validate_score(data.enhanced_score)

