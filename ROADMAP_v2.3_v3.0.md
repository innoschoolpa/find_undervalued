# 🗺️ 저평가 가치주 시스템 고도화 로드맵

**기반**: 전문가 평가 (2025-10-12)  
**현재 버전**: v2.2.1 (Evidence-Based + Stability)  
**목표**: v3.0 (Production-Grade Quant System)

---

## 📊 전문가 평가 요약

### 루브릭 점수 (5점 만점)

| 항목 | v2.1.3 | v2.2.1 | v3.0 목표 |
|------|--------|--------|-----------|
| 정확성 | 4.0 | 4.6 | **4.8** |
| 완전성 | 4.5 | 4.5 | **4.7** |
| 안정성 | 4.0 | 4.7 | **4.9** |
| 확장성 | 3.8 | 4.0 | **4.5** |
| 거버넌스 | 3.7 | 4.5 | **4.8** |
| **총점** | **19.9** | **22.3** | **23.7** |

**목표**: 95% 수준 (23.7/25) 달성

---

## 🎯 작업 우선순위 및 일정

### ✅ 완료 (v2.2.0~v2.2.1)

| ID | 작업 | 완료일 | 파일 |
|---|------|--------|------|
| P0-1 | 동적 r, b 레짐 모델 | 2025-10-12 | `dynamic_regime_calculator.py` |
| P0-2 | 데이터 신선도 가드 | 2025-10-12 | `DataFreshnessGuard` |
| P1-1 | 점수 캘리브레이션 | 2025-10-12 | `score_calibration_monitor.py` |
| P1-2 | 백테스트 프레임워크 | 2025-10-12 | `backtest_framework.py` |
| P1-3 | UX 안정성 패치 | 2025-10-12 | `value_stock_finder.py` |
| P1-4 | 크리티컬 버그 수정 | 2025-10-12 | `value_stock_finder.py` |

---

### 🔥 즉시 착수 (v2.2.2 ~ v2.3.0, 1~2주)

#### P1-5: 리스크 플래그 강화 🔴
**예상 시간**: 3일  
**우선순위**: HIGH  
**담당 모듈**: `risk_flag_evaluator.py` (신규)

**구현 내용**:
```python
class RiskFlagEvaluator:
    """리스크 플래그 평가 및 점수 감점"""
    
    def evaluate_accounting_risks(self, stock_data):
        """회계 리스크 평가"""
        penalties = []
        
        # 1. 연속 OCF 적자 (3년)
        if self._check_consecutive_negative_ocf(stock_data, years=3):
            penalties.append(('OCF_DEFICIT_3Y', -15))
        
        # 2. 순이익 변동성 (CV > 1.0)
        net_income_cv = self._calculate_net_income_cv(stock_data)
        if net_income_cv > 1.0:
            penalties.append(('HIGH_VOLATILITY', -10))
        
        # 3. 자사주 과다 취득 (시총 > 5% 연속 2년)
        if self._check_excessive_buyback(stock_data):
            penalties.append(('EXCESSIVE_BUYBACK', -8))
        
        # 4. 유증 반복 (3년 내 2회 이상)
        if self._check_frequent_capital_increase(stock_data):
            penalties.append(('FREQUENT_DILUTION', -12))
        
        # 5. 감사의견 한정/부적정
        audit_opinion = stock_data.get('audit_opinion', '적정')
        if audit_opinion in ['한정', '부적정', '의견거절']:
            penalties.append(('ADVERSE_AUDIT', -20))
        
        return penalties
    
    def evaluate_event_risks(self, stock_data):
        """이벤트 리스크 평가"""
        penalties = []
        
        # 1. 관리종목
        if stock_data.get('is_management_stock'):
            penalties.append(('MANAGEMENT_STOCK', -30))
        
        # 2. 불성실 공시 (최근 1년)
        if stock_data.get('unfaithful_disclosure'):
            penalties.append(('UNFAITHFUL_DISCLOSURE', -15))
        
        # 3. 자본잠식
        if stock_data.get('capital_impairment_ratio', 0) > 0:
            penalties.append(('CAPITAL_IMPAIRMENT', -25))
        
        return penalties
```

**적용 위치**: `evaluate_value_stock()` 최종 점수 계산 전

**효과**:
- 회계 이상 조기 탐지
- 리스크 회피 강화
- 펀더멘털 품질 향상

---

