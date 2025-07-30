"""
QA Copilot - Modular AI-powered QA automation tool
"""

__version__ = "0.1.0"
__author__ = "QA Copilot Contributors"

# Import core components
from .core import QAModule, ModuleInfo, ExecutionResult, ConfigManager

# Module imports will be dynamic based on what's installed
_modules = {}

try:
    from .detector import ElementDetector
    _modules['detector'] = ElementDetector
except ImportError:
    pass

try:
    from .bdd import BDDGenerator
    _modules['bdd'] = BDDGenerator
except ImportError:
    pass

try:
    from .executor import TestExecutor
    _modules['executor'] = TestExecutor
except ImportError:
    pass

try:
    from .analyzer import FailureAnalyzer
    _modules['analyzer'] = FailureAnalyzer
except ImportError:
    pass

try:
    from .datagen import TestDataGenerator
    _modules['datagen'] = TestDataGenerator
except ImportError:
    pass

try:
    from .reporter import ReportGenerator
    _modules['reporter'] = ReportGenerator
except ImportError:
    pass


def get_available_modules():
    """Get list of available modules"""
    return list(_modules.keys())


def load_module(module_name: str, config=None):
    """Dynamically load a module"""
    if module_name not in _modules:
        raise ImportError(f"Module '{module_name}' not installed")
    return _modules[module_name](config)


__all__ = [
    "QAModule",
    "ModuleInfo",
    "ExecutionResult",
    "ConfigManager",
    "get_available_modules",
    "load_module",
]