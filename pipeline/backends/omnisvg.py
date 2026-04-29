# pipeline/backends/omnisvg.py
import os
import sys
import subprocess

from pipeline.backends.base import AbstractBackend, GenerationRequest, GenerationResult
from pipeline.normalizer import SVGNormalizer
from pipeline.config import (
    OMNISVG_DIR,
    OMNISVG_TMP,
    MODEL_8B,
    MODEL_4B,
    QWEN_MODEL_3B,
    QWEN_MODEL_7B,
    OMNISVG_DEFAULT_SIZE,
    OMNISVG_TIMEOUT,
    OMNISVG_PROMPT_TEMPLATE,
    NUM_CANDIDATES,
    COMPLEX_CATEGORIES,
)


class OmniSVGBackend(AbstractBackend):
    """
    Generates SVG icons using the local OmniSVG model.
    Calls inference.py as a subprocess — keeps the model process
    isolated from the pipeline process.

    Model pairing:
      4B OmniSVG weights → Qwen2.5-VL-3B-Instruct base
      8B OmniSVG weights → Qwen2.5-VL-7B-Instruct base

    Post-processing:
      SVGNormalizer converts filled 200x200 output to
      stroke-only currentColor 24x24 style guide format.
    """

    def __init__(self, model_size: str = OMNISVG_DEFAULT_SIZE):
        self._model_size  = model_size
        self._model_path  = MODEL_8B      if model_size == "8B" else MODEL_4B
        self._qwen_model  = QWEN_MODEL_7B if model_size == "8B" else QWEN_MODEL_3B
        self._prompt_file = OMNISVG_TMP / "_prompt.txt"
        self._normalizer  = SVGNormalizer()

    # ── AbstractBackend interface ─────────────────────────────────────────────

    @property
    def name(self) -> str:
        return f"omnisvg:{self._model_size}"

    def is_available(self) -> bool:
        return (
            OMNISVG_DIR.exists()
            and self._model_path.exists()
            and self._qwen_model.exists()
            and (OMNISVG_DIR / "inference.py").exists()
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if not self.is_available():
            return GenerationResult.failure(
                f"OmniSVG not available — check:\n"
                f"  repo:    {OMNISVG_DIR}\n"
                f"  weights: {self._model_path}\n"
                f"  qwen:    {self._qwen_model}"
            )

        self._prepare_dirs()
        self._write_prompt(request)

        try:
            self._run_inference()
        except subprocess.TimeoutExpired:
            return GenerationResult.failure("OmniSVG inference timed out")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr if isinstance(e.stderr, str) else ""
            return GenerationResult.failure(
                f"OmniSVG process error (exit {e.returncode}):\n{stderr[-1000:]}"
            )

        stroke_width = (
            "1.5" if request.category in COMPLEX_CATEGORIES else "2"
        )
        candidates = self._collect_candidates(stroke_width)
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
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            str(OMNISVG_DIR / "inference.py"),
            "--task",           "text-to-svg",
            "--input",          str(self._prompt_file.resolve()),
            "--output",         str(OMNISVG_TMP.resolve()),
            "--model-path",     str(self._qwen_model.resolve()),
            "--weight-path",    str(self._model_path.resolve()),
            "--model-size",     self._model_size,
            "--num-candidates", str(NUM_CANDIDATES),
            "--save-all-candidates",
        ]
        result = subprocess.run(
            cmd,
            cwd=str(OMNISVG_DIR),
            capture_output=True,
            text=True,
            timeout=OMNISVG_TIMEOUT,
            env=env,
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd,
                output=result.stdout,
                stderr=result.stderr[-2000:],
            )

    def _collect_candidates(self, stroke_width: str) -> list[str]:
        candidates = []
        for svg_file in OMNISVG_TMP.glob("*.svg"):
            try:
                raw = svg_file.read_text(encoding="utf-8").strip()
                if raw:
                    normalized = self._normalizer.normalize(raw, stroke_width)
                    candidates.append(normalized)
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