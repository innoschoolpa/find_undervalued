#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
빠른 개선 패치 v2.2.3
실제 스크리닝 결과 기반 개선

개선 항목:
1. 섹터 정규화 룰 보수화 및 우선순위 조정
2. MoS 변별력 복원 (캡 조정)
3. 섹터 디버그 정보 노출
4. 품질 점수 가시화
5. 코드 zero-padding
"""

# ============================================
# 1. 섹터 정규화 룰 개선
# ============================================

IMPROVED_SECTOR_MAPPING = """
def _normalize_sector_name(self, raw_sector: str) -> str:
    '''
    ✅ v2.2.3: 섹터 정규화 (보수화 + 우선순위)
    
    개선사항:
    - 타이어/자동차부품 → 운송장비
    - 지주/홀딩스 → 지주회사
    - 보험/생명/손보 세분화
    - 충돌 키워드(금융) 후순위
    '''
    if not raw_sector or not isinstance(raw_sector, str):
        return '기타'
    
    s = raw_sector.strip()
    
    # ✅ 우선순위 1: 정확한 매칭 (긴 키워드 우선)
    
    # 자동차 관련 (타이어, 부품)
    if any(kw in s for kw in ['타이어', '자동차부품', '자동차용품']):
        return '운송장비'
    
    # 지주회사 (홀딩스 포함)
    if any(kw in s for kw in ['지주', '홀딩스', 'Holdings', '투자회사']):
        return '지주회사'
    
    # 보험 세분화
    if '생명보험' in s or '생보' in s:
        return '보험(생명)'
    if '손해보험' in s or '손보' in s:
        return '보험(손해)'
    if '보험' in s:
        return '보험'
    
    # 은행
    if '은행' in s or 'Bank' in s:
        return '은행'
    
    # 증권
    if '증권' in s or 'Securities' in s:
        return '증권'
    
    # 카드
    if '카드' in s or 'Card' in s:
        return '카드'
    
    # ✅ 우선순위 2: IT/기술 (금융과 충돌 방지)
    if any(kw in s for kw in ['IT', '정보기술', '소프트웨어', '인터넷', '게임', '플랫폼']):
        return 'IT'
    
    # 반도체/전자
    if '반도체' in s or 'Semiconductor' in s:
        return '전기전자'
    if '전자' in s or 'Electronics' in s:
        return '전기전자'
    if '전기' in s or 'Electric' in s:
        return '전기전자'
    
    # 제조업 세분화
    if '철강' in s or 'Steel' in s:
        return '철강'
    if '화학' in s or 'Chemical' in s:
        return '화학'
    if '에너지' in s or 'Energy' in s:
        return '에너지'
    if '제약' in s or 'Pharma' in s:
        return '제약'
    if '바이오' in s or 'Bio' in s:
        return '바이오'
    
    # 통신
    if '통신' in s or 'Telecom' in s:
        return '통신'
    
    # 건설
    if '건설' in s or 'Construction' in s:
        return '건설'
    
    # 운송
    if '운송' in s or '물류' in s or 'Transport' in s or 'Logistics' in s:
        return '운송'
    if '운송장비' in s or '자동차' in s or 'Auto' in s:
        return '운송장비'
    
    # 유통
    if '유통' in s or '백화점' in s or '마트' in s:
        return '유통'
    
    # 엔터테인먼트
    if '엔터테인먼트' in s or '방송' in s or '영화' in s:
        return '엔터테인먼트'
    
    # ✅ 우선순위 3: 금융 (가장 마지막, 오분류 방지)
    if '금융' in s or 'Financial' in s:
        return '금융'
    
    # 제조업 (포괄적)
    if '제조' in s or 'Manufacturing' in s:
        return '제조업'
    
    return '기타'
"""

# ============================================
# 2. MoS 캡 조정 (변별력 복원)
# ============================================

MOS_CAP_ADJUSTMENT = """
@staticmethod
def cap_mos_score(mos_raw, max_score=30):  # ✅ 35 → 30으로 완화
    '''
    ✅ v2.2.3: MoS 캡 조정 (변별력 복원)
    
    변경사항:
    - 최대 점수: 35 → 30
    - 스케일링: 0.35 → 0.30
    '''
    return min(max_score, round(mos_raw * 0.30))  # 0.35 → 0.30
"""

# ============================================
# 3. 섹터 디버그 정보 노출
# ============================================

SECTOR_DEBUG_EXPOSURE = """
# _augment_sector_data 메서드 수정

