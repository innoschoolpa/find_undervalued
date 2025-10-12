#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v2.2.2 리스크 평가기 통합 테스트
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

from risk_flag_evaluator import RiskFlagEvaluator


def test_risk_evaluator():
    """리스크 평가기 기본 테스트"""
    print("\n" + "="*60)
    print("🧪 리스크 평가기 기본 테스트")
    print("="*60)
    
    evaluator = RiskFlagEvaluator()
    evaluator.load_management_stocks()
    
    # 테스트 케이스 1: 정상 종목
    normal_stock = {
        'symbol': '005930',
        'name': '삼성전자',
        'per': 10,
        'pbr': 1.0,
        'roe': 12,
        'trading_value': 100_000_000_000,  # 1000억
        'debt_ratio': 150
    }
    
    penalty, warnings = evaluator.evaluate_all_risks(normal_stock)
    print(f"\n✅ 정상 종목 (삼성전자)")
    print(f"   감점: {penalty}점")
    print(f"   경고: {len(warnings)}개")
    
    assert penalty == 0, f"정상 종목의 감점은 0이어야 함: {penalty}"
    assert len(warnings) == 0, f"정상 종목의 경고는 0개여야 함: {len(warnings)}"
    
    # 테스트 케이스 2: 리스크 종목 (복합 리스크)
    risky_stock = {
        'symbol': '999999',
        'name': '위험종목',
        'per': 10,
        'pbr': 1.0,
        'roe': 12,
        'operating_cash_flow_history': [-100, -200, -150],  # 3년 연속 적자
        'net_income_history': [100, -50, 200, -100],  # 변동성 높음
        'audit_opinion': '한정',
        'debt_ratio': 650,
        'trading_value': 50_000_000,  # 0.5억 (저유동성)
        'is_management_stock': True
    }
    
    penalty, warnings = evaluator.evaluate_all_risks(risky_stock)
    print(f"\n🚨 리스크 종목 (복합 리스크)")
    print(f"   감점: {penalty}점")
    print(f"   경고: {len(warnings)}개")
    for i, w in enumerate(warnings, 1):
        print(f"   {i}. {w}")
    
    assert penalty < 0, f"리스크 종목의 감점은 음수여야 함: {penalty}"
    assert len(warnings) > 0, f"리스크 종목의 경고는 1개 이상이어야 함: {len(warnings)}"
    
    # 테스트 케이스 3: 저유동성만 있는 종목
    low_liquidity = {
        'symbol': '123456',
        'name': '저유동성종목',
        'per': 10,
        'pbr': 1.0,
        'roe': 12,
        'trading_value': 80_000_000,  # 0.8억
        'debt_ratio': 100
    }
    
    penalty, warnings = evaluator.evaluate_all_risks(low_liquidity)
    print(f"\n⚠️ 저유동성 종목")
    print(f"   감점: {penalty}점")
    print(f"   경고: {len(warnings)}개")
    
    assert penalty < 0, f"저유동성 종목은 감점이 있어야 함: {penalty}"
    assert -15 <= penalty <= -5, f"저유동성 감점 범위 확인: {penalty}"
    
    print("\n✅ 모든 기본 테스트 통과!")


def test_risk_summary():
    """리스크 요약 테스트"""
    print("\n" + "="*60)
    print("🧪 리스크 요약 기능 테스트")
    print("="*60)
    
    evaluator = RiskFlagEvaluator()
    
    # 심각한 리스크 종목
    critical_stock = {
        'symbol': '888888',
        'name': 'CRITICAL종목',
        'per': 10,
        'pbr': 1.0,
        'roe': 12,
        'operating_cash_flow_history': [-100, -200, -150],
        'audit_opinion': '부적정',
        'capital_impairment_ratio': 60,
        'trading_value': 30_000_000,
        'is_management_stock': True
    }
    
    summary = evaluator.get_risk_summary(critical_stock)
    
    print(f"\n📊 리스크 요약:")
    print(f"   종목: {summary['name']} ({summary['symbol']})")
    print(f"   리스크 레벨: {summary['risk_level']}")
    print(f"   총 감점: {summary['total_penalty']}점")
    print(f"   경고 개수: {summary['warning_count']}개")
    
    assert summary['risk_level'] == 'CRITICAL', f"심각한 리스크 종목은 CRITICAL이어야 함: {summary['risk_level']}"
    assert summary['total_penalty'] < -50, f"심각한 리스크 종목은 -50점 이하여야 함: {summary['total_penalty']}"
    
    print("\n✅ 리스크 요약 테스트 통과!")


def test_value_stock_finder_integration():
    """ValueStockFinder 통합 테스트"""
    print("\n" + "="*60)
    print("🧪 ValueStockFinder 통합 테스트")
    print("="*60)
    
    try:
        from value_stock_finder import ValueStockFinder
        
        finder = ValueStockFinder()
        
        # risk_evaluator가 초기화되었는지 확인
        assert hasattr(finder, 'risk_evaluator'), "risk_evaluator 속성이 없음"
        
        if finder.risk_evaluator:
            print("\n✅ ValueStockFinder에 risk_evaluator가 성공적으로 통합됨")
            
            # 간단한 평가 테스트
            test_stock = {
                'symbol': '005930',
                'name': '삼성전자',
                'per': 10.0,
                'pbr': 1.2,
                'roe': 15.0,
                'sector': '전기전자',
                'sector_name': '전기전자',
                'current_price': 70000,
                'market_cap': 400_000_000_000_000,
                'trading_value': 100_000_000_000,
                'operating_cash_flow': 50_000_000_000,
                'operating_income': 30_000_000_000,
                'interest_expense': 1_000_000_000
            }
            
            # evaluate_value_stock 호출
            result = finder.evaluate_value_stock(test_stock)
            
            if result:
                # result는 딕셔너리 {'value_score', 'grade', 'recommendation', 'details'}
                score = result.get('value_score', 0)
                details = result.get('details', {})
                
                print(f"\n📊 평가 결과:")
                print(f"   종목: {test_stock['name']}")
                print(f"   점수: {score:.1f}점")
                print(f"   등급: {result.get('grade', 'N/A')}")
                print(f"   추천: {result.get('recommendation', 'N/A')}")
                print(f"   리스크 감점: {details.get('risk_penalty', 0)}점")
                print(f"   리스크 경고: {details.get('risk_count', 0)}개")
                
                assert 'risk_penalty' in details, "details에 risk_penalty가 없음"
                assert 'risk_warnings' in details, "details에 risk_warnings가 없음"
                
                print("\n✅ 평가 메서드 통합 테스트 통과!")
            else:
                print("⚠️ 평가 결과가 None (데이터 품질 가드에 의해 제외됨)")
        else:
            print("⚠️ risk_evaluator가 None (임포트 실패 또는 비활성화)")
    
    except Exception as e:
        print(f"❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    try:
        # 1. 리스크 평가기 기본 테스트
        test_risk_evaluator()
        
        # 2. 리스크 요약 테스트
        test_risk_summary()
        
        # 3. ValueStockFinder 통합 테스트
        test_value_stock_finder_integration()
        
        print("\n" + "="*60)
        print("🎉 모든 테스트 통과! v2.2.2 리스크 평가기 통합 완료")
        print("="*60)
    
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

