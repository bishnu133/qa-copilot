import re
from typing import Dict, Any, List, Tuple


class NaturalLanguageParser:
    """
    Parses natural language descriptions into structured BDD components.
    """

    def __init__(self):
        # Common patterns for different types of functionality
        self.functionality_patterns = {
            "authentication": {
                "keywords": ["login", "signin", "sign in", "authenticate", "logout", "sign out"],
                "preconditions": ["the user is on the login page"],
                "entities": ["user", "username", "password", "credentials"]
            },
            "registration": {
                "keywords": ["register", "signup", "sign up", "create account", "join"],
                "preconditions": ["the user is on the registration page"],
                "entities": ["user", "email", "password", "account"]
            },
            "search": {
                "keywords": ["search", "find", "look for", "query", "filter"],
                "preconditions": ["the user is on the search page"],
                "entities": ["search term", "results", "filters"]
            },
            "shopping": {
                "keywords": ["add to cart", "buy", "purchase", "checkout", "order"],
                "preconditions": ["the user is on the product page"],
                "entities": ["product", "cart", "price", "quantity"]
            },
            "form": {
                "keywords": ["fill", "submit", "enter", "form", "input"],
                "preconditions": ["the user is on the form page"],
                "entities": ["form", "field", "data"]
            },
            "navigation": {
                "keywords": ["navigate", "go to", "visit", "open", "access"],
                "preconditions": ["the user is on the home page"],
                "entities": ["page", "link", "menu"]
            }
        }

        # Action patterns
        self.action_patterns = {
            r"(?:user\s+)?(?:can|should\s+be\s+able\s+to|is\s+able\s+to)\s+(.+)": "ability",
            r"(?:when\s+)?(?:user\s+)?(.+)": "action",
            r"(?:verify|check|ensure)\s+(?:that\s+)?(.+)": "verification",
            r"(?:validate)\s+(.+)": "validation",
        }

        # Condition patterns
        self.condition_patterns = {
            "valid": ["valid", "correct", "proper", "right"],
            "invalid": ["invalid", "incorrect", "wrong", "bad"],
            "empty": ["empty", "blank", "missing"],
            "special": ["special characters", "special"],
        }

    def parse(self, description: str) -> Dict[str, Any]:
        """
        Parse natural language description into BDD components.

        Args:
            description: Natural language description

        Returns:
            Dictionary containing parsed components
        """
        # Normalize description
        description = description.strip()
        desc_lower = description.lower()

        # Detect functionality type
        functionality = self._detect_functionality(desc_lower)

        # Extract components
        result = {
            "original": description,
            "functionality": functionality,
            "feature_name": self._generate_feature_name(description, functionality),
            "scenario_name": self._generate_scenario_name(description),
            "preconditions": self._extract_preconditions(description, functionality),
            "actions": self._extract_actions(description),
            "expectations": self._extract_expectations(description),
            "entities": self._extract_entities(description, functionality),
            "conditions": self._extract_conditions(desc_lower),
            "data_examples": self._generate_data_examples(functionality),
            "tags": self._generate_tags(functionality, desc_lower),
        }

        return result

    def _detect_functionality(self, description: str) -> str:
        """Detect the type of functionality being described"""
        for func_type, config in self.functionality_patterns.items():
            if any(keyword in description for keyword in config["keywords"]):
                return func_type
        return "generic"

    def _generate_feature_name(self, description: str, functionality: str) -> str:
        """Generate a feature name from description"""
        if functionality == "authentication":
            return "User Authentication"
        elif functionality == "registration":
            return "User Registration"
        elif functionality == "search":
            return "Search Functionality"
        elif functionality == "shopping":
            return "Shopping Cart"
        elif functionality == "form":
            return "Form Submission"
        elif functionality == "navigation":
            return "Site Navigation"
        else:
            # Extract key words for feature name
            words = description.split()
            if len(words) > 3:
                return " ".join(words[:3]).title()
            return description.title()

    def _generate_scenario_name(self, description: str) -> str:
        """Generate scenario name from description"""
        # Remove common prefixes
        prefixes = ["user can", "user should be able to", "verify that", "ensure that"]
        desc_lower = description.lower()

        for prefix in prefixes:
            if desc_lower.startswith(prefix):
                description = description[len(prefix):].strip()
                break

        # Capitalize first letter
        if description:
            return description[0].upper() + description[1:]
        return "Default scenario"

    def _extract_preconditions(self, description: str, functionality: str) -> List[str]:
        """Extract preconditions based on functionality"""
        preconditions = []

        # Add default preconditions based on functionality
        if functionality in self.functionality_patterns:
            preconditions.extend(self.functionality_patterns[functionality]["preconditions"])

        # Look for explicit preconditions in description
        if "given" in description.lower():
            # Extract given conditions
            given_match = re.search(r"given\s+(.+?)(?:when|then|$)", description, re.IGNORECASE)
            if given_match:
                preconditions.append(given_match.group(1).strip())

        # Add context-specific preconditions
        if "logged in" in description.lower() and "the user is logged in" not in preconditions:
            preconditions.append("the user is logged in")

        return preconditions if preconditions else ["the user is on the application"]

    def _extract_actions(self, description: str) -> List[str]:
        """Extract actions from description"""
        actions = []
        desc_lower = description.lower()

        # Authentication actions
        if "login" in desc_lower or "sign in" in desc_lower:
            if "valid" in desc_lower:
                actions.extend([
                    'the user enters "valid_user" in username field',
                    'the user enters "valid_password" in password field',
                    "the user clicks on Login button"
                ])
            else:
                actions.append("the user attempts to login")

        # Registration actions
        elif "register" in desc_lower or "sign up" in desc_lower:
            actions.extend([
                "the user fills in the registration form",
                "the user clicks on Register button"
            ])

        # Search actions
        elif "search" in desc_lower:
            actions.extend([
                'the user enters "search term" in search field',
                "the user clicks on Search button"
            ])

        # Form actions
        elif "form" in desc_lower or "submit" in desc_lower:
            actions.extend([
                "the user fills in all required fields",
                "the user clicks on Submit button"
            ])

        # Shopping actions
        elif "add to cart" in desc_lower:
            actions.extend([
                "the user selects a product",
                "the user clicks on Add to Cart button"
            ])

        # Generic action extraction
        else:
            # Try to extract verb phrases
            verb_pattern = r"(?:can|should|must|will)\s+(\w+)"
            matches = re.findall(verb_pattern, desc_lower)
            for match in matches:
                actions.append(f"the user {match}s")

        return actions if actions else ["the user performs the action"]

    def _extract_expectations(self, description: str) -> List[str]:
        """Extract expected outcomes"""
        expectations = []
        desc_lower = description.lower()

        # Success expectations
        if any(word in desc_lower for word in ["success", "successful", "valid"]):
            if "login" in desc_lower:
                expectations.append("the user should see the dashboard")
            elif "register" in desc_lower:
                expectations.append("the user account should be created successfully")
            elif "search" in desc_lower:
                expectations.append("the user should see relevant search results")
            elif "cart" in desc_lower:
                expectations.append("the product should be added to the cart")
            else:
                expectations.append("the action should complete successfully")

        # Failure expectations
        elif any(word in desc_lower for word in ["fail", "error", "invalid"]):
            expectations.append('the user should see an error message')

        # Validation expectations
        elif "validate" in desc_lower or "verify" in desc_lower:
            expectations.append("the system should validate the input")

        # Navigation expectations
        elif "navigate" in desc_lower or "redirect" in desc_lower:
            expectations.append("the user should be redirected to the appropriate page")

        # Default expectation
        else:
            expectations.append("the system should respond appropriately")

        return expectations

    def _extract_entities(self, description: str, functionality: str) -> List[str]:
        """Extract entities mentioned in the description"""
        entities = []

        # Get default entities for functionality
        if functionality in self.functionality_patterns:
            entities.extend(self.functionality_patterns[functionality]["entities"])

        # Extract specific entities from description
        # Look for quoted strings
        quoted_pattern = r'"([^"]+)"'
        quoted_matches = re.findall(quoted_pattern, description)
        entities.extend(quoted_matches)

        return list(set(entities))  # Remove duplicates

    def _extract_conditions(self, description: str) -> List[str]:
        """Extract test conditions"""
        conditions = []

        for condition_type, keywords in self.condition_patterns.items():
            if any(keyword in description for keyword in keywords):
                conditions.append(condition_type)

        return conditions

    def _generate_data_examples(self, functionality: str) -> Dict[str, List[Any]]:
        """Generate example data based on functionality"""
        examples = {}

        if functionality == "authentication":
            examples = {
                "username": ["valid_user", "invalid_user", "", "user@email.com"],
                "password": ["valid_pass", "wrong_pass", "", "Pass123!"],
            }
        elif functionality == "registration":
            examples = {
                "email": ["user@email.com", "invalid-email", "", "user+test@email.com"],
                "password": ["ValidPass123!", "weak", "", "NoSpecialChar1"],
                "username": ["newuser", "a", "", "user_with_special_@"],
            }
        elif functionality == "search":
            examples = {
                "search_term": ["product", "", "special@char", "very long search term"],
            }

        return examples

    def _generate_tags(self, functionality: str, description: str) -> List[str]:
        """Generate relevant tags"""
        tags = []

        # Add functionality tag
        if functionality != "generic":
            tags.append(f"@{functionality}")

        # Add priority tags
        if any(word in description for word in ["critical", "important", "must"]):
            tags.append("@critical")
        elif any(word in description for word in ["should", "normal"]):
            tags.append("@normal")

        # Add test type tags
        if "positive" in description or "valid" in description:
            tags.append("@positive")
        elif "negative" in description or "invalid" in description:
            tags.append("@negative")

        # Add automation tag
        tags.append("@automated")

        return tags