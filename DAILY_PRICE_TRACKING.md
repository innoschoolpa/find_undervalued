# 매일 현재가 누적 기록 시스템

**날짜**: 2025-10-12  
**목적**: 일별 시세 히스토리 구축  
**활용**: 백테스트, 성과 추적, 시계열 분석

---

## ✅ 완벽하게 가능합니다!

DB 설계에 이미 포함되어 있습니다:

```sql
CREATE TABLE stock_snapshots (
    stock_code TEXT NOT NULL,
    date DATE NOT NULL,           -- 📅 날짜
    
    -- 현재가 기록
    price REAL,                   -- 📊 종가 (15:30 기준)
    open_price REAL,              -- 시가
    high_price REAL,              -- 고가
    low_price REAL,               -- 저가
    volume INTEGER,               -- 거래량
    
    -- 재무지표 (스냅샷)
    per REAL,
    pbr REAL,
    roe REAL,
    
    UNIQUE(stock_code, date)      -- 종목당 하루 1개
);
```

---

## 📊 매일 자동 수집 프로세스

### 1. 스케줄러 설정
```python
# daily_collector.py

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date
import logging

logger = logging.getLogger(__name__)

def collect_daily_prices():
    """매일 장마감 후 현재가 수집 및 저장"""
    
    logger.info(f"📊 일별 시세 수집 시작: {date.today()}")
    
    db = DBCacheManager()
    
    # 1. 전체 종목 리스트 (또는 관심 종목)
    stock_codes = get_target_stocks()  # 1000~2000개
    
    # 2. 증분 업데이트: 오늘 아직 수집 안 된 종목만
    existing = db.get_today_collected_stocks()
    to_collect = [code for code in stock_codes if code not in existing]
    
    logger.info(f"  수집 대상: {len(to_collect)}개 (전체: {len(stock_codes)})")
    
    # 3. API 호출 (배치 처리)
    snapshots = []
    for i, code in enumerate(to_collect):
        try:
            # KIS API 호출
            data = kis_api.get_current_price(code)
            
            snapshot = {
                'stock_code': code,
                'date': date.today(),
                'price': data['current_price'],
                'open_price': data['open'],
                'high_price': data['high'],
                'low_price': data['low'],
                'volume': data['volume'],
                'per': data.get('per'),
                'pbr': data.get('pbr'),
                'roe': data.get('roe'),
                'market_cap': data.get('market_cap'),
                'sector': data.get('sector'),
            }
            
            snapshots.append(snapshot)
            
            # 100개마다 중간 저장 (안전성)
            if len(snapshots) >= 100:
                db.save_snapshots(snapshots)
                logger.info(f"  진행: {i+1}/{len(to_collect)} (중간저장)")
                snapshots = []
        
        except Exception as e:
            logger.error(f"  ❌ {code} 수집 실패: {e}")
            continue
    
    # 4. 최종 저장
    if snapshots:
        db.save_snapshots(snapshots)
    
    logger.info(f"✅ 일별 시세 수집 완료: {len(to_collect)}개")
    
    # 5. 섹터 통계 재계산
    db.compute_sector_stats()
    logger.info("✅ 섹터 통계 업데이트 완료")


# 스케줄러 설정
scheduler = BackgroundScheduler()

# 방법 1: 매일 장마감 후 (15:40)
scheduler.add_job(
    collect_daily_prices,
    trigger='cron',
    hour=15,
    minute=40,
    day_of_week='mon-fri',
    id='daily_price_collection'
)

# 방법 2: 하루 여러 번 (실시간 모니터링용)
# scheduler.add_job(
#     collect_daily_prices,
#     trigger='cron',
#     hour='9,12,15',  # 장 시작, 점심, 장마감
#     minute=0,
#     day_of_week='mon-fri'
# )

scheduler.start()
logger.info("✅ 일별 시세 수집 스케줄러 시작 (매일 15:40)")
```

---

## 📈 활용 사례

### 1. 종목별 시세 이력 조회
```python
def get_price_history(stock_code: str, days: int = 90):
    """특정 종목의 최근 N일 시세"""
    conn = sqlite3.connect('cache/stock_data.db')
    
    query = """
        SELECT date, price, open_price, high_price, low_price, volume
        FROM stock_snapshots
        WHERE stock_code = ?
        ORDER BY date DESC
        LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(stock_code, days))
    conn.close()
    
    return df

# 사용 예
samsung = get_price_history('005930', days=90)
print(samsung.head())

#        date    price  open_price  high_price  low_price    volume
# 0  2025-10-12  75000       74500       75500      74000  12345678
# 1  2025-10-11  74500       74000       75000      73500  11234567
# 2  2025-10-10  74000       73500       74500      73000  10234567
```

