# 섹터 캐시 → DB 전환 제안

**날짜**: 2025-10-12  
**제안자**: 사용자  
**우선순위**: P2-6 (캐시 계층화)

---

## 🎯 문제 인식

### 현재 상황 (Pickle 캐시)
```python
# 24시간마다 1000번 API 호출!
cache_file = 'cache/sector_stats.pkl'
ttl = 24 hours

# 문제점:
❌ 1000번 API 호출 = 높은 비용
❌ TTL 만료 시 전체 재수집 필요
❌ 이력 관리 불가
❌ 증분 업데이트 불가
❌ 동시성 제어 불가
```

### 개선 방향 (DB 저장)
```sql
-- 영구 저장 + 증분 업데이트
CREATE TABLE stock_snapshots (
    stock_code TEXT,
    timestamp DATETIME,
    price REAL,
    per REAL,
    pbr REAL,
    roe REAL,
    sector TEXT,
    ...
)

-- 장점:
✅ 영구 저장
✅ 증분 업데이트 (변경된 것만)
✅ 이력 관리 (시계열 분석)
✅ 쿼리 최적화
✅ 동시성 제어
✅ 백업/복구 용이
```

---

## 📊 비용 비교

### Pickle 캐시 (현재)
```
매일 1000번 API 호출
  → 월 30,000번
  → 분당 0.694번 (평균)
  → Rate Limit 여유 있지만 비효율적
```

### DB + 증분 업데이트 (제안)
```
최초: 1000번 (1회만)
이후: 50~100번/일 (변경된 종목만)
  → 월 1,500~3,000번
  → 90~95% 비용 절감! 💰
```

---

## 🏗️ 설계 제안

### 1단계: SQLite (로컬, 빠른 구현)

#### 스키마
```sql
-- 종목 스냅샷 (일별)
CREATE TABLE stock_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    date DATE NOT NULL,
    
    -- 기본 정보
    name TEXT,
    sector TEXT,
    sector_normalized TEXT,
    
    -- 시세
    price REAL,
    market_cap REAL,
    
    -- 재무
    per REAL,
    pbr REAL,
    roe REAL,
    debt_ratio REAL,
    
    -- 메타
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_code, date)
);

-- 인덱스
CREATE INDEX idx_stock_date ON stock_snapshots(stock_code, date);
CREATE INDEX idx_sector_date ON stock_snapshots(sector_normalized, date);
CREATE INDEX idx_date ON stock_snapshots(date);

-- 섹터 통계 (프리컴퓨팅, 빠른 조회)
CREATE TABLE sector_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector TEXT NOT NULL,
    date DATE NOT NULL,
    
    sample_size INTEGER,
    
    -- PER 통계
    per_p10 REAL,
    per_p25 REAL,
    per_p50 REAL,
    per_p75 REAL,
    per_p90 REAL,
    per_mean REAL,
    per_std REAL,
    
    -- PBR 통계
    pbr_p10 REAL,
    pbr_p25 REAL,
    pbr_p50 REAL,
    pbr_p75 REAL,
    pbr_p90 REAL,
    pbr_mean REAL,
    pbr_std REAL,
    
    -- ROE 통계
    roe_p10 REAL,
    roe_p25 REAL,
    roe_p50 REAL,
    roe_p75 REAL,
    roe_p90 REAL,
    roe_mean REAL,
    roe_std REAL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(sector, date)
);

CREATE INDEX idx_sector_stats_date ON sector_stats(sector, date);
```

