"""
향상된 점수 계산기 모듈

종합 점수 계산을 담당하는 EnhancedScoreCalculator를 제공합니다.
"""

import logging
from typing import Any, Dict, List, Optional

from abc import ABC, abstractmethod
from utils.metrics import MetricsCollector


class ScoreCalculator(ABC):
    """점수 계산기 추상 클래스"""
    
    @abstractmethod
    def calculate_score(self, data: Dict[str, Any]) -> float:
        """점수 계산"""
        pass


class EnhancedScoreCalculator(ScoreCalculator):
    """향상된 점수 계산기 (종합 점수)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        
        # 점수 가중치 설정
        self.score_weights = {
            'value_score': 0.35,      # 가치 점수 35%
            'quality_score': 0.25,    # 품질 점수 25%
            'growth_score': 0.15,     # 성장 점수 15%
            'safety_score': 0.15,     # 안전 점수 15%
            'momentum_score': 0.10    # 모멘텀 점수 10%
        }
        
        # 점수 범위 설정
        self.score_ranges = {
            'excellent': (90, 100),
            'good': (80, 89),
            'average': (70, 79),
            'below_average': (60, 69),
            'poor': (0, 59)
        }
    
    def calculate_score(self, data: Dict[str, Any], sector_info: Dict[str, Any] = None, price_data: Dict[str, Any] = None) -> tuple:
        """
        종합 점수 계산
        
        Args:
            data: 분석 데이터 딕셔너리
            sector_info: 섹터 분석 정보 (선택적)
            price_data: 가격 데이터 (선택적)
        
        Returns:
            tuple: (종합 점수, 세부 점수 breakdown)
        """
        try:
            # 각 구성 요소 점수 계산
            value_score = self._calculate_value_score(data)
            quality_score = self._calculate_quality_score(data)
            growth_score = self._calculate_growth_score(data)
            safety_score = self._calculate_safety_score(data)
            momentum_score = self._calculate_momentum_score(data)
            
            # 가중 평균 계산
            total_score = (
                value_score * self.score_weights['value_score'] +
                quality_score * self.score_weights['quality_score'] +
                growth_score * self.score_weights['growth_score'] +
                safety_score * self.score_weights['safety_score'] +
                momentum_score * self.score_weights['momentum_score']
            )
            
            # 점수 범위 제한 (0~100)
            final_score = max(0, min(100, total_score))
            
            # 세부 점수 breakdown 생성
            breakdown = {
                'value_score': value_score,
                'quality_score': quality_score,
                'growth_score': growth_score,
                'safety_score': safety_score,
                'momentum_score': momentum_score,
                'total_score': final_score
            }
            
            # 메트릭 기록
            if self.metrics:
                self.metrics.record_score_calculations(1)
            
            return final_score, breakdown
            
        except Exception as e:
            logging.error(f"점수 계산 실패: {e}")
            if self.metrics:
                self.metrics.record_score_calculation_errors(1)
            return 0.0, {}
    
    def _calculate_value_score(self, data: Dict[str, Any]) -> float:
        """가치 점수 계산 (0~100)"""
        try:
            # 가치 관련 지표들
            pe_ratio = data.get('pe_ratio', 0)
            pb_ratio = data.get('pb_ratio', 0)
            ev_ebit = data.get('ev_ebit', 0)
            dividend_yield = data.get('dividend_yield', 0)
            
            # PE 비율 점수 (낮을수록 좋음)
            if pe_ratio <= 10:
                pe_score = 100
            elif pe_ratio <= 15:
                pe_score = 80
            elif pe_ratio <= 20:
                pe_score = 60
            elif pe_ratio <= 30:
                pe_score = 40
            else:
                pe_score = 20
            
            # PB 비율 점수 (낮을수록 좋음)
            if pb_ratio <= 1.0:
                pb_score = 100
            elif pb_ratio <= 1.5:
                pb_score = 80
            elif pb_ratio <= 2.0:
                pb_score = 60
            elif pb_ratio <= 3.0:
                pb_score = 40
            else:
                pb_score = 20
            
            # EV/EBIT 점수 (낮을수록 좋음)
            if ev_ebit <= 8:
                ev_ebit_score = 100
            elif ev_ebit <= 12:
                ev_ebit_score = 80
            elif ev_ebit <= 16:
                ev_ebit_score = 60
            elif ev_ebit <= 24:
                ev_ebit_score = 40
            else:
                ev_ebit_score = 20
            
            # 배당 수익률 점수 (높을수록 좋음)
            if dividend_yield >= 0.05:  # 5% 이상
                div_score = 100
            elif dividend_yield >= 0.03:  # 3% 이상
                div_score = 80
            elif dividend_yield >= 0.02:  # 2% 이상
                div_score = 60
            elif dividend_yield >= 0.01:  # 1% 이상
                div_score = 40
            else:
                div_score = 20
            
            # 가중 평균
            value_score = (
                pe_score * 0.3 +
                pb_score * 0.3 +
                ev_ebit_score * 0.3 +
                div_score * 0.1
            )
            
            return value_score
            
        except Exception as e:
            logging.warning(f"가치 점수 계산 실패: {e}")
            return 0.0
    
    def _calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """품질 점수 계산 (0~100)"""
        try:
            # 품질 관련 지표들
            roe = data.get('roe', 0)
            roa = data.get('roa', 0)
            current_ratio = data.get('current_ratio', 0)
            debt_to_equity = data.get('debt_to_equity', 0)
            interest_coverage = data.get('interest_coverage', 0)
            
            # ROE 점수 (높을수록 좋음)
            if roe >= 0.20:  # 20% 이상
                roe_score = 100
            elif roe >= 0.15:  # 15% 이상
                roe_score = 80
            elif roe >= 0.10:  # 10% 이상
                roe_score = 60
            elif roe >= 0.05:  # 5% 이상
                roe_score = 40
            else:
                roe_score = 20
            
            # ROA 점수 (높을수록 좋음)
            if roa >= 0.10:  # 10% 이상
                roa_score = 100
            elif roa >= 0.08:  # 8% 이상
                roa_score = 80
            elif roa >= 0.05:  # 5% 이상
                roa_score = 60
            elif roa >= 0.03:  # 3% 이상
                roa_score = 40
            else:
                roa_score = 20
            
            # 유동비율 점수 (높을수록 좋음)
            if current_ratio >= 2.0:
                current_score = 100
            elif current_ratio >= 1.5:
                current_score = 80
            elif current_ratio >= 1.2:
                current_score = 60
            elif current_ratio >= 1.0:
                current_score = 40
            else:
                current_score = 20
            
            # 부채비율 점수 (낮을수록 좋음)
            if debt_to_equity <= 0.3:
                debt_score = 100
            elif debt_to_equity <= 0.5:
                debt_score = 80
            elif debt_to_equity <= 0.8:
                debt_score = 60
            elif debt_to_equity <= 1.2:
                debt_score = 40
            else:
                debt_score = 20
            
            # 이자보상배율 점수 (높을수록 좋음)
            if interest_coverage >= 5.0:
                interest_score = 100
            elif interest_coverage >= 3.0:
                interest_score = 80
            elif interest_coverage >= 2.0:
                interest_score = 60
            elif interest_coverage >= 1.5:
                interest_score = 40
            else:
                interest_score = 20
            
            # 가중 평균
            quality_score = (
                roe_score * 0.25 +
                roa_score * 0.25 +
                current_score * 0.2 +
                debt_score * 0.2 +
                interest_score * 0.1
            )
            
            return quality_score
            
        except Exception as e:
            logging.warning(f"품질 점수 계산 실패: {e}")
            return 0.0
    
    def _calculate_growth_score(self, data: Dict[str, Any]) -> float:
        """성장 점수 계산 (0~100)"""
        try:
            # 성장 관련 지표들
            eps_growth = data.get('eps_growth', 0)
            revenue_growth = data.get('revenue_growth', 0)
            book_value_growth = data.get('book_value_growth', 0)
            
            # EPS 성장률 점수
            if eps_growth >= 0.20:  # 20% 이상
                eps_score = 100
            elif eps_growth >= 0.15:  # 15% 이상
                eps_score = 80
            elif eps_growth >= 0.10:  # 10% 이상
                eps_score = 60
            elif eps_growth >= 0.05:  # 5% 이상
                eps_score = 40
            else:
                eps_score = 20
            
            # 매출 성장률 점수
            if revenue_growth >= 0.15:  # 15% 이상
                revenue_score = 100
            elif revenue_growth >= 0.10:  # 10% 이상
                revenue_score = 80
            elif revenue_growth >= 0.05:  # 5% 이상
                revenue_score = 60
            elif revenue_growth >= 0.02:  # 2% 이상
                revenue_score = 40
            else:
                revenue_score = 20
            
            # 순자산 성장률 점수
            if book_value_growth >= 0.15:  # 15% 이상
                bv_score = 100
            elif book_value_growth >= 0.10:  # 10% 이상
                bv_score = 80
            elif book_value_growth >= 0.05:  # 5% 이상
                bv_score = 60
            elif book_value_growth >= 0.02:  # 2% 이상
                bv_score = 40
            else:
                bv_score = 20
            
            # 가중 평균
            growth_score = (
                eps_score * 0.5 +
                revenue_score * 0.3 +
                bv_score * 0.2
            )
            
            return growth_score
            
        except Exception as e:
            logging.warning(f"성장 점수 계산 실패: {e}")
            return 0.0
    
    def _calculate_safety_score(self, data: Dict[str, Any]) -> float:
        """안전 점수 계산 (0~100)"""
        try:
            # 안전 관련 지표들
            beta = data.get('beta', 1.0)
            volatility = data.get('volatility', 0)
            margin_of_safety = data.get('margin_of_safety', 0)
            altman_z_score = data.get('altman_z_score', 0)
            
            # 베타 점수 (낮을수록 좋음)
            if beta <= 0.8:
                beta_score = 100
            elif beta <= 1.0:
                beta_score = 80
            elif beta <= 1.2:
                beta_score = 60
            elif beta <= 1.5:
                beta_score = 40
            else:
                beta_score = 20
            
            # 변동성 점수 (낮을수록 좋음)
            if volatility <= 0.20:  # 20% 이하
                vol_score = 100
            elif volatility <= 0.30:  # 30% 이하
                vol_score = 80
            elif volatility <= 0.40:  # 40% 이하
                vol_score = 60
            elif volatility <= 0.50:  # 50% 이하
                vol_score = 40
            else:
                vol_score = 20
            
            # 안전마진 점수 (높을수록 좋음)
            if margin_of_safety >= 0.30:  # 30% 이상
                mos_score = 100
            elif margin_of_safety >= 0.20:  # 20% 이상
                mos_score = 80
            elif margin_of_safety >= 0.15:  # 15% 이상
                mos_score = 60
            elif margin_of_safety >= 0.10:  # 10% 이상
                mos_score = 40
            else:
                mos_score = 20
            
            # 알트만 Z-점수 점수 (높을수록 좋음)
            if altman_z_score >= 3.0:
                altman_score = 100
            elif altman_z_score >= 2.5:
                altman_score = 80
            elif altman_z_score >= 2.0:
                altman_score = 60
            elif altman_z_score >= 1.8:
                altman_score = 40
            else:
                altman_score = 20
            
            # 가중 평균
            safety_score = (
                beta_score * 0.25 +
                vol_score * 0.25 +
                mos_score * 0.3 +
                altman_score * 0.2
            )
            
            return safety_score
            
        except Exception as e:
            logging.warning(f"안전 점수 계산 실패: {e}")
            return 0.0
    
    def _calculate_momentum_score(self, data: Dict[str, Any]) -> float:
        """모멘텀 점수 계산 (0~100)"""
        try:
            # 모멘텀 관련 지표들
            price_change_1m = data.get('price_change_1m', 0)
            price_change_3m = data.get('price_change_3m', 0)
            price_change_6m = data.get('price_change_6m', 0)
            relative_strength = data.get('relative_strength', 0)
            
            # 1개월 가격 변동률 점수
            if price_change_1m >= 0.10:  # 10% 이상
                momentum_1m_score = 100
            elif price_change_1m >= 0.05:  # 5% 이상
                momentum_1m_score = 80
            elif price_change_1m >= 0.0:  # 0% 이상
                momentum_1m_score = 60
            elif price_change_1m >= -0.05:  # -5% 이상
                momentum_1m_score = 40
            else:
                momentum_1m_score = 20
            
            # 3개월 가격 변동률 점수
            if price_change_3m >= 0.20:  # 20% 이상
                momentum_3m_score = 100
            elif price_change_3m >= 0.10:  # 10% 이상
                momentum_3m_score = 80
            elif price_change_3m >= 0.0:  # 0% 이상
                momentum_3m_score = 60
            elif price_change_3m >= -0.10:  # -10% 이상
                momentum_3m_score = 40
            else:
                momentum_3m_score = 20
            
            # 6개월 가격 변동률 점수
            if price_change_6m >= 0.30:  # 30% 이상
                momentum_6m_score = 100
            elif price_change_6m >= 0.15:  # 15% 이상
                momentum_6m_score = 80
            elif price_change_6m >= 0.0:  # 0% 이상
                momentum_6m_score = 60
            elif price_change_6m >= -0.15:  # -15% 이상
                momentum_6m_score = 40
            else:
                momentum_6m_score = 20
            
            # 상대강도 점수
            if relative_strength >= 70:
                rs_score = 100
            elif relative_strength >= 60:
                rs_score = 80
            elif relative_strength >= 50:
                rs_score = 60
            elif relative_strength >= 40:
                rs_score = 40
            else:
                rs_score = 20
            
            # 가중 평균
            momentum_score = (
                momentum_1m_score * 0.2 +
                momentum_3m_score * 0.3 +
                momentum_6m_score * 0.3 +
                rs_score * 0.2
            )
            
            return momentum_score
            
        except Exception as e:
            logging.warning(f"모멘텀 점수 계산 실패: {e}")
            return 0.0
    
    def get_score_breakdown(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """점수 세부 내역 반환"""
        try:
            breakdown = {
                'value_score': self._calculate_value_score(data),
                'quality_score': self._calculate_quality_score(data),
                'growth_score': self._calculate_growth_score(data),
                'safety_score': self._calculate_safety_score(data),
                'momentum_score': self._calculate_momentum_score(data),
                'total_score': self.calculate_score(data),
                'weights': self.score_weights
            }
            
            # 점수 등급 계산
            total_score = breakdown['total_score']
            for grade, (min_score, max_score) in self.score_ranges.items():
                if min_score <= total_score <= max_score:
                    breakdown['grade'] = grade
                    break
            else:
                breakdown['grade'] = 'unknown'
            
            return breakdown
            
        except Exception as e:
            logging.error(f"점수 세부 내역 계산 실패: {e}")
            return {}
    
    def get_score_recommendation(self, total_score: float) -> str:
        """점수 기반 투자 권고사항"""
        if total_score >= 90:
            return "강력 매수 (Excellent)"
        elif total_score >= 80:
            return "매수 (Good)"
        elif total_score >= 70:
            return "보통 (Average)"
        elif total_score >= 60:
            return "신중 (Below Average)"
        else:
            return "매도 (Poor)"



