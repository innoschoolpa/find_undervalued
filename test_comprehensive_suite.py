#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Integrated Analyzer
========================================================

This test suite covers:
1. Unit tests for edge cases and core functionality
2. Performance tests for analyzer components
3. Integration tests with fake providers
4. Validation tests for unit conversions

Usage:
    python test_comprehensive_suite.py [--verbose] [--performance] [--integration] [--unit-conversions]
"""

import os
import sys
import time
import math
import json
import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import tempfile
import shutil

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the analyzer and related components
try:
    import enhanced_integrated_analyzer_refactored as eia
    from enhanced_integrated_analyzer_refactored import (
        EnhancedIntegratedAnalyzer,
        DataValidator,
        AnalysisResult,
        AnalysisStatus,
        TPSRateLimiter,
        PercentCanonicalizer,
        MarketCapNormalizer,
        PricePositionCalculator,
        SectorAnalyzer,
        FinancialRatioAnalyzer,
        GrowthAnalyzer,
        ScaleAnalyzer,
        OpinionAnalyzer,
        EstimateAnalyzer
    )
except ImportError as e:
    print(f"❌ Failed to import analyzer: {e}")
    sys.exit(1)


@dataclass
class TestConfig:
    """Test configuration"""
    enable_fake_providers: bool = True
    verbose: bool = False
    performance_mode: bool = False
    integration_mode: bool = False
    unit_conversion_mode: bool = False
    max_workers: int = 2
    timeout_seconds: int = 30


class TestEnvironment:
    """Test environment setup and teardown"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.temp_dir = None
        self.original_env = {}
        
    def setup(self):
        """Set up test environment"""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="analyzer_test_")
        
        # Set environment variables for testing
        self.original_env = {
            'ENABLE_FAKE_PROVIDERS': os.environ.get('ENABLE_FAKE_PROVIDERS'),
            'MARKET_CAP_STRICT_MODE': os.environ.get('MARKET_CAP_STRICT_MODE'),
            'CURRENT_RATIO_STRATEGY': os.environ.get('CURRENT_RATIO_STRATEGY'),
            'TPS_LIMIT': os.environ.get('TPS_LIMIT'),
        }
        
        os.environ['ENABLE_FAKE_PROVIDERS'] = 'true'
        os.environ['MARKET_CAP_STRICT_MODE'] = 'false'  # Relaxed mode for testing
        os.environ['CURRENT_RATIO_STRATEGY'] = 'as_is'
        os.environ['TPS_LIMIT'] = '10'  # Higher limit for testing
        
        if self.config.verbose:
            print(f"🧪 Test environment setup: {self.temp_dir}")
            
    def teardown(self):
        """Clean up test environment"""
        # Restore original environment
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
                
        # Clean up temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
        if self.config.verbose:
            print("🧹 Test environment cleaned up")


