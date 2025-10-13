# 섹터 표본 부족 (n=0) 해결 방법

**문제**: 로그에 계속 "⚠️ 섹터 표본 부족 (n=0)" 경고

---

## 🔍 원인

**섹터 캐시가 Streamlit에서 로드되지 않음**

```
캐시 파일: ✅ 존재 (cache/sector_stats.pkl)
Streamlit: ❌ 로드 안 됨
```

---

## ✅ 즉시 해결 방법

### 방법 1: Streamlit 새로고침 (가장 간단)

```
1. Streamlit 앱 열기
2. F5 (새로고침)
3. 섹터 캐시 자동 로드
```

**예상 결과**:
```
✅ 섹터 통계 로드 완료: 6개 섹터
📊 제조업(n=165), 운송장비(n=171), IT(n=166), 화학(n=164), 전기전자(n=171)

→ n=0 경고 사라짐 ✅
```

---

### 방법 2: 캐시 강제 재생성

#### Step 1: 기존 캐시 삭제
```bash
# Windows
del cache\sector_stats.pkl

# Linux/Mac
rm cache/sector_stats.pkl
```

#### Step 2: 새로 생성
```bash
python create_sector_cache.py
```

#### Step 3: Streamlit 재시작
```bash
# 기존 앱 종료 (Ctrl+C)
streamlit run value_stock_finder.py
```

---

### 방법 3: Streamlit 내에서 자동 생성

#### Step 1: 앱 실행
```bash
streamlit run value_stock_finder.py
```

#### Step 2: UI에서 버튼 클릭
```
"전체 종목 스크리닝" 탭
  ↓
❌ 섹터 통계 캐시 없음 (알림)
  ↓
[🚀 섹터 통계 자동 생성] 클릭
  ↓
3~5분 대기
  ↓
✅ 섹터 통계 생성 완료
  ↓
F5 새로고침
```

---

## 🔧 현재 상태 확인

### 확인 스크립트
```bash
python check_sector_cache.py
```

**기대 출력**:
```
1️⃣ 캐시 파일 확인
   경로: cache\sector_stats.pkl
   존재: True
   생성: 2025-10-12 18:51:39
   크기: 2,312 bytes
   섹터: 6개
     - 제조업: n=165
     - 운송장비: n=171
     - IT: n=166
     - 화학: n=164
     - 전기전자: n=171
     - 금융: n=163
```

---

## 📊 n=0 경고가 사라지는 원리

### 이전 (n=0)
```python
def _cached_sector_data(sector_name):
    stats = data_provider.get_sector_data(sector)
    # → 실시간 조회, 표본 없음
    # → n=0
```

### 이후 (n=30~200)
```python
def _cached_sector_data(sector_name):
    stats = _load_sector_cache().get(sector)  # @st.cache_resource
    # → 캐시에서 조회
    # → n=165 (제조업 예시)
```

---

## 🎯 권장 순서

### 가장 빠른 방법 (1분)

```
1. Streamlit 앱에서 F5 새로고침
   
2. 확인:
   ✅ 섹터 통계 로드 완료: 6개 섹터
   
3. 스크리닝 실행
   
4. 로그 확인:
   ✅ n=0 경고 사라짐
   ✅ 섹터 캐시 히트 메시지
```

---

### 확실한 방법 (5분)

```
1. 캐시 삭제:
   del cache\sector_stats.pkl
   
2. 재생성:
   python create_sector_cache.py
   (y 입력하여 진행)
   
3. Streamlit 재시작:
   streamlit run value_stock_finder.py
   
4. F5 새로고침
```

---

## 💡 핵심 메시지

**"F5 새로고침만 하면 됩니다!"**

- 캐시 파일: ✅ 이미 존재
- 로드 실패: Streamlit 재실행 필요
- 해결: F5 한 번!

---

**작성**: 2025-10-12  
**문제**: n=0 경고  
**해결**: F5 새로고침 ⭐

