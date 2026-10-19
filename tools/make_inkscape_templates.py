#!/usr/bin/env python3
"""Generate the Inkscape poster templates (inkscape/lbi-poster-*.svg).

For maintainers: users only open the generated SVGs in Inkscape.
Run: python3 tools/make_inkscape_templates.py   (standard library only)

Colors come from beamercolorthemelbi.sty, logos from logos/svg/, and font
metrics from the bundled fonts in inkscape/fonts/, so both editions share one
source for each.
"""
from __future__ import annotations  # PEP 604 annotations on Python 3.9 (macOS system python3)

import argparse
import re
import struct
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FONTS = REPO / "inkscape" / "fonts"
SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"
SODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
OSB_NS = "http://www.openswatchbook.org/uri/2009/osb"
LOCKED = f"{{{SODI_NS}}}insensitive"   # Inkscape's lock, on a layer or on a single object
for _prefix, _uri in (("", SVG_NS), ("inkscape", INK_NS), ("sodipodi", SODI_NS), ("osb", OSB_NS)):
    ET.register_namespace(_prefix, _uri)


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

def inline_logo(svg: Path, prefix: str, x: float, y: float, height: float,
                box: tuple[float, float, float, float] | None = None) -> tuple[ET.Element, float]:
    """The logo's drawing as a group placed at (x, y) with the given height, plus its width.

    Embedded SVG images are rasterized on PDF export, so the logo's own
    elements are copied instead: class rules from its <style> become inline
    styles, ids get `prefix`, and metadata and editor attributes are dropped.
    `box` (x, y, width, height in the logo's units) is the area placed at
    (x, y); it defaults to the viewBox. LOGO_BOXES holds the drawing boxes.
    """
    root = ET.parse(svg).getroot()
    vbx, vby, vbw, vbh = box or tuple(float(v) for v in root.get("viewBox").split())
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


# ====================
# Layout constants
# ====================
# Measured on the LaTeX A0 build (mm, TeX pt for type) so both editions match;
# every absolute value is multiplied by the variant's scale.

PT = 25.4 / 72.27  # mm per TeX point
SEP = 0.025        # side margin and column gap, as a fraction of the page width

# (font size, line height) in TeX pt
TYPE = {
    "title": (61.92, 77), "authors": (35.83, 45), "institute": (24.88, 30), "body": (24.88, 30),
    "block_title": (29.86, 37), "caption": (20.74, 25), "references": (17.28, 22), "footer": (24.88, 30),
}

# drawing boxes (x, y, width, height in each SVG's units), measured with
# `inkscape --query-x/--query-y/--query-width/--query-height`; univie.svg has
# a 5-unit margin around its drawing
LOGO_BOXES = {
    "lbi-netmed": (0, 0, 966.96, 366.52),
    "univie": (5, 5, 176.8, 48.18),
    "vbc": (0, -0.0228, 504.49, 256.59),
    "cemm": (0, 0, 700.16, 385.89),
}
LOGO_HEIGHT = 90.0
HEADER_BASELINES = (27.69, 44.70, 57.23, 76.54)  # title, authors, institute 1, institute 2 (below the logo top)
RULE_HEIGHT = 2.03
FOOTER_LOGOS_BOTTOM_FROM_BOTTOM = 12.81
FOOTER_LOGOS = (("univie", 28.0),)   # as in poster_template.tex; logos/svg/ also has vbc and cemm
FOOTER_LOGO_GAP = 17.0
FOOTER_RULE_ABOVE_LOGOS = 15.14      # rule top above the tallest logo's top
FOOTER_BASELINE_BELOW_LOGOS_MIDDLE = 2.25


def footer_from_bottom(logos):
    """(rule top, footer text baseline) above the page bottom. The LaTeX footer centers its text on the logos
    and puts the rule 3ex above the tallest one, so both move with the tallest logo."""
    tallest = max(height for _, height in logos)
    return (FOOTER_LOGOS_BOTTOM_FROM_BOTTOM + tallest + FOOTER_RULE_ABOVE_LOGOS,
            FOOTER_LOGOS_BOTTOM_FROM_BOTTOM + tallest / 2 - FOOTER_BASELINE_BELOW_LOGOS_MIDDLE)


FOOTER_RULE_FROM_BOTTOM, FOOTER_BASELINE_FROM_BOTTOM = footer_from_bottom(FOOTER_LOGOS)

