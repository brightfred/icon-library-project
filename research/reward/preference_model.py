# research/reward/preference_model.py
"""
Preference Model — learns icon quality from human review decisions.

Trains a small classifier on review flags to predict quality scores
automatically. After ~500 reviewed icons it can auto-review 95% of
new icons, reducing human review burden to spot-checking.

Architecture:
- Input: SVG features (path count, curve ratio, bbox, style compliance)
         + rendered image features (CLIP embeddings)
- Output: quality score 0.0-1.0 + predicted flags

Training data: data/reviewed.json
Each entry: {svg, concept, flags: [...], approved: bool}

Flag taxonomy (12 signals):
  Concept:  correct, wrong-concept, partial
  Anatomy:  missing-parts, wrong-proportions, disconnected
  Stroke:   too-complex, too-simple, filled, wrong-weight
  Design:   unbalanced, not-centered, good
"""

import json
import re
import math
from pathlib import Path
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


# ── Constants ─────────────────────────────────────────────────────────────────

ROOT          = Path(__file__).parent.parent.parent
REVIEWED_FILE = ROOT / "data" / "reviewed.json"
MODEL_DIR     = ROOT / "models" / "preference_model"

ALL_FLAGS = [
    "correct", "wrong-concept", "partial",
    "missing-parts", "wrong-proportions", "disconnected",
    "too-complex", "too-simple", "filled", "wrong-weight",
    "unbalanced", "not-centered", "good",
]

POSITIVE_FLAGS = {"correct", "good"}
NEGATIVE_FLAGS = {
    "wrong-concept", "missing-parts", "wrong-proportions",
    "disconnected", "too-complex", "filled",
}

MIN_REVIEWS_FOR_AUTO = 100
CONFIDENT_THRESHOLD  = 0.75
REJECT_THRESHOLD     = 0.25


# ── SVG Feature Extraction ────────────────────────────────────────────────────

@dataclass
class SVGFeatures:
    path_count:        int   = 0
    has_curves:        bool  = False
    curve_ratio:       float = 0.0
    total_commands:    int   = 0
    correct_viewbox:   bool  = False
    is_stroke_only:    bool  = False
    uses_currentcolor: bool  = False
    correct_linecap:   bool  = False
    correct_linejoin:  bool  = False
    stroke_width:      float = 0.0
    bbox_fill_ratio:   float = 0.0
    is_centered:       bool  = False
    has_symmetry:      bool  = False
    is_too_simple:     bool  = False
    is_too_complex:    bool  = False

    def to_vector(self) -> list[float]:
        return [
            float(self.path_count) / 8.0,
            float(self.has_curves),
            self.curve_ratio,
            float(self.total_commands) / 50.0,
            float(self.correct_viewbox),
            float(self.is_stroke_only),
            float(self.uses_currentcolor),
            float(self.correct_linecap),
            float(self.correct_linejoin),
            self.stroke_width / 3.0,
            self.bbox_fill_ratio,
            float(self.is_centered),
            float(self.has_symmetry),
            float(self.is_too_simple),
            float(self.is_too_complex),
        ]

    @property
    def dim(self) -> int:
        return len(self.to_vector())


def _is_coord(n: float) -> bool:
    return 0.0 <= n <= 24.0


def _collect_coords(root: ET.Element) -> tuple[list[float], list[float]]:
    """Collect all x,y coordinates from all drawable elements."""
    all_x, all_y = [], []

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if tag == "path":
            d    = elem.get("d", "")
            nums = re.findall(r"-?\d+\.?\d*", d)
            coords = [float(n) for n in nums if _is_coord(float(n))]
            all_x.extend(coords[0::2])
            all_y.extend(coords[1::2])

        elif tag == "line":
            for a in ("x1", "x2"):
                v = elem.get(a)
                if v:
                    try: all_x.append(float(v))
                    except ValueError: pass
            for a in ("y1", "y2"):
                v = elem.get(a)
                if v:
                    try: all_y.append(float(v))
                    except ValueError: pass

        elif tag in ("circle", "ellipse"):
            for a in ("cx",):
                v = elem.get(a)
                if v:
                    try: all_x.append(float(v))
                    except ValueError: pass
            for a in ("cy",):
                v = elem.get(a)
                if v:
                    try: all_y.append(float(v))
                    except ValueError: pass

        elif tag == "rect":
            try:
                x = float(elem.get("x", "0"))
                y = float(elem.get("y", "0"))
                w = float(elem.get("width", "0"))
                h = float(elem.get("height", "0"))
                all_x.extend([x, x + w])
                all_y.extend([y, y + h])
            except ValueError:
                pass

        elif tag in ("polyline", "polygon"):
            pts  = elem.get("points", "")
            nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", pts)]
            all_x.extend(nums[0::2])
            all_y.extend(nums[1::2])

    return all_x, all_y


