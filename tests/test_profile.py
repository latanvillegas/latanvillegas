"""Pruebas de regresión del perfil visual (solo biblioteca estándar)."""

import tempfile
import unittest
from pathlib import Path

from scripts.check_profile import MAX_EXTERNAL_BADGES, validate_readme


class ProfileValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "assets").mkdir()
        self.write_svg('<svg xmlns="http://www.w3.org/2000/svg"/>')

    def write_svg(self, text: str) -> None:
        (self.root / "assets" / "banner.svg").write_text(text, encoding="utf-8")

    def check_error(self, content: str, expected: str) -> None:
        errors = validate_readme(content, self.root)
        self.assertTrue(any(expected in error for error in errors), errors)

    def test_documento_visual_valido(self) -> None:
        content = (
            '<h1 align="center">Perfil</h1>\n'
            '<img alt="Portada" src="assets/banner.svg">\n'
            '<img alt="Kotlin" src="https://img.shields.io/badge/Kotlin-blue">\n'
            '<a href="https://github.com">GitHub</a>\n'
        )
        self.assertEqual(validate_readme(content, self.root), [])

    def test_encabezado_markdown_valido(self) -> None:
        self.assertEqual(validate_readme("# Perfil\n", self.root), [])

    def test_exige_h1(self) -> None:
        self.check_error("## Perfil", "título H1")

    def test_rechaza_imagen_sin_alt(self) -> None:
        self.check_error('# Perfil\n<img src="assets/banner.svg">', "sin texto alternativo")

    def test_rechaza_imagen_externa(self) -> None:
        self.check_error("# Perfil\n![Foto](https://other.example/img.svg)", "Imagen externa")

    def test_rechaza_impostor_shields(self) -> None:
        self.check_error("# Perfil\n![Badge](https://img.shields.io.evil.test/badge/X-Y)", "Imagen externa")

    def test_rechaza_imagen_shields_sin_ruta_badge(self) -> None:
        self.check_error("# Perfil\n![Badge](https://img.shields.io/github/stars/x/y)", "Imagen externa")

    def test_rechaza_imagen_http(self) -> None:
        self.check_error("# Perfil\n![Badge](http://img.shields.io/badge/X-Y)", "Imagen externa")

    def test_rechaza_gif(self) -> None:
        (self.root / "assets" / "anim.gif").write_bytes(b"GIF89a")
        self.check_error("# Perfil\n![Animado](assets/anim.gif)", "GIF no permitida")

    def test_detecta_archivo_ausente(self) -> None:
        self.check_error("# Perfil\n![Banner](assets/falta.svg)", "no encontrado")

    def test_rechaza_enlace_inseguro(self) -> None:
        self.check_error("# Perfil\n[HTTP](http://example.com)", "Esquema de URL")

    def test_limita_badges(self) -> None:
        badges = "\n".join(
            f"![Badge](https://img.shields.io/badge/B-{n})"
            for n in range(MAX_EXTERNAL_BADGES + 1)
        )
        self.check_error("# Perfil\n" + badges, "Demasiados badges externos")

    def test_limita_tamano(self) -> None:
        self.check_error("# Perfil\n" + "x" * 13_000, "README supera")

    def test_detecta_svg_animado(self) -> None:
        self.write_svg('<svg xmlns="http://www.w3.org/2000/svg"><animate attributeName="x"/></svg>')
        self.check_error("# Perfil\n![Banner](assets/banner.svg)", "activo/animado")

    def test_detecta_svg_remoto(self) -> None:
        self.write_svg('<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/x.svg"/></svg>')
        self.check_error("# Perfil\n![Banner](assets/banner.svg)", "recursos remotos")

    def test_detecta_svg_malformado(self) -> None:
        self.write_svg('<svg xmlns="http://www.w3.org/2000/svg">')
        self.check_error("# Perfil\n![Banner](assets/banner.svg)", "XML inválido")

    def test_detecta_svg_con_eventos(self) -> None:
        self.write_svg('<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>')
        self.check_error("# Perfil\n![Banner](assets/banner.svg)", "manejadores de eventos")

    def test_admite_captura_real_versionada(self) -> None:
        url = (
            "https://raw.githubusercontent.com/latanvillegas/Radio-Escucha/"
            + "a" * 40
            + "/fastlane/metadata/android/es-ES/images/phoneScreenshots/1.jpg"
        )
        self.assertEqual(validate_readme("# Perfil\n![Pantalla](" + url + ")", self.root), [])

    def test_rechaza_captura_sin_pin(self) -> None:
        url = (
            "https://raw.githubusercontent.com/latanvillegas/Radio-Escucha/"
            "main/fastlane/metadata/android/es-ES/images/phoneScreenshots/1.jpg"
        )
        self.check_error("# Perfil\n![Pantalla](" + url + ")", "Imagen externa")

    def test_rechaza_otra_ruta_raw(self) -> None:
        url = (
            "https://raw.githubusercontent.com/latanvillegas/Radio-Escucha/"
            + "a" * 40 + "/malware.png"
        )
        self.check_error("# Perfil\n![Imagen](" + url + ")", "Imagen externa")

    def test_admite_picture_local(self) -> None:
        self.assertEqual(
            validate_readme(
                '<h1>Perfil</h1><picture><source media="(prefers-color-scheme: dark)" '
                'srcset="assets/banner.svg"><img src="assets/banner.svg" '
                'alt="Portada"></picture>',
                self.root,
            ),
            [],
        )

    def test_rechaza_picture_remoto(self) -> None:
        self.check_error(
            '<h1>Perfil</h1><picture><source srcset="https://example.org/x.svg">'
            '<img src="assets/banner.svg" alt="Banner"></picture>',
            "Fuente picture externa",
        )

    def test_rechaza_picture_faltante(self) -> None:
        self.check_error(
            '<h1>Perfil</h1><picture><source srcset="assets/no-existe.svg">'
            '<img src="assets/banner.svg" alt="Banner"></picture>',
            "Fuente picture local no encontrada",
        )


if __name__ == "__main__":
    unittest.main()
