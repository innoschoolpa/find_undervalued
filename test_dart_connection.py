#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART API 연결 테스트 스크립트
"""

import requests
import json

def test_dart_connection():
    """DART API 연결을 테스트합니다."""
    api_key = "881d7d29ca6d553ce02e78d22a1129c15a62ac47"
    
    # 1. 기업 고유번호 조회 테스트
    print("🔍 1. 기업 고유번호 조회 테스트")
    try:
        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        response = requests.get(url, timeout=10)
        print(f"   상태코드: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ 기업 고유번호 조회 성공")
        else:
            print(f"   ❌ 기업 고유번호 조회 실패: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ 기업 고유번호 조회 오류: {e}")
    
    # 2. 단일회사 전체 재무제표 조회 테스트
    print("\n📊 2. 단일회사 전체 재무제표 조회 테스트")
    try:
        url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
        params = {
            "crtfc_key": api_key,
            "corp_code": "00126380",  # 삼성전자
            "bsns_year": "2023",
            "reprt_code": "11011",
            "fs_div": "CFS"
        }
        response = requests.get(url, params=params, timeout=10)
        print(f"   상태코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '000':
                print("   ✅ 전체 재무제표 조회 성공")
                print(f"   📈 데이터 개수: {len(data.get('list', []))}")
            else:
                print(f"   ❌ API 오류: {data.get('message', '알 수 없는 오류')}")
        else:
            print(f"   ❌ HTTP 오류: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ 전체 재무제표 조회 오류: {e}")
    
    # 3. 간단한 재무제표 조회 테스트
    print("\n💰 3. 간단한 재무제표 조회 테스트")
    try:
        url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
        params = {
            "crtfc_key": api_key,
            "corp_code": "00126380",  # 삼성전자
            "bsns_year": "2023",
            "reprt_code": "11011",
            "fs_div": "CFS",
            "sj_div": "IS",
            "account_nm": "영업수익"
        }
        response = requests.get(url, params=params, timeout=10)
        print(f"   상태코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '000':
                print("   ✅ 간단한 재무제표 조회 성공")
                if data.get('list'):
                    item = data['list'][0]
                    print(f"   📊 영업수익: {item.get('thstrm_amount', 'N/A')}")
            else:
                print(f"   ❌ API 오류: {data.get('message', '알 수 없는 오류')}")
        else:
            print(f"   ❌ HTTP 오류: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ 간단한 재무제표 조회 오류: {e}")

if __name__ == "__main__":
    test_dart_connection()
