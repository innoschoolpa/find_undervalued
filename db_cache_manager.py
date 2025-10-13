#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB 기반 캐시 매니저 v1.0

목적:
- 일별 시세 데이터 누적 저장
- 섹터 통계 프리컴퓨팅
- 백테스트 데이터 파이프라인 지원

장점:
- API 호출 90% 절감 (증분 업데이트)
- 영구 저장 + 이력 관리
- 빠른 조회 (인덱스)
"""

import sqlite3
import logging
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DBCacheManager:
    """DB 기반 캐시 매니저 (SQLite)"""
    
    def __init__(self, db_path: str = 'cache/stock_data.db'):
        """
        Args:
            db_path: DB 파일 경로
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        logger.info(f"✅ DBCacheManager 초기화: {self.db_path}")
    
    def _init_db(self):
        """DB 초기화 (스키마 적용)"""
        schema_file = Path('db_schema.sql')
        
        if not schema_file.exists():
            logger.warning(f"⚠️ 스키마 파일 없음: {schema_file}")
            return
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.executescript(schema_sql)
            conn.commit()
            logger.info("✅ DB 스키마 적용 완료")
        except Exception as e:
            logger.error(f"❌ DB 스키마 적용 실패: {e}")
            raise
        finally:
            conn.close()
    
    @contextmanager
    def get_connection(self):
        """DB 커넥션 컨텍스트 매니저"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 반환
        try:
            yield conn
        finally:
            conn.close()
    
    # ============================================
    # 스냅샷 관리
    # ============================================
    
    def save_snapshots(self, snapshots: List[Dict[str, Any]], snapshot_date: date = None):
        """
        일별 시세 스냅샷 저장 (UPSERT)
        
        Args:
            snapshots: 종목 데이터 리스트
            snapshot_date: 스냅샷 날짜 (None이면 오늘)
        """
        if not snapshots:
            logger.warning("⚠️ 저장할 스냅샷 없음")
            return 0
        
        if snapshot_date is None:
            snapshot_date = date.today()
        
        saved_count = 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for snap in snapshots:
                try:
                    cursor.execute("""
                        INSERT INTO stock_snapshots (
                            stock_code, snapshot_date, name, sector, sector_normalized,
                            open_price, high_price, low_price, close_price, volume,
                            market_cap, per, pbr, roe, debt_ratio,
                            dividend_yield, data_source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(stock_code, snapshot_date) DO UPDATE SET
                            close_price = excluded.close_price,
                            per = excluded.per,
                            pbr = excluded.pbr,
                            roe = excluded.roe,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        snap.get('code'),
                        snapshot_date,
                        snap.get('name'),
                        snap.get('sector'),
                        snap.get('sector_normalized'),
                        snap.get('open_price'),
                        snap.get('high_price'),
                        snap.get('low_price'),
                        snap.get('price') or snap.get('close_price'),
                        snap.get('volume'),
                        snap.get('market_cap'),
                        snap.get('per'),
                        snap.get('pbr'),
                        snap.get('roe'),
                        snap.get('debt_ratio'),
                        snap.get('dividend_yield'),
                        snap.get('data_source', 'KIS')
                    ))
                    saved_count += 1
                
                except Exception as e:
                    logger.error(f"❌ 스냅샷 저장 실패 ({snap.get('code')}): {e}")
                    continue
            
            conn.commit()
        
        logger.info(f"✅ 스냅샷 저장: {saved_count}/{len(snapshots)}개")
        return saved_count
    
    def get_latest_snapshots(self, max_age_days: int = 1) -> pd.DataFrame:
        """
        최신 스냅샷 조회
        
        Args:
            max_age_days: 최대 경과 일수
        
        Returns:
            DataFrame
        """
        cutoff_date = date.today() - timedelta(days=max_age_days)
        
        query = """
            SELECT * FROM stock_snapshots
            WHERE snapshot_date >= ?
            ORDER BY snapshot_date DESC, stock_code
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(cutoff_date,))
        
        logger.debug(f"📊 최신 스냅샷 조회: {len(df)}개 (cutoff: {cutoff_date})")
        return df
    
    def get_snapshot_by_date(self, snapshot_date: date) -> pd.DataFrame:
        """
        특정 날짜의 스냅샷 조회
        
        Args:
            snapshot_date: 날짜
        
        Returns:
            DataFrame
        """
        query = """
            SELECT * FROM stock_snapshots
            WHERE snapshot_date = ?
            ORDER BY stock_code
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(snapshot_date,))
        
        logger.debug(f"📊 {snapshot_date} 스냅샷 조회: {len(df)}개")
        return df
    
    def get_stock_history(self, stock_code: str, days: int = 90) -> pd.DataFrame:
        """
        종목별 시세 이력 조회
        
        Args:
            stock_code: 종목코드
            days: 조회 일수
        
        Returns:
            DataFrame (날짜 내림차순)
        """
        query = """
            SELECT 
                snapshot_date as date,
                close_price as price,
                open_price, high_price, low_price, volume,
                per, pbr, roe, market_cap
            FROM stock_snapshots
            WHERE stock_code = ?
            ORDER BY snapshot_date DESC
            LIMIT ?
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(stock_code, days))
        
        logger.debug(f"📊 {stock_code} 이력 조회: {len(df)}일")
        return df
    
    def get_stale_stocks(self, max_age_days: int = 1) -> List[str]:
        """
        업데이트 필요한 종목 리스트 (증분 업데이트용)
        
        Args:
            max_age_days: 최대 경과 일수
        
        Returns:
            종목코드 리스트
        """
        cutoff_date = date.today() - timedelta(days=max_age_days)
        
        # 최근 업데이트된 종목
        query = """
            SELECT DISTINCT stock_code
            FROM stock_snapshots
            WHERE snapshot_date >= ?
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(cutoff_date,))
            recent_codes = set(df['stock_code'].tolist())
        
        # 전체 종목은 stock_master에서 가져오거나 외부 API 사용
        # 여기서는 간단히 최근 7일 내 등장한 종목을 전체로 가정
        query_all = """
            SELECT DISTINCT stock_code
            FROM stock_snapshots
            WHERE snapshot_date >= ?
        """
        
        with self.get_connection() as conn:
            df_all = pd.read_sql_query(query_all, conn, params=(date.today() - timedelta(days=7),))
            all_codes = set(df_all['stock_code'].tolist())
        
        stale_codes = all_codes - recent_codes
        
        logger.info(f"📊 증분 업데이트 대상: {len(stale_codes)}개 (전체: {len(all_codes)})")
        return list(stale_codes)
    
    # ============================================
    # 섹터 통계
    # ============================================
    
    def compute_sector_stats(self, snapshot_date: date = None) -> Dict[str, Dict]:
        """
        섹터 통계 계산 및 저장
        
        Args:
            snapshot_date: 기준 날짜 (None이면 오늘)
        
        Returns:
            섹터별 통계 딕셔너리
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        logger.info(f"📊 섹터 통계 계산 시작: {snapshot_date}")
        
        # 해당 날짜의 스냅샷 조회
        df = self.get_snapshot_by_date(snapshot_date)
        
        if df.empty:
            logger.warning(f"⚠️ {snapshot_date} 스냅샷 없음")
            return {}
        
        # 섹터별 그룹화
        sector_groups = df.groupby('sector_normalized')
        
        sector_stats = {}
        saved_count = 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for sector, group in sector_groups:
                if sector is None or pd.isna(sector):
                    continue
                
                n = len(group)
                
                # 최소 표본 크기 확인 (v2.3: 30 → 5)
                # - n < 5: 극소 표본, 저장 안 함
                # - 5 ≤ n < 10: 저장 → 사용 시 글로벌만
                # - 10 ≤ n < 30: 저장 → 사용 시 가중 평균
                # - n ≥ 30: 저장 → 사용 시 섹터 우선
                if n < 5:
                    logger.debug(f"⚠️ {sector}: 극소 표본 (n={n}) - 저장 안 함")
                    continue
                
                if n < 10:
                    logger.info(f"📌 {sector}: 소표본 저장 (n={n}) - 글로벌 대체 예정")
                elif n < 30:
                    logger.info(f"📌 {sector}: 중표본 저장 (n={n}) - 가중 평균 예정")
                
                # PER, PBR, ROE 추출 (유효값만)
                per_values = group['per'].dropna().values
                pbr_values = group['pbr'].dropna().values
                roe_values = group['roe'].dropna().values
                
                # 퍼센타일 계산
                def calc_percentiles(values):
                    if len(values) == 0:
                        return {}
                    return {
                        'p10': np.percentile(values, 10),
                        'p25': np.percentile(values, 25),
                        'p50': np.percentile(values, 50),
                        'p75': np.percentile(values, 75),
                        'p90': np.percentile(values, 90),
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'min': np.min(values),
                        'max': np.max(values),
                    }
                
                per_pct = calc_percentiles(per_values)
                pbr_pct = calc_percentiles(pbr_values)
                roe_pct = calc_percentiles(roe_values)
                
                # DB 저장
                try:
                    cursor.execute("""
                        INSERT INTO sector_stats (
                            sector, snapshot_date, sample_size,
                            per_p10, per_p25, per_p50, per_p75, per_p90, per_mean, per_std, per_min, per_max,
                            pbr_p10, pbr_p25, pbr_p50, pbr_p75, pbr_p90, pbr_mean, pbr_std, pbr_min, pbr_max,
                            roe_p10, roe_p25, roe_p50, roe_p75, roe_p90, roe_mean, roe_std, roe_min, roe_max
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(sector, snapshot_date) DO UPDATE SET
                            sample_size = excluded.sample_size,
                            per_p50 = excluded.per_p50,
                            pbr_p50 = excluded.pbr_p50,
                            roe_p50 = excluded.roe_p50
                    """, (
                        sector, snapshot_date, n,
                        per_pct.get('p10'), per_pct.get('p25'), per_pct.get('p50'), per_pct.get('p75'), per_pct.get('p90'),
                        per_pct.get('mean'), per_pct.get('std'), per_pct.get('min'), per_pct.get('max'),
                        pbr_pct.get('p10'), pbr_pct.get('p25'), pbr_pct.get('p50'), pbr_pct.get('p75'), pbr_pct.get('p90'),
                        pbr_pct.get('mean'), pbr_pct.get('std'), pbr_pct.get('min'), pbr_pct.get('max'),
                        roe_pct.get('p10'), roe_pct.get('p25'), roe_pct.get('p50'), roe_pct.get('p75'), roe_pct.get('p90'),
                        roe_pct.get('mean'), roe_pct.get('std'), roe_pct.get('min'), roe_pct.get('max')
                    ))
                    
                    saved_count += 1
                    
                    # 반환용 딕셔너리 (기존 캐시 형식 호환)
                    sector_stats[sector] = {
                        'sample_size': n,
                        'per_percentiles': per_pct,
                        'pbr_percentiles': pbr_pct,
                        'roe_percentiles': roe_pct,
                        'timestamp': datetime.now().isoformat()
                    }
                
                except Exception as e:
                    logger.error(f"❌ 섹터 통계 저장 실패 ({sector}): {e}")
                    continue
            
            conn.commit()
        
        logger.info(f"✅ 섹터 통계 계산 완료: {saved_count}개 섹터")
        return sector_stats
    
    def get_sector_stats(self, snapshot_date: date = None) -> Dict[str, Dict]:
        """
        섹터 통계 조회 (프리컴퓨팅된 것)
        
        Args:
            snapshot_date: 기준 날짜 (None이면 최신)
        
        Returns:
            섹터별 통계 딕셔너리 (기존 pickle 캐시 형식 호환)
        """
        if snapshot_date is None:
            # 최신 날짜 조회
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(snapshot_date) FROM sector_stats")
                result = cursor.fetchone()
                if result and result[0]:
                    snapshot_date = result[0]
                else:
                    logger.warning("⚠️ 섹터 통계 없음")
                    return {}
        
        query = """
            SELECT * FROM sector_stats
            WHERE snapshot_date = ?
        """
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(snapshot_date,))
        
        if df.empty:
            logger.warning(f"⚠️ {snapshot_date} 섹터 통계 없음")
            return {}
        
        # 기존 캐시 형식으로 변환
        sector_stats = {}
        for _, row in df.iterrows():
            sector = row['sector']
            sector_stats[sector] = {
                'sample_size': row['sample_size'],
                'per_percentiles': {
                    'p10': row['per_p10'], 'p25': row['per_p25'], 'p50': row['per_p50'],
                    'p75': row['per_p75'], 'p90': row['per_p90'],
                    'mean': row['per_mean'], 'std': row['per_std'],
                    'min': row['per_min'], 'max': row['per_max']
                },
                'pbr_percentiles': {
                    'p10': row['pbr_p10'], 'p25': row['pbr_p25'], 'p50': row['pbr_p50'],
                    'p75': row['pbr_p75'], 'p90': row['pbr_p90'],
                    'mean': row['pbr_mean'], 'std': row['pbr_std'],
                    'min': row['pbr_min'], 'max': row['pbr_max']
                },
                'roe_percentiles': {
                    'p10': row['roe_p10'], 'p25': row['roe_p25'], 'p50': row['roe_p50'],
                    'p75': row['roe_p75'], 'p90': row['roe_p90'],
                    'mean': row['roe_mean'], 'std': row['roe_std'],
                    'min': row['roe_min'], 'max': row['roe_max']
                },
                'timestamp': str(snapshot_date) if snapshot_date else datetime.now().isoformat()
            }
        
        logger.info(f"✅ 섹터 통계 조회: {len(sector_stats)}개 ({snapshot_date})")
        return sector_stats
    
    # ============================================
    # 유틸리티
    # ============================================
    
    def get_stats(self) -> Dict[str, Any]:
        """DB 통계 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 스냅샷 통계
            cursor.execute("SELECT COUNT(*) FROM stock_snapshots")
            total_snapshots = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_snapshots")
            unique_stocks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT snapshot_date) FROM stock_snapshots")
            unique_dates = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(snapshot_date), MAX(snapshot_date) FROM stock_snapshots")
            date_range = cursor.fetchone()
            
            # 섹터 통계
            cursor.execute("SELECT COUNT(DISTINCT sector) FROM sector_stats")
            unique_sectors = cursor.fetchone()[0]
            
            # 최신 날짜
            cursor.execute("SELECT MAX(snapshot_date) FROM stock_snapshots")
            latest_date = cursor.fetchone()[0]
        
        return {
            'total_snapshots': total_snapshots,
            'unique_stocks': unique_stocks,
            'unique_dates': unique_dates,
            'date_range': date_range,
            'unique_sectors': unique_sectors,
            'latest_date': latest_date,
            'db_size_mb': self.db_path.stat().st_size / 1024 / 1024 if self.db_path.exists() else 0
        }
    
    def cleanup_old_data(self, keep_days: int = 365):
        """
        오래된 데이터 정리
        
        Args:
            keep_days: 보관 일수 (기본 1년)
        """
        cutoff_date = date.today() - timedelta(days=keep_days)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 스냅샷 삭제
            cursor.execute("DELETE FROM stock_snapshots WHERE snapshot_date < ?", (cutoff_date,))
            deleted_snapshots = cursor.rowcount
            
            # 섹터 통계 삭제
            cursor.execute("DELETE FROM sector_stats WHERE snapshot_date < ?", (cutoff_date,))
            deleted_stats = cursor.rowcount
            
            conn.commit()
        
        logger.info(f"✅ 오래된 데이터 정리: 스냅샷 {deleted_snapshots}개, 통계 {deleted_stats}개")
        return deleted_snapshots, deleted_stats


# ============================================
# 전역 인스턴스 (싱글톤)
# ============================================
_global_db_cache: Optional[DBCacheManager] = None

def get_db_cache() -> DBCacheManager:
    """전역 DB 캐시 반환 (싱글톤)"""
    global _global_db_cache
    
    if _global_db_cache is None:
        _global_db_cache = DBCacheManager()
    
    return _global_db_cache

