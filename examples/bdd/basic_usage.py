"""
Basic usage examples for BDD Generator
"""

from qa_copilot.bdd import BDDGenerator


def example_basic_generation():
    """Basic BDD generation example"""

    # Initialize generator
    generator = BDDGenerator({
        "expansion_level": "medium",
        "include_negative_tests": True,
        "include_edge_cases": True,
    })

    # Example 1: Login functionality
    print("Example 1: Login Functionality")
    print("=" * 50)

    description = "User can login with valid credentials"
    gherkin = generator.generate_gherkin(description)
    print(gherkin)

    # Example 2: Registration
    print("\n\nExample 2: Registration")
    print("=" * 50)

    description = "User can register with email and password"
    gherkin = generator.generate_gherkin(description)
    print(gherkin)

    # Example 3: Search
    print("\n\nExample 3: Search Functionality")
    print("=" * 50)

    description = "User can search for products by name"
    gherkin = generator.generate_gherkin(description)
    print(gherkin)


def example_minimal_expansion():
    """Example with minimal expansion"""

    generator = BDDGenerator({
        "expansion_level": "minimal",
    })

    print("Minimal Expansion Example")
    print("=" * 50)

    description = "User can add items to shopping cart"
    gherkin = generator.generate_gherkin(description)
    print(gherkin)


def example_comprehensive_expansion():
    """Example with comprehensive expansion"""

    generator = BDDGenerator({
        "expansion_level": "comprehensive",
        "include_negative_tests": True,
        "include_edge_cases": True,
        "include_boundary_tests": True,
        "max_scenarios_per_feature": 15,
    })

    print("Comprehensive Expansion Example")
    print("=" * 50)

    description = "User can submit contact form with required fields"
    gherkin = generator.generate_gherkin(description)
    print(gherkin)


def example_data_driven():
    """Example of data-driven scenario generation"""

    generator = BDDGenerator({
        "expansion_level": "medium",
        "data_driven": True,
    })

    print("Data-Driven Scenario Example")
    print("=" * 50)

    # This would generate scenario outlines with examples
    description = "User can login with different types of credentials"
    feature = generator.generate(description)

    # Access the generated data
    print(f"Feature: {feature['name']}")
    print(f"Scenarios: {len(feature['scenarios'])}")
    for scenario in feature['scenarios']:
        print(f"  - {scenario['name']}")


def example_custom_functionality():
    """Example with custom domain functionality"""

    generator = BDDGenerator()

    print("Custom Domain Example")
    print("=" * 50)

    # Banking domain
    description = "User can transfer money between accounts"
    gherkin = generator.generate_gherkin(description)
    print(gherkin)

    print("\n\n")

    # E-commerce domain
    description = "User can apply discount coupon during checkout"
    gherkin = generator.generate_gherkin(description)
    print(gherkin)


if __name__ == "__main__":
    print("BDD Generator Examples")
    print("=" * 70)
    print()

    example_basic_generation()
    print("\n" + "=" * 70 + "\n")

    example_minimal_expansion()
    print("\n" + "=" * 70 + "\n")

    example_comprehensive_expansion()
    print("\n" + "=" * 70 + "\n")

    example_data_driven()
    print("\n" + "=" * 70 + "\n")

    example_custom_functionality()