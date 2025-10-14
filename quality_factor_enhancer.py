#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
품질 팩터 강화 모듈
필수 최소치와 소프트 감점을 동시 적용하여 회계 노이즈·섹터 차이에 견고한 평가
"""

import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class QualityThresholds:
    """품질 기준 임계값"""
    # 필수 최소치 (하드 탈락)
    min_roe: float = 3.0  # ROE 최소 3%
    min_current_ratio: float = 0.8  # 유동비율 최소 0.8
    max_debt_ratio: float = 200.0  # 부채비율 최대 200%
    
    # 소프트 감점 기준 (점진적 감점)
    good_roe: float = 8.0  # ROE 8% 이상이면 좋음
    excellent_roe: float = 15.0  # ROE 15% 이상이면 우수
    
    good_current_ratio: float = 1.2  # 유동비율 1.2 이상이면 좋음
    excellent_current_ratio: float = 2.0  # 유동비율 2.0 이상이면 우수
    
    good_debt_ratio: float = 100.0  # 부채비율 100% 이하면 좋음
    excellent_debt_ratio: float = 50.0  # 부채비율 50% 이하면 우수

@dataclass
class QualityScore:
    """품질 점수 결과"""
    total_score: float  # 총 품질 점수 (0-100)
    roe_score: float    # ROE 점수
    liquidity_score: float  # 유동성 점수
    leverage_score: float   # 레버리지 점수
    stability_score: float  # 안정성 점수
    penalties: List[str]    # 감점 사유
    warnings: List[str]     # 경고 사유
    is_hard_reject: bool    # 하드 탈락 여부

class QualityFactorEnhancer:
    """품질 팩터 강화 클래스"""
    
    def __init__(self, thresholds: Optional[QualityThresholds] = None):
        """
        Args:
            thresholds: 품질 기준 임계값 (None이면 기본값 사용)
        """
        self.thresholds = thresholds or QualityThresholds()
        
        # 섹터별 품질 기준 조정 (섹터 특성 반영)
        self.sector_adjustments = {
            '금융': {
                'min_roe': 5.0,  # 금융업은 ROE 기준 상향
                'max_debt_ratio': 1000.0,  # 금융업은 부채비율 기준 완화
                'good_debt_ratio': 500.0,
                'excellent_debt_ratio': 200.0
            },
            '건설': {
                'min_current_ratio': 1.0,  # 건설업은 유동성 기준 상향
                'good_current_ratio': 1.5,
                'excellent_current_ratio': 2.5
            },
            '제조업': {
                'min_roe': 4.0,  # 제조업은 ROE 기준 약간 상향
                'good_roe': 10.0,
                'excellent_roe': 18.0
            },
            'IT': {
                'min_roe': 2.0,  # IT업은 ROE 기준 완화 (성장기업)
                'good_roe': 6.0,
                'excellent_roe': 12.0,
                'max_debt_ratio': 150.0,  # IT업은 부채비율 기준 강화
                'good_debt_ratio': 80.0,
                'excellent_debt_ratio': 40.0
            }
        }
    
    def evaluate_quality(self, stock_data: Dict[str, Any], sector: str = '') -> QualityScore:
        """
        종목의 품질을 종합 평가
        
        Args:
            stock_data: 종목 데이터
            sector: 섹터명 (섹터별 기준 조정용)
            
        Returns:
            QualityScore: 품질 점수 결과
        """
        try:
            # 섹터별 기준 조정
            adjusted_thresholds = self._get_sector_adjusted_thresholds(sector)
            
            # 1. 필수 최소치 검사 (하드 탈락)
            hard_reject, reject_reasons = self._check_hard_thresholds(stock_data, adjusted_thresholds)
            
            if hard_reject:
                return QualityScore(
                    total_score=0.0,
                    roe_score=0.0,
                    liquidity_score=0.0,
                    leverage_score=0.0,
                    stability_score=0.0,
                    penalties=reject_reasons,
                    warnings=[],
                    is_hard_reject=True
                )
            
            # 2. 소프트 감점 평가
            roe_score, roe_penalties = self._evaluate_roe_quality(stock_data, adjusted_thresholds)
            liquidity_score, liquidity_penalties = self._evaluate_liquidity_quality(stock_data, adjusted_thresholds)
            leverage_score, leverage_penalties = self._evaluate_leverage_quality(stock_data, adjusted_thresholds)
            stability_score, stability_penalties = self._evaluate_stability_quality(stock_data, adjusted_thresholds)
            
            # 3. 종합 점수 계산 (가중평균)
            total_score = (
                roe_score * 0.35 +        # ROE 35%
                liquidity_score * 0.25 +  # 유동성 25%
                leverage_score * 0.25 +   # 레버리지 25%
                stability_score * 0.15    # 안정성 15%
            )
            
            # 4. 모든 감점 사유 수집
            all_penalties = roe_penalties + liquidity_penalties + leverage_penalties + stability_penalties
            
            return QualityScore(
                total_score=total_score,
                roe_score=roe_score,
                liquidity_score=liquidity_score,
                leverage_score=leverage_score,
                stability_score=stability_score,
                penalties=all_penalties,
                warnings=[],
                is_hard_reject=False
            )
            
        except Exception as e:
            logger.warning(f"품질 평가 중 오류: {e}")
            return QualityScore(
                total_score=50.0,  # 중립 점수
                roe_score=50.0,
                liquidity_score=50.0,
                leverage_score=50.0,
                stability_score=50.0,
                penalties=[f"품질 평가 오류: {e}"],
                warnings=[],
                is_hard_reject=False
            )
    
    def _get_sector_adjusted_thresholds(self, sector: str) -> QualityThresholds:
        """섹터별 기준 조정"""
        if not sector or sector not in self.sector_adjustments:
            return self.thresholds
        
        adjustments = self.sector_adjustments[sector]
        adjusted = QualityThresholds(
            min_roe=adjustments.get('min_roe', self.thresholds.min_roe),
            min_current_ratio=adjustments.get('min_current_ratio', self.thresholds.min_current_ratio),
            max_debt_ratio=adjustments.get('max_debt_ratio', self.thresholds.max_debt_ratio),
            good_roe=adjustments.get('good_roe', self.thresholds.good_roe),
            excellent_roe=adjustments.get('excellent_roe', self.thresholds.excellent_roe),
            good_current_ratio=adjustments.get('good_current_ratio', self.thresholds.good_current_ratio),
            excellent_current_ratio=adjustments.get('excellent_current_ratio', self.thresholds.excellent_current_ratio),
            good_debt_ratio=adjustments.get('good_debt_ratio', self.thresholds.good_debt_ratio),
            excellent_debt_ratio=adjustments.get('excellent_debt_ratio', self.thresholds.excellent_debt_ratio)
        )
        
        return adjusted
    
    def _check_hard_thresholds(self, stock_data: Dict[str, Any], thresholds: QualityThresholds) -> Tuple[bool, List[str]]:
        """필수 최소치 검사 (하드 탈락)"""
        reject_reasons = []
        
        # ROE 최소 기준
        roe = stock_data.get('roe', 0)
        if roe < thresholds.min_roe:
            reject_reasons.append(f"ROE {roe:.1f}% < 최소 기준 {thresholds.min_roe}%")
        
        # 유동비율 최소 기준
        current_ratio = stock_data.get('current_ratio', 0)
        if current_ratio > 0 and current_ratio < thresholds.min_current_ratio:
            reject_reasons.append(f"유동비율 {current_ratio:.2f} < 최소 기준 {thresholds.min_current_ratio}")
        
        # 부채비율 최대 기준
        debt_ratio = stock_data.get('debt_ratio', 0)
        if debt_ratio > 0 and debt_ratio > thresholds.max_debt_ratio:
            reject_reasons.append(f"부채비율 {debt_ratio:.1f}% > 최대 기준 {thresholds.max_debt_ratio}%")
        
        return len(reject_reasons) > 0, reject_reasons
    
    def _evaluate_roe_quality(self, stock_data: Dict[str, Any], thresholds: QualityThresholds) -> Tuple[float, List[str]]:
        """ROE 품질 평가 (소프트 감점)"""
        roe = stock_data.get('roe', 0)
        penalties = []
        
        if roe <= 0:
            return 0.0, ["ROE 음수 또는 0"]
        
        # 점진적 점수 계산
        if roe >= thresholds.excellent_roe:
            score = 100.0
        elif roe >= thresholds.good_roe:
            # 8% ~ 15% 구간: 선형 보간
            ratio = (roe - thresholds.good_roe) / (thresholds.excellent_roe - thresholds.good_roe)
            score = 70.0 + (ratio * 30.0)  # 70점 ~ 100점
        elif roe >= thresholds.min_roe:
            # 3% ~ 8% 구간: 선형 보간
            ratio = (roe - thresholds.min_roe) / (thresholds.good_roe - thresholds.min_roe)
            score = 30.0 + (ratio * 40.0)  # 30점 ~ 70점
        else:
            score = 0.0
            penalties.append(f"ROE {roe:.1f}% 낮음")
        
        return score, penalties
    
    def _evaluate_liquidity_quality(self, stock_data: Dict[str, Any], thresholds: QualityThresholds) -> Tuple[float, List[str]]:
        """유동성 품질 평가 (소프트 감점)"""
        current_ratio = stock_data.get('current_ratio', 0)
        penalties = []
        
        if current_ratio <= 0:
            return 50.0, ["유동비율 데이터 없음"]
        
        # 점진적 점수 계산
        if current_ratio >= thresholds.excellent_current_ratio:
            score = 100.0
        elif current_ratio >= thresholds.good_current_ratio:
            # 1.2 ~ 2.0 구간: 선형 보간
            ratio = (current_ratio - thresholds.good_current_ratio) / (thresholds.excellent_current_ratio - thresholds.good_current_ratio)
            score = 70.0 + (ratio * 30.0)  # 70점 ~ 100점
        elif current_ratio >= thresholds.min_current_ratio:
            # 0.8 ~ 1.2 구간: 선형 보간
            ratio = (current_ratio - thresholds.min_current_ratio) / (thresholds.good_current_ratio - thresholds.min_current_ratio)
            score = 30.0 + (ratio * 40.0)  # 30점 ~ 70점
        else:
            score = 0.0
            penalties.append(f"유동비율 {current_ratio:.2f} 낮음")
        
        return score, penalties
    
    def _evaluate_leverage_quality(self, stock_data: Dict[str, Any], thresholds: QualityThresholds) -> Tuple[float, List[str]]:
        """레버리지 품질 평가 (소프트 감점)"""
        debt_ratio = stock_data.get('debt_ratio', 0)
        penalties = []
        
        if debt_ratio <= 0:
            return 50.0, ["부채비율 데이터 없음"]
        
        # 점진적 점수 계산 (부채비율은 낮을수록 좋음)
        if debt_ratio <= thresholds.excellent_debt_ratio:
            score = 100.0
        elif debt_ratio <= thresholds.good_debt_ratio:
            # 50% ~ 100% 구간: 선형 보간
            ratio = (thresholds.good_debt_ratio - debt_ratio) / (thresholds.good_debt_ratio - thresholds.excellent_debt_ratio)
            score = 70.0 + (ratio * 30.0)  # 70점 ~ 100점
        elif debt_ratio <= thresholds.max_debt_ratio:
            # 100% ~ 200% 구간: 선형 보간
            ratio = (thresholds.max_debt_ratio - debt_ratio) / (thresholds.max_debt_ratio - thresholds.good_debt_ratio)
            score = 30.0 + (ratio * 40.0)  # 30점 ~ 70점
        else:
            score = 0.0
            penalties.append(f"부채비율 {debt_ratio:.1f}% 높음")
        
        return score, penalties
    
    def _evaluate_stability_quality(self, stock_data: Dict[str, Any], thresholds: QualityThresholds) -> Tuple[float, List[str]]:
        """안정성 품질 평가 (소프트 감점)"""
        # 안정성 지표들 (추가 지표가 있으면 활용)
        penalties = []
        score = 50.0  # 기본 점수
        
        # 배당수익률 (있는 경우)
        dividend_yield = stock_data.get('dividend_yield', 0)
        if dividend_yield > 0:
            if dividend_yield >= 3.0:
                score += 20.0  # 배당수익률 3% 이상이면 보너스
            elif dividend_yield >= 1.0:
                score += 10.0  # 배당수익률 1% 이상이면 소폭 보너스
        
        # 시가총액 (대형주일수록 안정성 높음)
        market_cap = stock_data.get('market_cap', 0)
        if market_cap > 0:
            if market_cap >= 1e13:  # 10조원 이상
                score += 15.0
            elif market_cap >= 1e12:  # 1조원 이상
                score += 10.0
            elif market_cap >= 1e11:  # 1000억원 이상
                score += 5.0
        
        # 점수 클램핑
        score = max(0.0, min(100.0, score))
        
        return score, penalties
    
    def get_quality_recommendation(self, quality_score: QualityScore) -> str:
        """품질 점수 기반 추천 등급"""
        if quality_score.is_hard_reject:
            return "REJECT"
        
        total_score = quality_score.total_score
        
        if total_score >= 80.0:
            return "EXCELLENT"
        elif total_score >= 65.0:
            return "GOOD"
        elif total_score >= 50.0:
            return "FAIR"
        elif total_score >= 35.0:
            return "POOR"
        else:
            return "VERY_POOR"
    
    def format_quality_report(self, quality_score: QualityScore, stock_name: str = "") -> str:
        """품질 평가 보고서 포맷팅"""
        report = []
        
        if stock_name:
            report.append(f"📊 {stock_name} 품질 평가")
        
        report.append(f"총 품질 점수: {quality_score.total_score:.1f}/100")
        
        if quality_score.is_hard_reject:
            report.append("❌ 하드 탈락 (필수 기준 미달)")
            for penalty in quality_score.penalties:
                report.append(f"  • {penalty}")
        else:
            report.append("✅ 소프트 감점 평가")
            report.append(f"  • ROE 점수: {quality_score.roe_score:.1f}/100")
            report.append(f"  • 유동성 점수: {quality_score.liquidity_score:.1f}/100")
            report.append(f"  • 레버리지 점수: {quality_score.leverage_score:.1f}/100")
            report.append(f"  • 안정성 점수: {quality_score.stability_score:.1f}/100")
            
            if quality_score.penalties:
                report.append("⚠️ 감점 사유:")
                for penalty in quality_score.penalties:
                    report.append(f"  • {penalty}")
        
        return "\n".join(report)


# 사용 예시
if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    enhancer = QualityFactorEnhancer()
    
    # 테스트 데이터
    test_stock = {
        'roe': 12.5,
        'current_ratio': 1.8,
        'debt_ratio': 85.0,
        'dividend_yield': 2.5,
        'market_cap': 5e12  # 5조원
    }
    
    # 품질 평가
    quality_score = enhancer.evaluate_quality(test_stock, sector='제조업')
    
    # 결과 출력
    print(enhancer.format_quality_report(quality_score, "테스트 종목"))
    print(f"추천 등급: {enhancer.get_quality_recommendation(quality_score)}")