#### P1-6: 퍼센타일 글로벌 대체 로직 🟡
**예상 시간**: 2일  
**우선순위**: MEDIUM  
**담당 모듈**: `value_stock_finder.py` 수정

**구현 내용**:
```python
def _percentile_from_breakpoints(self, value, percentiles, use_global_fallback=True):
    """퍼센타일 계산 (섹터 표본 부족 시 글로벌 대체)"""
    
    # 1. 섹터 퍼센타일 시도
    if percentiles and len(percentiles) >= 3:
        sample_size = percentiles.get('sample_size', 0)
        
        # 표본 충분 (n >= 30)
        if sample_size >= 30:
            return self._calculate_percentile(value, percentiles)
        
        # 표본 부족 (n < 10) → 글로벌 대체
        if sample_size < 10 and use_global_fallback:
            logger.info(f"⚠️ 섹터 표본 부족 (n={sample_size}) → 전시장 분포 사용")
            global_percentiles = self._get_global_percentiles()
            return self._calculate_percentile(value, global_percentiles)
        
        # 중간 (10 <= n < 30) → 가중 평균
        if 10 <= sample_size < 30:
            sector_pct = self._calculate_percentile(value, percentiles)
            global_pct = self._calculate_percentile(value, self._get_global_percentiles())
            
            # 표본 수에 따라 가중치 조정
            weight_sector = (sample_size - 10) / 20  # 10→0%, 30→100%
            weight_global = 1.0 - weight_sector
            
            return sector_pct * weight_sector + global_pct * weight_global
    
    # 2. IQR ≈ 0 체크
    if percentiles:
        iqr = percentiles.get('p75', 0) - percentiles.get('p25', 0)
        if abs(iqr) < 1e-6:
            logger.debug(f"IQR≈0 감지 → 글로벌 분포 사용")
            return self._calculate_percentile(value, self._get_global_percentiles())
    
    # 3. 최종 폴백
    return 50.0

def _get_global_percentiles(self):
    """전시장 글로벌 분포 (캐시)"""
    # 전체 KOSPI/KOSDAQ 분포 (사전 계산 또는 캐시)
    return {
        'per': {'p10': 5, 'p25': 8, 'p50': 12, 'p75': 18, 'p90': 30},
        'pbr': {'p10': 0.5, 'p25': 0.8, 'p50': 1.2, 'p75': 2.0, 'p90': 3.5},
        'roe': {'p10': 3, 'p25': 6, 'p50': 10, 'p75': 15, 'p90': 22}
    }
```

**효과**:
- 소형 섹터 차별력 확보
- 퍼센타일 안정성 향상
- 극단적 섹터 편향 완화

---

#### P1-7: 데이터 커트오프 스탬프 도입 🟡
**예상 시간**: 2일  
**우선순위**: MEDIUM  
**담당 모듈**: `value_stock_finder.py` + CSV export

**구현 내용**:
```python
def screen_all_stocks(self, options):
    """전체 종목 스크리닝 (데이터 버전 스탬프 추가)"""
    
    # 데이터 버전 스탬프 생성
    data_version = {
        'timestamp': datetime.now().isoformat(),
        'price_cutoff': self._get_price_cutoff_date().isoformat(),
        'financial_cutoff': self._get_financial_cutoff_date().isoformat(),
        'sector_version': self._get_sector_mapping_version(),
        'universe_size': len(stock_universe),
        'config_hash': self._hash_config(options)
    }
    
    # CSV 메타데이터 행 추가
    metadata_rows = [
        {'종목코드': '#META', '종목명': 'data_version', '섹터': json.dumps(data_version)},
        {'종목코드': '#META', '종목명': 'criteria', '섹터': json.dumps(options)}
    ]
    
    # 결과에 메타데이터 포함
    df_with_meta = pd.concat([
        pd.DataFrame(metadata_rows),
        results_df
    ], ignore_index=True)
    
    return df_with_meta

def verify_csv_reproducibility(csv_path):
    """CSV 재현성 검증"""
    df = pd.read_csv(csv_path)
    
    # 메타데이터 추출
    meta_rows = df[df['종목코드'] == '#META']
    data_version = json.loads(meta_rows[meta_rows['종목명'] == 'data_version']['섹터'].iloc[0])
    
    # 컷오프 일치 여부 확인
    current_cutoff = self._get_price_cutoff_date()
    saved_cutoff = datetime.fromisoformat(data_version['price_cutoff'])
    
    if current_cutoff != saved_cutoff:
        logger.warning(f"⚠️ 가격 컷오프 불일치: 현재 {current_cutoff} vs 저장 {saved_cutoff}")
        return False
    
    return True
```

