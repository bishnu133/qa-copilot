from .executor import TestExecutor, ExecutorConfig
from .step_definitions import StepDefinitionRegistry, given, when, then
from .test_context import TestContext
from .report_collector import ReportCollector

__all__ = [
    'TestExecutor',
    'ExecutorConfig',
    'StepDefinitionRegistry',
    'TestContext',
    'ReportCollector',
    'given',
    'when',
    'then'
]

# Module metadata
__version__ = '0.1.0'
__author__ = 'QA-Copilot Team'
__description__ = 'Test Executor Module - Execute BDD feature files with Playwright'