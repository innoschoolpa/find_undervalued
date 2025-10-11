# 가치주 발굴 시스템 - 즉시 실행 가이드

## 🚀 5분 안에 시작하기

### 필수 준비사항

#### 1. 패키지 설치 (필수)
```bash
pip install streamlit pandas plotly
```

#### 2. 선택 패키지 (권장)
```bash
pip install requests pyyaml
```

---

## ✅ 실행 체크리스트

### 필수 체크
- [x] **순서 버그 수정 완료** (v2.1.1)
  - `recommendation` 변수 정의 순서 수정
  - STEP 1→2→3→4 순서로 재구성
  - UnboundLocalError 해결

- [ ] **Python 3.8+** 설치 확인
  ```bash
  python --version
  ```

- [ ] **필수 패키지** 설치 확인
  ```bash
  pip list | grep streamlit
  pip list | grep pandas
  pip list | grep plotly
  ```

### 선택 체크
- [ ] **KIS API 설정** (실시간 데이터용)
  - `config.yaml` 파일에 API 키 입력
  - 없어도 폴백 유니버스로 작동 가능

- [ ] **개선 모듈** (`value_finder_improvements.py`)
  - 음수 PER 대체 평가 활성화
  - 품질 지표 (FCF, F-Score 등)

---

## 🎯 보수적 프리셋 (추천)

### 기본 설정으로 상위 20개만 빠르게 스크리닝

**사이드바 설정**:
```
분석 모드: 전체 종목 스크리닝
분석 대상 종목 수: 20
API 호출 전략: 안전 모드 (배치 처리)

가치주 기준:
- PER 최대값: 12.0
- PBR 최대값: 1.2
- ROE 최소값: 10.0
- 최소 점수: 60.0
```

**예상 결과**:
- STRONG_BUY: 0-3종목 (매우 우수)
- BUY: 3-7종목 (우수)
- HOLD: 5-10종목 (보통)
- SELL: 나머지

---

## 📋 실행 방법

### 1. 기본 실행
```bash
streamlit run value_stock_finder.py
```

