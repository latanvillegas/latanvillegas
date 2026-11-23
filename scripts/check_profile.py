#!/usr/bin/env python3
"""Validación offline y sin dependencias del perfil público GitHub."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r'(!?)\[([^\]]*)\]\(([^\s)]+)(?:\s+"[^"]*")?\)')
MAX_README_BYTES = 8_192
MAX_IMAGES = 3


class HtmlLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[bool, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "img":
            self.links.append((True, values.get("alt") or "", values.get("src") or ""))
        elif tag == "a":
            self.links.append((False, "", values.get("href") or ""))


def validate_readme(content: str, root: Path) -> list[str]:
    """Devuelve todos los problemas detectados sin realizar solicitudes HTTP."""
    errors: list[str] = []
    if len(content.encode("utf-8")) > MAX_README_BYTES:
        errors.append(f"README supera {MAX_README_BYTES} bytes")
    if not re.search(r"(?m)^#\s+\S", content):
        errors.append("Falta un título H1 Markdown")

    links = [(bool(m.group(1)), m.group(2), m.group(3)) for m in MARKDOWN_LINK.finditer(content)]
    parser = HtmlLinks()
    parser.feed(content)
    links.extend(parser.links)

    images = 0
    for is_image, label, target in links:
        if not target:
            errors.append("Enlace sin destino")
            continue
        parsed = urlsplit(target.strip("<>"))
        if is_image:
            images += 1
            if not label.strip():
                errors.append(f"Imagen sin texto alternativo: {target}")
            if parsed.scheme or parsed.netloc:
                errors.append(f"Imagen externa no permitida: {target}")
            if parsed.path.lower().endswith(".gif"):
                errors.append(f"Imagen GIF no permitida: {target}")

        if parsed.scheme in ("https", "mailto"):
            continue
        if parsed.scheme or parsed.netloc:
            errors.append(f"Esquema de URL no permitido: {target}")
            continue
        if target.startswith("#"):
            continue
        path = unquote(parsed.path)
        if not path:
            continue
        destination = (root / path).resolve()
        if not destination.is_relative_to(root.resolve()) or not destination.is_file():
            errors.append(f"Archivo local no encontrado o fuera del repositorio: {target}")

    if images > MAX_IMAGES:
        errors.append(f"Demasiadas imágenes: {images} (máximo {MAX_IMAGES})")

    for svg in (root / "assets").rglob("*.svg") if (root / "assets").exists() else []:
        data = svg.read_text(encoding="utf-8")
        if re.search(r"<(?:animate|animateTransform|animateMotion|set|script|foreignObject)\b", data, re.I):
            errors.append(f"SVG con contenido activo/animado: {svg.relative_to(root)}")
        if re.search(r"(?:href|src)\s*=\s*['\"]https?://", data, re.I):
            errors.append(f"SVG con recursos remotos: {svg.relative_to(root)}")

    return errors


def main() -> int:
    readme = ROOT / "README.md"
    if not readme.is_file():
        print("ERROR: no existe README.md", file=sys.stderr)
        return 1
    errors = validate_readme(readme.read_text(encoding="utf-8"), ROOT)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK: perfil validado (Markdown, enlaces locales, imágenes y SVG)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
