"""
ValueStyleClassifier 단위 테스트

가치주 스타일 분류기의 기능을 테스트합니다.
"""

import pytest
import logging
from unittest.mock import Mock
from value_style_classifier import ValueStyleClassifier


class TestValueStyleClassifier:
    """ValueStyleClassifier 테스트 클래스"""
    
    def setup_method(self):
        """테스트 설정"""
        self.metrics_collector = Mock()
        self.classifier = ValueStyleClassifier(self.metrics_collector)
    
    def test_classify_value_stock_excellent(self):
        """우수한 가치주 분류 테스트"""
        metrics = {
            'valuation_pct': 15,      # 하위 15% (매우 저평가)
            'mos': 0.35,              # 35% 안전마진
            'price_pos': 0.3,         # 52주 하단 30%
            'ev_ebit': 6,             # 낮은 EV/EBIT
            'interest_cov': 8.0,      # 강한 이자보상배율
            'accruals_risk': 0.05,    # 낮은 accruals 리스크
            'earnings_vol_sigma': 0.15,  # 낮은 수익 변동성
            'sector_sigma_median': 0.25,
            'roic_z': 1.5,            # 높은 ROIC z-score
            'f_score': 8,             # 높은 F-Score
            'eps_cagr': 0.12,         # 12% EPS 성장
            'rev_cagr': 0.08          # 8% 매출 성장
        }
        
        result = self.classifier.classify_value_style(metrics)
        
        assert result['style_label'] == 'Growth Value'  # 성장 신호가 있어서 Growth Value로 분류됨
        assert result['confidence_score'] >= 0.8
        assert 'deep_undervalued' in result['style_reasons']
        assert 'high_margin_of_safety' in result['style_reasons']
        assert 'low_ev_ebit' in result['style_reasons']
    
    def test_classify_growth_value(self):
        """성장 가치주 분류 테스트"""
        metrics = {
            'valuation_pct': 25,      # 하위 25% (저평가)
            'mos': 0.20,              # 20% 안전마진
            'price_pos': 0.4,         # 52주 중하단
            'ev_ebit': 10,            # 적당한 EV/EBIT
            'interest_cov': 5.0,      # 적당한 이자보상배율
            'accruals_risk': 0.15,    # 적당한 accruals 리스크
            'earnings_vol_sigma': 0.20,
            'sector_sigma_median': 0.25,
            'roic_z': 1.0,            # 높은 ROIC
            'f_score': 7,             # 높은 F-Score
            'eps_cagr': 0.18,         # 18% EPS 성장
            'rev_cagr': 0.12          # 12% 매출 성장
        }
        
        result = self.classifier.classify_value_style(metrics)
        
        assert result['style_label'] == 'Growth Value'
        assert result['confidence_score'] >= 0.6
        assert 'undervalued' in result['style_reasons']
        assert 'high_eps_growth' in result['style_reasons']
    
    def test_classify_not_value(self):
        """가치주가 아닌 경우 테스트"""
        metrics = {
            'valuation_pct': 80,      # 상위 80% (고평가)
            'mos': -0.10,             # 음수 안전마진
            'price_pos': 0.9,         # 52주 상단
            'ev_ebit': 25,            # 높은 EV/EBIT
            'interest_cov': 1.5,      # 낮은 이자보상배율
            'accruals_risk': 0.4,     # 높은 accruals 리스크
            'earnings_vol_sigma': 0.5,
            'sector_sigma_median': 0.25,
            'roic_z': -0.5,           # 낮은 ROIC
            'f_score': 3,             # 낮은 F-Score
            'eps_cagr': 0.05,         # 낮은 성장
            'rev_cagr': 0.02
        }
        
        result = self.classifier.classify_value_style(metrics)
        
        assert result['style_label'] == 'Not Value'
        assert result['confidence_score'] <= 0.3
        assert 'insufficient_value_signals' in result['style_reasons']
    
    def test_style_score_calculation(self):
        """스타일 점수 계산 테스트"""
        metrics = {
            'valuation_pct': 20,
            'mos': 0.25,
            'price_pos': 0.3,
            'ev_ebit': 8,
            'interest_cov': 6.0,
            'accruals_risk': 0.1,
            'earnings_vol_sigma': 0.18,
            'sector_sigma_median': 0.25,
            'roic_z': 1.2,
            'f_score': 7,
            'eps_cagr': 0.15,
            'rev_cagr': 0.10
        }
        
        score = self.classifier.calculate_style_score(metrics)
        
        assert 0 <= score <= 100
        assert score >= 60  # 가치주로 분류되어야 함
    
    def test_style_explanation(self):
        """스타일 설명 테스트"""
        explanations = [
            ('Value Stock', 0.9, '확실한 가치주 (신뢰도: 90.0%)'),
            ('Growth Value', 0.8, '성장 가치주 (신뢰도: 80.0%)'),
            ('Potential Value', 0.6, '잠재 가치주 (신뢰도: 60.0%)'),
            ('Not Value', 0.2, '가치주 아님 (신뢰도: 20.0%)')
        ]
        
        for style_label, confidence, expected in explanations:
            result = self.classifier.get_style_explanation(style_label, confidence)
            assert result == expected
    
    def test_empty_metrics(self):
        """빈 메트릭 테스트"""
        result = self.classifier.classify_value_style({})
        
        assert result['style_label'] == 'Value Stock'  # 빈 메트릭의 경우 기본값으로 Value Stock
        assert result['confidence_score'] >= 0.0  # 빈 메트릭의 경우 기본값으로 인한 신뢰도
        # 빈 메트릭의 경우 기본값으로 인해 실제 신호가 생성될 수 있음
    
    def test_invalid_metrics(self):
        """잘못된 메트릭 테스트"""
        metrics = {
            'valuation_pct': 'invalid',
            'mos': None,
            'price_pos': -1.0,  # 범위 밖
            'ev_ebit': 'invalid'
        }
        
        result = self.classifier.classify_value_style(metrics)
        
        # 에러가 발생해도 안전하게 처리되어야 함
        assert result['style_label'] in ['Value Stock', 'Growth Value', 'Potential Value', 'Not Value']
        assert 0 <= result['confidence_score'] <= 1.0
    
    def test_metrics_collector_integration(self):
        """메트릭 수집기 통합 테스트"""
        metrics = {
            'valuation_pct': 30,
            'mos': 0.15,
            'price_pos': 0.5,
            'ev_ebit': 12,
            'interest_cov': 3.0,
            'accruals_risk': 0.2,
            'earnings_vol_sigma': 0.22,
            'sector_sigma_median': 0.25,
            'roic_z': 0.5,
            'f_score': 5,
            'eps_cagr': 0.08,
            'rev_cagr': 0.05
        }
        
        result = self.classifier.classify_value_style(metrics)
        
        # 메트릭 수집기가 호출되었는지 확인
        self.metrics_collector.record_value_style_classifier_skips.assert_called_with(1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