#### 구현
```python
# db_cache_manager.py

import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, List, Any
import pandas as pd

class DBCacheManager:
    """DB 기반 섹터 캐시 (SQLite)"""
    
    def __init__(self, db_path: str = 'cache/stock_data.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """DB 초기화"""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA_SQL)  # 위 스키마
        conn.close()
    
    def get_latest_snapshots(self, max_age_days: int = 1) -> pd.DataFrame:
        """최신 스냅샷 조회 (캐시)"""
        cutoff_date = date.today() - timedelta(days=max_age_days)
        
        query = """
            SELECT * FROM stock_snapshots
            WHERE date >= ?
            ORDER BY date DESC, stock_code
        """
        
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(query, conn, params=(cutoff_date,))
        conn.close()
        
        return df
    
    def get_stale_stocks(self, max_age_days: int = 1) -> List[str]:
        """업데이트 필요한 종목 리스트"""
        cutoff_date = date.today() - timedelta(days=max_age_days)
        
        # 최근 업데이트된 종목
        recent_query = """
            SELECT DISTINCT stock_code
            FROM stock_snapshots
            WHERE date >= ?
        """
        
        conn = sqlite3.connect(self.db_path)
        recent = pd.read_sql_query(recent_query, conn, params=(cutoff_date,))
        recent_codes = set(recent['stock_code'].tolist())
        
        # 전체 종목 (외부에서 가져옴)
        all_codes = self._get_all_stock_codes()  # KIS API
        
        # 차집합 = 업데이트 필요
        stale_codes = all_codes - recent_codes
        
        conn.close()
        return list(stale_codes)
    
    def save_snapshots(self, snapshots: List[Dict[str, Any]]):
        """스냅샷 저장 (UPSERT)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for snap in snapshots:
            cursor.execute("""
                INSERT INTO stock_snapshots 
                (stock_code, date, name, sector, sector_normalized, 
                 price, market_cap, per, pbr, roe, debt_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stock_code, date) DO UPDATE SET
                    price = excluded.price,
                    per = excluded.per,
                    pbr = excluded.pbr,
                    roe = excluded.roe,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                snap['code'], snap['date'], snap['name'],
                snap['sector'], snap['sector_normalized'],
                snap['price'], snap['market_cap'],
                snap['per'], snap['pbr'], snap['roe'], snap['debt_ratio']
            ))
        
        conn.commit()
        conn.close()
    
    def compute_sector_stats(self, target_date: date = None) -> Dict[str, Dict]:
        """섹터 통계 계산 및 캐싱"""
        if target_date is None:
            target_date = date.today()
        
        conn = sqlite3.connect(self.db_path)
        
        # 스냅샷에서 섹터별 통계 계산
        query = """
            SELECT 
                sector_normalized,
                COUNT(*) as sample_size,
                -- PER
                percentile_cont(0.10) WITHIN GROUP (ORDER BY per) as per_p10,
                percentile_cont(0.25) WITHIN GROUP (ORDER BY per) as per_p25,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY per) as per_p50,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY per) as per_p75,
                percentile_cont(0.90) WITHIN GROUP (ORDER BY per) as per_p90,
                AVG(per) as per_mean,
                -- PBR
                percentile_cont(0.10) WITHIN GROUP (ORDER BY pbr) as pbr_p10,
                percentile_cont(0.25) WITHIN GROUP (ORDER BY pbr) as pbr_p25,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY pbr) as pbr_p50,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY pbr) as pbr_p75,
                percentile_cont(0.90) WITHIN GROUP (ORDER BY pbr) as pbr_p90,
                AVG(pbr) as pbr_mean,
                -- ROE
                percentile_cont(0.10) WITHIN GROUP (ORDER BY roe) as roe_p10,
                percentile_cont(0.25) WITHIN GROUP (ORDER BY roe) as roe_p25,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY roe) as roe_p50,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY roe) as roe_p75,
                percentile_cont(0.90) WITHIN GROUP (ORDER BY roe) as roe_p90,
                AVG(roe) as roe_mean
            FROM stock_snapshots
            WHERE date = ?
            GROUP BY sector_normalized
            HAVING sample_size >= 30
        """
        
        df = pd.read_sql_query(query, conn, params=(target_date,))
        
        # sector_stats 테이블에 저장
        for _, row in df.iterrows():
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sector_stats 
                (sector, date, sample_size,
                 per_p10, per_p25, per_p50, per_p75, per_p90, per_mean, per_std,
                 pbr_p10, pbr_p25, pbr_p50, pbr_p75, pbr_p90, pbr_mean, pbr_std,
                 roe_p10, roe_p25, roe_p50, roe_p75, roe_p90, roe_mean, roe_std)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sector, date) DO UPDATE SET
                    sample_size = excluded.sample_size,
                    per_p50 = excluded.per_p50,
                    updated_at = CURRENT_TIMESTAMP
            """, tuple(row))
        
        conn.commit()
        conn.close()
        
        # Dict 형식으로 반환 (기존 캐시 형식 호환)
        return df.set_index('sector_normalized').to_dict('index')
    
    def get_sector_stats(self, target_date: date = None) -> Dict[str, Dict]:
        """섹터 통계 조회 (프리컴퓨팅된 것)"""
        if target_date is None:
            target_date = date.today()
        
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT * FROM sector_stats WHERE date = ?",
            conn, params=(target_date,)
        )
        conn.close()
        
        if df.empty:
            # 없으면 계산
            return self.compute_sector_stats(target_date)
        
        return df.set_index('sector').to_dict('index')
```

