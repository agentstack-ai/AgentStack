from typing import Optional, Protocol, runtime_checkable
from types import ModuleType
import os
import sys
from pathlib import Path
from importlib import import_module
import pydantic
from agentstack.exceptions import ValidationError
from agentstack.utils import get_package_path, open_json_file, term_color, snake_to_camel
from agentstack import conf, log


TOOLS_DIR: Path = get_package_path() / '_tools'  # NOTE: if you change this dir, also update MANIFEST.in
TOOLS_CONFIG_FILENAME: str = 'config.json'


def _get_custom_tool_path(name: str) -> Path:
    """Get the path to a custom tool."""
    return conf.PATH / 'src/tools' / name / TOOLS_CONFIG_FILENAME


def _get_builtin_tool_path(name: str) -> Path:
    """Get the path to a builtin tool."""
    return TOOLS_DIR / name / TOOLS_CONFIG_FILENAME


class Callback(pydantic.BaseModel):
    """A callback to be called after a tool is run."""

    script: Optional[str] = None  # call a script (this is the current implementation)
    method: Optional[str] = None  # call a python method
    url: Optional[str] = None  # call a URL
    
    @pydantic.validator('script', 'method', 'url', mode='after')
    def check_callback(cls, v, values, field):
        if not any([values.get('script'), values.get('method'), values.get('url')]):
            raise ValueError('At least one of script, method, or url must be set')
        return v
    
    @property
    def SCRIPT(self) -> bool:
        return self.script is not None

    @property
    def METHOD(self) -> bool:
        return self.method is not None

    @property
    def URL(self) -> bool:
        return self.url is not None


class ToolConfig(pydantic.BaseModel):
    """
    This represents the configuration data for a tool.
    It parses and validates the `config.json` file and provides a dynamic
    interface for interacting with the tool implementation.
    """

    name: str
    category: str
    tools: list[str]
    url: Optional[str] = None
    cta: Optional[str] = None
    env: Optional[dict] = None
    dependencies: Optional[list[str]] = None
    post_install: Optional[Callback] = None
    post_remove: Optional[Callback] = None

    @classmethod
    def from_tool_name(cls, name: str) -> 'ToolConfig':
        # First check in the user's project directory for custom tools
        custom_path = _get_custom_tool_path(name)
        if custom_path.exists():
            return cls.from_json(custom_path)

        # Then check in the package's tools directory
        path = _get_builtin_tool_path(name)
        if not path.exists():
            raise ValidationError(f'No known agentstack tool: {name}')
        return cls.from_json(path)

    @classmethod
    def from_json(cls, path: Path) -> 'ToolConfig':
        data = open_json_file(path)
        try:
            return cls(**data)
        except pydantic.ValidationError as e:
            error_str = "Error validating tool config:\n"
            for error in e.errors():
                error_str += f"{' '.join([str(loc) for loc in error['loc']])}: {error['msg']}\n"
            raise ValidationError(f"Error loading tool from {path}.\n{error_str}")

    def write_to_file(self, filename: Path):
        """Write the tool config to a json file."""
        if not filename.suffix == '.json':
            raise ValidationError(f"Filename must end with .json: {filename}")

        with open(filename, 'w') as f:
            f.write(self.model_dump_json())

    @property
    def type(self) -> type:
        """
        Dynamically generate a type for the tool module.
        ie. indicate what methods it's importable module should have.
        """

        def method_stub(name: str):
            def not_implemented(*args, **kwargs):
                raise NotImplementedError(
                    f"Method '{name}' is configured in config.json for tool '{self.name}'"
                    f"but has not been implemented in the tool module ({self.module_name})."
                )

            return not_implemented

        # fmt: off
        type_ = type(f'{snake_to_camel(self.name)}Module', (Protocol,), {  # type: ignore[arg-type]
            method_name: method_stub(method_name) for method_name in self.tools
        },)
        # fmt: on
        return runtime_checkable(type_)

    @property
    def module_name(self) -> str:
        """Module name for the tool module."""
        # Check if this is a custom tool in the user's project
        custom_path = _get_custom_tool_path(self.name)
        if custom_path.exists():
            return f"src.tools.{self.name}"

        # Otherwise, it's a package tool
        return f"agentstack._tools.{self.name}"

    @property
    def module(self) -> ModuleType:
        """
        Import the tool module and validate that it implements the required methods.
        Returns the imported module ready for direct use.
        """
        try:
            _module = import_module(self.module_name)
            assert isinstance(_module, self.type)
            return _module
        except AssertionError as e:
            raise ValidationError(
                f"Tool module `{self.module_name}` does not match the expected implementation. \n"
                f"The tool's config.json file lists the following public methods: `{'`, `'.join(self.tools)}` "
                f"but only implements: '{'`, `'.join([m for m in dir(_module) if not m.startswith('_')])}`"
            )
        except ModuleNotFoundError as e:
            raise ValidationError(
                f"Could not import tool module: {self.module_name}\n"
                f"Are you sure you have installed the tool? (agentstack tools add {self.name})\n"
                f"ModuleNotFoundError: {e}"
            )


def get_all_tool_paths() -> list[Path]:
    """
    Get all the paths to the tool configuration files.
    ie. agentstack/_tools/<tool_name>/
    Tools are identified by having a `config.json` file inside the _tools/<tool_name> directory.
    Also checks the user's project directory for custom tools.
    """
    paths = []

    # Get package tools
    for tool_dir in TOOLS_DIR.iterdir():
        if tool_dir.is_dir():
            config_path = tool_dir / TOOLS_CONFIG_FILENAME
            if config_path.exists():
                paths.append(tool_dir)

    # Get custom tools from user's project if in a project directory
    if conf.PATH:
        custom_tools_dir = conf.PATH / 'src/tools'
        if custom_tools_dir.exists():
            for tool_dir in custom_tools_dir.iterdir():
                if tool_dir.is_dir():
                    config_path = tool_dir / TOOLS_CONFIG_FILENAME
                    if config_path.exists():
                        paths.append(tool_dir)

    return paths


def get_all_tool_names() -> list[str]:
    """Get names of all available tools, including custom tools."""
    return [path.name for path in get_all_tool_paths()]


def get_all_tools() -> list[ToolConfig]:
    """Get all tool configs, including custom tools."""
    tool_names = get_all_tool_names()
    return [ToolConfig.from_tool_name(name) for name in tool_names]
