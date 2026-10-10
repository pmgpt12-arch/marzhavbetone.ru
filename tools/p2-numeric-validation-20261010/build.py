"""Issue #580: transplant artifact_tool-generated validation nodes only.

The donor below was generated with Python artifact_tool range.data_validation.
This portable packager preserves every unrelated source XML byte and ZIP part.
It is not an Excel UI acceptance test and does not claim to block clipboard paste.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

BASE_SHA = "fd2a2b3688180989a6a8ac653eba0c8b2bcc958e"
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
SHEET = "xl/worksheets/sheet1.xml"
SOURCE_REL = Path("tools/reports/portfolio-20261010/p2-print")
SPECS = {
    "07-raschet-stoimosti.xlsx": (
        "00ff8043c0281ade1076d76285f853d53cd06ae995fdfacece533ca843bb7f3d",
        ("D4:D103", "E4:E103", "H4:H103"),
    ),
    "08-zhurnal-doprabot.xlsx": (
        "f50e316cd8e0ecb43343803112b0228f1e6584bd27fa13426c4af72972049950",
        ("F4:F103", "G4:G103"),
    ),
}
DONOR = '<dataValidations xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="5"><dataValidation type="custom" errorStyle="stop" allowBlank="1" showErrorMessage="1" errorTitle="Проверка числового ввода" error="Введите число или оставьте поле пустым" sqref="D4:D103"><formula1>OR(ISBLANK(D4),ISNUMBER(D4))</formula1></dataValidation><dataValidation type="custom" errorStyle="stop" allowBlank="1" showErrorMessage="1" errorTitle="Проверка числового ввода" error="Введите число или оставьте поле пустым" sqref="E4:E103"><formula1>OR(ISBLANK(E4),ISNUMBER(E4))</formula1></dataValidation><dataValidation type="custom" errorStyle="stop" allowBlank="1" showErrorMessage="1" errorTitle="Проверка числового ввода" error="Введите число или оставьте поле пустым" sqref="H4:H103"><formula1>OR(ISBLANK(H4),ISNUMBER(H4))</formula1></dataValidation><dataValidation type="custom" errorStyle="stop" allowBlank="1" showErrorMessage="1" errorTitle="Проверка числового ввода" error="Введите число или оставьте поле пустым" sqref="F4:F103"><formula1>OR(ISBLANK(F4),ISNUMBER(F4))</formula1></dataValidation><dataValidation type="custom" errorStyle="stop" allowBlank="1" showErrorMessage="1" errorTitle="Проверка числового ввода" error="Введите число или оставьте поле пустым" sqref="G4:G103"><formula1>OR(ISBLANK(G4),ISNUMBER(G4))</formula1></dataValidation></dataValidations>'
LATER_TAGS = {
    "hyperlinks", "printOptions", "pageMargins", "pageSetup", "headerFooter",
    "rowBreaks", "colBreaks", "customProperties", "cellWatches", "ignoredErrors",
    "smartTags", "drawing", "legacyDrawing", "legacyDrawingHF", "picture",
    "oleObjects", "controls", "webPublishItems", "tableParts", "extLst",
}
DV_RE = re.compile(r"<dataValidations\b[^>]*>.*?</dataValidations>", re.S)
ET.register_namespace("", NS)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def package_parts(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"Invalid ZIP CRC: {path.name}")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate ZIP names: {path.name}")
        return {name: archive.read(name) for name in names}


def patch_sheet(source: bytes, ranges: tuple[str, ...]) -> bytes:
    """Replace/add only the validation span; preserve all surrounding bytes."""
    text = source.decode("utf-8")
    root = ET.fromstring(source)
    if root.tag != f"{{{NS}}}worksheet" or not re.search(r"<worksheet\b", text):
        raise ValueError("Expected the pinned default-namespace worksheet")
    existing = root.find(f"{{{NS}}}dataValidations")
    donors = [entry for entry in ET.fromstring(DONOR)
              if entry.attrib["sqref"] in ranges]
    if len(donors) != len(ranges):
        raise ValueError("Donor/range mismatch")
    donor_text = "".join(ET.tostring(entry, encoding="unicode") for entry in donors)
    if existing is not None:
        matches = list(DV_RE.finditer(text))
        if len(matches) != 1:
            raise ValueError("Unexpected source validation representation")
        if any(entry.attrib.get("sqref") in ranges for entry in existing):
            raise ValueError("Numeric range is already validated")
        old_count = int(existing.attrib["count"])
        if old_count != len(existing):
            raise ValueError("Source count mismatch")
        match = matches[0]
        old = match.group()
        updated = re.sub(r'\bcount="\d+"', f'count="{old_count + len(donors)}"',
                         old, count=1)
        updated = updated.replace("</dataValidations>",
                                  donor_text + "</dataValidations>")
        result = text[:match.start()] + updated + text[match.end():]
    else:
        block = f'<dataValidations count="{len(donors)}">' + donor_text + "</dataValidations>"
        later = next((c.tag.rsplit("}", 1)[-1] for c in root
                      if c.tag.rsplit("}", 1)[-1] in LATER_TAGS), None)
        token = re.search(r"<" + re.escape(later) + r"\b", text) if later else None
        at = token.start() if token else text.rfind("</worksheet>")
        if at < 0:
            raise ValueError("No insertion point")
        result = text[:at] + block + text[at:]
    ET.fromstring(result)
    return result.encode("utf-8")


def build(source_root: Path, output_dir: Path) -> dict:
    source_dir = source_root / SOURCE_REL
    source_bytes = {name: (source_dir / name).read_bytes() for name in SPECS}
    for name, (expected, _) in SPECS.items():
        if sha256(source_bytes[name]) != expected:
            raise ValueError(f"Pinned input hash mismatch: {name}")
    if output_dir.resolve() == source_dir.resolve():
        raise ValueError("Output must not replace source")
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "source_issue": 580, "parent_issue": 291, "base_sha": BASE_SHA,
        "definition_origin": "Python artifact_tool range.data_validation export",
        "definition_sha256": sha256(DONOR.encode("utf-8")),
        "scope": "STRUCTURAL_VALIDATION_AND_PRESERVATION_ONLY",
        "numeric_input_cells": 500, "files": [],
        "not_verified": [
            "native Microsoft Excel typed input", "clipboard paste handling",
            "filled form printing", "independent product acceptance",
            "normative acceptance", "release",
        ],
        "next_step": "Independent exact-SHA review; native Excel and buyer gates remain open",
    }
    for name, (expected, ranges) in SPECS.items():
        source_path, target = source_dir / name, output_dir / name
        original = package_parts(source_path)
        patched = patch_sheet(original[SHEET], ranges)
        temporary = target.with_suffix(".xlsx.tmp")
        try:
            with zipfile.ZipFile(source_path) as source_zip, zipfile.ZipFile(temporary, "w") as dest_zip:
                dest_zip.comment = source_zip.comment
                for info in source_zip.infolist():
                    dest_zip.writestr(copy.copy(info),
                                      patched if info.filename == SHEET else original[info.filename])
            produced = package_parts(temporary)
            changed = [part for part in original if original[part] != produced[part]]
            if changed != [SHEET] or original.keys() != produced.keys():
                raise ValueError(f"Unexpected ZIP delta: {name}: {changed}")
            temporary.replace(target)
        finally:
            if temporary.exists():
                temporary.unlink()
        receipt["files"].append({
            "file": name, "input_sha256": expected,
            "output_sha256": sha256(target.read_bytes()),
            "new_numeric_ranges": list(ranges),
            "changed_parts": [SHEET],
            "formula": "OR(ISBLANK(relative_top_left),ISNUMBER(relative_top_left))",
            "allows": ["blank", "zero", "negative", "positive"],
        })
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = build(args.source_root, args.output_dir)
    print(json.dumps({"scope": result["scope"], "files": result["files"]}, ensure_ascii=False))
