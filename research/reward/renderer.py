# research/reward/renderer.py
"""
SVG Renderer — converts SVG strings to PIL Images for visual scoring.

Used by the reward model to render icon candidates before scoring them
with CLIP or the preference model.

Renders at multiple sizes:
- 96x96  — primary scoring size (4x upscale from 24x24)
- 224x224 — CLIP input size
- 24x24  — actual icon size (readability check)
"""

import io
import re
from pathlib import Path
from dataclasses import dataclass

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cairosvg
    CAIRO_AVAILABLE = True
except ImportError:
    CAIRO_AVAILABLE = False


# ── Constants ─────────────────────────────────────────────────────────────────

CLIP_SIZE  = 224
SCORE_SIZE = 96
ICON_SIZE  = 24
BG_COLOR   = (255, 255, 255)
ICON_COLOR = (30,  30,  30)


@dataclass
class RenderResult:
    success: bool
    image:   object
    error:   str = ""
    size:    int = 0

    @classmethod
    def failure(cls, error: str) -> "RenderResult":
        return cls(success=False, image=None, error=error)

    @classmethod
    def ok(cls, image: object, size: int) -> "RenderResult":
        return cls(success=True, image=image, size=size)


class SVGRenderer:
    """
    Renders SVG strings to PIL Images using CairoSVG.
    Handles currentColor substitution and background injection.
    """

    def __init__(
        self,
        bg_color:   tuple[int, int, int] = BG_COLOR,
        icon_color: tuple[int, int, int] = ICON_COLOR,
    ):
        self._bg_color   = bg_color
        self._icon_color = icon_color
        self._check_dependencies()

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self, svg: str, size: int = CLIP_SIZE) -> RenderResult:
        if not CAIRO_AVAILABLE:
            return RenderResult.failure("cairosvg not installed")
        if not PIL_AVAILABLE:
            return RenderResult.failure("Pillow not installed")
        if not svg or "<svg" not in svg:
            return RenderResult.failure("invalid SVG input")

        try:
            prepared = self._prepare_svg(svg, size)
            png_data = cairosvg.svg2png(
                bytestring    = prepared.encode("utf-8"),
                output_width  = size,
                output_height = size,
            )
            image = Image.open(io.BytesIO(png_data)).convert("RGB")
            if image.size != (size, size):
                image = image.resize((size, size), Image.LANCZOS)
            return RenderResult.ok(image, size)
        except Exception as e:
            return RenderResult.failure(str(e))

    def render_multi(self, svg: str) -> dict[int, RenderResult]:
        return {size: self.render(svg, size) for size in [ICON_SIZE, SCORE_SIZE, CLIP_SIZE]}

    def render_batch(self, svgs: list[str], size: int = CLIP_SIZE) -> list[RenderResult]:
        return [self.render(svg, size) for svg in svgs]

    def to_tensor(self, result: RenderResult):
        if not result.success:
            return None
        try:
            import torch
            import numpy as np
            arr    = np.array(result.image).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr).permute(2, 0, 1)
            return tensor
        except Exception:
            return None

    # ── Private ───────────────────────────────────────────────────────────────

    def _prepare_svg(self, svg: str, size: int) -> str:
        """
        Preparation order matters:
        1. Strip XML declaration
        2. Remove duplicate xmlns
        3. Set explicit dimensions
        4. Add white background (explicit hex, no currentColor)
        5. Substitute currentColor LAST so background is not affected
        """
        # Strip XML declaration
        svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()

        # Remove duplicate xmlns attributes
        svg = self._remove_duplicate_xmlns(svg)

        # Set explicit width/height
        svg = self._set_dimensions(svg, size)

        # Add white background BEFORE currentColor substitution
        svg = self._add_background(svg)

        # Substitute currentColor with explicit dark color LAST
        r, g, b   = self._icon_color
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        svg = svg.replace("currentColor", hex_color)

        return svg

    def _remove_duplicate_xmlns(self, svg: str) -> str:
        """Remove duplicate xmlns attributes that cause CairoSVG parse errors."""
        # Find all xmlns occurrences and keep only the first
        count = [0]
        def replace_xmlns(m):
            count[0] += 1
            return m.group(0) if count[0] == 1 else ""
        return re.sub(r'\s*xmlns="[^"]*"', replace_xmlns, svg)

    def _set_dimensions(self, svg: str, size: int) -> str:
        """Set explicit width and height on root svg element."""
        # Remove existing width/height
        svg = re.sub(r'\s+width="[^"]*"',  "", svg)
        svg = re.sub(r'\s+height="[^"]*"', "", svg)
        # Add correct dimensions
        svg = svg.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)
        return svg

    def _add_background(self, svg: str) -> str:
        """
        Insert white background rect as first child.
        Uses explicit hex color — NOT currentColor — so it stays white
        even after currentColor substitution.
        """
        r, g, b  = self._bg_color
        hex_bg   = f"#{r:02x}{g:02x}{b:02x}"
        bg_rect  = f'<rect width="100%" height="100%" fill="{hex_bg}" stroke="none"/>'
        svg = re.sub(r'(<svg[^>]*>)', r'\1' + bg_rect, svg, count=1)
        return svg

    @staticmethod
    def _check_dependencies():
        if not CAIRO_AVAILABLE:
            print("WARNING: cairosvg not installed. Run: pip install cairosvg")
        if not PIL_AVAILABLE:
            print("WARNING: Pillow not installed. Run: pip install Pillow")


# ── Convenience functions ─────────────────────────────────────────────────────

def render_svg(svg: str, size: int = CLIP_SIZE) -> RenderResult:
    return SVGRenderer().render(svg, size)


def render_to_file(svg: str, output_path: Path, size: int = CLIP_SIZE) -> bool:
    result = SVGRenderer().render(svg, size)
    if result.success:
        result.image.save(str(output_path))
        return True
    return False


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    ROOT = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(ROOT))

    from pipeline.config import SRC

    print("SVG Renderer — test")
    print(f"CairoSVG: {CAIRO_AVAILABLE}  Pillow: {PIL_AVAILABLE}")
    print()

    renderer  = SVGRenderer()
    svg_files = list(SRC.glob("*.svg"))

    success = failed = 0
    for svg_path in svg_files[:10]:
        svg    = svg_path.read_text(encoding="utf-8")
        result = renderer.render(svg, CLIP_SIZE)
        if result.success:
            # Sample center pixel — should be white (background) or dark (stroke)
            px = result.image.load()
            center = px[112, 112]
            corner = px[0, 0]
            print(f"  ✓ {svg_path.name:<35} center={center} corner={corner}")
            success += 1
        else:
            print(f"  ✗ {svg_path.name:<35} {result.error}")
            failed += 1

    print(f"\nResults: {success} ok, {failed} failed")

    # Save examples
    out = ROOT / "research" / "experiments"
    out.mkdir(exist_ok=True)
    for name in ["science-flask", "environment-leaf", "engineering-gear"]:
        p = SRC / f"{name}.svg"
        if p.exists():
            render_to_file(p.read_text(encoding="utf-8"), out / f"{name}.png", CLIP_SIZE)
            print(f"Saved: {out / name}.png")