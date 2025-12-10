#!/usr/bin/env python3
"""
Integration Test Runner with Detailed Reporting

Runs comprehensive integration tests for the pattern-based extraction system
and generates a detailed summary report.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
import subprocess

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(message):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_section(message):
    """Print a formatted section header."""
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'-' * len(message)}{Colors.ENDC}")


def print_success(message):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_warning(message):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def print_info(message):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def run_tests():
    """Run integration tests with pytest."""
    print_header("EPUB RECIPE PARSER - INTEGRATION TEST SUITE")

    print_info(f"Test execution started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Python version: {sys.version.split()[0]}")
    print()

    # Check if test EPUB exists
    test_epub = Path("/Users/csrdsg/projects/open_fire_cooking/books/101 Things to Do with a Smoker (Eliza Cross) (Z-Library).epub")
    if not test_epub.exists():
        print_error(f"Test EPUB not found: {test_epub}")
        print_warning("Please ensure the test EPUB file exists before running integration tests")
        return False

    print_success(f"Test EPUB found: {test_epub.name}")

    # Run pytest with verbose output and coverage
    test_file = Path(__file__).parent / "tests" / "integration" / "test_integration.py"

    if not test_file.exists():
        print_error(f"Test file not found: {test_file}")
        return False

    print_success(f"Test file found: {test_file.name}")
    print()

    print_section("Running Integration Tests")

    # Prepare pytest command
    pytest_cmd = [
        "pytest",
        str(test_file),
        "-v",  # Verbose
        "-s",  # Show print statements
        "--tb=short",  # Short traceback format
        "--color=yes",  # Colored output
        "-W", "ignore::DeprecationWarning",  # Ignore deprecation warnings
    ]

    print_info(f"Command: {' '.join(pytest_cmd)}")
    print()

    # Run tests and capture output
    start_time = time.time()

    try:
        result = subprocess.run(
            pytest_cmd,
            cwd=Path(__file__).parent,
            capture_output=False,  # Show output in real-time
            text=True
        )

        elapsed_time = time.time() - start_time

        print()
        print_section("Test Execution Summary")

        if result.returncode == 0:
            print_success("All tests passed!")
            print_success(f"Execution time: {elapsed_time:.2f} seconds")
            return True
        else:
            print_error(f"Some tests failed (exit code: {result.returncode})")
            print_info(f"Execution time: {elapsed_time:.2f} seconds")
            return False

    except FileNotFoundError:
        print_error("pytest not found. Please install it:")
        print_info("  pip install pytest")
        return False
    except Exception as e:
        print_error(f"Error running tests: {e}")
        return False


def print_test_coverage_summary():
    """Print summary of test coverage areas."""
    print_section("Integration Test Coverage")

    coverage_areas = [
        ("End-to-End Extraction", [
            "Full EPUB extraction pipeline",
            "Pattern-based confidence scoring",
            "Quality threshold filtering",
            "Recipe structure validation"
        ]),
        ("A/B Comparison Testing", [
            "Legacy vs pattern method agreement",
            "Confidence metrics validation",
            "Disagreement analysis"
        ]),
        ("Database Integration", [
            "Save/load with metadata preservation",
            "A/B test statistics aggregation",
            "Quality score filtering",
            "Metadata round-trip integrity"
        ]),
        ("Export Functionality", [
            "JSON export with confidence scores",
            "Markdown export readability",
            "Metadata inclusion in exports"
        ]),
        ("Quality Validation", [
            "Confidence-quality correlation",
            "Average confidence reasonableness",
            "High-quality recipe accuracy"
        ]),
        ("Pattern Detector Methods", [
            "Ingredient pattern detection",
            "Instruction pattern detection",
            "Metadata pattern extraction"
        ])
    ]

    for area, tests in coverage_areas:
        print(f"\n{Colors.BOLD}{area}:{Colors.ENDC}")
        for test in tests:
            print(f"  {Colors.OKGREEN}✓{Colors.ENDC} {test}")


def print_usage_guide():
    """Print guide for using the integration tests."""
    print_section("Usage Guide")

    print(f"{Colors.BOLD}Running specific test classes:{Colors.ENDC}")
    print("  pytest tests/integration/test_integration.py::TestEndToEndExtraction -v")
    print()

    print(f"{Colors.BOLD}Running specific test methods:{Colors.ENDC}")
    print("  pytest tests/integration/test_integration.py::TestEndToEndExtraction::test_full_extraction_pipeline -v")
    print()

    print(f"{Colors.BOLD}Running with different verbosity:{Colors.ENDC}")
    print("  pytest tests/integration/test_integration.py -vv  # Extra verbose")
    print("  pytest tests/integration/test_integration.py -q   # Quiet mode")
    print()

    print(f"{Colors.BOLD}Running with coverage report:{Colors.ENDC}")
    print("  pytest tests/integration/test_integration.py --cov=epub_recipe_parser --cov-report=html")
    print()


def main():
    """Main test runner."""
    # Check for help flag
    if "--help" in sys.argv or "-h" in sys.argv:
        print_header("Integration Test Runner - Help")
        print_usage_guide()
        print_test_coverage_summary()
        return

    # Check for coverage flag
    show_coverage = "--coverage" in sys.argv or "-c" in sys.argv

    if show_coverage:
        print_test_coverage_summary()
        print()
        return

    # Run the tests
    success = run_tests()

    # Print additional information
    print()
    print_test_coverage_summary()

    print()
    print_section("Next Steps")

    if success:
        print_success("Integration tests completed successfully!")
        print()
        print_info("You can now:")
        print("  1. Review test output above for detailed results")
        print("  2. Check confidence scores and agreement rates")
        print("  3. Run specific test classes for focused testing")
        print("  4. Generate coverage reports for detailed analysis")
    else:
        print_warning("Some tests failed. Please review the output above.")
        print()
        print_info("Debugging tips:")
        print("  1. Check test output for specific failure messages")
        print("  2. Run failing tests individually with -v flag")
        print("  3. Verify test EPUB file exists and is accessible")
        print("  4. Check that all dependencies are installed")

    print()
    print_usage_guide()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