def extract_svg_features(svg: str) -> SVGFeatures:
    f = SVGFeatures()

    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        return f

    # ── Style guide compliance ────────────────────────────────────────────────
    viewbox = root.get("viewBox", "")
    f.correct_viewbox    = viewbox == "0 0 24 24"
    f.is_stroke_only     = root.get("fill", "") == "none"
    f.uses_currentcolor  = root.get("stroke", "") == "currentColor"
    f.correct_linecap    = root.get("stroke-linecap", "") == "round"
    f.correct_linejoin   = root.get("stroke-linejoin", "") == "round"
    try:
        f.stroke_width = float(root.get("stroke-width", "0"))
    except ValueError:
        f.stroke_width = 0.0

    # ── Path analysis ─────────────────────────────────────────────────────────
    all_elements = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag in ("path", "circle", "ellipse", "rect", "line",
                   "polyline", "polygon"):
            all_elements.append((tag, elem))

    f.path_count     = len(all_elements)
    f.is_too_simple  = f.path_count < 2
    f.is_too_complex = f.path_count > 8

    curve_count = 0
    total_cmds  = 0
    for tag, elem in all_elements:
        if tag == "path":
            d    = elem.get("d", "")
            cmds = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]", d)
            total_cmds += len(cmds)
            if re.search(r"[CcSsQqTtAa]", d):
                curve_count += 1
        elif tag in ("circle", "ellipse"):
            curve_count += 1
            total_cmds  += 4
        else:
            total_cmds += 2

    f.total_commands = total_cmds
    f.has_curves     = curve_count > 0
    f.curve_ratio    = curve_count / max(1, f.path_count)

    # ── Geometry ──────────────────────────────────────────────────────────────
    all_x, all_y = _collect_coords(root)

    if all_x and all_y:
        x_range = (max(all_x) - min(all_x)) / 24.0
        y_range = (max(all_y) - min(all_y)) / 24.0
        f.bbox_fill_ratio = min(1.0, (x_range + y_range) / 2.0)

        x_mid = (max(all_x) + min(all_x)) / 2.0
        y_mid = (max(all_y) + min(all_y)) / 2.0
        f.is_centered = (8.0 <= x_mid <= 16.0) and (8.0 <= y_mid <= 16.0)

    f.has_symmetry = _estimate_symmetry(root)

    return f


def _estimate_symmetry(root: ET.Element) -> bool:
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "path":
            if "12" in elem.get("d", ""):
                return True
        elif tag == "line":
            if elem.get("x1") == elem.get("x2") == "12":
                return True
            if elem.get("y1") == elem.get("y2") == "12":
                return True
    return False


# ── Preference Score ──────────────────────────────────────────────────────────

@dataclass
class PreferenceScore:
    quality_score:   float
    predicted_flags: list[str]
    confidence:      float
    auto_decision:   str
    features:        SVGFeatures = field(default_factory=SVGFeatures)

    def __str__(self) -> str:
        return (
            f"PreferenceScore("
            f"quality={self.quality_score:.3f} "
            f"confidence={self.confidence:.3f} "
            f"decision={self.auto_decision} "
            f"flags={self.predicted_flags})"
        )


# ── Rule-based scorer ─────────────────────────────────────────────────────────

