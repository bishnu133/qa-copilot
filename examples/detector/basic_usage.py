"""
Basic usage example for the Element Detector module
"""

from playwright.sync_api import sync_playwright
from qa_copilot.detector import ElementDetector


def example_basic_detection():
    """Basic element detection example"""

    # Initialize detector
    detector = ElementDetector({
        "strategies": ["dom", "heuristic"],
        "fuzzy_match_threshold": 0.8,
    })

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to a demo site
        page.goto("https://www.saucedemo.com/")

        # Example 1: Find login button using natural language
        print("Finding login button...")
        login_button = detector.find(page, "Click on the Login button")
        print(f"Found: {login_button}")

        # Example 2: Find username field
        print("\nFinding username field...")
        username_field = detector.find(page, "Enter username")
        username_field.fill("standard_user")

        # Example 3: Find password field
        print("\nFinding password field...")
        password_field = detector.find(page, "Type in password field")
        password_field.fill("secret_sauce")

        # Example 4: Click login
        login_button.click()

        # Wait to see results
        page.wait_for_timeout(3000)

        browser.close()


def example_advanced_detection():
    """Advanced detection with different strategies"""

    from qa_copilot.detector import ElementDetector

    detector = ElementDetector({
        "strategies": ["dom", "heuristic"],
        "cache_elements": True,
    })

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to a more complex page
        page.goto("https://github.com/")

        # Example: Find by color and position
        print("Finding green Sign up button...")
        try:
            signup_button = detector.find(page, "Click on the green Sign up button")
            print(f"Found button with text: {signup_button.text_content()}")
        except Exception as e:
            print(f"Could not find: {e}")

        browser.close()


if __name__ == "__main__":
    print("Running basic detection example...")
    example_basic_detection()

    print("\n\nRunning advanced detection example...")
    example_advanced_detection()