# 📊 KIS vs DART 재무자료 불일치 처리 가이드

**작성**: 2025-10-12  
**목적**: KIS API와 DART API의 재무자료가 다를 때 처리 방법 설명

---

## 🤔 왜 데이터가 다를까?

### 1. 데이터 소스 차이
| 구분 | KIS API | DART API |
|------|---------|----------|
| **출처** | 한국투자증권 | 금융감독원 전자공시 |
| **데이터** | 실시간 추정치 | 공식 공시 재무제표 |
| **업데이트** | 실시간 | 분기/연간 (공시 기준) |
| **정확도** | 추정 포함 | 감사 완료 |
| **시차** | 즉시 | 최대 수개월 지연 |

### 2. 실제 사례: 삼성전자 ROE

**KIS API**: 12.0% (최근 추정치)  
**DART API**: 138.58% (2023년 공시)  
**차이**: 168.1% 🚨

**원인**:
- KIS: 최신 분기 실적 기반 연환산 추정
- DART: 전년도 확정 실적 (높은 수익성 시기)
- 시점 차이로 인한 불일치

---

## 🎯 처리 전략 (5가지)

### 1. CONSERVATIVE (보수적) ⭐ 기본 전략

**원칙**: 투자 안전성 우선

```
수익성 지표 (ROE, 영업이익률 등):
  → 낮은 값 선택 (보수적 추정)
  
리스크 지표 (PER, PBR, 부채비율 등):
  → 높은 값 선택 (위험 강조)
```

**예시**:
```
ROE:
  KIS: 12.0%, DART: 138.6%
  → 조정값: 12.0% (낮은 값, 보수적)

부채비율:
  KIS: 150.0%, DART: 883.1%
  → 조정값: 883.1% (높은 값, 보수적)
```

**장점**: 
- ✅ 투자 안전성 극대화
- ✅ 과대평가 방지
- ✅ 저평가 종목 발굴에 유리

**단점**:
- ⚠️ 실제 가치보다 과소평가 가능

**권장 대상**: 
- 보수적 투자자
- 리스크 회피 전략
- 저평가 가치주 발굴

---

### 2. PREFER_DART (DART 우선)

**원칙**: 공식 공시 데이터 신뢰

```
모든 메트릭:
  → DART 값 우선 사용
```

**예시**:
```
ROE:
  KIS: 12.0%, DART: 138.6%
  → 조정값: 138.6% (DART 우선)
```

**장점**:
- ✅ 공식 감사 데이터
- ✅ 법적 근거 명확
- ✅ 재무제표 일관성

**단점**:
- ⚠️ 시차 발생 (분기 지연)
- ⚠️ 최신 동향 반영 불가

**권장 대상**:
- 장기 투자자
- 펀더멘털 중심 투자
- 감사 데이터 신뢰

---

### 3. PREFER_KIS (KIS 우선)

**원칙**: 최신 데이터 우선

```
모든 메트릭:
  → KIS 값 우선 사용
```

**예시**:
```
ROE:
  KIS: 12.0%, DART: 138.6%
  → 조정값: 12.0% (KIS 우선)
```

**장점**:
- ✅ 최신 실적 반영
- ✅ 실시간 변화 추적
- ✅ 시장 반응 빠름

**단점**:
- ⚠️ 추정치 포함
- ⚠️ 수정 가능성

**권장 대상**:
- 단기 투자자
- 모멘텀 투자
- 최신 동향 중시

---

### 4. AVERAGE (평균)

**원칙**: 중간값 사용

```
모든 메트릭:
  → (KIS + DART) / 2
```

**예시**:
```
ROE:
  KIS: 12.0%, DART: 138.6%
  → 조정값: 74.3% (평균)
```

**장점**:
- ✅ 편향 최소화
- ✅ 극단값 완화

**단점**:
- ⚠️ 의미 없는 중간값 가능
- ⚠️ 큰 차이 시 부정확

**권장 대상**:
- 중립적 접근
- 소폭 불일치 시

---

### 5. WEIGHTED_BLEND (가중 평균)

**원칙**: 신뢰도 기반 가중

```
DART: 70% (공식 공시)
KIS: 30% (실시간 추정)

조정값 = DART * 0.7 + KIS * 0.3
```

