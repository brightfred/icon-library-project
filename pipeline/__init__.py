# pipeline/__init__.py
from pipeline.config import DEFAULT_BACKEND
from pipeline.generator import IconGenerator
from pipeline.queue import QueueEntry, QueueManager
from pipeline.validator import SVGValidator
from pipeline.scorer import SVGScorer
from pipeline.git import GitPublisher
from pipeline.normalizer import SVGNormalizer
from pipeline.backends.ollama import OllamaBackend
from pipeline.backends.omnisvg import OmniSVGBackend


def create_backend(name: str = DEFAULT_BACKEND):
    """
    Factory function — returns the correct backend instance by name.
    Add new backends here without touching any other file.
    """
    backends = {
        "ollama":  OllamaBackend,
        "omnisvg": OmniSVGBackend,
    }
    if name not in backends:
        raise ValueError(
            f"Unknown backend: '{name}'. "
            f"Available: {', '.join(backends.keys())}"
        )
    return backends[name]()


__all__ = [
    "IconGenerator",
    "QueueEntry",
    "QueueManager",
    "SVGValidator",
    "SVGScorer",
    "SVGNormalizer",
    "GitPublisher",
    "OllamaBackend",
    "OmniSVGBackend",
    "create_backend",
]