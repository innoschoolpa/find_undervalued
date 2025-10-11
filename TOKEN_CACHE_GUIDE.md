# KIS API 토큰 캐싱 가이드

## ⚠️ 중요: 토큰 발급 제한

KIS API 토큰은 **1일 1회 발급, 24시간 유효**입니다.

- ❌ **매번 새로운 토큰을 발급받으면 안 됩니다**
- ✅ **한 번 발급받은 토큰을 24시간 동안 재사용해야 합니다**

## 자동 토큰 캐싱 시스템

`MCPKISIntegration` 클래스는 자동으로 토큰을 캐싱합니다.

### 작동 방식

1. **첫 번째 API 호출**
   ```
   🔄 새로운 토큰 발급 중...
   💾 토큰 캐시 저장 완료 (유효 시간: 24.0시간)
   ```

2. **두 번째 이후 호출 (24시간 이내)**
   ```
   ✅ 캐시된 토큰 사용 (남은 시간: 23.5시간)
   ```

3. **24시간 경과 후**
   ```
   ⏰ 캐시된 토큰이 만료되었습니다
   🔄 새로운 토큰 발급 중...
   💾 토큰 캐시 저장 완료 (유효 시간: 24.0시간)
   ```

### 캐시 파일

- **위치**: `.kis_token_cache.json` (프로젝트 루트)
- **형식**: JSON
- **내용**:
  ```json
  {
    "access_token": "eyJhbGc...",
    "issue_time": 1728457821.234,
    "expires_in": 86400,
    "issue_date": "2025-10-09T10:30:21.234567"
  }
  ```

### 만료 시간 확인

- **자동 확인**: 매 API 호출 시 자동으로 확인
- **안전 여유**: 만료 5분 전부터 새 토큰 발급
- **실제 유효 시간**: 23시간 55분 (안전 여유 포함)

## 사용 예제

### 기본 사용 (자동 캐싱)

```python
from mcp_kis_integration import MCPKISIntegration

# OAuth 매니저 생성
oauth = SimpleOAuthManager(appkey="...", appsecret="...")

# MCP 통합 객체 생성
mcp = MCPKISIntegration(oauth)

# API 호출 (첫 번째: 토큰 발급 + 캐싱)
price1 = mcp.get_current_price("005930")

# API 호출 (두 번째: 캐시된 토큰 사용)
price2 = mcp.get_current_price("000660")

# 세션 종료
mcp.close()
```

### 프로그램 재시작 후 (캐시 재사용)

```python
# 프로그램을 종료하고 다시 시작해도
# 24시간 이내라면 캐시된 토큰을 자동으로 재사용합니다

mcp = MCPKISIntegration(oauth)
price = mcp.get_current_price("005930")  # ✅ 캐시된 토큰 사용
```

## 수동 관리

### 캐시 확인

```bash
# Windows
type .kis_token_cache.json

# Linux/Mac
cat .kis_token_cache.json
```

### 캐시 삭제 (강제 재발급)

```bash
# Windows
del .kis_token_cache.json

# Linux/Mac
rm .kis_token_cache.json
```

### Python에서 캐시 상태 확인

```python
import json
from pathlib import Path
import time

cache_file = Path(".kis_token_cache.json")
if cache_file.exists():
    with open(cache_file, 'r') as f:
        cache = json.load(f)
    
    elapsed = time.time() - cache['issue_time']
    remaining = cache['expires_in'] - elapsed
    hours = remaining / 3600
    
    print(f"토큰 남은 시간: {hours:.1f}시간")
else:
    print("캐시 없음 (다음 호출 시 새로 발급)")
```

## 주의사항

### ✅ DO

1. **토큰을 자동으로 관리하게 두세요**
   - `MCPKISIntegration`이 알아서 처리합니다

2. **캐시 파일을 Git에 커밋하지 마세요**
   - `.gitignore`에 추가: `.kis_token_cache.json`

3. **프로그램을 여러 번 재시작해도 괜찮습니다**
   - 24시간 이내라면 캐시된 토큰을 재사용합니다

### ❌ DON'T

1. **토큰을 매번 새로 발급받지 마세요**
   - 1일 발급 횟수 제한이 있습니다

2. **캐시 파일을 임의로 수정하지 마세요**
   - 손상된 캐시는 자동으로 무시되고 새로 발급됩니다

3. **여러 프로세스에서 동시에 토큰을 발급하지 마세요**
   - 캐시 시스템이 이를 방지하지만, 가능한 순차적으로 실행하세요

## 트러블슈팅

### 문제: "토큰 발급 실패"

**원인**: API 키가 잘못되었거나 네트워크 문제

**해결**:
1. API 키 확인: `config.yaml`의 `app_key`, `app_secret`
2. 네트워크 연결 확인
3. KIS API 서버 상태 확인

### 문제: "토큰이 계속 새로 발급됩니다"

**원인**: 캐시 파일이 손상되었거나 권한 문제

**해결**:
```bash
# 캐시 파일 삭제 후 재시작
rm .kis_token_cache.json
python your_script.py
```

### 문제: "401 Unauthorized"

**원인**: 토큰이 만료되었거나 무효화됨

**해결**:
1. 캐시 파일 삭제
2. 프로그램 재시작 (자동으로 새 토큰 발급)

## 로깅

토큰 관련 로그 메시지:

| 메시지 | 의미 |
|--------|------|
| `✅ 캐시된 토큰 사용 (남은 시간: XX시간)` | 캐시 사용 |
| `🔄 새로운 토큰 발급 중...` | 새 토큰 발급 |
| `💾 토큰 캐시 저장 완료 (유효 시간: 24.0시간)` | 캐싱 성공 |
| `⏰ 캐시된 토큰이 만료되었습니다` | 토큰 만료 |
| `⚠️ 토큰 캐시 로드 실패: ...` | 캐시 읽기 실패 (자동 복구) |

## 성능 및 안정성

### 장점

1. **불필요한 API 호출 방지**: 토큰 발급 횟수 최소화
2. **빠른 시작**: 프로그램 재시작 시 즉시 사용 가능
3. **자동 관리**: 만료 시간 자동 확인 및 갱신
4. **안전 여유**: 만료 5분 전 자동 갱신

### 통계 (일반적인 사용 시나리오)

- **토큰 발급 횟수**: 하루 1회
- **캐시 히트율**: ~99.9% (24시간 동안)
- **추가 지연 시간**: 0ms (캐시 사용 시)
- **첫 번째 토큰 발급 시간**: ~500ms

## 관련 파일

- `mcp_kis_integration.py`: 토큰 캐싱 구현
- `test_mcp_production.py`: SimpleOAuthManager (테스트용)
- `.kis_token_cache.json`: 토큰 캐시 파일 (자동 생성)
- `.gitignore`: 캐시 파일 제외 설정

## 참고

- KIS OpenAPI 공식 문서: https://apiportal.koreainvestment.com/
- 토큰 유효 기간: 24시간 (86400초)
- 발급 제한: 1일 1회


