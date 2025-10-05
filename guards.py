"""
입력 신뢰도 및 데이터 검증 가드 모듈

입력 데이터의 신뢰도를 검증하고 데이터 품질을 보장하는 클래스들을 제공합니다.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from metrics import MetricsCollector
from utils.data_utils import DataConverter
from utils.env_utils import safe_env_bool, safe_env_int


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
    
    def validate_percentage_units_consistency(self, financial_data: Dict[str, Any]) -> Tuple[bool, str]:
        """% 단위 일관성 검증 (이중 스케일링 방지)"""
        # 이미 표준화되었는지 확인
        if financial_data.get("_percent_canonicalized") is not True:
            return False, "percent_not_canonicalized"
        
        # % 필드들의 값 범위 검증
        percent_fields = DataConverter.PERCENT_FIELDS
        for field in percent_fields:
            if field in financial_data and financial_data[field] is not None:
                value = financial_data[field]
                if isinstance(value, (int, float)) and not math.isfinite(value):
                    return False, f"invalid_percent_value_{field}"
                # 비정상적으로 큰 % 값 검증 (예: 1000% 이상)
                if isinstance(value, (int, float)) and abs(value) > 1000:
                    return False, f"percent_value_too_large_{field}"
        
        return True, "valid"
    
    def validate_input_reliability(self, symbol: str, market_cap: Optional[float], 
                                 financial_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """종합 입력 신뢰도 검증"""
        validation_result = {
            'market_cap_valid': False,
            'financial_data_valid': False,
            'percentage_units_valid': False,
            'missing_core_fields': 0,
            'validation_errors': []
        }
        
        # 1. 시가총액 검증
        mc_valid, mc_error = self.validate_market_cap_reliability(market_cap)
        validation_result['market_cap_valid'] = mc_valid
        if not mc_valid:
            validation_result['validation_errors'].append(f"market_cap: {mc_error}")
        
        # 2. 재무 데이터 검증
        fin_valid, fin_error, missing_count = self.validate_financial_data_reliability(financial_data)
        validation_result['financial_data_valid'] = fin_valid
        validation_result['missing_core_fields'] = missing_count
        if not fin_valid:
            validation_result['validation_errors'].append(f"financial_data: {fin_error}")
        
        # 3. % 단위 일관성 검증
        pct_valid, pct_error = self.validate_percentage_units_consistency(financial_data)
        validation_result['percentage_units_valid'] = pct_valid
        if not pct_valid:
            validation_result['validation_errors'].append(f"percentage_units: {pct_error}")
        
        # 전체 검증 결과
        overall_valid = mc_valid and fin_valid and pct_valid
        error_summary = "; ".join(validation_result['validation_errors']) if validation_result['validation_errors'] else "valid"
        
        return overall_valid, error_summary, validation_result





