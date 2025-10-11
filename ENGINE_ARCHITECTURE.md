# 가치주 분석 시스템 아키텍처

## 📐 아키텍처 개요

엔진/뷰 분리 아키텍처를 통해 **테스트 용이성**과 **유지보수성**을 향상시켰습니다.

```
┌─────────────────────────────────────────┐
│         value_stock_finder.py           │  ← 기존 파일 (하위 호환)
│    (Streamlit UI + 전체 로직 통합)        │
└─────────────────────────────────────────┘
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
┌──────────────────┐   ┌──────────────────┐
│ value_stock_     │   │  Streamlit UI    │
│    engine.py     │   │   (렌더링 로직)   │
│ (순수 계산 엔진)  │   │                  │
└──────────────────┘   └──────────────────┘
         │
         ▼
┌──────────────────┐
│  test_engine.py  │
│  (단위 테스트)    │
└──────────────────┘
```

---

## 📦 모듈 구조

### 1. **value_stock_engine.py** (계산 엔진)

**목적**: UI 의존성 없는 순수 계산/분석 로직

**핵심 클래스**:
- `TokenBucket`: API 호출 한도 관리
- `ValueStockEngine`: 가치주 분석 엔진

**주요 메소드**:
```python
# 섹터 분석
- get_sector_specific_criteria()  # 업종별 기준
- _normalize_sector_name()        # 섹터명 정규화
- _augment_sector_data()          # 섹터 메타데이터

# 가치주 평가
- evaluate_value_stock()          # 가치주 종합 평가
- compute_mos_score()             # 안전마진(MoS) 계산
- calculate_intrinsic_value()     # 내재가치 계산
- is_value_stock_unified()        # 가치주 판정

# 데이터 조회
- get_stock_data()                # 종목 데이터 조회
- analyze_single_stock_parallel() # 병렬 분석
- get_stock_universe()            # 종목 유니버스

# 유틸리티
- format_pct_or_na()              # 퍼센트 포맷팅
- _relative_vs_median()           # 중앙값 대비 비율
- _estimate_analysis_time()       # 분석 시간 추정
```

**특징**:
- ✅ Streamlit 의존성 없음
- ✅ 독립적으로 테스트 가능
- ✅ 다른 UI 프레임워크에서도 재사용 가능
- ✅ CLI 도구로도 사용 가능

---

### 2. **value_stock_finder.py** (통합 시스템)

**목적**: 기존 하위 호환성 유지 + Streamlit UI

**역할**:
- 기존 `ValueStockFinder` 클래스 유지
- Streamlit 렌더링 메소드 포함 (`render_*`)
- 전체 워크플로우 관리 (`run()`)

**주요 렌더링 메소드**:
```python
- render_header()              # 헤더 렌더링
- render_sidebar()             # 사이드바 설정
- screen_all_stocks()          # 전체 스크리닝 UI
- render_individual_analysis() # 개별 종목 분석
- render_value_analysis()      # 가치 분석 탭
- render_mcp_tab()            # MCP 탭
```

---

### 3. **test_engine.py** (단위 테스트)

**목적**: 엔진 기능의 정확성 검증

**테스트 클래스**:
```python
- TestTokenBucket          # 토큰버킷 테스트
- TestValueStockEngine     # 엔진 메소드 테스트
- TestEngineIntegration    # 통합 플로우 테스트
```

**실행 방법**:
```bash
# pytest로 전체 테스트 실행
pytest test_engine.py -v

# 특정 테스트만 실행
pytest test_engine.py -v -k "test_sector"

# 직접 실행
python test_engine.py
```

---

## 🔧 사용 예제

### A. 엔진만 사용 (CLI / 스크립트)

```python
from value_stock_engine import ValueStockEngine

# 엔진 초기화
engine = ValueStockEngine()

# 섹터 기준 조회
criteria = engine.get_sector_specific_criteria('금융업')
print(f"금융업 기준: PER≤{criteria['per_max']}, PBR≤{criteria['pbr_max']}")

# 가치주 평가 (모의 데이터)
stock_data = {
    'symbol': '005930',
    'name': '삼성전자',
    'per': 12.0,
    'pbr': 1.3,
    'roe': 14.0,
    'current_price': 70000,
    'sector_name': '기술업',
    # ... 기타 데이터
}

# 평가 실행
result = engine.evaluate_value_stock(stock_data)
print(f"점수: {result['value_score']}, 등급: {result['grade']}")
print(f"추천: {result['recommendation']}")
```

### B. Streamlit 앱 실행 (기존 방식)

```bash
streamlit run value_stock_finder.py
```

---

## 🧪 테스트 전략

### 단위 테스트
```python
# 개별 메소드 테스트
def test_normalize_sector_name(engine):
    assert engine._normalize_sector_name('금융') == '금융업'
    assert engine._normalize_sector_name('IT') == '기술업'
```

