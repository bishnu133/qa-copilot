import click
import logging
from pathlib import Path
from typing import Optional
import click
import asyncio
from pathlib import Path
from executor import TestExecutor, ExecutorConfig

from .core import ConfigManager
from . import get_available_modules, load_module, __version__


@click.group()
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, verbose):
    """QA Copilot - Modular QA Automation Tool"""
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load configuration
    config_path = Path(config) if config else None
    ctx.obj = ConfigManager(config_path)


@cli.command()
def version():
    """Show version information"""
    click.echo(f"QA Copilot v{__version__}")
    click.echo(f"Available modules: {', '.join(get_available_modules())}")


@cli.command()
@click.argument('project_name')
def init(project_name):
    """Initialize a new QA Copilot project"""
    project_path = Path(project_name)

    if project_path.exists():
        click.echo(f"Error: Directory '{project_name}' already exists", err=True)
        return

    # Create project structure
    project_path.mkdir()
    (project_path / "features").mkdir()
    (project_path / "tests").mkdir()
    (project_path / "reports").mkdir()
    (project_path / "data").mkdir()

    # Create default config
    config = {
        "project": project_name,
        "detector": {
            "strategies": ["dom", "heuristic"],
            "timeout": 30,
        },
        "executor": {
            "browser": "chromium",
            "headless": False,
        }
    }

    import yaml
    with open(project_path / "qa-copilot.yaml", 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    click.echo(f"✅ Created QA Copilot project: {project_name}")
    click.echo(f"📁 Project structure:")
    click.echo(f"   {project_name}/")
    click.echo(f"   ├── features/     # BDD feature files")
    click.echo(f"   ├── tests/        # Test scripts")
    click.echo(f"   ├── reports/      # Test reports")
    click.echo(f"   ├── data/         # Test data")
    click.echo(f"   └── qa-copilot.yaml  # Configuration")


@cli.group()
def detect():
    """Element detection commands"""
    pass


@detect.command()
@click.argument('url')
@click.argument('description')
@click.option('--browser', '-b', default='chromium', help='Browser to use')
@click.option('--screenshot', '-s', is_flag=True, help='Take screenshot')
def find(url, description, browser, screenshot):
    """Find an element on a webpage"""
    from playwright.sync_api import sync_playwright

    try:
        # Load detector module
        detector = load_module('detector')

        with sync_playwright() as p:
            # Launch browser
            browser_obj = getattr(p, browser).launch(headless=False)
            page = browser_obj.new_page()

            # Navigate to URL
            click.echo(f"🌐 Navigating to: {url}")
            page.goto(url)
            page.wait_for_load_state('networkidle')

            # Find element
            click.echo(f"🔍 Looking for: {description}")
            result = detector.execute({
                "page": page,
                "description": description
            })

            if result.success:
                element = result.data
                click.echo(f"✅ Found element!")

                # Highlight element
                element.evaluate("""el => {
                    el.style.outline = '3px solid red';
                    el.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';
                }""")

                # Get element info
                tag = element.evaluate("el => el.tagName")
                text = element.text_content()
                click.echo(f"   Tag: {tag}")
                click.echo(f"   Text: {text}")

                if screenshot:
                    page.screenshot(path="element_found.png")
                    click.echo(f"📸 Screenshot saved: element_found.png")

                # Wait a bit to see the highlight
                page.wait_for_timeout(3000)
            else:
                click.echo(f"❌ Element not found: {result.error}", err=True)

            browser_obj.close()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.group()
def test():
    """Test execution commands"""
    pass

@cli.group()
def bdd():
    """BDD generation commands"""
    pass

@test.command()
@click.argument('feature_file')
def run(feature_file):
    """Run BDD tests"""
    click.echo(f"Running tests from: {feature_file}")
    # Placeholder for test execution

@bdd.command()
@click.argument('source_file', type=click.Path(exists=True))
@click.option('--type', '-t', type=click.Choice(['pdf', 'jira', 'figma']),
              help='Source file type')
@click.option('--output-dir', '-d', type=click.Path(),
              default='generated_features', help='Output directory')
@click.option('--expansion', '-e',
              type=click.Choice(['minimal', 'medium', 'comprehensive']),
              default='medium', help='Test case expansion level')
def from_requirements(source_file, type, output_dir, expansion):
    """Generate BDD scenarios from requirements documents"""

    click.echo(f"📄 Parsing requirements from: {source_file}")

    # Auto-detect type if not specified
    if not type:
        if source_file.endswith('.pdf'):
            type = 'pdf'
        elif source_file.endswith('.json'):
            type = 'jira'
        else:
            click.echo("❌ Cannot detect file type. Please specify with --type", err=True)
            return

    try:
        # Load appropriate parser
        if type == 'pdf':
            from .bdd.requirements_parser import PDFRequirementsParser
            parser = PDFRequirementsParser()
        elif type == 'jira':
            from .bdd.requirements_parser import JIRAParser
            parser = JIRAParser()
        elif type == 'figma':
            from .bdd.requirements_parser import FigmaParser
            parser = FigmaParser()

        # Parse requirements
        requirements = parser.parse(Path(source_file))
        click.echo(f"📋 Found {len(requirements)} requirements")

        # Generate BDD
        from .bdd.requirements_analyzer import RequirementsAnalyzer
        generator = load_module('bdd', {'expansion_level': expansion})
        analyzer = RequirementsAnalyzer(generator)

        features = analyzer.analyze_requirements(requirements)

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Save features
        for i, feature in enumerate(features):
            req_id = feature.get('requirement_id', f'REQ-{i + 1}')
            filename = f"{req_id}_{feature['name'].replace(' ', '_')}.feature"
            filepath = output_path / filename

            # Generate Gherkin
            gherkin = generator.template_engine.render_feature(feature)
            filepath.write_text(gherkin)

            click.echo(f"✅ Generated: {filepath}")

        click.echo(f"\n📊 Summary:")
        click.echo(f"  - Features generated: {len(features)}")
        total_scenarios = sum(len(f['scenarios']) for f in features)
        click.echo(f"  - Total scenarios: {total_scenarios}")
        click.echo(f"  - Output directory: {output_path}")

    except ImportError as e:
        click.echo(f"❌ Missing dependency: {e}", err=True)
        click.echo("💡 Install required dependencies:", err=True)
        if 'pdf' in str(e).lower():
            click.echo("    pip install PyPDF2", err=True)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@bdd.command()
@click.argument('description')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--expansion', '-e', type=click.Choice(['minimal', 'medium', 'comprehensive']),
              default='medium', help='Test case expansion level')
