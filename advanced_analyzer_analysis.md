# advanced_analyzer.py 병렬 처리 시스템 분석

## 🔍 시스템 개요

기존 `advanced_analyzer.py`의 병렬 처리 시스템은 KIS OpenAPI를 활용한 대규모 주식 분석 시스템으로, 30개 종목을 43.7초에 처리하여 11배의 성능 향상을 달성했습니다.

## 📊 처리 과정 분석

### 1단계: 초기화 및 설정
```
✅ KOSPI 마스터 데이터 로드 완료: 2479개 종목
✅ config.yaml에서 DART API 키를 로드했습니다.
⚡ DART 기업코드 매핑을 건너뛰고 동적 검색을 사용합니다.
✅ DART 포괄적 재무 분석기 초기화 완료
```

**주요 컴포넌트:**
- KOSPI 마스터 데이터 (2,479개 종목)
- DART API 통합 (재무제표 분석)
- KIS API 토큰 관리
- TPS 레이트 리미터 (초당 8건 제한)

### 2단계: 종목 선별
```
📊 1단계: 시가총액 상위 종목 선별
✅ 30개 종목 선별 완료
```

**선별 기준:**
- 시가총액 상위 30개 종목
- 최소 시가총액: 500억원
- 우선주 제외

### 3단계: 병렬 분석 수행

#### TPS 레이트 리미터
```python
class TPSRateLimiter:
    """KIS OpenAPI TPS 제한을 고려한 레이트리미터"""
    
    def __init__(self, max_tps: int = 8):  # 안전 마진
        self.max_tps = max_tps
        self.requests = queue.Queue()
        self.lock = Lock()
    
    def acquire(self):
        """요청 허가를 받습니다."""
        # 1초 이전 요청 제거 및 TPS 제한 확인
        # 필요시 대기 시간 적용
```

#### 병렬 처리 구조
```python
with ThreadPoolExecutor(max_workers=3) as executor:
    # 각 종목에 대한 Future 생성
    future_to_stock = {}
    for stock in stocks:
        future = executor.submit(
            analyze_single_stock_safe,
            symbol, name, market_cap, sector,
            analyzer, max_per, min_roe, max_debt_ratio
        )
        future_to_stock[future] = (symbol, name)
    
    # 완료된 작업들을 처리
    for future in as_completed(future_to_stock):
        # 결과 처리 및 진행률 업데이트
```

### 4단계: 단일 종목 분석 프로세스

각 종목마다 다음 7단계 분석을 수행합니다:

#### 1. 현재가 및 기본 정보 조회
```python
# TPS 제한 적용
rate_limiter.acquire()
current_data = analyzer.provider.get_stock_price_info(symbol)
```
- 현재가, 등락률, PER, PBR, 거래량 조회
- 실패 시 재시도 로직

#### 2. 재무비율 분석
```python
rate_limiter.acquire()
financial_ratios = analyzer.financial_ratio_analyzer.get_financial_ratios(symbol)
```
- ROE, ROA, 부채비율, 자기자본비율
- 매출액/영업이익/순이익 성장률

#### 3. 수익성비율 분석
```python
rate_limiter.acquire()
profit_ratios = analyzer.profit_ratio_analyzer.get_profit_ratios(symbol)
```
- 순이익률, 매출총이익률
- 수익성 등급 평가

#### 4. 안정성비율 분석
```python
rate_limiter.acquire()
stability_ratios = analyzer.stability_ratio_analyzer.get_stability_ratios(symbol)
```
- 유동비율, 당좌비율, 차입의존도
- 안정성 등급 평가

#### 5. 성장성비율 분석
```python
rate_limiter.acquire()
growth_ratios = analyzer.growth_ratio_analyzer.get_growth_ratios(symbol)
```
- 매출액/영업이익 연평균 성장률
- 자본/총자산 성장률
- 성장성 등급 평가

