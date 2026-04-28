# pipeline/backends/omnisvg.py
import sys
import subprocess
from pathlib import Path

from pipeline.backends.base import AbstractBackend, GenerationRequest, GenerationResult
from pipeline.config import (
    OMNISVG_DIR,
    OMNISVG_TMP,
    MODEL_8B,
    MODEL_4B,
    OMNISVG_DEFAULT_SIZE,
    OMNISVG_TIMEOUT,
    OMNISVG_PROMPT_TEMPLATE,
    NUM_CANDIDATES,
)


class OmniSVGBackend(AbstractBackend):
    """
    Generates SVG icons using the local OmniSVG model.
    Calls inference.py as a subprocess — keeps the model process
    isolated from the pipeline process.
    """

    def __init__(self, model_size: str = OMNISVG_DEFAULT_SIZE):
        self._model_size = model_size
        self._model_path = MODEL_8B if model_size == "8B" else MODEL_4B
        self._prompt_file = OMNISVG_TMP / "_prompt.txt"

    # ── AbstractBackend interface ─────────────────────────────────────────────

    @property
    def name(self) -> str:
        return f"omnisvg:{self._model_size}"

    def is_available(self) -> bool:
        return (
            OMNISVG_DIR.exists()
            and self._model_path.exists()
            and (OMNISVG_DIR / "inference.py").exists()
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if not self.is_available():
            return GenerationResult.failure(
                f"OmniSVG not available — check {OMNISVG_DIR} and {self._model_path}"
            )

        self._prepare_dirs()
        self._write_prompt(request)

        try:
            self._run_inference()
        except subprocess.TimeoutExpired:
            return GenerationResult.failure("OmniSVG inference timed out")
        except subprocess.CalledProcessError as e:
            return GenerationResult.failure(f"OmniSVG process error: {e}")

        candidates = self._collect_candidates()
        self._cleanup()

        if not candidates:
            return GenerationResult.failure("OmniSVG produced no SVG output")
        return GenerationResult.ok(candidates)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _prepare_dirs(self):
        OMNISVG_TMP.mkdir(exist_ok=True)

    def _write_prompt(self, request: GenerationRequest):
        prompt = OMNISVG_PROMPT_TEMPLATE.format(concept=request.concept)
        self._prompt_file.write_text(prompt, encoding="utf-8")

    def _run_inference(self):
        cmd = [
            sys.executable,
            str(OMNISVG_DIR / "inference.py"),
            "--task",           "text-to-svg",
            "--input",          str(self._prompt_file),
            "--output",         str(OMNISVG_TMP),
            "--model-path",     str(self._model_path),
            "--model-size",     self._model_size,
            "--num-candidates", str(NUM_CANDIDATES),
            "--save-all-candidates",
        ]
        subprocess.run(
            cmd,
            cwd=str(OMNISVG_DIR),
            check=True,
            capture_output=True,
            timeout=OMNISVG_TIMEOUT,
        )

    def _collect_candidates(self) -> list[str]:
        candidates = []
        for svg_file in OMNISVG_TMP.glob("*.svg"):
            try:
                svg = svg_file.read_text(encoding="utf-8").strip()
                if svg:
                    candidates.append(svg)
            except Exception:
                continue
        return candidates

    def _cleanup(self):
        for f in OMNISVG_TMP.glob("*.svg"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            self._prompt_file.unlink()
        except Exception:
            pass