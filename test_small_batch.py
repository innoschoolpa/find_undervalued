#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 소량 테스트 (3종목, 5종목)
- 현재가 조회만 테스트
- 레이트 리밋 및 안전성 확인
"""

import time
from datetime import datetime
from kis_data_provider import KISDataProvider

print("=" * 60)
print("[TEST] KIS API 소량 현재가 조회 테스트")
print("=" * 60)
print(f"시작 시각: {datetime.now().strftime('%H:%M:%S')}")

# Provider 초기화
print("\n[INIT] KISDataProvider 초기화 중...")
provider = KISDataProvider()
print(f"[OK] 초기화 완료")
print(f"  - API 간격: {provider.request_interval}초 ({1/provider.request_interval:.1f}건/초)")

# 테스트 종목
test_sets = [
    {
        'name': '3종목 테스트',
        'stocks': [
            ("005930", "삼성전자"),
            ("000660", "SK하이닉스"),
            ("035420", "NAVER"),
        ]
    },
    {
        'name': '5종목 테스트',
        'stocks': [
            ("005930", "삼성전자"),
            ("000660", "SK하이닉스"),
            ("035420", "NAVER"),
            ("005380", "현대차"),
            ("051910", "LG화학"),
        ]
    }
]

# 각 세트별 테스트
for test_set in test_sets:
    print("\n" + "=" * 60)
    print(f"[TEST] {test_set['name']}")
    print("=" * 60)
    
    stocks = test_set['stocks']
    start_time = time.time()
    success_count = 0
    results = []
    
    for i, (code, name) in enumerate(stocks, 1):
        print(f"\n[{i}/{len(stocks)}] {name} ({code})")
        req_start = time.time()
        
        try:
            data = provider.get_stock_price_info(code)
            req_time = time.time() - req_start
            
            if data:
                price = data.get('current_price', 0)
                change = data.get('change_rate', 0)
                market_cap = data.get('market_cap', 0)
                
                print(f"  [OK] 현재가: {int(price):,}원")
                print(f"       등락률: {change:+.2f}%")
                print(f"       시총: {int(market_cap/100000000):,}억원")
                print(f"       소요: {req_time:.2f}초")
                
                success_count += 1
                results.append({
                    'code': code,
                    'name': name,
                    'price': price,
                    'change': change,
                    'time': req_time
                })
            else:
                print(f"  [FAIL] 데이터 없음 ({req_time:.2f}초)")
                
        except Exception as e:
            req_time = time.time() - req_start
            print(f"  [ERROR] {e} ({req_time:.2f}초)")
    
    # 결과 요약
    total_time = time.time() - start_time
    avg_interval = total_time / len(stocks) if len(stocks) > 0 else 0
    
    print("\n" + "-" * 60)
    print(f"[RESULT] {test_set['name']} 결과")
    print("-" * 60)
    print(f"성공: {success_count}/{len(stocks)}개 ({success_count/len(stocks)*100:.1f}%)")
    print(f"총 소요: {total_time:.2f}초")
    print(f"평균 간격: {avg_interval:.2f}초/건")
    print(f"설정 간격: {provider.request_interval}초/건")
    print(f"500 에러: {provider.consecutive_500_errors}회")
    
    if provider.consecutive_500_errors > 0:
        print("\n[WARNING] 500 에러 발생! 차단 위험")
    
    # 결과 테이블
    if results:
        print("\n[TABLE] 조회 결과:")
        print(f"{'종목명':<12} {'코드':<8} {'현재가':>12} {'등락률':>8} {'소요시간':>8}")
        print("-" * 60)
        for r in results:
            print(f"{r['name']:<12} {r['code']:<8} {int(r['price']):>12,}원 {r['change']:>7.2f}% {r['time']:>7.2f}초")
    
    # 다음 테스트 전 대기
    if test_set != test_sets[-1]:
        wait_time = 5
        print(f"\n[WAIT] 다음 테스트까지 {wait_time}초 대기...")
        time.sleep(wait_time)

# 최종 요약
print("\n" + "=" * 60)
print("[SUMMARY] 테스트 완료")
print("=" * 60)
print(f"종료 시각: {datetime.now().strftime('%H:%M:%S')}")
print(f"최종 500 에러 카운트: {provider.consecutive_500_errors}회")

if provider.consecutive_500_errors == 0:
    print("\n[SUCCESS] 모든 테스트 정상 완료!")
    print("메인 프로그램 실행 가능합니다.")
else:
    print(f"\n[WARNING] 500 에러 {provider.consecutive_500_errors}회 발생")
    print("5~10분 대기 후 재시도 권장")

print("=" * 60)



