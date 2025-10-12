#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 현재가 조회 단독 테스트
- 단일 종목의 현재가 정보를 조회하여 API 동작 확인
"""

import sys
import logging
from kis_data_provider import KISDataProvider

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_single_stock_price():
    """단일 종목 현재가 조회 테스트"""
    print("=" * 60)
    print("KIS API 현재가 조회 테스트")
    print("=" * 60)
    
    try:
        # KIS Data Provider 초기화
        print("\n1️⃣ KIS Data Provider 초기화 중...")
        provider = KISDataProvider()
        print("✅ 초기화 완료")
        
        # 테스트 종목 (삼성전자)
        test_symbol = "005930"
        test_name = "삼성전자"
        
        print(f"\n2️⃣ 종목 조회: {test_name} ({test_symbol})")
        print(f"   API 호출 간격: {provider.request_interval}초")
        
        # 현재가 정보 조회
        print(f"\n3️⃣ 현재가 정보 API 호출 중...")
        stock_info = provider.get_stock_price_info(test_symbol)
        
        if stock_info:
            print("\n✅ API 호출 성공!")
            print("=" * 60)
            print("📊 조회 결과:")
            print("=" * 60)
            print(f"종목코드: {test_symbol}")
            print(f"종목명: {stock_info.get('name', 'N/A')}")
            print(f"현재가: {stock_info.get('current_price', 0):,}원")
            print(f"등락률: {stock_info.get('change_rate', 0):+.2f}%")
            print(f"거래량: {stock_info.get('volume', 0):,}주")
            print(f"시가총액: {stock_info.get('market_cap', 0)/1e8:,.0f}억원")
            print(f"PER: {stock_info.get('per', 0):.2f}배")
            print(f"PBR: {stock_info.get('pbr', 0):.2f}배")
            print(f"EPS: {stock_info.get('eps', 0):,.0f}원")
            print(f"BPS: {stock_info.get('bps', 0):,.0f}원")
            print(f"섹터: {stock_info.get('sector', 'N/A')}")
            print("=" * 60)
            
            # 추가 종목 테스트 (선택)
            print("\n4️⃣ 추가 종목 테스트 (SK하이닉스)")
            test_symbol2 = "000660"
            test_name2 = "SK하이닉스"
            print(f"   종목: {test_name2} ({test_symbol2})")
            print(f"   API 호출 간격 대기 중... ({provider.request_interval}초)")
            
            stock_info2 = provider.get_stock_price_info(test_symbol2)
            
            if stock_info2:
                print("\n✅ 두 번째 API 호출도 성공!")
                print(f"종목명: {stock_info2.get('name', 'N/A')}")
                print(f"현재가: {stock_info2.get('current_price', 0):,}원")
                print(f"PER: {stock_info2.get('per', 0):.2f}배")
                print(f"PBR: {stock_info2.get('pbr', 0):.2f}배")
            else:
                print("❌ 두 번째 API 호출 실패")
            
            print("\n" + "=" * 60)
            print("✅ 테스트 완료: KIS API 정상 동작")
            print("=" * 60)
            return True
        else:
            print("\n❌ API 호출 실패")
            print("=" * 60)
            print("가능한 원인:")
            print("1. 네트워크 연결 문제")
            print("2. API 키 설정 오류")
            print("3. 유량 제한 초과 (5-10분 후 재시도)")
            print("4. 토큰 만료")
            print("=" * 60)
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_single_stock_price()
    sys.exit(0 if success else 1)

