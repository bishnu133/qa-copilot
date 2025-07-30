class QACopilotError(Exception):
    """Base exception for QA Copilot"""
    pass


class ModuleError(QACopilotError):
    """Module-related errors"""
    pass


class ConfigurationError(QACopilotError):
    """Configuration-related errors"""
    pass


class ElementNotFoundError(QACopilotError):
    """Element not found during detection"""
    pass


class BDDGenerationError(QACopilotError):
    """Error generating BDD scenarios"""
    pass


class ExecutionError(QACopilotError):
    """Error during test execution"""
    pass


class AnalysisError(QACopilotError):
    """Error during failure analysis"""
    pass