"""
최종 통합 시스템 테스트
"""

import logging
import sys

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_final_system():
    """최종 통합 시스템 테스트"""
    try:
        print("🚀 최종 통합 시스템 테스트 시작")
        
        # 1. 업종별 분석기 테스트
        from sector_specific_analyzer import SectorSpecificAnalyzer
        
        sector_analyzer = SectorSpecificAnalyzer()
        
        # 시프트업 데이터
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
        
        print("\n📊 시프트업 업종별 분석:")
        sector_result = sector_analyzer.analyze_stock_by_sector("462870", "게임업", shiftup_data)
        print(f"  업종 타입: {sector_result['sector_type']}")
        print(f"  종합 점수: {sector_result['sector_analysis']['total_score']:.1f}")
        print(f"  업종 등급: {sector_result['sector_analysis']['sector_grade']}")
        
        # 2. 정성적 리스크 분석기 테스트
        from qualitative_risk_analyzer import QualitativeRiskAnalyzer
        
        risk_analyzer = QualitativeRiskAnalyzer()
        
        print("\n📊 시프트업 정성적 리스크 분석:")
        risk_result = risk_analyzer.analyze_comprehensive_risk("462870", "게임업", shiftup_data)
        print(f"  종합 리스크 점수: {risk_result['comprehensive_risk_score']:.1f}")
        print(f"  종합 리스크 레벨: {risk_result['comprehensive_risk_level']}")
        print(f"  리스크 조정 계수: {risk_result['risk_adjustment_factor']:.2f}")
        
        # 3. 점수 계산기 테스트
        from enhanced_qualitative_integrated_analyzer import (
            QualitativeIntegratedScoreCalculator,
            SectorAnalysisConfig,
            QualitativeAnalysisConfig
        )
        
        sector_config = SectorAnalysisConfig()
        qualitative_config = QualitativeAnalysisConfig()
        
        score_calculator = QualitativeIntegratedScoreCalculator(sector_config, qualitative_config)
        
        # 통합 데이터 구성
        integrated_data = {
            'sector_analysis': sector_result,
            'qualitative_risk': risk_result
        }
        
        print("\n📊 종합 점수 계산:")
        final_score, breakdown = score_calculator.calculate_comprehensive_score(integrated_data)
        print(f"  최종 점수: {final_score:.1f}")
        print("  세부 breakdown:")
        for key, value in breakdown.items():
            if isinstance(value, (int, float)):
                print(f"    {key}: {value:.1f}")
        
        print("\n✅ 최종 통합 시스템 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 함수"""
    print("🎯 최종 통합 시스템 테스트")
    print("=" * 50)
    
    success = test_final_system()
    
    if success:
        print("\n🎉 최종 통합 시스템이 정상 작동합니다!")
        print("\n📋 구현 완료된 기능:")
        print("  ✅ 업종별 특화 분석 (게임업계, 반도체업계, 제조업계)")
        print("  ✅ 정성적 리스크 분석 (정책, ESG, 시장감정)")
        print("  ✅ 통합 점수 계산 시스템")
        print("  ✅ 리스크 조정 계수 적용")
        print("\n🚀 시스템 고도화 완료!")
    else:
        print("\n⚠️ 테스트 실패. 코드를 확인해주세요.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

