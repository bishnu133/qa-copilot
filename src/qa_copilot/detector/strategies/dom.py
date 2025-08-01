import re
from typing import Any, Dict, List, Optional, Union
from playwright.sync_api import Page as SyncPage, Locator as SyncLocator
from playwright.async_api import Page as AsyncPage, Locator as AsyncLocator
import logging

from .base import DetectionStrategy
from ..utils import normalize_text, fuzzy_match

logger = logging.getLogger(__name__)


class DOMStrategy(DetectionStrategy):
    """
    Enhanced DOM-based element detection strategy with improved label-input association.
    Supports both sync and async operations.
    """

    @property
    def name(self) -> str:
        return "DOM"

    @property
    def priority(self) -> int:
        return 1  # Highest priority

    def find(self, page: SyncPage, description: Dict[str, Any]) -> Optional[SyncLocator]:
        """Synchronous find method"""
        element_type = description.get("element_type") or description.get("type", "")
        if element_type:
            element_type = element_type.lower()
        text = description.get("target") or description.get("text", "")
        attributes = description.get("attributes", {})

        logger.info(f"DOM Strategy - Looking for: type={element_type}, text={text}, attributes={attributes}")

        # Special handling for button elements - ENHANCED
        if element_type == "button" or "button" in (text or "").lower():
            element = self._find_button_enhanced_sync(page, text, attributes)
            if element:
                return element

        # Enhanced handling for input fields with label detection
        if element_type == "input" or "field" in (text or "").lower():
            element = self._find_input_by_label_enhanced_sync(page, text)
            if element:
                return element

        # Try various strategies
        strategies = [
            self._find_by_exact_text_sync,
            self._find_by_partial_text_sync,
            self._find_by_id_or_name_sync,
            self._find_by_aria_label_sync,
            self._find_by_css_patterns_sync,
            self._find_by_role_sync,
        ]

        for strategy in strategies:
            try:
                element = strategy(page, element_type, text, attributes)
                if element and element.count() > 0:
                    first = element.first
                    if first.is_visible() and first.is_enabled():
                        logger.info(f"Found element using strategy: {strategy.__name__}")
                        return first
            except Exception as e:
                logger.debug(f"Strategy {strategy.__name__} failed: {e}")
                continue

        return None

    async def find_async(self, page: AsyncPage, description: Dict[str, Any]) -> Optional[AsyncLocator]:
        """Asynchronous find method"""
        element_type = description.get("element_type") or description.get("type", "")
        if element_type:
            element_type = element_type.lower()
        text = description.get("target") or description.get("text", "")
        attributes = description.get("attributes", {})

        logger.info(f"DOM Strategy (Async) - Looking for: type={element_type}, text={text}, attributes={attributes}")

        # Special handling for button elements - ENHANCED
        if element_type == "button" or "button" in (text or "").lower():
            element = await self._find_button_enhanced_async(page, text, attributes)
            if element:
                return element

        # Enhanced handling for input fields with label detection
        if element_type == "input" or "field" in (text or "").lower():
            element = await self._find_input_by_label_enhanced_async(page, text)
            if element:
                return element

        # Try various strategies
        strategies = [
            self._find_by_exact_text_async,
            self._find_by_partial_text_async,
            self._find_by_id_or_name_async,
            self._find_by_aria_label_async,
            self._find_by_css_patterns_async,
            self._find_by_role_async,
        ]

        for strategy in strategies:
            try:
                element = await strategy(page, element_type, text, attributes)
                if element and await element.count() > 0:
                    first = element.first
                    if await first.is_visible() and await first.is_enabled():
                        logger.info(f"Found element using strategy: {strategy.__name__}")
                        return first
            except Exception as e:
                logger.debug(f"Strategy {strategy.__name__} failed: {e}")
                continue

        return None

    def _find_input_by_label_enhanced_sync(self, page: SyncPage, text: str) -> Optional[SyncLocator]:
        """Enhanced method to find input fields by their labels - synchronous"""
        if not text:
            return None

        # Extract the field name from the description
        field_name = self._extract_field_name(text)
        if not field_name:
            return None

        logger.info(f"Looking for input field with label: '{field_name}'")

        # Strategy 1: Direct label with 'for' attribute
        label_element = self._find_label_element_sync(page, field_name)
        if label_element:
            input_element = self._find_input_from_label_sync(page, label_element)
            if input_element:
                logger.info(f"Found input using label 'for' attribute")
                return input_element

        # Strategy 2: Find text and look for nearby inputs
        text_element = self._find_text_element_sync(page, field_name)
        if text_element:
            input_element = self._find_nearby_input_sync(page, text_element, field_name)
            if input_element:
                logger.info(f"Found input near text element")
                return input_element

        # Strategy 3: Look for inputs with matching attributes
        input_element = self._find_input_by_attributes_sync(page, field_name)
        if input_element:
            logger.info(f"Found input by attributes")
            return input_element

        # Strategy 4: Find by form structure
        input_element = self._find_input_in_form_structure_sync(page, field_name)
        if input_element:
            logger.info(f"Found input in form structure")
            return input_element

        return None

    async def _find_input_by_label_enhanced_async(self, page: AsyncPage, text: str) -> Optional[AsyncLocator]:
        """Enhanced method to find input fields by their labels - asynchronous"""
        if not text:
            return None

        # Extract the field name from the description
        field_name = self._extract_field_name(text)
        if not field_name:
            return None

        logger.info(f"Looking for input field with label: '{field_name}'")

        # Check if this might be a rich text editor
        is_rich_text = any(keyword in field_name.lower() for keyword in [
            'about', 'description', 'content', 'editor', 'rich text', 'message', 'details', 'key details'
        ])

        if is_rich_text:
            # Strategy 1: Find the form item containing both the label and the editor
            # This is the most reliable approach for Ant Design forms
            form_item_selector = f'.ant-form-item:has(label:text-is("{field_name}"))'
            try:
                form_items = page.locator(form_item_selector)
                count = await form_items.count()

                if count > 0:
                    # Get the first matching form item
                    form_item = form_items.first

                    # Look for the editor within this form item
                    editor_selectors = [
                        '.ql-editor',  # Quill editor
                        '[contenteditable="true"]',
                        '.rich-text-editor',
                        '.editor-content'
                    ]

                    for editor_sel in editor_selectors:
                        editor = form_item.locator(editor_sel).first
                        if await editor.count() > 0 and await editor.is_visible():
                            logger.info(f"Found rich text editor in form item for '{field_name}'")
                            return editor

            except Exception as e:
                logger.debug(f"Form item strategy failed: {e}")

            # Strategy 2: Use more specific selectors based on diagnostic findings
            rich_selectors = [
                # Based on diagnostic output - this works
                f'.ant-form-item:has(label:text-is("{field_name}")) .ql-editor',
                # Try with partial match
                f'.ant-form-item:has(label:has-text("{field_name}")) .ql-editor',
                # Try contenteditable
                f'.ant-form-item:has(label:text-is("{field_name}")) [contenteditable="true"]',
                # More generic form structures
                f'div:has(> label:text-is("{field_name}")) ~ div .ql-editor',
                f'label:text-is("{field_name}") ~ * .ql-editor',
                # With row structure
                f'.ant-row:has(label:text-is("{field_name}")) .ql-editor',
            ]

            for selector in rich_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        element = elements.first
                        if await element.is_visible():
                            logger.info(f"Found rich text editor with selector: {selector}")
                            return element
                except Exception as e:
                    logger.debug(f"Rich text selector {selector} failed: {e}")
                    continue

    async def _find_standard_input_field_async(self, page: AsyncPage, field_name: str) -> Optional[AsyncLocator]:
        """Find standard input fields"""
        # Continue with standard label-based search
        label_element = await self._find_label_element_async(page, field_name)
        if label_element:
            input_element = await self._find_input_from_label_async(page, label_element)
            if input_element:
                logger.info(f"Found input using label 'for' attribute")
                return input_element

        # Strategy 2: Find by form structure (PRIORITIZED)
        input_element = await self._find_input_in_form_structure_async(page, field_name)
        if input_element:
            logger.info(f"Found input in form structure")
            return input_element

        # Strategy 3: Find text and look for nearby inputs
        text_element = await self._find_text_element_async(page, field_name)
        if text_element:
            input_element = await self._find_nearby_input_async(page, text_element, field_name)
            if input_element:
                logger.info(f"Found input near text element")
                return input_element

        # Strategy 4: Look for inputs with matching attributes
        input_element = await self._find_input_by_attributes_async(page, field_name)
        if input_element:
            logger.info(f"Found input by attributes")
            return input_element

        return None

    def _extract_field_name(self, text: str) -> str:
        """Extract the actual field name from the description"""
        # Remove common prefixes
        prefixes_to_remove = ['enter', 'type', 'fill', 'input', 'in the', 'in', 'the']

        text_lower = text.lower()
        for prefix in prefixes_to_remove:
            if text_lower.startswith(prefix + ' '):
                text = text[len(prefix):].strip()
                text_lower = text.lower()

        # Remove 'field' suffix
        if text_lower.endswith(' field'):
            text = text[:-6].strip()

        return text

    def _find_label_element_sync(self, page: SyncPage, field_name: str) -> Optional[SyncLocator]:
        """Find label element with exact or fuzzy match - synchronous"""
        # Try exact match first
        selectors = [
            f'label:text-is("{field_name}")',
            f'label:has-text("{field_name}")',
            f'*[class*="label"]:text-is("{field_name}")',
            f'*[class*="label"]:has-text("{field_name}")',
            f'*[class*="form-label"]:has-text("{field_name}")',
            f'*[class*="field-label"]:has-text("{field_name}")',
            f'*[class*="input-label"]:has-text("{field_name}")',
        ]

        for selector in selectors:
            try:
                labels = page.locator(selector)
                if labels.count() > 0:
                    # Return the most specific match
                    return labels.first
            except:
                continue

        return None

    async def _find_label_element_async(self, page: AsyncPage, field_name: str) -> Optional[AsyncLocator]:
        """Find label element with exact or fuzzy match - asynchronous"""
        selectors = [
            f'label:text-is("{field_name}")',
            f'label:has-text("{field_name}")',
            f'*[class*="label"]:text-is("{field_name}")',
            f'*[class*="label"]:has-text("{field_name}")',
            f'*[class*="form-label"]:has-text("{field_name}")',
            f'*[class*="field-label"]:has-text("{field_name}")',
            f'*[class*="input-label"]:has-text("{field_name}")',
        ]

        for selector in selectors:
            try:
                labels = page.locator(selector)
                if await labels.count() > 0:
                    return labels.first
            except:
                continue

        return None

    def _find_input_from_label_sync(self, page: SyncPage, label: SyncLocator) -> Optional[SyncLocator]:
        """Find input associated with label - synchronous"""
        try:
            # Check for 'for' attribute
            for_attr = label.get_attribute('for')
            if for_attr:
                input_elem = page.locator(f'#{for_attr}')
                if input_elem.count() > 0 and input_elem.first.is_visible():
                    return input_elem.first

            # Check if input is inside label
            input_inside = label.locator('input, textarea, select')
            if input_inside.count() > 0:
                return input_inside.first

            # Check next sibling
            next_input = label.locator('~ input, ~ textarea, ~ select').first
            if next_input.count() > 0 and next_input.is_visible():
                return next_input

            # Check parent's next sibling
            parent = label.locator('..')
            next_elem = parent.locator('~ * input, ~ * textarea, ~ * select').first
            if next_elem.count() > 0 and next_elem.is_visible():
                return next_elem

        except Exception as e:
            logger.debug(f"Error finding input from label: {e}")

        return None

    async def _find_input_from_label_async(self, page: AsyncPage, label: AsyncLocator) -> Optional[AsyncLocator]:
        """Find input associated with label - asynchronous"""
        try:
            # Check for 'for' attribute
            for_attr = await label.get_attribute('for')
            if for_attr:
                input_elem = page.locator(f'#{for_attr}')
                if await input_elem.count() > 0 and await input_elem.first.is_visible():
                    return input_elem.first

            # Check if input is inside label
            input_inside = label.locator('input, textarea, select')
            if await input_inside.count() > 0:
                return input_inside.first

            # Check next sibling
            next_input = label.locator('~ input, ~ textarea, ~ select').first
            if await next_input.count() > 0 and await next_input.is_visible():
                return next_input

            # Check parent's next sibling
            parent = label.locator('..')
            next_elem = parent.locator('~ * input, ~ * textarea, ~ * select').first
            if await next_elem.count() > 0 and await next_elem.is_visible():
                return next_elem

        except Exception as e:
            logger.debug(f"Error finding input from label: {e}")

        return None

    def _find_text_element_sync(self, page: SyncPage, field_name: str) -> Optional[SyncLocator]:
        """Find any text element containing the field name - synchronous"""
        selectors = [
            f'*:text-is("{field_name}")',
            f'*:has-text("{field_name}")',
            f'span:has-text("{field_name}")',
            f'div:has-text("{field_name}")',
            f'p:has-text("{field_name}")',
        ]

        for selector in selectors:
            try:
                elements = page.locator(selector)
                # Get the smallest element containing the text
                for i in range(min(elements.count(), 5)):
                    elem = elements.nth(i)
                    # Check if this element directly contains the text (not in children)
                    text_content = elem.evaluate("""
                        (el) => {
                            // Get direct text content, not from children
                            let text = '';
                            for (let node of el.childNodes) {
                                if (node.nodeType === Node.TEXT_NODE) {
                                    text += node.textContent;
                                }
                            }
                            return text.trim();
                        }
                    """)
                    if field_name.lower() in text_content.lower():
                        return elem
            except:
                continue

        return None

    async def _find_text_element_async(self, page: AsyncPage, field_name: str) -> Optional[AsyncLocator]:
        """Find any text element containing the field name - asynchronous"""
        selectors = [
            f'*:text-is("{field_name}")',
            f'*:has-text("{field_name}")',
            f'span:has-text("{field_name}")',
            f'div:has-text("{field_name}")',
            f'p:has-text("{field_name}")',
        ]

        for selector in selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                for i in range(min(count, 5)):
                    elem = elements.nth(i)
                    # Check if this element directly contains the text
                    text_content = await elem.evaluate("""
                        (el) => {
                            let text = '';
                            for (let node of el.childNodes) {
                                if (node.nodeType === Node.TEXT_NODE) {
                                    text += node.textContent;
                                }
                            }
                            return text.trim();
                        }
                    """)
                    if field_name.lower() in text_content.lower():
                        return elem
            except:
                continue

        return None

    def _find_nearby_input_sync(self, page: SyncPage, text_element: SyncLocator, field_name: str) -> Optional[
        SyncLocator]:
        """Find input near text element - synchronous"""
        try:
            # Use JavaScript to find the nearest input element
            nearest_input = text_element.evaluate("""
                (el, fieldName) => {
                    // Helper function to calculate distance between elements
                    function getDistance(elem1, elem2) {
                        const rect1 = elem1.getBoundingClientRect();
                        const rect2 = elem2.getBoundingClientRect();
                        const centerX1 = rect1.left + rect1.width / 2;
                        const centerY1 = rect1.top + rect1.height / 2;
                        const centerX2 = rect2.left + rect2.width / 2;
                        const centerY2 = rect2.top + rect2.height / 2;
                        return Math.sqrt(Math.pow(centerX2 - centerX1, 2) + Math.pow(centerY2 - centerY1, 2));
                    }

                    // Find all input elements on the page
                    const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select, [contenteditable="true"], .ant-input');
                    let nearestInput = null;
                    let minDistance = Infinity;

                    for (let input of inputs) {
                        if (!input.offsetParent) continue; // Skip invisible elements

                        const distance = getDistance(el, input);

                        // Prefer inputs that are:
                        // 1. Below the label (positive Y difference)
                        // 2. To the right of the label (positive X difference)
                        // 3. Within reasonable proximity
                        const rect1 = el.getBoundingClientRect();
                        const rect2 = input.getBoundingClientRect();
                        const yDiff = rect2.top - rect1.top;
                        const xDiff = rect2.left - rect1.left;

                        // Scoring system
                        let score = distance;

                        // Prefer elements below
                        if (yDiff > 0 && yDiff < 100) {
                            score -= 1000;
                        }

                        // Prefer elements to the right
                        if (xDiff > 0 && xDiff < 300) {
                            score -= 500;
                        }

                        // Check if input already has a value (penalize)
                        if (input.value && input.value.trim() !== '') {
                            score += 2000;
                        }

                        if (score < minDistance) {
                            minDistance = score;
                            nearestInput = input;
                        }
                    }

                    return nearestInput;
                }
            """, field_name)

            if nearest_input:
                # Return a locator for the found element
                # Try to create a unique selector
                selector = self._create_unique_selector_sync(page, nearest_input)
                if selector:
                    return page.locator(selector)

        except Exception as e:
            logger.debug(f"Error finding nearby input: {e}")

        return None

    async def _find_nearby_input_async(self, page: AsyncPage, text_element: AsyncLocator, field_name: str) -> Optional[
        AsyncLocator]:
        """Find input near text element - asynchronous"""
        try:
            nearest_input = await text_element.evaluate("""
                (el, fieldName) => {
                    function getDistance(elem1, elem2) {
                        const rect1 = elem1.getBoundingClientRect();
                        const rect2 = elem2.getBoundingClientRect();
                        const centerX1 = rect1.left + rect1.width / 2;
                        const centerY1 = rect1.top + rect1.height / 2;
                        const centerX2 = rect2.left + rect2.width / 2;
                        const centerY2 = rect2.top + rect2.height / 2;
                        return Math.sqrt(Math.pow(centerX2 - centerX1, 2) + Math.pow(centerY2 - centerY1, 2));
                    }

                    const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select, [contenteditable="true"], .ant-input');
                    let nearestInput = null;
                    let minDistance = Infinity;

                    for (let input of inputs) {
                        if (!input.offsetParent) continue;

                        const distance = getDistance(el, input);
                        const rect1 = el.getBoundingClientRect();
                        const rect2 = input.getBoundingClientRect();
                        const yDiff = rect2.top - rect1.top;
                        const xDiff = rect2.left - rect1.left;

                        let score = distance;

                        if (yDiff > 0 && yDiff < 100) {
                            score -= 1000;
                        }

                        if (xDiff > 0 && xDiff < 300) {
                            score -= 500;
                        }

                        if (input.value && input.value.trim() !== '') {
                            score += 2000;
                        }

                        if (score < minDistance) {
                            minDistance = score;
                            nearestInput = input;
                        }
                    }

                    return nearestInput;
                }
            """, field_name)

            if nearest_input:
                selector = await self._create_unique_selector_async(page, nearest_input)
                if selector:
                    return page.locator(selector)

        except Exception as e:
            logger.debug(f"Error finding nearby input: {e}")

        return None

    def _create_unique_selector_sync(self, page: SyncPage, element_handle) -> Optional[str]:
        """Create a unique selector for an element - synchronous"""
        try:
            selector = page.evaluate("""
                (el) => {
                    // Try to create a unique selector
                    if (el.id) return '#' + el.id;

                    if (el.name) return el.tagName.toLowerCase() + '[name="' + el.name + '"]';

                    if (el.className) {
                        const classes = el.className.split(' ').filter(c => c).join('.');
                        if (classes) return el.tagName.toLowerCase() + '.' + classes;
                    }

                    // Use nth-child as last resort
                    let path = [];
                    let current = el;
                    while (current && current.nodeType === Node.ELEMENT_NODE) {
                        let selector = current.tagName.toLowerCase();
                        if (current.id) {
                            selector = '#' + current.id;
                            path.unshift(selector);
                            break;
                        }
                        let sibling = current;
                        let nth = 1;
                        while (sibling.previousElementSibling) {
                            sibling = sibling.previousElementSibling;
                            if (sibling.tagName === current.tagName) nth++;
                        }
                        if (nth > 1) selector += ':nth-of-type(' + nth + ')';
                        path.unshift(selector);
                        current = current.parentElement;
                    }
                    return path.join(' > ');
                }
            """, element_handle)
            return selector
        except:
            return None

    async def _create_unique_selector_async(self, page: AsyncPage, element_handle) -> Optional[str]:
        """Create a unique selector for an element - asynchronous"""
        try:
            selector = await page.evaluate("""
                (el) => {
                    if (el.id) return '#' + el.id;

                    if (el.name) return el.tagName.toLowerCase() + '[name="' + el.name + '"]';

                    if (el.className) {
                        const classes = el.className.split(' ').filter(c => c).join('.');
                        if (classes) return el.tagName.toLowerCase() + '.' + classes;
                    }

                    let path = [];
                    let current = el;
                    while (current && current.nodeType === Node.ELEMENT_NODE) {
                        let selector = current.tagName.toLowerCase();
                        if (current.id) {
                            selector = '#' + current.id;
                            path.unshift(selector);
                            break;
                        }
                        let sibling = current;
                        let nth = 1;
                        while (sibling.previousElementSibling) {
                            sibling = sibling.previousElementSibling;
                            if (sibling.tagName === current.tagName) nth++;
                        }
                        if (nth > 1) selector += ':nth-of-type(' + nth + ')';
                        path.unshift(selector);
                        current = current.parentElement;
                    }
                    return path.join(' > ');
                }
            """, element_handle)
            return selector
        except:
            return None

    def _find_input_by_attributes_sync(self, page: SyncPage, field_name: str) -> Optional[SyncLocator]:
        """Find input by attributes - synchronous"""
        # Normalize field name for attribute matching
        field_variations = self._generate_field_variations(field_name)

        selectors = []
        for variation in field_variations:
            selectors.extend([
                f'input[placeholder*="{variation}" i]',
                f'textarea[placeholder*="{variation}" i]',
                f'input[name*="{variation}" i]',
                f'textarea[name*="{variation}" i]',
                f'input[id*="{variation}" i]',
                f'textarea[id*="{variation}" i]',
                f'input[aria-label*="{variation}" i]',
                f'textarea[aria-label*="{variation}" i]',
                f'[contenteditable="true"][aria-label*="{variation}" i]',
                f'.ant-input[placeholder*="{variation}" i]',
            ])

        for selector in selectors:
            try:
                elements = page.locator(selector)
                if elements.count() > 0:
                    # Return first visible and empty input
                    for i in range(elements.count()):
                        elem = elements.nth(i)
                        if elem.is_visible() and elem.is_enabled():
                            # Check if input is empty
                            try:
                                value = elem.input_value() if hasattr(elem, 'input_value') else elem.get_attribute('value')
                                if not value or value.strip() == '':
                                    return elem
                            except:
                                # If input_value fails, it might not be a standard input
                                pass
                    # If no empty input found, return first visible
                    for i in range(elements.count()):
                        elem = elements.nth(i)
                        if elem.is_visible() and elem.is_enabled():
                            return elem
            except:
                continue

        return None

    async def _find_input_by_attributes_async(self, page: AsyncPage, field_name: str) -> Optional[AsyncLocator]:
        """Find input by attributes - asynchronous"""
        field_variations = self._generate_field_variations(field_name)

        selectors = []
        for variation in field_variations:
            selectors.extend([
                f'input[placeholder*="{variation}" i]',
                f'textarea[placeholder*="{variation}" i]',
                f'input[name*="{variation}" i]',
                f'textarea[name*="{variation}" i]',
                f'input[id*="{variation}" i]',
                f'textarea[id*="{variation}" i]',
                f'input[aria-label*="{variation}" i]',
                f'textarea[aria-label*="{variation}" i]',
                f'[contenteditable="true"][aria-label*="{variation}" i]',
                f'.ant-input[placeholder*="{variation}" i]',
            ])

        for selector in selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    # Return first visible and empty input
                    for i in range(count):
                        elem = elements.nth(i)
                        if await elem.is_visible() and await elem.is_enabled():
                            # Check if input is empty
                            value = await elem.input_value() if hasattr(elem,
                                                                        'input_value') else await elem.get_attribute(
                                'value')
                            if not value or value.strip() == '':
                                return elem
                    # If no empty input found, return first visible
                    return elements.first
            except:
                continue

        return None

    def _find_input_in_form_structure_sync(self, page: SyncPage, field_name: str) -> Optional[SyncLocator]:
        """Find input in form structure - synchronous"""
        try:
            # First try the most specific selector that we know works
            specific_selector = f'.ant-form-item:has(label:text-is("{field_name}")) input'
            element = page.locator(specific_selector).first
            if element.count() > 0 and element.is_visible():
                logger.info(f"Found input using specific form item selector: {specific_selector}")
                return element

            # Look for common form patterns
            form_selectors = [
                '.ant-form-item',
                '.form-group',
                '.form-field',
                '.field-wrapper',
                '.input-group',
                '[class*="form-item"]',
                '[class*="field-group"]',
            ]

            for form_selector in form_selectors:
                form_items = page.locator(form_selector)
                for i in range(min(form_items.count(), 20)):  # Limit to prevent hanging
                    form_item = form_items.nth(i)

                    # Check if this form item contains our field name
                    text_content = form_item.text_content()
                    if text_content and field_name.lower() in text_content.lower():
                        # Look for input within this form item
                        input_elem = form_item.locator('input, textarea, select, [contenteditable="true"]').first
                        if input_elem.count() > 0 and input_elem.is_visible():
                            return input_elem

        except Exception as e:
            logger.debug(f"Error finding input in form structure: {e}")

        return None

    async def _find_input_in_form_structure_async(self, page: AsyncPage, field_name: str) -> Optional[AsyncLocator]:
        """Find input in form structure - asynchronous"""
        try:
            # First try the most specific selector that we know works
            specific_selector = f'.ant-form-item:has(label:text-is("{field_name}")) input'
            element = page.locator(specific_selector).first
            if await element.count() > 0 and await element.is_visible():
                logger.info(f"Found input using specific form item selector: {specific_selector}")
                return element

            # Also try with textarea
            specific_selector_textarea = f'.ant-form-item:has(label:text-is("{field_name}")) textarea'
            element = page.locator(specific_selector_textarea).first
            if await element.count() > 0 and await element.is_visible():
                logger.info(f"Found textarea using specific form item selector: {specific_selector_textarea}")
                return element

            # Look for common form patterns
            form_selectors = [
                '.ant-form-item',
                '.form-group',
                '.form-field',
                '.field-wrapper',
                '.input-group',
                '[class*="form-item"]',
                '[class*="field-group"]',
            ]

            for form_selector in form_selectors:
                form_items = page.locator(form_selector)
                count = await form_items.count()
                for i in range(min(count, 20)):
                    form_item = form_items.nth(i)

                    text_content = await form_item.text_content()
                    if text_content and field_name.lower() in text_content.lower():
                        # Look for input within this form item
                        input_elem = form_item.locator('input, textarea, select, [contenteditable="true"]').first
                        if await input_elem.count() > 0 and await input_elem.is_visible():
                            return input_elem

        except Exception as e:
            logger.debug(f"Error finding input in form structure: {e}")

        return None

    def _generate_field_variations(self, field_name: str) -> List[str]:
        """Generate variations of field name for matching"""
        variations = [field_name]

        # Add lowercase version
        variations.append(field_name.lower())

        # Add versions with underscores and hyphens
        variations.append(field_name.replace(' ', '_'))
        variations.append(field_name.replace(' ', '-'))
        variations.append(field_name.replace(' ', ''))

        # Add camelCase version
        words = field_name.split()
        if len(words) > 1:
            camel_case = words[0].lower() + ''.join(w.capitalize() for w in words[1:])
            variations.append(camel_case)

        return list(set(variations))

    def _find_button_enhanced_sync(self, page: SyncPage, text: str, attributes: Dict) -> Optional[SyncLocator]:
        """Enhanced button finding logic - synchronous"""
        logger.info(f"Enhanced button search for: {text}")

        # Comprehensive button selectors
        selectors = [
            # Exact text match
            f'button:text-is("{text}")',
            f'button:has-text("{text}")',

            # Ant Design specific
            f'.ant-btn:text-is("{text}")',
            f'.ant-btn:has-text("{text}")',
            f'.ant-btn-primary:has-text("{text}")',

            # By role and text
            f'[role="button"]:text-is("{text}")',
            f'[role="button"]:has-text("{text}")',

            # Input buttons
            f'input[type="button"][value="{text}"]',
            f'input[type="submit"][value="{text}"]',

            # Generic button classes
            f'*[class*="btn"]:has-text("{text}")',
            f'*[class*="button"]:has-text("{text}")',

            # Links styled as buttons
            f'a[class*="btn"]:has-text("{text}")',
            f'a[class*="button"]:has-text("{text}")',

            # Buttons with spans/divs inside
            f'button:has(span:text-is("{text}"))',
            f'button:has(div:text-is("{text}"))',

            # Case-insensitive match
            f'button:text-is("{text}" i)',
            f'.ant-btn:text-is("{text}" i)',
        ]

        # Special handling for buttons with icons or special characters
        if text and any(char in text for char in ['+', '-', '*', '/', '>', '<']):
            clean_text = re.sub(r'[+\-*/<>]', '', text).strip()
            selectors.extend([
                f'button:has-text("{clean_text}")',
                f'.ant-btn:has-text("{clean_text}")',
                # Also try with the special character
                f'button:has(*:text-is("{text}"))',
                f'.ant-btn:has(*:text-is("{text}"))',
            ])

        for selector in selectors:
            try:
                elements = page.locator(selector)
                count = elements.count()
                if count > 0:
                    # Try to find the most visible/relevant button
                    for i in range(min(count, 5)):
                        element = elements.nth(i)
                        if element.is_visible() and element.is_enabled():
                            # Additional check for button validity
                            is_button = element.evaluate("""
                                (el) => {
                                    const tag = el.tagName.toLowerCase();
                                    const type = el.getAttribute('type') || '';
                                    const role = el.getAttribute('role') || '';
                                    const classes = el.className || '';

                                    return tag === 'button' || 
                                           type === 'button' || 
                                           type === 'submit' ||
                                           role === 'button' ||
                                           classes.includes('btn') ||
                                           classes.includes('button');
                                }
                            """)

                            if is_button:
                                logger.info(f"Found button using selector: {selector}")
                                return element
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        # Fallback: try to find by visible text anywhere on page
        return self._fallback_button_search_sync(page, text)

    async def _find_button_enhanced_async(self, page: AsyncPage, text: str, attributes: Dict) -> Optional[AsyncLocator]:
        """Enhanced button finding logic - asynchronous"""
        logger.info(f"Enhanced button search for: {text}")

        # Same comprehensive selectors as sync version
        selectors = [
            # Exact text match
            f'button:text-is("{text}")',
            f'button:has-text("{text}")',

            # Ant Design specific
            f'.ant-btn:text-is("{text}")',
            f'.ant-btn:has-text("{text}")',
            f'.ant-btn-primary:has-text("{text}")',

            # By role and text
            f'[role="button"]:text-is("{text}")',
            f'[role="button"]:has-text("{text}")',

            # Input buttons
            f'input[type="button"][value="{text}"]',
            f'input[type="submit"][value="{text}"]',

            # Generic button classes
            f'*[class*="btn"]:has-text("{text}")',
            f'*[class*="button"]:has-text("{text}")',

            # Links styled as buttons
            f'a[class*="btn"]:has-text("{text}")',
            f'a[class*="button"]:has-text("{text}")',

            # Buttons with spans/divs inside
            f'button:has(span:text-is("{text}"))',
            f'button:has(div:text-is("{text}"))',

            # Case-insensitive match
            f'button:text-is("{text}" i)',
            f'.ant-btn:text-is("{text}" i)',
        ]

        # Special handling for buttons with icons or special characters
        if text and any(char in text for char in ['+', '-', '*', '/', '>', '<']):
            clean_text = re.sub(r'[+\-*/<>]', '', text).strip()
            selectors.extend([
                f'button:has-text("{clean_text}")',
                f'.ant-btn:has-text("{clean_text}")',
                # Also try with the special character
                f'button:has(*:text-is("{text}"))',
                f'.ant-btn:has(*:text-is("{text}"))',
            ])

        for selector in selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    # Try to find the most visible/relevant button
                    for i in range(min(count, 5)):
                        element = elements.nth(i)
                        if await element.is_visible() and await element.is_enabled():
                            # Additional check for button validity
                            is_button = await element.evaluate("""
                                (el) => {
                                    const tag = el.tagName.toLowerCase();
                                    const type = el.getAttribute('type') || '';
                                    const role = el.getAttribute('role') || '';
                                    const classes = el.className || '';

                                    return tag === 'button' || 
                                           type === 'button' || 
                                           type === 'submit' ||
                                           role === 'button' ||
                                           classes.includes('btn') ||
                                           classes.includes('button');
                                }
                            """)

                            if is_button:
                                logger.info(f"Found button using selector: {selector}")
                                return element
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        # Fallback: try to find by visible text anywhere on page
        return await self._fallback_button_search_async(page, text)

    def _get_button_selectors(self, text: str) -> List[str]:
        """Get list of button selectors to try"""
        selectors = [
            f'button:text-is("{text}")',
            f'button:has-text("{text}")',
            f'[role="button"]:text-is("{text}")',
            f'[role="button"]:has-text("{text}")',
            f'.ant-btn:has-text("{text}")',
            f'button.ant-btn:has-text("{text}")',
            f'.ant-btn-primary:has-text("{text}")',
            f'input[type="button"][value*="{text}" i]',
            f'input[type="submit"][value*="{text}" i]',
            f'*[class*="btn"]:has-text("{text}")',
            f'*[class*="button"]:has-text("{text}")',
            f'a[class*="btn"]:has-text("{text}")',
            f'a[class*="button"]:has-text("{text}")',
        ]

        # If text contains special characters, also try without them
        if any(char in text for char in ['+', '-', '*', '/']):
            clean_text = re.sub(r'[+\-*/]', '', text).strip()
            selectors.extend([
                f'button:has-text("{clean_text}")',
                f'.ant-btn:has-text("{clean_text}")',
            ])

        return selectors

    def _fallback_button_search_sync(self, page: SyncPage, text: str) -> Optional[SyncLocator]:
        """Fallback button search - synchronous"""
        try:
            # Try to find any element with the text that might be clickable
            text_elements = page.locator(f'*:has-text("{text}"):visible').all()

            for element in text_elements[:10]:
                # Check if element or parent is clickable
                is_clickable = element.evaluate("""
                    (el) => {
                        // Check current element
                        const tag = el.tagName.toLowerCase();
                        const role = el.getAttribute('role') || '';
                        const classes = el.className || '';
                        const cursor = window.getComputedStyle(el).cursor;

                        if (tag === 'button' || tag === 'a' || 
                            role === 'button' || role === 'link' ||
                            classes.includes('btn') || classes.includes('button') ||
                            cursor === 'pointer') {
                            return true;
                        }

                        // Check parent elements
                        let parent = el.parentElement;
                        while (parent && parent !== document.body) {
                            const pTag = parent.tagName.toLowerCase();
                            const pRole = parent.getAttribute('role') || '';
                            const pClasses = parent.className || '';
                            const pCursor = window.getComputedStyle(parent).cursor;

                            if (pTag === 'button' || pTag === 'a' ||
                                pRole === 'button' || pRole === 'link' ||
                                pClasses.includes('btn') || pClasses.includes('button') ||
                                pCursor === 'pointer') {
                                return true;
                            }
                            parent = parent.parentElement;
                        }

                        return false;
                    }
                """)

                if is_clickable:
                    logger.info(f"Found clickable element with text '{text}' using fallback")
                    return element

        except Exception as e:
            logger.debug(f"Fallback button search failed: {e}")

        return None

    async def _fallback_button_search_async(self, page: AsyncPage, text: str) -> Optional[AsyncLocator]:
        """Fallback button search - asynchronous"""
        try:
            # Try to find any element with the text that might be clickable
            text_elements = await page.locator(f'*:has-text("{text}"):visible').all()

            for element in text_elements[:10]:
                # Check if element or parent is clickable
                is_clickable = await element.evaluate("""
                    (el) => {
                        // Check current element
                        const tag = el.tagName.toLowerCase();
                        const role = el.getAttribute('role') || '';
                        const classes = el.className || '';
                        const cursor = window.getComputedStyle(el).cursor;

                        if (tag === 'button' || tag === 'a' || 
                            role === 'button' || role === 'link' ||
                            classes.includes('btn') || classes.includes('button') ||
                            cursor === 'pointer') {
                            return true;
                        }

                        // Check parent elements
                        let parent = el.parentElement;
                        while (parent && parent !== document.body) {
                            const pTag = parent.tagName.toLowerCase();
                            const pRole = parent.getAttribute('role') || '';
                            const pClasses = parent.className || '';
                            const pCursor = window.getComputedStyle(parent).cursor;

                            if (pTag === 'button' || pTag === 'a' ||
                                pRole === 'button' || pRole === 'link' ||
                                pClasses.includes('btn') || pClasses.includes('button') ||
                                pCursor === 'pointer') {
                                return true;
                            }
                            parent = parent.parentElement;
                        }

                        return false;
                    }
                """)

                if is_clickable:
                    logger.info(f"Found clickable element with text '{text}' using fallback")
                    return element

        except Exception as e:
            logger.debug(f"Fallback button search failed: {e}")

        return None


    def _find_by_exact_text_sync(self, page: SyncPage, element_type: str,
                                 text: str, attributes: Dict) -> Optional[SyncLocator]:
        """Find by exact text match - synchronous"""
        if not text:
            return None

        type_map = {
            "button": ["button", "input[type='button']", "input[type='submit']", "[role='button']", ".ant-btn"],
            "link": ["a", "[role='link']"],
            "input": ["input", "textarea"],
            "dropdown": ["select", "[role='combobox']", ".ant-select"],
            "checkbox": ["input[type='checkbox']", "[role='checkbox']", ".ant-checkbox-input"],
            "radio": ["input[type='radio']", "[role='radio']"],
        }

        selectors = type_map.get(element_type, ["*"])

        for selector in selectors:
            element = page.locator(f"{selector}:text-is('{text}')")
            if element.count() > 0:
                return element

            normalized = normalize_text(text)
            element = page.locator(selector).filter(has_text=normalized)
            if element.count() > 0:
                return element

        return None

    async def _find_by_exact_text_async(self, page: AsyncPage, element_type: str,
                                        text: str, attributes: Dict) -> Optional[AsyncLocator]:
        """Find by exact text match - asynchronous"""
        if not text:
            return None

        type_map = {
            "button": ["button", "input[type='button']", "input[type='submit']", "[role='button']", ".ant-btn"],
            "link": ["a", "[role='link']"],
            "input": ["input", "textarea"],
            "dropdown": ["select", "[role='combobox']", ".ant-select"],
            "checkbox": ["input[type='checkbox']", "[role='checkbox']", ".ant-checkbox-input"],
            "radio": ["input[type='radio']", "[role='radio']"],
        }

        selectors = type_map.get(element_type, ["*"])

        for selector in selectors:
            element = page.locator(f"{selector}:text-is('{text}')")
            if await element.count() > 0:
                return element

            normalized = normalize_text(text)
            element = page.locator(selector).filter(has_text=normalized)
            if await element.count() > 0:
                return element

        return None

    def _find_by_partial_text_sync(self, page: SyncPage, element_type: str,
                                   text: str, attributes: Dict) -> Optional[SyncLocator]:
        """Find by partial text match - synchronous"""
        if not text:
            return None

        if element_type == "button":
            selectors = [
                f'button:has-text("{text}")',
                f'.ant-btn:has-text("{text}")',
                f'[role="button"]:has-text("{text}")',
                f'*[class*="btn"]:has-text("{text}")',
            ]
        elif element_type == "link":
            selectors = [
                f'a:has-text("{text}")',
                f'[role="link"]:has-text("{text}")',
            ]
        elif element_type == "input":
            # For input fields, be more specific
            return None  # Let other strategies handle input fields
        else:
            selectors = [f'*:has-text("{text}")']

        for selector in selectors:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    return element
            except:
                continue

        return None

    async def _find_by_partial_text_async(self, page: AsyncPage, element_type: str,
                                          text: str, attributes: Dict) -> Optional[AsyncLocator]:
        """Find by partial text match - asynchronous"""
        if not text:
            return None

        if element_type == "button":
            selectors = [
                f'button:has-text("{text}")',
                f'.ant-btn:has-text("{text}")',
                f'[role="button"]:has-text("{text}")',
                f'*[class*="btn"]:has-text("{text}")',
            ]
        elif element_type == "link":
            selectors = [
                f'a:has-text("{text}")',
                f'[role="link"]:has-text("{text}")',
            ]
        else:
            selectors = [f'*:has-text("{text}")']

        for selector in selectors:
            try:
                element = page.locator(selector)
                if await element.count() > 0:
                    return element
            except:
                continue

        return None

    def _find_by_id_or_name_sync(self, page: SyncPage, element_type: str,
                                 text: str, attributes: Dict) -> Optional[SyncLocator]:
        """Find by ID or name - synchronous"""
        possible_ids = self._generate_possible_ids(text)

        for id_value in possible_ids:
            element = page.locator(f"#{id_value}")
            if element.count() > 0:
                return element

            element = page.locator(f"[name='{id_value}']")
            if element.count() > 0:
                return element

        return None

    async def _find_by_id_or_name_async(self, page: AsyncPage, element_type: str,
                                        text: str, attributes: Dict) -> Optional[AsyncLocator]:
        """Find by ID or name - asynchronous"""
        possible_ids = self._generate_possible_ids(text)

        for id_value in possible_ids:
            element = page.locator(f"#{id_value}")
            if await element.count() > 0:
                return element

            element = page.locator(f"[name='{id_value}']")
            if await element.count() > 0:
                return element

        return None

    def _find_by_aria_label_sync(self, page: SyncPage, element_type: str,
                                 text: str, attributes: Dict) -> Optional[SyncLocator]:
        """Find by ARIA label - synchronous"""
        if not text:
            return None

        element = page.locator(f"[aria-label='{text}']")
        if element.count() > 0:
            return element

        element = page.locator(f"[aria-label*='{text}' i]")
        if element.count() > 0:
            return element

        return None

    async def _find_by_aria_label_async(self, page: AsyncPage, element_type: str,
                                        text: str, attributes: Dict) -> Optional[AsyncLocator]:
        """Find by ARIA label - asynchronous"""
        if not text:
            return None

        element = page.locator(f"[aria-label='{text}']")
        if await element.count() > 0:
            return element

        element = page.locator(f"[aria-label*='{text}' i]")
        if await element.count() > 0:
            return element

        return None

    def _find_by_css_patterns_sync(self, page: SyncPage, element_type: str,
                                   text: str, attributes: Dict) -> Optional[SyncLocator]:
        """Find by CSS patterns - synchronous"""
        patterns = self._get_css_patterns(element_type, text)

        for pattern in patterns:
            element = page.locator(pattern)
            if element.count() > 0:
                if text:
                    filtered = element.filter(has_text=text)
                    if filtered.count() > 0:
                        return filtered
                else:
                    return element

        return None

    async def _find_by_css_patterns_async(self, page: AsyncPage, element_type: str,
                                          text: str, attributes: Dict) -> Optional[AsyncLocator]:
        """Find by CSS patterns - asynchronous"""
        patterns = self._get_css_patterns(element_type, text)

        for pattern in patterns:
            element = page.locator(pattern)
            if await element.count() > 0:
                if text:
                    filtered = element.filter(has_text=text)
                    if await filtered.count() > 0:
                        return filtered
                else:
                    return element

        return None

    def _find_by_role_sync(self, page: SyncPage, element_type: str,
                           text: str, attributes: Dict) -> Optional[SyncLocator]:
        """Find by ARIA role - synchronous"""
        role_map = {
            "button": "button",
            "link": "link",
            "input": "textbox",
            "checkbox": "checkbox",
            "radio": "radio",
            "dropdown": "combobox",
        }

        role = role_map.get(element_type)
        if not role:
            return None

        element = page.get_by_role(role)

        if text and element.count() > 0:
            filtered = element.filter(has_text=text)
            if filtered.count() > 0:
                return filtered

            for i in range(min(element.count(), 10)):
                elem_text = element.nth(i).text_content()
                if elem_text and fuzzy_match(text, elem_text):
                    return element.nth(i)

        return element if element.count() > 0 else None

    async def _find_by_role_async(self, page: AsyncPage, element_type: str,
                                  text: str, attributes: Dict) -> Optional[AsyncLocator]:
        """Find by ARIA role - asynchronous"""
        role_map = {
            "button": "button",
            "link": "link",
            "input": "textbox",
            "checkbox": "checkbox",
            "radio": "radio",
            "dropdown": "combobox",
        }

        role = role_map.get(element_type)
        if not role:
            return None

        element = page.get_by_role(role)

        if text and await element.count() > 0:
            filtered = element.filter(has_text=text)
            if await filtered.count() > 0:
                return filtered

            count = await element.count()
            for i in range(min(count, 10)):
                elem_text = await element.nth(i).text_content()
                if elem_text and fuzzy_match(text, elem_text):
                    return element.nth(i)

        return element if await element.count() > 0 else None

    def _generate_possible_ids(self, text: str) -> List[str]:
        """Generate possible ID values from text"""
        if not text:
            return []

        ids = []
        clean_text = re.sub(r'[+\-*/\s]+', ' ', text).strip()

        ids.append(clean_text.lower())
        base = clean_text.lower()
        ids.append(base.replace(" ", "-"))
        ids.append(base.replace(" ", "_"))
        ids.append(base.replace(" ", ""))

        words = clean_text.split()
        if len(words) > 1:
            camel = words[0].lower() + "".join(w.title() for w in words[1:])
            ids.append(camel)

        ids.extend([
            f"{base}-btn",
            f"{base}-button",
            f"btn-{base}",
            f"{base}-link",
        ])

        return ids

    def _get_css_patterns(self, element_type: str, text: str) -> List[str]:
        """Get CSS patterns for element type"""
        patterns = {
            "button": [
                "[class*='btn']",
                "[class*='button']",
                "[class*='submit']",
            ],
            "link": [
                "[class*='link']",
                "[class*='nav']",
            ],
            "input": [
                "[class*='input']",
                "[class*='field']",
                "[class*='form-control']",
            ],
            "close": [
                "[class*='close']",
                "[class*='dismiss']",
                "[aria-label*='close']",
            ],
        }

        if "close" in (text or "").lower() or "x" == (text or "").lower():
            return patterns.get("close", [])
        else:
            return patterns.get(element_type, [])