**예시**:
```
ROE:
  KIS: 12.0%, DART: 138.6%
  → 조정값: 100.0% (138.6*0.7 + 12.0*0.3)
```

**장점**:
- ✅ 두 소스 모두 반영
- ✅ 신뢰도 고려
- ✅ 균형잡힌 추정

**단점**:
- ⚠️ 가중치 설정 어려움

**권장 대상**:
- 균형잡힌 접근
- 두 소스 모두 중요시

---

## ⚖️ 전략별 비교

### 시나리오: 삼성전자 ROE

| 전략 | KIS | DART | 조정값 | 특징 |
|------|-----|------|--------|------|
| **CONSERVATIVE** | 12.0% | 138.6% | **12.0%** | 보수적 (낮은 값) ⭐ |
| **PREFER_DART** | 12.0% | 138.6% | **138.6%** | 공식 우선 |
| **PREFER_KIS** | 12.0% | 138.6% | **12.0%** | 최신 우선 |
| **AVERAGE** | 12.0% | 138.6% | **74.3%** | 평균 |
| **WEIGHTED** | 12.0% | 138.6% | **100.0%** | 가중 (7:3) |

---

## 🔧 허용 오차 설정

### 메트릭별 기준

| 메트릭 | 허용 오차 | 이유 |
|--------|----------|------|
| **ROE** | ±10% | 수익성 변동성 고려 |
| **PER** | ±15% | 주가 변동 반영 |
| **PBR** | ±10% | 장부가치 안정성 |
| **부채비율** | ±20% | 부채 조정 빈번 |
| **매출액** | ±5% | 상대적으로 안정 |

### 처리 로직
```python
차이율 = |KIS - DART| / 평균 * 100

if 차이율 <= 허용오차:
    → 평균값 사용 (두 소스 모두 신뢰)
else:
    → 전략에 따라 조정 (CONSERVATIVE, DART, KIS 등)
```

---

## 💻 코드 예시

### 기본 사용 (CONSERVATIVE)

```python
from multi_data_provider import MultiDataProvider

provider = MultiDataProvider()

# 데이터 수집 (자동 조정)
data = provider.get_stock_data('005930', cross_check=True)

# 조정된 값 확인
if 'reconciled_data' in data:
    reconciled = data['reconciled_data']
    
    print(f"ROE (조정): {reconciled.get('roe_reconciled', 0):.2f}%")
    print(f"ROE (KIS): {reconciled.get('roe_kis', 0):.2f}%")
    print(f"ROE (DART): {reconciled.get('roe_dart', 0):.2f}%")
    
    # 조정 이유 확인
    for meta in data['reconciliation_metadata']:
        print(f"\n{meta['metric'].upper()}:")
        print(f"  전략: {meta['strategy_used']}")
        print(f"  사유: {meta['reason']}")
```

### 전략 변경

```python
from data_reconciliation_strategy import DataReconciliator, ReconciliationStrategy

# DART 우선 전략
reconciliator = DataReconciliator(strategy=ReconciliationStrategy.PREFER_DART)

# 조정
reconciled_val, meta = reconciliator.reconcile_metric(
    'roe', 
    kis_value=12.0, 
    dart_value=138.6
)

print(f"조정값: {reconciled_val:.2f}%")  # 138.6% (DART 우선)
```

---

## 📊 실제 테스트 결과

### 삼성전자 조정 예시 (CONSERVATIVE 전략)

```
📊 조정 결과:
   ROE (KIS): 12.00%
   ROE (DART): 138.58%
   차이: 168.1%
   
   → 조정값: 12.00% (보수적 - 낮은 수익성 선택)
   사유: 투자 안전성 우선

부채비율:
   KIS: 150.0%
   DART: 883.1%
   차이: 141.9%
   
   → 조정값: 883.1% (보수적 - 높은 리스크 선택)
   사유: 위험 강조
```

---

## ⚠️ 주의 사항

### 1. 시점 차이
```
KIS: 2024년 추정치
DART: 2023년 확정치

→ 비교 의미 제한적
→ 동일 시점 데이터 사용 권장
```

