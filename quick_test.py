#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""빠른 현재가 조회 테스트"""

from kis_data_provider import KISDataProvider
import json

print("🔍 삼성전자 현재가 조회 시작...\n")

try:
    # Provider 초기화
    provider = KISDataProvider()
    print(f"✅ KIS Data Provider 초기화 완료")
    print(f"⏱️  API 호출 간격: {provider.request_interval}초\n")
    
    # 삼성전자 조회
    symbol = "005930"
    print(f"📡 API 호출 중: {symbol} (삼성전자)...")
    
    result = provider.get_stock_price_info(symbol)
    
    if result:
        print("\n" + "="*60)
        print("✅ 조회 성공!")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("="*60)
    else:
        print("\n❌ 조회 실패 - API가 여전히 차단 상태일 수 있습니다.")
        print("💡 10-15분 후 다시 시도해주세요.")
        
except KeyboardInterrupt:
    print("\n\n⚠️ 사용자에 의해 중단됨")
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
