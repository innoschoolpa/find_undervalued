#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
가치주 발굴 시스템 개선 모듈
- 음수 PER 대체 로직
- 품질 지표 추가 (FCF Yield, Interest Coverage, Piotroski F-Score)
- 장기 앵커 기반 MoS
- 데이터 품질 가드
"""

import logging
import statistics
from typing import Dict, Optional, Any, Tuple
import pickle
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LongTermAnchorCache:
    """장기 앵커 캐시 시스템 (프로사이클 편향 완화)"""
    
    def __init__(self, cache_file='cache/long_term_anchors.pkl', ttl_days=90):
        self.cache_file = cache_file
        self.ttl_days = ttl_days
        self.anchors = {}
        self.timestamp = None
        self._load_cache()
    
    def _load_cache(self):
        """캐시 로드"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    data = pickle.load(f)
                    self.anchors = data.get('anchors', {})
                    self.timestamp = data.get('timestamp')
                    
                    # TTL 체크
                    if self.timestamp and datetime.now() - self.timestamp > timedelta(days=self.ttl_days):
                        logger.info("장기 앵커 캐시 만료 - 새로 계산 필요")
                        self.anchors = {}
                        self.timestamp = None
            except Exception as e:
                logger.warning(f"장기 앵커 캐시 로드 실패: {e}")
    
    def _save_cache(self):
        """캐시 저장"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'wb') as f:
                pickle.dump({
                    'anchors': self.anchors,
                    'timestamp': self.timestamp
                }, f)
        except Exception as e:
            logger.warning(f"장기 앵커 캐시 저장 실패: {e}")
    
    def get_anchor(self, sector: str, metric: str) -> Optional[float]:
        """장기 앵커 조회"""
        return self.anchors.get(sector, {}).get(metric)
    
    def update_anchors(self, sector_stats: Dict[str, Dict]):
        """
        장기 앵커 업데이트
        sector_stats: {sector_name: {'per_history': [], 'pbr_history': [], ...}}
        """
        self.timestamp = datetime.now()
        
        for sector, stats in sector_stats.items():
            per_history = stats.get('per_history', [])
            pbr_history = stats.get('pbr_history', [])
            roe_history = stats.get('roe_history', [])
            
            # 5년 또는 10년 중앙값 계산 (최소 3년 필요)
            if len(per_history) >= 36:  # 36개월
                self.anchors.setdefault(sector, {})
                self.anchors[sector]['per_median_5y'] = statistics.median(per_history[-60:]) if len(per_history) >= 60 else statistics.median(per_history)
                self.anchors[sector]['pbr_median_5y'] = statistics.median(pbr_history[-60:]) if len(pbr_history) >= 60 else statistics.median(pbr_history)
                self.anchors[sector]['roe_median_5y'] = statistics.median(roe_history[-60:]) if len(roe_history) >= 60 else statistics.median(roe_history)
        
        self._save_cache()


class QualityMetricsCalculator:
    """품질 지표 계산기"""
    
    @staticmethod
    def calculate_fcf_yield(fcf: float, market_cap: float) -> Optional[float]:
        """
        FCF Yield 계산
        fcf: 잉여현금흐름 (Free Cash Flow)
        market_cap: 시가총액
        """
        if market_cap and market_cap > 0:
            return (fcf / market_cap) * 100
        return None
    
    @staticmethod
    def calculate_interest_coverage(operating_income: float, interest_expense: float) -> Optional[float]:
        """
        이자보상배율 계산
        operating_income: 영업이익
        interest_expense: 이자비용
        """
        if interest_expense and interest_expense != 0:
            return operating_income / abs(interest_expense)
        elif operating_income > 0:
            return 999.0  # 무차입 경영 (매우 우수)
        return None
    
    @staticmethod
    def calculate_piotroski_fscore(financial_data: Dict) -> Tuple[int, Dict[str, int]]:
        """
        Piotroski F-Score 계산 (0-9점)
        
        Args:
            financial_data: {
                'net_income': 당기순이익,
                'cfo': 영업현금흐름,
                'roa': ROA (현재),
                'roa_prev': ROA (전년),
                'total_assets': 총자산,
                'current_assets': 유동자산,
                'current_liabilities': 유동부채,
                'long_term_debt': 장기부채,
                'long_term_debt_prev': 장기부채 (전년),
                'shares_outstanding': 발행주식수,
                'shares_outstanding_prev': 발행주식수 (전년),
                'gross_margin': 매출총이익률 (현재),
                'gross_margin_prev': 매출총이익률 (전년),
                'asset_turnover': 자산회전율 (현재),
                'asset_turnover_prev': 자산회전율 (전년)
            }
        
        Returns:
            (총점, 세부점수)
        """
        score = 0
        details = {}
        
        # 수익성 (4점)
        # 1. 순이익 > 0
        net_income = financial_data.get('net_income', 0)
        details['profit'] = 1 if net_income and net_income > 0 else 0
        score += details['profit']
        
        # 2. 영업현금흐름 > 0
        cfo = financial_data.get('cfo', 0)
        details['cfo_positive'] = 1 if cfo and cfo > 0 else 0
        score += details['cfo_positive']
        
        # 3. ROA 증가
        roa = financial_data.get('roa', 0)
        roa_prev = financial_data.get('roa_prev', 0)
        details['roa_increase'] = 1 if roa and roa_prev and roa > roa_prev else 0
        score += details['roa_increase']
        
        # 4. 발생액 품질 (CFO > Net Income)
        details['accrual_quality'] = 1 if cfo and net_income and cfo > net_income else 0
        score += details['accrual_quality']
        
        # 레버리지/유동성 (3점)
        # 5. 장기부채 감소
        ltd = financial_data.get('long_term_debt', 0)
        ltd_prev = financial_data.get('long_term_debt_prev', 0)
        details['debt_decrease'] = 1 if ltd_prev and ltd < ltd_prev else 0
        score += details['debt_decrease']
        
        # 6. 유동비율 증가
        current_assets = financial_data.get('current_assets', 0)
        current_liabilities = financial_data.get('current_liabilities', 1)
        current_assets_prev = financial_data.get('current_assets_prev', 0)
        current_liabilities_prev = financial_data.get('current_liabilities_prev', 1)
        
        current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0
        current_ratio_prev = current_assets_prev / current_liabilities_prev if current_liabilities_prev > 0 else 0
        
        details['current_ratio_increase'] = 1 if current_ratio > current_ratio_prev else 0
        score += details['current_ratio_increase']
        
        # 7. 신주발행 없음 (희석 방지)
        shares = financial_data.get('shares_outstanding', 0)
        shares_prev = financial_data.get('shares_outstanding_prev', 0)
        details['no_dilution'] = 1 if shares_prev and shares <= shares_prev else 0
        score += details['no_dilution']
        
        # 운영효율성 (2점)
        # 8. 매출총이익률 증가
        gm = financial_data.get('gross_margin', 0)
        gm_prev = financial_data.get('gross_margin_prev', 0)
        details['margin_increase'] = 1 if gm and gm_prev and gm > gm_prev else 0
        score += details['margin_increase']
        
        # 9. 자산회전율 증가
        turnover = financial_data.get('asset_turnover', 0)
        turnover_prev = financial_data.get('asset_turnover_prev', 0)
        details['turnover_increase'] = 1 if turnover and turnover_prev and turnover > turnover_prev else 0
        score += details['turnover_increase']
        
        return score, details
    
    @staticmethod
    def calculate_ev_to_sales(market_cap: float, net_debt: float, revenue: float) -> Optional[float]:
        """
        EV/Sales 계산
        market_cap: 시가총액
        net_debt: 순차입금 (부채 - 현금)
        revenue: 매출액
        """
        if revenue and revenue > 0:
            ev = market_cap + net_debt
            return ev / revenue
        return None
    
    @staticmethod
    def calculate_ev_to_ebit(market_cap: float, net_debt: float, ebit: float) -> Optional[float]:
        """
        EV/EBIT 계산
        market_cap: 시가총액
        net_debt: 순차입금
        ebit: 영업이익
        """
        if ebit and ebit > 0:
            ev = market_cap + net_debt
            return ev / ebit
        return None


class DataQualityGuard:
    """데이터 품질 가드"""
    
    @staticmethod
    def is_dummy_data(stock_data: Dict) -> bool:
        """더미 데이터 검증 (개선: 150.0 더미값 패턴 감지)"""
        # 1. 주요 지표가 모두 0 또는 None인지 체크
        critical_fields = ['per', 'pbr', 'roe', 'current_price', 'market_cap']
        zero_count = sum(1 for field in critical_fields if not stock_data.get(field))
        
        # 절반 이상이 0/None이면 더미 데이터로 판단
        if zero_count >= len(critical_fields) / 2:
            logger.warning(f"더미 데이터 감지 (필드 누락): {stock_data.get('symbol', 'UNKNOWN')} - {zero_count}/{len(critical_fields)} 필드 누락")
            return True
        
        # 2. ✅ v2.1.1: 150.0/150.0 더미값 패턴 감지
        debt_ratio = stock_data.get('debt_ratio')
        current_ratio = stock_data.get('current_ratio')
        
        # 부채비율과 유동비율이 정확히 150.0으로 동일한 경우 = 명백한 더미 데이터
        if debt_ratio == 150.0 and current_ratio == 150.0:
            logger.warning(f"더미 데이터 감지 (150/150 패턴): {stock_data.get('symbol', 'UNKNOWN')} - 부채비율={debt_ratio}, 유동비율={current_ratio}")
            return True
        
        return False
    
    @staticmethod
    def detect_accounting_anomalies(stock_data: Dict) -> Dict[str, Any]:
        """회계 이상 징후 감지"""
        anomalies = {}
        
        # 1. 일회성 손익 비중 체크
        net_income = stock_data.get('net_income', 0)
        operating_income = stock_data.get('operating_income', 0)
        
        if net_income and operating_income and operating_income != 0:
            non_operating_ratio = abs((net_income - operating_income) / operating_income)
            if non_operating_ratio > 0.5:  # 50% 이상
                anomalies['high_non_operating_income'] = {
                    'ratio': non_operating_ratio,
                    'severity': 'HIGH' if non_operating_ratio > 1.0 else 'MEDIUM'
                }
        
        # 2. 현금흐름 vs 이익 괴리
        cfo = stock_data.get('cfo', 0)
        if net_income and cfo and net_income != 0:
            cfo_to_ni_ratio = cfo / net_income
            if cfo_to_ni_ratio < 0.5:  # 현금흐름이 순이익의 50% 미만
                anomalies['poor_cash_quality'] = {
                    'ratio': cfo_to_ni_ratio,
                    'severity': 'HIGH' if cfo_to_ni_ratio < 0.3 else 'MEDIUM'
                }
        
        # 3. 매출채권 급증 (보수적: 전년 대비 2배 이상)
        receivables = stock_data.get('receivables', 0)
        receivables_prev = stock_data.get('receivables_prev', 0)
        
        if receivables and receivables_prev and receivables_prev > 0:
            receivables_growth = receivables / receivables_prev
            if receivables_growth > 2.0:
                anomalies['receivables_spike'] = {
                    'growth': receivables_growth,
                    'severity': 'MEDIUM'
                }
        
        # 4. 재고자산 급증
        inventory = stock_data.get('inventory', 0)
        inventory_prev = stock_data.get('inventory_prev', 0)
        
        if inventory and inventory_prev and inventory_prev > 0:
            inventory_growth = inventory / inventory_prev
            if inventory_growth > 2.0:
                anomalies['inventory_spike'] = {
                    'growth': inventory_growth,
                    'severity': 'MEDIUM'
                }
        
        return anomalies
    
    @staticmethod
    def check_data_freshness(stock_data: Dict, max_age_days: int = 180) -> bool:
        """데이터 신선도 체크"""
        data_date = stock_data.get('data_date')
        if not data_date:
            return False
        
        try:
            if isinstance(data_date, str):
                data_date = datetime.strptime(data_date, '%Y-%m-%d')
            
            age = (datetime.now() - data_date).days
            if age > max_age_days:
                logger.warning(f"오래된 데이터: {stock_data.get('symbol', 'UNKNOWN')} - {age}일 경과")
                return False
        except Exception as e:
            logger.error(f"데이터 날짜 파싱 실패: {e}")
            return False
        
        return True


class AlternativeValuationMetrics:
    """대체 밸류에이션 메트릭 (음수 PER 대응)"""
    
    @staticmethod
    def calculate_alternative_score(stock_data: Dict, sector_stats: Dict) -> float:
        """
        음수 PER 종목을 위한 대체 점수
        EV/Sales, P/S, Price/Book, 리버전 확률 등 활용
        
        Returns:
            0-20점 (PER 점수 대체)
        """
        score = 0
        
        # 1. EV/Sales 평가 (0-8점)
        ev_to_sales = stock_data.get('ev_to_sales')
        if ev_to_sales:
            sector_ev_sales_median = sector_stats.get('ev_sales_percentiles', {}).get('p50', 2.0)
            if ev_to_sales < sector_ev_sales_median * 0.5:
                score += 8
            elif ev_to_sales < sector_ev_sales_median * 0.75:
                score += 6
            elif ev_to_sales < sector_ev_sales_median:
                score += 4
            elif ev_to_sales < sector_ev_sales_median * 1.5:
                score += 2
        
        # 2. P/S 평가 (0-6점)
        ps = stock_data.get('ps')
        if ps:
            sector_ps_median = sector_stats.get('ps_percentiles', {}).get('p50', 1.0)
            if ps < sector_ps_median * 0.5:
                score += 6
            elif ps < sector_ps_median * 0.75:
                score += 4
            elif ps < sector_ps_median:
                score += 2
        
        # 3. 흑자 전환 징후 (0-6점)
        # 영업이익률 개선, 매출 증가 등
        operating_margin = stock_data.get('operating_margin', 0)
        operating_margin_prev = stock_data.get('operating_margin_prev', -999)
        
        if operating_margin > 0:
            score += 2  # 영업흑자
            if operating_margin_prev != -999 and operating_margin > operating_margin_prev:
                score += 2  # 개선 추세
        
        revenue_growth = stock_data.get('revenue_growth', 0)
        if revenue_growth > 10:
            score += 2  # 매출 성장
        
        return score


def enhance_stock_evaluation_with_quality(
    stock_data: Dict,
    sector_stats: Dict,
    long_term_anchors: LongTermAnchorCache,
    quality_calculator: QualityMetricsCalculator,
    data_guard: DataQualityGuard
) -> Dict[str, Any]:
    """
    품질 지표를 포함한 종합 평가
    
    Returns:
        {
            'quality_score': float,  # 0-100
            'quality_details': dict,
            'data_quality_flags': dict,
            'alternative_valuation': dict  # 음수 PER 대응
        }
    """
    result = {
        'quality_score': 0,
        'quality_details': {},
        'data_quality_flags': {},
        'alternative_valuation': {}
    }
    
    # 1. 데이터 품질 체크
    if data_guard.is_dummy_data(stock_data):
        result['data_quality_flags']['is_dummy'] = True
        return result
    
    anomalies = data_guard.detect_accounting_anomalies(stock_data)
    if anomalies:
        result['data_quality_flags']['anomalies'] = anomalies
    
    # 2. 품질 지표 계산
    quality_score = 0
    
    # FCF Yield (0-15점)
    fcf = stock_data.get('fcf', stock_data.get('operating_cash_flow', 0))
    market_cap = stock_data.get('market_cap', 0)
    fcf_yield = quality_calculator.calculate_fcf_yield(fcf, market_cap)
    
    if fcf_yield:
        result['quality_details']['fcf_yield'] = fcf_yield
        if fcf_yield > 10:
            quality_score += 15
        elif fcf_yield > 7:
            quality_score += 12
        elif fcf_yield > 5:
            quality_score += 9
        elif fcf_yield > 3:
            quality_score += 6
        elif fcf_yield > 0:
            quality_score += 3
    
    # Interest Coverage (0-10점)
    operating_income = stock_data.get('operating_income', 0)
    interest_expense = stock_data.get('interest_expense', 0)
    interest_coverage = quality_calculator.calculate_interest_coverage(operating_income, interest_expense)
    
    if interest_coverage:
        result['quality_details']['interest_coverage'] = interest_coverage
        if interest_coverage > 10:
            quality_score += 10
        elif interest_coverage > 5:
            quality_score += 8
        elif interest_coverage > 3:
            quality_score += 6
        elif interest_coverage > 2:
            quality_score += 4
        elif interest_coverage > 1:
            quality_score += 2
    
    # Piotroski F-Score (0-18점, 2점/점)
    try:
        fscore, fscore_details = quality_calculator.calculate_piotroski_fscore(stock_data)
        result['quality_details']['piotroski_fscore'] = fscore
        result['quality_details']['piotroski_details'] = fscore_details
        quality_score += fscore * 2  # 최대 18점
    except Exception as e:
        logger.warning(f"Piotroski F-Score 계산 실패: {e}")
    
    result['quality_score'] = quality_score
    
    # 3. 음수 PER 대체 밸류에이션
    per = stock_data.get('per', 0)
    if per <= 0:
        alt_metrics = AlternativeValuationMetrics()
        alt_score = alt_metrics.calculate_alternative_score(stock_data, sector_stats)
        result['alternative_valuation'] = {
            'score': alt_score,
            'used': True,
            'reason': 'negative_per'
        }
    
    return result


# 테스트 함수
if __name__ == '__main__':
    # 샘플 데이터로 테스트
    print("=== 가치주 발굴 개선 모듈 테스트 ===\n")
    
    # 1. 장기 앵커 캐시 테스트
    print("1. 장기 앵커 캐시 시스템")
    anchor_cache = LongTermAnchorCache()
    print(f"   캐시 상태: {len(anchor_cache.anchors)} 섹터")
    
    # 2. 품질 지표 계산 테스트
    print("\n2. 품질 지표 계산")
    qm = QualityMetricsCalculator()
    
    fcf_yield = qm.calculate_fcf_yield(fcf=50000000000, market_cap=1000000000000)
    print(f"   FCF Yield: {fcf_yield:.2f}%")
    
    interest_coverage = qm.calculate_interest_coverage(operating_income=100000000000, interest_expense=5000000000)
    print(f"   이자보상배율: {interest_coverage:.2f}x")
    
    # 3. Piotroski F-Score 테스트
    print("\n3. Piotroski F-Score 계산")
    sample_data = {
        'net_income': 100000000000,
        'cfo': 120000000000,
        'roa': 8.5,
        'roa_prev': 7.2,
        'long_term_debt': 300000000000,
        'long_term_debt_prev': 350000000000,
        'current_assets': 500000000000,
        'current_liabilities': 300000000000,
        'current_assets_prev': 450000000000,
        'current_liabilities_prev': 320000000000,
        'shares_outstanding': 1000000000,
        'shares_outstanding_prev': 1000000000,
        'gross_margin': 35.0,
        'gross_margin_prev': 32.0,
        'asset_turnover': 1.2,
        'asset_turnover_prev': 1.1
    }
    
    fscore, details = qm.calculate_piotroski_fscore(sample_data)
    print(f"   F-Score: {fscore}/9점")
    print(f"   세부: {details}")
    
    # 4. 데이터 품질 가드 테스트
    print("\n4. 데이터 품질 체크")
    guard = DataQualityGuard()
    
    dummy_data = {'symbol': 'TEST001', 'per': 0, 'pbr': 0, 'roe': 0}
    is_dummy = guard.is_dummy_data(dummy_data)
    print(f"   더미 데이터 감지: {is_dummy}")
    
    print("\n=== 테스트 완료 ===")

