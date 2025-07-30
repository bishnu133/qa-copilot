#!/usr/bin/env python3
"""
Test script to verify the Create Challenge button can be clicked
Includes login steps and navigation
"""

import asyncio
import logging
from playwright.async_api import async_playwright
from pathlib import Path
import sys
import yaml

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.qa_copilot.detector.detector import ElementDetector
from src.qa_copilot.executor.test_context import TestContext
from src.qa_copilot.executor.nlp_step_executor import NLPStepExecutor

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_config():
    """Load environment configuration"""
    config_path = Path("config/environments/dev.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        logger.warning(f"Config file not found: {config_path}")
        return {
            'base_url': 'http://localhost:3000',  # Default URL
            'roles': {
                'challenge_configurer': {
                    'username': 'admin@example.com',
                    'password': 'password123'
                }
            }
        }


async def test_create_challenge_flow():
    """Test the complete flow: login -> navigate -> click create challenge"""

    # Load configuration
    env_config = await load_config()
    base_url = env_config.get('base_url', '')

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=500  # Slow down for debugging
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        # Initialize element detector
        detector = ElementDetector()

        # Create test context
        test_context = TestContext(
            page=page,
            element_detector=detector,
            env_config=env_config,
            base_url=base_url,
            timeout=30000
        )

        # Load credentials
        test_context.load_credentials(env_config)

        # Initialize NLP executor for natural language steps
        nlp_executor = NLPStepExecutor(page, detector, env_config)

        try:
            # Step 1: Navigate to the base URL
            logger.info(f"Step 1: Navigating to {base_url}")
            await page.goto(base_url)
            await page.wait_for_load_state('networkidle')

            # Step 2: Login as challenge_configurer
            logger.info("Step 2: Logging in as challenge_configurer")
            result = await nlp_executor.execute_step('I log in as "challenge_configurer"')
            if result['status'] == 'failed':
                logger.error(f"Login failed: {result.get('error')}")
                # Try manual login approach
                await manual_login(page, env_config, detector)
            else:
                logger.info("Login successful")

            # Wait for page to load after login
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)

            # Step 3: Click on Challenges
            logger.info("Step 3: Clicking on Challenges")
            try:
                # Try multiple approaches to click Challenges
                challenges_clicked = False

                # Approach 1: Using NLP executor
                result = await nlp_executor.execute_step('I click on "Challenges"')
                if result['status'] == 'passed':
                    challenges_clicked = True
                    logger.info("Clicked Challenges using NLP executor")

                # Approach 2: Direct selectors if NLP failed
                if not challenges_clicked:
                    selectors = [
                        'a:has-text("Challenges")',
                        'button:has-text("Challenges")',
                        '[href*="challenges"]',
                        'nav a:has-text("Challenges")',
                        '.menu a:has-text("Challenges")',
                        '*[class*="menu"] a:has-text("Challenges")',
                    ]

                    for selector in selectors:
                        try:
                            elem = page.locator(selector).first
                            if await elem.count() > 0 and await elem.is_visible():
                                await elem.click()
                                logger.info(f"Clicked Challenges using selector: {selector}")
                                challenges_clicked = True
                                break
                        except:
                            continue

                if not challenges_clicked:
                    logger.error("Failed to click on Challenges")

            except Exception as e:
                logger.error(f"Error clicking Challenges: {e}")

            # Wait for navigation
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)

            # Step 4: Click the "+ Create a challenge" button
            logger.info("Step 4: Clicking '+ Create a challenge' button")

            # Try multiple approaches
            button_clicked = False

            # Approach 1: Using detector with various descriptions
            descriptions = [
                "Click + Create a challenge button",
                "Click Create a challenge button",
                "Click + Create a challenge",
                "Click Create a challenge",
            ]

            for desc in descriptions:
                try:
                    logger.info(f"Trying: {desc}")
                    button = await detector.find_async(page, desc)
                    if await button.is_visible():
                        await button.click()
                        logger.info(f"Successfully clicked button using: {desc}")
                        button_clicked = True
                        break
                except Exception as e:
                    logger.debug(f"Failed with '{desc}': {e}")

            # Approach 2: Direct selectors
            if not button_clicked:
                selectors = [
                    'button:has-text("+ Create a challenge")',
                    '.ant-btn:has-text("+ Create a challenge")',
                    '.ant-btn-primary:has-text("+ Create a challenge")',
                    'button.ant-btn:has-text("Create a challenge")',
                    'button:has-text("Create a challenge")',
                    '.ant-btn:has-text("Create")',
                    'button[class*="primary"]:has-text("Create")',
                ]

                for selector in selectors:
                    try:
                        elements = page.locator(selector).all()
                        for elem in await elements:
                            if await elem.is_visible():
                                await elem.click()
                                logger.info(f"Clicked button using selector: {selector}")
                                button_clicked = True
                                break
                        if button_clicked:
                            break
                    except Exception as e:
                        logger.debug(f"Selector failed: {selector} - {e}")

            # Approach 3: Find all buttons and check text
            if not button_clicked:
                logger.info("Trying to find button by checking all buttons...")
                all_buttons = await page.locator('button').all()
                for button in all_buttons:
                    try:
                        text = await button.text_content()
                        if text and ("create" in text.lower() or "+" in text):
                            if await button.is_visible():
                                logger.info(f"Found button with text: '{text}'")
                                await button.click()
                                button_clicked = True
                                break
                    except:
                        continue

            if not button_clicked:
                logger.error("Failed to click '+ Create a challenge' button")
                # Take screenshot for debugging
                await page.screenshot(path="create_button_not_found.png")

            # Wait for any action to complete
            await asyncio.sleep(2)

            # Step 5: Select "Online V1 (EDSH)" from dropdown
            logger.info("Step 5: Selecting 'Online V1 (EDSH)' from dropdown")
            try:
                result = await nlp_executor.execute_step('I select "Online V1 (EDSH)" from dropdown')
                if result['status'] == 'passed':
                    logger.info("Successfully selected from dropdown")
                else:
                    logger.error(f"Dropdown selection failed: {result.get('error')}")
            except Exception as e:
                logger.error(f"Error selecting from dropdown: {e}")

            # Step 6: Verify text "Create a challenge"
            logger.info("Step 6: Verifying text 'Create a challenge'")
            try:
                result = await nlp_executor.execute_step('I verify text "Create a challenge"')
                if result['status'] == 'passed':
                    logger.info("Text verification successful")
                else:
                    logger.error(f"Text verification failed: {result.get('error')}")
            except Exception as e:
                logger.error(f"Error verifying text: {e}")

            # Wait to see results
            logger.info("Test completed. Waiting 10 seconds before closing...")
            await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            # Take screenshot on failure
            await page.screenshot(path="test_failure.png")

        finally:
            await browser.close()


