from typing import Dict, Any, Optional, List
from playwright.async_api import Page, Locator
from dataclasses import dataclass, field
import logging

# Import date picker utilities
try:
    from .utils import DatePickerHandler, DateTimeParser
except ImportError:
    DatePickerHandler = None
    DateTimeParser = None

logger = logging.getLogger(__name__)


@dataclass
class TestContext:
    """
    Runtime context for test execution
    Holds page instance, test data, and provides helper methods
    """
    page: Page
    element_detector: Any  # ElementDetector instance
    env_config: Dict[str, Any] = field(default_factory=dict)
    base_url: str = ""
    timeout: int = 30000
    test_data: Dict[str, Any] = field(default_factory=dict)
    credentials: Dict[str, str] = field(default_factory=dict)
    current_step: Optional[Any] = None

    def load_credentials(self, env_config: Dict[str, Any]):
        """Load credentials from environment config"""
        # Load role-based credentials
        roles = env_config.get('roles', {})
        for role_name, creds in roles.items():
            if isinstance(creds, dict):
                # Store both by role name and by username
                if 'username' in creds:
                    self.credentials[creds['username']] = creds.get('password', '')
                if 'password' in creds:
                    self.credentials[f"{role_name}_password"] = creds['password']

        # Load legacy credentials
        legacy_creds = env_config.get('credentials', {})
        for cred_name, creds in legacy_creds.items():
            if isinstance(creds, dict):
                if 'username' in creds:
                    self.credentials[creds['username']] = creds.get('password', '')
                if 'password' in creds:
                    self.credentials[f"{cred_name}_password"] = creds['password']

    async def find_element(self, description: str, timeout: Optional[int] = None) -> Locator:
        """
        Find element using Element Detector

        Args:
            description: Natural language description of element
            timeout: Override default timeout

        Returns:
            Playwright Locator
        """
        timeout = timeout or self.timeout

        try:
            # Use Element Detector to find the element
            element = await self.element_detector.find_async(
                self.page,
                description,
                timeout=timeout
            )
            return element

        except Exception as e:
            logger.error(f"Failed to find element '{description}': {e}")
            # Try alternative strategies

            # Parse the description to understand what we're looking for
            desc_lower = description.lower()

            # Strategy 1: For input fields, try common selectors
            if "enter" in desc_lower or "type" in desc_lower or "input" in desc_lower:
                # Extract the field name/identifier
                parts = description.split()
                field_identifier = None

                # Look for text after "Enter" or before "field"
                for i, part in enumerate(parts):
                    if part.lower() == "enter" and i + 1 < len(parts):
                        field_identifier = parts[i + 1].strip('"')
                    elif part.lower() == "field" and i > 0:
                        field_identifier = parts[i - 1].strip('"')

                if field_identifier:
                    # Try multiple input selectors
                    selectors = [
                        f'input[name="{field_identifier}"]',
                        f'input[id="{field_identifier}"]',
                        f'input[placeholder*="{field_identifier}" i]',
                        f'textarea[name="{field_identifier}"]',
                        f'textarea[id="{field_identifier}"]',
                        f'input[type="text"]',
                        f'input[type="search"]',
                        'input:visible:not([type="hidden"]):not([type="submit"]):not([type="button"])'
                    ]

                    for selector in selectors:
                        try:
                            element = self.page.locator(selector).first
                            if await element.count() > 0:
                                # Verify it's actually visible and editable
                                if await element.is_visible() and await element.is_editable():
                                    return element
                        except:
                            continue

            # Strategy 2: Try exact text match for buttons
            if "button" in desc_lower or "click" in desc_lower:
                button_text = description.replace("Click", "").replace("button", "").strip()
                element = self.page.get_by_role("button", name=button_text)
                if await element.count() > 0:
                    return element.first

            # Strategy 3: Try by placeholder
            if "field" in desc_lower or "input" in desc_lower:
                field_name = description.replace("Enter", "").replace("field", "").replace("input", "").strip()
                element = self.page.get_by_placeholder(field_name)
                if await element.count() > 0:
                    return element.first

            # Strategy 4: Try by label
            if "field" in desc_lower:
                field_name = description.replace("Enter", "").replace("field", "").strip()
                element = self.page.get_by_label(field_name)
                if await element.count() > 0:
                    return element.first

            # Strategy 5: Try by text content
            text_to_find = description.replace("Click", "").replace("Enter", "").strip()
            element = self.page.get_by_text(text_to_find)
            if await element.count() > 0:
                return element.first

            raise Exception(f"Element not found: {description}")

    async def wait_for_element(self, description: str, state: str = "visible",
                               timeout: Optional[int] = None) -> Locator:
        """Wait for element to be in specific state"""
        element = await self.find_element(description, timeout)
        await element.wait_for(state=state, timeout=timeout or self.timeout)
        return element

    async def get_element_text(self, description: str) -> str:
        """Get text content of an element"""
        element = await self.find_element(description)
        return await element.inner_text()

    async def element_exists(self, description: str, timeout: int = 5000) -> bool:
        """Check if element exists on page"""
        try:
            await self.find_element(description, timeout=timeout)
            return True
        except:
            return False

    async def take_screenshot(self, name: str = "screenshot") -> str:
        """Take a screenshot and return the path"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = f"screenshots/{name}_{timestamp}.png"
        await self.page.screenshot(path=path)
        return path

    async def wait_for_navigation(self, timeout: Optional[int] = None):
        """Wait for navigation to complete"""
        await self.page.wait_for_load_state('networkidle', timeout=timeout or self.timeout)

    def store_data(self, key: str, value: Any):
        """Store data for use in later steps"""
        self.test_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve stored data"""
        return self.test_data.get(key, default)

    async def execute_javascript(self, script: str, *args) -> Any:
        """Execute JavaScript on the page"""
        return await self.page.evaluate(script, *args)

    async def scroll_to_element(self, description: str):
        """Scroll element into view"""
        element = await self.find_element(description)
        await element.scroll_into_view_if_needed()

    async def wait_for_text(self, text: str, timeout: Optional[int] = None):
        """Wait for specific text to appear on page"""
        await self.page.wait_for_function(
            f"document.body.innerText.includes('{text}')",
            timeout=timeout or self.timeout
        )

    async def select_dropdown_option(self, dropdown_desc: str, option_value: str):
        """Helper to select dropdown option"""
        # Click dropdown to open
        dropdown = await self.find_element(dropdown_desc)
        await dropdown.click()

        # Wait for dropdown to open
        await self.page.wait_for_timeout(500)

        # Click the option
        option = await self.find_element(f"Click {option_value}")
        await option.click()

    async def fill_form(self, form_data: Dict[str, str]):
        """Fill multiple form fields"""
        for field_name, value in form_data.items():
            element = await self.find_element(f"Enter {field_name}")
            await element.fill(value)

    async def verify_table_data(self, expected_data: List[Dict[str, str]]):
        """Verify data in tables on the page"""
        tables = await self.page.query_selector_all('table')

        for table in tables:
            # Implementation would check table contents
            # This is a placeholder for the actual implementation
            pass

    async def fill_rich_text_editor(self, description: str, content: str):
        """Fill a rich text editor field"""
        # First try to find the exact label
        label_selectors = [
            f'label:text-is("{description}")',
            f'label:has-text("{description}"):has-text("{description}")',  # Exact match
        ]

        for label_selector in label_selectors:
            try:
                labels = self.page.locator(label_selector)
                count = await labels.count()

                for i in range(count):
                    label = labels.nth(i)
                    label_text = await label.text_content()

                    # Verify exact match
                    if label_text and label_text.strip() == description:
                        # Find the rich text editor in the same form item
                        parent_container = await label.evaluate("""
                            (el) => {
                                let current = el;
                                while (current && current.parentElement) {
                                    const parent = current.parentElement;
                                    const classes = parent.className || '';
                                    if (classes.includes('ant-form-item') || 
                                        classes.includes('form-group') || 
                                        classes.includes('field-wrapper')) {
                                        return parent.outerHTML;
                                    }
                                    current = parent;
                                }
                                return el.parentElement.outerHTML;
                            }
                        """)

                        # Look for editor within this container
                        editor_selectors = [
                            '.ql-editor',
                            '[contenteditable="true"]',
                            '.rich-text-editor',
                            '.editor-content'
                        ]

                        for editor_sel in editor_selectors:
                            # Find all editors on page
                            all_editors = await self.page.locator(editor_sel).all()

                            for editor in all_editors:
                                # Check if this editor is in our container
                                is_in_container = await editor.evaluate("""
                                    (el, containerHtml) => {
                                        let parent = el;
                                        while (parent) {
                                            if (parent.outerHTML === containerHtml) {
                                                return true;
                                            }
                                            // Also check if parent contains our label
                                            const labels = parent.querySelectorAll('label');
                                            for (let label of labels) {
                                                if (label.textContent.trim() === arguments[2]) {
                                                    return true;
                                                }
                                            }
                                            parent = parent.parentElement;
                                        }
                                        return false;
                                    }
                                """, parent_container, description)

                                if is_in_container and await editor.is_visible():
                                    # Click to focus
                                    await editor.click()
                                    await self.page.wait_for_timeout(200)

                                    # Clear existing content
                                    await editor.click(click_count=3)  # Triple click to select all
                                    await self.page.keyboard.press('Delete')

                                    # Type new content
                                    await self.page.keyboard.type(content)

                                    logger.info(f"Successfully filled rich text editor for '{description}'")
                                    return True

            except Exception as e:
                logger.debug(f"Label selector {label_selector} failed: {e}")
                continue

        # Fallback: Try with less strict selectors
        rich_selectors = [
            f'label:text-is("{description}") + div .ql-editor',
            f'label:text-is("{description}") ~ div .ql-editor',
            f'.ant-form-item:has(label:text-is("{description}")) .ql-editor',
            f'label:text-is("{description}") + div [contenteditable="true"]',
            f'label:text-is("{description}") ~ div [contenteditable="true"]',
        ]

        for selector in rich_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0 and await element.is_visible():
                    # Click to focus
                    await element.click()
                    await self.page.wait_for_timeout(200)

                    # Clear existing content
                    await element.click(click_count=3)  # Triple click to select all
                    await self.page.keyboard.press('Delete')

                    # Type new content
                    await self.page.keyboard.type(content)

                    return True
            except:
                continue

        return False

    @property
    def current_url(self) -> str:
        """Get current page URL"""
        return self.page.url

    async def go_back(self):
        """Navigate back in browser history"""
        await self.page.go_back()

    async def go_forward(self):
        """Navigate forward in browser history"""
        await self.page.go_forward()

    async def reload(self):
        """Reload the current page"""
        await self.page.reload()

    async def select_date(self, field_description: str, date_description: str):
        """
        Select a date using natural language

        Args:
            field_description: Natural language description of the date field
            date_description: Natural language description of the date (e.g., "tomorrow", "next Monday")
        """
        if DateTimeParser and DatePickerHandler:
            # Parse the date
            date = DateTimeParser.parse(date_description)

            # Use date picker handler
            picker = DatePickerHandler(self.page)
            success = await picker.select_date(field_description, date)

            if not success:
                raise Exception(f"Failed to select date '{date_description}' in field '{field_description}'")
        else:
            raise Exception("Date picker utilities not available")

    async def select_date_range(self, field_description: str, start_description: str, end_description: str):
        """
        Select a date range using natural language

        Args:
            field_description: Natural language description of the date range field
            start_description: Natural language from typing import Dict, Any, Optional, List
        """