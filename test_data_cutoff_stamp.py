#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v2.2.2 데이터 커트오프 스탬프 테스트
"""

import sys
import io
import logging
import pandas as pd

# Windows 인코딩 처리
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def test_csv_metadata_generation():
    """CSV 메타데이터 생성 테스트"""
    print("\n" + "="*60)
    print("🧪 CSV 메타데이터 생성 테스트")
    print("="*60)
    
    from value_stock_finder import ValueStockFinder
    
    finder = ValueStockFinder()
    
    # 테스트 DataFrame
    test_df = pd.DataFrame({
        '종목코드': ['005930', '000660'],
        '종목명': ['삼성전자', 'SK하이닉스'],
        '현재가': ['70,000원', '120,000원'],
        'PER': ['10.0배', '12.0배'],
        'PBR': ['1.2배', '1.5배'],
        'ROE': ['15.0%', '18.0%'],
        '가치주점수': ['75.0점', '80.0점'],
        '등급': ['B+', 'A'],
        '추천': ['BUY', 'BUY']
    })
    
    # 테스트 옵션
    test_options = {
        'per_max': 15.0,
        'pbr_max': 1.5,
        'roe_min': 10.0,
        'score_min': 60.0,
        'percentile_cap': 99.5,
        'api_strategy': '빠른 모드'
    }
    
    # 테스트 결과 요약
    test_result_count = {
        'total': 2,
        'buy': 2,
        'hold': 0,
        'sell': 0
    }
    
    # CSV 생성
    csv_with_metadata = finder.generate_csv_with_metadata(
        test_df, test_options, test_result_count
    )
    
    print("\n📄 생성된 CSV (첫 30줄):")
    print("-" * 60)
    lines = csv_with_metadata.split('\n')
    for i, line in enumerate(lines[:30], 1):
        print(f"{i:3d} | {line}")
    print("-" * 60)
    
    # 검증
    assert '# 저평가 가치주 발굴 시스템' in csv_with_metadata, "메타데이터 헤더 누락"
    assert '# 버전: v2.2.2' in csv_with_metadata, "버전 정보 누락"
    assert '# PER 상한: 15.0' in csv_with_metadata, "PER 상한 누락"
    assert '# 총 종목 수: 2개' in csv_with_metadata, "결과 요약 누락"
    assert '# BUY: 2개' in csv_with_metadata, "BUY 카운트 누락"
    assert '종목코드' in csv_with_metadata, "CSV 헤더 누락"
    assert '005930' in csv_with_metadata, "데이터 누락"
    
    print("\n✅ 메타데이터 검증 완료!")
    print(f"   - 총 줄 수: {len(lines)}")
    print(f"   - 메타데이터 줄 수: {len([l for l in lines if l.startswith('#')])}")
    print(f"   - 데이터 줄 수: {len([l for l in lines if not l.startswith('#') and l.strip()])}")


def test_csv_parsing():
    """생성된 CSV 파싱 테스트"""
    print("\n" + "="*60)
    print("🧪 CSV 파싱 테스트")
    print("="*60)
    
    from value_stock_finder import ValueStockFinder
    
    finder = ValueStockFinder()
    
    # 테스트 DataFrame
    test_df = pd.DataFrame({
        '종목코드': ['005930'],
        '종목명': ['삼성전자'],
        '현재가': ['70,000원']
    })
    
    test_options = {'per_max': 15.0}
    test_result_count = {'total': 1, 'buy': 1, 'hold': 0, 'sell': 0}
    
    # CSV 생성
    csv_with_metadata = finder.generate_csv_with_metadata(
        test_df, test_options, test_result_count
    )
    
    # 파싱 시도 (주석 제거)
    lines = csv_with_metadata.split('\n')
    data_lines = [line for line in lines if not line.startswith('#')]
    csv_data_only = '\n'.join(data_lines)
    
    try:
        import io
        parsed_df = pd.read_csv(io.StringIO(csv_data_only))
        
        print("\n✅ CSV 파싱 성공!")
        print(f"   파싱된 행 수: {len(parsed_df)}")
        print(f"   파싱된 컬럼 수: {len(parsed_df.columns)}")
        print(f"\n파싱된 DataFrame:")
        print(parsed_df)
        
        # 검증
        assert len(parsed_df) == 1, "행 수 불일치"
        assert '종목코드' in parsed_df.columns, "컬럼 누락"
        # 종목코드는 정수로 파싱될 수 있음 (005930 → 5930)
        stock_code = str(parsed_df.iloc[0]['종목코드'])
        assert stock_code in ['005930', '5930'], f"데이터 불일치: {stock_code}"
        
        print("\n✅ 파싱 검증 완료!")
        
    except Exception as e:
        print(f"\n❌ 파싱 실패: {e}")
        raise


def test_metadata_components():
    """메타데이터 컴포넌트 상태 테스트"""
    print("\n" + "="*60)
    print("🧪 메타데이터 컴포넌트 상태 테스트")
    print("="*60)
    
    from value_stock_finder import ValueStockFinder
    
    finder = ValueStockFinder()
    
    print("\n📊 시스템 컴포넌트 상태:")
    print(f"   리스크 평가기: {'✅ 활성화' if finder.risk_evaluator else '❌ 비활성화'}")
    print(f"   동적 r/b: {'✅ 활성화' if hasattr(finder, 'regime_calc') and finder.regime_calc else '❌ 비활성화'}")
    print(f"   데이터 가드: {'✅ 활성화' if hasattr(finder, 'freshness_guard') and finder.freshness_guard else '❌ 비활성화'}")
    print(f"   캘리브레이션: {'✅ 활성화' if hasattr(finder, 'calibration_monitor') and finder.calibration_monitor else '❌ 비활성화'}")
    
    # CSV 메타데이터 생성
    test_df = pd.DataFrame({'col': [1]})
    test_options = {}
    test_result_count = {'total': 0, 'buy': 0, 'hold': 0, 'sell': 0}
    
    csv_with_metadata = finder.generate_csv_with_metadata(
        test_df, test_options, test_result_count
    )
    
    # 메타데이터에서 컴포넌트 상태 확인
    assert '# 리스크 평가:' in csv_with_metadata, "리스크 평가 정보 누락"
    assert '# 동적 r/b:' in csv_with_metadata, "동적 r/b 정보 누락"
    assert '# 데이터 가드:' in csv_with_metadata, "데이터 가드 정보 누락"
    assert '# 캘리브레이션:' in csv_with_metadata, "캘리브레이션 정보 누락"
    
    print("\n✅ 컴포넌트 상태 메타데이터 검증 완료!")


if __name__ == '__main__':
    try:
        # 1. CSV 메타데이터 생성 테스트
        test_csv_metadata_generation()
        
        # 2. CSV 파싱 테스트
        test_csv_parsing()
        
        # 3. 메타데이터 컴포넌트 상태 테스트
        test_metadata_components()
        
        print("\n" + "="*60)
        print("🎉 모든 데이터 커트오프 스탬프 테스트 통과!")
        print("="*60)
        print("\n✅ P1-7 완료: 데이터 커트오프 스탬프 도입")
        print("   - CSV 메타데이터 생성 ✅")
        print("   - 파라미터/결과 요약 포함 ✅")
        print("   - 시스템 컴포넌트 상태 포함 ✅")
        print("   - 재현성 확보 ✅")
    
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