FIRST_TOP_BELOW_RULE = 15.91   # first block top below the header rule (title baseline 25.91 - 10.0)
PLAIN_BASELINE_BELOW_TOP = 10.0
BLOCK_GAP = 11.0
BLOCK_RULE_BELOW_BASELINE = 6.43
BLOCK_RULE_HEIGHT = 0.25
FRAME_BELOW_RULE = 5.77
BAR_HEIGHT = 24.3
BAR_TITLE_BASELINE = 15.15
BAR_TITLE_INSET = 4.98
TINT_PADDING = 4.25
TINT_EXTRA = 9.50              # tint height = lines * line height + TINT_EXTRA
FRAME_SLACK = 1.0              # extra height of invisible plain frames
FIRST_BASELINE_EM = 7.27 / 8.744   # first flowed baseline below the frame's inner top, in em
DESCENT_EM = 3.27 / 8.744          # line box below the last baseline, in em
FIGURE_BELOW_BASELINE = 9.65
CAPTION_BELOW_FIGURE = 18.17
TAIL_BELOW_CAPTION = 14.45
PLACEHOLDER_HEIGHT = 150.0

# LaTeX demo network (TikZ units; 1 unit = 15 mm)
NETWORK_UNIT = 15.0
NETWORK_NODES = {
    "a": (0.5, 1.0), "b": (2.0, 0.3), "c": (1.6, 2.4), "d": (3.4, 1.6), "e": (0.8, 3.6), "f": (2.9, 4.0),
    "g": (4.6, 0.4), "n": (6.0, 5.0), "o": (9.8, 0.5), "h": (13.0, 0.6), "i": (14.8, 1.8), "j": (13.8, 3.8),
    "k": (15.4, 4.6), "l": (11.6, 4.8), "m1": (7.0, 2.0), "m2": (8.2, 3.4), "m3": (9.6, 2.8), "m4": (8.6, 1.4),
    "m5": (10.6, 4.0), "m6": (6.6, 3.6), "m7": (10.4, 1.6), "m8": (9.2, 4.6),
}
NETWORK_EDGES = ("a-b a-c b-d c-d c-e e-f f-d d-g b-g g-o o-h h-i i-j j-k j-l l-k f-n h-j "
                 "d-m6 g-m1 o-m7 l-m5 n-m8").split()
MODULE_EDGES = "m1-m2 m1-m4 m2-m3 m3-m4 m2-m6 m6-m1 m3-m5 m5-m8 m8-m2 m3-m7 m7-m4".split()
NODE_RADIUS = (3.3, 4.2)   # background, module
EDGE_WIDTH = (0.70, 1.41)  # background, module


# ====================
# Variants and demo content
# ====================

@dataclass(frozen=True)
class Variant:
    name: str
    width: float
    height: float
    columns: int
    colwidth_frac: float
    scale: float


VARIANTS = [
    Variant("a0-portrait", 841, 1189, 2, 0.4625, 1.0),
    Variant("a0-landscape", 1189, 841, 3, 0.3, 1.0),
    Variant("a1-portrait", 594, 841, 2, 0.4625, 594 / 841),
]


@dataclass
class Block:
    key: str
    kind: str  # plain, alert or example
    title: str
    paragraphs: list[list[tuple[str, str]]]
    figure: str | None = None  # None, "network" or "placeholder"
    caption: list[tuple[str, str]] | None = None
    tail: list[list[tuple[str, str]]] | None = None


def _bullet(bold: str, rest: str) -> list[tuple[str, str]]:
    return [("▴ ", "bullet"), (bold, "bold"), (rest, "regular")]


