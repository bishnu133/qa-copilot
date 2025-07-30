"""
Example of parsing requirements from different sources
"""

from pathlib import Path
from qa_copilot.bdd import BDDGenerator
from qa_copilot.bdd.requirements_parser import (
    PDFRequirementsParser,
    JIRAParser,
    RequirementsAnalyzer
)


def example_pdf_parsing():
    """Example of parsing requirements from PDF"""
    print("PDF Requirements Parsing Example")
    print("=" * 50)

    # Sample PDF content (in real scenario, this would be extracted from PDF)
    sample_pdf_content = """
    Epic: User Authentication System

    1. User Login Feature
    As a registered user, I want to login to the system so that I can access my account.

    Acceptance Criteria:
    - User can login with valid email and password
    - System displays error for invalid credentials
    - User is redirected to dashboard after successful login
    - Session timeout after 30 minutes of inactivity

    2. Password Reset Feature
    As a user, I want to reset my password so that I can regain access if I forget it.

    Acceptance Criteria:
    - User can request password reset via email
    - Reset link expires after 24 hours
    - User must enter new password twice for confirmation
    """

    # Initialize parser
    pdf_parser = PDFRequirementsParser()

    # Extract user stories (simulated)
    stories = [
        "As a registered user, I want to login to the system so that I can access my account",
        "As a user, I want to reset my password so that I can regain access if I forget it"
    ]

    # Generate BDD for each story
    generator = BDDGenerator({"expansion_level": "medium"})

    for story in stories:
        print(f"\nGenerating BDD for: {story[:50]}...")
        feature = generator.generate(story)

        print(f"Generated {len(feature['scenarios'])} scenarios:")
        for scenario in feature['scenarios']:
            print(f"  - {scenario['name']}")


def example_jira_parsing():
    """Example of parsing JIRA data"""
    print("\n\nJIRA Requirements Parsing Example")
    print("=" * 50)

    # Sample JIRA export data
    jira_data = {
        "issues": [
            {
                "key": "PROJ-123",
                "fields": {
                    "summary": "User Registration Feature",
                    "description": """
                    As a new user, I want to create an account so that I can use the application.

                    Acceptance Criteria:
                    - User can register with email and password
                    - Email must be unique
                    - Password must meet security requirements
                    - User receives confirmation email
                    """,
                    "issuetype": {"name": "Story"},
                    "customfield_10001": [  # Acceptance criteria field
                        "User can register with valid email",
                        "System validates email format",
                        "Password must be at least 8 characters",
                        "Duplicate emails are rejected"
                    ]
                }
            },
            {
                "key": "PROJ-124",
                "fields": {
                    "summary": "Shopping Cart Management",
                    "description": "Users should be able to add, remove, and update items in cart",
                    "issuetype": {"name": "Epic"}
                }
            }
        ]
    }

    # Parse JIRA data
    jira_parser = JIRAParser()
    requirements = jira_parser.parse(jira_data)

    # Analyze and generate BDD
    analyzer = RequirementsAnalyzer()
    features = analyzer.analyze_requirements(requirements)

    for feature in features:
        print(f"\nFeature: {feature['name']}")
        print(f"Source: JIRA {feature.get('requirement_id', '')}")
        print(f"Scenarios: {len(feature['scenarios'])}")

        # Show first 3 scenarios
        for scenario in feature['scenarios'][:3]:
            print(f"  - {scenario['name']}")


def example_combined_requirements():
    """Example of combining requirements from multiple sources"""
    print("\n\nCombined Requirements Analysis")
    print("=" * 50)

    # Simulate requirements from different sources
    all_requirements = [
        {
            "source": "pdf",
            "story": "User can search for products by category",
            "criteria": [
                "Search results should be relevant",
                "Results should load within 2 seconds",
                "User can filter results by price"
            ]
        },
        {
            "source": "jira",
            "key": "PROJ-200",
            "story": "Admin can manage user accounts",
            "acceptance_criteria": [
                "Admin can view all users",
                "Admin can deactivate user accounts",
                "Admin can reset user passwords",
                "All actions are logged for audit"
            ]
        },
        {
            "source": "figma",
            "flow_name": "Checkout Flow",
            "story": "User can complete purchase checkout",
            "interactions": [
                "Review cart",
                "Enter shipping info",
                "Select payment method",
                "Confirm order"
            ]
        }
    ]

    # Generate comprehensive BDD
    analyzer = RequirementsAnalyzer(
        BDDGenerator({"expansion_level": "comprehensive"})
    )

    features = analyzer.analyze_requirements(all_requirements)

    # Summary
    total_scenarios = sum(len(f['scenarios']) for f in features)
    print(f"\nGenerated {len(features)} features with {total_scenarios} total scenarios")

    for feature in features:
        print(f"\n{feature['name']}:")
        print(f"  Source: {feature['source']}")
        print(f"  Scenarios: {len(feature['scenarios'])}")

        # Group scenarios by type
        positive = [s for s in feature['scenarios'] if '@positive' in s.get('tags', [])]
        negative = [s for s in feature['scenarios'] if '@negative' in s.get('tags', [])]
        edge = [s for s in feature['scenarios'] if '@edge' in s.get('tags', [])]

        print(f"  - Positive: {len(positive)}")
        print(f"  - Negative: {len(negative)}")
        print(f"  - Edge Cases: {len(edge)}")


def example_save_generated_features():
    """Example of saving generated features to files"""
    print("\n\nSaving Generated Features")
    print("=" * 50)

    # Create output directory
    output_dir = Path("generated_features")
    output_dir.mkdir(exist_ok=True)

    # Sample requirement
    requirement = {
        "source": "jira",
        "key": "PROJ-300",
        "story": "User can manage profile settings",
        "acceptance_criteria": [
            "User can update email address",
            "User can change password",
            "User can upload profile picture",
            "User can set notification preferences"
        ]
    }

    # Generate BDD
    analyzer = RequirementsAnalyzer()
    features = analyzer.analyze_requirements([requirement])

    # Save each feature
    for feature in features:
        filename = f"{feature.get('requirement_id', 'feature')}_{feature['name'].replace(' ', '_')}.feature"
        filepath = output_dir / filename

        # Generate Gherkin
        generator = BDDGenerator()
        gherkin = generator.template_engine.render_feature(feature)

        # Save to file
        filepath.write_text(gherkin)
        print(f"Saved: {filepath}")

        # Also save as JSON for processing
        import json
        json_path = filepath.with_suffix('.json')
        json_path.write_text(json.dumps(feature, indent=2))
        print(f"Saved: {json_path}")


if __name__ == "__main__":
    print("Requirements Parsing Examples")
    print("=" * 70)

    example_pdf_parsing()
    example_jira_parsing()
    example_combined_requirements()
    example_save_generated_features()

    print("\n\nDone! Check 'generated_features' directory for output files.")