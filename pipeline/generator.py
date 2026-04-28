# pipeline/generator.py
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pipeline.backends.base import AbstractBackend, GenerationRequest
from pipeline.config import (
    ROOT,
    SRC,
    CATALOG,
    STYLE_GUIDE,
    LOG_FILE,
    COMPLEX_CATEGORIES,
    SLEEP_BETWEEN_ICONS,
    AUTO_PUSH,
)
from pipeline.git import GitPublisher
from pipeline.queue import QueueEntry, QueueManager
from pipeline.scorer import SVGScorer
from pipeline.validator import SVGValidator


@dataclass
class SessionStats:
    generated: int = 0
    failed:    int = 0
    skipped:   int = 0

    def __str__(self) -> str:
        return (
            f"generated={self.generated} "
            f"failed={self.failed} "
            f"skipped={self.skipped}"
        )


class IconGenerator:
    """
    Orchestrates the full icon generation pipeline.
    Reads from the queue, generates via a backend, validates, scores,
    saves, rebuilds the site, and publishes to GitHub.

    Depends on abstractions (AbstractBackend) not concretions —
    swap backends without touching this class.
    """

    def __init__(
        self,
        backend:   AbstractBackend,
        queue:     QueueManager  = None,
        validator: SVGValidator  = None,
        scorer:    SVGScorer     = None,
        publisher: GitPublisher  = None,
        auto_push: bool          = AUTO_PUSH,
    ):
        self._backend   = backend
        self._queue     = queue     or QueueManager()
        self._validator = validator or SVGValidator()
        self._scorer    = scorer    or SVGScorer()
        self._publisher = publisher or GitPublisher()
        self._auto_push = auto_push
        self._style_guide = self._load_style_guide()

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, once: bool = False) -> SessionStats:
        """
        Process the queue until empty (or once=True for a single icon).
        Returns session statistics.
        """
        stats = SessionStats()
        self._log(f"=== Session start (backend={self._backend.name}) ===")

        if not self._backend.is_available():
            self._log(f"Backend not available: {self._backend.name}", "ERROR")
            return stats

        while True:
            entry = self._queue.peek()
            if not entry:
                self._log("Queue empty — done.")
                break

            result = self._process(entry)

            if result == "generated":
                stats.generated += 1
            elif result == "failed":
                stats.failed += 1
            elif result == "skipped":
                stats.skipped += 1

            if once:
                self._log("--once: stopping after first icon.")
                break

            if self._queue.count() > 0:
                time.sleep(SLEEP_BETWEEN_ICONS)

        self._log(f"=== Session complete: {stats} ===")
        return stats

    # ── Private: single icon pipeline ─────────────────────────────────────────

    def _process(self, entry: QueueEntry) -> str:
        """
        Full pipeline for one icon.
        Returns 'generated', 'failed', or 'skipped'.
        """
        name = entry.name
        dest = SRC / f"{name}.svg"

        if dest.exists():
            self._log(f"Already exists: {name}.svg — skipping")
            self._queue.pop()
            return "skipped"

        request = self._build_request(entry)
        result  = self._backend.generate(request)

        if not result.success or not result.candidates:
            self._log(f"Generation failed: {result.error}", "ERROR")
            self._queue.pop()
            self._queue.reject(entry, result.error or "generation failed")
            return "failed"

        valid = self._filter_valid(result.candidates)
        if not valid:
            self._log(f"No valid candidates for {name}", "ERROR")
            self._queue.pop()
            self._queue.reject(entry, "all candidates failed validation")
            return "failed"

        best = self._scorer.best(valid)
        self._save(name, best)
        self._update_catalog(name, entry.concept)
        self._build_site()

        if self._auto_push:
            ok = self._publisher.publish(name)
            if ok:
                self._log(f"✓ Published: {name}")
            else:
                self._log(f"Push failed for {name}", "WARN")

        self._queue.pop()
        return "generated"

    # ── Private: helpers ──────────────────────────────────────────────────────

    def _build_request(self, entry: QueueEntry) -> GenerationRequest:
        category     = entry.name.split("-")[0]
        stroke_width = "1.5" if category in COMPLEX_CATEGORIES else "2"
        return GenerationRequest(
            name         = entry.name,
            concept      = entry.concept,
            category     = category,
            stroke_width = stroke_width,
            style_guide  = self._style_guide,
        )

    def _filter_valid(self, candidates: list[str]) -> list[str]:
        valid = []
        for svg in candidates:
            result = self._validator.validate(svg)
            if result:
                valid.append(svg)
                self._log(f"  ✓ valid candidate (score={self._scorer.score(svg):.1f})")
            else:
                self._log(f"  ✗ invalid: {result}")
        return valid

    def _save(self, name: str, svg: str):
        dest = SRC / f"{name}.svg"
        dest.write_text(svg, encoding="utf-8")
        self._log(f"✓ Saved: src/{name}.svg")

    def _build_site(self):
        try:
            subprocess.run(
                [sys.executable, "build.py"],
                cwd=str(ROOT),
                check=True,
                capture_output=True,
            )
            self._log("✓ Site rebuilt")
        except subprocess.CalledProcessError as e:
            self._log(f"build.py failed: {e}", "WARN")

    def _update_catalog(self, name: str, concept: str):
        if not CATALOG.exists():
            return
        import re
        content  = CATALOG.read_text(encoding="utf-8")
        category = name.split("-")[0]
        row      = f"| `{name}.svg` | {concept} | `needs-review` | |\n"
        section  = f"## {category}"

        if section in content:
            idx = content.find(section)
            end = content.find("\n## ", idx + 1)
            end = end if end != -1 else len(content)
            block   = content[idx:end]
            content = content[:idx] + block.rstrip() + "\n" + row + content[end:]
        else:
            content = (
                content.rstrip()
                + f"\n\n{section}\n\n"
                + "| File | Description | Status | Notes |\n"
                + "|---|---|---|---|\n"
                + row
            )
        CATALOG.write_text(content, encoding="utf-8")

    def _load_style_guide(self) -> str:
        return STYLE_GUIDE.read_text(encoding="utf-8") if STYLE_GUIDE.exists() else ""

    def _log(self, msg: str, level: str = "INFO"):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        print(line)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")