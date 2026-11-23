"""Pruebas de regresión para el control del perfil."""

import tempfile
import unittest
from pathlib import Path

from scripts.check_profile import validate_readme


class ProfileValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        assets = self.root / "assets"
        assets.mkdir()
        (assets / "banner.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")

    def check_error(self, content: str, expected: str) -> None:
        errors = validate_readme(content, self.root)
        self.assertTrue(any(expected in error for error in errors), errors)

    def test_permite_documento_valido(self) -> None:
        content = "# Perfil\n![Banner accesible](assets/banner.svg)\n[GitHub](https://github.com)\n"
        self.assertEqual(validate_readme(content, self.root), [])

    def test_exige_alternativa_textual(self) -> None:
        self.check_error("# Perfil\n![](assets/banner.svg)", "sin texto alternativo")

    def test_rechaza_imagenes_externas(self) -> None:
        self.check_error("# Perfil\n![Badge](https://img.shields.io/badge/X-Y-Z)", "Imagen externa")

    def test_rechaza_gif(self) -> None:
        (self.root / "assets" / "anim.gif").write_bytes(b"GIF89a")
        self.check_error("# Perfil\n![GIF](assets/anim.gif)", "GIF no permitida")

    def test_detecta_archivos_ausentes(self) -> None:
        self.check_error("# Perfil\n![Banner](assets/ausente.svg)", "no encontrado")

    def test_rechaza_url_insegura(self) -> None:
        self.check_error("# Perfil\n[Enlace](http://example.com)", "Esquema de URL")

    def test_detecta_svg_animado(self) -> None:
        (self.root / "assets" / "banner.svg").write_text("<svg><animate attributeName='x'/></svg>", encoding="utf-8")
        self.check_error("# Perfil\n![Banner](assets/banner.svg)", "activo/animado")

    def test_exige_h1(self) -> None:
        self.check_error("## Solo subtítulo", "título H1")


if __name__ == "__main__":
    unittest.main()
