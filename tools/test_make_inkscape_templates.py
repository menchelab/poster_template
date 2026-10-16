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


if __name__ == "__main__":
    unittest.main()
