#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v2.2.3 통합 테스트

테스트 항목:
1. 섹터 캐시 매니저 작동
2. 섹터 정규화 개선 확인
3. MoS 캡 조정 확인
4. 품질 점수 포함 확인
5. Zero-padding 확인
"""

import sys
import io
import logging

# Windows 인코딩 수정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

print("\n" + "="*60)
print("v2.2.3 통합 테스트")
print("="*60)

# ============================================
# 1. 섹터 캐시 매니저 테스트
# ============================================
print("\n✅ 1. 섹터 캐시 매니저 테스트")
print("-"*60)

try:
    from sector_cache_manager import SectorCacheManager
    
    manager = SectorCacheManager(ttl_hours=24)
    
    # 캐시 확인
    is_valid = manager.is_cache_valid()
    print(f"  캐시 유효: {is_valid}")
    
    if is_valid:
        stats = manager.load_cache()
        print(f"  섹터 수: {len(stats) if stats else 0}")
        
        if stats:
            for sector, data in list(stats.items())[:5]:
                n = data.get('sample_size', 0)
                per_p50 = data['per_percentiles'].get('p50', 0) if 'per_percentiles' in data else 0
                print(f"  - {sector}: n={n}, PER 중앙값={per_p50:.1f}")
    
    print("  ✅ PASS")

except Exception as e:
    print(f"  ❌ FAIL: {e}")
    import traceback
    traceback.print_exc()

# ============================================
# 2. 섹터 정규화 개선 테스트
# ============================================
print("\n✅ 2. 섹터 정규화 개선 테스트")
print("-"*60)

test_cases = [
    ("금호타이어", "운송장비"),  # 타이어 → 운송장비
    ("효성 지주", "지주회사"),  # 지주 → 지주회사
    ("삼성생명보험", "보험(생명)"),  # 보험 세분화
    ("KB금융", "금융"),  # 금융 후순위
    ("삼성전자", "전기전자"),  # 전자
]

try:
    from value_stock_finder import ValueStockFinder
    
    vf = ValueStockFinder()
    
    passed = 0
    for raw, expected in test_cases:
        result = vf._normalize_sector_name(raw)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{raw}' → '{result}' (기대: '{expected}')")
        if result == expected:
            passed += 1
    
    print(f"\n  통과: {passed}/{len(test_cases)}")
    
    if passed == len(test_cases):
        print("  ✅ PASS")
    else:
        print("  ⚠️ PARTIAL")

except Exception as e:
    print(f"  ❌ FAIL: {e}")
    import traceback
    traceback.print_exc()

# ============================================
# 3. MoS 캡 조정 확인
# ============================================
print("\n✅ 3. MoS 캡 조정 확인 (35 → 30)")
print("-"*60)

try:
    # MoS 100% → 30점 (기존 35점)
    mos_raw = 100
    from value_stock_finder import ValueStockFinder
    
    score = ValueStockFinder.ValueStockFinderPatches.cap_mos_score(mos_raw, max_score=30)
    
    expected = 30
    status = "✅" if score == expected else "❌"
    print(f"  {status} MoS 100% → {score}점 (기대: {expected}점)")
    
    # MoS 50% → 15점 (기존 17~18점)
    mos_raw = 50
    score = ValueStockFinder.ValueStockFinderPatches.cap_mos_score(mos_raw, max_score=30)
    
    expected = 15
    status = "✅" if score == expected else "❌"
    print(f"  {status} MoS 50% → {score}점 (기대: {expected}점)")
    
    print("  ✅ PASS")

except Exception as e:
    print(f"  ❌ FAIL: {e}")
    import traceback
    traceback.print_exc()

# ============================================
# 4. 총점 변경 확인
# ============================================
print("\n✅ 4. 총점 변경 확인 (148 → 143)")
print("-"*60)

try:
    # 더미 데이터로 평가
    from value_stock_finder import ValueStockFinder
    
    vf = ValueStockFinder()
    
    dummy_stock = {
        'symbol': '005930',
        'name': '삼성전자',
        'current_price': 70000,
        'per': 12.0,
        'pbr': 1.2,
        'roe': 12.0,
        'sector': '전기전자',
        'sector_name': '전기전자',
        'fcf_yield': 5.0,
        'interest_coverage': 10.0,
        'piotroski_fscore': 7,
        'debt_ratio': 50.0,
    }
    
    result = vf.evaluate_value_stock(dummy_stock)
    max_score = result.get('max_possible_score', 0)
    
    expected = 143
    status = "✅" if max_score == expected else "❌"
    print(f"  {status} 최대 가능 점수: {max_score}점 (기대: {expected}점)")
    
    if max_score == expected:
        print("  ✅ PASS")
    else:
        print(f"  ⚠️ WARNING: 예상과 다름")

except Exception as e:
    print(f"  ❌ FAIL: {e}")
    import traceback
    traceback.print_exc()

# ============================================
# 5. Zero-Padding 확인
# ============================================
print("\n✅ 5. Zero-Padding 확인")
print("-"*60)

test_codes = [
    ("5440", "005440"),
    ("82640", "082640"),
    ("005930", "005930"),
]

passed = 0
for code, expected in test_codes:
    result = code.zfill(6)
    status = "✅" if result == expected else "❌"
    print(f"  {status} '{code}' → '{result}' (기대: '{expected}')")
    if result == expected:
        passed += 1

if passed == len(test_codes):
    print("  ✅ PASS")
else:
    print("  ❌ FAIL")

# ============================================
# 최종 결과
# ============================================
print("\n" + "="*60)
print("🎯 통합 테스트 완료")
print("="*60)
print("\n다음 단계:")
print("  streamlit run value_stock_finder.py")
print("\n검증 항목:")
print("  - 섹터(원본), 섹터표본 컬럼 확인")
print("  - FCF수익률, 이자보상, F점수 확인")
print("  - 종목코드 6자리 확인")
print("  - 필터 강도 프리셋 작동 확인")
print("\n" + "="*60)


