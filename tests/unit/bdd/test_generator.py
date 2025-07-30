import pytest
from qa_copilot.bdd import BDDGenerator
from qa_copilot.core import ModuleStatus


class TestBDDGenerator:
    """Test BDD Generator class"""

    @pytest.fixture
    def generator(self):
        """Create BDD generator instance"""
        return BDDGenerator({
            "expansion_level": "medium",
            "include_negative_tests": True,
            "include_edge_cases": True,
        })

    def test_initialization(self, generator):
        """Test generator initialization"""
        assert generator.status == ModuleStatus.READY
        assert generator.config["expansion_level"] == "medium"
        assert generator.template_engine is not None
        assert generator.expander is not None
        assert generator.parser is not None

    def test_module_info(self, generator):
        """Test module info"""
        info = generator.get_info()
        assert info.name == "BDD Generator"
        assert "jinja2" in info.dependencies
        assert info.has_ai is False

    def test_generate_login_scenario(self, generator):
        """Test generating login scenario"""
        description = "User can login with valid credentials"
        feature = generator.generate(description)

        assert feature["name"] == "User Authentication"
        assert len(feature["scenarios"]) > 1  # Should have multiple scenarios

        # Check base scenario
        base_scenario = feature["scenarios"][0]
        assert "login" in base_scenario["name"].lower()
        assert len(base_scenario["steps"]) > 0

        # Check for Given, When, Then steps
        step_keywords = [step["keyword"] for step in base_scenario["steps"]]
        assert "Given" in step_keywords
        assert "When" in step_keywords
        assert "Then" in step_keywords

    def test_generate_registration_scenario(self, generator):
        """Test generating registration scenario"""
        description = "User can register with email and password"
        feature = generator.generate(description)

        assert feature["name"] == "User Registration"
        assert any("register" in s["name"].lower() for s in feature["scenarios"])

    def test_generate_search_scenario(self, generator):
        """Test generating search scenario"""
        description = "User can search for products"
        feature = generator.generate(description)

        assert feature["name"] == "Search Functionality"
        assert any("search" in s["name"].lower() for s in feature["scenarios"])

    def test_minimal_expansion(self):
        """Test minimal expansion level"""
        generator = BDDGenerator({
            "expansion_level": "minimal"
        })

        feature = generator.generate("User can login")
        assert len(feature["scenarios"]) == 1  # Only base scenario

    def test_comprehensive_expansion(self):
        """Test comprehensive expansion"""
        generator = BDDGenerator({
            "expansion_level": "comprehensive",
            "max_scenarios_per_feature": 20
        })

        feature = generator.generate("User can login")
        assert len(feature["scenarios"]) > 3  # Multiple scenarios

    def test_generate_gherkin(self, generator):
        """Test Gherkin generation"""
        description = "User can login with valid credentials"
        gherkin = generator.generate_gherkin(description)

        assert "Feature:" in gherkin
        assert "Scenario:" in gherkin
        assert "Given" in gherkin
        assert "When" in gherkin
        assert "Then" in gherkin

    def test_tags_generation(self, generator):
        """Test tag generation"""
        feature = generator.generate("User can login with valid credentials")

        # Check feature has scenarios with tags
        for scenario in feature["scenarios"]:
            assert len(scenario.get("tags", [])) > 0

        # Should have @authentication tag
        all_tags = []
        for scenario in feature["scenarios"]:
            all_tags.extend(scenario.get("tags", []))

        assert "@authentication" in all_tags
        assert "@automated" in all_tags