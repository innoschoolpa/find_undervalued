# 🚀 Week 1 구현 가이드 - v2.2.2 릴리스

**목표**: 리스크 플래그 + 퍼센타일 개선 + MoS 안정화  
**기간**: 7일  
**예상 시간**: 40시간  
**릴리스**: v2.2.2

---

## 📋 Day 1-2: 리스크 플래그 강화 (P1-5)

### 목표
연속 OCF 적자, 순이익 변동성, 감사의견 등으로 점수 감점

### 구현 파일
`risk_flag_evaluator.py` (신규)

### 코드 템플릿

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리스크 플래그 평가기
회계/이벤트 리스크 감지 및 점수 감점
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class RiskFlagEvaluator:
    """리스크 플래그 평가 및 점수 조정"""
    
    def __init__(self):
        # 관리종목 리스트 (외부 소스 또는 수동 관리)
        self.management_stocks = set()
        
        # 불성실공시 리스트
        self.unfaithful_disclosure = set()
    
    def evaluate_all_risks(self, stock_data: Dict) -> Tuple[int, List[str]]:
        """
        모든 리스크 평가
        
        Returns:
            (총 감점, 경고 메시지 리스트)
        """
        total_penalty = 0
        warnings = []
        
        # 1. 회계 리스크
        accounting_penalties = self.evaluate_accounting_risks(stock_data)
        for risk, penalty in accounting_penalties:
            total_penalty += penalty
            warnings.append(f"{risk}: {penalty}점")
        
        # 2. 이벤트 리스크
        event_penalties = self.evaluate_event_risks(stock_data)
        for risk, penalty in event_penalties:
            total_penalty += penalty
            warnings.append(f"{risk}: {penalty}점")
        
        # 3. 유동성 리스크
        liquidity_penalty = self.evaluate_liquidity_risk(stock_data)
        if liquidity_penalty < 0:
            total_penalty += liquidity_penalty
            warnings.append(f"LIQUIDITY_RISK: {liquidity_penalty}점")
        
        return total_penalty, warnings
    
    def evaluate_accounting_risks(self, stock_data: Dict) -> List[Tuple[str, int]]:
        """회계 리스크 평가"""
        penalties = []
        
        # 1. 연속 OCF 적자 (데이터 있을 때만)
        ocf_history = stock_data.get('operating_cash_flow_history', [])
        if len(ocf_history) >= 3:
            if all(ocf < 0 for ocf in ocf_history[-3:]):
                penalties.append(('OCF_DEFICIT_3Y', -15))
                logger.warning(f"⚠️ {stock_data.get('symbol')}: 3년 연속 OCF 적자")
        
        # 2. 순이익 변동성 (CV > 1.0)
        net_income_history = stock_data.get('net_income_history', [])
        if len(net_income_history) >= 3:
            import statistics
            try:
                mean_ni = statistics.mean(net_income_history)
                stdev_ni = statistics.stdev(net_income_history)
                cv = abs(stdev_ni / mean_ni) if mean_ni != 0 else 0
                
                if cv > 1.0:
                    penalties.append(('HIGH_VOLATILITY', -10))
                    logger.info(f"⚠️ {stock_data.get('symbol')}: 순이익 변동성 높음 (CV={cv:.2f})")
            except Exception as e:
                logger.debug(f"변동성 계산 실패: {e}")
        
        # 3. 감사의견 한정/부적정
        audit_opinion = stock_data.get('audit_opinion', '적정')
        if audit_opinion == '한정':
            penalties.append(('QUALIFIED_OPINION', -15))
        elif audit_opinion in ['부적정', '의견거절']:
            penalties.append(('ADVERSE_OPINION', -30))
        
        # 4. 자본잠식
        capital_impairment = stock_data.get('capital_impairment_ratio', 0)
        if capital_impairment > 0:
            if capital_impairment >= 50:
                penalties.append(('SEVERE_IMPAIRMENT', -25))
            else:
                penalties.append(('CAPITAL_IMPAIRMENT', -15))
        
        return penalties
    
    def evaluate_event_risks(self, stock_data: Dict) -> List[Tuple[str, int]]:
        """이벤트 리스크 평가"""
        penalties = []
        symbol = stock_data.get('symbol', '')
        
        # 1. 관리종목
        if symbol in self.management_stocks or stock_data.get('is_management_stock'):
            penalties.append(('MANAGEMENT_STOCK', -30))
            logger.warning(f"🚨 {symbol}: 관리종목 → -30점")
        
        # 2. 불성실 공시
        if symbol in self.unfaithful_disclosure:
            penalties.append(('UNFAITHFUL_DISCLOSURE', -15))
        
        # 3. 투자유의/경고
        if stock_data.get('investment_caution'):
            penalties.append(('INVESTMENT_CAUTION', -10))
        
        if stock_data.get('market_warning'):
            penalties.append(('MARKET_WARNING', -20))
        
        return penalties
    
    def evaluate_liquidity_risk(self, stock_data: Dict) -> int:
        """유동성 리스크 평가"""
        # 일평균 거래대금 < 1억원
        trading_value = stock_data.get('trading_value', 0)
        if trading_value > 0 and trading_value < 100_000_000:
            logger.info(f"⚠️ {stock_data.get('symbol')}: 저유동성 (거래대금 {trading_value/1e8:.2f}억)")
            return -8
        
        return 0
    
    def load_management_stocks(self, source='krx'):
        """관리종목 리스트 로드"""
        # TODO: KRX API 또는 파일에서 로드
        # 임시: 빈 set
        self.management_stocks = set()
        logger.info(f"관리종목 리스트 로드: {len(self.management_stocks)}개")
