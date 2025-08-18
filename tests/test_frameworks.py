import os
from pathlib import Path
import shutil
import unittest
from parameterized import parameterized

from agentstack.conf import ConfigFile, set_path
from agentstack.exceptions import ValidationError
from agentstack import frameworks
from agentstack._tools import ToolConfig, get_all_tools
from agentstack.agents import AGENTS_FILENAME, AgentConfig
from agentstack.tasks import TASKS_FILENAME, TaskConfig
from agentstack import graph

BASE_PATH = Path(__file__).parent


class TestFrameworks(unittest.TestCase):
    def setUp(self):
        self.framework = os.getenv('TEST_FRAMEWORK')
        self.project_dir = BASE_PATH / 'tmp' / self.framework / 'test_frameworks'

        # Clean up and recreate test directory
        os.makedirs(self.project_dir, exist_ok=True)
        os.chdir(self.project_dir)  # importing the crewai module requires us to be in a working directory
        os.makedirs(self.project_dir / 'src', exist_ok=True)
        os.makedirs(self.project_dir / 'src' / 'config', exist_ok=True)

        (self.project_dir / 'src' / '__init__.py').touch()

        shutil.copy(BASE_PATH / 'fixtures' / 'agentstack.json', self.project_dir / 'agentstack.json')
        set_path(self.project_dir)
        with ConfigFile() as config:
            config.framework = self.framework

    def tearDown(self):
        # Change directory before cleanup to avoid Windows file locks
        os.chdir(str(BASE_PATH))
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def _populate_min_entrypoint(self):
        """This entrypoint does not have any tools or agents."""
        entrypoint_path = frameworks.get_entrypoint_path(self.framework)
        shutil.copy(BASE_PATH / f"fixtures/frameworks/{self.framework}/entrypoint_min.py", entrypoint_path)

    def _populate_max_entrypoint(self):
        """This entrypoint has tools and agents."""
        entrypoint_path = frameworks.get_entrypoint_path(self.framework)
        shutil.copy(BASE_PATH / f"fixtures/frameworks/{self.framework}/entrypoint_max.py", entrypoint_path)
        shutil.copy(BASE_PATH / 'fixtures/agents_max.yaml', self.project_dir / AGENTS_FILENAME)
        shutil.copy(BASE_PATH / 'fixtures/tasks_max.yaml', self.project_dir / TASKS_FILENAME)

    def _get_test_agent(self) -> AgentConfig:
        return AgentConfig('agent_name')

    def _get_test_agent_alternate(self) -> AgentConfig:
        return AgentConfig('second_agent_name')

    def _get_test_task(self) -> TaskConfig:
        return TaskConfig('task_name')

    def _get_test_task_alternate(self) -> TaskConfig:
        return TaskConfig('task_name_two')

    def _get_test_tool(self) -> ToolConfig:
        return ToolConfig(name='test_tool', category='test', tools=['test_tool'])

    def _get_test_tool_alternate(self) -> ToolConfig:
        return ToolConfig(name='test_tool_alt', category='test', tools=['test_tool_alt'])

    def test_get_framework_module(self):
        module = frameworks.get_framework_module(self.framework)
        assert module.__name__ == f"agentstack.frameworks.{self.framework}"

    def test_framework_module_implements_protocol(self):
        """Assert that the framework implementation has methods for all the protocol methods."""
        protocol = frameworks.FrameworkModule
        module = frameworks.get_framework_module(self.framework)
        for method_name in dir(protocol):
            if method_name.startswith('_'):
                continue
            assert hasattr(module, method_name), f"Method {method_name} not implemented in {self.framework}"

    def test_get_framework_module_invalid(self):
        with self.assertRaises(Exception):
            frameworks.get_framework_module('invalid')

    def test_validate_project(self):
        self._populate_max_entrypoint()
        frameworks.validate_project()

    def test_validate_project_invalid(self):
        self._populate_min_entrypoint()
        with self.assertRaises(ValidationError):
            frameworks.validate_project()

    def test_validate_project_has_agent_no_task_invalid(self):
        self._populate_min_entrypoint()
        shutil.copy(BASE_PATH / 'fixtures/agents_max.yaml', self.project_dir / AGENTS_FILENAME)

        frameworks.add_agent(self._get_test_agent())
        with self.assertRaises(ValidationError):
            frameworks.validate_project()

    def test_validate_project_has_task_no_agent_invalid(self):
        self._populate_min_entrypoint()
        frameworks.add_task(self._get_test_task())
        with self.assertRaises(ValidationError):
            frameworks.validate_project()

    def test_validate_project_missing_agent_method_invalid(self):
        """Ensure that all agents have a method defined in the entrypoint."""
        self._populate_max_entrypoint()
        # add an extra entry to agents.yaml
        with open(self.project_dir / AGENTS_FILENAME, 'a') as f:
            f.write("""\nextra_agent:
  role: >-
    role
  goal: >-
    this is a goal
  backstory: >-
    this is a backstory
  llm: openai/gpt-4o""")
        with self.assertRaises(ValidationError):
            frameworks.validate_project()

    def test_validate_project_missing_task_method_invalid(self):
        """Ensure that all tasks have a method defined in the entrypoint."""
        self._populate_max_entrypoint()
        # add an extra entry to tasks.yaml
        with open(self.project_dir / TASKS_FILENAME, 'a') as f:
            f.write("""\nextra_task:
  description: >-
    Add your description here
  expected_output: >-
    Add your expected output here
  agent: >-
    default_agent""")

        with self.assertRaises(ValidationError):
            frameworks.validate_project()

    def test_get_agent_tool_names(self):
        self._populate_max_entrypoint()
        frameworks.add_tool(self._get_test_tool(), 'agent_name')
        tool_names = frameworks.get_agent_tool_names('agent_name')
        assert tool_names == ['test_tool']

    def test_add_tool(self):
        self._populate_max_entrypoint()
        frameworks.add_tool(self._get_test_tool(), 'agent_name')

        entrypoint_src = open(frameworks.get_entrypoint_path(self.framework)).read()
        assert "*agentstack.tools['test_tool']" in entrypoint_src

    def test_add_tool_duplicate(self):
        """Repeated calls to add_tool should not duplicate the tool."""
        self._populate_max_entrypoint()
        frameworks.add_tool(self._get_test_tool(), 'agent_name')
        frameworks.add_tool(self._get_test_tool(), 'agent_name')

        assert len(frameworks.get_agent_tool_names('agent_name')) == 1

    def test_add_tool_invalid(self):
        self._populate_min_entrypoint()
        with self.assertRaises(ValidationError):
            frameworks.add_tool(self._get_test_tool(), 'agent_name')

    def test_remove_tool(self):
        self._populate_max_entrypoint()
        frameworks.add_tool(self._get_test_tool(), 'agent_name')
        frameworks.remove_tool(self._get_test_tool(), 'agent_name')

        entrypoint_src = open(frameworks.get_entrypoint_path(self.framework)).read()
        assert "*agentstack.tools['test_tool']" not in entrypoint_src

    def test_add_multiple_tools(self):
        self._populate_max_entrypoint()
        frameworks.add_tool(self._get_test_tool(), 'agent_name')
        frameworks.add_tool(self._get_test_tool_alternate(), 'agent_name')

        entrypoint_src = open(frameworks.get_entrypoint_path(self.framework)).read()
        assert (  # ordering is not guaranteed
            "*agentstack.tools['test_tool'], *agentstack.tools['test_tool_alt']" in entrypoint_src
            or "*agentstack.tools['test_tool_alt'], *agentstack.tools['test_tool']" in entrypoint_src
        )

    def test_remove_one_tool_of_multiple(self):
        self._populate_max_entrypoint()
        frameworks.add_tool(self._get_test_tool(), 'agent_name')
        frameworks.add_tool(self._get_test_tool_alternate(), 'agent_name')
        frameworks.remove_tool(self._get_test_tool(), 'agent_name')

        entrypoint_src = open(frameworks.get_entrypoint_path(self.framework)).read()
        assert "*agentstack.tools['test_tool']" not in entrypoint_src
        assert "*agentstack.tools['test_tool_alt']" in entrypoint_src

    @parameterized.expand([(x,) for x in get_all_tools()])
    def test_get_tool_callables(self, tool_config):
        self._populate_max_entrypoint()
        try:
            callables = frameworks.get_tool_callables(tool_config.name)
        except (Exception, ValidationError):
            raise unittest.SkipTest(
                f"Skipping validation of {tool_config.name} likely because dependencies required for import are not available."
            )

        assert len(callables) == len(tool_config.tools)

    def test_get_graph(self):
        self._populate_max_entrypoint()
        shutil.copy(BASE_PATH / 'fixtures/agents_max.yaml', self.project_dir / AGENTS_FILENAME)
        shutil.copy(BASE_PATH / 'fixtures/tasks_max.yaml', self.project_dir / TASKS_FILENAME)

        self._get_test_agent()
        self._get_test_task()

        graph_ = frameworks.get_graph()
        # graph can be empty if the project is not using the graph, but should still return a list
        assert isinstance(graph_, list)
        for edge in graph_:
            assert isinstance(edge, graph.Edge)
