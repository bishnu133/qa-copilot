import pytest
from qa_copilot.bdd.templates import TemplateEngine


class TestTemplateEngine:
    """Test Template Engine"""

    @pytest.fixture
    def template_engine(self):
        return TemplateEngine()

    @pytest.fixture
    def sample_feature(self):
        return {
            "name": "Test Feature",
            "description": "Test description",
            "tags": ["@test", "@automated"],
            "scenarios": [
                {
                    "name": "Test Scenario",
                    "tags": ["@positive"],
                    "steps": [
                        {"keyword": "Given", "text": "a precondition"},
                        {"keyword": "When", "text": "an action occurs"},
                        {"keyword": "Then", "text": "expect a result"}
                    ]
                }
            ],
            "background": None
        }

    def test_render_cucumber_feature(self, template_engine, sample_feature):
        """Test Cucumber format rendering"""
        result = template_engine.render_feature(sample_feature, style="cucumber")

        assert "@test" in result
        assert "Feature: Test Feature" in result
        assert "Scenario: Test Scenario" in result
        assert "Given a precondition" in result
        assert "When an action occurs" in result
        assert "Then expect a result" in result

    def test_render_with_background(self, template_engine, sample_feature):
        """Test rendering with background steps"""
        sample_feature["background"] = {
            "steps": [
                {"keyword": "Given", "text": "common setup"}
            ]
        }

        result = template_engine.render_feature(sample_feature)
        assert "Background:" in result
        assert "Given common setup" in result

    def test_render_scenario_outline(self, template_engine):
        """Test scenario outline rendering"""
        scenario = {
            "name": "Login with credentials",
            "steps": [
                {"keyword": "When", "text": 'user enters "<username>"'},
                {"keyword": "Then", "text": 'result is "<result>"'}
            ]
        }

        examples = [
            {"username": "valid_user", "result": "success"},
            {"username": "invalid_user", "result": "failure"}
        ]

        result = template_engine.render_scenario_outline(scenario, examples)

        assert "Scenario Outline:" in result
        assert "Examples:" in result
        assert "| username | result |" in result
        assert "| valid_user | success |" in result