import asyncio
import os
import json
import yaml
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import logging
from dataclasses import dataclass, field
from .nlp_step_executor import NLPStepExecutor, NLPStepParser

# Playwright imports
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError:
    raise ImportError("Playwright is not installed. Run: pip install playwright && playwright install")

# Behave imports
try:
    from behave.parser import parse_feature
    from behave.model import Feature, Scenario, Step
except ImportError:
    raise ImportError("Behave is not installed. Run: pip install behave")

# Internal imports - adjust based on your actual file structure
try:
    from qa_copilot.core.base import QAModule
    BASE_CLASS = QAModule
except ImportError:
    # If QAModule is not available, use object as base
    BASE_CLASS = object
    # logger.warning("QAModule not found, using standalone TestExecutor")

    # Try to import additional items if they exist
    try:
        from qa_copilot.core.base import ModuleStatus
    except ImportError:
        # Define a simple ModuleStatus if not available
        from enum import Enum


        class ModuleStatus(Enum):
            READY = "ready"
            ERROR = "error"
            INITIALIZING = "initializing"
except ImportError:
    # Fallback: Create a simple QAModule base class if import fails
    from abc import ABC, abstractmethod


    class QAModule(ABC):
        def __init__(self, config=None):
            self.config = config
            self.status = None
            self._initialize()

        @abstractmethod
        def _initialize(self):
            pass

        @abstractmethod
        def execute(self, input_data):
            pass

        @abstractmethod
        def validate(self):
            pass

        @staticmethod
        @abstractmethod
        def get_info():
            pass

from qa_copilot.detector.detector import ElementDetector

# Local imports within executor module
from .step_definitions import StepDefinitionRegistry
from .test_context import TestContext
from .report_collector import ReportCollector

logger = logging.getLogger(__name__)


@dataclass
class ExecutorConfig:
    """Configuration for Test Executor"""
    browser: str = "chromium"
    headless: bool = False
    timeout: int = 30000
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 720})
    screenshot_on_failure: bool = True
    video_recording: bool = False
    parallel_workers: int = 1
    retry_failed_steps: int = 1
    environment: str = "dev"
    config_path: Optional[str] = None
    base_url: Optional[str] = None
    slow_mo: int = 0
    devtools: bool = False


