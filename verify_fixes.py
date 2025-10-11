#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
버그 수정 검증 스크립트
모든 크리티컬 수정이 제대로 적용되었는지 확인
"""

import sys
import re

def verify_fixes():
    """수정사항 검증"""
    print("🔍 버그 수정 검증 시작...\n")
    
    with open('value_stock_finder.py', 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    passed = []
    failed = []
    
    # 1. 섹터 라벨 완전성 체크
    print("1️⃣ 섹터 라벨 완전성 체크...")
    required_sectors = ['전기전자', '운송', '운송장비', '바이오/제약']
    
    # get_sector_specific_criteria 체크
    criteria_section = content[content.find('def get_sector_specific_criteria'):content.find('def _normalize_sector_name')]
    missing_in_criteria = [s for s in required_sectors if f"'{s}'" not in criteria_section]
    
    if not missing_in_criteria:
        passed.append("✅ get_sector_specific_criteria에 모든 섹터 존재")
    else:
        failed.append(f"❌ get_sector_specific_criteria에서 누락: {missing_in_criteria}")
    
    # _justified_multiples 체크
    justified_section = content[content.find('def _justified_multiples'):content.find('def compute_mos_score')]
    missing_in_justified = [s for s in required_sectors if f'"{s}"' not in justified_section]
    
    if not missing_in_justified:
        passed.append("✅ _justified_multiples에 모든 섹터 존재")
    else:
        failed.append(f"❌ _justified_multiples에서 누락: {missing_in_justified}")
    
    # 2. 레이트리미터 체크
    print("2️⃣ 레이트리미터 적용 체크...")
    
    # _is_tradeable 함수 전체 찾기
    start_idx = content.find('def _is_tradeable')
    if start_idx != -1:
        # 다음 함수까지 (약 100줄 정도 확인)
        is_tradeable_section = content[start_idx:start_idx+3000]
        
        if 'rate_limiter.take' in is_tradeable_section:
            passed.append("✅ _is_tradeable에 레이트리미터 적용됨")
        else:
            failed.append("❌ _is_tradeable에 레이트리미터 없음")
    else:
        failed.append("❌ _is_tradeable 함수를 찾을 수 없음")
    
    # 3. 캐시 클리어 체크
    print("3️⃣ 캐시 클리어 함수 체크...")
    refresh_section = content[content.find('def refresh_sector_stats_and_clear_cache'):content.find('def _percentile_from_breakpoints')]
    
    if '_cached_sector_data_global.clear()' in refresh_section:
        passed.append("✅ 올바른 캐시 클리어 함수 사용")
    elif 'cache_clear()' in refresh_section:
        failed.append("❌ 잘못된 cache_clear() 호출 (AttributeError 위험)")
    else:
        failed.append("❌ 캐시 클리어 로직 없음")
    
    # 4. 티커 매핑 체크
    print("4️⃣ 티커 매핑 정확성 체크...")
    
    # 003550은 없어야 함
    if "'003550': 'LG생활건강'" in content:
        failed.append("❌ 잘못된 티커 매핑: 003550 → LG생활건강")
    else:
        passed.append("✅ 003550 매핑 제거됨")
    
    # 051900이 있어야 함
    if "'051900': 'LG생활건강'" in content:
        passed.append("✅ 올바른 티커 매핑: 051900 → LG생활건강")
    else:
        failed.append("❌ 051900 매핑 누락")
    
    # 5. OAuth 토큰 갱신 체크
    print("5️⃣ OAuth 토큰 갱신 로직 체크...")
    
    if '_refresh_rest_token' in content and '/oauth2/tokenP' in content:
        passed.append("✅ OAuth 토큰 자동 갱신 로직 존재")
    else:
        failed.append("❌ OAuth 토큰 갱신 로직 누락")
    
    # 6. 토큰 만료 여유 체크
    print("6️⃣ 토큰 만료 여유 체크...")
    
    if 'exp - 120' in content:
        passed.append("✅ 토큰 만료 여유 120초 적용")
    elif 'exp - 60' in content:
        failed.append("❌ 토큰 만료 여유 60초 (권장: 120초)")
    
    # 7. 프라임 캐시 초기화 체크
    print("7️⃣ 프라임 캐시 초기화 체크...")
    
    if "self._primed_cache = {}" in content:
        passed.append("✅ 프라임 캐시 완전 초기화 (새 dict 교체)")
    
    # 8. 하드가드 조건 체크
    print("8️⃣ 하드가드 조건 체크...")
    
    if 'roe < 0 and pbr > 2.5' in content and 'per <= 0 and roe <= 0' in content:
        passed.append("✅ 하드가드 조건 보강됨 (3가지 위험 조합)")
    else:
        failed.append("❌ 하드가드 조건 보강 필요")
    
    # 9. 워커 수 체크
    print("9️⃣ 워커 수 제한 체크...")
    
    if 'min(6, max(3' in content:
        passed.append("✅ 워커 수 최대 6으로 보수화")
    elif 'min(8, max(4' in content:
        failed.append("❌ 워커 수 여전히 8 (권장: 6)")
    
    # 10. DataFrame 렌더 최적화 체크
    print("🔟 DataFrame 렌더 최적화 체크...")
    
    if 'MAX_RENDER_ROWS = 200' in content and '.head(self.MAX_RENDER_ROWS)' in content:
        passed.append("✅ DataFrame 렌더링 최적화 (상위 200개)")
    
    # 결과 출력
    print("\n" + "="*60)
    print("📊 검증 결과")
    print("="*60)
    
    print(f"\n✅ 통과: {len(passed)}개")
    for item in passed:
        print(f"  {item}")
    
    if failed:
        print(f"\n❌ 실패: {len(failed)}개")
        for item in failed:
            print(f"  {item}")
    else:
        print(f"\n🎉 모든 검증 통과!")
    
    print("\n" + "="*60)
    print(f"총점: {len(passed)}/{len(passed)+len(failed)}")
    print("="*60)
    
    # 점수 계산
    score = (len(passed) / (len(passed) + len(failed))) * 100 if (len(passed) + len(failed)) > 0 else 0
    
    if score == 100:
        print("\n🏆 완벽합니다! 프로덕션 준비 완료!")
        return 0
    elif score >= 80:
        print(f"\n⚠️ 양호 ({score:.0f}%) - 일부 항목 재확인 필요")
        return 1
    else:
        print(f"\n🔴 불충분 ({score:.0f}%) - 수정 필요")
        return 2


if __name__ == '__main__':
    """
    실행:
        python verify_fixes.py
    """
    exit_code = verify_fixes()
    sys.exit(exit_code)

