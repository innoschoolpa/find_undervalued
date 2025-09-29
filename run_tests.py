#!/usr/bin/env python3
"""
Simple Test Runner for Enhanced Integrated Analyzer
==================================================

This script provides a simple way to run the comprehensive test suite
with different configurations and options.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run unit tests only
    python run_tests.py --performance      # Run performance tests only
    python run_tests.py --integration      # Run integration tests only
    python run_tests.py --conversions      # Run unit conversion tests only
    python run_tests.py --verbose          # Verbose output
    python run_tests.py --quick            # Quick test run (unit tests only)
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path

def run_command(cmd, description="Running command"):
    """Run a command and return success status"""
    print(f"{description}...")
    print(f"   Command: {' '.join(cmd)}")
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        end_time = time.time()
        
        if result.returncode == 0:
            print(f"{description} completed successfully ({end_time - start_time:.2f}s)")
            if result.stdout:
                print("   Output:", result.stdout.strip())
            return True
        else:
            print(f"{description} failed ({end_time - start_time:.2f}s)")
            if result.stderr:
                print("   Error:", result.stderr.strip())
            if result.stdout:
                print("   Output:", result.stdout.strip())
            return False
            
    except subprocess.TimeoutExpired:
        print(f"{description} timed out after 300 seconds")
        return False
    except Exception as e:
        print(f"{description} failed with exception: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are available"""
    print("Checking dependencies...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Python 3.8+ required")
        return False
    
    # Check if analyzer module exists
    if not os.path.exists("enhanced_integrated_analyzer_refactored.py"):
        print("enhanced_integrated_analyzer_refactored.py not found")
        return False
    
    # Check if test suite exists
    if not os.path.exists("test_comprehensive_suite.py"):
        print("test_comprehensive_suite.py not found")
        return False
    
    # Check if config exists
    if not os.path.exists("config.yaml"):
        print("config.yaml not found")
        return False
    
    print("All dependencies available")
    return True

def run_import_test():
    """Test if the analyzer can be imported"""
    print("Testing module import...")
    
    cmd = [sys.executable, "-c", "import enhanced_integrated_analyzer_refactored; print('Import successful')"]
    return run_command(cmd, "Module import test")

def run_smoke_test():
    """Run a quick smoke test"""
    print("Running smoke test...")
    
    cmd = [sys.executable, "-c", """
import enhanced_integrated_analyzer_refactored as eia
analyzer = eia.EnhancedIntegratedAnalyzer()
result = analyzer.analyze_single_stock('005930', 'Samsung')
print(f'Smoke test result: {result.status}')
"""]
    return run_command(cmd, "Smoke test")

def run_comprehensive_tests(args):
    """Run the comprehensive test suite"""
    print("Running comprehensive test suite...")
    
    cmd = [sys.executable, "test_comprehensive_suite.py"]
    
    if args.verbose:
        cmd.append("--verbose")
    if args.unit:
        cmd.append("--unit-conversions")
    if args.performance:
        cmd.append("--performance")
    if args.integration:
        cmd.append("--integration")
    if args.conversions:
        cmd.append("--unit-conversions")
    if args.max_workers:
        cmd.extend(["--max-workers", str(args.max_workers)])
    if args.timeout:
        cmd.extend(["--timeout", str(args.timeout)])
    
    return run_command(cmd, "Comprehensive test suite")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Simple Test Runner for Enhanced Integrated Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit             # Run unit tests only
  python run_tests.py --performance      # Run performance tests only
  python run_tests.py --integration      # Run integration tests only
  python run_tests.py --conversions      # Run unit conversion tests only
  python run_tests.py --verbose          # Verbose output
  python run_tests.py --quick            # Quick test run (unit tests only)
  python run_tests.py --smoke            # Smoke test only
  python run_tests.py --import           # Import test only
        """
    )
    
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--conversions", action="store_true", help="Run unit conversion tests only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quick", action="store_true", help="Quick test run (unit tests only)")
    parser.add_argument("--smoke", action="store_true", help="Smoke test only")
    parser.add_argument("--import", action="store_true", dest="import_test", help="Import test only")
    parser.add_argument("--max-workers", type=int, help="Maximum number of workers for parallel tests")
    parser.add_argument("--timeout", type=int, help="Timeout for individual tests (seconds)")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency checks")
    
    args = parser.parse_args()
    
    print("Enhanced Integrated Analyzer Test Runner")
    print("=" * 50)
    
    # Check dependencies unless skipped
    if not args.skip_deps:
        if not check_dependencies():
            print("Dependency check failed")
            sys.exit(1)
    
    # Run specific tests based on arguments
    success = True
    
    if args.import_test:
        success = run_import_test()
    elif args.smoke:
        success = run_smoke_test()
    elif args.quick:
        # Quick test run - just unit tests
        success = run_comprehensive_tests(args)
    else:
        # Full test run
        success = run_comprehensive_tests(args)
    
    # Print summary
    print("\n" + "=" * 50)
    if success:
        print("All tests completed successfully!")
        sys.exit(0)
    else:
        print("Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
