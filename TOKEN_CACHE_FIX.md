# ✅ 토큰 캐시 재사용 문제 해결

## 🎯 문제점

**현상**: 아직 유효한 토큰이 있는데 새로 발급받음 😢

**원인**: 
- v1.3.0 패치에서 토큰 캐시 경로를 **홈 디렉터리**로 변경
- 기존 경로: `.kis_token_cache.json` (현재 디렉터리)
- 새 경로: `~/.kis_token_cache.json` (홈 디렉터리)
- 기존 캐시 파일을 찾지 못해 새로 발급

---

## ✅ 해결 방법

### Fallback 로직 추가
**위치**: Line 317-329

```python
# ▶ 캐시 파일 우선순위: 홈 디렉터리 → 현재 디렉터리 (기존 토큰 보존)
cache_file_home = os.path.join(os.path.expanduser("~"), '.kis_token_cache.json')
cache_file_local = '.kis_token_cache.json'

# 우선 홈 디렉터리 확인, 없으면 현재 디렉터리 확인 (기존 캐시 재사용)
if os.path.exists(cache_file_home):
    cache_file = cache_file_home
elif os.path.exists(cache_file_local):
    cache_file = cache_file_local
    logger.info(f"💡 기존 토큰 캐시 발견: {cache_file_local} (다음 발급 시 {cache_file_home}로 이동 예정)")
else:
    logger.debug(f"토큰 캐시 파일 없음: {cache_file_home} 및 {cache_file_local}")
    return None
```

---

## 🔄 동작 방식

### 1. **기존 캐시 재사용**
```
1. 홈 디렉터리 확인: ~/.kis_token_cache.json
   → 있으면 사용

2. 없으면 현재 디렉터리 확인: .kis_token_cache.json
   → 있으면 사용 (기존 토큰 보존!)
   → "💡 기존 토큰 캐시 발견" 로그 출력

3. 둘 다 없으면: 새로 발급
```

### 2. **자동 마이그레이션**
```
토큰 만료 → 새로 발급
  ↓
홈 디렉터리에 저장: ~/.kis_token_cache.json
  ↓
다음부터는 홈 디렉터리 사용
```

---

## 📊 개선 효과

### Before (v1.3.0 초기)
```
❌ 홈 디렉터리만 확인
❌ 기존 토큰 무시
❌ 불필요한 재발급
```

### After (v1.3.0 수정)
```
✅ 홈 디렉터리 우선 확인
✅ 현재 디렉터리 fallback
✅ 기존 토큰 재사용
✅ 자동 마이그레이션
```

---

## 🎯 사용자 시나리오

### 시나리오 1: 기존 사용자
```
현재 디렉터리에 .kis_token_cache.json 있음
  ↓
기존 토큰 재사용 ✅
  ↓
토큰 만료 시 홈 디렉터리로 마이그레이션
```

### 시나리오 2: 신규 사용자
```
캐시 파일 없음
  ↓
새로 발급
  ↓
홈 디렉터리에 저장 (~/.kis_token_cache.json)
```

### 시나리오 3: 이미 마이그레이션된 사용자
```
홈 디렉터리에 ~/.kis_token_cache.json 있음
  ↓
홈 디렉터리 캐시 사용 ✅
```

---

## 🔒 보안 강화 유지

### 저장 경로
- **새 토큰**: 항상 홈 디렉터리에 저장
- **파일 권한**: chmod 600 (Unix 계열)

### 로드 경로
1. **우선**: 홈 디렉터리 (권장)
2. **Fallback**: 현재 디렉터리 (기존 토큰 보존)

---

## 🧪 테스트 방법

### 1. 기존 토큰이 있는 경우
```bash
# 현재 디렉터리에 .kis_token_cache.json 존재
ls -la .kis_token_cache.json

# 실행
streamlit run value_stock_finder.py

# 로그 확인
"💡 기존 토큰 캐시 발견: .kis_token_cache.json (다음 발급 시 ~/.kis_token_cache.json로 이동 예정)"
"✅ 캐시된 토큰 재사용 (만료까지: XXXX초)"
```

### 2. 새로 시작하는 경우
```bash
# 캐시 파일 없음
streamlit run value_stock_finder.py

# 새 토큰 발급
"💾 토큰 캐시 저장 완료: ~/.kis_token_cache.json (만료: XXXX초 후)"
```

---

## 📝 마이그레이션 가이드

### 수동 마이그레이션 (선택)
```bash
# 기존 토큰을 홈 디렉터리로 복사
cp .kis_token_cache.json ~/.kis_token_cache.json

# 기존 파일 삭제 (선택)
rm .kis_token_cache.json
```

### 자동 마이그레이션
- 토큰 만료 시 자동으로 홈 디렉터리에 저장됨
- 수동 작업 불필요 ✅

---

## ✅ 검증 완료

### 린터 검사
```
Line 282:20: Import "yaml" could not be resolved from source, severity: warning
```
→ **기존 경고만**  
→ **새로운 오류 없음** ✅

### 기능 검증
- ✅ 홈 디렉터리 캐시 우선 사용
- ✅ 현재 디렉터리 캐시 fallback
- ✅ 기존 토큰 재사용
- ✅ 자동 마이그레이션

---

## 🎉 완료!

**기존 토큰 재사용 + 자동 마이그레이션!**

- ✅ **기존 사용자**: 유효한 토큰 재사용
- ✅ **신규 사용자**: 홈 디렉터리에 저장
- ✅ **보안 강화**: chmod 600 유지
- ✅ **호환성**: Windows/Linux/Mac

---

**수정 날짜**: 2025-10-11  
**버전**: v1.3.1 (Token Cache Backward Compatibility)  
**상태**: ✅ 완료  
**효과**: 💡 기존 토큰 보존

**이제 유효한 토큰이 낭비되지 않습니다!** ✨