### 2. 계정 기준 차이
```
KIS: 별도 재무제표
DART: 연결 재무제표 (기본)

→ 재무제표 구분 확인 필요
→ fs_div 파라미터 조정 (CFS/OFS)
```

### 3. 대폭 불일치 시
```
차이 > 100%:
  → 원인 확인 필요
  → 데이터 오류 가능성
  → 수동 검토 권장
```

---

## 💡 권장 처리 절차

### Step 1: 자동 조정
```python
# MultiDataProvider가 자동으로 조정
data = provider.get_stock_data('005930', cross_check=True)
```

### Step 2: 불일치 확인
```python
if data['discrepancies']:
    print(f"⚠️ 불일치 발견: {len(data['discrepancies'])}개")
    
    for disc in data['discrepancies']:
        print(f"  {disc['metric']}: {disc['diff_pct']:.1f}% 차이")
```

### Step 3: 조정 결과 검토
```python
if 'reconciled_data' in data:
    # 조정된 값 사용
    roe = data['reconciled_data']['roe_reconciled']
    
    # 조정 사유 확인
    for meta in data['reconciliation_metadata']:
        print(f"  {meta['metric']}: {meta['reason']}")
```

### Step 4: 수동 검토 (선택)
```python
# 대폭 불일치 시 (차이 > 100%)
for meta in data['reconciliation_metadata']:
    if meta['diff_pct'] > 100:
        print(f"🚨 수동 검토 필요: {meta['metric']}")
        print(f"   KIS: {meta['kis']:.1f}")
        print(f"   DART: {meta['dart']:.1f}")
        print(f"   차이: {meta['diff_pct']:.1f}%")
```

---

## 🎯 전략 선택 가이드

### 저평가 가치주 발굴 (권장)
```
전략: CONSERVATIVE (보수적)

이유:
  - 수익성을 낮게 추정 → 진짜 저평가 종목만 선택
  - 리스크를 높게 추정 → 안전 마진 확보
  - 투자 안전성 극대화
```

### 장기 투자
```
전략: PREFER_DART (DART 우선)

이유:
  - 공식 감사 데이터
  - 법적 근거 명확
  - 장기 트렌드 파악
```

### 단기 트레이딩
```
전략: PREFER_KIS (KIS 우선)

이유:
  - 최신 실적 반영
  - 시장 반응 빠름
  - 실시간 변화 추적
```

### 균형 접근
```
전략: WEIGHTED_BLEND (가중 평균)

이유:
  - 두 소스 모두 반영
  - DART 70% + KIS 30%
  - 극단값 완화
```

---

## 📈 실제 적용 예시

### 시나리오 1: 정상 범위 불일치

**데이터**:
```
ROE - KIS: 12.0%, DART: 13.0% (차이 8%)
```

**처리** (모든 전략 동일):
```
허용 오차 내 (10%) → 평균 사용
조정값: 12.5%
```

---

### 시나리오 2: 중간 불일치

**데이터**:
```
ROE - KIS: 15.0%, DART: 20.0% (차이 28.6%)
```

**처리**:
```
CONSERVATIVE → 15.0% (낮은 값)
PREFER_DART  → 20.0% (DART 우선)
PREFER_KIS   → 15.0% (KIS 우선)
AVERAGE      → 17.5% (평균)
WEIGHTED     → 18.5% (70:30 가중)
```

**권장**: CONSERVATIVE (15.0%)

---

### 시나리오 3: 대폭 불일치 (실제 삼성전자)

**데이터**:
```
ROE - KIS: 12.0%, DART: 138.6% (차이 168%)
```

**처리**:
```
CONSERVATIVE → 12.0% (낮은 값) ⭐ 권장
PREFER_DART  → 138.6% (DART 우선)
PREFER_KIS   → 12.0% (KIS 우선)
AVERAGE      → 74.3% (평균)
WEIGHTED     → 100.0% (70:30 가중)
```

**원인 분석 필요**:
- 시점 차이 (2023 vs 2024)
- 재무제표 구분 (연결 vs 별도)
- 특별 이익 포함 여부

**권장 조치**:
1. 시점 일치 확인
2. 재무제표 타입 확인
3. 수동 검토 후 결정

