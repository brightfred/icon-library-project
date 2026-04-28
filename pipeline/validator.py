# pipeline/validator.py
import re
from dataclasses import dataclass
from pipeline.config import (
    REQUIRED_VIEWBOX,
    REQUIRED_FILL,
    REQUIRED_STROKE,
    MIN_SVG_LENGTH,
)


@dataclass
class ValidationResult:
    is_valid: bool
    reason: str

    def __bool__(self) -> bool:
        return self.is_valid

    def __str__(self) -> str:
        return "ok" if self.is_valid else self.reason


class SVGValidator:
    """
    Validates SVG content against the OpenMark style guide.
    Single responsibility: validation only, no generation or scoring.
    """

    _HARDCODED_COLOR_PATTERN = re.compile(
        r'(?:fill|stroke|color)="(?!none|currentColor)[^"]*"'
    )

    def validate(self, svg: str) -> ValidationResult:
        """Run all checks in order. Return first failure or success."""
        checks = [
            self._check_length,
            self._check_svg_tag,
            self._check_viewbox,
            self._check_current_color,
            self._check_fill_none,
            self._check_stroke,
            self._check_no_hardcoded_colors,
        ]
        for check in checks:
            result = check(svg)
            if not result:
                return result
        return ValidationResult(is_valid=True, reason="ok")

    # ── Individual checks ─────────────────────────────────────────────────────

    def _check_length(self, svg: str) -> ValidationResult:
        if not svg or len(svg) < MIN_SVG_LENGTH:
            return ValidationResult(False, "too short or empty")
        return ValidationResult(True, "ok")

    def _check_svg_tag(self, svg: str) -> ValidationResult:
        if "<svg" not in svg:
            return ValidationResult(False, "missing <svg> tag")
        return ValidationResult(True, "ok")

    def _check_viewbox(self, svg: str) -> ValidationResult:
        if f'viewBox="{REQUIRED_VIEWBOX}"' not in svg:
            return ValidationResult(False, f'viewBox must be "{REQUIRED_VIEWBOX}"')
        return ValidationResult(True, "ok")

    def _check_current_color(self, svg: str) -> ValidationResult:
        if "currentColor" not in svg:
            return ValidationResult(False, "missing currentColor")
        return ValidationResult(True, "ok")

    def _check_fill_none(self, svg: str) -> ValidationResult:
        if 'fill="none"' not in svg:
            return ValidationResult(False, 'missing fill="none" on root element')
        return ValidationResult(True, "ok")

    def _check_stroke(self, svg: str) -> ValidationResult:
        if f'stroke="{REQUIRED_STROKE}"' not in svg:
            return ValidationResult(False, 'missing stroke="currentColor"')
        return ValidationResult(True, "ok")

    def _check_no_hardcoded_colors(self, svg: str) -> ValidationResult:
        match = self._HARDCODED_COLOR_PATTERN.search(svg)
        if match:
            return ValidationResult(False, f"hardcoded color: {match.group()}")
        return ValidationResult(True, "ok")