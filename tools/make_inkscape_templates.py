#!/usr/bin/env python3
"""Generate the Inkscape poster templates (inkscape/lbi-poster-*.svg).

For maintainers: users only open the generated SVGs in Inkscape.
Run: python3 tools/make_inkscape_templates.py   (standard library only)

Colors come from beamercolorthemelbi.sty, logos from logos/svg/, and font
metrics from the bundled fonts in inkscape/fonts/, so both editions share one
source for each.
"""
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SVG_NS = "http://www.w3.org/2000/svg"


def fmt(value: float, digits: int = 3) -> str:
    """Number for SVG output: fixed precision, trailing zeros stripped."""
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


# ====================
# Colors
# ====================

def read_colors(sty: Path) -> dict[str, str]:
    r"""Colors defined as \definecolor{name}{RGB}{r, g, b}, as lowercase #rrggbb."""
    pattern = r"\\definecolor\{(\w+)\}\{RGB\}\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}"
    return {
        name: "#%02x%02x%02x" % (int(r), int(g), int(b))
        for name, r, g, b in re.findall(pattern, sty.read_text(encoding="utf8"))
    }


def tint(color: str, percent: float) -> str:
    """xcolor's color!percent: p * color + (1 - p) * white, rounded half up."""
    p = percent / 100
    channels = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join("%02x" % int(p * c + (1 - p) * 255 + 0.5) for c in channels)


# ====================
# Font metrics and line wrapping
# ====================

def _cmap_format4(data: bytes, at: int) -> dict[int, int]:
    """Character code -> glyph id from a cmap format-4 subtable starting at `at`."""
    seg_count = struct.unpack_from(">H", data, at + 6)[0] // 2
    ends = struct.unpack_from(f">{seg_count}H", data, at + 14)
    starts = struct.unpack_from(f">{seg_count}H", data, at + 16 + 2 * seg_count)
    deltas = struct.unpack_from(f">{seg_count}h", data, at + 16 + 4 * seg_count)
    range_at = at + 16 + 6 * seg_count
    range_offsets = struct.unpack_from(f">{seg_count}H", data, range_at)
    cmap = {}
    for i in range(seg_count):
        for code in range(starts[i], ends[i] + 1):
            if code == 0xFFFF:
                continue
            if range_offsets[i] == 0:
                glyph = (code + deltas[i]) & 0xFFFF
            else:
                address = range_at + 2 * i + range_offsets[i] + 2 * (code - starts[i])
                glyph = struct.unpack_from(">H", data, address)[0]
                glyph = (glyph + deltas[i]) & 0xFFFF if glyph else 0
            if glyph:
                cmap[code] = glyph
    return cmap


class FontMetrics:
    """Horizontal advances of an OpenType font, read from cmap (3,1) format 4 and hmtx."""

    def __init__(self, cmap: dict[int, int], advances: list[int], units_per_em: int):
        self.cmap = cmap
        self.advances = advances
        self.units_per_em = units_per_em

    @classmethod
    def from_otf(cls, path: Path) -> "FontMetrics":
        data = path.read_bytes()
        num_tables = struct.unpack_from(">H", data, 4)[0]
        tables = {}
        for i in range(num_tables):
            tag, _checksum, offset, _length = struct.unpack_from(">4sIII", data, 12 + 16 * i)
            tables[tag.decode("latin-1")] = offset
        units_per_em = struct.unpack_from(">H", data, tables["head"] + 18)[0]
        num_hmetrics = struct.unpack_from(">H", data, tables["hhea"] + 34)[0]
        advances = [struct.unpack_from(">H", data, tables["hmtx"] + 4 * i)[0] for i in range(num_hmetrics)]
        cmap_at = tables["cmap"]
        for i in range(struct.unpack_from(">H", data, cmap_at + 2)[0]):
            platform, encoding, offset = struct.unpack_from(">HHI", data, cmap_at + 4 + 8 * i)
            if (platform, encoding) == (3, 1) and struct.unpack_from(">H", data, cmap_at + offset)[0] == 4:
                return cls(_cmap_format4(data, cmap_at + offset), advances, units_per_em)
        raise ValueError(f"{path.name}: no (3,1) format-4 cmap subtable")

    def advance(self, ch: str) -> float:
        """Advance width of `ch` in em; characters missing from the font use glyph 0."""
        glyph = self.cmap.get(ord(ch), 0)
        return self.advances[min(glyph, len(self.advances) - 1)] / self.units_per_em


