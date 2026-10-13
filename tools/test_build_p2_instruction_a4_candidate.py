#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import build_p2_instruction_a4_candidate as subject


def make_source(path: Path, pg_size: bytes = subject.SOURCE_PGSZ) -> bytes:
    document = b'<w:document xmlns:w="' + subject.W_NS.encode() + b'"><w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p><w:sectPr>' + pg_size + b'</w:sectPr></w:body></w:document>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", b"types")
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", b"styles")
    return path.read_bytes()


class CandidateBuilderTests(unittest.TestCase):
    def test_exact_one_member_change_and_text_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.docx"
            data = make_source(source)
            output = root / "candidate.docx"
            with mock.patch.object(subject, "EXPECTED_SOURCE_SHA256", hashlib.sha256(data).hexdigest()):
                report = subject.build_candidate(source, output)
            self.assertEqual(report["changed_members"], ["word/document.xml"])
            self.assertEqual(report["unchanged_member_count"], 2)
            self.assertTrue(report["text_sequence_unchanged"])
            with zipfile.ZipFile(output) as archive:
                document = archive.read("word/document.xml")
            self.assertEqual(document.count(subject.A4_PGSZ), 1)
            self.assertNotIn(subject.SOURCE_PGSZ, document)

    def test_source_bytes_remain_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.docx"
            data = make_source(source)
            with mock.patch.object(subject, "EXPECTED_SOURCE_SHA256", hashlib.sha256(data).hexdigest()):
                subject.build_candidate(source, root / "candidate.docx")
            self.assertEqual(source.read_bytes(), data)

    def test_repeated_build_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.docx"
            data = make_source(source)
            with mock.patch.object(subject, "EXPECTED_SOURCE_SHA256", hashlib.sha256(data).hexdigest()):
                subject.build_candidate(source, root / "first.docx")
                subject.build_candidate(source, root / "second.docx")
            self.assertEqual((root / "first.docx").read_bytes(), (root / "second.docx").read_bytes())

    def test_source_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.docx"
            make_source(source)
            with self.assertRaisesRegex(ValueError, "source SHA256 mismatch"):
                subject.build_candidate(source, Path(temporary) / "candidate.docx")

    def test_wrong_or_duplicate_page_size_fails_closed(self) -> None:
        for page_size in (subject.A4_PGSZ, subject.SOURCE_PGSZ + subject.SOURCE_PGSZ):
            with self.subTest(page_size=page_size), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "source.docx"
                data = make_source(source, page_size)
                with mock.patch.object(subject, "EXPECTED_SOURCE_SHA256", hashlib.sha256(data).hexdigest()), self.assertRaisesRegex(ValueError, "exactly one nominated Letter"):
                    subject.build_candidate(source, root / "candidate.docx")

    def test_atomic_json_report_has_no_temporary_residue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            subject.atomic_write_json(path, {"status": "PASS"})
            self.assertEqual(json.loads(path.read_text()), {"status": "PASS"})
            self.assertFalse(list(Path(temporary).glob(".*.tmp")))


if __name__ == "__main__":
    unittest.main()
