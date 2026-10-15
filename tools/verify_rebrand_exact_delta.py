#!/usr/bin/env python3
"""Independent, fail-closed exact delta gate for the 2026-10 site rebrand.

The historical accepted snapshot (2026-10-12) stays unchanged. This verifies
that all 88 current public HTML documents differ from the pinned pre-rebrand
source ONLY by the approved brand-label replacements, wordmark initial,
scoped body class and fingerprinted stylesheet. All other bytes including
prices, SKU, legal provisions, links, canonical URLs, scripts and order
metadata remain unchanged.

    python3 tools/verify_rebrand_exact_delta.py --check
    python3 tools/verify_rebrand_exact_delta.py --check --report /tmp/proof.json

Does not claim live rendering, payment or release acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_SHA = "32cb4ee8627c12d067a0db962fdab9adf49f3ade"
EXCLUDED_DIRS = {".git", ".claude", "content", "data", "tools", "node_modules"}
LINK = re.compile(r'<link\s+rel="stylesheet"[^>]*>', re.IGNORECASE)
MARK = re.compile(r'(<span\s+class="brand-mark">)М(</span>)')
CSS_NAME = "brand-approved-2026.css"


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True,
                            capture_output=True, timeout=15, check=True)
    return result.stdout


def expected_rebrand(original: str, name: str, css_version: str, absolute: bool = False) -> str:
    """Compute approved delta using a separate algorithm from the converter."""
    text = original
    for before, after in (
        ("Маржи в бетоне", "На стороне подрядчика"),
        ("Маржа в бетоне", "На стороне подрядчика"),
        ("маржа в бетоне", "на стороне подрядчика"),
    ):
        text = text.replace(before, after)
    text = MARK.sub(r"\g<1>Н\g<2>", text)
    if "<body>" not in text:
        raise ValueError(f"{name}: expected single unmodified body marker")
    if text.count("<body>") != 1:
        raise ValueError(f"{name}: duplicated body")
    text = text.replace("<body>", '<body class="rebrand-approved">', 1)
    close = text.lower().find("</head>")
    if close < 0:
        raise ValueError(f"{name}: missing head")
    links = list(LINK.finditer(text[:close]))
    if not links:
        raise ValueError(f"{name}: no existing stylesheet")
    prefix = "/" if absolute else ("../" if "/" in name else "")
    tag = f'\n  <link rel="stylesheet" href="{prefix}{CSS_NAME}?v={css_version}">'
    after = links[-1].end()
    return text[:after] + tag + text[after:]


def inspect() -> dict:
    files = []
    for rel in git("ls-files", "--", "*.html").splitlines():
        path = Path(rel)
        if set(path.parts) & EXCLUDED_DIRS:
            continue
        files.append(rel)
    version = hashlib.sha1((ROOT / CSS_NAME).read_bytes()).hexdigest()[:8]
    results = []
    for name in files:
        original = git("show", f"{BASE_SHA}:{name}")
        actual = (ROOT / name).read_text("utf-8")
        accepted = expected_rebrand(original, name, version)
        mode = "relative"
        if actual != accepted and "/" not in name:
            alternate = expected_rebrand(original, name, version, absolute=True)
            if actual == alternate:
                mode = "root_absolute"
                accepted = alternate
        match = actual == accepted
        results.append({
            "path": name,
            "match": match,
            "css_ref_mode": mode if match else "mismatch",
            "original_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
            "new_sha256": hashlib.sha256(actual.encode("utf-8")).hexdigest(),
            "failure_class": "" if match else "UNAPPROVED_HTML_DELTA",
        })
    mismatches = [row["path"] for row in results if not row["match"]]
    return {
        "gate": "REBRAND_EXACT_TRANSFORMATION_V1",
        "historical_baseline_sha": BASE_SHA,
        "current_commit": git("rev-parse", "HEAD").strip(),
        "css_version": version,
        "scope": "source-controlled public HTML (not backend)",
        "checked": len(files),
        "matches": len(files) - len(mismatches),
        "mismatches": mismatches,
        "pages": results,
        "pass": len(files) == 88 and not mismatches,
        "limitations": [
            "This permits only approved label/CSS changes; source snapshots remain historical",
            "Not a payment, buyer access, DNS, live browser or SEO migration gate",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    result = inspect()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({key: result[key] for key in
          ("gate", "historical_baseline_sha", "current_commit",
           "css_version", "checked", "matches", "mismatches", "pass")}, ensure_ascii=False))
    return 1 if args.check and not result["pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
