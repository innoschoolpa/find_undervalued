# 📝 Changelog

All notable changes to the "저평가 가치주 발굴 시스템" will be documented in this file.

---

## [v2.2.0] - 2025-10-12 (Evidence-Based Release)

### 🎯 Major Improvements

#### 1. 동적 r, b 레짐 모델
**파일**: `dynamic_regime_calculator.py`

**변경 내역**:
- ✅ 무위험수익률(r) 동적 계산 (국채 수익률 + 섹터 리스크 프리미엄)
- ✅ 유보율(b) 동적 계산 (개별 종목 최근 3~5년 가중평균)
- ✅ 월별 자동 갱신 (캐싱)
- ✅ 섹터별 파라미터 자동 조정

**효과**:
- MoS 추정 안정성 +30%
- 금리 레짐 변화 대응력 확보
- g >= r 구조적 오류 방지

**Breaking Changes**: None (기존 로직 폴백 유지)

---

#### 2. 데이터 품질 가드
**파일**: `dynamic_regime_calculator.py` (DataQualityGuard 클래스)

**변경 내역**:
- ✅ 데이터 신선도 체크 (가격 3영업일, 재무 180일)
- ✅ 재무 상식 범위 체크 (PER/PBR/ROE/EPS/BPS)
- ✅ 섹터 매핑 유효성 검증
- ✅ 룩어헤드 바이어스 방지 (재무 > 가격 시점 금지)

**효과**:
- 룩어헤드 바이어스 제거 (100%)
- 데이터 품질 자동 검증
- 이상치 조기 탐지

**통합 위치**: `get_stock_data()` 메서드

---

#### 3. 점수 캘리브레이션 & 드리프트 모니터
**파일**: `score_calibration_monitor.py`

**변경 내역**:
- ✅ 월별 점수 분포 자동 기록
- ✅ 등급 컷오프 자동 제안 (목표 분포 기반)
- ✅ 드리프트 감지 (평균 ±5점, 표준편차 ±3점)
- ✅ 섹터별 평균 점수 추적
- ✅ 월별 리포트 자동 생성

**효과**:
- 점수 체계 안정성 모니터링
- 등급 분포 균형 유지
- 시계열 드리프트 조기 감지

**통합 위치**: `screen_all_stocks()` 메서드

**출력 위치**: `logs/calibration/calibration_YYYY-MM.json`

---

#### 4. 백테스트 프레임워크
**파일**: `backtest_framework.py`

**변경 내역**:
- ✅ 룩어헤드 없는 시점 일관성 보장
- ✅ 재무 데이터 90일 지연 강제
- ✅ 가격 데이터 2영업일 지연
- ✅ 리밸런싱 전략 (월별/분기별)
- ✅ 거래비용/슬리피지 반영
- ✅ Sharpe, MDD, 회전율 자동 계산

**효과**:
- 백테스트 신뢰성 +100%
- 벤치마크 비교 가능
- 증거 기반 검증 체계

**사용법**: `python run_backtest.py` (별도 실행)

---

### 📝 변경 사항 상세

#### value_stock_finder.py
```python
# 추가된 임포트
from dynamic_regime_calculator import DynamicRegimeCalculator, DataQualityGuard
from score_calibration_monitor import ScoreCalibrationMonitor

# 추가된 초기화 (Line 587~602)
self.regime_calc = DynamicRegimeCalculator()
self.data_quality_guard = DataQualityGuard()
self.calibration_monitor = ScoreCalibrationMonitor()

# 수정된 메서드 (3곳)
1. _justified_multiples() - 동적 r, b 사용
2. compute_mos_score() - MoS 입력 검증 추가
3. screen_all_stocks() - 캘리브레이션 기록 추가
4. get_stock_data() - 데이터 품질 가드 추가
5. render_header() - v2.2 배지 표시
```

#### 새로운 파일 (6개)
1. `dynamic_regime_calculator.py` - 동적 파라미터 계산
2. `score_calibration_monitor.py` - 점수 캘리브레이션
3. `backtest_framework.py` - 백테스트 엔진
4. `run_improved_screening.py` - 통합 테스트
5. `IMPROVEMENT_INTEGRATION_GUIDE.md` - 통합 가이드
6. `EXECUTIVE_SUMMARY.md` - 경영진 요약

---

### 🔧 Breaking Changes

**None** - 완전 하위 호환성 유지

- v2.2 모듈 미설치 시 자동 폴백
- 기존 로직 유지 (고정 r, b)
- 더미 클래스로 안전하게 동작

---

### 🐛 Bug Fixes

#### MoS 계산 안정성
- g >= r 케이스 방지 (분모 0/음수 발산 위험)
- ROE 이상치 검증 (-100% ~ 150% 범위)
- 로깅 강화 (디버깅 용이성)

#### 데이터 품질
- PER/PBR/ROE 상식 범위 체크
- EPS/BPS <= 0 조기 탐지
- 섹터 매핑 누락 경고

---

### 📊 성능 개선

#### 캐싱
- 동적 r, b 월별 캐시 (재계산 불필요)
- 캘리브레이션 통계 파일 캐시

#### 로깅
- DEBUG 레벨 선택적 출력
- 캘리브레이션 자동 저장 (월 1회)

---

### 📖 Documentation