```

### 통합 (value_stock_finder.py)

```python
# 초기화
def __init__(self):
    # ... 기존 코드 ...
    
    # ✅ v2.2.2: 리스크 플래그 평가기
    try:
        from risk_flag_evaluator import RiskFlagEvaluator
        self.risk_evaluator = RiskFlagEvaluator()
        self.risk_evaluator.load_management_stocks()
        logger.info("✅ 리스크 플래그 평가기 초기화 완료")
    except ImportError:
        self.risk_evaluator = None

# evaluate_value_stock() 수정
def evaluate_value_stock(self, stock_data, percentile_cap=99.5):
    """가치주 평가 (리스크 감점 적용)"""
    
    # ... 기존 점수 계산 ...
    
    # ✅ v2.2.2: 리스크 플래그 감점 (추가)
    if self.risk_evaluator:
        risk_penalty, risk_warnings = self.risk_evaluator.evaluate_all_risks(stock_data)
        
        if risk_penalty < 0:
            logger.info(f"⚠️ {stock_data.get('symbol')}: 리스크 감점 {risk_penalty}점")
            score += risk_penalty  # 감점 적용
            details['risk_penalty'] = risk_penalty
            details['risk_warnings'] = risk_warnings
    
    # ... 등급 결정 ...
```

---

## 📋 Day 3-4: 퍼센타일 글로벌 대체 (P1-6)

### 목표
섹터 표본 부족 시 전시장 분포 사용, 안정성 확보

### 구현 (value_stock_finder.py)

```python
@lru_cache(maxsize=1)
def _get_global_percentiles_cached(self):
    """전시장 글로벌 퍼센타일 (캐시)"""
    # 실제로는 전체 KOSPI/KOSDAQ 계산
    # 임시: 합리적 기본값
    return {
        'per': {
            'p10': 5.0, 'p25': 8.0, 'p50': 12.0, 
            'p75': 18.0, 'p90': 30.0, 'sample_size': 2000
        },
        'pbr': {
            'p10': 0.5, 'p25': 0.8, 'p50': 1.2, 
            'p75': 2.0, 'p90': 3.5, 'sample_size': 2000
        },
        'roe': {
            'p10': 3.0, 'p25': 6.0, 'p50': 10.0, 
            'p75': 15.0, 'p90': 22.0, 'sample_size': 2000
        }
    }

