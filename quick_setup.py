#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
빠른 API 키 설정 도우미
"""

import os
import sys

def quick_setup():
    """빠른 설정 도우미"""
    print("=== 빠른 API 키 설정 도우미 ===")
    print()
    
    # .env 파일 경로 확인
    env_path = ".env"
    if not os.path.exists(env_path):
        print("ERROR: .env 파일이 없습니다!")
        print("먼저 'python setup_env.py'를 실행해주세요")
        return False
    
    print("현재 .env 파일 상태:")
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # API 키 상태 확인
        if "KIS_APPKEY=your_app_key_here" in content:
            print("- KIS_APPKEY: 미설정 (기본값)")
        elif "KIS_APPKEY=" in content:
            print("- KIS_APPKEY: 설정됨")
        else:
            print("- KIS_APPKEY: 설정되지 않음")
            
        if "KIS_APPSECRET=your_app_secret_here" in content:
            print("- KIS_APPSECRET: 미설정 (기본값)")
        elif "KIS_APPSECRET=" in content:
            print("- KIS_APPSECRET: 설정됨")
        else:
            print("- KIS_APPSECRET: 설정되지 않음")
            
    except Exception as e:
        print(f"ERROR: .env 파일 읽기 실패: {e}")
        return False
    
    print()
    print("API 키 설정 방법:")
    print("1. .env 파일을 텍스트 에디터로 열기")
    print("2. 다음 라인들을 찾아서 수정:")
    print("   KIS_APPKEY=your_app_key_here")
    print("   KIS_APPSECRET=your_app_secret_here")
    print("3. 실제 API 키로 변경:")
    print("   KIS_APPKEY=PS2024010100000000000000000000000")
    print("   KIS_APPSECRET=실제_180자리_시크릿키")
    print()
    print("API 키 발급:")
    print("- https://apiportal.koreainvestment.com/ 접속")
    print("- 회원가입 후 앱 등록")
    print("- appkey, appsecret 확인")
    print()
    
    # .env 파일 직접 편집 옵션
    choice = input(".env 파일을 직접 편집하시겠습니까? (y/N): ").lower()
    if choice == 'y':
        try:
            # Windows에서 notepad로 .env 파일 열기
            os.system(f"notepad {env_path}")
            print("편집 완료 후 'python test_oauth.py'로 테스트하세요")
        except Exception as e:
            print(f"에디터 실행 실패: {e}")
            print("수동으로 .env 파일을 열어서 편집해주세요")
    
    return True

def show_current_status():
    """현재 상태 표시"""
    print("\n=== 현재 시스템 상태 ===")
    
    # 환경변수 확인
    from dotenv import load_dotenv
    load_dotenv()
    
    appkey = os.getenv("KIS_APPKEY", "")
    appsecret = os.getenv("KIS_APPSECRET", "")
    
    print(f"KIS_APPKEY: {'설정됨' if appkey and appkey != 'your_app_key_here' else '미설정'}")
    print(f"KIS_APPSECRET: {'설정됨' if appsecret and appsecret != 'your_app_secret_here' else '미설정'}")
    
    # OAuth 테스트
    if appkey and appkey != "your_app_key_here" and appsecret and appsecret != "your_app_secret_here":
        print("\nOAuth 인증 테스트 중...")
        try:
            from value_stock_finder import KISOAuthManager
            oauth = KISOAuthManager()
            approval_key = oauth.get_approval_key()
            if approval_key:
                print("OAuth 상태: SUCCESS")
            else:
                print("OAuth 상태: FAILED")
        except Exception as e:
            print(f"OAuth 테스트 실패: {e}")
    else:
        print("\nOAuth 테스트: API 키 미설정으로 인해 스킵")

def main():
    """메인 함수"""
    success = quick_setup()
    
    if success:
        show_current_status()
        
        print("\n" + "="*50)
        print("다음 단계:")
        print("1. .env 파일에서 API 키 설정")
        print("2. python test_oauth.py (OAuth 테스트)")
        print("3. streamlit run value_stock_finder.py (시스템 실행)")

if __name__ == "__main__":
    main()




