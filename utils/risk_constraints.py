"""Risk constraints and validation management."""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from .env_utils import safe_env_bool, safe_env_float
from .metrics import MetricsCollector


class RiskConstraintsManager:
    """리스크/건전성 제약 관리 클래스"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 리스크 제약 임계치
        self.risk_thresholds = {
            'max_leverage_ratio': 2.0,        # 최대 부채/자본 비율 2.0
            'max_volatility_percentile': 80,   # 최대 변동성 백분위 80%
            'max_dividend_payout_ratio': 0.8,  # 최대 배당성향 80%
            'min_earnings_growth_threshold': -0.1,  # 최소 이익성장률 -10%
            'max_debt_to_equity': 1.5,        # 최대 부채/자기자본 1.5
            'min_current_ratio': 1.2          # 최소 유동비율 1.2
        }
        # 5년 변동성 계산 윈도우
        self.volatility_window = 5
        # 섹터 z-컷 설정 (기본 활성화)
        self.sector_z_cut_enabled = safe_env_bool("SECTOR_Z_CUT_ENABLED", True)
        self.sector_z_cut_threshold = safe_env_float("SECTOR_Z_CUT_THRESHOLD", -2.0, -5.0)  # -2.0 z-score 이하 컷
    
    def check_leverage_constraints(self, financial_data: Dict[str, Any], 
                                 sector_median: float = None) -> Tuple[bool, str, float]:
        """부채/자본(Leverage) 상한 검증"""
        debt_ratio = financial_data.get('debt_ratio', 0)
        debt_to_equity = financial_data.get('debt_to_equity', 0)
        
        # 부채비율 검증 (더 현실적인 기준으로 조정)
        if debt_ratio and debt_ratio > 100:  # 100% 이상 (50% → 100%)
            return False, f"high_debt_ratio_{debt_ratio:.1f}%", debt_ratio
        
        # 부채/자기자본 비율 검증
        if debt_to_equity and debt_to_equity > self.risk_thresholds['max_debt_to_equity']:
            return False, f"high_debt_to_equity_{debt_to_equity:.2f}", debt_to_equity
        
        # 섹터 상대 검증 (섹터 중위수 대비 +2σ 초과 시 컷)
        if sector_median and sector_median > 0:
            # 섹터 표준편차 추정 (중위수의 30%로 근사)
            sector_std = sector_median * 0.3
            sector_upper_bound = sector_median + 2 * sector_std
            
            if debt_ratio > sector_upper_bound:
                return False, f"debt_ratio_above_sector_2sigma_{debt_ratio:.1f}%_vs_{sector_upper_bound:.1f}%", debt_ratio
        
        return True, "leverage_acceptable", debt_ratio
    
    def check_earnings_volatility(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """순이익 변동성 검증 (5년 표준편차)"""
        net_income_history = financial_data.get('net_income_history', [])
        
        if len(net_income_history) < self.volatility_window:
            return True, "insufficient_history", 0.0
        
        # 최근 5년 순이익 변동성 계산
        recent_earnings = net_income_history[-self.volatility_window:]
        
        # 0 이하 값 제거 (손실 연도 제외)
        positive_earnings = [e for e in recent_earnings if e > 0]
        
        if len(positive_earnings) < 3:  # 최소 3년 양수 필요
            return False, "too_many_loss_years", 0.0
        
        # 변동성 계산 (CV = 표준편차/평균)
        mean_earnings = sum(positive_earnings) / len(positive_earnings)
        variance = sum((e - mean_earnings) ** 2 for e in positive_earnings) / len(positive_earnings)
        std_dev = math.sqrt(variance)
        coefficient_of_variation = std_dev / mean_earnings if mean_earnings > 0 else float('inf')
        
        # 변동성 임계치 검증 (CV > 0.5면 고변동성)
        if coefficient_of_variation > 0.5:
            return False, f"high_earnings_volatility_{coefficient_of_variation:.2f}", coefficient_of_variation
        
        return True, "earnings_stable", coefficient_of_variation
    
    def check_dividend_sustainability(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """배당 지속가능성 검증"""
        dividend_payout_ratio = financial_data.get('dividend_payout_ratio', 0)
        net_income = financial_data.get('net_income', 0)
        dividend_per_share = financial_data.get('dividend_per_share', 0)
        
        # 배당성향 검증
        if dividend_payout_ratio > self.risk_thresholds['max_dividend_payout_ratio']:
            return False, f"high_dividend_payout_{dividend_payout_ratio:.1%}", dividend_payout_ratio
        
        # 배당 지속가능성 검증 (순이익 대비)
        if dividend_per_share > 0 and net_income > 0:
            # 주당순이익 계산 (간단한 추정)
            shares_outstanding = financial_data.get('shares_outstanding', 1)
            eps = net_income / shares_outstanding if shares_outstanding > 0 else 0
            
            if eps > 0 and dividend_per_share / eps > 0.8:
                return False, f"unsustainable_dividend_{dividend_per_share:.2f}_vs_eps_{eps:.2f}", dividend_per_share / eps
        
        return True, "dividend_sustainable", dividend_payout_ratio
    
    def check_liquidity_constraints(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """유동성 제약 검증"""
        current_ratio = financial_data.get('current_ratio', 0)
        quick_ratio = financial_data.get('quick_ratio', 0)
        
        # 유동비율 검증
        if current_ratio < self.risk_thresholds['min_current_ratio']:
            return False, f"low_current_ratio_{current_ratio:.2f}", current_ratio
        
        # 당좌비율 검증 (재고 제외)
        if quick_ratio > 0 and quick_ratio < 0.8:
            return False, f"low_quick_ratio_{quick_ratio:.2f}", quick_ratio
        
        return True, "liquidity_adequate", current_ratio
    
    def check_earnings_growth_consistency(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """이익성장 일관성 검증"""
        net_income_growth_rate = financial_data.get('net_income_growth_rate', 0)
        revenue_growth_rate = financial_data.get('revenue_growth_rate', 0)
        
        # 순이익 성장률 검증
        if net_income_growth_rate < self.risk_thresholds['min_earnings_growth_threshold']:
            return False, f"negative_earnings_growth_{net_income_growth_rate:.1%}", net_income_growth_rate
        
        # 매출-이익 성장 일관성 검증
        if revenue_growth_rate > 0 and net_income_growth_rate < 0:
            return False, f"revenue_growth_positive_earnings_negative_{revenue_growth_rate:.1%}_{net_income_growth_rate:.1%}", net_income_growth_rate
        
        return True, "earnings_growth_consistent", net_income_growth_rate
    
    def check_sector_z_score(self, financial_data: Dict[str, Any], sector_metrics: Dict[str, float]) -> Tuple[bool, str, float]:
        """섹터 Z-스코어 검증"""
        if not self.sector_z_cut_enabled or not sector_metrics:
            return True, "z_score_check_disabled", 0.0
        
        # ROE Z-스코어 계산
        roe = financial_data.get('roe', 0)
        sector_roe_mean = sector_metrics.get('roe_mean', 0)
        sector_roe_std = sector_metrics.get('roe_std', 1)
        
        if sector_roe_std > 0:
            roe_z_score = (roe - sector_roe_mean) / sector_roe_std
            
            if roe_z_score < self.sector_z_cut_threshold:
                return False, f"roe_z_score_too_low_{roe_z_score:.2f}", roe_z_score
        
        return True, "z_score_acceptable", 0.0
    
    def validate_risk_constraints(self, symbol: str, financial_data: Dict[str, Any], 
                                sector_metrics: Dict[str, float] = None) -> Tuple[bool, List[str], Dict[str, Any]]:
        """종합 리스크 제약 검증"""
        violation_reasons = []
        constraint_results = {}
        
        # 1. 부채 제약 검증
        leverage_valid, leverage_reason, leverage_value = self.check_leverage_constraints(
            financial_data, sector_metrics.get('debt_ratio_median') if sector_metrics else None
        )
        constraint_results['leverage'] = {
            'valid': leverage_valid, 'reason': leverage_reason, 'value': leverage_value
        }
        if not leverage_valid:
            violation_reasons.append(leverage_reason)
        
        # 2. 변동성 검증
        volatility_valid, volatility_reason, volatility_value = self.check_earnings_volatility(financial_data)
        constraint_results['volatility'] = {
            'valid': volatility_valid, 'reason': volatility_reason, 'value': volatility_value
        }
        if not volatility_valid:
            violation_reasons.append(volatility_reason)
        
        # 3. 배당 지속가능성 검증
        dividend_valid, dividend_reason, dividend_value = self.check_dividend_sustainability(financial_data)
        constraint_results['dividend'] = {
            'valid': dividend_valid, 'reason': dividend_reason, 'value': dividend_value
        }
        if not dividend_valid:
            violation_reasons.append(dividend_reason)
        
        # 4. 유동성 검증
        liquidity_valid, liquidity_reason, liquidity_value = self.check_liquidity_constraints(financial_data)
        constraint_results['liquidity'] = {
            'valid': liquidity_valid, 'reason': liquidity_reason, 'value': liquidity_value
        }
        if not liquidity_valid:
            violation_reasons.append(liquidity_reason)
        
        # 5. 이익성장 일관성 검증
        growth_valid, growth_reason, growth_value = self.check_earnings_growth_consistency(financial_data)
        constraint_results['growth'] = {
            'valid': growth_valid, 'reason': growth_reason, 'value': growth_value
        }
        if not growth_valid:
            violation_reasons.append(growth_reason)
        
        # 6. 섹터 Z-스코어 검증
        zscore_valid, zscore_reason, zscore_value = self.check_sector_z_score(financial_data, sector_metrics or {})
        constraint_results['zscore'] = {
            'valid': zscore_valid, 'reason': zscore_reason, 'value': zscore_value
        }
        if not zscore_valid:
            violation_reasons.append(zscore_reason)
        
        # 전체 검증 결과
        overall_valid = all([
            leverage_valid, volatility_valid, dividend_valid, 
            liquidity_valid, growth_valid, zscore_valid
        ])
        
        # 메트릭 기록
        if self.metrics and not overall_valid:
            self.metrics.record_risk_constraint_violation(symbol, violation_reasons)
        
        return overall_valid, violation_reasons, constraint_results













