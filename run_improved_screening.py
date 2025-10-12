#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 가치주 스크리닝 실행 스크립트
동적 r/b, 데이터 품질 가드, 점수 캘리브레이션 적용
"""

import logging
import sys
import io
from datetime import datetime

# ✅ Windows 인코딩 문제 해결 (cp949 → utf-8)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """메인 실행 함수"""
    
    print("="*60)
    print("🚀 개선된 가치주 스크리닝 시스템 v2.2.0")
    print("="*60)
    print()
    
    # STEP 1: 모듈 임포트
    print("📦 STEP 1: 모듈 로딩 중...")
    try:
        from dynamic_regime_calculator import DynamicRegimeCalculator, DataFreshnessGuard
        from score_calibration_monitor import ScoreCalibrationMonitor
        logger.info("✅ 개선 모듈 로드 성공")
    except ImportError as e:
        logger.error(f"❌ 개선 모듈 로드 실패: {e}")
        logger.info("💡 먼저 개선 모듈 파일들이 같은 디렉터리에 있는지 확인하세요")
        sys.exit(1)
    
    try:
        from kis_data_provider import KISDataProvider
        logger.info("✅ KIS 데이터 제공자 로드 성공")
    except ImportError as e:
        logger.error(f"❌ KIS 데이터 제공자 로드 실패: {e}")
        sys.exit(1)
    
    # STEP 2: 초기화
    print("\n🔧 STEP 2: 시스템 초기화 중...")
    
    regime_calc = DynamicRegimeCalculator()
    data_guard = DataFreshnessGuard()
    calibration_monitor = ScoreCalibrationMonitor()
    data_provider = KISDataProvider()
    
    logger.info("✅ 모든 컴포넌트 초기화 완료")
    
    # STEP 3: 동적 r, b 계산 예시
    print("\n📊 STEP 3: 동적 파라미터 계산 예시")
    print("-" * 60)
    
    test_sectors = ['전기전자', '금융', 'IT', '제조업', '소비재']
    
    print(f"{'섹터':<12} {'r (요구수익률)':<18} {'b (유보율)':<15}")
    print("-" * 60)
    
    for sector in test_sectors:
        r = regime_calc.get_dynamic_r(sector)
        b = regime_calc.get_dynamic_b(sector)
        print(f"{sector:<10} {r:.4f} ({r*100:.2f}%)    {b:.4f} ({b*100:.2f}%)")
    
    # STEP 4: MoS 입력 검증 예시
    print("\n🔍 STEP 4: MoS 입력 검증 예시")
    print("-" * 60)
    
    test_cases = [
        {'per': 12.5, 'pbr': 1.2, 'roe': 15.0, 'sector': '전기전자', 'desc': '정상 케이스'},
        {'per': -5.0, 'pbr': 1.2, 'roe': 15.0, 'sector': '전기전자', 'desc': '음수 PER'},
        {'per': 12.5, 'pbr': 1.2, 'roe': 150.0, 'sector': 'IT', 'desc': '과도한 ROE (g >= r 위험)'},
    ]
    
    for tc in test_cases:
        is_valid, msg = regime_calc.validate_mos_inputs(
            tc['per'], tc['pbr'], tc['roe'], tc['sector']
        )
        status = "✅ 통과" if is_valid else "❌ 실패"
        print(f"{tc['desc']:<20} {status:<10} {msg}")
    
    # STEP 5: 데이터 품질 가드 예시
    print("\n🛡️ STEP 5: 데이터 품질 가드 예시")
    print("-" * 60)
    
    # 신선도 체크
    from datetime import timedelta
    
    data_dict = {
        'price_ts': datetime.now(),
        'financial_ts': datetime.now() - timedelta(days=30),
        'sector': '전기전자'
    }
    
    is_fresh, msg = data_guard.check_data_freshness(data_dict)
    print(f"데이터 신선도: {'✅ 통과' if is_fresh else '❌ 실패'} - {msg}")
    
    # 재무 상식 체크
    financial_data = {
        'per': 12.5,
        'pbr': 1.2,
        'roe': 15.0,
        'eps': 5000,
        'bps': 50000
    }
    
    is_sane, msg = data_guard.check_financial_sanity(financial_data)
    print(f"재무 상식 체크: {'✅ 통과' if is_sane else '❌ 실패'} - {msg}")
    
    # 섹터 매핑 체크
    valid_sectors = {'금융', '제조업', 'IT', '전기전자', '소비재', '건설'}
    
    for sector in ['전기전자', '기타', '']:
        is_valid, msg = data_guard.check_sector_mapping(sector, valid_sectors)
        status = "✅" if is_valid else "❌"
        print(f"섹터 '{sector}': {status} {msg}")
    
    # STEP 6: 가상 스크리닝 결과로 캘리브레이션 테스트
    print("\n📈 STEP 6: 점수 캘리브레이션 테스트")
    print("-" * 60)
    
    # 가상 결과 생성
    import random
    
    results = [
        {
            'symbol': f'{i:06d}',
            'name': f'종목{i}',
            'value_score': random.gauss(75, 15),  # 평균 75, 표준편차 15
            'recommendation': random.choice(
                ['STRONG_BUY'] * 1 + ['BUY'] * 2 + ['HOLD'] * 4 + ['SELL'] * 3
            ),
            'sector': random.choice(['제조업', '금융', 'IT', '소비재', '건설'])
        }
        for i in range(100)
    ]
    
    # 점수 기록
    calibration_monitor.record_scores(results)
    logger.info("✅ 캘리브레이션 통계 기록 완료")
    
    # 컷오프 제안
    scores = [r['value_score'] for r in results]
    cutoffs = calibration_monitor.suggest_grade_cutoffs(scores)
    
    print("\n제안된 점수 컷오프:")
    for grade, score in cutoffs.items():
        print(f"  {grade:<12}: {score:.1f}점 이상")
    
    # 월별 리포트
    print("\n월별 캘리브레이션 리포트:")
    print("=" * 60)
    report = calibration_monitor.generate_monthly_report()
    print(report)
    
    # STEP 7: 통합 예시 (단일 종목)
    print("\n💎 STEP 7: 단일 종목 통합 분석 예시")
    print("-" * 60)
    
    # 예시 종목 데이터 (실제로는 KIS API에서 조회)
    stock_data = {
        'symbol': '005930',
        'name': '삼성전자',
        'per': 12.5,
        'pbr': 1.2,
        'roe': 15.0,
        'eps': 5000,
        'bps': 50000,
        'sector': '전기전자'
    }
    
    print(f"\n종목: {stock_data['name']} ({stock_data['symbol']})")
    print(f"섹터: {stock_data['sector']}")
    print(f"PER: {stock_data['per']:.2f}, PBR: {stock_data['pbr']:.2f}, ROE: {stock_data['roe']:.1f}%")
    
    # 1. 데이터 품질 검증
    is_sane, msg = data_guard.check_financial_sanity(stock_data)
    print(f"\n데이터 품질: {'✅ 통과' if is_sane else '❌ 실패'} - {msg}")
    
    if is_sane:
        # 2. MoS 입력 검증
        is_valid, msg = regime_calc.validate_mos_inputs(
            stock_data['per'],
            stock_data['pbr'],
            stock_data['roe'],
            stock_data['sector']
        )
        print(f"MoS 검증: {'✅ 통과' if is_valid else '❌ 실패'} - {msg}")
        
        if is_valid:
            # 3. 동적 파라미터 조회
            r = regime_calc.get_dynamic_r(stock_data['sector'])
            b = regime_calc.get_dynamic_b(stock_data['sector'])
            
            print(f"\n동적 파라미터:")
            print(f"  r (요구수익률): {r:.4f} ({r*100:.2f}%)")
            print(f"  b (유보율): {b:.4f} ({b*100:.2f}%)")
            
            # 4. MoS 계산
            roe_decimal = stock_data['roe'] / 100.0
            g = roe_decimal * b
            
            print(f"  g (성장률): {g:.4f} ({g*100:.2f}%)")
            
            if g < r:
                # Justified Multiples
                pb_star = (roe_decimal - g) / (r - g)
                pe_star = (1 - b) / (r - g)
                
                print(f"\nJustified Multiples:")
                print(f"  PBR*: {pb_star:.2f}배 (현재: {stock_data['pbr']:.2f}배)")
                print(f"  PER*: {pe_star:.2f}배 (현재: {stock_data['per']:.2f}배)")
                
                # MoS 계산
                mos_pb = (pb_star / stock_data['pbr'] - 1.0) * 100 if stock_data['pbr'] > 0 else 0
                mos_pe = (pe_star / stock_data['per'] - 1.0) * 100 if stock_data['per'] > 0 else 0
                mos = min(mos_pb, mos_pe)
                
                print(f"\n안전마진(MoS):")
                print(f"  PBR 경로: {mos_pb:+.1f}%")
                print(f"  PER 경로: {mos_pe:+.1f}%")
                print(f"  최종 MoS: {mos:+.1f}% (보수적)")
                
                # 평가
                if mos >= 30:
                    assessment = "🌟 매우 안전"
                elif mos >= 20:
                    assessment = "✅ 안전"
                elif mos >= 10:
                    assessment = "⚠️ 보통"
                else:
                    assessment = "❌ 주의"
                
                print(f"\n평가: {assessment}")
            else:
                print(f"\n⚠️ 경고: g={g:.4f} >= r={r:.4f}, MoS 계산 불가")
    
    # 완료
    print("\n" + "="*60)
    print("✅ 개선 시스템 테스트 완료!")
    print("="*60)
    print()
    print("📂 생성된 파일:")
    print("  - logs/calibration/calibration_YYYY-MM.json")
    print()
    print("📖 다음 단계:")
    print("  1. value_stock_finder.py에 통합 (IMPROVEMENT_INTEGRATION_GUIDE.md 참조)")
    print("  2. streamlit run value_stock_finder.py 실행")
    print("  3. 월별 캘리브레이션 리포트 확인")
    print("  4. 백테스트 실행 (run_backtest.py)")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        logger.exception("예기치 못한 오류:")
        sys.exit(1)

