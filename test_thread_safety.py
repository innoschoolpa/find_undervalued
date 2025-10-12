#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
멀티스레드 환경에서 KIS API 호출 테스트
Lock 적용 후 동시 API 호출이 제대로 직렬화되는지 확인
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
from kis_data_provider import KISDataProvider

def test_concurrent_calls():
    """여러 스레드에서 동시에 API를 호출하여 Rate Limit이 작동하는지 테스트"""
    
    print("="*60)
    print("🧪 멀티스레드 Rate Limit 테스트")
    print("="*60)
    
    # 테스트 종목 리스트
    test_symbols = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("005380", "현대차"),
        ("000270", "기아"),
        ("051910", "LG화학")
    ]
    
    print(f"\n1️⃣ {len(test_symbols)}개 종목을 3개 스레드로 동시 조회")
    print(f"   예상: Lock으로 인해 순차적으로 처리 (약 {len(test_symbols) * 0.5}초 소요)\n")
    
    # KISDataProvider 인스턴스 생성 (단일 인스턴스 공유)
    provider = KISDataProvider()
    
    results = []
    call_times = []
    
    def fetch_stock(symbol_info):
        """개별 종목 조회 함수"""
        symbol, name = symbol_info
        start_time = time.time()
        print(f"📡 스레드 {threading.current_thread().name}: {name}({symbol}) 조회 시작...")
        
        result = provider.get_stock_price_info(symbol)
        
        end_time = time.time()
        call_times.append((name, start_time, end_time))
        
        if result:
            print(f"✅ 스레드 {threading.current_thread().name}: {name} 조회 성공 (현재가: {result.get('current_price', 0):,}원)")
            results.append((name, True))
        else:
            print(f"❌ 스레드 {threading.current_thread().name}: {name} 조회 실패")
            results.append((name, False))
        
        return result
    
    # 병렬 실행
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(fetch_stock, symbol_info) for symbol_info in test_symbols]
        for future in futures:
            future.result()  # 모든 작업 완료 대기
    
    total_time = time.time() - start_time
    
    # 결과 분석
    print("\n" + "="*60)
    print("📊 테스트 결과")
    print("="*60)
    
    print(f"\n총 소요 시간: {total_time:.2f}초")
    print(f"성공: {sum(1 for _, success in results if success)}/{len(results)}개")
    
    # 호출 간격 분석
    print("\n⏱️ API 호출 타이밍:")
    sorted_calls = sorted(call_times, key=lambda x: x[1])
    
    for i, (name, start, end) in enumerate(sorted_calls):
        if i == 0:
            print(f"  {i+1}. {name}: 시작 0.0초")
        else:
            prev_start = sorted_calls[i-1][1]
            interval = start - prev_start
            print(f"  {i+1}. {name}: 시작 {start - sorted_calls[0][1]:.2f}초 (이전 호출과 간격: {interval:.2f}초)")
    
    # Lock이 제대로 작동하는지 확인
    intervals = []
    for i in range(1, len(sorted_calls)):
        interval = sorted_calls[i][1] - sorted_calls[i-1][1]
        intervals.append(interval)
    
    if intervals:
        avg_interval = sum(intervals) / len(intervals)
        min_interval = min(intervals)
        
        print(f"\n📈 호출 간격 통계:")
        print(f"  평균 간격: {avg_interval:.2f}초")
        print(f"  최소 간격: {min_interval:.2f}초")
        print(f"  설정된 간격: {provider.request_interval}초")
        
        if min_interval >= (provider.request_interval - 0.1):  # 약간의 오차 허용
            print("\n✅✅✅ Lock이 정상 작동! 모든 호출이 순차적으로 처리됨")
        else:
            print(f"\n⚠️ 경고: 최소 간격({min_interval:.2f}초)이 설정값({provider.request_interval}초)보다 짧음")
            print("   → Lock이 제대로 작동하지 않거나, 재시도 로직에서 발생")
    
    print("="*60)
    
    return all(success for _, success in results)

if __name__ == "__main__":
    try:
        success = test_concurrent_calls()
        if success:
            print("\n🎉 모든 테스트 통과!")
        else:
            print("\n⚠️ 일부 API 호출 실패 (500 오류가 없다면 성공)")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

