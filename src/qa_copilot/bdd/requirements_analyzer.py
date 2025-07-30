from typing import List, Dict, Any
from .parser import NaturalLanguageParser
from .generator import BDDGenerator


class RequirementsAnalyzer:
    """Analyzes requirements from various sources and generates BDD scenarios"""

    def __init__(self, bdd_generator: BDDGenerator = None):
        self.bdd_generator = bdd_generator or BDDGenerator()
        self.nl_parser = NaturalLanguageParser()

        # Requirement patterns
        self.requirement_patterns = {
            "must": "critical",
            "should": "high",
            "could": "medium",
            "won't": "low"
        }

    def analyze_requirements(self, requirements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze requirements and generate BDD features"""
        features = []

        for req in requirements:
            # Generate BDD from requirement
            if req.get("story"):
                feature = self.bdd_generator.generate(req["story"])

                # Enhance with requirement context
                feature["source"] = req.get("source", "unknown")
                feature["requirement_id"] = req.get("key", "")

                # Add acceptance criteria as additional scenarios
                if req.get("acceptance_criteria") or req.get("criteria"):
                    criteria = req.get("acceptance_criteria") or req.get("criteria", [])
                    additional_scenarios = self._generate_scenarios_from_criteria(criteria)
                    feature["scenarios"].extend(additional_scenarios)

                features.append(feature)

        return features

    def _generate_scenarios_from_criteria(self, criteria: List[str]) -> List[Dict[str, Any]]:
        """Generate scenarios from acceptance criteria"""
        scenarios = []

        for criterion in criteria:
            # Check if it's already in Given/When/Then format
            if any(keyword in criterion for keyword in ["Given", "When", "Then"]):
                scenario = self._parse_gherkin_criterion(criterion)
            else:
                # Convert to scenario
                scenario = self._convert_criterion_to_scenario(criterion)

            if scenario:
                scenarios.append(scenario)

        return scenarios

    def _parse_gherkin_criterion(self, criterion: str) -> Dict[str, Any]:
        """Parse criterion that's already in Gherkin format"""
        steps = []

        # Split by Given/When/Then
        pattern = r"(Given|When|Then|And|But)\s+(.+?)(?=(?:Given|When|Then|And|But)|$)"
        matches = re.findall(pattern, criterion, re.IGNORECASE)

        for keyword, text in matches:
            steps.append({
                "keyword": keyword.capitalize(),
                "text": text.strip()
            })

        if steps:
            return {
                "name": "Acceptance Criterion",
                "steps": steps,
                "tags": ["@acceptance_criteria"]
            }

        return None

    def _convert_criterion_to_scenario(self, criterion: str) -> Dict[str, Any]:
        """Convert plain text criterion to scenario"""
        # Analyze the criterion
        parsed = self.nl_parser.parse(criterion)

        # Create scenario
        scenario = {
            "name": f"System {criterion}",
            "tags": ["@acceptance_criteria"],
            "steps": []
        }

        # Add steps based on criterion type
        if "display" in criterion.lower() or "show" in criterion.lower():
            scenario["steps"] = [
                {"keyword": "When", "text": "the user performs the action"},
                {"keyword": "Then", "text": criterion}
            ]
        elif "validate" in criterion.lower():
            scenario["steps"] = [
                {"keyword": "When", "text": "the user provides input"},
                {"keyword": "Then", "text": criterion}
            ]
        else:
            scenario["steps"] = [
                {"keyword": "Given", "text": "the system is ready"},
                {"keyword": "Then", "text": criterion}
            ]

        return scenario