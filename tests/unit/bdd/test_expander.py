import pytest
from qa_copilot.bdd.expander import TestCaseExpander


class TestTestCaseExpander:
    """Test Test Case Expander"""

    @pytest.fixture
    def expander(self):
        return TestCaseExpander({
            "include_negative_tests": True,
            "include_edge_cases": True,
            "include_boundary_tests": True,
        })

    @pytest.fixture
    def base_scenario(self):
        return {
            "name": "Successful login",
            "tags": ["@positive"],
            "steps": [
                {"keyword": "Given", "text": "the user is on the login page"},
                {"keyword": "When", "text": "the user enters valid credentials"},
                {"keyword": "Then", "text": "the user should see dashboard"}
            ]
        }

    @pytest.fixture
    def parsed_data(self):
        return {
            "functionality": "authentication",
            "entities": ["username", "password"],
            "conditions": ["valid"]
        }

    def test_expand_authentication(self, expander, base_scenario, parsed_data):
        """Test authentication expansion"""
        scenarios = expander.expand(base_scenario, parsed_data)

        assert len(scenarios) > 0

        # Check for negative scenarios
        negative_scenarios = [s for s in scenarios if "@negative" in s.get("tags", [])]
        assert len(negative_scenarios) > 0

        # Check for edge cases
        edge_scenarios = [s for s in scenarios if "@edge" in s.get("tags", [])]
        assert len(edge_scenarios) > 0

    def test_expand_with_different_functionalities(self, expander):
        """Test expansion for different functionalities"""
        functionalities = ["authentication", "registration", "search", "form", "generic"]

        for func in functionalities:
            base = {"name": "Test", "steps": [], "tags": []}
            parsed = {"functionality": func}

            scenarios = expander.expand(base, parsed)
            # Should generate at least some scenarios for each
            assert isinstance(scenarios, list)