#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Value Stock Finder v2.2 - UX/신뢰도 개선 패치
사용자 피드백 기반 실전 개선
"""

import streamlit as st
import pandas as pd
from typing import Dict, List


class UXImprovements:
    """UX 개선 패치"""
    
    @staticmethod
    def add_na_explanation():
        """N/A 표시 설명 추가"""
        st.info("""
        📊 **표시 안내**
        - **N/A**: 데이터 없음 또는 표본 부족 (추가 검증 권장)
        - **신뢰도 HIGH**: 섹터 표본 30+ (신뢰 가능)
        - **신뢰도 MEDIUM**: 섹터 표본 10-29 (참고용)
        - **신뢰도 LOW**: 섹터 표본 10 미만 (주의)
        """)
    
    @staticmethod
    def add_criteria_check_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        PER/PBR/ROE 기준 충족 여부 체크 칼럼 추가
        
        Args:
            df: 원본 DataFrame (criteria_met 포함)
            
        Returns:
            체크 표시 추가된 DataFrame
        """
        if 'criteria_met' not in df.columns:
            return df
        
        df_copy = df.copy()
        
        # 각 기준 충족 여부 체크 표시
        df_copy['PER✓'] = df_copy['criteria_met'].apply(
            lambda x: '✅' if 'PER' in (x if isinstance(x, list) else []) else '❌'
        )
        df_copy['PBR✓'] = df_copy['criteria_met'].apply(
            lambda x: '✅' if 'PBR' in (x if isinstance(x, list) else []) else '❌'
        )
        df_copy['ROE✓'] = df_copy['criteria_met'].apply(
            lambda x: '✅' if 'ROE' in (x if isinstance(x, list) else []) else '❌'
        )
        
        # 충족 개수 (정렬용)
        df_copy['기준충족'] = df_copy['criteria_met'].apply(
            lambda x: f"{len(x)}/3" if isinstance(x, list) else "0/3"
        )
        
        return df_copy
    
    @staticmethod
    def add_confidence_column(df: pd.DataFrame) -> pd.DataFrame:
        """
        신뢰도 칼럼을 기본 노출로 추가
        
        Args:
            df: 원본 DataFrame (confidence 포함)
            
        Returns:
            신뢰도 칼럼 추가된 DataFrame
        """
        if 'confidence' not in df.columns:
            return df
        
        df_copy = df.copy()
        
        # 신뢰도 아이콘 추가
        df_copy['신뢰도'] = df_copy['confidence'].apply(
            lambda x: {
                'HIGH': '🟢 높음',
                'MEDIUM': '🟡 보통',
                'LOW': '🔴 낮음',
                'UNKNOWN': '⚪ 미상'
            }.get(x, '⚪ 미상')
        )
        
        return df_copy
    
    @staticmethod
    def show_system_status_panel(has_improvements: bool, 
                                  has_quick_patches: bool,
                                  has_financial_provider: bool,
                                  has_sector_contextualizer: bool):
        """
        시스템 모듈 상태 패널 (사이드바)
        
        Args:
            has_improvements: 개선 모듈 활성화 여부
            has_quick_patches: Quick Patches 활성화 여부
            has_financial_provider: 재무 데이터 제공자 활성화 여부
            has_sector_contextualizer: 섹터 컨텍스트 활성화 여부
        """
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔧 시스템 상태")
        
        # 모듈 상태 표시
        modules = {
            '품질 지표': has_improvements,
            '실무 패치': has_quick_patches,
            '재무 데이터': has_financial_provider,
            '섹터 분석': has_sector_contextualizer
        }
        
        for module_name, is_active in modules.items():
            icon = '🟢' if is_active else '🔴'
            status = '활성' if is_active else '비활성'
            st.sidebar.markdown(f"{icon} **{module_name}**: {status}")
        
        # 전체 신뢰도
        active_count = sum(1 for v in modules.values() if v)
        total_count = len(modules)
        confidence_pct = (active_count / total_count) * 100
        
        if confidence_pct >= 75:
            st.sidebar.success(f"✅ 시스템 신뢰도: {confidence_pct:.0f}% (우수)")
        elif confidence_pct >= 50:
            st.sidebar.warning(f"⚠️ 시스템 신뢰도: {confidence_pct:.0f}% (보통)")
        else:
            st.sidebar.error(f"🚨 시스템 신뢰도: {confidence_pct:.0f}% (제한적)")
    
    @staticmethod
    def show_api_key_warning(has_kis_key: bool):
        """KIS API 키 설정 경고"""
        if not has_kis_key:
            st.sidebar.warning("""
            ⚠️ **KIS API 키 미설정**
            - 폴백 유니버스 사용 중
            - 실시간 데이터 제한적
            - `config.yaml` 설정 권장
            """)


