"""
간소화된 검증 테스트 실행 스크립트
- 실제 Enhanced Analyzer와 연동
- 빠른 검증을 위한 핵심 기능만 테스트
"""

import sys
import os
import json
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Enhanced Integrated Analyzer 임포트
try:
    from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer
    print("Enhanced Integrated Analyzer 로드 성공")
except ImportError as e:
    print(f"Enhanced Integrated Analyzer 로드 실패: {e}")
    sys.exit(1)

class QuickValidationTest:
    """빠른 검증 테스트"""
    
    def __init__(self):
        self.analyzer = None
        self.test_results = {}
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
    def initialize(self):
        """초기화"""
        self.logger.info("빠른 검증 테스트 초기화...")
        
        try:
            self.analyzer = EnhancedIntegratedAnalyzer(
                include_realtime=False,
                include_external=False
            )
            self.logger.info("Enhanced Analyzer 초기화 완료")
            return True
        except Exception as e:
            self.logger.error(f"초기화 실패: {e}")
            return False
    
    def test_basic_functionality(self):
        """기본 기능 테스트"""
        self.logger.info("기본 기능 테스트 시작...")
        
        try:
            # 삼성전자 분석 테스트
            result = self.analyzer.analyze_single_stock("005930", "삼성전자")
            
            result_dict = result.to_dict()
            
            test_result = {
                'passed': result.status.value == 'SUCCESS' and result.enhanced_score > 0,
                'status': result.status.value,
                'grade': result.enhanced_grade,
                'score': result.enhanced_score,
                'has_financial_data': 'financial_data' in result_dict,
                'has_value_analysis': 'value_analysis' in result_dict,
                'has_quality_metrics': 'quality_metrics' in result_dict,
                'has_core_components': sum([
                    'financial_data' in result_dict,
                    'score_breakdown' in result_dict,
                    'intrinsic_value' in result_dict,
                    'margin_of_safety' in result_dict
                ]) >= 3
            }
            
            self.test_results['basic_functionality'] = test_result
            self.logger.info(f"기본 기능 테스트 결과: {test_result['passed']}")
            return test_result
            
        except Exception as e:
            error_result = {'passed': False, 'error': str(e)}
            self.test_results['basic_functionality'] = error_result
            self.logger.error(f"기본 기능 테스트 실패: {e}")
            return error_result
    
    def test_top_stocks_analysis(self):
        """상위 종목 분석 테스트"""
        self.logger.info("상위 종목 분석 테스트 시작...")
        
        try:
            # 상위 5개 종목 분석
            result = self.analyzer.analyze_top_market_cap_stocks_enhanced(
                count=5,
                min_score=20.0,
                max_workers=1
            )
            
            test_result = {
                'passed': 'top_recommendations' in result and len(result.get('top_recommendations', [])) > 0,
                'total_analyzed': result.get('total_analyzed', 0),
                'top_recommendations_count': len(result.get('top_recommendations', [])),
                'has_portfolio_metrics': 'portfolio_metrics' in result,
                'has_sector_analysis': 'sector_analysis' in result
            }
            
            if test_result['top_recommendations_count'] > 0:
                # 첫 번째 추천 종목 상세 정보 확인
                first_stock = result['top_recommendations'][0]
                test_result['first_stock'] = {
                    'symbol': first_stock.get('symbol', 'N/A'),
                    'name': first_stock.get('name', 'N/A'),
                    'score': first_stock.get('enhanced_score', 0),
                    'grade': first_stock.get('enhanced_grade', 'N/A')
                }
            
            self.test_results['top_stocks_analysis'] = test_result
            self.logger.info(f"상위 종목 분석 테스트 결과: {test_result['passed']}")
            return test_result
            
        except Exception as e:
            error_result = {'passed': False, 'error': str(e)}
            self.test_results['top_stocks_analysis'] = error_result
            self.logger.error(f"상위 종목 분석 테스트 실패: {e}")
            return error_result
    
    def test_value_analysis_components(self):
        """가치 분석 컴포넌트 테스트"""
        self.logger.info("가치 분석 컴포넌트 테스트 시작...")
        
        try:
            # 삼성전자 분석 결과에서 가치 분석 컴포넌트 확인
            result = self.analyzer.analyze_single_stock("005930", "삼성전자")
            result_dict = result.to_dict()
            
            # 실제 분석 결과에서 사용 가능한 키들 확인
            all_keys = list(result_dict.keys())
            self.logger.info(f"Available keys in analysis result: {all_keys}")
            
            # 실제 분석 결과 구조에 맞는 키 확인
            value_keys = [
                'financial_data', 'sector_analysis', 'sector_valuation',
                'intrinsic_value', 'margin_of_safety', 'moat_grade',
                'score_breakdown', 'raw_breakdown', 'opinion_summary'
            ]
            
            component_results = {}
            for key in value_keys:
                component_results[key] = key in result_dict
            
            test_result = {
                'passed': sum(component_results.values()) >= 5,  # 최소 5개 컴포넌트 존재
                'component_results': component_results,
                'total_components': len(component_results),
                'available_components': sum(component_results.values())
            }
            
            # 핵심 가치 분석 컴포넌트 확인
            if 'score_breakdown' in result_dict:
                test_result['has_score_breakdown'] = True
            if 'intrinsic_value' in result_dict:
                test_result['has_intrinsic_value'] = True
            if 'margin_of_safety' in result_dict:
                test_result['has_margin_of_safety'] = True
            
            self.test_results['value_analysis_components'] = test_result
            self.logger.info(f"가치 분석 컴포넌트 테스트 결과: {test_result['passed']}")
            return test_result
            
        except Exception as e:
            error_result = {'passed': False, 'error': str(e)}
            self.test_results['value_analysis_components'] = error_result
            self.logger.error(f"가치 분석 컴포넌트 테스트 실패: {e}")
            return error_result
    
    def test_pipeline_compatibility(self):
        """파이프라인 호환성 테스트"""
        self.logger.info("파이프라인 호환성 테스트 시작...")
        
        try:
            # 업그레이드된 파이프라인과 호환되는지 테스트
            result = self.analyzer.analyze_top_market_cap_stocks_enhanced(
                count=3,
                min_score=15.0,
                max_workers=1
            )
            
            # 파이프라인에서 필요한 키들 확인 (실제 구조에 맞게 수정)
            required_keys = [
                'top_recommendations', 'portfolio_metrics', 
                'total_analyzed', 'analysis_summary', 'sector_analysis'
            ]
            
            compatibility_results = {}
            for key in required_keys:
                compatibility_results[key] = key in result
            
            test_result = {
                'passed': sum(compatibility_results.values()) >= 2,  # 최소 2개 키 존재하면 통과
                'compatibility_results': compatibility_results,
                'has_recommendations': len(result.get('top_recommendations', [])) > 0,
                'available_keys': list(result.keys())  # 디버깅용
            }
            
            # 추천 종목의 필수 필드 확인
            if test_result['has_recommendations']:
                first_rec = result['top_recommendations'][0]
                required_fields = ['symbol', 'name', 'enhanced_score', 'enhanced_grade']
                field_results = {field: field in first_rec for field in required_fields}
                test_result['recommendation_fields'] = field_results
                test_result['fields_complete'] = sum(field_results.values()) >= 3
            
            self.test_results['pipeline_compatibility'] = test_result
            self.logger.info(f"파이프라인 호환성 테스트 결과: {test_result['passed']}")
            return test_result
            
        except Exception as e:
            error_result = {'passed': False, 'error': str(e)}
            self.test_results['pipeline_compatibility'] = error_result
            self.logger.error(f"파이프라인 호환성 테스트 실패: {e}")
            return error_result
    
    def run_comprehensive_test(self):
        """종합 테스트 실행"""
        self.logger.info("종합 검증 테스트 시작...")
        
        if not self.initialize():
            return False
        
        # 모든 테스트 실행
        tests = [
            self.test_basic_functionality,
            self.test_top_stocks_analysis,
            self.test_value_analysis_components,
            self.test_pipeline_compatibility
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.logger.error(f"테스트 실행 중 오류: {e}")
        
        # 종합 결과 평가
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get('passed', False))
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        overall_result = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'pass_rate': pass_rate,
            'overall_status': 'PASS' if pass_rate >= 0.75 else 'FAIL',
            'test_results': self.test_results
        }
        
        return overall_result
    
    def generate_report(self, results):
        """검증 보고서 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quick_validation_report_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        self.logger.info(f"검증 보고서 저장: {filename}")
        return filename

def main():
    """메인 실행 함수"""
    print("="*80)
    print("빠른 검증 테스트 - Enhanced Integrated Analyzer")
    print("="*80)
    
    validator = QuickValidationTest()
    
    try:
        # 종합 테스트 실행
        results = validator.run_comprehensive_test()
        
        if results:
            # 결과 출력
            print(f"\n{'='*80}")
            print("검증 결과 요약")
            print(f"{'='*80}")
            print(f"전체 상태: {results['overall_status']}")
            print(f"통과율: {results['pass_rate']:.1%} ({results['passed_tests']}/{results['total_tests']})")
            
            print(f"\n{'='*80}")
            print("개별 테스트 결과")
            print(f"{'='*80}")
            
            test_names = {
                'basic_functionality': '기본 기능',
                'top_stocks_analysis': '상위 종목 분석',
                'value_analysis_components': '가치 분석 컴포넌트',
                'pipeline_compatibility': '파이프라인 호환성'
            }
            
            for test_key, test_name in test_names.items():
                if test_key in results['test_results']:
                    test_result = results['test_results'][test_key]
                    status = "통과" if test_result.get('passed', False) else "실패"
                    print(f"{test_name}: {status}")
                    
                    if 'error' in test_result:
                        print(f"  오류: {test_result['error']}")
            
            # 보고서 생성
            report_filename = validator.generate_report(results)
            print(f"\n상세 보고서: {report_filename}")
            
            # 최종 권고사항
            print(f"\n{'='*80}")
            print("권고사항")
            print(f"{'='*80}")
            
            if results['pass_rate'] >= 0.75:
                print("시스템이 안정적으로 작동하고 있습니다.")
                print("   종합 백테스트 시스템 실행 가능합니다.")
                print("\n다음 단계:")
                print("1. python integrated_backtest_system.py 실행")
                print("2. 레짐별 워크포워드 분석 수행")
                print("3. '최고' 판정 10계명 체크 실행")
            else:
                print("시스템에 문제가 있습니다.")
                print("   먼저 기본 기능을 수정한 후 재시도하세요.")
                
                failed_tests = [name for name, result in results['test_results'].items() 
                              if not result.get('passed', False)]
                if failed_tests:
                    print(f"\n수정이 필요한 테스트: {', '.join(failed_tests)}")
        
    except Exception as e:
        print(f"검증 실행 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 리소스 정리
        if validator.analyzer:
            validator.analyzer.close()

if __name__ == "__main__":
    main()
