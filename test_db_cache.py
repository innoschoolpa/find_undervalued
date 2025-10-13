#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB 캐시 시스템 테스트"""

import logging
from datetime import date, timedelta
from db_cache_manager import DBCacheManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

logger = logging.getLogger(__name__)

def test_db_cache():
    """DB 캐시 시스템 테스트"""
    
    print("=" * 60)
    print("DB 캐시 시스템 테스트")
    print("=" * 60)
    
    # 1. 초기화
    print("\n[1단계] DBCacheManager 초기화")
    db = DBCacheManager()
    
    # 2. 통계 확인
    print("\n[2단계] DB 통계 확인")
    stats = db.get_stats()
    print(f"  총 스냅샷: {stats['total_snapshots']:,}개")
    print(f"  종목 수: {stats['unique_stocks']:,}개")
    print(f"  날짜 수: {stats['unique_dates']:,}일")
    print(f"  날짜 범위: {stats['date_range']}")
    print(f"  섹터 수: {stats['unique_sectors']:,}개")
    print(f"  최신 날짜: {stats['latest_date']}")
    print(f"  DB 크기: {stats['db_size_mb']:.2f} MB")
    
    # 3. 샘플 데이터 저장 테스트
    print("\n[3단계] 샘플 데이터 저장 테스트")
    
    sample_snapshots = [
        {
            'code': '005930',
            'name': '삼성전자',
            'sector': '전기전자',
            'sector_normalized': '전기전자',
            'price': 75000,
            'open_price': 74500,
            'high_price': 75500,
            'low_price': 74000,
            'volume': 12345678,
            'market_cap': 450_000_000_000_000,
            'per': 12.5,
            'pbr': 1.2,
            'roe': 9.6,
            'debt_ratio': 35.0,
            'dividend_yield': 2.5,
        },
        {
            'code': '000660',
            'name': 'SK하이닉스',
            'sector': '전기전자',
            'sector_normalized': '전기전자',
            'price': 145000,
            'open_price': 144000,
            'high_price': 146000,
            'low_price': 143500,
            'volume': 5432109,
            'market_cap': 105_000_000_000_000,
            'per': 18.3,
            'pbr': 1.5,
            'roe': 8.2,
            'debt_ratio': 28.0,
            'dividend_yield': 1.8,
        },
        {
            'code': '035420',
            'name': 'NAVER',
            'sector': '서비스',
            'sector_normalized': '기타분야',
            'price': 235000,
            'open_price': 233000,
            'high_price': 237000,
            'low_price': 232500,
            'volume': 876543,
            'market_cap': 38_000_000_000_000,
            'per': 28.5,
            'pbr': 2.8,
            'roe': 9.8,
            'debt_ratio': 15.0,
            'dividend_yield': 0.5,
        }
    ]
    
    saved = db.save_snapshots(sample_snapshots, snapshot_date=date.today())
    print(f"  저장 완료: {saved}개")
    
    # 4. 최신 스냅샷 조회
    print("\n[4단계] 최신 스냅샷 조회")
    latest = db.get_latest_snapshots(max_age_days=1)
    print(f"  조회 결과: {len(latest)}개")
    if not latest.empty:
        print(f"\n  샘플 (최신 3개):")
        for _, row in latest.head(3).iterrows():
            print(f"    {row['stock_code']} {row['name']:10s} | "
                  f"가격: {row['close_price']:>8,.0f}원 | "
                  f"PER: {row['per']:>5.1f} | PBR: {row['pbr']:>5.2f}")
    
    # 5. 종목별 이력 조회 테스트
    print("\n[5단계] 종목별 이력 조회 테스트")
    if saved > 0:
        history = db.get_stock_history('005930', days=30)
        print(f"  삼성전자 이력: {len(history)}일")
        if not history.empty:
            print(f"  최신 가격: {history.iloc[0]['price']:,.0f}원")
    
    # 6. 섹터 통계 계산 테스트
    print("\n[6단계] 섹터 통계 계산 테스트")
    
    # 충분한 샘플 데이터 생성 (30개 이상)
    print("  충분한 샘플 데이터 생성 중...")
    more_samples = []
    for i in range(35):
        more_samples.append({
            'code': f'{100000 + i:06d}',
            'name': f'테스트종목{i+1}',
            'sector': '전기전자',
            'sector_normalized': '전기전자',
            'price': 10000 + i * 100,
            'per': 10.0 + i * 0.5,
            'pbr': 1.0 + i * 0.1,
            'roe': 8.0 + i * 0.2,
        })
    
    db.save_snapshots(more_samples, snapshot_date=date.today())
    
    sector_stats = db.compute_sector_stats(snapshot_date=date.today())
    print(f"  섹터 통계 계산 완료: {len(sector_stats)}개 섹터")
    
    for sector, stats in sector_stats.items():
        print(f"\n  [{sector}]")
        print(f"    표본 크기: {stats['sample_size']}개")
        print(f"    PER 중앙값: {stats['per_percentiles'].get('p50', 0):.1f}")
        print(f"    PBR 중앙값: {stats['pbr_percentiles'].get('p50', 0):.2f}")
        print(f"    ROE 중앙값: {stats['roe_percentiles'].get('p50', 0):.1f}%")
    
    # 7. 섹터 통계 조회 테스트
    print("\n[7단계] 섹터 통계 조회 테스트 (기존 캐시 형식 호환)")
    loaded_stats = db.get_sector_stats()
    print(f"  조회 결과: {len(loaded_stats)}개 섹터")
    
    for sector in loaded_stats.keys():
        print(f"    - {sector} (n={loaded_stats[sector]['sample_size']})")
    
    # 8. 증분 업데이트 테스트
    print("\n[8단계] 증분 업데이트 대상 조회")
    stale = db.get_stale_stocks(max_age_days=1)
    print(f"  업데이트 필요: {len(stale)}개")
    if stale:
        print(f"  샘플: {stale[:5]}")
    
    # 9. 최종 통계
    print("\n[9단계] 최종 DB 통계")
    final_stats = db.get_stats()
    print(f"  총 스냅샷: {final_stats['total_snapshots']:,}개")
    print(f"  종목 수: {final_stats['unique_stocks']:,}개")
    print(f"  날짜 수: {final_stats['unique_dates']:,}일")
    print(f"  섹터 수: {final_stats['unique_sectors']:,}개")
    print(f"  DB 크기: {final_stats['db_size_mb']:.2f} MB")
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_db_cache()
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

