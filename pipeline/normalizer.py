# pipeline/normalizer.py
import re
from xml.etree import ElementTree as ET


class SVGNormalizer:
    """
    Converts OmniSVG output (filled, 200x200) to OpenMark style guide
    (stroke-only, currentColor, 0 0 24 24 viewBox).

    OmniSVG generates filled SVGs on a 200x200 canvas.
    Our style guide requires:
      - viewBox="0 0 24 24"
      - stroke="currentColor"
      - fill="none"
      - stroke-linecap="round" stroke-linejoin="round"
      - no hardcoded colors
      - stroke-width set on root element only
    """

    SOURCE_SIZE  = 200.0
    TARGET_SIZE  = 24.0
    SCALE_FACTOR = TARGET_SIZE / SOURCE_SIZE  # 0.12

    # Attributes to strip from all elements
    _STRIP_ATTRS = {
        "fill-opacity", "filling", "stroke-opacity",
        "filter", "clip-path", "mask", "style",
        "height", "width",
    }

    # Color attributes to neutralize
    _COLOR_ATTRS = {"fill", "stroke", "color"}

    def normalize(self, svg: str, stroke_width: str = "1.5") -> str:
        """
        Full normalization pipeline.
        Returns a style-guide-compliant SVG string.
        """
        svg = self._clean_input(svg)

        try:
            root = ET.fromstring(svg)
        except ET.ParseError:
            return svg  # return as-is if unparseable

        self._normalize_root(root, stroke_width)
        self._normalize_children(root)
        self._scale_coordinates(root)

        ET.register_namespace("", "http://www.w3.org/2000/svg")
        result = ET.tostring(root, encoding="unicode")
        return self._clean_output(result)

    # ── Root element ──────────────────────────────────────────────────────────

    def _normalize_root(self, root: ET.Element, stroke_width: str):
        """Set correct attributes on the root <svg> element."""
        root.set("xmlns",        "http://www.w3.org/2000/svg")
        root.set("viewBox",      "0 0 24 24")
        root.set("fill",         "none")
        root.set("stroke",       "currentColor")
        root.set("stroke-width", stroke_width)
        root.set("stroke-linecap",  "round")
        root.set("stroke-linejoin", "round")

        # Remove size/dimension attrs from root
        for attr in ("height", "width", "style"):
            if attr in root.attrib:
                del root.attrib[attr]

    # ── Child elements ────────────────────────────────────────────────────────

    def _normalize_children(self, root: ET.Element):
        """Recursively clean all child elements."""
        for elem in root.iter():
            if elem is root:
                continue
            self._clean_element(elem)

    def _clean_element(self, elem: ET.Element):
        """Remove fill/color attrs and strip junk attributes from an element."""
        attrs_to_delete = []

        for attr in list(elem.attrib.keys()):
            # Strip decorative/incompatible attributes
            if attr in self._STRIP_ATTRS:
                attrs_to_delete.append(attr)
                continue

            # Remove hardcoded colors — let root currentColor cascade
            if attr in self._COLOR_ATTRS:
                attrs_to_delete.append(attr)
                continue

            # Remove inline style
            if attr == "style":
                attrs_to_delete.append(attr)

        for attr in attrs_to_delete:
            del elem.attrib[attr]

    # ── Coordinate scaling ────────────────────────────────────────────────────

    def _scale_coordinates(self, root: ET.Element):
        """Scale all coordinates from 200x200 to 24x24."""
        for elem in root.iter():
            tag = self._local_tag(elem.tag)

            if tag == "path":
                if "d" in elem.attrib:
                    elem.set("d", self._scale_path(elem.get("d")))

            elif tag in ("circle", "ellipse"):
                for attr in ("cx", "cy", "r", "rx", "ry"):
                    if attr in elem.attrib:
                        elem.set(attr, self._scale_val(elem.get(attr)))

            elif tag == "rect":
                for attr in ("x", "y", "width", "height", "rx", "ry"):
                    if attr in elem.attrib:
                        elem.set(attr, self._scale_val(elem.get(attr)))

            elif tag == "line":
                for attr in ("x1", "y1", "x2", "y2"):
                    if attr in elem.attrib:
                        elem.set(attr, self._scale_val(elem.get(attr)))

            elif tag in ("polyline", "polygon"):
                if "points" in elem.attrib:
                    elem.set("points", self._scale_points(elem.get("points")))

    def _scale_val(self, val: str) -> str:
        """Scale a single numeric value."""
        try:
            return self._fmt(float(val) * self.SCALE_FACTOR)
        except (ValueError, TypeError):
            return val

    def _scale_path(self, d: str) -> str:
        """Scale all numeric coordinates in an SVG path d attribute."""
        def replace_num(match):
            try:
                val = float(match.group())
                return self._fmt(val * self.SCALE_FACTOR)
            except ValueError:
                return match.group()

        return re.sub(r"-?\d+\.?\d*", replace_num, d)

    def _scale_points(self, points: str) -> str:
        """Scale polyline/polygon points."""
        def replace_num(match):
            try:
                return self._fmt(float(match.group()) * self.SCALE_FACTOR)
            except ValueError:
                return match.group()
        return re.sub(r"-?\d+\.?\d*", replace_num, points)

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt(val: float) -> str:
        """Format float — drop unnecessary decimals."""
        rounded = round(val, 2)
        if rounded == int(rounded):
            return str(int(rounded))
        return str(rounded)

    @staticmethod
    def _local_tag(tag: str) -> str:
        """Strip XML namespace prefix from tag name."""
        return tag.split("}")[-1] if "}" in tag else tag

    @staticmethod
    def _clean_input(svg: str) -> str:
        """Remove XML declaration and doctype if present."""
        svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
        svg = re.sub(r"<!DOCTYPE[^>]*>",  "", svg).strip()
        return svg

    @staticmethod
    def _clean_output(svg: str) -> str:
        """Clean up namespace artifacts from ElementTree serialization."""
        svg = re.sub(r'\s*xmlns:ns\d+="[^"]*"', "", svg)
        svg = re.sub(r'ns\d+:', "", svg)
        return svg