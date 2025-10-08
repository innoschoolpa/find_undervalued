# 시가총액 순위 API 상태 보고

## 📋 KIS 고객센터 안내 정보

### ✅ 공식 안내
- **엔드포인트**: `/uapi/domestic-stock/v1/quotations/inquire-market-cap`
- **TR_ID**: `FHPST01740000`
- **필수 파라미터**:
  - `FID_COND_MRKT_DIV_CODE`: J (코스피) / Q (코스닥)
  - `FID_INPUT_ISCD`: 0000
  - `FID_PERIOD_DIV_CODE`: 0 (시가총액 기준)
  - `FID_ORG_ADJ_PRC`: 0 (수정주가 미반영)

## ❌ 실제 테스트 결과

### 테스트 URL
```
https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-market-cap?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD=0000&FID_PERIOD_DIV_CODE=0&FID_ORG_ADJ_PRC=0
```

### 오류 메시지
```
❌ 404 Client Error: Not Found
```

### 시도한 다른 엔드포인트들 (모두 실패)
1. `quotations/inquire-market-cap` ❌ 404
2. `quotations/market-cap-rank` ❌ 404
3. `quotations/market-cap-ranking` ❌ 404
4. `ranking/market-cap` ❌ API 오류
5. `quotations/inquire-daily-price` ❌ API 오류
6. `quotations/volume-rank` (시총 TR_ID) ❌ API 오류

## ✅ 현재 작동하는 대안

### 방법 1: KOSPI 마스터 파일 사용 (현재 구현)
```python
# kospi_code.xlsx 파일에서 시가총액으로 정렬하여 반환
result = mcp.get_market_cap_ranking(limit=100)
# ✅ 100개 정상 반환 (삼성전자 5055370억 등)
```

**장점:**
- ✅ 안정적으로 작동
- ✅ 정확한 시가총액 데이터
- ✅ 빠른 응답 속도
- ✅ 100개 이상도 가능

**단점:**
- ⚠️ 실시간 데이터 아님 (마스터 파일 업데이트 주기에 의존)
- ⚠️ kospi_code.xlsx 파일 필요

### 방법 2: 다른 순위 API 조합
```python
# 거래량 30개 + 등락률 100개 + PER 100개 + 배당 100개
# 총 330개 정도 확보 가능
```

## 💡 권장 사항

### 1. 단기 해결책 (현재 구현됨)
**KOSPI 마스터 파일을 주 방법으로 사용**
- API 실패 시 자동으로 마스터 파일로 폴백
- 신뢰성 높고 안정적

### 2. 장기 해결책
**KIS API GitHub 또는 공식 샘플 코드 확인 필요**
```
https://github.com/koreainvestment/open-trading-api
```

고객센터에서 안내한 엔드포인트가 실제로 작동하지 않으므로:
1. GitHub 공식 샘플에서 실제 작동하는 코드 확인
2. 혹은 실전 투자 계좌에서만 작동하는지 확인 (현재 모의투자 계좌 사용 중)
3. API 버전이나 권한 설정 확인

### 3. 현실적인 접근
시가총액 API 없이도 충분히 가치주 발굴 가능:
- 거래량 순위: 30개 (유동성 높은 종목)
- PER 순위: 50~100개 (저평가 가치주)
- 배당률 순위: 100개 (안정적 가치주)
- KOSPI 마스터 파일: 전체 종목
- **총 200~300개 후보군 확보 가능**

## 📊 최종 결론

### 현재 상태
- ❌ KIS API 시가총액 순위: 작동 안 함 (404)
- ✅ KOSPI 마스터 파일: 정상 작동
- ✅ 기타 순위 API: 정상 작동 (거래량, 등락률 등)

### 코드 구현
```python
def get_market_cap_ranking(self, limit: int = 100):
    """
    1순위: KIS API 시도
    2순위: KOSPI 마스터 파일 (✅ 현재 작동)
    3순위: 등락률 상승 순위 API
    """
```

### 사용자 영향
**✅ 문제 없음!**
- 시가총액 상위 100개 정상 조회 가능
- 실시간성은 약간 떨어지지만 가치주 발굴에는 충분
- 안정적이고 신뢰할 수 있는 데이터

## 🎯 다음 단계

1. ✅ KOSPI 마스터 파일 방식 유지
2. ⏳ KIS GitHub 샘플 확인 (시간 날 때)
3. ⏳ 실전 계좌로 테스트 (모의투자 제한일 가능성)

