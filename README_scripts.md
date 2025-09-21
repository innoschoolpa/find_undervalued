# 🚀 저평가 가치주 발굴 자동화 스크립트 가이드

## 📋 개요

저평가 가치주 발굴 시스템을 자동화하는 다양한 스크립트들을 제공합니다. Windows, Linux, macOS 환경에서 모두 사용할 수 있습니다.

## 🛠️ 제공 스크립트

### 1. **Windows 배치 파일** (`find_undervalued_stocks.bat`)
- Windows 명령 프롬프트(cmd)에서 실행
- 가장 간단하고 빠른 실행

### 2. **PowerShell 스크립트** (`find_undervalued_stocks.ps1`)
- Windows PowerShell에서 실행
- 고급 기능과 색상 출력 지원

### 3. **Linux/macOS 쉘 스크립트** (`find_undervalued_stocks.sh`)
- Bash 쉘에서 실행
- Unix 계열 시스템용

## 🚀 사용법

### Windows에서 사용하기

#### 방법 1: 배치 파일 사용 (추천)
```cmd
# 도움말 보기
find_undervalued_stocks.bat -h

# 전체 분석 실행
find_undervalued_stocks.bat -a

# LG생활건강 분석
find_undervalued_stocks.bat -l

# 웹 대시보드 실행
find_undervalued_stocks.bat -w
```

#### 방법 2: PowerShell 사용
```powershell
# 도움말 보기
.\find_undervalued_stocks.ps1 -Help

# 전체 분석 실행
.\find_undervalued_stocks.ps1 -Analyze

# LG생활건강 분석
.\find_undervalued_stocks.ps1 -LG

# 웹 대시보드 실행
.\find_undervalued_stocks.ps1 -Web
```

### Linux/macOS에서 사용하기

```bash
# 실행 권한 부여 (최초 1회)
chmod +x find_undervalued_stocks.sh

# 도움말 보기
./find_undervalued_stocks.sh -h

# 전체 분석 실행
./find_undervalued_stocks.sh -a

# LG생활건강 분석
./find_undervalued_stocks.sh -l

# 웹 대시보드 실행
./find_undervalued_stocks.sh -w
```

## 📊 주요 기능

### 🔍 분석 기능
- **전체 분석** (`-a`, `--analyze`): 모든 분석을 순차적으로 실행
- **LG생활건강 분석** (`-l`, `--lg`): LG생활건강 종목 분석
- **뉴스 분석** (`-n`, `--news`): 네이버 뉴스 API를 통한 감정 분석
- **머신러닝 훈련** (`-m`, `--ml`): AI 모델 훈련 및 예측
- **백테스팅** (`-b`, `--backtest`): 과거 데이터 기반 전략 검증

### 🌐 웹 인터페이스
- **웹 대시보드** (`-w`, `--web`): Streamlit 기반 대화형 웹 인터페이스
  - 브라우저에서 http://localhost:8501 접속
  - 실시간 데이터 시각화
  - 포트폴리오 관리

### 🔧 시스템 관리
- **환경 설정** (`-s`, `--setup`): Python 가상환경 및 패키지 설치
- **임시 파일 정리** (`-c`, `--clean`): 캐시 및 임시 파일 삭제
- **시스템 업데이트** (`-u`, `--update`): 패키지 및 코드 업데이트
- **상태 확인** (`-status`): 시스템 상태 및 의존성 확인

## 📈 실행 예시

### 1. 처음 사용하는 경우
```bash
# 환경 설정
find_undervalued_stocks.bat -s

# 시스템 상태 확인
find_undervalued_stocks.bat -status
```

### 2. 일상적인 분석
```bash
# LG생활건강 분석
find_undervalued_stocks.bat -l

# 뉴스 감정 분석
find_undervalued_stocks.bat -n

# 웹 대시보드에서 결과 확인
find_undervalued_stocks.bat -w
```

### 3. 전체 분석 실행
```bash
# 모든 분석을 순차적으로 실행
find_undervalued_stocks.bat -a
```

## 🎯 분석 결과

### LG생활건강 분석 결과 예시
```
📊 기본 정보
종목명: LG생활건강
종목코드: 003550
현재가: 75,300원
시가총액: 118,750억원

📈 저평가 요인 분석
✅ 긍정 요인 (6개)
  1. PBR 저평가: PBR 0.44배로 순자산 대비 저평가
  2. 영업이익 고성장: 영업이익 증가율 24.98%로 높은 성장성
  3. 저부채 구조: 부채비율 10.18%로 매우 안정적
  4. 고수익성: 순이익률 22.84%로 높은 수익성

🎯 투자 추천: STRONG_BUY (신뢰도: HIGH)
```

## 🔧 문제 해결

### 일반적인 문제들

#### 1. Python이 설치되지 않음
```bash
# Python 설치 확인
python --version

# Python이 없다면 https://python.org에서 다운로드
```

#### 2. 패키지 설치 실패
```bash
# 환경 설정 다시 실행
find_undervalued_stocks.bat -s

# 또는 수동으로 설치
pip install -r requirements.txt
```

#### 3. 웹 대시보드가 열리지 않음
```bash
# 브라우저에서 수동 접속
# http://localhost:8501

# 포트 충돌 시 다른 포트 사용
streamlit run web_dashboard.py --server.port 8502
```

#### 4. API 키 오류
```bash
# config.yaml 파일에서 API 키 확인
# 네이버 API 키가 올바르게 설정되었는지 확인
```

### 로그 확인
```bash
# 로그 파일 위치
logs/
├── analysis.log
├── error.log
└── system.log
```

## 📚 고급 사용법

### 1. 배치 실행 (Windows)
```cmd
# 여러 분석을 연속으로 실행
find_undervalued_stocks.bat -l && find_undervalued_stocks.bat -n && find_undervalued_stocks.bat -m
```

### 2. 스케줄링 (Windows Task Scheduler)
```cmd
# 매일 오전 9시에 분석 실행
schtasks /create /tn "Stock Analysis" /tr "C:\path\to\find_undervalued_stocks.bat -a" /sc daily /st 09:00
```

### 3. 백그라운드 실행 (Linux/macOS)
```bash
# 백그라운드에서 실행
nohup ./find_undervalued_stocks.sh -a > analysis.log 2>&1 &
```

## 🎨 커스터마이징

### 설정 파일 수정 (`config.yaml`)
```yaml
# 분석 설정 변경
analysis_settings:
  max_stocks: 200        # 분석할 최대 종목 수
  parallel_workers: 8    # 병렬 처리 워커 수
  cache_enabled: true    # 캐시 사용 여부
  log_level: DEBUG       # 로그 레벨
```

### 스크립트 수정
- 각 스크립트는 텍스트 에디터로 수정 가능
- 새로운 분석 기능 추가 가능
- 출력 형식 커스터마이징 가능

## 📞 지원 및 문의

- **문제 신고**: GitHub Issues
- **기능 요청**: GitHub Discussions
- **문서**: README 파일들 참조

## 🎉 결론

이 스크립트들을 사용하면 복잡한 주식 분석 과정을 자동화할 수 있습니다. 

**권장 사용 순서:**
1. `-s` (환경 설정)
2. `-l` (LG생활건강 분석)
3. `-w` (웹 대시보드에서 결과 확인)
4. `-a` (전체 분석 실행)

자동화된 분석으로 더 효율적인 투자 결정을 내리세요! 🚀
