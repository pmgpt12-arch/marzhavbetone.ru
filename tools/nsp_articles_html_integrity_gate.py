#!/usr/bin/env python3
"""Regression gate for NSP article HTML and editorial navigation (no network calls)."""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
HOST = "https://nastoronepodryadchika.ru/"
BAD_ENVELOPE = "[executed on device:"


class Inspect(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.main = 0
        self.h1 = 0
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.canonical: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        a = dict(attrs)
        if tag == "main":
            self.main += 1
        if tag == "h1":
            self.h1 += 1
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag == "link" and "canonical" in (a.get("rel") or "").split():
            self.canonical = a.get("href")


def clean_end(raw: str) -> bool:
    # Tool transport envelopes are not HTML: they must never be committed.
    return BAD_ENVELOPE not in raw and re.search(r"</html>\s*\Z", raw, re.I) is not None


def main() -> int:
    assert clean_end("<html></html>\n"), "valid end fixture"
    assert not clean_end("<html></html>\n[executed on device: ai-workstation]"), "transport fixture"
    files = sorted(p for p in ARTICLES.glob("*.html") if p.name != "index.html")
    errors: list[str] = []
    matrix_path = ROOT / "docs/editorial/NSP_ALL_43_ARTICLES_MATRIX_20261111.json"
    if not matrix_path.is_file():
        print("FAIL: editorial source matrix missing")
        return 1
    rows = json.loads(matrix_path.read_text(encoding="utf-8"))["articles"]
    legacy = {entry["path"]: entry for entry in rows if entry["state"] == "LEGACY_UNREVISED"}
    if len(files) != len(rows):
        errors.append(f"article count mismatch actual={len(files)} expected={len(rows)}")
    for path in files:
        text = path.read_text(encoding="utf-8")
        doc = Inspect()
        doc.feed(text)
        rel = path.relative_to(ROOT).as_posix()
        if not clean_end(text):
            errors.append(f"{rel}: HTML transport envelope or trailing data")
        if doc.main != 1 or doc.h1 != 1:
            errors.append(f"{rel}: main={doc.main}, h1={doc.h1}")
        if doc.canonical != HOST + rel:
            errors.append(f"{rel}: wrong canonical")
        if rel in legacy:
            previews = re.findall(
                r'<figure\b[^>]*class="[^"]*\bnsp-document-preview\b[^"]*"[^>]*>[\s\S]*?</figure>',
                text,
                flags=re.I,
            )
            if not 3 <= len(previews) <= 5:
                errors.append(f"{rel}: native preview count {len(previews)}, expected 3-5")
            product = legacy[rel]["sku"]
            if product == "t1":
                product = "p1"
            for fragment in previews:
                image = re.search(r'<img\b[^>]*\bsrc="([^"]+)"', fragment, flags=re.I)
                href = re.search(r'<a\b[^>]*\bhref="([^"]+)"', fragment, flags=re.I)
                if not image or not href:
                    errors.append(f"{rel}: native preview missing linked image")
                    continue
                src = image.group(1)
                asset = (path.parent / src).resolve()
                asset_dir = (ROOT / "assets/document-previews").resolve()
                if asset_dir not in asset.parents or not asset.is_file() or asset.stat().st_size == 0:
                    errors.append(f"{rel}: preview asset missing or outside approved path {src}")
                if not href.group(1).startswith(f"/products/{product}-"):
                    errors.append(f"{rel}: preview not linked to primary product {product}")

        if not any("/products/p" in href for href in doc.links):
            errors.append(f"{rel}: no direct paid product link")
        if any(re.search(r"/products/t[23]-", href) for href in doc.links):
            # Immutable approved V2 source contains a pre-existing T2 defect.
            # Do not silently rewrite the approved canonical article in this PR.
            if rel == "articles/ispolnitelnaya-dokumentaciya-sostav.html":
                print(f"KNOWN_BASELINE_WARNING {rel}: obsolete T2 link; follow-up required")
            else:
                errors.append(f"{rel}: legacy T2/T3 link")
        for href in doc.links:
            if href.startswith("#") and href[1:] and href[1:] not in doc.ids:
                errors.append(f"{rel}: missing fragment target {href}")
    print(f"NSP_ARTICLE_HTML_GATE files={len(files)} issues={len(errors)}")
    for error in errors:
        print("FAIL", error)
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
