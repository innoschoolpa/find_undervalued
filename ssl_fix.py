#!/usr/bin/env python3
"""
SSL 인증서 문제 해결을 위한 유틸리티
"""

import ssl
import urllib3
import requests
import os

def fix_ssl_issues():
    """SSL 인증서 문제를 해결합니다."""
    
    # 1. urllib3 SSL 경고 비활성화
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # 2. SSL 컨텍스트 설정 (개발/테스트용)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # 3. 환경 변수 설정
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    
    # 4. requests 세션 기본 설정
    requests.packages.urllib3.disable_warnings()
    
    print("✅ SSL 문제 해결 설정 완료")
    print("⚠️  주의: SSL 검증이 비활성화되었습니다. 프로덕션 환경에서는 사용하지 마세요.")

def create_requests_session_with_ssl_fix():
    """SSL 문제가 해결된 requests 세션을 생성합니다."""
    fix_ssl_issues()
    
    session = requests.Session()
    session.verify = False
    
    # User-Agent 설정
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    return session

if __name__ == "__main__":
    fix_ssl_issues()
    print("SSL 설정이 완료되었습니다.")
