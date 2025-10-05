# Docker Desktop 시작 가이드

## Windows에서 Docker Desktop 시작하기

### 1. Docker Desktop 실행
1. **시작 메뉴**에서 "Docker Desktop" 검색
2. **Docker Desktop** 애플리케이션 클릭하여 실행
3. 시스템 트레이에서 Docker 아이콘 확인

### 2. 시작 확인
Docker Desktop이 완전히 시작되면:
- 시스템 트레이에 Docker 아이콘이 나타남
- 아이콘이 초록색으로 변경됨
- "Docker Desktop is running" 메시지 표시

### 3. 명령어로 확인
```bash
# Docker 상태 확인
docker info

# Docker 버전 확인
docker --version

# 간단한 테스트
docker run hello-world
```

### 4. 문제 해결

#### Docker Desktop이 시작되지 않는 경우:
1. **관리자 권한으로 실행**
   - Docker Desktop을 우클릭 → "관리자 권한으로 실행"

2. **Windows 기능 확인**
   - 제어판 → 프로그램 → Windows 기능 켜기/끄기
   - Hyper-V 체크
   - Windows Subsystem for Linux 체크

3. **WSL 2 업데이트**
   ```powershell
   # PowerShell 관리자 권한으로 실행
   wsl --update
   wsl --set-default-version 2
   ```

4. **Docker Desktop 재시작**
   - 시스템 트레이에서 Docker 아이콘 우클릭
   - "Restart Docker Desktop" 선택

#### 메모리 부족 오류:
1. **Docker Desktop 설정**
   - Docker Desktop → Settings → Resources
   - Memory를 4GB 이상으로 설정

2. **기타 실행 중인 프로그램 종료**
   - 불필요한 프로그램 종료하여 메모리 확보

### 5. 시작 시간
- **첫 실행**: 2-3분 소요
- **일반 실행**: 30초-1분 소요

### 6. 시작 완료 확인
```bash
# 이 명령어가 오류 없이 실행되면 Docker가 준비된 상태
docker run --rm hello-world
```

## 대안 방법

Docker Desktop을 사용할 수 없는 경우:

### 1. Python 가상환경으로 실행
```bash
# 가상환경 생성
python -m venv venv
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 애플리케이션 실행
python enhanced_integrated_analyzer_refactored.py
```

### 2. WSL 2에서 Docker 사용
```bash
# WSL 2에서 Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

## 다음 단계

Docker Desktop이 정상적으로 시작되면:
1. `docker build` 명령어로 이미지 빌드
2. `docker run` 명령어로 컨테이너 실행
3. `docker-compose up` 명령어로 전체 스택 실행












