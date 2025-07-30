# detector.py - Updated version with proper async support
import time
from typing import Any, Dict, List, Optional, Union
from playwright.sync_api import Page as SyncPage, Locator as SyncLocator
from playwright.async_api import Page as AsyncPage, Locator as AsyncLocator
import logging

try:
    from ..core import (
        ConfigurableModule,
        ModuleInfo,
        ExecutionResult,
        ModuleStatus,
        ElementNotFoundError,
    )
except ImportError:
    # Fallback for when core module is not available
    from dataclasses import dataclass


    class ConfigurableModule:
        def __init__(self, config=None):
            self.config = config or {}
            self.logger = logging.getLogger(self.__class__.__name__)
            self._initialize()

        def _initialize(self):
            pass


    @dataclass
    class ModuleInfo:
        name: str
        version: str
        description: str
        author: str
        dependencies: list
        optional_dependencies: list
        has_ai: bool


    @dataclass
    class ExecutionResult:
        success: bool
        data: Any
        error: Optional[str] = None
        metadata: Optional[Dict] = None


    class ModuleStatus:
        READY = "ready"
        ERROR = "error"


    class ElementNotFoundError(Exception):
        pass

from .strategies import get_default_strategies
from .utils import parse_element_description, normalize_text

logger = logging.getLogger(__name__)


