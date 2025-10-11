# 🚀 실전 서버 전환 가이드

## ✅ 완료된 작업

### 1. config.yaml 설정 변경
```yaml
kis_api:
  test_mode: false  # ✅ 실전 서버로 변경됨
```

**변경 사항**:
- `test_mode: false` 추가하여 실전 서버(`openapi.koreainvestment.com:9443`) 사용
- 기존 테스트 서버(`openapivts.koreainvestment.com:29443`)에서 전환

## 🔑 API 키 확인 필요

현재 설정된 API 키:
```yaml
app_key: "PSDC0a10eC3Klz083GJ8DZvYQcQwTbk6tDOA"
app_secret: "Nckvgu0K/I9Roz2Ed0WX1hiViT8evYyYA5HkC9qKXy87enDHqY4ivWOHtirrUICqz8Ao7lGcA0C5QxD+ZSYZE+gYENLeoOdSrdQfFySZOcWSHZPNyDI2YzbF3t9Ug8LSkLzAP77U9FIaDpYLD7yZzrVZl1hUaXzrhZJJGXDFWIOYiHs4hAI="
```

⚠️ **주의**: 
- 위 API 키가 **실전용**인지 **테스트용**인지 확인 필요
- KIS 증권사 홈페이지에서 확인:
  - 테스트용: `openapi.koreainvestment.com` 에서 발급
  - 실전용: 실제 계좌 연동 후 발급

### API 키 확인 방법
1. KIS 증권 홈페이지 로그인
2. Open API 메뉴 → API 키 관리
3. 현재 키가 **모의투자용**인지 **실전용**인지 확인

## 🔄 재시작 필요

설정 변경 후 Streamlit 앱을 재시작해야 합니다:

```bash
# 기존 앱 종료 (Ctrl+C)
# 새로 실행
python -m streamlit run value_stock_finder.py --server.port 8515
```

## 📊 기대 효과

### ✅ 해결될 문제
- ❌ 500 에러 해결
- ✅ 시장 상태 API 정상 작동
- ✅ 섹터 지수 API 정상 작동
- ✅ 실시간 데이터 조회 가능

### 🎯 변경 사항
| 항목 | 테스트 서버 | 실전 서버 |
|------|------------|----------|
| 도메인 | `openapivts.koreainvestment.com` | `openapi.koreainvestment.com` |
| 포트 | 29443 | 9443 |
| 데이터 | 모의 데이터 | 실시간 데이터 |
| API 안정성 | 낮음 (일부 API 미지원) | 높음 (모든 API 지원) |
| 호출 제한 | 느슨함 | 엄격함 |

## ⚡ 빠른 재시작

터미널에서:
```bash
# 1. 기존 프로세스 찾기
lsof -i :8515

# 2. 프로세스 종료
kill -9 <PID>

# 3. 앱 재시작
python -m streamlit run value_stock_finder.py --server.port 8515
```

## 🔍 확인 사항

앱 재시작 후 로그에서 확인:
```bash
# ✅ 실전 서버 사용 확인
OAuth 인증 시도 - 도메인: https://openapi.koreainvestment.com:9443

# ❌ 테스트 서버 사용 (변경 실패)
OAuth 인증 시도 - 도메인: https://openapivts.koreainvestment.com:29443
```

## 📝 참고사항

### 실전 서버 사용 시 주의사항
1. **API 호출 제한 엄격**: 초당 요청 수 제한 준수 필요
2. **토큰 관리**: 24시간 유효, 중복 발급 방지 (이미 구현됨 ✅)
3. **데이터 정확성**: 실제 시장 데이터 사용
4. **계좌 연동**: 주문 기능 사용 시 실제 계좌 연결

### 토큰 캐시 초기화 (필요 시)
```bash
# 기존 토큰 캐시 삭제
rm .kis_token_cache.json

# 앱 재시작하면 새로운 토큰 발급
```

## 🎉 완료!

설정 변경이 완료되었습니다. 이제 Streamlit 앱을 재시작하면 실전 서버를 사용하여 API가 정상 작동할 것입니다!

**다음 단계**:
1. ✅ config.yaml 변경 완료
2. ⏳ Streamlit 앱 재시작
3. ⏳ 시장 상태 API 테스트
4. ⏳ 섹터 지수 API 테스트

---

**문제 발생 시**:
1. API 키가 실전용인지 확인
2. 로그에서 도메인 확인
3. 토큰 캐시 초기화 후 재시도