BLOCKS = {b.key: b for b in [
    Block("abstract", "plain", "Abstract",
          [[("Some block contents, followed by a diagram, followed by a dummy paragraph.", "regular")]],
          figure="network",
          caption=[("Figure 1.", "label"), (" A disease module (blue) within the protein interaction network.", "regular")],
          tail=[[("Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi ultricies eget libero ac "
                  "ullamcorper. Integer et euismod ante.", "regular")]]),
    Block("list", "plain", "A block containing a list", [
        [("Nam vulputate nunc felis, non condimentum lacus porta ultrices. Nullam sed sagittis metus.", "regular")],
        _bullet("Mauris tempor", " risus nulla, sed ornare"),
        _bullet("Libero tincidunt", " a duis congue vitae"),
        _bullet("Dui ac pretium", " morbi justo neque, ullamcorper"),
        [("Eget augue porta, bibendum venenatis tortor.", "regular")],
    ]),
    Block("alert", "alert", "A highlighted block", [
        [("This block catches your eye, so ", "regular"), ("important stuff", "bold"),
         (" should probably go here.", "regular")],
        [("Curabitur eu libero vehicula, cursus est fringilla, luctus est. Morbi consectetur mauris quam, "
          "at finibus elit auctor ac.", "regular")],
    ]),
    Block("results", "plain", "Fusce aliquam magna velit",
          [[("Et rutrum ex euismod vel. Pellentesque ultricies, velit in fermentum vestibulum, lectus nisi "
             "pretium nibh.", "regular")]],
          figure="placeholder",
          caption=[("Figure 2.", "label"), (" Describe your figure here.", "regular")]),
    Block("example", "example", "Another highlighted block", [
        [("A different kind of highlighted block.", "regular")],
        [("Praesent consectetur mi x", "regular"), ("2", "sup"), (" + y", "regular"), ("2", "sup"),
         (" metus, nec vestibulum justo viverra nec.", "regular")],
    ]),
    Block("conclusion", "plain", "Conclusion", [
        [("Nulla eget sem quam. Ut aliquam volutpat nisi vestibulum convallis. Nunc a lectus et eros "
          "facilisis hendrerit eu non urna.", "regular")],
        _bullet("Sed consequat", " id ante vel efficitur."),
        _bullet("Sed luctus, elit sit amet", " dictum maximus, diam dolor faucibus purus."),
    ]),
    Block("references", "plain", "References", [
        [("[1] Claude E. Shannon. A mathematical theory of communication. Bell System Technical Journal, "
          "27(3):379–423, 1948.", "regular")],
    ]),
]}

COLUMN_LAYOUT = {
    "a0-portrait": [["abstract", "list", "alert"], ["results", "example", "conclusion", "references"]],
    "a0-landscape": [["abstract", "list"], ["alert", "results"], ["example", "conclusion", "references"]],
    "a1-portrait": [["abstract", "list", "alert"], ["results", "example", "conclusion", "references"]],
}

TITLE = "Disease modules in the human interactome"
AUTHORS = [("Jane Doe", "regular"), ("1", "sup"), ("  John Roe", "regular"), ("1 2", "sup"),
           ("  Alex Poe", "regular"), ("2", "sup")]
INSTITUTES = [
    [("1", "sup"), ("Ludwig Boltzmann Institute for Network Medicine at the University of Vienna, Vienna, Austria",
                    "regular")],
    [("2", "sup"), ("CeMM Research Center for Molecular Medicine of the Austrian Academy of Sciences, Vienna, "
                    "Austria", "regular")],
]
FOOTER = "netmed.lbg.ac.at  ·  ABC Conference 2026, Vienna — XYZ-1234  ·  name@lbi-netmed.com"
PLACEHOLDER_TEXT = "Place your figure here: File ▸ Import (Ctrl+I)"


# ====================
# SVG building
# ====================

def _el(parent: ET.Element, tag: str, attrs: dict[str, str], text: str | None = None) -> ET.Element:
    element = ET.SubElement(parent, f"{{{SVG_NS}}}{tag}", attrs)
    element.text = text
    return element


def _font(kind: str, scale: float, serif: bool = False) -> str:
    size, line = TYPE[kind]
    family = "Source Serif Pro" if serif else "Source Sans Pro"
    weight = "font-weight:600;" if serif else ""
    return f"font-family:'{family}';{weight}font-size:{fmt(size * PT * scale)}px;line-height:{fmt(line / size, 4)}"


def _add_runs(text: ET.Element, paragraphs: list[list[tuple[str, str]]], blue: str) -> None:
    """Append runs to a <text>: plain text inline, other kinds as styled tspans, paragraphs on new lines."""
    styles = {"bold": "font-weight:600", "bullet": f"fill:{blue}", "label": f"fill:{blue}",
              "sup": "font-size:65%;baseline-shift:super"}
    last = None
    for index, runs in enumerate(paragraphs):
        for content, kind in ([("\n", "regular")] if index else []) + runs:
            if kind == "regular":
                if last is None:
                    text.text = (text.text or "") + content
                else:
                    last.tail = (last.tail or "") + content
            else:
                last = _el(text, "tspan", {"style": styles[kind]}, content)


