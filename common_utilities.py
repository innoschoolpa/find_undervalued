# common_utilities.py
"""
공통 유틸리티 모듈
- 중복 코드 제거
- 재사용 가능한 함수들
- 공통 로직 추출
"""

import pandas as pd
import numpy as np
import logging
import time
import re
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

# =============================================================================
# 1. 데이터 변환 및 검증 유틸리티
# =============================================================================

class DataConverter:
    """데이터 변환 유틸리티 클래스"""
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """안전하게 float로 변환"""
        if value is None or pd.isna(value):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        """안전하게 int로 변환"""
        if value is None or pd.isna(value):
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_str(value: Any, default: str = "") -> str:
        """안전하게 str로 변환"""
        if value is None or pd.isna(value):
            return default
        try:
            return str(value).strip()
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def normalize_percentage(value: Any, assume_ratio_if_abs_lt_1: bool = True) -> float:
        """퍼센트 값을 정규화 (0.12 → 12.0)"""
        try:
            v = float(value)
            if pd.isna(v):
                return 0.0
            return v * 100.0 if assume_ratio_if_lt_1 and -1.0 <= v <= 1.0 else v
        except Exception:
            return 0.0
    
    @staticmethod
    def format_percentage(value: Any, decimal_places: int = 1) -> str:
        """퍼센트 값 포맷팅"""
        try:
            if value is None or pd.isna(value):
                return "N/A"
            v = float(value)
            return f"{v:.{decimal_places}f}%"
        except Exception:
            return "N/A"
    
    @staticmethod
    def format_currency(value: Any, currency: str = "원") -> str:
        """통화 값 포맷팅"""
        try:
            if value is None or pd.isna(value):
                return "N/A"
            v = float(value)
            return f"{v:,.0f}{currency}"
        except Exception:
            return "N/A"

class DataValidator:
    """데이터 검증 유틸리티 클래스"""
    
    @staticmethod
    def is_valid_symbol(symbol: str) -> bool:
        """종목 코드 유효성 검사"""
        if not symbol or not isinstance(symbol, str):
            return False
        # 6자리 숫자 패턴
        return bool(re.match(r'^\d{6}$', symbol.strip()))
    
    @staticmethod
    def is_preferred_stock(name: str) -> bool:
        """우선주 여부 확인"""
        if not name or not isinstance(name, str):
            return False
        pref_pattern = r'\s*우(?:[ABC])?(?:\(.+?\))?\s*$'
        return bool(re.search(pref_pattern, name))
    
    @staticmethod
    def is_valid_financial_ratio(value: Any, min_val: float = -999, max_val: float = 999) -> bool:
        """재무비율 유효성 검사"""
        try:
            v = float(value)
            return not pd.isna(v) and min_val <= v <= max_val
        except Exception:
            return False
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """필수 필드 검증"""
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or pd.isna(data[field]):
                missing_fields.append(field)
        return missing_fields

# =============================================================================
# 2. 파일 및 I/O 유틸리티
# =============================================================================

