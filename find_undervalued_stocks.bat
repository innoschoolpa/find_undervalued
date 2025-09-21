@echo off
chcp 65001 > nul
title 저평가 가치주 발굴 시스템

REM 색상 설정
color 0F

REM 헤더 출력
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    저평가 가치주 발굴 시스템                    ║
echo ║                   AI-Powered Stock Analysis                  ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM 인수 처리
if "%1"=="" goto :help
if "%1"=="-h" goto :help
if "%1"=="--help" goto :help
if "%1"=="-a" goto :analyze
if "%1"=="--analyze" goto :analyze
if "%1"=="-l" goto :lg
if "%1"=="--lg" goto :lg
if "%1"=="-f" goto :finder
if "%1"=="--finder" goto :finder
if "%1"=="-m" goto :market
if "%1"=="--market" goto :market
if "%1"=="-v2" goto :v2
if "%1"=="--v2" goto :v2
if "%1"=="-c" goto :cap
if "%1"=="--cap" goto :cap
if "%1"=="-comp" goto :comprehensive
if "%1"=="--comprehensive" goto :comprehensive
if "%1"=="-n" goto :news
if "%1"=="--news" goto :news
if "%1"=="-m" goto :ml
if "%1"=="--ml" goto :ml
if "%1"=="-b" goto :backtest
if "%1"=="--backtest" goto :backtest
if "%1"=="-w" goto :web
if "%1"=="--web" goto :web
if "%1"=="-s" goto :setup
if "%1"=="--setup" goto :setup
if "%1"=="-c" goto :clean
if "%1"=="--clean" goto :clean
if "%1"=="-u" goto :update
if "%1"=="--update" goto :update
goto :unknown

:help
echo 사용법:
echo   find_undervalued_stocks.bat [옵션]
echo.
echo 옵션:
echo   -h, --help              이 도움말 표시
echo   -a, --analyze           전체 분석 실행
echo   -l, --lg                LG생활건강 분석
echo   -f, --finder            저평가 종목 발굴 (100개 종목)
echo   -m, --market            전체 시장 분석 (500개 종목)
echo   -v2, --v2               궁극의 향상된 분석 v2.0
echo   -c, --cap               시가총액 상위 종목 분석 (기본 50개)
echo   -comp, --comprehensive  종합점수 기반 분석 (정량+정성 통합)
echo   -n, --news              뉴스 분석만 실행
echo   -ml, --ml               머신러닝 모델 훈련
echo   -b, --backtest          백테스팅 실행
echo   -w, --web               웹 대시보드 실행
echo   -s, --setup             환경 설정
echo   -c, --clean             임시 파일 정리
echo   -u, --update            시스템 업데이트
echo.
echo 예시:
echo   find_undervalued_stocks.bat -a    # 전체 분석 실행 (저평가 가치주 발굴)
echo   find_undervalued_stocks.bat -l    # LG생활건강 분석
echo   find_undervalued_stocks.bat -f    # 저평가 가치주 발굴만 실행 (10개)
echo   find_undervalued_stocks.bat -m    # 전체 시장 분석 (500개 종목)
echo   find_undervalued_stocks.bat -v2   # 궁극의 향상된 분석 v2.0 (enhanced_integrated_analyzer_refactored.py 통합)
echo   find_undervalued_stocks.bat -w    # 웹 대시보드 실행
goto :end

:analyze
echo [INFO] 저평가 가치주 발굴 시스템 실행 중...
echo [INFO] 다중 종목 분석 및 저평가 종목 발굴 시작...
python undervalued_stock_finder.py
if %errorlevel% neq 0 (
    echo [ERROR] 저평가 가치주 발굴 실패
    goto :end
)
echo [SUCCESS] 저평가 가치주 발굴 완료

echo [INFO] 궁극의 통합 분석 실행 중...
echo [INFO] LG생활건강 궁극의 분석 시작...
python ultimate_enhanced_analyzer.py
if %errorlevel% neq 0 (
    echo [ERROR] 궁극의 분석 실패
    goto :end
)
echo [SUCCESS] 궁극의 분석 완료

echo [SUCCESS] 전체 분석 완료
goto :end

