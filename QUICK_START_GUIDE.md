# 개선된 가치주 발굴 시스템 - 빠른 시작 가이드

## 🚀 5분 만에 시작하기

### 1. 의존성 확인
```bash
# 필수 패키지 확인
pip install streamlit pandas numpy plotly pyyaml

# 개선 모듈 테스트
python value_finder_improvements.py
```

### 2. 시스템 실행
```bash
# Streamlit UI로 실행 (권장)
streamlit run value_stock_finder.py

# 웹 브라우저가 자동으로 열리면서 http://localhost:8501 접속
```

### 3. 화면 구성
```
┌─────────────────────────────────────────────────┐
│  💎 저평가 가치주 발굴 시스템 (v2.0 Enhanced)    │
├─────────────────────────────────────────────────┤
│  사이드바:                                       │
│  - 분석 모드 선택 (전체/개별)                    │
│  - 분석 대상 종목 수 (5~250)                     │
│  - API 호출 전략                                 │
│  - 가치주 기준 (PER/PBR/ROE)                     │
│                                                  │
│  메인 화면:                                      │
│  - 추천 종목 테이블                              │
│  - 상세 분석 (클릭 시)                           │
│  - 품질 지표 (FCF Yield, F-Score 등)             │
│  - 회계 이상 징후 경고                           │
└─────────────────────────────────────────────────┘
```

---

## 📊 주요 개선사항 (v2.0)

### ✅ 1. 음수 PER 대응
- **이전**: 적자 기업 자동 탈락
- **현재**: EV/Sales, P/S 기반 대체 평가
- **효과**: 경기 저점의 가치주 발굴

### ✅ 2. 품질 지표 (43점)
- **FCF Yield** (0-15점): 현금흐름 품질
- **Interest Coverage** (0-10점): 이자보상배율
- **Piotroski F-Score** (0-18점): 9개 항목 종합 평가
- **효과**: 가치 함정 회피

### ✅ 3. 데이터 품질 가드
- 더미 데이터 자동 감지
- 회계 이상 징후 경고 (일회성 손익, CFO 괴리 등)
- **효과**: 오판 방지

### ✅ 4. 섹터 보너스 축소
- **이전**: 최대 25점 (이중카운팅)
- **현재**: 최대 10점 (단순화)
- **효과**: 공정한 평가

### ✅ 5. 디버그 로깅
- 종목별 JSON 로그 (`logs/debug_evaluations/`)
- 점수 구성 요소 상세 기록
- **효과**: 추천 사유 투명성

---

## 🎯 사용 팁

### 필터링 전략
```
1단계: 데이터 품질 체크 통과
2단계: 점수 60% 이상 (BUY 등급)
3단계: 회계 이상 징후 없음
4단계: Piotroski F-Score 6점 이상 (있는 경우)
5단계: FCF Yield > 3% (있는 경우)
```

### 포트폴리오 구성 예시
| 등급 | 비중 | 종목 수 |
|------|------|---------|
| STRONG_BUY | 60-70% | 3-4종목 |
| BUY | 30-40% | 1-2종목 |

### 리밸런싱 주기
- **권장**: 분기별 1회 (3개월)
- **조기 매도**: 등급 C 이하로 하락 시
- **추가 매수**: 등급 상승 시 고려

---

## 📈 점수 체계 (v2.0)

### 총점 구성 (148점 만점)
1. **PER/PBR/ROE 기본 점수**: 최대 60점
   - 섹터 퍼센타일 기반 (각 20점)
   - 음수 PER 시 대체 평가 적용

2. **품질 지표 점수**: 최대 43점
   - FCF Yield: 15점
   - Interest Coverage: 10점
   - Piotroski F-Score: 18점

3. **섹터 보너스**: 최대 10점
   - PER 기준 충족: 3점
   - PBR 기준 충족: 3점
   - ROE 기준 충족: 4점

4. **안전마진(MoS)**: 최대 35점
   - Justified Multiple 기반

### 등급 기준 (백분율)
| 등급 | 백분율 | 점수 범위 | 의미 |
|------|--------|-----------|------|
| A+ | 75%+ | 111+ | 매우 우수한 가치주 |
| A | 65-75% | 96-110 | 우수한 가치주 |
| B+ | 55-65% | 81-95 | 양호한 가치주 |
| B | 45-55% | 67-80 | 보통 수준 |
| C+ | 35-45% | 52-66 | 주의 필요 |
| C | 35%- | 51- | 투자 부적합 |

---

## 🔍 상세 분석 화면