**효과**:
- 재현성 100% 보장
- 시점 일관성 검증
- 버전별 비교 가능

---

#### P1-8: MoS 안정화 가드 🟢
**예상 시간**: 1일  
**우선순위**: HIGH  
**담당 모듈**: `value_stock_finder.py` (진행 중)

**구현 내용**:
```python
def _winsorize_roe(self, roe, percentile=95):
    """ROE 윈저라이즈 (이상치 제거)"""
    if roe > 100:  # 100% 초과 → 캡핑
        logger.warning(f"⚠️ ROE {roe:.1f}% 이상치 → 100%로 캡핑")
        return 100.0
    if roe < -50:  # -50% 미만 → 플로어
        logger.warning(f"⚠️ ROE {roe:.1f}% 이상치 → -50%로 플로어")
        return -50.0
    return roe

def compute_mos_score(self, per, pbr, roe, sector):
    """MoS 점수 계산 (윈저라이즈 적용)"""
    
    # ✅ ROE 이상치 처리
    roe_clean = self._winsorize_roe(roe)
    
    # ✅ g >= r 상세 경고
    r = self.regime_calc.get_dynamic_r(sector)
    b = self.regime_calc.get_dynamic_b(sector)
    g = (roe_clean / 100.0) * b
    
    if g >= r:
        logger.warning(
            f"⚠️ MoS 계산 불가(성장률≥요구수익률):\n"
            f"  종목: {sector}\n"
            f"  ROE: {roe_clean:.1f}% (원본: {roe:.1f}%)\n"
            f"  g = ROE × b = {roe_clean:.1f}% × {b:.2f} = {g:.2%}\n"
            f"  r = {r:.2%}\n"
            f"  조건: g < r 필요, 현재 g={g:.2%} >= r={r:.2%}\n"
            f"  → MoS 점수 = 0점"
        )
        return 0
    
    # ... 기존 로직
```

**효과**:
- ROE 이상치 방지
- g >= r 투명한 설명
- MoS 안정성 확보

---

### 🚀 단기 (v2.3.0, 1개월)

#### P2-1: 캘리브레이션 UI 피드백 루프 🟡
**예상 시간**: 3일  
**우선순위**: MEDIUM  

**구현**:
```python
# 사이드바에 동적 컷오프 슬라이더
st.sidebar.subheader("🎯 동적 등급 컷오프")

target_strong_buy_pct = st.sidebar.slider(
    "STRONG_BUY 비율 (%)", 5, 20, 10, 1,
    help="전체 종목 중 상위 몇 %를 STRONG_BUY로?"
)

target_buy_pct = st.sidebar.slider(
    "BUY 비율 (%)", 10, 40, 20, 5,
    help="STRONG_BUY 다음 몇 %를 BUY로?"
)

# 실시간 컷오프 계산
if results:
    scores = [r['value_score'] for r in results]
    dynamic_cutoffs = calculate_dynamic_cutoffs(
        scores, 
        {
            'STRONG_BUY': target_strong_buy_pct,
            'BUY': target_buy_pct
        }
    )
    
    # 적용
    for r in results:
        if r['value_score'] >= dynamic_cutoffs['STRONG_BUY']:
            r['recommendation'] = 'STRONG_BUY'
        elif r['value_score'] >= dynamic_cutoffs['BUY']:
            r['recommendation'] = 'BUY'
        # ...
```

---

#### P2-2: 설명 가능성(XAI) - 기여도 분해 🟡
**예상 시간**: 4일  
**우선순위**: MEDIUM  

**구현**:
```python
def explain_score(self, stock_data, score_details):
    """점수 기여도 분해 (SHAP 유사)"""
    
    contributions = []
    
    # 1. PER 기여도
    per_score = score_details['per_score']
    per_percentile = score_details.get('per_percentile', 50)
    contributions.append({
        'factor': 'PER',
        'value': stock_data['per'],
        'percentile': per_percentile,
        'weight': 20,
        'score': per_score,
        'contribution': per_score / 148 * 100,  # 총점 대비 기여율
        'explanation': f"PER {stock_data['per']:.1f}배는 섹터 내 하위 {100-per_percentile:.0f}%ile (저평가)"
    })
    
    # 2~6. PBR, ROE, 품질, MoS, 섹터 보너스 동일
    
    # 기여도순 정렬
    contributions.sort(key=lambda x: x['contribution'], reverse=True)
    
    return contributions

# UI 표시
st.markdown("##### 🔍 왜 이 점수인가? (기여도 분해)")
for c in contributions[:5]:  # 상위 5개
    st.write(f"**{c['factor']}**: {c['score']:.1f}점 ({c['contribution']:.1f}%) - {c['explanation']}")
```

