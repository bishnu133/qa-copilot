"""
Date Picker Utility for handling various date picker implementations
Supports Ant Design, Material UI, and native HTML date pickers
"""

import re
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from playwright.async_api import Page, Locator
import logging

logger = logging.getLogger(__name__)


class DatePickerHandler:
    """Handles interaction with various date picker implementations"""

    def __init__(self, page: Page):
        self.page = page

    async def select_date(self, field_identifier: str, date: datetime) -> bool:
        """
        Select a single date in a date picker

        Args:
            field_identifier: Field name or description to find the date picker
            date: The date to select

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Selecting date {date.strftime('%Y-%m-%d')} in field: {field_identifier}")

        # Find and click the date input field
        date_input = await self._find_date_input(field_identifier)
        if not date_input:
            logger.error(f"Could not find date input for: {field_identifier}")
            return False

        # Try different date picker strategies
        strategies = [
            self._handle_ant_design_picker,
            self._handle_native_date_picker,
            self._handle_material_date_picker,
            self._handle_custom_date_picker
        ]

        for strategy in strategies:
            try:
                if await strategy(date_input, date):
                    logger.info(f"Successfully selected date using {strategy.__name__}")
                    return True
            except Exception as e:
                logger.debug(f"Strategy {strategy.__name__} failed: {e}")
                continue

        return False

    async def select_date_range(self, field_identifier: str, start_date: datetime,
                                end_date: datetime) -> bool:
        """
        Select a date range in a date range picker

        Args:
            field_identifier: Field name or description to find the date picker
            start_date: Start date of the range
            end_date: End date of the range

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Selecting date range {start_date.strftime('%Y-%m-%d')} to "
                    f"{end_date.strftime('%Y-%m-%d')} in field: {field_identifier}")

        # Strategy 1: Find by field name in form structure
        range_element = await self._find_date_range_by_label(field_identifier)

        # Strategy 2: Find any visible range picker on page
        if not range_element:
            range_element = await self._find_any_visible_range_picker()

        # Strategy 3: Find by generic input search
        if not range_element:
            range_element = await self._find_date_input(field_identifier)

        if not range_element:
            logger.error(f"Could not find date range input for: {field_identifier}")
            return False

        # Try to fill the date range
        return await self._fill_date_range(range_element, start_date, end_date)

    async def _find_date_range_by_label(self, field_identifier: str) -> Optional[Locator]:
        """Find date range picker by label"""
        field_name = field_identifier.replace(" field", "").strip()

        # Try to find the form structure first
        form_structures = [
            '.ant-form-item',
            '.ant-row',
            '.form-group',
            '.field-wrapper',
            'div[class*="form"]',
        ]

        for structure in form_structures:
            containers = await self.page.locator(structure).all()

            for container in containers:
                # Check if this container has our label
                label_text = await container.inner_text()
                if field_name.lower() in label_text.lower():
                    # Look for range picker within this container
                    range_picker = container.locator('.ant-picker-range').first
                    if await range_picker.count() > 0 and await range_picker.is_visible():
                        logger.info(f"Found range picker in container with label: {field_name}")
                        return range_picker

                    # Also check for regular picker
                    picker = container.locator('.ant-picker').first
                    if await picker.count() > 0 and await picker.is_visible():
                        # Check if it has range inputs
                        inputs = await picker.locator('input').all()
                        if len(inputs) >= 2:
                            logger.info(f"Found picker with multiple inputs in container")
                            return picker

        return None

    async def _find_any_visible_range_picker(self) -> Optional[Locator]:
        """Find any visible range picker on the page"""
        # Look for common range picker selectors
        selectors = [
            '.ant-picker-range:visible',
            '.ant-picker:has(input[placeholder*="Start"]):visible',
            '[class*="range-picker"]:visible',
            '[class*="date-range"]:visible',
        ]

        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                for elem in elements:
                    if await elem.is_visible():
                        # Verify it has multiple inputs
                        inputs = await elem.locator('input').all()
                        if len(inputs) >= 2:
                            logger.info(f"Found visible range picker with selector: {selector}")
                            return elem
            except:
                continue

        return None

    async def _fill_date_range(self, range_element: Locator, start_date: datetime,
                               end_date: datetime) -> bool:
        """Fill a date range in the given element"""

        # Get element info
        tag_name = await range_element.evaluate("el => el.tagName.toLowerCase()")
        class_name = await range_element.get_attribute('class') or ''

        logger.info(f"Filling date range in element: tag={tag_name}, class={class_name}")

        # Method 1: Direct input filling for range pickers
        if 'picker' in class_name or tag_name == 'div':
            inputs = await range_element.locator('input:visible').all()

            if len(inputs) >= 2:
                try:
                    # Format dates
                    date_formats = [
                        '%Y-%m-%d',  # ISO format
                        '%Y/%m/%d',  # Slash format
                        '%m/%d/%Y',  # US format
                        '%d/%m/%Y',  # EU format
                    ]

                    # Try each format
                    for date_format in date_formats:
                        start_str = start_date.strftime(date_format)
                        end_str = end_date.strftime(date_format)

                        logger.info(f"Trying date format: {date_format}")

                        # Fill start date
                        await inputs[0].click()
                        await self.page.wait_for_timeout(100)

                        # Clear and type
                        await self.page.keyboard.press('Control+A')
                        await self.page.keyboard.press('Delete')
                        await inputs[0].type(start_str, delay=50)
                        await self.page.wait_for_timeout(200)

                        # Move to end date
                        await self.page.keyboard.press('Tab')
                        await self.page.wait_for_timeout(200)

                        # Fill end date
                        await self.page.keyboard.press('Control+A')
                        await self.page.keyboard.press('Delete')
                        await inputs[1].type(end_str, delay=50)
                        await self.page.wait_for_timeout(200)

                        # Confirm
                        await self.page.keyboard.press('Enter')
                        await self.page.wait_for_timeout(500)

                        # Verify the values were accepted
                        start_value = await inputs[0].get_attribute('value')
                        end_value = await inputs[1].get_attribute('value')

                        if start_value and end_value:
                            logger.info(f"Successfully filled range: {start_value} to {end_value}")
                            return True

                except Exception as e:
                    logger.error(f"Failed to fill inputs directly: {e}")

            # Method 2: Click to open picker
            try:
                await range_element.click()
                await self.page.wait_for_timeout(500)

                if await self._handle_ant_design_range_picker(start_date, end_date):
                    return True
            except Exception as e:
                logger.debug(f"Click method failed: {e}")

        # Method 3: Single input with range text
        elif tag_name == 'input':
            try:
                # Skip if checkbox/radio
                input_type = await range_element.get_attribute('type')
                if input_type in ['checkbox', 'radio']:
                    return False

                # Try various range formats
                range_formats = [
                    f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}",
                    f"{start_date.strftime('%Y/%m/%d')} - {end_date.strftime('%Y/%m/%d')}",
                    f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}",
                    f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                ]

                for range_text in range_formats:
                    await range_element.click()
                    await range_element.clear()
                    await range_element.fill(range_text)
                    await self.page.keyboard.press('Enter')
                    await self.page.wait_for_timeout(300)

                    value = await range_element.get_attribute('value')
                    if value and value.strip():
                        logger.info(f"Successfully filled single input with: {range_text}")
                        return True

            except Exception as e:
                logger.error(f"Single input method failed: {e}")

        return False

    async def _find_date_range_picker(self, field_identifier: str) -> Optional[Locator]:
        """Find the date range picker element"""
        field_name = field_identifier.replace(" field", "").strip()

        # Specific selectors for date range pickers
        selectors = [
            # Ant Design range picker specific
            f'.ant-form-item:has(label:has-text("{field_name}")) .ant-picker-range',
            f'.ant-form-item:has(label:has-text("{field_name}")) div.ant-picker-range',
            f'label:has-text("{field_name}") ~ .ant-picker-range',
            f'label:has-text("{field_name}") + div .ant-picker-range',

            # Look for the container with range picker class
            f'.ant-row:has(label:has-text("{field_name}")) .ant-picker-range',
            f'.ant-col:has(label:has-text("{field_name}")) .ant-picker-range',

            # Fallback to any range picker if field name matches nearby text
            '.ant-picker-range',
        ]

        for selector in selectors:
            try:
                elements = self.page.locator(selector)
                count = await elements.count()

                if count > 0:
                    for i in range(count):
                        elem = elements.nth(i)
                        if await elem.is_visible():
                            # For generic selector, check if it's in the right context
                            if selector == '.ant-picker-range':
                                parent_text = await elem.evaluate("""
                                    (el) => {
                                        let parent = el.closest('.ant-form-item, .ant-row');
                                        return parent ? parent.innerText : '';
                                    }
                                """)

                                if field_name.lower() not in parent_text.lower():
                                    continue

                            logger.info(f"Found date range picker using selector: {selector}")
                            return elem
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        # If no range picker found, fall back to regular date input search
        return await self._find_date_input(field_identifier)

    async def _find_date_input(self, field_identifier: str) -> Optional[Locator]:
        """Find the date input field using various strategies"""

        # Clean the field identifier
        field_name = field_identifier.replace(" field", "").strip()

        # Strategy 1: Find by form structure with label
        containers = await self._find_form_containers_with_label(field_name)
        for container in containers:
            # Look for inputs within the container
            inputs = await container.locator('input:not([type="checkbox"]):not([type="radio"]):visible').all()
            if inputs:
                return inputs[0]

            # Look for picker containers
            picker = container.locator('.ant-picker, .ant-picker-range').first
            if await picker.count() > 0:
                return picker

        # Strategy 2: Find by placeholder
        placeholders = [field_name, "Select date", "Start date", "End date", "Date"]
        for placeholder in placeholders:
            input_elem = self.page.locator(f'input[placeholder*="{placeholder}" i]:visible').first
            if await input_elem.count() > 0:
                return input_elem

        # Strategy 3: Find any date-related input
        date_selectors = [
            'input[type="date"]:visible',
            'input[type="datetime-local"]:visible',
            '.ant-picker:visible',
            '.ant-picker-range:visible',
            'input[class*="date"]:visible',
        ]

        for selector in date_selectors:
            elem = self.page.locator(selector).first
            if await elem.count() > 0:
                return elem

        return None

    async def _find_form_containers_with_label(self, label_text: str) -> List[Locator]:
        """Find form containers that contain the specified label text"""
        containers = []

        # Common form container patterns
        container_selectors = [
            '.ant-form-item',
            '.ant-row',
            '.ant-col',
            '.form-group',
            '.field-wrapper',
            'div[class*="form"]',
            'div[class*="field"]',
        ]

        for selector in container_selectors:
            elements = await self.page.locator(selector).all()
            for elem in elements:
                try:
                    text = await elem.inner_text()
                    if label_text.lower() in text.lower():
                        containers.append(elem)
                except:
                    continue

        return containers

    async def _handle_ant_design_picker(self, date_input: Locator, date: datetime) -> bool:
        """Handle Ant Design date picker"""
        try:
            # Clear and click the input
            await date_input.clear()
            await date_input.click()
            await self.page.wait_for_timeout(300)

            # Wait for picker popup
            picker = self.page.locator('.ant-picker-dropdown:visible').first
            if not await picker.count():
                return False

            # Navigate to correct month/year if needed
            await self._navigate_to_month(picker, date)

            # Click the specific date
            date_cell_selector = (
                f'.ant-picker-cell[title="{date.strftime("%Y-%m-%d")}"]'
                f':not(.ant-picker-cell-disabled)'
            )

            date_cell = picker.locator(date_cell_selector).first
            if await date_cell.count() > 0:
                await date_cell.click()
                logger.info(f"Clicked date cell: {date.strftime('%Y-%m-%d')}")

                # Wait for picker to close
                await self.page.wait_for_timeout(300)
                return True

        except Exception as e:
            logger.debug(f"Ant Design picker handling failed: {e}")

        return False

    async def _handle_ant_design_range_picker(self, start_date: datetime,
                                              end_date: datetime) -> bool:
        """Handle Ant Design date range picker popup"""
        try:
            # Wait for the range picker popup
            picker = self.page.locator('.ant-picker-dropdown:visible').first
            if not await picker.count():
                return False

            # Select start date
            await self._navigate_to_month(picker, start_date)

            start_selector = (
                f'.ant-picker-cell[title="{start_date.strftime("%Y-%m-%d")}"]'
                f':not(.ant-picker-cell-disabled)'
            )
            start_cell = picker.locator(start_selector).first
            if await start_cell.count() > 0:
                await start_cell.click()
                logger.info(f"Selected start date: {start_date.strftime('%Y-%m-%d')}")
                await self.page.wait_for_timeout(300)

            # Select end date
            await self._navigate_to_month(picker, end_date)

            end_selector = (
                f'.ant-picker-cell[title="{end_date.strftime("%Y-%m-%d")}"]'
                f':not(.ant-picker-cell-disabled)'
            )
            end_cell = picker.locator(end_selector).first
            if await end_cell.count() > 0:
                await end_cell.click()
                logger.info(f"Selected end date: {end_date.strftime('%Y-%m-%d')}")

                # Wait for picker to close
                await self.page.wait_for_timeout(500)
                return True

        except Exception as e:
            logger.debug(f"Ant Design range picker handling failed: {e}")

        return False

    async def _navigate_to_month(self, picker: Locator, target_date: datetime):
        """Navigate the date picker to show the target month/year"""
        max_attempts = 24  # Prevent infinite loops (2 years)
        attempts = 0

        while attempts < max_attempts:
            # Get current displayed month/year
            header = picker.locator('.ant-picker-header').first
            if not await header.count():
                break

            # Try to find month/year text
            month_year_text = await header.inner_text()

            # Parse current month/year (handle different formats)
            current_date = self._parse_picker_header(month_year_text)
            if not current_date:
                break

            # Check if we're in the right month
            if (current_date.year == target_date.year and
                    current_date.month == target_date.month):
                return

            # Navigate to correct month
            if target_date > current_date:
                # Go forward
                next_btn = picker.locator('.ant-picker-header-next-btn').first
                if await next_btn.count() > 0:
                    await next_btn.click()
                    await self.page.wait_for_timeout(200)
            else:
                # Go backward
                prev_btn = picker.locator('.ant-picker-header-prev-btn').first
                if await prev_btn.count() > 0:
                    await prev_btn.click()
                    await self.page.wait_for_timeout(200)

            attempts += 1

    def _parse_picker_header(self, header_text: str) -> Optional[datetime]:
        """Parse the month/year from picker header text"""
        # Common formats: "December 2024", "Dec 2024", "2024-12", "12/2024"
        patterns = [
            (r'(\w+)\s+(\d{4})', '%B %Y'),  # "December 2024"
            (r'(\w{3})\s+(\d{4})', '%b %Y'),  # "Dec 2024"
            (r'(\d{4})-(\d{1,2})', '%Y-%m'),  # "2024-12"
            (r'(\d{1,2})/(\d{4})', '%m/%Y'),  # "12/2024"
        ]

        for pattern, date_format in patterns:
            match = re.search(pattern, header_text)
            if match:
                try:
                    if '%B' in date_format or '%b' in date_format:
                        # Month name format
                        return datetime.strptime(match.group(0), date_format)
                    else:
                        # Numeric format
                        return datetime.strptime(match.group(0), date_format)
                except:
                    continue

        return None

    async def _handle_native_date_picker(self, date_input: Locator, date: datetime) -> bool:
        """Handle native HTML5 date picker"""
        try:
            # For native date inputs, we can often just fill the value
            date_string = date.strftime('%Y-%m-%d')
            await date_input.fill(date_string)
            await self.page.keyboard.press('Enter')
            return True
        except:
            return False

    async def _handle_material_date_picker(self, date_input: Locator, date: datetime) -> bool:
        """Handle Material UI date picker"""
        # Placeholder for Material UI implementation
        return False

    async def _handle_custom_date_picker(self, date_input: Locator, date: datetime) -> bool:
        """Handle custom date picker implementations"""
        # Placeholder for custom implementations
        return False


