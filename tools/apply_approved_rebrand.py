#!/usr/bin/env python3
"""Apply approved public brand/UI only. Does NOT migrate URLs, payment, accounts or SEO.

    python3 tools/apply_approved_rebrand.py          # inspect, no writes
    python3 tools/apply_approved_rebrand.py --write  # rewrite public HTML and generators
    python3 tools/apply_approved_rebrand.py --check  # exit non-zero if incomplete

Scope: tracked HTML pages, source for navigation, and RSS channel label. Historical
order files, product artifacts, payment code, personal-data records and provider
handles are NOT targets. Re-runs must be idempotent.
"""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD_NAME = "Маржа в бетоне"
NEW_NAME = "На стороне подрядчика"
NEW_CSS = "brand-approved-2026.css?v=1"
SKIP_FOLDERS = {".git", "node_modules", "content", "data", ".claude"}
CSS_LINK = re.compile(r'<link\b[^>]*\brel=["\']stylesheet["\'][^>]*>', re.I)
BODY = re.compile(r'<body(\s[^>]*)?>', re.I)


def tracked_html() -> list[Path]:
    cmd = subprocess.run(
        ["git", "ls-files", "--", "*.html"], cwd=ROOT,
        check=True, capture_output=True, text=True, timeout=15
    )
    pages = []
    for rel in cmd.stdout.splitlines():
        p = Path(rel)
        if set(p.parts) & SKIP_FOLDERS:
            continue
        if (ROOT / p).is_file():
            pages.append(p)
    return pages


def transform_html(text: str, relative: Path) -> str:
    """Only site-identifying strings and approved CSS. No URL substitutions."""
    text = text.replace("Маржи в бетоне", NEW_NAME)
    text = text.replace(OLD_NAME, NEW_NAME).replace("маржа в бетоне", "на стороне подрядчика")
    text = re.sub(
        r'(<span\s+class="brand-mark">)М(</span>)',
        r'\g<1>Н\g<2>', text
    )
    body = BODY.search(text)
    if not body:
        raise ValueError(f"{relative}: HTML body is missing")
    if "rebrand-approved" not in body.group(0):
        if body.group(0) != "<body>":
            raise ValueError(f"{relative}: unexpected body tag: {body.group(0)}")
        text = text[:body.start()] + '<body class="rebrand-approved">' + text[body.end():]
    if NEW_CSS in text:
        if text.count(NEW_CSS) != 1:
            raise ValueError(f"{relative}: repeated brand CSS references")
        return text

    head_close = text.lower().find("</head>")
    if head_close < 0:
        raise ValueError(f"{relative}: head not closed")
    matches = list(CSS_LINK.finditer(text[:head_close]))
    if not matches:
        raise ValueError(f"{relative}: no existing CSS to append after")
    prefix = "../" if len(relative.parts) > 1 else ""
    link = f'\n  <link rel="stylesheet" href="{prefix}{NEW_CSS}">'
    pos = matches[-1].end()
    return text[:pos] + link + text[pos:]


def transform_navigation(text: str) -> str:
    edits = {
        "  text: маржа в бетоне": "  text: на стороне подрядчика",
        "  mark: М": "  mark: Н",
        "  aria: Маржа в бетоне, на главную":
            "  aria: На стороне подрядчика, на главную",
    }
    for old, new in edits.items():
        if old in text:
            if text.count(old) != 1:
                raise ValueError(f"navigation: multiple occurrences of {old}")
            text = text.replace(old, new)
        elif new not in text:
            raise ValueError(f"navigation: neither old nor new entry for {old}")
    return text


def transform_rss_builder(text: str) -> str:
    old = 'CHANNEL_TITLE = "Маржа в бетоне"'
    new = 'CHANNEL_TITLE = "На стороне подрядчика"'
    if old in text:
        if text.count(old) != 1:
            raise ValueError("build_rss: multiple old channel titles")
        return text.replace(old, new)
    if new not in text:
        raise ValueError("build_rss: title source is unknown")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--write", action="store_true")
    selection.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not (ROOT / "brand-approved-2026.css").is_file():
        raise ValueError("Approved CSS is missing")
    updates: list[tuple[Path, str]] = []
    pages = tracked_html()
    if not pages:
        raise ValueError("No tracked HTML pages in repository")
    for p in pages:
        original = (ROOT / p).read_text(encoding="utf-8")
        changed = transform_html(original, p)
        if changed != original:
            updates.append((p, changed))
    special = {
        Path("data/site/navigation.yaml"): transform_navigation,
        Path("tools/build_rss.py"): transform_rss_builder,
    }
    for p, change in special.items():
        before = (ROOT / p).read_text(encoding="utf-8")
        after = change(before)
        if after != before:
            updates.append((p, after))
    print(f"Total tracked HTML: {len(pages)}; pending changes: {len(updates)}")
    for p, _ in updates:
        print(p.as_posix())
    if args.check:
        return 1 if updates else 0
    if args.write:
        for p, changed in updates:
            (ROOT / p).write_text(changed, encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"BRAND_GATE_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2)
