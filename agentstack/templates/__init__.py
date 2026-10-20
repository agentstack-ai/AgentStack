from typing import Optional, Literal, Union
import os, sys
from pathlib import Path
import pydantic
import requests
import json
from dotenv import dotenv_values
from agentstack.exceptions import ValidationError
from agentstack.utils import get_package_path

CURRENT_VERSION: Literal[4] = 4


def _get_builtin_templates_path() -> Path:
    return get_package_path() / 'templates'


def _model_dump_agent(agent: Union[dict, pydantic.BaseModel]) -> dict:
    """Between template version 3 and 4 we fixed the naming of the model/llm field."""
    if isinstance(agent, pydantic.BaseModel):
        agent = agent.model_dump()
    return {
        "name": agent['name'],
        "role": agent['role'],
        "goal": agent['goal'],
        "backstory": agent['backstory'],
        "llm": agent['model'],  # model -> llm
    }


class TemplateConfig_v1(pydantic.BaseModel):
    name: str
    description: str
    template_version: Literal[1]
    framework: str
    method: str
    agents: list[dict]
    tasks: list[dict]
    tools: list[dict]
    inputs: list[str]

    def to_v4(self) -> 'TemplateConfig':
        return TemplateConfig(
            name=self.name,
            description=self.description,
            template_version=CURRENT_VERSION,
            framework=self.framework,
            method=self.method,
            manager_agent=None,
            agents=[TemplateConfig.Agent(**_model_dump_agent(agent)) for agent in self.agents],
            tasks=[TemplateConfig.Task(**task) for task in self.tasks],
            tools=[TemplateConfig.Tool(**tool) for tool in self.tools],
            graph=[],
            inputs={key: "" for key in self.inputs},
        )


class TemplateConfig_v2(pydantic.BaseModel):
    class Agent(pydantic.BaseModel):
        name: str
        role: str
        goal: str
        backstory: str
        model: str

    class Task(pydantic.BaseModel):
        name: str
        description: str
        expected_output: str
        agent: str

    class Tool(pydantic.BaseModel):
        name: str
        agents: list[str]

    name: str
    description: str
    template_version: Literal[2]
    framework: str
    method: str
    agents: list[Agent]
    tasks: list[Task]
    tools: list[Tool]
    inputs: dict[str, str]

    def to_v4(self) -> 'TemplateConfig':
        return TemplateConfig(
            name=self.name,
            description=self.description,
            template_version=CURRENT_VERSION,
            framework=self.framework,
            method=self.method,
            manager_agent=None,
            agents=[TemplateConfig.Agent(**_model_dump_agent(agent)) for agent in self.agents],
            tasks=[TemplateConfig.Task(**task.model_dump()) for task in self.tasks],
            tools=[TemplateConfig.Tool(**tool.model_dump()) for tool in self.tools],
            graph=[],
            inputs=self.inputs,
        )


class TemplateConfig_v3(pydantic.BaseModel):
    class Agent(pydantic.BaseModel):
        name: str
        role: str
        goal: str
        backstory: str
        allow_delegation: bool = False
        model: str

    class Task(pydantic.BaseModel):
        name: str
        description: str
        expected_output: str
        agent: str

    class Tool(pydantic.BaseModel):
        name: str
        agents: list[str]

    name: str
    description: str
    template_version: Literal[3]
    framework: str
    method: str
    manager_agent: Optional[str]
    agents: list[Agent]
    tasks: list[Task]
    tools: list[Tool]
    inputs: dict[str, str]

    def to_v4(self) -> 'TemplateConfig':
        return TemplateConfig(
            name=self.name,
            description=self.description,
            template_version=CURRENT_VERSION,
            framework=self.framework,
            method=self.method,
            manager_agent=self.manager_agent,
            agents=[TemplateConfig.Agent(**_model_dump_agent(agent)) for agent in self.agents],
            tasks=[TemplateConfig.Task(**task.model_dump()) for task in self.tasks],
            tools=[TemplateConfig.Tool(**tool.model_dump()) for tool in self.tools],
            graph=[],
            inputs=self.inputs,
        )


