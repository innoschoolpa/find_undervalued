# 백테스팅 시스템 사용 가이드

## 🎯 개요

이 백테스팅 시스템은 퀀트 투자 전략의 성과를 검증하고 최적의 파라미터를 찾기 위한 도구입니다.

## 🚀 주요 기능

### 1. 백테스팅 실행
- 과거 데이터를 이용한 전략 성과 검증
- 다양한 성과 지표 계산 (수익률, 샤프 비율, 최대 낙폭 등)
- 리밸런싱 주기 설정 (월별, 분기별)

### 2. 파라미터 최적화
- 그리드 서치 및 랜덤 서치 알고리즘
- 가중치 자동 조정
- 최적 파라미터 자동 탐색

### 3. 전략 비교
- 여러 투자 전략의 성과 비교
- 최적 전략 자동 선별

## 📋 사용법

### 1. 기본 백테스팅 실행

```bash
# 기본 설정으로 백테스팅 실행
python enhanced_integrated_analyzer.py run-backtest

# 커스텀 설정으로 백테스팅 실행
python enhanced_integrated_analyzer.py run-backtest \
    --symbols "005930,000660,035420,051910,006400" \
    --start-date "2023-01-01" \
    --end-date "2024-12-31" \
    --rebalance-frequency "monthly" \
    --initial-capital 10000000
```

### 2. 파라미터 최적화

```bash
# 그리드 서치로 최적화
python enhanced_integrated_analyzer.py optimize-parameters \
    --symbols "005930,000660,035420" \
    --start-date "2023-01-01" \
    --end-date "2024-12-31" \
    --optimization-method "grid_search" \
    --max-iterations 100

# 랜덤 서치로 최적화
python enhanced_integrated_analyzer.py optimize-parameters \
    --optimization-method "random_search" \
    --max-iterations 200
```

### 3. 전략 비교

```bash
# 여러 전략 비교
python enhanced_integrated_analyzer.py compare-strategies \
    --symbols "005930,000660,035420" \
    --strategies "balanced,value_focused,growth_focused" \
    --start-date "2023-01-01" \
    --end-date "2024-12-31"
```

## 📊 성과 지표

### 수익성 지표
- **총 수익률**: 전체 기간 수익률
- **연평균 수익률**: 연환산 수익률
- **샤프 비율**: 위험 대비 수익률

### 리스크 지표
- **최대 낙폭**: 최대 손실률
- **변동성**: 수익률의 표준편차

### 거래 지표
- **승률**: 수익 거래 비율
- **수익 팩터**: 총 수익 / 총 손실
- **평균 수익/손실**: 수익/손실 거래의 평균

## ⚙️ 파라미터 설정

### 분석 요소별 가중치
```yaml
weights:
  opinion_analysis: 25      # 투자의견 분석 (25%)
  estimate_analysis: 30     # 추정실적 분석 (30%)
  financial_ratios: 30      # 재무비율 분석 (30%)
  growth_analysis: 10       # 성장성 분석 (10%)
  scale_analysis: 5         # 규모 분석 (5%)
```

### 재무비율 세부 가중치
```yaml
financial_ratio_weights:
  roe_score: 8              # ROE 점수 (8점)
  roa_score: 5              # ROA 점수 (5점)
  debt_ratio_score: 7       # 부채비율 점수 (7점)
  net_profit_margin_score: 5 # 순이익률 점수 (5점)
  current_ratio_score: 3    # 유동비율 점수 (3점)
  growth_score: 2           # 성장성 점수 (2점)
```

### 등급 기준
```yaml
grade_thresholds:
  A_plus: 80               # A+ 등급 (80점 이상)
  A: 70                    # A 등급 (70-79점)
  B_plus: 60               # B+ 등급 (60-69점)
  B: 50                    # B 등급 (50-59점)
  C_plus: 40               # C+ 등급 (40-49점)
  C: 30                    # C 등급 (30-39점)
  D: 20                    # D 등급 (20-29점)
  F: 0                     # F 등급 (20점 미만)
```

## 🔧 고급 설정

### 리밸런싱 주기
- **monthly**: 매월 첫째 날
- **quarterly**: 분기별 첫째 날

### 최적화 방법
- **grid_search**: 그리드 서치 (체계적 탐색)
- **random_search**: 랜덤 서치 (무작위 탐색)

### 목적 함수
```python
# 기본 목적 함수: 샤프 비율 - 0.5 * 최대 낙폭
score = sharpe_ratio - 0.5 * max_drawdown

# 커스터마이징 가능
score = sharpe_ratio - 0.3 * max_drawdown + 0.1 * total_return
```

## 📁 결과 파일

### 백테스팅 결과
- `backtest_result_[timestamp].json`: 백테스팅 결과 저장
- `optimization_result_[timestamp].json`: 최적화 결과 저장

### 로그 파일
- `logs/backtest_[timestamp].log`: 백테스팅 로그
- `logs/optimization_[timestamp].log`: 최적화 로그

## 🚨 주의사항

### 1. 데이터 품질
- 과거 데이터의 정확성 확인 필요
- 결측 데이터 처리 방법 검토

### 2. 과최적화 방지
- 충분한 샘플 수 확보
- 교차 검증 수행
- 아웃오브샘플 테스트

### 3. 거래 비용
- 실제 거래 시 수수료, 슬리피지 고려
- 리밸런싱 비용 계산

### 4. 시장 환경 변화
- 시장 구조 변화 고려
- 전략의 지속 가능성 검토

## 📈 사용 예시

### 1. 기본 백테스팅
```bash
# 삼성전자, SK하이닉스, NAVER로 2023년 백테스팅
python enhanced_integrated_analyzer.py run-backtest \
    --symbols "005930,000660,035420" \
    --start-date "2023-01-01" \
    --end-date "2023-12-31"
```

### 2. 파라미터 최적화
```bash
# 50회 반복으로 최적 파라미터 탐색
python enhanced_integrated_analyzer.py optimize-parameters \
    --max-iterations 50 \
    --optimization-method "grid_search"
```

### 3. 전략 비교
```bash
# 3가지 전략 비교
python enhanced_integrated_analyzer.py compare-strategies \
    --strategies "balanced,value_focused,growth_focused"
```

## 🔍 문제 해결

### 1. 데이터 로드 실패
- API 키 확인
- 네트워크 연결 상태 확인
- 종목 코드 유효성 검증

### 2. 메모리 부족
- 종목 수 줄이기
- 기간 단축
- 배치 크기 조정

### 3. 최적화 실패
- 반복 횟수 증가
- 파라미터 범위 조정
- 다른 최적화 방법 시도

## 📞 지원

문제가 발생하면 로그 파일을 확인하고, 필요시 개발팀에 문의하세요.

---

**백테스팅은 과거 성과를 바탕으로 한 참고용 도구입니다. 실제 투자 시에는 추가적인 검토가 필요합니다.**
