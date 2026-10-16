"""Unit tests for make_inkscape_templates.py. Run: python3 -m unittest discover -s tools"""
import re
import unittest
import xml.etree.ElementTree as ET

import make_inkscape_templates as gen

SVG = "{http://www.w3.org/2000/svg}"
PT = 25.4 / 72.27  # mm per TeX point
FONTS = gen.REPO / "inkscape" / "fonts"


class ColorTests(unittest.TestCase):
    def test_read_colors(self):
        self.assertEqual(
            gen.read_colors(gen.REPO / "beamercolorthemelbi.sty"),
            {"lbiblue": "#004a99", "lbimauve": "#b9aebb", "lbinavy": "#001242"},
        )

    def test_tint(self):
        # xcolor color!p = p*c + (1-p)*255 per channel, rounded half up (hand-computed)
        self.assertEqual(gen.tint("#004a99", 7), "#edf2f8")
        self.assertEqual(gen.tint("#b9aebb", 60), "#d5ced6")
        self.assertEqual(gen.tint("#b9aebb", 18), "#f2f0f3")
        self.assertEqual(gen.tint("#001242", 80), "#334168")


class TextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sans = gen.FontMetrics.from_otf(FONTS / "SourceSansPro-Regular.otf")
        cls.sans_bold = gen.FontMetrics.from_otf(FONTS / "SourceSansPro-Semibold.otf")
        cls.serif_bold = gen.FontMetrics.from_otf(FONTS / "SourceSerifPro-Semibold.otf")

    def test_text_width_matches_latex(self):
        # widths measured on the LaTeX A0 build with pdftotext -bbox (mm)
        for text, metrics, size_pt, latex_mm in [
            ("Abstract", self.serif_bold, 29.86, 40.19),
            ("Some", self.sans, 24.88, 20.99),
            ("netmed.lbg.ac.at", self.sans, 24.88, 62.13),
        ]:
            with self.subTest(text=text):
                width = gen.text_width(text, metrics, size_pt * PT)
                self.assertAlmostEqual(width, latex_mm, delta=0.03 * latex_mm)

    def test_wrap_lines(self):
        size = 24.88 * PT
        width = gen.text_width("lorem " * 5, self.sans, size) / 0.98 + 0.01
        lorem = [("lorem " * 20, "regular")]
        self.assertEqual(gen.wrap_lines([lorem], width, size, self.sans, self.sans_bold), 4)
        bullet = [("▴ ", "bullet"), ("x", "regular")]
        self.assertEqual(gen.wrap_lines([lorem, bullet], width, size, self.sans, self.sans_bold), 5)


class LogoTests(unittest.TestCase):
    def test_inline_logo(self):
        # width at height 90 = 90 * viewBox width / viewBox height (hand-computed)
        for name, width_at_90 in [("lbi-netmed", 237.05), ("univie", 288.97), ("vbc", 176.96), ("cemm", 163.30)]:
            with self.subTest(logo=name):
                group, width = gen.inline_logo(gen.REPO / "logos" / "svg" / f"{name}.svg", f"logo-{name}", 21.025, 21.025, 90)
                self.assertAlmostEqual(width, width_at_90, delta=0.01)
                tags = [el.tag for el in group.iter()]
                self.assertNotIn(SVG + "style", tags)
                self.assertNotIn(SVG + "image", tags)
                self.assertTrue(any(t in tags for t in (SVG + "path", SVG + "polygon", SVG + "rect", SVG + "circle")))
                self.assertFalse([el for el in group.iter() if "class" in el.attrib])
                self.assertTrue(all(el.get("id").startswith(f"logo-{name}") for el in group.iter() if el.get("id")))
                self.assertTrue(group.get("transform").startswith("translate(21.025,21.025)"))

    def test_inline_logo_applies_class_styles(self):
        group, _ = gen.inline_logo(gen.REPO / "logos" / "svg" / "lbi-netmed.svg", "logo-lbi", 0, 0, 90)
        fills = {m.lower() for el in group.iter() for m in re.findall(r"fill:\s*(#[0-9a-fA-F]{6})", el.get("style") or "")}
        self.assertTrue({"#004a99", "#b9aebb"} <= fills)


