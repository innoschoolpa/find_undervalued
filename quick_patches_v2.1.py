#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Value Stock Finder v2.1 - Quick Patches
즉시 적용 가능한 실무 개선 패치
"""

import os
import logging

logger = logging.getLogger(__name__)


class QuickPatches:
    """빠르게 적용 가능한 패치 모음"""
    
    @staticmethod
    def clean_name(s: str) -> str:
        """
        이름 정규화 (공백/이모지/우회문자 제거)
        
        Args:
            s: 원본 문자열
            
        Returns:
            정제된 문자열
        """
        if not s:
            return ""
        return ''.join(ch for ch in s.strip() if ch.isprintable())
    
    @staticmethod
    def short_text(s: str, width: int = 120) -> str:
        """
        멀티바이트 안전 텍스트 잘라내기
        
        Args:
            s: 원본 문자열
            width: 최대 길이
            
        Returns:
            잘라낸 문자열
        """
        try:
            if not s:
                return ""
            return s if len(s) <= width else s[:width-3] + '...'
        except Exception:
            return str(s)  # 마지막 방어
    
    @staticmethod
    def merge_options(opts: dict) -> dict:
        """
        옵션 딕셔너리 스키마 가드 (기본값 머지)
        
        Args:
            opts: 사용자 옵션
            
        Returns:
            기본값과 병합된 옵션
        """
        defaults = {
            'per_max': 15.0,
            'pbr_max': 1.5,
            'roe_min': 10.0,
            'score_min': 60.0,
            'percentile_cap': 99.5,
            'api_strategy': "안전 모드 (배치 처리)",
            'fast_mode': False,
            'fast_latency': 0.7
        }
        out = defaults.copy()
        if opts:
            out.update({k: v for k, v in opts.items() if v is not None})
        return out
    
    @staticmethod
    def safe_chmod(file_path: str, mode: int = 0o600):
        """
        권한 설정 (실패 시 로깅)
        
        Args:
            file_path: 파일 경로
            mode: 권한 모드
        """
        try:
            os.chmod(file_path, mode)
        except Exception as e:
            logger.debug(f"chmod skipped for {file_path}: {e}")
    
    @staticmethod
    def clean_dataframe_for_export(df):
        """
        CSV 내보내기용 DataFrame 정제 (내부 컬럼 제거)
        
        Args:
            df: 원본 DataFrame
            
        Returns:
            정제된 DataFrame
        """
        # '_'로 시작하는 내부 컬럼 제거
        internal_cols = [c for c in df.columns if c.startswith('_')]
        return df.drop(columns=internal_cols, errors='ignore')


class ValueStockFinderPatches:
    """ValueStockFinder 클래스에 적용할 패치들"""
    
    @staticmethod
    def prime_cache_for_fallback(finder, stock_universe: dict, max_prime: int = 10):
        """
        폴백 유니버스에서도 프라임 캐시 활성화
        
        Args:
            finder: ValueStockFinder 인스턴스
            stock_universe: 전체 종목 딕셔너리
            max_prime: 최대 프라임 개수
        """
        if not getattr(finder, "_last_api_success", False):
            seed = list(stock_universe.items())[:min(max_prime, len(stock_universe))]
            primed_count = 0
            
            for code, name in seed:
                try:
                    ok, primed = finder._is_tradeable(code, name)
                    if ok and primed:
                        finder._primed_cache[code] = primed
                        primed_count += 1
                except Exception as e:
                    logger.debug(f"Prime cache failed for {code}: {e}")
            
            logger.info(f"✅ 폴백 경로 프라임 캐시: {primed_count}/{len(seed)} 성공")
    
    @staticmethod
    def handle_negative_indicator(value, indicator_name: str = "value") -> tuple:
        """
        음수 지표 처리 (명확한 0점 + 사유 태그)
        
        Args:
            value: 지표 값
            indicator_name: 지표 이름
            
        Returns:
            (점수, 사유)
        """
        if isinstance(value, (int, float)) and value < 0:
            return 0.0, f"{indicator_name}_negative"
        return None, None  # 정상 처리 계속
    
    @staticmethod
    def cap_mos_score(mos_raw_score: float, max_score: int = 35) -> int:
        """
        MoS 점수 상한 캡 (과도한 가점 방지)
        
        Args:
            mos_raw_score: 원점수 (0-100)
            max_score: 최대 점수
            
        Returns:
            캡 적용된 점수
        """
        return min(max_score, round(mos_raw_score * 0.35))
    
    @staticmethod
    def soft_hard_guard(roe: float, pbr: float, 
                        current_recommendation: str,
                        downgrade_func) -> str:
        """
        하드 가드 완화 (즉시 SELL → 한 단계 하향)
        
        Args:
            roe: ROE 값
            pbr: PBR 값
            current_recommendation: 현재 추천 등급
            downgrade_func: 한 단계 하향 함수
            
        Returns:
            조정된 추천 등급
        """
        if roe < 0 and pbr > 3:
            # 즉시 SELL이 아닌 한 단계만 하향
            return downgrade_func(current_recommendation)
        return current_recommendation
    
    @staticmethod
    def get_sector_params_from_config(sector: str, 
                                       default_r: float = 0.115,
                                       default_b: float = 0.35,
                                       benchmarks: dict = None) -> tuple:
        """
        섹터 r, b를 벤치마크/설정에서 가져오기
        
        Args:
            sector: 섹터명
            default_r: 기본 요구수익률
            default_b: 기본 유보율
            benchmarks: 섹터 벤치마크 딕셔너리
            
        Returns:
            (r, b)
        """
        if benchmarks:
            r = benchmarks.get('req_return', default_r)
            b = benchmarks.get('retention_ratio', default_b)
        else:
            # 하드코딩 폴백
            sector_r = {
                "금융": 0.10, "금융업": 0.10,
                "통신": 0.105, "통신업": 0.105,
                "제조업": 0.115, "필수소비재": 0.11,
                "운송": 0.12, "운송장비": 0.12,
                "전기전자": 0.12, "IT": 0.125, "기술업": 0.125,
                "건설": 0.12, "건설업": 0.12,
                "바이오/제약": 0.12, "에너지/화학": 0.115, "소비재": 0.11,
                "서비스업": 0.115, "철강금속": 0.115, "섬유의복": 0.11,
                "종이목재": 0.115, "유통업": 0.11,
                "기타": 0.115
            }
            sector_b = {
                "금융": 0.40, "금융업": 0.40,
                "통신": 0.55, "통신업": 0.55,
                "제조업": 0.35, "필수소비재": 0.40,
                "운송": 0.35, "운송장비": 0.35,
                "전기전자": 0.35, "IT": 0.30, "기술업": 0.30,
                "건설": 0.35, "건설업": 0.35,
                "바이오/제약": 0.30, "에너지/화학": 0.35, "소비재": 0.40,
                "서비스업": 0.35, "철강금속": 0.35, "섬유의복": 0.40,
                "종이목재": 0.35, "유통업": 0.40,
                "기타": 0.35
            }
            r = sector_r.get(sector, default_r)
            b = sector_b.get(sector, default_b)
        
        return r, b


# 패치 적용 가이드
PATCH_GUIDE = """
=== Value Stock Finder v2.1 Quick Patches 적용 가이드 ===

