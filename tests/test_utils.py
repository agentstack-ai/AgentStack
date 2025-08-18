import os
import unittest
from pathlib import Path
from unittest.mock import patch

from agentstack.utils import clean_input, is_snake_case, get_base_dir


class TestUtils(unittest.TestCase):
    def test_clean_input_no_change(self):
        cleaned = clean_input('test_project')
        self.assertEqual('test_project', cleaned)

    def test_clean_input_remove_space(self):
        cleaned = clean_input('test project')
        self.assertEqual('test_project', cleaned)

    def test_is_snake_case(self):
        assert is_snake_case("hello_world")
        assert not is_snake_case("HelloWorld")
        assert not is_snake_case("Hello-World")
        assert not is_snake_case("hello-world")
        assert not is_snake_case("hello world")

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