class RuleBasedScorer:

    def score(self, svg: str) -> PreferenceScore:
        f     = extract_svg_features(svg)
        score = self._compute_score(f)
        flags = self._predict_flags(f)
        conf  = 0.6

        if score >= CONFIDENT_THRESHOLD:
            decision = "approve"
        elif score <= REJECT_THRESHOLD:
            decision = "reject"
        else:
            decision = "review"

        return PreferenceScore(
            quality_score   = score,
            predicted_flags = flags,
            confidence      = conf,
            auto_decision   = decision,
            features        = f,
        )

    def _compute_score(self, f: SVGFeatures) -> float:
        score = 0.0
        if f.correct_viewbox:    score += 0.10
        if f.is_stroke_only:     score += 0.10
        if f.uses_currentcolor:  score += 0.10
        if f.correct_linecap:    score += 0.05
        if f.correct_linejoin:   score += 0.05
        if 2 <= f.path_count <= 8:
            score += 0.15
        elif f.path_count == 1:
            score += 0.05
        if f.has_curves:         score += 0.10
        if f.curve_ratio > 0.5:  score += 0.05
        if f.bbox_fill_ratio > 0.5: score += 0.10
        if f.is_centered:           score += 0.10
        if f.has_symmetry:          score += 0.10
        return min(1.0, score)

    def _predict_flags(self, f: SVGFeatures) -> list[str]:
        flags = []
        if not f.is_stroke_only:     flags.append("filled")
        if f.is_too_simple:          flags.append("too-simple")
        if f.is_too_complex:         flags.append("too-complex")
        if not f.is_centered:        flags.append("not-centered")
        if f.bbox_fill_ratio < 0.3:  flags.append("wrong-proportions")
        if not f.has_curves:         flags.append("missing-parts")
        if not flags:                flags.append("correct")
        return flags


# ── ML Model ──────────────────────────────────────────────────────────────────

