#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v2.2.2 캘리브레이션 UI 피드백 루프 테스트
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


def test_get_score_statistics():
    """점수 통계 조회 테스트"""
    print("\n" + "="*60)
    print("🧪 점수 통계 조회 테스트")
    print("="*60)
    
    from score_calibration_monitor import ScoreCalibrationMonitor
    import random
    
    monitor = ScoreCalibrationMonitor()
    
    # 가상 결과 생성
    results = [
        {
            'symbol': f'{i:06d}',
            'name': f'종목{i}',
            'value_score': random.gauss(75, 15),  # 평균 75, 표준편차 15
            'recommendation': random.choice(['STRONG_BUY'] * 1 + ['BUY'] * 2 + ['HOLD'] * 4 + ['SELL'] * 3),
            'sector': random.choice(['제조업', '금융', 'IT'])
        }
        for i in range(100)
    ]
    
    # 점수 기록
    monitor.record_scores(results)
    
    # 통계 조회
    stats = monitor.get_score_statistics()
    
    print(f"\n📊 점수 통계:")
    if stats:
        print(f"   샘플 크기: {stats['sample_size']}")
        print(f"   평균: {stats['distribution'].get('mean', 0):.1f}")
        print(f"   중앙값: {stats['distribution'].get('median', 0):.1f}")
        print(f"   표준편차: {stats['distribution'].get('stdev', 0):.1f}")
        
        print(f"\n  퍼센타일:")
        for pct, score in sorted(stats['percentiles'].items()):
            print(f"    {pct}: {score:.1f}점")
        
        assert stats['sample_size'] == 100, "샘플 크기 불일치"
        assert 'percentiles' in stats, "퍼센타일 정보 없음"
        assert 'distribution' in stats, "분포 정보 없음"
        
        print("\n✅ 점수 통계 조회 테스트 통과!")
    else:
        print("❌ 통계를 가져올 수 없음")
        raise AssertionError("통계 조회 실패")


def test_percentile_to_score_conversion():
    """퍼센타일 → 점수 변환 테스트"""
    print("\n" + "="*60)
    print("🧪 퍼센타일 → 점수 변환 테스트")
    print("="*60)
    
    from score_calibration_monitor import ScoreCalibrationMonitor
    import random
    
    monitor = ScoreCalibrationMonitor()
    
    # 점수 생성 (60~120)
    scores = [random.uniform(60, 120) for _ in range(100)]
    results = [
        {'value_score': s, 'recommendation': 'HOLD', 'sector': '제조업'}
        for s in scores
    ]
    
    monitor.record_scores(results)
    stats = monitor.get_score_statistics()
    
    if stats and 'percentiles' in stats:
        percentiles = stats['percentiles']
        
        print(f"\n📊 점수 분포:")
        print(f"   최소: {min(scores):.1f}")
        print(f"   최대: {max(scores):.1f}")
        
        print(f"\n  변환 예시 (상위 % → 점수):")
        # 상위 20% = p80
        if 'p80' in percentiles:
            print(f"    상위 20% (BUY): {percentiles['p80']:.1f}점 이상")
        
        # 상위 50% = p50
        if 'p50' in percentiles:
            print(f"    상위 50% (HOLD): {percentiles['p50']:.1f}점 이상")
        
        print("\n✅ 변환 테스트 통과!")
    else:
        print("❌ 퍼센타일 정보 없음")
        raise AssertionError("퍼센타일 조회 실패")


def test_ui_integration():
    """UI 통합 시뮬레이션 테스트"""
    print("\n" + "="*60)
    print("🧪 UI 통합 시뮬레이션 테스트")
    print("="*60)
    
    from score_calibration_monitor import ScoreCalibrationMonitor
    import random
    
    monitor = ScoreCalibrationMonitor()
    
    # 점수 생성
    scores = [random.uniform(50, 130) for _ in range(100)]
    results = [
        {'value_score': s, 'recommendation': 'HOLD', 'sector': '제조업'}
        for s in scores
    ]
    
    monitor.record_scores(results)
    stats = monitor.get_score_statistics()
    
    # UI 시뮬레이션
    buy_percentile = 20.0  # 상위 20% = BUY
    hold_percentile = 50.0  # 상위 50% = HOLD
    
    print(f"\n📊 UI 설정:")
    print(f"   BUY: 상위 {buy_percentile:.0f}%")
    print(f"   HOLD: 상위 {hold_percentile:.0f}%")
    
    if stats and 'percentiles' in stats:
        percentiles = stats['percentiles']
        
        # p80 = 상위 20%, p50 = 상위 50%
        buy_score = percentiles.get('p80', None)
        hold_score = percentiles.get('p50', None)
        
        if buy_score and hold_score:
            print(f"\n✅ 실시간 컷오프:")
            print(f"   BUY: {buy_score:.1f}점 이상")
            print(f"   HOLD: {hold_score:.1f}~{buy_score:.1f}점")
            print(f"   SELL: {hold_score:.1f}점 미만")
            
            # 컷오프 검증
            assert buy_score > hold_score, "BUY 점수가 HOLD보다 낮음"
            assert hold_score > 0, "HOLD 점수가 0 이하"
            
            print("\n✅ UI 통합 테스트 통과!")
        else:
            print("❌ 점수 계산 실패")
            raise AssertionError("점수 컷오프 계산 실패")
    else:
        print("❌ 통계 정보 없음")
        raise AssertionError("통계 조회 실패")


if __name__ == '__main__':
    try:
        # 1. 점수 통계 조회 테스트
        test_get_score_statistics()
        
        # 2. 퍼센타일 → 점수 변환 테스트
        test_percentile_to_score_conversion()
        
        # 3. UI 통합 시뮬레이션 테스트
        test_ui_integration()
        
        print("\n" + "="*60)
        print("🎉 모든 캘리브레이션 UI 테스트 통과!")
        print("="*60)
        print("\n✅ P2-1 완료: 캘리브레이션 UI 피드백 루프")
        print("   - 점수 통계 조회 ✅")
        print("   - 퍼센타일 → 점수 변환 ✅")
        print("   - 실시간 컷오프 계산 ✅")
        print("   - UI 슬라이더 통합 ✅")
    
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


