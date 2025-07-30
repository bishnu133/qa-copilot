import asyncio
from pathlib import Path
from qa_copilot.executor import TestExecutor, ExecutorConfig


async def main():
    """Example of using Test Executor programmatically"""

    # Configure the executor
    config = ExecutorConfig(
        browser='chromium',
        headless=False,
        environment='dev',
        screenshot_on_failure=True,
        timeout=30000,
        retry_failed_steps=1
    )

    # Create executor instance
    executor = TestExecutor(config)

    # Example 1: Execute a single feature file
    print("Executing single feature file...")
    result = await executor.execute_feature('features/login.feature')

    print(f"\nFeature: {result['feature']}")
    print(f"Status: {result['status']}")
    print(f"Scenarios executed: {len(result['scenarios'])}")

    for scenario in result['scenarios']:
        print(f"\n  Scenario: {scenario['name']}")
        print(f"  Status: {scenario['status']}")
        if scenario['status'] == 'failed' and 'error' in scenario:
            print(f"  Error: {scenario['error']}")

    # Example 2: Execute all features in a directory
    print("\n\nExecuting all features in directory...")
    results = executor.execute_directory('features/')

    summary = results['summary']
    print(f"\nExecution Summary:")
    print(f"  Total Features: {summary['total']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Pass Rate: {(summary['passed'] / summary['total'] * 100):.1f}%")

    # Example 3: Custom step definitions
    print("\n\nAdding custom step definitions...")

    @executor.step_registry.given(r'I have a custom precondition')
    async def custom_precondition(context):
        # Custom implementation
        print("Executing custom precondition")
        await context.page.goto('https://example.com')

    @executor.step_registry.when(r'I perform a custom action with "([^"]*)"')
    async def custom_action(context, parameter):
        print(f"Performing custom action with: {parameter}")
        # Custom implementation

    @executor.step_registry.then(r'I verify custom result')
    async def verify_custom_result(context):
        print("Verifying custom result")
        # Custom verification
        assert context.page.url == 'https://example.com'

    # Execute with custom steps
    # result = await executor.execute_feature('features/custom.feature')


if __name__ == '__main__':
    asyncio.run(main())