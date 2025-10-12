#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
동적 r, b 레짐 계산 모듈
금리 레짐 전환 시 정당 멀티플 안정성 확보
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import statistics

logger = logging.getLogger(__name__)


class DynamicRegimeCalculator:
    """동적 r(요구수익률), b(유보율) 계산기"""
    
    # 캐시 (월별 갱신)
    _cached_regime = None
    _cache_month = None
    
    # 기본 파라미터 (폴백용)
    DEFAULT_RISK_FREE_RATE = 0.035  # 3.5% (한국 국채 10년 평균)
    
    SECTOR_RISK_PREMIUM = {
        '금융': 0.065,      # 6.5%
        '금융업': 0.065,
        '통신': 0.070,      # 7.0%
        '통신업': 0.070,
        '제조업': 0.080,    # 8.0%
        '필수소비재': 0.075,
        '운송': 0.085,      # 8.5%
        '운송장비': 0.085,
        '전기전자': 0.085,
        'IT': 0.090,        # 9.0%
        '기술업': 0.090,
        '건설': 0.085,
        '건설업': 0.085,
        '바이오/제약': 0.085,
        '에너지/화학': 0.080,
        '소비재': 0.075,
        '서비스업': 0.080,
        '철강금속': 0.080,
        '섬유의복': 0.075,
        '종이목재': 0.080,
        '유통업': 0.075,
        '기타': 0.080
    }
    
    def __init__(self):
        self.risk_free_rate_cache = {}
        self.payout_ratio_cache = {}
    
    def get_dynamic_r(self, sector: str, use_cache: bool = True) -> float:
        """
        동적 요구수익률(r) 계산
        r = 무위험수익률 + 섹터 리스크 프리미엄
        
        Args:
            sector: 정규화된 섹터명
            use_cache: 월별 캐시 사용 여부
        
        Returns:
            요구수익률 (소수)
        """
        try:
            # 월별 캐시 확인
            current_month = datetime.now().strftime('%Y-%m')
            if use_cache and DynamicRegimeCalculator._cache_month == current_month:
                if DynamicRegimeCalculator._cached_regime:
                    cached_r = DynamicRegimeCalculator._cached_regime.get('r', {}).get(sector)
                    if cached_r:
                        return cached_r
            
            # 무위험수익률 조회 (실제로는 API 또는 데이터 소스 필요)
            risk_free = self._get_current_risk_free_rate()
            
            # 섹터 리스크 프리미엄
            risk_premium = self.SECTOR_RISK_PREMIUM.get(sector, 0.080)
            
            r = risk_free + risk_premium
            
            # 상식 범위 체크 (5% ~ 20%)
            r = max(0.05, min(0.20, r))
            
            # 캐시 저장
            if use_cache:
                if DynamicRegimeCalculator._cached_regime is None:
                    DynamicRegimeCalculator._cached_regime = {'r': {}, 'b': {}}
                DynamicRegimeCalculator._cached_regime['r'][sector] = r
                DynamicRegimeCalculator._cache_month = current_month
            
            logger.debug(f"동적 r 계산: {sector} → {r:.4f} (무위험: {risk_free:.4f}, 프리미엄: {risk_premium:.4f})")
            return r
            
        except Exception as e:
            logger.warning(f"동적 r 계산 실패, 기본값 사용: {e}")
            # 폴백
            return self.DEFAULT_RISK_FREE_RATE + self.SECTOR_RISK_PREMIUM.get(sector, 0.080)
    
    def get_dynamic_b(self, sector: str, stock_data: Optional[Dict] = None, use_cache: bool = True) -> float:
        """
        동적 유보율(b) 계산
        - 개별 종목: 최근 3~5년 가중평균 유보율 (윈저라이즈)
        - 섹터 평균: 섹터 내 중앙값 유보율
        
        Args:
            sector: 정규화된 섹터명
            stock_data: 개별 종목 재무 데이터 (선택)
            use_cache: 월별 캐시 사용 여부
        
        Returns:
            유보율 (소수, 0.0~1.0)
        """
        try:
            # 월별 캐시 확인
            current_month = datetime.now().strftime('%Y-%m')
            if use_cache and DynamicRegimeCalculator._cache_month == current_month:
                if DynamicRegimeCalculator._cached_regime:
                    cached_b = DynamicRegimeCalculator._cached_regime.get('b', {}).get(sector)
                    if cached_b:
                        return cached_b
            
            # 개별 종목 데이터가 있으면 우선 사용
            if stock_data:
                b_stock = self._calculate_stock_payout_ratio(stock_data)
                if b_stock is not None:
                    return b_stock
            
            # 섹터 기본값 (실제로는 DB나 캐시에서 섹터 통계 조회)
            sector_defaults = {
                '금융': 0.40, '금융업': 0.40,
                '통신': 0.55, '통신업': 0.55,
                '제조업': 0.35, '필수소비재': 0.40,
                '운송': 0.35, '운송장비': 0.35,
                '전기전자': 0.35, 'IT': 0.30, '기술업': 0.30,
                '건설': 0.35, '건설업': 0.35,
                '바이오/제약': 0.30, '에너지/화학': 0.35, '소비재': 0.40,
                '서비스업': 0.35, '철강금속': 0.35, '섬유의복': 0.40,
                '종이목재': 0.35, '유통업': 0.40,
                '기타': 0.35
            }
            
            b = sector_defaults.get(sector, 0.35)
            
            # 캐시 저장
            if use_cache:
                if DynamicRegimeCalculator._cached_regime is None:
                    DynamicRegimeCalculator._cached_regime = {'r': {}, 'b': {}}
                DynamicRegimeCalculator._cached_regime['b'][sector] = b
                DynamicRegimeCalculator._cache_month = current_month
            
            return b
            
        except Exception as e:
            logger.warning(f"동적 b 계산 실패, 기본값 사용: {e}")
            return 0.35
    
    def _get_current_risk_free_rate(self) -> float:
        """
        현재 무위험수익률 조회
        실제로는 한국은행 API나 데이터 소스에서 국채 10년물 수익률 조회
        
        Returns:
            무위험수익률 (소수)
        """
        try:
            # TODO: 실제 API 연동 (한국은행 경제통계시스템 등)
            # 현재는 최근 평균값 사용
            return self.DEFAULT_RISK_FREE_RATE
            
        except Exception as e:
            logger.warning(f"무위험수익률 조회 실패: {e}")
            return self.DEFAULT_RISK_FREE_RATE
    
    def _calculate_stock_payout_ratio(self, stock_data: Dict) -> Optional[float]:
        """
        개별 종목의 유보율(배당성향의 역수) 계산
        
        Args:
            stock_data: 종목 재무 데이터
        
        Returns:
            유보율 (0.0~1.0), 계산 불가 시 None
        """
        try:
            # 배당금 / 순이익 = 배당성향
            dividend_per_share = stock_data.get('dividend_per_share', 0)
            eps = stock_data.get('eps', 0)
            
            if eps <= 0:
                return None
            
            payout_ratio = dividend_per_share / eps  # 배당성향
            
            # 윈저라이즈 (0% ~ 80% 범위)
            payout_ratio = max(0.0, min(0.80, payout_ratio))
            
            # 유보율 = 1 - 배당성향
            b = 1.0 - payout_ratio
            
            # 상식 범위 체크 (20% ~ 100%)
            b = max(0.20, min(1.00, b))
            
            return b
            
        except Exception as e:
            logger.debug(f"개별 종목 유보율 계산 실패: {e}")
            return None
    
    def validate_mos_inputs(self, per: float, pbr: float, roe: float, sector: str) -> Tuple[bool, str]:
        """
        MoS 계산 입력값 검증
        
        Args:
            per: PER
            pbr: PBR
            roe: ROE (%)
            sector: 섹터명
        
        Returns:
            (유효 여부, 경고 메시지)
        """
        warnings = []
        
        # 1. 음수/0 체크
        if per <= 0:
            warnings.append("PER ≤ 0")
        if pbr <= 0:
            warnings.append("PBR ≤ 0")
        if roe <= 0:
            warnings.append("ROE ≤ 0")
        
        # 2. 이상치 체크
        if per > 100:
            warnings.append(f"PER={per:.1f} (이상치)")
        if pbr > 10:
            warnings.append(f"PBR={pbr:.1f} (이상치)")
        if roe < -50 or roe > 100:
            warnings.append(f"ROE={roe:.1f}% (이상치)")
        
        # 3. g ≥ r 체크 (구조적 불안정)
        r = self.get_dynamic_r(sector)
        b = self.get_dynamic_b(sector)
        g = (roe / 100.0) * b
        
        if g >= r:
            warnings.append(f"g={g:.4f} ≥ r={r:.4f} (분모 0/음수 위험)")
        
        is_valid = len(warnings) == 0
        msg = "; ".join(warnings) if warnings else "OK"
        
        return is_valid, msg


