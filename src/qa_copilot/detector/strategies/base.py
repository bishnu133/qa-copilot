from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from playwright.sync_api import Page as SyncPage, Locator as SyncLocator
from playwright.async_api import Page as AsyncPage, Locator as AsyncLocator


class DetectionStrategy(ABC):
    """Base class for element detection strategies with both sync and async support"""

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

    @abstractmethod
    def find(self, page: SyncPage, description: Dict[str, Any]) -> Optional[SyncLocator]:
        """
        Find a single element matching the description (synchronous).

        Args:
            page: Playwright sync page object
            description: Parsed element description

        Returns:
            Locator if found, None otherwise
        """
        pass

    async def find_async(self, page: AsyncPage, description: Dict[str, Any]) -> Optional[AsyncLocator]:
        """
        Find a single element matching the description (asynchronous).

        Default implementation raises NotImplementedError.
        Override in subclasses to provide async support.

        Args:
            page: Playwright async page object
            description: Parsed element description

        Returns:
            Locator if found, None otherwise
        """
        raise NotImplementedError(f"{self.name} strategy does not implement async support")

    def find_all(self, page: SyncPage, description: Dict[str, Any]) -> List[SyncLocator]:
        """
        Find all elements matching the description (synchronous).

        Default implementation just wraps find().
        Override for better performance.
        """
        element = self.find(page, description)
        return [element] if element else []

    async def find_all_async(self, page: AsyncPage, description: Dict[str, Any]) -> List[AsyncLocator]:
        """
        Find all elements matching the description (asynchronous).

        Default implementation just wraps find_async().
        Override for better performance.
        """
        element = await self.find_async(page, description)
        return [element] if element else []

    def supports(self, description: Dict[str, Any]) -> bool:
        """Check if this strategy can handle the description"""
        return True

    def supports_async(self) -> bool:
        """Check if this strategy supports async operations"""
        # Check if find_async is overridden
        return self.find_async is not DetectionStrategy.find_async