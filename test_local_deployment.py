#!/usr/bin/env python3
"""
로컬 배포 테스트 스크립트
Docker 없이도 애플리케이션의 핵심 기능을 테스트할 수 있습니다.
"""

import sys
import time
import requests
import subprocess
from pathlib import Path

def test_imports():
    """모든 모듈 import 테스트"""
    print("🔍 모듈 import 테스트 중...")
    
    try:
        # 핵심 모듈들 import 테스트
        import enhanced_integrated_analyzer_refactored
        print("✅ enhanced_integrated_analyzer_refactored import 성공")
        
        import value_style_classifier
        print("✅ value_style_classifier import 성공")
        
        import uvs_eligibility_filter
        print("✅ uvs_eligibility_filter import 성공")
        
        import config_manager
        print("✅ config_manager import 성공")
        
        import metrics
        print("✅ metrics import 성공")
        
        return True
    except ImportError as e:
        print(f"❌ Import 실패: {e}")
        return False

def test_config_manager():
    """ConfigManager 기능 테스트"""
    print("\n🔧 ConfigManager 테스트 중...")
    
    try:
        from config_manager import ConfigManager
        
        config = ConfigManager()
        
        # 기본 설정 로딩 테스트
        timeout = config.get('api_timeout')
        print(f"✅ API 타임아웃 설정: {timeout}")
        
        # 설정 변경 테스트
        config.set('api_timeout', 120)
        new_timeout = config.get('api_timeout')
        print(f"✅ 설정 변경 테스트: {new_timeout}")
        
        # 검증 테스트
        is_valid = config.is_valid()
        print(f"✅ 설정 검증: {is_valid}")
        
        return True
    except Exception as e:
        print(f"❌ ConfigManager 테스트 실패: {e}")
        return False

def test_metrics_collector():
    """MetricsCollector 기능 테스트"""
    print("\n📊 MetricsCollector 테스트 중...")
    
    try:
        from metrics import MetricsCollector
        
        metrics = MetricsCollector()
        
        # API 호출 기록 테스트
        metrics.record_api_call(success=True)
        metrics.record_api_call(success=False)
        print("✅ API 호출 기록 테스트 완료")
        
        # 분석 시간 기록 테스트
        metrics.record_analysis_duration(1.5)
        print("✅ 분석 시간 기록 테스트 완료")
        
        # 통계 조회 테스트
        stats = metrics.get_summary()
        print(f"✅ 통계 조회: {len(stats)} 항목")
        
        return True
    except Exception as e:
        print(f"❌ MetricsCollector 테스트 실패: {e}")
        return False

def test_value_style_classifier():
    """ValueStyleClassifier 기능 테스트"""
    print("\n🎯 ValueStyleClassifier 테스트 중...")
    
    try:
        from value_style_classifier import ValueStyleClassifier
        
        classifier = ValueStyleClassifier()
        
        # 테스트 메트릭
        test_metrics = {
            'valuation_pct': 15,
            'mos': 0.35,
            'price_pos': 0.3,
            'ev_ebit': 6,
            'interest_cov': 8.0,
            'accruals_risk': 0.05,
            'earnings_vol_sigma': 0.15,
            'sector_sigma_median': 0.25,
            'roic_z': 1.5,
            'f_score': 8,
            'eps_cagr': 0.12,
            'rev_cagr': 0.08
        }
        
        # 스타일 분류 테스트
        result = classifier.classify_value_style(test_metrics)
        print(f"✅ 스타일 분류: {result['style_label']}")
        print(f"✅ 신뢰도: {result['confidence_score']:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ ValueStyleClassifier 테스트 실패: {e}")
        return False

def test_uvs_eligibility_filter():
    """UVSEligibilityFilter 기능 테스트"""
    print("\n🔍 UVSEligibilityFilter 테스트 중...")
    
    try:
        from uvs_eligibility_filter import UVSEligibilityFilter
        
        filter_obj = UVSEligibilityFilter()
        
        # 테스트 메트릭
        test_metrics = {
            'value_style_score': 85.0,
            'valuation_percentile': 25.0,
            'margin_of_safety': 0.20,
            'quality_score': 75.0,
            'risk_score': 0.25,
            'confidence_score': 0.8
        }
        
        # UVS 자격 검증 테스트
        result = filter_obj.check_uvs_eligibility(test_metrics)
        print(f"✅ UVS 자격: {result['is_eligible']}")
        print(f"✅ UVS 점수: {result['uvs_score']:.1f}")
        
        return True
    except Exception as e:
        print(f"❌ UVSEligibilityFilter 테스트 실패: {e}")
        return False