class DataFreshnessGuard:
    """데이터 신선도 및 정합성 가드 (v2.2 신규)"""
    
    @staticmethod
    def check_data_freshness(data_dict: Dict) -> Tuple[bool, str]:
        """
        데이터 신선도 체크
        
        Args:
            data_dict: {'price_ts': timestamp, 'financial_ts': timestamp, 'sector': str}
        
        Returns:
            (신선 여부, 경고 메시지)
        """
        try:
            price_ts = data_dict.get('price_ts')
            financial_ts = data_dict.get('financial_ts')
            
            if not price_ts or not financial_ts:
                return False, "타임스탬프 누락"
            
            # 가격 신선도: 최근 3영업일 이내
            now = datetime.now()
            price_age = (now - price_ts).days
            if price_age > 3:
                return False, f"가격 데이터 오래됨 ({price_age}일)"
            
            # 재무 신선도: 최근 6개월 이내
            financial_age = (now - financial_ts).days
            if financial_age > 180:
                return False, f"재무 데이터 오래됨 ({financial_age}일)"
            
            # 정합성: 재무 데이터가 가격보다 미래면 룩어헤드 바이어스
            if financial_ts > price_ts + timedelta(days=2):
                return False, "재무 데이터가 가격보다 미래 (룩어헤드 바이어스)"
            
            return True, "OK"
            
        except Exception as e:
            return False, f"신선도 체크 오류: {e}"
    
    @staticmethod
    def check_financial_sanity(financial_data: Dict) -> Tuple[bool, str]:
        """
        재무 데이터 상식 범위 체크
        
        Args:
            financial_data: {'per': float, 'pbr': float, 'roe': float, ...}
        
        Returns:
            (정상 여부, 경고 메시지)
        """
        warnings = []
        
        per = financial_data.get('per', 0)
        pbr = financial_data.get('pbr', 0)
        roe = financial_data.get('roe', 0)
        eps = financial_data.get('eps', 0)
        bps = financial_data.get('bps', 0)
        
        # PER 범위 (음수 ~ 300배)
        if per < 0 or per > 300:
            warnings.append(f"PER={per:.1f} (비정상)")
        
        # PBR 범위 (0.1배 ~ 20배)
        if pbr < 0.1 or pbr > 20:
            warnings.append(f"PBR={pbr:.1f} (비정상)")
        
        # ROE 범위 (-100% ~ 150%)
        if roe < -100 or roe > 150:
            warnings.append(f"ROE={roe:.1f}% (비정상)")
        
        # EPS/BPS 0 또는 음수
        if eps <= 0:
            warnings.append("EPS ≤ 0")
        if bps <= 0:
            warnings.append("BPS ≤ 0")
        
        # 일관성: PER * EPS ≈ Price (10% 오차 허용)
        # PBR * BPS ≈ Price (10% 오차 허용)
        # (실제로는 current_price 필요)
        
        is_sane = len(warnings) == 0
        msg = "; ".join(warnings) if warnings else "OK"
        
        return is_sane, msg
    
    @staticmethod
    def check_sector_mapping(sector: str, valid_sectors: set) -> Tuple[bool, str]:
        """
        섹터 매핑 유효성 체크
        
        Args:
            sector: 섹터명
            valid_sectors: 유효한 섹터 집합
        
        Returns:
            (유효 여부, 경고 메시지)
        """
        if not sector or sector.strip() == '':
            return False, "섹터 누락"
        
        if sector in ['기타', '미분류', 'N/A']:
            return False, f"섹터 미매핑 ({sector})"
        
        if sector not in valid_sectors:
            return False, f"알 수 없는 섹터 ({sector})"
        
        return True, "OK"