### 2. 수익률 계산
```python
def calculate_returns(stock_code: str, buy_date: str, sell_date: str = None):
    """특정 기간 수익률"""
    if sell_date is None:
        sell_date = date.today().isoformat()
    
    conn = sqlite3.connect('cache/stock_data.db')
    
    query = """
        SELECT date, price
        FROM stock_snapshots
        WHERE stock_code = ?
          AND date IN (?, ?)
        ORDER BY date
    """
    
    df = pd.read_sql_query(query, conn, params=(stock_code, buy_date, sell_date))
    
    if len(df) == 2:
        buy_price = df.iloc[0]['price']
        sell_price = df.iloc[1]['price']
        return_pct = (sell_price - buy_price) / buy_price * 100
        
        return {
            'buy_date': buy_date,
            'buy_price': buy_price,
            'sell_date': sell_date,
            'sell_price': sell_price,
            'return_pct': return_pct,
            'profit': sell_price - buy_price
        }
    
    return None

# 사용 예
result = calculate_returns('005930', '2025-01-01', '2025-10-12')
print(f"수익률: {result['return_pct']:.2f}%")
```

### 3. 포트폴리오 성과 추적
```python
def track_portfolio_performance(portfolio: Dict[str, Dict]):
    """
    포트폴리오 일별 평가액 추적
    
    Args:
        portfolio: {
            '005930': {'shares': 100, 'buy_date': '2025-01-01'},
            '000660': {'shares': 50, 'buy_date': '2025-02-01'},
        }
    """
    conn = sqlite3.connect('cache/stock_data.db')
    
    codes = list(portfolio.keys())
    placeholders = ','.join(['?' for _ in codes])
    
    query = f"""
        SELECT stock_code, date, price
        FROM stock_snapshots
        WHERE stock_code IN ({placeholders})
        ORDER BY date, stock_code
    """
    
    df = pd.read_sql_query(query, conn, params=codes)
    conn.close()
    
    # 일별 평가액 계산
    daily_value = []
    for date_val in df['date'].unique():
        day_data = df[df['date'] == date_val]
        
        total_value = 0
        for _, row in day_data.iterrows():
            code = row['stock_code']
            price = row['price']
            shares = portfolio[code]['shares']
            total_value += price * shares
        
        daily_value.append({
            'date': date_val,
            'total_value': total_value
        })
    
    return pd.DataFrame(daily_value)

# 사용 예
portfolio = {
    '005930': {'shares': 100, 'buy_date': '2025-01-01'},  # 삼성전자
    '000660': {'shares': 50, 'buy_date': '2025-02-01'},   # SK하이닉스
}

performance = track_portfolio_performance(portfolio)
print(performance.tail())

#          date  total_value
# 86  2025-10-08     17500000
# 87  2025-10-09     17650000
# 88  2025-10-10     17550000
# 89  2025-10-11     17700000
# 90  2025-10-12     17850000
```

### 4. 백테스트 지원 (P3-1 연동!)
```python
def backtest_strategy(start_date: str, end_date: str, strategy_func):
    """
    전략 백테스트
    
    - 매일 스냅샷 데이터로 전략 시뮬레이션
    - 과거 데이터만 사용 (미래 정보 누출 방지)
    """
    conn = sqlite3.connect('cache/stock_data.db')
    
    query = """
        SELECT *
        FROM stock_snapshots
        WHERE date BETWEEN ? AND ?
        ORDER BY date, stock_code
    """
    
    snapshots = pd.read_sql_query(query, conn, params=(start_date, end_date))
    conn.close()
    
    # 일별 전략 실행
    portfolio = {}
    trades = []
    
    for date_val in snapshots['date'].unique():
        day_data = snapshots[snapshots['date'] == date_val]
        
        # 전략 실행 (예: 저PER 매수)
        signals = strategy_func(day_data)
        
        for signal in signals:
            if signal['action'] == 'BUY':
                portfolio[signal['code']] = {
                    'buy_price': signal['price'],
                    'buy_date': date_val
                }
                trades.append(signal)
            elif signal['action'] == 'SELL':
                if signal['code'] in portfolio:
                    buy_info = portfolio[signal['code']]
                    profit = signal['price'] - buy_info['buy_price']
                    trades.append({
                        **signal,
                        'profit': profit,
                        'buy_date': buy_info['buy_date']
                    })
                    del portfolio[signal['code']]
    
    return pd.DataFrame(trades)

# 사용 예
def low_per_strategy(day_data):
    """저PER 전략"""
    signals = []
    
    # PER 10 이하 매수
    low_per = day_data[day_data['per'] <= 10].head(5)
    for _, stock in low_per.iterrows():
        signals.append({
            'action': 'BUY',
            'code': stock['stock_code'],
            'price': stock['price'],
            'per': stock['per']
        })
    
    return signals

results = backtest_strategy('2024-01-01', '2024-12-31', low_per_strategy)
print(f"총 거래: {len(results)}건")
print(f"평균 수익률: {results['profit'].mean():.2f}원")
```

