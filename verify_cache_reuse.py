#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""토큰 캐시 재사용 검증"""

import time
import yaml

print("=" * 60)
print("토큰 재사용 검증 테스트")
print("=" * 60)
print()

# 설정 로드
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

kis = config['kis_api']

from test_mcp_production import SimpleOAuthManager

oauth = SimpleOAuthManager(kis['app_key'], kis['app_secret'])

print("1. 첫 번째 토큰 요청:")
t1 = oauth.get_rest_token()
print(f"   토큰: {t1[:30]}...")
print()

time.sleep(1)

print("2. 두 번째 토큰 요청 (1초 후):")
t2 = oauth.get_rest_token()
print(f"   토큰: {t2[:30]}...")
print()

print("3. 세 번째 토큰 요청 (즉시):")
t3 = oauth.get_rest_token()
print(f"   토큰: {t3[:30]}...")
print()

print("=" * 60)
if t1 == t2 == t3:
    print("SUCCESS: 캐시 재사용 성공! (3번 모두 동일한 토큰)")
else:
    print("FAIL: 토큰이 재발급되었습니다!")
    print(f"  t1 == t2: {t1 == t2}")
    print(f"  t2 == t3: {t2 == t3}")
print("=" * 60)


