"""Input reliability and validation guards."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .env_utils import safe_env_bool, safe_env_int
from .metrics import MetricsCollector


class InputReliabilityGuard:
    """입력 데이터 신뢰도 검증 및 가드 클래스"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 핵심 재무 필드 정의 (2개 이상 결측 시 스코어링 제외)
        self.core_financial_fields = {
            'roe', 'roa', 'debt_ratio', 'net_profit_margin', 'current_ratio'
        }
        # 시총 스크립트 모드 강제 설정
        self.market_cap_strict_mode = safe_env_bool("MARKET_CAP_STRICT_MODE", True)
        # 결측 필드 임계치 (환경변수로 조정 가능)
        self.max_missing_core_fields = safe_env_int("MAX_MISSING_CORE_FIELDS", 2, 0)
    
    def validate_market_cap_reliability(self, market_cap: Optional[float]) -> Tuple[bool, str]:
        """시가총액 신뢰도 검증"""
        if market_cap is None:
            return False, "market_cap_missing"
        
        # 스크립트 모드에서 애매한 밴드(1e7~1e11원) 드롭
        if self.market_cap_strict_mode and 1e7 <= market_cap < 1e11:
            return False, "market_cap_ambiguous_strict_mode"
        
        # 이상치 검증 (너무 작거나 큰 값) - 억원 단위 기준
        if market_cap < 1e-2:  # 0.01억원 미만 (100만원 미만)
            return False, "market_cap_too_small"
        if market_cap > 1e6:  # 100만억원 초과 (100조원 초과)
            return False, "market_cap_too_large"
        
        return True, "valid"
    
    def validate_financial_data_reliability(self, financial_data: Dict[str, Any]) -> Tuple[bool, str, int]:
        """재무 데이터 신뢰도 검증"""
        if not financial_data:
            return False, "financial_data_empty", 0
        
        # 핵심 필드 결측 개수 계산
        missing_count = 0
        for field in self.core_financial_fields:
            if field not in financial_data or financial_data[field] is None:
                missing_count += 1
        
        # 결측 필드 메트릭 기록
        if self.metrics and missing_count > 0:
            self.metrics.record_missing_financial_fields(missing_count)
        
        # 임계치 초과 시 스코어링 제외
        if missing_count > self.max_missing_core_fields:
            return False, f"too_many_missing_fields_{missing_count}", missing_count
        
        return True, "valid", missing_count
    
    def validate_price_data_reliability(self, price_data: Dict[str, Any]) -> Tuple[bool, str]:
        """가격 데이터 신뢰도 검증"""
        if not price_data:
            return False, "price_data_empty"
        
        # 필수 가격 필드 검증
        required_fields = ['current_price', '52w_high', '52w_low']
        missing_fields = [field for field in required_fields if field not in price_data or price_data[field] is None]
        
        if missing_fields:
            return False, f"missing_price_fields_{','.join(missing_fields)}"
        
        # 52주 밴드 유효성 검증
        high = price_data.get('52w_high', 0)
        low = price_data.get('52w_low', 0)
        current = price_data.get('current_price', 0)
        
        if high <= 0 or low <= 0 or current <= 0:
            return False, "invalid_price_values"
        
        if high < low:
            return False, "invalid_52w_band"
        
        return True, "valid"
    
    def validate_symbol_reliability(self, symbol: str) -> Tuple[bool, str]:
        """종목 코드 신뢰도 검증"""
        if not symbol or not isinstance(symbol, str):
            return False, "symbol_invalid_type"
        
        symbol = symbol.strip()
        if len(symbol) != 6 or not symbol.isdigit():
            return False, "symbol_invalid_format"
        
        return True, "valid"
    
    def validate_overall_reliability(self, symbol: str, market_cap: Optional[float], 
                                   financial_data: Dict[str, Any], price_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """전체 입력 데이터 신뢰도 종합 검증"""
        validation_results = {}
        
        # 각 항목별 검증
        symbol_valid, symbol_reason = self.validate_symbol_reliability(symbol)
        validation_results['symbol'] = {'valid': symbol_valid, 'reason': symbol_reason}
        
        market_cap_valid, market_cap_reason = self.validate_market_cap_reliability(market_cap)
        validation_results['market_cap'] = {'valid': market_cap_valid, 'reason': market_cap_reason}
        
        financial_valid, financial_reason, missing_count = self.validate_financial_data_reliability(financial_data)
        validation_results['financial_data'] = {'valid': financial_valid, 'reason': financial_reason, 'missing_count': missing_count}
        
        price_valid, price_reason = self.validate_price_data_reliability(price_data)
        validation_results['price_data'] = {'valid': price_valid, 'reason': price_reason}
        
        # 전체 유효성 판단 (모든 핵심 항목이 유효해야 함)
        overall_valid = symbol_valid and market_cap_valid and financial_valid and price_valid
        
        if not overall_valid:
            reasons = [f"{k}: {v['reason']}" for k, v in validation_results.items() if not v['valid']]
            overall_reason = f"validation_failed: {', '.join(reasons)}"
        else:
            overall_reason = "all_valid"
        
        return overall_valid, overall_reason, validation_results












