import re
from typing import Any, Dict, List, Optional, Tuple
from playwright.sync_api import Page as SyncPage, Locator as SyncLocator
from playwright.async_api import Page as AsyncPage, Locator as AsyncLocator
import logging

from .base import DetectionStrategy
from ..utils import normalize_text, fuzzy_match

logger = logging.getLogger(__name__)


class HeuristicStrategy(DetectionStrategy):
    """
    Enhanced heuristic-based element detection strategy.
    Supports both sync and async operations.
    """

    def __init__(self):
        # Common UI patterns
        self.common_patterns = {
            "create": {
                "variations": ["create", "add", "new", "+ create", "create new", "add new", "create a"],
                "element_types": ["button", "link", "a"],
                "classes": ["btn", "button", "primary", "action"],
                "nearby_elements": []
            },
            "login": {
                "variations": ["login", "sign in", "signin", "log in", "authenticate"],
                "element_types": ["button", "link"],
                "nearby_elements": ["username", "password", "email"]
            },
            "submit": {
                "variations": ["submit", "save", "confirm", "ok", "apply", "continue", "next"],
                "element_types": ["button", "input[type='submit']"],
                "context": ["form", "modal", "dialog"]
            },
            "cancel": {
                "variations": ["cancel", "close", "dismiss", "back", "no", "x", "×"],
                "element_types": ["button", "link", "span"],
                "attributes": ["aria-label", "title"]
            },
            "search": {
                "variations": ["search", "find", "lookup", "query"],
                "element_types": ["input", "button"],
                "attributes": ["placeholder", "aria-label"]
            },
            "menu": {
                "variations": ["menu", "hamburger", "☰", "⋮", "more", "options"],
                "element_types": ["button", "div", "span"],
                "attributes": ["aria-label", "role"]
            }
        }

    @property
    def name(self) -> str:
        return "Heuristic"

    @property
    def priority(self) -> int:
        return 2  # Second priority after DOM

    def find(self, page: SyncPage, description: Dict[str, Any]) -> Optional[SyncLocator]:
        """Find element using heuristic patterns - synchronous"""
        text = description.get("target") or description.get("text", "")
        element_type = description.get("element_type") or description.get("type", "")
        if element_type:
            element_type = element_type.lower()

        logger.info(f"Heuristic Strategy - Looking for: type={element_type}, text={text}")

        # Special handling for buttons with special characters
        if element_type == "button" or "button" in text.lower():
            element = self._find_button_with_special_chars_sync(page, text)
            if element:
                return element

        # Check if text matches any common pattern
        for pattern_name, pattern_config in self.common_patterns.items():
            if self._matches_pattern(text.lower(), pattern_config["variations"]):
                element = self._find_by_pattern_sync(page, pattern_name, pattern_config, description)
                if element:
                    return element

        # Try contextual search
        element = self._find_by_context_sync(page, description)
        if element:
            return element

        # Try proximity search
        element = self._find_by_proximity_sync(page, description)
        if element:
            return element

        # Last resort - try coordinate-based clicking for visible text
        element = self._find_by_coordinates_sync(page, text)
        if element:
            return element

        return None

    async def find_async(self, page: AsyncPage, description: Dict[str, Any]) -> Optional[AsyncLocator]:
        """Find element using heuristic patterns - asynchronous"""
        text = description.get("target") or description.get("text", "")
        element_type = description.get("element_type") or description.get("type", "")
        if element_type:
            element_type = element_type.lower()

        logger.info(f"Heuristic Strategy (Async) - Looking for: type={element_type}, text={text}")

        # Special handling for buttons with special characters
        if element_type == "button" or "button" in text.lower():
            element = await self._find_button_with_special_chars_async(page, text)
            if element:
                return element

        # Check if text matches any common pattern
        for pattern_name, pattern_config in self.common_patterns.items():
            if self._matches_pattern(text.lower(), pattern_config["variations"]):
                element = await self._find_by_pattern_async(page, pattern_name, pattern_config, description)
                if element:
                    return element

        # Try contextual search
        element = await self._find_by_context_async(page, description)
        if element:
            return element

        # Try proximity search
        element = await self._find_by_proximity_async(page, description)
        if element:
            return element

        # Last resort - try coordinate-based clicking for visible text
        element = await self._find_by_coordinates_async(page, text)
        if element:
            return element

        return None

    def _matches_pattern(self, text: str, variations: List[str]) -> bool:
        """Check if text matches any variation"""
        for variation in variations:
            if variation in text or fuzzy_match(text, variation, threshold=0.7):
                return True
        return False

    # Synchronous methods
    def _find_button_with_special_chars_sync(self, page: SyncPage, text: str) -> Optional[SyncLocator]:
        """Find buttons with special characters - synchronous"""
        logger.info(f"Looking for button with special chars: {text}")

        selectors = [
            f'text="{text}"',
            f'button:has-text("{text}")',
            f'.ant-btn:has-text("{text}")',
            f'[class*="btn"]:has-text("{text}")',
            f'a:has-text("{text}")',
        ]

        if text and text[0] in ['+', '-', '*', '/']:
            clean_text = text[1:].strip()
            selectors.extend([
                f'button:has-text("{clean_text}")',
                f'.ant-btn:has-text("{clean_text}")',
            ])

        for selector in selectors:
            try:
                elements = page.locator(selector).all()
                for element in elements[:5]:
                    if element.is_visible():
                        tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                        class_name = element.get_attribute("class") or ""
                        role = element.get_attribute("role") or ""

                        if (tag_name in ['button', 'a', 'input'] or
                                'btn' in class_name or 'button' in class_name or
                                role == 'button'):
                            logger.info(f"Found button with special chars using: {selector}")
                            return element
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        return None

    # Asynchronous methods
    async def _find_button_with_special_chars_async(self, page: AsyncPage, text: str) -> Optional[AsyncLocator]:
        """Find buttons with special characters - asynchronous"""
        logger.info(f"Looking for button with special chars: {text}")

        selectors = [
            f'text="{text}"',
            f'button:has-text("{text}")',
            f'.ant-btn:has-text("{text}")',
            f'[class*="btn"]:has-text("{text}")',
            f'a:has-text("{text}")',
        ]

        if text and text[0] in ['+', '-', '*', '/']:
            clean_text = text[1:].strip()
            selectors.extend([
                f'button:has-text("{clean_text}")',
                f'.ant-btn:has-text("{clean_text}")',
            ])

        for selector in selectors:
            try:
                elements = await page.locator(selector).all()
                for element in elements[:5]:
                    if await element.is_visible():
                        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                        class_name = await element.get_attribute("class") or ""
                        role = await element.get_attribute("role") or ""

                        if (tag_name in ['button', 'a', 'input'] or
                                'btn' in class_name or 'button' in class_name or
                                role == 'button'):
                            logger.info(f"Found button with special chars using: {selector}")
                            return element
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        return None

    def _find_by_pattern_sync(self, page: SyncPage, pattern_name: str,
                              pattern_config: Dict, description: Dict) -> Optional[SyncLocator]:
        """Find element using pattern - synchronous"""
        variations = pattern_config["variations"]
        element_types = pattern_config.get("element_types", [])
        classes = pattern_config.get("classes", [])

        selectors = []

        for element_type in element_types:
            for variation in variations:
                selectors.append(f"{element_type}:has-text('{variation}')")

                for attr in pattern_config.get("attributes", []):
                    selectors.append(f"{element_type}[{attr}*='{variation}' i]")

        for class_name in classes:
            for variation in variations:
                selectors.append(f'.{class_name}:has-text("{variation}")')
                selectors.append(f'[class*="{class_name}"]:has-text("{variation}")')

        for selector in selectors:
            try:
                elements = page.locator(selector)
                if elements.count() > 0:
                    if elements.count() == 1:
                        if elements.first.is_visible():
                            return elements.first
                    else:
                        best_match = self._select_best_match_sync(elements, description)
                        if best_match:
                            return best_match
            except Exception as e:
                logger.debug(f"Pattern selector {selector} failed: {e}")
                continue

        return None

    async def _find_by_pattern_async(self, page: AsyncPage, pattern_name: str,
                                     pattern_config: Dict, description: Dict) -> Optional[AsyncLocator]:
        """Find element using pattern - asynchronous"""
        variations = pattern_config["variations"]
        element_types = pattern_config.get("element_types", [])
        classes = pattern_config.get("classes", [])

        selectors = []

        for element_type in element_types:
            for variation in variations:
                selectors.append(f"{element_type}:has-text('{variation}')")

                for attr in pattern_config.get("attributes", []):
                    selectors.append(f"{element_type}[{attr}*='{variation}' i]")

        for class_name in classes:
            for variation in variations:
                selectors.append(f'.{class_name}:has-text("{variation}")')
                selectors.append(f'[class*="{class_name}"]:has-text("{variation}")')

        for selector in selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    if count == 1:
                        if await elements.first.is_visible():
                            return elements.first
                    else:
                        best_match = await self._select_best_match_async(elements, description)
                        if best_match:
                            return best_match
            except Exception as e:
                logger.debug(f"Pattern selector {selector} failed: {e}")
                continue

        return None

    def _find_by_context_sync(self, page: SyncPage, description: Dict) -> Optional[SyncLocator]:
        """Find element by context - synchronous"""
        text = description.get("target") or description.get("text", "")
        element_type = description.get("element_type") or description.get("type", "")

        contexts = {
            "header": ["header", "nav", "navigation", "navbar", "top-bar", "toolbar"],
            "form": ["form", "login", "signup", "register"],
            "modal": ["modal", "dialog", "popup", "overlay"],
            "footer": ["footer"],
            "sidebar": ["sidebar", "aside", "menu", "drawer"],
            "content": ["content", "main", "container", "wrapper"],
        }

        for context_name, context_selectors in contexts.items():
            for selector in context_selectors:
                containers = page.locator(f"[class*='{selector}' i], [id*='{selector}' i], {selector}")

                for i in range(min(containers.count(), 3)):
                    container = containers.nth(i)

                    if text:
                        element = container.locator(f"*:has-text('{text}')")
                        if element.count() > 0:
                            for j in range(min(element.count(), 3)):
                                elem = element.nth(j)
                                if elem.is_visible():
                                    if self._verify_element_type_sync(elem, element_type):
                                        return elem

                    if element_type:
                        type_selector = self._get_type_selector(element_type)
                        element = container.locator(type_selector)
                        if element.count() > 0:
                            filtered = element.filter(has_text=text) if text else element
                            if filtered.count() > 0 and filtered.first.is_visible():
                                return filtered.first

        return None

    async def _find_by_context_async(self, page: AsyncPage, description: Dict) -> Optional[AsyncLocator]:
        """Find element by context - asynchronous"""
        text = description.get("target") or description.get("text", "")
        element_type = description.get("element_type") or description.get("type", "")

        contexts = {
            "header": ["header", "nav", "navigation", "navbar", "top-bar", "toolbar"],
            "form": ["form", "login", "signup", "register"],
            "modal": ["modal", "dialog", "popup", "overlay"],
            "footer": ["footer"],
            "sidebar": ["sidebar", "aside", "menu", "drawer"],
            "content": ["content", "main", "container", "wrapper"],
        }

        for context_name, context_selectors in contexts.items():
            for selector in context_selectors:
                containers = page.locator(f"[class*='{selector}' i], [id*='{selector}' i], {selector}")

                count = await containers.count()
                for i in range(min(count, 3)):
                    container = containers.nth(i)

                    if text:
                        element = container.locator(f"*:has-text('{text}')")
                        elem_count = await element.count()
                        if elem_count > 0:
                            for j in range(min(elem_count, 3)):
                                elem = element.nth(j)
                                if await elem.is_visible():
                                    if await self._verify_element_type_async(elem, element_type):
                                        return elem

                    if element_type:
                        type_selector = self._get_type_selector(element_type)
                        element = container.locator(type_selector)
                        if await element.count() > 0:
                            filtered = element.filter(has_text=text) if text else element
                            if await filtered.count() > 0 and await filtered.first.is_visible():
                                return filtered.first

        return None

    def _find_by_proximity_sync(self, page: SyncPage, description: Dict) -> Optional[SyncLocator]:
        """Find element by proximity - synchronous"""
        text = description.get("target") or description.get("text", "")

        if text:
            text_elements = page.locator(f"*:has-text('{text}')")

            for i in range(min(text_elements.count(), 5)):
                text_element = text_elements.nth(i)

                if text_element.evaluate("el => el.tagName").lower() == "label":
                    for_attr = text_element.get_attribute("for")
                    if for_attr:
                        associated = page.locator(f"#{for_attr}")
                        if associated.count() > 0:
                            return associated.first

                parent = text_element.locator("..")
                nearby_inputs = parent.locator("input, button, select, textarea")

                if nearby_inputs.count() > 0:
                    return nearby_inputs.first

        return None

    async def _find_by_proximity_async(self, page: AsyncPage, description: Dict) -> Optional[AsyncLocator]:
        """Find element by proximity - asynchronous"""
        text = description.get("target") or description.get("text", "")

        if text:
            text_elements = page.locator(f"*:has-text('{text}')")

            count = await text_elements.count()
            for i in range(min(count, 5)):
                text_element = text_elements.nth(i)

                tag_name = await text_element.evaluate("el => el.tagName")
                if tag_name.lower() == "label":
                    for_attr = await text_element.get_attribute("for")
                    if for_attr:
                        associated = page.locator(f"#{for_attr}")
                        if await associated.count() > 0:
                            return associated.first

                parent = text_element.locator("..")
                nearby_inputs = parent.locator("input, button, select, textarea")

                if await nearby_inputs.count() > 0:
                    return nearby_inputs.first

        return None

    def _find_by_coordinates_sync(self, page: SyncPage, text: str) -> Optional[SyncLocator]:
        """Find by coordinates - synchronous"""
        try:
            text_elements = page.locator(f'text="{text}"').all()
            for text_element in text_elements[:3]:
                if text_element.is_visible():
                    parent = text_element.evaluate("""
                        (el) => {
                            let current = el;
                            while (current && current.parentElement) {
                                const parent = current.parentElement;
                                const tag = parent.tagName.toLowerCase();
                                const classes = parent.className || '';

                                if (tag === 'button' || tag === 'a' || 
                                    classes.includes('btn') || classes.includes('button') ||
                                    parent.onclick || parent.role === 'button') {
                                    return parent;
                                }
                                current = parent;
                            }
                            return el;
                        }
                    """)

                    if parent:
                        logger.info(f"Found element by coordinates for text: {text}")
                        return text_element

        except Exception as e:
            logger.debug(f"Coordinate search failed: {e}")

        return None

    async def _find_by_coordinates_async(self, page: AsyncPage, text: str) -> Optional[AsyncLocator]:
        """Find by coordinates - asynchronous"""
        try:
            text_elements = await page.locator(f'text="{text}"').all()
            for text_element in text_elements[:3]:
                if await text_element.is_visible():
                    parent = await text_element.evaluate("""
                        (el) => {
                            let current = el;
                            while (current && current.parentElement) {
                                const parent = current.parentElement;
                                const tag = parent.tagName.toLowerCase();
                                const classes = parent.className || '';

                                if (tag === 'button' || tag === 'a' || 
                                    classes.includes('btn') || classes.includes('button') ||
                                    parent.onclick || parent.role === 'button') {
                                    return parent;
                                }
                                current = parent;
                            }
                            return el;
                        }
                    """)

                    if parent:
                        logger.info(f"Found element by coordinates for text: {text}")
                        return text_element

        except Exception as e:
            logger.debug(f"Coordinate search failed: {e}")

        return None

    def _select_best_match_sync(self, elements: SyncLocator, description: Dict) -> Optional[SyncLocator]:
        """Select best match - synchronous"""
        text = description.get("target") or description.get("text", "")
        attributes = description.get("attributes", {})

        best_score = 0
        best_element = None

        for i in range(min(elements.count(), 10)):
            try:
                element = elements.nth(i)
                score = 0

                if element.is_visible():
                    score += 10

                if element.is_enabled():
                    score += 5

                if text:
                    elem_text = element.text_content() or ""
                    if text.lower() == elem_text.lower():
                        score += 30
                    elif text.lower() in elem_text.lower():
                        score += 20
                    elif fuzzy_match(text, elem_text):
                        score += 10

                if attributes.get("color"):
                    style = element.get_attribute("style") or ""
                    class_name = element.get_attribute("class") or ""
                    if attributes["color"] in style or attributes["color"] in class_name:
                        score += 5

                if attributes.get("position"):
                    if attributes["position"] == "first" and i == 0:
                        score += 15
                    elif attributes["position"] == "last" and i == elements.count() - 1:
                        score += 15

                class_name = element.get_attribute("class") or ""
                if any(pattern in class_name.lower() for pattern in ["primary", "main", "submit", "action"]):
                    score += 5

                tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                expected_type = description.get("element_type", "").lower()
                if expected_type == "button" and tag_name == "button":
                    score += 10
                elif expected_type == "link" and tag_name == "a":
                    score += 10

                if score > best_score:
                    best_score = score
                    best_element = element

            except Exception as e:
                logger.debug(f"Error scoring element {i}: {e}")
                continue

        return best_element

    async def _select_best_match_async(self, elements: AsyncLocator, description: Dict) -> Optional[AsyncLocator]:
        """Select best match - asynchronous"""
        text = description.get("target") or description.get("text", "")
        attributes = description.get("attributes", {})

        best_score = 0
        best_element = None
        count = await elements.count()

        for i in range(min(count, 10)):
            try:
                element = elements.nth(i)
                score = 0

                if await element.is_visible():
                    score += 10

                if await element.is_enabled():
                    score += 5

                if text:
                    elem_text = await element.text_content() or ""
                    if text.lower() == elem_text.lower():
                        score += 30
                    elif text.lower() in elem_text.lower():
                        score += 20
                    elif fuzzy_match(text, elem_text):
                        score += 10

                if attributes.get("color"):
                    style = await element.get_attribute("style") or ""
                    class_name = await element.get_attribute("class") or ""
                    if attributes["color"] in style or attributes["color"] in class_name:
                        score += 5

                if attributes.get("position"):
                    if attributes["position"] == "first" and i == 0:
                        score += 15
                    elif attributes["position"] == "last" and i == count - 1:
                        score += 15

                class_name = await element.get_attribute("class") or ""
                if any(pattern in class_name.lower() for pattern in ["primary", "main", "submit", "action"]):
                    score += 5

                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                expected_type = description.get("element_type", "").lower()
                if expected_type == "button" and tag_name == "button":
                    score += 10
                elif expected_type == "link" and tag_name == "a":
                    score += 10

                if score > best_score:
                    best_score = score
                    best_element = element

            except Exception as e:
                logger.debug(f"Error scoring element {i}: {e}")
                continue

        return best_element

    def _verify_element_type_sync(self, element: SyncLocator, expected_type: str) -> bool:
        """Verify element type - synchronous"""
        if not expected_type:
            return True

        try:
            tag_name = element.evaluate("el => el.tagName.toLowerCase()")
            element_type = element.get_attribute("type") or ""
            role = element.get_attribute("role") or ""
            class_name = element.get_attribute("class") or ""

            if expected_type == "button":
                return (tag_name == "button" or
                        element_type in ["button", "submit"] or
                        role == "button" or
                        "btn" in class_name or "button" in class_name)
            elif expected_type == "link":
                return tag_name == "a" or role == "link"
            elif expected_type == "input":
                return tag_name in ["input", "textarea"] or role == "textbox"
            elif expected_type == "checkbox":
                return element_type == "checkbox" or role == "checkbox"
            elif expected_type == "radio":
                return element_type == "radio" or role == "radio"
            elif expected_type == "dropdown":
                return tag_name == "select" or role == "combobox"

        except:
            pass

        return True

    async def _verify_element_type_async(self, element: AsyncLocator, expected_type: str) -> bool:
        """Verify element type - asynchronous"""
        if not expected_type:
            return True

        try:
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            element_type = await element.get_attribute("type") or ""
            role = await element.get_attribute("role") or ""
            class_name = await element.get_attribute("class") or ""

            if expected_type == "button":
                return (tag_name == "button" or
                        element_type in ["button", "submit"] or
                        role == "button" or
                        "btn" in class_name or "button" in class_name)
            elif expected_type == "link":
                return tag_name == "a" or role == "link"
            elif expected_type == "input":
                return tag_name in ["input", "textarea"] or role == "textbox"
            elif expected_type == "checkbox":
                return element_type == "checkbox" or role == "checkbox"
            elif expected_type == "radio":
                return element_type == "radio" or role == "radio"
            elif expected_type == "dropdown":
                return tag_name == "select" or role == "combobox"

        except:
            pass

        return True

    def _get_type_selector(self, element_type: str) -> str:
        """Get CSS selector for element type"""
        type_map = {
            "button": "button, input[type='button'], input[type='submit'], [role='button'], .ant-btn, [class*='btn']",
            "link": "a, [role='link']",
            "input": "input:not([type='button']):not([type='submit']), textarea",
            "checkbox": "input[type='checkbox'], [role='checkbox']",
            "radio": "input[type='radio'], [role='radio']",
            "dropdown": "select, [role='combobox'], .ant-select",
            "image": "img, [role='img']",
        }
        return type_map.get(element_type, "*")