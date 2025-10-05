"""
로깅 및 에러 처리 유틸리티 모듈

이 모듈은 애플리케이션 전체에서 사용되는 공통 로깅 기능과 에러 분류를 제공합니다.
"""

import logging
from typing import Optional


class LogLevel:
    """로깅 레벨 상수"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


class ErrorType:
    """에러 타입 분류 상수 (메트릭스 집계용)"""
    API_TIMEOUT = "api_timeout"
    API_CONNECTION = "api_connection"
    API_RATE_LIMIT = "api_rate_limit"
    DATA_PARSE = "data_parse"
    SECTOR_PEER_DATA = "sector_peer_data_error"
    FINANCIAL_DATA = "financial_data_error"
    PRICE_DATA = "price_data_error"
    STABILITY_RATIO = "stability_ratio_error"
    # ✅ 추가된 에러타입 상수들
    OPINION = "opinion_analysis_error"
    ESTIMATE = "estimate_analysis_error"
    EMPTY_PRICE_PAYLOAD = "empty_price_payload"
    INVALID_52W_BAND = "invalid_52w_band"  # 52주 밴드 빈약/퇴화
    HTTP_4XX = "http_4xx"
    HTTP_5XX = "http_5xx"
    UNKNOWN = "unknown_error"
    
    # 상위 카테고리 매핑 (SRE 대시보드용)
    CATEGORY_MAP = {
        API_TIMEOUT: "네트워크",
        API_CONNECTION: "네트워크", 
        API_RATE_LIMIT: "HTTP",
        HTTP_4XX: "HTTP",
        HTTP_5XX: "HTTP",
        DATA_PARSE: "데이터",
        FINANCIAL_DATA: "데이터",
        PRICE_DATA: "데이터",
        EMPTY_PRICE_PAYLOAD: "데이터",
        INVALID_52W_BAND: "데이터",
        SECTOR_PEER_DATA: "분석",
        STABILITY_RATIO: "분석",
        OPINION: "분석",
        ESTIMATE: "분석",
        UNKNOWN: "기타"
    }
    
    @classmethod
    def get_category(cls, error_type: str) -> str:
        """에러 타입을 상위 카테고리로 매핑"""
        return cls.CATEGORY_MAP.get(error_type, "기타")


def log_error(operation: str, symbol: Optional[str] = None, error: Optional[Exception] = None, level: str = LogLevel.WARNING):
    """일관된 에러 로깅 포맷 (운영 로그 grep 친화적)"""
    if symbol:
        message = f"{operation} 실패 | symbol={symbol} | err={error}"
    else:
        message = f"{operation} 실패 | err={error}"
    
    # ✅ LogLevel 값 일관성 개선: 레벨 매핑 사용
    LEVEL_MAP = {
        LogLevel.ERROR: logging.error,
        LogLevel.WARNING: logging.warning,
        LogLevel.INFO: logging.info,
        LogLevel.DEBUG: logging.debug
    }
    LEVEL_MAP.get(level, logging.warning)(message)


def log_success(operation: str, symbol: Optional[str] = None, details: Optional[str] = None):
    """일관된 성공 로깅 포맷"""
    if symbol and details:
        message = f"✅ {operation} 성공 {symbol}: {details}"
    elif symbol:
        message = f"✅ {operation} 성공 {symbol}"
    else:
        message = f"✅ {operation} 성공"
    
    logging.info(message)





