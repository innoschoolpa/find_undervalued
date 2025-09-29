#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Input Validator
- 강화된 입력 검증 시스템
- 비즈니스 로직 검증
- 데이터 무결성 보장
- 보안 검증
"""

import re
import logging
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, date

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """검증 심각도"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    value: Any = None
    suggestions: List[str] = None

class BusinessRuleValidator:
    """비즈니스 규칙 검증기"""
    
    # 주식 관련 상수
    MIN_STOCK_PRICE = 100  # 최소 주가 (원)
    MAX_STOCK_PRICE = 10000000  # 최대 주가 (원)
    MIN_MARKET_CAP = 1000000000  # 최소 시가총액 (10억원)
    MAX_MARKET_CAP = 1000000000000000  # 최대 시가총액 (1000조원)
    
    # 재무 비율 상수
    MIN_PER = 0.1
    MAX_PER = 1000.0
    MIN_PBR = 0.01
    MAX_PBR = 100.0
    MIN_ROE = -100.0
    MAX_ROE = 100.0
    MIN_DEBT_RATIO = 0.0
    MAX_DEBT_RATIO = 1000.0
    
    @staticmethod
    def validate_stock_symbol(symbol: str) -> ValidationResult:
        """종목 코드 검증"""
        if not symbol or not isinstance(symbol, str):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="종목 코드는 문자열이어야 합니다",
                field="symbol"
            )
        
        symbol = symbol.strip()
        
        # 6자리 숫자 패턴
        if not re.match(r'^\d{6}$', symbol):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="종목 코드는 6자리 숫자여야 합니다",
                field="symbol",
                value=symbol,
                suggestions=["예: 005930 (삼성전자)"]
            )
        
        # 유효한 종목 코드 범위 확인 (6자리 숫자이므로 000000~999999)
        code_int = int(symbol)
        if code_int < 0 or code_int > 999999:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="종목 코드가 유효한 범위를 벗어났습니다",
                field="symbol",
                value=symbol
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="유효한 종목 코드입니다",
            field="symbol",
            value=symbol
        )
    
    @staticmethod
    def validate_stock_price(price: Any) -> ValidationResult:
        """주가 검증"""
        try:
            price_float = float(price)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="주가는 숫자여야 합니다",
                field="price",
                value=price
            )
        
        if pd.isna(price_float):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="주가가 유효하지 않습니다 (NaN)",
                field="price"
            )
        
        if price_float <= 0:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="주가는 양수여야 합니다",
                field="price",
                value=price_float
            )
        
        if price_float < BusinessRuleValidator.MIN_STOCK_PRICE:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"주가가 너무 낮습니다 (최소: {BusinessRuleValidator.MIN_STOCK_PRICE:,}원)",
                field="price",
                value=price_float
            )
        
        if price_float > BusinessRuleValidator.MAX_STOCK_PRICE:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"주가가 너무 높습니다 (최대: {BusinessRuleValidator.MAX_STOCK_PRICE:,}원)",
                field="price",
                value=price_float
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="유효한 주가입니다",
            field="price",
            value=price_float
        )
    
    @staticmethod
    def validate_market_cap(market_cap: Any) -> ValidationResult:
        """시가총액 검증"""
        try:
            cap_float = float(market_cap)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="시가총액은 숫자여야 합니다",
                field="market_cap",
                value=market_cap
            )
        
        if pd.isna(cap_float):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="시가총액이 유효하지 않습니다 (NaN)",
                field="market_cap"
            )
        
        if cap_float <= 0:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="시가총액은 양수여야 합니다",
                field="market_cap",
                value=cap_float
            )
        
        if cap_float < BusinessRuleValidator.MIN_MARKET_CAP:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"시가총액이 너무 작습니다 (최소: {BusinessRuleValidator.MIN_MARKET_CAP:,}원)",
                field="market_cap",
                value=cap_float
            )
        
        if cap_float > BusinessRuleValidator.MAX_MARKET_CAP:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"시가총액이 너무 큽니다 (최대: {BusinessRuleValidator.MAX_MARKET_CAP:,}원)",
                field="market_cap",
                value=cap_float
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="유효한 시가총액입니다",
            field="market_cap",
            value=cap_float
        )
    
    @staticmethod
    def validate_per_ratio(per: Any) -> ValidationResult:
        """PER 비율 검증"""
        try:
            per_float = float(per)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="PER은 숫자여야 합니다",
                field="per",
                value=per
            )
        
        if pd.isna(per_float):
            return ValidationResult(
                is_valid=True,  # PER이 없을 수 있음
                severity=ValidationSeverity.INFO,
                message="PER 데이터가 없습니다",
                field="per"
            )
        
        if per_float < BusinessRuleValidator.MIN_PER:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"PER이 너무 낮습니다 (최소: {BusinessRuleValidator.MIN_PER})",
                field="per",
                value=per_float
            )
        
        if per_float > BusinessRuleValidator.MAX_PER:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"PER이 너무 높습니다 (최대: {BusinessRuleValidator.MAX_PER})",
                field="per",
                value=per_float
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="유효한 PER입니다",
            field="per",
            value=per_float
        )
    
    @staticmethod
    def validate_roe(roe: Any) -> ValidationResult:
        """ROE 검증"""
        try:
            roe_float = float(roe)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="ROE는 숫자여야 합니다",
                field="roe",
                value=roe
            )
        
        if pd.isna(roe_float):
            return ValidationResult(
                is_valid=True,  # ROE가 없을 수 있음
                severity=ValidationSeverity.INFO,
                message="ROE 데이터가 없습니다",
                field="roe"
            )
        
        if roe_float < BusinessRuleValidator.MIN_ROE:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"ROE가 너무 낮습니다 (최소: {BusinessRuleValidator.MIN_ROE}%)",
                field="roe",
                value=roe_float
            )
        
        if roe_float > BusinessRuleValidator.MAX_ROE:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"ROE가 너무 높습니다 (최대: {BusinessRuleValidator.MAX_ROE}%)",
                field="roe",
                value=roe_float
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="유효한 ROE입니다",
            field="roe",
            value=roe_float
        )

