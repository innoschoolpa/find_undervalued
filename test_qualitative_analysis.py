"""
정성적 리스크 분석 테스트 코드
"""

import logging
import sys
from typing import Dict, Any

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_qualitative_risk_analyzer():
    """정성적 리스크 분석기 테스트"""
    try:
        from qualitative_risk_analyzer import (
            QualitativeRiskAnalyzer,
            PolicyRiskAnalyzer,
            ESGRiskAnalyzer,
            SentimentRiskAnalyzer,
            RiskType
        )
        
        print("🚀 정성적 리스크 분석기 테스트 시작")
        
        # 분석기 초기화
        analyzer = QualitativeRiskAnalyzer()
        
        # 테스트 데이터
        test_data = {
            'roe': 31.3,
            'roa': 25.0,
            'debt_ratio': 15.5,
            'current_ratio': 250.0,
            'revenue_growth_rate': 63.07,
            'operating_income_growth_rate': 85.33,
            'net_income_growth_rate': 106.67,
            'net_profit_margin': 36.48,
            'per': 15.2,
            'pbr': 3.1
        }
        
        print("\n📊 테스트 데이터:")
        for key, value in test_data.items():
            print(f"  {key}: {value}")
        
        # 시프트업 정성적 리스크 분석
        print("\n🎮 시프트업 정성적 리스크 분석")
        shiftup_risk = analyzer.analyze_comprehensive_risk("462870", "게임업", test_data)
        print(f"  종합 리스크 점수: {shiftup_risk['comprehensive_risk_score']:.1f}")
        print(f"  종합 리스크 레벨: {shiftup_risk['comprehensive_risk_level']}")
        print(f"  리스크 조정 계수: {shiftup_risk['risk_adjustment_factor']:.2f}")
        print("  개별 리스크:")
        for risk_type, assessment in shiftup_risk['individual_risks'].items():
            print(f"    {risk_type}: {assessment.score:.1f}점 ({assessment.risk_level.value})")
        
        # 한미반도체 정성적 리스크 분석
        print("\n🔬 한미반도체 정성적 리스크 분석")
        hanmi_risk = analyzer.analyze_comprehensive_risk("042700", "반도체", test_data)
        print(f"  종합 리스크 점수: {hanmi_risk['comprehensive_risk_score']:.1f}")
        print(f"  종합 리스크 레벨: {hanmi_risk['comprehensive_risk_level']}")
        print(f"  리스크 조정 계수: {hanmi_risk['risk_adjustment_factor']:.2f}")
        print("  개별 리스크:")
        for risk_type, assessment in hanmi_risk['individual_risks'].items():
            print(f"    {risk_type}: {assessment.score:.1f}점 ({assessment.risk_level.value})")
        
        # 리스크 요약 생성
        print("\n📋 리스크 요약:")
        shiftup_summary = analyzer.get_risk_summary(shiftup_risk)
        hanmi_summary = analyzer.get_risk_summary(hanmi_risk)
        print(f"  시프트업: {shiftup_summary}")
        print(f"  한미반도체: {hanmi_summary}")
        
        print("\n✅ 정성적 리스크 분석기 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_risk_analyzers():
    """개별 리스크 분석기 테스트"""
    try:
        print("\n🚀 개별 리스크 분석기 테스트 시작")
        
        from qualitative_risk_analyzer import (
            PolicyRiskAnalyzer,
            ESGRiskAnalyzer,
            SentimentRiskAnalyzer
        )
        
        # 테스트 데이터
        test_data = {
            'roe': 42.29,
            'roa': 33.38,
            'debt_ratio': 26.71,
            'current_ratio': 284.28,
            'revenue_growth_rate': 63.07,
            'operating_income_growth_rate': 85.33,
            'net_income_growth_rate': 106.67,
            'net_profit_margin': 36.48,
            'per': 59.31,
            'pbr': 13.06
        }
        
        # 정책 리스크 분석기 테스트
        print("\n🏛️ 정책 리스크 분석기 테스트")
        policy_analyzer = PolicyRiskAnalyzer()
        policy_assessment = policy_analyzer.analyze_risk("042700", "반도체", test_data)
        print(f"  정책 리스크 점수: {policy_assessment.score:.1f}")
        print(f"  정책 리스크 레벨: {policy_assessment.risk_level.value}")
        print(f"  설명: {policy_assessment.description}")
        print(f"  신뢰도: {policy_assessment.confidence:.1f}")
        
        # ESG 리스크 분석기 테스트
        print("\n🌱 ESG 리스크 분석기 테스트")
        esg_analyzer = ESGRiskAnalyzer()
        esg_assessment = esg_analyzer.analyze_risk("042700", "반도체", test_data)
        print(f"  ESG 리스크 점수: {esg_assessment.score:.1f}")
        print(f"  ESG 리스크 레벨: {esg_assessment.risk_level.value}")
        print(f"  설명: {esg_assessment.description}")
        print(f"  신뢰도: {esg_assessment.confidence:.1f}")
        
        # 시장 감정 리스크 분석기 테스트
        print("\n📈 시장 감정 리스크 분석기 테스트")
        sentiment_analyzer = SentimentRiskAnalyzer()
        sentiment_assessment = sentiment_analyzer.analyze_risk("042700", "반도체", test_data)
        print(f"  감정 리스크 점수: {sentiment_assessment.score:.1f}")
        print(f"  감정 리스크 레벨: {sentiment_assessment.risk_level.value}")
        print(f"  설명: {sentiment_assessment.description}")
        print(f"  신뢰도: {sentiment_assessment.confidence:.1f}")
        
        print("\n✅ 개별 리스크 분석기 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 개별 분석기 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_qualitative_analyzer():
    """향상된 정성적 통합 분석기 테스트"""
    try:
        print("\n🚀 향상된 정성적 통합 분석기 테스트 시작")
        
        from enhanced_qualitative_integrated_analyzer import (
            EnhancedQualitativeIntegratedAnalyzer
        )
        
        # 분석기 초기화
        analyzer = EnhancedQualitativeIntegratedAnalyzer()
        
        # 테스트 종목들
        test_stocks = [
            ("462870", "시프트업"),
            ("042700", "한미반도체"),
            ("000270", "기아")
        ]
        
        print("\n📈 종목별 종합 분석 결과:")
        print("=" * 80)
        
        results = []
        for symbol, name in test_stocks:
            result = analyzer.analyze_single_stock_comprehensive(symbol, name)
            results.append(result)
            
            print(f"\n{name} ({symbol}):")
            print(f"  종합 점수: {result['comprehensive_score']:.1f}점 ({result['comprehensive_grade']})")
            print(f"  리스크 레벨: {result['risk_level']} ({result['risk_grade']})")
            print(f"  투자 추천: {result['investment_recommendation']}")
            
            # 세부 breakdown
            breakdown = result.get('score_breakdown', {})
            if breakdown:
                print("  세부 점수:")
                for key, value in breakdown.items():
                    if isinstance(value, (int, float)):
                        print(f"    {key}: {value:.1f}")
        
        # 프리미엄 저평가 종목 발굴
        print("\n🏆 프리미엄 저평가 종목 (60점 이상, 보통 리스크 이하):")
        premium_stocks = analyzer.find_premium_undervalued_stocks(
            [s[0] for s in test_stocks],
            [s[1] for s in test_stocks],
            min_score=60.0,
            max_risk_level="보통"
        )
        
        if premium_stocks:
            for i, stock in enumerate(premium_stocks, 1):
                print(f"  {i}. {stock['name']}({stock['symbol']}): {stock['comprehensive_score']:.1f}점")
        else:
            print("  조건을 만족하는 프리미엄 종목이 없습니다.")
        
        # 분석 리포트 생성
        print("\n📋 종합 분석 리포트:")
        report = analyzer.generate_analysis_report(results)
        print(report)
        
        print("\n✅ 향상된 정성적 통합 분석기 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 향상된 분석기 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def compare_risk_analysis():
    """리스크 분석 결과 비교"""
    try:
        print("\n🚀 리스크 분석 결과 비교 테스트 시작")
        
        from qualitative_risk_analyzer import QualitativeRiskAnalyzer
        
        analyzer = QualitativeRiskAnalyzer()
        
        # 시프트업 데이터 (게임업계)
        shiftup_data = {
            'roe': 31.3,
            'roa': 25.0,
            'debt_ratio': 15.5,
            'current_ratio': 250.0,
            'revenue_growth_rate': 63.07,
            'operating_income_growth_rate': 85.33,
            'net_income_growth_rate': 106.67,
            'net_profit_margin': 36.48,
            'per': 15.2,
            'pbr': 3.1
        }
        
        # 한미반도체 데이터 (반도체업계)
        hanmi_data = {
            'roe': 42.29,
            'roa': 33.38,
            'debt_ratio': 26.71,
            'current_ratio': 284.28,
            'revenue_growth_rate': 63.07,
            'operating_income_growth_rate': 85.33,
            'net_income_growth_rate': 106.67,
            'net_profit_margin': 36.48,
            'per': 59.31,
            'pbr': 13.06
        }
        
        print("\n📊 리스크 분석 비교:")
        print("=" * 60)
        
        # 시프트업 리스크 분석
        shiftup_risk = analyzer.analyze_comprehensive_risk("462870", "게임업", shiftup_data)
        print(f"시프트업 (게임업계):")
        print(f"  종합 리스크 점수: {shiftup_risk['comprehensive_risk_score']:.1f}")
        print(f"  종합 리스크 레벨: {shiftup_risk['comprehensive_risk_level']}")
        print(f"  조정 계수: {shiftup_risk['risk_adjustment_factor']:.2f}")
        
        # 한미반도체 리스크 분석
        hanmi_risk = analyzer.analyze_comprehensive_risk("042700", "반도체", hanmi_data)
        print(f"한미반도체 (반도체업계):")
        print(f"  종합 리스크 점수: {hanmi_risk['comprehensive_risk_score']:.1f}")
        print(f"  종합 리스크 레벨: {hanmi_risk['comprehensive_risk_level']}")
        print(f"  조정 계수: {hanmi_risk['risk_adjustment_factor']:.2f}")
        
        print("\n🔍 리스크 분석 결과 해석:")
        if shiftup_risk['comprehensive_risk_score'] > hanmi_risk['comprehensive_risk_score']:
            print("  - 시프트업이 더 높은 리스크를 보임")
            print("  - 게임업계의 정책 리스크와 시장 변동성이 영향")
        else:
            print("  - 한미반도체가 더 높은 리스크를 보임")
            print("  - 반도체업계의 기술 리스크와 무역 정책 리스크가 영향")
        
        print("\n✅ 리스크 분석 비교 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 비교 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 함수"""
    print("🎯 정성적 리스크 분석 시스템 테스트")
    print("=" * 50)
    
    test_results = []
    
    # 1. 개별 리스크 분석기 테스트
    print("\n1️⃣ 개별 리스크 분석기 테스트")
    result1 = test_individual_risk_analyzers()
    test_results.append(result1)
    
    # 2. 정성적 리스크 분석기 테스트
    print("\n2️⃣ 정성적 리스크 분석기 테스트")
    result2 = test_qualitative_risk_analyzer()
    test_results.append(result2)
    
    # 3. 리스크 분석 결과 비교
    print("\n3️⃣ 리스크 분석 결과 비교 테스트")
    result3 = compare_risk_analysis()
    test_results.append(result3)
    
    # 4. 향상된 통합 분석기 테스트
    print("\n4️⃣ 향상된 정성적 통합 분석기 테스트")
    result4 = test_enhanced_qualitative_analyzer()
    test_results.append(result4)
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📋 테스트 결과 요약:")
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"  통과: {passed}/{total}")
    print(f"  성공률: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과! 정성적 리스크 분석 시스템이 정상 작동합니다.")
        print("\n🚀 다음 단계:")
        print("  1. 실제 뉴스 API와 연동하여 정성적 데이터 수집")
        print("  2. 머신러닝 기반 감정 분석 모델 도입")
        print("  3. 백테스팅을 통한 성능 검증")
        print("  4. 실시간 리스크 모니터링 시스템 구축")
    else:
        print(f"\n⚠️ {total-passed}개 테스트 실패. 코드를 확인해주세요.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

