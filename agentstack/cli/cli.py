from typing import Optional
from art import text2art
import questionary
from agentstack import conf, log
from agentstack.conf import ConfigFile
from agentstack.generation import InsertionPoint
from agentstack import repo
from agentstack.providers import get_available_models
from agentstack.utils import is_snake_case

PREFERRED_MODELS = [
    'groq/deepseek-r1-distill-llama-70b',
    'deepseek/deepseek-chat',
    'deepseek/deepseek-coder',
    'deepseek/deepseek-reasoner',
    'openai/gpt-4o',
    'anthropic/claude-3-5-sonnet',
    'openai/o1-preview',
    'openai/gpt-4-turbo',
    'anthropic/claude-3-opus',
]


def get_validated_input(
    message: str,
    default: Optional[str] = None,
    validate_func=None,
    min_length: int = 0,
    snake_case: bool = False,
) -> str:
    """Helper function to get validated input from user.

    Args:
        message: The prompt message to display
        validate_func: Optional custom validation function that returns (bool, str)
        min_length: Minimum length requirement (0 for no requirement)
        snake_case: Whether to enforce snake_case naming
        if no validators are provided the default validation applies
    """
    while True:

        def validate(text: str) -> str | bool:
            if min_length and len(text) < min_length:
                return f"Input must be at least {min_length} characters long"

            if snake_case and not is_snake_case(text):
                return "Input must be in snake_case format (lowercase with underscores)"

            if validate_func:
                is_valid, error_msg = validate_func(text)
                if not is_valid:
                    return error_msg

            return True

        value = questionary.text(
            message,
            default=default or "",
            validate=validate if validate_func or min_length or snake_case else None,
        ).ask()

        if value:
            return value


def welcome_message():
    title = text2art("AgentStack", font="smisome1")
    tagline = "The easiest way to build a robust agent application!"
    border = "-" * len(tagline)

    # Print the welcome message with ASCII art
    log.info(title)
    log.info(border)
    log.info(tagline)
    log.info(border)


def undo() -> None:
    """Undo the last committed changes."""
    conf.assert_project()

    changed_files = repo.get_uncommitted_files()
    if changed_files:
        log.warning("There are uncommitted changes that may be overwritten.")
        for changed in changed_files:
            log.info(f" - {changed}")
        should_continue = questionary.confirm(
            "Do you want to continue?",
            default=False,
        ).ask()
        if not should_continue:
            return

    repo.revert_last_commit(hard=True)


def configure_default_model():
    """Set the default model"""
    agentstack_config = ConfigFile()
    if agentstack_config.default_model:
        log.debug("Using default model from project config.")
        return  # Default model already set

    log.info("Project does not have a default model configured.")

    # First question - show preferred models + "Other" option
    other_msg = "Other (see all available models)"
    model_choice = questionary.select(
        "Which model would you like to use?",
        choices=PREFERRED_MODELS + [other_msg],
        use_indicator=True,
        use_shortcuts=False,
        use_jk_keys=False,
        use_emacs_keys=False,
        use_arrow_keys=True,
        use_search_filter=True,
    ).ask()

    # If they choose "Other", show searchable all available models
    if model_choice == other_msg:
        log.info('\nA complete list of models is available at: "https://docs.litellm.ai/docs/providers"')
        available_models = get_available_models()

        model_choice = questionary.select(
            "Select from all available models (some may not yet be supported by AgentStack):",
            choices=available_models,
            use_indicator=True,
            use_shortcuts=False,
            use_jk_keys=False,
            use_emacs_keys=False,
            use_arrow_keys=True,
            use_search_filter=True,
        ).ask()

    log.debug("Writing default model to project config.")
    with ConfigFile() as agentstack_config:
        agentstack_config.default_model = model_choice


def parse_insertion_point(position: Optional[str] = None) -> Optional[InsertionPoint]:
    """
    Parse an insertion point CLI argument into an InsertionPoint enum.
    """
    if position is None:
        return None  # defer assumptions

    valid_positions = {x.value for x in InsertionPoint}
    if position not in valid_positions:
        raise ValueError(f"Position must be one of {','.join(valid_positions)}.")

    return next(x for x in InsertionPoint if x.value == position)
