# Kubernetes 배포 가이드

## 클러스터 요구사항

### 최소 요구사항
- **CPU**: 2 cores
- **메모리**: 4GB RAM
- **스토리지**: 20GB
- **Kubernetes**: v1.20+

### 권장 사양
- **CPU**: 4 cores
- **메모리**: 8GB RAM
- **스토리지**: 50GB SSD
- **Kubernetes**: v1.24+

## 배포 단계

### 1. 네임스페이스 생성
```bash
kubectl create namespace enhanced-analyzer
kubectl config set-context --current --namespace=enhanced-analyzer
```

### 2. ConfigMap 생성
```bash
kubectl apply -f configmap.yaml
```

### 3. Secret 생성
```bash
# API 키 등 민감한 정보
kubectl create secret generic analyzer-secrets \
  --from-literal=api-key=your-api-key \
  --from-literal=db-password=your-db-password
```

### 4. 서비스 배포
```bash
# Redis 배포
kubectl apply -f redis-deployment.yaml

# PostgreSQL 배포
kubectl apply -f postgres-deployment.yaml

# 메인 애플리케이션 배포
kubectl apply -f analyzer-deployment.yaml
```

### 5. Ingress 설정
```bash
# Nginx Ingress Controller 설치 (선택사항)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# Ingress 규칙 적용
kubectl apply -f ingress.yaml
```

## 모니터링 및 관리

### 상태 확인
```bash
# 전체 리소스 상태
kubectl get all

# 포드 로그 확인
kubectl logs -f deployment/analyzer-deployment

# 서비스 엔드포인트 확인
kubectl get endpoints
```

### 스케일링
```bash
# 수동 스케일링
kubectl scale deployment analyzer-deployment --replicas=3

# 자동 스케일링 (HPA)
kubectl apply -f hpa.yaml
```

### 업데이트
```bash
# 이미지 업데이트
kubectl set image deployment/analyzer-deployment analyzer=enhanced-analyzer:v2.0.1

# 롤백
kubectl rollout undo deployment/analyzer-deployment
```

## 클라우드 배포

### AWS EKS
```bash
# EKS 클러스터 생성
eksctl create cluster --name enhanced-analyzer --region us-west-2 --nodegroup-name workers --node-type t3.medium --nodes 3

# kubeconfig 설정
aws eks update-kubeconfig --region us-west-2 --name enhanced-analyzer
```

### Google GKE
```bash
# GKE 클러스터 생성
gcloud container clusters create enhanced-analyzer --zone us-central1-a --num-nodes=3

# kubeconfig 설정
gcloud container clusters get-credentials enhanced-analyzer --zone us-central1-a
```

### Azure AKS
```bash
# AKS 클러스터 생성
az aks create --resource-group myResourceGroup --name enhanced-analyzer --node-count 3 --enable-addons monitoring --generate-ssh-keys

# kubeconfig 설정
az aks get-credentials --resource-group myResourceGroup --name enhanced-analyzer
```

## 보안 설정

### RBAC 설정
```bash
kubectl apply -f rbac.yaml
```

### Network Policy
```bash
kubectl apply -f network-policy.yaml
```

### Pod Security Policy
```bash
kubectl apply -f pod-security-policy.yaml
```













