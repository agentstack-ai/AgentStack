from contextlib import contextmanager
from unittest.mock import MagicMock
from agentstack.cli.cli import get_validated_input
from unittest.mock import patch


@contextmanager
def mock_questionary_ask(return_value: str):
    """Mock questionary.text().ask() to return a specific value"""
    with patch('agentstack.cli.cli.questionary.text') as mock_text:
        mock_text.return_value = MagicMock(ask=lambda: return_value)
        yield mock_text


def test_get_validated_input_basic():
    with mock_questionary_ask("test_input"):
        result = get_validated_input("Enter something:")
        assert result == "test_input"


def test_get_validated_input_min_length():
    # First try with invalid input
    with mock_questionary_ask("a") as mock_text:
        get_validated_input("Enter something:", min_length=3)
        # Verify the validation function returned an error message
        validation_func = mock_text.call_args[1]['validate']
        assert validation_func("a") == "Input must be at least 3 characters long"

    # Then verify valid input works
    with mock_questionary_ask("abc") as mock_text:
        result = get_validated_input("Enter something:", min_length=3)
        validation_func = mock_text.call_args[1]['validate']
        assert validation_func("abc") is True
        assert result == "abc"


def test_get_validated_input_snake_case():
    with mock_questionary_ask("notSnakeCase") as mock_text:
        get_validated_input("Enter something:", snake_case=True)
        validation_func = mock_text.call_args[1]['validate']
        assert (
            validation_func("notSnakeCase")
            == "Input must be in snake_case format (lowercase with underscores)"
        )

    with mock_questionary_ask("is_snake_case") as mock_text:
        result = get_validated_input("Enter something:", snake_case=True)
        validation_func = mock_text.call_args[1]['validate']
        assert validation_func("is_snake_case") is True
        assert result == "is_snake_case"


def test_get_validated_input_custom_validation():
    def validate_no_numbers(text: str) -> tuple[bool, str]:
        if any(char.isdigit() for char in text):
            return False, "Input should not contain numbers"
        return True, ""

    # Test invalid input
    with mock_questionary_ask("test123") as mock_text:
        get_validated_input("Enter something:", validate_func=validate_no_numbers)
        validation_func = mock_text.call_args[1]['validate']
        assert validation_func("test123") == "Input should not contain numbers"

    # Test valid input
    with mock_questionary_ask("test_input") as mock_text:
        result = get_validated_input("Enter something:", validate_func=validate_no_numbers)
        validation_func = mock_text.call_args[1]['validate']
        assert validation_func("test_input") is True
        assert result == "test_input"


def test_get_validated_input_multiple_validations():
    def validate_has_number(text: str) -> tuple[bool, str]:
        if not any(char.isdigit() for char in text):
            return False, "Input must contain at least one number"
        return True, ""

    # Test min_length validation
    with mock_questionary_ask("test") as mock_text:
        get_validated_input(
            "Enter something:", min_length=5, snake_case=True, validate_func=validate_has_number
        )
        validation_func = mock_text.call_args[1]['validate']
        assert validation_func("test") == "Input must be at least 5 characters long"

    # Test snake_case validation
    with mock_questionary_ask("testInput") as mock_text:
        get_validated_input(
            "Enter something:", min_length=5, snake_case=True, validate_func=validate_has_number
        )
        validation_func = mock_text.call_args[1]['validate']
        assert (
            validation_func("testInput") == "Input must be in snake_case format (lowercase with underscores)"
        )

    # Test custom validation
    with mock_questionary_ask("test_input") as mock_text:
        get_validated_input(
            "Enter something:", min_length=5, snake_case=True, validate_func=validate_has_number
        )
        validation_func = mock_text.call_args[1]['validate']
        assert validation_func("test_input") == "Input must contain at least one number"

    # Test valid input - use snake_case with number
    with mock_questionary_ask("test_input_123") as mock_text:
        result = get_validated_input(
            "Enter something:", min_length=5, snake_case=True, validate_func=validate_has_number
        )
        validation_func = mock_text.call_args[1]['validate']
        assert validation_func("test_input_123") is True
        assert result == "test_input_123"