class TestExecutor:
    """
    Executes BDD feature files using Playwright
    Integrates with Element Detector for intelligent element finding
    """

    def __init__(self, config: Optional[Union[Dict, ExecutorConfig]] = None):
        """
            Executes BDD feature files using Playwright
            Integrates with Element Detector for intelligent element finding
        """
        # Store raw config for custom parameters
        self.raw_config = config if isinstance(config, dict) else {}

        # Convert dict to ExecutorConfig if needed, excluding custom params
        if isinstance(config, dict):
            # Extract standard ExecutorConfig fields
            executor_config_fields = {
                'browser', 'headless', 'timeout', 'viewport',
                'screenshot_on_failure', 'video_recording',
                'parallel_workers', 'retry_failed_steps',
                'environment', 'config_path', 'base_url',
                'slow_mo', 'devtools'
            }

            # Create ExecutorConfig with only standard fields
            config_dict = {k: v for k, v in config.items() if k in executor_config_fields}
            self.config = ExecutorConfig(**config_dict)
        else:
            self.config = config or ExecutorConfig()

        self.element_detector = ElementDetector()
        self.step_registry = StepDefinitionRegistry()
        self.report_collector = ReportCollector()
        self.env_config = self._load_environment_config()

        # Add NLP parser support
        self.use_nlp_parser = self.raw_config.get('use_nlp_parser', True)
        if self.use_nlp_parser:
            try:
                from .nlp_step_executor import NLPStepParser
                self.nlp_parser = NLPStepParser()
                logger.info("NLP parser enabled")
            except ImportError:
                logger.warning("NLP parser not available, falling back to traditional steps")
                self.use_nlp_parser = False
                self.nlp_parser = None

        # Register built-in step definitions
        self._register_builtin_steps()

        # Initialize status
        self.status = "ready"

    def _initialize(self) -> None:
        """Initialize the Test Executor module"""
        try:
            # Set initial status
            if hasattr(self, 'status'):
                self.status = getattr(ModuleStatus, 'INITIALIZING', 'initializing')

            # Initialize components (already done in __init__)
            logger.info("Initializing Test Executor components...")

            # Validate configuration
            if not self.validate():
                raise ValueError("Invalid executor configuration")

            # Register built-in steps (already called in __init__)
            logger.info(f"Registered {len(self.step_registry.definitions)} step definitions")

            # Set status to ready
            if hasattr(self, 'status'):
                self.status = getattr(ModuleStatus, 'READY', 'ready')

            logger.info("Test Executor initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Test Executor: {e}")
            if hasattr(self, 'status'):
                self.status = getattr(ModuleStatus, 'ERROR', 'error')
            raise

    def debug_mode(self, enabled: bool = True):
        """Enable/disable debug mode"""
        if enabled:
            logging.getLogger().setLevel(logging.DEBUG)
            self.config.slow_mo = 500  # Slow down actions
            self.config.headless = False  # Show browser
            logger.info("Debug mode enabled")
        else:
            logging.getLogger().setLevel(logging.INFO)
            self.config.slow_mo = 0
            logger.info("Debug mode disabled")

    def list_all_steps(self):
        """List all registered step definitions"""
        definitions = self.step_registry.list_definitions()

        print("\n" + "=" * 60)
        print("REGISTERED STEP DEFINITIONS")
        print("=" * 60)

        # Group by keyword
        grouped = {}
        for defn in definitions:
            keyword = defn['keyword'].upper()
            if keyword not in grouped:
                grouped[keyword] = []
            grouped[keyword].append(defn)

        for keyword in ['GIVEN', 'WHEN', 'THEN']:
            if keyword in grouped:
                print(f"\n{keyword} Steps ({len(grouped[keyword])}):")
                print("-" * 40)
                for defn in grouped[keyword]:
                    print(f"  Pattern: {defn['pattern']}")
                    if defn.get('description'):
                        print(f"    Desc: {defn['description']}")
                    print()

    def _load_environment_config(self) -> Dict[str, Any]:
        """Load environment-specific configuration"""
        if self.config.config_path:
            config_path = Path(self.config.config_path)
        else:
            # Default config location
            config_path = Path("config/environments") / f"{self.config.environment}.yaml"

        if config_path.exists():
            with open(config_path, 'r') as f:
                env_config = yaml.safe_load(f)
                logger.info(f"Loaded environment config from {config_path}")

                # Override base_url if provided in env config
                if 'base_url' in env_config and not self.config.base_url:
                    self.config.base_url = env_config['base_url']

                return env_config
        else:
            logger.warning(f"Environment config not found: {config_path}")
            return {}

    def _register_builtin_steps(self):
        """Register built-in step definitions"""
        registry = self.step_registry

        # Navigation steps
        @registry.given(r'I navigate to the login page')
        @registry.given(r'I navigate to "([^"]*)"')
        @registry.when(r'I navigate to "([^"]*)"')
        async def navigate_to(context: TestContext, path: str = None):
            # FIXED: Removed the automatic addition of '/login' to the URL
            if path is None:
                # This is specifically for "I navigate to the login page" step
                path = context.env_config.get('pages', {}).get('login', '/login')
                url = context.base_url.rstrip('/') + '/' + path.lstrip('/')
            elif path.startswith(('http://', 'https://')):
                # If it's already a full URL, use it as is
                url = path
            else:
                # Otherwise, append to base URL only if it's a relative path
                url = context.base_url.rstrip('/') + '/' + path.lstrip('/')

            await context.page.goto(url)
            await context.page.wait_for_load_state('networkidle')

        # Input steps - Enhanced for rich text editors
        @registry.when(r'I enter "([^"]*)" in the "([^"]*)" field')
        @registry.when(r'I type "([^"]*)" in the "([^"]*)" field')
        async def enter_text(context: TestContext, value: str, field_name: str):
            # Handle credential substitution
            if value in context.credentials:
                value = context.credentials[value]

            # Check if this is a rich text editor field
            rich_text_fields = ['about this challenge', 'description', 'content', 'editor', 'message']
            is_rich_text = any(keyword in field_name.lower() for keyword in rich_text_fields)

            if is_rich_text:
                # Try to fill as rich text editor first
                success = await context.fill_rich_text_editor(field_name, value)
                if success:
                    return

            # Fallback to standard element finding
            element = await context.find_element(f"Enter {field_name}")

            # Check if it's contenteditable
            is_contenteditable = await element.evaluate(
                "el => el.contentEditable === 'true' || el.classList.contains('ql-editor')"
            )

            if is_contenteditable:
                # Handle as rich text
                await element.click()
                await asyncio.sleep(0.2)
                await element.click(click_count=3)  # Select all
                await context.page.keyboard.press('Delete')
                await context.page.keyboard.type(value)
            else:
                # Standard input
                await element.fill(value)


        # # Input steps
        # @registry.when(r'I enter "([^"]*)" in the "([^"]*)" field')
        # @registry.when(r'I type "([^"]*)" in the "([^"]*)" field')
        # async def enter_text(context: TestContext, value: str, field_name: str):
        #     # Handle credential substitution
        #     if value in context.credentials:
        #         value = context.credentials[value]
        #
        #     element = await context.find_element(f"Enter {field_name}")
        #     await element.fill(value)

        # Click steps
        @registry.when(r'I click the "([^"]*)" button')
        @registry.when(r'I click on "([^"]*)"')
        @registry.when(r'I click "([^"]*)"')
        async def click_element(context: TestContext, element_desc: str):
            try:
                element = await context.find_element(f"Click {element_desc}")
                await element.click()
                # Wait for potential navigation or dynamic content
                await context.page.wait_for_load_state('networkidle')
            except Exception as e:
                logger.error(f"Failed to click '{element_desc}': {e}")
                raise Exception(f"Could not click element: {element_desc}")

        # Select/Dropdown steps
        @registry.when(r'I select "([^"]*)" in the "([^"]*)" dropdown')
        @registry.when(r'I select "([^"]*)" in ([^"]*) dropdown')
        async def select_option(context: TestContext, value: str, dropdown_name: str):
            # First click the dropdown to open it
            dropdown = await context.find_element(f"Click {dropdown_name} dropdown")
            await dropdown.click()

            # Wait for dropdown to open
            await asyncio.sleep(0.5)

            # Click the option
            option = await context.find_element(f"Click {value} option")
            await option.click()

        # Search steps
        @registry.when(r'I search with text "([^"]*)"')
        @registry.when(r'I search for "([^"]*)"')
        async def search_text(context: TestContext, search_term: str):
            search_box = await context.find_element("Enter search")
            await search_box.fill(search_term)

            # Try to find and click search button or press Enter
            try:
                search_btn = await context.find_element("Click search button", timeout=2000)
                await search_btn.click()
            except:
                # Press Enter if no search button found
                await search_box.press("Enter")

            # Wait for results
            await context.page.wait_for_load_state('networkidle')

        # Table verification steps
        @registry.then(r'the table should show:')
        async def verify_table(context: TestContext):
            table_data = context.current_step.table
            if not table_data:
                raise ValueError("No table data provided in the step")

            # Wait for table to be visible
            await context.page.wait_for_selector('table', state='visible')

            # Get all tables on the page
            tables = await context.page.query_selector_all('table')

            for table in tables:
                # Check if this table contains the expected data
                rows = await table.query_selector_all('tr')

                # Look for header row matching our expected headers
                if rows:
                    header_cells = await rows[0].query_selector_all('th, td')
                    headers = []
                    for cell in header_cells:
                        text = await cell.inner_text()
                        headers.append(text.strip())

                    # Check if headers match
                    expected_headers = table_data.headings
                    if all(h in headers for h in expected_headers):
                        # Found matching table, verify data
                        for row_data in table_data.rows:
                            found = False
                            for row in rows[1:]:  # Skip header
                                cells = await row.query_selector_all('td')
                                cell_values = []
                                for cell in cells:
                                    text = await cell.inner_text()
                                    cell_values.append(text.strip())

                                # Check if this row matches expected data
                                matches = True
                                for i, expected_value in enumerate(row_data.cells):
                                    header_idx = headers.index(expected_headers[i])
                                    if header_idx < len(cell_values):
                                        if cell_values[header_idx] != expected_value:
                                            matches = False
                                            break

                                if matches:
                                    found = True
                                    break

                            if not found:
                                raise AssertionError(
                                    f"Expected row not found: {dict(zip(expected_headers, row_data.cells))}")

                        return  # All rows verified

            raise AssertionError("No table found with expected headers")

        # Link click steps
        @registry.when(r'I click on the ([^"]*) link "([^"]*)"')
        @registry.when(r'I click on link "([^"]*)"')
        async def click_link(context: TestContext, link_type: str = None, link_text: str = None):
            if link_text is None:
                link_text = link_type
                link_type = "link"

            # Try multiple strategies to find the link
            link = await context.find_element(f"Click {link_text} link")
            await link.click()
            await context.page.wait_for_load_state('networkidle')

        # Text verification steps
        @registry.then(r'I verify text "([^"]*)"')
        @registry.then(r'I should see "([^"]*)"')
        @registry.then(r'the page should contain "([^"]*)"')
        async def verify_text(context: TestContext, expected_text: str):
            # Wait for text to appear
            await context.page.wait_for_timeout(1000)  # Brief wait for dynamic content

            # Check if text is visible on page
            text_locator = context.page.get_by_text(expected_text)
            try:
                await text_locator.wait_for(state='visible', timeout=5000)
            except:
                # Get page content for debugging
                content = await context.page.content()
                raise AssertionError(f"Text '{expected_text}' not found on page")

        def register_enhanced_dropdown_steps(registry):
            """Register enhanced dropdown handling steps"""

            # Enhanced Select/Dropdown steps
            @registry.when(r'I select "([^"]*)" from "([^"]*)" dropdown')
            @registry.when(r'I select "([^"]*)" from dropdown')
            @registry.when(r'I select "([^"]*)" in the "([^"]*)" dropdown')
            @registry.when(r'I choose "([^"]*)" from "([^"]*)"')
            async def select_option_enhanced(context: TestContext, value: str, dropdown_name: str = None):
                """Enhanced dropdown selection with multiple strategies"""
                logger = logging.getLogger(__name__)
                logger.info(f"Selecting '{value}' from dropdown: {dropdown_name if dropdown_name else 'default'}")

                # Strategy 1: If dropdown name is provided, try to click it first
                if dropdown_name:
                    # Try to find and click the dropdown trigger
                    dropdown_selectors = [
                        # Ant Design patterns
                        f'.ant-select:has(*:has-text("{dropdown_name}"))',
                        f'.ant-select-selector:has(*:has-text("{dropdown_name}"))',

                        # Generic patterns with dropdown name
                        f'[aria-label*="{dropdown_name}" i]',
                        f'[placeholder*="{dropdown_name}" i]',
                        f'select[name*="{dropdown_name}" i]',
                        f'[class*="select"]:has(*:has-text("{dropdown_name}"))',
                        f'[class*="dropdown"]:has(*:has-text("{dropdown_name}"))',

                        # Label-based selection
                        f'label:has-text("{dropdown_name}") + .ant-select',
                        f'label:has-text("{dropdown_name}") + [class*="select"]',
                        f'label:has-text("{dropdown_name}") ~ .ant-select',
                        f'label:has-text("{dropdown_name}") ~ [class*="select"]',
                    ]

                    dropdown_clicked = False
                    for selector in dropdown_selectors:
                        try:
                            dropdown = context.page.locator(selector).first
                            if await dropdown.count() > 0 and await dropdown.is_visible():
                                await dropdown.click()
                                logger.info(f"Clicked dropdown: {selector}")
                                dropdown_clicked = True
                                await asyncio.sleep(0.5)  # Wait for dropdown to open
                                break
                        except:
                            continue

                    if not dropdown_clicked:
                        # Try using element detector
                        try:
                            dropdown = await context.find_element(f"Click {dropdown_name} dropdown")
                            await dropdown.click()
                            dropdown_clicked = True
                            await asyncio.sleep(0.5)
                        except:
                            logger.warning(f"Could not find dropdown: {dropdown_name}")

                # Strategy 2: Look for the option in various dropdown structures
                option_selectors = [
                    # Ant Design dropdown patterns
                    f'.ant-dropdown:not(.ant-dropdown-hidden) .ant-dropdown-menu-item:has-text("{value}")',
                    f'.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item:has-text("{value}")',
                    f'.ant-dropdown-menu-item:has-text("{value}"):visible',
                    f'.ant-select-item:has-text("{value}"):visible',
                    f'li.ant-dropdown-menu-item:has-text("{value}"):visible',

                    # Role-based patterns
                    f'[role="listbox"] [role="option"]:has-text("{value}")',
                    f'[role="menu"] [role="menuitem"]:has-text("{value}")',
                    f'[role="option"]:has-text("{value}"):visible',

                    # Generic dropdown patterns
                    f'.dropdown-menu:visible li:has-text("{value}")',
                    f'.dropdown-content:visible [class*="item"]:has-text("{value}")',
                    f'ul:visible > li:has-text("{value}")',

                    # Data attribute patterns
                    f'[data-value="{value}"]:visible',
                    f'[data-option="{value}"]:visible',

                    # Select/Option patterns
                    f'select option:has-text("{value}")',
                    f'option[value="{value}"]',

                    # Exact text match as last resort
                    f'*:visible:text-is("{value}")',
                ]

                # Try each selector
                for selector in option_selectors:
                    try:
                        # First check if element exists and is visible
                        option = context.page.locator(selector).first
                        if await option.count() > 0:
                            # Additional check to ensure it's in a dropdown context
                            is_in_dropdown = await option.evaluate("""
                                (el) => {
                                    // Check if element or its parents have dropdown-related classes/roles
                                    let current = el;
                                    for (let i = 0; i < 5; i++) {
                                        if (!current) break;
                                        const classes = (current.className || '').toLowerCase();
                                        const role = (current.getAttribute('role') || '').toLowerCase();
                                        const isDropdown = 
                                            classes.includes('dropdown') ||
                                            classes.includes('select') ||
                                            classes.includes('menu') ||
                                            classes.includes('option') ||
                                            role === 'listbox' ||
                                            role === 'menu' ||
                                            role === 'option' ||
                                            role === 'menuitem';
                                        if (isDropdown) return true;
                                        current = current.parentElement;
                                    }
                                    return false;
                                }
                            """)

                            if is_in_dropdown or selector.includes('option'):  # Always allow <option> tags
                                await option.click()
                                logger.info(f"Selected option '{value}' using: {selector}")

                                # Wait for dropdown to close
                                await asyncio.sleep(0.3)
                                return
                            else:
                                logger.debug(f"Found '{value}' but not in dropdown context with: {selector}")

                    except Exception as e:
                        logger.debug(f"Selector failed: {selector} - {str(e)}")
                        continue

                # Strategy 3: If no dropdown name provided, try clicking any visible dropdown first
                if not dropdown_name:
                    generic_dropdown_selectors = [
                        '.ant-select-selector:visible',
                        '.ant-select:visible',
                        '[role="combobox"]:visible',
                        'select:visible',
                        '[class*="dropdown-trigger"]:visible',
                        '[class*="select-trigger"]:visible',
                    ]

                    for selector in generic_dropdown_selectors:
                        try:
                            dropdowns = await context.page.locator(selector).all()
                            for dropdown in dropdowns[:3]:  # Try first 3 visible dropdowns
                                if await dropdown.is_visible():
                                    await dropdown.click()
                                    await asyncio.sleep(0.5)

                                    # Try to find option again
                                    for option_selector in option_selectors[:5]:  # Try first 5 option selectors
                                        try:
                                            option = context.page.locator(option_selector).first
                                            if await option.count() > 0:
                                                await option.click()
                                                logger.info(f"Selected option after opening generic dropdown")
                                                return
                                        except:
                                            continue
                        except:
                            continue

                # Last resort: Use element detector
                try:
                    option_element = await context.find_element(f"Click {value} option")
                    await option_element.click()
                    logger.info(f"Selected option using element detector")
                except Exception as e:
                    raise Exception(f"Could not select option '{value}' from dropdown" +
                                    (f" '{dropdown_name}'" if dropdown_name else ""))

            # Additional helper for radio buttons with better selection
            @registry.when(r'I select "([^"]*)" radio button')
            @registry.when(r'I choose "([^"]*)" radio option')
            async def select_radio_enhanced(context: TestContext, option_text: str):
                """Enhanced radio button selection"""
                logger = logging.getLogger(__name__)

                # Try various radio button patterns
                radio_selectors = [
                    # Direct value match
                    f'input[type="radio"][value="{option_text}"]',
                    f'input[type="radio"][value*="{option_text}" i]',

                    # Label association patterns
                    f'label:has-text("{option_text}") input[type="radio"]',
                    f'label:has-text("{option_text}") > input[type="radio"]',
                    f'input[type="radio"] + label:has-text("{option_text}")',

                    # Ant Design patterns
                    f'.ant-radio-wrapper:has-text("{option_text}") input[type="radio"]',
                    f'.ant-radio-group label:has-text("{option_text}") input[type="radio"]',

                    # Aria patterns
                    f'input[type="radio"][aria-label*="{option_text}" i]',
                    f'[role="radio"][aria-label*="{option_text}" i]',

                    # Parent container patterns
                    f'*:has-text("{option_text}") input[type="radio"]',
                ]

                for selector in radio_selectors:
                    try:
                        # Find the radio input
                        radio = context.page.locator(selector).first
                        if await radio.count() > 0:
                            # Check if it's already selected
                            is_checked = await radio.is_checked()
                            if not is_checked:
                                # Try to click the radio button directly
                                if await radio.is_visible():
                                    await radio.click()
                                else:
                                    # If radio is hidden, click the label or wrapper
                                    parent = await radio.evaluate_handle(
                                        "el => el.closest('label, .ant-radio-wrapper, [role=\"radio\"]')")
                                    if parent:
                                        await parent.click()
                                    else:
                                        await radio.click(force=True)

                            logger.info(f"Selected radio button '{option_text}' using: {selector}")
                            return

                    except Exception as e:
                        logger.debug(f"Radio selector failed: {selector} - {str(e)}")
                        continue

                # Fallback to element detector
                try:
                    radio = await context.find_element(f"Click {option_text} radio button")
                    await radio.click()
                except:
                    raise Exception(f"Could not find radio button: {option_text}")

            # Enhanced checkbox handling
            @registry.when(r'I select "([^"]*)" checkbox')
            @registry.when(r'I check "([^"]*)"')
            @registry.when(r'I uncheck "([^"]*)"')
            async def handle_checkbox_enhanced(context: TestContext, checkbox_text: str):
                """Enhanced checkbox handling"""
                logger = logging.getLogger(__name__)

                # Determine if we're checking or unchecking
                step_text = context.current_step.name if hasattr(context, 'current_step') else ""
                should_uncheck = "uncheck" in step_text.lower()

                checkbox_selectors = [
                    # Direct value match
                    f'input[type="checkbox"][value="{checkbox_text}"]',
                    f'input[type="checkbox"][value*="{checkbox_text}" i]',

                    # Label patterns
                    f'label:has-text("{checkbox_text}") input[type="checkbox"]',
                    f'label:has-text("{checkbox_text}") > input[type="checkbox"]',
                    f'input[type="checkbox"] + label:has-text("{checkbox_text}")',

                    # Ant Design patterns
                    f'.ant-checkbox-wrapper:has-text("{checkbox_text}") input[type="checkbox"]',
                    f'.ant-checkbox-group label:has-text("{checkbox_text}") input[type="checkbox"]',

                    # Aria patterns
                    f'input[type="checkbox"][aria-label*="{checkbox_text}" i]',
                    f'[role="checkbox"][aria-label*="{checkbox_text}" i]',

                    # Parent patterns
                    f'*:has-text("{checkbox_text}") input[type="checkbox"]',
                ]

                for selector in checkbox_selectors:
                    try:
                        checkbox = context.page.locator(selector).first
                        if await checkbox.count() > 0:
                            is_checked = await checkbox.is_checked()

                            # Only click if state needs to change
                            if (should_uncheck and is_checked) or (not should_uncheck and not is_checked):
                                if await checkbox.is_visible():
                                    await checkbox.click()
                                else:
                                    # Click parent if checkbox is hidden
                                    parent = await checkbox.evaluate_handle(
                                        "el => el.closest('label, .ant-checkbox-wrapper, [role=\"checkbox\"]')")
                                    if parent:
                                        await parent.click()
                                    else:
                                        await checkbox.click(force=True)

                            action = "Unchecked" if should_uncheck else "Checked"
                            logger.info(f"{action} checkbox '{checkbox_text}' using: {selector}")
                            return

                    except Exception as e:
                        logger.debug(f"Checkbox selector failed: {selector} - {str(e)}")
                        continue

                # Fallback
                try:
                    checkbox = await context.find_element(f"Click {checkbox_text} checkbox")
                    await checkbox.click()
                except:
                    raise Exception(f"Could not find checkbox: {checkbox_text}")

            # Verification step for selected options
            @registry.then(r'I verify "([^"]*)" option is selected')
            @registry.then(r'"([^"]*)" should be selected')
            async def verify_option_selected(context: TestContext, option_text: str):
                """Verify that an option/radio/checkbox is selected"""
                logger = logging.getLogger(__name__)

                # Check radio buttons
                radio_checks = [
                    f'input[type="radio"][value="{option_text}"]:checked',
                    f'label:has-text("{option_text}") input[type="radio"]:checked',
                    f'.ant-radio-wrapper:has-text("{option_text}") input[type="radio"]:checked',
                ]

                for selector in radio_checks:
                    try:
                        if await context.page.locator(selector).count() > 0:
                            logger.info(f"Verified radio button '{option_text}' is selected")
                            return
                    except:
                        continue

                # Check checkboxes
                checkbox_checks = [
                    f'input[type="checkbox"][value="{option_text}"]:checked',
                    f'label:has-text("{option_text}") input[type="checkbox"]:checked',
                    f'.ant-checkbox-wrapper:has-text("{option_text}") input[type="checkbox"]:checked',
                ]

                for selector in checkbox_checks:
                    try:
                        if await context.page.locator(selector).count() > 0:
                            logger.info(f"Verified checkbox '{option_text}' is selected")
                            return
                    except:
                        continue

                # Check dropdown selected value
                dropdown_checks = [
                    f'.ant-select-selection-item:has-text("{option_text}")',
                    f'.ant-select-selection-item[title="{option_text}"]',
                    f'select option:checked:has-text("{option_text}")',
                    f'[class*="selected"]:has-text("{option_text}")',
                ]

                for selector in dropdown_checks:
                    try:
                        if await context.page.locator(selector).count() > 0:
                            logger.info(f"Verified dropdown option '{option_text}' is selected")
                            return
                    except:
                        continue

                raise AssertionError(f"Option '{option_text}' is not selected")

    async def execute_feature(self, feature_path: Union[str, Path]) -> Dict[str, Any]:
        """Execute a single feature file"""
        feature_path = Path(feature_path)

        if not feature_path.exists():
            raise FileNotFoundError(f"Feature file not found: {feature_path}")

        # Parse feature file
        with open(feature_path, 'r') as f:
            feature_content = f.read()

        feature = parse_feature(feature_content, filename=str(feature_path))

        # Execute feature
        result = {
            'feature': feature.name,
            'file': str(feature_path),
            'scenarios': [],
            'start_time': datetime.now().isoformat(),
            'status': 'passed'
        }

        async with async_playwright() as p:
            # Launch browser
            browser = await self._launch_browser(p)

            try:
                # Execute each scenario
                for scenario in feature.scenarios:
                    if self._should_run_scenario(scenario):
                        scenario_result = await self._execute_scenario(
                            browser, feature, scenario
                        )
                        result['scenarios'].append(scenario_result)

                        if scenario_result['status'] == 'failed':
                            result['status'] = 'failed'

                result['end_time'] = datetime.now().isoformat()

            finally:
                await browser.close()

        return result

    async def _launch_browser(self, playwright) -> Browser:
        """Launch browser with configuration"""
        browser_type = getattr(playwright, self.config.browser)

        launch_args = {
            'headless': self.config.headless,
            'slow_mo': self.config.slow_mo,
        }

        if self.config.devtools:
            launch_args['devtools'] = True

        return await browser_type.launch(**launch_args)

    async def _execute_scenario(
            self,
            browser: Browser,
            feature: Feature,
            scenario: Scenario
    ) -> Dict[str, Any]:
        """Execute a single scenario"""
        result = {
            'name': scenario.name,
            # 'tags': [tag.name for tag in scenario.tags],
            'tags': [str(tag) for tag in scenario.tags],
            'steps': [],
            'status': 'passed',
            'start_time': datetime.now().isoformat()
        }

        # Create new context for scenario
        context = await browser.new_context(
            viewport=self.config.viewport,
            record_video_dir="videos/" if self.config.video_recording else None
        )

        page = await context.new_page()

        # Create test context
        test_context = TestContext(
            page=page,
            element_detector=self.element_detector,
            env_config=self.env_config,
            base_url=self.config.base_url or self.env_config.get('base_url', ''),
            timeout=self.config.timeout
        )

        # Load credentials if available
        test_context.load_credentials(self.env_config)

        try:
            # Execute background steps
            if feature.background:
                for step in feature.background.steps:
                    await self._execute_step(test_context, step, result)

            # Execute scenario steps
            for step in scenario.steps:
                await self._execute_step(test_context, step, result)

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)

            # Take screenshot on failure
            if self.config.screenshot_on_failure:
                screenshot_path = f"screenshots/{scenario.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path)
                result['screenshot'] = screenshot_path

        finally:
            await context.close()
            result['end_time'] = datetime.now().isoformat()

        return result

    async def _execute_step(
            self,
            context: TestContext,
            step: Step,
            result: Dict[str, Any]
    ):
        """Execute a single step with NLP support"""
        step_result = {
            'keyword': step.keyword,
            'name': step.name,
            'status': 'passed',
            'start_time': datetime.now().isoformat()
        }

        try:
            # Set current step in context
            context.current_step = step

            # First try NLP parser if enabled
            if self.use_nlp_parser:
                # Create NLP executor
                nlp_executor = NLPStepExecutor(
                    context.page,
                    context.element_detector,
                    context.env_config
                )

                # Execute using NLP
                try:
                    exec_result = await nlp_executor.execute_step(step.name)
                    if exec_result['status'] == 'passed':
                        step_result['end_time'] = datetime.now().isoformat()
                        result['steps'].append(step_result)
                        return
                    elif exec_result['action'] != 'unknown':
                        # Known action but failed
                        raise Exception(exec_result.get('error', 'Step execution failed'))
                except Exception as e:
                    if 'Unknown action' not in str(e):
                        # Real error, not just unrecognized pattern
                        raise

            # Fall back to traditional step definitions
            step_def = self.step_registry.find_step_definition(
                step.keyword.strip(), step.name
            )

            if not step_def:
                raise NotImplementedError(
                    f"No step definition found for: {step.keyword} {step.name}"
                )

            # Execute with retry logic
            retry_count = 0
            while retry_count <= self.config.retry_failed_steps:
                try:
                    await step_def.execute(context, step.name)
                    break
                except Exception as e:
                    if retry_count < self.config.retry_failed_steps:
                        retry_count += 1
                        logger.warning(f"Step failed, retrying ({retry_count}/{self.config.retry_failed_steps}): {e}")
                        await asyncio.sleep(1)
                    else:
                        raise

            step_result['end_time'] = datetime.now().isoformat()

        except Exception as e:
            step_result['status'] = 'failed'
            step_result['error'] = str(e)
            step_result['end_time'] = datetime.now().isoformat()
            raise

        finally:
            result['steps'].append(step_result)

    def _should_run_scenario(self, scenario: Scenario) -> bool:
        """Check if scenario should be executed based on tags"""
        # For now, run all scenarios
        # TODO: Add tag filtering support
        return True

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute feature files

        Args:
            input_data: Dict with 'feature_path' or 'feature_dir'

        Returns:
            Execution results
        """
        feature_path = input_data.get('feature_path')
        feature_dir = input_data.get('feature_dir', 'features/')

        if feature_path:
            # Execute single feature
            return asyncio.run(self.execute_feature(feature_path))
        else:
            # Execute all features in directory
            return self.execute_directory(feature_dir)

    def execute_directory(self, feature_dir: Union[str, Path]) -> Dict[str, Any]:
        """Execute all feature files in a directory"""
        feature_dir = Path(feature_dir)

        if not feature_dir.exists():
            raise FileNotFoundError(f"Feature directory not found: {feature_dir}")

        results = {
            'features': [],
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0
            },
            'start_time': datetime.now().isoformat()
        }

        # Find all feature files
        feature_files = list(feature_dir.glob('**/*.feature'))

        if self.config.parallel_workers > 1:
            # TODO: Implement parallel execution
            pass
        else:
            # Sequential execution
            for feature_file in feature_files:
                logger.info(f"Executing feature: {feature_file}")
                feature_result = asyncio.run(self.execute_feature(feature_file))
                results['features'].append(feature_result)

                # Update summary
                results['summary']['total'] += 1
                if feature_result['status'] == 'passed':
                    results['summary']['passed'] += 1
                else:
                    results['summary']['failed'] += 1

        results['end_time'] = datetime.now().isoformat()

        # Generate report
        self.report_collector.generate_report(results)

        return results

    def validate(self) -> bool:
        """Validate executor configuration"""
        # Check if browser is supported
        if self.config.browser not in ['chromium', 'firefox', 'webkit']:
            logger.error(f"Unsupported browser: {self.config.browser}")
            return False

        return True

    @staticmethod
    def get_info() -> Dict[str, Any]:
        """Get module information"""
        return {
            'name': 'Test Executor',
            'version': '0.1.0',
            'description': 'Executes BDD feature files using Playwright',
            'author': 'QA-Copilot Team',
            'capabilities': [
                'Execute Gherkin scenarios',
                'Multi-browser support',
                'Parallel execution',
                'Screenshot on failure',
                'Video recording',
                'Integration with Element Detector'
            ]
        }