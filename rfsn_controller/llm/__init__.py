"""LLM Client Package."""

from .deepseek import call_model as call_deepseek
from .gemini import call_model as call_gemini
from .ensemble import call_ensemble_sync
from .async_client import generate_patches_parallel

__all__ = [
    "call_deepseek",
    "call_gemini",
    "call_ensemble_sync",
    "generate_patches_parallel",
]
