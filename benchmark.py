#!/usr/bin/env python3
"""
리팩토링된 분석 시스템 성능 벤치마크

모듈별 성능을 측정하고 비교합니다.
"""

import time
import psutil
import json
import statistics
from datetime import datetime
from typing import Dict, List, Any
import argparse

# 모듈 import
try:
    from config_manager import ConfigManager
    from metrics import MetricsCollector
    from value_style_classifier import ValueStyleClassifier
    from uvs_eligibility_filter import UVSEligibilityFilter
    from financial_data_provider import FinancialDataProvider
    from enhanced_score_calculator import EnhancedScoreCalculator
    from analysis_models import AnalysisConfig, AnalysisResult, AnalysisStatus
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    print("💡 해결: 필요한 모듈들이 설치되어 있는지 확인하세요.")
    exit(1)


class PerformanceBenchmark:
    """성능 벤치마크 클래스"""
    
    def __init__(self):
        self.results = {}
        self.memory_usage = []
        self.cpu_usage = []
        
    def measure_memory_cpu(self):
        """메모리 및 CPU 사용량 측정"""
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        
        self.memory_usage.append(memory_info.rss / 1024 / 1024)  # MB
        self.cpu_usage.append(cpu_percent)
        
        return memory_info.rss / 1024 / 1024, cpu_percent
    
    def benchmark_config_manager(self, iterations: int = 1000) -> Dict[str, Any]:
        """ConfigManager 성능 벤치마크"""
        print("[TEST] ConfigManager 성능 측정 중...")
        
        times = []
        memory_usage = []
        
        for i in range(iterations):
            start_time = time.time()
            start_memory, _ = self.measure_memory_cpu()
            
            # ConfigManager 초기화
            config = ConfigManager()
            
            # 설정값 조회/설정
            config.set('test_key', f'test_value_{i}')
            value = config.get('test_key')
            
            end_time = time.time()
            end_memory, _ = self.measure_memory_cpu()
            
            times.append(end_time - start_time)
            memory_usage.append(end_memory - start_memory)
        
        return {
            'module': 'ConfigManager',
            'iterations': iterations,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_time': statistics.stdev(times) if len(times) > 1 else 0,
            'avg_memory': statistics.mean(memory_usage),
            'max_memory': max(memory_usage)
        }
    
    def benchmark_metrics_collector(self, iterations: int = 1000) -> Dict[str, Any]:
        """MetricsCollector 성능 벤치마크"""
        print("[TEST] MetricsCollector 성능 측정 중...")
        
        times = []
        memory_usage = []
        
        for i in range(iterations):
            start_time = time.time()
            start_memory, _ = self.measure_memory_cpu()
            
            # MetricsCollector 초기화
            metrics = MetricsCollector()
            
            # 메트릭 기록
            for _ in range(i):
                metrics.record_api_call(success=True)
            for _ in range(i % 10):
                metrics.record_api_call(success=False)
            metrics.record_analysis_duration(i * 0.001)
            
            # 통계 조회
            stats = metrics.get_summary()
            
            end_time = time.time()
            end_memory, _ = self.measure_memory_cpu()
            
            times.append(end_time - start_time)
            memory_usage.append(end_memory - start_memory)
        
        return {
            'module': 'MetricsCollector',
            'iterations': iterations,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_time': statistics.stdev(times) if len(times) > 1 else 0,
            'avg_memory': statistics.mean(memory_usage),
            'max_memory': max(memory_usage)
        }
    
    def benchmark_value_style_classifier(self, iterations: int = 1000) -> Dict[str, Any]:
        """ValueStyleClassifier 성능 벤치마크"""
        print("[TEST] ValueStyleClassifier 성능 측정 중...")
        
        times = []
        memory_usage = []
        
        # 테스트용 메트릭 데이터
        test_metrics = {
            'valuation_pct': 20,
            'mos': 0.25,
            'price_pos': 0.3,
            'ev_ebit': 8,
            'interest_cov': 6.0,
            'accruals_risk': 0.1,
            'earnings_vol_sigma': 0.18,
            'sector_sigma_median': 0.25,
            'roic_z': 1.2,
            'f_score': 7,
            'eps_cagr': 0.15,
            'rev_cagr': 0.10
        }
        
        for i in range(iterations):
            start_time = time.time()
            start_memory, _ = self.measure_memory_cpu()
            
            # ValueStyleClassifier 초기화
            classifier = ValueStyleClassifier()
            
            # 스타일 분류
            result = classifier.classify_value_style(test_metrics)
            score = classifier.calculate_style_score(test_metrics)
            
            end_time = time.time()
            end_memory, _ = self.measure_memory_cpu()
            
            times.append(end_time - start_time)
            memory_usage.append(end_memory - start_memory)
        
        return {
            'module': 'ValueStyleClassifier',
            'iterations': iterations,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_time': statistics.stdev(times) if len(times) > 1 else 0,
            'avg_memory': statistics.mean(memory_usage),
            'max_memory': max(memory_usage)
        }
    
    def benchmark_uvs_eligibility_filter(self, iterations: int = 1000) -> Dict[str, Any]:
        """UVSEligibilityFilter 성능 벤치마크"""
        print("[TEST] UVSEligibilityFilter 성능 측정 중...")
        
        times = []
        memory_usage = []
        
        # 테스트용 메트릭 데이터
        test_metrics = {
            'value_style_score': 85.0,
            'valuation_percentile': 25.0,
            'margin_of_safety': 0.20,
            'quality_score': 75.0,
            'risk_score': 0.25,
            'confidence_score': 0.8
        }
        
        for i in range(iterations):
            start_time = time.time()
            start_memory, _ = self.measure_memory_cpu()
            
            # UVSEligibilityFilter 초기화
            filter = UVSEligibilityFilter()
            
            # 자격 검증
            result = filter.check_uvs_eligibility(test_metrics)
            grade = filter.get_uvs_grade(result['uvs_score'])
            
            end_time = time.time()
            end_memory, _ = self.measure_memory_cpu()
            
            times.append(end_time - start_time)
            memory_usage.append(end_memory - start_memory)
        
        return {
            'module': 'UVSEligibilityFilter',
            'iterations': iterations,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_time': statistics.stdev(times) if len(times) > 1 else 0,
            'avg_memory': statistics.mean(memory_usage),
            'max_memory': max(memory_usage)
        }
    
    def benchmark_enhanced_score_calculator(self, iterations: int = 1000) -> Dict[str, Any]:
        """EnhancedScoreCalculator 성능 벤치마크"""
        print("[TEST] EnhancedScoreCalculator 성능 측정 중...")
        
        times = []
        memory_usage = []
        
        # 테스트용 데이터
        test_data = {
            'pe_ratio': 15.0,
            'pb_ratio': 1.5,
            'roe': 15.0,
            'roa': 8.0,
            'debt_ratio': 30.0,
            'current_ratio': 2.0,
            'eps_growth': 0.12,
            'revenue_growth': 0.08,
            'beta': 1.2,
            'volatility': 0.25
        }
        
        # 분석 구성 설정
        config = AnalysisConfig.get_default_config()
        
        for i in range(iterations):
            start_time = time.time()
            start_memory, _ = self.measure_memory_cpu()
            
            # EnhancedScoreCalculator 초기화
            calculator = EnhancedScoreCalculator(config)
            
            # 점수 계산
            score = calculator.calculate_score(test_data)
            breakdown = calculator.get_score_breakdown(test_data)
            
            end_time = time.time()
            end_memory, _ = self.measure_memory_cpu()
            
            times.append(end_time - start_time)
            memory_usage.append(end_memory - start_memory)
        
        return {
            'module': 'EnhancedScoreCalculator',
            'iterations': iterations,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_time': statistics.stdev(times) if len(times) > 1 else 0,
            'avg_memory': statistics.mean(memory_usage),
            'max_memory': max(memory_usage)
        }
    
    def benchmark_analysis_models(self, iterations: int = 1000) -> Dict[str, Any]:
        """AnalysisModels 성능 벤치마크"""
        print("[TEST] AnalysisModels 성능 측정 중...")
        
        times = []
        memory_usage = []
        
        for i in range(iterations):
            start_time = time.time()
            start_memory, _ = self.measure_memory_cpu()
            
            # AnalysisResult 생성
            result = AnalysisResult(
                symbol=f'TEST{i:03d}',
                analysis_id=f'analysis_{i}',
                status=AnalysisStatus.COMPLETED,
                timestamp=datetime.now().isoformat(),
                financial_data={'revenue': 1000000000, 'net_income': 100000000},
                price_data={'current_price': 1500, 'market_cap': 15000000000},
                sector_data={'sector': 'Technology', 'industry': 'Software'},
                metrics={'pe_ratio': 15.0, 'pb_ratio': 1.5},
                scores={'total_score': 75.0, 'value_score': 80.0},
                recommendation='BUY',
                confidence_score=0.8,
                risk_level='LOW',
                analysis_duration=5.0,
                data_quality_score=85.0,
                error_messages=[]
            )
            
            # 메서드 호출
            is_successful = result.is_successful()
            has_errors = result.has_errors()
            summary = result.get_summary()
            result_dict = result.to_dict()
            
            end_time = time.time()
            end_memory, _ = self.measure_memory_cpu()
            
            times.append(end_time - start_time)
            memory_usage.append(end_memory - start_memory)
        
        return {
            'module': 'AnalysisModels',
            'iterations': iterations,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_time': statistics.stdev(times) if len(times) > 1 else 0,
            'avg_memory': statistics.mean(memory_usage),
            'max_memory': max(memory_usage)
        }
    
    def run_all_benchmarks(self, iterations: int = 1000) -> Dict[str, Any]:
        """모든 벤치마크 실행"""
        print(f"[BENCHMARK] 성능 벤치마크 시작 (반복 횟수: {iterations})")
        print("="*60)
        
        benchmarks = [
            self.benchmark_config_manager,
            self.benchmark_metrics_collector,
            self.benchmark_value_style_classifier,
            self.benchmark_uvs_eligibility_filter,
            self.benchmark_enhanced_score_calculator,
            self.benchmark_analysis_models
        ]
        
        results = []
        
        for benchmark_func in benchmarks:
            try:
                result = benchmark_func(iterations)
                results.append(result)
                print(f"[PASS] {result['module']} 완료")
            except Exception as e:
                print(f"[FAIL] {benchmark_func.__name__} 실패: {e}")
        
        # 전체 시스템 메모리/CPU 사용량
        process = psutil.Process()
        system_memory = process.memory_info().rss / 1024 / 1024  # MB
        system_cpu = process.cpu_percent()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'iterations': iterations,
            'system_memory_mb': system_memory,
            'system_cpu_percent': system_cpu,
            'benchmarks': results
        }
    
    def generate_report(self, results: Dict[str, Any], output_file: str = "benchmark_report.json"):
        """벤치마크 리포트 생성"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"[REPORT] 벤치마크 리포트 생성: {output_file}")
    
    def print_summary(self, results: Dict[str, Any]):
        """벤치마크 결과 요약 출력"""
        print("\n" + "="*60)
        print("[SUMMARY] 성능 벤치마크 결과 요약")
        print("="*60)
        
        print(f"[TIME] 실행 시간: {results['timestamp']}")
        print(f"[ITER] 반복 횟수: {results['iterations']}")
        print(f"[MEM] 시스템 메모리: {results['system_memory_mb']:.1f} MB")
        print(f"[CPU] 시스템 CPU: {results['system_cpu_percent']:.1f}%")
        
        print("\n[PERF] 모듈별 성능:")
        print("-" * 60)
        print(f"{'모듈':<25} {'평균 시간(ms)':<15} {'최대 메모리(MB)':<15}")
        print("-" * 60)
        
        for benchmark in results['benchmarks']:
            avg_time_ms = benchmark['avg_time'] * 1000
            max_memory_mb = benchmark['max_memory']
            print(f"{benchmark['module']:<25} {avg_time_ms:<15.2f} {max_memory_mb:<15.2f}")
        
        print("-" * 60)
        
        # 가장 빠른/느린 모듈 찾기
        if results['benchmarks']:
            fastest = min(results['benchmarks'], key=lambda x: x['avg_time'])
            slowest = max(results['benchmarks'], key=lambda x: x['avg_time'])
            
            print(f"\n🏃 가장 빠른 모듈: {fastest['module']} ({fastest['avg_time']*1000:.2f}ms)")
            print(f"🐌 가장 느린 모듈: {slowest['module']} ({slowest['avg_time']*1000:.2f}ms)")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="리팩토링된 분석 시스템 성능 벤치마크")
    parser.add_argument("--iterations", "-i", type=int, default=1000, help="반복 횟수")
    parser.add_argument("--output", "-o", default="benchmark_report.json", help="출력 파일")
    parser.add_argument("--summary", "-s", action="store_true", help="요약만 출력")
    
    args = parser.parse_args()
    
    try:
        benchmark = PerformanceBenchmark()
        results = benchmark.run_all_benchmarks(args.iterations)
        
        # 리포트 생성
        benchmark.generate_report(results, args.output)
        
        # 요약 출력
        if args.summary:
            benchmark.print_summary(results)
        else:
            benchmark.print_summary(results)
            print(f"\n[REPORT] 상세 결과는 {args.output} 파일을 확인하세요.")
    
    except KeyboardInterrupt:
        print("\n[STOP] 벤치마크가 중단되었습니다.")
    except Exception as e:
        print(f"\n[ERROR] 벤치마크 실행 중 오류 발생: {e}")


if __name__ == "__main__":
    main()
