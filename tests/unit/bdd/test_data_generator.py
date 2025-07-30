import pytest
from qa_copilot.bdd.data_generator import BDDDataGenerator


class TestBDDDataGenerator:
    """Test BDD Data Generator"""

    @pytest.fixture
    def generator(self):
        return BDDDataGenerator()

    def test_detect_field_type(self, generator):
        """Test field type detection"""
        assert generator._detect_field_type("email") == "email"
        assert generator._detect_field_type("user_email") == "email"
        assert generator._detect_field_type("username") == "username"
        assert generator._detect_field_type("password") == "password"
        assert generator._detect_field_type("phone_number") == "phone"
        assert generator._detect_field_type("random_field") == "generic"

    def test_generate_examples(self, generator):
        """Test example generation"""
        fields = ["username", "password", "email"]
        examples = generator.generate_examples(fields, count=3)

        assert len(examples) == 3
        for example in examples:
            assert "username" in example
            assert "password" in example
            assert "email" in example

    def test_generate_email_variations(self, generator):
        """Test email generation"""
        valid_email = generator._generate_emails("valid")
        assert "@" in valid_email
        assert "." in valid_email

        invalid_email = generator._generate_emails("invalid")
        # Should be invalid format

        edge_email = generator._generate_emails("edge")
        # Should be edge case like minimal valid email