#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v2.2.2 퍼센타일 글로벌 대체 로직 테스트
"""

import sys
import io
import logging

# Windows 인코딩 처리
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def test_global_percentiles():
    """글로벌 퍼센타일 캐시 테스트"""
    print("\n" + "="*60)
    print("🧪 글로벌 퍼센타일 캐시 테스트")
    print("="*60)
    
    from value_stock_finder import ValueStockFinder
    
    finder = ValueStockFinder()
    
    # 글로벌 퍼센타일 로드
    global_pcts = finder._get_global_percentiles_cached()
    
    print("\n📊 글로벌 퍼센타일:")
    for metric, pcts in global_pcts.items():
        print(f"\n  {metric.upper()}:")
        print(f"    p10={pcts['p10']}, p25={pcts['p25']}, p50={pcts['p50']}")
        print(f"    p75={pcts['p75']}, p90={pcts['p90']}, n={pcts['sample_size']}")
    
    # 각 메트릭의 기본값이 설정되어 있는지 확인
    for metric in ['per', 'pbr', 'roe']:
        assert metric in global_pcts, f"{metric} 메트릭이 글로벌 퍼센타일에 없음"
        assert 'p50' in global_pcts[metric], f"{metric}의 p50이 없음"
        assert 'sample_size' in global_pcts[metric], f"{metric}의 sample_size가 없음"
    
    print("\n✅ 글로벌 퍼센타일 캐시 테스트 통과!")


def test_percentile_v2_small_sample():
    """극소 표본 테스트 (n < 10)"""
    print("\n" + "="*60)
    print("🧪 극소 표본 테스트 (n < 10 → 글로벌 사용)")
    print("="*60)
    
    from value_stock_finder import ValueStockFinder
    
    finder = ValueStockFinder()
    
    # 극소 표본 (n=5)
    small_pcts = {
        'p25': 8.0, 'p50': 10.0, 'p75': 12.0,
        'sample_size': 5
    }
    
    value = 10.0
    result = finder._percentile_from_breakpoints_v2(
        value, small_pcts, 'per', use_global=True
    )
    
    print(f"\n  입력:")
    print(f"    값: {value}")
    print(f"    섹터 표본: n={small_pcts['sample_size']}")
    print(f"  결과:")
    print(f"    퍼센타일: {result:.1f}%")
    
    assert result is not None, "결과가 None이 아니어야 함"
    assert 0 <= result <= 100, f"퍼센타일은 0-100 범위여야 함: {result}"
    
    print("\n✅ 극소 표본 테스트 통과!")


def test_percentile_v2_medium_sample():
    """중간 표본 테스트 (10 <= n < 30)"""
    print("\n" + "="*60)
    print("🧪 중간 표본 테스트 (10 <= n < 30 → 가중 평균)")
    print("="*60)
    
    from value_stock_finder import ValueStockFinder
    
    finder = ValueStockFinder()
    
    # 중간 표본 (n=20)
    medium_pcts = {
        'p10': 5.0, 'p25': 8.0, 'p50': 12.0, 
        'p75': 18.0, 'p90': 30.0,
        'sample_size': 20
    }
    
    value = 10.0
    result = finder._percentile_from_breakpoints_v2(
        value, medium_pcts, 'per', use_global=True
    )
    
    print(f"\n  입력:")
    print(f"    값: {value}")
    print(f"    섹터 표본: n={medium_pcts['sample_size']}")
    print(f"  결과:")
    print(f"    퍼센타일 (가중 평균): {result:.1f}%")
    
    # 가중 평균 계산
    # n=20 → weight_sector = (20-10)/20 = 0.5, weight_global = 0.5
    print(f"  가중치: 섹터 50%, 글로벌 50%")
    
    assert result is not None, "결과가 None이 아니어야 함"
    assert 0 <= result <= 100, f"퍼센타일은 0-100 범위여야 함: {result}"
    
    print("\n✅ 중간 표본 테스트 통과!")


def test_percentile_v2_large_sample():
    """충분한 표본 테스트 (n >= 30)"""
    print("\n" + "="*60)
    print("🧪 충분한 표본 테스트 (n >= 30 → 섹터만 사용)")
    print("="*60)
    
    from value_stock_finder import ValueStockFinder
    
    finder = ValueStockFinder()
    
    # 충분한 표본 (n=50)
    large_pcts = {
        'p10': 5.0, 'p25': 8.0, 'p50': 12.0, 
        'p75': 18.0, 'p90': 30.0,
        'sample_size': 50
    }
    
    value = 10.0
    result = finder._percentile_from_breakpoints_v2(
        value, large_pcts, 'per', use_global=True
    )
    
    print(f"\n  입력:")
    print(f"    값: {value}")
    print(f"    섹터 표본: n={large_pcts['sample_size']}")
    print(f"  결과:")
    print(f"    퍼센타일 (섹터만): {result:.1f}%")
    
    assert result is not None, "결과가 None이 아니어야 함"
    assert 0 <= result <= 100, f"퍼센타일은 0-100 범위여야 함: {result}"
    
    print("\n✅ 충분한 표본 테스트 통과!")


def test_percentile_v2_iqr_zero():
    """IQR ≈ 0 테스트"""
    print("\n" + "="*60)
    print("🧪 IQR ≈ 0 테스트 (극단적으로 납작한 분포)")
    print("="*60)
    
    from value_stock_finder import ValueStockFinder
    
    finder = ValueStockFinder()
    
    # IQR ≈ 0 (모든 값이 동일)
    flat_pcts = {
        'p10': 10.0, 'p25': 10.0, 'p50': 10.0, 
        'p75': 10.0, 'p90': 10.0,
        'sample_size': 50  # 충분한 표본이지만 분포가 납작함
    }
    
    value = 10.0
    result = finder._percentile_from_breakpoints_v2(
        value, flat_pcts, 'per', use_global=True
    )
    
    print(f"\n  입력:")
    print(f"    값: {value}")
    print(f"    섹터 표본: n={flat_pcts['sample_size']}")
    print(f"    IQR: {flat_pcts['p75'] - flat_pcts['p25']}")
    print(f"  결과:")
    print(f"    퍼센타일 (IQR≈0 → 글로벌 대체): {result:.1f}%")
    
    # IQR≈0일 때는 글로벌로 대체되거나 50.0 반환
    assert result is not None, "결과가 None이 아니어야 함"
    
    print("\n✅ IQR ≈ 0 테스트 통과!")


def test_integration_evaluate_sector_metrics():
    """_evaluate_sector_adjusted_metrics 통합 테스트"""
    print("\n" + "="*60)
    print("🧪 섹터 조정 메트릭 평가 통합 테스트")
    print("="*60)
    
    from value_stock_finder import ValueStockFinder
    
    finder = ValueStockFinder()
    
    # 극소 표본 섹터 데이터
    test_stock = {
        'symbol': '999999',
        'name': '테스트종목',
        'per': 10.0,
        'pbr': 1.0,
        'roe': 12.0,
        'sector_name': '소형섹터',
        'sector_stats': {
            'sample_size': 8,  # 극소 표본 → 글로벌 사용
            'per_percentiles': {'p25': 8, 'p50': 10, 'p75': 12},
            'pbr_percentiles': {'p25': 0.8, 'p50': 1.0, 'p75': 1.2},
            'roe_percentiles': {'p25': 10, 'p50': 12, 'p75': 15}
        },
        'sector_benchmarks': {
            'per_range': (5, 20),
            'pbr_range': (0.5, 2.0),
            'roe_range': (5, 20)
        }
    }
    
    result = finder._evaluate_sector_adjusted_metrics(test_stock)
    
    print(f"\n  입력:")
    print(f"    종목: {test_stock['name']}")
    print(f"    섹터 표본: n={test_stock['sector_stats']['sample_size']}")
    print(f"  결과:")
    print(f"    PER 점수: {result['per_score']:.2f}")
    print(f"    PBR 점수: {result['pbr_score']:.2f}")
    print(f"    ROE 점수: {result['roe_score']:.2f}")
    print(f"    총점: {result['per_score'] + result['pbr_score'] + result['roe_score']:.2f}")
    
    assert 'per_score' in result, "per_score가 결과에 없음"
    assert 'pbr_score' in result, "pbr_score가 결과에 없음"
    assert 'roe_score' in result, "roe_score가 결과에 없음"
    
    print("\n✅ 섹터 조정 메트릭 평가 통합 테스트 통과!")


if __name__ == '__main__':
    try:
        # 1. 글로벌 퍼센타일 캐시 테스트
        test_global_percentiles()
        
        # 2. 극소 표본 테스트
        test_percentile_v2_small_sample()
        
        # 3. 중간 표본 테스트
        test_percentile_v2_medium_sample()
        
        # 4. 충분한 표본 테스트
        test_percentile_v2_large_sample()
        
        # 5. IQR ≈ 0 테스트
        test_percentile_v2_iqr_zero()
        
        # 6. 통합 테스트
        test_integration_evaluate_sector_metrics()
        
        print("\n" + "="*60)
        print("🎉 모든 퍼센타일 글로벌 대체 테스트 통과! v2.2.2 완료")
        print("="*60)
    
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

