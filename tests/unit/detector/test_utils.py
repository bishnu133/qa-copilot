#!/usr/bin/env python3
"""
Test script to verify Element Detector is working correctly on real websites
Save this file in the qa-copilot root directory and run: python test_detector.py
"""

from playwright.sync_api import sync_playwright
from qa_copilot.detector import ElementDetector
import sys


def test_basic_detection():
    """Test detector on common websites"""
    print("🚀 Testing QA-Copilot Element Detector\n")

    # Initialize detector
    detector = ElementDetector({
        "strategies": ["dom", "heuristic"],
        "timeout": 30,
        "retry_count": 3,
    })

    # Test cases
    test_cases = [
        {
            "url": "https://www.google.com",
            "tests": [
                ("Click on Search button", "Google Search"),
                ("Enter text in search box", "search input"),
                ("Click on I'm Feeling Lucky button", "I'm Feeling Lucky"),
            ]
        },
        {
            "url": "https://www.saucedemo.com",
            "tests": [
                ("Enter username", "username field"),
                ("Enter password", "password field"),
                ("Click on Login button", "login button"),
            ]
        },
        {
            "url": "https://github.com",
            "tests": [
                ("Click on Sign in link", "sign in"),
                ("Click on Sign up button", "sign up"),
                ("Enter text in search box", "search"),
            ]
        }
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        for test_site in test_cases:
            url = test_site["url"]
            print(f"\n📍 Testing on: {url}")
            print("=" * 50)

            page = browser.new_page()
            try:
                page.goto(url)
                page.wait_for_load_state('networkidle', timeout=10000)

                for description, expected in test_site["tests"]:
                    print(f"\n🔍 Looking for: '{description}'")

                    try:
                        element = detector.find(page, description)

                        # Get element details
                        tag = element.evaluate("el => el.tagName.toLowerCase()")
                        text = element.text_content() or ""
                        visible = element.is_visible()

                        print(f"   ✅ Found: <{tag}>")
                        print(f"   📝 Text: {text[:50]}")
                        print(f"   👁️  Visible: {visible}")

                        # Highlight the element
                        element.evaluate("""el => {
                            el.style.outline = '3px solid green';
                            el.style.backgroundColor = 'rgba(0, 255, 0, 0.1)';
                        }""")

                        # Wait a bit to see the highlight
                        page.wait_for_timeout(1000)

                    except Exception as e:
                        print(f"   ❌ Failed: {str(e)[:100]}")

                # Take screenshot of final state
                page.screenshot(path=f"test_{url.replace('https://', '').replace('/', '_')}.png")
                print(f"   📸 Screenshot saved")

            except Exception as e:
                print(f"   ⚠️  Error loading page: {e}")
            finally:
                page.close()

        browser.close()

    print("\n✨ Testing complete!")


def test_cli_command():
    """Test CLI detection command"""
    print("\n🔧 Testing CLI Command\n")

    import subprocess

    # Test CLI find command
    cmd = [
        "qa-copilot", "detect", "find",
        "https://www.google.com",
        "Click on Search button",
        "--screenshot"
    ]

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print("\nOutput:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
    except Exception as e:
        print(f"CLI test failed: {e}")


def test_module_info():
    """Test module information"""
    print("\n📋 Module Information\n")

    from qa_copilot import get_available_modules, __version__

    print(f"QA-Copilot Version: {__version__}")
    print(f"Available Modules: {get_available_modules()}")

    # Test loading detector
    from qa_copilot import load_module

    detector = load_module('detector')
    info = detector.get_info()

    print(f"\nDetector Module Info:")
    print(f"  Name: {info.name}")
    print(f"  Version: {info.version}")
    print(f"  Description: {info.description}")
    print(f"  Has AI: {info.has_ai}")


if __name__ == "__main__":
    print("=" * 60)
    print("QA-COPILOT ELEMENT DETECTOR TEST")
    print("=" * 60)

    # Run tests
    try:
        test_module_info()
        test_basic_detection()
        test_cli_command()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)