#!/usr/bin/env python3
"""Protected P1/P2/P3 buyer ZIP name-set gate (no buyer archive export)."""
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import build_preview as b

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "p1": "p1-oplata-po-ks2.html",
    "p2": "p2-dopolnitelnye-raboty.html",
    "p3": "p3-shablony-ks2-ks3.html",
}


def must_fail(sku: str, text: str) -> None:
    error = b.pinned_inventory_error(sku, text)
    assert error, f"{sku}: unauthorized source mutant was accepted"


def main() -> None:
    catalog = b.catalog()
    receipt = json.loads(b.PINNED_RECEIPT.read_text(encoding="utf-8"))
    assert set(receipt["products"]) == set(PAGES)
    for sku, name in PAGES.items():
        page = ROOT / "products" / name
        original = page.read_text(encoding="utf-8")
        assert b.render(page, catalog) == (original, ""), sku
        members = receipt["products"][sku]["members"]
        assert b.pinned_inventory_error(sku, original) == ""
        original_marker = "<code>" + members[0] + "</code>"
        assert original_marker in original, sku
        must_fail(sku, original.replace(original_marker,
                                        "<code>unapproved.docx</code>", 1))
        with TemporaryDirectory(prefix="p123-preview-negative-") as d:
            root = Path(d)
            wrong_receipt = json.loads(json.dumps(receipt))
            wrong_receipt["products"][sku]["sha256"] = "0" * 64
            fake = root / "wrong-sha.json"
            fake.write_text(json.dumps(wrong_receipt), encoding="utf-8")
            with patch.object(b, "PINNED_RECEIPT", fake):
                must_fail(sku, original)
            wrong_list = json.loads(json.dumps(receipt))
            wrong_list["products"][sku]["members"].append("invented.docx")
            fake.write_text(json.dumps(wrong_list), encoding="utf-8")
            with patch.object(b, "PINNED_RECEIPT", fake):
                must_fail(sku, original)
            fake_config = root / "wrong-products-config.php"
            fake_config.write_text(b.CONFIG.read_text(encoding="utf-8").replace(
                receipt["products"][sku]["sha256"], "0" * 64, 1),
                encoding="utf-8")
            with patch.object(b, "CONFIG", fake_config):
                must_fail(sku, original)
            # An obsolete unpacked folder may not override immutable buyer ZIP.
            with patch.object(b, "STORAGE", root / "not-deliverable"):
                assert b.render(page, catalog) == (original, ""), sku
    print("P123_PINNED_PREVIEW_PASS active_skus=3 "
          "mutations=12 linked_sha_and_members=3 no_public_buyer_zip=1")


if __name__ == "__main__":
    main()