class RecommendationLogicRefactor:
    """추천 로직 간결화 (가독성/테스트 용이)"""
    
    @staticmethod
    def calculate_base_recommendation(score_pct: float, 
                                       criteria_met_count: int) -> str:
        """
        기본 추천 산출 (점수 기반)
        
        Args:
            score_pct: 점수 백분율 (0-100)
            criteria_met_count: 기준 충족 개수 (0-3)
            
        Returns:
            기본 추천 등급
        """
        # 우수 가치주
        if criteria_met_count == 3 and score_pct >= 60:
            return "STRONG_BUY"
        elif score_pct >= 65:
            return "STRONG_BUY"
        # 양호 가치주
        elif criteria_met_count >= 2 and score_pct >= 50:
            return "BUY"
        elif score_pct >= 55:
            return "BUY"
        # 보류
        elif score_pct >= 45:
            return "HOLD"
        else:
            return "SELL"
    
    @staticmethod
    def apply_hard_guards(base_rec: str, 
                          roe: float, 
                          pbr: float, 
                          per: float,
                          alt_valuation_used: bool,
                          downgrade_func) -> str:
        """
        하드 가드 적용 (ROE<0 & PBR>3, 음수 PER 등)
        
        Args:
            base_rec: 기본 추천
            roe: ROE 값
            pbr: PBR 값
            per: PER 값
            alt_valuation_used: 대체 평가 사용 여부
            downgrade_func: 한 단계 하향 함수
            
        Returns:
            가드 적용된 추천
        """
        rec = base_rec
        
        # ROE < 0 & PBR > 3: 한 단계 하향
        if roe < 0 and pbr > 3:
            rec = downgrade_func(rec)
        
        # 음수 PER (대체 평가 미사용): 한 단계 하향
        if per <= 0 and not alt_valuation_used:
            rec = downgrade_func(rec)
        
        return rec
    
    @staticmethod
    def apply_anomaly_cap(base_rec: str, 
                          anomalies: Dict) -> str:
        """
        회계 이상 징후 캡 적용
        
        Args:
            base_rec: 기본 추천
            anomalies: 회계 이상 징후 딕셔너리
            
        Returns:
            캡 적용된 추천
        """
        if anomalies and any(v.get('severity') == 'HIGH' for v in anomalies.values()):
            return "HOLD"  # 최대 HOLD로 제한
        return base_rec
    
    @staticmethod
    def apply_penalties(base_rec: str,
                       penalties: int,
                       downgrade_func,
                       max_steps: int = 2) -> str:
        """
        보수화 패널티 적용
        
        Args:
            base_rec: 기본 추천
            penalties: 패널티 개수
            downgrade_func: 한 단계 하향 함수
            max_steps: 최대 하향 단계
            
        Returns:
            패널티 적용된 추천
        """
        rec = base_rec
        for _ in range(min(penalties, max_steps)):
            rec = downgrade_func(rec)
        return rec


