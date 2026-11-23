#!/usr/bin/env python3
"""Verificador offline de contenido y recursos del README de perfil."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r'(!?)\[([^\]]*)\]\(([^\s)]+)(?:\s+"[^"]*")?\)')
MAX_README_BYTES = 12_288
MAX_IMAGES = 20
MAX_EXTERNAL_BADGES = 14
SVG_BAD_TAG = re.compile(r"<\s*(?:animate|animateTransform|animateMotion|set|script|foreignObject)\b", re.I)
SVG_REMOTE_REF = re.compile(r"(?:href|src)\s*=\s*['\"](?:https?:|//|data:)", re.I)
SVG_EVENT = re.compile(r"\bon[a-z]+\s*=", re.I)
SVG_CSS_REMOTE = re.compile(r"(?:@import|url\s*\(\s*['\"]?(?:https?:|//|data:))", re.I)


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


def allowed_badge(target: str) -> bool:
    """Solo imágenes de insignias SVG de Shields, por HTTPS y sin puertos."""
    parts = urlsplit(target)
    return (
        parts.scheme == "https"
        and parts.hostname == "img.shields.io"
        and parts.port is None
        and parts.username is None
        and parts.password is None
        and parts.path.startswith("/badge/")
        and not parts.path.lower().endswith(".gif")
    )


def validate_readme(content: str, root: Path) -> list[str]:
    """Audita calidad del perfil sin conectarse a Internet."""
    errors: list[str] = []
    if len(content.encode("utf-8")) > MAX_README_BYTES:
        errors.append(f"README supera {MAX_README_BYTES} bytes")
    if not re.search(r"(?m)^#\s+\S|<h1(?:\s|>)", content, re.I):
        errors.append("Falta un título H1 Markdown o HTML")

    links = [(bool(m.group(1)), m.group(2), m.group(3)) for m in MARKDOWN_LINK.finditer(content)]
    parser = HtmlLinks()
    parser.feed(content)
    links.extend(parser.links)

    image_count = 0
    remote_badges = 0
    for is_image, label, target in links:
        if not target:
            errors.append("Enlace sin destino")
            continue

        parts = urlsplit(target.strip("<>"))
        if is_image:
            image_count += 1
            if not label.strip():
                errors.append(f"Imagen sin texto alternativo: {target}")
            if parts.path.lower().endswith(".gif"):
                errors.append(f"Imagen GIF no permitida: {target}")
            if parts.scheme or parts.netloc:
                if allowed_badge(target):
                    remote_badges += 1
                else:
                    errors.append(f"Imagen externa no permitida: {target}")

        if parts.scheme in ("https", "mailto") and not (is_image and not allowed_badge(target)):
            continue
        if parts.scheme or parts.netloc:
            errors.append(f"Esquema de URL no permitido: {target}")
            continue
        if target.startswith("#"):
            continue

        path = unquote(parts.path)
        if not path:
            continue
        destination = (root / path).resolve()
        if not destination.is_relative_to(root.resolve()) or not destination.is_file():
            errors.append(f"Archivo local no encontrado o fuera del repositorio: {target}")

    if image_count > MAX_IMAGES:
        errors.append(f"Demasiadas imágenes: {image_count} (máximo {MAX_IMAGES})")
    if remote_badges > MAX_EXTERNAL_BADGES:
        errors.append(f"Demasiados badges externos: {remote_badges} (máximo {MAX_EXTERNAL_BADGES})")

    assets = root / "assets"
    for svg in assets.rglob("*.svg") if assets.is_dir() else []:
        data = svg.read_text(encoding="utf-8")
        path = svg.relative_to(root)
        try:
            doc = ET.fromstring(data)
            if doc.tag != "{http://www.w3.org/2000/svg}svg":
                errors.append(f"No es un SVG válido: {path}")
        except ET.ParseError:
            errors.append(f"SVG XML inválido: {path}")
        if SVG_BAD_TAG.search(data):
            errors.append(f"SVG con contenido activo/animado: {path}")
        if SVG_REMOTE_REF.search(data) or SVG_CSS_REMOTE.search(data):
            errors.append(f"SVG con recursos remotos: {path}")
        if SVG_EVENT.search(data):
            errors.append(f"SVG con manejadores de eventos: {path}")

    return errors


def main() -> int:
    file = ROOT / "README.md"
    if not file.is_file():
        print("ERROR: no existe README.md", file=sys.stderr)
        return 1
    errors = validate_readme(file.read_text(encoding="utf-8"), ROOT)
    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1
    print("OK: presentación, enlaces locales, badges permitidos y SVG seguros")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
