-- ============================================
-- 주식 데이터 캐시 DB 스키마
-- ============================================
-- 버전: 1.0
-- 날짜: 2025-10-12
-- 목적: 일별 시세 누적 저장 + 섹터 통계 캐싱
-- ============================================

-- 종목 마스터 (기본 정보)
CREATE TABLE IF NOT EXISTS stock_master (
    stock_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    market TEXT,                    -- KOSPI, KOSDAQ, KONEX
    sector TEXT,                    -- 원본 섹터명
    sector_normalized TEXT,         -- 정규화된 섹터명
    listed_date DATE,               -- 상장일
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_sector ON stock_master(sector_normalized);

-- 일별 시세 스냅샷 (핵심 테이블)
CREATE TABLE IF NOT EXISTS stock_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    
    -- 기본 정보
    name TEXT,
    sector TEXT,
    sector_normalized TEXT,
    
    -- OHLCV (시가/고가/저가/종가/거래량)
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,               -- 종가 (현재가)
    volume INTEGER,
    trading_value REAL,             -- 거래대금
    
    -- 시가총액
    market_cap REAL,
    shares_outstanding INTEGER,     -- 발행주식수
    
    -- 밸류에이션 지표
    per REAL,
    pbr REAL,
    pcr REAL,                       -- Price to Cash Flow Ratio
    psr REAL,                       -- Price to Sales Ratio
    
    -- 재무 지표
    roe REAL,
    roa REAL,
    debt_ratio REAL,
    current_ratio REAL,             -- 유동비율
    quick_ratio REAL,               -- 당좌비율
    
    -- 수익성 지표
    operating_margin REAL,          -- 영업이익률
    net_margin REAL,                -- 순이익률
    
    -- 배당
    dividend_yield REAL,
    
    -- 메타 정보
    data_source TEXT DEFAULT 'KIS', -- KIS, DART, etc.
    data_quality TEXT,              -- A, B, C, D
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_code, snapshot_date)
);

