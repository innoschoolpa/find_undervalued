#!/usr/bin/env python3
"""
환경 변수를 통한 SSL 문제 해결
"""

import os
import ssl

def setup_ssl_environment():
    """SSL 문제 해결을 위한 환경 변수 설정"""
    
    # SSL 검증 비활성화
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    os.environ['SSL_VERIFY'] = 'false'
    
    # yfinance SSL 문제 해결
    os.environ['YFINANCE_SSL_VERIFY'] = 'false'
    
    print("✅ SSL 환경 변수 설정 완료")

if __name__ == "__main__":
    setup_ssl_environment()