### 5. 시계열 분석 및 차트
```python
def plot_price_comparison(stock_codes: List[str], days: int = 90):
    """여러 종목 가격 추이 비교"""
    import matplotlib.pyplot as plt
    
    conn = sqlite3.connect('cache/stock_data.db')
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for code in stock_codes:
        query = """
            SELECT date, price
            FROM stock_snapshots
            WHERE stock_code = ?
            ORDER BY date DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(code, days))
        
        # 정규화 (시작일 = 100)
        df['normalized'] = df['price'] / df['price'].iloc[-1] * 100
        
        ax.plot(df['date'], df['normalized'], label=code)
    
    conn.close()
    
    ax.set_xlabel('Date')
    ax.set_ylabel('Normalized Price (Start = 100)')
    ax.set_title(f'Price Comparison (Last {days} days)')
    ax.legend()
    ax.grid(True)
    
    plt.tight_layout()
    plt.show()

# 사용 예
plot_price_comparison(['005930', '000660', '035420'], days=90)
```

---

## 📅 데이터 저장 예시

### DB 내용 예시
```sql
-- 삼성전자 최근 3일
SELECT * FROM stock_snapshots 
WHERE stock_code = '005930' 
ORDER BY date DESC 
LIMIT 3;

-- 결과:
| stock_code | date       | price | open_price | high_price | low_price | volume   | per  | pbr  | roe  |
|------------|------------|-------|------------|------------|-----------|----------|------|------|------|
| 005930     | 2025-10-12 | 75000 | 74500      | 75500      | 74000     | 12345678 | 12.5 | 1.2  | 9.6  |
| 005930     | 2025-10-11 | 74500 | 74000      | 75000      | 73500     | 11234567 | 12.4 | 1.2  | 9.6  |
| 005930     | 2025-10-10 | 74000 | 73500      | 74500      | 73000     | 10234567 | 12.3 | 1.2  | 9.6  |
```

### 데이터 크기 추정
```
종목 수: 2,000개
거래일: 250일/년
기간: 5년

총 레코드: 2,000 × 250 × 5 = 2,500,000 rows
레코드당 크기: ~150 bytes
총 크기: ~375 MB (5년치)

→ SQLite로 충분히 관리 가능!
→ 10년치도 1GB 미만
```

---

## 🔄 실시간 vs 일별 수집 비교

### 옵션 1: 일 1회 (장마감 후)
```python
# 매일 15:40 한 번만
scheduler.add_job(collect_daily_prices, trigger='cron', hour=15, minute=40)

장점:
✅ API 호출 최소화
✅ 안정적
✅ 관리 간단

단점:
❌ 장중 변동 추적 불가
```

### 옵션 2: 일 3회 (장 시작/점심/마감)
```python
# 09:00, 12:00, 15:40
scheduler.add_job(collect_daily_prices, trigger='cron', hour='9,12,15')

장점:
✅ 장중 변동 추적
✅ 이상 거래 탐지

단점:
❌ API 호출 3배
```

### 옵션 3: 실시간 (1분마다)
```python
# 매분마다 (권장 안 함)
scheduler.add_job(collect_daily_prices, trigger='interval', minutes=1)

장점:
✅ 완전한 실시간 추적

단점:
❌ API 호출 폭발 (390회/일/종목)
❌ Rate Limit 초과 위험
❌ 복잡도 증가
```

**추천: 옵션 1 (일 1회, 장마감)** ✅

---

## 🎯 구현 우선순위

### Phase 1: 기본 수집 (1일)
```
1. ✅ DB 스키마 (stock_snapshots)
2. ✅ 일별 수집 로직 (collect_daily_prices)
3. ✅ 스케줄러 설정 (15:40)
4. ✅ 에러 처리 및 로깅
```

### Phase 2: 조회 기능 (0.5일)
```
1. ✅ 종목별 이력 조회
2. ✅ 수익률 계산
3. ✅ 포트폴리오 추적
```

### Phase 3: 분석 기능 (1일)
```
1. ✅ 백테스트 지원
2. ✅ 시계열 분석
3. ✅ 차트 시각화
```

---

## 💬 즉시 시작 가능!

**DB 설계에 이미 포함되어 있으므로 바로 구현 가능합니다!**

다음 단계:
1. ✅ **지금 바로 구현** (DBCacheManager + 스케줄러)
2. 📋 **설계 검토 후 구현**
3. 🔄 **현재 n=0 문제 먼저 해결**

**어떻게 진행할까요?** 🚀

---

**작성**: 2025-10-12  
**관련 문서**: DB_CACHE_PROPOSAL.md  
**구현 시간**: 1~2일  
**우선순위**: HIGH

