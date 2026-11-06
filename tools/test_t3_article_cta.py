#!/usr/bin/env python3
"""T3 retirement: no legacy purchase links in approved articles or diagnosis.

Active P3/P5 CTA prices must still match server prices. No payments or network.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "products-config.php").read_text(encoding="utf-8")
EXPECTED = {
    "raboty-ne-prinyaty": ("p3", "p3-shablony-ks2-ks3.html"),
    "garantiynoe-uderzhanie-v-ks-2-i-ks-3": ("p5", "p5-shtrafy-uderzhaniya.html"),
}
REMOVED = "/products/t3-odnostoronniy-akt-i-zachet.html"


def server_price(sku: str) -> int:
    section = CONFIG[CONFIG.index("function mvb_products()"):]
    match = re.search(
        rf"'{re.escape(sku)}'\s*=>\s*\[\s*'name'\s*=>\s*'(?:[^'\\]|\\.)*'"
        rf"\s*,\s*'price'\s*=>\s*(\d+)",
        section, re.S)
    assert match, f"active {sku} missing from products-config.php"
    return int(match.group(1)) // 100


def article(slug: str) -> str:
    return html.unescape((ROOT / "articles" / (slug + ".html")).read_text(encoding="utf-8"))


def check_article(slug: str, source: str) -> None:
    sku, page = EXPECTED[slug]
    assert REMOVED not in source, f"{slug}: retired T3 cross sell restored"
    main_cta = re.search(r'<div class="article-cta"[^>]*>(.*?)</div>', source, re.S)
    assert main_cta, f"{slug}: no CTA"
    body = main_cta.group(1)
    assert f'href="/products/{page}"' in body, f"{slug}: approved core missing"
    visible = re.search(r'<p[^>]*>\s*([\d\s\u00a0]+)\s*₽\s*</p>', body)
    assert visible, f"{slug}: main CTA price missing"
    amount = int(re.sub(r"\D", "", visible.group(1)))
    assert amount == server_price(sku), f"{slug}: CTA price {amount} vs server {server_price(sku)}"
    if sku == "p5":
        assert "30 файлов." in body and "11 файлов." not in body, f"{slug}: P5 edition count stale"


def diagnostic_items(source: str):
    m = re.search(r"const SCENARIOS = (\[.*?\]);", source, re.S)
    assert m, "no diagnosis scenario JSON"
    return json.loads(m.group(1))


def check_diagnosis(source: str) -> None:
    assert REMOVED not in source, "retired T3 still linked by diagnosis"
    scenarios = {x["id"]: x for x in diagnostic_items(source)}
    for sid, (sku, page) in (("S-2", EXPECTED["raboty-ne-prinyaty"]),
                             ("S-4", EXPECTED["garantiynoe-uderzhanie-v-ks-2-i-ks-3"])):
        row = scenarios[sid]
        assert row.get("entry") is None, f"{sid}: retired entry revived"
        assert row["core"]["url"] == "/products/" + page, f"{sid}: active core mismatch"
        assert row["core"]["price"] == server_price(sku), f"{sid}: core price mismatch"


def must_fail(fn, *args) -> None:
    try:
        fn(*args)
    except AssertionError:
        return
    raise AssertionError("negative mutant passed validation")


def main() -> None:
    assert not re.search(r"'t3'\s*=>\s*\[", CONFIG), "T3 active in server price list"
    for slug in EXPECTED:
        source = article(slug)
        check_article(slug, source)
    diagnosis = (ROOT / "diagnostika.html").read_text(encoding="utf-8")
    check_diagnosis(diagnosis)

    a = article("raboty-ne-prinyaty")
    must_fail(check_article, "raboty-ne-prinyaty",
              a.replace("</div>", '<a href="' + REMOVED + '">old T3</a></div>', 1))
    b = article("garantiynoe-uderzhanie-v-ks-2-i-ks-3")
    must_fail(check_article, "garantiynoe-uderzhanie-v-ks-2-i-ks-3",
              b.replace(">29 900 ₽</p>", ">29 ₽</p>", 1))
    must_fail(check_diagnosis,
              diagnosis.replace('"id":"S-2"', '"id":"S-2"', 1).replace(
                  '"entry":null', '"entry":{"url":"' + REMOVED + '","price":14900}', 1))
    print("RETIRED_T3_ARTICLE_DIAG_PASS articles=2 scenarios=2 negative_mutations=3")


if __name__ == "__main__":
    sys.exit(main() or 0)