:lg
echo [INFO] LG생활건강 궁극의 분석 중...
python ultimate_enhanced_analyzer.py
goto :end

:finder
echo [INFO] 저평가 가치주 발굴 시스템 실행 중...
python undervalued_stock_finder.py
goto :end

:market
echo [INFO] 전체 시장 분석 시스템 실행 중...
echo [INFO] KOSPI 전체 종목 분석 시작 (500개 종목)...
python full_market_analyzer.py --max-stocks 500 --workers 10 --min-score 30.0
goto :end

:v2
echo [INFO] 궁극의 향상된 분석 v2.0 실행 중...
echo [INFO] enhanced_integrated_analyzer_refactored.py 핵심 장점 통합...
python ultimate_market_analyzer_v2.py --max-stocks 100 --workers 2 --min-score 30.0
goto :end

:cap
echo [INFO] 코스피 시가총액 상위 종목 분석 시스템 실행 중...
echo [INFO] 궁극의 향상된 분석 v2.0 통합 시스템 사용...
python ultimate_market_analyzer_v2.py --market-cap --top-n 50 --min-score 40.0
goto :end

:comprehensive
echo [INFO] 종합점수 기반 분석 시스템 실행 중...
echo [INFO] 정량적 지표(70%) + 정성적 지표(30%) 통합 분석...
python ultimate_market_analyzer_v2.py --comprehensive --max-stocks 50 --min-comprehensive-score 45.0
goto :end

:news
echo [INFO] 뉴스 분석 중...
python naver_news_api.py
goto :end

:ml
echo [INFO] 머신러닝 모델 훈련 중...
python advanced_system_upgrade.py
goto :end

:backtest
echo [INFO] 백테스팅 실행 중...
python advanced_system_upgrade.py
goto :end

:web
echo [INFO] 웹 대시보드 시작 중...
echo [INFO] 브라우저에서 http://localhost:8501 접속하세요
start http://localhost:8501
python -m streamlit run web_dashboard.py
goto :end

:setup
echo [INFO] 환경 설정 중...
if not exist "venv" (
    echo [INFO] Python 가상환경 생성 중...
    python -m venv venv
    echo [SUCCESS] 가상환경 생성 완료
)

echo [INFO] 가상환경 활성화 중...
call venv\Scripts\activate.bat

echo [INFO] 필수 패키지 설치 중...
pip install -r requirements.txt

if not exist "config.yaml" (
    echo [WARNING] config.yaml 파일이 없습니다. 기본 설정을 생성합니다.
    echo # 저평가 가치주 발굴 시스템 설정 > config.yaml
    echo kis_api: >> config.yaml
    echo   app_key: "your_app_key_here" >> config.yaml
    echo   app_secret: "your_app_secret_here" >> config.yaml
    echo. >> config.yaml
    echo naver_api: >> config.yaml
    echo   client_id: "ZFrT7e9RJ9JcosG30dUV" >> config.yaml
    echo   client_secret: "YsUytWqqLQ" >> config.yaml
    echo [SUCCESS] 기본 설정 파일 생성 완료
)

echo [SUCCESS] 환경 설정 완료
goto :end

:clean
echo [INFO] 임시 파일 정리 중...
if exist "__pycache__" rmdir /s /q "__pycache__"
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f"
for /r . %%f in (temp_*.json) do @if exist "%%f" del /q "%%f"
for /r . %%f in (*.tmp) do @if exist "%%f" del /q "%%f"
echo [SUCCESS] 임시 파일 정리 완료
goto :end

:update
echo [INFO] 시스템 업데이트 중...
if exist ".git" (
    echo [INFO] Git 저장소 업데이트 중...
    git pull origin main
    echo [SUCCESS] Git 업데이트 완료
)
echo [INFO] Python 패키지 업데이트 중...
pip install --upgrade -r requirements.txt
echo [SUCCESS] 패키지 업데이트 완료
echo [SUCCESS] 시스템 업데이트 완료
goto :end

:unknown
echo [ERROR] 알 수 없는 옵션: %1
echo 도움말을 보려면 -h 또는 --help를 사용하세요.
goto :end

:end
echo.
echo 분석 완료. 아무 키나 누르면 종료됩니다.
pause > nul
