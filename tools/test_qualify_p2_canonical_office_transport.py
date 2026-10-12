#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import qualify_p2_canonical_office_transport as subject


def make_docx(path: Path, *, missing: str | None = None, forbidden: str | None = None, duplicate: bool = False) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    members = sorted(subject.REQUIRED_MEMBERS - ({missing} if missing else set()))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in members:
            archive.writestr(name, "<root/>")
        if forbidden:
            archive.writestr(forbidden, b"x")
        if duplicate:
            archive.writestr("word/document.xml", "<root/>")
    return path.read_bytes()


def spec_for(path: str, data: bytes, registry_id: str = "R1") -> dict[str, object]:
    return {
        "registry_id": registry_id,
        "path": path,
        "nomination_commit": "abc",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob": subject.git_blob_sha1(data),
    }


class QualificationTests(unittest.TestCase):
    def test_valid_container_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = make_docx(root / "a.docx")
            result = subject.qualify_docx(root, spec_for("a.docx", data))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["duplicate_members"], [])

    def test_missing_required_member_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = make_docx(root / "a.docx", missing="word/styles.xml")
            with self.assertRaisesRegex(ValueError, "missing OOXML"):
                subject.qualify_docx(root, spec_for("a.docx", data))

    def test_duplicate_member_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = make_docx(root / "a.docx", duplicate=True)
            with self.assertRaisesRegex(ValueError, "duplicate ZIP"):
                subject.qualify_docx(root, spec_for("a.docx", data))

    def test_macro_and_encryption_members_fail(self) -> None:
        for forbidden in sorted(subject.FORBIDDEN_MEMBERS):
            with self.subTest(forbidden=forbidden), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                data = make_docx(root / "a.docx", forbidden=forbidden)
                with self.assertRaisesRegex(ValueError, "forbidden"):
                    subject.qualify_docx(root, spec_for("a.docx", data))

    def test_hash_size_and_blob_mismatches_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = make_docx(root / "a.docx")
            for key, wrong in (("bytes", 1), ("sha256", "0" * 64), ("git_blob", "0" * 40)):
                spec = spec_for("a.docx", data)
                spec[key] = wrong
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, f"{key} mismatch"):
                    subject.qualify_docx(root, spec)

    def test_failure_receipt_is_atomic_and_acceptance_stays_false(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = root / "out"
            with mock.patch.object(subject, "INPUTS", (spec_for("missing.docx", b"x"),) * 2):
                code = subject.run(root, out)
            self.assertEqual(code, 1)
            report = json.loads((out / "report.json").read_text())
            receipt = json.loads((out / "receipt.json").read_text())
            self.assertEqual(report["status"], subject.STATUS_FAIL)
            self.assertFalse(any(report["acceptance"].values()))
            self.assertEqual(receipt["status"], subject.STATUS_FAIL)
            self.assertEqual((out / "exit.code").read_text(), "1\n")
            self.assertFalse(list(out.glob(".*.tmp")))

    def test_pass_receipt_hash_chain_and_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            specs = []
            for index in range(2):
                rel = f"input-{index}.docx"
                data = make_docx(root / rel)
                specs.append(spec_for(rel, data, f"R{index}"))
            out = root / "out"
            with mock.patch.object(subject, "INPUTS", tuple(specs)):
                code = subject.run(root, out)
            self.assertEqual(code, 0)
            report = json.loads((out / "report.json").read_text())
            receipt = json.loads((out / "receipt.json").read_text())
            self.assertEqual(report["status"], subject.STATUS_PASS)
            accepted = {key for key, value in report["acceptance"].items() if value}
            self.assertEqual(accepted, {
                "exact_registry_nomination_accepted",
                "github_binary_transport_accepted",
                "docx_container_integrity_accepted",
            })
            for name, digest in receipt["hash_chain"].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)

    def test_exact_head_mismatch_writes_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.dict("os.environ", {"GITHUB_SHA": "actual"}):
                code = subject.run(root, root / "out", expected_head="expected")
            self.assertEqual(code, 1)
            report = json.loads((root / "out/report.json").read_text())
            self.assertIn("exact-head mismatch", report["failure"]["message"])


if __name__ == "__main__":
    unittest.main()
