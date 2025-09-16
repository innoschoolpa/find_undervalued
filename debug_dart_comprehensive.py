#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART API 전체 재무제표 디버깅 스크립트
"""

import requests
import json

def debug_dart_comprehensive():
    api_key = "881d7d29ca6d553ce02e78d22a1129c15a62ac47"
    corp_code = "00126380"  # 삼성전자
    
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": "2023",
        "reprt_code": "11011",
        "fs_div": "CFS"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == '000':
            print("✅ API 호출 성공")
            print(f"📊 총 데이터 개수: {len(data.get('list', []))}")
            
            # 손익계산서 데이터만 필터링
            is_data = [item for item in data.get('list', []) if item.get('sj_div') == 'IS']
            print(f"📈 손익계산서 데이터 개수: {len(is_data)}")
            
            print("\n🔍 손익계산서 계정명들:")
            for item in is_data[:10]:  # 처음 10개만 출력
                print(f"  - {item.get('account_nm', 'N/A')}")
            
            # 매출액 관련 계정 찾기
            print("\n💰 매출액 관련 계정:")
            for item in is_data:
                account_nm = item.get('account_nm', '')
                if '매출' in account_nm or '수익' in account_nm or 'Revenue' in account_nm:
                    print(f"  - {account_nm}: {item.get('thstrm_amount', 'N/A')}")
            
            # 영업이익 관련 계정 찾기
            print("\n💼 영업이익 관련 계정:")
            for item in is_data:
                account_nm = item.get('account_nm', '')
                if '영업' in account_nm or 'Operating' in account_nm:
                    print(f"  - {account_nm}: {item.get('thstrm_amount', 'N/A')}")
                    
        else:
            print(f"❌ API 오류: {data.get('message', '알 수 없는 오류')}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    debug_dart_comprehensive()