@click.option('--format', '-f', type=click.Choice(['gherkin', 'json', 'yaml']),
              default='gherkin', help='Output format')
def generate(description, output, expansion, format):
    """Generate BDD scenarios from natural language description"""
    try:
        # Load BDD generator
        generator = load_module('bdd', {
            'expansion_level': expansion,
            'output_format': format
        })

        click.echo(f"🎭 Generating BDD scenarios for: {description}")

        # Generate feature
        if format == 'gherkin':
            result = generator.generate_gherkin(description)
        else:
            feature = generator.generate(description)
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


@bdd.command()
@click.argument('requirements_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--ac-only', is_flag=True, help='Extract only Acceptance Criteria from JIRA PDFs')
@click.option('--expansion', '-e', type=click.Choice(['minimal', 'medium', 'comprehensive']),
              default='minimal', help='Test case expansion level (ignored in ac-only mode)')
def batch(requirements_file, output, ac_only, expansion):
    """Generate BDD from requirements document"""

    try:
        from .bdd.batch_generator import BatchBDDGenerator

        # Configure generator based on ac-only mode
        if ac_only:
            click.echo("🎯 AC-only mode: Extracting only Acceptance Criteria from JIRA PDF")
            batch_gen = BatchBDDGenerator(ac_only_mode=True)
        else:
            # Create BDD generator with expansion level
            bdd_gen = load_module('bdd', {'expansion_level': expansion})
            batch_gen = BatchBDDGenerator(bdd_generator=bdd_gen)

        # Generate features
        features = batch_gen.generate_from_file(
            Path(requirements_file),
            Path(output) if output else None
        )

        # Summary
        click.echo(f"\n✅ Generated {len(features)} feature(s)")

        if ac_only and features:
            # Show AC-specific summary
            total_scenarios = sum(len(f.get('scenarios', [])) for f in features)
            click.echo(f"📋 Total acceptance criteria converted: {total_scenarios}")

            if output:
                click.echo(f"📁 Feature file saved to: {output}")

    except ValueError as e:
        click.echo(f"⚠️  {e}", err=True)
        if "No Acceptance Criteria section found" in str(e):
            click.echo("💡 Make sure the PDF contains an 'Acceptance Criteria' section", err=True)
    except ImportError as e:
        click.echo(f"❌ Missing dependency: {e}", err=True)
        click.echo("💡 Install required dependencies:", err=True)
        click.echo("    pip install PyPDF2", err=True)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@bdd.command()
