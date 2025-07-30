"""
Test scenarios for Element Detector
"""

from playwright.sync_api import sync_playwright
from qa_copilot.detector import ElementDetector

# Natural language descriptions to test
TEST_DESCRIPTIONS = [
    # Basic elements
    "Click on Login button",
    "Enter email address",
    "Select country from dropdown",
    "Check the Remember me checkbox",
    "Click on the first product",

    # With attributes
    "Click on the blue Submit button",
    "Find the search box at the top",
    "Click the close button (X)",

    # Complex descriptions
    "Enter john@example.com in the email field",
    "Click on Sign in with Google",
    "Select United States from the country dropdown",

    # Navigation
    "Click on the Home link",
    "Open the hamburger menu",
    "Go to Settings page",
]


def test_detector_on_site(url: str, descriptions: list):
    """Test detector on a specific site"""

    detector = ElementDetector()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print(f"\n🌐 Testing on: {url}")
        page.goto(url)
        page.wait_for_load_state('networkidle')

        results = []

        for desc in descriptions:
            print(f"\n🔍 Looking for: '{desc}'")
            try:
                element = detector.find(page, desc)
                tag = element.evaluate("el => el.tagName")
                text = element.text_content() or "No text"
                print(f"   ✅ Found: <{tag}> - {text[:50]}")
                results.append((desc, True))
            except Exception as e:
                print(f"   ❌ Not found: {str(e)[:100]}")
                results.append((desc, False))

        browser.close()

        # Summary
        success_rate = sum(1 for _, success in results if success) / len(results) * 100
        print(f"\n📊 Success rate: {success_rate:.1f}%")

        return results


if __name__ == "__main__":
    # Test on different sites
    sites = [
        "https://www.saucedemo.com/",
        "https://www.google.com/",
        "https://github.com/",
    ]

    for site in sites:
        # Filter descriptions relevant to each site
        test_detector_on_site(site, TEST_DESCRIPTIONS[:5])