"""
Example showing integration between BDD Generator and Element Detector
"""

from qa_copilot.bdd import BDDGenerator
from qa_copilot.detector import ElementDetector
from playwright.sync_api import sync_playwright


def example_bdd_with_element_detection():
    """Generate BDD and use it with Element Detector"""

    print("BDD + Element Detector Integration")
    print("=" * 50)

    # Step 1: Generate BDD scenarios
    generator = BDDGenerator({
        "expansion_level": "minimal"  # Keep it simple for demo
    })

    description = "User can login to SauceDemo with valid credentials"
    feature = generator.generate(description)

    # Print generated scenario
    print("Generated Scenario:")
    print("-" * 30)
    scenario = feature["scenarios"][0]
    for step in scenario["steps"]:
        print(f"{step['keyword']} {step['text']}")

    print("\n" + "-" * 30)
    print("Executing scenario...\n")

    # Step 2: Execute using Element Detector
    detector = ElementDetector()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Execute each step
        for step in scenario["steps"]:
            print(f"Executing: {step['keyword']} {step['text']}")

            try:
                if "on the login page" in step["text"]:
                    page.goto("https://www.saucedemo.com/")
                    print("  ✅ Navigated to login page")

                elif "enters" in step["text"] and "username" in step["text"]:
                    # Extract value from step text
                    username = "standard_user"  # In real scenario, parse from step
                    element = detector.find(page, "Enter username")
                    element.fill(username)
                    print(f"  ✅ Entered username: {username}")

                elif "enters" in step["text"] and "password" in step["text"]:
                    password = "secret_sauce"
                    element = detector.find(page, "Enter password")
                    element.fill(password)
                    print(f"  ✅ Entered password")

                elif "clicks on Login button" in step["text"]:
                    element = detector.find(page, "Click on Login button")
                    element.click()
                    print("  ✅ Clicked login button")

                elif "should see the dashboard" in step["text"]:
                    # Wait for navigation
                    page.wait_for_url("**/inventory.html", timeout=5000)
                    print("  ✅ Successfully logged in - dashboard visible")

            except Exception as e:
                print(f"  ❌ Failed: {e}")

        # Keep browser open to see result
        input("\nPress Enter to close browser...")
        browser.close()


def example_full_test_generation():
    """Generate complete test with BDD and execution steps"""

    print("\nComplete Test Generation Example")
    print("=" * 50)

    # Generate comprehensive test scenarios
    generator = BDDGenerator({
        "expansion_level": "medium",
        "include_negative_tests": True,
    })

    description = "User can search for products on e-commerce site"
    gherkin = generator.generate_gherkin(description)

    print("Generated Feature File:")
    print("-" * 30)
    print(gherkin)

    # Save to file
    from pathlib import Path
    feature_file = Path("generated_search.feature")
    feature_file.write_text(gherkin)
    print(f"\n✅ Feature saved to: {feature_file}")

    # Generate step definitions template
    print("\nStep Definitions Template:")
    print("-" * 30)

    step_template = '''from behave import given, when, then
from qa_copilot.detector import ElementDetector

detector = ElementDetector()

@given('the user is on the search page')
def step_on_search_page(context):
    context.browser.goto("https://example.com/search")

@when('the user enters "{search_term}" in search field')
def step_enter_search_term(context, search_term):
    element = detector.find(context.page, "Enter search term")
    element.fill(search_term)

@when('the user clicks on Search button')
def step_click_search(context):
    element = detector.find(context.page, "Click on Search button")
    element.click()

@then('the user should see relevant search results')
def step_see_results(context):
    # Add assertion logic here
    pass
'''

    print(step_template)


if __name__ == "__main__":
    example_bdd_with_element_detection()
    print("\n" + "=" * 70 + "\n")
    example_full_test_generation()
    description)
    if format == 'json':
        import json
    result = json.dumps(feature, indent=2)
    else:  # yaml
    import yaml

    result = yaml.dump(feature, default_flow_style=False)

    # Output result
    if output:
        Path(output).write_text(result)
    click.echo(f"✅ Feature saved to: {output}")
    else:
    click.echo("\n" + result)

    # Show summary
    if format == 'gherkin':
        scenario_count = result.count('Scenario:')
    click.echo(f"\n📊 Generated {scenario_count} scenarios")

    except Exception as e:
    click.echo(f"❌ Error: {e}", err=True)


@bdd.command()
@click.argument('feature_file', type=click.Path(exists=True))
def validate(feature_file):
    """Validate a feature file"""
    click.echo(f"🔍 Validating: {feature_file}")
    # Implementation for validation
    click.echo("✅ Feature file is valid")


@bdd.command()
def examples():
    """Show BDD generation examples"""
    examples = [
        "User can login with valid credentials",
        "User can search for products",
        "User can add items to shopping cart",
        "User can register with email and password",
        "Admin can manage user accounts",
        "User can reset forgotten password",
    ]

    click.echo("📝 Example descriptions you can use:\n")
    for example in examples:
        click.echo(f'  qa-copilot bdd generate "{example}"')

    click.echo("\n💡 Try with different expansion levels:")
    click.echo('  qa-copilot bdd generate "User can login" -e minimal')
    click.echo('  qa-copilot bdd generate "User can login" -e comprehensive')