---

## 🔧 설정 방법

### config.yaml 설정

```yaml
data_reconciliation:
  # 기본 전략
  default_strategy: "conservative"  # conservative, dart, kis, average, weighted
  
  # 메트릭별 허용 오차
  tolerance:
    roe: 10.0      # ±10%
    per: 15.0      # ±15%
    pbr: 10.0      # ±10%
    debt_ratio: 20.0  # ±20%
  
  # 가중치 (WEIGHTED 전략 사용 시)
  weights:
    dart: 0.7      # 70%
    kis: 0.3       # 30%
  
  # 대폭 불일치 임계값
  manual_review_threshold: 100.0  # 100% 이상 차이 시 경고
```

### 코드에서 변경

```python
# 전략 변경
from data_reconciliation_strategy import ReconciliationStrategy

provider = MultiDataProvider()

# DART 우선으로 변경
provider.reconciliator.strategy = ReconciliationStrategy.PREFER_DART
```

---

## 📊 통계 및 모니터링

### 불일치 추적

```python
# 통계 조회
stats = provider.get_statistics()

print(f"크로스체크 통과: {stats['cross_check_passed']}건")
print(f"크로스체크 실패: {stats['cross_check_failed']}건")
print(f"데이터 조정: {stats['reconciled']}건")

# 불일치 분포
discrepancies = stats.get('discrepancies', [])
for disc in discrepancies:
    print(f"  {disc['metric']}: 평균 {disc['avg_diff_pct']:.1f}% 차이")
```

---

## 🎯 실무 가이드

### Case 1: 소폭 불일치 (< 10%)
```
상황: ROE 차이 8%
조치: 자동 평균 사용
검토: 불필요
```

### Case 2: 중간 불일치 (10~50%)
```
상황: ROE 차이 28%
조치: CONSERVATIVE 전략 (낮은 값)
검토: 로그 확인
```

### Case 3: 대폭 불일치 (> 50%)
```
상황: ROE 차이 168%
조치: CONSERVATIVE 전략 + 경고
검토: 필수! 원인 분석 필요
```

### Case 4: 극단 불일치 (> 200%)
```
상황: 데이터 오류 의심
조치: 종목 제외 또는 수동 입력
검토: 즉시
```

---

## 🚀 베스트 프랙티스

### 1. 기본 설정
```python
# 저평가 가치주 발굴용
strategy = ReconciliationStrategy.CONSERVATIVE

# 이유:
# - 수익성 보수적 → 진짜 저평가만 선택
# - 리스크 보수적 → 안전 마진 확보
```

### 2. 로깅 활성화
```python
import logging
logging.basicConfig(level=logging.INFO)

# 불일치 자동 로깅됨:
# INFO: ⚖️ roe 보수적 선택: 12.0 (차이 168.1%)
```

### 3. 대폭 불일치 시 알림
```python
for meta in reconciliation_metadata:
    if meta['diff_pct'] > 100:
        # Slack/Email 알림
        send_alert(f"⚠️ {meta['metric']} 대폭 불일치: {meta['diff_pct']:.0f}%")
```

---

## 📚 참고 자료

### 관련 파일
- `data_reconciliation_strategy.py` - 조정 전략 구현
- `multi_data_provider.py` - 멀티 소스 통합
- `dart_data_provider.py` - DART API

### 문서
- `DART_API_TEST_REPORT.md` - DART 테스트
- `P2_ALL_COMPLETE.md` - P2 완료 보고서

---

## 🎉 결론

**KIS와 DART 재무자료가 다를 때 → CONSERVATIVE 전략 권장!**

✅ **보수적 접근**:
- 수익성은 낮게 (안전)
- 리스크는 높게 (경고)
- 투자 안전성 극대화

✅ **자동 처리**:
- 허용 오차 내: 평균 사용
- 허용 오차 초과: 전략 적용
- 대폭 불일치: 경고 로깅

✅ **투명성**:
- 조정 이유 명확
- 원본 데이터 보존
- 메타데이터 제공

---

**작성**: 2025-10-12  
**전략**: CONSERVATIVE (기본) ⭐  
**상태**: 프로덕션 적용 가능 ✅

