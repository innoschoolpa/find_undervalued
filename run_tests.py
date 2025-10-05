#!/usr/bin/env python3
"""
리팩토링된 분석 시스템 테스트 실행 스크립트

모든 테스트를 실행하고 결과를 리포트합니다.
"""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime
from pathlib import Path


def run_command(command, capture_output=True):
    """명령어 실행"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=True
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout, e.stderr


def run_unit_tests(test_path="tests", verbose=False):
    """단위 테스트 실행"""
    print("[TEST] 단위 테스트 실행 중...")
    
    # pytest 명령어 구성
    cmd = f"python -m pytest {test_path}"
    if verbose:
        cmd += " -v"
    cmd += " --tb=short --cov=. --cov-report=html --cov-report=term"
    
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        print("[PASS] 단위 테스트 통과")
        return True
    else:
        print("[FAIL] 단위 테스트 실패")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return False


def run_integration_tests(test_path="tests/test_integration.py", verbose=False):
    """통합 테스트 실행"""
    print("[TEST] 통합 테스트 실행 중...")
    
    cmd = f"python -m pytest {test_path}"
    if verbose:
        cmd += " -v"
    cmd += " --tb=short"
    
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        print("[PASS] 통합 테스트 통과")
        return True
    else:
        print("[FAIL] 통합 테스트 실패")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return False


def run_linting():
    """코드 린팅 실행"""
    print("[TEST] 코드 린팅 실행 중...")
    
    # flake8 린팅
    cmd = "python -m flake8 . --exclude=venv,env,.git,__pycache__,.pytest_cache --max-line-length=120"
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        print("[PASS] 린팅 통과")
        return True
    else:
        print("[FAIL] 린팅 실패")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return False


def run_type_checking():
    """타입 체킹 실행"""
    print("[TEST] 타입 체킹 실행 중...")
    
    # mypy 타입 체킹
    cmd = "python -m mypy . --ignore-missing-imports --exclude=venv --exclude=env"
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        print("[PASS] 타입 체킹 통과")
        return True
    else:
        print("[FAIL] 타입 체킹 실패")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return False


def run_format_check():
    """코드 포맷 체크 실행"""
    print("[TEST] 코드 포맷 체크 실행 중...")
    
    # black 포맷 체크
    cmd = "python -m black --check ."
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        print("[PASS] 코드 포맷 체크 통과")
        return True
    else:
        print("[FAIL] 코드 포맷 체크 실패")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return False


def generate_test_report(results, output_file="test_report.json"):
    """테스트 리포트 생성"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "summary": {
            "total_tests": len(results),
            "passed": sum(1 for r in results.values() if r),
            "failed": sum(1 for r in results.values() if not r)
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"[REPORT] 테스트 리포트 생성: {output_file}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="리팩토링된 분석 시스템 테스트 실행")
    parser.add_argument("--unit", action="store_true", help="단위 테스트만 실행")
    parser.add_argument("--integration", action="store_true", help="통합 테스트만 실행")
    parser.add_argument("--lint", action="store_true", help="린팅만 실행")
    parser.add_argument("--type-check", action="store_true", help="타입 체킹만 실행")
    parser.add_argument("--format-check", action="store_true", help="포맷 체크만 실행")
    parser.add_argument("--all", action="store_true", help="모든 테스트 실행")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 출력")
    parser.add_argument("--report", "-r", help="리포트 파일 경로")
    
    args = parser.parse_args()
    
    # 기본값: 모든 테스트 실행
    if not any([args.unit, args.integration, args.lint, args.type_check, args.format_check]):
        args.all = True
    
    results = {}
    
    try:
        if args.unit or args.all:
            results["unit_tests"] = run_unit_tests(verbose=args.verbose)
        
        if args.integration or args.all:
            results["integration_tests"] = run_integration_tests(verbose=args.verbose)
        
        if args.lint or args.all:
            results["linting"] = run_linting()
        
        if args.type_check or args.all:
            results["type_checking"] = run_type_checking()
        
        if args.format_check or args.all:
            results["format_check"] = run_format_check()
        
        # 리포트 생성
        if args.report:
            generate_test_report(results, args.report)
        elif args.all:
            generate_test_report(results)
        
        # 결과 요약
        print("\n" + "="*50)
        print("[SUMMARY] 테스트 결과 요약")
        print("="*50)
        
        for test_name, passed in results.items():
            status = "[PASS] 통과" if passed else "[FAIL] 실패"
            print(f"{test_name}: {status}")
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r)
        failed_tests = total_tests - passed_tests
        
        print(f"\n총 {total_tests}개 테스트 중 {passed_tests}개 통과, {failed_tests}개 실패")
        
        if failed_tests > 0:
            print("\n[FAIL] 일부 테스트가 실패했습니다. 로그를 확인해 주세요.")
            sys.exit(1)
        else:
            print("\n[SUCCESS] 모든 테스트가 통과했습니다!")
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n[STOP] 테스트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 테스트 실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()