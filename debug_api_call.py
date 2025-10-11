#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 호출 디버깅
- 실제 헤더, 파라미터, 응답 상세 로그
"""

import requests
import json
from config_manager import ConfigManager
from kis_token_manager import KISTokenManager

print("=" * 60)
print("[DEBUG] KIS API 호출 디버깅")
print("=" * 60)

# Config 로드
config = ConfigManager()
token_manager = KISTokenManager('config.yaml')

# 토큰 발급
print("\n[1] 토큰 확인...")
token = token_manager.get_valid_token()
if token:
    print(f"[OK] 토큰: {token[:30]}...")
else:
    print("[FAIL] 토큰 발급 실패")
    exit(1)

# API 호출 준비
base_url = "https://openapi.koreainvestment.com:9443"
path = "/uapi/domestic-stock/v1/quotations/inquire-price"
tr_id = "FHKST01010100"

# 헤더 구성
headers = {
    "content-type": "application/json; charset=utf-8",
    "appkey": token_manager.app_key,
    "appsecret": token_manager.app_secret,
    "authorization": f"Bearer {token}",
    "tr_id": tr_id,
}

# 파라미터
params = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_INPUT_ISCD": "005930"
}

print("\n[2] 요청 정보:")
print(f"URL: {base_url}{path}")
print(f"TR_ID: {tr_id}")
print(f"파라미터: {json.dumps(params, indent=2)}")
print(f"\n헤더:")
for key, value in headers.items():
    if key in ('appkey', 'appsecret', 'authorization'):
        print(f"  {key}: {value[:20]}...")
    else:
        print(f"  {key}: {value}")

# API 호출
print("\n[3] API 호출 시도...")
try:
    response = requests.get(
        f"{base_url}{path}",
        headers=headers,
        params=params,
        timeout=(10, 30)
    )
    
    print(f"\n[4] 응답:")
    print(f"상태 코드: {response.status_code}")
    print(f"응답 헤더:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    print(f"\n응답 본문:")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # rt_cd 체크
        if 'rt_cd' in data:
            print(f"\nrt_cd: {data['rt_cd']}")
            print(f"msg1: {data.get('msg1', 'N/A')}")
            print(f"msg_cd: {data.get('msg_cd', 'N/A')}")
        
        if response.status_code == 200 and data.get('rt_cd') == '0':
            print("\n[SUCCESS] API 호출 정상")
            output = data.get('output', {})
            print(f"종목명: {output.get('hts_kor_isnm', 'N/A')}")
            print(f"현재가: {output.get('stck_prpr', 'N/A')}원")
        elif response.status_code == 500:
            print("\n[ERROR 500] 서버 내부 오류")
            print("응답 본문에서 실제 원인 확인 필요")
        else:
            print(f"\n[WARNING] 예상치 못한 응답: {response.status_code}")
            
    except json.JSONDecodeError:
        print("[ERROR] JSON 파싱 실패")
        print(f"원본: {response.text[:500]}")
    
except requests.exceptions.RequestException as e:
    print(f"\n[ERROR] 요청 실패: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"상태 코드: {e.response.status_code}")
        print(f"응답: {e.response.text[:500]}")

print("\n" + "=" * 60)