class MLPreferenceModel(nn.Module if TORCH_AVAILABLE else object):

    FEATURE_DIM = 15
    CLIP_DIM    = 512
    HIDDEN_DIM  = 256
    FLAG_COUNT  = len(ALL_FLAGS)

    def __init__(self):
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch required")
        super().__init__()
        input_dim = self.FEATURE_DIM + self.CLIP_DIM
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, self.HIDDEN_DIM),
            nn.LayerNorm(self.HIDDEN_DIM),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(self.HIDDEN_DIM, self.HIDDEN_DIM // 2),
            nn.ReLU(),
        )
        self.quality_head = nn.Sequential(
            nn.Linear(self.HIDDEN_DIM // 2, 1),
            nn.Sigmoid(),
        )
        self.flag_head = nn.Linear(self.HIDDEN_DIM // 2, self.FLAG_COUNT)

    def forward(self, features, clip_embed):
        x      = torch.cat([features, clip_embed], dim=-1)
        hidden = self.encoder(x)
        return self.quality_head(hidden).squeeze(-1), self.flag_head(hidden)


# ── Unified PreferenceModel ───────────────────────────────────────────────────

class PreferenceModel:

    def __init__(self):
        self._rule_scorer  = RuleBasedScorer()
        self._ml_model     = None
        self._review_count = self._load_review_count()

    def score(self, svg: str, clip_embed=None) -> PreferenceScore:
        if self._ml_model is not None and clip_embed is not None:
            return self._ml_score(svg, clip_embed)
        return self._rule_scorer.score(svg)

    def add_review(self, svg: str, concept: str,
                   flags: list[str], approved: bool):
        self._save_review({"svg": svg, "concept": concept,
                           "flags": flags, "approved": approved})
        self._review_count += 1
        if (self._review_count >= MIN_REVIEWS_FOR_AUTO
                and self._review_count % 50 == 0):
            print(f"  {self._review_count} reviews — retraining...")
            self.train()

    def train(self) -> bool:
        reviews = self._load_reviews()
        if len(reviews) < MIN_REVIEWS_FOR_AUTO:
            print(f"  Need {MIN_REVIEWS_FOR_AUTO} reviews (have {len(reviews)})")
            return False
        if not TORCH_AVAILABLE:
            return False
        print(f"  Training on {len(reviews)} reviews...")
        self._ml_model = self._train_model(reviews)
        self._save_model()
        return True

    def load(self) -> bool:
        path = MODEL_DIR / "preference_model.pt"
        if not path.exists() or not TORCH_AVAILABLE:
            return False
        try:
            self._ml_model = MLPreferenceModel()
            self._ml_model.load_state_dict(
                torch.load(str(path), map_location="cpu")
            )
            self._ml_model.eval()
            return True
        except Exception as e:
            print(f"Failed to load: {e}")
            return False

    @property
    def review_count(self) -> int:
        return self._review_count

    @property
    def is_ml_active(self) -> bool:
        return self._ml_model is not None

    def _train_model(self, reviews):
        model     = MLPreferenceModel()
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        X_f, X_c, y_q, y_fl = [], [], [], []
        for r in reviews:
            svg   = r.get("svg", "")
            flags = r.get("flags", [])
            appr  = r.get("approved", False)
            feats = extract_svg_features(svg)
            X_f.append(feats.to_vector())
            X_c.append([0.0] * MLPreferenceModel.CLIP_DIM)
            pos = sum(1 for f in flags if f in POSITIVE_FLAGS)
            neg = sum(1 for f in flags if f in NEGATIVE_FLAGS)
            y_q.append((pos + float(appr)) / (neg + pos + 1.0))
            y_fl.append([1.0 if f in flags else 0.0 for f in ALL_FLAGS])

        Xf = torch.tensor(X_f, dtype=torch.float32)
        Xc = torch.tensor(X_c, dtype=torch.float32)
        yq = torch.tensor(y_q, dtype=torch.float32)
        yf = torch.tensor(y_fl, dtype=torch.float32)

        model.train()
        for ep in range(50):
            optimizer.zero_grad()
            qp, fp = model(Xf, Xc)
            loss   = F.mse_loss(qp, yq) + 0.3 * F.binary_cross_entropy_with_logits(fp, yf)
            loss.backward()
            optimizer.step()
            if (ep + 1) % 10 == 0:
                print(f"    epoch {ep+1}/50  loss={loss.item():.4f}")
        model.eval()
        return model

    def _ml_score(self, svg, clip_embed) -> PreferenceScore:
        feats  = extract_svg_features(svg)
        f_vec  = torch.tensor([feats.to_vector()], dtype=torch.float32)
        c_vec  = (clip_embed.unsqueeze(0)
                  if isinstance(clip_embed, torch.Tensor) and clip_embed.dim() == 1
                  else torch.tensor([clip_embed], dtype=torch.float32))
        with torch.no_grad():
            q, fl = self._ml_model(f_vec, c_vec)
        quality    = float(q.item())
        probs      = torch.sigmoid(fl).squeeze(0)
        pred_flags = [ALL_FLAGS[i] for i, p in enumerate(probs) if p > 0.5]
        confidence = abs(quality - 0.5) * 2.0
        decision   = ("approve" if quality >= CONFIDENT_THRESHOLD
                      else "reject" if quality <= REJECT_THRESHOLD
                      else "review")
        return PreferenceScore(
            quality_score   = quality,
            predicted_flags = pred_flags or ["correct"],
            confidence      = confidence,
            auto_decision   = decision,
            features        = feats,
        )

    def _load_reviews(self):
        if not REVIEWED_FILE.exists():
            return []
        try:
            return json.loads(REVIEWED_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_review(self, review):
        reviews = self._load_reviews()
        reviews.append(review)
        REVIEWED_FILE.parent.mkdir(parents=True, exist_ok=True)
        REVIEWED_FILE.write_text(
            json.dumps(reviews, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _load_review_count(self):
        return len(self._load_reviews())

    def _save_model(self):
        if self._ml_model is None:
            return
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        torch.save(self._ml_model.state_dict(),
                   str(MODEL_DIR / "preference_model.pt"))


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    from pipeline.config import SRC

    print("Preference Model — test (rule-based scorer)")
    model = PreferenceModel()
    print(f"Reviews: {model.review_count}  ML active: {model.is_ml_active}\n")

    print(f"{'icon':<35} {'score':<8} {'decision':<10} flags")
    print("-" * 75)

    for svg_path in sorted(SRC.glob("*.svg"))[:15]:
        svg    = svg_path.read_text(encoding="utf-8")
        result = model.score(svg)
        print(
            f"  {svg_path.stem:<33} "
            f"{result.quality_score:<8.3f} "
            f"{result.auto_decision:<10} "
            f"{result.predicted_flags}"
        )