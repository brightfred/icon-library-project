# pipeline/backends/ollama.py
import json
import time
import urllib.request
import urllib.error

from pipeline.backends.base import AbstractBackend, GenerationRequest, GenerationResult
from pipeline.config import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    OLLAMA_TEMPERATURE,
    OLLAMA_MAX_TOKENS,
    OLLAMA_TIMEOUT,
    NUM_CANDIDATES,
)


class OllamaBackend(AbstractBackend):
    """
    Generates SVG icons by prompting a local Ollama model.
    Handles prompt construction, HTTP communication, and SVG extraction.
    """

    def __init__(self, model: str = OLLAMA_MODEL, url: str = OLLAMA_URL):
        self._model = model
        self._url   = url

    # ── AbstractBackend interface ─────────────────────────────────────────────

    @property
    def name(self) -> str:
        return f"ollama:{self._model}"

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False

    def generate(self, request: GenerationRequest) -> GenerationResult:
        prompt     = self._build_prompt(request)
        candidates = []

        for i in range(NUM_CANDIDATES):
            raw = self._call_ollama(prompt)
            if raw:
                svg = self._extract_svg(raw)
                if svg:
                    candidates.append(svg)
            if i < NUM_CANDIDATES - 1:
                time.sleep(0.5)

        if not candidates:
            return GenerationResult.failure("ollama returned no valid SVG")
        return GenerationResult.ok(candidates)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_prompt(self, request: GenerationRequest) -> str:
        return f"""You are an expert SVG icon designer. Output ONLY raw SVG code — no markdown, no explanation, no code fences.

STRICT RULES (violating any = rejected):
- viewBox="0 0 24 24" exactly
- fill="none" on root svg element
- stroke="currentColor" on root svg element
- stroke-width="{request.stroke_width}" on root svg element
- stroke-linecap="round" stroke-linejoin="round" on root svg element
- NO hardcoded colors — only currentColor
- NO filled shapes
- NO <title>, NO <desc>, NO comments, NO inline styles
- Minimum 1.5px padding from all edges

DESIGN RULES:
- Use bezier curves (C, c, Q, q) for organic shapes — not just straight lines
- 2 to 8 paths maximum — must read clearly at 16px
- Each path represents one named anatomical part of the object
- Trace real silhouettes with curves, not disconnected lines
- Visually balanced left-to-right and top-to-bottom

ICON TO DRAW:
Name: {request.name}
Concept: {request.concept}
Category: {request.category}

Output the SVG now:"""

    def _call_ollama(self, prompt: str) -> str | None:
        payload = json.dumps({
            "model":  self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": OLLAMA_TEMPERATURE,
                "num_predict": OLLAMA_MAX_TOKENS,
            }
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                self._url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")
        except urllib.error.URLError as e:
            return None
        except Exception:
            return None

    def _extract_svg(self, text: str) -> str | None:
        """Pull the SVG element out of a response that may contain markdown."""
        import re
        match = re.search(r'(<svg[\s\S]*?</svg>)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None