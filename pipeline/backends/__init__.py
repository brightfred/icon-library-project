# pipeline/backends/__init__.py
from pipeline.backends.base import AbstractBackend, GenerationRequest, GenerationResult
from pipeline.backends.ollama import OllamaBackend
from pipeline.backends.omnisvg import OmniSVGBackend

__all__ = [
    "AbstractBackend",
    "GenerationRequest",
    "GenerationResult",
    "OllamaBackend",
    "OmniSVGBackend",
]