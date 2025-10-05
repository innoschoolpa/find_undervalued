"""
리스크 제약 관리 모듈

재무 건전성과 리스크 관리에 대한 제약 조건을 검증하는 클래스를 제공합니다.
"""

import numpy as np
from typing import Any, Dict, List, Tuple

from metrics import MetricsCollector
from utils.env_utils import safe_env_bool, safe_env_float


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
            return True, "insufficient_volatility_data", 0.0  # 데이터 부족 시 통과
        
        # 최근 5년 데이터
        recent_income = net_income_history[-self.volatility_window:]
        
        # 0 이하 값 제거 (적자 연도 제외)
        positive_income = [x for x in recent_income if x > 0]
        
        if len(positive_income) < 3:  # 양수 연도가 3년 미만이면 리스크
            return False, "insufficient_positive_earnings_years", 0.0
        
        # 변동성 계산 (계수변동성)
        mean_income = np.mean(positive_income)
        std_income = np.std(positive_income)
        cv = std_income / mean_income if mean_income > 0 else 1.0
        
        # 변동성 백분위 계산 (간이형: CV 기준)
        if cv > 0.5:  # 50% 이상 변동성
            return False, f"high_earnings_volatility_cv_{cv:.2f}", cv
        
        return True, f"earnings_volatility_acceptable_cv_{cv:.2f}", cv
    
    def check_dividend_cut_risk(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """배당 컷 리스크 검증"""
        dividend_payout_ratio = financial_data.get('dividend_payout_ratio', 0)
        earnings_growth_rate = financial_data.get('earnings_growth_rate', 0)
        dividend_yield = financial_data.get('dividend_yield', 0)
        
        # 배당성향이 80% 이상이면서 이익성장이 둔화된 경우
        if dividend_payout_ratio > self.risk_thresholds['max_dividend_payout_ratio']:
            if earnings_growth_rate < self.risk_thresholds['min_earnings_growth_threshold']:
                return False, f"high_dividend_cut_risk_payout_{dividend_payout_ratio:.1%}_growth_{earnings_growth_rate:.1%}", dividend_payout_ratio
        
        # 배당수익률이 비정상적으로 높은 경우 (10% 이상)
        if dividend_yield > 10.0:
            return False, f"suspicious_high_dividend_yield_{dividend_yield:.1%}", dividend_yield
        
        return True, "dividend_risk_acceptable", dividend_payout_ratio
    
    def check_liquidity_constraints(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """유동성 제약 검증"""
        current_ratio = financial_data.get('current_ratio', 0)
        quick_ratio = financial_data.get('quick_ratio', 0)
        
        # 유동비율 검증
        if current_ratio and current_ratio < self.risk_thresholds['min_current_ratio']:
            return False, f"low_current_ratio_{current_ratio:.2f}", current_ratio
        
        # 당좌비율 검증 (유동비율의 50% 이상)
        if quick_ratio and current_ratio:
            quick_ratio_threshold = current_ratio * 0.5
            if quick_ratio < quick_ratio_threshold:
                return False, f"low_quick_ratio_{quick_ratio:.2f}_vs_threshold_{quick_ratio_threshold:.2f}", quick_ratio
        
        return True, "liquidity_acceptable", current_ratio
    
    def check_sector_z_score_constraints(self, financial_data: Dict[str, Any], 
                                       sector_data: Dict[str, Any] = None) -> Tuple[bool, str, float]:
        """섹터 z-컷 검사 (섹터 특성 반영)"""
        if not self.sector_z_cut_enabled or not sector_data:
            return True, "sector_z_cut_disabled", 0.0
        
        # 섹터 평균 및 표준편차 가져오기
        sector_mean = sector_data.get('debt_ratio_mean', None)
        sector_std = sector_data.get('debt_ratio_std', None)
        
        if sector_mean is None or sector_std is None or sector_std <= 0:
            return True, "insufficient_sector_data", 0.0
        
        # 회사 부채비율
        company_debt_ratio = financial_data.get('debt_ratio', 0)
        
        # z-score 계산
        z_score = (company_debt_ratio - sector_mean) / sector_std
        
        # z-컷 임계치 검사
        if z_score <= self.sector_z_cut_threshold:
            return False, f"sector_z_cut_violated_z_{z_score:.2f}_threshold_{self.sector_z_cut_threshold}", z_score
        
        return True, "sector_z_cut_passed", z_score
    
    def apply_risk_constraints(self, symbol: str, financial_data: Dict[str, Any], 
                             sector_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """종합 리스크 제약 적용"""
        result = {
            'symbol': symbol,
            'passed': True,
            'constraint_results': {},
            'overall_risk_score': 0.0,
            'violation_reasons': []
        }
        
        # 1. 레버리지 제약 검사
        leverage_ok, leverage_reason, leverage_value = self.check_leverage_constraints(
            financial_data, sector_data.get('debt_ratio_median') if sector_data else None
        )
        result['constraint_results']['leverage'] = {
            'passed': leverage_ok,
            'reason': leverage_reason,
            'value': leverage_value
        }
        if not leverage_ok:
            result['passed'] = False
            result['violation_reasons'].append(f"leverage: {leverage_reason}")
        
        # 2. 변동성 제약 검사
        volatility_ok, volatility_reason, volatility_value = self.check_earnings_volatility(financial_data)
        result['constraint_results']['volatility'] = {
            'passed': volatility_ok,
            'reason': volatility_reason,
            'value': volatility_value
        }
        if not volatility_ok:
            result['passed'] = False
            result['violation_reasons'].append(f"volatility: {volatility_reason}")
        
        # 3. 배당 컷 리스크 검사
        dividend_ok, dividend_reason, dividend_value = self.check_dividend_cut_risk(financial_data)
        result['constraint_results']['dividend_risk'] = {
            'passed': dividend_ok,
            'reason': dividend_reason,
            'value': dividend_value
        }
        if not dividend_ok:
            result['passed'] = False
            result['violation_reasons'].append(f"dividend_risk: {dividend_reason}")
        
        # 4. 유동성 제약 검사
        liquidity_ok, liquidity_reason, liquidity_value = self.check_liquidity_constraints(financial_data)
        result['constraint_results']['liquidity'] = {
            'passed': liquidity_ok,
            'reason': liquidity_reason,
            'value': liquidity_value
        }
        if not liquidity_ok:
            result['passed'] = False
            result['violation_reasons'].append(f"liquidity: {liquidity_reason}")
        
        # 5. 섹터 z-컷 검사 (새로 추가)
        sector_z_ok, sector_z_reason, sector_z_value = self.check_sector_z_score_constraints(financial_data, sector_data)
        result['constraint_results']['sector_z_cut'] = {
            'passed': sector_z_ok,
            'reason': sector_z_reason,
            'value': sector_z_value
        }
        if not sector_z_ok:
            result['passed'] = False
            result['violation_reasons'].append(f"sector_z_cut: {sector_z_reason}")
        
        # 전체 리스크 점수 계산 (통과한 제약의 가중 평균)
        risk_components = []
        if leverage_ok:
            # 부채비율이 낮을수록 높은 점수
            debt_ratio = financial_data.get('debt_ratio', 0)
            leverage_score = max(0, 1 - debt_ratio / 50)  # 50% 기준 정규화
            risk_components.append(leverage_score * 0.3)  # 레버리지 30%
        
        if volatility_ok:
            # 변동성이 낮을수록 높은 점수
            volatility_score = max(0, 1 - volatility_value / 0.5)  # CV 0.5 기준 정규화
            risk_components.append(volatility_score * 0.25)  # 변동성 25%
        
        if dividend_ok:
            # 배당성향이 적절할수록 높은 점수
            payout_ratio = financial_data.get('dividend_payout_ratio', 0)
            dividend_score = max(0, 1 - abs(payout_ratio - 0.3) / 0.3)  # 30% 기준 정규화
            risk_components.append(dividend_score * 0.2)  # 배당 20%
        
        if liquidity_ok:
            # 유동성이 높을수록 높은 점수
            current_ratio = financial_data.get('current_ratio', 0)
            liquidity_score = min(1, current_ratio / 2)  # 2.0 기준 정규화
            risk_components.append(liquidity_score * 0.25)  # 유동성 25%
        
        if risk_components:
            result['overall_risk_score'] = sum(risk_components) / len(risk_components)
        else:
            result['overall_risk_score'] = 0.0
        
        # 메트릭 기록
        if self.metrics:
            if not result['passed']:
                self.metrics.record_risk_constraint_violation(symbol, result['violation_reasons'])
        
        return result
    
    def is_eligible_after_risk_check(self, symbol: str, financial_data: Dict[str, Any], 
                                   sector_data: Dict[str, Any] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """리스크 제약 통과 여부 검증"""
        constraint_result = self.apply_risk_constraints(symbol, financial_data, sector_data)
        
        if not constraint_result['passed']:
            violation_summary = "; ".join(constraint_result['violation_reasons'])
            return False, f"risk_constraints_violated: {violation_summary}", constraint_result
        
        return True, "risk_constraints_passed", constraint_result





