# API 참조 문서

## 개요

향상된 통합 분석 시스템의 API 참조 문서입니다. 이 문서는 모든 공개 클래스, 메서드, 함수의 상세한 사용법을 제공합니다.

## 목차

1. [핵심 클래스](#핵심-클래스)
2. [유틸리티 클래스](#유틸리티-클래스)
3. [에러 처리](#에러-처리)
4. [캐싱 시스템](#캐싱-시스템)
5. [로깅 시스템](#로깅-시스템)
6. [설정 관리](#설정-관리)
7. [사용 예시](#사용-예시)

---

## 핵심 클래스

### EnhancedIntegratedAnalyzer

향상된 통합 분석의 메인 클래스입니다.

#### 생성자

```python
def __init__(self, config_file: str = "config.yaml")
```

**매개변수:**
- `config_file` (str): 설정 파일 경로 (기본값: "config.yaml")

**예시:**
```python
analyzer = EnhancedIntegratedAnalyzer("my_config.yaml")
```

#### 주요 메서드

##### analyze_single_stock

단일 종목의 향상된 통합 분석을 수행합니다.

```python
def analyze_single_stock(self, symbol: str, name: str, days_back: int = 30) -> AnalysisResult
```

**매개변수:**
- `symbol` (str): 종목 코드 (6자리 숫자)
- `name` (str): 종목명
- `days_back` (int): 투자의견 분석 기간 (일, 기본값: 30)

**반환값:**
- `AnalysisResult`: 분석 결과 객체

**예시:**
```python
result = analyzer.analyze_single_stock("005930", "삼성전자", 30)
print(f"점수: {result.enhanced_score}")
print(f"등급: {result.enhanced_grade}")
```

##### get_top_market_cap_stocks

시가총액 상위 종목들을 반환합니다.

```python
def get_top_market_cap_stocks(self, count: int = 100, min_market_cap: float = 500) -> List[Dict[str, Any]]
```

**매개변수:**
- `count` (int): 반환할 종목 수 (기본값: 100)
- `min_market_cap` (float): 최소 시가총액 (억원, 기본값: 500)

**반환값:**
- `List[Dict[str, Any]]`: 종목 정보 리스트

**예시:**
```python
stocks = analyzer.get_top_market_cap_stocks(50, 1000)
for stock in stocks:
    print(f"{stock['name']}: {stock['market_cap']}억원")
```

### AnalysisResult

분석 결과를 담는 데이터 클래스입니다.

#### 속성

- `symbol` (str): 종목 코드
- `name` (str): 종목명
- `status` (AnalysisStatus): 분석 상태
- `enhanced_score` (float): 향상된 통합 점수
- `enhanced_grade` (str): 향상된 등급
- `market_cap` (float): 시가총액
- `current_price` (float): 현재가
- `price_position` (Optional[float]): 52주 위치
- `risk_score` (Optional[float]): 리스크 점수
- `financial_data` (Dict[str, Any]): 재무 데이터
- `opinion_analysis` (Dict[str, Any]): 투자의견 분석
- `estimate_analysis` (Dict[str, Any]): 추정실적 분석
- `score_breakdown` (Dict[str, float]): 점수 구성

#### 예시

```python
result = analyzer.analyze_single_stock("005930", "삼성전자")

# 기본 정보
print(f"종목: {result.name} ({result.symbol})")
print(f"점수: {result.enhanced_score:.1f}점")
print(f"등급: {result.enhanced_grade}")

# 점수 구성
for category, score in result.score_breakdown.items():
    print(f"{category}: {score:.1f}점")

# 재무 데이터
financial = result.financial_data
print(f"ROE: {financial.get('roe', 0):.1f}%")
print(f"부채비율: {financial.get('debt_ratio', 0):.1f}%")
```

---

## 유틸리티 클래스

### DataConverter

데이터 변환을 위한 유틸리티 클래스입니다.

#### 주요 메서드

##### safe_float

안전하게 float로 변환합니다.

```python
@staticmethod
def safe_float(value: Any, default: float = 0.0) -> float
```

**매개변수:**
- `value` (Any): 변환할 값
- `default` (float): 변환 실패 시 기본값 (기본값: 0.0)

**반환값:**
- `float`: 변환된 float 값

**예시:**
```python
converter = DataConverter()
value = converter.safe_float("12.34")  # 12.34
value = converter.safe_float("invalid")  # 0.0
value = converter.safe_float(None, 1.0)  # 1.0
```

##### normalize_percentage

퍼센트 값을 정규화합니다.

```python
@staticmethod
def normalize_percentage(value: Any, assume_ratio_if_abs_lt_1: bool = True) -> float
```

**매개변수:**
- `value` (Any): 정규화할 값
- `assume_ratio_if_abs_lt_1` (bool): 절댓값이 1 미만이면 비율로 간주 (기본값: True)

**반환값:**
- `float`: 정규화된 퍼센트 값

**예시:**
```python
converter = DataConverter()
value = converter.normalize_percentage(0.1234)  # 12.34
value = converter.normalize_percentage(12.34)  # 12.34
```

### DataValidator

데이터 검증을 위한 유틸리티 클래스입니다.

#### 주요 메서드

##### is_valid_symbol

종목 코드 유효성을 검사합니다.

```python
@staticmethod
def is_valid_symbol(symbol: str) -> bool
```

**매개변수:**
- `symbol` (str): 검사할 종목 코드

**반환값:**
- `bool`: 유효성 여부

**예시:**
```python
validator = DataValidator()
print(validator.is_valid_symbol("005930"))  # True
print(validator.is_valid_symbol("12345"))   # False (5자리)
print(validator.is_valid_symbol("abc123"))  # False (문자 포함)
```

##### is_preferred_stock

우선주 여부를 확인합니다.

```python
@staticmethod
def is_preferred_stock(name: str) -> bool
```

**매개변수:**
- `name` (str): 검사할 종목명

**반환값:**
- `bool`: 우선주 여부

**예시:**
```python
validator = DataValidator()
print(validator.is_preferred_stock("삼성전자우"))  # True
print(validator.is_preferred_stock("삼성전자"))    # False
```

### MathUtils

수학 계산을 위한 유틸리티 클래스입니다.

#### 주요 메서드

##### safe_divide

안전한 나눗셈을 수행합니다.

```python
@staticmethod
def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float
```

**매개변수:**
- `numerator` (float): 분자
- `denominator` (float): 분모
- `default` (float): 0으로 나누기 시 기본값 (기본값: 0.0)

**반환값:**
- `float`: 나눗셈 결과

**예시:**
```python
math_utils = MathUtils()
result = math_utils.safe_divide(10, 2)  # 5.0
result = math_utils.safe_divide(10, 0)  # 0.0
result = math_utils.safe_divide(10, 0, 1.0)  # 1.0
```

##### calculate_percentage_change

변화율을 계산합니다.

```python
@staticmethod
def calculate_percentage_change(old_value: float, new_value: float) -> float
```

**매개변수:**
- `old_value` (float): 이전 값
- `new_value` (float): 현재 값

**반환값:**
- `float`: 변화율 (%)

**예시:**
```python
math_utils = MathUtils()
change = math_utils.calculate_percentage_change(100, 110)  # 10.0
change = math_utils.calculate_percentage_change(100, 90)   # -10.0
```

---

## 에러 처리

### 커스텀 예외 클래스

#### AnalysisError

분석 관련 기본 예외 클래스입니다.

```python
class AnalysisError(Exception):
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None)
```

**매개변수:**
- `message` (str): 에러 메시지
- `error_code` (str): 에러 코드 (선택사항)
- `details` (Dict[str, Any]): 추가 세부사항 (선택사항)

#### DataProviderError

데이터 제공자 관련 예외 클래스입니다.

```python
class DataProviderError(AnalysisError):
    pass
```

#### APIRateLimitError

API 호출 제한 예외 클래스입니다.

```python
class APIRateLimitError(DataProviderError):
    def __init__(self, message: str, retry_after: float = None)
```

**매개변수:**
- `message` (str): 에러 메시지
- `retry_after` (float): 재시도 대기 시간 (초, 선택사항)

### 에러 핸들러

#### ErrorHandler

에러를 처리하고 통계를 수집하는 클래스입니다.

```python
class ErrorHandler:
    def __init__(self)
```

#### 주요 메서드

##### handle_error

에러를 처리합니다.

```python
def handle_error(self, error: Exception, context: ErrorContext) -> Optional[Any]
```

**매개변수:**
- `error` (Exception): 처리할 예외
- `context` (ErrorContext): 에러 컨텍스트

**반환값:**
- `Optional[Any]`: 처리 결과 (선택사항)

##### get_error_stats

에러 통계를 조회합니다.

```python
def get_error_stats(self) -> Dict[str, Any]
```

**반환값:**
- `Dict[str, Any]`: 에러 통계

**예시:**
```python
error_handler = ErrorHandler()
context = ErrorContext(
    category=ErrorCategory.API,
    severity=ErrorSeverity.MEDIUM,
    operation="api_call"
)

try:
    # API 호출
    pass
except Exception as e:
    error_handler.handle_error(e, context)

# 통계 조회
stats = error_handler.get_error_stats()
print(f"총 에러 수: {stats['total_errors']}")
```

### 에러 처리 데코레이터

#### handle_errors

에러 처리를 위한 데코레이터입니다.

```python
def handle_errors(category: ErrorCategory, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 operation: str = None,
                 retry_strategy: RetryStrategy = None)
```

**매개변수:**
- `category` (ErrorCategory): 에러 카테고리
- `severity` (ErrorSeverity): 에러 심각도 (기본값: MEDIUM)
- `operation` (str): 작업명 (선택사항)
- `retry_strategy` (RetryStrategy): 재시도 전략 (선택사항)

**예시:**
```python
@handle_errors(ErrorCategory.API, ErrorSeverity.MEDIUM, "api_call")
def call_api(symbol: str):
    # API 호출 로직
    pass
```

#### retry_on_failure

재시도를 위한 데코레이터입니다.

```python
def retry_on_failure(max_retries: int = 3, 
                    base_delay: float = 1.0,
                    max_delay: float = 60.0)
```

**매개변수:**
- `max_retries` (int): 최대 재시도 횟수 (기본값: 3)
- `base_delay` (float): 기본 지연 시간 (초, 기본값: 1.0)
- `max_delay` (float): 최대 지연 시간 (초, 기본값: 60.0)

**예시:**
```python
@retry_on_failure(max_retries=3, base_delay=1.0)
def unreliable_function():
    # 불안정한 함수
    pass
```

---

## 캐싱 시스템

### MemoryCache

메모리 캐시 클래스입니다.

```python
class MemoryCache:
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0)
```

**매개변수:**
- `max_size` (int): 최대 캐시 크기 (기본값: 1000)
- `default_ttl` (float): 기본 TTL (초, 기본값: 3600.0)

#### 주요 메서드

##### get

캐시에서 값을 조회합니다.

```python
def get(self, key: str) -> Optional[Any]
```

**매개변수:**
- `key` (str): 캐시 키

**반환값:**
- `Optional[Any]`: 캐시된 값 또는 None

##### set

캐시에 값을 저장합니다.

```python
def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None
```

**매개변수:**
- `key` (str): 캐시 키
- `value` (Any): 저장할 값
- `ttl` (Optional[float]): TTL (초, 선택사항)

**예시:**
```python
cache = MemoryCache(max_size=1000, default_ttl=3600)

# 값 저장
cache.set("key1", "value1")
cache.set("key2", {"data": "value2"}, ttl=1800)  # 30분 TTL

# 값 조회
value1 = cache.get("key1")  # "value1"
value2 = cache.get("key2")  # {"data": "value2"}
value3 = cache.get("key3")  # None
```

### HybridCache

하이브리드 캐시 (메모리 + 디스크) 클래스입니다.

```python
class HybridCache:
    def __init__(self, 
                 memory_max_size: int = 1000,
                 memory_ttl: float = 3600.0,
                 disk_cache_dir: str = "cache",
                 disk_ttl: float = 86400.0,
                 compress: bool = True)
```

**매개변수:**
- `memory_max_size` (int): 메모리 캐시 최대 크기 (기본값: 1000)
- `memory_ttl` (float): 메모리 캐시 TTL (초, 기본값: 3600.0)
- `disk_cache_dir` (str): 디스크 캐시 디렉토리 (기본값: "cache")
- `disk_ttl` (float): 디스크 캐시 TTL (초, 기본값: 86400.0)
- `compress` (bool): 압축 사용 여부 (기본값: True)

**예시:**
```python
cache = HybridCache(
    memory_max_size=1000,
    memory_ttl=3600,  # 1시간
    disk_cache_dir="cache",
    disk_ttl=86400,   # 24시간
    compress=True
)

# 값 저장 (메모리 + 디스크)
cache.set("key1", "value1")

# 값 조회 (메모리 → 디스크 순)
value = cache.get("key1")
```

### 캐시 데코레이터

#### cached

캐싱을 위한 데코레이터입니다.

```python
def cached(cache: HybridCache, ttl: float = 3600.0, key_prefix: str = "")
```

**매개변수:**
- `cache` (HybridCache): 사용할 캐시 인스턴스
- `ttl` (float): TTL (초, 기본값: 3600.0)
- `key_prefix` (str): 키 접두사 (기본값: "")

**예시:**
```python
cache = HybridCache()

@cached(cache, ttl=1800, key_prefix="api")
def expensive_api_call(symbol: str):
    # 비용이 큰 API 호출
    return {"symbol": symbol, "data": "result"}

# 첫 번째 호출: API 호출
result1 = expensive_api_call("005930")

# 두 번째 호출: 캐시에서 조회
result2 = expensive_api_call("005930")
```

---

## 로깅 시스템

### LogManager

로그 매니저 클래스입니다.

```python
class LogManager:
    def __init__(self, config: Dict[str, Any] = None)
```

**매개변수:**
- `config` (Dict[str, Any]): 로깅 설정 (선택사항)

#### 주요 메서드

##### get_logger

로거를 반환합니다.

```python
def get_logger(self, name: str, category: LogCategory = LogCategory.SYSTEM) -> logging.Logger
```

**매개변수:**
- `name` (str): 로거 이름
- `category` (LogCategory): 로그 카테고리 (기본값: SYSTEM)

**반환값:**
- `logging.Logger`: 로거 인스턴스

**예시:**
```python
log_manager = LogManager()
logger = log_manager.get_logger(__name__, LogCategory.ANALYSIS)

logger.info("분석 시작")
logger.warning("경고 메시지")
logger.error("에러 메시지")
```

##### get_stats

로그 통계를 조회합니다.

```python
def get_stats(self) -> Dict[str, Any]
```

**반환값:**
- `Dict[str, Any]`: 로그 통계

### 로깅 데코레이터

#### log_function

함수 로깅을 위한 데코레이터입니다.

```python
def log_function(category: LogCategory = LogCategory.SYSTEM, 
                level: LogLevel = LogLevel.INFO,
                include_args: bool = False,
                include_result: bool = False)
```

**매개변수:**
- `category` (LogCategory): 로그 카테고리 (기본값: SYSTEM)
- `level` (LogLevel): 로그 레벨 (기본값: INFO)
- `include_args` (bool): 인수 포함 여부 (기본값: False)
- `include_result` (bool): 결과 포함 여부 (기본값: False)

**예시:**
```python
@log_function(LogCategory.ANALYSIS, LogLevel.INFO, include_args=True)
def analyze_stock(symbol: str, days: int = 30):
    # 분석 로직
    return {"symbol": symbol, "score": 85.5}

result = analyze_stock("005930", 30)
```

---

## 설정 관리

### ConfigManager

설정 관리자 클래스입니다.

```python
class ConfigManager:
    def __init__(self, config_dir: str = "config")
```

**매개변수:**
- `config_dir` (str): 설정 디렉토리 (기본값: "config")

#### 주요 메서드

##### load

설정을 로드합니다.

```python
def load(self, 
         config_name: str = "config",
         environment: Environment = Environment.DEVELOPMENT,
         validate: bool = True) -> Dict[str, Any]
```

**매개변수:**
- `config_name` (str): 설정 파일명 (기본값: "config")
- `environment` (Environment): 환경 (기본값: DEVELOPMENT)
- `validate` (bool): 검증 여부 (기본값: True)

**반환값:**
- `Dict[str, Any]`: 설정 딕셔너리

##### get

설정 값을 조회합니다.

```python
def get(self, key: str, default: Any = None) -> Any
```

**매개변수:**
- `key` (str): 설정 키 (점 표기법 지원)
- `default` (Any): 기본값 (선택사항)

**반환값:**
- `Any`: 설정 값

##### set

설정 값을 설정합니다.

```python
def set(self, key: str, value: Any) -> None
```

**매개변수:**
- `key` (str): 설정 키 (점 표기법 지원)
- `value` (Any): 설정할 값

**예시:**
```python
config_manager = ConfigManager()

# 설정 로드
config = config_manager.load(environment=Environment.PRODUCTION)

# 설정 값 조회
api_key = config_manager.get('api.kis_api_key')
timeout = config_manager.get('api.timeout', 30)

# 설정 값 설정
config_manager.set('analysis.max_workers', 4)
config_manager.set('cache.memory_ttl', 1800)
```

---

## 사용 예시

### 기본 사용법

```python
from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer
from common_utilities import DataConverter, DataValidator
from error_handling import handle_errors, ErrorCategory, ErrorSeverity
from caching_system import HybridCache, cached
from logging_system import get_logger, LogCategory

# 분석기 생성
analyzer = EnhancedIntegratedAnalyzer("config.yaml")

# 캐시 설정
cache = HybridCache()

# 로거 설정
logger = get_logger(__name__, LogCategory.ANALYSIS)

# 캐시된 분석 함수
@cached(cache, ttl=3600)
@handle_errors(ErrorCategory.ANALYSIS, ErrorSeverity.MEDIUM)
def analyze_stock_cached(symbol: str, name: str):
    logger.info(f"분석 시작: {name} ({symbol})")
    result = analyzer.analyze_single_stock(symbol, name)
    logger.info(f"분석 완료: {name} - {result.enhanced_score:.1f}점")
    return result

# 종목 분석
result = analyze_stock_cached("005930", "삼성전자")

# 결과 출력
print(f"종목: {result.name}")
print(f"점수: {result.enhanced_score:.1f}점")
print(f"등급: {result.enhanced_grade}")

# 점수 구성
for category, score in result.score_breakdown.items():
    print(f"{category}: {score:.1f}점")
```

### 배치 분석

```python
import concurrent.futures
from typing import List

def batch_analyze(symbols: List[str], names: List[str], max_workers: int = 2):
    """배치 분석 수행"""
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Future 생성
        futures = []
        for symbol, name in zip(symbols, names):
            future = executor.submit(analyze_stock_cached, symbol, name)
            futures.append(future)
        
        # 결과 수집
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"분석 실패: {e}")
    
    # 점수순 정렬
    results.sort(key=lambda x: x.enhanced_score, reverse=True)
    return results

# 배치 분석 실행
symbols = ["005930", "000660", "035420", "051910", "006400"]
names = ["삼성전자", "SK하이닉스", "NAVER", "LG화학", "현대차"]

results = batch_analyze(symbols, names)

# 결과 출력
for i, result in enumerate(results, 1):
    print(f"{i}. {result.name} ({result.symbol}): {result.enhanced_score:.1f}점")
```

### 에러 처리 및 재시도

```python
from error_handling import retry_on_failure, APIRateLimitError

@retry_on_failure(max_retries=3, base_delay=1.0)
@handle_errors(ErrorCategory.API, ErrorSeverity.MEDIUM)
def robust_api_call(symbol: str):
    """견고한 API 호출"""
    try:
        # API 호출 로직
        return {"symbol": symbol, "data": "success"}
    except APIRateLimitError as e:
        logger.warning(f"API 제한: {e.retry_after}초 후 재시도")
        raise
    except Exception as e:
        logger.error(f"API 호출 실패: {e}")
        raise

# 견고한 API 호출
try:
    result = robust_api_call("005930")
    print(f"API 호출 성공: {result}")
except Exception as e:
    print(f"API 호출 최종 실패: {e}")
```

### 성능 모니터링

```python
from common_utilities import PerformanceProfiler, measure_time

# 성능 측정
profiler = PerformanceProfiler()

@measure_time("stock_analysis")
def monitored_analysis(symbol: str, name: str):
    """성능 모니터링이 포함된 분석"""
    profiler.start_timer("api_call")
    # API 호출
    profiler.end_timer("api_call")
    
    profiler.start_timer("calculation")
    # 계산 로직
    profiler.end_timer("calculation")
    
    return {"symbol": symbol, "name": name, "score": 85.5}

# 분석 실행
result = monitored_analysis("005930", "삼성전자")

# 성능 통계 출력
measurements = profiler.get_all_measurements()
for name, measurement in measurements.items():
    print(f"{name}: {measurement['duration']:.3f}초")
```

이 문서는 향상된 통합 분석 시스템의 모든 주요 기능과 사용법을 다룹니다. 더 자세한 정보가 필요하거나 특정 기능에 대한 질문이 있으시면 개발팀에 문의해 주세요.