---

#### P2-3: 데이터 품질 UI 연동 🟡
**예상 시간**: 2일  
**우선순위**: MEDIUM  

**구현**:
```python
# 테이블에 경고 컬럼 추가
table_data.append({
    '종목명': stock['name'],
    '경고': self._get_quality_warning_icon(stock),
    # ... 기타
})

def _get_quality_warning_icon(self, stock_data):
    """데이터 품질 경고 아이콘"""
    warnings = []
    
    if self.freshness_guard:
        is_fresh, msg = self.freshness_guard.check_data_freshness({
            'price_ts': stock_data.get('price_ts'),
            'financial_ts': stock_data.get('financial_ts'),
            'sector': stock_data.get('sector')
        })
        if not is_fresh:
            warnings.append(f"⏰ {msg}")
    
    if stock_data.get('mos_warning'):
        warnings.append(f"⚠️ {stock_data['mos_warning']}")
    
    if not warnings:
        return "✅"
    
    # Tooltip 생성
    return f"⚠️ ({len(warnings)})"  # Streamlit tooltip 추가
```

---

### 🔮 중기 (v2.4.0, 2~3개월)

#### P2-4: 멀티 데이터 공급자 🔵
**예상 시간**: 2주  
**우선순위**: HIGH  

**구조**:
```
MultiDataProvider
├── KISProvider (가격, 현재 재무)
├── DARTProvider (과거 재무, 감사의견)
├── KRXProvider (섹터, 업종 분류)
└── CacheLayer (Redis/로컬)

데이터 정합성:
  - KIS vs DART PER 차이 > 20% → 경고
  - 섹터 불일치 → KRX 우선
  - 타임스탬프 강제 동기화
```

---

#### P2-5: 비동기 I/O 최적화 🔵
**예상 시간**: 1주  
**우선순위**: MEDIUM  

**구조**:
```python
async def analyze_stock_async(self, symbol, name):
    """비동기 종목 분석"""
    async with self.rate_limiter:  # 비동기 토큰버킷
        price_task = asyncio.create_task(self.get_price_async(symbol))
        financial_task = asyncio.create_task(self.get_financial_async(symbol))
        
        price, financial = await asyncio.gather(price_task, financial_task)
        
        return self._combine_and_score(price, financial)

# 배치 처리
async def screen_all_stocks_async(self, stock_universe):
    """비동기 배치 스크리닝"""
    tasks = [
        self.analyze_stock_async(symbol, name)
        for symbol, name in stock_universe.items()
    ]
    
    # 진행률 추적
    for coro in asyncio.as_completed(tasks):
        result = await coro
        results.append(result)
        progress_bar.progress(len(results) / len(tasks))
```

**효과**:
- 처리 속도 +50%
- API 대기 시간 활용
- 더 많은 종목 분석 가능

---

### 🌟 장기 (v3.0, 6개월)

#### P3-1: 백테스트 데이터 파이프라인 🟣
**예상 시간**: 3주  
**우선순위**: HIGH  

**컴포넌트**:
```
BacktestDataPipeline
├── DARTCrawler (재무제표 수집, 2010~현재)
├── PriceHistoryLoader (일봉 데이터, KIS or 외부)
├── CutoffEnforcer (룩어헤드 방지)
└── VersionManager (데이터 스냅샷 관리)

스케줄:
  - 주말: DART 재무 크롤링
  - 일일: 가격 업데이트
  - 월말: 백테스트 실행
```

---

#### P3-2: 벤치마크 비교 체계 🟣
**예상 시간**: 2주  

**벤치마크 3종**:
```python
benchmarks = {
    'KOSPI': kospi_index_returns,
    'Low_PERPBR': simple_value_strategy,  # PER 하위 30% & PBR 하위 30%
    'Quality': quality_strategy  # ROE 상위 30% & F-Score >= 7
}

# 비교 지표
metrics = {
    'CAGR': calculate_cagr(),
    'Sharpe': calculate_sharpe(),
    'MDD': calculate_mdd(),
    'Hit_Rate': calculate_hit_rate(),
    'Turnover': calculate_turnover()
}
```

