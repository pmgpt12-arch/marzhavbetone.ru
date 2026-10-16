#!/usr/bin/env python3
"""R2a: exact own-domain URL migration in public SEO source (no runtime changes).

Only replaces full `https://marzhavbetone.ru` URLs in 88 public HTML pages,
the existing sitemap and the two generator BASE/SITE constants, plus Host and
Sitemap in robots.txt.  It never rewrites email, Telegram/Instagram handles,
order identifiers, product artifacts, PHP, .htaccess, old-domain redirects
or payment configuration.

Run in isolated R2 branch:
    python3 tools/prepare_rebrand_url_migration.py
    python3 tools/prepare_rebrand_url_migration.py --write
    python3 tools/prepare_rebrand_url_migration.py --check
"""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD = "https://marzhavbetone.ru"
NEW = "https://nastoronepodryadchika.ru"
SKIP = {".git", "node_modules", ".claude", "data", "content", "tools"}
HTML_RE = re.compile(r".*\.html$")


def public_html() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "--", "*.html"], cwd=ROOT,
        capture_output=True, text=True, timeout=14, check=True
    )
    paths = [Path(x) for x in proc.stdout.splitlines()
             if HTML_RE.fullmatch(x) and not set(Path(x).parts) & SKIP]
    if len(paths) != 88:
        raise RuntimeError(f"Expected 88 public pages, got {len(paths)}")
    return paths


def change_exact(path: Path, text: str) -> str:
    name=path.as_posix()
    if name.endswith(".html") or name == "sitemap.xml":
        return text.replace(OLD, NEW)
    if name == "robots.txt":
        before = "Host: marzhavbetone.ru"
        after = "Host: nastoronepodryadchika.ru"
        text=text.replace(before,after).replace(OLD,NEW)
        if after not in text:
            raise ValueError("robots Host marker missing")
        return text
    if name == "tools/build_sitemap.py":
        before = f'BASE = "{OLD}"'
        after = f'BASE = "{NEW}"'
    elif name == "tools/build_rss.py":
        before = f'SITE = "{OLD}"'
        after = f'SITE = "{NEW}"'
    else:
        raise ValueError(f"Refusing unapproved path: {name}")
    if before in text:
        if text.count(before)!=1:
            raise ValueError(f"{name}: duplicate old BASE")
        return text.replace(before,after)
    if after not in text:
        raise ValueError(f"{name}: neither old nor new BASE")
    return text


def main() -> int:
    ap=argparse.ArgumentParser()
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--write",action="store_true")
    args=ap.parse_args()
    paths=public_html()+[Path(x) for x in (
        "sitemap.xml","robots.txt","tools/build_sitemap.py","tools/build_rss.py"
    )]
    modified=[]
    old_instances=0
    for path in paths:
        src=(ROOT/path).read_text("utf-8")
        old_instances+=src.count(OLD)
        result=change_exact(path,src)
        if src!=result:
            modified.append(str(path))
            if args.write:
                (ROOT/path).write_text(result,encoding="utf-8")
    print(f"checked={len(paths)} public_html=88 old_host_occurrences={old_instances} pending={len(modified)}")
    if modified:print("pending paths:",*modified[:12],sep="\n  ")
    if args.check and modified:
        return 1
    return 0


if __name__=="__main__":
    try:raise SystemExit(main())
    except (RuntimeError,ValueError) as exc:
        print(f"R2_DOMAIN_GATE_FAIL: {exc}",file=sys.stderr)
        raise SystemExit(2)
