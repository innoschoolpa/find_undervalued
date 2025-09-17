# 투자의견 분석 시스템

한국투자증권 KIS API를 활용한 국내주식 종목투자의견 분석 시스템입니다.

## 주요 기능

### 1. 투자의견 데이터 수집
- KIS API를 통한 실시간 투자의견 조회
- 종목별, 기간별 투자의견 데이터 수집
- 증권사별 투자의견 추적

### 2. 투자의견 분석
- 단일 종목 투자의견 종합 분석
- 다중 종목 투자의견 비교 분석
- 컨센서스 분석 및 트렌드 파악
- 목표가 분석 및 상승률 계산

### 3. 데이터 처리 및 시각화
- Rich 라이브러리를 활용한 콘솔 출력
- CSV 파일 내보내기 기능
- DataFrame 변환 및 데이터 분석

## 사용법

### 1. 단일 종목 투자의견 분석

```bash
python main.py opinion analyze-opinion 005930 --days 30 --details
```

**옵션:**
- `symbol`: 분석할 종목 코드 (필수)
- `--days, -d`: 분석 기간 (일, 기본값: 30)
- `--export-csv`: CSV 파일로 내보내기
- `--details`: 상세 분석 표시

### 2. 다중 종목 투자의견 비교

```bash
python main.py opinion compare-opinions --symbols "005930,000660,035420,051910" --days 30
```

**옵션:**
- `--symbols, -s`: 비교할 종목 코드들 (쉼표로 구분)
- `--days, -d`: 분석 기간 (일, 기본값: 30)
- `--export-csv`: CSV 파일로 내보내기
- `--ranking-only`: 랭킹만 표시

### 3. 최근 투자의견 조회

```bash
python main.py opinion recent-opinions 005930 --limit 10
```

**옵션:**
- `symbol`: 종목 코드 (필수)
- `--limit, -l`: 조회할 최근 의견 수 (기본값: 10)
- `--changes-only`: 의견 변경된 것만 표시

### 4. API 테스트

```bash
python main.py opinion test-opinion
```

## 파일 구조

```
investment_opinion_models.py      # 데이터 모델 정의
investment_opinion_client.py      # KIS API 클라이언트
investment_opinion_analyzer.py    # 투자의견 분석 엔진
investment_opinion_cli.py         # CLI 인터페이스
test_investment_opinion.py        # 테스트 스크립트
```

## 주요 클래스

### InvestmentOpinionClient
- KIS API와의 통신을 담당
- 투자의견 데이터 수집 및 처리
- API 호출 제한 및 오류 처리

### InvestmentOpinionAnalyzer
- 투자의견 데이터 분석
- 컨센서스 및 트렌드 분석
- 보고서 생성 및 데이터 내보내기

### ProcessedInvestmentOpinion
- 처리된 투자의견 데이터 모델
- 원시 데이터를 분석 가능한 형태로 변환

## 분석 결과 예시

### 요약 정보
- 총 의견 수
- 매수/보유/매도 의견 분포
- 평균/최고/최저 목표가
- 평균 상승률
- 투자의견 트렌드

### 상세 분석
- 최근 의견 변경 수
- 참여 증권사 수
- 컨센서스 점수 및 해석
- 목표가 커버리지
- 증권사별 분석

### 비교 분석
- 목표가 랭킹
- 컨센서스 점수 랭킹
- 투자의견 수 랭킹

## API 제한사항

- KIS API TPS 제한: 20회/초
- 한 번의 호출에 최대 100건 조회 가능
- 토큰 유효기간: 1일 (개인), 3개월 (법인)

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

### 1. 삼성전자 투자의견 분석
```bash
python main.py opinion analyze-opinion 005930 --days 30 --export-csv
```

### 2. 주요 종목 비교 분석
```bash
python main.py opinion compare-opinions --symbols "005930,000660,035420,051910,006400" --days 60
```

### 3. 최근 의견 변경 조회
```bash
python main.py opinion recent-opinions 005930 --changes-only --limit 5
```

이 시스템을 통해 투자 의사결정에 도움이 되는 투자의견 분석을 수행할 수 있습니다.