### 종목 클릭 시 표시 정보
```
기본 정보
├─ 종목코드/명
├─ 현재가
├─ 시가총액
└─ 섹터

밸류에이션 (60점)
├─ PER 점수 (20점)
├─ PBR 점수 (20점)
└─ ROE 점수 (20점)

품질 지표 (43점) ⭐ NEW
├─ FCF Yield (15점)
├─ Interest Coverage (10점)
└─ Piotroski F-Score (18점)
    ├─ 수익성 (4점)
    ├─ 레버리지/유동성 (3점)
    └─ 운영효율성 (2점)

섹터 평가 (10점)
├─ PER 기준 충족 여부
├─ PBR 기준 충족 여부
└─ ROE 기준 충족 여부

안전마진 (35점)
├─ 내재가치
├─ 안전마진 %
└─ 신뢰도

회계 품질 ⭐ NEW
├─ 일회성 손익 비중
├─ 현금흐름 품질
├─ 매출채권/재고 추이
└─ 이상 징후 경고
```

---

## 🚨 경고 신호

### 즉시 재검토 필요
- ⛔ **회계 이상 징후 (HIGH)**: 매도 고려
- ⛔ **등급 C 이하**: 매도 검토
- ⛔ **ROE < 0 and PBR > 3**: 자동 SELL

### 주의 필요
- ⚠️ **회계 이상 징후 (MEDIUM)**: 면밀한 분석
- ⚠️ **F-Score < 4**: 품질 낮음
- ⚠️ **FCF Yield < 0**: 현금흐름 부족

---

## 💾 디버그 로그 활용

### 로그 위치
```bash
logs/debug_evaluations/005930_1736553600.json
```

### 로그 구조
```json
{
  "symbol": "005930",
  "name": "삼성전자",
  "timestamp": "2025-01-11T10:00:00",
  "score": 98.5,
  "score_percentage": 66.6,
  "grade": "A (우수)",
  "recommendation": "BUY",
  "details": {
    "per_score": 18.5,
    "pbr_score": 19.2,
    "roe_score": 17.8,
    "quality_score": 35.0,
    "sector_bonus": 8.0,
    "mos_score": 28.0,
    "fcf_yield": 8.5,
    "interest_coverage": 12.3,
    "piotroski_fscore": 8,
    "accounting_anomalies": {}
  },
  "raw_metrics": {
    "per": 8.5,
    "pbr": 1.2,
    "roe": 15.3,
    "market_cap": 500000000000000,
    "current_price": 75000
  }
}
```

### 분석 방법
```bash
# 특정 종목 로그 조회
cat logs/debug_evaluations/005930_*.json | jq '.'

# 모든 종목의 점수 분포
ls logs/debug_evaluations/*.json | xargs -I {} jq '.score_percentage' {} | sort -n

# 회계 이상 징후 종목 찾기
grep -l "accounting_anomalies" logs/debug_evaluations/*.json
```

---

## 🛠️ 문제 해결

### Q1: "더미 데이터 감지" 메시지가 많이 나와요
**A**: 외부 데이터 제공자(KIS API, DART 등) 연결 상태 확인
```bash
# config.yaml 확인
cat config.yaml | grep -A5 "kis_api:"

# API 키 유효성 확인
python debug_api_call.py
```

### Q2: Piotroski F-Score가 항상 0이에요
**A**: 전년도 비교 데이터가 부족할 수 있습니다.
- 최소 2년치 재무제표 데이터 필요
- 일부 종목은 계산 불가 (정상)

### Q3: 추천 종목이 너무 적어요
**A**: 필터 기준을 완화하세요
```python
# config.yaml 수정
thresholds:
  min_ml_signal: 0.3  # 0.3 → 0.2로 낮춤
  min_composite_signal: 0.4  # 0.4 → 0.3으로 낮춤
```

---

## 📚 추가 자료

### 관련 문서
- `VALUE_FINDER_IMPROVEMENTS_SUMMARY.md`: 상세 개선사항
- `value_finder_improvements.py`: 개선 모듈 소스
- `backtest_value_finder.py`: 백테스트 프레임워크

### 이론적 배경
- **Piotroski F-Score**: [원문 논문](https://www.chicagobooth.edu/~/media/FE874EE65F624AAEBD0166B1974FD74D.pdf)
- **Justified Multiples**: CFA Level II Equity Valuation
- **Value Investing**: Benjamin Graham - "The Intelligent Investor"

### 커뮤니티
- GitHub Issues: 버그 리포트 및 기능 요청
- Discussions: 사용법 질문 및 전략 공유

---

## 🎓 학습 자료

### 초보자용
1. **가치투자 기초**
   - PER, PBR, ROE의 의미
   - 안전마진 개념
   - 포트폴리오 분산

2. **시스템 이해**
   - 점수 계산 방식
   - 등급 기준
   - 리밸런싱 전략

### 고급 사용자용
1. **커스터마이징**
   - 섹터별 기준 조정
   - 가중치 튜닝
   - 백테스트 실행

2. **알고리즘 개선**
   - 새로운 지표 추가
   - 점수 체계 수정
   - 최적화 알고리즘

---

**마지막 업데이트**: 2025-01-11
**버전**: v2.0 Enhanced
**작성자**: AI Assistant (Claude Sonnet 4.5)

**면책조항**: 본 시스템은 투자 참고용이며, 투자 권유가 아닙니다. 모든 투자 결정은 투자자 본인의 판단과 책임 하에 이루어져야 합니다.