async def manual_login(page, env_config, detector):
    """Manual login approach if NLP executor fails"""
    logger.info("Attempting manual login...")

    # Get credentials
    role_config = env_config.get('roles', {}).get('challenge_configurer', {})
    username = role_config.get('username', '')
    password = role_config.get('password', '')

    if not username or not password:
        logger.error("No credentials found for challenge_configurer")
        return

    # Find and fill username field
    username_selectors = [
        'input[name="username"]',
        'input[type="text"][name="username"]',
        'input#username',
        'input[placeholder*="username" i]',
        'input[placeholder*="user" i]',
        'input[type="email"]',
        'input[type="text"]:visible',
    ]

    for selector in username_selectors:
        try:
            elem = page.locator(selector).first
            if await elem.count() > 0 and await elem.is_visible():
                await elem.fill(username)
                logger.info(f"Filled username using: {selector}")
                break
        except:
            continue

    # Find and fill password field
    password_selectors = [
        'input[type="password"]',
        'input[name="password"]',
        'input#password',
        'input[placeholder*="password" i]',
    ]

    for selector in password_selectors:
        try:
            elem = page.locator(selector).first
            if await elem.count() > 0 and await elem.is_visible():
                await elem.fill(password)
                logger.info(f"Filled password using: {selector}")
                break
        except:
            continue

    # Click login button
    login_selectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Sign In")',
        'button:has-text("Log In")',
        'button:has-text("Login")',
        'input[value="Sign In"]',
        'input[value="Log In"]',
        'input[value="Login"]',
    ]

    for selector in login_selectors:
        try:
            elem = page.locator(selector).first
            if await elem.count() > 0 and await elem.is_visible():
                await elem.click()
                logger.info(f"Clicked login button using: {selector}")
                break
        except:
            continue

    # Wait for login to complete
    await page.wait_for_load_state('networkidle')


if __name__ == "__main__":
    asyncio.run(test_create_challenge_flow())