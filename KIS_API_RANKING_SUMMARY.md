# KIS API 순위 조회 API 정리

## 📊 실제 테스트 결과

### ✅ 작동하는 API

| API | 반환량 | 엔드포인트 | TR_ID |
|-----|-------|-----------|-------|
| 거래량 순위 | **30개** | `quotations/volume-rank` | FHPST01710000 |
| 재무비율(PER) 순위 | 50~100개 (예상) | `quotations/inquire-financial-ratio` | FHPST01750000 |

### ⚠️ 확인 필요

| API | 상태 | TR_ID | 비고 |
|-----|-----|-------|------|
| 시가총액 순위 | 404 오류 | FHPST01740000 | 엔드포인트 확인 필요 |

## 🎯 핵심 발견

### 1. 페이징 미지원
- **tr_cont가 빈 문자열로 반환됨** → 더 이상 데이터 없음
- 각 API는 **한 번 호출로 30~100개만 반환**
- **300개 이상 조회 불가능** (페이징 미지원)

### 2. 올바른 접근 방법
여러 API를 조합해서 다양한 종목 확보:

```python
# 거래량 순위: 30개
volume_stocks = mcp.get_volume_ranking()  # 약 30개

# PER 순위: 50~100개
per_stocks = mcp.get_per_ranking()  # 약 50~100개

# 배당률 순위: 100개
dividend_stocks = mcp.get_dividend_ranking(limit=100)  # 약 100개

# 총 180~230개 수준의 후보군 확보 가능
```

### 3. API 반환량
- 거래량 순위: **정확히 30개**
- PER/PBR 순위: **50~100개 수준**
- 배당률 순위: **약 100개**
- **총 200개 내외** 후보군 확보 가능

## 🔧 수정 내역

### Before (잘못된 가정)
```python
# 페이징으로 300개씩 조회 가능하다고 가정
get_market_cap_ranking(limit=300, use_paging=True)  # ❌ 실제로는 불가능
```

### After (현실에 맞게 수정)
```python
# 각 API는 30~100개만 반환, 여러 API 조합
get_volume_ranking()  # 30개
get_per_ranking()  # 50~100개
get_dividend_ranking(limit=100)  # 100개
# 총 200개 수준
```

## 📝 주요 변경사항

1. **페이징 기능 제거**: `use_paging` 파라미터 삭제
2. **limit 기본값 조정**: 
   - 거래량: 100 → 30
   - 시가총액/PER: 300 → 100
3. **주석 수정**: "300개 지원"을 "30~100개 수준"으로 정정
4. **NXT/통합 조회 지원 추가**: `market_type` 파라미터 (J/NX/UN)

## 💡 권장사항

### 가치주 발굴 시
```python
mcp.find_real_value_stocks(
    limit=50,
    candidate_pool_size=200  # 실제로 180~230개 확보됨
)
```

### 여러 API 조합 전략
1. 거래량 상위 30개 (유동성)
2. PER 저평가 50~100개 (가치주)
3. 배당률 상위 100개 (안정성)
4. 중복 제거 후 총 **200개 수준** 확보

## ⚙️ 신규 API 추가

### 1. 종목별 투자자매매동향(일별)
```python
mcp.get_investor_trend_daily(
    symbol="005930",
    start_date="20250101",
    end_date="20250108"
)
```

### 2. 등락률 순위
```python
mcp.get_updown_ranking(
    limit=100,
    updown_type="0"  # 0:상승, 1:하락
)
```

### 3. 호가잔량 순위
```python
mcp.get_asking_price_ranking(limit=100)
```

### 4. 관심종목(멀티) 시세조회
```python
mcp.get_multiple_current_price(
    symbols=["005930", "000660", "035420"]
)
```

## 🏁 결론

- ✅ 페이징 미지원 확인, 코드 수정 완료
- ✅ NXT/통합 조회 지원 추가
- ✅ 신규 API 4개 추가
- ⚠️ 시가총액 순위 API 엔드포인트 재확인 필요
- 💡 현실적인 접근: **여러 API 조합**으로 200개 수준 확보