class DateTimeParser:
    """Parse natural language datetime descriptions"""

    @staticmethod
    def parse(description: str, reference_date: Optional[datetime] = None) -> datetime:
        """
        Parse natural language datetime description

        Args:
            description: Natural language description like "tomorrow at 10:30 am"
            reference_date: Reference date for relative calculations (default: now)

        Returns:
            Parsed datetime object
        """
        if reference_date is None:
            reference_date = datetime.now()

        description = description.lower().strip()
        result = reference_date

        # Handle relative days
        if "today" in description:
            result = reference_date
        elif "tomorrow" in description:
            result = reference_date + timedelta(days=1)
        elif "yesterday" in description:
            result = reference_date - timedelta(days=1)
        elif match := re.search(r'(\d+)\s*days?\s*from\s*now', description):
            days = int(match.group(1))
            result = reference_date + timedelta(days=days)
        elif match := re.search(r'(\d+)\s*days?\s*ago', description):
            days = int(match.group(1))
            result = reference_date - timedelta(days=days)
        elif match := re.search(r'next\s*(\w+)', description):
            day_name = match.group(1)
            result = DateTimeParser._next_weekday(reference_date, day_name)

        # Handle relative weeks/months
        if match := re.search(r'(\d+)\s*weeks?\s*from\s*now', description):
            weeks = int(match.group(1))
            result = result + timedelta(weeks=weeks)
        elif match := re.search(r'(\d+)\s*months?\s*from\s*now', description):
            months = int(match.group(1))
            # Approximate month calculation
            result = result + timedelta(days=30 * months)

        # Handle specific time
        if match := re.search(r'at\s*(\d{1,2}):(\d{2})\s*(am|pm)', description):
            hour = int(match.group(1))
            minute = int(match.group(2))
            meridiem = match.group(3)

            # Convert to 24-hour format
            if meridiem == 'pm' and hour != 12:
                hour += 12
            elif meridiem == 'am' and hour == 12:
                hour = 0

            result = result.replace(hour=hour, minute=minute, second=0, microsecond=0)
        elif match := re.search(r'at\s*(\d{1,2})\s*(am|pm)', description):
            hour = int(match.group(1))
            meridiem = match.group(2)

            # Convert to 24-hour format
            if meridiem == 'pm' and hour != 12:
                hour += 12
            elif meridiem == 'am' and hour == 12:
                hour = 0

            result = result.replace(hour=hour, minute=0, second=0, microsecond=0)

        # Handle specific dates
        if match := re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', description):
            # Handle MM/DD/YYYY or MM-DD-YYYY format
            month = int(match.group(1))
            day = int(match.group(2))
            year = int(match.group(3))

            # Handle 2-digit year
            if year < 100:
                year += 2000

            result = result.replace(year=year, month=month, day=day)

        return result

    @staticmethod
    def _next_weekday(reference_date: datetime, weekday_name: str) -> datetime:
        """Get the next occurrence of a weekday"""
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }

        target_weekday = weekdays.get(weekday_name.lower())
        if target_weekday is None:
            return reference_date

        days_ahead = target_weekday - reference_date.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7

        return reference_date + timedelta(days=days_ahead)

    @staticmethod
    def format_for_input(date: datetime, format_type: str = "default") -> str:
        """
        Format datetime for different input types

        Args:
            date: Datetime object to format
            format_type: Type of format needed ('default', 'iso', 'us', 'eu')

        Returns:
            Formatted date string
        """
        formats = {
            'default': '%Y/%m/%d %H:%M',
            'iso': '%Y-%m-%d',
            'us': '%m/%d/%Y',
            'eu': '%d/%m/%Y',
            'datetime': '%Y-%m-%dT%H:%M',
            'time': '%H:%M'
        }

        return date.strftime(formats.get(format_type, formats['default']))