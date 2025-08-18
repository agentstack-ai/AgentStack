import os
import unittest
from unittest.mock import patch
from parameterized import parameterized
from pathlib import Path
import shutil
from cli_test_utils import run_cli
from agentstack import conf
from agentstack import frameworks
from agentstack.cli import init_project
from agentstack.templates import get_all_templates
from agentstack.exceptions import EnvironmentError

BASE_PATH = Path(__file__).parent


class CLIInitTest(unittest.TestCase):
    def setUp(self):
        self.framework = os.getenv('TEST_FRAMEWORK')
        self.project_dir = BASE_PATH / 'tmp' / self.framework / 'test_repo'
        os.chdir(str(BASE_PATH))  # Change directory before cleanup to avoid Windows file locks

        # Clean up any existing test directory
        if self.project_dir.exists():
            shutil.rmtree(self.project_dir, ignore_errors=True)
        os.makedirs(self.project_dir, exist_ok=True)
        os.chdir(self.project_dir)  # gitpython needs a cwd
        # Force UTF-8 encoding for the test environment
        os.environ['PYTHONIOENCODING'] = 'utf-8'

    def tearDown(self):
        shutil.rmtree(self.project_dir, ignore_errors=True)

    @parameterized.expand([(template.name,) for template in get_all_templates()])
    def test_init_command(self, template_name: str):
        """Test the 'init' command to create a project directory."""
        result = run_cli('init', 'test_project', '--template', template_name)
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.project_dir / 'test_project').exists())

    @parameterized.expand([(k, v) for k, v in frameworks.ALIASED_FRAMEWORKS.items()])
    def test_init_command_aliased_framework_empty_project(self, alias: str, framework: str):
        """Test the 'init' command with an aliased framework."""
        if framework != self.framework:
            self.skipTest(f"{alias} is not related to this framework")

        result = run_cli('init', 'test_project', '--template', 'empty', '--framework', alias)
        self.assertEqual(result.returncode, 0)

        # Then set the path and check the config
        project_dir = self.project_dir / 'test_project'
        self.assertTrue(project_dir.exists())
        conf.set_path(project_dir)
        config = conf.ConfigFile()
        self.assertEqual(config.framework, framework)

    def test_init_with_invalid_framework(self):
        """Test initialization with an unsupported framework."""
        with self.assertRaises(Exception) as context:
            init_project(slug_name='test_project', template='empty', framework='invalid_framework')
        self.assertIn("not supported", str(context.exception))

    @patch('agentstack.cli.init.packaging')
    def test_init_without_uv(self, mock_packaging):
        """Test initialization when uv is not installed."""
        mock_packaging.get_uv_bin.side_effect = ImportError()

        with self.assertRaises(EnvironmentError) as context:
            init_project(slug_name='test_project')
        self.assertIn("uv is not installed", str(context.exception))

    def test_init_existing_directory(self):
        """Test initialization when target directory already exists."""
        os.makedirs(self.project_dir / 'test_project', exist_ok=True)

        result = run_cli('init', 'test_project')
        self.assertNotEqual(result.returncode, 0)  # Should fail
        self.assertIn("already exists", result.stderr)

    @patch('agentstack.cli.init.repo')
    def test_init_in_existing_repo(self, mock_repo):
        """Test initialization inside an existing git repository."""
        mock_repo.find_parent_repo.return_value = True

        result = run_cli('init', 'test_project', '--template', 'empty')
        self.assertEqual(result.returncode, 0)

        project_dir = self.project_dir / 'test_project'
        conf.set_path(project_dir)
        config = conf.ConfigFile()
        self.assertFalse(config.use_git)

    def test_init_with_template_and_wizard(self):
        """Test that template and wizard flags cannot be used together."""
        with self.assertRaises(Exception) as context:
            init_project(slug_name='test_project', template='empty', use_wizard=True)
        self.assertIn("Template and wizard flags cannot be used together", str(context.exception))

    @patch('agentstack.cli.init.questionary')
    def test_prompt_slug_name_validation(self, mock_questionary):
        """Test project name validation in prompt."""
        # Test invalid cases
        invalid_names = ['Invalid-Name', 'invalid name', 'InvalidName']
        for name in invalid_names:
            mock_questionary.text.return_value.ask.return_value = name
            with self.assertRaises(Exception):
                init_project()

    @patch('agentstack.cli.init.packaging')
    @patch('agentstack.cli.init.conf.set_path')
    def test_dependency_installation(self, mock_set_path, mock_packaging):
        """Test that dependencies are properly installed."""
        # Clean up specific project directory
        project_dir = self.project_dir / 'test_project'
        shutil.rmtree(project_dir, ignore_errors=True)

        # Mock the conf.PATH to point to our test directory
        with patch('agentstack.packaging.conf.PATH', project_dir):
            init_project(slug_name='test_project', template='empty')

        # Verify the mocks were called correctly
        mock_set_path.assert_called_once()
        mock_packaging.create_venv.assert_called_once()
        mock_packaging.install_project.assert_called_once()

    def test_template_component_generation(self):
        """Test that template components (agents, tasks, tools) are generated."""
        result = run_cli('init', 'test_project', '--template', 'research')
        self.assertEqual(result.returncode, 0)

        project_dir = self.project_dir / 'test_project'
        self.assertTrue((project_dir / 'src/config/agents.yaml').exists())
        self.assertTrue((project_dir / 'src/config/tasks.yaml').exists())
        self.assertTrue((project_dir / 'src/tools').exists())
        self.assertTrue((project_dir / 'src/tools/__init__.py').exists())