# ===== 사용 예시 =====
if __name__ == "__main__":
    # 동적 레짐 계산기 초기화
    regime_calc = DynamicRegimeCalculator()
    
    # 섹터별 동적 r, b 조회
    sector = '전기전자'
    r = regime_calc.get_dynamic_r(sector)
    b = regime_calc.get_dynamic_b(sector)
    
    print(f"섹터: {sector}")
    print(f"요구수익률(r): {r:.4f} ({r*100:.2f}%)")
    print(f"유보율(b): {b:.4f} ({b*100:.2f}%)")
    
    # MoS 입력값 검증
    is_valid, msg = regime_calc.validate_mos_inputs(
        per=12.5, pbr=1.2, roe=15.0, sector=sector
    )
    print(f"MoS 입력 검증: {is_valid}, {msg}")
    
    # 데이터 신선도 가드
    guard = DataFreshnessGuard()
    
    # 신선도 체크
    is_fresh, msg = guard.check_data_freshness({
        'price_ts': datetime.now(),
        'financial_ts': datetime.now() - timedelta(days=30),
        'sector': sector
    })
    print(f"데이터 신선도: {is_fresh}, {msg}")
    
    # 재무 상식 체크
    is_sane, msg = guard.check_financial_sanity({
        'per': 12.5, 'pbr': 1.2, 'roe': 15.0, 'eps': 5000, 'bps': 50000
    })
    print(f"재무 상식 체크: {is_sane}, {msg}")

