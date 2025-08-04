"""
Enhanced step executor with improved dropdown handling
"""

import re
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from playwright.async_api import Page, Locator
from datetime import datetime, timedelta
import logging

# Import date picker utilities
try:
    from ..utils import DatePickerHandler, DateTimeParser
except ImportError:
    # Fallback if utils not available
    DatePickerHandler = None
    DateTimeParser = None

logger = logging.getLogger(__name__)


class NLPStepParser:
    """Parse natural language steps into executable actions"""

    def __init__(self):
        self.action_patterns = self._initialize_action_patterns()

    def _initialize_action_patterns(self) -> Dict:
        """Initialize NLP patterns for step mapping"""
        return {
            # Navigation patterns
            'navigate': {
                'patterns': [
                    r'(?:i )?(?:navigate to|go to|visit|access) (?:the )?(?:url |page |site )?(.+)',
                    r'(?:i am|user is) on (?:the )?(.+) page',
                ],
                'action': 'navigate',
                'params': ['url']
            },

            # Login patterns
            'login_as_role': {
                'patterns': [
                    r'(?:i )?log in as ["\'](.*?)["\']',
                    r'(?:i )?login as ["\'](.*?)["\']',
                    r'(?:i )?sign in as ["\'](.*?)["\']',
                ],
                'action': 'login_as_role',
                'params': ['role']
            },

            # Click patterns
            'click': {
                'patterns': [
                    r'(?:i )?click on ["\'](.*?)["\']',
                    r'(?:i )?click (?:the )?["\'](.*?)["\']\s*(?:button|link)?',
                    r'(?:i )?click (?:on )?(?:the )?(.+?)(?:\s+button)?$',
                ],
                'action': 'click',
                'params': ['element']
            },

            # Select/Dropdown patterns - Enhanced
            'select': {
                'patterns': [
                    r'(?:i )?select ["\'](.*?)["\']\s+from\s+["\'](.*?)["\']\s*dropdown',
                    r'(?:i )?select ["\'](.*?)["\']\s+from\s+dropdown',
                    r'(?:i )?choose ["\'](.*?)["\']\s+from\s+(?:the\s+)?["\'](.*?)["\']',
                    r'(?:i )?select ["\'](.*?)["\']\s+in\s+(?:the\s+)?["\'](.*?)["\']\s*dropdown',
                ],
                'action': 'select',
                'params': ['option', 'element']
            },

            # Input patterns
            'input': {
                'patterns': [
                    r'(?:i )?enter ["\'](.*?)["\']\s+in\s+(?:the\s+)?["\'](.*?)["\']\s*field(?:\s*\[force ai\])?',
                    r'(?:i )?enter ["\'](.*?)["\']\s+in\s+(?:the\s+)?(.+?)\s+field(?:\s*\[force ai\])?',
                    r'(?:i )?type ["\'](.*?)["\']\s+in\s+(?:the\s+)?["\'](.*?)["\']',
                ],
                'action': 'input',
                'params': ['value', 'element']
            },

            # Radio button patterns
            'radio': {
                'patterns': [
                    r'(?:i )?select ["\'](.*?)["\']\s+radio\s*button',
                    r'(?:i )?choose ["\'](.*?)["\']\s+radio\s*(?:button|option)',
                ],
                'action': 'radio',
                'params': ['element']
            },

            # Checkbox patterns
            'checkbox': {
                'patterns': [
                    r'(?:i )?select ["\'](.*?)["\']\s+checkbox',
                    r'(?:i )?check ["\'](.*?)["\']\s+checkbox',
                ],
                'action': 'checkbox',
                'params': ['element']
            },

            # Verification patterns
            'verify_text': {
                'patterns': [
                    r'(?:i )?verify text ["\'](.*?)["\']',
                    r'(?:i )?(?:should )?see ["\'](.*?)["\']',
                    r'(?:the )?page (?:should )?(?:contain|display|show)s? ["\'](.*?)["\']',
                ],
                'action': 'verify_text',
                'params': ['text']
            },

            'verify_selected': {
                'patterns': [
                    r'(?:i )?verify ["\'](.*?)["\']\s+option is selected',
                    r'["\'](.*?)["\']\s+(?:should be|is) selected',
                ],
                'action': 'verify_selected',
                'params': ['element']
            },

            # Date/Time generation patterns
            'generate_datetime': {
                'patterns': [
                    r'(?:i )?generate datetime ["\'](.*?)["\']\s+and store it as ["\'](.*?)["\']',
                ],
                'action': 'generate_datetime',
                'params': ['datetime_spec', 'variable_name']
            },

            # Date range patterns
            'select_date_range': {
                'patterns': [
                    r'(?:i )?select date range ["\']?\$\{(.*?)\}["\']?\s+to\s+["\']?\$\{(.*?)\}["\']?\s+in\s+["\'](.*?)["\']\s*field',
                ],
                'action': 'select_date_range',
                'params': ['start_var', 'end_var', 'field']
            },
        }

    def parse_step(self, step_text: str) -> Tuple[str, Dict]:
        """Parse step text and return action and parameters"""
        step_text = step_text.strip()

        # Check for force AI flag
        force_ai = '[force ai]' in step_text.lower()
        if force_ai:
            step_text = step_text.replace('[force ai]', '').replace('[FORCE AI]', '').strip()

        # Try to match against patterns
        for action_key, pattern_info in self.action_patterns.items():
            for pattern in pattern_info['patterns']:
                match = re.match(pattern, step_text, re.IGNORECASE)
                if match:
                    params = {}
                    groups = match.groups()

                    # Map matched groups to parameter names
                    for i, param_name in enumerate(pattern_info['params']):
                        if i < len(groups) and groups[i]:
                            params[param_name] = groups[i]

                    # Add force_ai flag if present
                    if force_ai:
                        params['force_ai'] = True

                    return pattern_info['action'], params

        # No pattern matched
        return 'unknown', {'text': step_text}