class FileUtils:
    """파일 처리 유틸리티 클래스"""
    
    @staticmethod
    def ensure_directory(path: str) -> bool:
        """디렉토리 존재 확인 및 생성"""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"디렉토리 생성 실패 {path}: {e}")
            return False
    
    @staticmethod
    def safe_read_json(file_path: str, default: Dict = None) -> Dict:
        """안전하게 JSON 파일 읽기"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"JSON 파일 읽기 실패 {file_path}: {e}")
            return default or {}
    
    @staticmethod
    def safe_write_json(file_path: str, data: Dict, ensure_ascii: bool = False) -> bool:
        """안전하게 JSON 파일 쓰기"""
        try:
            # 디렉토리 확인
            FileUtils.ensure_directory(os.path.dirname(file_path))
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=ensure_ascii, indent=2)
            return True
        except Exception as e:
            logger.error(f"JSON 파일 쓰기 실패 {file_path}: {e}")
            return False
    
    @staticmethod
    def safe_read_excel(file_path: str, sheet_name: str = None) -> Optional[pd.DataFrame]:
        """안전하게 Excel 파일 읽기"""
        try:
            return pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
        except Exception as e:
            logger.warning(f"Excel 파일 읽기 실패 {file_path}: {e}")
            return None
    
    @staticmethod
    def safe_write_csv(file_path: str, df: pd.DataFrame, encoding: str = 'utf-8-sig') -> bool:
        """안전하게 CSV 파일 쓰기"""
        try:
            # 디렉토리 확인
            FileUtils.ensure_directory(os.path.dirname(file_path))
            
            df.to_csv(file_path, index=False, encoding=encoding)
            return True
        except Exception as e:
            logger.error(f"CSV 파일 쓰기 실패 {file_path}: {e}")
            return False

# =============================================================================
# 3. 시간 및 날짜 유틸리티
# =============================================================================

class TimeUtils:
    """시간 관련 유틸리티 클래스"""
    
    @staticmethod
    def get_timestamp() -> str:
        """현재 타임스탬프 문자열 반환"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    @staticmethod
    def get_date_string() -> str:
        """현재 날짜 문자열 반환"""
        return datetime.now().strftime("%Y-%m-%d")
    
    @staticmethod
    def get_datetime_string() -> str:
        """현재 날짜시간 문자열 반환"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def is_business_hours() -> bool:
        """영업시간 여부 확인 (한국 시간 기준)"""
        now = datetime.now()
        # 월-금 9:00-18:00
        return (now.weekday() < 5 and 
                9 <= now.hour < 18)
    
    @staticmethod
    def get_market_open_time() -> datetime:
        """다음 시장 개장 시간 반환"""
        now = datetime.now()
        
        # 오늘 9시
        today_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        
        if now < today_open and now.weekday() < 5:
            return today_open
        
        # 다음 영업일 9시
        days_ahead = 1
        while True:
            next_day = now + timedelta(days=days_ahead)
            if next_day.weekday() < 5:  # 월-금
                return next_day.replace(hour=9, minute=0, second=0, microsecond=0)
            days_ahead += 1

# =============================================================================
# 4. 수학 및 통계 유틸리티
# =============================================================================

class MathUtils:
    """수학 관련 유틸리티 클래스"""
    
    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """안전한 나눗셈 (0으로 나누기 방지)"""
        try:
            if denominator == 0 or pd.isna(denominator):
                return default
            result = numerator / denominator
            return result if not pd.isna(result) else default
        except Exception:
            return default
    
    @staticmethod
    def calculate_percentage_change(old_value: float, new_value: float) -> float:
        """변화율 계산"""
        if old_value == 0 or pd.isna(old_value):
            return 0.0
        return MathUtils.safe_divide(new_value - old_value, old_value) * 100
    
    @staticmethod
    def calculate_compound_growth_rate(values: List[float]) -> float:
        """복합 성장률 계산"""
        if len(values) < 2:
            return 0.0
        
        try:
            # 첫 번째와 마지막 값으로 CAGR 계산
            first_value = values[0]
            last_value = values[-1]
            periods = len(values) - 1
            
            if first_value <= 0 or last_value <= 0:
                return 0.0
            
            cagr = (last_value / first_value) ** (1 / periods) - 1
            return cagr * 100
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_volatility(values: List[float]) -> float:
        """변동성 계산 (표준편차)"""
        if len(values) < 2:
            return 0.0
        
        try:
            return np.std(values) * 100
        except Exception:
            return 0.0
    
    @staticmethod
    def normalize_score(value: float, min_val: float, max_val: float, 
                       target_min: float = 0, target_max: float = 100) -> float:
        """점수 정규화"""
        if max_val == min_val:
            return target_min
        
        normalized = (value - min_val) / (max_val - min_val)
        return target_min + normalized * (target_max - target_min)

# =============================================================================
# 5. 성능 측정 유틸리티
# =============================================================================

class PerformanceProfiler:
    """성능 측정 유틸리티 클래스"""
    
    def __init__(self):
        self.measurements = {}
    
    def start_timer(self, name: str) -> None:
        """타이머 시작"""
        self.measurements[name] = {
            'start_time': time.time(),
            'end_time': None,
            'duration': None
        }
    
    def end_timer(self, name: str) -> float:
        """타이머 종료 및 지속시간 반환"""
        if name not in self.measurements:
            return 0.0
        
        end_time = time.time()
        start_time = self.measurements[name]['start_time']
        duration = end_time - start_time
        
        self.measurements[name].update({
            'end_time': end_time,
            'duration': duration
        })
        
        return duration
    
    def get_measurement(self, name: str) -> Optional[Dict[str, float]]:
        """측정 결과 조회"""
        return self.measurements.get(name)
    
    def get_all_measurements(self) -> Dict[str, Dict[str, float]]:
        """모든 측정 결과 조회"""
        return self.measurements.copy()
    
    def reset(self) -> None:
        """측정 결과 초기화"""
        self.measurements.clear()

def measure_time(name: str = None):
    """실행 시간 측정 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            timer_name = name or func.__name__
            profiler = PerformanceProfiler()
            
            profiler.start_timer(timer_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = profiler.end_timer(timer_name)
                logger.info(f"{timer_name} 실행 시간: {duration:.3f}초")
        
        return wrapper
    return decorator

# =============================================================================
# 6. 재시도 및 백오프 유틸리티
# =============================================================================

class RetryUtils:
    """재시도 관련 유틸리티 클래스"""
    
    @staticmethod
    def exponential_backoff(attempt: int, 
                           base_delay: float = 1.0,
                           max_delay: float = 60.0,
                           exponential_base: float = 2.0,
                           jitter: bool = True) -> float:
        """지수 백오프 지연 시간 계산"""
        if attempt <= 0:
            return 0
        
        delay = base_delay * (exponential_base ** (attempt - 1))
        delay = min(delay, max_delay)
        
        if jitter:
            jitter_factor = np.random.uniform(0.5, 1.5)
            delay *= jitter_factor
        
        return delay
    
    @staticmethod
    def linear_backoff(attempt: int, 
                      base_delay: float = 1.0,
                      max_delay: float = 60.0,
                      increment: float = 1.0) -> float:
        """선형 백오프 지연 시간 계산"""
        if attempt <= 0:
            return 0
        
        delay = base_delay + (attempt - 1) * increment
        delay = min(delay, max_delay)
        
        return delay

# =============================================================================
# 7. 문자열 처리 유틸리티
# =============================================================================

class StringUtils:
    """문자열 처리 유틸리티 클래스"""
    
    @staticmethod
    def clean_symbol(symbol: str) -> str:
        """종목 코드 정리 (6자리 0패딩)"""
        if not symbol:
            return ""
        
        # 숫자만 추출
        cleaned = re.sub(r'[^\d]', '', str(symbol))
        
        # 6자리 0패딩
        return cleaned.zfill(6)
    
    @staticmethod
    def clean_company_name(name: str) -> str:
        """회사명 정리"""
        if not name:
            return ""
        
        # 앞뒤 공백 제거
        cleaned = str(name).strip()
        
        # 연속된 공백을 하나로
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    @staticmethod
    def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
        """문자열 자르기"""
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """문자열에서 숫자 추출"""
        if not text:
            return []
        
        pattern = r'-?\d+\.?\d*'
        matches = re.findall(pattern, str(text))
        
        numbers = []
        for match in matches:
            try:
                numbers.append(float(match))
            except ValueError:
                continue
        
        return numbers

# =============================================================================
# 8. 전역 유틸리티 인스턴스
# =============================================================================

# 전역 인스턴스들
data_converter = DataConverter()
data_validator = DataValidator()
file_utils = FileUtils()
time_utils = TimeUtils()
math_utils = MathUtils()
performance_profiler = PerformanceProfiler()
retry_utils = RetryUtils()
string_utils = StringUtils()

# =============================================================================
# 9. 사용 예시
# =============================================================================

if __name__ == "__main__":
    # 데이터 변환 예시
    print("=== 데이터 변환 예시 ===")
    print(f"safe_float('12.34'): {data_converter.safe_float('12.34')}")
    print(f"normalize_percentage(0.1234): {data_converter.normalize_percentage(0.1234)}")
    print(f"format_percentage(12.34): {data_converter.format_percentage(12.34)}")
    
    # 데이터 검증 예시
    print("\n=== 데이터 검증 예시 ===")
    print(f"is_valid_symbol('005930'): {data_validator.is_valid_symbol('005930')}")
    print(f"is_preferred_stock('삼성전자우'): {data_validator.is_preferred_stock('삼성전자우')}")
    
    # 성능 측정 예시
    print("\n=== 성능 측정 예시 ===")
    
    @measure_time("test_function")
    def test_function():
        time.sleep(0.1)
        return "완료"
    
    result = test_function()
    print(f"결과: {result}")
    
    # 수학 계산 예시
    print("\n=== 수학 계산 예시 ===")
    values = [100, 110, 120, 130, 140]
    print(f"복합 성장률: {math_utils.calculate_compound_growth_rate(values):.2f}%")
    print(f"변동성: {math_utils.calculate_volatility(values):.2f}%")
    
    # 재시도 예시
    print("\n=== 재시도 예시 ===")
    for i in range(1, 6):
        delay = retry_utils.exponential_backoff(i, base_delay=1.0, max_delay=10.0)
        print(f"시도 {i}: {delay:.2f}초 대기")

