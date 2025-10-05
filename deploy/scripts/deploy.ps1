# Enhanced Analyzer 배포 스크립트 (PowerShell)
# 사용법: .\deploy.ps1 -Environment [staging|production] -Version [version]

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("staging", "production")]
    [string]$Environment = "staging",
    
    [Parameter(Mandatory=$false)]
    [string]$Version = "latest",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipHealthCheck
)

# 색상 함수
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# 로그 함수
function Write-Info {
    param([string]$Message)
    Write-ColorOutput "[INFO] $Message" "Cyan"
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "[SUCCESS] $Message" "Green"
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "[WARNING] $Message" "Yellow"
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "[ERROR] $Message" "Red"
}

# 환경 설정
$Namespace = "enhanced-analyzer"
$ImageName = "enhanced-analyzer"
$Registry = "your-registry.com"

# 환경별 설정
if ($Environment -eq "production") {
    $Domain = "analyzer.yourdomain.com"
    $Replicas = 3
    $ResourcesCpu = "1000m"
    $ResourcesMemory = "2Gi"
} else {
    $Domain = "staging.analyzer.yourdomain.com"
    $Replicas = 1
    $ResourcesCpu = "500m"
    $ResourcesMemory = "1Gi"
}

Write-Info "Starting deployment to $Environment environment"
Write-Info "Version: $Version"
Write-Info "Namespace: $Namespace"

# kubectl 설치 확인
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Error "kubectl is not installed or not in PATH"
    exit 1
}

# Kubernetes 클러스터 연결 확인
try {
    kubectl cluster-info | Out-Null
    Write-Success "Kubernetes cluster connection verified"
} catch {
    Write-Error "Cannot connect to Kubernetes cluster"
    exit 1
}

# 네임스페이스 생성
Write-Info "Creating namespace $Namespace if it doesn't exist"
kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -

# ConfigMap 적용
Write-Info "Applying ConfigMap"
kubectl apply -f deploy/kubernetes/configmap.yaml -n $Namespace

# Secret 생성 (환경변수에서)
if ($env:API_KEY -and $env:DB_PASSWORD) {
    Write-Info "Creating secrets"
    kubectl create secret generic analyzer-secrets `
        --from-literal=api-key=$env:API_KEY `
        --from-literal=db-password=$env:DB_PASSWORD `
        -n $Namespace `
        --dry-run=client -o yaml | kubectl apply -f -
} else {
    Write-Warning "API_KEY or DB_PASSWORD environment variables not set, skipping secret creation"
}

# 서비스 배포
Write-Info "Deploying services"
kubectl apply -f deploy/kubernetes/redis-deployment.yaml -n $Namespace
kubectl apply -f deploy/kubernetes/postgres-deployment.yaml -n $Namespace

# 메인 애플리케이션 배포
Write-Info "Deploying main application"
kubectl apply -f deploy/kubernetes/analyzer-deployment.yaml -n $Namespace
kubectl apply -f deploy/kubernetes/analyzer-service.yaml -n $Namespace

# 이미지 업데이트
Write-Info "Updating image to $Registry/$ImageName`:$Version"
kubectl set image deployment/analyzer-deployment `
    analyzer="$Registry/$ImageName`:$Version" `
    -n $Namespace

# 프로덕션 환경의 경우 추가 설정
if ($Environment -eq "production") {
    Write-Info "Applying production-specific configurations"
    
    # Ingress 설정
    kubectl apply -f deploy/kubernetes/ingress.yaml -n $Namespace
    
    # HPA 설정
    kubectl apply -f deploy/kubernetes/hpa.yaml -n $Namespace
    
    # 모니터링 설정
    kubectl apply -f deploy/monitoring/prometheus-config.yaml -n monitoring
    kubectl apply -f deploy/monitoring/alertmanager-config.yaml -n monitoring
    
    # 네트워크 정책
    if (Test-Path "deploy/kubernetes/network-policy.yaml") {
        kubectl apply -f deploy/kubernetes/network-policy.yaml -n $Namespace
    }
}

# 배포 상태 확인
Write-Info "Waiting for deployment to complete"
kubectl rollout status deployment/analyzer-deployment -n $Namespace --timeout=300s

# 파드 상태 확인
Write-Info "Checking pod status"
kubectl wait --for=condition=ready pod -l app=analyzer -n $Namespace --timeout=300s

# 헬스체크
if (-not $SkipHealthCheck) {
    Write-Info "Performing health check"
    
    # 포트 포워딩 시작
    $portForwardJob = Start-Job -ScriptBlock {
        kubectl port-forward service/analyzer-service 8000:8000 -n $using:Namespace
    }
    
    Start-Sleep -Seconds 10
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 30
        if ($response.StatusCode -eq 200) {
            Write-Success "Health check passed"
        } else {
            Write-Error "Health check failed with status code: $($response.StatusCode)"
            Stop-Job $portForwardJob
            Remove-Job $portForwardJob
            exit 1
        }
    } catch {
        Write-Warning "Health check failed: $($_.Exception.Message)"
    } finally {
        Stop-Job $portForwardJob
        Remove-Job $portForwardJob
    }
}

# 배포 정보 출력
Write-Info "Deployment completed successfully!"
Write-Host ""
Write-Host "Environment: $Environment"
Write-Host "Version: $Version"
Write-Host "Namespace: $Namespace"
Write-Host "Replicas: $Replicas"
Write-Host "Domain: $Domain"
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  kubectl get pods -n $Namespace"
Write-Host "  kubectl logs -f deployment/analyzer-deployment -n $Namespace"
Write-Host "  kubectl describe deployment analyzer-deployment -n $Namespace"
Write-Host ""

# Slack 알림 (선택사항)
if ($env:SLACK_WEBHOOK) {
    Write-Info "Sending Slack notification"
    try {
        $body = @{
            text = "✅ Enhanced Analyzer deployed to $Environment (v$Version)"
        } | ConvertTo-Json
        
        Invoke-RestMethod -Uri $env:SLACK_WEBHOOK -Method Post -Body $body -ContentType "application/json"
    } catch {
        Write-Warning "Slack notification failed: $($_.Exception.Message)"
    }
}

Write-Success "Deployment script completed"













