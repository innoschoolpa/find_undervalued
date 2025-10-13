#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
섹터 캐시 생성 스크립트

목적: 
- Streamlit 외부에서 섹터 통계 캐시 생성
- 1000개 종목 수집 → 섹터별 통계 계산 → 24시간 캐싱

사용법:
  python create_sector_cache.py
"""

import sys
import io
import logging
from datetime import datetime

# Windows 인코딩 수정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

logger = logging.getLogger(__name__)

print("\n" + "="*60)
print("섹터 캐시 생성 스크립트")
print("="*60)
print(f"\n시작: {datetime.now()}\n")

try:
    # 1. 모듈 임포트
    print("1️⃣ 모듈 로드 중...")
    from sector_cache_manager import SectorCacheManager
    from kis_data_provider import KISDataProvider
    
    print("   ✅ 모듈 로드 완료\n")
    
    # 2. 매니저 초기화
    print("2️⃣ 섹터 캐시 매니저 초기화...")
    manager = SectorCacheManager(ttl_hours=24)
    print("   ✅ 초기화 완료\n")
    
    # 3. ValueStockFinder 초기화
    print("3️⃣ ValueStockFinder 초기화...")
    from value_stock_finder import ValueStockFinder
    vf = ValueStockFinder()
    print("   ✅ 초기화 완료\n")
    
    # 4. 기존 캐시 확인
    print("4️⃣ 기존 캐시 확인...")
    if manager.is_cache_valid():
        print("   ⚠️ 유효한 캐시가 이미 존재합니다!")
        
        response = input("\n   덮어쓰시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("\n   취소됨. 기존 캐시를 유지합니다.")
            sys.exit(0)
        print("")
    else:
        print("   ✅ 캐시 없음 - 생성 시작\n")
    
    # 5. 섹터 통계 계산
    print("5️⃣ 섹터 통계 계산 시작...")
    print("   (1000개 종목 수집 → 섹터별 분리 → 통계 계산)")
    print("   예상 소요 시간: 3~5분")
    print("   ※ 사용자가 선택한 종목 수와 무관하게 전체 시장 데이터를 수집합니다.\n")
    
    sector_stats = manager.compute_sector_stats(vf)
    
    if not sector_stats:
        print("\n   ❌ 섹터 통계 계산 실패")
        sys.exit(1)
    
    print(f"\n   ✅ 계산 완료: {len(sector_stats)}개 섹터\n")
    
    # 6. 캐시 저장
    print("6️⃣ 캐시 저장 중...")
    manager.save_cache(sector_stats)
    print("   ✅ 저장 완료\n")
    
    # 7. 결과 요약
    print("="*60)
    print("✅ 섹터 캐시 생성 완료!")
    print("="*60)
    
    print(f"\n📊 섹터별 표본 크기:\n")
    for sector, stats in sector_stats.items():
        n = stats.get('sample_size', 0)
        per_p50 = stats['per_percentiles'].get('p50', 0) if 'per_percentiles' in stats else 0
        pbr_p50 = stats['pbr_percentiles'].get('p50', 0) if 'pbr_percentiles' in stats else 0
        roe_p50 = stats['roe_percentiles'].get('p50', 0) if 'roe_percentiles' in stats else 0
        
        print(f"  {sector}: n={n}")
        print(f"    - PER 중앙값: {per_p50:.1f}배")
        print(f"    - PBR 중앙값: {pbr_p50:.2f}배")
        print(f"    - ROE 중앙값: {roe_p50:.1f}%")
        print("")
    
    print("="*60)
    print("🚀 이제 Streamlit 앱을 실행하세요:")
    print("   streamlit run value_stock_finder.py")
    print("="*60)
    print(f"\n완료: {datetime.now()}")
    print("")

except KeyboardInterrupt:
    print("\n\n중단됨.")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

