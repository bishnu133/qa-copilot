import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ExecutorDebugger:
    """Debug utilities for Test Executor"""

    @staticmethod
    def validate_environment():
        """Validate the executor environment"""
        issues = []

        # Check dependencies
        try:
            import playwright
        except ImportError:
            issues.append("Playwright not installed: pip install playwright")

        try:
            import behave
        except ImportError:
            issues.append("Behave not installed: pip install behave")

        try:
            import yaml
        except ImportError:
            issues.append("PyYAML not installed: pip install pyyaml")

        try:
            import jinja2
        except ImportError:
            issues.append("Jinja2 not installed: pip install jinja2")

        # Check directories
        required_dirs = ['features', 'screenshots', 'test-results', 'config/environments']
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                issues.append(f"Missing directory: {dir_path}")

        # Check playwright browsers
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=True)
                    browser.close()
                except Exception as e:
                    issues.append(f"Playwright browsers not installed: playwright install")
        except Exception as e:
            issues.append(f"Playwright issue: {e}")

        return issues

    @staticmethod
    def debug_step_execution(step_text: str, registry):
        """Debug why a step definition cannot be found"""
        print(f"\n🔍 Debugging step: '{step_text}'")

        # Extract keyword and text
        parts = step_text.split(maxsplit=1)
        keyword = parts[0] if parts else ""
        text = parts[1] if len(parts) > 1 else ""

        print(f"  Keyword: {keyword}")
        print(f"  Text: {text}")

        # Check all registered patterns
        print("\n  Checking patterns:")
        found_any = False

        for defn in registry.definitions:
            match = defn.pattern.search(text)
            if match:
                print(f"  ✓ MATCH: {defn.keyword} - {defn.pattern.pattern}")
                print(f"    Groups: {match.groups()}")
                found_any = True
            else:
                print(f"  ✗ No match: {defn.keyword} - {defn.pattern.pattern}")

        if not found_any:
            print("\n  ❌ No patterns matched!")
            print("  Suggestions:")
            print("  - Check the step text format")
            print("  - Ensure quotes are used for parameters")
            print("  - Verify the keyword (Given/When/Then) is correct")

        return found_any

    @staticmethod
    def validate_feature_file(feature_path: Path):
        """Validate a feature file"""
        from behave.parser import parse_feature

        try:
            with open(feature_path, 'r') as f:
                content = f.read()

            feature = parse_feature(content, filename=str(feature_path))

            print(f"\n📄 Feature: {feature.name}")
            print(f"   Scenarios: {len(feature.scenarios)}")

            # Check each scenario
            for scenario in feature.scenarios:
                print(f"\n   Scenario: {scenario.name}")
                print(f"   Steps: {len(scenario.steps)}")

                for step in scenario.steps:
                    print(f"     - {step.keyword} {step.name}")
                    if step.table:
                        print(f"       Table with {len(step.table.rows)} rows")

            return True

        except Exception as e:
            print(f"\n❌ Feature file validation failed: {e}")
            return False

    @staticmethod
    def generate_debug_report(results: Dict[str, Any]):
        """Generate a detailed debug report"""
        report = []
        report.append("=" * 60)
        report.append("TEST EXECUTOR DEBUG REPORT")
        report.append("=" * 60)

        # Summary
        summary = results.get('summary', {})
        report.append(f"\nSummary:")
        report.append(f"  Total Features: {summary.get('total', 0)}")
        report.append(f"  Passed: {summary.get('passed', 0)}")
        report.append(f"  Failed: {summary.get('failed', 0)}")

        # Detailed results
        for feature in results.get('features', []):
            report.append(f"\n\nFeature: {feature['feature']}")
            report.append(f"File: {feature['file']}")
            report.append(f"Status: {feature['status']}")

            for scenario in feature.get('scenarios', []):
                report.append(f"\n  Scenario: {scenario['name']}")
                report.append(f"  Status: {scenario['status']}")

                if scenario.get('error'):
                    report.append(f"  Error: {scenario['error']}")

                # Failed steps details
                failed_steps = [s for s in scenario.get('steps', []) if s['status'] == 'failed']
                if failed_steps:
                    report.append("\n  Failed Steps:")
                    for step in failed_steps:
                        report.append(f"    - {step['keyword']} {step['name']}")
                        report.append(f"      Error: {step.get('error', 'Unknown error')}")

        return "\n".join(report)