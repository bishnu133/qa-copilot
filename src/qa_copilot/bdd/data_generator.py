from typing import Dict, Any, List
from faker import Faker
import random
import string


class BDDDataGenerator:
    """
    Generates test data for BDD scenarios.
    Works with TestDataGenerator module for comprehensive data generation.
    """

    def __init__(self):
        self.faker = Faker()
        self.data_patterns = {
            "email": self._generate_emails,
            "username": self._generate_usernames,
            "password": self._generate_passwords,
            "phone": self._generate_phones,
            "name": self._generate_names,
            "address": self._generate_addresses,
            "credit_card": self._generate_credit_cards,
            "date": self._generate_dates,
            "number": self._generate_numbers,
        }

    def generate_examples(self, fields: List[str], count: int = 5) -> List[Dict[str, Any]]:
        """
        Generate example data for scenario outlines.

        Args:
            fields: List of field names
            count: Number of examples to generate

        Returns:
            List of example dictionaries
        """
        examples = []

        for i in range(count):
            example = {}
            for field in fields:
                field_type = self._detect_field_type(field)
                generator = self.data_patterns.get(field_type, self._generate_generic)

                # Generate different types of data
                if i == 0:  # Valid data
                    example[field] = generator("valid")
                elif i == 1:  # Invalid data
                    example[field] = generator("invalid")
                elif i == 2:  # Empty data
                    example[field] = ""
                elif i == 3:  # Edge case
                    example[field] = generator("edge")
                else:  # Random
                    example[field] = generator("random")

            examples.append(example)

        return examples

    def _detect_field_type(self, field_name: str) -> str:
        """Detect field type from name"""
        field_lower = field_name.lower()

        if any(word in field_lower for word in ["email", "mail"]):
            return "email"
        elif any(word in field_lower for word in ["user", "username"]):
            return "username"
        elif any(word in field_lower for word in ["pass", "password"]):
            return "password"
        elif any(word in field_lower for word in ["phone", "mobile", "tel"]):
            return "phone"
        elif any(word in field_lower for word in ["name", "first", "last"]):
            return "name"
        elif any(word in field_lower for word in ["address", "street", "city"]):
            return "address"
        elif any(word in field_lower for word in ["card", "credit"]):
            return "credit_card"
        elif any(word in field_lower for word in ["date", "dob", "birth"]):
            return "date"
        elif any(word in field_lower for word in ["number", "amount", "qty"]):
            return "number"

        return "generic"

    def _generate_emails(self, data_type: str) -> str:
        """Generate email addresses"""
        if data_type == "valid":
            return self.faker.email()
        elif data_type == "invalid":
            return random.choice([
                "invalid-email",
                "@example.com",
                "user@",
                "user@.com",
                "user..name@example.com"
            ])
        elif data_type == "edge":
            return random.choice([
                "a@b.c",  # Minimal valid
                f"{'a' * 64}@example.com",  # Long local part
                "user+tag@example.com",  # With plus
                "user.name+tag@example.co.uk"  # Complex
            ])
        else:
            return self.faker.email()

    def _generate_usernames(self, data_type: str) -> str:
        """Generate usernames"""
        if data_type == "valid":
            return self.faker.user_name()
        elif data_type == "invalid":
            return random.choice([
                "a",  # Too short
                "user name",  # Space
                "user@name",  # Special char
                ""  # Empty
            ])
        elif data_type == "edge":
            return random.choice([
                "ab",  # Minimum length
                "user_123",  # With numbers
                "user-name",  # With dash
                "a" * 50  # Long username
            ])
        else:
            return self.faker.user_name()

    def _generate_passwords(self, data_type: str) -> str:
        """Generate passwords"""
        if data_type == "valid":
            return f"{self.faker.password(12)}A1!"
        elif data_type == "invalid":
            return random.choice([
                "123",  # Too short
                "password",  # No numbers/special
                "12345678",  # No letters
                "Password",  # No numbers
            ])
        elif data_type == "edge":
            return random.choice([
                "Pass1!",  # Minimum valid
                "P@ssw0rd123!ABC" * 5,  # Very long
                "!@#$%^&*()123Abc",  # Many special chars
            ])
        else:
            return self.faker.password()

    def _generate_phones(self, data_type: str) -> str:
        """Generate phone numbers"""
        if data_type == "valid":
            return self.faker.phone_number()
        elif data_type == "invalid":
            return random.choice([
                "123",  # Too short
                "phone-number",  # Text
                "123-456-789a",  # Letters
            ])
        elif data_type == "edge":
            return random.choice([
                "+1234567890",  # International
                "123-456-7890 ext 123",  # With extension
                "(123) 456-7890",  # Formatted
            ])
        else:
            return self.faker.phone_number()

    def _generate_names(self, data_type: str) -> str:
        """Generate names"""
        if data_type == "valid":
            return self.faker.name()
        elif data_type == "invalid":
            return random.choice([
                "123",  # Numbers
                "",  # Empty
                "Name@123",  # Special chars
            ])
        elif data_type == "edge":
            return random.choice([
                "O'Brien",  # Apostrophe
                "María José",  # Accents
                "A",  # Single letter
                "Van Der Berg"  # Multiple parts
            ])
        else:
            return self.faker.name()

    def _generate_addresses(self, data_type: str) -> str:
        """Generate addresses"""
        if data_type == "valid":
            return self.faker.address().replace('\n', ', ')
        elif data_type == "invalid":
            return ""
        elif data_type == "edge":
            return "123 Main St, Apt #456, Building 7-B, New York, NY 10001"
        else:
            return self.faker.address().replace('\n', ', ')

    def _generate_credit_cards(self, data_type: str) -> str:
        """Generate credit card numbers"""
        if data_type == "valid":
            return "4111111111111111"  # Test Visa
        elif data_type == "invalid":
            return "1234567890"
        elif data_type == "edge":
            return "5555555555554444"  # Test Mastercard
        else:
            return "4111111111111111"

    def _generate_dates(self, data_type: str) -> str:
        """Generate dates"""
        if data_type == "valid":
            return self.faker.date_of_birth(minimum_age=18, maximum_age=80).strftime("%Y-%m-%d")
        elif data_type == "invalid":
            return random.choice([
                "invalid-date",
                "2024-13-01",  # Invalid month
                "2024-02-30",  # Invalid day
            ])
        elif data_type == "edge":
            return random.choice([
                "1900-01-01",  # Very old
                "2999-12-31",  # Future
                "2024-02-29",  # Leap year
            ])
        else:
            return self.faker.date().strftime("%Y-%m-%d")

    def _generate_numbers(self, data_type: str) -> str:
        """Generate numbers"""
        if data_type == "valid":
            return str(random.randint(1, 1000))
        elif data_type == "invalid":
            return random.choice(["abc", "", "-"])
        elif data_type == "edge":
            return random.choice(["0", "-1", "999999999", "1.5"])
        else:
            return str(random.randint(1, 10000))

    def _generate_generic(self, data_type: str) -> str:
        """Generate generic data"""
        if data_type == "valid":
            return self.faker.word()
        elif data_type == "invalid":
            return ""
        elif data_type == "edge":
            return "".join(random.choices(string.punctuation, k=10))
        else:
            return self.faker.sentence()