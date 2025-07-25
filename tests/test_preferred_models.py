from importlib.util import find_spec
import pytest
import subprocess
import sys
from difflib import get_close_matches
from agentstack.cli.cli import PREFERRED_MODELS


@pytest.fixture(scope="session", autouse=True)
def install_litellm():
    """Install litellm if not already installed."""
    print("\nChecking for litellm installation...")
    spec = find_spec("litellm")
    if spec is None:
        print("litellm not found, installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "litellm"])
        print("litellm installation complete")


def clean_model_name(provider: str, model: str) -> str:
    """
    Clean up model name by removing duplicate provider strings.
    Seems like in litellm groq and deepseek have the provider twice in the model name.
    """
    if model.startswith(f"{provider}/"):
        return f"{provider}/{model[len(provider) + 1 :]}"
    return f"{provider}/{model}"


def find_similar_models(model: str, all_models: set, num_suggestions: int = 3) -> list[str]:
    """
    Find similar model names using string matching.
    If the test fails, now you can see the ideal model to replace a broken one with.
    """
    try:
        provider, model_name = model.split('/')
    except ValueError:
        return get_close_matches(model, all_models, n=num_suggestions, cutoff=0.3)

    provider_models = [m for m in all_models if m.startswith(f"{provider}/")]
    if provider_models:
        matches = get_close_matches(model, provider_models, n=num_suggestions, cutoff=0.3)
        if matches:
            return matches
    return get_close_matches(model, all_models, n=num_suggestions, cutoff=0.3)


def test_preferred_models_validity():
    """Test that all PREFERRED_MODELS are valid LiteLLM models."""
    from litellm import models_by_provider

    all_litellm_models = set()
    for provider, models in models_by_provider.items():
        for model in models:
            full_model_name = clean_model_name(provider, model)
            all_litellm_models.add(full_model_name)

    invalid_models_with_suggestions = {}
    for model in PREFERRED_MODELS:
        if model not in all_litellm_models:
            suggestions = find_similar_models(model, all_litellm_models)
            invalid_models_with_suggestions[model] = suggestions

    if invalid_models_with_suggestions:
        error_message = (
            "The following models are not in LiteLLM's supported models:\n"
            "\nFor a complete list of supported models, visit: https://docs.litellm.ai/docs/providers\n"
        )
        for model, suggestions in invalid_models_with_suggestions.items():
            error_message += f"\n- {model}"
            if suggestions:
                error_message += "\n  Similar available models:"
                for suggestion in suggestions:
                    error_message += f"\n    * {suggestion}"
            else:
                error_message += "\n  No similar models found."

        assert False, error_message
