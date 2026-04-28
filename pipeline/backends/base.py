# pipeline/backends/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GenerationRequest:
    """Everything a backend needs to generate one icon."""
    name:        str
    concept:     str
    category:    str
    stroke_width: str
    style_guide: str


@dataclass
class GenerationResult:
    """What a backend returns after attempting generation."""
    success:     bool
    candidates:  list[str]
    error:       str = ""

    @classmethod
    def failure(cls, error: str) -> "GenerationResult":
        return cls(success=False, candidates=[], error=error)

    @classmethod
    def ok(cls, candidates: list[str]) -> "GenerationResult":
        return cls(success=True, candidates=candidates)


class AbstractBackend(ABC):
    """
    Interface all generation backends must implement.
    Open for extension (new backends), closed for modification (generator
    never needs to change when a new backend is added).
    """

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Generate SVG candidates for the given request.
        Must return a GenerationResult — never raise.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check whether this backend is reachable/installed.
        Used at startup to give clear error messages.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name for logging."""
        ...