def _percentile_from_breakpoints_v2(self, value, sector_percentiles, 
                                     metric_name='per', use_global=True):
    """
    ✅ v2.2.2: 퍼센타일 계산 (글로벌 대체 지원)
    
    Args:
        value: 계산할 값
        sector_percentiles: 섹터 퍼센타일
        metric_name: 'per', 'pbr', 'roe' 중 하나
        use_global: 글로벌 대체 사용 여부
    """
    
    # 1. 섹터 퍼센타일 유효성 체크
    if not sector_percentiles or not isinstance(sector_percentiles, dict):
        if use_global:
            logger.debug(f"섹터 퍼센타일 없음 → 글로벌 사용 ({metric_name})")
            global_pcts = self._get_global_percentiles_cached()[metric_name]
            return self._percentile_from_breakpoints(value, global_pcts)
        return None
    
    sample_size = sector_percentiles.get('sample_size', 0)
    
    # 2. 표본 크기별 전략
    if sample_size < 10:
        # 극소 표본 → 글로벌만 사용
        if use_global:
            logger.info(f"⚠️ 섹터 표본 부족 (n={sample_size}) → 글로벌 분포 사용 ({metric_name})")
            global_pcts = self._get_global_percentiles_cached()[metric_name]
            return self._percentile_from_breakpoints(value, global_pcts)
        return 50.0  # 중립
    
    elif 10 <= sample_size < 30:
        # 소표본 → 가중 평균
        sector_pct = self._percentile_from_breakpoints(value, sector_percentiles)
        
        if use_global and sector_pct is not None:
            global_pcts = self._get_global_percentiles_cached()[metric_name]
            global_pct = self._percentile_from_breakpoints(value, global_pcts)
            
            if global_pct is not None:
                # 가중치: n=10 → 0%, n=30 → 100%
                weight_sector = (sample_size - 10) / 20
                weight_global = 1.0 - weight_sector
                
                blended = sector_pct * weight_sector + global_pct * weight_global
                logger.debug(f"가중 평균 (n={sample_size}): 섹터 {sector_pct:.1f}% × {weight_sector:.2f} "
                            f"+ 글로벌 {global_pct:.1f}% × {weight_global:.2f} = {blended:.1f}%")
                return blended
        
        return sector_pct
    
    else:
        # 충분한 표본 → 섹터만 사용
        return self._percentile_from_breakpoints(value, sector_percentiles)
    
    # 3. IQR ≈ 0 체크
    if sector_percentiles:
        p25 = sector_percentiles.get('p25', 0)
        p75 = sector_percentiles.get('p75', 0)
        iqr = abs(p75 - p25)
        
        if iqr < 1e-6:
            logger.warning(f"⚠️ IQR≈0 감지 (p25={p25}, p75={p75}) → 글로벌 대체 ({metric_name})")
            if use_global:
                global_pcts = self._get_global_percentiles_cached()[metric_name]
                return self._percentile_from_breakpoints(value, global_pcts)
            return 50.0
    
    return 50.0  # 최종 폴백
```

### 적용 (value_stock_finder.py)

```python
def _evaluate_sector_adjusted_metrics(self, stock_data, percentile_cap=99.5):
    """섹터 조정 메트릭 평가 (글로벌 대체 적용)"""
    
    stats = stock_data.get('sector_stats', {}) or {}
    
    per = stock_data.get('per') or 0
    pbr = stock_data.get('pbr') or 0
    roe = stock_data.get('roe') or 0
    
    # ✅ v2.2.2: 글로벌 대체 사용
    per_percentiles = stats.get('per_percentiles', {})
    pbr_percentiles = stats.get('pbr_percentiles', {})
    roe_percentiles = stats.get('roe_percentiles', {})
    
    per_pct = self._percentile_from_breakpoints_v2(
        per, per_percentiles, 'per', use_global=True
    )
    pbr_pct = self._percentile_from_breakpoints_v2(
        pbr, pbr_percentiles, 'pbr', use_global=True
    )
    roe_pct = self._percentile_from_breakpoints_v2(
        roe, roe_percentiles, 'roe', use_global=True
    )
    
    # ... 점수 계산
