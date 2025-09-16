# Find Undervalued Stocks

한국 주식시장에서 저평가된 가치주를 찾는 AI 기반 분석 시스템입니다.

## 🚀 주요 기능

### 📊 다중 데이터 소스 통합
- **KIS OpenAPI**: 한국투자증권 실시간 주식 데이터
- **DART API**: 전자공시시스템 재무제표 데이터
- **KOSPI 마스터 데이터**: 상장 종목 정보

### 🔍 고급 분석 기능
- **재무비율 분석**: PER, PBR, ROE, ROA 등 종합 분석
- **성장성 분석**: 매출, 영업이익, 순이익 성장률
- **안정성 분석**: 부채비율, 유동비율, 자기자본비율
- **수익성 분석**: 매출총이익률, 영업이익률, 순이익률
- **DART 포괄적 재무 분석**: 단일회사 전체 재무제표 분석

### ⚡ 병렬 처리 및 성능 최적화
- **병렬 분석**: 다중 워커를 통한 동시 처리
- **캐싱 시스템**: DART 기업 고유번호 24시간 캐시
- **TPS 제한**: API 호출 제한 준수
- **배치 처리**: 효율적인 대량 데이터 처리

### 🎯 AI 기반 투자 신호
- **ML 신호**: 머신러닝 기반 투자 매력도 점수
- **가치 신호**: 저평가 종목 식별
- **품질 신호**: 재무 건전성 평가
- **모멘텀 신호**: 가격 추세 분석

## 🛠️ 설치 및 설정

### 1. 저장소 클론
```bash
git clone https://github.com/innoschoolpa/find_undervalued.git
cd find_undervalued
```

### 2. 가상환경 설정
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 설정 파일 구성
`config.yaml` 파일에서 API 키를 설정하세요:

```yaml
api:
  kis_api:
    app_key: "YOUR_KIS_APP_KEY"
    app_secret: "YOUR_KIS_APP_SECRET"
    account_number: "YOUR_ACCOUNT_NUMBER"
  
  dart:
    api_key: "YOUR_DART_API_KEY"
```

## 📖 사용법

### 기본 분석 실행
```bash
# 시가총액 상위 100개 종목 분석
python advanced_analyzer.py analyze --count 100 --display 20

# 병렬 처리 테스트
python advanced_analyzer.py test-parallel-processing --count 10 --display 10
```

### DART 기업 고유번호 관리
```bash
# DART 상태 확인
python advanced_analyzer.py dart-info

# DART 데이터 새로고침
python advanced_analyzer.py dart-refresh

# 기업 검색
python advanced_analyzer.py dart-search 삼성 --limit 10
```

### 개별 모듈 테스트
```bash
# 재무비율 분석
python financial_ratio_analyzer.py

# DART 연결 테스트
python test_dart_connection.py

# DART 개선사항 테스트
python test_dart_improvements.py
```

## 📁 프로젝트 구조

```
find_undervalued/
├── advanced_analyzer.py          # 메인 분석 시스템
├── corpCode.py                   # DART 기업 고유번호 관리
├── dart_comprehensive_analyzer.py # DART 포괄적 재무 분석
├── dart_financial_analyzer.py    # DART 기본 재무 분석
├── financial_ratio_analyzer.py   # 재무비율 분석
├── growth_ratio_analyzer.py      # 성장성 분석
├── stability_ratio_analyzer.py   # 안정성 분석
├── profit_ratio_analyzer.py      # 수익성 분석
├── balance_sheet_analyzer.py     # 대차대조표 분석
├── income_statement_analyzer.py  # 손익계산서 분석
├── stock_info_analyzer.py        # 주식 정보 분석
├── sector_analyzer.py            # 섹터 분석
├── estimate_performance_analyzer.py # 실적 추정 분석
├── kis_data_provider.py          # KIS API 데이터 제공자
├── kis_token_manager.py          # KIS 토큰 관리
├── parallel_utils.py             # 병렬 처리 유틸리티
├── kospi_master_download.py      # KOSPI 마스터 데이터 다운로드
├── main.py                       # 메인 실행 파일
├── config.yaml                   # 설정 파일
├── requirements.txt              # 의존성 목록
└── README.md                     # 프로젝트 문서
```

## 🔧 주요 개선사항

### DART 기업 고유번호 처리 개선
- ✅ **캐싱 시스템**: 24시간 로컬 캐시로 API 호출 최소화
- ✅ **유사도 매칭**: 정확한 매칭 + 퍼지 매칭으로 매칭률 향상
- ✅ **에러 처리 강화**: 상세한 로깅 및 폴백 처리
- ✅ **성능 최적화**: 메모리 캐시 및 배치 처리
- ✅ **설정 관리**: YAML 기반 설정 파일로 유연한 관리

### 병렬 처리 최적화
- ✅ **TPS 제한**: KIS API 호출 제한 준수
- ✅ **배치 처리**: 효율적인 대량 데이터 처리
- ✅ **진행률 표시**: 실시간 처리 상태 모니터링
- ✅ **에러 복구**: 재시도 메커니즘 및 부분 성공 처리

## 📊 분석 결과 예시

```
🏆 병렬 처리 결과 TOP 10
┏━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ 순위 ┃ 종목코드 ┃ 종목명   ┃ 시가총액 ┃   현재가 ┃     PER ┃   ROE ┃ 종합점수┃
┡━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│  1   │  000660  │ SK하이닉스│ 2,409,6… │ 348,000… │  12.8배 │ 37.5% │  95.0점 │
│  2   │  000270  │ 기아     │ 400,483… │ 101,400… │   4.2배 │ 16.5% │  90.0점 │
│  3   │  005930  │ 삼성전자 │ 4,528,5… │ 79,400원 │  16.0배 │  6.6% │  65.0점 │
└──────┴──────────┴──────────┴──────────┴──────────┴─────────┴───────┴─────────┘
```

## ⚠️ 주의사항

1. **API 키 보안**: API 키를 안전하게 관리하고 공개하지 마세요
2. **사용 제한**: 각 API의 사용 제한을 준수하세요
3. **투자 위험**: 이 도구는 참고용이며, 투자 결정은 신중히 하세요
4. **데이터 정확성**: 실시간 데이터의 정확성을 보장하지 않습니다

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 생성해 주세요.

---

**면책조항**: 이 도구는 교육 및 연구 목적으로 제작되었습니다. 투자 결정에 대한 책임은 사용자에게 있습니다.
