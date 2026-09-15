import os
import unittest
from pathlib import Path
from unittest.mock import patch

from agentstack.utils import (
    clean_input,
    is_snake_case,
    validator_not_empty,
    get_base_dir
)
from inquirer import errors as inquirer_errors


class TestUtils(unittest.TestCase):
    def test_clean_input_no_change(self):
        cleaned = clean_input('test_project')
        self.assertEqual('test_project', cleaned)

    def test_clean_input_remove_space(self):
        cleaned = clean_input('test project')
        self.assertEqual('test_project', cleaned)

    def test_clean_input_normalize_hyphen(self):
        cleaned = clean_input('test-project')
        self.assertEqual('test_project', cleaned)

    def test_is_snake_case(self):
        assert is_snake_case("hello_world")
        assert not is_snake_case("HelloWorld")
        assert not is_snake_case("Hello-World")
        assert not is_snake_case("hello-world")
        assert not is_snake_case("hello world")

    def test_validator_not_empty(self):
        validator = validator_not_empty(min_length=1)
        
        # Valid input should return True
        self.assertTrue(validator(None, "test"))
        self.assertTrue(validator(None, "a"))
        
        # Empty input should raise ValidationError        
        with self.assertRaises(inquirer_errors.ValidationError):
            validator(None, "")
            
        # Test with larger min_length
        validator = validator_not_empty(min_length=3)
        self.assertTrue(validator(None, "test"))
        with self.assertRaises(inquirer_errors.ValidationError):
            validator(None, "ab")

    @patch('agentstack.utils.user_data_dir')
    def test_get_base_dir_not_writable(self, mock_user_data_dir):
        """
        Test that get_base_dir() falls back to a temporary directory when user_data_dir is not writable.
        """
        mock_user_data_dir.side_effect = PermissionError

        result = get_base_dir()

        self.assertIsInstance(result, Path)
        self.assertTrue(result.is_absolute())
        self.assertIn(str(result), ['/tmp', os.environ.get('TEMP', '/tmp')])

    @patch('agentstack.utils.user_data_dir')
    def test_get_base_dir_writable(self, mock_user_data_dir):
        """
        Test that get_base_dir() returns a writable Path when user_data_dir is accessible.
        """
        mock_path = '/mock/user/data/dir'
        mock_user_data_dir.return_value = mock_path

        result = get_base_dir()

        self.assertIsInstance(result, Path)
        self.assertTrue(result.is_absolute())
