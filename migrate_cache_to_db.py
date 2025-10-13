#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 캐시 데이터를 DB로 마이그레이션

목적:
- 현재 메모리/pickle 캐시의 999개 종목 데이터를 DB에 저장
- 섹터 통계 계산 및 저장
"""

import logging
from datetime import date
from db_cache_manager import DBCacheManager
from value_stock_finder import ValueStockFinder

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

logger = logging.getLogger(__name__)

def migrate_to_db():
    """캐시 데이터를 DB로 마이그레이션"""
    
    print("=" * 60)
    print("캐시 → DB 마이그레이션")
    print("=" * 60)
    
    # 1. 초기화
    print("\n[1단계] 초기화")
    vf = ValueStockFinder()  # 내부에서 자체적으로 data_provider 생성
    db = DBCacheManager()
    
    print("  [OK] 초기화 완료")
    
    # 2. 현재 캐시에서 종목 데이터 조회
    print("\n[2단계] 현재 캐시에서 종목 수집")
    print("  (메모리에 로드된 999개 종목 사용)")
    
    # ValueStockFinder의 get_stock_universe를 사용하여 최신 데이터 조회
    stock_data = vf.get_stock_universe(max_count=1000)
    
    if not stock_data:
        logger.error("❌ 종목 데이터 없음")
        return
    
    print(f"  [OK] {len(stock_data)}개 종목 로드")
    
    # 3. DB 형식으로 변환
    print("\n[3단계] DB 형식으로 변환")
    snapshots = []
    
    for code, data in stock_data.items():
        try:
            # 섹터 정규화
            sector_raw = data.get('sector', '기타')
            sector_normalized = vf._normalize_sector_name(sector_raw)
            
            snapshot = {
                'code': code,
                'name': data.get('name'),
                'sector': sector_raw,
                'sector_normalized': sector_normalized,
                'price': data.get('price') or data.get('close_price'),
                'open_price': data.get('open_price'),
                'high_price': data.get('high_price'),
                'low_price': data.get('low_price'),
                'volume': data.get('volume'),
                'market_cap': data.get('market_cap'),
                'per': data.get('per'),
                'pbr': data.get('pbr'),
                'roe': data.get('roe'),
                'debt_ratio': data.get('debt_ratio'),
                'dividend_yield': data.get('dividend_yield'),
                'data_source': 'KIS'
            }
            
            snapshots.append(snapshot)
        
        except Exception as e:
            logger.error(f"  [FAIL] {code} 변환 실패: {e}")
            continue
    
    print(f"  [OK] {len(snapshots)}개 변환 완료")
    
    # 4. DB 저장
    print("\n[4단계] DB 저장")
    saved = db.save_snapshots(snapshots, snapshot_date=date.today())
    print(f"  [OK] {saved}개 저장 완료")
    
    # 5. 섹터 통계 계산
    print("\n[5단계] 섹터 통계 계산")
    sector_stats = db.compute_sector_stats(snapshot_date=date.today())
    print(f"  [OK] {len(sector_stats)}개 섹터 통계 계산 완료")
    
    for sector, stats in sector_stats.items():
        n = stats['sample_size']
        per_p50 = stats['per_percentiles'].get('p50', 0)
        pbr_p50 = stats['pbr_percentiles'].get('p50', 0)
        roe_p50 = stats['roe_percentiles'].get('p50', 0)
        print(f"    {sector:15s} → n={n:3d}, PER={per_p50:6.1f}, PBR={pbr_p50:5.2f}, ROE={roe_p50:5.1f}%")
    
    # 6. 검증
    print("\n[6단계] 검증")
    db_stats = db.get_stats()
    print(f"  총 스냅샷: {db_stats['total_snapshots']:,}개")
    print(f"  종목 수: {db_stats['unique_stocks']:,}개")
    print(f"  날짜 수: {db_stats['unique_dates']:,}일")
    print(f"  섹터 수: {db_stats['unique_sectors']:,}개")
    print(f"  최신 날짜: {db_stats['latest_date']}")
    print(f"  DB 크기: {db_stats['db_size_mb']:.2f} MB")
    
    # 7. 섹터 통계 조회 테스트
    print("\n[7단계] 섹터 통계 조회 테스트 (기존 캐시 형식 호환)")
    loaded_stats = db.get_sector_stats()
    print(f"  [OK] {len(loaded_stats)}개 섹터 조회 성공")
    
    for sector in loaded_stats.keys():
        n = loaded_stats[sector]['sample_size']
        print(f"    - {sector} (n={n})")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] 마이그레이션 완료!")
    print("=" * 60)
    print(f"\n다음 단계:")
    print(f"  1. Streamlit에서 DB 캐시 우선 사용")
    print(f"  2. 자동 수집 스케줄러 시작")
    print(f"     python daily_price_collector.py")
    print(f"  3. 내일부터 자동으로 일별 데이터 누적!")
    print()


if __name__ == "__main__":
    try:
        migrate_to_db()
    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()

