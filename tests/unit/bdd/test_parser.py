import pytest
from qa_copilot.bdd.parser import NaturalLanguageParser


class TestNaturalLanguageParser:
    """Test Natural Language Parser"""

    @pytest.fixture
    def parser(self):
        return NaturalLanguageParser()

    def test_detect_functionality(self, parser):
        """Test functionality detection"""
        assert parser._detect_functionality("user can login") == "authentication"
        assert parser._detect_functionality("user can register") == "registration"
        assert parser._detect_functionality("user can search") == "search"
        assert parser._detect_functionality("add to cart") == "shopping"
        assert parser._detect_functionality("submit form") == "form"
        assert parser._detect_functionality("navigate to page") == "navigation"
        assert parser._detect_functionality("unknown action") == "generic"

    def test_parse_login_description(self, parser):
        """Test parsing login description"""
        result = parser.parse("User can login with valid credentials")

        assert result["functionality"] == "authentication"
        assert result["feature_name"] == "User Authentication"
        assert "login" in result["scenario_name"].lower()
        assert len(result["preconditions"]) > 0
        assert len(result["actions"]) > 0
        assert len(result["expectations"]) > 0

    def test_extract_conditions(self, parser):
        """Test condition extraction"""
        result = parser.parse("User can login with invalid password")
        assert "invalid" in result["conditions"]

        result = parser.parse("User can login with empty fields")
        assert "empty" in result["conditions"]

        result = parser.parse("User can login with valid credentials")
        assert "valid" in result["conditions"]

    def test_generate_tags(self, parser):
        """Test tag generation"""
        result = parser.parse("User must be able to login")
        assert "@critical" in result["tags"]
        assert "@authentication" in result["tags"]

        result = parser.parse("User can search with invalid input")
        assert "@negative" in result["tags"]
        assert "@search" in result["tags"]

    def test_extract_entities(self, parser):
        """Test entity extraction"""
        result = parser.parse('User enters "test@email.com" in email field')
        assert "test@email.com" in result["entities"]

        result = parser.parse("User can login with username and password")
        entities = result["entities"]
        assert "username" in entities or "user" in entities
        assert "password" in entities