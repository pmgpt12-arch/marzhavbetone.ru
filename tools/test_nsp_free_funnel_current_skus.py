#!/usr/bin/env python3
"""FREE→PAID post-delivery gate: only currently sold SKU pages, one card each.

Offline public-source check. No lead POST, payment, email, or external network.
"""
from html import unescape
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "dengi": "p1-oplata-po-ks2",
    "dop-raboty": "p2-dopolnitelnye-raboty",
    "vozvrat-ks": "p3-shablony-ks2-ks3",
    "uderzhaniya": "p5-shtrafy-uderzhaniya",
    "dogovor": "p7-dogovor-podryada",
    "bankrotstvo": "p9-bankrotstvo-genpodryadchika",
    "avans": "p8-avans-po-dogovoru-subpodryada",
    "raschet-metrami": "p11-raschet-metrami",
    "ispolnitelnaya-dokumentaciya": "p4-ispolnitelnaya-dokumentaciya-pto",
    "akt-skrytyh-rabot": "p4-ispolnitelnaya-dokumentaciya-pto",
}
REMOVED_SKU = re.compile(r"products/t[1-6]-", re.I)
FORM = re.compile(r'<form\b[^>]*\bid="lead-form"[^>]*>', re.I)
DEST = re.compile(r'data-continue="([^"]+)"')


def verify_page(name: str, source: str) -> None:
    forms = FORM.findall(source)
    assert len(forms) == 1, f"{name}: expected one lead form"
    match = DEST.search(forms[0])
    assert match, f"{name}: missing data-continue"
    target = urlparse(unescape(match.group(1)))
    expected_path = "/products/" + EXPECTED[name] + ".html"
    assert target.scheme == "https" and target.netloc == "nastoronepodryadchika.ru"
    assert target.path == expected_path, f"{name}: bad postdelivery {target.path}"
    assert "utm_source=site" in target.query and "utm_medium=post-delivery" in target.query
    assert not REMOVED_SKU.search(source), f"{name}: obsolete T-SKU link"
    assert source.count('class="product-card"') == 1, f"{name}: not exactly one paid card"
    assert f'href="../products/{EXPECTED[name]}.html"' in source, f"{name}: paid card mismatch"
    if name in ("ispolnitelnaya-dokumentaciya", "akt-skrytyh-rabot"):
        assert "30 файлов." in source and "25 файла." not in source, f"{name}: stale P4 count"


def must_fail(name: str, modified: str) -> None:
    try:
        verify_page(name, modified)
    except AssertionError:
        return
    raise AssertionError(f"{name}: mutant accepted")


def main() -> None:
    materialy = ROOT / "materialy"
    pages = {
        name: (materialy / f"{name}.html").read_text(encoding="utf-8")
        for name in EXPECTED
    }
    for name, source in pages.items():
        verify_page(name, source)
    old = "p4-ispolnitelnaya-dokumentaciya-pto"
    must_fail("akt-skrytyh-rabot", pages["akt-skrytyh-rabot"].replace(
        "/products/" + old + ".html?utm_source",
        "/products/t2-peredacha-ispolnitelnoy-dokumentacii.html?utm_source", 1))
    must_fail("ispolnitelnaya-dokumentaciya", pages["ispolnitelnaya-dokumentaciya"].replace(
        "30 файлов.", "25 файла.", 1))
    must_fail("dengi", pages["dengi"].replace(
        "/products/p1-oplata-po-ks2.html?utm_source",
        "/products/p9-bankrotstvo-genpodryadchika.html?utm_source", 1))
    must_fail("uderzhaniya", pages["uderzhaniya"].replace(
        '</div>', '<article class="product-card"><a href="../products/t3-legacy.html">old</a></article></div>', 1))
    print(f"FREE_FUNNEL_PASS material_pages={len(pages)} "
          "active_destinations=10 single_paid_card=10 negative_mutations=4")


if __name__ == "__main__":
    main()
