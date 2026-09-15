import os, sys
import unittest
from parameterized import parameterized
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
from cli_test_utils import run_cli
from agentstack import conf
from agentstack import frameworks
from agentstack.cli import init_project
from agentstack.templates import get_all_templates

BASE_PATH = Path(__file__).parent


class CLIInitTest(unittest.TestCase):
    def setUp(self):
        self.framework = os.getenv('TEST_FRAMEWORK')
        self.project_dir = Path(BASE_PATH / 'tmp' / self.framework / 'test_cli_init')
        os.chdir(BASE_PATH)  # Change to parent directory first
        os.makedirs(self.project_dir, exist_ok=True)
        os.chdir(self.project_dir)
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

    def test_init_command_normalizes_hyphenated_project_name(self):
        """The CLI path must match the normalized Cookiecutter project slug."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_path = conf.PATH
            conf.set_path(temp_dir)
            try:
                with patch('agentstack.cli.init.require_uv'), \
                    patch('agentstack.cli.init.welcome_message'), \
                    patch('agentstack.cli.init.insert_template') as insert_template, \
                    patch('agentstack.cli.init.packaging.create_venv'), \
                    patch('agentstack.cli.init.packaging.install_project'), \
                    patch('agentstack.cli.init.repo.init'), \
                    patch('agentstack.cli.init.repo.find_parent_repo', return_value=None), \
                    patch('agentstack.cli.init.repo.Transaction') as transaction:
                    transaction.return_value.__enter__.return_value = transaction.return_value
                    init_project(slug_name='test-project', template='empty', framework='crewai')

                self.assertEqual(conf.PATH, Path(temp_dir) / 'test_project')
                insert_template.assert_called_once()
                self.assertEqual(insert_template.call_args.kwargs['name'], 'test_project')
            finally:
                conf.set_path(original_path)

    @parameterized.expand([(k, v) for k, v in frameworks.ALIASED_FRAMEWORKS.items()])
    def test_init_command_aliased_framework_empty_project(self, alias: str, framework: str):
        """Test the 'init' command with an aliased framework."""
        if framework != self.framework:
            self.skipTest(f"{alias} is not related to this framework")

        conf.set_path(self.project_dir)  # set working dir, init adds `slug_name`
        init_project(slug_name='test_project', template='empty', framework=alias)
        config = conf.ConfigFile()
        assert config.framework == framework