class UnitTests(unittest.TestCase):
    """Unit tests for edge cases and core functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = EnhancedIntegratedAnalyzer()
        self.validator = DataValidator()
        
    def test_data_validator_edge_cases(self):
        """Test DataValidator with edge cases"""
        # Test None values
        self.assertIsNone(self.validator.safe_float_optional(None))
        self.assertEqual(self.validator.safe_float(None, 0.0), 0.0)
        
        # Test string conversions
        self.assertEqual(self.validator.safe_float("123.45"), 123.45)
        self.assertEqual(self.validator.safe_float("invalid", 99.0), 99.0)
        
        # Test infinity and NaN
        self.assertIsNone(self.validator.safe_float_optional(float('inf')))
        self.assertIsNone(self.validator.safe_float_optional(float('nan')))
        
        # Test negative values
        self.assertEqual(self.validator.safe_float(-123.45), -123.45)
        
    def test_percent_canonicalizer_edge_cases(self):
        """Test PercentCanonicalizer with edge cases"""
        canon = PercentCanonicalizer()
        
        # Test boundary values
        test_cases = [
            (0.0, 0.0),      # Zero
            (0.05, 5.0),     # Just below 0.1 threshold
            (0.1, 10.0),     # At threshold
            (0.5, 50.0),     # Middle range
            (1.0, 100.0),    # 100%
            (1.5, 150.0),    # Above 100%
            (10.0, 1000.0),  # High value
            (50.0, 50.0),    # Above 10, should remain as-is
            (100.0, 100.0),  # High value, should remain as-is
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = canon.canonicalize_percent(input_val)
                self.assertAlmostEqual(result, expected, places=2)
                
    def test_market_cap_normalizer_edge_cases(self):
        """Test MarketCapNormalizer with edge cases"""
        normalizer = MarketCapNormalizer()
        
        # Test various input formats
        test_cases = [
            # (input, expected_output_억원, description)
            (100000000000, 1000.0, "1000억원 in won"),
            (10000000000, 100.0, "100억원 in won"),
            (1000000000, 10.0, "10억원 in won"),
            (100000000, 1.0, "1억원 in won"),
            (10000000, 0.1, "0.1억원 in won"),
            (1000000, 0.01, "0.01억원 in won"),
            (100000, 0.001, "0.001억원 in won"),
            (10000, 0.0001, "0.0001억원 in won"),
            (1000, 0.00001, "0.00001억원 in won"),
            (100, 0.000001, "0.000001억원 in won"),
            (10, 0.0000001, "0.0000001억원 in won"),
            (1, 0.00000001, "0.00000001억원 in won"),
        ]
        
        for input_val, expected, description in test_cases:
            with self.subTest(description=description):
                result = normalizer.normalize_market_cap_ekwon(input_val)
                self.assertAlmostEqual(result, expected, places=8)
                
    def test_price_position_calculator_edge_cases(self):
        """Test PricePositionCalculator with edge cases"""
        calculator = PricePositionCalculator()
        
        # Test with None values
        self.assertIsNone(calculator.calculate_price_position({}))
        
        # Test with missing fields
        price_data = {"current": 100}
        self.assertIsNone(calculator.calculate_price_position(price_data))
        
        # Test with zero range (w52_high == w52_low)
        price_data = {
            "current": 100,
            "w52_high": 100,
            "w52_low": 100
        }
        result = calculator.calculate_price_position(price_data)
        self.assertEqual(result, 50.0)  # Should return middle position
        
        # Test with normal range
        price_data = {
            "current": 150,
            "w52_high": 200,
            "w52_low": 100
        }
        result = calculator.calculate_price_position(price_data)
        self.assertEqual(result, 50.0)  # Middle of range
        
        # Test at boundaries
        price_data = {
            "current": 100,
            "w52_high": 200,
            "w52_low": 100
        }
        result = calculator.calculate_price_position(price_data)
        self.assertEqual(result, 0.0)  # At low
        
        price_data = {
            "current": 200,
            "w52_high": 200,
            "w52_low": 100
        }
        result = calculator.calculate_price_position(price_data)
        self.assertEqual(result, 100.0)  # At high
        
    def test_sector_analyzer_edge_cases(self):
        """Test SectorAnalyzer with edge cases"""
        analyzer = SectorAnalyzer()
        
        # Test with unknown sector
        result = analyzer._get_sector_characteristics("UNKNOWN")
        self.assertEqual(result.get('name'), '기타')
        
        # Test with None symbol
        result = analyzer._get_sector_characteristics(None)
        self.assertEqual(result.get('name'), '기타')
        
        # Test with empty string
        result = analyzer._get_sector_characteristics("")
        self.assertEqual(result.get('name'), '기타')
        
    def test_financial_ratio_analyzer_edge_cases(self):
        """Test FinancialRatioAnalyzer with edge cases"""
        analyzer = FinancialRatioAnalyzer()
        
        # Test with None values
        result = analyzer.analyze_financial_ratios("TEST", None, None)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
        # Test with empty data
        result = analyzer.analyze_financial_ratios("TEST", {}, {})
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
        # Test with invalid data types
        result = analyzer.analyze_financial_ratios("TEST", {"roe": "invalid"}, {"per": "invalid"})
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
    def test_growth_analyzer_edge_cases(self):
        """Test GrowthAnalyzer with edge cases"""
        analyzer = GrowthAnalyzer()
        
        # Test with None values
        result = analyzer.analyze_growth("TEST", None, None)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
        # Test with empty data
        result = analyzer.analyze_growth("TEST", {}, {})
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
        # Test with negative growth
        financial_data = {
            "operating_profit_growth": -10.0,
            "net_profit_growth": -5.0
        }
        result = analyzer.analyze_growth("TEST", financial_data, {})
        self.assertIsInstance(result, dict)
        self.assertLess(result.get('total_score', 0), 50.0)  # Should be low score
        
    def test_scale_analyzer_edge_cases(self):
        """Test ScaleAnalyzer with edge cases"""
        analyzer = ScaleAnalyzer()
        
        # Test with None market cap
        result = analyzer.analyze_scale("TEST", None, {})
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
        # Test with zero market cap
        result = analyzer.analyze_scale("TEST", 0.0, {})
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
        # Test with negative market cap
        result = analyzer.analyze_scale("TEST", -1000.0, {})
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
    def test_opinion_analyzer_edge_cases(self):
        """Test OpinionAnalyzer with edge cases"""
        analyzer = OpinionAnalyzer()
        
        # Test with None data
        result = analyzer.analyze_opinion("TEST", None)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
        # Test with empty data
        result = analyzer.analyze_opinion("TEST", {})
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
    def test_estimate_analyzer_edge_cases(self):
        """Test EstimateAnalyzer with edge cases"""
        analyzer = EstimateAnalyzer()
        
        # Test with None data
        result = analyzer.analyze_estimate("TEST", None)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)
        
        # Test with empty data
        result = analyzer.analyze_estimate("TEST", {})
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('total_score'), 0.0)


class PerformanceTests(unittest.TestCase):
    """Performance tests for analyzer components"""
    
    def setUp(self):
        """Set up performance test fixtures"""
        self.analyzer = EnhancedIntegratedAnalyzer()
        self.test_symbols = ["005930", "000660", "035420", "051910", "006400"]
        
    def test_single_stock_analysis_performance(self):
        """Test single stock analysis performance"""
        symbol = "005930"
        name = "Samsung"
        
        start_time = time.time()
        result = self.analyzer.analyze_single_stock(symbol, name)
        end_time = time.time()
        
        duration = end_time - start_time
        self.assertLess(duration, 30.0, f"Single stock analysis took {duration:.2f}s, expected < 30s")
        self.assertEqual(result.status, AnalysisStatus.SUCCESS)
        
        if hasattr(self, 'config') and self.config.verbose:
            print(f"⏱️  Single stock analysis: {duration:.2f}s")
            
    def test_parallel_analysis_performance(self):
        """Test parallel analysis performance"""
        def analyze_symbol(symbol_name_pair):
            symbol, name = symbol_name_pair
            return self.analyzer.analyze_single_stock(symbol, name)
            
        # Test parallel execution
        test_pairs = [(symbol, f"Stock_{symbol}") for symbol in self.test_symbols]
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(analyze_symbol, pair) for pair in test_pairs]
            results = [future.result(timeout=60) for future in as_completed(futures, timeout=60)]
        end_time = time.time()
        
        duration = end_time - start_time
        self.assertLess(duration, 120.0, f"Parallel analysis took {duration:.2f}s, expected < 120s")
        
        # Check all results
        for result in results:
            self.assertEqual(result.status, AnalysisStatus.SUCCESS)
            
        if hasattr(self, 'config') and self.config.verbose:
            print(f"⏱️  Parallel analysis ({len(test_pairs)} stocks): {duration:.2f}s")
            
    def test_tps_rate_limiter_performance(self):
        """Test TPS rate limiter performance"""
        limiter = TPSRateLimiter(tps_limit=10, burst_limit=15)
        
        # Test rate limiting
        start_time = time.time()
        for i in range(20):
            limiter.acquire()
        end_time = time.time()
        
        duration = end_time - start_time
        expected_min_duration = 1.0  # 20 requests at 10 TPS = 2 seconds, but burst allows faster start
        self.assertGreater(duration, expected_min_duration, 
                          f"Rate limiting too fast: {duration:.2f}s, expected > {expected_min_duration}s")
        
        if hasattr(self, 'config') and self.config.verbose:
            print(f"⏱️  TPS rate limiter (20 requests): {duration:.2f}s")
            
    def test_cache_performance(self):
        """Test cache performance"""
        # Test cache hit performance
        symbol = "005930"
        name = "Samsung"
        
        # First call (cache miss)
        start_time = time.time()
        result1 = self.analyzer.analyze_single_stock(symbol, name)
        first_duration = time.time() - start_time
        
        # Second call (cache hit)
        start_time = time.time()
        result2 = self.analyzer.analyze_single_stock(symbol, name)
        second_duration = time.time() - start_time
        
        # Cache hit should be significantly faster
        self.assertLess(second_duration, first_duration * 0.5, 
                       f"Cache hit not faster: {second_duration:.2f}s vs {first_duration:.2f}s")
        
        if hasattr(self, 'config') and self.config.verbose:
            print(f"⏱️  Cache performance: {first_duration:.2f}s (miss) vs {second_duration:.2f}s (hit)")
            
    def test_memory_usage(self):
        """Test memory usage during analysis"""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform multiple analyses
        for i in range(10):
            symbol = f"00{i:04d}"
            name = f"TestStock_{i}"
            result = self.analyzer.analyze_single_stock(symbol, name)
            self.assertEqual(result.status, AnalysisStatus.SUCCESS)
            
        # Force garbage collection
        gc.collect()
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB)
        self.assertLess(memory_increase, 100.0, 
                       f"Memory increase too high: {memory_increase:.2f}MB")
        
        if hasattr(self, 'config') and self.config.verbose:
            print(f"💾 Memory usage: {initial_memory:.2f}MB → {final_memory:.2f}MB (+{memory_increase:.2f}MB)")


class IntegrationTests(unittest.TestCase):
    """Integration tests with fake providers"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        # Ensure fake providers are enabled
        os.environ['ENABLE_FAKE_PROVIDERS'] = 'true'
        self.analyzer = EnhancedIntegratedAnalyzer()
        
    def test_fake_provider_integration(self):
        """Test integration with fake providers"""
        symbol = "TEST001"
        name = "TestStock"
        
        result = self.analyzer.analyze_single_stock(symbol, name)
        
        # Should succeed with fake providers
        self.assertEqual(result.status, AnalysisStatus.SUCCESS)
        self.assertGreater(result.enhanced_score, 0.0)
        self.assertIsNotNone(result.enhanced_grade)
        
    def test_data_provider_fallback(self):
        """Test data provider fallback mechanism"""
        # Mock a provider to fail
        with patch.object(self.analyzer.data_provider, 'get_price_data') as mock_price:
            mock_price.side_effect = Exception("Provider error")
            
            symbol = "TEST002"
            name = "TestStock2"
            
            result = self.analyzer.analyze_single_stock(symbol, name)
            
            # Should still succeed with fallback
            self.assertEqual(result.status, AnalysisStatus.SUCCESS)
            
    def test_api_rate_limiting_integration(self):
        """Test API rate limiting integration"""
        # Test with high TPS limit
        os.environ['TPS_LIMIT'] = '20'
        
        symbol = "TEST003"
        name = "TestStock3"
        
        start_time = time.time()
        result = self.analyzer.analyze_single_stock(symbol, name)
        end_time = time.time()
        
        self.assertEqual(result.status, AnalysisStatus.SUCCESS)
        
        if hasattr(self, 'config') and self.config.verbose:
            print(f"⏱️  API rate limiting test: {end_time - start_time:.2f}s")
            
    def test_cache_integration(self):
        """Test cache integration"""
        symbol = "TEST004"
        name = "TestStock4"
        
        # First call
        result1 = self.analyzer.analyze_single_stock(symbol, name)
        self.assertEqual(result1.status, AnalysisStatus.SUCCESS)
        
        # Second call (should use cache)
        result2 = self.analyzer.analyze_single_stock(symbol, name)
        self.assertEqual(result2.status, AnalysisStatus.SUCCESS)
        
        # Results should be identical
        self.assertEqual(result1.enhanced_score, result2.enhanced_score)
        self.assertEqual(result1.enhanced_grade, result2.enhanced_grade)
        
    def test_error_handling_integration(self):
        """Test error handling integration"""
        # Test with invalid symbol
        result = self.analyzer.analyze_single_stock("INVALID", "InvalidStock")
        
        # Should handle gracefully
        self.assertIn(result.status, [AnalysisStatus.SUCCESS, AnalysisStatus.PARTIAL_SUCCESS, AnalysisStatus.FAILED])
        
    def test_concurrent_analysis_integration(self):
        """Test concurrent analysis integration"""
        def analyze_stock(symbol_name_pair):
            symbol, name = symbol_name_pair
            return self.analyzer.analyze_single_stock(symbol, name)
            
        test_pairs = [
            ("TEST005", "TestStock5"),
            ("TEST006", "TestStock6"),
            ("TEST007", "TestStock7"),
        ]
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(analyze_stock, pair) for pair in test_pairs]
            results = [future.result(timeout=60) for future in as_completed(futures, timeout=60)]
            
        # All should succeed
        for result in results:
            self.assertEqual(result.status, AnalysisStatus.SUCCESS)


