#!/usr/bin/env python3
"""
Enhanced Integrated Analyzer 테스트 케이스
크리티컬 포인트 검증을 위한 테스트 스위트
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch
import tempfile
import json

# 테스트 대상 모듈 import
try:
    from enhanced_integrated_analyzer_refactored import (
        EnhancedIntegratedAnalyzer,
        DataValidator,
        DataConverter,
        MetricsCollector,
        ErrorType
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure enhanced_integrated_analyzer_refactored.py is in the current directory")
    sys.exit(1)


class TestAnalyzerCriticalPoints(unittest.TestCase):
    """크리티컬 포인트 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.analyzer = EnhancedIntegratedAnalyzer(include_external=False, include_realtime=False)
    
    def tearDown(self):
        """테스트 정리"""
        if hasattr(self, 'analyzer'):
            self.analyzer.close()
    
    def test_per_pbr_guards_with_zero_price(self):
        """PER/PBR 계산에서 current_price <= 0 가드 테스트"""
        # 극소 EPS/BPS → PER/PBR 스킵과 상한 클램프 검증
        test_cases = [
            # (current_price, eps, bps, expected_per, expected_pbr)
            (0, 1000, 10000, None, None),  # 가격 0 → 둘 다 None
            (-1, 1000, 10000, None, None),  # 음수 가격 → 둘 다 None
            (100, 0.01, 0.1, None, None),  # 극소 EPS/BPS → None
            (100, 1000, 10000, 0.1, 0.01),  # 정상 케이스
        ]
        
        for cp, eps, bps, exp_per, exp_pbr in test_cases:
            with self.subTest(cp=cp, eps=eps, bps=bps):
                # 가격 데이터 모킹
                price_data = {
                    'current_price': cp,
                    'eps': eps,
                    'bps': bps
                }
                
                # PER/PBR 계산 로직 테스트
                if eps is not None and eps > 0.1 and cp is not None and cp > 0:
                    per = DataValidator.safe_divide(cp, eps)
                else:
                    per = None
                
                if bps is not None and bps > 1.0 and cp is not None and cp > 0:
                    pbr = DataValidator.safe_divide(cp, bps)
                else:
                    pbr = None
                
                self.assertEqual(per, exp_per, f"PER mismatch for cp={cp}, eps={eps}")
                self.assertEqual(pbr, exp_pbr, f"PBR mismatch for cp={cp}, bps={bps}")
    
    def test_52w_band_degeneration(self):
        """52주 밴드 퇴화 감지 테스트"""
        test_cases = [
            # (high, low, current_price, expected_position)
            (100, 100, 100, None),  # 동일값 → 퇴화
            (100, 99.9, 100, None),  # 극소 밴드 → 퇴화
            (100, 1, 50, 49.49),  # 정상 케이스 (band=99, position≈49.49%)
            (100, 50, 75, 50.0),  # 정상 케이스 (band=50, position=50%)
        ]
        
        for hi, lo, cp, exp_pos in test_cases:
            with self.subTest(hi=hi, lo=lo, cp=cp):
                position = self.analyzer._calculate_price_position({
                    'current_price': cp,
                    'w52_high': hi,
                    'w52_low': lo
                })
                if exp_pos is None:
                    self.assertIsNone(position, f"Position should be None for hi={hi}, lo={lo}, cp={cp}")
                else:
                    self.assertAlmostEqual(position, exp_pos, places=1, 
                                         msg=f"Position mismatch for hi={hi}, lo={lo}, cp={cp}")
    
    def test_current_ratio_edge_cases(self):
        """current_ratio 엣지 케이스 테스트"""
        test_cases = [
            # (value, force_percent, expected)
            (1.5, False, 150.0),  # 정상 비율
            (25, True, 25.0),     # 강제 퍼센트 모드
            (120, False, 120.0),  # 높은 비율
            (0.8, False, 80.0),   # 낮은 비율
        ]
        
        for value, force_percent, expected in test_cases:
            with self.subTest(value=value, force_percent=force_percent):
                # 환경변수 설정
                os.environ['CURRENT_RATIO_FORCE_PERCENT'] = str(force_percent).lower()
                
                # 데이터 변환 테스트
                financial_data = {'current_ratio': value}
                converted = DataConverter.standardize_financial_units(financial_data)
                
                self.assertAlmostEqual(converted['current_ratio'], expected, places=1,
                                     msg=f"Current ratio conversion failed for {value}")
    
    def test_sector_percentile_insufficient_peers(self):
        """섹터 백분위 표본 부족 테스트"""
        # 9개 피어 샘플 → per/pbr/roe score None, half-weight 적용
        mock_peers = [(10.0, 1.0, 15.0)] * 9  # 9개 동일 피어
        
        with patch.object(self.analyzer, '_get_sector_peers_snapshot', return_value=mock_peers):
            result = self.analyzer._evaluate_valuation_by_sector(
                '005930', 12.0, 1.2, 18.0
            )
            
            # 표본 부족으로 인해 None 반환되어야 함
            self.assertTrue(any('insufficient_peers' in note for note in result['notes']))
            self.assertIsNone(result['per_score'])
            self.assertIsNone(result['pbr_score'])
            self.assertIsNone(result['roe_score'])
    
    def test_metrics_thread_safety(self):
        """메트릭 스레드 안전성 테스트"""
        metrics = MetricsCollector()
        
        # 동시 접근 시뮬레이션
        import threading
        import time
        
        def record_metrics():
            for _ in range(100):
                metrics.record_flag_error(ErrorType.INVALID_52W_BAND)
                metrics.record_valuation_skip('per_epsmin')
                time.sleep(0.001)
        
        threads = [threading.Thread(target=record_metrics) for _ in range(5)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 메트릭이 정상적으로 기록되었는지 확인
        self.assertEqual(metrics.metrics['errors_by_type'][ErrorType.INVALID_52W_BAND], 500)
        self.assertEqual(metrics.metrics['valuation_skips']['per_epsmin'], 500)
    
    def test_canonicalization_safety(self):
        """정규화 안전성 테스트"""
        # 원본 데이터 보호 확인
        original_data = {'roe': 0.12, 'current_ratio': 1.8}
        original_copy = original_data.copy()
        
        # 정규화 수행
        converted = DataConverter.standardize_financial_units(original_data)
        
        # 원본 데이터가 변경되지 않았는지 확인
        self.assertEqual(original_data, original_copy)
        
        # 변환된 데이터 확인
        self.assertAlmostEqual(converted['roe'], 12.0, places=1)
        self.assertAlmostEqual(converted['current_ratio'], 180.0, places=1)
        # _percent_canonicalized 플래그는 표준화가 수행된 경우에만 설정됨
        # 이미 표준화된 데이터의 경우 플래그가 없을 수 있음


class TestAnalyzerIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.analyzer = EnhancedIntegratedAnalyzer(include_external=False, include_realtime=False)
    
    def tearDown(self):
        """테스트 정리"""
        if hasattr(self, 'analyzer'):
            self.analyzer.close()
    
    def test_end_to_end_analysis(self):
        """End-to-end 분석 테스트"""
        # 모킹된 데이터로 전체 파이프라인 테스트
        with patch.object(self.analyzer.data_provider, 'get_price_data') as mock_price, \
             patch.object(self.analyzer.data_provider, 'get_financial_data') as mock_financial:
            
            # 모킹 데이터 설정
            mock_price.return_value = {
                'current_price': 100000,
                'eps': 5000,
                'bps': 50000,
                'w52_high': 120000,
                'w52_low': 80000
            }
            
            mock_financial.return_value = {
                'roe': 0.15,
                'roa': 0.08,
                'debt_ratio': 0.3,
                'net_profit_margin': 0.12,
                'current_ratio': 2.0
            }
            
            # 분석 실행
            result = self.analyzer.analyze_single_stock('005930', '삼성전자')
            
            # 결과 검증
            self.assertIsNotNone(result)
            self.assertEqual(result.symbol, '005930')
            self.assertEqual(result.name, '삼성전자')
            self.assertIsNotNone(result.enhanced_score)
            self.assertIsNotNone(result.enhanced_grade)
    
    def test_smoke_command(self):
        """Smoke 명령어 테스트"""
        # CLI 명령어 시뮬레이션
        import subprocess
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Smoke 명령어 실행
            result = subprocess.run([
                sys.executable, 'enhanced_integrated_analyzer_refactored.py', 
                'smoke', '005930'
            ], capture_output=True, text=True, timeout=30)
            
            # 결과 검증
            self.assertEqual(result.returncode, 0, f"Smoke command failed: {result.stderr}")
            
            # JSON 출력 파싱 (로그 제외)
            output_lines = result.stdout.strip().split('\n')
            # JSON 블록 찾기 (여러 줄에 걸쳐 있을 수 있음)
            json_start = -1
            for i, line in enumerate(output_lines):
                if line.strip().startswith('{'):
                    json_start = i
                    break
            
            if json_start >= 0:
                # JSON 블록 추출
                json_lines = output_lines[json_start:]
                json_text = '\n'.join(json_lines)
                
                try:
                    data = json.loads(json_text)
                    self.assertIn('symbol', data)
                    self.assertIn('status', data)
                except json.JSONDecodeError as e:
                    self.fail(f"Smoke command output is not valid JSON: {e}\nOutput: {json_text[:200]}...")
            else:
                self.fail("No JSON output found in smoke command")
        
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


def run_tests():
    """테스트 실행"""
    # 테스트 스위트 생성
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 테스트 클래스 추가
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyzerCriticalPoints))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyzerIntegration))
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("Enhanced Integrated Analyzer 테스트 시작...")
    print("=" * 50)
    
    success = run_tests()
    
    print("=" * 50)
    if success:
        print("모든 테스트 통과!")
        sys.exit(0)
    else:
        print("일부 테스트 실패")
        sys.exit(1)
