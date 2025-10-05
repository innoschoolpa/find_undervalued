"""
품질 일관성 필터 모듈

재무 데이터의 품질과 지속성을 검증하여 가치 평가 자격을 확인하는 클래스를 제공합니다.
"""

import logging
import numpy as np
from typing import Any, Dict, List, Tuple

from metrics import MetricsCollector


class QualityConsistencyFilter:
    """품질·지속성 필터 클래스 (가치 계산 전 자격 검증)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 품질 임계치
        self.quality_thresholds = {
            'min_operating_margin': 5.0,      # 최소 영업이익률 5%
            'min_net_margin': 3.0,            # 최소 순이익률 3%
            'min_piotroski_score': 6,         # 최소 Piotroski F-Score 6/9
            'min_interest_coverage': 3.0,     # 최소 이자보상배율 3배
            'max_accruals_ratio': 0.3,        # 최대 Accruals 비율 30%
            'min_profitability_consistency': 0.6  # 최소 수익성 일관성 60%
        }
        # 5년 롤링 윈도우
        self.rolling_window = 5
    
    def check_profitability_consistency(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """지속적 수익성 검증 (5년 롤링)"""
        # 영업이익률과 순이익률 5년 데이터 필요 (데이터 부족 시 현재 데이터로 대체)
        operating_margins = financial_data.get('operating_margin_history', [])
        net_margins = financial_data.get('net_margin_history', [])
        
        # 데이터가 부족한 경우 현재 데이터로 대체
        if len(operating_margins) < self.rolling_window:
            current_operating = financial_data.get('operating_margin', 0)
            if current_operating == 0:
                # operating_margin이 없으면 net_profit_margin 사용
                current_operating = financial_data.get('net_profit_margin', 0)
            operating_margins = [current_operating] * self.rolling_window
        
        if len(net_margins) < self.rolling_window:
            current_net = financial_data.get('net_margin', 0)
            if current_net == 0:
                # net_margin이 없으면 net_profit_margin 사용
                current_net = financial_data.get('net_profit_margin', 0)
            net_margins = [current_net] * self.rolling_window
        
        # 최근 5년 데이터
        recent_operating = operating_margins[-self.rolling_window:]
        recent_net = net_margins[-self.rolling_window:]
        
        # 평균값으로 검사 (백분위 대신)
        avg_operating = np.mean(recent_operating)
        avg_net = np.mean(recent_net)
        
        # 임계치 미달 검사
        if avg_operating < self.quality_thresholds['min_operating_margin']:
            return False, f"operating_margin_avg_{avg_operating:.1f}%", avg_operating
        
        if avg_net < self.quality_thresholds['min_net_margin']:
            return False, f"net_margin_avg_{avg_net:.1f}%", avg_net
        
        # 일관성 점수 계산 (양수 연도 비율)
        positive_operating_years = sum(1 for margin in recent_operating if margin > 0)
        positive_net_years = sum(1 for margin in recent_net if margin > 0)
        
        consistency_score = (positive_operating_years + positive_net_years) / (2 * self.rolling_window)
        
        if consistency_score < self.quality_thresholds['min_profitability_consistency']:
            return False, f"low_profitability_consistency_{consistency_score:.1%}", consistency_score
        
        return True, "profitability_consistent", consistency_score
    
    def check_accruals_quality(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """Accruals 가드 (회계적 이익/현금 괴리 검증)"""
        # 총자산 증가 대비 순이익 증가 비율
        total_assets_history = financial_data.get('total_assets_history', [])
        net_income_history = financial_data.get('net_income_history', [])
        
        if len(total_assets_history) < 2 or len(net_income_history) < 2:
            return True, "insufficient_data_for_accruals", 0.0  # 데이터 부족 시 통과
        
        # 최근 2년 비교
        assets_growth = (total_assets_history[-1] - total_assets_history[-2]) / total_assets_history[-2]
        income_growth = (net_income_history[-1] - net_income_history[-2]) / abs(net_income_history[-2]) if net_income_history[-2] != 0 else 0
        
        # Accruals 비율 = (순이익 증가 - 총자산 증가) / 총자산 증가
        if abs(assets_growth) < 0.01:  # 총자산 변화가 1% 미만이면 정상
            accruals_ratio = 0.0
        else:
            accruals_ratio = abs(income_growth - assets_growth) / abs(assets_growth)
        
        if accruals_ratio > self.quality_thresholds['max_accruals_ratio']:
            return False, f"high_accruals_ratio_{accruals_ratio:.1%}", accruals_ratio
        
        return True, "accruals_acceptable", accruals_ratio
    
    def calculate_piotroski_f_score(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, int]:
        """Piotroski F-Score 계산 (간이형)"""
        score = 0
        max_score = 9
        
        # 디버깅 정보
        logging.debug("Piotroski F-Score 계산 시작")
        
        # 1. 순이익 > 0 (1점) - ROE로 대체
        roe = financial_data.get('roe', 0)
        if roe > 0:
            score += 1
            logging.debug(f"ROE > 0: {roe:.1f}% (PASS)")
        else:
            logging.debug(f"ROE > 0: {roe:.1f}% (FAIL)")
        
        # 2. 영업현금흐름 > 0 (1점) - ROA로 대체
        roa = financial_data.get('roa', 0)
        if roa > 0:
            score += 1
            logging.debug(f"ROA > 0: {roa:.1f}% (PASS)")
        else:
            logging.debug(f"ROA > 0: {roa:.1f}% (FAIL)")
        
        # 3. 부채비율 적정 (1점)
        debt_ratio = financial_data.get('debt_ratio', 0)
        if debt_ratio < 50:  # 부채비율 50% 미만
            score += 1
            logging.debug(f"부채비율 < 50%: {debt_ratio:.1f}% (PASS)")
        else:
            logging.debug(f"부채비율 < 50%: {debt_ratio:.1f}% (FAIL)")
        
        # 4. 유동비율 적정 (1점)
        current_ratio = financial_data.get('current_ratio', 0)
        if current_ratio > 1.0:  # 유동비율 1.0 이상
            score += 1
            logging.debug(f"유동비율 > 1.0: {current_ratio:.1f} (PASS)")
        else:
            logging.debug(f"유동비율 > 1.0: {current_ratio:.1f} (FAIL)")
        
        # 5. 매출총이익률 양호 (1점)
        gross_margin = financial_data.get('gross_profit_margin', 0)
        if gross_margin > 0:
            score += 1
            logging.debug(f"매출총이익률 > 0: {gross_margin:.1f}% (PASS)")
        else:
            logging.debug(f"매출총이익률 > 0: {gross_margin:.1f}% (FAIL)")
        
        # 6. 순이익률 양호 (1점)
        net_margin = financial_data.get('net_profit_margin', 0)
        if net_margin > 0:
            score += 1
            logging.debug(f"순이익률 > 0: {net_margin:.1f}% (PASS)")
        else:
            logging.debug(f"순이익률 > 0: {net_margin:.1f}% (FAIL)")
        
        # 7. ROE 양호 (1점)
        if roe > 5:  # ROE 5% 이상
            score += 1
            logging.debug(f"ROE > 5%: {roe:.1f}% (PASS)")
        else:
            logging.debug(f"ROE > 5%: {roe:.1f}% (FAIL)")
        
        # 8. ROA 양호 (1점)
        if roa > 3:  # ROA 3% 이상
            score += 1
            logging.debug(f"ROA > 3%: {roa:.1f}% (PASS)")
        else:
            logging.debug(f"ROA > 3%: {roa:.1f}% (FAIL)")
        
        # 9. 성장률 양호 (1점)
        revenue_growth = financial_data.get('revenue_growth_rate', 0)
        if revenue_growth > 0:
            score += 1
            logging.debug(f"매출성장률 > 0: {revenue_growth:.1f}% (PASS)")
        else:
            logging.debug(f"매출성장률 > 0: {revenue_growth:.1f}% (FAIL)")
        
        # 임계치 검사
        if score < self.quality_thresholds['min_piotroski_score']:
            return False, f"low_piotroski_score_{score}/{max_score}", score
        
        return True, f"piotroski_acceptable_{score}/{max_score}", score
    
    def check_interest_coverage(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """이자보상배율 검증"""
        operating_income = financial_data.get('operating_income', 0)
        interest_expense = financial_data.get('interest_expense', 0)
        
        if interest_expense <= 0:
            return True, "no_interest_expense", float('inf')  # 이자비용이 없으면 통과
        
        interest_coverage = operating_income / interest_expense
        
        if interest_coverage < self.quality_thresholds['min_interest_coverage']:
            return False, f"low_interest_coverage_{interest_coverage:.1f}x", interest_coverage
        
        return True, f"interest_coverage_acceptable_{interest_coverage:.1f}x", interest_coverage
    
    def apply_quality_filter(self, symbol: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """종합 품질 필터 적용"""
        result = {
            'symbol': symbol,
            'passed': True,
            'filter_results': {},
            'overall_quality_score': 0.0,
            'rejection_reasons': []
        }
        
        # 1. 수익성 일관성 검사
        prof_consistent, prof_reason, prof_score = self.check_profitability_consistency(financial_data)
        result['filter_results']['profitability_consistency'] = {
            'passed': prof_consistent,
            'reason': prof_reason,
            'score': prof_score
        }
        if not prof_consistent:
            result['passed'] = False
            result['rejection_reasons'].append(f"profitability: {prof_reason}")
        
        # 2. Accruals 품질 검사
        accruals_ok, accruals_reason, accruals_ratio = self.check_accruals_quality(financial_data)
        result['filter_results']['accruals_quality'] = {
            'passed': accruals_ok,
            'reason': accruals_reason,
            'ratio': accruals_ratio
        }
        if not accruals_ok:
            result['passed'] = False
            result['rejection_reasons'].append(f"accruals: {accruals_reason}")
        
        # 3. Piotroski F-Score 검사
        piotroski_ok, piotroski_reason, piotroski_score = self.calculate_piotroski_f_score(financial_data)
        result['filter_results']['piotroski_score'] = {
            'passed': piotroski_ok,
            'reason': piotroski_reason,
            'score': piotroski_score
        }
        if not piotroski_ok:
            result['passed'] = False
            result['rejection_reasons'].append(f"piotroski: {piotroski_reason}")
        
        # 4. 이자보상배율 검사
        interest_ok, interest_reason, interest_coverage = self.check_interest_coverage(financial_data)
        result['filter_results']['interest_coverage'] = {
            'passed': interest_ok,
            'reason': interest_reason,
            'coverage': interest_coverage
        }
        if not interest_ok:
            result['passed'] = False
            result['rejection_reasons'].append(f"interest_coverage: {interest_reason}")
        
        # 전체 품질 점수 계산 (통과한 필터의 가중 평균)
        quality_components = []
        if prof_consistent:
            quality_components.append(prof_score * 0.3)  # 수익성 일관성 30%
        if accruals_ok:
            quality_components.append((1 - accruals_ratio) * 0.2)  # Accruals 품질 20%
        if piotroski_ok:
            quality_components.append(piotroski_score / 9 * 0.3)  # Piotroski 30%
        if interest_ok:
            quality_components.append(min(1.0, interest_coverage / 5) * 0.2)  # 이자보상 20%
        
        if quality_components:
            result['overall_quality_score'] = sum(quality_components) / len(quality_components)
        else:
            result['overall_quality_score'] = 0.0
        
        # 메트릭 기록
        if self.metrics:
            if not result['passed']:
                self.metrics.record_quality_filter_rejection(symbol, result['rejection_reasons'])
        
        return result
    
    def is_eligible_for_valuation(self, symbol: str, financial_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """가치평가 자격 검증 (전체 점수 계산 전 SKIP 여부)"""
        filter_result = self.apply_quality_filter(symbol, financial_data)
        
        if not filter_result['passed']:
            rejection_summary = "; ".join(filter_result['rejection_reasons'])
            return False, f"quality_filter_failed: {rejection_summary}", filter_result
        
        return True, "quality_filter_passed", filter_result