---

#### P3-3: 실험 추적 시스템 (MLflow 유사) 🟣
**예상 시간**: 1주  

**구조**:
```
experiments/
├── 2025-10-12_v2.2.1/
│   ├── config.yaml
│   ├── results.csv
│   ├── metrics.json
│   └── calibration.json
├── 2025-11-01_v2.3.0/
│   └── ...
```

**추적 항목**:
- 파라미터 (r, b, 가중치)
- 성과 (CAGR, Sharpe, MDD)
- 드리프트 (점수 분포)
- 변경 사유

---

#### P3-4: 파라미터 버전 관리 🟣
**예상 시간**: 3일  

**criteria.yaml**:
```yaml
version: "v2.2.1"
author: "Quant Team"
date: "2025-10-12"
reason: "동적 r, b 레짐 도입"

parameters:
  score_weights:
    per: 20
    pbr: 20
    roe: 20
    quality: 43
    mos: 35
    sector_bonus: 10
  
  grade_cutoffs:
    strong_buy: 111  # 75%
    buy: 96          # 65%
    hold: 82         # 55%
  
  sector_caps:
    max_weight: 0.30
    rebalance_threshold: 0.05

changelog:
  - version: "v2.2.1"
    date: "2025-10-12"
    changes:
      - "동적 r, b 도입"
      - "MoS 점수 캡 35점"
    author: "AI Assistant"
```

---

## 📅 타임라인

### Phase 1: v2.2.2 (1주)
```
Week 1:
  - P1-5: 리스크 플래그 강화 (3일)
  - P1-6: 퍼센타일 글로벌 대체 (2일)
  - P1-8: MoS 윈저라이즈 (1일)
  - 테스트 및 배포 (1일)
```

### Phase 2: v2.3.0 (1개월)
```
Week 2-3:
  - P1-7: 데이터 커트오프 스탬프 (2일)
  - P2-1: 캘리브레이션 UI 피드백 (3일)
  - P2-2: 설명 가능성(XAI) (4일)
  - P2-3: 데이터 품질 UI 연동 (2일)

Week 4:
  - 통합 테스트
  - 문서 업데이트
  - v2.3.0 릴리스
```

### Phase 3: v2.4.0 (3개월)
```
Month 2:
  - P2-4: 멀티 데이터 공급자 (2주)
  - P2-5: 비동기 I/O (1주)
  - P2-6: 캐시 계층화 (1주)

Month 3:
  - 성능 최적화
  - 부하 테스트
  - v2.4.0 릴리스
```

### Phase 4: v3.0 (6개월)
```
Month 4-5:
  - P3-1: 백테스트 데이터 파이프라인 (3주)
  - P3-2: 벤치마크 비교 체계 (2주)

Month 6:
  - P3-3: 실험 추적 시스템 (1주)
  - P3-4: 파라미터 버전 관리 (3일)
  - 최종 검증 및 문서화
  - v3.0 릴리스
```

---

## 🎯 마일스톤

### M1: v2.2.2 (1주 후)
```
목표:
  ✅ 리스크 플래그 강화
  ✅ 퍼센타일 글로벌 대체
  ✅ MoS 안정화

기대 효과:
  - 정확성: 4.6 → 4.7
  - 안정성: 4.7 → 4.8
```

### M2: v2.3.0 (1개월 후)
```
목표:
  ✅ 캘리브레이션 UI 토글
  ✅ 설명 가능성(XAI)
  ✅ 데이터 품질 UI

기대 효과:
  - 완전성: 4.5 → 4.6
  - 거버넌스: 4.5 → 4.6
```

### M3: v2.4.0 (3개월 후)
```
목표:
  ✅ 멀티 데이터 공급자
  ✅ 비동기 I/O
  ✅ 캐시 계층화

기대 효과:
  - 확장성: 4.0 → 4.3
  - 안정성: 4.8 → 4.9
```

### M4: v3.0 (6개월 후)
```
목표:
  ✅ 백테스트 파이프라인
  ✅ 벤치마크 비교
  ✅ 실험 추적

기대 효과:
  - 정확성: 4.7 → 4.8
  - 거버넌스: 4.6 → 4.8
  - 총점: 22.3 → 23.7 (95%)
```

---

## 📊 예상 ROI

### 개발 투자
```
v2.2.2: 1주 (40시간)
v2.3.0: 1개월 (160시간)
v2.4.0: 2개월 (320시간)
v3.0:   2개월 (320시간)

총: 6개월 (840시간)
```