1. 이름 정규화 (get_stock_data 반환 직전)
   ```python
   stock['name'] = QuickPatches.clean_name(
       stock.get('name') or 
       stock.get('financial_data', {}).get('name') or 
       symbol
   )
   ```

2. 폴백 캐시 프라임 (screen_all_stocks 배치 루프 직전)
   ```python
   ValueStockFinderPatches.prime_cache_for_fallback(
       self, stock_universe, max_prime=10
   )
   ```

3. 음수 지표 처리 (_percentile_or_range_score 시작부)
   ```python
   score, reason = ValueStockFinderPatches.handle_negative_indicator(
       value, indicator_name
   )
   if score is not None:
       return score
   ```

4. MoS 점수 캡 (compute_mos_score 반환부)
   ```python
   return ValueStockFinderPatches.cap_mos_score(mos_raw_score, max_score=35)
   ```

5. 하드 가드 완화 (evaluate_value_stock 추천 결정부)
   ```python
   recommendation = ValueStockFinderPatches.soft_hard_guard(
       roe, pbr, recommendation, downgrade
   )
   ```

6. CSV 클린 다운로드 (render_batch_analysis 다운로드 버튼)
   ```python
   clean_df = QuickPatches.clean_dataframe_for_export(summary_df)
   st.download_button(
       "📥 전체 분석 결과 CSV 다운로드 (클린)",
       data=clean_df.to_csv(index=False).encode("utf-8-sig"),
       file_name=f"all_analysis_summary_{datetime.now():%Y%m%d_%H%M}_clean.csv",
       mime="text/csv"
   )
   ```

7. 옵션 스키마 가드 (screen_all_stocks 시작부)
   ```python
   options = QuickPatches.merge_options(options)
   ```

8. 토큰 캐시 권한 (SimpleOAuthManager._refresh_rest_token)
   ```python
   QuickPatches.safe_chmod(cache_file, 0o600)
   ```

9. 에러 텍스트 잘라내기 (에러 처리부)
   ```python
   error_msg = QuickPatches.short_text(str(e), width=120)
   ```

10. 섹터 파라미터 설정화 (_justified_multiples)
    ```python
    r, b = ValueStockFinderPatches.get_sector_params_from_config(
        sector, 
        default_r=0.115, 
        default_b=0.35,
        benchmarks=stock_data.get('sector_benchmarks')
    )
    ```
"""

if __name__ == '__main__':
    print("=== Value Stock Finder v2.1 Quick Patches ===\n")
    print("즉시 적용 가능한 실무 개선 패치\n")
    
    # 테스트
    qp = QuickPatches()
    
    print("1. 이름 정규화 테스트")
    test_names = [
        "삼성전자  \n",
        "SK하이닉스 🚀",
        "  NAVER  ",
        "LG화학\t(주)"
    ]
    for name in test_names:
        clean = qp.clean_name(name)
        print(f"   '{name}' → '{clean}'")
    
    print("\n2. 텍스트 잘라내기 테스트")
    long_text = "이것은 매우 긴 한글 텍스트입니다. " * 10
    short = qp.short_text(long_text, width=50)
    print(f"   원본 길이: {len(long_text)}")
    print(f"   잘린 길이: {len(short)}")
    print(f"   결과: {short}")
    
    print("\n3. 옵션 머지 테스트")
    user_opts = {'per_max': 20.0, 'unknown_key': 'test'}
    merged = qp.merge_options(user_opts)
    print(f"   사용자 옵션: {user_opts}")
    print(f"   병합 결과: {merged}")
    
    print("\n4. MoS 점수 캡 테스트")
    vsp = ValueStockFinderPatches()
    for raw in [50, 80, 100, 120]:
        capped = vsp.cap_mos_score(raw)
        print(f"   원점수 {raw} → 캡 적용 {capped}")
    
    print("\n5. 음수 지표 처리 테스트")
    for val in [-5.0, 0.0, 10.0]:
        score, reason = vsp.handle_negative_indicator(val, "ROE")
        print(f"   값 {val} → 점수 {score}, 사유 {reason}")
    
    print("\n" + "="*60)
    print(PATCH_GUIDE)