def _indent(element: ET.Element, level: int = 0) -> None:
    """Pretty-print structure without touching whitespace inside <text> (xml:space="preserve")."""
    if element.tag == f"{{{SVG_NS}}}text" or not len(element):
        return
    pad = "\n" + "  " * (level + 1)
    element.text = pad
    for child in element:
        _indent(child, level + 1)
        child.tail = pad
    element[-1].tail = "\n" + "  " * level


class _Builder:
    def __init__(self, variant: Variant):
        self.v = variant
        self.s = variant.scale
        self.sep = SEP * variant.width
        self.col = variant.colwidth_frac * variant.width
        colors = read_colors(REPO / "beamercolorthemelbi.sty")
        self.blue, self.mauve, self.navy = colors["lbiblue"], colors["lbimauve"], colors["lbinavy"]
        self.regular = FontMetrics.from_otf(FONTS / "SourceSansPro-Regular.otf")
        self.bold = FontMetrics.from_otf(FONTS / "SourceSansPro-Semibold.otf")

    def size(self, kind: str) -> float:
        return TYPE[kind][0] * PT * self.s

    def line(self, kind: str) -> float:
        return TYPE[kind][1] * PT * self.s

    def text(self, parent, element_id, x, y, kind, fill, runs, serif=False, extra=""):
        text = _el(parent, "text", {"id": element_id, "x": fmt(x), "y": fmt(y),
                                    "{http://www.w3.org/XML/1998/namespace}space": "preserve",
                                    "style": f"{_font(kind, self.s, serif)};fill:{fill}{extra}"})
        _add_runs(text, [runs], self.blue)
        return text

    def rect(self, parent, element_id, x, y, width, height, style):
        return _el(parent, "rect", {"id": element_id, "x": fmt(x), "y": fmt(y), "width": fmt(width),
                                    "height": fmt(height), "style": style})

    def build(self) -> str:
        v, s, sep = self.v, self.s, self.sep
        root = ET.Element(f"{{{SVG_NS}}}svg", {"width": f"{fmt(v.width)}mm", "height": f"{fmt(v.height)}mm",
                                               "viewBox": f"0 0 {fmt(v.width)} {fmt(v.height)}", "version": "1.1"})
        view = ET.SubElement(root, f"{{{SODI_NS}}}namedview", {
            "id": "namedview", "pagecolor": "#ffffff", f"{{{INK_NS}}}document-units": "mm", "showguides": "true"})
        for i in range(v.columns):
            left = sep + i * (self.col + sep)
            for edge, x in (("left", left), ("right", left + self.col)):
                ET.SubElement(view, f"{{{SODI_NS}}}guide",
                              {"id": f"guide-col{i + 1}-{edge}", "position": f"{fmt(x)},0", "orientation": "1,0"})
        defs = _el(root, "defs", {"id": "defs"})
        for name, color in (("lbiblue", self.blue), ("lbimauve", self.mauve), ("lbinavy", self.navy),
                            ("lbiblue!7", tint(self.blue, 7)), ("lbimauve!60", tint(self.mauve, 60)),
                            ("lbimauve!18", tint(self.mauve, 18))):
            swatch_id = "swatch-" + name.replace("!", "-")
            gradient = _el(defs, "linearGradient", {"id": swatch_id, f"{{{INK_NS}}}swatch": "solid",
                                                     f"{{{OSB_NS}}}paint": "solid", f"{{{INK_NS}}}label": name})
            _el(gradient, "stop", {"id": f"{swatch_id}-stop", "offset": "0", "style": f"stop-color:{color};stop-opacity:1"})

        def layer(layer_id, label):
            return _el(root, "g", {"id": layer_id, f"{{{INK_NS}}}groupmode": "layer", f"{{{INK_NS}}}label": label})

        # The Branding layer stays unlocked so users can move or resize the logos; only the rules are locked.
        branding = layer("layer-branding", "Branding")
        texts = layer("layer-text", "Header & footer text")
        content = layer("layer-content", "Content")
        self.header(branding, texts)
        self.footer(branding, texts)
        rule_bottom = sep + LOGO_HEIGHT * s + sep + RULE_HEIGHT * s
        for i, keys in enumerate(COLUMN_LAYOUT[v.name]):
            x, top = sep + i * (self.col + sep), rule_bottom + FIRST_TOP_BELOW_RULE * s
            for key in keys:
                top = self.block(content, BLOCKS[key], x, top) + BLOCK_GAP * s
        _indent(root)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"

    def header(self, branding, texts):
        s, sep = self.s, self.sep
        logo, width = inline_logo(REPO / "logos" / "svg" / "lbi-netmed.svg", "logo-lbi", sep, sep,
                                  LOGO_HEIGHT * s, LOGO_BOXES["lbi-netmed"])
        branding.append(logo)
        self.rect(branding, "header-rule", 0, sep + LOGO_HEIGHT * s + sep, self.v.width, RULE_HEIGHT * s,
                  f"fill:{self.blue}").set(LOCKED, "true")
        x = sep + width + sep
        title, authors, inst1, inst2 = (sep + b * s for b in HEADER_BASELINES)
        self.text(texts, "title", x, title, "title", self.navy, [(TITLE, "regular")], serif=True)
        self.text(texts, "authors", x, authors, "authors", self.navy, AUTHORS)
        for i, (y, runs) in enumerate(zip((inst1, inst2), INSTITUTES), 1):
            self.text(texts, f"institute-{i}", x, y, "institute", tint(self.navy, 80), runs)

    def footer(self, branding, texts):
        s, sep, v = self.s, self.sep, self.v
        self.rect(branding, "footer-rule", 0, v.height - FOOTER_RULE_FROM_BOTTOM * s, v.width, RULE_HEIGHT * s,
                  f"fill:{self.blue}").set(LOCKED, "true")
        self.text(texts, "footer", sep, v.height - FOOTER_BASELINE_FROM_BOTTOM * s, "footer", self.navy,
                  [(FOOTER, "regular")])
        bottom = v.height - FOOTER_LOGOS_BOTTOM_FROM_BOTTOM * s
        widths = [LOGO_BOXES[name][2] / LOGO_BOXES[name][3] * height * s for name, height in FOOTER_LOGOS]
        x = v.width - sep - sum(widths) - FOOTER_LOGO_GAP * s * (len(widths) - 1)
        for (name, height), width in zip(FOOTER_LOGOS, widths):
            logo, _ = inline_logo(REPO / "logos" / "svg" / f"{name}.svg", f"logo-{name}", x, bottom - height * s,
                                  height * s, LOGO_BOXES[name])
            branding.append(logo)
            x += width + FOOTER_LOGO_GAP * s

    def frame(self, group, name, paragraphs, x, y, width, kind, fill=None):
        """A flowing text frame; returns (frame bottom, last baseline)."""
        s, size, line = self.s, self.size(kind), self.line(kind)
        padding = TINT_PADDING * s if fill else 0.0
        lines = wrap_lines(paragraphs, width - 2 * padding, size, self.regular, self.bold)
        if fill:
            height = lines * line + TINT_EXTRA * s
        else:
            height = (lines - 1) * line + (FIRST_BASELINE_EM + DESCENT_EM) * size + FRAME_SLACK * s
        self.rect(group, f"frame-{name}", x, y, width, height, f"fill:{fill}" if fill else "fill:none;stroke:none")
        style = (f"{_font(kind, s)};fill:{self.navy};text-align:start;white-space:pre-wrap;"
                 f"shape-inside:url(#frame-{name})" + (f";shape-padding:{fmt(padding)}" if fill else ""))
        text = _el(group, "text", {"id": f"text-{name}", "{http://www.w3.org/XML/1998/namespace}space": "preserve",
                                   "style": style})
        _add_runs(text, paragraphs, self.blue)
        return y + height, y + padding + FIRST_BASELINE_EM * size + (lines - 1) * line

    def block(self, content, block, x, top):
        """Draw one block at (x, top) in its column; returns its bottom."""
        s, width, key = self.s, self.col, block.key
        group = _el(content, "g", {"id": f"block-{key}"})
        if block.kind == "plain":
            baseline = top + PLAIN_BASELINE_BELOW_TOP * s
            self.text(group, f"title-{key}", x, baseline, "block_title", self.navy, [(block.title, "regular")], serif=True)
            rule_y = baseline + BLOCK_RULE_BELOW_BASELINE * s
            self.rect(group, f"rule-{key}", x, rule_y, width, BLOCK_RULE_HEIGHT * s, f"fill:{self.blue}")
            frame_y, fill = rule_y + BLOCK_RULE_HEIGHT * s + FRAME_BELOW_RULE * s, None
        else:
            alert = block.kind == "alert"
            self.rect(group, f"bar-{key}", x, top, width, BAR_HEIGHT * s,
                      f"fill:{self.blue if alert else tint(self.mauve, 60)}")
            self.text(group, f"title-{key}", x + BAR_TITLE_INSET * s, top + BAR_TITLE_BASELINE * s, "block_title",
                      "#ffffff" if alert else self.navy, [(block.title, "regular")], serif=True)
            frame_y = top + BAR_HEIGHT * s
            fill = tint(self.blue, 7) if alert else tint(self.mauve, 18)
        kind = "references" if key == "references" else "body"
        bottom, last_baseline = self.frame(group, key, block.paragraphs, x, frame_y, width, kind, fill)
        if block.figure:
            # figures are standalone objects in the Content layer, so a click selects just the
            # figure and Delete removes only it (inside the block group it removed the whole block)
            figure_top = last_baseline + FIGURE_BELOW_BASELINE * s
            if block.figure == "network":
                figure_bottom = self.network(content, key, x, figure_top)
            else:
                figure_bottom = figure_top + PLACEHOLDER_HEIGHT * s
                holder = _el(content, "g", {"id": f"placeholder-{key}"})
                self.rect(holder, f"placeholder-frame-{key}", x, figure_top, width, PLACEHOLDER_HEIGHT * s,
                          f"fill:none;stroke:{self.mauve};stroke-width:{fmt(0.5 * s)};"
                          f"stroke-dasharray:{fmt(4 * s)},{fmt(3 * s)}")
                self.text(holder, f"placeholder-text-{key}", x + width / 2,
                          figure_top + PLACEHOLDER_HEIGHT * s / 2 + 0.35 * self.size("caption"), "caption", self.navy,
                          [(PLACEHOLDER_TEXT, "regular")], extra=";text-anchor:middle")
            caption_y = figure_bottom + CAPTION_BELOW_FIGURE * s
            self.text(group, f"caption-{key}", x + width / 2, caption_y, "caption", self.navy, block.caption,
                      extra=";text-anchor:middle")
            bottom = caption_y
            if block.tail:
                bottom, _ = self.frame(group, f"{key}-tail", block.tail, x, caption_y + TAIL_BELOW_CAPTION * s,
                                       width, "body")
        return bottom

    def network(self, group, key, x, top):
        """The LaTeX demo's network figure, centered in the column; returns its bottom."""
        s, unit = self.s, NETWORK_UNIT * self.s
        radius = {n: (NODE_RADIUS[1] if n.startswith("m") else NODE_RADIUS[0]) * s for n in NETWORK_NODES}
        left = min(px * unit - radius[n] for n, (px, _) in NETWORK_NODES.items())
        right = max(px * unit + radius[n] for n, (px, _) in NETWORK_NODES.items())
        high = max(py * unit + radius[n] for n, (_, py) in NETWORK_NODES.items())
        low = min(py * unit - radius[n] for n, (_, py) in NETWORK_NODES.items())
        offset = x + (self.col - (right - left)) / 2 - left
        pos = {n: (offset + px * unit, top + high - py * unit) for n, (px, py) in NETWORK_NODES.items()}
        figure = _el(group, "g", {"id": f"figure-{key}"})
        for edges, color, width in ((NETWORK_EDGES, self.mauve, EDGE_WIDTH[0]), (MODULE_EDGES, self.blue, EDGE_WIDTH[1])):
            for edge in edges:
                a, b = edge.split("-")
                _el(figure, "line", {"x1": fmt(pos[a][0]), "y1": fmt(pos[a][1]), "x2": fmt(pos[b][0]),
                                     "y2": fmt(pos[b][1]), "style": f"stroke:{color};stroke-width:{fmt(width * s)}"})
        for name, (cx, cy) in pos.items():
            color = self.blue if name.startswith("m") else self.mauve
            _el(figure, "circle", {"cx": fmt(cx), "cy": fmt(cy), "r": fmt(radius[name]), "style": f"fill:{color}"})
        return top + high - low


def build_svg(variant: Variant) -> str:
    """The complete template for one variant, as SVG text."""
    return _Builder(variant).build()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write inkscape/lbi-poster-<variant>.svg for all variants.")
    parser.add_argument("--out", type=Path, default=REPO / "inkscape", help="output folder (default: inkscape/)")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    for variant in VARIANTS:
        path = args.out / f"lbi-poster-{variant.name}.svg"
        path.write_text(build_svg(variant), encoding="utf8")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
