"""Tests para la identidad visual: un nombre visible y degradado luminoso accesible."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SVG = "{http://www.w3.org/2000/svg}"


class NeonBrandTests(unittest.TestCase):
    def test_nombre_principal_unico_en_readme(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("<h1>"), 1)
        self.assertEqual(text.count('alt="Latan Villegas"'), 1)
        self.assertIn('srcset="assets/name-gradient-dark.svg"', text)
        self.assertNotIn("Hola, soy", text)

    def test_banners_sin_nombre_repetido(self) -> None:
        for filename in ("banner.svg", "banner-dark.svg"):
            with self.subTest(file=filename):
                root = ET.parse(ROOT / "assets" / filename).getroot()
                displayed = [(element.text or "") for element in root.iter(f"{SVG}text")]
                self.assertNotIn("Latan Villegas", displayed)
                self.assertIn("BUILD · SHIP · EVOLVE", displayed)

    def test_degradado_multicolor_7_tonos(self) -> None:
        for filename in ("name-gradient.svg", "name-gradient-dark.svg"):
            with self.subTest(file=filename):
                root = ET.parse(ROOT / "assets" / filename).getroot()
                gradients = [
                    element for element in root.iter(f"{SVG}linearGradient")
                    if element.get("id") == "spectrum"
                ]
                self.assertEqual(len(gradients), 1)
                stops = gradients[0].findall(f"{SVG}stop")
                self.assertGreaterEqual(len(stops), 7)
                self.assertEqual(len({stop.get("stop-color") for stop in stops}), len(stops))

    def test_efecto_sin_scripts_y_movimiento_reducido(self) -> None:
        for filename in ("name-gradient.svg", "name-gradient-dark.svg"):
            with self.subTest(file=filename):
                svg = (ROOT / "assets" / filename).read_text(encoding="utf-8")
                self.assertIn("prefers-reduced-motion: reduce", svg)
                self.assertIn("@keyframes sweep", svg)
                self.assertIn('filter="url(#halo)"', svg)
                self.assertNotIn("<script", svg)
                self.assertNotIn("<animate", svg)


if __name__ == "__main__":
    unittest.main()