def text_width(text: str, metrics: FontMetrics, size: float) -> float:
    """Width of `text` at font size `size` (same unit as size), without kerning."""
    return sum(metrics.advance(ch) for ch in text) * size


def wrap_lines(paragraphs: list[list[tuple[str, str]]], width: float, size: float,
               regular: FontMetrics, bold: FontMetrics) -> int:
    """Number of lines greedy word wrapping needs at `width * 0.98`.

    Each paragraph is a list of (text, kind) runs, kind in regular / bold /
    bullet / sup, and starts on a new line. Bold runs are measured with the
    bold metrics, sup runs at 65% size.
    """
    limit = width * 0.98
    space = regular.advance(" ") * size
    lines = 0
    for runs in paragraphs:
        words, current = [], 0.0
        for text, kind in runs:
            metrics = bold if kind == "bold" else regular
            scale = 0.65 if kind == "sup" else 1.0
            for ch in text:
                if ch == " ":
                    if current:
                        words.append(current)
                    current = 0.0
                else:
                    current += metrics.advance(ch) * size * scale
        if current:
            words.append(current)
        count, line = 1, None
        for word in words:
            if line is None:
                line = word
            elif line + space + word <= limit:
                line += space + word
            else:
                count, line = count + 1, word
        lines += count
    return lines


# ====================
# Logos
# ====================

def inline_logo(svg: Path, prefix: str, x: float, y: float, height: float) -> tuple[ET.Element, float]:
    """The logo's drawing as a group placed at (x, y) with the given height, plus its width.

    Embedded SVG images are rasterized on PDF export, so the logo's own
    elements are copied instead: class rules from its <style> become inline
    styles, ids get `prefix`, and metadata and editor attributes are dropped.
    """
    root = ET.parse(svg).getroot()
    vbx, vby, vbw, vbh = (float(v) for v in root.get("viewBox").split())
    rules: dict[str, list[str]] = {}
    for style in root.iter(f"{{{SVG_NS}}}style"):
        for selectors, declarations in re.findall(r"([^{}]+)\{([^}]*)\}", style.text or ""):
            for selector in selectors.split(","):
                selector = selector.strip()
                if selector.startswith("."):
                    rules.setdefault(selector[1:], []).append(declarations.strip().rstrip(";"))

    k = height / vbh
    group = ET.Element(f"{{{SVG_NS}}}g", {
        "id": prefix,
        "transform": f"translate({fmt(x)},{fmt(y)}) scale({fmt(k, 6)}) translate({fmt(-vbx)},{fmt(-vby)})",
    })

    def copy(element: ET.Element, parent: ET.Element) -> None:
        tag = element.tag.rpartition("}")[2]
        if not element.tag.startswith(f"{{{SVG_NS}}}") or tag in ("style", "metadata", "title", "defs"):
            return
        attrs = {name: value for name, value in element.attrib.items() if not name.startswith("{") and name != "class"}
        declarations = [d for cls in (element.get("class") or "").split() for d in rules.get(cls, [])]
        if "style" in attrs:
            declarations.append(attrs["style"])
        if declarations:
            attrs["style"] = ";".join(declarations)
        if "id" in attrs:
            attrs["id"] = f"{prefix}-{attrs['id']}"
        child = ET.SubElement(parent, element.tag, attrs)
        for sub in element:
            copy(sub, child)

    for element in root:
        copy(element, group)
    return group, vbw * k