class NLPStepExecutor:
    """Execute steps parsed by NLP parser with enhanced dropdown handling"""

    def __init__(self, page: Page, element_detector, env_config: Dict):
        self.page = page
        self.element_detector = element_detector
        self.env_config = env_config
        self.context_data = {}  # Store variables
        self.parser = NLPStepParser()

    async def execute_step(self, step_text: str) -> Dict:
        """Execute a single step"""
        action, params = self.parser.parse_step(step_text)

        logger.info(f"Executing: {action} with params: {params}")

        # Map to handler method
        handler = getattr(self, f'_handle_{action}', None)
        if handler:
            try:
                result = await handler(params)
                return {
                    'status': 'passed',
                    'action': action,
                    'params': params,
                    'result': result
                }
            except Exception as e:
                logger.error(f"Step failed: {str(e)}")
                return {
                    'status': 'failed',
                    'action': action,
                    'params': params,
                    'error': str(e)
                }
        else:
            return {
                'status': 'failed',
                'action': action,
                'params': params,
                'error': f'Unknown action: {action}'
            }

    async def _handle_navigate(self, params: Dict) -> Any:
        """Handle navigation"""
        url = params.get('url', '')

        # Check if it's a page name from config
        pages = self.env_config.get('pages', {})
        page_name = url.lower().replace(' page', '').strip()

        if page_name in pages:
            url = pages[page_name]

        # Build full URL
        if not url.startswith(('http://', 'https://')):
            base_url = self.env_config.get('base_url', '')
            url = f"{base_url.rstrip('/')}"

        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')
        return {'url': url}

    async def _handle_login_as_role(self, params: Dict) -> Any:
        """Handle role-based login"""
        role = params.get('role', '')

        # Get credentials from config
        roles = self.env_config.get('roles', {})
        if role not in roles:
            raise Exception(f"Role '{role}' not found in configuration")

        role_config = roles[role]
        username = role_config.get('username', '')
        password = role_config.get('password', '')

        # Navigate to login page if not already there
        if 'login' not in self.page.url.lower():
            await self._handle_navigate({'url': 'login page'})

        logger.info(f"Filling login form for role: {role}")

        # Look for username field using various selectors
        username_selectors = [
            'input[name="username"]',
            'input[type="text"][name="username"]',
            'input#username',
            'input[placeholder*="username" i]',
            'input[placeholder*="user" i]',
            'input[type="text"]:visible',
            'input[type="email"]'
        ]

        username_field = None
        for selector in username_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0 and await element.is_visible():
                    username_field = element
                    logger.info(f"Found username field with selector: {selector}")
                    break
            except:
                continue

        if username_field:
            await username_field.fill(username)
        else:
            # Fallback to element detector
            await self._handle_input({'element': 'Username', 'value': username})

        # Look for password field
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input#password',
            'input[placeholder*="password" i]'
        ]

        password_field = None
        for selector in password_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0 and await element.is_visible():
                    password_field = element
                    logger.info(f"Found password field with selector: {selector}")
                    break
            except:
                continue

        if password_field:
            await password_field.fill(password)
        else:
            # Fallback to element detector
            await self._handle_input({'element': 'Password', 'value': password})

        # Find and click the submit button
        submit_selectors = [
            'input#kc-login[type="submit"]',
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Sign In")',
            'button:has-text("Log In")',
            'button:has-text("Login")',
            'input[value="Sign In"]',
            'input[value="Log In"]',
            'input[value="Login"]',
            '.kc-form-buttons input[type="submit"]',
        ]

        clicked = False
        for selector in submit_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0 and await element.is_visible():
                    await element.click()
                    logger.info(f"Clicked submit button with selector: {selector}")
                    clicked = True
                    break
            except:
                continue

        if not clicked:
            # Try to find any visible submit button
            try:
                buttons = await self.page.locator('button:visible, input[type="submit"]:visible').all()
                for button in buttons:
                    text = await button.get_attribute('value') or await button.text_content() or ''
                    if any(word in text.lower() for word in ['sign', 'log', 'submit', 'enter']):
                        await button.click()
                        logger.info(f"Clicked button with text: {text}")
                        clicked = True
                        break
            except:
                pass

        if not clicked:
            raise Exception("Could not find login/submit button")

        # Wait for navigation after login
        logger.info("Waiting for navigation after login")
        try:
            await self.page.wait_for_url(lambda url: 'login' not in url.lower(), timeout=10000)
        except:
            await self.page.wait_for_load_state('networkidle')

        await asyncio.sleep(2)

        return {'logged_in': True, 'role': role}

    async def _handle_click(self, params: Dict) -> Any:
        """Handle click actions with improved button detection"""
        element_desc = params.get('element', '')

        logger.info(f"Attempting to click: {element_desc}")

        # Special handling for "Next" button
        if element_desc.lower() == "next":
            # Try multiple selectors specifically for Next button
            next_button_selectors = [
                # Exact text matches
                'button:text-is("Next")',
                'button:text-is("Next"):visible',

                # Ant Design patterns
                '.ant-btn:text-is("Next")',
                '.ant-btn:text-is("Next"):visible',
                '.ant-btn-primary:text-is("Next")',
                'button.ant-btn:text-is("Next")',

                # Has-text variations
                'button:has-text("Next"):visible',
                '.ant-btn:has-text("Next"):visible',

                # Generic button with text
                '*[class*="btn"]:text-is("Next"):visible',
                '*[class*="button"]:text-is("Next"):visible',

                # By role
                '[role="button"]:text-is("Next")',

                # Last resort - any visible element with exact "Next" text
                '*:text-is("Next"):visible',
            ]

            for selector in next_button_selectors:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()

                    if count > 0:
                        # Try each matching element
                        for i in range(count):
                            element = elements.nth(i)

                            # Verify it's actually visible and enabled
                            if await element.is_visible() and await element.is_enabled():
                                # Additional check to ensure it's a clickable element
                                is_clickable = await element.evaluate("""
                                    (el) => {
                                        const tag = el.tagName.toLowerCase();
                                        const role = el.getAttribute('role') || '';
                                        const type = el.getAttribute('type') || '';
                                        const classes = el.className || '';
                                        const cursor = window.getComputedStyle(el).cursor;

                                        return tag === 'button' || 
                                               tag === 'a' ||
                                               type === 'button' || 
                                               type === 'submit' ||
                                               role === 'button' ||
                                               classes.includes('btn') ||
                                               classes.includes('button') ||
                                               cursor === 'pointer';
                                    }
                                """)

                                if is_clickable:
                                    logger.info(f"Found Next button with selector: {selector}, index: {i}")

                                    # Scroll into view if needed
                                    await element.scroll_into_view_if_needed()

                                    # Small delay to ensure element is ready
                                    await asyncio.sleep(0.1)

                                    # Click the button
                                    await element.click()

                                    logger.info(f"Successfully clicked Next button")

                                    # Wait for any navigation or state change
                                    try:
                                        # Wait for either navigation or DOM change
                                        await self.page.wait_for_load_state('networkidle', timeout=5000)
                                    except:
                                        # If no navigation, just wait a bit for DOM updates
                                        await asyncio.sleep(1)

                                    return {'clicked': element_desc}

                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            # If specific Next button selectors fail, try generic approach
            logger.warning("Could not find Next button with specific selectors, trying generic approach")

        # Generic click handling for other elements
        try:
            # First try direct selectors for common elements
            if element_desc.lower() == "challenges":
                selectors = [
                    'a:has-text("Challenges")',
                    'button:has-text("Challenges")',
                    '[href*="challenges"]',
                    'nav a:has-text("Challenges")',
                    '.menu a:has-text("Challenges")',
                    '.sidebar a:has-text("Challenges")',
                    '[role="navigation"] a:has-text("Challenges")',
                    'li:has-text("Challenges") a',
                    'span:has-text("Challenges")',
                    'div:has-text("Challenges")'
                ]

                for selector in selectors:
                    try:
                        element = self.page.locator(selector).first
                        if await element.count() > 0 and await element.is_visible():
                            await element.click()
                            logger.info(f"Clicked {element_desc} using selector: {selector}")
                            await self.page.wait_for_load_state('networkidle')
                            return {'clicked': element_desc}
                    except:
                        continue

            # Fallback to element detector
            element = await self.element_detector.find_async(
                self.page,
                f"Click {element_desc}"
            )

            # Ensure element is ready
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.1)

            await element.click()

            # Wait for any navigation
            try:
                await self.page.wait_for_load_state('networkidle', timeout=3000)
            except:
                await asyncio.sleep(0.5)

            return {'clicked': element_desc}

        except Exception as e:
            logger.error(f"Failed to click '{element_desc}': {e}")
            raise Exception(f"Could not click element: {element_desc}")

    async def _handle_input(self, params: Dict) -> Any:
        """Handle input actions"""
        element_desc = params.get('element', '')
        value = params.get('value', '')
        force_ai = params.get('force_ai', False)

        logger.info(f"Attempting to input into: {element_desc}")

        # First check if this is likely a rich text editor
        is_rich_text = any(keyword in element_desc.lower() for keyword in [
            'about', 'description', 'content', 'editor', 'rich text', 'message', 'details'
        ])

        if is_rich_text or force_ai:
            logger.info(f"Detected rich text editor for: {element_desc}")

            # Try to find the rich text editor using the form item approach
            form_item_selector = f'.ant-form-item:has(label:text-is("{element_desc}"))'
            try:
                form_items = self.page.locator(form_item_selector)
                count = await form_items.count()

                if count > 0:
                    form_item = form_items.first

                    # Look for editors within this form item
                    editor_selectors = ['.ql-editor', '[contenteditable="true"]']

                    for editor_sel in editor_selectors:
                        editor = form_item.locator(editor_sel).first
                        if await editor.count() > 0 and await editor.is_visible():
                            logger.info(f"Found editor in form item using: {editor_sel}")

                            # Click to focus
                            await editor.click()
                            await asyncio.sleep(0.2)

                            # Clear existing content
                            await editor.click(click_count=3)  # Triple click to select all
                            await self.page.keyboard.press('Delete')

                            # Type new content
                            await self.page.keyboard.type(value)

                            logger.info("Successfully typed into rich text editor")
                            return {'typed': value, 'element': element_desc}

            except Exception as e:
                logger.debug(f"Form item approach failed: {e}")

            # Fallback to original rich text editor search
            rich_editor_selectors = [
                # Most specific selectors based on diagnostic
                f'.ant-form-item:has(label:text-is("{element_desc}")) .ql-editor',
                f'.ant-form-item:has(label:has-text("{element_desc}")) .ql-editor',
                # Quill editor patterns
                '.ql-editor',
                '.ql-container .ql-editor',
                '[class*="ql-editor"]',
                # Generic contenteditable
                '[contenteditable="true"]',
                # Other common editors
                '.editor-content',
                '.rich-text-editor',
                '[role="textbox"][contenteditable="true"]',
            ]

            for selector in rich_editor_selectors:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        element = elements.first
                        if await element.is_visible():
                            logger.info(f"Found rich text editor with selector: {selector}")

                            # Click to focus
                            await element.click()
                            await asyncio.sleep(0.2)

                            # Clear existing content
                            await element.click(click_count=3)  # Triple click to select all
                            await self.page.keyboard.press('Delete')

                            # Type new content
                            await self.page.keyboard.type(value)

                            logger.info("Successfully typed into rich text editor")
                            return {'typed': value, 'element': element_desc}
                except Exception as e:
                    logger.debug(f"Rich text selector {selector} failed: {e}")
                    continue

        # If not rich text or rich text selectors failed, try standard approach
        try:
            # Find element using detector
            element = await self.element_detector.find_async(
                self.page,
                f"Enter {element_desc}"
            )

            # Check if it's a contenteditable element
            is_contenteditable = await element.evaluate(
                "el => el.contentEditable === 'true' || el.classList.contains('ql-editor')"
            )

            if is_contenteditable:
                # Handle as rich text editor
                await element.click()
                await asyncio.sleep(0.2)

                # Clear content
                await element.click(click_count=3)
                await self.page.keyboard.press('Delete')

                # Type new content
                await self.page.keyboard.type(value)

                return {'typed': value, 'element': element_desc}
            else:
                # Standard input field
                await element.clear()
                await element.fill(value)

                return {'typed': value, 'element': element_desc}

        except Exception as e:
            logger.error(f"Failed to input into {element_desc}: {e}")
            raise Exception(f"Could not input into field: {element_desc}")

    async def _handle_select(self, params: Dict) -> Any:
        """Enhanced dropdown selection handler"""
        option = params.get('option', '')
        dropdown = params.get('element', '')

        logger.info(f"Selecting '{option}' from dropdown: {dropdown if dropdown else 'unnamed'}")

        # Strategy 1: Try to find and click the dropdown trigger first
        if dropdown:
            # Common dropdown trigger selectors
            dropdown_selectors = [
                f'[aria-label*="{dropdown}" i]',
                f'[placeholder*="{dropdown}" i]',
                f'.ant-select:has-text("{dropdown}")',
                f'[class*="select"]:has-text("{dropdown}")',
                f'select[name*="{dropdown}" i]',
                f'div[class*="dropdown"]:has-text("{dropdown}")',
                # Generic dropdown patterns
                '.ant-select-selector',
                '[class*="select-trigger"]',
                '[class*="dropdown-trigger"]',
                '[role="combobox"]',
            ]

            dropdown_clicked = False
            for selector in dropdown_selectors:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        element = elements.first
                        if await element.is_visible():
                            await element.click()
                            logger.info(f"Clicked dropdown trigger: {selector}")
                            dropdown_clicked = True
                            break
                except Exception as e:
                    logger.debug(f"Dropdown selector failed: {selector} - {e}")
                    continue

            if not dropdown_clicked:
                logger.warning("Could not find specific dropdown, will try to click any visible dropdown")

        # Wait for dropdown to open
        await asyncio.sleep(0.5)

        # Strategy 2: Look for the option in dropdown menus
        # Enhanced selectors for dropdown options
        option_selectors = [
            # Ant Design patterns
            f'.ant-dropdown-menu-item:has-text("{option}")',
            f'.ant-select-dropdown .ant-select-item:has-text("{option}")',
            f'.ant-select-dropdown-menu-item:has-text("{option}")',
            f'li.ant-dropdown-menu-item:has-text("{option}")',

            # Generic dropdown patterns
            f'[role="option"]:has-text("{option}")',
            f'li[role="option"]:has-text("{option}")',
            f'.dropdown-menu li:has-text("{option}")',
            f'.dropdown-item:has-text("{option}")',
            f'[class*="menu-item"]:has-text("{option}")',
            f'[class*="option"]:has-text("{option}")',

            # By data attributes
            f'[data-menu-id*="{option}" i]',
            f'[data-value*="{option}" i]',
            f'[data-option*="{option}" i]',

            # Select/Option tags
            f'option:has-text("{option}")',
            f'select option:has-text("{option}")',

            # Generic list items
            f'ul li:has-text("{option}")',
            f'.menu li:has-text("{option}")',

            # Exact text match
            f'*:text-is("{option}")',
        ]

        # Try each selector
        for selector in option_selectors:
            try:
                # Wait for dropdown items to be visible
                await self.page.wait_for_selector(selector, state='visible', timeout=2000)

                elements = self.page.locator(selector)
                count = await elements.count()

                if count > 0:
                    # If multiple matches, try to find the most specific one
                    best_match = None

                    for i in range(count):
                        element = elements.nth(i)
                        if await element.is_visible():
                            # Check if it's in a dropdown context
                            parent_classes = await element.evaluate("""
                                (el) => {
                                    let parent = el.parentElement;
                                    let classes = [];
                                    while (parent && classes.length < 5) {
                                        if (parent.className) {
                                            classes.push(parent.className);
                                        }
                                        parent = parent.parentElement;
                                    }
                                    return classes.join(' ');
                                }
                            """)

                            # Prefer elements in dropdown contexts
                            if any(dropdown_class in parent_classes.lower() for dropdown_class in
                                   ['dropdown', 'select', 'menu', 'options', 'popup']):
                                best_match = element
                                break
                            elif not best_match:
                                best_match = element

                    if best_match:
                        await best_match.click()
                        logger.info(f"Selected option '{option}' using selector: {selector}")

                        # Wait for dropdown to close
                        await asyncio.sleep(0.3)
                        return {'selected': option, 'dropdown': dropdown}

            except Exception as e:
                logger.debug(f"Option selector failed: {selector} - {e}")
                continue

        # Strategy 3: Try clicking on the option text directly if visible
        try:
            # Use detector to find the option
            option_elem = await self.element_detector.find_async(
                self.page,
                f"Click {option}"
            )

            # Verify it's in a dropdown context before clicking
            is_in_dropdown = await option_elem.evaluate("""
                (el) => {
                    let parent = el;
                    for (let i = 0; i < 5; i++) {
                        if (!parent) break;
                        const classes = parent.className || '';
                        const role = parent.getAttribute('role') || '';
                        if (classes.includes('dropdown') || classes.includes('select') || 
                            classes.includes('menu') || role === 'listbox' || role === 'menu') {
                            return true;
                        }
                        parent = parent.parentElement;
                    }
                    return false;
                }
            """)

            if is_in_dropdown:
                await option_elem.click()
                logger.info(f"Selected option using element detector")
                return {'selected': option, 'dropdown': dropdown}
            else:
                logger.warning(f"Found element '{option}' but it's not in a dropdown context")

        except Exception as e:
            logger.error(f"Failed to select option using element detector: {e}")

        # If all strategies fail
        raise Exception(f"Could not select option '{option}' from dropdown" +
                       (f" '{dropdown}'" if dropdown else ""))

    async def _handle_radio(self, params: Dict) -> Any:
        """Handle radio button selection"""
        element_desc = params.get('element', '')

        # Try specific radio button selectors first
        radio_selectors = [
            f'input[type="radio"][value="{element_desc}"]',
            f'input[type="radio"][id*="{element_desc}" i]',
            f'label:has-text("{element_desc}") input[type="radio"]',
            f'input[type="radio"] + label:has-text("{element_desc}")',
            f'.ant-radio-wrapper:has-text("{element_desc}") input',
            f'[role="radio"][aria-label*="{element_desc}" i]',
        ]

        for selector in radio_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0:
                    await element.click()
                    logger.info(f"Selected radio button using selector: {selector}")
                    return {'selected': element_desc}
            except:
                continue

        # Fallback to detector
        radio = await self.element_detector.find_async(
            self.page,
            f"Click {element_desc} radio button"
        )
        await radio.click()

        return {'selected': element_desc}

    async def _handle_checkbox(self, params: Dict) -> Any:
        """Handle checkbox selection"""
        element_desc = params.get('element', '')

        # Try specific checkbox selectors first
        checkbox_selectors = [
            f'input[type="checkbox"][value="{element_desc}"]',
            f'input[type="checkbox"][id*="{element_desc}" i]',
            f'label:has-text("{element_desc}") input[type="checkbox"]',
            f'input[type="checkbox"] + label:has-text("{element_desc}")',
            f'.ant-checkbox-wrapper:has-text("{element_desc}") input',
            f'[role="checkbox"][aria-label*="{element_desc}" i]',
        ]

        for selector in checkbox_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0:
                    # Check if already checked
                    is_checked = await element.is_checked()
                    if not is_checked:
                        await element.click()
                    logger.info(f"Selected checkbox using selector: {selector}")
                    return {'checked': element_desc}
            except:
                continue

        # Fallback to detector
        checkbox = await self.element_detector.find_async(
            self.page,
            f"Click {element_desc} checkbox"
        )
        await checkbox.click()

        return {'checked': element_desc}

    async def _handle_verify_text(self, params: Dict) -> Any:
        """Verify text on page"""
        text = params.get('text', '')

        # Wait for text to appear
        await self.page.wait_for_selector(f'text="{text}"', timeout=5000)

        return {'verified': text}

    async def _handle_verify_selected(self, params: Dict) -> Any:
        """Verify element is selected"""
        element_desc = params.get('element', '')

        # Check for radio button
        radio_selectors = [
            f'input[type="radio"][value="{element_desc}"]:checked',
            f'label:has-text("{element_desc}") input[type="radio"]:checked',
        ]

        for selector in radio_selectors:
            try:
                element = self.page.locator(selector)
                if await element.count() > 0:
                    return {'verified': element_desc, 'type': 'radio'}
            except:
                continue

        # Check for checkbox
        checkbox_selectors = [
            f'input[type="checkbox"][value="{element_desc}"]:checked',
            f'label:has-text("{element_desc}") input[type="checkbox"]:checked',
        ]

        for selector in checkbox_selectors:
            try:
                element = self.page.locator(selector)
                if await element.count() > 0:
                    return {'verified': element_desc, 'type': 'checkbox'}
            except:
                continue

        # Check for selected option in dropdown
        option_selectors = [
            f'option:has-text("{element_desc}")[selected]',
            f'.ant-select-selection-item:has-text("{element_desc}")',
        ]

        for selector in option_selectors:
            try:
                element = self.page.locator(selector)
                if await element.count() > 0:
                    return {'verified': element_desc, 'type': 'option'}
            except:
                continue

        raise Exception(f"Could not verify '{element_desc}' is selected")

    async def _handle_generate_datetime(self, params: Dict) -> Any:
        """Generate datetime and store in context"""
        datetime_spec = params.get('datetime_spec', '')
        variable_name = params.get('variable_name', '')

        # Parse datetime specification
        now = datetime.now()
        result_dt = now

        # Parse relative dates
        if 'tomorrow' in datetime_spec:
            result_dt = now + timedelta(days=1)
        elif 'days from now' in datetime_spec:
            match = re.search(r'(\d+) days from now', datetime_spec)
            if match:
                days = int(match.group(1))
                result_dt = now + timedelta(days=days)

        # Parse time
        time_match = re.search(r'at (\d+):(\d+) (am|pm)', datetime_spec)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            am_pm = time_match.group(3)

            if am_pm == 'pm' and hour != 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0

            result_dt = result_dt.replace(hour=hour, minute=minute)

        # Format and store
        formatted = result_dt.strftime('%Y/%m/%d %H:%M')
        self.context_data[variable_name] = formatted

        return {'generated': formatted, 'stored_as': variable_name}

    async def _handle_select_date_range(self, params: Dict) -> Any:
        """Handle date range selection"""
        start_var = params.get('start_var', '')
        end_var = params.get('end_var', '')
        field = params.get('field', '')

        # Get stored dates
        start_date = self.context_data.get(start_var, '')
        end_date = self.context_data.get(end_var, '')

        # Find and fill date range field
        element = await self.element_detector.find_async(
            self.page,
            f"Enter {field}"
        )

        # This might need custom handling based on your date picker
        await element.click()
        await element.fill(f"{start_date} - {end_date}")

        return {'start': start_date, 'end': end_date, 'field': field}