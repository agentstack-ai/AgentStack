from agentstack.exceptions import ValidationError
import litellm
from typing import List
from functools import lru_cache


@lru_cache(maxsize=1)
def get_available_models() -> List[str]:
    """
    Get list of available models in provider/model format.
    Results are cached to avoid processing multiple times.
    """
    models = []

    try:
        for provider, provider_models in litellm.models_by_provider.items():
            for model in provider_models:
                models.append(f"{provider}/{model}")

    except Exception:
        # since the models exist in the package, this should only throw
        # in the case of a breaking change or bug in litellm.
        raise Exception("Failed to parse models from litellm.")

    return sorted(models)


def parse_provider_model(model_id: str) -> tuple[str, str]:
    """Parse the provider and model name from the model ID"""
    # most providers are in the format "<provider>/<model-name>"
    # openrouter models are in the format "openrouter/<provider>/<model-name>"
    parts = tuple(model_id.split('/'))
    if len(parts) == 2:
        return parts
    elif len(parts) == 3:
        return '/'.join(parts[:2]), parts[2]
    else:
        raise ValidationError(f"Model id '{model_id}' does not match expected format.")