```

---

## 📋 Day 5: MoS 윈저라이즈 (P1-8)

### 구현 (value_stock_finder.py)

```python
def _winsorize_metric(self, value, lower=-50, upper=100, metric_name='ROE'):
    """메트릭 윈저라이즈 (이상치 클리핑)"""
    if value > upper:
        logger.info(f"⚠️ {metric_name} {value:.1f} 이상치 → {upper}로 캡핑")
        return upper
    if value < lower:
        logger.info(f"⚠️ {metric_name} {value:.1f} 이상치 → {lower}로 플로어")
        return lower
    return value

def compute_mos_score(self, per, pbr, roe, sector):
    """MoS 점수 계산 (윈저라이즈 적용)"""
    
    # ✅ v2.2.2: ROE 윈저라이즈
    roe_clean = self._winsorize_metric(roe, lower=-50, upper=100, metric_name='ROE')
    
    # ✅ PER, PBR도 윈저라이즈
    per_clean = self._winsorize_metric(per, lower=1, upper=300, metric_name='PER')
    pbr_clean = self._winsorize_metric(pbr, lower=0.1, upper=20, metric_name='PBR')
    
    # ... 기존 로직 (clean 값 사용)
```

---

## 📋 Day 6: 통합 테스트

### 테스트 시나리오

#### 시나리오 1: 리스크 플래그
```python
# 관리종목
stock_data = {
    'symbol': '999999',
    'name': '테스트종목',
    'is_management_stock': True,
    'per': 10, 'pbr': 1.0, 'roe': 12
}

# 예상: 기본 60점 - 30점 = 30점
```

#### 시나리오 2: 퍼센타일 글로벌
```python
# 섹터 표본 5개
sector_pcts = {'p25': 10, 'p50': 12, 'p75': 15, 'sample_size': 5}
value = 10

# 예상: 글로벌 분포 사용 (섹터 무시)
```

#### 시나리오 3: MoS 윈저라이즈
```python
# ROE 150%
per, pbr, roe = 10, 1.0, 150

# 예상: ROE → 100%로 캡핑, g 계산
```

---

## 📋 Day 7: 문서 및 릴리스

### 업데이트 문서
```
1. CHANGELOG.md
   - v2.2.2 섹션 추가
   - 리스크 플래그 설명
   - 퍼센타일 개선 설명

2. README_v2.2.md
   - 리스크 평가 섹션 추가
   - 퍼센타일 로직 설명

3. PATCH_NOTES_v2.2.2.md (신규)
   - 상세 변경 사항
   - 마이그레이션 가이드
```

### 릴리스 체크리스트
```
- [ ] 모든 테스트 통과
- [ ] 문서 업데이트
- [ ] CHANGELOG 작성
- [ ] 버전 번호 업데이트
- [ ] Git 태그 생성 (v2.2.2)
```

---

## 🎯 Week 1 목표 지표

### 정량적 목표
```
리스크 감지율: 95% 이상
퍼센타일 안정성: ±5% 이내
MoS 계산 성공률: 98% 이상
```

### 정성적 목표
```
✅ 회계 이상 조기 탐지
✅ 소형 섹터 차별력 확보
✅ ROE 이상치 안정화
✅ 사용자 신뢰도 향상
```

---

## 📊 예상 개선 효과

### Before (v2.2.1)
```
정확성: 4.6
안정성: 4.7
거버넌스: 4.5
```

### After (v2.2.2)
```
정확성: 4.7 (+0.1) ✅
안정성: 4.8 (+0.1) ✅
거버넌스: 4.6 (+0.1) ✅

총점: 22.3 → 22.6 (+0.3)
```

---

## 🚀 즉시 시작

### Day 1 (오늘)
```bash
# 1. 파일 생성
touch risk_flag_evaluator.py

# 2. 위 템플릿 복사
# 3. 테스트 실행
python -c "from risk_flag_evaluator import RiskFlagEvaluator; print('✅ 임포트 성공')"
```

### Day 3
```bash
# 퍼센타일 로직 수정
# value_stock_finder.py에 _percentile_from_breakpoints_v2 추가
```

### Day 5
```bash
# MoS 윈저라이즈 적용
# _winsorize_metric 메서드 추가
```

---

**작성**: 2025-10-12  
**목표 버전**: v2.2.2  
**예상 완료**: 2025-10-19 (7일 후)  
**상태**: **착수 준비 완료** ✅