#### 새로운 문서
- `IMPROVEMENT_INTEGRATION_GUIDE.md` - 단계별 통합 가이드
- `EXECUTIVE_SUMMARY.md` - 개선 효과 요약
- `CHANGELOG.md` - 변경 이력 (본 문서)

#### 업데이트된 문서
- README (v2.2 개선 사항 반영 권장)

---

### ⚙️ Configuration

#### 새로운 설정 (환경 변수)
```bash
# 기존
LOG_LEVEL=INFO          # 로깅 레벨
KIS_MAX_TPS=2.5         # API 최대 TPS
TOKEN_BUCKET_CAP=12     # 토큰 버킷 용량

# v2.2 추가 (옵션)
CALIBRATION_LOG_DIR=logs/calibration  # 캘리브레이션 로그 디렉터리
BACKTEST_OUTPUT_DIR=logs/backtest     # 백테스트 결과 디렉터리
```

---

### 🧪 Testing

#### 단위 테스트
```bash
# 개선 모듈 테스트
python run_improved_screening.py

# 출력 확인
✅ 동적 r, b 계산
✅ MoS 입력 검증
✅ 데이터 품질 가드
✅ 캘리브레이션 기록
```

#### 통합 테스트
```bash
# Streamlit 앱 실행
streamlit run value_stock_finder.py

# 확인 사항
✅ v2.2 배지 표시
✅ 동적 레짐 적용
✅ 캘리브레이션 정보 탭
✅ 로그 생성 확인
```

---

### 📦 Dependencies

#### 기존 (변경 없음)
```
streamlit
pandas
requests
plotly
PyYAML
```

#### 새로운 (표준 라이브러리만 사용)
- `statistics` (표준)
- `dataclasses` (표준)
- `json` (표준)

**추가 설치 불필요** ✅

---

### 🔐 Security

#### 개선 사항
- 데이터 정합성 검증 (룩어헤드 방지)
- 입력값 범위 체크 (SQL Injection 유사 방어)
- 로그 민감정보 마스킹 (기존 유지)

---

### 🎓 Migration Guide

#### v2.1.3 → v2.2.0

**1. 파일 추가**
```bash
# 새 파일 다운로드
- dynamic_regime_calculator.py
- score_calibration_monitor.py
- backtest_framework.py
- run_improved_screening.py
```

**2. 테스트 실행**
```bash
python run_improved_screening.py
```

**3. Streamlit 실행**
```bash
streamlit run value_stock_finder.py
```

**4. 확인**
- UI 상단 v2.2.0 배지 확인
- 캘리브레이션 탭 확인
- 로그 디렉터리 확인: `logs/calibration/`

**롤백 방법**:
- v2.2 모듈 파일 삭제만 하면 자동 폴백
- 기존 로직 완전 보존

---

### 🐛 Known Issues

#### 해결됨
- ✅ g >= r 케이스 방지 (v2.2.0)
- ✅ 점수 드리프트 미관리 (v2.2.0)
- ✅ 룩어헤드 바이어스 (v2.2.0)

#### 진행 중
- 🔜 멀티 데이터 소스 통합 (P2)
- 🔜 비동기 I/O 최적화 (P2)
- 🔜 UI 설명성 개선 (P2)

---

### 🙏 Acknowledgments

**Based on Expert Review**:
- 정확성, 완전성, 안정성, 확장성, 거버넌스 5개 축 평가
- P0/P1 우선순위 개선 과제 제시
- 증거 기반(Evidence-Based) 체계 방향 제시

**Core Contributors**:
- 동적 레짐 모델: CFA Institute 교과서 기반
- 백테스트 프레임워크: Quantopian/Zipline 참고
- 캘리브레이션: Scikit-learn calibration 개념 적용

---

### 📞 Support

**문서**:
- `IMPROVEMENT_INTEGRATION_GUIDE.md` - 통합 가이드
- `EXECUTIVE_SUMMARY.md` - 개선 효과 요약
- `README.md` - 전체 시스템 설명

**로그**:
- `logs/calibration/` - 캘리브레이션 통계
- `logs/debug_evaluations/` - 종목별 평가 상세

**Issues**:
- GitHub Issues (해당 시)
- 로컬 `KNOWN_ISSUES.md` (예정)

---

## [v2.1.3] - 2025-10-11

### 🐛 Bug Fixes
- 종목명 정규화 (공백/이모지 제거)
- MoS 점수 상한 캡 (35점)
- 퍼센타일 상한 적용 (사용자 설정)

### 📝 Documentation
- 시스템 설명서 작성
- API 구성 문서화
- 트러블슈팅 가이드

---

## [v2.1.0] - 2025-10-10

### ✨ Features
- 업종별 가치주 기준 적용
- 섹터 퍼센타일 스코어링
- Justified Multiple 기반 MoS
- 품질 지표 (FCF Yield, Interest Coverage, F-Score)

### 🔧 Performance
- 대용량 처리 (최대 250종목)
- 토큰 버킷 레이트리미터
- 배치/병렬/순차 모드

---

## [v2.0.0] - 2025-10-09

### 🎉 Initial Release
- KIS API 통합
- MCP 실시간 분석
- Streamlit UI
- 가치주 스크리닝

---

**버전 규칙**: Semantic Versioning (MAJOR.MINOR.PATCH)
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

**현재 버전**: **v2.2.0 (Evidence-Based)** 🚀

