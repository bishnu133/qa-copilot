import re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from ..core import (
    ConfigurableModule,
    ModuleInfo,
    ExecutionResult,
    ModuleStatus,
    BDDGenerationError,
)
from .templates import TemplateEngine
from .expander import TestCaseExpander
from .parser import NaturalLanguageParser


class BDDGenerator(ConfigurableModule):
    """
    Generates BDD scenarios from plain English descriptions.

    Example:
        generator = BDDGenerator()
        feature = generator.generate("User can login with valid credentials")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.template_engine = TemplateEngine(self.config.get("template_path"))
        self.expander = TestCaseExpander(self.config)
        self.parser = NaturalLanguageParser()

    def _initialize(self) -> None:
        """Initialize the BDD generator module"""
        self.logger.info("Initializing BDD Generator")
        if self.validate():
            self.status = ModuleStatus.READY
        else:
            self.status = ModuleStatus.ERROR

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "expansion_level": "medium",  # minimal, medium, comprehensive
            "include_negative_tests": True,
            "include_edge_cases": True,
            "include_boundary_tests": True,
            "data_driven": True,
            "max_scenarios_per_feature": 10,
            "template_style": "cucumber",  # cucumber, behave, pytest-bdd
            "output_format": "feature",  # feature, json, yaml
        }

    def execute(self, input_data: Any) -> ExecutionResult:
        """Execute BDD generation"""
        if isinstance(input_data, str):
            description = input_data
        elif isinstance(input_data, dict):
            description = input_data.get("description", "")
        else:
            return ExecutionResult(
                success=False,
                data=None,
                error="Input must be a string description or dict with 'description'"
            )

        try:
            feature = self.generate(description)
            return ExecutionResult(
                success=True,
                data=feature,
                metadata={
                    "description": description,
                    "scenarios_count": len(feature.get("scenarios", []))
                }
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                data=None,
                error=str(e)
            )

    def generate(self, description: str) -> Dict[str, Any]:
        """
        Generate BDD feature from plain English description.

        Args:
            description: Natural language description

        Returns:
            Dictionary containing feature data
        """
        # Parse the description
        parsed = self.parser.parse(description)
        self.logger.info(f"Parsed description: {parsed}")

        # Generate base scenario
        base_scenario = self._generate_base_scenario(parsed)

        # Expand test cases based on configuration
        scenarios = [base_scenario]

        if self.config.get("expansion_level") != "minimal":
            expanded = self.expander.expand(base_scenario, parsed)
            scenarios.extend(expanded)

        # Create feature
        feature = {
            "name": parsed.get("feature_name", "Generated Feature"),
            "description": parsed.get("feature_description", description),
            "scenarios": scenarios[:self.config.get("max_scenarios_per_feature", 10)],
            "tags": parsed.get("tags", []),
            "background": self._generate_background(parsed),
        }

        return feature

    def generate_gherkin(self, description: str) -> str:
        """
        Generate Gherkin formatted feature file.

        Args:
            description: Natural language description

        Returns:
            Gherkin formatted string
        """
        feature = self.generate(description)
        return self.template_engine.render_feature(feature)

    def _generate_base_scenario(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the base positive scenario"""
        scenario = {
            "name": parsed.get("scenario_name", "Default scenario"),
            "description": parsed.get("scenario_description", ""),
            "tags": [],
            "steps": []
        }

        # Generate Given steps (preconditions)
        for precondition in parsed.get("preconditions", []):
            scenario["steps"].append({
                "keyword": "Given",
                "text": precondition,
                "data_table": None
            })

        # Generate When steps (actions)
        for action in parsed.get("actions", []):
            keyword = "When" if scenario["steps"] and scenario["steps"][-1]["keyword"] != "When" else "And"
            scenario["steps"].append({
                "keyword": keyword,
                "text": action,
                "data_table": None
            })

        # Generate Then steps (expectations)
        for expectation in parsed.get("expectations", []):
            keyword = "Then" if not any(s["keyword"] == "Then" for s in scenario["steps"]) else "And"
            scenario["steps"].append({
                "keyword": keyword,
                "text": expectation,
                "data_table": None
            })

        return scenario

    def _generate_background(self, parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate background steps if common preconditions exist"""
        common_preconditions = parsed.get("common_preconditions", [])

        if not common_preconditions:
            return None

        return {
            "steps": [
                {"keyword": "Given", "text": precondition}
                for precondition in common_preconditions
            ]
        }

    def validate(self) -> bool:
        """Validate module configuration"""
        try:
            # Check expansion level
            valid_levels = ["minimal", "medium", "comprehensive"]
            if self.config.get("expansion_level") not in valid_levels:
                self.logger.error(f"Invalid expansion level: {self.config.get('expansion_level')}")
                return False

            # Check template style
            valid_styles = ["cucumber", "behave", "pytest-bdd"]
            if self.config.get("template_style") not in valid_styles:
                self.logger.error(f"Invalid template style: {self.config.get('template_style')}")
                return False

            return True
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False

    def get_info(self) -> ModuleInfo:
        """Get module information"""
        return ModuleInfo(
            name="BDD Generator",
            version="0.1.0",
            description="Generates BDD scenarios from plain English descriptions",
            author="QA Copilot Contributors",
            dependencies=["jinja2"],
            optional_dependencies=["gherkin-official"],
            has_ai=False
        )

    def save_feature(self, feature: Dict[str, Any], filepath: Path) -> None:
        """Save feature to file"""
        gherkin = self.template_engine.render_feature(feature)
        filepath.write_text(gherkin)
        self.logger.info(f"Feature saved to: {filepath}")