#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
가치 투자 패치 테스트 스크립트
"""

import os
import sys
from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer

def test_value_investing_patch():
    """가치 투자 패치 테스트"""
    print("=== 가치 투자 패치 테스트 ===")
    
    # 환경변수 설정
    os.environ["MOS_BUY_THRESHOLD"] = "0.30"
    os.environ["MOS_WATCH_THRESHOLD"] = "0.15"
    
    try:
        # 분석기 초기화
        analyzer = EnhancedIntegratedAnalyzer()
        
        # 테스트 종목 분석
        test_symbols = [
            ("005930", "삼성전자"),
            ("000660", "SK하이닉스"),
            ("005380", "현대차")
        ]
        
        for symbol, name in test_symbols:
            print(f"\n--- {name} ({symbol}) 분석 ---")
            
            # 단일 종목 분석
            result = analyzer.analyze_single_stock(symbol, name)
            
            # 새로운 필드들 확인
            print(f"내재가치: {result.intrinsic_value}")
            print(f"안전마진: {result.margin_of_safety}")
            print(f"해자 등급: {result.moat_grade}")
            print(f"관심목록 시그널: {result.watchlist_signal}")
            print(f"가치투자 점수: {result.score_breakdown.get('가치투자', 'N/A')}")
            print(f"가치투자 원점수: {result.score_breakdown.get('value_raw', 'N/A')}")
            
            # to_dict() 메서드 테스트
            result_dict = result.to_dict()
            print(f"딕셔너리 변환 확인:")
            print(f"  - intrinsic_value: {result_dict.get('intrinsic_value')}")
            print(f"  - margin_of_safety: {result_dict.get('margin_of_safety')}")
            print(f"  - moat_grade: {result_dict.get('moat_grade')}")
            print(f"  - watchlist_signal: {result_dict.get('watchlist_signal')}")
        
        print("\n=== 패치 테스트 완료 ===")
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'analyzer' in locals():
            analyzer.close()

if __name__ == "__main__":
    success = test_value_investing_patch()
    sys.exit(0 if success else 1)


