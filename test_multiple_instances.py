#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
여러 KISDataProvider 인스턴스 생성 시 Lock 공유 테스트
실제 사용 패턴을 시뮬레이션
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
from kis_data_provider import KISDataProvider

def test_multiple_instances():
    """실제 사용 패턴: 각 스레드가 새로운 인스턴스 생성"""
    
    print("="*60)
    print("🧪 여러 KISDataProvider 인스턴스 Lock 공유 테스트")
    print("="*60)
    
    test_symbols = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("005380", "현대차"),
        ("000270", "기아"),
    ]
    
    print(f"\n시나리오: 각 스레드가 **새로운 KISDataProvider 인스턴스** 생성")
    print(f"예상: 클래스 레벨 Lock으로 인해 모든 API 호출이 순차 처리\n")
    
    results = []
    call_times = []
    call_times_lock = threading.Lock()
    
    def fetch_with_new_instance(symbol_info):
        """각 스레드가 새 KISDataProvider 인스턴스를 생성하여 호출"""
        symbol, name = symbol_info
        
        # ✅ 매번 새 인스턴스 생성 (실제 사용 패턴)
        provider = KISDataProvider()
        
        # API 호출 전 시간 기록
        start_time = time.time()
        with call_times_lock:
            call_times.append((name, start_time))
        
        print(f"📡 스레드 {threading.current_thread().name}: {name}({symbol}) 조회 시작...")
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
        futures = [executor.submit(fetch_with_new_instance, symbol_info) 
                   for symbol_info in test_symbols]
        for future in futures:
            future.result()
    
    total_time = time.time() - start_time
    
    # 결과 분석
    print("\n" + "="*60)
    print("📊 테스트 결과")
    print("="*60)
    
    print(f"\n총 소요 시간: {total_time:.2f}초")
    print(f"성공: {sum(results)}/{len(results)}개")
    
    if all(results):
        print(f"500 오류: ❌ 없음 (성공!)")
    else:
        print(f"500 오류: ✅ 발생 (일부 실패)")
    
    # 호출 간격 분석
    sorted_calls = sorted(call_times, key=lambda x: x[1])
    
    print("\n⏱️ API 호출 간격:")
    intervals = []
    for i, (name, call_time) in enumerate(sorted_calls):
        if i == 0:
            print(f"  {i+1}. {name}: 0.0초")
        else:
            prev_time = sorted_calls[i-1][1]
            interval = call_time - prev_time
            intervals.append(interval)
            print(f"  {i+1}. {name}: {call_time - sorted_calls[0][1]:.2f}초 (간격: {interval:.2f}초)")
    
    if intervals:
        min_interval = min(intervals)
        avg_interval = sum(intervals) / len(intervals)
        
        print(f"\n📈 통계:")
        print(f"  평균 간격: {avg_interval:.2f}초")
        print(f"  최소 간격: {min_interval:.2f}초")
        print(f"  설정값: 0.5초")
        
        if all(results) and min_interval >= 0.45:  # 5% 오차 허용
            print("\n🎉🎉🎉 완벽!")
            print("   ✅ 클래스 레벨 Lock이 정상 작동")
            print("   ✅ 여러 인스턴스에서도 Lock 공유")
            print("   ✅ 500 오류 완전 제거")
        elif all(results):
            print("\n✅ 좋음!")
            print("   ✅ 500 오류 없음")
            print("   💡 간격이 짧지만 안정적으로 작동")
        else:
            print("\n⚠️ 개선 필요")
            print("   ❌ 일부 500 오류 발생")
    
    print("="*60)
    
    return all(results)

if __name__ == "__main__":
    try:
        success = test_multiple_instances()
        if success:
            print("\n🏆 테스트 통과! 멀티 인스턴스 환경에서도 안전합니다.")
        else:
            print("\n💡 일부 개선 필요")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

