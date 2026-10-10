"""Offline acceptance for #580. No Excel UI or financial/legal verdict."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import build

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
N = {"m": build.NS}
EXPECTED = {
    "07-raschet-stoimosti.xlsx": ["D4:D103", "E4:E103", "H4:H103"],
    "08-zhurnal-doprabot.xlsx": ["F4:F103", "G4:G103"],
}


def read_parts(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise AssertionError("ZIP CRC failed")
        return {name: archive.read(name) for name in archive.namelist()}


def strip_validations(xml: bytes) -> bytes:
    return re.sub(rb"<dataValidations\b[^>]*>.*?</dataValidations>", b"", xml, flags=re.S)


class ValidationAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = {name: read_parts(ROOT / build.SOURCE_REL / name) for name in EXPECTED}
        cls.output = {name: read_parts(HERE / name) for name in EXPECTED}
        cls.receipt = json.loads((HERE / "receipt.json").read_text(encoding="utf-8"))

    def test_01_pinned_input_hashes(self):
        for name, (sha, _) in build.SPECS.items():
            self.assertEqual(hashlib.sha256((ROOT / build.SOURCE_REL / name).read_bytes()).hexdigest(), sha)

    def test_02_all_xml_and_zip_integrity(self):
        for parts in self.output.values():
            for name, value in parts.items():
                if name.endswith((".xml", ".rels")):
                    ET.fromstring(value)

    def test_03_only_one_part_changes(self):
        for name in EXPECTED:
            before, after = self.original[name], self.output[name]
            self.assertEqual(list(before), list(after))
            self.assertEqual([p for p in before if before[p] != after[p]], [build.SHEET])

    def test_04_every_other_sheet_byte_preserved(self):
        for name in EXPECTED:
            self.assertEqual(strip_validations(self.original[name][build.SHEET]),
                             strip_validations(self.output[name][build.SHEET]))

    def test_05_exact_count_and_numeric_rules(self):
        for name, ranges in EXPECTED.items():
            root = ET.fromstring(self.output[name][build.SHEET])
            container = root.find("m:dataValidations", N)
            entries = list(container)
            expected_count = 3 if name.startswith("07") else 5
            self.assertEqual(int(container.attrib["count"]), expected_count)
            self.assertEqual(len(entries), expected_count)
            numeric = [e for e in entries if e.attrib["type"] == "custom"]
            self.assertEqual([e.attrib["sqref"] for e in numeric], ranges)
            for entry, target in zip(numeric, ranges):
                first = target.split(":")[0]
                self.assertEqual(entry.find("m:formula1", N).text,
                                 f"OR(ISBLANK({first}),ISNUMBER({first}))")
                self.assertEqual(entry.attrib["allowBlank"], "1")
                self.assertEqual(entry.attrib["showErrorMessage"], "1")
                self.assertEqual(entry.attrib["errorStyle"], "stop")
                self.assertEqual(entry.attrib["error"], "Введите число или оставьте поле пустым")
                self.assertIsNone(entry.find("m:formula2", N))

    def test_06_all_500_numeric_cells_covered(self):
        total = 0
        for name, ranges in EXPECTED.items():
            covered = set()
            root = ET.fromstring(self.output[name][build.SHEET])
            for entry in root.findall("m:dataValidations/m:dataValidation", N):
                if entry.attrib["type"] != "custom":
                    continue
                match = re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", entry.attrib["sqref"])
                self.assertIsNotNone(match)
                a, lo, b, hi = match.groups()
                self.assertEqual(a, b)
                cells = {f"{a}{row}" for row in range(int(lo), int(hi) + 1)}
                self.assertFalse(covered.intersection(cells))
                covered.update(cells)
            expected = {f"{r.split(':')[0][0]}{row}" for r in ranges for row in range(4, 104)}
            self.assertEqual(covered, expected)
            total += len(covered)
        self.assertEqual(total, 500)

    def test_07_existing_status_lists_unchanged(self):
        name = "08-zhurnal-doprabot.xlsx"
        before = ET.fromstring(self.original[name][build.SHEET]).findall("m:dataValidations/m:dataValidation", N)
        after = ET.fromstring(self.output[name][build.SHEET]).findall("m:dataValidations/m:dataValidation", N)
        self.assertEqual([ET.tostring(e) for e in before],
                         [ET.tostring(e) for e in after if e.attrib["type"] == "list"])

    def test_08_validation_schema_position(self):
        for name in EXPECTED:
            children = list(ET.fromstring(self.output[name][build.SHEET]))
            tags = [e.tag.rsplit("}", 1)[-1] for e in children]
            position = tags.index("dataValidations")
            self.assertTrue(all(i < position for i, tag in enumerate(tags)
                                if tag == "conditionalFormatting"))
            self.assertTrue(all(i > position for i, tag in enumerate(tags)
                                if tag in build.LATER_TAGS))

    def test_09_formulas_and_native_features_unchanged(self):
        for name in EXPECTED:
            a = ET.fromstring(self.original[name][build.SHEET])
            b = ET.fromstring(self.output[name][build.SHEET])
            for selector in ["m:sheetData", "m:sheetProtection", "m:conditionalFormatting",
                             "m:printOptions", "m:pageMargins", "m:pageSetup"]:
                self.assertEqual([ET.tostring(e) for e in a.findall(selector, N)],
                                 [ET.tostring(e) for e in b.findall(selector, N)])
            for part in ["xl/styles.xml", "xl/workbook.xml", "xl/worksheets/sheet2.xml"]:
                self.assertEqual(self.original[name][part], self.output[name][part])

    def test_10_receipt_matches_files(self):
        self.assertEqual(self.receipt["numeric_input_cells"], 500)
        self.assertEqual(self.receipt["source_issue"], 580)
        self.assertIn("STRUCTURAL", self.receipt["scope"])
        self.assertIn("clipboard paste handling", self.receipt["not_verified"])
        for item in self.receipt["files"]:
            actual = hashlib.sha256((HERE / item["file"]).read_bytes()).hexdigest()
            self.assertEqual(item["output_sha256"], actual)
            self.assertEqual(item["allows"], ["blank", "zero", "negative", "positive"])

    def test_11_two_independent_builds_are_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            one, two = Path(temp) / "one", Path(temp) / "two"
            build.build(ROOT, one)
            build.build(ROOT, two)
            for name in [*EXPECTED, "receipt.json"]:
                self.assertEqual((one / name).read_bytes(), (two / name).read_bytes())
                self.assertEqual((one / name).read_bytes(), (HERE / name).read_bytes())

    def test_12_exact_five_artifacts(self):
        expected = {"build.py", "test_numeric_validation.py", "receipt.json", *EXPECTED}
        self.assertEqual({p.name for p in HERE.iterdir()}, expected)

    def test_13_input_tampering_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            fake_root, output = Path(temp) / "root", Path(temp) / "output"
            inputs = fake_root / build.SOURCE_REL
            inputs.mkdir(parents=True)
            for name in EXPECTED:
                data = (ROOT / build.SOURCE_REL / name).read_bytes()
                (inputs / name).write_bytes(data + b"changed")
            with self.assertRaisesRegex(ValueError, "Pinned input hash mismatch"):
                build.build(fake_root, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
