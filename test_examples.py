#!/usr/bin/env python3
"""
Test Examples for Enhanced Integrated Analyzer
=============================================

This file contains example test cases and usage patterns for testing
the Enhanced Integrated Analyzer. These examples can be used as
templates for creating additional tests.

Usage:
    python test_examples.py
"""

import os
import sys
import time
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import enhanced_integrated_analyzer_refactored as eia
    from enhanced_integrated_analyzer_refactored import (
        EnhancedIntegratedAnalyzer,
        DataValidator,
        AnalysisResult,
        AnalysisStatus
    )
except ImportError as e:
    print(f"❌ Failed to import analyzer: {e}")
    sys.exit(1)


class TestExamples(unittest.TestCase):
    """Example test cases for the analyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = EnhancedIntegratedAnalyzer()
        
    def test_example_single_stock_analysis(self):
        """Example: Test single stock analysis"""
        # Arrange
        symbol = "005930"
        name = "Samsung"
        
        # Act
        result = self.analyzer.analyze_single_stock(symbol, name)
        
        # Assert
        self.assertIsInstance(result, AnalysisResult)
        self.assertEqual(result.symbol, symbol)
        self.assertEqual(result.name, name)
        self.assertIn(result.status, [AnalysisStatus.SUCCESS, AnalysisStatus.PARTIAL_SUCCESS, AnalysisStatus.FAILED])
        
        if result.status == AnalysisStatus.SUCCESS:
            self.assertGreater(result.enhanced_score, 0.0)
            self.assertIsNotNone(result.enhanced_grade)
            
    def test_example_data_validation(self):
        """Example: Test data validation"""
        validator = DataValidator()
        
        # Test valid data
        self.assertEqual(validator.safe_float("123.45"), 123.45)
        self.assertEqual(validator.safe_float("0"), 0.0)
        self.assertEqual(validator.safe_float("-50.5"), -50.5)
        
        # Test invalid data
        self.assertEqual(validator.safe_float("invalid", 99.0), 99.0)
        self.assertEqual(validator.safe_float(None, 0.0), 0.0)
        self.assertIsNone(validator.safe_float_optional("invalid"))
        
        # Test edge cases
        self.assertIsNone(validator.safe_float_optional(float('inf')))
        self.assertIsNone(validator.safe_float_optional(float('nan')))
        
    def test_example_market_cap_normalization(self):
        """Example: Test market cap normalization"""
        from enhanced_integrated_analyzer_refactored import MarketCapNormalizer
        
        normalizer = MarketCapNormalizer()
        
        # Test various market cap values
        test_cases = [
            (100000000000, 1000.0),  # 1000억원
            (10000000000, 100.0),    # 100억원
            (1000000000, 10.0),      # 10억원
            (100000000, 1.0),        # 1억원
            (10000000, 0.1),         # 0.1억원
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalizer.normalize_market_cap_ekwon(input_val)
                self.assertAlmostEqual(result, expected, places=2)
                
    def test_example_percent_canonicalization(self):
        """Example: Test percent canonicalization"""
        from enhanced_integrated_analyzer_refactored import PercentCanonicalizer
        
        canonicalizer = PercentCanonicalizer()
        
        # Test percent conversion
        test_cases = [
            (0.05, 5.0),    # 0.05 → 5%
            (0.1, 10.0),    # 0.1 → 10%
            (0.5, 50.0),    # 0.5 → 50%
            (1.0, 100.0),   # 1.0 → 100%
            (1.5, 150.0),   # 1.5 → 150%
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = canonicalizer.canonicalize_percent(input_val)
                self.assertAlmostEqual(result, expected, places=2)
                
    def test_example_price_position_calculation(self):
        """Example: Test price position calculation"""
        from enhanced_integrated_analyzer_refactored import PricePositionCalculator
        
        calculator = PricePositionCalculator()
        
        # Test price position calculation
        price_data = {
            "current": 150,
            "w52_high": 200,
            "w52_low": 100
        }
        
        result = calculator.calculate_price_position(price_data)
        self.assertEqual(result, 50.0)  # Middle of range
        
        # Test edge cases
        price_data_zero_range = {
            "current": 100,
            "w52_high": 100,
            "w52_low": 100
        }
        
        result = calculator.calculate_price_position(price_data_zero_range)
        self.assertEqual(result, 50.0)  # Should return middle position
        
    def test_example_sector_analysis(self):
        """Example: Test sector analysis"""
        from enhanced_integrated_analyzer_refactored import SectorAnalyzer
        
        analyzer = SectorAnalyzer()
        
        # Test sector characteristics
        result = analyzer._get_sector_characteristics("005930")
        self.assertIsInstance(result, dict)
        self.assertIn('name', result)
        
        # Test unknown sector
        result = analyzer._get_sector_characteristics("UNKNOWN")
        self.assertEqual(result.get('name'), '기타')
        
    def test_example_financial_ratio_analysis(self):
        """Example: Test financial ratio analysis"""
        from enhanced_integrated_analyzer_refactored import FinancialRatioAnalyzer
        
        analyzer = FinancialRatioAnalyzer()
        
        # Test with sample data
        financial_data = {
            "roe": 15.0,
            "roa": 8.0,
            "debt_ratio": 30.0,
            "current_ratio": 150.0
        }
        
        price_data = {
            "per": 12.0,
            "pbr": 1.5
        }
        
        result = analyzer.analyze_financial_ratios("TEST", financial_data, price_data)
        self.assertIsInstance(result, dict)
        self.assertIn('total_score', result)
        self.assertGreaterEqual(result['total_score'], 0.0)
        self.assertLessEqual(result['total_score'], 100.0)
        
    def test_example_growth_analysis(self):
        """Example: Test growth analysis"""
        from enhanced_integrated_analyzer_refactored import GrowthAnalyzer
        
        analyzer = GrowthAnalyzer()
        
        # Test with sample data
        financial_data = {
            "operating_profit_growth": 10.0,
            "net_profit_growth": 8.0
        }
        
        result = analyzer.analyze_growth("TEST", financial_data, {})
        self.assertIsInstance(result, dict)
        self.assertIn('total_score', result)
        self.assertGreaterEqual(result['total_score'], 0.0)
        self.assertLessEqual(result['total_score'], 100.0)
        
    def test_example_scale_analysis(self):
        """Example: Test scale analysis"""
        from enhanced_integrated_analyzer_refactored import ScaleAnalyzer
        
        analyzer = ScaleAnalyzer()
        
        # Test with different market caps
        test_cases = [
            (100000, "메가캡"),      # 10조원
            (50000, "대형주"),       # 5조원
            (10000, "중대형주"),     # 1조원
            (5000, "중형주"),        # 5천억원
            (1000, "소형주"),        # 1천억원
            (100, "마이크로캡"),     # 100억원
        ]
        
        for market_cap, expected_category in test_cases:
            with self.subTest(market_cap=market_cap):
                result = analyzer.analyze_scale("TEST", market_cap, {})
                self.assertIsInstance(result, dict)
                self.assertIn('total_score', result)
                self.assertGreaterEqual(result['total_score'], 0.0)
                self.assertLessEqual(result['total_score'], 100.0)
                
    def test_example_opinion_analysis(self):
        """Example: Test opinion analysis"""
        from enhanced_integrated_analyzer_refactored import OpinionAnalyzer
        
        analyzer = OpinionAnalyzer()
        
        # Test with sample data
        opinion_data = {
            "buy_count": 5,
            "hold_count": 3,
            "sell_count": 2,
            "target_price": 80000,
            "current_price": 70000
        }
        
        result = analyzer.analyze_opinion("TEST", opinion_data)
        self.assertIsInstance(result, dict)
        self.assertIn('total_score', result)
        self.assertGreaterEqual(result['total_score'], 0.0)
        self.assertLessEqual(result['total_score'], 100.0)
        
    def test_example_estimate_analysis(self):
        """Example: Test estimate analysis"""
        from enhanced_integrated_analyzer_refactored import EstimateAnalyzer
        
        analyzer = EstimateAnalyzer()
        
        # Test with sample data
        estimate_data = {
            "revenue_growth": 8.0,
            "operating_profit_growth": 12.0,
            "net_profit_growth": 10.0
        }
        
        result = analyzer.analyze_estimate("TEST", estimate_data)
        self.assertIsInstance(result, dict)
        self.assertIn('total_score', result)
        self.assertGreaterEqual(result['total_score'], 0.0)
        self.assertLessEqual(result['total_score'], 100.0)
        
    def test_example_mocking_external_dependencies(self):
        """Example: Test with mocked external dependencies"""
        # Mock the data provider
        with patch.object(self.analyzer.data_provider, 'get_price_data') as mock_price:
            with patch.object(self.analyzer.data_provider, 'get_financial_data') as mock_financial:
                # Set up mock return values
                mock_price.return_value = {
                    "current": 70000,
                    "per": 12.0,
                    "pbr": 1.5,
                    "w52_high": 80000,
                    "w52_low": 60000
                }
                
                mock_financial.return_value = {
                    "roe": 15.0,
                    "roa": 8.0,
                    "debt_ratio": 30.0,
                    "current_ratio": 150.0
                }
                
                # Test analysis with mocked data
                result = self.analyzer.analyze_single_stock("TEST", "TestStock")
                
                # Verify mocks were called
                mock_price.assert_called_once_with("TEST")
                mock_financial.assert_called_once_with("TEST")
                
                # Verify result
                self.assertIsInstance(result, AnalysisResult)
                self.assertEqual(result.symbol, "TEST")
                self.assertEqual(result.name, "TestStock")
                
    def test_example_error_handling(self):
        """Example: Test error handling"""
        # Test with invalid symbol
        result = self.analyzer.analyze_single_stock("INVALID", "InvalidStock")
        
        # Should handle gracefully
        self.assertIsInstance(result, AnalysisResult)
        self.assertIn(result.status, [AnalysisStatus.SUCCESS, AnalysisStatus.PARTIAL_SUCCESS, AnalysisStatus.FAILED])
        
        # Test with None values
        result = self.analyzer.analyze_single_stock(None, None)
        self.assertIsInstance(result, AnalysisResult)
        
    def test_example_performance_measurement(self):
        """Example: Test performance measurement"""
        symbol = "005930"
        name = "Samsung"
        
        # Measure analysis time
        start_time = time.time()
        result = self.analyzer.analyze_single_stock(symbol, name)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Verify performance
        self.assertLess(duration, 30.0, f"Analysis took {duration:.2f}s, expected < 30s")
        self.assertEqual(result.status, AnalysisStatus.SUCCESS)
        
        print(f"Analysis completed in {duration:.2f}s")
        
    def test_example_concurrent_analysis(self):
        """Example: Test concurrent analysis"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def analyze_stock(symbol_name_pair):
            symbol, name = symbol_name_pair
            return self.analyzer.analyze_single_stock(symbol, name)
            
        # Test concurrent execution
        test_pairs = [
            ("005930", "Samsung"),
            ("000660", "SK Hynix"),
            ("035420", "NAVER"),
        ]
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(analyze_stock, pair) for pair in test_pairs]
            results = [future.result(timeout=60) for future in as_completed(futures, timeout=60)]
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Verify all results
        for result in results:
            self.assertEqual(result.status, AnalysisStatus.SUCCESS)
            
        print(f"Concurrent analysis completed in {duration:.2f}s")


def run_examples():
    """Run the example tests"""
    print("Running Test Examples")
    print("=" * 40)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestExamples)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 40)
    if result.wasSuccessful():
        print("All example tests passed!")
        return True
    else:
        print(f"{len(result.failures)} failures, {len(result.errors)} errors")
        return False


if __name__ == "__main__":
    success = run_examples()
    sys.exit(0 if success else 1)
