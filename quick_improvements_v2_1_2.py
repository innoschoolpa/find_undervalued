#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Value Stock Finder v2.1.2 - 빠른 개선 패치
사용자 피드백 기반 실무 개선사항 적용
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional


class QuickImprovementsV212:
    """v2.1.2 빠른 개선사항"""
    
    @staticmethod
    def add_percentile_cap_info(options: Dict) -> None:
        """퍼센타일 캡 효과 표시"""
        cap = options.get('percentile_cap', 99.5)
        st.caption(f"📊 **퍼센타일 상한 {cap:.1f}%** 적용 중 - 극단값 제한으로 안정적 점수 계산")
    
    @staticmethod
    def normalize_sector_names() -> Dict[str, str]:
        """섹터명 정규화 맵핑 통일"""
        return {
            # IT/기술 관련 → '기술업' 통일
            'it': '기술업',
            '아이티': '기술업', 
            '기술': '기술업',
            '반도체': '기술업',
            '전자': '기술업',
            '소프트웨어': '기술업',
            '인터넷': '기술업',
            '통신': '기술업',
            
            # 금융 관련 → '금융업' 통일
            '금융': '금융업',
            '은행': '금융업',
            '보험': '금융업',
            '증권': '금융업',
            
            # 제조업 관련 → '제조업' 통일
            '제조': '제조업',
            '화학': '제조업',
            '철강': '제조업',
            '기계': '제조업',
            
            # 기타
            '운송': '운송업',
            '건설': '건설업',
            '유통': '유통업',
            '에너지': '에너지업'
        }
    
    @staticmethod
    def improve_progress_display(progress_bar, progress: float, 
                                 completed: int, total: int,
                                 ok_count: int = 0, err_count: int = 0) -> None:
        """진행률 표시 개선 (에러/성공 카운터 추가)"""
        if progress_bar:
            status_text = f"{completed}/{total} • {progress*100:.1f}%"
            if ok_count > 0 or err_count > 0:
                status_text += f" | ✅ {ok_count} / ❌ {err_count}"
            progress_bar.progress(progress, text=status_text)
    
    @staticmethod
    def safe_timeout_calculation(options: Dict) -> float:
        """타임아웃 계산 안전성 개선"""
        if options.get('fast_mode', False):
            timeout = options.get('fast_latency', 0.7)
            return max(timeout, 1.5)  # 하한선 1.5초
        else:
            return 10.0  # 기본 모드
    
    @staticmethod
    def improve_error_sampling(error_msg: str, max_width: int = 120) -> str:
        """에러 메시지 샘플링 개선"""
        try:
            if len(error_msg) <= max_width:
                return error_msg
            return error_msg[:max_width-3] + "..."
        except Exception:
            return str(error_msg)[:50] + "..."
    
    @staticmethod
    def ensure_dataframe_sort_consistency(df: pd.DataFrame) -> pd.DataFrame:
        """DataFrame 정렬 일관성 보장"""
        if '_value_score_num' in df.columns:
            df = df.sort_values('_value_score_num', ascending=False).reset_index(drop=True)
        return df
    
    @staticmethod
    def add_module_warning_once(warning_key: str, message: str) -> None:
        """모듈 경고 한 번만 표시"""
        if not st.session_state.get(f"_warned_{warning_key}", False):
            st.info(message)
            st.session_state[f"_warned_{warning_key}"] = True
    
    @staticmethod
    def add_fallback_info() -> None:
        """폴백 유니버스 정보 표시"""
        st.info("""
        📋 **기본 리스트 사용 중**
        - KIS API 연결 제한으로 기본 대형주 리스트로 분석
        - 일부 종목은 실시간 지표 조회가 제한될 수 있습니다
        - 실시간 데이터가 필요한 경우 config.yaml 설정을 확인해주세요
        """)


class SectorNormalizer:
    """섹터명 정규화 클래스"""
    
    def __init__(self):
        self.mapping = QuickImprovementsV212.normalize_sector_names()
    
    def normalize(self, sector_name: str) -> str:
        """섹터명 정규화"""
        if not sector_name:
            return '기타'
        
        # 소문자 변환 후 매핑
        normalized = self.mapping.get(sector_name.lower(), sector_name)
        
        # 추가 정규화: 공백 제거, 특수문자 처리
        return normalized.strip().replace(' ', '')


class Constants:
    """상수 정의 (매직넘버 제거)"""
    
    # 더미 데이터 감지용
    DUMMY_SENTINEL = 150.0  # mcp_kis_integration.py의 결측 채움값
    
    # 에러 메시지 최대 길이
    ERROR_MSG_WIDTH = 120
    
    # 타임아웃 하한선
    MIN_TIMEOUT = 1.5
    
    # 기본 타임아웃
    DEFAULT_TIMEOUT = 10.0


# 적용 예시 및 테스트
if __name__ == '__main__':
    print("=== Value Stock Finder v2.1.2 - 빠른 개선 패치 ===\n")
    
    # 1. 섹터명 정규화 테스트
    print("1. 섹터명 정규화 테스트")
    normalizer = SectorNormalizer()
    test_sectors = ['IT', '금융', '반도체', '기술', '금융업', '기타']
    
    for sector in test_sectors:
        normalized = normalizer.normalize(sector)
        print(f"   '{sector}' → '{normalized}'")
    
    # 2. 타임아웃 계산 테스트
    print("\n2. 타임아웃 계산 테스트")
    quick = QuickImprovementsV212()
    
    # 빠른 모드 (하한선 적용)
    fast_options = {'fast_mode': True, 'fast_latency': 0.7}
    timeout_fast = quick.safe_timeout_calculation(fast_options)
    print(f"   빠른 모드 (0.7초): {timeout_fast}초 (하한선 적용)")
    
    # 기본 모드
    normal_options = {'fast_mode': False}
    timeout_normal = quick.safe_timeout_calculation(normal_options)
    print(f"   기본 모드: {timeout_normal}초")
    
    # 3. 에러 메시지 샘플링 테스트
    print("\n3. 에러 메시지 샘플링 테스트")
    long_error = "This is a very long error message that should be truncated for better readability in the UI"
    short_error = "Short error"
    
    print(f"   긴 메시지: '{quick.improve_error_sampling(long_error)}'")
    print(f"   짧은 메시지: '{quick.improve_error_sampling(short_error)}'")
    
    # 4. DataFrame 정렬 테스트
    print("\n4. DataFrame 정렬 테스트")
    test_df = pd.DataFrame([
        {'symbol': 'A', '_value_score_num': 85.0, 'name': 'Stock A'},
        {'symbol': 'B', '_value_score_num': 92.0, 'name': 'Stock B'},
        {'symbol': 'C', '_value_score_num': 78.0, 'name': 'Stock C'},
    ])
    
    sorted_df = quick.ensure_dataframe_sort_consistency(test_df)
    print("   정렬 결과:")
    print(sorted_df[['symbol', '_value_score_num', 'name']].to_string(index=False))
    
    print("\n" + "="*60)
    print("✅ 모든 개선사항 테스트 완료!")
    print("\n📋 적용 권장 순서:")
    print("1. 섹터명 정규화 통일")
    print("2. 매직넘버 상수화")
    print("3. 타임아웃 하한선 적용")
    print("4. 진행률 카운터 추가")
    print("5. 에러 메시지 샘플링 개선")
    print("6. DataFrame 정렬 일관성 보장")
    print("7. 모듈 경고 최적화")
