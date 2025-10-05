# 리팩토링된 분석 시스템 Docker 이미지
FROM python:3.11-slim

# 메타데이터
LABEL maintainer="Enhanced Analyzer Team"
LABEL description="리팩토링된 고성능 주식 분석 시스템"
LABEL version="2.0.0"

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 권한 설정
RUN chmod +x *.py

# 포트 노출 (웹 인터페이스용)
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# 기본 실행 명령
CMD ["python", "enhanced_integrated_analyzer_refactored.py"]


