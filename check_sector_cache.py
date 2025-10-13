#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""섹터 캐시 상태 확인 및 강제 생성"""

import os
import sys
from pathlib import Path
from datetime import datetime

print("\n" + "="*60)
print("섹터 캐시 상태 확인")
print("="*60)

# 1. 캐시 파일 확인
cache_path = Path('cache/sector_stats.pkl')

print(f"\n1️⃣ 캐시 파일 확인")
print(f"   경로: {cache_path}")
print(f"   존재: {cache_path.exists()}")

if cache_path.exists():
    mtime = cache_path.stat().st_mtime
    size = cache_path.stat().st_size
    print(f"   생성: {datetime.fromtimestamp(mtime)}")
    print(f"   크기: {size:,} bytes")
    
    # 캐시 로드 시도
    try:
        import pickle
        with open(cache_path, 'rb') as f:
            sector_stats = pickle.load(f)
        print(f"   섹터: {len(sector_stats)}개")
        
        for sector, data in list(sector_stats.items())[:5]:
            n = data.get('sample_size', 0)
            print(f"     - {sector}: n={n}")
    except Exception as e:
        print(f"   ❌ 로드 실패: {e}")
else:
    print("   ❌ 캐시 파일 없음")
    print("\n   → 수동 생성 필요!")

print("\n" + "="*60)

# 2. 수동 생성 옵션
if not cache_path.exists():
    print("\n2️⃣ 섹터 캐시 수동 생성")
    print("   다음 스크립트 실행:")
    print("   python create_sector_cache.py")
    print("")

print("="*60)