class UnitConversionTests(unittest.TestCase):
    """Validation tests for unit conversions"""
    
    def setUp(self):
        """Set up unit conversion test fixtures"""
        self.validator = DataValidator()
        self.canonicalizer = PercentCanonicalizer()
        self.normalizer = MarketCapNormalizer()
        
    def test_market_cap_conversion_strict_mode(self):
        """Test market cap conversion in strict mode"""
        os.environ['MARKET_CAP_STRICT_MODE'] = 'true'
        
        # Test clear cases
        test_cases = [
            (100000000000, 1000.0, "1000억원"),
            (10000000000, 100.0, "100억원"),
            (1000000000, 10.0, "10억원"),
            (100000000, 1.0, "1억원"),
        ]
        
        for input_val, expected, description in test_cases:
            with self.subTest(description=description):
                result = self.normalizer.normalize_market_cap_ekwon(input_val)
                self.assertAlmostEqual(result, expected, places=2)
                
    def test_market_cap_conversion_relaxed_mode(self):
        """Test market cap conversion in relaxed mode"""
        os.environ['MARKET_CAP_STRICT_MODE'] = 'false'
        
        # Test ambiguous cases that should work in relaxed mode
        test_cases = [
            (25000000000, 250.0, "2.5e10 → 250억원 (relaxed)"),
            (5000000000, 50.0, "5e9 → 50억원 (relaxed)"),
        ]
        
        for input_val, expected, description in test_cases:
            with self.subTest(description=description):
                result = self.normalizer.normalize_market_cap_ekwon(input_val)
                self.assertAlmostEqual(result, expected, places=2)
                
    def test_current_ratio_conversion_strategies(self):
        """Test current ratio conversion strategies"""
        test_cases = [
            # (input, strategy, expected_output, description)
            (0.8, 'multiply', 80.0, "0.8 → 80% (multiply)"),
            (1.5, 'as_is', 1.5, "1.5 → 1.5 (as_is)"),
            (12.0, 'multiply', 1200.0, "12 → 1200% (multiply)"),
            (65.0, 'as_is', 65.0, "65 → 65 (as_is)"),
            (25.0, 'clamp', 25.0, "25 → 25 (clamp)"),
        ]
        
        for input_val, strategy, expected, description in test_cases:
            with self.subTest(description=description):
                os.environ['CURRENT_RATIO_STRATEGY'] = strategy
                result = self.canonicalizer.canonicalize_percent(input_val)
                self.assertAlmostEqual(result, expected, places=2)
                
    def test_percent_canonicalization_edge_cases(self):
        """Test percent canonicalization edge cases"""
        test_cases = [
            # (input, expected_output, description)
            (0.0, 0.0, "Zero"),
            (0.05, 5.0, "Just below threshold"),
            (0.1, 10.0, "At threshold"),
            (0.5, 50.0, "Middle range"),
            (1.0, 100.0, "100%"),
            (1.5, 150.0, "Above 100%"),
            (10.0, 1000.0, "High value"),
            (50.0, 50.0, "Above 10, as-is"),
            (100.0, 100.0, "Very high, as-is"),
        ]
        
        for input_val, expected, description in test_cases:
            with self.subTest(description=description):
                result = self.canonicalizer.canonicalize_percent(input_val)
                self.assertAlmostEqual(result, expected, places=2)
                
    def test_financial_ratio_unit_consistency(self):
        """Test financial ratio unit consistency"""
        # Test that all financial ratios are properly canonicalized
        test_data = {
            'roe': 0.12,      # Should become 12
            'roa': 0.07,      # Should become 7
            'debt_ratio': 0.45,  # Should become 45
            'current_ratio': 1.5,  # Should remain 1.5 (strategy dependent)
        }
        
        # Mock the analyzer to test canonicalization
        analyzer = EnhancedIntegratedAnalyzer()
        
        # Test that ratios are properly processed
        result = analyzer._standardize_financial_units(test_data)
        
        # Check that ratios are in expected format
        self.assertIsInstance(result.get('roe'), (int, float))
        self.assertIsInstance(result.get('roa'), (int, float))
        self.assertIsInstance(result.get('debt_ratio'), (int, float))
        self.assertIsInstance(result.get('current_ratio'), (int, float))
        
    def test_price_position_edge_cases(self):
        """Test price position calculation edge cases"""
        calculator = PricePositionCalculator()
        
        # Test with zero range
        price_data = {
            "current": 100,
            "w52_high": 100,
            "w52_low": 100
        }
        result = calculator.calculate_price_position(price_data)
        self.assertEqual(result, 50.0)
        
        # Test with tiny range
        price_data = {
            "current": 100.1,
            "w52_high": 100.2,
            "w52_low": 100.0
        }
        result = calculator.calculate_price_position(price_data)
        self.assertIsInstance(result, (int, float))
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 100.0)
        
        # Test with realistic inputs
        price_data = {
            "current": 75000,
            "w52_high": 80000,
            "w52_low": 60000
        }
        result = calculator.calculate_price_position(price_data)
        self.assertAlmostEqual(result, 75.0, places=1)  # 75% position


