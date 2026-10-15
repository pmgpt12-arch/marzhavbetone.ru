#!/usr/bin/env python3
"""R2a exact URL-migration acceptance: no payload, SKU, mail or social changes.

Compares to approved R1 commit. Only URL host of own-domain absolute HTTPS
links (and the robots Host directive) can change. No runtime/.htaccess/payment
migration is covered or authorized.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
PARENT_SHA="7f0d0154a9c1f618fa60d5cea028316592050ac0"
OLD="https://marzhavbetone.ru"
NEW="https://nastoronepodryadchika.ru"


def git(*args: str) -> str:
    return subprocess.run(["git",*args],cwd=ROOT,capture_output=True,
                          text=True,check=True,timeout=15).stdout


def candidates() -> list[Path]:
    files=[Path(p) for p in git("ls-files","--","*.html").splitlines()
           if not p.startswith(("data/","content/","tools/","node_modules/"))]
    return files+[Path(p) for p in (
        "robots.txt","sitemap.xml","tools/build_rss.py","tools/build_sitemap.py")]


def transformed(before: str, path: Path) -> str:
    text=before.replace(OLD,NEW)
    if path.as_posix()=="robots.txt":
        text=text.replace("Host: marzhavbetone.ru","Host: nastoronepodryadchika.ru")
    return text


def read_sitemap(text: str) -> list[str]:
    node=ET.fromstring(text)
    return [el.text for el in node.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]


def inspect() -> dict:
    paths=candidates()
    if len(paths)!=92:
        raise RuntimeError(f"Expected 92 migration inputs, found {len(paths)}")
    rows=[]
    originals={}
    for p in paths:
        rel=p.as_posix()
        before=git("show",f"{PARENT_SHA}:{rel}")
        after=(ROOT/p).read_text("utf-8")
        originals[rel]=before
        expected=transformed(before,p)
        rows.append({
          "path":rel,
          "changed":before!=after,
          "exact_allowed_delta":expected==after,
          "old_host_after":after.count(OLD),
          "old_host_before":before.count(OLD),
          "new_host_after":after.count(NEW),
          "sha256":hashlib.sha256(after.encode("utf-8")).hexdigest(),
        })
    old_locs=read_sitemap(originals["sitemap.xml"])
    new_locs=read_sitemap((ROOT/"sitemap.xml").read_text("utf-8"))
    paths_ok=(len(old_locs)==len(new_locs)==84
              and [x.replace(OLD,"") for x in old_locs]
                  ==[x.replace(NEW,"") for x in new_locs])
    problems=[row["path"] for row in rows
              if not row["exact_allowed_delta"] or row["old_host_after"]]
    report={
        "gate":"DOMAIN_HOST_SWAP_R2A_ONLY",
        "baseline_commit":PARENT_SHA,
        "current_commit":git("rev-parse","HEAD").strip(),
        "inputs":len(rows),
        "changed_files":sum(x["changed"] for x in rows),
        "old_host_occurrences_before":sum(x["old_host_before"] for x in rows),
        "old_host_occurrences_after":sum(x["old_host_after"] for x in rows),
        "new_host_occurrences_after":sum(x["new_host_after"] for x in rows),
        "sitemap_route_preservation":paths_ok,
        "failed_inputs":problems,
        "pass":not problems and paths_ok and len(rows)==92,
        "rows":rows,
        "limitations":[
          "No .htaccess new-host redirection applied",
          "No backend PHP or YooKassa configuration changed",
          "No email sender, contact or external social account changed",
          "No production or staging site cutover performed",
          "Canonical, OpenGraph and sitemap URL changes are a candidate until release",
        ]
    }
    return report


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true")
    p.add_argument("--report",type=Path)
    args=p.parse_args()
    r=inspect()
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:r[k] for k in (
        "gate","inputs","changed_files","old_host_occurrences_before",
        "old_host_occurrences_after","new_host_occurrences_after",
        "sitemap_route_preservation","failed_inputs","pass"
    )},ensure_ascii=False))
    return 1 if args.check and not r["pass"] else 0


if __name__=="__main__":
    raise SystemExit(main())