class ElementDetector(ConfigurableModule):
    """
    Detects UI elements using natural language descriptions.
    Supports both synchronous and asynchronous operations.

    Example:
        detector = ElementDetector()
        # Sync
        element = detector.find(page, "Click on the blue Login button")
        # Async
        element = await detector.find_async(page, "Click on the blue Login button")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.strategies = []  # Initialize empty list first
        self.strategies_dict = {}  # Strategy instances by name
        self._cache = {}  # Cache for found elements
        self.parser = self  # Add parser reference
        super().__init__(config)

    def _initialize(self) -> None:
        """Initialize the detector module"""
        self.logger.info("Initializing Element Detector")
        try:
            self.strategies = self._load_strategies()
            if self.validate():
                self.status = ModuleStatus.READY
            else:
                self.status = ModuleStatus.ERROR
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            self.status = ModuleStatus.ERROR

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "strategies": ["dom", "heuristic"],  # Default strategies
            "enable_ocr": False,
            "enable_ml": False,
            "timeout": 30,
            "retry_count": 3,
            "cache_elements": True,
            "fuzzy_match_threshold": 0.8,
            "wait_before_retry": 1,
        }

    def _load_strategies(self) -> List[Any]:
        """Load detection strategies based on configuration"""
        strategy_names = self.config.get("strategies", ["dom", "heuristic"])
        strategies = []

        available_strategies = get_default_strategies()

        for name in strategy_names:
            if name in available_strategies:
                strategy_class = available_strategies[name]
                strategy_instance = strategy_class()
                strategies.append(strategy_instance)
                self.strategies_dict[name] = strategy_instance
                self.logger.info(f"Loaded strategy: {name}")
            else:
                self.logger.warning(f"Unknown strategy: {name}")

        # Sort by priority
        strategies.sort(key=lambda s: s.priority)
        return strategies

    def execute(self, input_data: Any) -> ExecutionResult:
        """Execute element detection"""
        if not isinstance(input_data, dict):
            return ExecutionResult(
                success=False,
                data=None,
                error="Input must be a dictionary with 'page' and 'description'"
            )

        page = input_data.get("page")
        description = input_data.get("description")

        if not page or not description:
            return ExecutionResult(
                success=False,
                data=None,
                error="Missing required fields: 'page' and 'description'"
            )

        try:
            element = self.find(page, description)
            return ExecutionResult(
                success=True,
                data=element,
                metadata={"description": description}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                data=None,
                error=str(e)
            )

    def find(self, page: SyncPage, description: str) -> SyncLocator:
        """
        Find an element using natural language description (synchronous).

        Args:
            page: Playwright page object
            description: Natural language description of element

        Returns:
            Locator for the found element

        Raises:
            ElementNotFoundError: If element cannot be found
        """
        start_time = time.time()

        # Check cache first
        cache_key = f"{page.url}:{description}"
        if self.config.get("cache_elements") and cache_key in self._cache:
            self.logger.info(f"Found element in cache: {description}")
            return self._cache[cache_key]

        # Parse the description
        parsed = parse_element_description(description)
        self.logger.info(f"Parsed description: {parsed}")

        # Try each strategy
        for attempt in range(self.config.get("retry_count", 3)):
            for strategy in self.strategies:
                try:
                    self.logger.debug(f"Trying strategy: {strategy.name}")
                    element = strategy.find(page, parsed)

                    if element:
                        # Verify element is visible and enabled
                        if element.is_visible() and element.is_enabled():
                            self.logger.info(
                                f"Found element using {strategy.name} strategy "
                                f"in {time.time() - start_time:.2f}s"
                            )

                            # Cache the result
                            if self.config.get("cache_elements"):
                                self._cache[cache_key] = element

                            return element
                        else:
                            self.logger.debug("Element found but not visible/enabled")

                except Exception as e:
                    self.logger.debug(f"Strategy {strategy.name} failed: {e}")

            # Wait before retry
            if attempt < self.config.get("retry_count", 3) - 1:
                wait_time = self.config.get("wait_before_retry", 1)
                self.logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)

        # All strategies failed
        raise ElementNotFoundError(
            f"Could not find element: {description}\n"
            f"Tried strategies: {[s.name for s in self.strategies]}"
        )

    async def find_async(self, page: AsyncPage, description: str, timeout: int = 30000) -> AsyncLocator:
        """
        Async version of find method for Playwright async API

        Args:
            page: Playwright async page instance
            description: Natural language description of the element
            timeout: Maximum time to wait for element (ms)

        Returns:
            Playwright Locator object
        """
        import asyncio

        start_time = time.time()

        # Parse the description
        parsed = parse_element_description(description)
        logger.info(f"Parsed description: {parsed}")

        # Try each strategy
        for attempt in range(self.config.get("retry_count", 3)):
            for strategy in self.strategies:
                try:
                    # Check if strategy supports async
                    if hasattr(strategy, 'find_async'):
                        self.logger.debug(f"Trying async strategy: {strategy.name}")
                        element = await strategy.find_async(page, parsed)

                        if element:
                            # Verify element is visible and enabled
                            if await element.is_visible() and await element.is_enabled():
                                self.logger.info(
                                    f"Found element using {strategy.name} async strategy "
                                    f"in {time.time() - start_time:.2f}s"
                                )
                                return element
                            else:
                                self.logger.debug("Element found but not visible/enabled")
                    else:
                        self.logger.debug(f"Strategy {strategy.name} does not support async")

                except Exception as e:
                    self.logger.debug(f"Async strategy {strategy.name} failed: {e}")

            # Wait before retry
            if attempt < self.config.get("retry_count", 3) - 1:
                wait_time = self.config.get("wait_before_retry", 1)
                self.logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        # If all async strategies fail, try fallback approach
        return await self._fallback_find_async(page, description, parsed, timeout)

    async def _fallback_find_async(self, page: AsyncPage, description: str,
                                   parsed: Dict[str, Any], timeout: int) -> AsyncLocator:
        """Fallback method when strategies don't work"""
        target_text = parsed.get('target', '')
        element_type = parsed.get('element_type', '')

        # Check if this might be a rich text editor field
        is_rich_text_field = any(keyword in description.lower() for keyword in [
            'about', 'description', 'content', 'editor', 'rich text', 'message', 'details'
        ])

        # Try common locator patterns
        locators_to_try = []

        if is_rich_text_field or element_type == 'input':
            # For rich text editors, prioritize contenteditable elements
            locators_to_try.extend([
                # Quill editor
                page.locator('.ql-editor').first,
                page.locator('[contenteditable="true"]').first,
                # Label-based search for rich text
                page.locator(f'label:has-text("{target_text}") + div .ql-editor'),
                page.locator(f'label:has-text("{target_text}") ~ div .ql-editor'),
                page.locator(f'div:has(label:has-text("{target_text}")) .ql-editor'),
                # Standard inputs
                page.get_by_placeholder(target_text),
                page.get_by_label(target_text),
                page.locator(f"input[placeholder*='{target_text}' i]"),
            ])
        elif element_type == 'button':
            locators_to_try.extend([
                page.get_by_role("button", name=target_text),
                page.get_by_text(target_text).filter(has=page.locator("button")),
                page.locator(f"button:has-text('{target_text}')"),
                page.locator(f".ant-btn:has-text('{target_text}')"),
            ])
        elif element_type == 'link':
            locators_to_try.extend([
                page.get_by_role("link", name=target_text),
                page.get_by_text(target_text).filter(has=page.locator("a")),
                page.locator(f"a:has-text('{target_text}')"),
            ])
        else:
            # Generic text search
            locators_to_try.extend([
                page.get_by_text(target_text),
                page.locator(f"*:has-text('{target_text}')"),
            ])

        # Also try exact text match
        if target_text:
            locators_to_try.append(page.locator(f'*:text-is("{target_text}")'))

        # Try each locator
        for locator in locators_to_try:
            try:
                count = await locator.count()
                if count > 0:
                    # Use first match
                    first = locator.first
                    if await first.is_visible():
                        logger.info(f"Found element using fallback selector: {target_text}")
                        return first
            except Exception as e:
                logger.debug(f"Fallback locator failed: {e}")
                continue

        # If all fail, raise exception
        raise ElementNotFoundError(f"Could not find element: {description}")

    def parse(self, description: str) -> Dict[str, Any]:
        """Parse natural language description"""
        return parse_element_description(description)

    def find_all(self, page: SyncPage, description: str) -> List[SyncLocator]:
        """Find all elements matching the description (synchronous)"""
        parsed = parse_element_description(description)
        elements = []

        for strategy in self.strategies:
            try:
                found = strategy.find_all(page, parsed)
                if found:
                    elements.extend(found)
            except Exception as e:
                self.logger.debug(f"Strategy {strategy.name} failed: {e}")

        return list(set(elements))  # Remove duplicates

    async def find_all_async(self, page: AsyncPage, description: str) -> List[AsyncLocator]:
        """Find all elements matching the description (asynchronous)"""
        parsed = parse_element_description(description)
        elements = []

        for strategy in self.strategies:
            try:
                if hasattr(strategy, 'find_all_async'):
                    found = await strategy.find_all_async(page, parsed)
                    if found:
                        elements.extend(found)
            except Exception as e:
                self.logger.debug(f"Strategy {strategy.name} failed: {e}")

        return list(set(elements))  # Remove duplicates

    def validate(self) -> bool:
        """Validate module configuration"""
        try:
            # Check if strategies are loaded
            if not self.strategies:
                self.logger.error("No strategies loaded")
                return False

            # Validate each strategy
            for strategy in self.strategies:
                if not hasattr(strategy, 'find'):
                    self.logger.error(f"Strategy {strategy.name} missing 'find' method")
                    return False

            return True
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False

    def get_info(self) -> ModuleInfo:
        """Get module information"""
        return ModuleInfo(
            name="Element Detector",
            version="0.2.0",
            description="Detects UI elements using natural language descriptions with async support",
            author="QA Copilot Contributors",
            dependencies=["playwright", "beautifulsoup4"],
            optional_dependencies=["easyocr", "transformers"],
            has_ai=self.config.get("enable_ml", False)
        )

    def clear_cache(self) -> None:
        """Clear element cache"""
        self._cache.clear()
        self.logger.info("Element cache cleared")

    def get_selector(self, element: Union[SyncLocator, AsyncLocator]) -> str:
        """Get a robust selector for an element"""
        # This would generate a selector that's less likely to break
        # Implementation would analyze the element and create the best selector
        pass