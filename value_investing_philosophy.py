# value_investing_philosophy.py
"""
가치 투자 철학 모듈
- 워렌 버핏 스타일의 가치 투자 원칙 구현
- 4대 핵심 원칙과 5단계 실행 계획
- 장기적 관점의 투자 의사결정 지원
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MoatType(Enum):
    """경제적 해자 유형"""
    INTANGIBLE_ASSETS = "무형자산"  # 브랜드, 특허, 라이선스
    NETWORK_EFFECTS = "네트워크효과"  # 사용자 증가에 따른 가치 증대
    SWITCHING_COSTS = "전환비용"  # 고객의 이탈 비용
    COST_ADVANTAGE = "비용우위"  # 규모의 경제, 효율성
    REGULATORY_BARRIERS = "규제장벽"  # 정부 허가, 면허

class SafetyLevel(Enum):
    """안전마진 수준"""
    EXCELLENT = "우수"  # 50% 이상 할인
    GOOD = "양호"  # 30-50% 할인
    ADEQUATE = "적정"  # 20-30% 할인
    LOW = "낮음"  # 10-20% 할인
    INSUFFICIENT = "부족"  # 10% 미만 할인

class TemperamentScore(Enum):
    """투자 기질 점수"""
    EXCELLENT = "우수"  # 90점 이상
    GOOD = "양호"  # 70-89점
    AVERAGE = "보통"  # 50-69점
    POOR = "부족"  # 30-49점
    VERY_POOR = "매우부족"  # 30점 미만

@dataclass
class EconomicMoat:
    """경제적 해자 분석"""
    moat_type: MoatType
    strength: float  # 0-100점
    sustainability: float  # 0-100점 (지속가능성)
    description: str
    evidence: List[str] = field(default_factory=list)

@dataclass
class IntrinsicValue:
    """내재가치 평가"""
    conservative_estimate: float  # 보수적 추정치
    optimistic_estimate: float  # 낙관적 추정치
    fair_value: float  # 공정가치 (평균)
    confidence_level: float  # 신뢰도 (0-100%)
    valuation_method: str  # 평가 방법
    assumptions: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MarginOfSafety:
    """안전마진 분석"""
    current_price: float
    intrinsic_value: float
    discount_percentage: float
    safety_level: SafetyLevel
    margin_amount: float
    recommendation: str

@dataclass
class BusinessAnalysis:
    """기업 분석"""
    business_model_score: float  # 0-100점
    competitive_advantage_score: float  # 0-100점
    management_quality_score: float  # 0-100점
    financial_strength_score: float  # 0-100점
    growth_prospects_score: float  # 0-100점
    moats: List[EconomicMoat] = field(default_factory=list)
    business_description: str = ""
    revenue_sources: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)

@dataclass
class InvestmentWatchlist:
    """투자 관심 종목 목록"""
    symbol: str
    name: str
    business_analysis: BusinessAnalysis
    intrinsic_value: IntrinsicValue
    target_buy_price: float
    current_price: float
    margin_of_safety: MarginOfSafety
    added_date: datetime
    last_updated: datetime
    notes: str = ""

class ValueInvestingPhilosophy:
    """가치 투자 철학 구현 클래스"""
    
    def __init__(self):
        self.watchlist: List[InvestmentWatchlist] = []
        self.circle_of_competence: List[str] = []  # 능력 범위
        self.temperament_score: float = 0.0
        
    def analyze_business_model(self, stock_data: Dict[str, Any]) -> BusinessAnalysis:
        """1단계: 기업 분석 (Buy a Business, Not a Stock)"""
        try:
            # 비즈니스 모델 점수 계산
            business_model_score = self._calculate_business_model_score(stock_data)
            
            # 경쟁 우위 점수 계산
            competitive_advantage_score = self._calculate_competitive_advantage_score(stock_data)
            
            # 경영진 품질 점수 (간접 추정)
            management_quality_score = self._calculate_management_quality_score(stock_data)
            
            # 재무 건전성 점수
            financial_strength_score = self._calculate_financial_strength_score(stock_data)
            
            # 성장 전망 점수
            growth_prospects_score = self._calculate_growth_prospects_score(stock_data)
            
            # 경제적 해자 분석
            moats = self._analyze_economic_moats(stock_data)
            
            # 비즈니스 설명 생성
            business_description = self._generate_business_description(stock_data)
            
            # 수익원 분석
            revenue_sources = self._analyze_revenue_sources(stock_data)
            
            # 주요 리스크 식별
            key_risks = self._identify_key_risks(stock_data)
            
            return BusinessAnalysis(
                business_model_score=business_model_score,
                competitive_advantage_score=competitive_advantage_score,
                management_quality_score=management_quality_score,
                financial_strength_score=financial_strength_score,
                growth_prospects_score=growth_prospects_score,
                moats=moats,
                business_description=business_description,
                revenue_sources=revenue_sources,
                key_risks=key_risks
            )
            
        except Exception as e:
            logger.error(f"비즈니스 모델 분석 실패: {e}")
            return BusinessAnalysis(0, 0, 0, 0, 0)
    
    def calculate_intrinsic_value(self, stock_data: Dict[str, Any]) -> IntrinsicValue:
        """2단계: 내재가치 평가"""
        try:
            # DCF 모델 기반 내재가치 계산
            dcf_value = self._calculate_dcf_value(stock_data)
            
            # PER/PBR 기반 상대가치 평가
            relative_value = self._calculate_relative_value(stock_data)
            
            # 자산가치 기반 평가
            asset_value = self._calculate_asset_value(stock_data)
            
            # 보수적 추정치 (최저값)
            conservative_estimate = min(dcf_value, relative_value, asset_value)
            
            # 낙관적 추정치 (최고값)
            optimistic_estimate = max(dcf_value, relative_value, asset_value)
            
            # 공정가치 (평균)
            fair_value = (conservative_estimate + optimistic_estimate) / 2
            
            # 신뢰도 계산
            confidence_level = self._calculate_confidence_level(stock_data)
            
            return IntrinsicValue(
                conservative_estimate=conservative_estimate,
                optimistic_estimate=optimistic_estimate,
                fair_value=fair_value,
                confidence_level=confidence_level,
                valuation_method="DCF + 상대가치 + 자산가치 종합",
                assumptions={
                    "dcf_value": dcf_value,
                    "relative_value": relative_value,
                    "asset_value": asset_value
                }
            )
            
        except Exception as e:
            logger.error(f"내재가치 계산 실패: {e}")
            return IntrinsicValue(0, 0, 0, 0, "계산 실패")
    
    def calculate_margin_of_safety(self, current_price: float, intrinsic_value: IntrinsicValue) -> MarginOfSafety:
        """3단계: 안전마진 계산"""
        try:
            # 할인율 계산
            discount_percentage = ((intrinsic_value.fair_value - current_price) / intrinsic_value.fair_value) * 100
            
            # 안전마진 금액
            margin_amount = intrinsic_value.fair_value - current_price
            
            # 안전마진 수준 결정
            if discount_percentage >= 50:
                safety_level = SafetyLevel.EXCELLENT
                recommendation = "강력 매수 - 우수한 안전마진"
            elif discount_percentage >= 30:
                safety_level = SafetyLevel.GOOD
                recommendation = "매수 - 양호한 안전마진"
            elif discount_percentage >= 20:
                safety_level = SafetyLevel.ADEQUATE
                recommendation = "신중한 매수 - 적정 안전마진"
            elif discount_percentage >= 10:
                safety_level = SafetyLevel.LOW
                recommendation = "관망 - 낮은 안전마진"
            else:
                safety_level = SafetyLevel.INSUFFICIENT
                recommendation = "매도 고려 - 부족한 안전마진"
            
            return MarginOfSafety(
                current_price=current_price,
                intrinsic_value=intrinsic_value.fair_value,
                discount_percentage=discount_percentage,
                safety_level=safety_level,
                margin_amount=margin_amount,
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.error(f"안전마진 계산 실패: {e}")
            return MarginOfSafety(current_price, 0, 0, SafetyLevel.INSUFFICIENT, 0, "계산 실패")
    
    def assess_temperament(self, investment_history: List[Dict[str, Any]]) -> float:
        """4단계: 투자 기질 평가"""
        try:
            temperament_score = 0.0
            
            # 인내심 평가 (보유 기간)
            patience_score = self._assess_patience(investment_history)
            temperament_score += patience_score * 0.3
            
            # 능력 범위 준수 평가
            competence_score = self._assess_competence_range(investment_history)
            temperament_score += competence_score * 0.3
            
            # 역발상적 사고 평가
            contrarian_score = self._assess_contrarian_thinking(investment_history)
            temperament_score += contrarian_score * 0.4
            
            self.temperament_score = temperament_score
            return temperament_score
            
        except Exception as e:
            logger.error(f"투자 기질 평가 실패: {e}")
            return 0.0
    
    def add_to_watchlist(self, symbol: str, name: str, stock_data: Dict[str, Any]) -> InvestmentWatchlist:
        """관심 종목 목록에 추가"""
        try:
            # 기업 분석
            business_analysis = self.analyze_business_model(stock_data)
            
            # 내재가치 평가
            intrinsic_value = self.calculate_intrinsic_value(stock_data)
            
            # 현재가
            current_price = stock_data.get('current_price', 0)
            
            # 목표 매수가 (내재가치의 70% - 30% 안전마진)
            target_buy_price = intrinsic_value.fair_value * 0.7
            
            # 안전마진 계산
            margin_of_safety = self.calculate_margin_of_safety(current_price, intrinsic_value)
            
            watchlist_item = InvestmentWatchlist(
                symbol=symbol,
                name=name,
                business_analysis=business_analysis,
                intrinsic_value=intrinsic_value,
                target_buy_price=target_buy_price,
                current_price=current_price,
                margin_of_safety=margin_of_safety,
                added_date=datetime.now(),
                last_updated=datetime.now()
            )
            
            self.watchlist.append(watchlist_item)
            return watchlist_item
            
        except Exception as e:
            logger.error(f"관심 종목 추가 실패: {e}")
            return None
    
    def get_buy_signals(self) -> List[InvestmentWatchlist]:
        """매수 신호가 있는 종목들 반환"""
        buy_signals = []
        
        for item in self.watchlist:
            # 목표가에 도달했고, 안전마진이 충분한 경우
            if (item.current_price <= item.target_buy_price and 
                item.margin_of_safety.safety_level in [SafetyLevel.EXCELLENT, SafetyLevel.GOOD]):
                buy_signals.append(item)
        
        return buy_signals
    
    def generate_investment_report(self, symbol: str) -> str:
        """투자 철학 기반 분석 리포트 생성"""
        try:
            item = next((x for x in self.watchlist if x.symbol == symbol), None)
            if not item:
                return f"종목 {symbol}이 관심 목록에 없습니다."
            
            report = []
            report.append(f"\n=== {item.name} ({item.symbol}) 가치 투자 분석 ===")
            report.append("=" * 60)
            
            # 1. 기업 분석
            report.append(f"\n[1단계: 기업 분석]")
            report.append(f"비즈니스 모델 점수: {item.business_analysis.business_model_score:.1f}/100")
            report.append(f"경쟁 우위 점수: {item.business_analysis.competitive_advantage_score:.1f}/100")
            report.append(f"경영진 품질 점수: {item.business_analysis.management_quality_score:.1f}/100")
            report.append(f"재무 건전성 점수: {item.business_analysis.financial_strength_score:.1f}/100")
            report.append(f"성장 전망 점수: {item.business_analysis.growth_prospects_score:.1f}/100")
            
            # 경제적 해자
            if item.business_analysis.moats:
                report.append(f"\n경제적 해자:")
                for moat in item.business_analysis.moats:
                    report.append(f"  - {moat.moat_type.value}: {moat.strength:.1f}점 ({moat.description})")
            
            # 2. 내재가치 평가
            report.append(f"\n[2단계: 내재가치 평가]")
            report.append(f"보수적 추정치: {item.intrinsic_value.conservative_estimate:,.0f}원")
            report.append(f"공정가치: {item.intrinsic_value.fair_value:,.0f}원")
            report.append(f"낙관적 추정치: {item.intrinsic_value.optimistic_estimate:,.0f}원")
            report.append(f"신뢰도: {item.intrinsic_value.confidence_level:.1f}%")
            
            # 3. 안전마진
            report.append(f"\n[3단계: 안전마진 분석]")
            report.append(f"현재가: {item.margin_of_safety.current_price:,.0f}원")
            report.append(f"내재가치: {item.margin_of_safety.intrinsic_value:,.0f}원")
            report.append(f"할인율: {item.margin_of_safety.discount_percentage:.1f}%")
            report.append(f"안전마진 수준: {item.margin_of_safety.safety_level.value}")
            report.append(f"추천: {item.margin_of_safety.recommendation}")
            
            # 4. 투자 기질
            report.append(f"\n[4단계: 투자 기질]")
            report.append(f"현재 기질 점수: {self.temperament_score:.1f}/100")
            
            # 5. 최종 추천
            report.append(f"\n[최종 투자 추천]")
            if item.margin_of_safety.safety_level in [SafetyLevel.EXCELLENT, SafetyLevel.GOOD]:
                report.append("✅ 매수 추천 - 충분한 안전마진 확보")
            elif item.margin_of_safety.safety_level == SafetyLevel.ADEQUATE:
                report.append("⚠️ 신중한 매수 - 적정 안전마진")
            else:
                report.append("❌ 매수 보류 - 안전마진 부족")
            
            report.append(f"목표 매수가: {item.target_buy_price:,.0f}원")
            report.append("=" * 60)
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"투자 리포트 생성 실패: {e}")
            return f"리포트 생성 실패: {e}"
    
    # 내부 메서드들
    def _calculate_business_model_score(self, stock_data: Dict[str, Any]) -> float:
        """비즈니스 모델 점수 계산"""
        score = 50.0  # 기본 점수
        
        # 수익성 기반 점수
        roe = stock_data.get('financial_data', {}).get('roe', 0)
        if roe > 15:
            score += 20
        elif roe > 10:
            score += 15
        elif roe > 5:
            score += 10
        
        # 성장성 기반 점수
        revenue_growth = stock_data.get('financial_data', {}).get('revenue_growth_rate', 0)
        if revenue_growth > 10:
            score += 15
        elif revenue_growth > 5:
            score += 10
        elif revenue_growth > 0:
            score += 5
        
        # 안정성 기반 점수
        debt_ratio = stock_data.get('financial_data', {}).get('debt_ratio', 0)
        if debt_ratio < 30:
            score += 15
        elif debt_ratio < 50:
            score += 10
        elif debt_ratio < 100:
            score += 5
        
        return min(100, max(0, score))
    
    def _calculate_competitive_advantage_score(self, stock_data: Dict[str, Any]) -> float:
        """경쟁 우위 점수 계산"""
        score = 50.0
        
        # ROE가 높을수록 경쟁 우위
        roe = stock_data.get('financial_data', {}).get('roe', 0)
        if roe > 20:
            score += 25
        elif roe > 15:
            score += 20
        elif roe > 10:
            score += 15
        
        # 영업이익률이 높을수록 경쟁 우위
        operating_margin = stock_data.get('financial_data', {}).get('gross_profit_margin', 0)
        if operating_margin > 20:
            score += 25
        elif operating_margin > 15:
            score += 20
        elif operating_margin > 10:
            score += 15
        
        return min(100, max(0, score))
    
    def _calculate_management_quality_score(self, stock_data: Dict[str, Any]) -> float:
        """경영진 품질 점수 계산 (간접 추정)"""
        score = 50.0
        
        # ROE 일관성 (간접적으로 경영진 품질 반영)
        roe = stock_data.get('financial_data', {}).get('roe', 0)
        if roe > 15:
            score += 20
        elif roe > 10:
            score += 15
        elif roe > 5:
            score += 10
        
        # 부채 관리 (경영진의 신중함)
        debt_ratio = stock_data.get('financial_data', {}).get('debt_ratio', 0)
        if debt_ratio < 30:
            score += 20
        elif debt_ratio < 50:
            score += 15
        elif debt_ratio < 100:
            score += 10
        
        # 성장성 (경영진의 역량)
        revenue_growth = stock_data.get('financial_data', {}).get('revenue_growth_rate', 0)
        if revenue_growth > 10:
            score += 10
        elif revenue_growth > 5:
            score += 5
        
        return min(100, max(0, score))
    
    def _calculate_financial_strength_score(self, stock_data: Dict[str, Any]) -> float:
        """재무 건전성 점수 계산"""
        score = 50.0
        
        # 부채비율
        debt_ratio = stock_data.get('financial_data', {}).get('debt_ratio', 0)
        if debt_ratio < 30:
            score += 25
        elif debt_ratio < 50:
            score += 20
        elif debt_ratio < 100:
            score += 15
        elif debt_ratio < 150:
            score += 10
        
        # 유동비율
        current_ratio = stock_data.get('financial_data', {}).get('current_ratio', 0)
        if current_ratio > 2:
            score += 15
        elif current_ratio > 1.5:
            score += 10
        elif current_ratio > 1:
            score += 5
        
        # ROE
        roe = stock_data.get('financial_data', {}).get('roe', 0)
        if roe > 15:
            score += 10
        elif roe > 10:
            score += 5
        
        return min(100, max(0, score))
    
    def _calculate_growth_prospects_score(self, stock_data: Dict[str, Any]) -> float:
        """성장 전망 점수 계산"""
        score = 50.0
        
        # 매출 성장률
        revenue_growth = stock_data.get('financial_data', {}).get('revenue_growth_rate', 0)
        if revenue_growth > 15:
            score += 25
        elif revenue_growth > 10:
            score += 20
        elif revenue_growth > 5:
            score += 15
        elif revenue_growth > 0:
            score += 10
        
        # 영업이익 성장률
        operating_growth = stock_data.get('financial_data', {}).get('operating_income_growth_rate', 0)
        if operating_growth > 20:
            score += 25
        elif operating_growth > 10:
            score += 20
        elif operating_growth > 5:
            score += 15
        elif operating_growth > 0:
            score += 10
        
        return min(100, max(0, score))
    
    def _analyze_economic_moats(self, stock_data: Dict[str, Any]) -> List[EconomicMoat]:
        """경제적 해자 분석"""
        moats = []
        
        # ROE 기반 해자 (수익성 해자)
        roe = stock_data.get('financial_data', {}).get('roe', 0)
        if roe > 20:
            moats.append(EconomicMoat(
                moat_type=MoatType.INTANGIBLE_ASSETS,
                strength=roe,
                sustainability=80,
                description=f"높은 ROE({roe:.1f}%)로 인한 수익성 해자",
                evidence=[f"ROE {roe:.1f}%", "지속적인 고수익성"]
            ))
        
        # 브랜드 가치 (시가총액 대비 높은 수익성)
        market_cap = stock_data.get('market_cap', 0)
        net_profit = stock_data.get('financial_data', {}).get('net_profit_margin', 0)
        if market_cap > 10000 and net_profit > 15:  # 대기업이면서 높은 순이익률
            moats.append(EconomicMoat(
                moat_type=MoatType.INTANGIBLE_ASSETS,
                strength=net_profit,
                sustainability=70,
                description="브랜드 파워 기반 해자",
                evidence=[f"순이익률 {net_profit:.1f}%", "대기업 지위"]
            ))
        
        # 비용 우위 (낮은 부채비율과 높은 효율성)
        debt_ratio = stock_data.get('financial_data', {}).get('debt_ratio', 0)
        if debt_ratio < 30:
            moats.append(EconomicMoat(
                moat_type=MoatType.COST_ADVANTAGE,
                strength=100 - debt_ratio,
                sustainability=75,
                description="재무 건전성 기반 비용 우위",
                evidence=[f"부채비율 {debt_ratio:.1f}%", "낮은 자금 조달 비용"]
            ))
        
        return moats
    
    def _generate_business_description(self, stock_data: Dict[str, Any]) -> str:
        """비즈니스 설명 생성"""
        name = stock_data.get('name', '')
        sector = stock_data.get('sector_analysis', {}).get('grade', '')
        
        # 기본 설명
        description = f"{name}은(는) "
        
        # 섹터별 특성 추가
        if '전자' in name or '반도체' in name:
            description += "기술 집약적인 전자/반도체 업체로, "
        elif '화학' in name:
            description += "화학 소재 전문 기업으로, "
        elif '금융' in name or '은행' in name:
            description += "금융 서비스 제공업체로, "
        elif '자동차' in name:
            description += "자동차 관련 제조업체로, "
        else:
            description += "다양한 사업을 영위하는 기업으로, "
        
        # 재무 특성 추가
        roe = stock_data.get('financial_data', {}).get('roe', 0)
        if roe > 15:
            description += "높은 수익성을 바탕으로 "
        elif roe > 10:
            description += "양호한 수익성을 바탕으로 "
        
        description += "지속적인 성장을 추구하고 있습니다."
        
        return description
    
    def _analyze_revenue_sources(self, stock_data: Dict[str, Any]) -> List[str]:
        """수익원 분석"""
        sources = []
        
        # 섹터 기반 수익원 추정
        name = stock_data.get('name', '')
        if '전자' in name or '반도체' in name:
            sources.extend(["제품 판매", "기술 라이선스", "서비스"])
        elif '화학' in name:
            sources.extend(["화학 제품 판매", "원자재 공급"])
        elif '금융' in name:
            sources.extend(["대출 이자", "수수료 수익", "투자 수익"])
        else:
            sources.extend(["제품/서비스 판매", "기타 수익"])
        
        return sources
    
    def _identify_key_risks(self, stock_data: Dict[str, Any]) -> List[str]:
        """주요 리스크 식별"""
        risks = []
        
        # 부채비율 기반 리스크
        debt_ratio = stock_data.get('financial_data', {}).get('debt_ratio', 0)
        if debt_ratio > 100:
            risks.append("높은 부채비율로 인한 재무 리스크")
        
        # 성장률 기반 리스크
        revenue_growth = stock_data.get('financial_data', {}).get('revenue_growth_rate', 0)
        if revenue_growth < 0:
            risks.append("매출 감소로 인한 성장성 리스크")
        
        # 수익성 기반 리스크
        roe = stock_data.get('financial_data', {}).get('roe', 0)
        if roe < 5:
            risks.append("낮은 수익성으로 인한 경쟁력 리스크")
        
        # 일반적 리스크
        risks.extend([
            "경기 변동성 리스크",
            "경쟁 심화 리스크",
            "규제 변화 리스크"
        ])
        
        return risks
    
    def _calculate_dcf_value(self, stock_data: Dict[str, Any]) -> float:
        """DCF 모델 기반 내재가치 계산"""
        try:
            # 간단한 DCF 계산 (실제로는 더 복잡한 모델 필요)
            current_price = stock_data.get('current_price', 0)
            eps = stock_data.get('price_data', {}).get('eps', 0)
            growth_rate = stock_data.get('financial_data', {}).get('revenue_growth_rate', 0)
            
            if eps > 0 and growth_rate > 0:
                # 간단한 성장률 적용
                future_eps = eps * (1 + growth_rate / 100) ** 5  # 5년 후
                # 15배 PER 적용 (보수적)
                dcf_value = future_eps * 15
                return dcf_value
            else:
                return current_price * 1.2  # 20% 프리미엄
                
        except Exception:
            return 0
    
    def _calculate_relative_value(self, stock_data: Dict[str, Any]) -> float:
        """상대가치 평가"""
        try:
            current_price = stock_data.get('current_price', 0)
            per = stock_data.get('price_data', {}).get('per', 0)
            
            if per > 0:
                # 업종 평균 PER 12배 기준
                fair_per = 12
                relative_value = current_price * (fair_per / per)
                return relative_value
            else:
                return current_price
                
        except Exception:
            return 0
    
    def _calculate_asset_value(self, stock_data: Dict[str, Any]) -> float:
        """자산가치 기반 평가"""
        try:
            current_price = stock_data.get('current_price', 0)
            pbr = stock_data.get('price_data', {}).get('pbr', 0)
            
            if pbr > 0:
                # 공정 PBR 1.5배 기준
                fair_pbr = 1.5
                asset_value = current_price * (fair_pbr / pbr)
                return asset_value
            else:
                return current_price
                
        except Exception:
            return 0
    
    def _calculate_confidence_level(self, stock_data: Dict[str, Any]) -> float:
        """신뢰도 계산"""
        confidence = 50.0  # 기본 신뢰도
        
        # 데이터 완성도
        financial_data = stock_data.get('financial_data', {})
        price_data = stock_data.get('price_data', {})
        
        if financial_data and price_data:
            confidence += 20
        
        # 재무 지표의 합리성
        roe = financial_data.get('roe', 0)
        if 5 <= roe <= 30:  # 합리적인 ROE 범위
            confidence += 15
        
        debt_ratio = financial_data.get('debt_ratio', 0)
        if debt_ratio < 100:  # 합리적인 부채비율
            confidence += 15
        
        return min(100, confidence)
    
    def _assess_patience(self, investment_history: List[Dict[str, Any]]) -> float:
        """인내심 평가"""
        # 실제 구현에서는 투자 이력을 분석
        # 여기서는 기본값 반환
        return 70.0
    
    def _assess_competence_range(self, investment_history: List[Dict[str, Any]]) -> float:
        """능력 범위 준수 평가"""
        # 실제 구현에서는 투자 분야의 집중도 분석
        # 여기서는 기본값 반환
        return 75.0
    
    def _assess_contrarian_thinking(self, investment_history: List[Dict[str, Any]]) -> float:
        """역발상적 사고 평가"""
        # 실제 구현에서는 시장 상황과 투자 타이밍 분석
        # 여기서는 기본값 반환
        return 65.0

# 전역 인스턴스
value_investing = ValueInvestingPhilosophy()

# 편의 함수들
def analyze_business_model(stock_data: Dict[str, Any]) -> BusinessAnalysis:
    """비즈니스 모델 분석"""
    return value_investing.analyze_business_model(stock_data)

def calculate_intrinsic_value(stock_data: Dict[str, Any]) -> IntrinsicValue:
    """내재가치 계산"""
    return value_investing.calculate_intrinsic_value(stock_data)

def calculate_margin_of_safety(current_price: float, intrinsic_value: IntrinsicValue) -> MarginOfSafety:
    """안전마진 계산"""
    return value_investing.calculate_margin_of_safety(current_price, intrinsic_value)

def add_to_watchlist(symbol: str, name: str, stock_data: Dict[str, Any]) -> InvestmentWatchlist:
    """관심 종목 추가"""
    return value_investing.add_to_watchlist(symbol, name, stock_data)

def get_buy_signals() -> List[InvestmentWatchlist]:
    """매수 신호 조회"""
    return value_investing.get_buy_signals()

def generate_investment_report(symbol: str) -> str:
    """투자 리포트 생성"""
    return value_investing.generate_investment_report(symbol)


