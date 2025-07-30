from typing import List, Dict, Any
from pathlib import Path
from .generator import BDDGenerator
from .requirements_parser import SimpleRequirementsParser, JIRAAcceptanceCriteriaParser
import re


class BatchBDDGenerator:
    """Generate BDD scenarios in batch from requirements documents"""

    def __init__(self, bdd_generator: BDDGenerator = None, ac_only_mode: bool = False):
        self.generator = bdd_generator or BDDGenerator()
        self.ac_only_mode = ac_only_mode

        # Use appropriate parser based on mode
        if ac_only_mode:
            self.parser = JIRAAcceptanceCriteriaParser()
        else:
            self.parser = SimpleRequirementsParser()

    def generate_from_file(self, file_path: Path, output_dir: Path = None) -> List[Dict[str, Any]]:
        """Generate BDD features from a requirements file"""
        # Parse requirements
        requirements = self.parser.parse_file(file_path)

        if not requirements:
            raise ValueError(f"No requirements found in {file_path}")

        print(f"Found {len(requirements)} requirements")

        # Generate BDD for each requirement
        features = []

        if self.ac_only_mode:
            # For AC-only mode, group by story and create single feature
            features.append(self._generate_ac_feature(requirements, file_path))

            if output_dir:
                self._save_feature(features[0], output_dir, 0)
        else:
            # Standard mode - one feature per requirement
            for i, req in enumerate(requirements):
                print(f"Processing {i + 1}/{len(requirements)}: {req['text'][:50]}...")

                try:
                    # Generate feature
                    feature = self.generator.generate(req["text"])

                    # Add metadata
                    feature["source_file"] = str(file_path)
                    feature["requirement_type"] = req.get("type", "unknown")

                    features.append(feature)

                    # Save if output directory specified
                    if output_dir:
                        self._save_feature(feature, output_dir, i)

                except Exception as e:
                    print(f"  ⚠️  Failed to generate BDD: {e}")

        return features

    def _generate_ac_feature(self, requirements: List[Dict[str, Any]], file_path: Path) -> Dict[str, Any]:
        """Generate a single feature from acceptance criteria"""
        # Get story info from first requirement
        first_req = requirements[0]
        story_key = first_req.get("key", "STORY")
        story_title = first_req.get("story", "User Management Enhancement")

        # Create feature
        feature = {
            "name": f"{story_key} - {story_title}",
            "description": "Generated from JIRA Acceptance Criteria",
            "tags": ["@jira", f"@{story_key}"],
            "source_file": str(file_path),
            "requirement_type": "acceptance_criteria",
            "scenarios": [],
            "background": {
                "steps": [
                    {"keyword": "Given", "text": "I am logged in as a Privileged User"},
                    {"keyword": "And", "text": "I have access to the User Management Listing Page"}
                ]
            }
        }

        # Convert each AC to a scenario
        for req in requirements:
            scenario = {
                "name": f"{req['ac_id']} - {self._generate_scenario_name(req)}",
                "tags": [f"@{req['ac_id']}"],
                "steps": []
            }

            # Add Given step
            given_text = req['given']
            # Clean up common patterns
            given_text = self._clean_given_text(given_text)
            scenario["steps"].append({
                "keyword": "Given",
                "text": given_text
            })

            # Add When step
            when_text = req['when']
            when_text = self._clean_when_text(when_text)
            scenario["steps"].append({
                "keyword": "When",
                "text": f"I {when_text}" if not when_text.startswith("I ") else when_text
            })

            # Add Then step
            then_text = req['then']
            then_text = self._clean_then_text(then_text)
            scenario["steps"].append({
                "keyword": "Then",
                "text": f"I {then_text}" if not then_text.startswith("I ") else then_text
            })

            feature["scenarios"].append(scenario)

        return feature

    def _generate_scenario_name(self, req: Dict[str, Any]) -> str:
        """Generate a descriptive scenario name from AC"""
        when = req.get('when', '')
        then = req.get('then', '')

        # Extract key action
        action = "Verify"
        if "download" in when.lower():
            action = "Download"
        elif "click" in when.lower():
            action = "Click"
        elif "open" in when.lower():
            action = "Open"
        elif "enter" in when.lower():
            action = "Enter"

        # Extract key outcome
        outcome = "Expected Behavior"
        if "division" in then.lower():
            if "column" in then.lower():
                outcome = "Division Column Display"
            elif "filter" in then.lower():
                outcome = "Division Filter"
            elif "alphabetic" in then.lower():
                outcome = "Alphabetical Sorting"
        elif "epic" in then.lower():
            outcome = "Epic Filter"

        return f"{action} {outcome}"

    def _clean_given_text(self, text: str) -> str:
        """Clean up Given text"""
        # Remove redundant phrases
        replacements = {
            "A Privileged User who has access to User Management Listing Page logs into the system":
                "I am on the User Management Listing Page",
            "A Privileged User who has access to User Management Listing Page logs into BAP":
                "I am on the User Management Listing Page",
            "the system": "the User Management page"
        }

        for old, new in replacements.items():
            if old in text:
                return new

        return text

    def _clean_when_text(self, text: str) -> str:
        """Clean up When text"""
        # Remove "the user" prefix if present
        text = re.sub(r'^the\s+user\s+', '', text, flags=re.IGNORECASE)

        # Ensure it reads naturally
        replacements = {
            "downloads the User management csv report": "download the User Management CSV report",
            "clicks on create user and open the division dropdown": "click on Create User and open the Division dropdown",
            "opens the User Listing Page": "open the User Listing Page",
            "clicks on filter on Division column": "click on the Division column filter",
            "clicks on filter on Epic column": "click on the Epic column filter"
        }

        for old, new in replacements.items():
            if old in text:
                return new

        return text

    def _clean_then_text(self, text: str) -> str:
        """Clean up Then text"""
        # Ensure proper formatting
        replacements = {
            "should see Division column in the csv as the second column(before First Name)":
                "should see Division column as the second column (before First Name) in the CSV",
            "should see Division column in the Listing Page as the second column(before First Name)":
                "should see Division column as the second column (before First Name) on the page",
            "should see the filter on the Division column in the Listing Page":
                "should see a filter option on the Division column",
            "should be able to see all the Divisions and should be able to filter based on Division(s)":
                "should see all Divisions and be able to filter by them",
            "the Divisions should be listed in Alphabetic Order":
                "should see the Divisions listed in alphabetical order",
            "the Epic should be listed in Alphabetic Order":
                "should see the Epics listed in alphabetical order"
        }

        for old, new in replacements.items():
            if old in text:
                return new

        return text

    def _save_feature(self, feature: Dict[str, Any], output_dir: Path, index: int):
        """Save a feature to file"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        # Generate filename
        if self.ac_only_mode:
            # Use story key if available
            story_key = feature["name"].split(" - ")[0] if " - " in feature["name"] else "feature"
            filename = f"{story_key}_acceptance_criteria.feature"
        else:
            feature_name = feature["name"].replace(" ", "_").lower()
            filename = f"{index + 1:03d}_{feature_name}.feature"

        filepath = output_dir / filename

        # Generate Gherkin
        gherkin = self.generator.template_engine.render_feature(feature)
        filepath.write_text(gherkin)

        print(f"  ✅ Saved: {filepath.name}")