# 적용 예시
USAGE_EXAMPLE = """
=== v2.2 UX 개선 패치 적용 가이드 ===

1. 시스템 상태 패널 (사이드바에 추가)
   ```python
   UXImprovements.show_system_status_panel(
       has_improvements=HAS_IMPROVEMENTS,
       has_quick_patches=HAS_QUICK_PATCHES,
       has_financial_provider=HAS_FINANCIAL_PROVIDER,
       has_sector_contextualizer=HAS_SECTOR_CONTEXTUALIZER
   )
   
   UXImprovements.show_api_key_warning(
       has_kis_key=bool(kis_config.get('app_key'))
   )
   ```

2. N/A 설명 추가 (결과 테이블 상단)
   ```python
   UXImprovements.add_na_explanation()
   ```

3. 기준 충족 체크 칼럼 (결과 DataFrame)
   ```python
   df = UXImprovements.add_criteria_check_columns(df)
   df = UXImprovements.add_confidence_column(df)
   ```

4. 추천 로직 간결화 (evaluate_value_stock)
   ```python
   # 기본 추천
   rec = RecommendationLogicRefactor.calculate_base_recommendation(
       score_pct, len(criteria_met_list)
   )
   
   # 하드 가드
   rec = RecommendationLogicRefactor.apply_hard_guards(
       rec, roe, pbr, per, 
       details.get('alternative_valuation_used', False),
       downgrade
   )
   
   # 회계 이상 캡
   rec = RecommendationLogicRefactor.apply_anomaly_cap(
       rec, details.get('accounting_anomalies', {})
   )
   
   # 패널티
   rec = RecommendationLogicRefactor.apply_penalties(
       rec, penalties, downgrade, max_steps=2
   )
   
   recommendation = rec
   ```
"""

if __name__ == '__main__':
    print("=== Value Stock Finder v2.2 - UX 개선 패치 ===\n")
    
    # 1. 체크 칼럼 테스트
    print("1. 기준 충족 체크 칼럼 추가")
    sample_df = pd.DataFrame([
        {'symbol': '005930', 'name': '삼성전자', 'criteria_met': ['PER', 'PBR', 'ROE'], 'confidence': 'HIGH'},
        {'symbol': '000660', 'name': 'SK하이닉스', 'criteria_met': ['PER', 'PBR'], 'confidence': 'MEDIUM'},
        {'symbol': '035420', 'name': 'NAVER', 'criteria_met': ['PBR'], 'confidence': 'LOW'},
    ])
    
    ux = UXImprovements()
    enhanced_df = ux.add_criteria_check_columns(sample_df)
    enhanced_df = ux.add_confidence_column(enhanced_df)
    
    print(enhanced_df[['symbol', 'name', 'PER✓', 'PBR✓', 'ROE✓', '기준충족', '신뢰도']].to_string(index=False))
    
    # 2. 추천 로직 리팩터링 테스트
    print("\n\n2. 추천 로직 간결화 테스트")
    
    def downgrade(r):
        order = ["STRONG_BUY", "BUY", "HOLD", "SELL"]
        idx = order.index(r) if r in order else 2
        return order[min(idx + 1, len(order) - 1)]
    
    refactor = RecommendationLogicRefactor()
    
    # Case 1: 정상 우수 종목
    rec1 = refactor.calculate_base_recommendation(score_pct=70, criteria_met_count=3)
    rec1 = refactor.apply_hard_guards(rec1, roe=15, pbr=1.2, per=8, alt_valuation_used=False, downgrade_func=downgrade)
    rec1 = refactor.apply_anomaly_cap(rec1, {})
    rec1 = refactor.apply_penalties(rec1, penalties=0, downgrade_func=downgrade)
    print(f"   Case 1 (정상 우수): {rec1} ✅")
    
    # Case 2: ROE<0 & PBR>3
    rec2 = refactor.calculate_base_recommendation(score_pct=60, criteria_met_count=2)
    rec2 = refactor.apply_hard_guards(rec2, roe=-2, pbr=4, per=10, alt_valuation_used=False, downgrade_func=downgrade)
    print(f"   Case 2 (ROE<0 & PBR>3): {rec2} (BUY→HOLD 한단계 하향)")
    
    # Case 3: 회계 이상 HIGH
    rec3 = refactor.calculate_base_recommendation(score_pct=70, criteria_met_count=3)
    rec3 = refactor.apply_anomaly_cap(rec3, {'high_non_operating': {'severity': 'HIGH'}})
    print(f"   Case 3 (회계 이상 HIGH): {rec3} (최대 HOLD)")
    
    print("\n" + "="*60)
    print(USAGE_EXAMPLE)

