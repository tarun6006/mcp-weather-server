#!/usr/bin/env python3
"""
Test runner script for Weather MCP Server with coverage reporting
Enforces 90% code coverage requirement
"""
import subprocess
import sys
import os
import json
from datetime import datetime

def main():
    """Run tests with coverage for Weather MCP Server"""
    print("🧪 Weather MCP Server - Test Suite with Coverage")
    print("Running black box tests with 90% coverage requirement")
    print("="*60)
    
    try:
        # Run pytest with coverage (using configuration from pytest.ini)
        result = subprocess.run([
            sys.executable, "-m", "pytest"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        # Try to read coverage report
        coverage_data = None
        if os.path.exists("coverage.json"):
            try:
                with open("coverage.json", 'r') as f:
                    coverage_data = json.load(f)
                    coverage_percent = coverage_data.get('totals', {}).get('percent_covered', 0)
                    print(f"📊 Coverage: {coverage_percent:.2f}%")
                    
                    # Create summary report
                    summary_report = {
                        "timestamp": datetime.now().isoformat(),
                        "application": "Weather MCP Server",
                        "tests_passed": result.returncode == 0,
                        "coverage_percentage": coverage_percent,
                        "coverage_meets_threshold": coverage_percent >= 90,
                        "coverage_data": coverage_data
                    }
                    
                    # Save summary
                    with open("test_summary.json", "w") as f:
                        json.dump(summary_report, f, indent=2)
                    
            except Exception as e:
                print(f"⚠️  Could not read coverage report: {e}")
        
        if result.returncode == 0:
            print("✅ Weather MCP Server tests passed with sufficient coverage!")
            sys.exit(0)
        else:
            print("❌ Weather MCP Server tests failed or coverage below 90%!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

