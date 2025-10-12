#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
멀티스레드 환경에서 KIS API 호출 테스트 V2
_rate_limit() 내부에서 타이밍을 측정하여 정확한 간격 확인
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
from kis_data_provider import KISDataProvider

# 전역 변수로 API 호출 시각 기록
api_call_times = []
lock_for_times = threading.Lock()

def test_concurrent_with_monitoring():
    """Lock이 API 호출을 제대로 직렬화하는지 모니터링"""
    
    print("="*60)
    print("🧪 멀티스레드 Rate Limit 테스트 V2 (정밀 측정)")
    print("="*60)
    
    test_symbols = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("005380", "현대차"),
        ("000270", "기아"),
        ("051910", "LG화학"),
        ("035420", "NAVER"),
    ]
    
    print(f"\n{len(test_symbols)}개 종목을 3개 스레드로 동시 조회")
    print("Lock이 제대로 작동하면 각 API 호출 간격이 0.5초 이상이어야 함\n")
    
    provider = KISDataProvider()
    
    # 원본 _rate_limit을 래핑하여 타이밍 기록
    original_rate_limit = provider._rate_limit
    
    def monitored_rate_limit():
        with lock_for_times:
            api_call_times.append(time.time())
        return original_rate_limit()
    
    provider._rate_limit = monitored_rate_limit
    
    results = []
    
    def fetch_stock(symbol_info):
        symbol, name = symbol_info
        result = provider.get_stock_price_info(symbol)
        
        if result:
            print(f"✅ {name}: {result.get('current_price', 0):,}원")
            results.append(True)
        else:
            print(f"❌ {name}: 조회 실패")
            results.append(False)
        
        return result
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(fetch_stock, symbol_info) for symbol_info in test_symbols]
        for future in futures:
            future.result()
    
    total_time = time.time() - start_time
    
    # 결과 분석
    print("\n" + "="*60)
    print("📊 테스트 결과")
    print("="*60)
    
    print(f"\n총 소요 시간: {total_time:.2f}초")
    print(f"성공: {sum(results)}/{len(results)}개")
    print(f"500 오류 발생: {'❌ 없음 (성공!)' if all(results) else '✅ 있음'}")
    
    # API 호출 간격 분석
    if len(api_call_times) >= 2:
        print("\n⏱️ 실제 API 호출 타이밍:")
        intervals = []
        
        for i, call_time in enumerate(api_call_times):
            if i == 0:
                print(f"  {i+1}. 호출 시각: 0.0초")
            else:
                interval = call_time - api_call_times[i-1]
                intervals.append(interval)
                print(f"  {i+1}. 호출 시각: {call_time - api_call_times[0]:.2f}초 (간격: {interval:.2f}초)")
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)
            
            print(f"\n📈 API 호출 간격 통계:")
            print(f"  평균: {avg_interval:.2f}초")
            print(f"  최소: {min_interval:.2f}초")
            print(f"  최대: {max_interval:.2f}초")
            print(f"  설정값: {provider.request_interval}초")
            
            # Lock 동작 확인
            if min_interval >= (provider.request_interval * 0.95):  # 5% 오차 허용
                print("\n🎉🎉🎉 완벽! Lock이 정상 작동하여 모든 호출이 순차적으로 처리됨!")
                print("   → 멀티스레드 환경에서도 동시 API 호출 방지 성공")
            elif min_interval >= 0.3:
                print("\n✅ 양호: 대부분의 호출이 적절한 간격으로 처리됨")
                print(f"   → 최소 간격 {min_interval:.2f}초로 500 오류 위험 낮음")
            else:
                print("\n⚠️ 경고: 일부 호출 간격이 너무 짧음!")
                print(f"   → 최소 간격 {min_interval:.2f}초는 500 오류 위험")
    
    print("="*60)
    
    return all(results) and (min(intervals) >= 0.4 if intervals else False)

if __name__ == "__main__":
    try:
        success = test_concurrent_with_monitoring()
        if success:
            print("\n🏆 모든 테스트 통과! 멀티스레드 환경에서 안전하게 작동합니다.")
        else:
            print("\n💡 일부 개선 필요하지만, 500 오류가 없다면 실용적으로 사용 가능")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