**자동 실행**:
- 웹 브라우저 자동 열림 (http://localhost:8501)
- 사이드바에서 설정 조정
- "전체 종목 스크리닝" 버튼 클릭

### 2. 포트 변경 (선택)
```bash
streamlit run value_stock_finder.py --server.port 8502
```

### 3. 외부 접속 허용 (선택)
```bash
streamlit run value_stock_finder.py --server.address 0.0.0.0
```

---

## 🔧 트러블슈팅

### 문제 1: "ModuleNotFoundError: No module named 'streamlit'"
**해결**:
```bash
pip install streamlit pandas plotly
```

### 문제 2: "KIS API 연결 실패"
**해결**: 
- 정상 동작 (폴백 유니버스 사용)
- 실시간 데이터는 제한적
- `config.yaml`에 API 키 설정하면 개선

### 문제 3: "더미 데이터 감지" 메시지 많음
**해결**:
- 정상 동작 (데이터 품질 가드)
- 외부 API 연결 상태 확인
- 대형주 우선 분석 권장

### 문제 4: "UnboundLocalError: recommendation"
**해결**:
- ✅ v2.1.1에서 수정 완료
- 최신 파일 사용 중인지 확인
- line 1556-1608 순서 확인

---

## 💡 사용 팁

### 초보자용
1. **처음 사용 시**: 종목 수 20개, 보수적 기준
2. **결과 확인**: STRONG_BUY부터 검토
3. **CSV 다운로드**: 엑셀에서 추가 분석
4. **개별 분석**: 관심 종목 상세 확인

### 중급자용
1. **점수 조정**: 최소 점수 55-60 범위 실험
2. **섹터별 분석**: 금융업/제조업 등 특화
3. **품질 필터**: Piotroski F-Score 6+ 우선
4. **백테스트**: `backtest_value_finder.py` 활용

### 고급자용
1. **파라미터 튜닝**: MoS 캡 조정 (35→40)
2. **섹터 r, b 설정**: `config.yaml` 커스터마이징
3. **디버그 로그**: `logs/debug_evaluations/` 분석
4. **백테스트 최적화**: 그리드서치 실행

---

## 📊 결과 해석 가이드

### 추천 등급
| 등급 | 의미 | 조치 |
|------|------|------|
| **STRONG_BUY** | 매우 우수한 가치주 | 적극 검토 |
| **BUY** | 우수한 가치주 | 포트폴리오 후보 |
| **HOLD** | 보통 수준 | 관망 또는 소량 |
| **SELL** | 투자 부적합 | 제외 |

### 점수 의미
- **90+점**: A+ 등급 (최우수)
- **80-90점**: A 등급 (우수)
- **70-80점**: B+ 등급 (양호)
- **60-70점**: B 등급 (보통)
- **60점 미만**: 투자 재검토

### 주의사항
- ⚠️ **회계 이상 징후 (HIGH)**: 즉시 제외
- ⚠️ **데이터 신선도**: 180일 이상 오래된 데이터 주의
- ⚠️ **섹터 편향**: 금융/IT 등 특정 섹터 쏠림 주의

---

## 🎯 포트폴리오 구성 예시

### 보수적 전략 (안정성 우선)
```
STRONG_BUY: 60% (3종목)
BUY: 40% (2종목)
총 5종목, 균등 분산
```

### 균형 전략 (수익/안정 균형)
```
STRONG_BUY: 50% (2-3종목)
BUY: 40% (2-3종목)
HOLD: 10% (1종목, 실험)
총 5-7종목
```

### 공격적 전략 (수익 우선)
```
STRONG_BUY: 70% (4-5종목)
BUY: 30% (2-3종목)
총 6-8종목
```

---

## 📈 리밸런싱 전략

### 권장 주기
- **분기별 1회** (3개월마다)
- 시장 급변 시 추가 검토

### 매도 신호
1. 등급 C 이하로 하락
2. 회계 이상 징후 발생
3. Piotroski F-Score 3점 이하
4. 목표가 달성 (30%+)

### 매수 신호
1. 등급 A 이상으로 상승
2. 점수 70점 이상 유지
3. 섹터 기준 3개 완벽 충족
4. FCF Yield 7% 이상

---

## 🔐 면책조항

**투자 판단은 본인 책임**
- 본 시스템은 리서치 보조 도구입니다
- 투자 권유가 아닙니다
- 실제 투자 전 충분한 검토 필요

**데이터 제한**
- 외부 API 의존 (KIS, DART 등)
- 실시간 데이터 아님 (지연 가능)
- 데이터 오류 가능성

**백테스트 미완료**
- 과거 성과 검증 부족
- 점수 컷오프 경험적 기준
- 향후 최적화 필요

---

## 📚 추가 문서

### 상세 가이드
- `QUICK_START_GUIDE.md`: 기능 상세 설명
- `VALUE_FINDER_IMPROVEMENTS_SUMMARY.md`: v2.0 개선사항
- `PATCH_V2.1_SUMMARY.md`: v2.1 Quick Patches
- `IMPROVEMENTS_CHECKLIST.md`: 완료 체크리스트

### 기술 문서
- `value_finder_improvements.py`: 품질 지표 모듈
- `quick_patches_v2_1.py`: 실무 개선 패치
- `backtest_value_finder.py`: 백테스트 프레임워크

---

## 🤝 커뮤니티

### 질문/버그 리포트
- GitHub Issues: 버그 및 기능 요청
- Discussions: 사용법 질문

### 개선 제안
- 새로운 지표 추가
- 섹터별 최적화
- UI/UX 개선

---

## 📝 버전 정보

**현재 버전**: v2.1.1 (Hotfix)
**릴리스 날짜**: 2025-01-11
**주요 수정**: 
- ✅ `recommendation` 순서 버그 수정
- ✅ STEP 1→4 명확한 구조화
- ✅ 중복 함수 제거

**다음 버전**: v2.2 (예정)
- 폴백 캐시 프라임
- CSV 클린 다운로드
- 섹터 파라미터 설정화

---

## 🎉 빠른 시작 체크리스트

실행 전 마지막 확인:

- [ ] Python 3.8+ 설치 확인
- [ ] `pip install streamlit pandas plotly` 완료
- [ ] `streamlit run value_stock_finder.py` 실행
- [ ] 브라우저 자동 열림 확인 (http://localhost:8501)
- [ ] 사이드바에서 "종목 수 20개" 설정
- [ ] "전체 종목 스크리닝" 버튼 클릭
- [ ] 결과 테이블 확인 (STRONG_BUY부터)
- [ ] CSV 다운로드로 저장

**모든 준비 완료! 가치주 발굴을 시작하세요! 🚀**

---

**작성자**: AI Assistant (Claude Sonnet 4.5)  
**기반 리뷰**: 전문 개발자 피드백  
**최종 업데이트**: 2025-01-11 (v2.1.1 Hotfix)

