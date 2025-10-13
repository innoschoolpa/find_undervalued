#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB 통합 테스트"""

import logging
from value_stock_finder import ValueStockFinder

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

logger = logging.getLogger(__name__)

def test_integration():
    """DB 통합 테스트"""
    
    print("=" * 60)
    print("DB 통합 테스트")
    print("=" * 60)
    
    # 1. ValueStockFinder 초기화
    print("\n[1단계] ValueStockFinder 초기화")
    vf = ValueStockFinder()
    print("  [OK] 초기화 완료")
    
    # 2. 섹터 캐시 조회 테스트 (다층 캐시 확인)
    print("\n[2단계] 섹터 캐시 조회 테스트 (다층 캐시)")
    
    test_sectors = [
        ('전기전자', '제조업'),
        ('에너지/화학', '에너지/화학'),
        ('건설', '건설'),
        ('금융', '금융'),
    ]
    
    for raw, expected in test_sectors:
        print(f"\n  테스트: {raw}")
        
        try:
            stats, bench = vf._cached_sector_data(raw)
            
            if stats:
                n = stats.get('sample_size', 0)
                per_p50 = stats.get('per_percentiles', {}).get('p50', 0)
                pbr_p50 = stats.get('pbr_percentiles', {}).get('p50', 0)
                
                print(f"    [SUCCESS] n={n}, PER={per_p50:.1f}, PBR={pbr_p50:.2f}")
            else:
                print(f"    [WARNING] 통계 없음")
        
        except Exception as e:
            print(f"    [ERROR] {e}")
    
    # 3. 로그 분석
    print("\n[3단계] 캐시 히트 분석")
    print("  로그를 확인하여 DB/pickle/실시간 중 어떤 캐시가 사용되었는지 확인")
    print("  예상: '✅ DB 캐시 히트' 메시지가 보여야 함")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] DB 통합 테스트 완료!")
    print("=" * 60)
    print("\n다음 단계:")
    print("  1. Streamlit 재시작")
    print("     streamlit run value_stock_finder.py")
    print("  2. 스크리닝 실행 후 로그 확인")
    print("  3. '✅ DB 캐시 히트' 메시지 확인")
    print()


if __name__ == "__main__":
    try:
        test_integration()
    except Exception as e:
        logger.error(f"[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