#### 6. 추정실적 분석
```python
rate_limiter.acquire()
estimate_performance = analyzer.estimate_performance_analyzer.get_estimate_performance(symbol)
```
- 추정 EPS, PER, ROE
- 미래 실적 전망

#### 7. 종합 점수 계산
```python
def calculate_comprehensive_score(stock_info, max_per, min_roe, max_debt_ratio):
    score = 0
    
    # 1. 가치 평가 점수 (40%)
    per = stock_info.get('per', 0)
    if per > 0 and per <= max_per:
        if per <= 10: score += 40
        elif per <= 15: score += 30
        elif per <= 20: score += 20
        else: score += 10
    
    # 2. 수익성 점수 (30%)
    roe = stock_info.get('roe', 0)
    if roe >= min_roe:
        if roe >= 20: score += 30
        elif roe >= 15: score += 25
        elif roe >= 10: score += 20
        else: score += 10
    
    # 3. 안정성 점수 (20%)
    debt_ratio = stock_info.get('debt_ratio', 0)
    if debt_ratio <= max_debt_ratio:
        if debt_ratio <= 30: score += 20
        elif debt_ratio <= 50: score += 15
        elif debt_ratio <= 70: score += 10
        else: score += 5
    
    # 4. 성장성 점수 (10%)
    revenue_growth = stock_info.get('revenue_growth_rate', 0)
    if revenue_growth > 0:
        if revenue_growth >= 20: score += 10
        elif revenue_growth >= 10: score += 8
        elif revenue_growth >= 5: score += 5
        else: score += 2
    
    # 5. 규모 점수 (10%)
    market_cap = stock_info.get('market_cap', 0)
    if market_cap >= 100000: score += 10  # 10조원 이상
    elif market_cap >= 50000: score += 8  # 5조원 이상
    elif market_cap >= 10000: score += 5  # 1조원 이상
    elif market_cap >= 5000: score += 2   # 5천억원 이상
    
    return score
```

### 5단계: 필터 조건 적용

```python
def apply_filter_penalties(stock_info, max_per, min_roe, max_debt_ratio):
    penalty_reasons = []
    penalty_score = 0
    
    per = stock_info.get('per', 0)
    roe = stock_info.get('roe', 0)
    debt_ratio = stock_info.get('debt_ratio', 0)
    
    # PER 필터
    if pd.isna(per) or per <= 0:
        penalty_score -= 30
        penalty_reasons.append("PER 데이터 없음")
    elif per > max_per:
        penalty_score -= 20
        penalty_reasons.append(f"PER {per:.1f}배 > {max_per}배")
    
    # ROE 필터
    if pd.isna(roe):
        penalty_score -= 20
        penalty_reasons.append("ROE 데이터 없음")
    elif roe < min_roe:
        penalty_score -= 20
        penalty_reasons.append(f"ROE {roe:.1f}% < {min_roe}%")
    
    # 부채비율 필터
    if debt_ratio > max_debt_ratio:
        penalty_score -= 15
        penalty_reasons.append(f"부채비율 {debt_ratio:.1f}% > {max_debt_ratio}%")
    
    stock_info['score'] += penalty_score
    stock_info['penalty_reasons'] = penalty_reasons
    
    return stock_info
```

## 📈 성능 분석 결과

### 처리 성능
- **총 소요시간**: 43.7초
- **성공률**: 100% (30/30개)
- **평균 처리속도**: 0.69종목/초
- **순차 처리 예상시간**: 480.0초
- **성능 향상**: 11.0배
- **시간 절약**: 436.3초

### 분석 품질
- **TPS 준수**: 초당 8건 이하 유지
- **에러 처리**: 안정적인 예외 처리
- **데이터 완성도**: 높은 데이터 수집률

## 🏆 분석 결과 TOP 10

