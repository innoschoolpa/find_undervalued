# Enhanced Analyzer 배포 가이드

## 📋 목차
1. [개요](#개요)
2. [시스템 요구사항](#시스템-요구사항)
3. [Docker 배포](#docker-배포)
4. [Kubernetes 배포](#kubernetes-배포)
5. [모니터링 설정](#모니터링-설정)
6. [CI/CD 파이프라인](#cicd-파이프라인)
7. [트러블슈팅](#트러블슈팅)

## 개요

Enhanced Analyzer는 리팩토링된 고성능 주식 분석 시스템으로, 다음과 같은 배포 옵션을 제공합니다:

- **Docker**: 단일 컨테이너 배포
- **Kubernetes**: 컨테이너 오케스트레이션
- **클라우드**: AWS EKS, Google GKE, Azure AKS

## 시스템 요구사항

### 최소 요구사항
- **CPU**: 2 cores
- **메모리**: 4GB RAM
- **스토리지**: 20GB
- **네트워크**: 인터넷 연결

### 권장 사양
- **CPU**: 4+ cores
- **메모리**: 8GB+ RAM
- **스토리지**: 50GB+ SSD
- **네트워크**: 안정적인 인터넷 연결

## Docker 배포

### 1. Docker 설치

#### Windows
```powershell
# Docker Desktop 다운로드 및 설치
# https://www.docker.com/products/docker-desktop/

# 설치 확인
docker --version
docker-compose --version
```

#### Linux
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 설치 확인
docker --version
```

### 2. 이미지 빌드 및 실행

```bash
# 프로젝트 루트에서
cd deploy/docker

# 이미지 빌드
docker build -t enhanced-analyzer:latest -f Dockerfile ../..

# 단일 컨테이너 실행
docker run -d \
  --name analyzer \
  -p 8000:8000 \
  -e API_KEY=your-api-key \
  enhanced-analyzer:latest

# Docker Compose 실행
docker-compose up -d
```

### 3. 헬스체크

```bash
# 상태 확인
docker ps
docker logs analyzer

# API 테스트
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

## Kubernetes 배포

### 1. 클러스터 준비

#### 로컬 (minikube)
```bash
# minikube 설치
minikube start --memory=8192 --cpus=4

# kubectl 설정
kubectl config use-context minikube
```

#### 클라우드 (AWS EKS)
```bash
# EKS 클러스터 생성
eksctl create cluster \
  --name enhanced-analyzer \
  --region us-west-2 \
  --nodegroup-name workers \
  --node-type t3.medium \
  --nodes 3

# kubeconfig 설정
aws eks update-kubeconfig --region us-west-2 --name enhanced-analyzer
```

### 2. 네임스페이스 생성

```bash
kubectl create namespace enhanced-analyzer
kubectl config set-context --current --namespace=enhanced-analyzer
```

### 3. 설정 적용

```bash
# ConfigMap 적용
kubectl apply -f deploy/kubernetes/configmap.yaml

# Secret 생성
kubectl create secret generic analyzer-secrets \
  --from-literal=api-key=your-api-key \
  --from-literal=db-password=your-db-password

# 서비스 배포
kubectl apply -f deploy/kubernetes/redis-deployment.yaml
kubectl apply -f deploy/kubernetes/postgres-deployment.yaml
kubectl apply -f deploy/kubernetes/analyzer-deployment.yaml
kubectl apply -f deploy/kubernetes/analyzer-service.yaml
```

### 4. 프로덕션 설정 (선택사항)

```bash
# Ingress 설정
kubectl apply -f deploy/kubernetes/ingress.yaml

# HPA (자동 스케일링)
kubectl apply -f deploy/kubernetes/hpa.yaml

# 네트워크 정책
kubectl apply -f deploy/kubernetes/network-policy.yaml
```

### 5. 배포 확인

```bash
# 파드 상태 확인
kubectl get pods

# 서비스 확인
kubectl get services

# 로그 확인
kubectl logs -f deployment/analyzer-deployment

# 포트 포워딩으로 테스트
kubectl port-forward service/analyzer-service 8000:8000
```

## 모니터링 설정

### 1. Prometheus 설정

```bash
# Prometheus 네임스페이스 생성
kubectl create namespace monitoring

# Prometheus 배포
kubectl apply -f deploy/monitoring/prometheus-config.yaml

# 서비스 확인
kubectl get pods -n monitoring
```

### 2. Grafana 대시보드

```bash
# Grafana 배포
kubectl apply -f deploy/monitoring/grafana-deployment.yaml

# 대시보드 임포트
kubectl apply -f deploy/monitoring/grafana-dashboard.json
```

### 3. 알림 설정

```bash
# Alertmanager 배포
kubectl apply -f deploy/monitoring/alertmanager-config.yaml

# 알림 규칙 확인
kubectl get prometheusrule -n monitoring
```

## CI/CD 파이프라인

### 1. GitHub Actions

```bash
# GitHub 저장소에 시크릿 설정
# Settings > Secrets and variables > Actions

# 필요한 시크릿:
# - KUBE_CONFIG_PRODUCTION
# - KUBE_CONFIG_STAGING
# - SLACK_WEBHOOK
# - API_KEY
# - DB_PASSWORD
```

### 2. GitLab CI

```bash
# GitLab 프로젝트에 변수 설정
# Settings > CI/CD > Variables

# 필요한 변수:
# - KUBE_CONFIG_PRODUCTION
# - KUBE_CONFIG_STAGING
# - SLACK_WEBHOOK
# - API_KEY
# - DB_PASSWORD
```

### 3. 배포 스크립트 사용

#### Linux/macOS
```bash
# 스테이징 배포
./deploy/scripts/deploy.sh staging v1.0.0

# 프로덕션 배포
./deploy/scripts/deploy.sh production v1.0.0
```

#### Windows
```powershell
# 스테이징 배포
.\deploy\scripts\deploy.ps1 -Environment staging -Version v1.0.0

# 프로덕션 배포
.\deploy\scripts\deploy.ps1 -Environment production -Version v1.0.0
```

## 트러블슈팅

### 일반적인 문제들

#### 1. 파드가 시작되지 않음
```bash
# 파드 상태 확인
kubectl describe pod <pod-name>

# 로그 확인
kubectl logs <pod-name>

# 일반적인 원인:
# - 이미지 pull 실패
# - 리소스 부족
# - 환경변수 누락
```

#### 2. 서비스 연결 실패
```bash
# 서비스 엔드포인트 확인
kubectl get endpoints

# 네트워크 정책 확인
kubectl get networkpolicy

# 포트 포워딩 테스트
kubectl port-forward service/analyzer-service 8000:8000
```

#### 3. 메모리 부족
```bash
# 리소스 사용량 확인
kubectl top pods
kubectl top nodes

# 리소스 제한 증가
kubectl patch deployment analyzer-deployment -p '{"spec":{"template":{"spec":{"containers":[{"name":"analyzer","resources":{"limits":{"memory":"4Gi"}}}]}}}}'
```

#### 4. 성능 문제
```bash
# HPA 상태 확인
kubectl get hpa

# 메트릭 확인
kubectl get --raw /apis/metrics.k8s.io/v1beta1/pods

# 스케일링
kubectl scale deployment analyzer-deployment --replicas=5
```

### 로그 수집

```bash
# 애플리케이션 로그
kubectl logs -f deployment/analyzer-deployment

# 시스템 로그
kubectl logs -f -n kube-system <system-pod>

# 이벤트 확인
kubectl get events --sort-by=.metadata.creationTimestamp
```

### 백업 및 복구

```bash
# ConfigMap 백업
kubectl get configmap analyzer-config -o yaml > backup-configmap.yaml

# Secret 백업 (민감한 정보 주의)
kubectl get secret analyzer-secrets -o yaml > backup-secret.yaml

# 배포 롤백
kubectl rollout undo deployment/analyzer-deployment
```

## 지원 및 문의

- **이슈 리포팅**: GitHub Issues
- **문서**: 프로젝트 README
- **커뮤니티**: 프로젝트 Discussions

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.