-- 인덱스 (조회 성능 최적화)
CREATE INDEX IF NOT EXISTS idx_snapshot_date ON stock_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_snapshot_code_date ON stock_snapshots(stock_code, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_snapshot_sector_date ON stock_snapshots(sector_normalized, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_snapshot_per ON stock_snapshots(per);
CREATE INDEX IF NOT EXISTS idx_snapshot_pbr ON stock_snapshots(pbr);

-- 섹터 통계 (프리컴퓨팅 - 빠른 조회)
CREATE TABLE IF NOT EXISTS sector_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    
    sample_size INTEGER NOT NULL,
    
    -- PER 통계
    per_p10 REAL,
    per_p25 REAL,
    per_p50 REAL,
    per_p75 REAL,
    per_p90 REAL,
    per_mean REAL,
    per_std REAL,
    per_min REAL,
    per_max REAL,
    
    -- PBR 통계
    pbr_p10 REAL,
    pbr_p25 REAL,
    pbr_p50 REAL,
    pbr_p75 REAL,
    pbr_p90 REAL,
    pbr_mean REAL,
    pbr_std REAL,
    pbr_min REAL,
    pbr_max REAL,
    
    -- ROE 통계
    roe_p10 REAL,
    roe_p25 REAL,
    roe_p50 REAL,
    roe_p75 REAL,
    roe_p90 REAL,
    roe_mean REAL,
    roe_std REAL,
    roe_min REAL,
    roe_max REAL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(sector, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_sector_stats_date ON sector_stats(sector, snapshot_date);

-- 포트폴리오 (사용자 포트폴리오 추적)
CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_name TEXT NOT NULL DEFAULT 'default',
    stock_code TEXT NOT NULL,
    
    shares INTEGER NOT NULL,        -- 보유 수량
    avg_buy_price REAL NOT NULL,    -- 평균 매수가
    buy_date DATE NOT NULL,         -- 최초 매수일
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(portfolio_name, stock_code)
);

-- 거래 이력 (매수/매도 기록)
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_name TEXT NOT NULL DEFAULT 'default',
    stock_code TEXT NOT NULL,
    
    transaction_type TEXT NOT NULL, -- BUY, SELL
    transaction_date DATE NOT NULL,
    
    shares INTEGER NOT NULL,
    price REAL NOT NULL,
    commission REAL DEFAULT 0,      -- 수수료
    tax REAL DEFAULT 0,             -- 세금
    
    note TEXT,                      -- 거래 메모
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_portfolio ON transactions(portfolio_name, transaction_date);

-- 스크리닝 결과 히스토리 (일별 스크리닝 결과 저장)
CREATE TABLE IF NOT EXISTS screening_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screening_date DATE NOT NULL,
    
    stock_code TEXT NOT NULL,
    stock_name TEXT,
    
    -- 점수
    value_score REAL,
    quality_score REAL,
    mos_score REAL,
    total_score REAL,
    
    -- 평가
    rating TEXT,                    -- STRONG_BUY, BUY, HOLD, SELL
    
    -- 주요 지표
    per REAL,
    pbr REAL,
    roe REAL,
    price REAL,
    
    -- 섹터
    sector TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(screening_date, stock_code)
);

CREATE INDEX IF NOT EXISTS idx_screening_date ON screening_results(screening_date);
CREATE INDEX IF NOT EXISTS idx_screening_rating ON screening_results(rating);

-- 데이터 수집 로그 (수집 이력 추적)
CREATE TABLE IF NOT EXISTS collection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_date DATE NOT NULL,
    
    stocks_attempted INTEGER,       -- 시도한 종목 수
    stocks_succeeded INTEGER,       -- 성공한 종목 수
    stocks_failed INTEGER,          -- 실패한 종목 수
    
    api_calls INTEGER,              -- API 호출 수
    duration_seconds REAL,          -- 소요 시간
    
    error_message TEXT,             -- 오류 메시지
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_collection_date ON collection_log(collection_date);

-- ============================================
-- 뷰 (편의 조회)
-- ============================================

-- 최신 스냅샷 뷰
CREATE VIEW IF NOT EXISTS v_latest_snapshots AS
SELECT 
    s.*,
    (SELECT snapshot_date FROM stock_snapshots ORDER BY snapshot_date DESC LIMIT 1) as max_date
FROM stock_snapshots s
WHERE s.snapshot_date = (SELECT MAX(snapshot_date) FROM stock_snapshots)
ORDER BY s.stock_code;

-- 섹터별 최신 통계 뷰
CREATE VIEW IF NOT EXISTS v_latest_sector_stats AS
SELECT *
FROM sector_stats
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM sector_stats)
ORDER BY sector;

-- 포트폴리오 평가 뷰 (최신 시세 기준)
CREATE VIEW IF NOT EXISTS v_portfolio_valuation AS
SELECT 
    p.portfolio_name,
    p.stock_code,
    p.shares,
    p.avg_buy_price,
    p.buy_date,
    s.close_price as current_price,
    s.snapshot_date as price_date,
    (s.close_price * p.shares) as market_value,
    ((s.close_price - p.avg_buy_price) * p.shares) as unrealized_pnl,
    ((s.close_price - p.avg_buy_price) / p.avg_buy_price * 100) as return_pct
FROM portfolio p
LEFT JOIN v_latest_snapshots s ON p.stock_code = s.stock_code
ORDER BY p.portfolio_name, unrealized_pnl DESC;

-- ============================================
-- 초기 데이터 / 설정
-- ============================================

-- 버전 정보 테이블
CREATE TABLE IF NOT EXISTS db_version (
    version TEXT PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT OR IGNORE INTO db_version (version, description) 
VALUES ('1.0.0', 'Initial schema: stock snapshots, sector stats, portfolio tracking');

-- ============================================
-- 정리 (Cleanup) 함수들
-- ============================================

-- 오래된 스냅샷 삭제 (N일 이상 경과)
-- 사용법: DELETE FROM stock_snapshots WHERE snapshot_date < date('now', '-365 days');

-- 고아 레코드 정리
-- DELETE FROM stock_snapshots WHERE stock_code NOT IN (SELECT stock_code FROM stock_master);

