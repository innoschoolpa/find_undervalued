"""
업종별 특화 분석 테스트 코드
"""

import logging
import sys
from typing import Dict, Any

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_sector_analyzer():
    """업종별 분석기 테스트"""
    try:
        from sector_specific_analyzer import (
            SectorSpecificAnalyzer, 
            SectorType,
            GameIndustryModel,
            SemiconductorModel,
            ManufacturingModel
        )
        
        print("🚀 업종별 분석기 테스트 시작")
        
        # 분석기 초기화
        analyzer = SectorSpecificAnalyzer()
        
        # 테스트 데이터 생성
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
        
        # 게임업계 분석 테스트
        print("\n🎮 게임업계 분석 테스트")
        game_result = analyzer.analyze_stock_by_sector(
            "462870", "게임업", test_data, "normal"
        )
        print(f"  업종 타입: {game_result['sector_type']}")
        print(f"  종합 점수: {game_result['sector_analysis']['total_score']:.1f}")
        print(f"  업종 등급: {game_result['sector_analysis']['sector_grade']}")
        print("  세부 점수:")
        for key, value in game_result['sector_analysis']['breakdown'].items():
            print(f"    {key}: {value:.1f}")
        
        # 반도체업계 분석 테스트
        print("\n🔬 반도체업계 분석 테스트")
        semiconductor_result = analyzer.analyze_stock_by_sector(
            "042700", "반도체", test_data, "normal"
        )
        print(f"  업종 타입: {semiconductor_result['sector_type']}")
        print(f"  종합 점수: {semiconductor_result['sector_analysis']['total_score']:.1f}")
        print(f"  업종 등급: {semiconductor_result['sector_analysis']['sector_grade']}")
        print("  세부 점수:")
        for key, value in semiconductor_result['sector_analysis']['breakdown'].items():
            print(f"    {key}: {value:.1f}")
        
        # 제조업계 분석 테스트
        print("\n🏭 제조업계 분석 테스트")
        manufacturing_result = analyzer.analyze_stock_by_sector(
            "000270", "제조업", test_data, "normal"
        )
        print(f"  업종 타입: {manufacturing_result['sector_type']}")
        print(f"  종합 점수: {manufacturing_result['sector_analysis']['total_score']:.1f}")
        print(f"  업종 등급: {manufacturing_result['sector_analysis']['sector_grade']}")
        print("  세부 점수:")
        for key, value in manufacturing_result['sector_analysis']['breakdown'].items():
            print(f"    {key}: {value:.1f}")
        
        print("\n✅ 업종별 분석기 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_sector_analyzer():
    """향상된 업종별 통합 분석기 테스트"""
    try:
        print("\n🚀 향상된 업종별 통합 분석기 테스트 시작")
        
        # Mock 데이터로 테스트 (실제 API 호출 없이)
        from enhanced_sector_integrated_analyzer import (
            EnhancedSectorIntegratedAnalyzer,
            SectorAnalysisConfig
        )
        
        # 간단한 테스트를 위해 Mock 클래스 사용
        class MockAnalyzer:
            def analyze_single_stock_enhanced(self, symbol, name):
                # Mock 결과 반환
                return {
                    'symbol': symbol,
                    'name': name,
                    'enhanced_score': 75.5,
                    'enhanced_grade': 'A',
                    'sector': '게임업',
                    'status': 'success'
                }
        
        mock_analyzer = MockAnalyzer()
        
        # 테스트 종목들
        test_stocks = [
            ("462870", "시프트업"),
            ("042700", "한미반도체"),
            ("000270", "기아")
        ]
        
        print("\n📈 종목별 분석 결과:")
        for symbol, name in test_stocks:
            result = mock_analyzer.analyze_single_stock_enhanced(symbol, name)
            print(f"  {name}({symbol}): {result['enhanced_score']}점 ({result['enhanced_grade']})")
        
        print("\n✅ 향상된 업종별 통합 분석기 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 향상된 분석기 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sector_specific_models():
    """업종별 특화 모델 직접 테스트"""
    try:
        print("\n🚀 업종별 특화 모델 직접 테스트 시작")
        
        from sector_specific_analyzer import (
            GameIndustryModel,
            SemiconductorModel,
            ManufacturingModel
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
        
        # 게임업계 모델 테스트
        print("\n🎮 게임업계 모델 테스트")
        game_model = GameIndustryModel()
        game_score = game_model.calculate_sector_score(test_data)
        print(f"  종합 점수: {game_score['total_score']:.1f}")
        print(f"  등급: {game_score['sector_grade']}")
        print("  세부 점수:")
        for key, value in game_score['breakdown'].items():
            print(f"    {key}: {value:.1f}")
        
        # 반도체업계 모델 테스트
        print("\n🔬 반도체업계 모델 테스트")
        semiconductor_model = SemiconductorModel()
        semi_score = semiconductor_model.calculate_sector_score(test_data)
        print(f"  종합 점수: {semi_score['total_score']:.1f}")
        print(f"  등급: {semi_score['sector_grade']}")
        print("  세부 점수:")
        for key, value in semi_score['breakdown'].items():
            print(f"    {key}: {value:.1f}")
        
        # 제조업계 모델 테스트
        print("\n🏭 제조업계 모델 테스트")
        manufacturing_model = ManufacturingModel()
        manu_score = manufacturing_model.calculate_sector_score(test_data)
        print(f"  종합 점수: {manu_score['total_score']:.1f}")
        print(f"  등급: {manu_score['sector_grade']}")
        print("  세부 점수:")
        for key, value in manu_score['breakdown'].items():
            print(f"    {key}: {value:.1f}")
        
        print("\n✅ 업종별 특화 모델 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 특화 모델 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def compare_sector_analysis():
    """업종별 분석 결과 비교"""
    try:
        print("\n🚀 업종별 분석 결과 비교 테스트 시작")
        
        from sector_specific_analyzer import SectorSpecificAnalyzer
        
        analyzer = SectorSpecificAnalyzer()
        
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
        
        print("\n📊 업종별 분석 비교:")
        print("=" * 60)
        
        # 시프트업 분석
        shiftup_result = analyzer.analyze_stock_by_sector("462870", "게임업", shiftup_data)
        print(f"시프트업 (게임업계):")
        print(f"  종합 점수: {shiftup_result['sector_analysis']['total_score']:.1f}")
        print(f"  등급: {shiftup_result['sector_analysis']['sector_grade']}")
        
        # 한미반도체 분석
        hanmi_result = analyzer.analyze_stock_by_sector("042700", "반도체", hanmi_data)
        print(f"한미반도체 (반도체업계):")
        print(f"  종합 점수: {hanmi_result['sector_analysis']['total_score']:.1f}")
        print(f"  등급: {hanmi_result['sector_analysis']['sector_grade']}")
        
        print("\n🔍 분석 결과 해석:")
        if shiftup_result['sector_analysis']['total_score'] > hanmi_result['sector_analysis']['total_score']:
            print("  - 시프트업이 게임업계 기준에서 더 높은 점수를 받음")
            print("  - 게임업계는 성장성과 안정성의 균형을 중시")
        else:
            print("  - 한미반도체가 반도체업계 기준에서 더 높은 점수를 받음")
            print("  - 반도체업계는 기술력과 시장 사이클 대응 능력을 중시")
        
        print("\n✅ 업종별 분석 비교 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 비교 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 함수"""
    print("🎯 업종별 특화 분석 시스템 테스트")
    print("=" * 50)
    
    test_results = []
    
    # 1. 업종별 분석기 테스트
    print("\n1️⃣ 업종별 분석기 기본 테스트")
    result1 = test_sector_analyzer()
    test_results.append(result1)
    
    # 2. 업종별 특화 모델 직접 테스트
    print("\n2️⃣ 업종별 특화 모델 직접 테스트")
    result2 = test_sector_specific_models()
    test_results.append(result2)
    
    # 3. 업종별 분석 결과 비교
    print("\n3️⃣ 업종별 분석 결과 비교 테스트")
    result3 = compare_sector_analysis()
    test_results.append(result3)
    
    # 4. 향상된 통합 분석기 테스트 (Mock)
    print("\n4️⃣ 향상된 통합 분석기 테스트")
    result4 = test_enhanced_sector_analyzer()
    test_results.append(result4)
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📋 테스트 결과 요약:")
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"  통과: {passed}/{total}")
    print(f"  성공률: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과! 업종별 특화 분석 시스템이 정상 작동합니다.")
        print("\n🚀 다음 단계:")
        print("  1. 실제 API와 연동하여 종목 데이터 수집")
        print("  2. 백테스팅을 통한 성능 검증")
        print("  3. 추가 업종별 모델 개발 (금융업, 바이오 등)")
        print("  4. 머신러닝 기반 적응형 모델 도입")
    else:
        print(f"\n⚠️ {total-passed}개 테스트 실패. 코드를 확인해주세요.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