@click.argument('jira_url')
@click.option('--username', '-u', prompt=True, help='JIRA username')
@click.option('--token', '-t', prompt=True, hide_input=True,
              help='JIRA API token')
@click.option('--jql', help='JQL query to filter issues')
@click.option('--output-dir', '-d', type=click.Path(),
              default='generated_features')
def from_jira(jira_url, username, token, jql, output_dir):
    """Generate BDD scenarios from JIRA issues"""

    click.echo(f"🔗 Connecting to JIRA: {jira_url}")

    try:
        import requests
        from requests.auth import HTTPBasicAuth

        # Default JQL if not provided
        if not jql:
            jql = "type in (Epic, Story) AND status != Closed"

        # JIRA API endpoint
        api_url = f"{jira_url}/rest/api/2/search"

        # Query parameters
        params = {
            "jql": jql,
            "fields": "summary,description,issuetype,customfield_*",
            "maxResults": 100
        }

        # Make API request
        response = requests.get(
            api_url,
            params=params,
            auth=HTTPBasicAuth(username, token)
        )

        if response.status_code != 200:
            click.echo(f"❌ JIRA API error: {response.status_code}", err=True)
            return

        jira_data = response.json()
        click.echo(f"📋 Found {len(jira_data.get('issues', []))} issues")

        # Parse and generate BDD
        from .bdd.requirements_parser import JIRAParser
        from .bdd.requirements_analyzer import RequirementsAnalyzer

        parser = JIRAParser()
        requirements = parser.parse(jira_data)

        generator = load_module('bdd')
        analyzer = RequirementsAnalyzer(generator)
        features = analyzer.analyze_requirements(requirements)

        # Save features
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for feature in features:
            filename = f"{feature.get('requirement_id', 'feature')}.feature"
            filepath = output_path / filename

            gherkin = generator.template_engine.render_feature(feature)
            filepath.write_text(gherkin)

            click.echo(f"✅ Generated: {filepath}")

        click.echo(f"\n✨ Successfully generated {len(features)} features")

    except ImportError:
        click.echo("❌ Missing dependency: requests", err=True)
        click.echo("💡 Install with: pip install requests", err=True)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@bdd.command()
@click.argument('pdf_file', type=click.Path(exists=True))
def preview_ac(pdf_file):
    """Preview Acceptance Criteria found in a JIRA PDF"""
    try:
        from .bdd.requirements_parser import JIRAAcceptanceCriteriaParser

        parser = JIRAAcceptanceCriteriaParser()

        # Extract text
        text = parser._extract_from_pdf(Path(pdf_file))

        # Validate structure
        validation = parser.validate_pdf_structure(text)

        click.echo("📄 PDF Structure Analysis:")
        click.echo(f"  ✓ JIRA Key Found: {'Yes' if validation['has_jira_key'] else 'No'}")
        click.echo(f"  ✓ Story Section: {'Yes' if validation['has_story_section'] else 'No'}")
        click.echo(f"  ✓ AC Section: {'Yes' if validation['has_ac_section'] else 'No'}")
        click.echo(f"  ✓ AC Table Format: {'Yes' if validation['has_ac_table'] else 'No'}")

        if validation['has_ac_section']:
            # Extract and show AC section
            ac_section = parser._extract_acceptance_criteria_section(text)
            if ac_section:
                click.echo("\n📋 Acceptance Criteria Found:")
                click.echo("-" * 50)

                # Parse and display
                acs = parser._parse_acceptance_criteria_table(ac_section)
                for ac in acs:
                    click.echo(f"\n{ac['id']}:")
                    click.echo(f"  Given: {ac['given']}")
                    click.echo(f"  When:  {ac['when']}")
                    click.echo(f"  Then:  {ac['then']}")

                click.echo(f"\n✅ Total ACs found: {len(acs)}")
        else:
            click.echo("\n❌ No Acceptance Criteria section found")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@bdd.command()