---

## 🔄 증분 업데이트 전략

### 매일 업데이트 프로세스
```python
def daily_update():
    """매일 증분 업데이트 (스케줄러)"""
    db = DBCacheManager()
    
    # 1. 업데이트 필요한 종목 확인
    stale_stocks = db.get_stale_stocks(max_age_days=1)
    
    logger.info(f"📊 증분 업데이트: {len(stale_stocks)}개 종목")
    
    # 2. API 호출 (최소화)
    updated_data = []
    for code in stale_stocks:
        data = kis_api.get_stock_data(code)  # 1번 API 호출
        updated_data.append(data)
    
    # 3. DB 저장
    db.save_snapshots(updated_data)
    
    # 4. 섹터 통계 재계산
    db.compute_sector_stats()
    
    logger.info(f"✅ 증분 업데이트 완료: {len(stale_stocks)}개")
```

### 스케줄링
```python
# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# 매일 장마감 후 (15:40)
scheduler.add_job(
    daily_update,
    trigger='cron',
    hour=15,
    minute=40,
    day_of_week='mon-fri'
)

scheduler.start()
```

---

## 📈 추가 이점

### 1. 백테스트 지원
```python
# 과거 특정 날짜의 섹터 통계 조회 가능
stats_20240101 = db.get_sector_stats(date(2024, 1, 1))
stats_20240201 = db.get_sector_stats(date(2024, 2, 1))

# → P3-1: 백테스트 데이터 파이프라인과 완벽 연동!
```

### 2. 시계열 분석
```sql
-- 섹터 PER 추이 (6개월)
SELECT sector, date, per_p50
FROM sector_stats
WHERE sector = '전기전자'
  AND date >= date('now', '-6 months')
ORDER BY date
```

### 3. 데이터 품질 모니터링
```sql
-- 최근 7일간 수집 현황
SELECT date, COUNT(*) as stocks_count
FROM stock_snapshots
WHERE date >= date('now', '-7 days')
GROUP BY date
ORDER BY date DESC
```

---

## 🚀 구현 로드맵

### Phase 1: 기본 DB 전환 (1~2일)
- [x] SQLite 스키마 설계
- [ ] DBCacheManager 구현
- [ ] 기존 pickle 캐시와 병행 운영
- [ ] 테스트 및 검증

### Phase 2: 증분 업데이트 (1일)
- [ ] get_stale_stocks 구현
- [ ] 증분 업데이트 로직
- [ ] 스케줄러 통합

### Phase 3: 고도화 (1~2일)
- [ ] 백테스트 지원
- [ ] 이력 관리
- [ ] 데이터 품질 대시보드
- [ ] PostgreSQL 마이그레이션 (선택)

---

## 💰 비용 절감 효과

### API 호출 비교
```
Pickle (현재):
  월 30,000번 (매일 1000번 × 30일)

DB + 증분 (제안):
  최초: 1,000번 (1회만)
  이후: 50~100번/일 × 30일 = 1,500~3,000번/월
  
절감: 27,000~28,500번/월 (90~95% ↓)
```

### 성능 개선
```
캐시 로드:
  Pickle: ~100ms (파일 I/O)
  SQLite: ~10ms (인덱스 쿼리)
  → 10배 빠름! ⚡
```

---

## 🎯 결론

**강력 추천!** ✅

1. **비용**: 90% 절감
2. **성능**: 10배 향상
3. **기능**: 백테스트, 이력 관리, 시계열 분석
4. **확장성**: PostgreSQL 마이그레이션 가능
5. **투자**: 3~5일 구현

**즉시 시작 가능한가요?** 🚀

---

**작성**: 2025-10-12  
**관련 태스크**: P2-6 (캐시 계층화), P3-1 (백테스트 파이프라인)  
**우선순위**: HIGH

