# 🚀 저평가 가치주 발굴 시스템 - 빠른 시작 가이드

## ✅ 최소 실행 요구사항

### 1. Python 환경
- **Python 3.8 이상** 권장 (3.10+ 최적)
- Windows/Mac/Linux 모두 지원

### 2. 필수 패키지 설치

```bash
# 필수 패키지만 설치 (최소 구성)
pip install streamlit pandas plotly requests PyYAML

# 또는 requirements 파일로 일괄 설치
pip install -r requirements_streamlit.txt
```

### 3. 설정 파일 (선택, 없어도 동작)

`config.yaml` 파일을 생성하여 KIS API 연동 (선택 사항):

```yaml
kis_api:
  app_key: "YOUR_KIS_APP_KEY"
  app_secret: "YOUR_KIS_APP_SECRET"
  test_mode: false  # true: 모의투자, false: 실투자
```

**주의**: API 키가 없어도 기본 폴백 모드로 동작합니다!

---

## 🎯 실행 방법

### 방법 1: 직접 실행 (권장)

```bash
streamlit run value_stock_finder.py
```

### 방법 2: Python 스크립트로 실행

```bash
python value_stock_finder.py
```

실행 후 브라우저에서 자동으로 열립니다:
- 기본 주소: `http://localhost:8501`

---

## ⚙️ 환경변수 설정 (고급)

### API 레이트 리미터 조정

```bash
# 초당 요청 수 (기본 2.5)
export KIS_MAX_TPS=2.0

# 토큰 버킷 용량 (기본 12)
export TOKEN_BUCKET_CAP=8

# 로그 레벨 (기본 INFO)
export LOG_LEVEL=DEBUG
```

Windows (PowerShell):
```powershell
$env:KIS_MAX_TPS="2.0"
$env:TOKEN_BUCKET_CAP="8"
$env:LOG_LEVEL="DEBUG"
```

---

## 📊 사용 모드

### 1️⃣ 기본 가치주 스크리닝 (API 없이 동작)
- 사이드바에서 "분석 모드" 선택
- 전체 종목 스크리닝 또는 개별 종목 분석
- 폴백 종목 리스트 사용 (40개 대형주)

### 2️⃣ KIS API 연동 (설정 시 자동 활성화)
- `config.yaml`에 API 키 설정
- 실시간 시가총액순 종목 자동 로딩 (최대 250개)
- MCP 고급 분석 탭 활성화

---

## 🔍 주요 기능

### 📈 점수 체계 (총점 120점)
- **PER/PBR/ROE 기본 점수**: 각 20점 (퍼센타일 기반)
- **업종별 기준 충족 보너스**: 최대 25점 (3개 조건 완벽 충족 시)
- **안전마진(MoS) 점수**: 최대 35점 (Justified Multiple 방식)

### 🎯 업종별 가치주 기준 (자동 적용)
| 업종 | PER | PBR | ROE |
|------|-----|-----|-----|
| 금융 | ≤12 | ≤1.2 | ≥12% |
| 제조 | ≤18 | ≤2.0 | ≥10% |
| 통신 | ≤15 | ≤2.0 | ≥8% |
| 건설 | ≤12 | ≤1.5 | ≥8% |
| IT | ≤25 | ≤3.0 | ≥15% |

### 🚀 API 호출 전략
- **안전 모드**: 배치 처리 (추천, API 한도 안전)
- **빠른 모드**: 병렬 처리 (빠르지만 API 한도 주의)
- **순차 모드**: 하나씩 처리 (느리지만 가장 안전)

---

## 🐛 문제 해결

### 1. `ModuleNotFoundError: No module named 'streamlit'`
```bash
pip install streamlit
```

### 2. KIS API 토큰 만료
- `.kis_token_cache.json` 파일 삭제 후 재실행
- 자동으로 새 토큰 발급

### 3. 종목 데이터 없음
- API 연동 실패 시 폴백 모드로 자동 전환
- 최소 40개 대형주는 항상 제공

### 4. 캐시 문제
- 사이드바 → "개발자 도구" → "캐시 클리어"
- 또는 브라우저 새로고침 (F5)

### 5. 포트 충돌
```bash
# 다른 포트로 실행
streamlit run value_stock_finder.py --server.port 8502
```

---

## 📁 파일 구조

```
find_undervalued/
├── value_stock_finder.py          # ✅ 메인 실행 파일
├── requirements_streamlit.txt     # 필수 패키지
├── config.yaml                    # API 설정 (선택)
├── QUICKSTART.md                  # 이 파일
│
├── financial_data_provider.py     # 재무 데이터 (폴백 가능)
├── sector_contextualizer.py       # 섹터 분석 (폴백 가능)
├── sector_utils.py                # 섹터 벤치마크 (폴백 가능)
├── enhanced_integrated_analyzer_refactored.py  # 통합 분석기 (폴백 가능)
│
└── .kis_token_cache.json          # 토큰 캐시 (자동 생성)
```

**폴백 가능**: 해당 모듈이 없어도 더미 클래스로 대체되어 실행됩니다.

---

## 💡 성능 최적화 팁

### 1. 대용량 분석 시 (100+ 종목)
- "안전 모드" 사용
- `KIS_MAX_TPS=2.0` 으로 낮춤

### 2. 빠른 테스트
- 분석 대상 종목 수: 10~15개
- "빠른 모드" 사용

### 3. 배포 환경
```bash
# Docker에서 실행 시
streamlit run value_stock_finder.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true
```

---

## 📞 지원

### 로그 확인
```bash
# 상세 로그 활성화
export LOG_LEVEL=DEBUG
streamlit run value_stock_finder.py
```

### 디버그 정보
- UI 상단: 현재 시간 및 데이터 소스 확인
- 에러 발생 시: "개발자용 디버그 정보" 확장 패널 확인

---

## 🎓 사용 예시

### 예시 1: 기본 스크리닝 (API 없이)
1. 실행: `streamlit run value_stock_finder.py`
2. 사이드바: "전체 종목 스크리닝" 선택
3. "분석 대상 종목 수": 15개
4. "API 호출 전략": 안전 모드
5. 자동으로 40개 폴백 종목 중 15개 분석

### 예시 2: KIS API 연동 전체 분석
1. `config.yaml`에 API 키 설정
2. 실행: `streamlit run value_stock_finder.py`
3. 사이드바: "분석 대상 종목 수": 100개
4. "API 호출 전략": 안전 모드
5. 시가총액 상위 100개 종목 실시간 분석

### 예시 3: 개별 종목 심화 분석
1. 사이드바: "개별 종목 분석" 선택
2. 종목 선택: 삼성전자 (005930)
3. 업종별 기준 충족 여부 자동 확인
4. MoS 점수, 내재가치, 안전마진 표시

---

**즐거운 가치투자 되세요! 💎**

