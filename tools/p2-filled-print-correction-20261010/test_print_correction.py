"""Offline structural acceptance for the P2 print correction."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import build

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(element: ET.Element) -> tuple:
    return (
        element.tag,
        tuple(sorted(element.attrib.items())),
        element.text or "",
        element.tail or "",
        tuple(signature(child) for child in element),
    )


def restore_register_changes(source: ET.Element, candidate: ET.Element) -> None:
    source_setup_pr = source.find(f"{{{build.NS}}}sheetPr/{{{build.NS}}}pageSetUpPr")
    candidate_setup_pr = candidate.find(f"{{{build.NS}}}sheetPr/{{{build.NS}}}pageSetUpPr")
    if source_setup_pr is not None and candidate_setup_pr is not None:
        if "fitToPage" in source_setup_pr.attrib:
            candidate_setup_pr.set("fitToPage", source_setup_pr.attrib["fitToPage"])
        else:
            candidate_setup_pr.attrib.pop("fitToPage", None)

    source_rows = {
        int(row.get("r", "0")): row
        for row in source.findall(f".//{{{build.NS}}}sheetData/{{{build.NS}}}row")
    }
    for row in candidate.findall(f".//{{{build.NS}}}sheetData/{{{build.NS}}}row"):
        number = int(row.get("r", "0"))
        if 4 <= number <= 103:
            for attribute in ("ht", "customHeight"):
                if attribute in source_rows[number].attrib:
                    row.set(attribute, source_rows[number].attrib[attribute])
                else:
                    row.attrib.pop(attribute, None)

    source_setup = source.find(f"{{{build.NS}}}pageSetup")
    candidate_setup = candidate.find(f"{{{build.NS}}}pageSetup")
    if source_setup is None or candidate_setup is None:
        raise AssertionError("pageSetup must exist")
    candidate_setup.attrib.clear()
    candidate_setup.attrib.update(source_setup.attrib)


def restore_instruction_changes(source: ET.Element, candidate: ET.Element) -> None:
    source_setup_pr = source.find(f"{{{build.NS}}}sheetPr/{{{build.NS}}}pageSetUpPr")
    candidate_setup_pr = candidate.find(f"{{{build.NS}}}sheetPr/{{{build.NS}}}pageSetUpPr")
    if source_setup_pr is not None and candidate_setup_pr is not None:
        if "fitToPage" in source_setup_pr.attrib:
            candidate_setup_pr.set("fitToPage", source_setup_pr.attrib["fitToPage"])
        else:
            candidate_setup_pr.attrib.pop("fitToPage", None)
    source_row = source.find(f".//{{{build.NS}}}sheetData/{{{build.NS}}}row[@r='3']")
    candidate_row = candidate.find(f".//{{{build.NS}}}sheetData/{{{build.NS}}}row[@r='3']")
    if source_row is None or candidate_row is None:
        raise AssertionError("instruction row 3 must exist")
    for attribute in ("ht", "customHeight"):
        if attribute in source_row.attrib:
            candidate_row.set(attribute, source_row.attrib[attribute])
        else:
            candidate_row.attrib.pop(attribute, None)
    source_setup = source.find(f"{{{build.NS}}}pageSetup")
    candidate_setup = candidate.find(f"{{{build.NS}}}pageSetup")
    if source_setup is None or candidate_setup is None:
        raise AssertionError("instruction pageSetup must exist")
    candidate_setup.attrib.clear()
    candidate_setup.attrib.update(source_setup.attrib)


class PrintCorrectionAcceptance(unittest.TestCase):
    def test_01_acceptance_receipt_is_bounded(self):
        receipt = json.loads((HERE / "acceptance.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "PASS_ROOT_V2_PENDING_INDEPENDENT")
        self.assertEqual(receipt["model_calls"], 0)
        self.assertTrue(receipt["no_paid_api"])
        self.assertIn("native Microsoft Excel typed, paste, UI or print behavior", receipt["not_accepted"])
        self.assertIn("product or release acceptance", receipt["not_accepted"])
        self.assertIn("publication, price, SKU, checkout or delivery", receipt["not_accepted"])

    def test_02_pinned_input_and_output_hashes(self):
        for name, spec in build.SPECS.items():
            self.assertEqual(sha256(ROOT / build.SOURCE_REL / name), spec["input_sha256"])
            self.assertEqual(sha256(HERE / name), spec["output_sha256"])

    def test_03_zip_integrity_and_only_approved_sheets_change(self):
        for name in build.SPECS:
            with zipfile.ZipFile(ROOT / build.SOURCE_REL / name) as source_zip, zipfile.ZipFile(HERE / name) as candidate_zip:
                self.assertIsNone(source_zip.testzip())
                self.assertIsNone(candidate_zip.testzip())
                self.assertEqual(source_zip.namelist(), candidate_zip.namelist())
                changed = [entry for entry in source_zip.namelist() if source_zip.read(entry) != candidate_zip.read(entry)]
                self.assertEqual(changed, [build.REGISTER_SHEET, build.INSTRUCTION_SHEET])

    def test_04_only_page_setup_and_auto_height_semantics_change(self):
        for name in build.SPECS:
            with zipfile.ZipFile(ROOT / build.SOURCE_REL / name) as source_zip, zipfile.ZipFile(HERE / name) as candidate_zip:
                source_register = ET.fromstring(source_zip.read(build.REGISTER_SHEET))
                candidate_register = ET.fromstring(candidate_zip.read(build.REGISTER_SHEET))
                normalized_register = deepcopy(candidate_register)
                restore_register_changes(source_register, normalized_register)
                self.assertEqual(signature(source_register), signature(normalized_register), name)
                source_instruction = ET.fromstring(source_zip.read(build.INSTRUCTION_SHEET))
                candidate_instruction = ET.fromstring(candidate_zip.read(build.INSTRUCTION_SHEET))
                normalized_instruction = deepcopy(candidate_instruction)
                restore_instruction_changes(source_instruction, normalized_instruction)
                self.assertEqual(signature(source_instruction), signature(normalized_instruction), name)

    def test_05_exact_page_setup_and_auto_height_rows(self):
        for name, spec in build.SPECS.items():
            with zipfile.ZipFile(HERE / name) as archive:
                root = ET.fromstring(archive.read(build.REGISTER_SHEET))
            setup = root.find(f"{{{build.NS}}}pageSetup")
            self.assertEqual(setup.attrib, {
                "paperSize": "8",
                "orientation": "landscape",
                "scale": str(spec["scale"]),
                "horizontalDpi": "300",
                "verticalDpi": "300",
            })
            setup_pr = root.find(f"{{{build.NS}}}sheetPr/{{{build.NS}}}pageSetUpPr")
            if setup_pr is not None:
                self.assertNotIn("fitToPage", setup_pr.attrib)
            for row in root.findall(f".//{{{build.NS}}}sheetData/{{{build.NS}}}row"):
                number = int(row.get("r", "0"))
                if 4 <= number <= 103:
                    self.assertNotIn("ht", row.attrib)
                    self.assertNotIn("customHeight", row.attrib)
            with zipfile.ZipFile(HERE / name) as archive:
                instruction = ET.fromstring(archive.read(build.INSTRUCTION_SHEET))
            instruction_setup = instruction.find(f"{{{build.NS}}}pageSetup")
            self.assertEqual(instruction_setup.attrib, {
                "paperSize": "9",
                "orientation": "landscape",
                "scale": "100",
                "horizontalDpi": "300",
                "verticalDpi": "300",
            })
            instruction_setup_pr = instruction.find(f"{{{build.NS}}}sheetPr/{{{build.NS}}}pageSetUpPr")
            if instruction_setup_pr is not None:
                self.assertNotIn("fitToPage", instruction_setup_pr.attrib)
            instruction_row = instruction.find(f".//{{{build.NS}}}sheetData/{{{build.NS}}}row[@r='3']")
            self.assertIsNotNone(instruction_row)
            self.assertNotIn("ht", instruction_row.attrib)
            self.assertNotIn("customHeight", instruction_row.attrib)

    def test_06_formula_validation_protection_and_style_counts(self):
        expected = {
            "07-raschet-stoimosti.xlsx": (202, 3, 1031),
            "08-zhurnal-doprabot.xlsx": (0, 5, 1237),
        }
        for name, (formula_count, validation_count, cell_count) in expected.items():
            with zipfile.ZipFile(HERE / name) as archive:
                root = ET.fromstring(archive.read(build.REGISTER_SHEET))
            self.assertEqual(len(root.findall(f".//{{{build.NS}}}f")), formula_count)
            validations = root.find(f"{{{build.NS}}}dataValidations")
            self.assertEqual(int(validations.get("count")), validation_count)
            self.assertIsNotNone(root.find(f"{{{build.NS}}}sheetProtection"))
            self.assertEqual(len(root.findall(f".//{{{build.NS}}}c")), cell_count)

    def test_07_build_is_byte_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            build.build(ROOT, target)
            for name, spec in build.SPECS.items():
                self.assertEqual(sha256(target / name), spec["output_sha256"])
                self.assertEqual((target / name).read_bytes(), (HERE / name).read_bytes())

    def test_08_tampered_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_root = Path(directory)
            source_dir = fake_root / build.SOURCE_REL
            source_dir.mkdir(parents=True)
            for name in build.SPECS:
                data = (ROOT / build.SOURCE_REL / name).read_bytes()
                (source_dir / name).write_bytes(data + b"tamper")
            with self.assertRaises(ValueError):
                build.build(fake_root, fake_root / "out")

    def test_09_render_evidence_hashes_are_pinned(self):
        expected = {
            "evidence/07-raschet-stoimosti-filled-print-v2.pdf": "6eca6e46ecd0cc5caaf38018b823f26501200e39b7346dbea86f7d0b12d6b0b9",
            "evidence/08-zhurnal-doprabot-filled-print-v2.pdf": "700007f3d0518eef4b87c714987f694098b05274f96293de40dcee7a2b4b6381",
            "evidence/07-contact.jpg": "c4c92fdd38e856e20f307b53d08322cc8b8a6231d26c52628f16857419cc4612",
            "evidence/08-contact.jpg": "5b0890fec0ce96bc0a3730defc90b9dc1a8a47eb3c9ab6080ce1d60ebfe8e19d",
        }
        for relative_path, expected_hash in expected.items():
            self.assertEqual(sha256(HERE / relative_path), expected_hash)

    def test_10_independent_acceptance_is_exact_and_bounded(self):
        path = HERE / "independent-acceptance.json"
        self.assertEqual(
            sha256(path),
            "8d15485c9c57c789f591fbc1a72fa27014402939995bcc565224190662f5792e",
        )
        receipt = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "PASS_INDEPENDENT_V2_SCOPE_ONLY")
        self.assertEqual(receipt["reviewed_root_receipt"]["sha256"],
                         "d09d737bfd7cccfce02b41ca7fd50686c4b3e10071750a7d9a1b148b96098b35")
        self.assertEqual(receipt["model_calls"], 0)
        self.assertTrue(receipt["no_paid_api"])
        self.assertFalse(receipt["merge_performed"])
        self.assertFalse(receipt["publication_performed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
