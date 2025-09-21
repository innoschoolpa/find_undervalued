"""
업종별 특화 분석기
저평가 가치주 발굴을 위한 업종별 맞춤형 분석 모델
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SectorType(Enum):
    """업종 타입 열거형"""
    GAME = "게임업"
    SEMICONDUCTOR = "반도체"
    MANUFACTURING = "제조업"
    FINANCE = "금융업"
    BIO = "바이오/제약"
    TECHNOLOGY = "기술업"
    CONSUMER = "소비재"
    ENERGY = "에너지"
    MATERIALS = "소재"
    OTHER = "기타"

@dataclass
class SectorCharacteristics:
    """업종별 특성 데이터 클래스"""
    sector_name: str
    typical_per_range: tuple[float, float]  # (최소, 최대)
    typical_pbr_range: tuple[float, float]
    typical_roe_range: tuple[float, float]
    growth_importance: float  # 성장성 중요도 (0-1)
    stability_importance: float  # 안정성 중요도 (0-1)
    market_cycle_sensitivity: float  # 시장 사이클 민감도 (0-1)
    regulatory_risk: float  # 규제 리스크 (0-1)
    technology_risk: float  # 기술 리스크 (0-1)
    key_metrics: List[str]  # 핵심 지표 목록

class BaseSectorModel(ABC):
    """업종별 분석 모델의 기본 클래스"""
    
    def __init__(self, characteristics: SectorCharacteristics):
        self.characteristics = characteristics
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def calculate_sector_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """업종별 특화 점수 계산"""
        pass
    
    @abstractmethod
    def evaluate_growth_potential(self, data: Dict[str, Any]) -> float:
        """성장성 평가 (업종별 특화)"""
        pass
    
    @abstractmethod
    def evaluate_stability(self, data: Dict[str, Any]) -> float:
        """안정성 평가 (업종별 특화)"""
        pass
    
    @abstractmethod
    def calculate_valuation_score(self, data: Dict[str, Any]) -> float:
        """밸류에이션 점수 계산 (업종별 기준)"""
        pass
    
    def get_sector_weight_adjustment(self, market_phase: str) -> Dict[str, float]:
        """시장 사이클에 따른 가중치 조정"""
        base_weights = {
            'opinion_analysis': 20.0,
            'estimate_analysis': 25.0,
            'financial_ratios': 30.0,
            'growth_analysis': 10.0,
            'scale_analysis': 5.0,
            'valuation_bonus': 10.0
        }
        
        # 시장 사이클에 따른 조정
        if market_phase == "expansion":
            # 성장장에서는 성장성과 투자의견 비중 증가
            base_weights['growth_analysis'] *= 1.5
            base_weights['opinion_analysis'] *= 1.2
        elif market_phase == "recession":
            # 침체기에는 안정성과 재무비율 비중 증가
            base_weights['financial_ratios'] *= 1.3
            base_weights['scale_analysis'] *= 1.5
        
        # 업종 특성에 따른 조정
        base_weights['growth_analysis'] *= (1 + self.characteristics.growth_importance)
        base_weights['financial_ratios'] *= (1 + self.characteristics.stability_importance)
        
        # 정규화 (총합이 100이 되도록)
        total = sum(base_weights.values())
        for key in base_weights:
            base_weights[key] = (base_weights[key] / total) * 100
            
        return base_weights

class GameIndustryModel(BaseSectorModel):
    """게임업계 특화 모델"""
    
    def __init__(self):
        characteristics = SectorCharacteristics(
            sector_name="게임업",
            typical_per_range=(8.0, 35.0),
            typical_pbr_range=(1.0, 8.0),
            typical_roe_range=(5.0, 50.0),
            growth_importance=0.8,  # 게임업은 성장성이 매우 중요
            stability_importance=0.4,  # 안정성은 상대적으로 덜 중요
            market_cycle_sensitivity=0.6,  # 시장 사이클에 중간 정도 민감
            regulatory_risk=0.7,  # 규제 리스크 높음 (게임 규제, 판호 등)
            technology_risk=0.8,  # 기술 리스크 높음 (플랫폼 변화, 기술 트렌드)
            key_metrics=["DAU", "ARPU", "게임_라이프사이클", "신작_파이프라인", "글로벌_진출"]
        )
        super().__init__(characteristics)
    
    def calculate_sector_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """게임업계 특화 점수 계산"""
        score = 0.0
        breakdown = {}
        
        # 기본 재무 지표 평가 (업종별 기준 적용)
        financial_score = self.calculate_valuation_score(data)
        score += financial_score * 0.3
        breakdown['재무_건전성'] = financial_score * 0.3
        
        # 성장성 평가 (게임업에서 매우 중요)
        growth_score = self.evaluate_growth_potential(data)
        score += growth_score * 0.4
        breakdown['성장성'] = growth_score * 0.4
        
        # 안정성 평가
        stability_score = self.evaluate_stability(data)
        score += stability_score * 0.2
        breakdown['안정성'] = stability_score * 0.2
        
        # 게임업 특화 지표
        game_specific_score = self._evaluate_game_specific_metrics(data)
        score += game_specific_score * 0.1
        breakdown['게임_특화_지표'] = game_specific_score * 0.1
        
        return {
            'total_score': min(100, max(0, score)),
            'breakdown': breakdown,
            'sector_grade': self._get_sector_grade(score)
        }
    
    def evaluate_growth_potential(self, data: Dict[str, Any]) -> float:
        """게임업계 성장성 평가"""
        score = 0.0
        
        # 매출 성장률 (게임업에서 매우 중요)
        revenue_growth = data.get('revenue_growth_rate', 0)
        if revenue_growth > 30:
            score += 40  # 매우 높은 성장
        elif revenue_growth > 15:
            score += 30  # 높은 성장
        elif revenue_growth > 5:
            score += 20  # 보통 성장
        elif revenue_growth > 0:
            score += 10  # 낮은 성장
        
        # 영업이익 성장률
        operating_growth = data.get('operating_income_growth_rate', 0)
        if operating_growth > 50:
            score += 30
        elif operating_growth > 20:
            score += 20
        elif operating_growth > 0:
            score += 10
        
        # 신작 파이프라인 (추정, 실제로는 별도 데이터 필요)
        # 게임업은 신작이 성공의 핵심
        score += 30  # 기본 점수 (향후 실제 데이터로 대체)
        
        return min(100, score)
    
    def evaluate_stability(self, data: Dict[str, Any]) -> float:
        """게임업계 안정성 평가"""
        score = 0.0
        
        # 부채비율 (게임업은 현금 흐름이 중요)
        debt_ratio = data.get('debt_ratio', 100)
        if debt_ratio < 30:
            score += 40
        elif debt_ratio < 50:
            score += 30
        elif debt_ratio < 70:
            score += 20
        elif debt_ratio < 100:
            score += 10
        
        # 유동비율 (단기 자금 조달 능력)
        current_ratio = data.get('current_ratio', 100)
        if current_ratio > 200:
            score += 30
        elif current_ratio > 150:
            score += 20
        elif current_ratio > 100:
            score += 10
        
        # ROE 안정성
        roe = data.get('roe', 0)
        if 10 <= roe <= 50:  # 게임업 적정 ROE 범위
            score += 30
        elif 5 <= roe < 10 or 50 < roe <= 100:
            score += 20
        elif roe > 0:
            score += 10
        
        return min(100, score)
    
    def calculate_valuation_score(self, data: Dict[str, Any]) -> float:
        """게임업계 밸류에이션 점수 계산"""
        score = 0.0
        
        # PER 평가 (게임업 기준)
        per = data.get('per', 50)
        if per <= 12:
            score += 40  # 매우 저평가
        elif per <= 20:
            score += 30  # 저평가
        elif per <= 30:
            score += 20  # 적정가
        elif per <= 40:
            score += 10  # 약간 고평가
        else:
            score += 0   # 고평가
        
        # PBR 평가 (게임업 기준)
        pbr = data.get('pbr', 5)
        if pbr <= 1.5:
            score += 30
        elif pbr <= 2.5:
            score += 20
        elif pbr <= 4.0:
            score += 10
        elif pbr <= 6.0:
            score += 5
        
        # ROE 평가
        roe = data.get('roe', 0)
        if roe >= 30:
            score += 30
        elif roe >= 20:
            score += 25
        elif roe >= 15:
            score += 20
        elif roe >= 10:
            score += 15
        elif roe >= 5:
            score += 10
        
        return min(100, score)
    
    def _evaluate_game_specific_metrics(self, data: Dict[str, Any]) -> float:
        """게임업 특화 지표 평가"""
        score = 50  # 기본 점수
        
        # 향후 실제 데이터가 있다면:
        # - DAU (일간 활성 사용자)
        # - ARPU (사용자당 평균 수익)
        # - 게임 라이프사이클 단계
        # - 신작 파이프라인
        # - 글로벌 진출 현황
        
        return score
    
    def _get_sector_grade(self, score: float) -> str:
        """업종별 등급 결정"""
        if score >= 85:
            return "A+"
        elif score >= 75:
            return "A"
        elif score >= 65:
            return "B+"
        elif score >= 55:
            return "B"
        elif score >= 45:
            return "C+"
        elif score >= 35:
            return "C"
        elif score >= 25:
            return "D"
        else:
            return "F"

class SemiconductorModel(BaseSectorModel):
    """반도체업계 특화 모델"""
    
    def __init__(self):
        characteristics = SectorCharacteristics(
            sector_name="반도체",
            typical_per_range=(10.0, 50.0),
            typical_pbr_range=(1.5, 10.0),
            typical_roe_range=(8.0, 60.0),
            growth_importance=0.7,  # 성장성 중요
            stability_importance=0.6,  # 안정성도 중요
            market_cycle_sensitivity=0.9,  # 시장 사이클에 매우 민감
            regulatory_risk=0.8,  # 규제 리스크 높음 (무역 규제, 기술 제한)
            technology_risk=0.9,  # 기술 리스크 매우 높음 (기술 노드, R&D)
            key_metrics=["기술_노드", "시장_점유율", "R&D_투자", "고객_다변화", "글로벌_경쟁력"]
        )
        super().__init__(characteristics)
    
    def calculate_sector_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """반도체업계 특화 점수 계산"""
        score = 0.0
        breakdown = {}
        
        # 기본 재무 지표 평가
        financial_score = self.calculate_valuation_score(data)
        score += financial_score * 0.25
        breakdown['재무_건전성'] = financial_score * 0.25
        
        # 성장성 평가 (반도체에서 중요)
        growth_score = self.evaluate_growth_potential(data)
        score += growth_score * 0.35
        breakdown['성장성'] = growth_score * 0.35
        
        # 안정성 평가 (반도체에서 중요)
        stability_score = self.evaluate_stability(data)
        score += stability_score * 0.25
        breakdown['안정성'] = stability_score * 0.25
        
        # 반도체 특화 지표
        semiconductor_specific_score = self._evaluate_semiconductor_specific_metrics(data)
        score += semiconductor_specific_score * 0.15
        breakdown['반도체_특화_지표'] = semiconductor_specific_score * 0.15
        
        return {
            'total_score': min(100, max(0, score)),
            'breakdown': breakdown,
            'sector_grade': self._get_sector_grade(score)
        }
    
    def evaluate_growth_potential(self, data: Dict[str, Any]) -> float:
        """반도체업계 성장성 평가"""
        score = 0.0
        
        # 매출 성장률 (반도체는 사이클성이 강함)
        revenue_growth = data.get('revenue_growth_rate', 0)
        if revenue_growth > 40:
            score += 35  # 매우 높은 성장
        elif revenue_growth > 20:
            score += 25  # 높은 성장
        elif revenue_growth > 5:
            score += 15  # 보통 성장
        elif revenue_growth > 0:
            score += 5   # 낮은 성장
        
        # 영업이익 성장률
        operating_growth = data.get('operating_income_growth_rate', 0)
        if operating_growth > 60:
            score += 35
        elif operating_growth > 30:
            score += 25
        elif operating_growth > 10:
            score += 15
        elif operating_growth > 0:
            score += 5
        
        # R&D 투자 (반도체에서 매우 중요)
        # 향후 실제 R&D 데이터로 대체
        score += 30  # 기본 점수
        
        return min(100, score)
    
    def evaluate_stability(self, data: Dict[str, Any]) -> float:
        """반도체업계 안정성 평가"""
        score = 0.0
        
        # 부채비율 (반도체는 자본 집약적)
        debt_ratio = data.get('debt_ratio', 100)
        if debt_ratio < 40:
            score += 35
        elif debt_ratio < 60:
            score += 25
        elif debt_ratio < 80:
            score += 15
        elif debt_ratio < 100:
            score += 10
        
        # 유동비율
        current_ratio = data.get('current_ratio', 100)
        if current_ratio > 250:
            score += 25
        elif current_ratio > 200:
            score += 20
        elif current_ratio > 150:
            score += 15
        elif current_ratio > 100:
            score += 10
        
        # ROE 안정성 (반도체 적정 범위)
        roe = data.get('roe', 0)
        if 15 <= roe <= 60:  # 반도체 적정 ROE 범위
            score += 40
        elif 8 <= roe < 15 or 60 < roe <= 80:
            score += 25
        elif roe > 0:
            score += 10
        
        return min(100, score)
    
    def calculate_valuation_score(self, data: Dict[str, Any]) -> float:
        """반도체업계 밸류에이션 점수 계산"""
        score = 0.0
        
        # PER 평가 (반도체 기준)
        per = data.get('per', 50)
        if per <= 15:
            score += 35  # 매우 저평가
        elif per <= 25:
            score += 25  # 저평가
        elif per <= 35:
            score += 15  # 적정가
        elif per <= 45:
            score += 10  # 약간 고평가
        else:
            score += 0   # 고평가
        
        # PBR 평가 (반도체 기준)
        pbr = data.get('pbr', 5)
        if pbr <= 2.0:
            score += 25
        elif pbr <= 3.0:
            score += 20
        elif pbr <= 5.0:
            score += 15
        elif pbr <= 7.0:
            score += 10
        elif pbr <= 10.0:
            score += 5
        
        # ROE 평가
        roe = data.get('roe', 0)
        if roe >= 40:
            score += 40
        elif roe >= 25:
            score += 30
        elif roe >= 15:
            score += 25
        elif roe >= 10:
            score += 20
        elif roe >= 5:
            score += 15
        
        return min(100, score)
    
    def _evaluate_semiconductor_specific_metrics(self, data: Dict[str, Any]) -> float:
        """반도체업계 특화 지표 평가"""
        score = 50  # 기본 점수
        
        # 향후 실제 데이터가 있다면:
        # - 기술 노드 (5nm, 7nm 등)
        # - 시장 점유율
        # - R&D 투자 비중
        # - 고객 다변화도
        # - 글로벌 경쟁력
        
        return score
    
    def _get_sector_grade(self, score: float) -> str:
        """업종별 등급 결정"""
        if score >= 85:
            return "A+"
        elif score >= 75:
            return "A"
        elif score >= 65:
            return "B+"
        elif score >= 55:
            return "B"
        elif score >= 45:
            return "C+"
        elif score >= 35:
            return "C"
        elif score >= 25:
            return "D"
        else:
            return "F"

class ManufacturingModel(BaseSectorModel):
    """제조업계 특화 모델"""
    
    def __init__(self):
        characteristics = SectorCharacteristics(
            sector_name="제조업",
            typical_per_range=(5.0, 25.0),
            typical_pbr_range=(0.5, 3.0),
            typical_roe_range=(5.0, 25.0),
            growth_importance=0.5,  # 성장성은 보통
            stability_importance=0.8,  # 안정성이 매우 중요
            market_cycle_sensitivity=0.7,  # 시장 사이클에 민감
            regulatory_risk=0.4,  # 규제 리스크 보통
            technology_risk=0.5,  # 기술 리스크 보통
            key_metrics=["생산_효율성", "원자재_비용", "수출_비중", "자동화_수준", "품질_관리"]
        )
        super().__init__(characteristics)
    
    def calculate_sector_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """제조업계 특화 점수 계산"""
        score = 0.0
        breakdown = {}
        
        # 기본 재무 지표 평가 (제조업에서 중요)
        financial_score = self.calculate_valuation_score(data)
        score += financial_score * 0.4
        breakdown['재무_건전성'] = financial_score * 0.4
        
        # 성장성 평가
        growth_score = self.evaluate_growth_potential(data)
        score += growth_score * 0.25
        breakdown['성장성'] = growth_score * 0.25
        
        # 안정성 평가 (제조업에서 매우 중요)
        stability_score = self.evaluate_stability(data)
        score += stability_score * 0.35
        breakdown['안정성'] = stability_score * 0.35
        
        return {
            'total_score': min(100, max(0, score)),
            'breakdown': breakdown,
            'sector_grade': self._get_sector_grade(score)
        }
    
    def evaluate_growth_potential(self, data: Dict[str, Any]) -> float:
        """제조업계 성장성 평가"""
        score = 0.0
        
        # 매출 성장률 (제조업은 안정적 성장 선호)
        revenue_growth = data.get('revenue_growth_rate', 0)
        if 5 <= revenue_growth <= 20:  # 안정적 성장 범위
            score += 40
        elif 0 <= revenue_growth < 5 or 20 < revenue_growth <= 30:
            score += 30
        elif revenue_growth > 30:
            score += 20  # 너무 급격한 성장은 리스크
        else:
            score += 0   # 마이너스 성장
        
        # 영업이익 성장률
        operating_growth = data.get('operating_income_growth_rate', 0)
        if 10 <= operating_growth <= 30:
            score += 35
        elif 0 <= operating_growth < 10 or 30 < operating_growth <= 50:
            score += 25
        elif operating_growth > 50:
            score += 15
        else:
            score += 0
        
        # 안정성 보너스 (제조업 특성)
        score += 25
        
        return min(100, score)
    
    def evaluate_stability(self, data: Dict[str, Any]) -> float:
        """제조업계 안정성 평가"""
        score = 0.0
        
        # 부채비율 (제조업은 안정적 재무 구조 중요)
        debt_ratio = data.get('debt_ratio', 100)
        if debt_ratio < 30:
            score += 40
        elif debt_ratio < 50:
            score += 35
        elif debt_ratio < 70:
            score += 25
        elif debt_ratio < 100:
            score += 15
        elif debt_ratio < 150:
            score += 5
        
        # 유동비율 (운영자금 관리 중요)
        current_ratio = data.get('current_ratio', 100)
        if current_ratio > 150:
            score += 30
        elif current_ratio > 120:
            score += 25
        elif current_ratio > 100:
            score += 20
        elif current_ratio > 80:
            score += 10
        
        # ROE 안정성 (제조업 적정 범위)
        roe = data.get('roe', 0)
        if 8 <= roe <= 20:  # 제조업 적정 ROE 범위
            score += 30
        elif 5 <= roe < 8 or 20 < roe <= 30:
            score += 20
        elif roe > 0:
            score += 10
        
        return min(100, score)
    
    def calculate_valuation_score(self, data: Dict[str, Any]) -> float:
        """제조업계 밸류에이션 점수 계산"""
        score = 0.0
        
        # PER 평가 (제조업 기준)
        per = data.get('per', 20)
        if per <= 8:
            score += 40  # 매우 저평가
        elif per <= 12:
            score += 35  # 저평가
        elif per <= 18:
            score += 25  # 적정가
        elif per <= 25:
            score += 15  # 약간 고평가
        else:
            score += 0   # 고평가
        
        # PBR 평가 (제조업 기준)
        pbr = data.get('pbr', 2)
        if pbr <= 0.8:
            score += 30
        elif pbr <= 1.2:
            score += 25
        elif pbr <= 1.8:
            score += 20
        elif pbr <= 2.5:
            score += 15
        elif pbr <= 3.5:
            score += 10
        
        # ROE 평가
        roe = data.get('roe', 0)
        if roe >= 20:
            score += 30
        elif roe >= 15:
            score += 25
        elif roe >= 10:
            score += 20
        elif roe >= 5:
            score += 15
        elif roe > 0:
            score += 10
        
        return min(100, score)
    
    def _get_sector_grade(self, score: float) -> str:
        """업종별 등급 결정"""
        if score >= 85:
            return "A+"
        elif score >= 75:
            return "A"
        elif score >= 65:
            return "B+"
        elif score >= 55:
            return "B"
        elif score >= 45:
            return "C+"
        elif score >= 35:
            return "C"
        elif score >= 25:
            return "D"
        else:
            return "F"

class SectorSpecificAnalyzer:
    """업종별 특화 분석기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models = {
            SectorType.GAME: GameIndustryModel(),
            SectorType.SEMICONDUCTOR: SemiconductorModel(),
            SectorType.MANUFACTURING: ManufacturingModel(),
            # 향후 추가 모델들
        }
        self.default_model = None  # 기본 모델 (향후 구현)
    
    def get_sector_type(self, symbol: str, sector_name: str) -> SectorType:
        """종목 코드와 업종명으로부터 SectorType 결정"""
        sector_lower = sector_name.lower()
        
        if any(keyword in sector_lower for keyword in ['게임', 'game', '엔터테인먼트']):
            return SectorType.GAME
        elif any(keyword in sector_lower for keyword in ['반도체', 'semiconductor', '칩']):
            return SectorType.SEMICONDUCTOR
        elif any(keyword in sector_lower for keyword in ['제조', 'manufacturing', '기계']):
            return SectorType.MANUFACTURING
        elif any(keyword in sector_lower for keyword in ['금융', 'finance', '은행']):
            return SectorType.FINANCE
        elif any(keyword in sector_lower for keyword in ['바이오', 'bio', '제약', 'pharma']):
            return SectorType.BIO
        elif any(keyword in sector_lower for keyword in ['기술', 'technology', '소프트웨어']):
            return SectorType.TECHNOLOGY
        else:
            return SectorType.OTHER
    
    def analyze_stock_by_sector(self, symbol: str, sector_name: str, 
                               data: Dict[str, Any], market_phase: str = "normal") -> Dict[str, Any]:
        """업종별 특화 분석 수행"""
        try:
            sector_type = self.get_sector_type(symbol, sector_name)
            model = self.models.get(sector_type)
            
            if not model:
                self.logger.warning(f"업종별 모델이 없습니다: {sector_type}")
                return self._create_default_analysis(data)
            
            # 업종별 분석 수행
            sector_analysis = model.calculate_sector_score(data)
            
            # 시장 사이클에 따른 가중치 조정
            adjusted_weights = model.get_sector_weight_adjustment(market_phase)
            
            return {
                'sector_type': sector_type.value,
                'sector_analysis': sector_analysis,
                'adjusted_weights': adjusted_weights,
                'market_phase': market_phase,
                'analysis_timestamp': data.get('analysis_timestamp')
            }
            
        except Exception as e:
            self.logger.error(f"업종별 분석 실패 {symbol}: {e}")
            return self._create_default_analysis(data)
    
    def _create_default_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """기본 분석 결과 생성"""
        return {
            'sector_type': '기타',
            'sector_analysis': {
                'total_score': 50.0,
                'breakdown': {'기본_분석': 50.0},
                'sector_grade': 'C'
            },
            'adjusted_weights': {
                'opinion_analysis': 20.0,
                'estimate_analysis': 25.0,
                'financial_ratios': 30.0,
                'growth_analysis': 10.0,
                'scale_analysis': 5.0,
                'valuation_bonus': 10.0
            },
            'market_phase': 'normal',
            'error': '업종별 모델 없음'
        }
