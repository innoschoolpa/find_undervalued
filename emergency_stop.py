"""
긴급 중단 스크립트 - 무한루프 방지
"""

import os
import signal
import subprocess
import sys

def kill_streamlit_processes():
    """Streamlit 프로세스 강제 종료"""
    try:
        # Windows에서 Streamlit 프로세스 찾기
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True, shell=True)
        
        if 'streamlit' in result.stdout.lower() or 'value_stock_finder' in result.stdout.lower():
            print("Streamlit 프로세스를 찾았습니다. 종료 중...")
            
            # Python 프로세스 종료
            subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], shell=True)
            print("✅ Streamlit 프로세스가 종료되었습니다.")
        else:
            print("❌ 실행 중인 Streamlit 프로세스를 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"❌ 프로세스 종료 중 오류: {e}")

def main():
    print("🚨 긴급 중단 스크립트")
    print("=" * 50)
    
    choice = input("Streamlit 프로세스를 강제 종료하시겠습니까? (y/N): ")
    
    if choice.lower() in ['y', 'yes']:
        kill_streamlit_processes()
    else:
        print("취소되었습니다.")
    
    print("\n💡 팁: Ctrl+C를 눌러도 프로세스를 종료할 수 있습니다.")

if __name__ == "__main__":
    main()




