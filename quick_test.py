#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""빠른 API 테스트"""

from config_manager import ConfigManager
from mcp_kis_integration import MCPKISIntegration

print("🔄 새 AppKey로 API 테스트 중...")

# Config 로드
config = ConfigManager()

# OAuth 객체 생성
class OAuth:
    pass

oauth = OAuth()
# ConfigManager는 kis_api_key, kis_api_secret으로 로드
oauth.appkey = config.get('kis_api_key')
oauth.appsecret = config.get('kis_api_secret')
oauth.app_key = oauth.appkey
oauth.app_secret = oauth.appsecret

# 토큰 발급 메서드 추가
def get_rest_token():
    """KIS API 토큰 발급"""
    import requests
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"content-type": "application/json; charset=utf-8"}
    data = {
        "grant_type": "client_credentials",
        "appkey": oauth.appkey,
        "appsecret": oauth.appsecret
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('access_token')
    except Exception as e:
        print(f"토큰 발급 오류: {e}")
    return None

oauth.get_rest_token = get_rest_token

if not oauth.appkey or not oauth.appsecret:
    print("❌ Config에서 API 키를 찾을 수 없습니다!")
    print(f"kis_api_key: {oauth.appkey}")
    print(f"kis_api_secret: {oauth.appsecret}")
    exit(1)

print(f"✅ AppKey 로드 성공: {oauth.appkey[:10]}...")

# MCP 클라이언트 생성
mcp = MCPKISIntegration(oauth, request_interval=1.0)

# 삼성전자 조회
print("\n삼성전자 (005930) 조회 중...")
result = mcp.get_current_price('005930', 'J')

if result:
    print("\n✅ 성공!")
    print(f"종목명: {result.get('hts_kor_isnm', 'N/A')}")
    print(f"현재가: {result.get('stck_prpr', 'N/A')}원")
    print(f"등락률: {result.get('prdy_ctrt', 'N/A')}%")
else:
    print("\n❌ 실패 - 데이터 없음")

