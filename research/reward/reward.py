# research/reward/reward.py
"""
Unified Reward Function — combines all reward signals for RL training.

Reward = w1 * clip_score          (concept accuracy, fixed)
       + w2 * style_score         (style guide compliance, fixed)
       + w3 * preference_score    (human preference, learned)

This is the single function the RL training loop calls.
Everything else in research/reward/ feeds into this.

Design principles:
- Fast: scores a candidate in <100ms (excluding model load)
- Differentiable-friendly: returns float, not bool
- Transparent: returns breakdown so we can debug reward hacking
- Robust: handles invalid SVG gracefully (score = 0.0)
"""

import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


# ── Reward weights ────────────────────────────────────────────────────────────

# These weights sum to 1.0
# Adjust as the system matures:
# - Early training: higher style weight (model needs to learn format first)
# - Later training: higher clip weight (format learned, focus on concept)

W_CLIP       = 0.40   # concept accuracy (CLIP image-to-image vs Lucide)
W_STYLE      = 0.35   # style guide compliance (rule-based, deterministic)
W_PREFERENCE = 0.25   # human preference (learned, starts rule-based)

assert abs(W_CLIP + W_STYLE + W_PREFERENCE - 1.0) < 1e-6, "Weights must sum to 1.0"

# Reward shaping — penalties applied multiplicatively
INVALID_SVG_PENALTY  = 0.0   # completely invalid SVG
RENDER_FAIL_PENALTY  = 0.1   # valid SVG but won't render
FILLED_ICON_PENALTY  = 0.5   # filled instead of stroke


@dataclass
class RewardBreakdown:
    """
    Full reward breakdown for one candidate SVG.
    Transparent scoring — every component visible for debugging.
    """
    # Final reward
    total:        float = 0.0

    # Component scores (0.0 - 1.0 each)
    clip_score:        float = 0.0
    style_score:       float = 0.0
    preference_score:  float = 0.0

    # Lucide reference similarity (image-to-image)
    lucide_similarity: float = 0.0

    # Metadata
    concept:      str  = ""
    render_ok:    bool = False
    svg_valid:    bool = False
    elapsed_ms:   float = 0.0
    error:        str  = ""

    # Preference model flags
    predicted_flags: list = None

    def __post_init__(self):
        if self.predicted_flags is None:
            self.predicted_flags = []

    def __str__(self) -> str:
        return (
            f"Reward(total={self.total:.3f} "
            f"clip={self.clip_score:.3f} "
            f"style={self.style_score:.3f} "
            f"pref={self.preference_score:.3f} "
            f"flags={self.predicted_flags})"
        )

    @classmethod
    def invalid(cls, concept: str, error: str) -> "RewardBreakdown":
        return cls(
            total     = INVALID_SVG_PENALTY,
            concept   = concept,
            svg_valid = False,
            error     = error,
        )

    @classmethod
    def render_failed(cls, concept: str, error: str) -> "RewardBreakdown":
        return cls(
            total     = RENDER_FAIL_PENALTY,
            concept   = concept,
            svg_valid = True,
            render_ok = False,
            error     = error,
        )


