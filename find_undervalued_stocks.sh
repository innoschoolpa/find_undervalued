#!/bin/bash
# 저평가 가치주 발굴 자동화 스크립트
# 사용법: ./find_undervalued_stocks.sh [옵션]

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${PURPLE}$1${NC}"
}

# 헤더 출력
print_header() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    저평가 가치주 발굴 시스템                    ║"
    echo "║                   AI-Powered Stock Analysis                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 도움말 출력
show_help() {
    echo -e "${WHITE}사용법:${NC}"
    echo "  ./find_undervalued_stocks.sh [옵션]"
    echo ""
    echo -e "${WHITE}옵션:${NC}"
    echo "  -h, --help              이 도움말 표시"
    echo "  -a, --analyze           전체 분석 실행"
    echo "  -l, --lg                LG생활건강 분석"
    echo "  -n, --news              뉴스 분석만 실행"
    echo "  -m, --ml                머신러닝 모델 훈련"
    echo "  -b, --backtest          백테스팅 실행"
    echo "  -w, --web               웹 대시보드 실행"
    echo "  -s, --setup             환경 설정"
    echo "  -c, --clean             임시 파일 정리"
    echo "  -u, --update            시스템 업데이트"
    echo ""
    echo -e "${WHITE}예시:${NC}"
    echo "  ./find_undervalued_stocks.sh -a    # 전체 분석 실행"
    echo "  ./find_undervalued_stocks.sh -l    # LG생활건강 분석"
    echo "  ./find_undervalued_stocks.sh -w    # 웹 대시보드 실행"
}

# 환경 설정
setup_environment() {
    log_header "🔧 환경 설정 시작"
    
    # Python 가상환경 확인 및 생성
    if [ ! -d "venv" ]; then
        log_info "Python 가상환경 생성 중..."
        python -m venv venv
        log_success "가상환경 생성 완료"
    fi
    
    # 가상환경 활성화
    log_info "가상환경 활성화 중..."
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
    
    # 필수 패키지 설치
    log_info "필수 패키지 설치 중..."
    pip install -r requirements.txt
    
    # 설정 파일 확인
    if [ ! -f "config.yaml" ]; then
        log_warning "config.yaml 파일이 없습니다. 기본 설정을 생성합니다."
        create_default_config
    fi
    
    log_success "환경 설정 완료"
}

# 기본 설정 파일 생성
create_default_config() {
    cat > config.yaml << EOF
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
EOF
    log_success "기본 설정 파일 생성 완료"
}

# 전체 분석 실행
run_full_analysis() {
    log_header "📊 전체 분석 실행"
    
    # 1. LG생활건강 분석
    log_info "LG생활건강 분석 시작..."
    python lg_life_analysis.py
    if [ $? -eq 0 ]; then
        log_success "LG생활건강 분석 완료"
    else
        log_error "LG생활건강 분석 실패"
        return 1
    fi
    
    # 2. 네이버 뉴스 API 통합 분석
    log_info "네이버 뉴스 API 통합 분석 시작..."
    python enhanced_naver_integration.py
    if [ $? -eq 0 ]; then
        log_success "네이버 뉴스 API 통합 분석 완료"
    else
        log_error "네이버 뉴스 API 통합 분석 실패"
        return 1
    fi
    
    # 3. 최종 분석 요약
    log_info "최종 분석 요약 생성 중..."
    python final_analysis_summary.py
    if [ $? -eq 0 ]; then
        log_success "최종 분석 요약 완료"
    else
        log_error "최종 분석 요약 실패"
        return 1
    fi
    
    log_success "전체 분석 완료"
}

# LG생활건강 분석
analyze_lg_life() {
    log_header "🏢 LG생활건강 분석"
    python lg_life_analysis.py
}

# 뉴스 분석
analyze_news() {
    log_header "📰 뉴스 분석"
    python naver_news_api.py
}

# 머신러닝 모델 훈련
train_ml_models() {
    log_header "🤖 머신러닝 모델 훈련"
    python advanced_system_upgrade.py
}

# 백테스팅 실행
run_backtesting() {
    log_header "📈 백테스팅 실행"
    log_info "백테스팅 기능은 advanced_system_upgrade.py에 통합되어 있습니다."
    python advanced_system_upgrade.py
}

# 웹 대시보드 실행
run_web_dashboard() {
    log_header "🌐 웹 대시보드 실행"
    log_info "웹 대시보드를 시작합니다..."
    log_info "브라우저에서 http://localhost:8501 접속하세요"
    
    # 백그라운드에서 실행
    python -m streamlit run web_dashboard.py &
    DASHBOARD_PID=$!
    
    log_success "웹 대시보드가 시작되었습니다 (PID: $DASHBOARD_PID)"
    log_info "종료하려면 Ctrl+C를 누르세요"
    
    # 프로세스 대기
    wait $DASHBOARD_PID
}

# 시스템 업데이트
update_system() {
    log_header "🔄 시스템 업데이트"
    
    # Git 업데이트
    if [ -d ".git" ]; then
        log_info "Git 저장소 업데이트 중..."
        git pull origin main
        log_success "Git 업데이트 완료"
    fi
    
    # 패키지 업데이트
    log_info "Python 패키지 업데이트 중..."
    pip install --upgrade -r requirements.txt
    log_success "패키지 업데이트 완료"
    
    log_success "시스템 업데이트 완료"
}

# 임시 파일 정리
clean_temp_files() {
    log_header "🧹 임시 파일 정리"
    
    # Python 캐시 파일 삭제
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find . -name "*.pyc" -delete 2>/dev/null
    
    # 로그 파일 정리 (7일 이상 된 파일)
    find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null
    
    # 임시 분석 결과 파일 정리
    find . -name "temp_*.json" -delete 2>/dev/null
    find . -name "*.tmp" -delete 2>/dev/null
    
    log_success "임시 파일 정리 완료"
}

# 시스템 상태 확인
check_system_status() {
    log_header "🔍 시스템 상태 확인"
    
    # Python 버전 확인
    python_version=$(python --version 2>&1)
    log_info "Python 버전: $python_version"
    
    # 필수 패키지 확인
    log_info "필수 패키지 확인 중..."
    python -c "
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
"
    
    # 설정 파일 확인
    if [ -f "config.yaml" ]; then
        log_success "설정 파일 존재"
    else
        log_warning "설정 파일이 없습니다"
    fi
    
    # API 키 확인
    if grep -q "your_app_key_here" config.yaml 2>/dev/null; then
        log_warning "API 키가 설정되지 않았습니다"
    else
        log_success "API 키 설정됨"
    fi
}

# 메인 함수
main() {
    # 인수 처리
    case "${1:-}" in
        -h|--help)
            show_help
            ;;
        -a|--analyze)
            print_header
            setup_environment
            run_full_analysis
            ;;
        -l|--lg)
            print_header
            analyze_lg_life
            ;;
        -n|--news)
            print_header
            analyze_news
            ;;
        -m|--ml)
            print_header
            train_ml_models
            ;;
        -b|--backtest)
            print_header
            run_backtesting
            ;;
        -w|--web)
            print_header
            run_web_dashboard
            ;;
        -s|--setup)
            print_header
            setup_environment
            ;;
        -c|--clean)
            print_header
            clean_temp_files
            ;;
        -u|--update)
            print_header
            update_system
            ;;
        -status)
            print_header
            check_system_status
            ;;
        "")
            print_header
            show_help
            ;;
        *)
            log_error "알 수 없는 옵션: $1"
            show_help
            exit 1
            ;;
    esac
}

# 스크립트 시작
main "$@"
