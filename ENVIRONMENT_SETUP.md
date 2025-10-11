# 환경변수 설정 가이드

## 🔧 KIS API 환경변수 설정

### 1. .env 파일 생성
```bash
python setup_env.py
```

### 2. API 키 발급
1. [한국투자증권 OpenAPI 포털](https://apiportal.koreainvestment.com/) 접속
2. 회원가입 및 로그인
3. '앱 등록' 메뉴에서 새 앱 등록
4. 앱 이름, 설명 입력 후 등록
5. 등록된 앱에서 appkey, appsecret 확인

### 3. .env 파일 수정
생성된 `.env` 파일을 열어서 다음 값들을 실제 값으로 변경하세요:

```bash
# 앱키 (36자리)
KIS_APPKEY=실제_앱키_입력

# 시크릿키 (180자리)  
KIS_APPSECRET=실제_시크릿키_입력

# 테스트 모드 (true: 모의투자, false: 실전투자)
KIS_TEST_MODE=true
```

### 4. 시스템 설정 (선택사항)
```bash
# 개발 모드 (디버그 로그 활성화)
VSF_DEBUG=false

# 상세 로그 모드 (분석 과정 상세 출력)
VSF_VERBOSE=false

# 캐시 TTL (초 단위, 0이면 캐시 비활성화)
CACHE_TTL=1800

# API 레이트 리미팅 설정
VSF_RATE_PER_SEC=0.5                    # 초당 요청 수 (0.5-2.0 권장)
VSF_ANALYZER_MAX_CONCURRENCY=3          # API 동시 요청 수 (1-5 권장)
VSF_FAST_MODE_WORKERS=4                 # 빠른 모드 워커 수 (2-16 권장)
```

## 🚀 시스템 실행

환경변수 설정이 완료되면 다음 명령으로 시스템을 실행할 수 있습니다:

```bash
streamlit run value_stock_finder.py
```

## 🔍 환경변수 확인

현재 설정된 환경변수를 확인하려면:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('KIS_APPKEY:', '설정됨' if os.getenv('KIS_APPKEY', '').startswith('PS') else '미설정'); print('KIS_TEST_MODE:', os.getenv('KIS_TEST_MODE'))"
```

## ⚠️ 주의사항

- **API 키 보안**: API 키는 절대 공개하지 마세요
- **Git 보안**: `.env` 파일은 `.gitignore`에 포함되어 있어 Git에 올라가지 않습니다
- **키 구분**: 모의투자용 키와 실전투자용 키가 다릅니다
- **테스트 우선**: 처음에는 반드시 `KIS_TEST_MODE=true`로 설정하여 모의투자에서 테스트하세요

## 🛠️ 문제 해결

### OAuth 인증 실패
- API 키가 올바르게 설정되었는지 확인
- 모의투자/실전투자 모드가 올바른지 확인
- 네트워크 연결 상태 확인

### API 호출 실패
- `VSF_RATE_PER_SEC` 값을 낮춰보세요 (0.3-0.5)
- `VSF_ANALYZER_MAX_CONCURRENCY` 값을 줄여보세요 (1-2)
- API 키의 일일 호출 한도 확인

### 성능 문제
- `VSF_FAST_MODE_WORKERS` 값을 조정하세요
- `CACHE_TTL` 값을 늘려보세요 (3600-7200)
- `VSF_DEBUG=false`로 설정하여 로그 출력 최소화
