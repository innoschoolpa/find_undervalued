#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Value Stock Finder v2.1.3 - 치명적 이슈 수정
실전 운영에서 발생할 수 있는 진짜 문제들 해결
"""

import concurrent.futures
import time
import math
from typing import Dict, Optional


class CriticalFixesV213:
    """v2.1.3 치명적 이슈 수정"""
    
    @staticmethod
    def improve_threadpool_reuse():
        """
        ThreadPoolExecutor 남발 수정
        배치마다 새로 생성 → 한 번만 생성 후 재사용
        """
        return """
        # Before (v2.1.2) - 배치마다 ThreadPoolExecutor 생성
        for batch_start in range(0, len(stock_items), batch_size):
            batch = stock_items[batch_start: batch_start+batch_size]
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # 배치 처리...
        
        # After (v2.1.3) - 한 번만 생성 후 재사용
        max_workers = min(3, batch_size)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for batch_start in range(0, len(stock_items), batch_size):
                batch = stock_items[batch_start: batch_start+batch_size]
                # 배치 처리...
        """
    
    @staticmethod
    def improve_percentile_distribution_guard():
        """
        퍼센타일 분포 방어 강화
        납작한 분포 IQR≈0 처리에서 조기 탈출
        """
        return """
        def _percentile_from_breakpoints(self, value: float, p: Dict[str, float]) -> Optional[float]:
            # 입력값 안전장치
            if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
                return None
            if not p:
                return None
            
            # ✅ v2.1.3: 납작한 분포 조기 탈출 (IQR≈0 방어)
            p25 = p.get('p25')
            p50 = p.get('p50') 
            p75 = p.get('p75')
            
            if not all(math.isfinite(x) for x in [p25, p50, p75] if x is not None):
                return None
                
            iqr = p75 - p25 if p75 is not None and p25 is not None else None
            if iqr is not None and (not math.isfinite(iqr) or abs(iqr) < 1e-9):
                # 분포가 의미 없으면 중앙값 기준 단순 랭킹으로 대체
                return 50.0 if (isinstance(value, (int, float)) and math.isfinite(value)) else None
            
            # 기존 로직 계속...
        """
    
    @staticmethod
    def improve_mos_scale_comment():
        """
        MoS 점수 스케일 이중/미스매치 방지
        주석 강화로 리팩토링 시 실수 방지
        """
        return """
        # ✅ v2.1.3: Justified Multiple 기반 MoS 점수 (이미 35점 만점)
        # ⚠️ 중요: mos_score는 이미 0~35 점수로 스케일된 값입니다. 추가 스케일 금지!
        # compute_mos_score() 내부에서 cap_mos_score()가 *0.35 적용하여 0-35점 반환
        mos_score = self.compute_mos_score(per, pbr, roe, sector_name)
        """
    
    @staticmethod
    def improve_token_cache_locking():
        """
        토큰 캐시 파일 경합 방지
        다중 프로세스/탭 동시 접근 시 파일락 적용
        """
        return """
        # SimpleOAuthManager._refresh_rest_token()
        import portalocker
        
        # Before (v2.1.2) - 경합 가능
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        # After (v2.1.3) - 파일락 적용
        with portalocker.Lock(cache_file, 'w', timeout=3) as f:
            json.dump(cache_data, f, indent=2)
        """
    
    @staticmethod
    def improve_backoff_recovery():
        """
        배치 백오프/딜레이 비례 개선
        감쇠 계수를 높여 회복 속도 향상
        """
        return """
        # Before (v2.1.2) - 느린 회복
        backoff = max(backoff / 1.2, 1.0)
        
        # After (v2.1.3) - 빠른 회복
        backoff = max(backoff / 1.5, 1.0)  # 1.2 → 1.5
        """
    
    @staticmethod
    def improve_sector_normalization():
        """
        섹터 정규화 누적 치환 규칙 개선
        순서 민감도 낮추기 위해 사전 매핑 1회 통과
        """
        return """
        def _normalize_sector_name(self, s: str) -> str:
            if not s:
                return '기타'
            
            # 토큰화 (영숫자만)
            tokens = ''.join(ch for ch in s if ch.isalnum())
            
            # 사전 매핑 1회 통과
            aliases = {
                '금융업': '금융업', '금융': '금융업', '은행': '금융업', 
                '증권': '금융업', '보험': '금융업',
                'it': '기술업', '아이티': '기술업', '반도체': '기술업',
                '소프트웨어': '기술업', '인터넷': '기술업', '통신': '기술업',
                '제조': '제조업', '화학': '제조업', '철강': '제조업',
                '운송': '운송업', '건설': '건설업'
            }
            
            for k, v in aliases.items():
                if k in tokens:
                    return v
            
            return '기타'
        """
    
    @staticmethod
    def improve_sector_adjustment_early_exit():
        """
        SectorCycleContextualizer 조정계수 조기 종료
        샘플 수가 0인 경우 무조건 1.0으로 빠르게 리턴
        """
        return """
        # SectorCycleContextualizer.calculate_adjustment()
        def calculate_adjustment(self, sector_name: str, sample_size: int) -> float:
            # ✅ v2.1.3: 조기 종료 (빠름+안정)
            if not sample_size or sample_size < 30:
                return 1.0
            
            # 기존 로직 계속...
        """
    
    @staticmethod
    def improve_number_conversion_utility():
        """
        숫자 변환 한 곳으로 모으기
        _pos_or_none, fmt_ratio, _safe_num 중복 역할 통합
        """
        return """
        def to_num(x, default=None, pos_only=False):
            \"\"\"
            범용 숫자 변환 유틸리티
            Args:
                x: 변환할 값
                default: 변환 실패 시 기본값
                pos_only: 양수만 허용 여부
            Returns:
                변환된 숫자 또는 기본값
            \"\"\"
            try:
                v = float(x)
                if not math.isfinite(v):
                    return default
                if pos_only and v <= 0:
                    return default
                return v
            except:
                return default
        """


# 테스트 체크리스트
TEST_CHECKLIST = """
=== v2.1.3 테스트 체크리스트 ===

