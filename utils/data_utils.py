"""Data validation and conversion helpers extracted from the analyzer."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

import enum
import logging
import math

import numpy as np
import pandas as pd

# JSON 직렬화를 위한 타입 정의
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]


class DataValidator:
    """Data validation utilities shared across the analyzer."""

    @staticmethod
    def _finite(val: Any, default: float = 0.0) -> float:
        try:
            x = float(val)
            if math.isfinite(x):
                return x
        except Exception:
            pass
        return default

    @staticmethod
    def safe_divide(numerator: Any, denominator: Any, default: float = None, allow_negative_den: bool = False) -> Optional[float]:
        try:
            num = DataValidator._finite(numerator)
            den = DataValidator._finite(denominator)
            if den == 0 or (den < 0 and not allow_negative_den):
                return default
            result = num / den
            return result if math.isfinite(result) else default
        except Exception:
            return default

    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None or pd.isna(value):
                return default
            if isinstance(value, str):
                v = value.strip().replace(',', '')
                if v == '':
                    return default
                return float(v)
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def validate_price_data(price_data: Dict[str, Any]) -> bool:
        """가격 데이터 유효성 검증"""
        try:
            if not price_data or not isinstance(price_data, dict):
                return False
            
            # 필수 필드 확인
            required_fields = ['current_price', 'volume']
            for field in required_fields:
                if field not in price_data:
                    return False
                
                value = price_data[field]
                if value is None or pd.isna(value):
                    return False
                
                # 숫자형 검증
                if not isinstance(value, (int, float)) or value < 0:
                    return False
            
            return True
        except Exception:
            return False

    @staticmethod
    def validate_financial_data(financial_data: Dict[str, Any]) -> bool:
        """재무 데이터 유효성 검증"""
        try:
            if not financial_data or not isinstance(financial_data, dict):
                return False
            
            # 필수 필드 확인 (최소한의 필수 필드)
            required_fields = ['symbol']
            for field in required_fields:
                if field not in financial_data:
                    return False
                
                value = financial_data[field]
                if value is None:
                    return False
            
            # 숫자 필드 검증 (존재하는 경우)
            numeric_fields = ['per', 'pbr', 'eps', 'bps', 'market_cap']
            for field in numeric_fields:
                if field in financial_data:
                    value = financial_data[field]
                    if value is not None and not isinstance(value, (int, float)):
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            return False
            
            return True
        except Exception:
            return False

    @staticmethod
    def safe_float_optional(value: Any) -> Optional[float]:
        try:
            if value is None or pd.isna(value):
                return None
            if isinstance(value, float):
                return value if math.isfinite(value) else None
            if isinstance(value, str):
                v = value.strip().replace(',', '')
                if v == '':
                    return None
                x = float(v)
                return x if math.isfinite(x) else None
            x = float(value)
            return x if math.isfinite(x) else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def is_valid_symbol(symbol: str) -> bool:
        if not symbol or not isinstance(symbol, str):
            return False
        import re
        return bool(re.match(r'^\d{6}$', symbol.strip()))

    @staticmethod
    def is_preferred_stock(name: str) -> bool:
        if not name or not isinstance(name, str):
            return False
        s = name.strip()
        from .env_utils import safe_env_bool  # type: ignore
        if safe_env_bool("PREFERRED_STOCK_INCLUDE_WOORI", False) and s.startswith("우리"):
            return True
        import re
        pat = re.compile(r"(?:\((?:우|우B|우C)\)|\b우선주\b|(?:\s|^)우(?:B|C)?$)")
        return bool(pat.search(s))

    @staticmethod
    def serialize_for_json(obj: Any):
        from datetime import date, datetime
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, enum.Enum):
            return obj.value
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, "tolist"):
            try:
                return obj.tolist()
            except Exception:
                pass
        if isinstance(obj, (np.generic,)):
            try:
                return obj.item()
            except Exception:
                pass
        if isinstance(obj, dict):
            return {DataValidator.serialize_for_json(k): DataValidator.serialize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [DataValidator.serialize_for_json(x) for x in obj]
        if hasattr(obj, "__dict__"):
            return {k: DataValidator.serialize_for_json(v) for k, v in obj.__dict__.items()}
        return str(obj)


class DataConverter:
    PERCENT_FIELDS = {
        "roe", "roa", "revenue_growth_rate", "operating_income_growth_rate",
        "net_income_growth_rate", "net_profit_margin", "gross_profit_margin",
        "debt_ratio", "equity_ratio", "current_ratio"
    }

    @staticmethod
    def to_percent(x: Any) -> float:
        v = DataValidator.safe_float(x, 0.0)
        return v * 100.0 if abs(v) <= 5.0 else v

    @staticmethod
    def normalize_percentage(value: Any, assume_ratio_if_abs_lt_1: bool = True) -> Optional[float]:
        try:
            v = float(value)
            if pd.isna(v):
                return None
            return v * 100.0 if assume_ratio_if_abs_lt_1 and -1.0 <= v <= 1.0 else v
        except Exception:
            return None

    @staticmethod
    def format_percentage(value: Any, decimal_places: int = 1) -> str:
        try:
            if value is None or pd.isna(value):
                return "N/A"
            v = float(value)
            return f"{v:.{decimal_places}f}%"
        except Exception:
            return "N/A"

    @staticmethod
    def standardize_financial_units(data: Dict[str, Any]) -> Dict[str, Any]:
        from .env_utils import _refresh_env_cache  # type: ignore

        if data.get("_percent_canonicalized") is True:
            raise ValueError("CRITICAL: Data already canonicalized!")

        try:
            _refresh_env_cache()
        except Exception:
            pass
        out = data.copy()

        for k in DataConverter.PERCENT_FIELDS:
            if k in out:
                v = out[k]
                if v is None or (isinstance(v, float) and (not math.isfinite(v))):
                    out[k] = None
                else:
                    if k == "current_ratio":
                        vv = DataValidator.safe_float_optional(v)
                        if vv is None:
                            out[k] = None
                        else:
                            from .env_utils import safe_env_bool
                            force_percent = safe_env_bool("CURRENT_RATIO_FORCE_PERCENT", False)
                            if force_percent:
                                out[k] = vv * 100.0 if 0.0 <= vv <= 5.0 else vv
                            elif 0.0 <= vv <= 10.0:
                                out[k] = vv * 100.0
                            elif vv >= 50.0:
                                out[k] = vv
                            else:
                                out[k] = max(10.0, min(300.0, vv))
                    else:
                        out[k] = DataConverter.to_percent(v)
                    if out[k] is not None:
                        bounds = 5000.0 if k in ["roe", "roa"] else 1000.0 if k.endswith("growth_rate") else 10000.0
                        if abs(out[k]) > bounds:
                            out[k] = math.copysign(bounds, out[k])

        for k, v in list(out.items()):
            if k in DataConverter.PERCENT_FIELDS:
                continue
            if isinstance(v, (int, float)):
                out[k] = v if math.isfinite(float(v)) else None
            elif isinstance(v, str):
                out[k] = DataValidator.safe_float_optional(v)
            elif v is None:
                out[k] = None

        out["_percent_canonicalized"] = True
        return out

    @staticmethod
    def convert_price_data(price_data: Dict[str, Any]) -> Dict[str, Any]:
        """가격 데이터 변환 및 정규화"""
        try:
            logging.debug(f"convert_price_data 시작: {price_data}")
            
            if not price_data or not isinstance(price_data, dict):
                logging.warning("가격 데이터가 비어있거나 딕셔너리가 아님")
                return {}
            
            converted_data = {}
            
            # 기본 가격 정보 변환
            price_fields = {
                'current_price': 'current_price',
                'open_price': 'open_price', 
                'high_price': 'high_price',
                'low_price': 'low_price',
                'close_price': 'close_price',
                'volume': 'volume',
                'market_cap': 'market_cap'
            }
            
            logging.debug(f"변환할 필드들: {price_fields}")
            
            for source_field, target_field in price_fields.items():
                if source_field in price_data:
                    value = price_data[source_field]
                    converted_value = DataValidator.safe_float(value, 0.0)
                    converted_data[target_field] = converted_value
                    logging.debug(f"  {source_field} -> {target_field}: {value} -> {converted_value}")
                else:
                    logging.debug(f"  {source_field} 필드 없음")
            
            logging.debug(f"변환된 데이터: {converted_data}")
            
            # 추가 계산 필드
            if 'current_price' in converted_data and 'close_price' in converted_data:
                current = converted_data['current_price']
                close = converted_data['close_price']
                if close > 0:
                    converted_data['price_change_rate'] = ((current - close) / close) * 100
            
            logging.debug(f"최종 변환 결과: {converted_data}")
            return converted_data
            
        except Exception as e:
            logging.error(f"가격 데이터 변환 실패: {e}")
            import traceback
            logging.error(f"스택 트레이스: {traceback.format_exc()}")
            return {}

    @staticmethod
    def convert_financial_data(financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """재무 데이터 변환 및 정규화"""
        try:
            if not financial_data or not isinstance(financial_data, dict):
                return {}
            
            converted_data = {}
            
            # 기본 재무 정보 변환
            financial_fields = {
                'symbol': 'symbol',
                'per': 'per',
                'pbr': 'pbr', 
                'eps': 'eps',
                'bps': 'bps',
                'dividend_yield': 'dividend_yield',
                'market_cap': 'market_cap',
                'listed_shares': 'listed_shares',
                'trading_value': 'trading_value',
                'sector': 'sector'
            }
            
            for source_field, target_field in financial_fields.items():
                if source_field in financial_data:
                    value = financial_data[source_field]
                    if source_field == 'symbol' or source_field == 'sector':
                        converted_data[target_field] = str(value) if value is not None else ''
                    else:
                        converted_data[target_field] = DataValidator.safe_float(value, 0.0)
            
            # 추가 계산 필드
            if 'eps' in converted_data and 'bps' in converted_data:
                eps = converted_data['eps']
                bps = converted_data['bps']
                if bps > 0:
                    converted_data['roe'] = (eps / bps) * 100  # ROE 계산
            
            return converted_data
            
        except Exception as e:
            logging.error(f"재무 데이터 변환 실패: {e}")
            return {}


def serialize_for_json(obj: Any) -> JSONValue:
    """
    Convert various Python/NumPy/Decimal/Datetime containers to JSON-serializable.
    - Handles: dict/list/tuple/set, numpy scalars/arrays, Decimal, datetime/date, objects with __dict__
    """
    from datetime import date, datetime

    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "tolist"):  # numpy arrays
        try:
            return obj.tolist()
        except Exception:
            pass
    # numpy scalar detection (more robust than module check)
    if isinstance(obj, (np.generic,)):
        try:
            return obj.item()
        except Exception:
            pass
    if isinstance(obj, dict):
        return {serialize_for_json(k): serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [serialize_for_json(x) for x in obj]
    if hasattr(obj, "__dict__"):
        return {k: serialize_for_json(v) for k, v in obj.__dict__.items()}
    return str(obj)


