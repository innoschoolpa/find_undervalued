# 섹터 매핑 불일치 문제

**날짜**: 2025-10-12  
**문제**: 일부 섹터가 pickle/DB에 없음

---

## 🔍 발견된 문제

### pickle 캐시 섹터 (6개)
```
1. 제조업 (n=339)
2. 제약 (n=36)
3. 금융 (n=37)
4. 건설 (n=47)
5. 지주회사 (n=55)
6. 기타 (n=371)
```

### 로그에서 찾는 섹터
```
✅ 전기전자 -> 제조업? (매핑 필요)
❌ 운송장비 -> ??? (없음!)
✅ 금융
✅ 건설
✅ 기타
✅ 제약
```

---

## 💡 해결 방법

### 옵션 1: 섹터명 매핑 추가 (빠름)

pickle 캐시의 섹터명과 실제 조회 섹터명 매핑:

```python
# value_stock_finder.py

SECTOR_ALIASES = {
    '전기전자': '제조업',
    '운송장비': '제조업',  # 또는 별도 섹터 생성
    '금융서비스': '금융',
    '에너지/화학': '에너지/화학',  # 또는 별도
}

def _normalize_sector_key(self, sector_name):
    # 별칭 적용
    sector = SECTOR_ALIASES.get(sector_name, sector_name)
    return sector.lower().replace(' ', '_')
```

### 옵션 2: 섹터 캐시 재생성 (정확)

더 세분화된 섹터 분류로 재생성:

```bash
# pickle 캐시 삭제
Remove-Item cache\sector_stats.pkl

# 버튼 클릭하여 재생성
# [🚀 섹터 통계 자동 생성]
```

### 옵션 3: DB에 추가 섹터 생성 (권장)

999개 종목 데이터를 다시 섹터별로 분류하여 DB에 저장:
- 기존: 6개 광범위 섹터
- 신규: 10~15개 세분화 섹터

---

## 🎯 즉시 해결 (1분)

### 임시 매핑 추가
```python
# _cached_sector_data 수정

def _cached_sector_data(self, sector_name):
    normalized = self._normalize_sector_name(sector_name)
    
    # 임시 매핑
    TEMP_MAP = {
        '전기전자': '제조업',
        '운송장비': '제조업',
    }
    
    db_sector = TEMP_MAP.get(normalized, normalized)
    
    # DB 조회 (매핑된 이름 사용)
    db_stats = db.get_sector_stats()
    stats = db_stats.get(db_sector)
    
    if stats:
        logger.info(f"✅ DB 캐시 히트 (매핑): {normalized} -> {db_sector} (n={stats['sample_size']})")
```

---

## 📊 현재 상태

### DB
```
✅ 6개 섹터 저장됨
✅ 999개 종목 스냅샷 (이전)
✅ pickle과 동일한 통계
```

### 문제
```
❌ 섹터명 불일치
   - pickle: 제조업, 제약, 금융...
   - 조회: 전기전자, 운송장비...
```

---

## 💬 추천

**Option 1 (즉시 해결)**:
임시 매핑 추가 → Streamlit 재시작 → 정상 작동

**Option 2 (장기 해결)**:
섹터 분류 체계 정비 → DB 재생성 → 완벽한 매핑

**어떻게 하시겠어요?**