INK = "{http://www.inkscape.org/namespaces/inkscape}"
SODI = "{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}"
OSB = "{http://www.openswatchbook.org/uri/2009/osb}"


def parse(name):
    variant = next(v for v in gen.VARIANTS if v.name == name)
    return variant, ET.fromstring(gen.build_svg(variant))


def by_id(root, element_id):
    return next(el for el in root.iter() if el.get("id") == element_id)


def logo_box(group):
    """(left, top, right, bottom) of an inlined logo from its transform and its drawing box."""
    x, y, k, bx, by = map(float, re.match(
        r"translate\(([-\d.]+),([-\d.]+)\) scale\(([-\d.]+)\) translate\(([-\d.]+),([-\d.]+)\)", group.get("transform")).groups())
    name = group.get("id").removeprefix("logo-")
    _, _, bw, bh = gen.LOGO_BOXES["lbi-netmed" if name == "lbi" else name]
    return x, y, x + k * bw, y + k * bh


class TemplateTests(unittest.TestCase):
    def test_page_size(self):
        for name, width, height in [("a0-portrait", "841", "1189"), ("a0-landscape", "1189", "841"), ("a1-portrait", "594", "841")]:
            with self.subTest(variant=name):
                _, root = parse(name)
                self.assertEqual((root.get("width"), root.get("height")), (f"{width}mm", f"{height}mm"))
                self.assertEqual(root.get("viewBox"), f"0 0 {width} {height}")

    def test_guides(self):
        # sep = 0.025 W; columns at sep + i*(col+sep) .. + col (hand-computed)
        for name, xs in [
            ("a0-portrait", [21.025, 409.9875, 431.0125, 819.975]),
            ("a0-landscape", [29.725, 386.425, 416.15, 772.85, 802.575, 1159.275]),
            ("a1-portrait", [14.85, 289.575, 304.425, 579.15]),
        ]:
            with self.subTest(variant=name):
                _, root = parse(name)
                guides = [g for g in root.iter(SODI + "guide")]
                self.assertTrue(all(g.get("orientation") == "1,0" for g in guides))
                got = sorted(float(g.get("position").split(",")[0]) for g in guides)
                self.assertEqual(len(got), len(xs))
                for a, b in zip(got, xs):
                    self.assertAlmostEqual(a, b, delta=0.001)

    def test_layers(self):
        _, root = parse("a0-portrait")
        layers = [g for g in root if g.get(INK + "groupmode") == "layer"]
        self.assertEqual([g.get(INK + "label") for g in layers], ["Branding", "Header & footer text", "Content"])
        self.assertEqual([g.get(SODI + "insensitive") for g in layers], ["true", None, None])

    def test_swatches(self):
        _, root = parse("a0-portrait")
        swatches = [g for g in root.iter(SVG + "linearGradient") if g.get(INK + "swatch") == "solid"]
        self.assertTrue(all(g.get(OSB + "paint") == "solid" for g in swatches))
        colors = sorted(re.search(r"stop-color:(#[0-9a-f]{6})", g[0].get("style")).group(1) for g in swatches)
        self.assertEqual(colors, sorted(["#004a99", "#b9aebb", "#001242", "#edf2f8", "#d5ced6", "#f2f0f3"]))

    def test_no_images(self):
        for variant in gen.VARIANTS:
            with self.subTest(variant=variant.name):
                self.assertNotIn("<image", gen.build_svg(variant))

    def test_deterministic(self):
        for variant in gen.VARIANTS:
            with self.subTest(variant=variant.name):
                self.assertEqual(gen.build_svg(variant), gen.build_svg(variant))

    def test_header_geometry(self):
        _, root = parse("a0-portrait")
        left, top, right, bottom = logo_box(by_id(root, "logo-lbi"))
        self.assertAlmostEqual(left, 21.025, delta=0.001)
        self.assertAlmostEqual(top, 21.025, delta=0.001)
        self.assertAlmostEqual(bottom - top, 90, delta=0.01)
        self.assertAlmostEqual(float(by_id(root, "title").get("x")), 279.49, delta=0.1)  # LaTeX title start
        rule = by_id(root, "header-rule")
        self.assertAlmostEqual(float(rule.get("y")), 132.05, delta=0.01)
        self.assertAlmostEqual(float(rule.get("height")), 2.03, delta=0.001)

    def test_title_baseline_matches_latex(self):
        # LaTeX A0: title baseline 48.72 mm (bottom of "Dise" at 300 dpi, 49.02 incl. round-letter overshoot)
        _, root = parse("a0-portrait")
        self.assertAlmostEqual(float(by_id(root, "title").get("y")), 48.72, delta=0.35)

    def test_footer_geometry(self):
        _, root = parse("a0-portrait")
        self.assertAlmostEqual(float(by_id(root, "footer-rule").get("y")), 1125.05, delta=0.01)
        boxes = [logo_box(by_id(root, f"logo-{n}")) for n in ("univie", "vbc", "cemm")]
        self.assertAlmostEqual(boxes[-1][2], 819.975, delta=0.01)
        for box in boxes:
            self.assertAlmostEqual(box[3], 1176.19, delta=0.01)
        for a, b in zip(boxes, boxes[1:]):
            self.assertAlmostEqual(b[0] - a[2], 17.0, delta=0.01)

    def test_every_frame_inside_its_block_group(self):
        for variant in gen.VARIANTS:
            _, root = parse(variant.name)
            for block in (g for g in root.iter(SVG + "g") if (g.get("id") or "").startswith("block-")):
                frames = {el.get("id") for el in block.iter(SVG + "rect")}
                for text in block.iter(SVG + "text"):
                    target = re.search(r"shape-inside:url\(#([^)]+)\)", text.get("style") or "")
                    if target:
                        with self.subTest(variant=variant.name, text=text.get("id")):
                            self.assertIn(target.group(1), frames)

    def test_flowed_text_markup(self):
        # probe finding: paragraphs need pre-wrap newlines; sodipodi:role lines run together
        for variant in gen.VARIANTS:
            _, root = parse(variant.name)
            flowed = [t for t in root.iter(SVG + "text") if "shape-inside" in (t.get("style") or "")]
            self.assertGreater(len(flowed), 0)
            for text in flowed:
                self.assertIn("white-space:pre-wrap", text.get("style"))
                self.assertFalse([el for el in text.iter() if el.get(SODI + "role")])

    def test_columns_leave_room_above_footer(self):
        for variant in gen.VARIANTS:
            _, root = parse(variant.name)
            limit = float(by_id(root, "footer-rule").get("y")) - 30 * variant.scale
            for block in (g for g in root.iter(SVG + "g") if (g.get("id") or "").startswith("block-")):
                bottoms = [float(r.get("y")) + float(r.get("height")) for r in block.iter(SVG + "rect")]
                bottoms += [float(c.get("cy")) + float(c.get("r")) for c in block.iter(SVG + "circle")]
                bottoms += [float(t.get("y")) for t in block.iter(SVG + "text") if t.get("y")]
                with self.subTest(variant=variant.name, block=block.get("id")):
                    self.assertLessEqual(max(bottoms), limit)

    def test_last_column_has_plain_block(self):
        # a plain block's blue rule marks the last column's right edge for grid-check
        for variant in gen.VARIANTS:
            _, root = parse(variant.name)
            right = variant.width * (1 - 0.025)
            rules = [r for r in root.iter(SVG + "rect") if (r.get("id") or "").startswith("rule-")]
            with self.subTest(variant=variant.name):
                self.assertTrue(any(abs(float(r.get("x")) + float(r.get("width")) - right) < 0.01 for r in rules))

    def test_a1_scaled(self):
        _, a0 = parse("a0-portrait")
        _, a1 = parse("a1-portrait")
        size = lambda root: float(re.search(r"font-size:([\d.]+)px", by_id(root, "title").get("style")).group(1))
        ratio = 594 / 841
        self.assertAlmostEqual(size(a1), size(a0) * ratio, delta=0.002)
        self.assertAlmostEqual(float(by_id(a1, "header-rule").get("height")), 2.03 * ratio, delta=0.002)
        a0_logo, a1_logo = logo_box(by_id(a0, "logo-lbi")), logo_box(by_id(a1, "logo-lbi"))
        self.assertAlmostEqual(a1_logo[3] - a1_logo[1], (a0_logo[3] - a0_logo[1]) * ratio, delta=0.01)


if __name__ == "__main__":
    unittest.main()
