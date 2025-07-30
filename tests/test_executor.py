import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from qa_copilot.executor import TestExecutor, ExecutorConfig
from qa_copilot.executor.test_context import TestContext
from qa_copilot.executor.step_definitions import StepDefinitionRegistry


class TestExecutorConfig:
    """Test ExecutorConfig class"""

    def test_default_config(self):
        """Test default configuration values"""
        config = ExecutorConfig()
        assert config.browser == "chromium"
        assert config.headless == False
        assert config.timeout == 30000
        assert config.environment == "dev"
        assert config.parallel_workers == 1

    def test_custom_config(self):
        """Test custom configuration"""
        config = ExecutorConfig(
            browser="firefox",
            headless=True,
            timeout=60000,
            environment="staging"
        )
        assert config.browser == "firefox"
        assert config.headless == True
        assert config.timeout == 60000
        assert config.environment == "staging"


class TestStepDefinitionRegistry:
    """Test StepDefinitionRegistry"""

    def test_register_step_definition(self):
        """Test registering step definitions"""
        registry = StepDefinitionRegistry()

        @registry.given(r'I have (\d+) items')
        def given_items(context, count):
            context.items = int(count)

        # Check definition is registered
        definitions = registry.list_definitions()
        assert len(definitions) == 1
        assert definitions[0]['keyword'] == 'given'
        assert definitions[0]['function'] == 'given_items'

    def test_find_matching_definition(self):
        """Test finding matching step definition"""
        registry = StepDefinitionRegistry()

        @registry.when(r'I click the "([^"]*)" button')
        def click_button(context, button_name):
            pass

        # Find matching definition
        step_def = registry.find_step_definition('when', 'I click the "Login" button')
        assert step_def is not None
        assert step_def.function.__name__ == 'click_button'

        # Test non-matching
        step_def = registry.find_step_definition('when', 'I do something else')
        assert step_def is None

    def test_step_decorators(self):
        """Test step definition decorators"""
        registry = StepDefinitionRegistry()

        @registry.given('I am on the home page')
        @registry.when('I navigate to the home page')
        def navigate_home(context):
            pass

        # Should be registered for both keywords
        given_def = registry.find_step_definition('given', 'I am on the home page')
        when_def = registry.find_step_definition('when', 'I navigate to the home page')

        assert given_def is not None
        assert when_def is not None


class TestExecutor:
    """Test TestExecutor class"""

    @pytest.fixture
    def executor(self):
        """Create test executor instance"""
        config = ExecutorConfig(headless=True)
        return TestExecutor(config)

    def test_executor_initialization(self, executor):
        """Test executor initialization"""
        assert executor.config.headless == True
        assert executor.element_detector is not None
        assert executor.step_registry is not None
        assert executor.report_collector is not None

    def test_validate(self, executor):
        """Test configuration validation"""
        assert executor.validate() == True

        # Test invalid browser
        executor.config.browser = "invalid_browser"
        assert executor.validate() == False

    @patch('qa_copilot.executor.executor.Path.exists')
    @patch('builtins.open')
    @patch('yaml.safe_load')
    def test_load_environment_config(self, mock_yaml, mock_open, mock_exists):
        """Test loading environment configuration"""
        mock_exists.return_value = True
        mock_yaml.return_value = {
            'base_url': 'https://test.example.com',
            'roles': {
                'admin': {
                    'username': 'admin@example.com',
                    'password': 'admin123'
                }
            }
        }

        config = ExecutorConfig(environment='test')
        executor = TestExecutor(config)

        assert executor.env_config['base_url'] == 'https://test.example.com'
        assert 'admin' in executor.env_config['roles']

    def test_builtin_step_definitions(self, executor):
        """Test that built-in steps are registered"""
        registry = executor.step_registry

        # Test navigation step
        step_def = registry.find_step_definition('given', 'I navigate to the login page')
        assert step_def is not None

        # Test input step
        step_def = registry.find_step_definition('when', 'I enter "test" in the "username" field')
        assert step_def is not None

        # Test click step
        step_def = registry.find_step_definition('when', 'I click the "Submit" button')
        assert step_def is not None

        # Test verification step
        step_def = registry.find_step_definition('then', 'I verify text "Welcome"')
        assert step_def is not None

    @pytest.mark.asyncio
    async def test_execute_step(self, executor):
        """Test step execution"""
        # Mock page and context
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()

        context = TestContext(
            page=mock_page,
            element_detector=Mock(),
            base_url='https://example.com'
        )

        # Create a simple step
        from behave.model import Step
        step = Step('Given', 'Given', 'I navigate to the login page', 1)

        # Execute step
        result = {}
        await executor._execute_step(context, step, result)

        # Verify execution
        assert len(result['steps']) == 1
        assert result['steps'][0]['status'] == 'passed'
        mock_page.goto.assert_called_once()


class TestContext:
    """Test TestContext class"""

    @pytest.fixture
    def context(self):
        """Create test context"""
        mock_page = AsyncMock()
        mock_detector = Mock()

        return TestContext(
            page=mock_page,
            element_detector=mock_detector,
            base_url='https://example.com'
        )

    def test_load_credentials(self, context):
        """Test loading credentials"""
        env_config = {
            'roles': {
                'admin': {
                    'username': 'admin@test.com',
                    'password': 'admin123'
                },
                'user': {
                    'username': 'user@test.com',
                    'password': 'user123'
                }
            }
        }

        context.load_credentials(env_config)

        assert context.credentials['admin@test.com'] == 'admin123'
        assert context.credentials['user@test.com'] == 'user123'
        assert context.credentials['admin_password'] == 'admin123'

    def test_store_and_get_data(self, context):
        """Test data storage and retrieval"""
        context.store_data('user_id', '12345')
        context.store_data('status', 'active')

        assert context.get_data('user_id') == '12345'
        assert context.get_data('status') == 'active'
        assert context.get_data('missing', 'default') == 'default'

    @pytest.mark.asyncio
    async def test_find_element(self, context):
        """Test finding elements"""
        # Mock element detector
        mock_element = AsyncMock()
        context.element_detector.find_async = AsyncMock(return_value=mock_element)

        element = await context.find_element('Click Login button')

        assert element == mock_element
        context.element_detector.find_async.assert_called_once_with(
            context.page,
            'Click Login button',
            timeout=30000
        )

    @pytest.mark.asyncio
    async def test_wait_for_element(self, context):
        """Test waiting for element"""
        mock_element = AsyncMock()
        mock_element.wait_for = AsyncMock()
        context.element_detector.find_async = AsyncMock(return_value=mock_element)

        element = await context.wait_for_element('Submit button', state='visible')

        mock_element.wait_for.assert_called_once_with(state='visible', timeout=30000)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])