@click.option('--format', '-f', type=click.Choice(['basic', 'detailed']), default='basic')
def show_ac_examples(format):
    """Show examples of supported AC formats"""

    if format == 'basic':
        click.echo("📝 Supported Acceptance Criteria Formats:\n")

        click.echo("1️⃣ Table Format:")
        click.echo("   AC1 | Given ... | When ... | Then ...")
        click.echo("   AC2 | Given ... | When ... | Then ...\n")

        click.echo("2️⃣ Structured Format:")
        click.echo("   AC1 Given the user is logged in")
        click.echo("       When the user clicks on Login")
        click.echo("       Then the user sees the dashboard\n")

        click.echo("3️⃣ List Format:")
        click.echo("   AC1: User can login with valid credentials")
        click.echo("   AC2: System validates email format\n")

    else:
        # Show detailed examples with actual JIRA formatting
        example_content = """
📝 Detailed JIRA AC Format Examples:

1️⃣ Standard JIRA Table Format (Most Common):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AC# | Given                           | When                    | Then
AC1 | A user on login page           | enters valid creds      | should see dashboard
AC2 | A logged in user               | clicks logout           | should be logged out

2️⃣ JIRA Text Format with Structure:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AC1 Given a user is on the login page
    When the user enters valid credentials
    Then the user should see the dashboard

AC2 Given a user is logged in
    When the user clicks on logout button
    Then the user should be redirected to login page

3️⃣ JIRA Description List Format:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AC1: User can successfully login with valid email and password
AC2: System displays error for invalid credentials
AC3: Password field is masked for security

💡 Tips:
- The parser automatically detects the format
- Given/When/Then keywords are flexible (given, Given, GIVEN all work)
- Table columns can be separated by | or tabs
- AC numbers can be AC1, AC 1, or AC-1
"""
        click.echo(example_content)


@click.group()
def test():
    """Test execution commands"""
    pass


@test.command()
@click.argument('feature_path', required=False)
@click.option('-d', '--directory', default='features/', help='Feature files directory')
@click.option('-e', '--env', default='dev', help='Environment to use (dev, staging, prod)')
@click.option('-b', '--browser', default='chromium', type=click.Choice(['chromium', 'firefox', 'webkit']),
              help='Browser to use')
@click.option('--headless/--headed', default=False, help='Run in headless mode')
@click.option('-p', '--parallel', default=1, type=int, help='Number of parallel workers')
@click.option('-c', '--config', help='Path to environment config file')
@click.option('--screenshots/--no-screenshots', default=True, help='Take screenshots on failure')
@click.option('--video/--no-video', default=False, help='Record video of test execution')
@click.option('-t', '--tags', help='Run scenarios with specific tags (comma-separated)')
@click.option('-r', '--report', default='html', type=click.Choice(['html', 'json', 'junit']), help='Report format')
@click.option('--retry', default=1, type=int, help='Number of retries for failed steps')
@click.option('--timeout', default=30000, type=int, help='Default timeout in milliseconds')
@click.option('-v', '--verbose', is_flag=True, help='Verbose output')
def run(feature_path, directory, env, browser, headless, parallel, config,
        screenshots, video, tags, report, retry, timeout, verbose):
    """
    Execute feature files

    Examples:
        qa-copilot test run login.feature
        qa-copilot test run -d features/ -e staging
        qa-copilot test run --browser firefox --headless
        qa-copilot test run -t @smoke,@critical
    """
    # Configure executor
    executor_config = ExecutorConfig(
        browser=browser,
        headless=headless,
        environment=env,
        config_path=config,
        parallel_workers=parallel,
        screenshot_on_failure=screenshots,
        video_recording=video,
        retry_failed_steps=retry,
        timeout=timeout
    )

    # Create executor
    executor = TestExecutor(executor_config)

    if verbose:
        click.echo(f"Executing tests with configuration:")
        click.echo(f"  Environment: {env}")
        click.echo(f"  Browser: {browser} ({'headless' if headless else 'headed'})")
        click.echo(f"  Parallel workers: {parallel}")

    try:
        # Execute tests
        if feature_path:
            # Single feature file
            click.echo(f"Executing feature: {feature_path}")
            results = asyncio.run(executor.execute_feature(feature_path))
        else:
            # All features in directory
            click.echo(f"Executing all features in: {directory}")
            results = executor.execute_directory(directory)

        # Display summary
        summary = results.get('summary', {})
        click.echo("\nTest Execution Summary:")
        click.echo(f"  Total Features: {summary.get('total', 0)}")
        click.echo(f"  Passed: {summary.get('passed', 0)}")
        click.echo(f"  Failed: {summary.get('failed', 0)}")

        # Display failed scenarios
        if summary.get('failed', 0) > 0:
            click.echo("\nFailed Scenarios:")
            for feature in results.get('features', []):
                if feature['status'] == 'failed':
                    click.echo(f"\n  Feature: {feature['feature']}")
                    for scenario in feature.get('scenarios', []):
                        if scenario['status'] == 'failed':
                            click.echo(f"    - {scenario['name']}")
                            if 'error' in scenario:
                                click.echo(f"      Error: {scenario['error']}")

        # Report location
        if 'report_path' in results:
            click.echo(f"\nDetailed report: {results['report_path']}")

        # Exit with appropriate code
        exit_code = 0 if summary.get('failed', 0) == 0 else 1
        raise SystemExit(exit_code)

    except Exception as e:
        click.echo(f"Error executing tests: {str(e)}", err=True)
        raise SystemExit(1)