class SecurityValidator:
    """보안 검증기"""
    
    @staticmethod
    def validate_api_key(api_key: str) -> ValidationResult:
        """API 키 검증"""
        if not api_key or not isinstance(api_key, str):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="API 키는 문자열이어야 합니다",
                field="api_key"
            )
        
        api_key = api_key.strip()
        
        # 길이 검증
        if len(api_key) < 10:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="API 키가 너무 짧습니다",
                field="api_key"
            )
        
        if len(api_key) > 100:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="API 키가 너무 깁니다",
                field="api_key"
            )
        
        # 더미 키 검증
        dummy_patterns = [
            r'^test.*',
            r'^dummy.*',
            r'^sample.*',
            r'^example.*',
            r'^your_.*',
            r'^replace_.*'
        ]
        
        for pattern in dummy_patterns:
            if re.match(pattern, api_key, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.CRITICAL,
                    message="더미 API 키가 감지되었습니다. 실제 키로 교체하세요",
                    field="api_key",
                    value=api_key[:10] + "..."  # 보안을 위해 일부만 표시
                )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="유효한 API 키 형식입니다",
            field="api_key"
        )
    
    @staticmethod
    def validate_input_safety(input_data: str) -> ValidationResult:
        """입력 데이터 보안 검증"""
        if not input_data or not isinstance(input_data, str):
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message="입력 데이터가 없습니다"
            )
        
        # SQL 인젝션 패턴 검증
        sql_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)',
            r'(\b(UNION|OR|AND)\b.*\b(SELECT|INSERT|UPDATE|DELETE)\b)',
            r'(\b(EXEC|EXECUTE)\b)',
            r'(\b(SCRIPT|JAVASCRIPT|VBSCRIPT)\b)'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.CRITICAL,
                    message="잠재적인 SQL 인젝션 패턴이 감지되었습니다",
                    field="input_data"
                )
        
        # XSS 패턴 검증
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>'
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.CRITICAL,
                    message="잠재적인 XSS 패턴이 감지되었습니다",
                    field="input_data"
                )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="입력 데이터가 안전합니다"
        )

