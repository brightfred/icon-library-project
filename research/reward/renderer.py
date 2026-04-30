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
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cairosvg
    CAIRO_AVAILABLE = True
except ImportError:
    CAIRO_AVAILABLE = False


# ── Constants ─────────────────────────────────────────────────────────────────

CLIP_SIZE    = 224   # CLIP expects 224x224
SCORE_SIZE   = 96    # primary scoring resolution
ICON_SIZE    = 24    # actual icon size
BG_COLOR     = (255, 255, 255)  # white background
ICON_COLOR   = (30,  30,  30)   # dark gray stroke (approximates currentColor)


@dataclass
class RenderResult:
    """Result of rendering one SVG."""
    success:  bool
    image:    object   # PIL Image or None
    error:    str = ""
    size:     int = 0

    @classmethod
    def failure(cls, error: str) -> "RenderResult":
        return cls(success=False, image=None, error=error)

    @classmethod
    def ok(cls, image: object, size: int) -> "RenderResult":
        return cls(success=True, image=image, size=size)


class SVGRenderer:
    """
    Renders SVG strings to PIL Images using CairoSVG.

    Handles the currentColor substitution — SVG icons use currentColor
    which renders as black by default. We substitute a dark gray to
    match typical UI usage against white backgrounds.

    Single responsibility: rendering only. No scoring, no validation.
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
        """
        Render SVG to a PIL Image at the given size.
        Returns RenderResult with success/failure and the image.
        """
        if not CAIRO_AVAILABLE:
            return RenderResult.failure("cairosvg not installed")
        if not PIL_AVAILABLE:
            return RenderResult.failure("Pillow not installed")
        if not svg or "<svg" not in svg:
            return RenderResult.failure("invalid SVG input")

        try:
            prepared = self._prepare_svg(svg, size)
            png_data = self._render_to_png(prepared, size)
            image    = self._png_to_pil(png_data, size)
            return RenderResult.ok(image, size)
        except Exception as e:
            return RenderResult.failure(str(e))

    def render_multi(self, svg: str) -> dict[int, RenderResult]:
        """Render at all standard sizes. Returns dict of size → RenderResult."""
        return {
            size: self.render(svg, size)
            for size in [ICON_SIZE, SCORE_SIZE, CLIP_SIZE]
        }

    def render_batch(
        self, svgs: list[str], size: int = CLIP_SIZE
    ) -> list[RenderResult]:
        """Render multiple SVGs at the same size."""
        return [self.render(svg, size) for svg in svgs]

    def to_tensor(self, result: RenderResult):
        """
        Convert a RenderResult to a normalized torch tensor (C, H, W).
        Returns None if result failed.
        Used as input to CLIP.
        """
        if not result.success:
            return None
        try:
            import torch
            import numpy as np
            arr = np.array(result.image).astype(np.float32) / 255.0
            # HWC → CHW
            tensor = torch.from_numpy(arr).permute(2, 0, 1)
            return tensor
        except Exception:
            return None

    # ── Private helpers ───────────────────────────────────────────────────────

    def _prepare_svg(self, svg: str, size: int) -> str:
        """
        Prepare SVG for rendering:
        1. Substitute currentColor with a concrete color
        2. Set explicit width/height
        3. Ensure white background
        """
        # Substitute currentColor with icon color
        r, g, b  = self._icon_color
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        svg = svg.replace("currentColor", hex_color)

        # Set explicit dimensions
        svg = self._set_dimensions(svg, size)

        # Add white background rect if not present
        svg = self._add_background(svg)

        return svg

    def _set_dimensions(self, svg: str, size: int) -> str:
        """Set width and height on root svg element."""
        # Replace existing width/height or add them
        svg = re.sub(r'\bwidth="[^"]*"',  f'width="{size}"',  svg)
        svg = re.sub(r'\bheight="[^"]*"', f'height="{size}"', svg)

        # If no width/height present, add them
        if f'width="{size}"' not in svg:
            svg = svg.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)

        return svg

    def _add_background(self, svg: str) -> str:
        """Insert white background rect as first child of svg."""
        r, g, b = self._bg_color
        bg_rect = f'<rect width="100%" height="100%" fill="rgb({r},{g},{b})"/>'

        # Insert after opening svg tag
        svg = re.sub(
            r'(<svg[^>]*>)',
            r'\1' + bg_rect,
            svg,
            count=1
        )
        return svg

    def _render_to_png(self, svg: str, size: int) -> bytes:
        """Use CairoSVG to render SVG to PNG bytes."""
        return cairosvg.svg2png(
            bytestring    = svg.encode("utf-8"),
            output_width  = size,
            output_height = size,
        )

    def _png_to_pil(self, png_data: bytes, size: int) -> object:
        """Convert PNG bytes to PIL Image, ensuring RGB mode."""
        image = Image.open(io.BytesIO(png_data))
        image = image.convert("RGB")
        if image.size != (size, size):
            image = image.resize((size, size), Image.LANCZOS)
        return image

    @staticmethod
    def _check_dependencies():
        if not CAIRO_AVAILABLE:
            print(
                "WARNING: cairosvg not installed. "
                "Run: pip install cairosvg"
            )
        if not PIL_AVAILABLE:
            print(
                "WARNING: Pillow not installed. "
                "Run: pip install Pillow"
            )


# ── Convenience functions ─────────────────────────────────────────────────────

def render_svg(svg: str, size: int = CLIP_SIZE) -> RenderResult:
    """Module-level convenience function."""
    return SVGRenderer().render(svg, size)


def render_to_file(svg: str, output_path: Path, size: int = CLIP_SIZE) -> bool:
    """Render SVG and save to file. Returns True on success."""
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
    print(f"CairoSVG available: {CAIRO_AVAILABLE}")
    print(f"Pillow available:   {PIL_AVAILABLE}")
    print()

    renderer = SVGRenderer()

    # Test with all icons in icons/
    svg_files = list(SRC.glob("*.svg"))
    if not svg_files:
        print("No SVG files found in icons/")
        sys.exit(1)

    print(f"Testing with {len(svg_files)} icons...\n")

    success = 0
    failed  = 0

    for svg_path in svg_files[:10]:
        svg    = svg_path.read_text(encoding="utf-8")
        result = renderer.render(svg, CLIP_SIZE)

        if result.success:
            print(f"  ✓ {svg_path.name} — {result.image.size} {result.image.mode}")
            success += 1
        else:
            print(f"  ✗ {svg_path.name} — {result.error}")
            failed += 1

    print(f"\nResults: {success} ok, {failed} failed")

    # Save one example
    if svg_files:
        out_path = ROOT / "research" / "experiments" / "render_test.png"
        out_path.parent.mkdir(exist_ok=True)
        svg    = svg_files[0].read_text(encoding="utf-8")
        result = renderer.render(svg, 224)
        if result.success:
            result.image.save(str(out_path))
            print(f"\nSaved test render: {out_path}")