class RewardFunction:
    """
    Unified reward function for RL training.

    Lazy-loads all sub-components on first use.
    Keeps Lucide reference embeddings cached in memory.
    """

    def __init__(
        self,
        lucide_dir: Path | None = None,
        clip_size:  int = 224,
    ):
        self._lucide_dir = lucide_dir or (
            ROOT / "research" / "evaluation" / "benchmark_icons" / "lucide"
        )
        self._clip_size = clip_size

        # Lazy-loaded components
        self._renderer   = None
        self._clip       = None
        self._preference = None

        # Cached Lucide reference embeddings {concept: tensor}
        self._lucide_cache: dict = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def score(self, svg: str, concept: str) -> RewardBreakdown:
        """
        Score one SVG candidate for a given concept.
        Returns RewardBreakdown with full transparency.
        """
        t0 = time.perf_counter()

        # 1. Validate SVG
        if not self._is_valid_svg(svg):
            return RewardBreakdown.invalid(concept, "invalid SVG")

        # 2. Render to PNG
        self._load_renderer()
        render = self._renderer.render(svg, self._clip_size)
        if not render.success:
            return RewardBreakdown.render_failed(concept, render.error)

        # 3. Compute all reward components
        clip_score, lucide_sim = self._compute_clip_score(render.image, concept)
        style_score            = self._compute_style_score(svg)
        pref_result            = self._compute_preference_score(svg)

        # 4. Apply penalties
        penalty = self._compute_penalty(svg)

        # 5. Weighted sum
        total = penalty * (
            W_CLIP       * clip_score +
            W_STYLE      * style_score +
            W_PREFERENCE * pref_result.quality_score
        )

        elapsed = (time.perf_counter() - t0) * 1000

        return RewardBreakdown(
            total            = round(total, 4),
            clip_score       = round(clip_score, 4),
            style_score      = round(style_score, 4),
            preference_score = round(pref_result.quality_score, 4),
            lucide_similarity= round(lucide_sim, 4),
            concept          = concept,
            render_ok        = True,
            svg_valid        = True,
            elapsed_ms       = round(elapsed, 1),
            predicted_flags  = pref_result.predicted_flags,
        )

    def score_batch(
        self,
        svgs:    list[str],
        concept: str,
    ) -> list[RewardBreakdown]:
        """Score multiple candidates for the same concept."""
        return [self.score(svg, concept) for svg in svgs]

    def best(
        self,
        svgs:    list[str],
        concept: str,
    ) -> tuple[int, RewardBreakdown]:
        """Return (index, reward) of the best candidate."""
        results = self.score_batch(svgs, concept)
        best_i  = max(range(len(results)), key=lambda i: results[i].total)
        return best_i, results[best_i]

    def preload_lucide(self, concepts: list[str] | None = None):
        """
        Pre-encode Lucide reference icons into CLIP embedding cache.
        Call this once before a training run to avoid repeated disk reads.
        """
        self._load_clip()
        self._load_renderer()

        if concepts is None:
            concepts = [p.stem for p in self._lucide_dir.glob("*.svg")]

        print(f"Preloading {len(concepts)} Lucide reference embeddings...")
        loaded = 0
        for concept in concepts:
            if concept in self._lucide_cache:
                continue
            path = self._lucide_dir / f"{concept}.svg"
            if not path.exists():
                continue
            svg    = path.read_text(encoding="utf-8")
            render = self._renderer.render(svg, self._clip_size)
            if render.success:
                self._lucide_cache[concept] = self._clip._encode_image(
                    render.image
                )
                loaded += 1

        print(f"  Loaded {loaded} reference embeddings.")

    # ── Private: component loaders ────────────────────────────────────────────

    def _load_renderer(self):
        if self._renderer is None:
            import sys
            sys.path.insert(0, str(ROOT))
            from research.reward.renderer import SVGRenderer
            self._renderer = SVGRenderer()

    def _load_clip(self):
        if self._clip is None:
            import sys
            sys.path.insert(0, str(ROOT))
            from research.reward.clip_scorer import CLIPScorer
            self._clip = CLIPScorer()
            self._clip._load_model()

    def _load_preference(self):
        if self._preference is None:
            import sys
            sys.path.insert(0, str(ROOT))
            from research.reward.preference_model import PreferenceModel
            self._preference = PreferenceModel()
            self._preference.load()

    # ── Private: scoring ──────────────────────────────────────────────────────

    def _compute_clip_score(
        self,
        image:   object,
        concept: str,
    ) -> tuple[float, float]:
        """
        Returns (clip_score, lucide_similarity).

        clip_score = image-to-image similarity vs Lucide reference.
        If no Lucide reference exists for this concept, falls back
        to text-to-image similarity.
        """
        self._load_clip()
        import torch.nn.functional as F

        icon_features = self._clip._encode_image(image)

        # Try image-to-image vs Lucide reference
        if concept in self._lucide_cache:
            ref_features   = self._lucide_cache[concept]
            lucide_sim     = float((icon_features @ ref_features.T).item())
            # Normalize: 0.7 = floor (random icon), 1.0 = ceiling (perfect match)
            clip_score     = max(0.0, (lucide_sim - 0.70) / 0.30)
            return clip_score, lucide_sim

        # Fallback: text-to-image similarity
        text_score = self._clip.score(image, concept).final_score
        # Normalize text score (0.20 = noise floor, 0.30 = good)
        clip_score = max(0.0, (text_score - 0.20) / 0.10)
        return min(1.0, clip_score), 0.0

    def _compute_style_score(self, svg: str) -> float:
        """
        Style guide compliance score.
        Directly encodes the rules from style-guide.md.
        Deterministic — same SVG always gets same score.
        """
        self._load_preference()
        from research.reward.preference_model import extract_svg_features

        f     = extract_svg_features(svg)
        score = 0.0

        # Required attributes (must have all four)
        if f.correct_viewbox:    score += 0.20
        if f.is_stroke_only:     score += 0.20
        if f.uses_currentcolor:  score += 0.15
        if f.correct_linecap:    score += 0.05
        if f.correct_linejoin:   score += 0.05

        # Path structure
        if 2 <= f.path_count <= 8:   score += 0.15
        elif f.path_count == 1:       score += 0.05
        if f.has_curves:              score += 0.10
        if f.curve_ratio > 0.5:       score += 0.05

        # Geometry
        if f.bbox_fill_ratio > 0.5:   score += 0.03
        if f.is_centered:             score += 0.02

        return min(1.0, score)

    def _compute_preference_score(self, svg: str) -> object:
        """Score using preference model (rule-based or ML)."""
        self._load_preference()
        return self._preference.score(svg)

    def _compute_penalty(self, svg: str) -> float:
        """Multiplicative penalty for style violations."""
        import re
        # Penalize filled icons heavily
        if 'fill="' in svg and 'fill="none"' not in svg:
            return FILLED_ICON_PENALTY
        # Penalize hardcoded colors
        hardcoded = re.findall(
            r'(?:fill|stroke|color)="(?!none|currentColor)[^"]*"', svg
        )
        if hardcoded:
            return 0.7
        return 1.0

    @staticmethod
    def _is_valid_svg(svg: str) -> bool:
        if not svg or len(svg) < 50:
            return False
        if "<svg" not in svg:
            return False
        return True


