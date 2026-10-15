#!/usr/bin/env python3
"""Verified rebrand coverage gate. Read only; no production or file mutations.

Defaults to report-only for an in-progress feature branch.
    python3 tools/check_approved_rebrand.py --report /tmp/brand-gate.json
    python3 tools/check_approved_rebrand.py --strict --report /tmp/brand-gate.json

Counts tracked HTML, checks brand/CSS/old label, validates protected product
SKU+price and cart IDs against the default pre-rebrand Git baseline. Canonical,
product URLs, buyer paths, social handles, and old mail domains stay untouched
at this stage: changing them belongs to the later migration acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = "На стороне подрядчика"
BASE = "origin/main"
PROTECTED = re.compile(r'data-(?:sku|price)="[^"]*"|id="(?:cart-[^"]*|checkout-[^"]*)"', re.I)
LINKS = re.compile(r'(?:href|src)="[^"]*"', re.I)
LEGACY = re.compile(r'Маржа в бетоне|маржа в бетоне|Маржи в бетоне')
SKIP = {".git", "node_modules", ".claude", "data", "content"}
CSS_VERSION = hashlib.sha1((ROOT / "brand-approved-2026.css").read_bytes()).hexdigest()[:8]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True,
        check=True, timeout=15
    ).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    pages = []
    for name in git("ls-files", "--", "*.html").splitlines():
        path = Path(name)
        if set(path.parts) & SKIP:
            continue
        pages.append(path)

    results = []
    for path in pages:
        text = (ROOT / path).read_text(encoding="utf-8")
        problems = []
        correct_version = re.search(
            r'href="(?:\.\./|/)?brand-approved-2026\.css\?v='
            + CSS_VERSION + r'"', text
        )
        if not correct_version:
            problems.append("NO_APPROVED_CSS_OR_STALE_VERSION")
        if not re.search(r'<body[^>]*class="[^"]*\brebrand-approved\b[^"]*"', text, re.I):
            problems.append("NO_APPROVED_BODY_CLASS")
        if LEGACY.search(text):
            problems.append("OLD_BRAND_DISPLAY")
        # Payment result pages have a standalone brand link, not the
        # canonical site-wide navigation header. Keep both contracts strict.
        if 'class="brand"' in text:
            short_brand = bool(
                re.search(r'<span\s+class="brand-mark">Н</span>', text)
                and '<span>на стороне подрядчика</span>' in text
            )
            if path.as_posix() in {"success.html", "fail.html"}:
                if not short_brand:
                    problems.append("RESULT_BRAND_MISMATCH")
            elif not (
                short_brand
                and 'aria-label="На стороне подрядчика, на главную"' in text
            ):
                problems.append("HEADER_BRAND_MISMATCH")
        if not re.search(r'<title[^>]*>.*?</title>', text, re.I | re.S):
            problems.append("TITLE_MISSING")
        rel = path.as_posix()
        try:
            base = git("show", f"{BASE}:{rel}")
        except subprocess.CalledProcessError:
            problems.append("BASELINE_MISSING")
        else:
            if PROTECTED.findall(base) != PROTECTED.findall(text):
                problems.append("BUYER_PRODUCT_IDENTIFIERS_CHANGED")
            old_links = LINKS.findall(base)
            new_links = LINKS.findall(text)
            css_regex = re.compile(
                r'href="(?:\.\./|/)?brand-approved-2026\.css\?v=[0-9a-f]{8}"'
            )
            new_links = [link for link in new_links if not css_regex.fullmatch(link)]
            if old_links != new_links:
                problems.append("LINK_OR_ASSET_CHANGED_BEFORE_MIGRATION")
        results.append({"path":rel, "problems":problems})

    nav = (ROOT / "data/site/navigation.yaml").read_text(encoding="utf-8")
    rss = (ROOT / "tools/build_rss.py").read_text(encoding="utf-8")
    sources = {
        "navigation_brand": (
            "  text: на стороне подрядчика" in nav
            and "  mark: Н" in nav
            and "  aria: На стороне подрядчика, на главную" in nav
        ),
        "rss_channel_title": 'CHANNEL_TITLE = "На стороне подрядчика"' in rss,
    }
    codes = Counter(code for item in results for code in item["problems"])
    report = {
        "gate": "APPROVED_BRAND_COVERAGE_R1_ONLY",
        "total": len(results),
        "complete": sum(not item["problems"] for item in results),
        "pending": sum(bool(item["problems"]) for item in results),
        "source_gates": sources,
        "errors_by_class": dict(codes),
        "problems": [row for row in results if row["problems"]],
        "pass": bool(results) and not codes and all(sources.values()),
        "scope_exclusions": [
            "No actual backend payment/webhook/old-buyer functionality was tested",
            "Canonical/DNS/social handles remain on old domain until migration gate",
            "CSS rendering across all pages requires separate browser regression"
        ]
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({key:report[key] for key in (
        "gate","total","complete","pending","source_gates","errors_by_class","pass"
    )},ensure_ascii=False,indent=2))
    for row in report["problems"][:20]:
        print(row["path"],":",",".join(row["problems"]))
    if args.strict and not report["pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
