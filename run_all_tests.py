#!/usr/bin/env python3
"""
Run All Terraform LSP Benchmarks

This script executes the complete test suite for Terraform LSP benchmarking.
"""

import sys
import os
import json
import time
from pathlib import Path

def run_test(test_file, test_name):
    """Run a single test and capture results"""
    print(f"\n🚀 Running {test_name}")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Import and run the test
        if "ab_tests" in test_file:
            sys.path.insert(0, "ab_tests")
        elif "token_benchmarks" in test_file:
            sys.path.insert(0, "token_benchmarks")
        
        # Execute the test file
        result = os.system(f"cd /Users/yen/fork_repo/serena/terraform_lsp_benchmarks && python {test_file}")
        
        execution_time = time.time() - start_time
        success = result == 0
        
        print(f"\n✅ {test_name} {'completed' if success else 'failed'} in {execution_time:.1f}s")
        
        return {
            "test": test_name,
            "file": test_file,
            "success": success,
            "execution_time": execution_time
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"\n❌ {test_name} failed: {e}")
        
        return {
            "test": test_name,
            "file": test_file,
            "success": False,
            "execution_time": execution_time,
            "error": str(e)
        }

def main():
    """Run all benchmarks"""
    print("🎯 Terraform LSP Benchmarks - Complete Test Suite")
    print("=" * 80)
    
    # Test suite configuration
    tests = [
        ("ab_tests/semantic_quality_test.py", "Semantic Quality Test"),
        ("ab_tests/error_detection_test.py", "Error Detection Test"),
        ("token_benchmarks/token_benchmark_terraform.py", "Token Usage Benchmark"),
        ("ab_tests/comprehensive_ab_test.py", "Comprehensive A/B Test")
    ]
    
    results = []
    total_start_time = time.time()
    
    # Run each test
    for test_file, test_name in tests:
        result = run_test(test_file, test_name)
        results.append(result)
    
    total_execution_time = time.time() - total_start_time
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUITE SUMMARY")
    print("=" * 80)
    
    successful_tests = sum(1 for r in results if r['success'])
    total_tests = len(results)
    
    print(f"Total tests run: {total_tests}")
    print(f"Successful tests: {successful_tests}")
    print(f"Failed tests: {total_tests - successful_tests}")
    print(f"Success rate: {(successful_tests / total_tests) * 100:.1f}%")
    print(f"Total execution time: {total_execution_time:.1f}s")
    
    # Detailed results
    print(f"\n📋 DETAILED RESULTS")
    print("-" * 60)
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{result['test']:<30} {status} ({result['execution_time']:.1f}s)")
    
    # Save summary
    summary = {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": (successful_tests / total_tests) * 100,
        "total_execution_time": total_execution_time,
        "test_results": results,
        "timestamp": time.time()
    }
    
    os.makedirs("results", exist_ok=True)
    with open("results/test_suite_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 Summary saved to: results/test_suite_summary.json")
    
    if successful_tests == total_tests:
        print("\n🎉 All tests completed successfully!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - successful_tests} test(s) failed. Check individual results for details.")
        return 1

if __name__ == "__main__":
    exit(main())