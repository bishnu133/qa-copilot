from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime


class ModuleStatus(Enum):
    """Status of a QA module"""
    NOT_INITIALIZED = "not_initialized"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ModuleInfo:
    """Information about a QA module"""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str]
    optional_dependencies: List[str]
    has_ai: bool = False


@dataclass
class ExecutionResult:
    """Standard result format for all modules"""
    success: bool
    data: Any
    error: Optional[str] = None
    timestamp: datetime = None
    duration: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class QAModule(ABC):
    """Base class for all QA Copilot modules"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._status = ModuleStatus.NOT_INITIALIZED
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize the module"""
        pass

    @abstractmethod
    def execute(self, input_data: Any) -> ExecutionResult:
        """Execute the module's main functionality"""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate module configuration and dependencies"""
        pass

    @abstractmethod
    def get_info(self) -> ModuleInfo:
        """Get module information"""
        pass

    @property
    def status(self) -> ModuleStatus:
        """Get current module status"""
        return self._status

    @status.setter
    def status(self, value: ModuleStatus) -> None:
        """Set module status"""
        self.logger.info(f"Status changed from {self._status} to {value}")
        self._status = value

    def is_ready(self) -> bool:
        """Check if module is ready to execute"""
        return self._status == ModuleStatus.READY

    def cleanup(self) -> None:
        """Cleanup resources"""
        self.logger.info("Cleaning up module resources")


class Strategy(ABC):
    """Base class for strategies used within modules"""

    @abstractmethod
    def apply(self, *args, **kwargs) -> Any:
        """Apply the strategy"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name"""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Strategy priority (lower = higher priority)"""
        pass


class ConfigurableModule(QAModule):
    """Base class for modules with configuration management"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._default_config = self._get_default_config()
        config = {**self._default_config, **(config or {})}
        super().__init__(config)

    @abstractmethod
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        pass

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration"""
        self.config.update(updates)
        self.logger.info(f"Configuration updated: {updates}")
        self._on_config_update()

    def _on_config_update(self) -> None:
        """Called when configuration is updated"""
        pass

    def reset_config(self) -> None:
        """Reset to default configuration"""
        self.config = self._default_config.copy()
        self.logger.info("Configuration reset to defaults")