class TemplateConfig(pydantic.BaseModel):
    """
    Interface for interacting with template configuration files.

    Templates are read-only.

    Template Schema
    -------------
    name: str
        The name of the project.
    description: str
        A description of the template.
    template_version: int
        The version of the template.
    framework: str
        The framework the template is for.
    method: str
        The method used by the project. ie. "sequential"
    manager_agent: Optional[str]
        The name of the agent that manages the project.
    agents: list[TemplateConfig.Agent]
        A list of agents used by the project.
    tasks: list[TemplateConfig.Task]
        A list of tasks used by the project.
    tools: list[TemplateConfig.Tool]
        A list of tools used by the project.
    graph: list[list[TemplateConfig.Node]]
        A list of graph relationships. Each edge must have exactly 2 nodes.
    inputs: dict[str, str]
        Key/value pairs of inputs used by the project.
    """

    class Agent(pydantic.BaseModel):
        name: str
        role: str
        goal: str
        backstory: str
        allow_delegation: bool = False
        llm: str

    class Task(pydantic.BaseModel):
        name: str
        description: str
        expected_output: str
        agent: str  # TODO this is redundant with the graph

    class Tool(pydantic.BaseModel):
        name: str
        agents: list[str]

    class Node(pydantic.BaseModel):
        type: Literal["agent", "task", "special"]
        name: str

    name: str
    description: str
    template_version: Literal[4] = CURRENT_VERSION
    framework: str
    method: str = "sequential"
    manager_agent: Optional[str] = None
    agents: list[Agent] = pydantic.Field(default_factory=list)
    tasks: list[Task] = pydantic.Field(default_factory=list)
    tools: list[Tool] = pydantic.Field(default_factory=list)
    graph: list[list[Node]] = pydantic.Field(default_factory=list)
    inputs: dict[str, str] = pydantic.Field(default_factory=dict)

    @pydantic.field_validator('graph')
    @classmethod
    def validate_graph_edges(cls, value: list[list[Node]]) -> list[list[Node]]:
        for i, edge in enumerate(value):
            if len(edge) != 2:
                raise ValueError(f"Graph edge {i} must have exactly 2 nodes.")
        return value

    def write_to_file(self, filename: Path):
        if not filename.suffix == '.json':
            filename = filename.with_suffix('.json')

        with open(filename, 'w') as f:
            model_dump = self.model_dump()
            f.write(json.dumps(model_dump, indent=4))

    @classmethod
    def from_user_input(cls, identifier: str):
        """
        Load a template from a user-provided identifier.
        Three cases will be tried: A URL, a file path, or a template name.
        """
        if identifier.startswith('https://'):
            return cls.from_url(identifier)

        if identifier.endswith('.json'):
            path = Path() / identifier
            return cls.from_file(path)

        return cls.from_template_name(identifier)

    @classmethod
    def from_template_name(cls, name: str) -> 'TemplateConfig':
        if not name in get_all_template_names():
            raise ValidationError(f"Template {name} not bundled with agentstack.")

        path = _get_builtin_templates_path() / f"{name}.json"
        template = cls.from_file(path)
        # Only choose a default for new projects using the bundled research
        # starter. Saved projects and explicit file/URL templates keep their tools.
        if name == 'research':
            home_key = dotenv_values(Path.home() / '.env').get('PERPLEXITY_API_KEY')
            key = os.getenv('PERPLEXITY_API_KEY', home_key)
            if not key or not key.strip():
                template.tools = [
                    cls.Tool(name='parallel', agents=tool.agents) if tool.name == 'perplexity' else tool
                    for tool in template.tools
                ]
        return template

    @classmethod
    def from_file(cls, path: Path) -> 'TemplateConfig':
        if not os.path.exists(path):
            raise ValidationError(f"Template {path} not found.")
        try:
            with open(path, 'r') as f:
                return cls.from_json(json.load(f))
        except json.JSONDecodeError as e:
            raise ValidationError(f"Error decoding template JSON.\n{e}")
        except ValidationError as e:
            raise ValidationError(f"{e}\nTemplateConfig.from_file({path})")

    @classmethod
    def from_url(cls, url: str) -> 'TemplateConfig':
        if not url.startswith("https://"):
            raise ValidationError(f"Invalid URL: {url}")
        response = requests.get(url)
        if response.status_code != 200:
            raise ValidationError(f"Failed to fetch template from {url}")
        try:
            return cls.from_json(response.json())
        except json.JSONDecodeError as e:
            raise ValidationError(f"Error decoding template JSON.\n{e}")
        except ValidationError as e:
            raise ValidationError(f"{e}\nTemplateConfig.from_url({url})")

    @classmethod
    def from_json(cls, data: dict) -> 'TemplateConfig':
        try:
            match data.get('template_version'):
                case 1:
                    return TemplateConfig_v1(**data).to_v4()
                case 2:
                    return TemplateConfig_v2(**data).to_v4()
                case 3:
                    return TemplateConfig_v3(**data).to_v4()
                case 4:
                    return cls(**data)  # current version
                case _:
                    raise ValidationError(f"Unsupported template version: {data.get('template_version')}")
        except pydantic.ValidationError as e:
            err_msg = "Error validating template config JSON:\n"
            for error in e.errors():
                err_msg += f"{' '.join([str(loc) for loc in error['loc']])}: {error['msg']}\n"
            raise ValidationError(err_msg)


def get_all_template_paths() -> list[Path]:
    paths = []
    templates_dir = _get_builtin_templates_path()
    for file in templates_dir.iterdir():
        if file.suffix == '.json':
            paths.append(file)
    return paths


def get_all_template_names() -> list[str]:
    return [path.stem for path in get_all_template_paths()]


def get_all_templates() -> list[TemplateConfig]:
    return [TemplateConfig.from_file(path) for path in get_all_template_paths()]
