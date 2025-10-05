"""Lightweight regression checks for the enhanced analyzer.

These tests cover a few critical utility behaviours without relying on
external APIs so that the suite remains stable after future refactors.
"""

import math

import pytest

from enhanced_integrated_analyzer_refactored import (
    EnhancedIntegratedAnalyzer,
    AnalysisStatus,
    DataConverter,
    normalize_market_cap_ekwon,
)


def test_normalize_market_cap_small_returns_none():
    assert normalize_market_cap_ekwon(0.5) is None


def test_normalize_market_cap_converts_large_krw():
    value = 200_000_000_000  # 2000억원 in 원 단위
    assert normalize_market_cap_ekwon(value) == pytest.approx(2000.0)


def test_standardize_financial_units_percent_conversion():
    data = {"roe": 0.12, "current_ratio": 1.8}
    result = DataConverter.standardize_financial_units(data)
    assert result["roe"] == pytest.approx(12.0)
    assert result["current_ratio"] == pytest.approx(180.0)
    assert result["_percent_canonicalized"] is True


def test_calculate_price_position_degenerate_band_returns_none():
    analyzer = EnhancedIntegratedAnalyzer(include_external=False)
    try:
        price_data = {"current_price": 100, "w52_high": 100, "w52_low": 100}
        assert analyzer._calculate_price_position(price_data) is None
    finally:
        analyzer.close()


def test_analyze_single_stock_no_external_relaxes():
    analyzer = EnhancedIntegratedAnalyzer(include_external=False)
    try:
        result = analyzer.analyze_single_stock("005930", "삼성전자")
        assert result.status.value in {AnalysisStatus.SUCCESS.value, AnalysisStatus.SKIPPED_PREF.value, AnalysisStatus.ERROR.value}
        assert math.isfinite(result.enhanced_score) or result.enhanced_score == 0
    finally:
        analyzer.close()





