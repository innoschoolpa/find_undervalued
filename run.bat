@echo off
REM 저평가 가치주 발굴 시스템 실행 스크립트 (Windows)

echo 🚀 저평가 가치주 발굴 시스템 시작...
echo.

REM 환경변수 설정 (선택)
REM set KIS_MAX_TPS=2.5
REM set TOKEN_BUCKET_CAP=12
REM set LOG_LEVEL=INFO

REM Python 버전 확인
python --version 2>nul
if errorlevel 1 (
    echo ❌ Python이 설치되지 않았습니다.
    echo Python 3.8 이상을 설치하세요: https://www.python.org/
    pause
    exit /b 1
)

echo ✅ Python 설치 확인됨
echo.

REM 필수 패키지 확인
echo 📦 패키지 확인 중...

python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo ⚠️  Streamlit이 설치되지 않았습니다.
    echo 설치 중: pip install streamlit
    pip install streamlit
)

python -c "import pandas" 2>nul
if errorlevel 1 (
    echo ⚠️  pandas가 설치되지 않았습니다.
    echo 설치 중: pip install pandas
    pip install pandas
)

python -c "import plotly" 2>nul
if errorlevel 1 (
    echo ⚠️  plotly가 설치되지 않았습니다.
    echo 설치 중: pip install plotly
    pip install plotly
)

echo.
echo ✅ 모든 필수 패키지 준비 완료!
echo.

REM Streamlit 실행
echo 🌐 웹 브라우저에서 http://localhost:8501 열기...
echo 🛑 종료하려면 Ctrl+C를 누르세요
echo.

streamlit run value_stock_finder.py

pause

