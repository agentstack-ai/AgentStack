from typing import Optional
import json
import os, sys
from pathlib import Path
from importlib import import_module
import requests
from agentstack import conf, log
from agentstack.conf import ConfigFile
from agentstack.exceptions import ValidationError
from agentstack import frameworks
from agentstack import packaging
from agentstack.utils import term_color
from agentstack._tools import Callback, ToolConfig
from agentstack.generation import asttools
from agentstack.generation.files import EnvFile


def _handle_callback(callback: Callback) -> None:
    if callback.SCRIPT:
        log.debug(f'Calling script {callback.script}')
        os.system(callback.script)

    elif callback.METHOD:
        log.debug(f'Calling method {callback.method}')
        module_name, method_name = callback.method.rsplit('.', 1)
        module = import_module(module_name)
        method = getattr(module, method_name)
        method()

    elif callback.URL:
        log.debug(f'Calling URL {callback.url}')
        response = requests.get(callback.url)  # TODO methods
        if response.status_code == 200:
            log.info(response.text)
        else:
            log.error(f'Response Code: {response.status_code}')
    
    else:
        raise ValidationError('Invalid callback type')


def add_tool(name: str, agents: Optional[list[str]] = []):
    agentstack_config = ConfigFile()
    tool = ToolConfig.from_tool_name(name)

    if name in agentstack_config.tools:
        log.notify(f'Tool {name} is already installed')
    else:  # handle install
        if tool.dependencies:
            for dependency in tool.dependencies:
                packaging.install(dependency)

        if tool.env:  # add environment variables which don't exist
            with EnvFile() as env:
                for var, value in tool.env.items():
                    env.append_if_new(var, value)
            with EnvFile(".env.example") as env:
                for var, value in tool.env.items():
                    env.append_if_new(var, value)

        if tool.post_install:
            _handle_callback(tool.post_install)

        with agentstack_config as config:
            config.tools.append(tool.name)

    # Edit the framework entrypoint file to include the tool in the agent definition
    if not agents:  # If no agents are specified, add the tool to all agents
        agents = frameworks.get_agent_method_names()
    for agent_name in agents:
        frameworks.add_tool(tool, agent_name)

    log.success(f'🔨 Tool {tool.name} added to agentstack project successfully!')
    if tool.cta:
        log.notify(f'🪩  {tool.cta}')


def create_tool(tool_name: str, agents: Optional[list[str]] = []):
    """Create a new custom tool.

    Args:
        tool_name: Name of the tool to create (must be snake_case)
        agents: List of agents to make tool available to
    """

    # Check if tool already exists
    user_tools_dir = conf.PATH / "src/tools"
    tool_path = user_tools_dir / tool_name
    if tool_path.exists():
        raise Exception(f"Tool '{tool_name}' already exists.")

    # Create tool directory
    tool_path.mkdir(parents=True, exist_ok=False)

    # Create __init__.py with basic function template
    init_file = tool_path / '__init__.py'
    init_content = f'''
    
def {tool_name}_tool(value: str) -> str:
    """
    Define your tool's functionality here.

    Args:
        value: Input to process (should be typed in function definition)

    Returns:
        str: Result of the tool's operation
    """ 
    # Add your tool's logic here
    return value
'''
    init_file.write_text(init_content)

    tool_config = ToolConfig(
        name=tool_name,
        category="custom",
        tools=[f'{tool_name}_tool', ],
    )
    tool_config.write_to_file(tool_path / 'config.json')

    # Edit the framework entrypoint file to include the tool in the agent definition
    if not agents:  # If no agents are specified, add the tool to all agents
        agents = frameworks.get_agent_method_names()
    for agent_name in agents:
        frameworks.add_tool(tool_config, agent_name)

    log.success(f"🔨 Tool '{tool_name}' has been created successfully in {user_tools_dir}.")


def remove_tool(name: str, agents: Optional[list[str]] = []):
    agentstack_config = ConfigFile()

    if name not in agentstack_config.tools:
        raise ValidationError(f'Tool {name} is not installed')

    # TODO ensure other agents are not using the tool
    tool = ToolConfig.from_tool_name(name)
    if tool.dependencies:
        for dependency in tool.dependencies:
            packaging.remove(dependency)

    # Edit the framework entrypoint file to exclude the tool in the agent definition
    if not agents:  # If no agents are specified, remove the tool from all agents
        agents = frameworks.get_agent_method_names()
    for agent_name in agents:
        frameworks.remove_tool(tool, agent_name)

    if tool.post_remove:
        _handle_callback(tool.post_remove)
    # We don't remove the .env variables to preserve user data.

    with agentstack_config as config:
        config.tools.remove(tool.name)

    log.success(f'🔨 Tool {tool.name} removed from agentstack project successfully')
