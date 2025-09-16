#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART 기업 고유번호 처리 개선사항 테스트 스크립트
"""

import logging
from corpCode import DARTCorpCodeManager
from advanced_analyzer import AdvancedStockAnalyzer

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_dart_corp_code_manager():
    """DART 기업 고유번호 관리자 테스트"""
    print("🧪 DART 기업 고유번호 관리자 테스트")
    print("=" * 50)
    
    # API 키 설정
    api_key = "881d7d29ca6d553ce02e78d22a1129c15a62ac47"
    
    # 관리자 초기화
    manager = DARTCorpCodeManager(api_key)
    
    # 1. 캐시 정보 확인
    print("\n📦 1. 캐시 정보 확인:")
    cache_info = manager.get_cache_info()
    print(f"   상태: {cache_info}")
    
    # 2. 기업 고유번호 데이터 로드
    print("\n📊 2. 기업 고유번호 데이터 로드:")
    df = manager.get_dart_corp_codes()
    if df is not None:
        print(f"   총 기업 수: {len(df):,}개")
        print(f"   상장 기업 수: {len(df[df['is_listed'] == True]):,}개")
        print(f"   비상장 기업 수: {len(df[df['is_listed'] == False]):,}개")
        
        # 상위 5개 기업 출력
        print("\n   상위 5개 기업:")
        for i, row in df.head().iterrows():
            print(f"     {row['corp_name']} ({row['corp_code']}) - {row['stock_code'] if row['stock_code'] else '비상장'}")
    else:
        print("   ❌ 데이터 로드 실패")
        return
    
    # 3. 기업 검색 테스트
    print("\n🔍 3. 기업 검색 테스트:")
    test_keywords = ["삼성", "LG", "SK", "현대"]
    for keyword in test_keywords:
        results = manager.search_companies(keyword, limit=3)
        print(f"   '{keyword}' 검색 결과: {len(results)}개")
        for result in results[:2]:  # 상위 2개만 출력
            print(f"     - {result['corp_name']} ({result['corp_code']})")
    
    # 4. 유사도 매칭 테스트
    print("\n🎯 4. 유사도 매칭 테스트:")
    test_names = ["삼성전자", "삼성전자주식회사", "삼성", "LG전자", "SK하이닉스"]
    for name in test_names:
        corp_code = manager.find_corp_code_by_name(name, threshold=0.8)
        if corp_code:
            print(f"   '{name}' -> {corp_code}")
        else:
            print(f"   '{name}' -> 매칭 실패")
    
    # 5. 상장 기업만 필터링
    print("\n📈 5. 상장 기업 필터링:")
    listed_df = manager.get_listed_companies()
    print(f"   상장 기업 수: {len(listed_df):,}개")
    
    print("\n✅ DART 기업 고유번호 관리자 테스트 완료")

def test_advanced_analyzer():
    """고급 분석기 DART 통합 테스트"""
    print("\n🧪 고급 분석기 DART 통합 테스트")
    print("=" * 50)
    
    # 분석기 초기화
    analyzer = AdvancedStockAnalyzer()
    
    # 1. DART 상태 정보 확인
    print("\n📊 1. DART 상태 정보:")
    info = analyzer.get_dart_corp_code_info()
    print(f"   상태: {info['status']}")
    if info['status'] == 'initialized':
        print(f"   매핑된 종목: {info['mapping_count']}개")
        print(f"   KOSPI 종목: {info['kospi_count']}개")
        print(f"   매칭률: {info['mapping_rate']}")
        
        cache_info = info['cache_info']
        if cache_info['status'] == 'cached':
            print(f"   캐시 상태: 유효 (마지막 업데이트: {cache_info['age_hours']:.1f}시간 전)")
    
    # 2. 기업 검색 테스트
    print("\n🔍 2. 기업 검색 테스트:")
    test_keywords = ["삼성", "LG", "SK"]
    for keyword in test_keywords:
        results = analyzer.search_dart_company(keyword, limit=3)
        print(f"   '{keyword}' 검색 결과: {len(results)}개")
        for result in results[:2]:
            print(f"     - {result['corp_name']} ({result['corp_code']})")
    
    print("\n✅ 고급 분석기 DART 통합 테스트 완료")

def main():
    """메인 테스트 함수"""
    print("🚀 DART 기업 고유번호 처리 개선사항 테스트")
    print("=" * 60)
    
    try:
        # DART 관리자 테스트
        test_dart_corp_code_manager()
        
        # 고급 분석기 테스트
        test_advanced_analyzer()
        
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        logger.error(f"테스트 실패: {e}", exc_info=True)

if __name__ == "__main__":
    main()
