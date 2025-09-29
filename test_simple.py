#!/usr/bin/env python3
"""
Simple Test Suite for Enhanced Integrated Analyzer
=================================================

This file contains simple, working test cases that use the actual
classes and methods available in the analyzer.

Usage:
    python test_simple.py
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
    print(f"Failed to import analyzer: {e}")
    sys.exit(1)


class SimpleTests(unittest.TestCase):
    """Simple test cases for the analyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = EnhancedIntegratedAnalyzer()
        
    def test_analyzer_import(self):
        """Test that the analyzer can be imported and instantiated"""
        self.assertIsNotNone(self.analyzer)
        self.assertIsInstance(self.analyzer, EnhancedIntegratedAnalyzer)
        
    def test_data_validator_basic(self):
        """Test basic data validation functionality"""
        validator = DataValidator()
        
        # Test valid conversions
        self.assertEqual(validator.safe_float("123.45"), 123.45)
        self.assertEqual(validator.safe_float("0"), 0.0)
        self.assertEqual(validator.safe_float("-50.5"), -50.5)
        
        # Test invalid data with default
        self.assertEqual(validator.safe_float("invalid", 99.0), 99.0)
        self.assertEqual(validator.safe_float(None, 0.0), 0.0)
        
        # Test optional conversion
        self.assertIsNone(validator.safe_float_optional("invalid"))
        self.assertEqual(validator.safe_float_optional("123.45"), 123.45)
        
    def test_single_stock_analysis_basic(self):
        """Test basic single stock analysis"""
        symbol = "005930"
        name = "Samsung"
        
        result = self.analyzer.analyze_single_stock(symbol, name)
        
        # Verify result structure
        self.assertIsInstance(result, AnalysisResult)
        self.assertEqual(result.symbol, symbol)
        self.assertEqual(result.name, name)
        self.assertIn(result.status, [AnalysisStatus.SUCCESS, AnalysisStatus.ERROR, AnalysisStatus.SKIPPED_PREF, AnalysisStatus.NO_DATA])
        
        # If successful, check additional fields
        if result.status == AnalysisStatus.SUCCESS:
            self.assertGreater(result.enhanced_score, 0.0)
            self.assertIsNotNone(result.enhanced_grade)
            
    def test_analysis_status_values(self):
        """Test that all expected analysis status values exist"""
        expected_statuses = [
            AnalysisStatus.SUCCESS,
            AnalysisStatus.ERROR,
            AnalysisStatus.SKIPPED_PREF,
            AnalysisStatus.NO_DATA
        ]
        
        for status in expected_statuses:
            self.assertIsNotNone(status)
            self.assertIsInstance(status, AnalysisStatus)
            
    def test_analyzer_with_invalid_input(self):
        """Test analyzer with invalid input"""
        # Test with None values
        result = self.analyzer.analyze_single_stock(None, None)
        self.assertIsInstance(result, AnalysisResult)
        
        # Test with empty strings
        result = self.analyzer.analyze_single_stock("", "")
        self.assertIsInstance(result, AnalysisResult)
        
        # Test with invalid symbol
        result = self.analyzer.analyze_single_stock("INVALID", "InvalidStock")
        self.assertIsInstance(result, AnalysisResult)
        
    def test_analyzer_performance_basic(self):
        """Test basic performance of analyzer"""
        symbol = "005930"
        name = "Samsung"
        
        start_time = time.time()
        result = self.analyzer.analyze_single_stock(symbol, name)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Should complete within reasonable time
        self.assertLess(duration, 60.0, f"Analysis took {duration:.2f}s, expected < 60s")
        self.assertIsInstance(result, AnalysisResult)
        
        print(f"Analysis completed in {duration:.2f}s")
        
    def test_data_validator_edge_cases(self):
        """Test data validator with edge cases"""
        validator = DataValidator()
        
        # Test infinity and NaN
        self.assertIsNone(validator.safe_float_optional(float('inf')))
        self.assertIsNone(validator.safe_float_optional(float('nan')))
        
        # Test negative values
        self.assertEqual(validator.safe_float(-123.45), -123.45)
        
        # Test zero
        self.assertEqual(validator.safe_float(0), 0.0)
        self.assertEqual(validator.safe_float("0"), 0.0)
        
    def test_analyzer_configuration(self):
        """Test analyzer configuration"""
        # Test that analyzer has expected attributes
        self.assertIsNotNone(self.analyzer.data_provider)
        self.assertIsNotNone(self.analyzer.score_calculator)
        
        # Test that analyzer can be reconfigured
        original_provider = self.analyzer.data_provider
        self.assertIsNotNone(original_provider)
        
    def test_analyzer_caching(self):
        """Test analyzer caching behavior"""
        symbol = "005930"
        name = "Samsung"
        
        # First call
        start_time = time.time()
        result1 = self.analyzer.analyze_single_stock(symbol, name)
        first_duration = time.time() - start_time
        
        # Second call (should use cache if available)
        start_time = time.time()
        result2 = self.analyzer.analyze_single_stock(symbol, name)
        second_duration = time.time() - start_time
        
        # Both should succeed
        self.assertEqual(result1.status, result2.status)
        self.assertEqual(result1.symbol, result2.symbol)
        self.assertEqual(result1.name, result2.name)
        
        print(f"First call: {first_duration:.2f}s, Second call: {second_duration:.2f}s")
        
    def test_analyzer_error_handling(self):
        """Test analyzer error handling"""
        # Test with various invalid inputs
        test_cases = [
            (None, None),
            ("", ""),
            ("INVALID", "InvalidStock"),
            ("123456789", "VeryLongSymbol"),
            ("005930", None),
            (None, "Samsung"),
        ]
        
        for symbol, name in test_cases:
            with self.subTest(symbol=symbol, name=name):
                result = self.analyzer.analyze_single_stock(symbol, name)
                self.assertIsInstance(result, AnalysisResult)
                self.assertIn(result.status, [AnalysisStatus.SUCCESS, AnalysisStatus.ERROR, AnalysisStatus.SKIPPED_PREF, AnalysisStatus.NO_DATA])


def run_simple_tests():
    """Run the simple tests"""
    print("Running Simple Tests")
    print("=" * 40)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(SimpleTests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 40)
    if result.wasSuccessful():
        print("All simple tests passed!")
        return True
    else:
        print(f"{len(result.failures)} failures, {len(result.errors)} errors")
        return False


if __name__ == "__main__":
    success = run_simple_tests()
    sys.exit(0 if success else 1)
