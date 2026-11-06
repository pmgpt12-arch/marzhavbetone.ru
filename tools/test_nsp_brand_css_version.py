#!/usr/bin/env python3
"""NSP CSS cache key follows exact approved stylesheet bytes, not an old label.

Checks all eligible HTML pages and guards against empty extraction. No writes.
"""
from __future__ import annotations
from hashlib import sha1
from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parents[1]
CSS=ROOT/"brand-approved-2026.css"
SKIP={"content",".git","products-storage","orders","tools",
      "node_modules",".claude",".github","data"}
REF=re.compile(r'(?:href|src)="[^"]*brand-approved-2026\.css\?v=([a-z0-9]{8})"')

def check_page(text:str,sha:str)->bool:
    matches=REF.findall(text)
    return len(matches)==1 and matches[0]==sha

def main():
    real=sha1(CSS.read_bytes()).hexdigest()[:8]
    paths=sorted(p for p in ROOT.rglob("*.html")
        if not set(p.relative_to(ROOT).parts[:-1]) & SKIP)
    assert len(paths)>=85, "SOURCE_PAGE_COVERAGE_SUSPICIOUSLY_LOW"
    wrong=[]
    for p in paths:
        s=p.read_text(encoding="utf-8")
        if not check_page(s,real):
            wrong.append(p.relative_to(ROOT).as_posix())
    assert not wrong, "BAD_CSS_HASH_OR_MISSING_CSS: "+", ".join(wrong[:12])
    assert "index.html" in [p.relative_to(ROOT).as_posix() for p in paths]
    home=(ROOT/"index.html").read_text(encoding="utf-8")
    article=(ROOT/"articles/index.html").read_text(encoding="utf-8")
    assert check_page(home,real) and check_page(article,real)

    # Both pre-cutover historic hashes must be rejected; absence is not PASS.
    cases=[
        home.replace(real,"a388f3a2",1),
        article.replace(real,"129e847b",1),
        re.sub(r'<link[^>]*brand-approved-2026\.css[^>]*>',"",home,count=1),
    ]
    assert len(cases)==3 and all(not check_page(s,real) for s in cases)
    print(json.dumps({"status":"PASS","pages":len(paths),"css_sha1_prefix":real,
       "historic_hash_mutations_rejected":2,
       "missing_css_mutation_rejected":1,"production_writes":0},ensure_ascii=False))

if __name__=="__main__":
    main()
