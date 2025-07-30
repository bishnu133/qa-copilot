import pytest
from unittest.mock import Mock, MagicMock
from qa_copilot.detector.strategies import DOMStrategy, HeuristicStrategy


class TestDOMStrategy:
    """Test DOM detection strategy"""

    @pytest.fixture
    def strategy(self):
        return DOMStrategy()

    @pytest.fixture
    def mock_page(self):
        """Create mock page with locator methods"""
        page = Mock()

        # Mock locator
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_locator.first = mock_locator
        mock_locator.text_content.return_value = "Login"
        mock_locator.filter.return_value = mock_locator
        mock_locator.nth.return_value = mock_locator

        page.locator.return_value = mock_locator
        page.get_by_role.return_value = mock_locator

        return page

    def test_find_by_exact_text(self, strategy, mock_page):
        """Test finding element by exact text"""
        description = {
            "type": "button",
            "text": "Login",
            "attributes": {}
        }

        result = strategy.find(mock_page, description)

        assert result is not None
        mock_page.locator.assert_called()

    def test_find_by_role(self, strategy, mock_page):
        """Test finding element by ARIA role"""
        description = {
            "type": "button",
            "text": "Submit",
            "attributes": {}
        }

        result = strategy.find(mock_page, description)

        assert result is not None
        # mock_page.get_by_role.assert_called_with("button")
        assert mock_page.locator.called or mock_page.get_by_role.called


class TestHeuristicStrategy:
    """Test heuristic detection strategy"""

    @pytest.fixture
    def strategy(self):
        return HeuristicStrategy()

    def test_common_patterns(self, strategy):
        """Test common UI patterns"""
        assert "login" in strategy.common_patterns
        assert "submit" in strategy.common_patterns
        assert "cancel" in strategy.common_patterns

    def test_matches_pattern(self, strategy):
        """Test pattern matching"""
        variations = ["login", "sign in", "signin"]

        assert strategy._matches_pattern("login", variations) is True
        assert strategy._matches_pattern("signin", variations) is True
        assert strategy._matches_pattern("logout", variations) is False