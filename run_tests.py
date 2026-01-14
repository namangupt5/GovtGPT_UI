#!/usr/bin/env python3
"""
Test Runner Script
Provides convenient commands to run the GovGPT chatbot tests.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_behave(tags=None, features=None, allure=True, verbose=False, clean=True):
    """Run behave tests with proper Allure integration."""
    # Clean old allure results if requested (prevents stale data)
    if allure and clean:
        allure_results_dir = PROJECT_ROOT / "reports" / "allure-results"
        if allure_results_dir.exists():
            import shutil

            print(f"Cleaning old Allure results from {allure_results_dir}")
            shutil.rmtree(allure_results_dir)
        allure_results_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["behave"]

    if tags:
        cmd.extend(["--tags", tags])

    if features:
        cmd.append(features)

    if allure:
        cmd.extend(["-f", "allure_behave.formatter:AllureFormatter", "-o", "reports/allure-results"])
        # Also add pretty formatter for console output
        cmd.extend(["-f", "pretty"])

    if verbose:
        cmd.append("-v")

    # Disable capture to prevent issues with allure
    cmd.extend(["--no-capture"])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    # Auto-generate allure report after test run
    if allure:
        print("\n📊 Generating Allure HTML report...")
        run_allure_generate()

    return result


def run_allure_serve():
    """Serve Allure report."""
    cmd = ["allure", "serve", "reports/allure-results"]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=PROJECT_ROOT)


def run_allure_generate():
    """Generate static Allure report."""
    cmd = ["allure", "generate", "reports/allure-results", "-o", "reports/allure-report", "--clean"]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        report_path = PROJECT_ROOT / "reports" / "allure-report" / "index.html"
        print(f"✅ Report generated: {report_path}")
    return result


def run_allure_open():
    """Open the generated Allure HTML report in browser."""
    cmd = ["allure", "open", "reports/allure-report"]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=PROJECT_ROOT)


def verify_excel():
    """Verify Excel test data."""
    from utils.excel_reader import ExcelReader

    try:
        reader = ExcelReader()
        stats = reader.get_statistics()

        print("\n📊 Excel Test Data Statistics:")
        print(f"   Total Prompts: {stats['total_prompts']}")
        print(f"   High Risk: {stats['high_risk']}")
        print(f"   Medium Risk: {stats['medium_risk']}")
        print(f"   Low Risk: {stats['low_risk']}")
        print(f"   Multi-turn: {stats['multi_turn']}")

        print("\n✅ Excel data loaded successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Error loading Excel: {e}")
        return False


def verify_validators():
    """Verify AI validators can be loaded."""
    print("\n🔍 Verifying AI Validators...")

    validators = [
        ("SafetyValidator", "validators.safety_validator", "SafetyValidator"),
        ("RelevanceValidator", "validators.relevance_validator", "RelevanceValidator"),
        ("GrammarValidator", "validators.grammar_validator", "GrammarValidator"),
        ("SemanticValidator", "validators.semantic_validator", "SemanticValidator"),
    ]

    all_ok = True
    for name, module, cls_name in validators:
        try:
            mod = __import__(module, fromlist=[cls_name])
            validator_cls = getattr(mod, cls_name)
            validator = validator_cls()
            print(f"   ✅ {name} loaded")
        except Exception as e:
            print(f"   ❌ {name} failed: {e}")
            all_ok = False

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="GovGPT Test Runner")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run tests")
    run_parser.add_argument("--tags", "-t", help="Behave tags (e.g., @high-risk)")
    run_parser.add_argument("--feature", "-f", help="Specific feature file")
    run_parser.add_argument("--no-allure", action="store_true", help="Disable Allure")
    run_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # Shortcuts
    subparsers.add_parser("high-risk", help="Run high-risk tests only")
    subparsers.add_parser("medium-risk", help="Run medium-risk tests only")
    subparsers.add_parser("low-risk", help="Run low-risk tests only")
    subparsers.add_parser("security", help="Run security tests only")

    # Report commands
    subparsers.add_parser("report", help="Serve Allure report")
    subparsers.add_parser("report-gen", help="Generate static Allure report")
    subparsers.add_parser("report-open", help="Open Allure HTML report in browser")

    # Verify command
    subparsers.add_parser("verify", help="Verify setup")

    args = parser.parse_args()

    if args.command == "run":
        run_behave(tags=args.tags, features=args.feature, allure=not args.no_allure, verbose=args.verbose)
    elif args.command == "high-risk":
        run_behave(tags="@high-risk")
    elif args.command == "medium-risk":
        run_behave(tags="@medium-risk")
    elif args.command == "low-risk":
        run_behave(tags="@low-risk")
    elif args.command == "security":
        run_behave(tags="@security")
    elif args.command == "report":
        run_allure_serve()
    elif args.command == "report-gen":
        run_allure_generate()
    elif args.command == "report-open":
        run_allure_open()
    elif args.command == "verify":
        print("🔧 Verifying GovGPT Test Framework Setup...\n")
        excel_ok = verify_excel()
        validators_ok = verify_validators()

        if excel_ok and validators_ok:
            print("\n✅ All verifications passed!")
        else:
            print("\n⚠️ Some verifications failed. Check above for details.")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
