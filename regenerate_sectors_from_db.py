#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB 스냅샷으로부터 섹터 통계 재계산 (현재 정규화 로직 사용)"""

import logging
import pickle
from datetime import date
from pathlib import Path
from db_cache_manager import DBCacheManager
from value_stock_finder import ValueStockFinder

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

def regenerate_sectors():
    """DB 스냅샷으로부터 섹터 통계 재생성"""
    
    print("=" * 60)
    print("섹터 통계 재생성 (현재 정규화 로직)")
    print("=" * 60)
    
    # 1. DB에서 최신 스냅샷 조회
    print("\n[1단계] DB 스냅샷 조회")
    db = DBCacheManager()
    snapshots = db.get_snapshot_by_date(date.today())
    
    if snapshots.empty:
        print("  [ERROR] DB 스냅샷 없음")
        return
    
    print(f"  [OK] {len(snapshots)}개 종목 로드")
    
    # 2. ValueStockFinder로 섹터 재정규화
    print("\n[2단계] 섹터 재정규화 (현재 로직)")
    vf = ValueStockFinder()
    
    sector_groups = {}
    
    for _, row in snapshots.iterrows():
        code = row['stock_code']
        raw_sector = row['sector']
        
        # 현재 정규화 로직 적용
        normalized = vf._normalize_sector_name(raw_sector)
        
        if normalized not in sector_groups:
            sector_groups[normalized] = []
        
        sector_groups[normalized].append({
            'per': row['per'],
            'pbr': row['pbr'],
            'roe': row['roe'],
        })
    
    print(f"  [OK] {len(sector_groups)}개 섹터 발견")
    for sector in sector_groups.keys():
        print(f"    - {sector} (n={len(sector_groups[sector])})")
    
    # 3. 섹터 통계 계산
    print("\n[3단계] 섹터 통계 계산")
    
    import numpy as np
    
    sector_stats = {}
    
    for sector, stocks in sector_groups.items():
        n = len(stocks)
        
        if n < 30:
            print(f"  [SKIP] {sector}: n={n} < 30")
            continue
        
        # PER, PBR, ROE 추출
        per_values = [s['per'] for s in stocks if s.get('per') and s['per'] > 0]
        pbr_values = [s['pbr'] for s in stocks if s.get('pbr') and s['pbr'] > 0]
        roe_values = [s['roe'] for s in stocks if s.get('roe')]
        
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
        
        sector_stats[sector] = {
            'sample_size': n,
            'per_percentiles': calc_percentiles(per_values),
            'pbr_percentiles': calc_percentiles(pbr_values),
            'roe_percentiles': calc_percentiles(roe_values),
            'timestamp': date.today().isoformat()
        }
        
        print(f"  [OK] {sector} (n={n})")
    
    # 4. pickle 캐시 저장
    print("\n[4단계] pickle 캐시 저장")
    cache_dir = Path('cache')
    cache_dir.mkdir(exist_ok=True)
    
    with open(cache_dir / 'sector_stats.pkl', 'wb') as f:
        pickle.dump(sector_stats, f)
    
    print(f"  [OK] {len(sector_stats)}개 섹터 저장")
    
    # 5. DB에도 저장
    print("\n[5단계] DB 저장")
    
    import sqlite3
    conn = sqlite3.connect(str(db.db_path))
    cursor = conn.cursor()
    
    # 기존 데이터 삭제
    cursor.execute("DELETE FROM sector_stats WHERE snapshot_date = ?", (date.today(),))
    
    for sector, stats in sector_stats.items():
        n = stats['sample_size']
        per_pct = stats['per_percentiles']
        pbr_pct = stats['pbr_percentiles']
        roe_pct = stats['roe_percentiles']
        
        cursor.execute("""
            INSERT INTO sector_stats (
                sector, snapshot_date, sample_size,
                per_p10, per_p25, per_p50, per_p75, per_p90, per_mean, per_std, per_min, per_max,
                pbr_p10, pbr_p25, pbr_p50, pbr_p75, pbr_p90, pbr_mean, pbr_std, pbr_min, pbr_max,
                roe_p10, roe_p25, roe_p50, roe_p75, roe_p90, roe_mean, roe_std, roe_min, roe_max
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sector, date.today(), n,
            per_pct.get('p10'), per_pct.get('p25'), per_pct.get('p50'), per_pct.get('p75'), per_pct.get('p90'),
            per_pct.get('mean'), per_pct.get('std'), per_pct.get('min'), per_pct.get('max'),
            pbr_pct.get('p10'), pbr_pct.get('p25'), pbr_pct.get('p50'), pbr_pct.get('p75'), pbr_pct.get('p90'),
            pbr_pct.get('mean'), pbr_pct.get('std'), pbr_pct.get('min'), pbr_pct.get('max'),
            roe_pct.get('p10'), roe_pct.get('p25'), roe_pct.get('p50'), roe_pct.get('p75'), roe_pct.get('p90'),
            roe_pct.get('mean'), roe_pct.get('std'), roe_pct.get('min'), roe_pct.get('max')
        ))
    
    conn.commit()
    conn.close()
    
    print(f"  [OK] DB 저장 완료")
    
    # 6. 검증
    print("\n[6단계] 검증")
    loaded_stats = db.get_sector_stats()
    print(f"  [OK] {len(loaded_stats)}개 섹터 조회")
    
    for sector, stats in loaded_stats.items():
        n = stats['sample_size']
        per_p50 = stats['per_percentiles'].get('p50', 0)
        print(f"    {sector:20s} -> n={n:3d}, PER={per_p50:6.1f}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] 섹터 통계 재생성 완료!")
    print("=" * 60)
    print("\n다음: Streamlit 재시작")
    print("  streamlit run value_stock_finder.py")
    print()


if __name__ == "__main__":
    try:
        regenerate_sectors()
    except Exception as e:
        logger.error(f"[FAIL] 재생성 실패: {e}")
        import traceback
        traceback.print_exc()

