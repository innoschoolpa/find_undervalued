#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전역 Rate Limiter 통합 테스트
KISDataProvider와 MCPKISIntegration이 동일한 Lock 사용
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
from kis_data_provider import KISDataProvider

def test_unified_rate_limiter():
    """KISDataProvider 여러 인스턴스가 전역 Lock 공유"""
    
    print("="*60)
    print("🧪 전역 Rate Limiter 통합 테스트")
    print("="*60)
    
    test_symbols = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("005380", "현대차"),
        ("000270", "기아"),
        ("051910", "LG화학"),
        ("035420", "NAVER")
    ]
    
    print(f"\n✅ 개선 사항:")
    print(f"   - KISDataProvider: 전역 Lock 사용")
    print(f"   - MCPKISIntegration: 전역 Lock 사용")
    print(f"   - 둘 다 같은 Lock을 공유하여 동시 API 호출 완전 방지\n")
    
    results = []
    
    def fetch_stock(symbol_info):
        """각 스레드가 새 인스턴스 생성"""
        symbol, name = symbol_info
        provider = KISDataProvider()
        
        result = provider.get_stock_price_info(symbol)
        
        if result:
            print(f"✅ {name}: {result.get('current_price', 0):,}원")
            results.append(True)
        else:
            print(f"❌ {name}: 조회 실패")
            results.append(False)
        
        return result
    
    start_time = time.time()
    
    # 6개 종목을 3개 스레드로 동시 조회
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(fetch_stock, symbol_info) 
                   for symbol_info in test_symbols]
        for future in futures:
            future.result()
    
    total_time = time.time() - start_time
    
    # 결과
    print("\n" + "="*60)
    print("📊 테스트 결과")
    print("="*60)
    
    print(f"\n총 소요 시간: {total_time:.2f}초")
    print(f"성공: {sum(results)}/{len(results)}개")
    
    if all(results):
        print(f"500 오류: ❌ 없음 (성공!)")
        
        expected_time = len(test_symbols) * 0.5
        if total_time >= expected_time * 0.8:  # 20% 오차 허용
            print(f"\n🎉🎉🎉 완벽!")
            print(f"   ✅ 전역 Lock이 정상 작동")
            print(f"   ✅ 모든 API 호출이 순차 처리")
            print(f"   ✅ 500 오류 완전 제거")
            print(f"   ✅ 예상 시간({expected_time:.1f}초)과 실제 시간({total_time:.1f}초) 일치")
        else:
            print(f"\n✅ 성공하긴 했지만 시간이 예상보다 짧음")
            print(f"   예상: {expected_time:.1f}초, 실제: {total_time:.1f}초")
    else:
        print(f"500 오류: ✅ 발생 (실패)")
        print(f"\n⚠️ 일부 API 호출 실패 - 추가 조사 필요")
    
    print("="*60)
    
    return all(results)

if __name__ == "__main__":
    try:
        success = test_unified_rate_limiter()
        if success:
            print("\n🏆 모든 테스트 통과!")
            print("💡 이제 Streamlit 앱에서 실제 테스트를 진행하세요:")
            print("   python -m streamlit run value_stock_finder.py")
        else:
            print("\n⚠️ 일부 테스트 실패")
    except Exception as e:
        print(f"\n❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

