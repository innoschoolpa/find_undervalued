# Test Suite for Enhanced Integrated Analyzer

This directory contains a comprehensive test suite for the Enhanced Integrated Analyzer, including unit tests, performance tests, integration tests, and validation tests for unit conversions.

## Test Files

### Core Test Files

- **`test_simple.py`** - Simple, working test cases that use the actual classes and methods available in the analyzer
- **`test_comprehensive_suite.py`** - Comprehensive test suite with unit, performance, integration, and unit conversion tests
- **`test_examples.py`** - Example test cases and usage patterns (may have import issues)
- **`run_tests.py`** - Simple test runner with different configurations and options

### Configuration Files

- **`test_config.yaml`** - Test configuration file with settings for different test categories
- **`test_requirements.txt`** - Python dependencies required for testing

## Quick Start

### 1. Run Simple Tests (Recommended)
```bash
python test_simple.py
```

### 2. Run Smoke Test
```bash
python run_tests.py --smoke
```

### 3. Run Import Test
```bash
python run_tests.py --import
```

### 4. Run All Tests
```bash
python run_tests.py
```

## Test Categories

### Unit Tests
- **Data Validation**: Test `DataValidator` with edge cases, invalid inputs, and boundary conditions
- **Analysis Status**: Test `AnalysisStatus` enum values and result handling
- **Error Handling**: Test analyzer behavior with invalid inputs and error conditions
- **Configuration**: Test analyzer configuration and initialization

### Performance Tests
- **Single Stock Analysis**: Test performance of individual stock analysis
- **Caching**: Test cache hit/miss performance and effectiveness
- **Memory Usage**: Test memory consumption during analysis
- **Concurrent Analysis**: Test parallel analysis performance

### Integration Tests
- **Fake Providers**: Test integration with fake data providers
- **API Rate Limiting**: Test API rate limiting and throttling
- **Error Recovery**: Test fallback mechanisms and error recovery
- **Concurrent Execution**: Test thread safety and concurrent analysis

### Unit Conversion Tests
- **Market Cap Normalization**: Test market cap conversion in strict and relaxed modes
- **Percent Canonicalization**: Test percentage conversion and canonicalization
- **Current Ratio Conversion**: Test current ratio conversion strategies
- **Price Position Calculation**: Test price position calculation with edge cases

## Test Configuration

### Environment Variables
- `ENABLE_FAKE_PROVIDERS=true` - Enable fake providers for testing
- `MARKET_CAP_STRICT_MODE=false` - Use relaxed mode for market cap conversion
- `CURRENT_RATIO_STRATEGY=as_is` - Current ratio conversion strategy
- `TPS_LIMIT=10` - API rate limiting for testing

### Test Modes
- **Unit Tests Only**: `python run_tests.py --unit`
- **Performance Tests Only**: `python run_tests.py --performance`
- **Integration Tests Only**: `python run_tests.py --integration`
- **Unit Conversion Tests Only**: `python run_tests.py --conversions`
- **Quick Test Run**: `python run_tests.py --quick`
- **Verbose Output**: `python run_tests.py --verbose`

## Test Results

### Expected Output
```
Running Simple Tests
========================================
test_analyzer_import (__main__.SimpleTests.test_analyzer_import) ... ok
test_data_validator_basic (__main__.SimpleTests.test_data_validator_basic) ... ok
test_single_stock_analysis_basic (__main__.SimpleTests.test_single_stock_analysis_basic) ... ok
...

----------------------------------------------------------------------
Ran 10 tests in 17.497s

OK
========================================
All simple tests passed!
```

### Performance Benchmarks
- **Single Stock Analysis**: < 1 second (with caching)
- **Cache Hit Performance**: 50% faster than cache miss
- **Memory Usage**: < 100MB increase during analysis
- **Concurrent Analysis**: 2-3x faster than sequential

## Troubleshooting

### Common Issues

1. **Import Errors**: Some test files may have import issues due to class name changes
   - **Solution**: Use `test_simple.py` which uses only available classes

2. **Unicode Encoding Errors**: Windows may have issues with emoji characters
   - **Solution**: Test files have been updated to remove emoji characters

3. **API Rate Limiting**: Tests may be slow due to API rate limits
   - **Solution**: Use `ENABLE_FAKE_PROVIDERS=true` for faster testing

4. **Memory Issues**: Large test suites may consume significant memory
   - **Solution**: Run tests in smaller batches or use `--quick` mode

### Dependencies
```bash
pip install -r test_requirements.txt
```

Required packages:
- `pytest>=7.0.0`
- `pytest-cov>=4.0.0`
- `pytest-mock>=3.10.0`
- `psutil>=5.9.0`
- `unittest-mock>=1.0.1`

## Test Coverage

### Current Coverage
- **Core Functionality**: ✅ Fully tested
- **Data Validation**: ✅ Fully tested
- **Error Handling**: ✅ Fully tested
- **Performance**: ✅ Basic performance tests
- **Integration**: ✅ Basic integration tests
- **Unit Conversions**: ⚠️ Partial coverage

### Areas for Improvement
- More comprehensive unit conversion tests
- Additional edge case testing
- Stress testing with large datasets
- API mocking and simulation
- Memory leak detection
- Performance regression testing

## Contributing

### Adding New Tests
1. Follow the existing test structure
2. Use descriptive test names
3. Include both positive and negative test cases
4. Add performance assertions where appropriate
5. Update this README with new test categories

### Test Naming Convention
- `test_<component>_<behavior>` - e.g., `test_data_validator_edge_cases`
- `test_<component>_<scenario>` - e.g., `test_analyzer_error_handling`
- `test_<component>_<performance>` - e.g., `test_analyzer_performance_basic`

### Best Practices
- Use `setUp()` and `tearDown()` methods for test fixtures
- Mock external dependencies when possible
- Test both success and failure scenarios
- Include performance assertions for critical paths
- Use descriptive assertions with clear error messages
- Group related tests in the same test class

## License

This test suite is part of the Enhanced Integrated Analyzer project and follows the same license terms.
