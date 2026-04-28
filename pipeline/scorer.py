# pipeline/scorer.py
import re
from pipeline.config import MAX_PATHS_IDEAL, MIN_PATHS_IDEAL


class SVGScorer:
    """
    Heuristic quality scorer for SVG icon candidates.
    Higher score = better design quality (syntactic proxy, not visual).
    Single responsibility: scoring only.
    """

    _CURVE_PATTERN    = re.compile(r'[CcQqSsTt]')
    _ELEMENT_PATTERN  = re.compile(
        r'<(?:path|circle|ellipse|rect|polyline|polygon|line)'
    )
    _SIZE_MIN = 200
    _SIZE_MAX = 1500

    def score(self, svg: str) -> float:
        """Return a composite quality score. Higher is better."""
        return sum([
            self._score_curves(svg),
            self._score_path_count(svg),
            self._score_roundedness(svg),
            self._score_file_size(svg),
        ])

    # ── Individual scoring components ─────────────────────────────────────────

    def _score_curves(self, svg: str) -> float:
        """
        Reward bezier curves (C, Q, S, T commands).
        These produce organic shapes — the core problem with LLM-generated icons
        is they default to straight lines. More curves = better design.
        """
        count = len(self._CURVE_PATTERN.findall(svg))
        return count * 2.0

    def _score_path_count(self, svg: str) -> float:
        """
        Reward icons with an ideal number of elements.
        Too few = too simple. Too many = too complex for 16px.
        """
        count = len(self._ELEMENT_PATTERN.findall(svg))
        if MIN_PATHS_IDEAL <= count <= MAX_PATHS_IDEAL:
            return 5.0
        if count == 1:
            return 1.0
        if count > MAX_PATHS_IDEAL:
            return -((count - MAX_PATHS_IDEAL) * 2.0)
        return 0.0

    def _score_roundedness(self, svg: str) -> float:
        """
        Reward round linecaps and linejoins — style guide requirement.
        """
        return 3.0 if "round" in svg else 0.0

    def _score_file_size(self, svg: str) -> float:
        """
        Reward reasonable file size.
        Too small = too simple. Too large = over-engineered.
        """
        size = len(svg)
        return 2.0 if self._SIZE_MIN < size < self._SIZE_MAX else 0.0

    def best(self, candidates: list[str]) -> str:
        """Return the highest-scoring SVG from a list of candidates."""
        if not candidates:
            raise ValueError("No candidates to score")
        return max(candidates, key=self.score)