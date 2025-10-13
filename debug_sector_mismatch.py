#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""섹터명 불일치 디버깅"""

from db_cache_manager import get_db_cache

db = get_db_cache()
stats = db.get_sector_stats()

print("=" * 60)
print("DB 섹터 목록")
print("=" * 60)

for sector, data in stats.items():
    n = data['sample_size']
    print(f"{repr(sector):25s} -> n={n:3d}")

print("\n" + "=" * 60)
print("로그에서 찾는 섹터명")
print("=" * 60)

test_sectors = [
    "전기전자",
    "운송장비",
    "기타",
    "기타분야",
    "제조업",
    "금융",
    "금융서비스",
    "제약",
    "에너지/화학",
]

for sector in test_sectors:
    found = sector in stats
    print(f"{sector:15s} -> {'[FOUND]' if found else '[MISSING]'}")

print("\n" + "=" * 60)
print("정규화 테스트")
print("=" * 60)

from value_stock_finder import ValueStockFinder

vf = ValueStockFinder()

for sector in test_sectors:
    normalized = vf._normalize_sector_name(sector)
    key = vf._normalize_sector_key(normalized)
    found = key in [vf._normalize_sector_key(s) for s in stats.keys()]
    
    print(f"{sector:15s} -> {normalized:15s} -> {key:20s} {'[OK]' if found else '[MISS]'}")
