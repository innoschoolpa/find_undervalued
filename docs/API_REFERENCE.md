# API 참조 문서

이 문서는 리팩토링된 모듈들의 API를 설명합니다.

## 목차

1. [ValueStyleClassifier](#valuestyleclassifier)
2. [UVSEligibilityFilter](#uvseligibilityfilter)
3. [ConfigManager](#configmanager)
4. [MetricsCollector](#metricscollector)
5. [FinancialDataProvider](#financialdataprovider)
6. [EnhancedScoreCalculator](#enhancedscorecalculator)
7. [AnalysisModels](#analysismodels)

---

## ValueStyleClassifier

가치주 스타일 분류기 - 저평가 vs 가치주를 구분합니다.

### 클래스 정의

```python
class ValueStyleClassifier:
    def __init__(self, metrics_collector: MetricsCollector = None)
```

### 메서드

#### `classify_value_style(metrics: Dict[str, Any]) -> Dict[str, Any]`

가치주 스타일을 분류합니다.

**매개변수:**
- `metrics` (Dict[str, Any]): 분석 메트릭 딕셔너리
  - `valuation_pct` (float): 섹터 상대 가치 퍼센타일 (0~100)
  - `mos` (float): 안전마진 (0.30 = 30%)
  - `price_pos` (float): 52주 가격위치 (0~1)
  - `roic_z` (float): ROIC z-score
  - `f_score` (int): F-Score (0~9)
  - `accruals_risk` (float): Accruals 리스크
  - `earnings_vol_sigma` (float): 수익 변동성
  - `sector_sigma_median` (float): 섹터 중위수 변동성
  - `eps_cagr` (float): EPS 성장률
  - `rev_cagr` (float): 매출 성장률
  - `ev_ebit` (float): EV/EBIT 배수

**반환값:**
- `Dict[str, Any]`: 분류 결과
  - `style_label` (str): 스타일 라벨 ('Value Stock', 'Growth Value', 'Potential Value', 'Not Value')
  - `style_reasons` (List[str]): 분류 이유 목록
  - `confidence_score` (float): 신뢰도 점수 (0~1)

**예시:**
```python
classifier = ValueStyleClassifier()
metrics = {
    'valuation_pct': 20,
    'mos': 0.25,
    'price_pos': 0.3,
    'ev_ebit': 8,
    'interest_cov': 6.0,
    'accruals_risk': 0.1,
    'earnings_vol_sigma': 0.18,
    'sector_sigma_median': 0.25,
    'roic_z': 1.2,
    'f_score': 7,
    'eps_cagr': 0.15,
    'rev_cagr': 0.10
}
result = classifier.classify_value_style(metrics)
print(result['style_label'])  # 'Value Stock'
```

#### `get_style_explanation(style_label: str, confidence_score: float) -> str`

스타일 라벨의 설명을 반환합니다.

**매개변수:**
- `style_label` (str): 스타일 라벨
- `confidence_score` (float): 신뢰도 점수

**반환값:**
- `str`: 스타일 설명

#### `calculate_style_score(metrics: Dict[str, Any]) -> float`

스타일 점수를 계산합니다 (0~100).

**매개변수:**
- `metrics` (Dict[str, Any]): 분석 메트릭 딕셔너리

**반환값:**
- `float`: 스타일 점수 (0~100)

---

## UVSEligibilityFilter

UVS 자격 필터 - 가치 스타일, 저평가, 품질/리스크 통과를 확인합니다.

### 클래스 정의

```python
class UVSEligibilityFilter:
    def __init__(self, metrics_collector: MetricsCollector = None)
```

### 메서드

#### `check_uvs_eligibility(metrics: Dict[str, Any]) -> Dict[str, Any]`

UVS 자격을 검증합니다.

**매개변수:**
- `metrics` (Dict[str, Any]): 분석 메트릭 딕셔너리
  - `value_style_score` (float): 가치 스타일 점수
  - `valuation_percentile` (float): 가치 퍼센타일
  - `margin_of_safety` (float): 안전마진
  - `quality_score` (float): 품질 점수
  - `risk_score` (float): 리스크 점수
  - `confidence_score` (float): 신뢰도 점수

**반환값:**
- `Dict[str, Any]`: 자격 검증 결과
  - `is_eligible` (bool): 자격 여부
  - `eligibility_reasons` (List[str]): 자격 이유 목록
  - `uvs_score` (float): UVS 점수 (0~100)
  - `failed_criteria` (List[str]): 실패한 기준 목록

**예시:**
```python
filter = UVSEligibilityFilter()
metrics = {
    'value_style_score': 85.0,
    'valuation_percentile': 25.0,
    'margin_of_safety': 0.20,
    'quality_score': 75.0,
    'risk_score': 0.25,
    'confidence_score': 0.8
}
result = filter.check_uvs_eligibility(metrics)
print(result['is_eligible'])  # True
```

#### `filter_uvs_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

UVS 후보를 필터링합니다.

**매개변수:**
- `candidates` (List[Dict[str, Any]]): 후보 목록

**반환값:**
- `List[Dict[str, Any]]`: 자격 있는 후보 목록 (UVS 점수 순 정렬)

#### `get_uvs_grade(uvs_score: float) -> str`

UVS 점수를 등급으로 변환합니다.

**매개변수:**
- `uvs_score` (float): UVS 점수

**반환값:**
- `str`: 등급 ('A+', 'A', 'B+', 'B', 'C+', 'C', 'D', 'F')

---

## ConfigManager

설정 관리자 - 환경변수, 기본값, 검증을 관리합니다.

### 클래스 정의

```python
class ConfigManager:
    def __init__(self)
```

### 메서드

#### `get(key: str, default: Any = None) -> Any`

설정값을 조회합니다.

**매개변수:**
- `key` (str): 설정 키
- `default` (Any): 기본값

**반환값:**
- `Any`: 설정값

#### `set(key: str, value: Any) -> bool`

설정값을 설정합니다.

**매개변수:**
- `key` (str): 설정 키
- `value` (Any): 설정값

**반환값:**
- `bool`: 설정 성공 여부

#### `get_all() -> Dict[str, Any]`

모든 설정값을 조회합니다.

**반환값:**
- `Dict[str, Any]`: 모든 설정값

#### `validate_all() -> Dict[str, bool]`

모든 설정값을 검증합니다.

**반환값:**
- `Dict[str, bool]`: 검증 결과

#### `export_config(file_path: str) -> bool`

설정을 파일로 내보냅니다.

**매개변수:**
- `file_path` (str): 파일 경로

**반환값:**
- `bool`: 내보내기 성공 여부

#### `import_config(file_path: str) -> bool`

파일에서 설정을 가져옵니다.

**매개변수:**
- `file_path` (str): 파일 경로

**반환값:**
- `bool`: 가져오기 성공 여부

**예시:**
```python
config = ConfigManager()
config.set('api_timeout', 60)
config.set('max_tps', 20)

# 설정 내보내기
config.export_config('config.json')

# 설정 가져오기
new_config = ConfigManager()
new_config.import_config('config.json')
```

---

## MetricsCollector

메트릭 수집기 - 성능 및 운영 메트릭을 수집합니다.

### 클래스 정의

```python
class MetricsCollector:
    def __init__(self)
```

### 메서드

#### `record_api_calls(count: int)`

API 호출 수를 기록합니다.

**매개변수:**
- `count` (int): API 호출 수

#### `record_api_errors(count: int)`

API 에러 수를 기록합니다.

**매개변수:**
- `count` (int): API 에러 수

#### `record_data_processing_time(time_seconds: float)`

데이터 처리 시간을 기록합니다.

**매개변수:**
- `time_seconds` (float): 처리 시간 (초)

#### `get_stats() -> Dict[str, Any]`

통계 정보를 조회합니다.

**반환값:**
- `Dict[str, Any]`: 통계 정보
  - `api_calls`: API 호출 통계
  - `data_processing_time`: 데이터 처리 시간 통계
  - `cache_stats`: 캐시 통계

#### `save_metrics(file_path: str) -> bool`

메트릭을 파일로 저장합니다.

**매개변수:**
- `file_path` (str): 파일 경로

**반환값:**
- `bool`: 저장 성공 여부

#### `load_metrics(file_path: str) -> bool`

파일에서 메트릭을 로드합니다.

**매개변수:**
- `file_path` (str): 파일 경로

**반환값:**
- `bool`: 로드 성공 여부

**예시:**
```python
metrics = MetricsCollector()
metrics.record_api_calls(100)
metrics.record_api_errors(5)
metrics.record_data_processing_time(2.5)

stats = metrics.get_stats()
print(stats['api_calls']['total'])  # 100
```

---

## FinancialDataProvider

재무 데이터 제공자 - API 호출, 캐싱, 검증을 담당합니다.

### 클래스 정의

```python
class FinancialDataProvider(DataProvider):
    def __init__(self, metrics_collector: MetricsCollector = None, cache=None)
```

### 메서드

#### `get_financial_data(symbol: str, **kwargs) -> Dict[str, Any]`

재무 데이터를 조회합니다.

**매개변수:**
- `symbol` (str): 종목 코드
- `**kwargs`: 추가 파라미터

**반환값:**
- `Dict[str, Any]`: 재무 데이터

#### `get_price_data(symbol: str, **kwargs) -> Dict[str, Any]`

가격 데이터를 조회합니다.

**매개변수:**
- `symbol` (str): 종목 코드
- `**kwargs`: 추가 파라미터

**반환값:**
- `Dict[str, Any]`: 가격 데이터

#### `get_data_quality_score(data: Dict[str, Any]) -> float`

데이터 품질 점수를 계산합니다 (0~100).

**매개변수:**
- `data` (Dict[str, Any]): 데이터

**반환값:**
- `float`: 품질 점수 (0~100)

#### `is_data_fresh(data: Dict[str, Any], max_age_hours: int = 24) -> bool`

데이터 신선도를 확인합니다.

**매개변수:**
- `data` (Dict[str, Any]): 데이터
- `max_age_hours` (int): 최대 허용 시간 (시간)

**반환값:**
- `bool`: 신선도 여부

**예시:**
```python
provider = FinancialDataProvider()
data = provider.get_financial_data('AAPL')
quality_score = provider.get_data_quality_score(data)
print(quality_score)  # 85.0
```

---

## EnhancedScoreCalculator

향상된 점수 계산기 - 종합 점수를 계산합니다.

### 클래스 정의

```python
class EnhancedScoreCalculator(ScoreCalculator):
    def __init__(self, config: AnalysisConfig)
```

### 메서드

#### `calculate_score(data: Dict[str, Any]) -> float`

종합 점수를 계산합니다.

**매개변수:**
- `data` (Dict[str, Any]): 분석 데이터

**반환값:**
- `float`: 종합 점수 (0~100)

#### `get_score_breakdown(data: Dict[str, Any]) -> Dict[str, Any]`

점수 세부 내역을 반환합니다.

**매개변수:**
- `data` (Dict[str, Any]): 분석 데이터

**반환값:**
- `Dict[str, Any]`: 점수 세부 내역
  - `value_score`: 가치 점수
  - `quality_score`: 품질 점수
  - `growth_score`: 성장 점수
  - `safety_score`: 안전 점수
  - `momentum_score`: 모멘텀 점수
  - `total_score`: 총점
  - `grade`: 등급

#### `get_score_recommendation(total_score: float) -> str`

점수 기반 투자 권고사항을 반환합니다.

**매개변수:**
- `total_score` (float): 총점

**반환값:**
- `str`: 투자 권고사항

**예시:**
```python
calculator = EnhancedScoreCalculator(config)
data = {
    'pe_ratio': 15.0,
    'pb_ratio': 1.5,
    'roe': 15.0,
    'roa': 8.0,
    'debt_ratio': 30.0
}
score = calculator.calculate_score(data)
breakdown = calculator.get_score_breakdown(data)
print(breakdown['total_score'])  # 75.0
```

---

## AnalysisModels

분석 모델 - 데이터 클래스들을 정의합니다.

### AnalysisStatus

분석 상태 열거형

```python
class AnalysisStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### AnalysisResult

분석 결과 데이터 클래스

```python
@dataclass
class AnalysisResult:
    symbol: str
    analysis_id: str
    status: AnalysisStatus
    timestamp: str
    financial_data: Dict[str, Any]
    price_data: Dict[str, Any]
    sector_data: Dict[str, Any]
    metrics: Dict[str, Any]
    scores: Dict[str, float]
    recommendation: str
    confidence_score: float
    risk_level: str
    analysis_duration: float
    data_quality_score: float
    error_messages: List[str]
```

**메서드:**
- `is_successful() -> bool`: 분석 성공 여부
- `has_errors() -> bool`: 에러 존재 여부
- `get_summary() -> Dict[str, Any]`: 분석 결과 요약
- `to_dict() -> Dict[str, Any]`: 딕셔너리로 변환

### AnalysisConfig

분석 설정 데이터 클래스

```python
@dataclass
class AnalysisConfig:
    analysis_type: str = "comprehensive"
    timeout_seconds: int = 300
    max_retries: int = 3
    min_data_quality_score: float = 70.0
    data_freshness_hours: int = 24
    include_sector_analysis: bool = True
    include_risk_analysis: bool = True
    include_growth_analysis: bool = True
    include_valuation_analysis: bool = True
    value_weight: float = 0.35
    quality_weight: float = 0.25
    growth_weight: float = 0.15
    safety_weight: float = 0.15
    momentum_weight: float = 0.10
```

**메서드:**
- `get_analysis_options() -> Dict[str, bool]`: 분석 옵션 반환
- `get_score_weights() -> Dict[str, float]`: 점수 가중치 반환
- `get_filtering_criteria() -> Dict[str, float]`: 필터링 기준 반환
- `to_dict() -> Dict[str, Any]`: 딕셔너리로 변환
- `from_dict(data: Dict[str, Any]) -> AnalysisConfig`: 딕셔너리에서 생성
- `get_default_config() -> AnalysisConfig`: 기본 설정 반환
- `get_conservative_config() -> AnalysisConfig`: 보수적 설정 반환
- `get_aggressive_config() -> AnalysisConfig`: 공격적 설정 반환

**예시:**
```python
config = AnalysisConfig.get_default_config()
result = AnalysisResult(
    symbol='AAPL',
    analysis_id='analysis_001',
    status=AnalysisStatus.COMPLETED,
    timestamp='2024-01-01T00:00:00Z',
    financial_data={},
    price_data={},
    sector_data={},
    metrics={},
    scores={},
    recommendation='BUY',
    confidence_score=0.8,
    risk_level='LOW',
    analysis_duration=5.0,
    data_quality_score=85.0,
    error_messages=[]
)
print(result.is_successful())  # True
```

---

## 사용 예시

### 기본 사용법

```python
from config_manager import ConfigManager
from metrics import MetricsCollector
from value_style_classifier import ValueStyleClassifier
from uvs_eligibility_filter import UVSEligibilityFilter
from financial_data_provider import FinancialDataProvider
from enhanced_score_calculator import EnhancedScoreCalculator
from analysis_models import AnalysisConfig, AnalysisResult, AnalysisStatus

# 설정 관리자 초기화
config = ConfigManager()
config.set('api_timeout', 60)
config.set('max_tps', 20)

# 메트릭 수집기 초기화
metrics = MetricsCollector()

# 분석 구성 설정
analysis_config = AnalysisConfig.get_default_config()

# 데이터 제공자 초기화
data_provider = FinancialDataProvider(metrics_collector=metrics)

# 점수 계산기 초기화
score_calculator = EnhancedScoreCalculator(analysis_config)

# 가치주 스타일 분류기 초기화
style_classifier = ValueStyleClassifier(metrics_collector=metrics)

# UVS 자격 필터 초기화
uvs_filter = UVSEligibilityFilter(metrics_collector=metrics)

# 분석 실행
symbol = 'AAPL'
financial_data = data_provider.get_financial_data(symbol)
price_data = data_provider.get_price_data(symbol)

# 점수 계산
score = score_calculator.calculate_score({
    'financial_data': financial_data,
    'price_data': price_data
})

# 스타일 분류
style_result = style_classifier.classify_value_style({
    'valuation_pct': 20,
    'mos': 0.25,
    'price_pos': 0.3
})

# UVS 자격 검증
uvs_result = uvs_filter.check_uvs_eligibility({
    'value_style_score': style_result['confidence_score'] * 100,
    'valuation_percentile': 20,
    'margin_of_safety': 0.25,
    'quality_score': 75.0,
    'risk_score': 0.25,
    'confidence_score': style_result['confidence_score']
})

# 결과 출력
print(f"종목: {symbol}")
print(f"점수: {score:.1f}")
print(f"스타일: {style_result['style_label']}")
print(f"UVS 자격: {uvs_result['is_eligible']}")
print(f"UVS 점수: {uvs_result['uvs_score']:.1f}")
```

### 고급 사용법

```python
# 보수적 설정으로 분석
conservative_config = AnalysisConfig.get_conservative_config()
conservative_calculator = EnhancedScoreCalculator(conservative_config)

# 여러 종목 일괄 분석
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
results = []

for symbol in symbols:
    try:
        # 데이터 수집
        financial_data = data_provider.get_financial_data(symbol)
        price_data = data_provider.get_price_data(symbol)
        
        # 품질 검증
        quality_score = data_provider.get_data_quality_score(financial_data)
        if quality_score < analysis_config.min_data_quality_score:
            continue
        
        # 점수 계산
        score = conservative_calculator.calculate_score({
            'financial_data': financial_data,
            'price_data': price_data
        })
        
        # 스타일 분류
        style_result = style_classifier.classify_value_style({
            'valuation_pct': 20,
            'mos': 0.25,
            'price_pos': 0.3
        })
        
        # UVS 자격 검증
        uvs_result = uvs_filter.check_uvs_eligibility({
            'value_style_score': style_result['confidence_score'] * 100,
            'valuation_percentile': 20,
            'margin_of_safety': 0.25,
            'quality_score': quality_score,
            'risk_score': 0.25,
            'confidence_score': style_result['confidence_score']
        })
        
        # 결과 저장
        if uvs_result['is_eligible']:
            results.append({
                'symbol': symbol,
                'score': score,
                'style': style_result['style_label'],
                'uvs_score': uvs_result['uvs_score'],
                'uvs_grade': uvs_filter.get_uvs_grade(uvs_result['uvs_score'])
            })
    
    except Exception as e:
        print(f"분석 실패: {symbol} - {e}")
        continue

# 결과 정렬 및 출력
results.sort(key=lambda x: x['uvs_score'], reverse=True)
for result in results:
    print(f"{result['symbol']}: {result['uvs_grade']} ({result['uvs_score']:.1f}) - {result['style']}")
```

이 문서는 각 모듈의 API를 상세히 설명하며, 실제 사용 예시를 포함하고 있습니다. 추가적인 질문이나 요청사항이 있으시면 언제든지 문의해 주세요.