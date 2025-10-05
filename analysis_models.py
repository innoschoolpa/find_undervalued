"""
분석 모델 모듈

분석 상태, 결과, 설정을 정의하는 데이터 클래스들을 제공합니다.
"""

import enum
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class AnalysisStatus(enum.Enum):
    """분석 상태 열거형"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AnalysisResult:
    """분석 결과 데이터 클래스"""
    
    # 기본 정보
    symbol: str
    analysis_id: str
    status: AnalysisStatus
    timestamp: str
    
    # 분석 데이터
    financial_data: Dict[str, Any]
    price_data: Dict[str, Any]
    sector_data: Dict[str, Any]
    
    # 계산된 메트릭
    metrics: Dict[str, Any]
    scores: Dict[str, float]
    
    # 분석 결과
    recommendation: str
    confidence_score: float
    risk_level: str
    
    # 메타데이터
    analysis_duration: float
    data_quality_score: float
    error_messages: List[str]
    
    def __post_init__(self):
        """초기화 후 검증"""
        if not self.symbol:
            raise ValueError("symbol은 필수입니다")
        if not self.analysis_id:
            raise ValueError("analysis_id는 필수입니다")
        if not isinstance(self.status, AnalysisStatus):
            raise ValueError("status는 AnalysisStatus 타입이어야 합니다")
    
    def is_successful(self) -> bool:
        """분석 성공 여부"""
        return self.status == AnalysisStatus.COMPLETED and self.confidence_score > 0.5
    
    def has_errors(self) -> bool:
        """에러 존재 여부"""
        return len(self.error_messages) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """분석 결과 요약"""
        return {
            'symbol': self.symbol,
            'status': self.status.value,
            'recommendation': self.recommendation,
            'confidence_score': self.confidence_score,
            'risk_level': self.risk_level,
            'analysis_duration': self.analysis_duration,
            'data_quality_score': self.data_quality_score,
            'has_errors': self.has_errors(),
            'error_count': len(self.error_messages)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'symbol': self.symbol,
            'analysis_id': self.analysis_id,
            'status': self.status.value,
            'timestamp': self.timestamp,
            'financial_data': self.financial_data,
            'price_data': self.price_data,
            'sector_data': self.sector_data,
            'metrics': self.metrics,
            'scores': self.scores,
            'recommendation': self.recommendation,
            'confidence_score': self.confidence_score,
            'risk_level': self.risk_level,
            'analysis_duration': self.analysis_duration,
            'data_quality_score': self.data_quality_score,
            'error_messages': self.error_messages
        }


@dataclass
class AnalysisConfig:
    """분석 설정 데이터 클래스"""
    
    # 기본 설정
    analysis_type: str = "comprehensive"
    timeout_seconds: int = 300
    max_retries: int = 3
    
    # 데이터 품질 설정
    min_data_quality_score: float = 70.0
    data_freshness_hours: int = 24
    
    # 분석 옵션
    include_sector_analysis: bool = True
    include_risk_analysis: bool = True
    include_growth_analysis: bool = True
    include_valuation_analysis: bool = True
    
    # 점수 가중치
    value_weight: float = 0.35
    quality_weight: float = 0.25
    growth_weight: float = 0.15
    safety_weight: float = 0.15
    momentum_weight: float = 0.10
    
    # 필터링 설정
    min_market_cap: float = 1000000000  # 10억원
    max_pe_ratio: float = 50.0
    min_roe: float = 0.05  # 5%
    max_debt_ratio: float = 1.0
    
    # 출력 설정
    include_detailed_metrics: bool = True
    include_recommendations: bool = True
    include_risk_assessment: bool = True
    
    def __post_init__(self):
        """초기화 후 검증"""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds는 0보다 커야 합니다")
        if self.max_retries < 0:
            raise ValueError("max_retries는 0 이상이어야 합니다")
        if not 0 <= self.min_data_quality_score <= 100:
            raise ValueError("min_data_quality_score는 0~100 사이여야 합니다")
        
        # 가중치 합계 검증
        total_weight = (
            self.value_weight + self.quality_weight + self.growth_weight +
            self.safety_weight + self.momentum_weight
        )
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"가중치 합계는 1.0이어야 합니다. 현재: {total_weight}")
    
    def get_analysis_options(self) -> Dict[str, bool]:
        """분석 옵션 반환"""
        return {
            'include_sector_analysis': self.include_sector_analysis,
            'include_risk_analysis': self.include_risk_analysis,
            'include_growth_analysis': self.include_growth_analysis,
            'include_valuation_analysis': self.include_valuation_analysis
        }
    
    def get_score_weights(self) -> Dict[str, float]:
        """점수 가중치 반환"""
        return {
            'value_weight': self.value_weight,
            'quality_weight': self.quality_weight,
            'growth_weight': self.growth_weight,
            'safety_weight': self.safety_weight,
            'momentum_weight': self.momentum_weight
        }
    
    def get_filtering_criteria(self) -> Dict[str, float]:
        """필터링 기준 반환"""
        return {
            'min_market_cap': self.min_market_cap,
            'max_pe_ratio': self.max_pe_ratio,
            'min_roe': self.min_roe,
            'max_debt_ratio': self.max_debt_ratio
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'analysis_type': self.analysis_type,
            'timeout_seconds': self.timeout_seconds,
            'max_retries': self.max_retries,
            'min_data_quality_score': self.min_data_quality_score,
            'data_freshness_hours': self.data_freshness_hours,
            'include_sector_analysis': self.include_sector_analysis,
            'include_risk_analysis': self.include_risk_analysis,
            'include_growth_analysis': self.include_growth_analysis,
            'include_valuation_analysis': self.include_valuation_analysis,
            'value_weight': self.value_weight,
            'quality_weight': self.quality_weight,
            'growth_weight': self.growth_weight,
            'safety_weight': self.safety_weight,
            'momentum_weight': self.momentum_weight,
            'min_market_cap': self.min_market_cap,
            'max_pe_ratio': self.max_pe_ratio,
            'min_roe': self.min_roe,
            'max_debt_ratio': self.max_debt_ratio,
            'include_detailed_metrics': self.include_detailed_metrics,
            'include_recommendations': self.include_recommendations,
            'include_risk_assessment': self.include_risk_assessment
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisConfig':
        """딕셔너리에서 생성"""
        return cls(**data)
    
    @classmethod
    def get_default_config(cls) -> 'AnalysisConfig':
        """기본 설정 반환"""
        return cls()
    
    @classmethod
    def get_conservative_config(cls) -> 'AnalysisConfig':
        """보수적 설정 반환"""
        return cls(
            min_data_quality_score=80.0,
            min_roe=0.10,  # 10%
            max_debt_ratio=0.5,
            value_weight=0.4,
            quality_weight=0.3,
            growth_weight=0.1,
            safety_weight=0.15,
            momentum_weight=0.05
        )
    
    @classmethod
    def get_aggressive_config(cls) -> 'AnalysisConfig':
        """공격적 설정 반환"""
        return cls(
            min_data_quality_score=60.0,
            min_roe=0.03,  # 3%
            max_debt_ratio=1.5,
            value_weight=0.3,
            quality_weight=0.2,
            growth_weight=0.25,
            safety_weight=0.15,
            momentum_weight=0.10
        )