### 통합 테스트
```python
# 전체 플로우 테스트
def test_full_evaluation_flow(engine):
    stock_data = {...}  # 모의 데이터
    result = engine.evaluate_value_stock(stock_data)
    assert result is not None
    assert 0 <= result['value_score'] <= 120
```

### 테스트 실행
```bash
# 전체 테스트
pytest test_engine.py -v

# 커버리지 포함
pytest test_engine.py --cov=value_stock_engine --cov-report=html

# 빠른 테스트
pytest test_engine.py -v --tb=short
```

---

## 📈 개발 워크플로우

### 1. 새 기능 추가

```python
# ① value_stock_engine.py에 메소드 추가
class ValueStockEngine:
    def calculate_new_metric(self, stock_data):
        # 계산 로직
        return result
```

```python
# ② test_engine.py에 테스트 추가
def test_calculate_new_metric(engine):
    stock_data = {...}
    result = engine.calculate_new_metric(stock_data)
    assert result is not None
```

```bash
# ③ 테스트 실행
pytest test_engine.py::test_calculate_new_metric -v
```

```python
# ④ UI에서 사용 (value_stock_finder.py)
def render_new_analysis(self):
    result = self.engine.calculate_new_metric(data)
    st.write(f"새 지표: {result}")
```

### 2. 버그 수정

1. **테스트 작성** - 버그를 재현하는 테스트 먼저 작성
2. **수정 구현** - engine.py에서 버그 수정
3. **테스트 확인** - pytest로 수정 검증
4. **UI 확인** - Streamlit 앱에서 실제 동작 확인

---

## 🎯 이점 정리

### ✅ 테스트 용이성
- 엔진은 Streamlit 없이 독립 테스트 가능
- pytest로 자동화된 단위 테스트
- CI/CD 파이프라인 통합 가능

### ✅ 유지보수성
- 계산 로직과 UI 로직 분리
- 각 모듈의 책임이 명확
- 버그 추적이 쉬움

### ✅ 재사용성
- 엔진은 다른 UI에서도 사용 가능
- CLI 도구, REST API 등으로 확장 가능
- 다른 프로젝트에서도 import 가능

### ✅ 하위 호환성
- 기존 `value_stock_finder.py` 유지
- 기존 사용자 코드 영향 없음
- 점진적 마이그레이션 가능

---

## 📝 마이그레이션 가이드

### 기존 코드에서 엔진 사용으로 전환

**Before** (기존):
```python
finder = ValueStockFinder()
result = finder.evaluate_value_stock(stock_data)
```

**After** (엔진 사용):
```python
from value_stock_engine import ValueStockEngine

engine = ValueStockEngine()
result = engine.evaluate_value_stock(stock_data)
```

**하위 호환** (기존 방식도 계속 작동):
```python
# 기존 코드 그대로 사용 가능
finder = ValueStockFinder()
finder.run()  # Streamlit 앱 실행
```

---

## 🚀 향후 확장 계획

### 1. REST API 서버
```python
from fastapi import FastAPI
from value_stock_engine import ValueStockEngine

app = FastAPI()
engine = ValueStockEngine()

@app.post("/analyze")
def analyze_stock(stock_data: dict):
    return engine.evaluate_value_stock(stock_data)
```

### 2. CLI 도구
```bash
python analyze_stock.py --symbol 005930 --export json
```

### 3. 배치 분석 스크립트
```python
from value_stock_engine import ValueStockEngine

engine = ValueStockEngine()
results = []

for symbol in symbols:
    data = engine.get_stock_data(symbol)
    result = engine.evaluate_value_stock(data)
    results.append(result)

export_to_excel(results)
```

---

## 🔍 디버깅 팁

### 엔진 로그 활성화
```bash
export LOG_LEVEL=DEBUG
python test_engine.py
```

### 특정 메소드 디버깅
```python
import logging
logging.basicConfig(level=logging.DEBUG)

from value_stock_engine import ValueStockEngine
engine = ValueStockEngine()
result = engine.evaluate_value_stock(stock_data)
```

### pytest 디버깅
```bash
# 상세 출력
pytest test_engine.py -vv -s

# 첫 번째 실패에서 중단
pytest test_engine.py -x

# 디버거 실행
pytest test_engine.py --pdb
```

---

## 📚 참고 문서

- **pytest 문서**: https://docs.pytest.org/
- **Streamlit 문서**: https://docs.streamlit.io/
- **Python 테스트 Best Practices**: https://docs.python-guide.org/writing/tests/

---

## 💡 결론

엔진/뷰 분리 아키텍처를 통해:
1. ✅ **테스트 가능**한 코드 작성
2. ✅ **유지보수 쉬운** 구조
3. ✅ **재사용 가능**한 모듈
4. ✅ **하위 호환성** 보장

이제 `pytest`로 엔진 로직만 독립적으로 테스트할 수 있으며, UI는 따로 검증할 수 있습니다! 🎉