1. ThreadPoolExecutor 재사용
   - 배치 처리 시 스레드 생성/파괴 오버헤드 감소 확인
   - 메모리 사용량 안정성 확인

2. 퍼센타일 분포 방어
   - p25==p50==p75 분포에서 조기 탈출 확인
   - IQR≈0 케이스에서 50.0 반환 확인

3. MoS 점수 스케일
   - 이중 스케일링 없음 확인
   - 주석으로 리팩토링 시 실수 방지

4. 토큰 캐시 파일락
   - 다중 탭에서 동시 접근 시 안정성 확인
   - 파일 경합 상황에서 데이터 무결성 확인

5. 백오프 회복 속도
   - 에러 없을 때 빠른 회복 확인
   - 1.2 → 1.5 감쇠 계수 효과 확인

6. 섹터 정규화
   - 누적 치환 없이 1회 통과 확인
   - 순서 민감도 제거 확인

7. 조정계수 조기 종료
   - sample_size < 30에서 즉시 1.0 반환 확인
   - 성능 향상 확인

8. 숫자 변환 통합
   - 중복 로직 제거 확인
   - 타입/NaN 처리 일관성 확인
"""

if __name__ == '__main__':
    print("=== Value Stock Finder v2.1.3 - 치명적 이슈 수정 ===\n")
    
    fixes = CriticalFixesV213()
    
    print("1. ThreadPoolExecutor 재사용 개선")
    print(fixes.improve_threadpool_reuse())
    
    print("\n2. 퍼센타일 분포 방어 강화")
    print(fixes.improve_percentile_distribution_guard())
    
    print("\n3. MoS 점수 스케일 주석 강화")
    print(fixes.improve_mos_scale_comment())
    
    print("\n4. 토큰 캐시 파일락 적용")
    print(fixes.improve_token_cache_locking())
    
    print("\n5. 백오프 회복 속도 개선")
    print(fixes.improve_backoff_recovery())
    
    print("\n6. 섹터 정규화 개선")
    print(fixes.improve_sector_normalization())
    
    print("\n7. 조정계수 조기 종료")
    print(fixes.improve_sector_adjustment_early_exit())
    
    print("\n8. 숫자 변환 통합")
    print(fixes.improve_number_conversion_utility())
    
    print(TEST_CHECKLIST)
