# 섹터 편향 분석

## 📊 가치주 발굴 결과 (섹터 분포)

```
금융             9개 (45%) ⚠️
운송장비·부품    3개 (15%)
운송·창고        3개 (15%)
보험             2개 (10%)
전기·가스        1개 (5%)
통신             1개 (5%)
전기·전자        1개 (5%)
────────────────────────
총 20개
```

## 🔍 원인 분석

### 1. 섹터별 보너스 점수

| 섹터 | 조건 | 보너스 |
|------|------|--------|
| **금융/은행/증권/보험** | PBR < 0.7 | **+10점** ⭐ |
| **금융/은행/증권/보험** | PBR < 1.0 | +5점 |
| IT/바이오/제약 | PER < 25 | +5점 |
| 제조/화학/철강 | PER < 12 & PBR < 1.0 | +10점 |
| 제조/화학/철강 | PER < 15 | +5점 |
| 전력/가스/에너지 | PBR < 1.0 | +8점 |

### 2. 실제 데이터 분석

#### 금융주가 많은 이유
```
신한금융지주: PBR 0.61 → +10점 보너스 → 총 85점
하나금융지주: PBR 0.57 → +10점 보너스 → 총 85점
KB금융:       PBR 0.74 → +5점 보너스  → 총 70점
우리금융:     PBR 0.56 → +10점 보너스 → 총 70점
SK:           PBR 0.58 → +10점 보너스 → 총 100점
```

**금융주의 PBR이 일반적으로 0.4~0.7 수준으로 낮음**
→ PBR < 0.7 조건 쉽게 충족
→ +10점 보너스 받음
→ 점수 상승 → 많이 선정됨

#### 다른 섹터와 비교
```
한국전력(전기·가스): PBR 0.54 → +8점  → 총 100점
LG전자(전기·전자):   PBR 0.64 → +5점  → 총 80점
기아(운송장비):      PBR 0.72 → +5점  → 총 85점
```

**금융주가 +10점을 받기 쉬운 반면, 다른 섹터는 +5~8점**

---

## 💡 해결 방안

### 방안 1: 섹터 보너스 균등화 (추천)

```python
def _get_sector_bonus(self, sector: str, per: float, pbr: float) -> float:
    """섹터별 보너스 점수 (최대 10점, 균등 조정)"""
    try:
        bonus = 0.0
        
        # ✅ 금융주: 보너스 축소 (10 → 5점)
        if '금융' in sector or '은행' in sector or '증권' in sector or '보험' in sector:
            if pbr < 0.5:  # 기준 강화 (0.7 → 0.5)
                bonus += 5  # 축소 (10 → 5)
            elif pbr < 0.8:  # 기준 완화 (1.0 → 0.8)
                bonus += 3  # 축소 (5 → 3)
        
        # ✅ IT/바이오: 보너스 증가
        elif 'IT' in sector or '바이오' in sector or '제약' in sector:
            if per < 20:  # 기준 강화 (25 → 20)
                bonus += 8  # 증가 (5 → 8)
            elif per < 30:
                bonus += 4
        
        # ✅ 제조업: 보너스 증가
        elif '제조' in sector or '화학' in sector or '철강' in sector:
            if per < 12 and pbr < 1.0:
                bonus += 8  # 축소 (10 → 8)
            elif per < 15:
                bonus += 5  # 유지
        
        # ✅ 유틸리티: 보너스 증가
        elif '전력' in sector or '가스' in sector or '에너지' in sector:
            if pbr < 1.0:
                bonus += 8  # 유지
            if per < 10:  # 추가 조건
                bonus += 3
        
        # ✅ 통신: 신규 추가
        elif '통신' in sector:
            if pbr < 1.0 and per < 15:
                bonus += 6
        
        # ✅ 운송: 신규 추가  
        elif '운송' in sector or '물류' in sector:
            if pbr < 1.0:
                bonus += 5
        
        return bonus
    except:
        return 0.0
```

### 방안 2: 섹터별 할당량 (다양성 보장)

```python
def find_real_value_stocks(self, limit: int = 50, criteria: Dict = None, 
                          candidate_pool_size: int = 200,
                          sector_diversification: bool = True) -> Optional[List[Dict]]:
    """
    진짜 가치주 발굴
    
    Args:
        sector_diversification: 섹터 다양성 보장 여부
    """
    ...
    
    if sector_diversification:
        # 섹터별 최대 비중 제한 (예: 30%)
        max_per_sector = int(limit * 0.3)
        
        diversified_stocks = []
        sector_count = {}
        
        for stock in value_stocks:
            sector = stock['sector']
            
            # 섹터별 카운트
            if sector not in sector_count:
                sector_count[sector] = 0
            
            # 섹터 최대치 확인
            if sector_count[sector] < max_per_sector:
                diversified_stocks.append(stock)
                sector_count[sector] += 1
            
            if len(diversified_stocks) >= limit:
                break
        
        return diversified_stocks
    else:
        return value_stocks[:limit]
```

### 방안 3: 섹터 가중치 반영

```python
# 각 섹터의 시장 대표성을 반영
sector_weights = {
    '금융': 0.15,      # 15% 제한
    '전기·전자': 0.25,  # 25%
    'IT': 0.20,        # 20%
    '운송': 0.10,      # 10%
    '보험': 0.08,      # 8%
    '기타': 0.22       # 22%
}
```

---

## 📈 예상 결과

### Before (현재)
```
금융: 9개 (45%) ⚠️ 편중
기타: 11개 (55%)
```

### After (방안 1: 보너스 조정)
```
금융: 6개 (30%)
전기·전자: 4개 (20%)
IT: 3개 (15%)
운송: 3개 (15%)
기타: 4개 (20%)
```

### After (방안 2: 할당량)
```
금융: 6개 (30%) - 최대 제한
전기·전자: 4개 (20%)
IT: 3개 (15%)
운송: 4개 (20%)
기타: 3개 (15%)
```

---

## 💡 권장 사항

**방안 1 + 방안 2 조합**
1. 섹터 보너스 조정 (금융 축소, IT/제조 증가)
2. 섹터별 최대 30% 제한 (다양성 보장)

이렇게 하면:
- ✅ 금융 편중 해소
- ✅ 섹터 다양성 확보
- ✅ 포트폴리오 리스크 분산

어떤 방안을 적용하시겠습니까?

