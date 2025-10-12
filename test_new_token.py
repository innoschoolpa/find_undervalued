#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""새 AppKey로 토큰 발급 및 현재가 조회 테스트"""

from kis_data_provider import KISDataProvider
import json

print("="*60)
print("🔑 새 AppKey로 토큰 발급 및 현재가 조회 테스트")
print("="*60)

try:
    print("\n1️⃣ 토큰 캐시 삭제 완료 ✅")
    print("2️⃣ 새 AppKey로 토큰 발급 시작...\n")
    
    # Provider 초기화 (새 토큰 자동 발급)
    provider = KISDataProvider()
    print(f"\n✅ KIS Data Provider 초기화 완료")
    print(f"⏱️  API 호출 간격: {provider.request_interval}초")
    
    # 삼성전자 조회
    symbol = "005930"
    print(f"\n3️⃣ 삼성전자({symbol}) 현재가 조회 시작...")
    print(f"   (새 토큰으로 첫 API 호출)")
    
    result = provider.get_stock_price_info(symbol)
    
    if result:
        print("\n" + "="*60)
        print("✅✅✅ 성공! 새 AppKey 정상 작동")
        print("="*60)
        print(f"종목코드: {symbol}")
        print(f"종목명: {result.get('name', 'N/A')}")
        print(f"현재가: {result.get('current_price', 0):,}원")
        print(f"등락률: {result.get('change_rate', 0):+.2f}%")
        print(f"거래량: {result.get('volume', 0):,}주")
        print(f"시가총액: {result.get('market_cap', 0)/1e8:,.0f}억원")
        print(f"PER: {result.get('per', 0):.2f}배")
        print(f"PBR: {result.get('pbr', 0):.2f}배")
        print(f"섹터: {result.get('sector', 'N/A')}")
        print("="*60)
        print("\n✅ 새 AppKey가 정상적으로 작동합니다!")
        print("💡 이제 메인 프로그램을 실행하실 수 있습니다.")
    else:
        print("\n❌ 조회 실패")
        print("\n가능한 원인:")
        print("1. 새 AppKey도 유량 제한에 걸렸을 수 있음")
        print("2. AppKey/AppSecret 설정 확인 필요")
        print("3. 계정 타입 확인 (실전투자/모의투자)")
        
except KeyboardInterrupt:
    print("\n\n⚠️ 사용자에 의해 중단됨")
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

