#!/usr/bin/env python3
"""11 live-buyer ZIP counts must match catalog cards and Product JSON-LD.
Source of truth: verified private master SHA/CRC receipt run 42133240407.
Read-only, stdlib only. P3 explicit "10 документов и инструкция" = 11 entries.
"""
from __future__ import annotations
from html import unescape
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tools/reports/nsp-paid-master-counts-20261106.json"
CATALOG = ROOT / "katalog.html"
LD_RE = re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
CARD_RE = re.compile(r'<article\b[^>]*class="product-card"[^>]*>(.*?)</article>', re.S)
P_RE = re.compile(r'<p(?:\s[^>]*)?>(.*?)</p>', re.S)
TAG_RE = re.compile(r'<[^>]+>')
SKU_RE = re.compile(r'\bdata-sku="(p\d+)"')
FILES_RE = re.compile(r'(?<!\d)(\d{1,3})\s+файл(?:ов|а)?\b', re.I)
P3_DOC_RE = re.compile(r'(?<!\d)(\d{1,3})\s+документов\s+и\s+инструкция\b', re.I)


def products_in(value):
    if isinstance(value, list):
        for child in value:
            yield from products_in(child)
    elif isinstance(value, dict):
        if value.get("@type") == "Product":
            yield value
        for child in value.values():
            yield from products_in(child)


def normalized_count(text: str, *, sku: str, allow_p3_semantics: bool = False) -> int:
    files = [int(m.group(1)) for m in FILES_RE.finditer(text)]
    if len(files) == 1:
        return files[0]
    if allow_p3_semantics and sku == "p3" and not files:
        docs = [int(m.group(1)) for m in P3_DOC_RE.finditer(text)]
        if len(docs) == 1:
            return docs[0] + 1
    raise AssertionError("AMBIGUOUS_OR_MISSING_COUNT_" + sku)


def verify(source: str, truth: dict[str, int]) -> dict[str, int]:
    scripts = LD_RE.findall(source)
    if len(scripts) != 1:
        raise AssertionError("CATALOG_JSONLD_COUNT")
    payload = json.loads(scripts[0])
    ld = {}
    for prod in products_in(payload):
        offers = prod.get("offers")
        url = offers.get("url", "") if isinstance(offers, dict) else prod.get("url", "")
        match = re.search(r"/products/(p\d+)-", str(url))
        if match and match[1] in truth:
            sku = match[1]
            if sku in ld:
                raise AssertionError("DUPLICATE_JSONLD_" + sku)
            desc = prod.get("description")
            if not isinstance(desc, str):
                raise AssertionError("MISSING_DESCRIPTION_" + sku)
            got = normalized_count(desc, sku=sku, allow_p3_semantics=True)
            if got != truth[sku]:
                raise AssertionError(f"STRUCTURED_COUNT_MISMATCH_{sku}_{got}_VS_{truth[sku]}")
            ld[sku] = got
    if set(ld) != set(truth):
        raise AssertionError("STRUCTURED_SKU_COVERAGE")

    cards = {}
    for match in CARD_RE.finditer(source):
        part = match.group(1)
        sku_match = SKU_RE.search(part)
        if not sku_match or sku_match[1] not in truth:
            continue
        sku = sku_match[1]
        if sku in cards:
            raise AssertionError("DUPLICATE_CARD_" + sku)
        plain = " ".join(unescape(TAG_RE.sub(" ", p)) for p in P_RE.findall(part))
        got = normalized_count(plain, sku=sku)
        if got != truth[sku]:
            raise AssertionError(f"CARD_COUNT_MISMATCH_{sku}_{got}_VS_{truth[sku]}")
        cards[sku] = got
    if set(cards) != set(truth):
        raise AssertionError("CARD_SKU_COVERAGE")
    return ld


def main():
    claim = json.loads(REPORT.read_text(encoding="utf-8"))
    assert claim["schema"] == "NSP_PAID_MASTER_COUNT_CONTRACT_20261106_v1"
    assert claim["evidence"]["read_only_action_run"] == 42133240407
    assert claim["evidence"]["result"] == "PASS_ALL_11_REAL_PRIVATE_PINNED_ZIPS"
    truth = claim["count_by_sku"]
    assert len(truth) == 11 and set(truth) == {
        "p1", "p2", "p3", "p4", "p5", "p7", "p8", "p9", "p10", "p11", "p13"
    }
    text = CATALOG.read_text(encoding="utf-8")
    accepted = verify(text, truth)
    assert accepted["p3"] == 11, "P3_COUNT_SEMANTIC_GATE"

    # Negative fixture: a silently stale structured P4 description MUST fail.
    scripts = LD_RE.findall(text)
    records = list(products_in(json.loads(scripts[0])))
    p4 = next(p for p in records if "/products/p4-" in str(
        (p.get("offers") or {}).get("url", "")
    ))
    previous = json.dumps(p4["description"], ensure_ascii=False)
    stale = json.dumps(p4["description"].replace("30 файлов", "25 файлов"), ensure_ascii=False)
    assert previous != stale and text.count(previous) == 1, "P4_NEGATIVE_FIXTURE_PREIMAGE"
    try:
        verify(text.replace(previous, stale, 1), truth)
        raise AssertionError("P4_NEGATIVE_GATE_DID_NOT_FAIL")
    except AssertionError as exc:
        assert "STRUCTURED_COUNT_MISMATCH_p4" in str(exc), str(exc)

    # P3 "10 документов и инструкция" is legitimate; "10 файлов" is NOT.
    p3 = next(p for p in records if "/products/p3-" in str(
        (p.get("offers") or {}).get("url", "")
    ))
    old = json.dumps(p3["description"], ensure_ascii=False)
    wrong = json.dumps(p3["description"].replace("10 документов и инструкция", "10 файлов"), ensure_ascii=False)
    assert old != wrong and text.count(old) == 1, "P3_NEGATIVE_FIXTURE_PREIMAGE"
    try:
        verify(text.replace(old, wrong, 1), truth)
        raise AssertionError("P3_NEGATIVE_GATE_DID_NOT_FAIL")
    except AssertionError as exc:
        assert "STRUCTURED_COUNT_MISMATCH_p3" in str(exc), str(exc)

    print(json.dumps({
        "status": "PASS", "catalog_cards": 11, "jsonld_products": 11,
        "private_master_source_run": 42133240407,
        "p3_document_plus_instruction": "PASS",
        "negative_regressions": 2, "actual_paid_zip_bytes_read": 0,
        "production_writes": 0
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
