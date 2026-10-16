#!/usr/bin/env python3
"""Read-only public HTML rebrand inventory. Never rewrites a site document."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from collections import Counter

PUBLIC_ROOT_FILES = {
    "404.html", "contacts.html", "diagnostika.html", "fail.html",
    "index.html", "kalkulyator.html", "katalog.html", "offer.html",
    "payment-delivery.html", "privacy.html", "refund.html", "success.html"
}
PUBLIC_DIRS = {"products", "articles", "materialy", "demo"}
APPROVED_NAME = "на стороне подрядчика"
OLD_NAME = "маржа в бетоне"
APPROVED_STYLE = "brand-approved-2026.css"

def inspect(root: Path) -> dict:
    rows = []
    for page in sorted(root.rglob("*.html")):
        relative = page.relative_to(root).as_posix()
        first = relative.split("/")[0]
        if relative not in PUBLIC_ROOT_FILES and first not in PUBLIC_DIRS:
            continue
        content = page.read_text("utf-8")
        body = re.search(r"<body\b([^>]*)>", content, re.I | re.S)
        header = re.search(r"<header\b[^>]*>(.*?)</header>", content, re.I | re.S)
        title = re.search(r"<title>(.*?)</title>", content, re.I | re.S)
        canonical = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"',content,re.I)
        body_text = body.group(1) if body else ""
        old_count = len(re.findall(OLD_NAME,content,re.I))
        new_count = len(re.findall(APPROVED_NAME,content,re.I))
        style = APPROVED_STYLE in content
        scoped = bool(re.search(r'\bclass="[^"]*\brebrand-approved\b[^"]*"',body_text))
        expected_brand = bool(header and re.search(r'>\s*на стороне подрядчика\s*</span>',header.group(0),re.I))
        rows.append({
          "path":relative,"section":first if "/" in relative else "root",
          "has_html_body":bool(body),"old_brand_occurrences":old_count,
          "approved_brand_occurrences":new_count,
          "scoped_approved_css":scoped and style,
          "header_approved":expected_brand if header else None,
          "title_old_brand":bool(title and OLD_NAME in title.group(1).lower()),
          "canonical_old_host":bool(canonical and "marzhavbetone.ru" in canonical.group(1)),
          "has_public_canonical":bool(canonical)
        })
    counters=Counter(r["section"] for r in rows)
    return {
      "schema_version":1,
      "mode":"READ_ONLY_INVENTORY",
      "public_html_count":len(rows),
      "sections":dict(sorted(counters.items())),
      "approved_scoped_pages":sum(r["scoped_approved_css"] for r in rows),
      "still_old_brand_pages":sum(r["old_brand_occurrences"]>0 for r in rows),
      "needs_css_or_scope":[r["path"] for r in rows if not r["scoped_approved_css"]],
      "needs_header_brand":[r["path"] for r in rows if r["header_approved"] is False],
      "legacy_canonical_count":sum(r["canonical_old_host"] for r in rows),
      "rows":rows,
      "notes":[
        "Canonical old-host values intentionally retained until independent domain migration gate.",
        "Legacy paid buyer documents and source archives are outside scope.",
        "Only source-controlled public HTML is counted; generated XML/RSS, emails and other scripts require separate inventory.",
        "No page was changed during this inspection."
      ]
    }

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parent.parent)
    p.add_argument("--out",type=Path)
    p.add_argument("--require-complete",action="store_true")
    args=p.parse_args()
    report=inspect(args.root.resolve())
    data=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if args.out:args.out.write_text(data,encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in {"rows","needs_css_or_scope","needs_header_brand"}},ensure_ascii=False))
    print("NEEDS_CSS",len(report["needs_css_or_scope"]),"NEEDS_HEADER",len(report["needs_header_brand"]))
    if args.require_complete and (report["needs_css_or_scope"] or report["needs_header_brand"] or report["still_old_brand_pages"]):
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
