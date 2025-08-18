import os
import unittest
from parameterized import parameterized
from pathlib import Path
import shutil
from agentstack._tools import get_all_tool_names
from cli_test_utils import run_cli
from agentstack.cli import get_validated_input
from unittest.mock import patch, MagicMock


BASE_PATH = Path(__file__).parent
TEMPLATE_NAME = "empty"


class CLIToolsTest(unittest.TestCase):
    def setUp(self):
        self.framework = os.getenv('TEST_FRAMEWORK')
        self.project_path = BASE_PATH / 'tmp' / self.framework / 'test_repo'
        os.chdir(str(BASE_PATH))  # Change directory before cleanup to avoid Windows file locks

        # Clean up any existing test directory
        if self.project_path.exists():
            shutil.rmtree(self.project_path, ignore_errors=True)
        os.makedirs(self.project_path, exist_ok=True)
        os.chdir(self.project_path)  # gitpython needs a cwd

    def tearDown(self):
        shutil.rmtree(self.project_path, ignore_errors=True)

    @parameterized.expand([(x,) for x in get_all_tool_names()])
    @unittest.skip("Dependency resolution issue")
    def test_add_tool(self, tool_name):
        """Test the adding every tool to a project."""
        result = run_cli('init', f"{tool_name}_project", "--template", TEMPLATE_NAME)
        self.assertEqual(result.returncode, 0)
        os.chdir(self.project_path / f"{tool_name}_project")
        result = run_cli('generate', 'agent', 'test_agent', '--llm', 'opeenai/gpt-4o')
        self.assertEqual(result.returncode, 0)
        result = run_cli('generate', 'task', 'test_task')
        self.assertEqual(result.returncode, 0)

        result = run_cli('tools', 'add', tool_name)
        print(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.project_path.exists())

    def test_get_validated_input(self):
        """Test the get_validated_input function with various validation scenarios"""

        # Create a mock Question object with ask() method
        mock_question = MagicMock()

        # Test basic input
        mock_question.ask.return_value = 'test_input'
        with patch('questionary.text', return_value=mock_question):
            result = get_validated_input("Test message")
            self.assertEqual(result, 'test_input')

        # Test min length validation - valid input
        mock_question.ask.return_value = 'abc'
        with patch('questionary.text', return_value=mock_question):
            result = get_validated_input("Test message", min_length=3)
            self.assertEqual(result, 'abc')

        # Test snake_case validation - valid input
        mock_question.ask.return_value = 'test_case'
        with patch('questionary.text', return_value=mock_question):
            result = get_validated_input("Test message", snake_case=True)
            self.assertEqual(result, 'test_case')

        # Test custom validation function
        def custom_validator(text):
            if text == 'valid':
                return True, ''
            return False, 'Invalid input'

        mock_question.ask.return_value = 'valid'
        with patch('questionary.text', return_value=mock_question):
            result = get_validated_input("Test message", validate_func=custom_validator)
            self.assertEqual(result, 'valid')

    def test_create_tool_basic(self):
        """Test creating a new custom tool via CLI"""
        # Initialize a project first
        result = run_cli('init', "test_project", "--template", TEMPLATE_NAME)
        self.assertEqual(result.returncode, 0)
        os.chdir(self.project_path / "test_project")

        # Create an agent to test with
        result = run_cli('generate', 'agent', 'test_agent', '--llm', 'openai/gpt-4')
        self.assertEqual(result.returncode, 0)

        # Create a new tool
        result = run_cli('tools', 'new', 'test_tool')
        self.assertEqual(result.returncode, 0)

        # Verify tool directory and files were created
        tool_path = self.project_path / "test_project" / 'src/tools/test_tool'
        self.assertTrue(tool_path.exists())
        self.assertTrue((tool_path / '__init__.py').exists())
        self.assertTrue((tool_path / 'config.json').exists())

    def test_create_tool_with_agents(self):
        """Test creating a new custom tool with specific agents via CLI"""
        # Initialize project and create multiple agents
        result = run_cli('init', "test_project", "--template", TEMPLATE_NAME)
        self.assertEqual(result.returncode, 0)
        os.chdir(self.project_path / "test_project")

        run_cli('generate', 'agent', 'agent1', '--llm', 'openai/gpt-4')
        run_cli('generate', 'agent', 'agent2', '--llm', 'openai/gpt-4')

        # Create tool with specific agent
        result = run_cli('tools', 'new', 'test_tool', '--agents', 'agent1')
        self.assertEqual(result.returncode, 0)

        # Verify tool was created (fix path)
        tool_path = self.project_path / "test_project" / 'src/tools/test_tool'
        self.assertTrue(tool_path.exists())

    @patch('agentstack.cli.init.packaging')
    def test_create_tool_existing(self, mock_packaging):
        """Test creating a tool that already exists"""
        # Initialize project
        result = run_cli('init', "test_project", "--template", TEMPLATE_NAME)
        self.assertEqual(result.returncode, 0)
        os.chdir(self.project_path / "test_project")

        # Create agent
        run_cli('generate', 'agent', 'test_agent', '--llm', 'openai/gpt-4')

        # Create tool first time
        result = run_cli('tools', 'new', 'test_tool')
        self.assertEqual(result.returncode, 0)

        # Try to create same tool again
        result = run_cli('tools', 'new', 'test_tool')  # Should fail
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)

    @patch('agentstack.cli.init.packaging')
    def test_create_tool_invalid_name(self, mock_packaging):
        """Test creating a tool with invalid name formats"""
        # Clean up the specific project directory first
        project_path = self.project_path / "test_project"
        shutil.rmtree(project_path, ignore_errors=True)

        # Initialize project with mocked packaging
        result = run_cli('init', "test_project", "--template", TEMPLATE_NAME)
        self.assertEqual(result.returncode, 0)

        os.chdir(self.project_path / "test_project")

        # Create agent
        result = run_cli('generate', 'agent', 'test_agent', '--llm', 'openai/gpt-4')
        self.assertEqual(result.returncode, 0)

        # Test various invalid names
        # Quote the space-containing name (for win)
        invalid_names = ['TestTool', 'test-tool', '"test tool"']
        for name in invalid_names:
            result = run_cli('tools', 'new', name)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be snake_case", result.stderr)

            # Also verify the tool wasn't actually created
            tool_path = self.project_path / "test_project" / 'src/tools' / name.replace('"', '')
            self.assertFalse(tool_path.exists(), f"Tool directory was created for invalid name: {name}")

    def test_create_tool_no_project(self):
        """Test creating a tool outside a project directory"""
        # Try to create tool without initializing project
        result = run_cli('tools', 'new', 'test_tool')
        self.assertNotEqual(result.returncode, 0)
