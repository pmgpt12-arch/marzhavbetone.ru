#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import hashlib
import io
import json
import os
import sys

ROOT = Path("/home/denis/projects/mb001-p11-archive-ics-20261014")
SRC = ROOT / "tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami"
OUT = ROOT / "tools/candidates/portfolio-owner-pdf-20261013"
EVIDENCE = OUT / "p11-t6-dayone-20261014"
ARCHIVE = OUT / "p11-t6-eight-files-candidate-ics-20261014.zip"
RECEIPT = EVIDENCE / "final-buyer-archive-after-ics-20261014.json"
HOLD = EVIDENCE / "release-manifest-after-ics-HOLD.json"
HEAD = "d4e2d84666f0c20a2942bb6b13791f9633b950c2"
FILES = {
    "00-START-HERE.txt": "2f895a2f2b8ea5e166c8f18dd416465f2651b3562068551fc9f26841fd5dcf3a",
    "50-slovar-poley-raschet-metrami.docx": "6f40e5d3757d77d6460efb990f459167220f5fb9f3f36a6a6bcfb92b415869d5",
    "51-algoritm-raschet-metrami.pdf": "2a4c98dc4a1b131dbccb787276f487a17a76a0c6643932c0ee0ca666601135d7",
    "52-chek-list-raschet-metrami.docx": "6094a91af0a2e750a1ef71f9b394ea49207af11f8c5420ade1a7da48ff79fd38",
    "53-zapros-status-obekta.docx": "c3fccbdc5e7e6841ca8c48b5ab1c199bdebe0d2f4990c232040d20f70bfc023e",
    "54-zapros-sostoyanie-escrow.docx": "8e76f513b4f72c51bd8e9ad1bd56c27409285585b2f38f96c76b5f8dfbfa4f96",
    "55-pamyatka-punkt-ustupki-escrow.pdf": "20f65a850db70836b2897dc747ed6478781641e3a4f5a537b094a7afec0814a2",
    "56-pervyy-den-do-podpisi.docx": "9c40a96498037b53a68ecea6f3ee57129a9f2c236d1073d1818c603016260807",
}

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())

def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    fsync_dir(path.parent)

def atomic_json(path: Path, payload: dict) -> None:
    atomic_bytes(path, (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode())

def main() -> int:
    actual = {name: sha_file(SRC / name) for name in FILES}
    if actual != FILES:
        raise AssertionError({"expected": FILES, "actual": actual})
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            info = ZipInfo(name, date_time=(2026, 10, 14, 9, 18, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, (SRC / name).read_bytes())
    atomic_bytes(ARCHIVE, buffer.getvalue())
    with ZipFile(ARCHIVE) as archive:
        bad = archive.testzip()
        names = archive.namelist()
        extracted = {name: sha_bytes(archive.read(name)) for name in names}
    assert bad is None
    assert names == list(FILES)
    assert extracted == FILES
    package_sha = sha_file(ARCHIVE)
    now = datetime.now(timezone.utc).isoformat()
    receipt = {
        "schema_version": 1,
        "id": "P11-T6-EIGHT-FILE-ARCHIVE-AFTER-ICS-20261014",
        "status": "PASS_AUTHOR_ARCHIVE_ONLY",
        "finished_at": now,
        "input_head": HEAD,
        "buyer_files": FILES,
        "package": {
            "path": str(ARCHIVE.relative_to(ROOT)),
            "sha256": package_sha,
            "file_count": len(names),
            "ordered_members": names,
            "zip_crc": "PASS",
            "extracted_sha256_match": "8_OF_8_PASS",
            "deterministic_timestamp": "2026-10-14T09:18:00+07:00",
        },
        "accepted_dependencies": {
            "prior_buyer_acceptance": "final-buyer-acceptance-20261014.json; content/numeric/native checks retained, old archive superseded",
            "ics_independent_verdict": "PASS_INDEPENDENT_ICS_CLEANUP_SCOPE_ONLY",
            "ics_receipt_sha256": "4f620ddb8e4cb276b3453eb05989386c4635569afb7d089f13e139490b4e37d8",
            "pr621_merge_commit": HEAD,
        },
        "limitations": [
            "author cannot independently accept own archive",
            "no new visual, normative, legal, native Word, delivery or production acceptance",
            "formal ARTIFACT-REGISTRY nomination remains open",
            "release HOLD; G1-G8 0/13",
        ],
        "next_step": "commit and publish isolated archive candidate; independent exact-SHA archive/composition acceptance",
        "release_authorized": False,
    }
    manifest = {
        "schema_version": 1,
        "id": "P11-T6-RELEASE-MANIFEST-AFTER-ICS-HOLD",
        "status": "HOLD",
        "input_head": HEAD,
        "package_sha256": package_sha,
        "buyer_files": FILES,
        "accepted_scope": ["archive CRC", "8/8 member SHA", "independent iCs structural correction"],
        "open_gates": ["independent archive acceptance", "full normative signoff", "ARTIFACT-REGISTRY nomination", "controlled production delivery"],
        "G1_G8_accepted_products": 0,
        "portfolio_total": 13,
        "release_authorized": False,
    }
    atomic_json(RECEIPT, receipt)
    atomic_json(HOLD, manifest)
    summary = {
        "status": receipt["status"],
        "archive_sha256": package_sha,
        "receipt_sha256": sha_file(RECEIPT),
        "hold_sha256": sha_file(HOLD),
        "members": len(names),
    }
    atomic_json(EVIDENCE / "archive-after-ics-result.json", summary)
    atomic_bytes(EVIDENCE / "archive-after-ics-exit.code", b"0\n")
    print(json.dumps(summary, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "id": "P11-T6-EIGHT-FILE-ARCHIVE-AFTER-ICS-20261014",
            "status": "FAIL",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "input_head": HEAD,
            "release_authorized": False,
        }
        atomic_json(EVIDENCE / "archive-after-ics-failure.json", failure)
        atomic_bytes(EVIDENCE / "archive-after-ics-exit.code", b"1\n")
        raise