class EnhancedInputValidator:
    """
    강화된 입력 검증기
    - 비즈니스 규칙 검증
    - 보안 검증
    - 데이터 무결성 검증
    """
    
    def __init__(self):
        self.business_validator = BusinessRuleValidator()
        self.security_validator = SecurityValidator()
        self.validation_history: List[ValidationResult] = []
    
    def validate_stock_data(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """주식 데이터 종합 검증"""
        results = []
        
        # 필수 필드 검증
        required_fields = ['symbol', 'name']
        for field in required_fields:
            if field not in data or not data[field]:
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"필수 필드가 누락되었습니다: {field}",
                    field=field
                ))
        
        # 종목 코드 검증
        if 'symbol' in data:
            symbol_result = self.business_validator.validate_stock_symbol(data['symbol'])
            results.append(symbol_result)
        
        # 주가 검증
        if 'current_price' in data:
            price_result = self.business_validator.validate_stock_price(data['current_price'])
            results.append(price_result)
        
        # 시가총액 검증
        if 'market_cap' in data:
            cap_result = self.business_validator.validate_market_cap(data['market_cap'])
            results.append(cap_result)
        
        # PER 검증
        if 'per' in data:
            per_result = self.business_validator.validate_per_ratio(data['per'])
            results.append(per_result)
        
        # ROE 검증
        if 'roe' in data:
            roe_result = self.business_validator.validate_roe(data['roe'])
            results.append(roe_result)
        
        # 보안 검증
        for key, value in data.items():
            if isinstance(value, str):
                security_result = self.security_validator.validate_input_safety(value)
                if not security_result.is_valid:
                    results.append(security_result)
        
        # 검증 결과 저장
        self.validation_history.extend(results)
        
        return results
    
    def validate_api_config(self, config: Dict[str, Any]) -> List[ValidationResult]:
        """API 설정 검증"""
        results = []
        
        # API 키 검증
        if 'api_key' in config:
            key_result = self.security_validator.validate_api_key(config['api_key'])
            results.append(key_result)
        
        # URL 검증
        if 'base_url' in config:
            url_result = self._validate_url(config['base_url'])
            results.append(url_result)
        
        # 타임아웃 검증
        if 'timeout' in config:
            timeout_result = self._validate_timeout(config['timeout'])
            results.append(timeout_result)
        
        return results
    
    def _validate_url(self, url: str) -> ValidationResult:
        """URL 검증"""
        if not url or not isinstance(url, str):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="URL은 문자열이어야 합니다",
                field="base_url"
            )
        
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="유효하지 않은 URL 형식입니다",
                field="base_url",
                value=url
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="유효한 URL입니다",
            field="base_url",
            value=url
        )
    
    def _validate_timeout(self, timeout: Any) -> ValidationResult:
        """타임아웃 검증"""
        try:
            timeout_float = float(timeout)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="타임아웃은 숫자여야 합니다",
                field="timeout",
                value=timeout
            )
        
        if timeout_float <= 0:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="타임아웃은 양수여야 합니다",
                field="timeout",
                value=timeout_float
            )
        
        if timeout_float > 300:  # 5분
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message="타임아웃이 너무 깁니다 (최대: 300초)",
                field="timeout",
                value=timeout_float
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="유효한 타임아웃입니다",
            field="timeout",
            value=timeout_float
        )
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """검증 요약 반환"""
        total_validations = len(self.validation_history)
        error_count = sum(1 for r in self.validation_history if r.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for r in self.validation_history if r.severity == ValidationSeverity.WARNING)
        critical_count = sum(1 for r in self.validation_history if r.severity == ValidationSeverity.CRITICAL)
        
        return {
            'total_validations': total_validations,
            'error_count': error_count,
            'warning_count': warning_count,
            'critical_count': critical_count,
            'success_rate': ((total_validations - error_count - critical_count) / total_validations * 100 
                           if total_validations > 0 else 100.0),
            'recent_validations': [self._result_to_dict(r) for r in self.validation_history[-10:]]
        }
    
    def _result_to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """검증 결과를 딕셔너리로 변환"""
        return {
            'is_valid': result.is_valid,
            'severity': result.severity.value,
            'message': result.message,
            'field': result.field,
            'value': str(result.value) if result.value is not None else None,
            'suggestions': result.suggestions
        }

# 전역 검증기 인스턴스
_global_validator = None

def get_global_validator() -> EnhancedInputValidator:
    """전역 검증기 반환"""
    global _global_validator
    if _global_validator is None:
        _global_validator = EnhancedInputValidator()
    return _global_validator
