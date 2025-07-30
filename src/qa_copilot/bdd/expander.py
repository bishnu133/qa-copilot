from typing import Dict, Any, List
import copy


class TestCaseExpander:
    """
    Expands a base scenario into multiple test cases including:
    - Positive scenarios
    - Negative scenarios
    - Edge cases
    - Boundary value tests
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.expansion_strategies = {
            "authentication": self._expand_authentication,
            "registration": self._expand_registration,
            "search": self._expand_search,
            "form": self._expand_form,
            "generic": self._expand_generic,
        }

    def expand(self, base_scenario: Dict[str, Any], parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Expand base scenario into multiple test scenarios.

        Args:
            base_scenario: The base positive scenario
            parsed: Parsed description data

        Returns:
            List of expanded scenarios
        """
        scenarios = []
        functionality = parsed.get("functionality", "generic")

        # Get expansion strategy
        expand_func = self.expansion_strategies.get(
            functionality,
            self._expand_generic
        )

        # Generate scenarios based on configuration
        if self.config.get("include_negative_tests", True):
            scenarios.extend(expand_func(base_scenario, parsed, "negative"))

        if self.config.get("include_edge_cases", True):
            scenarios.extend(expand_func(base_scenario, parsed, "edge"))

        if self.config.get("include_boundary_tests", True):
            scenarios.extend(expand_func(base_scenario, parsed, "boundary"))

        return scenarios

    def _expand_authentication(self, base_scenario: Dict[str, Any],
                               parsed: Dict[str, Any], test_type: str) -> List[Dict[str, Any]]:
        """Expand authentication scenarios"""
        scenarios = []

        if test_type == "negative":
            # Invalid username
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Login fails with invalid username"
            scenario["tags"] = ["@negative", "@authentication"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the login page"},
                {"keyword": "When", "text": 'the user enters "invalid_user" in username field'},
                {"keyword": "And", "text": 'the user enters "valid_password" in password field'},
                {"keyword": "And", "text": "the user clicks on Login button"},
                {"keyword": "Then", "text": 'the user should see error message "Invalid credentials"'},
            ]
            scenarios.append(scenario)

            # Invalid password
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Login fails with invalid password"
            scenario["tags"] = ["@negative", "@authentication"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the login page"},
                {"keyword": "When", "text": 'the user enters "valid_user" in username field'},
                {"keyword": "And", "text": 'the user enters "wrong_password" in password field'},
                {"keyword": "And", "text": "the user clicks on Login button"},
                {"keyword": "Then", "text": 'the user should see error message "Invalid credentials"'},
            ]
            scenarios.append(scenario)

        elif test_type == "edge":
            # Empty credentials
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Login fails with empty credentials"
            scenario["tags"] = ["@edge", "@authentication"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the login page"},
                {"keyword": "When", "text": "the user clicks on Login button"},
                {"keyword": "Then", "text": 'the user should see error message "Username and password are required"'},
            ]
            scenarios.append(scenario)

            # SQL injection attempt
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Login handles SQL injection attempts"
            scenario["tags"] = ["@security", "@edge", "@authentication"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the login page"},
                {"keyword": "When", "text": '''the user enters "admin' OR '1'='1" in username field'''},
                {"keyword": "And", "text": 'the user enters "password" in password field'},
                {"keyword": "And", "text": "the user clicks on Login button"},
                {"keyword": "Then", "text": 'the user should see error message "Invalid credentials"'},
            ]
            scenarios.append(scenario)

        elif test_type == "boundary":
            # Maximum length username
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Login with maximum length username"
            scenario["tags"] = ["@boundary", "@authentication"]
            long_username = "a" * 255
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the login page"},
                {"keyword": "When", "text": f'the user enters "{long_username}" in username field'},
                {"keyword": "And", "text": 'the user enters "valid_password" in password field'},
                {"keyword": "And", "text": "the user clicks on Login button"},
                {"keyword": "Then", "text": "the system should handle the input appropriately"},
            ]
            scenarios.append(scenario)

        return scenarios

    def _expand_registration(self, base_scenario: Dict[str, Any],
                             parsed: Dict[str, Any], test_type: str) -> List[Dict[str, Any]]:
        """Expand registration scenarios"""
        scenarios = []

        if test_type == "negative":
            # Existing email
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Registration fails with existing email"
            scenario["tags"] = ["@negative", "@registration"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the registration page"},
                {"keyword": "And", "text": 'an account with email "existing@email.com" already exists'},
                {"keyword": "When", "text": 'the user enters "existing@email.com" in email field'},
                {"keyword": "And", "text": "the user fills in other required fields"},
                {"keyword": "And", "text": "the user clicks on Register button"},
                {"keyword": "Then", "text": 'the user should see error message "Email already registered"'},
            ]
            scenarios.append(scenario)

            # Invalid email format
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Registration fails with invalid email format"
            scenario["tags"] = ["@negative", "@registration"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the registration page"},
                {"keyword": "When", "text": 'the user enters "invalid-email" in email field'},
                {"keyword": "And", "text": "the user fills in other required fields"},
                {"keyword": "And", "text": "the user clicks on Register button"},
                {"keyword": "Then", "text": 'the user should see error message "Please enter a valid email"'},
            ]
            scenarios.append(scenario)

        elif test_type == "edge":
            # Special characters in username
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Registration with special characters in username"
            scenario["tags"] = ["@edge", "@registration"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the registration page"},
                {"keyword": "When", "text": 'the user enters "user@#$%test" in username field'},
                {"keyword": "And", "text": 'the user enters "valid@email.com" in email field'},
                {"keyword": "And", "text": 'the user enters "ValidPass123!" in password field'},
                {"keyword": "And", "text": "the user clicks on Register button"},
                {"keyword": "Then", "text": "the system should validate the username format"},
            ]
            scenarios.append(scenario)

        elif test_type == "boundary":
            # Minimum password length
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Registration with minimum password length"
            scenario["tags"] = ["@boundary", "@registration"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the registration page"},
                {"keyword": "When", "text": "the user fills in all required fields"},
                {"keyword": "And", "text": 'the user enters "Pass1!" in password field'},
                {"keyword": "And", "text": "the user clicks on Register button"},
                {"keyword": "Then", "text": "the registration should be processed"},
            ]
            scenarios.append(scenario)

        return scenarios

    def _expand_search(self, base_scenario: Dict[str, Any],
                       parsed: Dict[str, Any], test_type: str) -> List[Dict[str, Any]]:
        """Expand search scenarios"""
        scenarios = []

        if test_type == "negative":
            # No results found
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Search returns no results message"
            scenario["tags"] = ["@negative", "@search"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the search page"},
                {"keyword": "When", "text": 'the user enters "xyznonexistentterm123" in search field'},
                {"keyword": "And", "text": "the user clicks on Search button"},
                {"keyword": "Then", "text": 'the user should see message "No results found"'},
            ]
            scenarios.append(scenario)

        elif test_type == "edge":
            # Empty search
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Search with empty query"
            scenario["tags"] = ["@edge", "@search"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the search page"},
                {"keyword": "When", "text": "the user clicks on Search button"},
                {"keyword": "Then", "text": 'the user should see message "Please enter a search term"'},
            ]
            scenarios.append(scenario)

            # Special characters search
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Search with special characters"
            scenario["tags"] = ["@edge", "@search"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the search page"},
                {"keyword": "When", "text": 'the user enters "@#$%^&*()" in search field'},
                {"keyword": "And", "text": "the user clicks on Search button"},
                {"keyword": "Then", "text": "the search should be handled safely"},
            ]
            scenarios.append(scenario)

        elif test_type == "boundary":
            # Very long search term
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Search with maximum length query"
            scenario["tags"] = ["@boundary", "@search"]
            long_search = "search " * 50  # 350 characters
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the search page"},
                {"keyword": "When", "text": f'the user enters "{long_search}" in search field'},
                {"keyword": "And", "text": "the user clicks on Search button"},
                {"keyword": "Then", "text": "the search should be processed within reasonable time"},
            ]
            scenarios.append(scenario)

        return scenarios

    def _expand_form(self, base_scenario: Dict[str, Any],
                     parsed: Dict[str, Any], test_type: str) -> List[Dict[str, Any]]:
        """Expand form scenarios"""
        scenarios = []

        if test_type == "negative":
            # Missing required fields
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Form submission fails with missing required fields"
            scenario["tags"] = ["@negative", "@form"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the form page"},
                {"keyword": "When", "text": "the user leaves required fields empty"},
                {"keyword": "And", "text": "the user clicks on Submit button"},
                {"keyword": "Then", "text": 'the user should see validation errors for required fields'},
            ]
            scenarios.append(scenario)

        elif test_type == "edge":
            # Form with all optional fields empty
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Form submission with only required fields"
            scenario["tags"] = ["@edge", "@form"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the form page"},
                {"keyword": "When", "text": "the user fills in only the required fields"},
                {"keyword": "And", "text": "the user clicks on Submit button"},
                {"keyword": "Then", "text": "the form should be submitted successfully"},
            ]
            scenarios.append(scenario)

        elif test_type == "boundary":
            # Maximum field lengths
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = "Form submission with maximum field lengths"
            scenario["tags"] = ["@boundary", "@form"]
            scenario["steps"] = [
                {"keyword": "Given", "text": "the user is on the form page"},
                {"keyword": "When", "text": "the user fills all text fields with maximum allowed characters"},
                {"keyword": "And", "text": "the user clicks on Submit button"},
                {"keyword": "Then", "text": "the form should handle the data appropriately"},
            ]
            scenarios.append(scenario)

        return scenarios

    def _expand_generic(self, base_scenario: Dict[str, Any],
                        parsed: Dict[str, Any], test_type: str) -> List[Dict[str, Any]]:
        """Generic expansion for unspecified functionality"""
        scenarios = []

        if test_type == "negative":
            # Generic failure scenario
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = f"{base_scenario['name']} - Negative case"
            scenario["tags"] = ["@negative"]

            # Modify last step to expect failure
            if scenario["steps"]:
                last_step = scenario["steps"][-1]
                if last_step["keyword"] in ["Then", "And"]:
                    scenario["steps"][-1] = {
                        "keyword": last_step["keyword"],
                        "text": "the action should fail with appropriate error message"
                    }

            scenarios.append(scenario)

        elif test_type == "edge":
            # Generic edge case
            scenario = copy.deepcopy(base_scenario)
            scenario["name"] = f"{base_scenario['name']} - Edge case"
            scenario["tags"] = ["@edge"]
            scenarios.append(scenario)

        return scenarios