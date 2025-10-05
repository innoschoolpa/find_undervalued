# Docker 설치 및 배포 가이드

## Windows에서 Docker 설치

### 1. Docker Desktop for Windows 설치

1. **Docker Desktop 다운로드**
   - https://www.docker.com/products/docker-desktop/ 접속
   - "Download for Windows" 클릭

2. **시스템 요구사항 확인**
   - Windows 10 64-bit: Pro, Enterprise, 또는 Education (Build 16299 이상)
   - WSL 2 기능 활성화 필요
   - BIOS에서 가상화 기술 활성화

3. **설치 과정**
   ```bash
   # 설치 후 Docker Desktop 실행
   # 시스템 트레이에서 Docker 아이콘 확인
   docker --version
   docker-compose --version
   ```

### 2. WSL 2 설정 (필요시)

```bash
# PowerShell 관리자 권한으로 실행
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# WSL 2 업데이트
wsl --set-default-version 2

# Ubuntu 설치 (선택사항)
wsl --install -d Ubuntu
```

## Docker 배포 테스트

### 1. 기본 배포 테스트

```bash
# 프로젝트 루트에서
cd deploy/docker

# 이미지 빌드
docker build -t enhanced-analyzer:latest -f Dockerfile ../..

# 컨테이너 실행
docker run -d --name analyzer-test -p 8000:8000 enhanced-analyzer:latest

# 상태 확인
docker ps
docker logs analyzer-test
```

### 2. Docker Compose 배포

```bash
# 전체 스택 배포
docker-compose up -d

# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs analyzer

# 정리
docker-compose down
```

### 3. 헬스체크 및 테스트

```bash
# API 엔드포인트 테스트
curl http://localhost:8000/health

# 메트릭 확인
curl http://localhost:8000/metrics

# 분석 API 테스트
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "005930"}'
```

## 트러블슈팅

### 일반적인 문제들

1. **Docker Desktop 시작 안됨**
   ```bash
   # Windows 기능 확인
   # Hyper-V 활성화
   # WSL 2 설치 확인
   ```

2. **포트 충돌**
   ```bash
   # 포트 사용 중인 프로세스 확인
   netstat -ano | findstr :8000
   
   # 다른 포트 사용
   docker run -p 8001:8000 enhanced-analyzer:latest
   ```

3. **메모리 부족**
   ```bash
   # Docker Desktop 설정에서 메모리 할당량 증가
   # 최소 4GB 권장
   ```

## 대안 배포 방법

Docker가 설치되지 않은 경우:

### 1. Python 가상환경 배포
```bash
# 가상환경 생성
python -m venv venv
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 서비스 실행
python enhanced_integrated_analyzer_refactored.py
```

### 2. Windows Service 배포
```bash
# NSSM 사용
nssm install EnhancedAnalyzer python.exe enhanced_integrated_analyzer_refactored.py
nssm start EnhancedAnalyzer
```

### 3. IIS 배포 (Python 웹앱)
```bash
# wfastcgi 설치
pip install wfastcgi

# IIS에서 Python 웹앱 설정
```

