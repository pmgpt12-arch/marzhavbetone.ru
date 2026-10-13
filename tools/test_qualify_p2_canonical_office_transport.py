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


def make_registry(root: Path, specs: tuple[dict[str, object], ...], *, drift: bool = False) -> bytes:
    records = [subject.expected_registry_record(spec) for spec in specs]
    if drift:
        records[0]["office_status"] = "PASS"
    path = root / subject.REGISTRY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps({"registry_status": "ACTIVE_PARTIAL_SEED", "artifacts": records}, indent=2) + "\n").encode()
    path.write_bytes(data)
    return data


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
            specs = (spec_for("missing.docx", b"x", "R1"), spec_for("missing2.docx", b"y", "R2"))
            registry = make_registry(root, specs)
            with mock.patch.object(subject, "INPUTS", specs), mock.patch.object(
                subject, "EXPECTED_REGISTRY_BLOB", subject.git_blob_sha1(registry)
            ):
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
            specs_tuple = tuple(specs)
            registry = make_registry(root, specs_tuple)
            out = root / "out"
            with mock.patch.object(subject, "INPUTS", specs_tuple), mock.patch.object(
                subject, "EXPECTED_REGISTRY_BLOB", subject.git_blob_sha1(registry)
            ):
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
            specs = (spec_for("a.docx", b"x", "R1"), spec_for("b.docx", b"y", "R2"))
            registry = make_registry(root, specs)
            with mock.patch.object(subject, "INPUTS", specs), mock.patch.object(
                subject, "EXPECTED_REGISTRY_BLOB", subject.git_blob_sha1(registry)
            ), mock.patch.object(subject, "checked_out_head", return_value="actual"):
                code = subject.run(root, root / "out", expected_head="expected")
            self.assertEqual(code, 1)
            report = json.loads((root / "out/report.json").read_text())
            self.assertIn("exact-head mismatch", report["failure"]["message"])

    def test_registry_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            specs = (spec_for("a.docx", b"x", "R1"), spec_for("b.docx", b"y", "R2"))
            registry = make_registry(root, specs, drift=True)
            with mock.patch.object(subject, "INPUTS", specs), mock.patch.object(
                subject, "EXPECTED_REGISTRY_BLOB", subject.git_blob_sha1(registry)
            ), self.assertRaisesRegex(ValueError, "records do not exactly match"):
                subject.qualify_registry(root)



class RegistryHistoryQualificationTests(unittest.TestCase):
    def check_with_mutation(self, mutation, expect_pass):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            specs=(spec_for("a.docx",b"a","R1"),spec_for("b.docx",b"b","R2"))
            baseline=make_registry(root,specs)
            identity=subject.registry_identity_sha256(json.loads(baseline))
            data=json.loads(baseline);data["change_history"]={"audit_note":"new metadata only"}
            mutation(data)
            (root/subject.REGISTRY_PATH).write_text(json.dumps(data))
            with mock.patch.object(subject,"INPUTS",specs),mock.patch.object(subject,"EXPECTED_REGISTRY_IDENTITY_SHA256",identity):
                if expect_pass:self.assertEqual(subject.qualify_registry(root)["status"],"PASS")
                else:
                    with self.assertRaises(ValueError):subject.qualify_registry(root)

    def test_history_only_append_preserves_nomination(self):
        self.check_with_mutation(lambda d: None,True)

    def test_history_cannot_hide_document_sha_change(self):
        self.check_with_mutation(lambda d:d["artifacts"][0].update(sha256="0"*64),False)

    def test_history_cannot_hide_unknown_registry_field(self):
        self.check_with_mutation(lambda d:d.update(unapproved_scope="changed"),False)


if __name__ == "__main__":
    unittest.main()
