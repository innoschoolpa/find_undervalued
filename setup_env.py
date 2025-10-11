#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
환경변수 설정 도우미 스크립트
"""

import os
import sys

def create_env_file():
    """환경변수 파일 생성"""
    
    env_content = """# KIS API 설정
# 한국투자증권 OpenAPI 키 설정
# https://apiportal.koreainvestment.com/ 에서 발급받은 키를 입력하세요

# 앱키 (36자리)
KIS_APPKEY=your_app_key_here

# 시크릿키 (180자리)
KIS_APPSECRET=your_app_secret_here

# 테스트 모드 (true: 모의투자, false: 실전투자)
KIS_TEST_MODE=true

# 가치주 분석 시스템 설정
# 개발 모드 (디버그 로그 활성화)
VSF_DEBUG=false

# 상세 로그 모드 (분석 과정 상세 출력)
VSF_VERBOSE=false

# 캐시 TTL (초 단위, 0이면 캐시 비활성화)
CACHE_TTL=1800

# API 레이트 리미팅 설정
# 초당 요청 수 (0.5-2.0 권장)
VSF_RATE_PER_SEC=0.5

# API 동시 요청 수 (1-5 권장)
VSF_ANALYZER_MAX_CONCURRENCY=3

# 빠른 모드 워커 수 (2-16 권장)
VSF_FAST_MODE_WORKERS=4
"""
    
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("SUCCESS: .env 파일이 성공적으로 생성되었습니다!")
        print("\n다음 단계:")
        print("1. .env 파일을 열어서 KIS_APPKEY와 KIS_APPSECRET을 실제 값으로 변경하세요")
        print("2. 한국투자증권 OpenAPI 포털에서 API 키를 발급받으세요:")
        print("   https://apiportal.koreainvestment.com/")
        print("3. 모의투자/실전투자에 따라 KIS_TEST_MODE를 설정하세요")
        return True
    except Exception as e:
        print(f"ERROR: .env 파일 생성 실패: {e}")
        return False

def check_env_vars():
    """환경변수 확인"""
    print("\n현재 환경변수 상태:")
    
    required_vars = [
        'KIS_APPKEY',
        'KIS_APPSECRET',
        'KIS_TEST_MODE',
        'VSF_DEBUG',
        'VSF_VERBOSE',
        'CACHE_TTL',
        'VSF_RATE_PER_SEC',
        'VSF_ANALYZER_MAX_CONCURRENCY',
        'VSF_FAST_MODE_WORKERS'
    ]
    
    for var in required_vars:
        value = os.getenv(var, '설정되지 않음')
        if var in ['KIS_APPKEY', 'KIS_APPSECRET']:
            # 보안을 위해 일부만 표시
            if value != '설정되지 않음' and len(value) > 10:
                display_value = f"{value[:10]}... ({len(value)}자)"
            else:
                display_value = value
        else:
            display_value = value
            
        status = "OK" if value != '설정되지 않음' else "NO"
        print(f"{status} {var}: {display_value}")

def setup_guide():
    """설정 가이드 출력"""
    print("\nKIS API 키 발급 가이드:")
    print("1. 한국투자증권 OpenAPI 포털 접속:")
    print("   https://apiportal.koreainvestment.com/")
    print("2. 회원가입 및 로그인")
    print("3. '앱 등록' 메뉴에서 새 앱 등록")
    print("4. 앱 이름, 설명 입력 후 등록")
    print("5. 등록된 앱에서 appkey, appsecret 확인")
    print("6. .env 파일의 KIS_APPKEY, KIS_APPSECRET에 입력")
    print("\n주의사항:")
    print("- API 키는 절대 공개하지 마세요")
    print("- .env 파일은 .gitignore에 포함되어 있어 Git에 올라가지 않습니다")
    print("- 모의투자용 키와 실전투자용 키가 다릅니다")

def main():
    """메인 함수"""
    print("가치주 분석 시스템 환경변수 설정 도우미")
    print("=" * 50)
    
    # .env 파일이 이미 있는지 확인
    if os.path.exists('.env'):
        print(".env 파일이 이미 존재합니다.")
        choice = input("덮어쓰시겠습니까? (y/N): ").lower()
        if choice != 'y':
            print("설정을 취소했습니다.")
            return
    
    # .env 파일 생성
    if create_env_file():
        # 환경변수 확인
        check_env_vars()
        
        # 설정 가이드 출력
        setup_guide()
        
        print("\n설정이 완료되었습니다!")
        print("이제 'streamlit run value_stock_finder.py'로 시스템을 실행할 수 있습니다.")

if __name__ == "__main__":
    main()
