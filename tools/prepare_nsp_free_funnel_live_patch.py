#!/usr/bin/env python3
"""Prepare exact-live FREE→PAID HTML candidates without touching production.

The only outputs are local backup bytes, proposed HTML and a SHA receipt.
Do not upload proposed files from this program. A separate owner release gate
is required before any production update.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

# Accepted READ-ONLY live HTTPS snapshots (2026-11-06); fail closed on drift.
FILES = {
    "dengi": ("dbc431e7fbde10a2e8e18cd6465356737c88c55de22e39f7d9c065f6e4a88555",
              "t1-pervyy-shag-pri-neoplate", "p1-oplata-po-ks2", True, False),
    "uderzhaniya": ("6a333059adb5917281a2e3f426c6bb6cd1d3668632bb8afe516826a15a83e1d1",
                   "t3-odnostoronniy-akt-i-zachet", "p5-shtrafy-uderzhaniya", False, False),
    "bankrotstvo": ("5a6534374bb1d9ec61f81256a0fa8b356e0e8b5bdf379ac1472a9029c951a08f",
                   "t4-genpodryadchik-bankrotitsya", "p9-bankrotstvo-genpodryadchika", True, False),
    "avans": ("f83517c795c928a40f071209ff27b3e7485764621a1186849eb5e44852ef925c",
              "t5-trebuyut-vernut-avans", "p8-avans-po-dogovoru-subpodryada", True, False),
    "ispolnitelnaya-dokumentaciya": (
        "41a19bf042772432e096c536d43f4c999e2fc792c166997c6ff44b1d6a37f655",
        "t2-peredacha-ispolnitelnoy-dokumentacii", "p4-ispolnitelnaya-dokumentaciya-pto", True, True),
    "akt-skrytyh-rabot": (
        "38a1c34253f471be47caae319bb12bf8fb210c361016bb85b7bdf84f3894a6f9",
        "t2-peredacha-ispolnitelnoy-dokumentacii", "p4-ispolnitelnaya-dokumentaciya-pto", True, True),
}
RETIRED = re.compile(r"products/t[1-6]-", flags=re.IGNORECASE)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_exact_live(name: str, blob: bytes, *, check_sha: bool = True) -> bytes:
    expected_sha, old_sku, new_sku, remove_card, replace_count = FILES[name]
    if check_sha and digest(blob) != expected_sha:
        raise ValueError(f"{name}: LIVE_SHA_DRIFT current={digest(blob)} expected={expected_sha}")
    original = blob.decode("utf-8", errors="strict")
    lines = original.splitlines(keepends=True)
    assert original and lines, f"{name}: empty HTML"
    old_form = f'data-continue="https://nastoronepodryadchika.ru/products/{old_sku}.html?'
    new_form = f'data-continue="https://nastoronepodryadchika.ru/products/{new_sku}.html?'
    if sum(line.count(old_form) for line in lines) != 1:
        raise ValueError(f"{name}: invalid form preimage")
    patched = []
    count_form = 0
    count_card = 0
    count_p4 = 0
    for line in lines:
        if old_form in line:
            if '<form' not in line or 'id="lead-form"' not in line:
                raise ValueError(f"{name}: old destination not on lead form")
            line = line.replace(old_form, new_form, 1)
            count_form += 1
        if 'class="product-card"' in line and f'href="../products/{old_sku}.html"' in line:
            count_card += 1
            if remove_card:
                continue
            raise ValueError(f"{name}: unexpected retired card")
        if replace_count and 'class="product-card"' in line and f'href="../products/{new_sku}.html"' in line:
            if line.count("25 файла.") != 1:
                raise ValueError(f"{name}: P4 preimage count changed")
            line = line.replace("25 файла.", "30 файлов.", 1)
            count_p4 += 1
        patched.append(line)
    candidate = "".join(patched)
    if count_form != 1 or count_card != int(remove_card) or count_p4 != int(replace_count):
        raise ValueError(f"{name}: unexpected edit count")
    if RETIRED.search(candidate) or candidate.count('class="product-card"') != 1:
        raise ValueError(f"{name}: retired SKU or duplicate card remains")
    if f'href="../products/{new_sku}.html"' not in candidate:
        raise ValueError(f"{name}: current paid card missing")
    if original == candidate:
        raise ValueError(f"{name}: no-op patch")
    return candidate.encode("utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, required=True,
                   help="folder containing the six LIVE materialy/*.html snapshots")
    p.add_argument("--output-dir", type=Path, required=True,
                   help="a new, non-existing folder on local/private disk")
    args = p.parse_args()
    if args.output_dir.exists():
        p.error("output dir already exists; refusing overwrite")
    snapshots = {}
    for name in FILES:
        rel = Path("materialy") / (name + ".html")
        source = args.input_dir / rel
        if not source.is_file():
            p.error(f"missing snapshot {rel}")
        data = source.read_bytes()
        patch = patch_exact_live(name, data)
        snapshots[rel] = (data, patch)
    # All six read/QA checks finished before any output is created.
    args.output_dir.mkdir(parents=True)
    records = []
    for rel, (before, after) in snapshots.items():
        backup = args.output_dir / "backup" / rel
        candidate = args.output_dir / "candidate" / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(before)
        candidate.write_bytes(after)
        if backup.read_bytes() != before or candidate.read_bytes() != after:
            raise OSError(f"write verification failed for {rel}")
        records.append({
            "path": rel.as_posix(),
            "preimage_sha256": digest(before),
            "candidate_sha256": digest(after),
            "backup": str(backup.relative_to(args.output_dir)),
            "candidate": str(candidate.relative_to(args.output_dir)),
            "form_redirects_replaced": 1,
            "retired_cards_removed": int(FILES[rel.stem][3]),
            "p4_file_count_fixed": int(FILES[rel.stem][4]),
        })
    receipt = {
        "status": "CANDIDATES_ONLY_NOT_DEPLOYED",
        "owner_approval_required": True,
        "live_writes": 0,
        "payment_calls": 0,
        "files": records,
    }
    out = args.output_dir / "manifest.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FREE_FUNNEL_LIVE_CANDIDATE_PASS files=6 forms=6 removed_cards=5 p4_counts=2 "
          f"manifest_sha256={digest(out.read_bytes())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