def test_analyzer_initialization():
    """EnhancedIntegratedAnalyzer 초기화 테스트"""
    print("\n🚀 EnhancedIntegratedAnalyzer 초기화 테스트 중...")
    
    try:
        from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer
        
        # 분석기 초기화
        analyzer = EnhancedIntegratedAnalyzer()
        print("✅ 분석기 초기화 성공")
        
        # 기본 설정 확인
        config = analyzer.config_manager
        print(f"✅ 설정 관리자: {type(config).__name__}")
        
        # 메트릭 수집기 확인
        metrics = analyzer.metrics_collector
        print(f"✅ 메트릭 수집기: {type(metrics).__name__}")
        
        return True
    except Exception as e:
        print(f"❌ EnhancedIntegratedAnalyzer 초기화 실패: {e}")
        return False

def test_cli_functionality():
    """CLI 기능 테스트"""
    print("\n💻 CLI 기능 테스트 중...")
    
    try:
        # CLI 도움말 테스트
        result = subprocess.run([
            sys.executable, 
            "enhanced_integrated_analyzer_refactored.py", 
            "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ CLI 도움말 출력 성공")
            return True
        else:
            print(f"❌ CLI 도움말 출력 실패: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ CLI 테스트 시간 초과")
        return False
    except Exception as e:
        print(f"❌ CLI 테스트 실패: {e}")
        return False

def test_file_structure():
    """파일 구조 테스트"""
    print("\n📁 파일 구조 테스트 중...")
    
    required_files = [
        "enhanced_integrated_analyzer_refactored.py",
        "value_style_classifier.py",
        "uvs_eligibility_filter.py",
        "config_manager.py",
        "metrics.py",
        "requirements.txt",
        "deploy/docker/Dockerfile",
        "deploy/docker/docker-compose.yml",
        "deploy/kubernetes/analyzer-deployment.yaml",
        "deploy/monitoring/prometheus-config.yaml",
        ".github/workflows/ci-cd.yml"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if not missing_files:
        print("✅ 모든 필수 파일 존재")
        return True
    else:
        print(f"❌ 누락된 파일들: {missing_files}")
        return False

def run_performance_test():
    """성능 테스트"""
    print("\n⚡ 성능 테스트 중...")
    
    try:
        from benchmark import BenchmarkSuite
        
        benchmark = BenchmarkSuite()
        
        # 간단한 성능 테스트 (100회 반복)
        print("ConfigManager 성능 측정...")
        config_result = benchmark.benchmark_config_manager(100)
        print(f"✅ ConfigManager 평균 시간: {config_result['avg_time']*1000:.2f}ms")
        
        print("MetricsCollector 성능 측정...")
        metrics_result = benchmark.benchmark_metrics_collector(100)
        print(f"✅ MetricsCollector 평균 시간: {metrics_result['avg_time']*1000:.2f}ms")
        
        print("ValueStyleClassifier 성능 측정...")
        classifier_result = benchmark.benchmark_value_style_classifier(100)
        print(f"✅ ValueStyleClassifier 평균 시간: {classifier_result['avg_time']*1000:.2f}ms")
        
        return True
    except Exception as e:
        print(f"❌ 성능 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🧪 Enhanced Analyzer 로컬 배포 테스트 시작")
    print("=" * 60)
    
    start_time = time.time()
    
    tests = [
        ("모듈 Import", test_imports),
        ("파일 구조", test_file_structure),
        ("ConfigManager", test_config_manager),
        ("MetricsCollector", test_metrics_collector),
        ("ValueStyleClassifier", test_value_style_classifier),
        ("UVSEligibilityFilter", test_uvs_eligibility_filter),
        ("분석기 초기화", test_analyzer_initialization),
        ("CLI 기능", test_cli_functionality),
        ("성능 테스트", run_performance_test),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 예외 발생: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📋 테스트 결과 요약")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.1f}%)")
    
    elapsed_time = time.time() - start_time
    print(f"실행 시간: {elapsed_time:.2f}초")
    
    if passed == total:
        print("\n🎉 모든 테스트가 통과했습니다!")
        print("✅ 애플리케이션이 정상적으로 작동합니다.")
        print("✅ Docker 없이도 로컬에서 실행 가능합니다.")
        return True
    else:
        print(f"\n⚠️ {total - passed}개 테스트가 실패했습니다.")
        print("❌ 일부 기능에 문제가 있을 수 있습니다.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)












