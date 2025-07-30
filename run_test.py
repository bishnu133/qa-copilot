# run_test.py - Updated version
"""
Script to run the feature file with NLP parser
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qa_copilot.executor.executor import TestExecutor, ExecutorConfig
from qa_copilot.detector.detector import ElementDetector


async def main():
    # Configuration - use dict instead of ExecutorConfig for custom params
    config = {
        "browser": "chromium",
        "headless": False,
        "screenshot_on_failure": True,
        "environment": "dev",
        "config_path": "config/environments/dev.yaml",
        "use_nlp_parser": True,  # Custom parameter
        "timeout": 30000,
        "viewport": {"width": 1280, "height": 720},
        "video_recording": False,
        "parallel_workers": 1,
        "retry_failed_steps": 1,
        "slow_mo": 2000,
        "devtools": False
    }

    # Initialize executor with dict config
    executor = TestExecutor(config)

    # Path to your feature file
    feature_file = "features/create_challenge.feature"

    print(f"Running feature: {feature_file}")

    try:
        # Execute the feature
        result = await executor.execute_feature(feature_file)

        # Print summary
        print("\n" + "=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Feature: {result['feature']}")
        print(f"Status: {result['status']}")

        for scenario in result['scenarios']:
            print(f"\nScenario: {scenario['name']}")
            print(f"  Status: {scenario['status']}")

            if scenario['status'] == 'failed':
                print(f"  Error: {scenario.get('error', 'Unknown error')}")

                # Show failed steps
                failed_steps = [s for s in scenario['steps'] if s['status'] == 'failed']
                if failed_steps:
                    print("  Failed steps:")
                    for step in failed_steps:
                        print(f"    - {step['keyword']} {step['name']}")
                        print(f"      Error: {step.get('error', 'Unknown error')}")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())