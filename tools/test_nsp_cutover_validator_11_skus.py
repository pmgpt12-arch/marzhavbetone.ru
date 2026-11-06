#!/usr/bin/env python3
"""11 approved paid SKUs in NSP cutover catalog; T2/T3 retired from new sales.

Isolated, read-only production fixture: four negative gates must fail closed.
No live requests, product ZIP extraction, payment, mail, or deployment.
"""
from contextlib import redirect_stdout
from html import escape
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
import json
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "tools/nsp-final/validate.py"
spec = spec_from_file_location("nsp_final_validate", CODE)
assert spec and spec.loader
module = module_from_spec(spec)
spec.loader.exec_module(module)

assert len(module.PRICES) == 11, "ACTIVE_PAID_SKU_COUNT"
assert "t2" not in module.PRICES and "t3" not in module.PRICES, "RETIRED_PRODUCTS_IN_PRICE_GATE"
assert module.GROUPS["zakrytie-i-oplata"] == ["p3", "p1"], "RETIRED_PRODUCTS_IN_GROUP"
assert set(module.PRICES) == set().union(*map(set, module.GROUPS.values())), "PRODUCT_COVERAGE"

source = (ROOT / "katalog.html").read_text(encoding="utf-8")
assert source.count('data-sku="p1"') == 1
assert source.count('data-price="2990000"') == 1
assert source.count('class="product-card free"') == 10

def exact_replace(text, old, new):
    assert text.count(old) == 1, "NEGATIVE_FIXTURE_NONUNIQUE"
    return text.replace(old, new, 1)

with tempfile.TemporaryDirectory(prefix="nsp-11-sku-validate-") as tmp:
    root = Path(tmp)
    (root / "tools/nsp-final").mkdir(parents=True)
    (root / "tools/nsp-final/static-before.json").write_text("[]\n")
    (root / "tools/nsp-final/manifest.json").write_text("[]\n")
    (root / "tools/nsp-final/contract.json").write_text('{"pages": {}}\n')
    path = root / "katalog.html"

    def check(html, expect_pass):
        path.write_text(html, encoding="utf-8")
        with redirect_stdout(StringIO()) as captured:
            try:
                report = module.validate(root=root, catalog_only=True)
            except AssertionError:
                if expect_pass:
                    raise
                return "REJECTED"
        if not expect_pass:
            raise AssertionError("NEGATIVE_FIXTURE_FALSE_PASS")
        assert report["paid_sku"] == 11 and report["prices"] == "UNCHANGED"
        assert report["groups"] == [4,2,2,2,1] and report["free_materials"] == 10
        return "PASS"

    assert check(source, True) == "PASS"

    # New-sale T2 is prohibited even when a developer adds an otherwise valid button.
    t2 = exact_replace(source, 'data-sku="p1"', 'data-sku="t2"')
    assert check(t2, False) == "REJECTED"

    # User-provided frontend prices must agree with the accepted server contract.
    bad_price = exact_replace(source, 'data-price="2990000"', 'data-price="2990001"')
    assert check(bad_price, False) == "REJECTED"

    # A catalog count must match the SKUs actually in its group.
    assert len(re.findall(r'id="group-zakrytie-i-oplata"', source)) == 1
    bad_group = exact_replace(source,
        '<span class="product-group-count">2</span></summary>',
        '<span class="product-group-count">3</span></summary>')
    assert check(bad_group, False) == "REJECTED"

    # Free-material coverage must remain exactly ten.
    bad_free = source.replace('class="product-card free"', 'class="product-card inactive"', 1)
    assert check(bad_free, False) == "REJECTED"

print(json.dumps({
    "status":"PASS", "approved_paid_skus":11, "retired_new_sales":["t2","t3"],
    "group_counts":[4,2,2,2,1], "free_materials":10,
    "negative_mutations_rejected":4, "production_writes":0,
    "orders_created":0, "paid_files_exported":0,
}, ensure_ascii=False))
