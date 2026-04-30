# research/reward/clip_scorer.py
"""
CLIP Scorer — measures concept accuracy of rendered SVG icons.

Uses OpenCLIP to compute cosine similarity between a rendered icon
and its target concept. Higher score = the icon looks more like
what it's supposed to represent.

This is the fixed component of our hybrid reward model:
- CLIP score: does it look like the concept? (fixed, not learned)
- Preference model: does it match style preferences? (learned)
"""

import torch
import torch.nn.functional as F
from dataclasses import dataclass
from pathlib import Path

try:
    import open_clip
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ── Constants ─────────────────────────────────────────────────────────────────

# Best CLIP model for icon-sized images — ViT-B/32 is fast and accurate
# for small, simple images. Larger models don't help much for 24x24 icons.
DEFAULT_MODEL    = "ViT-B-32"
DEFAULT_PRETRAIN = "openai"

# Text prompt templates — we score against multiple phrasings
# and take the max, which is more robust than a single prompt
CONCEPT_TEMPLATES = [
    "an icon of {concept}",
    "a {concept} icon",
    "a simple {concept} symbol",
    "a minimal {concept} illustration",
    "a line drawing of {concept}",
    "{concept}",
]

# Negative prompts — penalize outputs that look like these
NEGATIVE_CONCEPTS = [
    "random lines",
    "abstract shapes",
    "empty white square",
    "noise",
    "broken image",
]


@dataclass
class CLIPScore:
    """Result of scoring one rendered icon."""
    concept:       str
    score:         float          # 0.0 - 1.0, higher is better
    best_template: str            # which prompt template scored highest
    negative_score: float         # similarity to negative concepts (lower is better)
    final_score:   float          # score - negative_penalty

    def __str__(self) -> str:
        return (
            f"CLIPScore({self.concept!r}: "
            f"raw={self.score:.3f} "
            f"neg={self.negative_score:.3f} "
            f"final={self.final_score:.3f})"
        )