class TestRunner:
    """Test runner with configuration and reporting"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.results = {}
        
    def run_tests(self):
        """Run all tests based on configuration"""
        print("🚀 Starting Comprehensive Test Suite")
        print(f"📋 Configuration: {self.config}")
        print("=" * 60)
        
        # Set up test environment
        env = TestEnvironment(self.config)
        env.setup()
        
        try:
            # Run unit tests
            if not self.config.performance_mode and not self.config.integration_mode and not self.config.unit_conversion_mode:
                print("\n🧪 Running Unit Tests...")
                self._run_test_class(UnitTests)
                
            # Run performance tests
            if self.config.performance_mode:
                print("\n⏱️  Running Performance Tests...")
                self._run_test_class(PerformanceTests)
                
            # Run integration tests
            if self.config.integration_mode:
                print("\n🔗 Running Integration Tests...")
                self._run_test_class(IntegrationTests)
                
            # Run unit conversion tests
            if self.config.unit_conversion_mode:
                print("\n🔄 Running Unit Conversion Tests...")
                self._run_test_class(UnitConversionTests)
                
            # Run all tests if no specific mode specified
            if not any([self.config.performance_mode, self.config.integration_mode, self.config.unit_conversion_mode]):
                print("\n🧪 Running Unit Tests...")
                self._run_test_class(UnitTests)
                print("\n⏱️  Running Performance Tests...")
                self._run_test_class(PerformanceTests)
                print("\n🔗 Running Integration Tests...")
                self._run_test_class(IntegrationTests)
                print("\n🔄 Running Unit Conversion Tests...")
                self._run_test_class(UnitConversionTests)
                
        finally:
            env.teardown()
            
        self._print_summary()
        
    def _run_test_class(self, test_class):
        """Run a specific test class"""
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        
        # Add config to test instances
        for test in suite:
            test.config = self.config
            
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if self.config.verbose else 1)
        result = runner.run(suite)
        
        # Store results
        class_name = test_class.__name__
        self.results[class_name] = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success': result.wasSuccessful()
        }
        
    def _print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        
        for class_name, result in self.results.items():
            total_tests += result['tests_run']
            total_failures += result['failures']
            total_errors += result['errors']
            
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{class_name:30} {status:8} ({result['tests_run']} tests, {result['failures']} failures, {result['errors']} errors)")
            
        print("-" * 60)
        print(f"{'TOTAL':30} {'✅ PASS' if total_failures == 0 and total_errors == 0 else '❌ FAIL':8} ({total_tests} tests, {total_failures} failures, {total_errors} errors)")
        
        if total_failures == 0 and total_errors == 0:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {total_failures + total_errors} test(s) failed")
            
        return total_failures == 0 and total_errors == 0


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Test Suite for Enhanced Integrated Analyzer")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--performance", "-p", action="store_true", help="Run performance tests only")
    parser.add_argument("--integration", "-i", action="store_true", help="Run integration tests only")
    parser.add_argument("--unit-conversions", "-u", action="store_true", help="Run unit conversion tests only")
    parser.add_argument("--max-workers", type=int, default=2, help="Maximum number of workers for parallel tests")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout for individual tests (seconds)")
    
    args = parser.parse_args()
    
    # Create configuration
    config = TestConfig(
        verbose=args.verbose,
        performance_mode=args.performance,
        integration_mode=args.integration,
        unit_conversion_mode=args.unit_conversions,
        max_workers=args.max_workers,
        timeout_seconds=args.timeout
    )
    
    # Run tests
    runner = TestRunner(config)
    success = runner.run_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
