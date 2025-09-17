# 추정실적 분석 시스템

한국투자증권 KIS API를 활용한 국내주식 종목추정실적 분석 시스템입니다.

## 주요 기능

### 1. 추정실적 데이터 수집
- KIS API를 통한 실시간 추정실적 조회
- 종목별 추정손익계산서 및 투자지표 데이터 수집
- 데이터 품질 평가 및 검증

### 2. 추정실적 분석
- 단일 종목 추정실적 종합 분석
- 다중 종목 추정실적 비교 분석
- 고품질 데이터 기반 분석
- 재무건전성, 밸류에이션, 성장성 분석

### 3. 데이터 처리 및 시각화
- Rich 라이브러리를 활용한 콘솔 출력
- CSV 파일 내보내기 기능
- DataFrame 변환 및 데이터 분석

## 사용법

### 1. 단일 종목 추정실적 분석

```bash
python main.py estimate analyze-estimate 005930 --details --export-csv
```

**옵션:**
- `symbol`: 분석할 종목 코드 (필수)
- `--export-csv`: CSV 파일로 내보내기
- `--details`: 상세 분석 표시

### 2. 다중 종목 추정실적 비교

```bash
python main.py estimate compare-estimates --symbols "005930,000660,035420,051910"
```

**옵션:**
- `--symbols, -s`: 비교할 종목 코드들 (쉼표로 구분)
- `--export-csv`: CSV 파일로 내보내기
- `--ranking-only`: 랭킹만 표시

### 3. 고품질 추정실적 분석

```bash
python main.py estimate high-quality-estimates --symbols "005930,000660,035420,051910,006400" --min-quality 0.7
```

**옵션:**
- `--symbols, -s`: 분석할 종목 코드들 (쉼표로 구분)
- `--min-quality, -q`: 최소 품질 점수 (0-1)
- `--export-csv`: CSV 파일로 내보내기

### 4. 추정실적 요약 조회

```bash
python main.py estimate estimate-summary 005930
```

**옵션:**
- `symbol`: 종목 코드 (필수)

## 파일 구조

```
estimate_performance_models.py      # 데이터 모델 정의
estimate_performance_client.py      # KIS API 클라이언트
estimate_performance_analyzer.py    # 추정실적 분석 엔진
estimate_performance_cli.py         # CLI 인터페이스
test_estimate_performance.py        # 테스트 스크립트
```

## 주요 클래스

### EstimatePerformanceClient
- KIS API와의 통신을 담당
- 추정실적 데이터 수집 및 처리
- API 호출 제한 및 오류 처리

### EstimatePerformanceAnalyzer
- 추정실적 데이터 분석
- 재무건전성, 밸류에이션, 성장성 분석
- 보고서 생성 및 데이터 내보내기

### ProcessedEstimatePerformance
- 처리된 추정실적 데이터 모델
- 원시 데이터를 분석 가능한 형태로 변환

## 분석 결과 예시

### 요약 정보
- 종목명, 현재가, 등락률
- 매출액, 영업이익, 순이익 및 성장률
- EPS, PER, ROE, EV/EBITDA
- 매출액, 영업이익, EPS 트렌드
- 데이터 품질 점수

### 상세 분석
- 재무건전성 분석 (ROE, 부채비율, 이자보상배율)
- 밸류에이션 분석 (PER, EV/EBITDA)
- 성장성 분석 (매출액, 영업이익, EPS 성장률)
- 데이터 품질 분석 (완성도, 일관성)

### 비교 분석
- PER 랭킹 (저평가 종목 순)
- ROE 랭킹 (수익성 우수 종목 순)
- 데이터 품질 랭킹

## API 제한사항

- KIS API TPS 제한: 20회/초
- 추정실적 데이터는 매월 초 애널리스트 의견 기준
- 종목별 수익추정은 160여개 기업에 한정

## 설정 요구사항

`config.yaml` 파일에 KIS API 인증 정보가 필요합니다:

```yaml
kis_api:
  app_key: "your_app_key"
  app_secret: "your_app_secret"
```

## 오류 처리

- API 호출 실패 시 자동 재시도
- 데이터 부족 시 적절한 메시지 표시
- 네트워크 오류 및 토큰 만료 처리

## 예제 사용법

### 1. 삼성전자 추정실적 분석
```bash
python main.py estimate analyze-estimate 005930 --details --export-csv
```

### 2. 주요 종목 비교 분석
```bash
python main.py estimate compare-estimates --symbols "005930,000660,035420,051910,006400"
```

### 3. 고품질 추정실적 분석
```bash
python main.py estimate high-quality-estimates --symbols "005930,000660,035420,051910,006400" --min-quality 0.8
```

### 4. 추정실적 요약 조회
```bash
python main.py estimate estimate-summary 005930
```

## 데이터 구조

### 추정손익계산서 (6개월)
- 매출액, 매출액증감율
- 영업이익, 영업이익증감율
- 순이익, 순이익증감율

### 투자지표 (8개월)
- EBITDA(십억원)
- EPS(원), EPS 증감율(0.1%)
- PER(배, 0.1%)
- EV/EBITDA(배, 0.1)
- ROE(0.1%)
- 부채비율(0.1%)
- 이자보상배율(0.1%)

### 데이터 품질 평가
- 데이터 완성도 (0-100%)
- 데이터 일관성 (0-1)
- 종합 품질 점수 (0-1)

이 시스템을 통해 투자 의사결정에 도움이 되는 추정실적 분석을 수행할 수 있습니다.
