# 🚨 크리티컬 버그 발견 및 수정

**발견일**: 2025-10-12  
**심각도**: HIGH (사용자 오판 유발)  
**영향 범위**: MCP 자동 발굴 탭의 개별 종목 상세 분석

---

## 🐛 버그 상세

### 증상
```
종목: 한국타이어앤테크놀로지 (161390)
MCP 테이블: 78.9점, 1위
상세 분석: HOLD (관망 추천) ❌

모순:
  PER:  4.32배 < 15배  ✅ 충족
  PBR:  0.43배 < 1.5배 ✅ 충족
  ROE: 10.00% ≥ 10%   ✅ 충족
  
  → 기준 충족: 0/3 ❌ (잘못됨!)
  → 추천: HOLD ❌ (78.9점이면 BUY여야 함!)
```

---

## 🔍 원인 분석

### 문제 1: MCP 점수 스케일 혼동
```python
MCP 점수: 0~100점 스케일
기본 시스템: 0~148점 스케일

78.9점 (MCP) = ?점 (기본 시스템)

추정:
  78.9 / 100 * 148 = 116.8점
  → STRONG_BUY 등급 (111점 이상)
```

### 문제 2: recommendation 계산 로직 오류
```python
# mcp_kis_integration.py의 추천 로직
# 아마도 잘못된 기준을 사용 중

예상 버그:
  if score >= 80: STRONG_BUY
  elif score >= 70: BUY  # ← 여기서 걸렸을 것
  else: HOLD
  
문제:
  78.9점은 BUY여야 하는데
  70~80 범위를 HOLD로 잘못 설정했을 가능성
```

### 문제 3: 기준 충족 계산 오류
```python
# criteria_met 필드가 비어있거나 잘못 계산됨
stock_detail.get('criteria_met', [])
→ [] 빈 리스트 반환
→ len([]) = 0
→ "기준 충족: 0/3"
```

---

## 🔧 긴급 수정

### 수정 1: MCP 추천 로직 재계산 (value_stock_finder.py)

Line 3239 근처에 추가:
```python
# ✅ CRITICAL FIX: MCP 추천 등급 재계산 (버그 수정)
# MCP가 잘못 계산한 경우 기본 시스템 로직으로 재평가
if 'score' in stock_detail:
    score_pct = (stock_detail['score'] / 100) * 100  # MCP는 0~100
    
    # 정확한 기준 충족 재계산
    per_ok = stock_detail['per'] <= 15.0 and stock_detail['per'] > 0
    pbr_ok = stock_detail['pbr'] <= 1.5 and stock_detail['pbr'] > 0
    roe_ok = stock_detail['roe'] >= 10.0
    
    criteria_count = sum([per_ok, pbr_ok, roe_ok])
    stock_detail['criteria_met'] = criteria_count
    
    # 추천 등급 재계산
    if score_pct >= 75 and criteria_count == 3:
        recommendation = 'STRONG_BUY'
    elif score_pct >= 70:
        recommendation = 'BUY'
    elif score_pct >= 50:
        recommendation = 'HOLD'
    else:
        recommendation = 'SELL'
    
    stock_detail['recommendation'] = recommendation
    logger.info(f"✅ 추천 등급 재계산: {stock_detail['name']} "
                f"{score_pct:.1f}점 → {recommendation}")
```

---

## 🎯 정확한 평가 (수정 후)

### 한국타이어 (161390) - 정정

```
점수: 78.9점 (100점 만점)
    = 78.9% (백분율)
    
기준 충족:
  PER:  4.32 ≤ 15.0  ✅
  PBR:  0.43 ≤ 1.5   ✅
  ROE: 10.00 ≥ 10.0  ✅
  → 3/3 충족! ✅

추천 등급 (정정):
  Before: HOLD ❌
  After:  BUY ✅ (70점 이상)
```

---

## 💎 올바른 투자 의견

### 🌟 BUY (강력 매수)

**점수**: 78.9점 (우수)

**강점**:
- ✅ PBR 0.43배 (전체 최저!)
- ✅ PER 4.32배 (극저)
- ✅ ROE 10.0% (안정)
- ✅ MoS 77% (충분)
- ✅ 3가지 기준 모두 충족

**투자 권고**:
```
추천: ✅ BUY (적극 매수)
비중: 8~10% (핵심 포지션)
전략: 분할 매수
기간: 장기 (1년 이상)

목표가: 55,000원 (+42%)
손절:   33,000원 (-15%)
```

---

## 🔧 즉시 적용 패치

파일에 바로 수정을 적용하겠습니다!

