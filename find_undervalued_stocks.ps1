# 저평가 가치주 발굴 자동화 PowerShell 스크립트
# 사용법: .\find_undervalued_stocks.ps1 [옵션]

param(
    [switch]$Help,
    [switch]$Analyze,
    [switch]$LG,
    [switch]$News,
    [switch]$ML,
    [switch]$Backtest,
    [switch]$Web,
    [switch]$Setup,
    [switch]$Clean,
    [switch]$Update,
    [switch]$Status
)

# 색상 정의
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"
$Magenta = "Magenta"
$Cyan = "Cyan"
$White = "White"

# 로그 함수들
function Write-LogInfo {
    param($Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Blue
}

function Write-LogSuccess {
    param($Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Green
}

function Write-LogWarning {
    param($Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Yellow
}

function Write-LogError {
    param($Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

function Write-LogHeader {
    param($Message)
    Write-Host $Message -ForegroundColor $Magenta
}

# 헤더 출력
function Show-Header {
    Clear-Host
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor $Cyan
    Write-Host "║                    저평가 가치주 발굴 시스템                    ║" -ForegroundColor $Cyan
    Write-Host "║                   AI-Powered Stock Analysis                  ║" -ForegroundColor $Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor $Cyan
    Write-Host ""
}

# 도움말 출력
function Show-Help {
    Write-Host "사용법:" -ForegroundColor $White
    Write-Host "  .\find_undervalued_stocks.ps1 [옵션]"
    Write-Host ""
    Write-Host "옵션:" -ForegroundColor $White
    Write-Host "  -Help              이 도움말 표시"
    Write-Host "  -Analyze           전체 분석 실행"
    Write-Host "  -LG                LG생활건강 분석"
    Write-Host "  -News              뉴스 분석만 실행"
    Write-Host "  -ML                머신러닝 모델 훈련"
    Write-Host "  -Backtest          백테스팅 실행"
    Write-Host "  -Web               웹 대시보드 실행"
    Write-Host "  -Setup             환경 설정"
    Write-Host "  -Clean             임시 파일 정리"
    Write-Host "  -Update            시스템 업데이트"
    Write-Host "  -Status            시스템 상태 확인"
    Write-Host ""
    Write-Host "예시:" -ForegroundColor $White
    Write-Host "  .\find_undervalued_stocks.ps1 -Analyze    # 전체 분석 실행"
    Write-Host "  .\find_undervalued_stocks.ps1 -LG         # LG생활건강 분석"
    Write-Host "  .\find_undervalued_stocks.ps1 -Web        # 웹 대시보드 실행"
}

# 환경 설정
function Setup-Environment {
    Write-LogHeader "🔧 환경 설정 시작"
    
    # Python 가상환경 확인 및 생성
    if (-not (Test-Path "venv")) {
        Write-LogInfo "Python 가상환경 생성 중..."
        python -m venv venv
        Write-LogSuccess "가상환경 생성 완료"
    }
    
    # 가상환경 활성화
    Write-LogInfo "가상환경 활성화 중..."
    & "venv\Scripts\Activate.ps1"
    
    # 필수 패키지 설치
    Write-LogInfo "필수 패키지 설치 중..."
    pip install -r requirements.txt
    
    # 설정 파일 확인
    if (-not (Test-Path "config.yaml")) {
        Write-LogWarning "config.yaml 파일이 없습니다. 기본 설정을 생성합니다."
        New-DefaultConfig
    }
    
    Write-LogSuccess "환경 설정 완료"
}

# 기본 설정 파일 생성
function New-DefaultConfig {
    $configContent = @"
# 저평가 가치주 발굴 시스템 설정
kis_api:
  app_key: "your_app_key_here"
  app_secret: "your_app_secret_here"
  
naver_api:
  client_id: "ZFrT7e9RJ9JcosG30dUV"
  client_secret: "YsUytWqqLQ"

enhanced_integrated_analysis:
  weights:
    opinion_analysis: 20
    estimate_analysis: 25
    financial_ratios: 30
    growth_analysis: 10
    scale_analysis: 5
    valuation_bonus: 10
    
  grade_thresholds:
    A_plus: 85
    A: 75
    B_plus: 65
    B: 55
    C_plus: 45
    C: 35
    D: 25

analysis_settings:
  max_stocks: 100
  parallel_workers: 4
  cache_enabled: true
  log_level: INFO
"@
    
    $configContent | Out-File -FilePath "config.yaml" -Encoding UTF8
    Write-LogSuccess "기본 설정 파일 생성 완료"
}

# 전체 분석 실행
function Start-FullAnalysis {
    Write-LogHeader "📊 전체 분석 실행"
    
    # 1. LG생활건강 분석
    Write-LogInfo "LG생활건강 분석 시작..."
    python lg_life_analysis.py
    if ($LASTEXITCODE -eq 0) {
        Write-LogSuccess "LG생활건강 분석 완료"
    } else {
        Write-LogError "LG생활건강 분석 실패"
        return
    }
    
    # 2. 네이버 뉴스 API 통합 분석
    Write-LogInfo "네이버 뉴스 API 통합 분석 시작..."
    python enhanced_naver_integration.py
    if ($LASTEXITCODE -eq 0) {
        Write-LogSuccess "네이버 뉴스 API 통합 분석 완료"
    } else {
        Write-LogError "네이버 뉴스 API 통합 분석 실패"
        return
    }
    
    # 3. 최종 분석 요약
    Write-LogInfo "최종 분석 요약 생성 중..."
    python final_analysis_summary.py
    if ($LASTEXITCODE -eq 0) {
        Write-LogSuccess "최종 분석 요약 완료"
    } else {
        Write-LogError "최종 분석 요약 실패"
        return
    }
    
    Write-LogSuccess "전체 분석 완료"
}

# LG생활건강 분석
function Start-LGLifeAnalysis {
    Write-LogHeader "🏢 LG생활건강 분석"
    python lg_life_analysis.py
}

# 뉴스 분석
function Start-NewsAnalysis {
    Write-LogHeader "📰 뉴스 분석"
    python naver_news_api.py
}

# 머신러닝 모델 훈련
function Start-MLTraining {
    Write-LogHeader "🤖 머신러닝 모델 훈련"
    python advanced_system_upgrade.py
}

# 백테스팅 실행
function Start-Backtesting {
    Write-LogHeader "📈 백테스팅 실행"
    Write-LogInfo "백테스팅 기능은 advanced_system_upgrade.py에 통합되어 있습니다."
    python advanced_system_upgrade.py
}

# 웹 대시보드 실행
function Start-WebDashboard {
    Write-LogHeader "🌐 웹 대시보드 실행"
    Write-LogInfo "웹 대시보드를 시작합니다..."
    Write-LogInfo "브라우저에서 http://localhost:8501 접속하세요"
    
    # 백그라운드에서 실행
    Start-Process python -ArgumentList "-m", "streamlit", "run", "web_dashboard.py" -WindowStyle Hidden
    
    Write-LogSuccess "웹 대시보드가 시작되었습니다"
    Write-LogInfo "브라우저가 자동으로 열립니다. 종료하려면 Ctrl+C를 누르세요"
    
    # 잠시 대기 후 브라우저 열기
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:8501"
    
    # 사용자 입력 대기
    Write-Host "웹 대시보드가 실행 중입니다. 종료하려면 아무 키나 누르세요..." -ForegroundColor $Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# 시스템 업데이트
function Update-System {
    Write-LogHeader "🔄 시스템 업데이트"
    
    # Git 업데이트
    if (Test-Path ".git") {
        Write-LogInfo "Git 저장소 업데이트 중..."
        git pull origin main
        Write-LogSuccess "Git 업데이트 완료"
    }
    
    # 패키지 업데이트
    Write-LogInfo "Python 패키지 업데이트 중..."
    pip install --upgrade -r requirements.txt
    Write-LogSuccess "패키지 업데이트 완료"
    
    Write-LogSuccess "시스템 업데이트 완료"
}

# 임시 파일 정리
function Clear-TempFiles {
    Write-LogHeader "🧹 임시 파일 정리"
    
    # Python 캐시 파일 삭제
    Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | ForEach-Object { Remove-Item $_ -Recurse -Force }
    Get-ChildItem -Path . -Recurse -Name "*.pyc" | Remove-Item -Force
    
    # 로그 파일 정리 (7일 이상 된 파일)
    Get-ChildItem -Path "logs" -Name "*.log" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Force
    
    # 임시 분석 결과 파일 정리
    Get-ChildItem -Path . -Name "temp_*.json" | Remove-Item -Force
    Get-ChildItem -Path . -Name "*.tmp" | Remove-Item -Force
    
    Write-LogSuccess "임시 파일 정리 완료"
}

# 시스템 상태 확인
function Test-SystemStatus {
    Write-LogHeader "🔍 시스템 상태 확인"
    
    # Python 버전 확인
    $pythonVersion = python --version 2>&1
    Write-LogInfo "Python 버전: $pythonVersion"
    
    # 필수 패키지 확인
    Write-LogInfo "필수 패키지 확인 중..."
    python -c @"
import sys
packages = ['streamlit', 'plotly', 'scikit-learn', 'pandas', 'numpy', 'requests']
missing = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}')
    except ImportError:
        missing.append(pkg)
        print(f'❌ {pkg}')

if missing:
    print(f'\\n누락된 패키지: {missing}')
    sys.exit(1)
else:
    print('\\n✅ 모든 필수 패키지가 설치되어 있습니다.')
"@
    
    # 설정 파일 확인
    if (Test-Path "config.yaml") {
        Write-LogSuccess "설정 파일 존재"
    } else {
        Write-LogWarning "설정 파일이 없습니다"
    }
    
    # API 키 확인
    if ((Get-Content "config.yaml" -ErrorAction SilentlyContinue) -match "your_app_key_here") {
        Write-LogWarning "API 키가 설정되지 않았습니다"
    } else {
        Write-LogSuccess "API 키 설정됨"
    }
}

# 메인 실행 로직
function Main {
    if ($Help) {
        Show-Header
        Show-Help
    }
    elseif ($Analyze) {
        Show-Header
        Setup-Environment
        Start-FullAnalysis
    }
    elseif ($LG) {
        Show-Header
        Start-LGLifeAnalysis
    }
    elseif ($News) {
        Show-Header
        Start-NewsAnalysis
    }
    elseif ($ML) {
        Show-Header
        Start-MLTraining
    }
    elseif ($Backtest) {
        Show-Header
        Start-Backtesting
    }
    elseif ($Web) {
        Show-Header
        Start-WebDashboard
    }
    elseif ($Setup) {
        Show-Header
        Setup-Environment
    }
    elseif ($Clean) {
        Show-Header
        Clear-TempFiles
    }
    elseif ($Update) {
        Show-Header
        Update-System
    }
    elseif ($Status) {
        Show-Header
        Test-SystemStatus
    }
    else {
        Show-Header
        Show-Help
    }
}

# 스크립트 실행
Main