def _augment_sector_data(self, symbol: str, stock_data: Dict[str, Any]) -> Dict[str, Any]:
    '''섹터 평균 및 상대 지표 계산 (디버그 정보 추가)'''
    raw_sector = (
        stock_data.get('sector')
        or stock_data.get('sector_analysis', {}).get('sector_name', '')
        or stock_data.get('industry', '')
    )
    sector_name = self._normalize_sector_name(raw_sector)
    sector_stats, benchmarks = self._cached_sector_data(sector_name)
    
    # ... 기존 로직 ...
    
    return {
        'symbol': symbol,
        'sector_name': sector_name,
        'sector_raw': raw_sector or '',  # ✅ v2.2.3: 원본 섹터명 추가
        'sector_sample_size': (sector_stats or {}).get('sample_size', 0),  # ✅ 표본 크기
        'sector_benchmarks': benchmarks,
        'sector_stats': sector_stats,
        'relative_per': relative_per,
        'relative_pbr': relative_pbr,
        'sector_percentile': roe_percentile
    }
"""

# ============================================
# 4. 품질 점수 가시화
# ============================================

QUALITY_SCORE_VISIBILITY = """
# screen_all_stocks 결과 테이블에 추가

# BUY 종목 테이블 예시
buy_rows.append({
    '종목코드': s['symbol'].zfill(6),  # ✅ zero-padding
    '종목명': s['name'],
    '섹터': s.get('sector', 'N/A'),
    '섹터(원본)': s.get('sector_raw', 'N/A'),  # ✅ 디버그
    '섹터표본': s.get('sector_sample_size', 0),  # ✅ 디버그
    '_value_score_num': float(s.get('value_score', 0) or 0),
    '_price_num': float(s.get('current_price', 0) or 0),
    '_per_num': float(s.get('per', 0) or 0),
    '_pbr_num': float(s.get('pbr', 0) or 0),
    '_roe_num': float(s.get('roe', 0) or 0),
    '_mos_num': float(s.get('safety_margin', 0) or 0),
    '_fcf_yield': float(s.get('fcf_yield', 0) or 0),  # ✅ 품질
    '_coverage': float(s.get('interest_coverage', 0) or 0),  # ✅ 품질
    '_fscore': int(s.get('piotroski_fscore', 0) or 0),  # ✅ 품질
})

# 표시용 컬럼에 추가
buy_df['FCF수익률'] = buy_df['_fcf_yield'].map(lambda v: f"{v:.1f}%" if v > 0 else "N/A")
buy_df['이자보상'] = buy_df['_coverage'].map(lambda v: f"{v:.1f}배" if v > 0 else "N/A")
buy_df['F점수'] = buy_df['_fscore'].map(lambda v: f"{v}/9" if v > 0 else "N/A")
"""

# ============================================
# 5. 코드 zero-padding
# ============================================

ZFILL_FIX = """
# 모든 종목코드 표시 시
'종목코드': s['symbol'].zfill(6)  # ✅ 6자리로 패딩
"""

print(__doc__)
print("\n" + "="*60)
print("📋 빠른 개선 패치 v2.2.3")
print("="*60)

print("\n✅ 1. 섹터 정규화 룰 보수화")
print("   - 타이어 → 운송장비")
print("   - 지주/홀딩스 세분화")
print("   - 금융 키워드 후순위")
print("\n코드:")
print(IMPROVED_SECTOR_MAPPING)

print("\n" + "="*60)
print("\n✅ 2. MoS 캡 조정 (35 → 30)")
print("   - 변별력 복원")
print("   - 상위권 포화 완화")
print("\n코드:")
print(MOS_CAP_ADJUSTMENT)

print("\n" + "="*60)
print("\n✅ 3. 섹터 디버그 정보 노출")
print("   - sector_raw (원본)")
print("   - sector_sample_size (표본)")
print("\n코드:")
print(SECTOR_DEBUG_EXPOSURE)

print("\n" + "="*60)
print("\n✅ 4. 품질 점수 가시화")
print("   - FCF Yield")
print("   - Interest Coverage")
print("   - Piotroski F-Score")
print("\n코드:")
print(QUALITY_SCORE_VISIBILITY)

print("\n" + "="*60)
print("\n✅ 5. 코드 zero-padding")
print("   - 5440 → 005440")
print("   - 가독성 향상")
print("\n코드:")
print(ZFILL_FIX)

print("\n" + "="*60)
print("\n🚀 다음 단계:")
print("   1. value_stock_finder.py에 패치 적용")
print("   2. 섹터 매핑 테스트")
print("   3. 스크리닝 재실행 및 검증")
print("\n" + "="*60)