class CLIPScorer:
    """
    Scores rendered SVG icons for concept accuracy using OpenCLIP.

    Loads the model once and keeps it in memory for fast batch scoring.
    Single responsibility: concept accuracy scoring only.
    """

    def __init__(
        self,
        model_name:  str = DEFAULT_MODEL,
        pretrained:  str = DEFAULT_PRETRAIN,
        device:      str | None = None,
    ):
        self._model_name = model_name
        self._pretrained = pretrained
        self._device     = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model      = None
        self._preprocess = None
        self._tokenizer  = None

    # ── Public API ────────────────────────────────────────────────────────────

    def score(self, image: object, concept: str) -> CLIPScore:
        """
        Score a single PIL Image against a concept.
        Returns CLIPScore with raw, negative, and final scores.
        """
        self._load_model()

        image_features   = self._encode_image(image)
        positive_score   = self._score_positive(image_features, concept)
        negative_score   = self._score_negative(image_features)
        final_score      = self._compute_final(positive_score, negative_score)

        best_template = self._best_template(image_features, concept)

        return CLIPScore(
            concept        = concept,
            score          = positive_score,
            best_template  = best_template,
            negative_score = negative_score,
            final_score    = final_score,
        )

    def score_batch(
        self,
        images:   list[object],
        concepts: list[str],
    ) -> list[CLIPScore]:
        """Score multiple image/concept pairs efficiently."""
        self._load_model()
        return [
            self.score(img, concept)
            for img, concept in zip(images, concepts)
        ]

    def rank(
        self,
        images:  list[object],
        concept: str,
    ) -> list[tuple[int, CLIPScore]]:
        """
        Rank multiple candidate images for the same concept.
        Returns list of (original_index, CLIPScore) sorted best first.
        """
        scores = self.score_batch(images, [concept] * len(images))
        ranked = sorted(enumerate(scores), key=lambda x: -x[1].final_score)
        return ranked

    def best(
        self,
        images:  list[object],
        concept: str,
    ) -> tuple[int, CLIPScore]:
        """Return (index, score) of the best candidate image."""
        ranked = self.rank(images, concept)
        return ranked[0]

    def is_available(self) -> bool:
        return CLIP_AVAILABLE and PIL_AVAILABLE

    # ── Private: model loading ────────────────────────────────────────────────

    def _load_model(self):
        if self._model is not None:
            return

        if not CLIP_AVAILABLE:
            raise RuntimeError(
                "open-clip-torch not installed. Run: pip install open-clip-torch"
            )

        print(f"Loading CLIP model {self._model_name} on {self._device}...")
        self._model, _, self._preprocess = open_clip.create_model_and_transforms(
            self._model_name,
            pretrained = self._pretrained,
            device     = self._device,
        )
        self._tokenizer = open_clip.get_tokenizer(self._model_name)
        self._model.eval()
        print("CLIP model loaded.")

    # ── Private: encoding ─────────────────────────────────────────────────────

    def _encode_image(self, image: object) -> torch.Tensor:
        """Encode PIL Image to normalized feature vector."""
        tensor = self._preprocess(image).unsqueeze(0).to(self._device)
        with torch.no_grad():
            features = self._model.encode_image(tensor)
        return F.normalize(features, dim=-1)

    def _encode_texts(self, texts: list[str]) -> torch.Tensor:
        """Encode list of text strings to normalized feature vectors."""
        tokens = self._tokenizer(texts).to(self._device)
        with torch.no_grad():
            features = self._model.encode_text(tokens)
        return F.normalize(features, dim=-1)

    # ── Private: scoring ──────────────────────────────────────────────────────

    def _score_positive(self, image_features: torch.Tensor, concept: str) -> float:
        """Score image against all positive prompt templates, return max."""
        prompts        = [t.format(concept=concept) for t in CONCEPT_TEMPLATES]
        text_features  = self._encode_texts(prompts)
        similarities   = (image_features @ text_features.T).squeeze(0)
        return float(similarities.max().item())

    def _score_negative(self, image_features: torch.Tensor) -> float:
        """Score image against negative concepts, return mean."""
        text_features  = self._encode_texts(NEGATIVE_CONCEPTS)
        similarities   = (image_features @ text_features.T).squeeze(0)
        return float(similarities.mean().item())

    def _compute_final(self, positive: float, negative: float) -> float:
        """
        Final score = positive - negative_penalty.
        Penalizes images that look like abstract noise or empty squares.
        """
        negative_penalty = max(0.0, negative - 0.2) * 0.5
        return max(0.0, positive - negative_penalty)

    def _best_template(self, image_features: torch.Tensor, concept: str) -> str:
        """Return the prompt template that scored highest."""
        prompts       = [t.format(concept=concept) for t in CONCEPT_TEMPLATES]
        text_features = self._encode_texts(prompts)
        similarities  = (image_features @ text_features.T).squeeze(0)
        best_idx      = int(similarities.argmax().item())
        return prompts[best_idx]


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    ROOT = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(ROOT))

    from pipeline.config import SRC
    from research.reward.renderer import SVGRenderer, CLIP_SIZE

    if not CLIP_AVAILABLE:
        print("ERROR: pip install open-clip-torch")
        sys.exit(1)

    print("CLIP Scorer — test")
    print(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    print()

    renderer = SVGRenderer()
    scorer   = CLIPScorer()

    svg_files = list(SRC.glob("*.svg"))
    if not svg_files:
        print("No SVG files found in icons/")
        sys.exit(1)

    print(f"Scoring {min(10, len(svg_files))} icons...\n")

    results = []
    for svg_path in svg_files[:10]:
        svg    = svg_path.read_text(encoding="utf-8")
        render = renderer.render(svg, CLIP_SIZE)

        if not render.success:
            print(f"  ✗ {svg_path.name} — render failed: {render.error}")
            continue

        # Extract concept from filename: category-concept.svg
        parts   = svg_path.stem.split("-", 1)
        concept = parts[1].replace("-", " ") if len(parts) > 1 else svg_path.stem

        clip_score = scorer.score(render.image, concept)
        results.append((svg_path.name, concept, clip_score))

        print(f"  {svg_path.stem:<35} {clip_score}")

    # Summary
    if results:
        print(f"\n{'='*60}")
        scores = [r[2].final_score for r in results]
        print(f"  Mean score:  {sum(scores)/len(scores):.3f}")
        print(f"  Best:        {max(scores):.3f} ({results[scores.index(max(scores))][0]})")
        print(f"  Worst:       {min(scores):.3f} ({results[scores.index(min(scores))][0]})")
        print(f"{'='*60}")

        # Save scores to experiments
        import json
        out = ROOT / "research" / "experiments" / "clip_scores_baseline.json"
        out.parent.mkdir(exist_ok=True)
        data = [
            {
                "icon":           r[0],
                "concept":        r[1],
                "clip_score":     r[2].score,
                "negative_score": r[2].negative_score,
                "final_score":    r[2].final_score,
                "best_template":  r[2].best_template,
            }
            for r in results
        ]
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\nBaseline scores saved to: {out}")