### 기대 효과
```
정확성: +20% (4.6 → 4.8)
안정성: +20% (4.7 → 4.9)
확장성: +50% (4.0 → 4.5)
거버넌스: +30% (4.5 → 4.8)

→ 백테스트 수익률 +10~15%p 예상
→ Sharpe Ratio 1.0 → 1.5 목표
```

---

## 🔧 즉시 착수 가능한 작업 (Week 1)

### Day 1-2: 리스크 플래그 강화
```python
# 파일: risk_flag_evaluator.py (신규)
# 위치: value_stock_finder.py 통합

구현:
  1. RiskFlagEvaluator 클래스
  2. 회계 리스크 평가 (OCF, 변동성, 감사의견)
  3. 이벤트 리스크 평가 (관리종목, 불성실공시)
  4. evaluate_value_stock()에 통합

테스트:
  - 관리종목 -30점 확인
  - 감사의견 한정 -20점 확인
```

### Day 3-4: 퍼센타일 글로벌 대체
```python
# 파일: value_stock_finder.py 수정

구현:
  1. _get_global_percentiles() 메서드
  2. _percentile_from_breakpoints() 수정
  3. 표본 크기별 가중 평균
  4. IQR ≈ 0 처리

테스트:
  - n=0 섹터 → 글로벌 사용
  - n=15 섹터 → 가중 평균
  - n=50 섹터 → 섹터만 사용
```

### Day 5: MoS 윈저라이즈
```python
# 파일: value_stock_finder.py 수정

구현:
  1. _winsorize_roe() 메서드
  2. compute_mos_score() 적용
  3. 상세 경고 로그

테스트:
  - ROE 150% → 100% 캡핑
  - ROE -80% → -50% 플로어
  - g >= r 상세 메시지 확인
```

### Day 6-7: 통합 테스트 및 문서
```
테스트:
  - 50개 종목 스크리닝
  - 리스크 플래그 확인
  - 퍼센타일 안정성 확인
  - MoS 계산 안정성 확인

문서:
  - CHANGELOG 업데이트
  - README 업데이트
  - 테스트 리포트 작성
```

---

## 📚 필요 자료/API

### 즉시 (v2.2.2)
- [ ] 관리종목 리스트 (KRX)
- [ ] 불성실공시 이력 (금감원)
- [ ] 전시장 PER/PBR/ROE 분포 (직접 계산)

### 단기 (v2.3.0)
- [ ] 과거 재무제표 (DART API)
- [ ] 감사의견 (DART)
- [ ] 자사주 취득 이력 (DART)

### 중기 (v2.4.0)
- [ ] DART API 키 발급
- [ ] Redis 서버 (또는 로컬 캐시)
- [ ] KRX 섹터 마스터 파일

### 장기 (v3.0)
- [ ] 2010~현재 일봉 데이터
- [ ] 벤치마크 지수 데이터
- [ ] 거래비용 모델

---

## ✅ 체크리스트 (전문가 제안 10개)

### 완료 (6개) ✅
- [x] r, b 동적 산출 모듈
- [x] 데이터 커트오프 스탬프 (부분 완료)
- [x] MoS 안정화 가드 (진행 중)
- [x] 점수 캘리브레이션
- [x] 백테스트 프레임워크
- [x] 레이트리미터 가시화

### 진행 중 (2개) 🔄
- [ ] 퍼센타일 대체 로직 (Week 1)
- [ ] 리스크 플래그 강화 (Week 1)

### 계획 (2개) 📅
- [ ] 등급컷 자동화 옵션 (v2.3.0)
- [ ] 기여도 카드 (v2.3.0)

---

## 🎯 다음 액션

### 이번 주 (즉시 착수)
1. `risk_flag_evaluator.py` 작성
2. 퍼센타일 글로벌 대체 구현
3. MoS 윈저라이즈 적용
4. v2.2.2 릴리스

### 다음 주
5. 캘리브레이션 UI 토글
6. 설명 가능성 카드
7. 데이터 품질 UI

### 1개월 후
8. v2.3.0 릴리스
9. 성과 측정
10. 백테스트 준비

---

**작성**: 2025-10-12  
**기반**: 전문가 평가 10개 체크리스트  
**완료도**: 6/10 (60%) → 목표 10/10 (100%)  
**예상 완료**: v3.0 (6개월 후)