# ── Convenience function ──────────────────────────────────────────────────────

_default_reward: RewardFunction | None = None


def get_reward_function() -> RewardFunction:
    """Get or create the default reward function singleton."""
    global _default_reward
    if _default_reward is None:
        _default_reward = RewardFunction()
    return _default_reward


def score_svg(svg: str, concept: str) -> RewardBreakdown:
    """Module-level convenience function."""
    return get_reward_function().score(svg, concept)


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    from pipeline.config import SRC

    print("Unified Reward Function — test")
    print(f"Weights: clip={W_CLIP} style={W_STYLE} preference={W_PREFERENCE}")
    print()

    reward = RewardFunction()

    # Preload Lucide references for benchmark concepts
    reward.preload_lucide()

    svg_files = list(SRC.glob("*.svg"))
    print(f"\nScoring {len(svg_files)} icons...\n")
    print(f"{'icon':<35} {'total':<8} {'clip':<8} {'style':<8} {'pref':<8} {'ms'}")
    print("-" * 75)

    results = []
    for svg_path in sorted(svg_files):
        svg  = svg_path.read_text(encoding="utf-8")
        parts   = svg_path.stem.split("-", 1)
        concept = parts[1].replace("-", " ") if len(parts) > 1 else svg_path.stem

        r = reward.score(svg, concept)
        results.append((svg_path.stem, r))
        print(
            f"  {svg_path.stem:<33} "
            f"{r.total:<8.3f} "
            f"{r.clip_score:<8.3f} "
            f"{r.style_score:<8.3f} "
            f"{r.preference_score:<8.3f} "
            f"{r.elapsed_ms:.0f}ms"
        )

    print()
    totals = [r.total for _, r in results]
    print(f"  Mean reward: {sum(totals)/len(totals):.3f}")
    print(f"  Best:        {max(totals):.3f} ({results[totals.index(max(totals))][0]})")
    print(f"  Worst:       {min(totals):.3f} ({results[totals.index(min(totals))][0]})")

    # Also score Lucide reference icons for comparison
    lucide_dir = ROOT / "research/evaluation/benchmark_icons/lucide"
    print(f"\nLucide reference icons (target scores):\n")
    print(f"{'icon':<35} {'total':<8} {'clip':<8} {'style':<8} {'pref'}")
    print("-" * 65)

    for svg_path in sorted(lucide_dir.glob("*.svg"))[:10]:
        svg     = svg_path.read_text(encoding="utf-8")
        concept = svg_path.stem
        r       = reward.score(svg, concept)
        print(
            f"  lucide-{svg_path.stem:<27} "
            f"{r.total:<8.3f} "
            f"{r.clip_score:<8.3f} "
            f"{r.style_score:<8.3f} "
            f"{r.preference_score:.3f}"
        )