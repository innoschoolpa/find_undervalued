# 사용자 가이드

## 개요

향상된 통합 분석 시스템의 사용자 가이드입니다. 이 문서는 시스템 설치부터 고급 사용법까지 단계별로 안내합니다.

## 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [설치 및 설정](#설치-및-설정)
3. [기본 사용법](#기본-사용법)
4. [고급 사용법](#고급-사용법)
5. [문제 해결](#문제-해결)
6. [FAQ](#faq)

---

## 시스템 요구사항

### 하드웨어 요구사항

- **CPU**: Intel i5 이상 또는 동등한 성능의 AMD 프로세서
- **메모리**: 최소 8GB RAM (16GB 권장)
- **저장공간**: 최소 2GB 여유 공간
- **네트워크**: 안정적인 인터넷 연결 (API 호출용)

### 소프트웨어 요구사항

- **Python**: 3.8 이상
- **운영체제**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **브라우저**: Chrome, Firefox, Safari, Edge (최신 버전)

### 필수 라이브러리

```txt
pandas>=1.3.0
numpy>=1.21.0
requests>=2.25.0
pyyaml>=5.4.0
rich>=10.0.0
typer>=0.4.0
openpyxl>=3.0.0
```

---

## 설치 및 설정

### 1. 저장소 클론

```bash
git clone https://github.com/your-repo/enhanced-integrated-analyzer.git
cd enhanced-integrated-analyzer
```

### 2. 가상환경 생성 및 활성화

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 설정 파일 생성

```bash
# 설정 파일 복사
cp config.yaml.example config.yaml

# 설정 파일 편집
nano config.yaml  # 또는 원하는 에디터 사용
```

### 5. API 키 설정

`config.yaml` 파일에서 다음 항목들을 설정합니다:

```yaml
api:
  kis_api_key: "your_kis_api_key"
  kis_secret_key: "your_kis_secret_key"
  dart_api_key: "your_dart_api_key"
```

### 6. KOSPI 마스터 데이터 다운로드

```bash
python kospi_master_download.py
```

---

## 기본 사용법

### 1. 단일 종목 분석

가장 기본적인 사용법입니다.

```python
from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer

# 분석기 생성
analyzer = EnhancedIntegratedAnalyzer()

# 종목 분석
result = analyzer.analyze_single_stock("005930", "삼성전자")

# 결과 출력
print(f"종목: {result.name}")
print(f"점수: {result.enhanced_score:.1f}점")
print(f"등급: {result.enhanced_grade}")
```

### 2. CLI를 통한 분석

터미널에서 직접 분석을 실행할 수 있습니다.

```bash
# 기본 분석
python enhanced_integrated_analyzer_refactored.py test_enhanced_analysis

# 옵션 지정
python enhanced_integrated_analyzer_refactored.py test_enhanced_analysis \
    --count 20 \
    --min-score 60 \
    --max-workers 2
```

### 3. 시가총액 상위 종목 분석

```python
# 상위 50개 종목 조회
stocks = analyzer.get_top_market_cap_stocks(count=50, min_market_cap=1000)

# 각 종목 분석
results = []
for stock in stocks:
    result = analyzer.analyze_single_stock(stock['symbol'], stock['name'])
    results.append(result)

# 점수순 정렬
results.sort(key=lambda x: x.enhanced_score, reverse=True)

# 상위 10개 출력
for i, result in enumerate(results[:10], 1):
    print(f"{i}. {result.name}: {result.enhanced_score:.1f}점")
```

---

## 고급 사용법

### 1. 병렬 처리

대량의 종목을 효율적으로 분석하기 위해 병렬 처리를 사용합니다.

```python
import concurrent.futures
from typing import List

def parallel_analysis(symbols: List[str], names: List[str], max_workers: int = 2):
    """병렬 분석 수행"""
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Future 생성
        futures = []
        for symbol, name in zip(symbols, names):
            future = executor.submit(analyzer.analyze_single_stock, symbol, name)
            futures.append((future, symbol, name))
        
        # 결과 수집
        for future, symbol, name in futures:
            try:
                result = future.result()
                results.append(result)
                print(f"완료: {name} ({symbol}) - {result.enhanced_score:.1f}점")
            except Exception as e:
                print(f"실패: {name} ({symbol}) - {e}")
    
    return results

# 사용 예시
symbols = ["005930", "000660", "035420", "051910", "006400"]
names = ["삼성전자", "SK하이닉스", "NAVER", "LG화학", "현대차"]

results = parallel_analysis(symbols, names, max_workers=2)
```

### 2. 캐싱 활용

반복적인 분석을 위해 캐싱을 활용합니다.

```python
from caching_system import HybridCache, cached

# 캐시 생성
cache = HybridCache(
    memory_max_size=1000,
    memory_ttl=3600,  # 1시간
    disk_cache_dir="cache",
    disk_ttl=86400    # 24시간
)

# 캐시된 분석 함수
@cached(cache, ttl=1800)  # 30분 캐시
def cached_analysis(symbol: str, name: str):
    return analyzer.analyze_single_stock(symbol, name)

# 첫 번째 호출: 실제 분석 수행
result1 = cached_analysis("005930", "삼성전자")

# 두 번째 호출: 캐시에서 조회
result2 = cached_analysis("005930", "삼성전자")
```

### 3. 에러 처리 및 재시도

안정적인 분석을 위해 에러 처리와 재시도를 구현합니다.

```python
from error_handling import retry_on_failure, handle_errors, ErrorCategory, ErrorSeverity

@retry_on_failure(max_retries=3, base_delay=1.0)
@handle_errors(ErrorCategory.ANALYSIS, ErrorSeverity.MEDIUM)
def robust_analysis(symbol: str, name: str):
    """견고한 분석 함수"""
    try:
        return analyzer.analyze_single_stock(symbol, name)
    except Exception as e:
        print(f"분석 실패: {name} ({symbol}) - {e}")
        raise

# 견고한 분석 실행
try:
    result = robust_analysis("005930", "삼성전자")
    print(f"분석 성공: {result.enhanced_score:.1f}점")
except Exception as e:
    print(f"분석 최종 실패: {e}")
```

### 4. 성능 모니터링

분석 성능을 모니터링합니다.

```python
from common_utilities import PerformanceProfiler, measure_time

# 성능 측정기 생성
profiler = PerformanceProfiler()

@measure_time("stock_analysis")
def monitored_analysis(symbol: str, name: str):
    """성능 모니터링이 포함된 분석"""
    profiler.start_timer("api_call")
    # API 호출 시뮬레이션
    import time
    time.sleep(0.1)
    profiler.end_timer("api_call")
    
    profiler.start_timer("calculation")
    # 계산 로직 시뮬레이션
    time.sleep(0.05)
    profiler.end_timer("calculation")
    
    return {"symbol": symbol, "name": name, "score": 85.5}

# 분석 실행
result = monitored_analysis("005930", "삼성전자")

# 성능 통계 출력
measurements = profiler.get_all_measurements()
for name, measurement in measurements.items():
    print(f"{name}: {measurement['duration']:.3f}초")
```

### 5. 로깅 설정

상세한 로깅을 설정합니다.

```python
from logging_system import get_logger, LogCategory, LogLevel

# 로거 생성
logger = get_logger(__name__, LogCategory.ANALYSIS)

# 로깅 레벨 설정
logger.setLevel(LogLevel.DEBUG)

# 분석 함수에 로깅 추가
def logged_analysis(symbol: str, name: str):
    logger.info(f"분석 시작: {name} ({symbol})")
    
    try:
        result = analyzer.analyze_single_stock(symbol, name)
        logger.info(f"분석 완료: {name} - {result.enhanced_score:.1f}점")
        return result
    except Exception as e:
        logger.error(f"분석 실패: {name} ({symbol}) - {e}")
        raise

# 로깅이 포함된 분석 실행
result = logged_analysis("005930", "삼성전자")
```

### 6. 설정 관리

환경별 설정을 관리합니다.

```python
from config_manager import ConfigManager, Environment

# 설정 관리자 생성
config_manager = ConfigManager()

# 개발 환경 설정 로드
dev_config = config_manager.load(environment=Environment.DEVELOPMENT)

# 프로덕션 환경 설정 로드
prod_config = config_manager.load(environment=Environment.PRODUCTION)

# 설정 값 조회
api_key = config_manager.get('api.kis_api_key')
max_workers = config_manager.get('analysis.max_workers', 2)

# 설정 값 변경
config_manager.set('analysis.max_workers', 4)
config_manager.set('cache.memory_ttl', 1800)

# 설정 저장
config_manager.save_config(environment=Environment.DEVELOPMENT)
```

---

## 문제 해결

### 1. 일반적인 문제

#### API 키 오류

**증상**: "API 키가 유효하지 않습니다" 오류

**해결방법**:
1. `config.yaml` 파일에서 API 키 확인
2. API 키가 올바르게 설정되었는지 확인
3. API 키의 권한 및 만료일 확인

```yaml
api:
  kis_api_key: "올바른_API_키"
  kis_secret_key: "올바른_시크릿_키"
  dart_api_key: "올바른_DART_API_키"
```

#### 메모리 부족 오류

**증상**: "MemoryError" 또는 시스템이 느려짐

**해결방법**:
1. 분석할 종목 수 줄이기
2. 병렬 워커 수 줄이기
3. 캐시 크기 줄이기

```python
# 종목 수 줄이기
stocks = analyzer.get_top_market_cap_stocks(count=20)  # 50 → 20

# 워커 수 줄이기
results = parallel_analysis(symbols, names, max_workers=1)  # 2 → 1

# 캐시 크기 줄이기
cache = HybridCache(memory_max_size=500)  # 1000 → 500
```

#### 네트워크 연결 오류

**증상**: "ConnectionError" 또는 "TimeoutError"

**해결방법**:
1. 인터넷 연결 확인
2. 방화벽 설정 확인
3. 재시도 로직 사용

```python
@retry_on_failure(max_retries=5, base_delay=2.0)
def network_robust_analysis(symbol: str, name: str):
    return analyzer.analyze_single_stock(symbol, name)
```

### 2. 성능 문제

#### 분석 속도가 느림

**해결방법**:
1. 병렬 처리 사용
2. 캐싱 활용
3. 불필요한 분석 요소 제거

```python
# 병렬 처리
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(analyze_stock, symbol, name) 
              for symbol, name in zip(symbols, names)]
    results = [future.result() for future in futures]

# 캐싱
@cached(cache, ttl=3600)
def cached_analysis(symbol: str, name: str):
    return analyzer.analyze_single_stock(symbol, name)
```

#### 메모리 사용량이 높음

**해결방법**:
1. 배치 크기 줄이기
2. 불필요한 데이터 제거
3. 가비지 컬렉션 강제 실행

```python
import gc

# 배치 처리
batch_size = 10
for i in range(0, len(symbols), batch_size):
    batch_symbols = symbols[i:i+batch_size]
    batch_names = names[i:i+batch_size]
    
    # 배치 분석
    batch_results = parallel_analysis(batch_symbols, batch_names)
    
    # 결과 처리
    process_results(batch_results)
    
    # 가비지 컬렉션
    gc.collect()
```

### 3. 데이터 문제

#### KOSPI 데이터 로드 실패

**증상**: "KOSPI 데이터를 로드할 수 없습니다" 오류

**해결방법**:
1. `kospi_code.xlsx` 파일 존재 확인
2. 파일 권한 확인
3. 파일 형식 확인

```bash
# 파일 존재 확인
ls -la kospi_code.xlsx

# 파일 권한 확인
chmod 644 kospi_code.xlsx

# 파일 재다운로드
python kospi_master_download.py
```

#### 재무 데이터 없음

**증상**: 재무비율이 모두 0 또는 N/A

**해결방법**:
1. 종목 코드 확인
2. API 키 권한 확인
3. 데이터 제공자 상태 확인

```python
# 종목 코드 검증
from common_utilities import DataValidator
validator = DataValidator()

if not validator.is_valid_symbol(symbol):
    print(f"잘못된 종목 코드: {symbol}")

# API 연결 테스트
try:
    test_data = analyzer.data_provider.get_financial_data("005930")
    print(f"API 연결 성공: {len(test_data)}개 데이터")
except Exception as e:
    print(f"API 연결 실패: {e}")
```

---

## FAQ

### Q1: 분석 결과가 예상과 다릅니다.

**A**: 다음을 확인해보세요:
1. 설정 파일의 가중치 설정
2. 분석 기간 설정
3. 데이터 품질 확인
4. 로그에서 에러 메시지 확인

```python
# 설정 확인
config = analyzer.config
print(f"가중치: {config.weights}")

# 로그 확인
from logging_system import get_log_stats
stats = get_log_stats()
print(f"에러 수: {stats.get('total_errors', 0)}")
```

### Q2: API 호출 제한에 걸렸습니다.

**A**: 다음 방법을 시도해보세요:
1. 재시도 간격 늘리기
2. 병렬 워커 수 줄이기
3. 캐싱 활용하기

```python
# 재시도 간격 늘리기
@retry_on_failure(max_retries=3, base_delay=5.0)  # 1초 → 5초
def api_call_with_delay():
    pass

# 워커 수 줄이기
results = parallel_analysis(symbols, names, max_workers=1)  # 2 → 1
```

### Q3: 시스템이 너무 느립니다.

**A**: 성능 최적화를 위해 다음을 시도해보세요:
1. 병렬 처리 사용
2. 캐싱 활용
3. 불필요한 분석 요소 제거
4. 하드웨어 업그레이드

```python
# 성능 측정
from common_utilities import measure_time

@measure_time("analysis")
def optimized_analysis():
    # 최적화된 분석 로직
    pass

# 결과 확인
measurements = profiler.get_all_measurements()
for name, measurement in measurements.items():
    print(f"{name}: {measurement['duration']:.3f}초")
```

### Q4: 에러가 자주 발생합니다.

**A**: 에러 처리를 강화해보세요:
1. 재시도 로직 추가
2. 에러 핸들링 개선
3. 로깅 강화

```python
from error_handling import handle_errors, ErrorCategory, ErrorSeverity

@handle_errors(ErrorCategory.ANALYSIS, ErrorSeverity.MEDIUM)
@retry_on_failure(max_retries=3)
def robust_analysis(symbol: str, name: str):
    try:
        return analyzer.analyze_single_stock(symbol, name)
    except Exception as e:
        logger.error(f"분석 실패: {name} ({symbol}) - {e}")
        raise
```

### Q5: 설정을 변경하고 싶습니다.

**A**: 설정 파일을 수정하거나 코드에서 동적으로 변경할 수 있습니다:

```python
# 설정 파일 수정
# config.yaml 파일에서 원하는 값 변경

# 코드에서 동적 변경
config_manager = ConfigManager()
config_manager.set('analysis.max_workers', 4)
config_manager.set('cache.memory_ttl', 1800)
config_manager.save_config()
```

이 가이드를 통해 향상된 통합 분석 시스템을 효과적으로 사용할 수 있습니다. 추가 질문이나 문제가 있으시면 개발팀에 문의해 주세요.