| 순위 | 종목코드 | 종목명 | 시가총액 | 현재가 | PER | ROE | 종합점수 |
|------|----------|--------|----------|--------|-----|-----|----------|
| 1 | 402340 | SK스퀘어 | 265,744억 | 206,000원 | 7.5배 | 29.9% | 100.0점 |
| 2 | 000660 | SK하이닉스 | 2,409,600억 | 348,000원 | 12.8배 | 37.5% | 95.0점 |
| 3 | 000270 | 기아 | 400,483억 | 101,400원 | 4.2배 | 16.5% | 90.0점 |
| 4 | 011200 | HMM | 240,371억 | 23,700원 | 5.5배 | 8.9% | 85.0점 |
| 5 | 012330 | 현대모비스 | 284,105억 | 309,000원 | 7.1배 | 8.5% | 80.0점 |
| 6 | 005930 | 삼성전자 | 4,528,500억 | 79,400원 | 16.0배 | 6.6% | 65.0점 |
| 7 | 015760 | 한국전력 | 236,242억 | 36,800원 | 6.8배 | 16.8% | 65.0점 |
| 8 | 035420 | NAVER | 367,035억 | 235,000원 | 19.7배 | 7.0% | 63.0점 |
| 9 | 005380 | 현대차 | 440,229억 | 215,000원 | 4.7배 | 11.2% | 60.0점 |
| 10 | 000810 | 삼성화재 | 216,252억 | 464,500원 | 11.3배 | 15.5% | 58.0점 |

## ⚠️ 주요 감점 사유 분석

### 1. PER 초과 (가장 빈번)
- 삼성바이오로직스: PER 68.1배 > 25.0배 (-20점)
- LG에너지솔루션: PER 데이터 없음 (-30점)
- 카카오: PER 507.3배 > 25.0배 (-20점)

### 2. 부채비율 초과
- 한화에어로스페이스: 부채비율 278.0% > 150.0% (-15점)
- KB금융: 부채비율 1180.7% > 150.0% (-15점)
- 현대차: 부채비율 179.5% > 150.0% (-15점)

### 3. ROE 미달
- LG에너지솔루션: ROE -4.3% < 5.0% (-20점)
- LG화학: ROE -3.4% < 5.0% (-20점)
- 셀트리온: ROE 2.0% < 5.0% (-20점)

## 🔧 시스템 특징

### 장점
1. **고성능 병렬 처리**: 11배 성능 향상
2. **안정적인 TPS 관리**: API 제한 준수
3. **포괄적 분석**: 7단계 심층 분석
4. **실시간 진행률**: Rich Progress Bar
5. **강건한 에러 처리**: 높은 성공률

### 개선 가능 영역
1. **분석 깊이**: 투자의견 데이터 미활용
2. **점수 체계**: 단순한 가중치 기반
3. **필터링**: 고정된 임계값 사용
4. **실시간성**: 배치 처리 방식

## 🚀 통합 시스템과의 비교

| 항목 | 기존 시스템 | 통합 시스템 |
|------|-------------|-------------|
| 분석 범위 | 재무비율 중심 | 투자의견 + 추정실적 |
| 점수 체계 | 5단계 가중치 | 4단계 통합 점수 |
| 처리 속도 | 0.69종목/초 | 6.36종목/초 |
| 분석 품질 | 재무 중심 | 종합적 분석 |
| 사용 편의성 | 복잡한 설정 | 직관적 명령어 |

## 📊 결론

기존 `advanced_analyzer.py`의 병렬 처리 시스템은 다음과 같은 특징을 가집니다:

1. **안정성**: TPS 제한 준수로 안정적인 처리
2. **포괄성**: 7단계 심층 재무 분석
3. **성능**: 11배 병렬 처리 성능 향상
4. **확장성**: 대규모 종목 분석 가능

하지만 투자의견 데이터를 활용하지 못하고, 단순한 점수 체계를 사용하는 한계가 있습니다. 새로운 통합 시스템은 이러한 한계를 보완하여 더욱 종합적이고 실용적인 분석을 제공합니다.