@test.command()
@click.option('-e', '--env', default='dev', help='Environment to check')
@click.option('-c', '--config', help='Path to environment config file')
def validate(env, config):
    """Validate test configuration"""
    click.echo(f"Validating configuration for environment: {env}")

    try:
        # Create executor with config
        executor_config = ExecutorConfig(
            environment=env,
            config_path=config
        )
        executor = TestExecutor(executor_config)

        # Validate configuration
        if executor.validate():
            click.echo("✓ Configuration is valid")

            # Display loaded configuration
            if executor.env_config:
                click.echo("\nLoaded configuration:")
                click.echo(f"  Base URL: {executor.env_config.get('base_url', 'Not set')}")

                # Show available credentials
                roles = executor.env_config.get('roles', {})
                if roles:
                    click.echo(f"  Available roles: {', '.join(roles.keys())}")

                # Show page mappings
                pages = executor.env_config.get('pages', {})
                if pages:
                    click.echo(f"  Page mappings: {len(pages)}")
        else:
            click.echo("✗ Configuration validation failed", err=True)
            raise SystemExit(1)

    except Exception as e:
        click.echo(f"Error validating configuration: {str(e)}", err=True)
        raise SystemExit(1)


@test.command()
def list_steps():
    """List all available step definitions"""
    from executor import TestExecutor

    executor = TestExecutor()
    definitions = executor.step_registry.list_definitions()

    click.echo("Available Step Definitions:")
    click.echo("=" * 60)

    # Group by keyword
    grouped = {}
    for defn in definitions:
        keyword = defn['keyword'].upper()
        if keyword not in grouped:
            grouped[keyword] = []
        grouped[keyword].append(defn)

    # Display grouped definitions
    for keyword in ['GIVEN', 'WHEN', 'THEN']:
        if keyword in grouped:
            click.echo(f"\n{keyword} Steps:")
            click.echo("-" * 40)
            for defn in grouped[keyword]:
                click.echo(f"  {defn['pattern']}")
                if defn.get('description'):
                    click.echo(f"    {defn['description']}")

    click.echo("\nNote: AND and BUT keywords can be used with any step type")


@test.command()
@click.argument('feature_file')
@click.option('-n', '--dry-run', is_flag=True, help='Show what would be executed without running')
def preview(feature_file, dry_run):
    """Preview feature file execution plan"""
    from behave.parser import parse_feature

    try:
        with open(feature_file, 'r') as f:
            content = f.read()

        feature = parse_feature(content, filename=feature_file)

        click.echo(f"Feature: {feature.name}")
        if feature.description:
            click.echo(f"  {' '.join(feature.description)}")

        if feature.background:
            click.echo("\n  Background:")
            for step in feature.background.steps:
                click.echo(f"    {step.keyword} {step.name}")

        for scenario in feature.scenarios:
            click.echo(f"\n  Scenario: {scenario.name}")
            if scenario.tags:
                tags = ' '.join(tag.name for tag in scenario.tags)
                click.echo(f"    Tags: {tags}")

            for step in scenario.steps:
                click.echo(f"    {step.keyword} {step.name}")
                if step.table:
                    # Display table
                    headers = step.table.headings
                    click.echo(f"      | {' | '.join(headers)} |")
                    for row in step.table.rows:
                        click.echo(f"      | {' | '.join(row.cells)} |")

        click.echo(f"\nTotal scenarios: {len(feature.scenarios)}")

    except Exception as e:
        click.echo(f"Error parsing feature file: {str(e)}", err=True)
        raise SystemExit(1)

def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main()
