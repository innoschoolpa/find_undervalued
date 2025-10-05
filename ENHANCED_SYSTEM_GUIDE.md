# 🚀 Enhanced Integrated Analyzer 통합 시스템 가이드

## 📋 개요

Enhanced Integrated Analyzer는 KIS API 연동, 백테스팅, 포트폴리오 최적화 기능을 통합한 종합 투자 분석 시스템입니다.

## 🏗️ 시스템 아키텍처

```
Enhanced Integrated Analyzer
├── 🔧 설정 관리 (Enhanced Config Manager)
├── 📡 KIS API 연동 (KIS API Manager)
├── 📊 백테스팅 엔진 (Backtesting Engine)
├── 📈 포트폴리오 최적화 (Portfolio Optimizer)
├── 🧠 분석 엔진 (Enhanced Analyzer)
└── 🌐 웹 대시보드 (Web Dashboard)
```

## 🚀 빠른 시작

### 1. 시스템 진단
```bash
python run_enhanced_system.py --mode diagnostics
```

### 2. 백테스팅 실행
```bash
python run_enhanced_system.py --mode backtest --symbols 005930 000270 035420
```

### 3. 포트폴리오 최적화
```bash
python run_enhanced_system.py --mode optimize --symbols 005930 000270 035420 012330 005380
```

### 4. 전체 시스템 실행
```bash
python run_enhanced_system.py --mode full --symbols 005930 000270 035420
```

## ⚙️ 설정 방법

### 1. 환경변수 설정
`config.env` 파일을 생성하고 다음 내용을 설정하세요:

```bash
# KIS API 설정
KIS_API_KEY=your_api_key_here
KIS_API_SECRET=your_api_secret_here

# 성능 최적화 설정
MAX_WORKERS=8
KIS_MAX_TPS=8
CACHE_SIZE_MB=512
```

### 2. 설정 파일 사용
```bash
python run_enhanced_system.py --config config.env --mode diagnostics
```

## 📊 주요 기능

### 🔧 Enhanced Config Manager
- **자동 성능 최적화**: CPU/메모리 기반 자동 설정
- **환경변수 관리**: 중첩된 설정 구조 지원
- **시스템 진단**: 하드웨어 리소스 모니터링

```python
from enhanced_config_manager import create_enhanced_config_manager

config_manager = create_enhanced_config_manager()
system_info = config_manager.get_system_info()
performance_config = config_manager.get_performance_config()
```

### 📡 KIS API Manager
- **실시간 데이터 조회**: 주식 가격, 재무 데이터
- **Rate Limiting**: TPS 제한 자동 관리
- **캐싱 시스템**: 중복 요청 최적화

```python
from kis_api_manager import create_kis_api_manager

api_manager = create_kis_api_manager()
price_data = api_manager.get_stock_price("005930")
financial_data = api_manager.get_financial_data("005930")
```

### 📊 Backtesting Engine
- **전략 백테스팅**: 과거 데이터 기반 성과 검증
- **리스크 분석**: 최대 낙폭, 샤프 비율 계산
- **거래 비용 고려**: 실제 거래 환경 시뮬레이션

```python
from backtesting_engine import create_backtesting_engine

engine = create_backtesting_engine()
result = engine.run_backtest(strategy_function, symbols)
print(f"총 수익률: {result.total_return:.2%}")
print(f"샤프 비율: {result.sharpe_ratio:.2f}")
```

### 📈 Portfolio Optimizer
- **평균-분산 최적화**: Markowitz 모델
- **리스크 패리티**: 리스크 균등 분산
- **동일 가중**: 단순 균등 분산

```python
from portfolio_optimizer import create_portfolio_optimizer

optimizer = create_portfolio_optimizer()
results = optimizer.compare_strategies(symbols)
```

## 🎯 실행 모드

### 1. Diagnostics 모드
```bash
python run_enhanced_system.py --mode diagnostics
```
- 시스템 상태 진단
- 하드웨어 리소스 확인
- 설정 검증

### 2. Backtest 모드
```bash
python run_enhanced_system.py --mode backtest --symbols 005930 000270
```
- 백테스팅 실행
- 전략 성과 분석
- 리스크 지표 계산

### 3. Optimize 모드
```bash
python run_enhanced_system.py --mode optimize --symbols 005930 000270 035420
```
- 포트폴리오 최적화
- 전략 비교 분석
- 최적 가중치 계산

### 4. Full 모드
```bash
python run_enhanced_system.py --mode full --symbols 005930 000270
```
- 전체 시스템 실행
- 모든 기능 통합 테스트
- 종합 분석 결과

## 📈 결과 해석

### 백테스팅 결과
- **총 수익률**: 전체 기간 투자 수익률
- **연환산 수익률**: 연간 평균 수익률
- **샤프 비율**: 위험 대비 수익률 (높을수록 좋음)
- **최대 낙폭**: 최악의 손실 구간
- **승률**: 수익 거래 비율

### 포트폴리오 최적화 결과
- **예상 수익률**: 포트폴리오 기대 수익률
- **예상 변동성**: 포트폴리오 리스크 수준
- **다각화 비율**: 분산 투자 효과
- **집중도 리스크**: 포트폴리오 집중도

## 🔧 고급 설정

### 성능 최적화
```bash
# CPU 코어 수 기반 워커 설정
MAX_WORKERS=8

# 메모리 기반 캐시 크기
CACHE_SIZE_MB=1024

# API Rate Limit
KIS_MAX_TPS=10
```

### 분석 설정
```bash
# 분석 타임아웃
ANALYSIS_TIMEOUT=300

# 동시 분석 수
MAX_CONCURRENT_ANALYSES=5

# 데이터 품질 기준
MIN_DATA_QUALITY_SCORE=70.0
```

## 🐳 Docker 배포

### Docker 이미지 빌드
```bash
docker build -t enhanced-analyzer:latest .
```

### 컨테이너 실행
```bash
docker run -p 8000:8000 -v ./data:/app/data enhanced-analyzer:latest
```

### 웹 대시보드 접속
```
http://localhost:8000
```

## 📝 로그 및 모니터링

### 로그 레벨 설정
```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### 결과 파일 저장
- 백테스팅 결과: `backtest_results_YYYYMMDD_HHMMSS.json`
- 포트폴리오 최적화: `portfolio_optimization_YYYYMMDD_HHMMSS.json`
- 시스템 진단: `enhanced_system_results_YYYYMMDD_HHMMSS.json`

## 🚨 주의사항

### KIS API 사용
- 실제 데이터 사용을 위해서는 KIS API 키가 필요합니다
- API 키가 없으면 Mock 데이터로 실행됩니다
- Rate Limiting을 준수하여 API 제한을 피하세요

### 메모리 사용량
- 대용량 데이터 처리 시 메모리 사용량을 모니터링하세요
- `MEMORY_LIMIT_GB` 설정으로 메모리 사용량을 제한할 수 있습니다

### 백테스팅 한계
- 과거 성과가 미래 성과를 보장하지 않습니다
- 거래 비용과 슬리피지를 고려한 결과입니다
- 실제 투자 전 충분한 검증이 필요합니다

## 📞 지원 및 문의

### 문제 해결
1. 로그 파일 확인
2. 시스템 진단 실행
3. 설정 검증
4. 메모리/CPU 사용량 확인

### 성능 최적화
1. `MAX_WORKERS` 설정 조정
2. 캐시 크기 최적화
3. API Rate Limit 조정
4. 배치 크기 설정

---

**Enhanced Integrated Analyzer v2.0**  
*통합 투자 분석 시스템*










