from typing import Optional
from difflib import get_close_matches
import questionary
from agentstack import conf, log
from agentstack.utils import term_color, is_snake_case
from agentstack import generation
from agentstack import repo
from agentstack._tools import get_all_tools, get_all_tool_names
from agentstack.agents import get_all_agents
from pathlib import Path


def list_tools():
    """
    List all available tools by category.
    """
    tools = [t for t in get_all_tools() if t is not None]  # Filter out None values
    categories = {}
    custom_tools = []

    # Group tools by category
    for tool in tools:
        if tool.category == 'custom':
            custom_tools.append(tool)
        else:
            if tool.category not in categories:
                categories[tool.category] = []
            categories[tool.category].append(tool)

    print("\n\nAvailable AgentStack Tools:")
    # Display tools by category
    for category in sorted(categories.keys()):
        print(f"\n{category}:")
        for tool in categories[category]:
            print("  - ", end='')
            print(term_color(f"{tool.name}", 'blue'), end='')
            print(f": {tool.url if tool.url else 'AgentStack default tool'}")
    
    # Display custom tools if any exist
    if custom_tools:
        print("\nCustom Tools:")
        for tool in custom_tools:
            print("  - ", end='')
            print(term_color(f"{tool.name}", 'blue'), end='')
            print(": Custom tool")

    print("\n\n✨ Add a tool with: agentstack tools add <tool_name>")
    print("   Create a custom tool with: agentstack tools create <tool_name>")
    print("   https://docs.agentstack.sh/tools/core")


def add_tool(tool_name: Optional[str], agents=Optional[list[str]]):
    """
    Add a tool to the user's project.
    If no tool name is provided:
        - prompt the user to select a tool
        - prompt the user to select one or more agents
    If a tool name is provided:
        - add the tool to the user's project
        - add the tool to the specified agents or all agents if none are specified
    """
    conf.assert_project()

    all_tool_names = get_all_tool_names()
    if tool_name and not tool_name in all_tool_names:
        # tool was provided, but not found. make a suggestion.
        suggestions = get_close_matches(tool_name, all_tool_names, n=1)
        message = f"Tool '{tool_name}' not found."
        if suggestions:
            message += f"\nDid you mean '{suggestions[0]}'?"
        log.error(message)
        return

    if not tool_name:
        # Get all available tools including custom ones
        available_tools = [t for t in get_all_tools() if t is not None]

        tool_name = questionary.select(
            "Select a tool to add to your project",
            choices=[t.name for t in available_tools],
            use_indicator=True,
            use_shortcuts=False,
            use_jk_keys=False,
            use_emacs_keys=False,
            use_arrow_keys=True,
            use_search_filter=True,
        ).ask()

        # ask the user for the agents to add the tool to
        agents = questionary.checkbox(
            "Select which agents to make the tool available to",
            choices=[agent.name for agent in get_all_agents()],
        ).ask()

    assert tool_name  # appease type checker

    repo.commit_user_changes()
    with repo.Transaction() as commit:
        commit.add_message(f"Added tool {tool_name}")
        generation.add_tool(tool_name, agents=agents)


def remove_tool(tool_name: str):
    """
    Remove a tool from the user's project.
    """
    conf.assert_project()

    repo.commit_user_changes()
    with repo.Transaction() as commit:
        commit.add_message(f"Removed tool {tool_name}")
        generation.remove_tool(tool_name)


def create_tool(tool_name: str, agents=Optional[list[str]]):
    """Create a new custom tool.
    Args:
        tool_name: Name of the tool to create (must be snake_case)
        agents: list of agents to make the tool available to
    """
    if not is_snake_case(tool_name):
        raise Exception("Invalid tool name: must be snake_case")

    # Check if tool already exists
    user_tools_dir = Path('src/tools').resolve()
    tool_path = conf.PATH / user_tools_dir / tool_name
    if tool_path.exists():
        raise Exception(f"Tool '{tool_name}' already exists.")

    generation.create_tool(tool_name, agents=agents)
