#!/usr/bin/env python3
"""Read-only P8 edition gate: independent owner acceptance beats candidate SHA_PASS.

Trust anchors are exact immutable Git commit/path and SHA; edited staging metadata,
QA01's own correctly computed SHA, and historical release authority do not open sales.
"""
from __future__ import annotations

import hashlib
import io
import json
import pathlib
import subprocess
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent

# Independent 2026-10-20 acceptance: immutable existing Git record.
OWNER_COMMIT = "bf40053356b8bc1ab81eaab197dbbebf4068c752"
OWNER_RECEIPT = "tools/candidates/remaining-batch-r3-20261018/release-20261020/owner-acceptance.json"
OWNER_MANIFEST = "tools/candidates/remaining-batch-r3-20261018/final-buyer-review-20261020/P8-manifest-R3.json"
OWNER_ARCHIVE = "tools/candidates/remaining-batch-r3-20261018/final-buyer-review-20261020/P8-buyer-review-R3-20261020.zip"
ACCEPTED_EDITION_ID = "P8-R3-20261020-WHOLE-OWNER-ACCEPTED"
ACCEPTED_ZIP_SHA = "a22b2a2fc4dec5e51298d2582b22608252948ff70cc30d47b47c7c346936bc76"


class EditionEvidenceError(ValueError):
    """Fail closed on absent/forged/inconsistent acceptance evidence."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def original_git_bytes(path: str) -> bytes:
    process = subprocess.run(
        ["git", "-C", str(ROOT), "show", OWNER_COMMIT + ":" + path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40,
    )
    if process.returncode:
        raise EditionEvidenceError("ORIGINAL_GIT_PROOF_MISSING:" + path)
    return process.stdout


def archive_members(data: bytes) -> dict[str, str]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if z.testzip() is not None:
                raise EditionEvidenceError("ZIP_CRC_INVALID")
            names = [n for n in z.namelist() if not n.endswith("/")]
            if len(names) != len(set(names)):
                raise EditionEvidenceError("DUPLICATE_MEMBER_NAME")
            return {n: sha(z.read(n)) for n in names}
    except (zipfile.BadZipFile, EOFError) as ex:
        raise EditionEvidenceError("ZIP_INVALID") from ex


def accepted_contract(anchor: dict | None = None) -> dict:
    """Resolve and independently verify all four acceptance factors.

    No editable local JSON can approve QA01 by changing a declared SHA/edition.
    The original R3 evidence itself remains historical, not a current-site ALLOW.
    """
    if anchor is None:
        anchor = json.loads((HERE / "P8_ACCEPTED_EDITION_ANCHOR.json").read_text("utf-8"))
    evidence = anchor.get("ACCEPTANCE_EVIDENCE") or {}
    source = anchor.get("ARCHIVE_SOURCE_GIT") or {}
    manifest = anchor.get("MEMBER_MANIFEST_GIT") or {}
    if any((
        anchor.get("SKU") != "P8",
        anchor.get("ACCEPTED_EDITION_ID") != ACCEPTED_EDITION_ID,
        anchor.get("ARCHIVE_SHA256") != ACCEPTED_ZIP_SHA,
        anchor.get("MEMBER_COUNT") != 11,
        anchor.get("RELEASE_PERMISSION") != "HOLD",
        anchor.get("ALLOW_NEW_SALES") is not False,
        evidence.get("commit") != OWNER_COMMIT,
        evidence.get("path") != OWNER_RECEIPT,
        source != {"commit": OWNER_COMMIT, "path": OWNER_ARCHIVE},
        manifest != {"commit": OWNER_COMMIT, "path": OWNER_MANIFEST},
        not isinstance(anchor.get("MEMBER_SHA256"), dict),
        len(anchor.get("MEMBER_SHA256", {})) != 11,
    )):
        raise EditionEvidenceError("P8_EDITABLE_ANCHOR_NOT_PINNED_TO_ORIGINAL_OWNER_DECISION")

    receipt_raw = original_git_bytes(OWNER_RECEIPT)
    if evidence.get("sha256") != sha(receipt_raw):
        raise EditionEvidenceError("ORIGINAL_OWNER_EVIDENCE_SHA_MISMATCH")
    receipt = json.loads(receipt_raw)
    packages = [p for p in receipt.get("packages", []) if p.get("sku") == "P8"]
    if receipt.get("status") != "OWNER_ACCEPTED_AND_RELEASE_AUTHORIZED" or len(packages) != 1:
        raise EditionEvidenceError("WHOLE_PACKAGE_OWNER_DECISION_MISSING")
    package = packages[0]
    if (package.get("sha256") != ACCEPTED_ZIP_SHA or
        package.get("file_count") != 11 or
        package.get("archive") != OWNER_ARCHIVE.rsplit("/", 1)[-1]):
        raise EditionEvidenceError("OWNER_ACCEPTED_SHA_COUNT_OR_NAME_MISMATCH")

    source_manifest = json.loads(original_git_bytes(OWNER_MANIFEST))
    expected = {m["file"]: m["sha256"] for m in source_manifest["members"]}
    if (source_manifest["sha256"] != ACCEPTED_ZIP_SHA or
        source_manifest["file_count"] != 11 or
        len(expected) != 11 or
        expected != anchor["MEMBER_SHA256"]):
        raise EditionEvidenceError("OWNER_MANIFEST_MEMBER_SHA_MISMATCH")

    original_archive = original_git_bytes(OWNER_ARCHIVE)
    if sha(original_archive) != ACCEPTED_ZIP_SHA:
        raise EditionEvidenceError("OWNER_ORIGINAL_ARCHIVE_SHA_MISMATCH")
    if archive_members(original_archive) != expected:
        raise EditionEvidenceError("OWNER_ORIGINAL_ZIP_CRC_COMPOSITION_OR_MEMBER_SHA_MISMATCH")
    return {
        "ACCEPTED_EDITION_ID": ACCEPTED_EDITION_ID,
        "ACCEPTANCE_EVIDENCE": {"commit": OWNER_COMMIT, "path": OWNER_RECEIPT,
                                "sha256": sha(receipt_raw)},
        "ARCHIVE_SHA256": ACCEPTED_ZIP_SHA,
        "MEMBER_SHA256": expected,
        "RELEASE_PERMISSION": "HOLD",
        "scope": "HISTORICAL_WHOLE_OWNER_ACCEPTED_NOT_NEW_SITE_RELEASE",
    }


def check_p8_edition(actual_archive: bytes, claimed_edition_id: str,
                     anchor: dict | None = None) -> dict:
    """Returns EDITION_NOT_ACCEPTED for correct QA01 SHA and composition.

    A matching *historical* R3 returns HISTORICAL_EDITION_ACCEPTED_HOLD,
    NEVER buyer permission or approval of later mixed files.
    """
    try:
        accepted = accepted_contract(anchor)
    except (EditionEvidenceError, json.JSONDecodeError, OSError, KeyError,
            subprocess.TimeoutExpired, ValueError) as ex:
        return {"status": "ACCEPTANCE_EVIDENCE_INVALID",
                "reason": type(ex).__name__ + ":" + str(ex)[:180],
                "RELEASE_PERMISSION": "HOLD", "eligible_for_new_sales": False}

    try:
        actual_members = archive_members(actual_archive)
    except EditionEvidenceError as ex:
        return {"status": "EDITION_NOT_ACCEPTED", "reason": str(ex),
                "ARCHIVE_SHA256": sha(actual_archive),
                "ACCEPTED_EDITION_ID": accepted["ACCEPTED_EDITION_ID"],
                "RELEASE_PERMISSION": "HOLD", "eligible_for_new_sales": False}

    same_id = claimed_edition_id == accepted["ACCEPTED_EDITION_ID"]
    same_archive = sha(actual_archive) == accepted["ARCHIVE_SHA256"]
    same_members = actual_members == accepted["MEMBER_SHA256"]
    verdict = ("HISTORICAL_EDITION_ACCEPTED_HOLD"
               if same_id and same_archive and same_members else "EDITION_NOT_ACCEPTED")
    return {
        "status": verdict,
        "claimed_edition_id": claimed_edition_id,
        "ACCEPTED_EDITION_ID": accepted["ACCEPTED_EDITION_ID"],
        "ACCEPTANCE_EVIDENCE": accepted["ACCEPTANCE_EVIDENCE"],
        "ARCHIVE_SHA256": sha(actual_archive),
        "owner_accepted_archive_sha256": accepted["ARCHIVE_SHA256"],
        "edition_id_match": same_id,
        "archive_sha_match": same_archive,
        "member_sha_match": same_members,
        "member_count": len(actual_members),
        "expected_member_count": len(accepted["MEMBER_SHA256"]),
        "RELEASE_PERMISSION": "HOLD",
        "eligible_for_new_sales": False,
    }
