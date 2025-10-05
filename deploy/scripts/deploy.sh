#!/bin/bash

# Enhanced Analyzer 배포 스크립트
# 사용법: ./deploy.sh [staging|production] [version]

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
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

# 환경 설정
ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
NAMESPACE="enhanced-analyzer"
IMAGE_NAME="enhanced-analyzer"
REGISTRY="your-registry.com"

# 환경별 설정
if [ "$ENVIRONMENT" = "production" ]; then
    KUBE_CONFIG=${KUBE_CONFIG_PRODUCTION}
    DOMAIN="analyzer.yourdomain.com"
    REPLICAS=3
    RESOURCES_CPU="1000m"
    RESOURCES_MEMORY="2Gi"
elif [ "$ENVIRONMENT" = "staging" ]; then
    KUBE_CONFIG=${KUBE_CONFIG_STAGING}
    DOMAIN="staging.analyzer.yourdomain.com"
    REPLICAS=1
    RESOURCES_CPU="500m"
    RESOURCES_MEMORY="1Gi"
else
    log_error "Invalid environment: $ENVIRONMENT. Use 'staging' or 'production'"
    exit 1
fi

log_info "Starting deployment to $ENVIRONMENT environment"
log_info "Version: $VERSION"
log_info "Namespace: $NAMESPACE"

# kubectl 설정 확인
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is not installed"
    exit 1
fi

# Kubernetes 클러스터 연결 확인
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

log_success "Kubernetes cluster connection verified"

# 네임스페이스 생성
log_info "Creating namespace $NAMESPACE if it doesn't exist"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# ConfigMap 적용
log_info "Applying ConfigMap"
kubectl apply -f deploy/kubernetes/configmap.yaml -n $NAMESPACE

# Secret 생성 (필요시)
log_info "Creating secrets"
kubectl create secret generic analyzer-secrets \
    --from-literal=api-key=${API_KEY} \
    --from-literal=db-password=${DB_PASSWORD} \
    -n $NAMESPACE \
    --dry-run=client -o yaml | kubectl apply -f -

# 서비스 배포
log_info "Deploying services"
kubectl apply -f deploy/kubernetes/redis-deployment.yaml -n $NAMESPACE
kubectl apply -f deploy/kubernetes/postgres-deployment.yaml -n $NAMESPACE

# 메인 애플리케이션 배포
log_info "Deploying main application"
kubectl apply -f deploy/kubernetes/analyzer-deployment.yaml -n $NAMESPACE
kubectl apply -f deploy/kubernetes/analyzer-service.yaml -n $NAMESPACE

# 이미지 업데이트
log_info "Updating image to $REGISTRY/$IMAGE_NAME:$VERSION"
kubectl set image deployment/analyzer-deployment \
    analyzer=$REGISTRY/$IMAGE_NAME:$VERSION \
    -n $NAMESPACE

# 프로덕션 환경의 경우 추가 설정
if [ "$ENVIRONMENT" = "production" ]; then
    log_info "Applying production-specific configurations"
    
    # Ingress 설정
    kubectl apply -f deploy/kubernetes/ingress.yaml -n $NAMESPACE
    
    # HPA 설정
    kubectl apply -f deploy/kubernetes/hpa.yaml -n $NAMESPACE
    
    # 모니터링 설정
    kubectl apply -f deploy/monitoring/prometheus-config.yaml -n monitoring
    kubectl apply -f deploy/monitoring/alertmanager-config.yaml -n monitoring
    
    # 네트워크 정책
    kubectl apply -f deploy/kubernetes/network-policy.yaml -n $NAMESPACE
fi

# 배포 상태 확인
log_info "Waiting for deployment to complete"
kubectl rollout status deployment/analyzer-deployment -n $NAMESPACE --timeout=300s

# 파드 상태 확인
log_info "Checking pod status"
kubectl wait --for=condition=ready pod -l app=analyzer -n $NAMESPACE --timeout=300s

# 헬스체크
log_info "Performing health check"
if kubectl port-forward service/analyzer-service 8000:8000 -n $NAMESPACE &> /dev/null &
then
    PORT_FORWARD_PID=$!
    sleep 10
    
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        kill $PORT_FORWARD_PID 2>/dev/null || true
        exit 1
    fi
    
    kill $PORT_FORWARD_PID 2>/dev/null || true
else
    log_warning "Port forwarding failed, skipping health check"
fi

# 배포 정보 출력
log_info "Deployment completed successfully!"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"
echo "Namespace: $NAMESPACE"
echo "Replicas: $REPLICAS"
echo "Domain: $DOMAIN"
echo ""
echo "Useful commands:"
echo "  kubectl get pods -n $NAMESPACE"
echo "  kubectl logs -f deployment/analyzer-deployment -n $NAMESPACE"
echo "  kubectl describe deployment analyzer-deployment -n $NAMESPACE"
echo ""

# Slack 알림 (선택사항)
if [ ! -z "$SLACK_WEBHOOK" ]; then
    log_info "Sending Slack notification"
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"✅ Enhanced Analyzer deployed to $ENVIRONMENT (v$VERSION)\"}" \
        $SLACK_WEBHOOK &> /dev/null || log_warning "Slack notification failed"
fi

log_success "Deployment script completed"













