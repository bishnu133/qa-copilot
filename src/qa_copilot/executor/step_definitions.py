import re
import inspect
from typing import Dict, List, Callable, Pattern, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class StepDefinition:
    """Represents a step definition with its pattern and function"""
    keyword: str  # Given, When, Then, And, But
    pattern: Pattern
    function: Callable
    description: str = ""

    async def execute(self, context: Any, step_text: str) -> Any:
        """Execute the step function with extracted parameters"""
        # Extract parameters from step text using regex
        match = self.pattern.search(step_text)
        if not match:
            raise ValueError(f"Step text doesn't match pattern: {step_text}")

        # Get matched groups
        params = match.groups()

        # Execute function (handle both sync and async)
        if inspect.iscoroutinefunction(self.function):
            return await self.function(context, *params)
        else:
            return self.function(context, *params)


class StepDefinitionRegistry:
    """Registry for step definitions"""

    def __init__(self):
        self.definitions: List[StepDefinition] = []
        self._keyword_aliases = {
            'and': ['given', 'when', 'then'],
            'but': ['given', 'when', 'then']
        }

    def add_definition(self, keyword: str, pattern: str, function: Callable, description: str = ""):
        """Add a step definition to registry"""
        # Compile pattern if it's a string
        if isinstance(pattern, str):
            pattern = re.compile(pattern, re.IGNORECASE)

        definition = StepDefinition(
            keyword=keyword.lower(),
            pattern=pattern,
            function=function,
            description=description
        )

        self.definitions.append(definition)
        logger.debug(f"Registered step: {keyword} {pattern.pattern}")

    def given(self, pattern: str, description: str = ""):
        """Decorator for Given steps"""

        def decorator(func):
            self.add_definition('given', pattern, func, description)
            return func

        return decorator

    def when(self, pattern: str, description: str = ""):
        """Decorator for When steps"""

        def decorator(func):
            self.add_definition('when', pattern, func, description)
            return func

        return decorator

    def then(self, pattern: str, description: str = ""):
        """Decorator for Then steps"""

        def decorator(func):
            self.add_definition('then', pattern, func, description)
            return func

        return decorator

    def step(self, pattern: str, description: str = ""):
        """Decorator for any step type"""

        def decorator(func):
            # Register for all keywords
            for keyword in ['given', 'when', 'then']:
                self.add_definition(keyword, pattern, func, description)
            return func

        return decorator

    def find_step_definition(self, keyword: str, step_text: str) -> Optional[StepDefinition]:
        """Find matching step definition for given step text"""
        keyword = keyword.lower().strip()

        # Handle And/But keywords
        if keyword in self._keyword_aliases:
            # For And/But, we need to look at the previous step context
            # For now, try all possible keywords
            possible_keywords = self._keyword_aliases[keyword]
        else:
            possible_keywords = [keyword]

        # Search for matching definition
        for definition in self.definitions:
            if definition.keyword in possible_keywords:
                if definition.pattern.search(step_text):
                    logger.debug(f"Found matching step definition: {definition.pattern.pattern}")
                    return definition

        # If no match found, log available patterns for debugging
        logger.warning(f"No step definition found for: {keyword} {step_text}")
        logger.debug("Available patterns:")
        for definition in self.definitions:
            logger.debug(f"  {definition.keyword}: {definition.pattern.pattern}")

        return None

    def list_definitions(self) -> List[Dict[str, str]]:
        """List all registered step definitions"""
        return [
            {
                'keyword': defn.keyword,
                'pattern': defn.pattern.pattern,
                'description': defn.description,
                'function': defn.function.__name__
            }
            for defn in self.definitions
        ]

    def clear(self):
        """Clear all registered definitions"""
        self.definitions.clear()

    def register_from_module(self, module):
        """Register all step definitions from a module"""
        for name, obj in inspect.getmembers(module):
            if hasattr(obj, '_step_definition'):
                step_info = obj._step_definition
                self.add_definition(
                    step_info['keyword'],
                    step_info['pattern'],
                    obj,
                    step_info.get('description', '')
                )


# Utility decorators for marking functions as step definitions
def given(pattern: str, description: str = ""):
    """Mark function as a Given step"""

    def decorator(func):
        func._step_definition = {
            'keyword': 'given',
            'pattern': pattern,
            'description': description
        }
        return func

    return decorator


def when(pattern: str, description: str = ""):
    """Mark function as a When step"""

    def decorator(func):
        func._step_definition = {
            'keyword': 'when',
            'pattern': pattern,
            'description': description
        }
        return func

    return decorator


def then(pattern: str, description: str = ""):
    """Mark function as a Then step"""

    def decorator(func):
        func._step_definition = {
            'keyword': 'then',
            'pattern': pattern,
            'description': description
        }
        return func

    return decorator