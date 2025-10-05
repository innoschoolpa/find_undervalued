"""
가치주 스타일 분류기 모듈

저평가 vs 가치주를 구분하는 스타일 분류기를 제공합니다.
"""

import logging
from typing import Any, Dict

from metrics import MetricsCollector


class ValueStyleClassifier:
    """가치주 스타일 분류기 (저평가 vs 가치주 구분)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
    
    def classify_value_style(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        가치주 스타일 분류
        
        Args:
            metrics: 분석 메트릭 딕셔너리
                - valuation_pct: 섹터 상대 가치 퍼센타일 (0~100)
                - mos: 안전마진 (0.30 = 30%)
                - price_pos: 52주 가격위치 (0~1)
                - roic_z, f_score, accruals_risk: 품질 신호
                - eps_cagr, rev_cagr: 성장성
                - earnings_vol_sigma, interest_cov: 변동성/지급능력
                - ev_ebit: EV/EBIT 배수
        
        Returns:
            Dict: style_label, style_reasons, confidence_score
        """
        result = {
            'style_label': 'Not Value',
            'style_reasons': [],
            'confidence_score': 0.0
        }
        
        try:
            # 필수 메트릭 추출
            v = metrics.get('valuation_pct', 0)      # 가치 퍼센타일
            mos = metrics.get('mos', 0)              # 안전마진
            ppos = metrics.get('price_pos', 0.5)     # 가격위치
            
            # 품질 신호
            interest_cov = metrics.get('interest_cov', 0)
            accruals_risk = metrics.get('accruals_risk', 0)
            earnings_vol_sigma = metrics.get('earnings_vol_sigma', 1e9)
            sector_sigma_median = metrics.get('sector_sigma_median', 1e9)
            
            # 고품질 신호
            roic_z = metrics.get('roic_z', 0)
            f_score = metrics.get('f_score', 0)
            
            # 성장성
            eps_cagr = metrics.get('eps_cagr', 0)
            rev_cagr = metrics.get('rev_cagr', 0)
            max_growth = max(eps_cagr, rev_cagr)
            
            # EV/EBIT (절대 가치)
            ev_ebit = metrics.get('ev_ebit', 1e9)
            
            # === 1. 가치 신호 체크 ===
            value_signals = []
            
            # 저평가 신호 (섹터 상대)
            if v <= 20:  # 하위 20% (매우 저평가)
                value_signals.append('deep_undervalued')
            elif v <= 40:  # 하위 40% (저평가)
                value_signals.append('undervalued')
            
            # 절대 가치 신호
            if ev_ebit <= 8:  # EV/EBIT ≤ 8
                value_signals.append('low_ev_ebit')
            elif ev_ebit <= 12:  # EV/EBIT ≤ 12
                value_signals.append('reasonable_ev_ebit')
            
            # 안전마진 신호
            if mos >= 0.30:  # 30% 이상 MoS
                value_signals.append('high_margin_of_safety')
            elif mos >= 0.15:  # 15% 이상 MoS
                value_signals.append('moderate_margin_of_safety')
            
            # === 2. 품질 신호 체크 ===
            quality_signals = []
            
            # 이자보상배율 (지급능력)
            if interest_cov >= 5.0:  # 5배 이상
                quality_signals.append('strong_interest_coverage')
            elif interest_cov >= 2.5:  # 2.5배 이상
                quality_signals.append('adequate_interest_coverage')
            
            # Accruals 품질
            if accruals_risk <= 0.1:  # 10% 이하
                quality_signals.append('low_accruals_risk')
            elif accruals_risk <= 0.2:  # 20% 이하
                quality_signals.append('moderate_accruals_risk')
            
            # 수익 변동성 (안정성)
            if earnings_vol_sigma <= sector_sigma_median * 0.7:  # 섹터 중위수 70% 이하
                quality_signals.append('low_earnings_volatility')
            elif earnings_vol_sigma <= sector_sigma_median:  # 섹터 중위수 이하
                quality_signals.append('below_sector_volatility')
            
            # ROIC z-score (수익성)
            if roic_z >= 1.0:  # 섹터 평균 +1σ 이상
                quality_signals.append('high_roic')
            elif roic_z >= 0.0:  # 섹터 평균 이상
                quality_signals.append('above_sector_roic')
            
            # F-Score (재무 건전성)
            if f_score >= 7:  # 7점 이상
                quality_signals.append('high_f_score')
            elif f_score >= 5:  # 5점 이상
                quality_signals.append('moderate_f_score')
            
            # === 3. 성장 신호 체크 ===
            growth_signals = []
            
            # EPS 성장성
            if eps_cagr >= 0.15:  # 15% 이상
                growth_signals.append('high_eps_growth')
            elif eps_cagr >= 0.05:  # 5% 이상
                growth_signals.append('moderate_eps_growth')
            
            # 매출 성장성
            if rev_cagr >= 0.10:  # 10% 이상
                growth_signals.append('high_revenue_growth')
            elif rev_cagr >= 0.03:  # 3% 이상
                growth_signals.append('moderate_revenue_growth')
            
            # === 4. 스타일 분류 로직 ===
            
            # 강한 가치 신호 + 품질 신호 → Value Stock
            strong_value = len([s for s in value_signals if s in ['deep_undervalued', 'high_margin_of_safety', 'low_ev_ebit']]) >= 2
            strong_quality = len([s for s in quality_signals if s in ['strong_interest_coverage', 'low_accruals_risk', 'high_roic', 'high_f_score']]) >= 2
            
            if strong_value and strong_quality:
                result['style_label'] = 'Value Stock'
                result['style_reasons'] = value_signals + quality_signals
                result['confidence_score'] = 0.9
            elif len(value_signals) >= 2 and len(quality_signals) >= 1:
                result['style_label'] = 'Value Stock'
                result['style_reasons'] = value_signals + quality_signals
                result['confidence_score'] = 0.7
            elif len(value_signals) >= 1 and len(quality_signals) >= 2:
                result['style_label'] = 'Value Stock'
                result['style_reasons'] = value_signals + quality_signals
                result['confidence_score'] = 0.6
            elif len(value_signals) >= 1 and len(quality_signals) >= 1:
                result['style_label'] = 'Potential Value'
                result['style_reasons'] = value_signals + quality_signals
                result['confidence_score'] = 0.5
            else:
                result['style_label'] = 'Not Value'
                result['style_reasons'] = ['insufficient_value_signals']
                result['confidence_score'] = 0.2
            
            # === 5. 성장 가치 조정 ===
            if result['style_label'] in ['Value Stock', 'Potential Value'] and len(growth_signals) >= 1:
                result['style_label'] = 'Growth Value'
                result['style_reasons'].extend(growth_signals)
                result['confidence_score'] = min(1.0, result['confidence_score'] + 0.1)
            
            # === 6. 가격위치 조정 ===
            if ppos > 0.8:  # 52주 상단 80% 이상
                result['confidence_score'] *= 0.8  # 신뢰도 감소
                result['style_reasons'].append('high_price_position_penalty')
            elif ppos < 0.3:  # 52주 하단 30% 이하
                result['confidence_score'] = min(1.0, result['confidence_score'] * 1.1)  # 신뢰도 증가
                result['style_reasons'].append('low_price_position_bonus')
            
            # 메트릭 기록
            if self.metrics:
                self.metrics.record_value_style_classifier_skips(1)
            
        except Exception as e:
            logging.warning(f"가치주 스타일 분류 실패: {e}")
            result['style_reasons'].append(f'classification_error: {str(e)}')
            result['confidence_score'] = 0.0
        
        return result
    
    def get_style_explanation(self, style_label: str, confidence_score: float) -> str:
        """스타일 라벨 설명"""
        explanations = {
            'Value Stock': f'확실한 가치주 (신뢰도: {confidence_score:.1%})',
            'Growth Value': f'성장 가치주 (신뢰도: {confidence_score:.1%})',
            'Potential Value': f'잠재 가치주 (신뢰도: {confidence_score:.1%})',
            'Not Value': f'가치주 아님 (신뢰도: {confidence_score:.1%})'
        }
        return explanations.get(style_label, f'알 수 없는 스타일: {style_label}')
    
    def calculate_style_score(self, metrics: Dict[str, Any]) -> float:
        """스타일 점수 계산 (0~100)"""
        try:
            result = self.classify_value_style(metrics)
            base_score = result['confidence_score'] * 100
            
            # 스타일별 가중치
            style_weights = {
                'Value Stock': 1.0,
                'Growth Value': 0.9,
                'Potential Value': 0.7,
                'Not Value': 0.3
            }
            
            weight = style_weights.get(result['style_label'], 0.5)
            return base_score * weight
            
        except Exception as e:
            logging.warning(f"스타일 점수 계산 실패: {e}")
            return 0.0













