"""Build the narrow P2 filled-print correction from PR #581 candidates."""
from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REGISTER_SHEET = "xl/worksheets/sheet1.xml"
INSTRUCTION_SHEET = "xl/worksheets/sheet2.xml"
SOURCE_REL = Path("tools/p2-numeric-validation-20261010")
SPECS = {
    "07-raschet-stoimosti.xlsx": {
        "input_sha256": "f2ed0b234111a717eded1d214ddc9c60eb113be51c51c09a75f7d7a641d47134",
        "output_sha256": "d751c8c6326da23b39a4024ec9548ed9b88ed357b7158980c6930897fd7e808f",
        "scale": 120,
    },
    "08-zhurnal-doprabot.xlsx": {
        "input_sha256": "f18c1e71dced81ebe6fe4f95d978a3dada5d04c4778bdbdd1bd15a1f1c7f27e2",
        "output_sha256": "d9f6b1d94eb04dbb5283572c6446926f9d424753deb50f6a517a2f75278cc20c",
        "scale": 60,
    },
}
ET.register_namespace("x", NS)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_register(xml_bytes: bytes, scale: int) -> bytes:
    root = ET.fromstring(xml_bytes)
    setup_pr = root.find(f"{{{NS}}}sheetPr/{{{NS}}}pageSetUpPr")
    if setup_pr is not None:
        setup_pr.attrib.pop("fitToPage", None)
    for row in root.findall(f".//{{{NS}}}sheetData/{{{NS}}}row"):
        number = int(row.get("r", "0"))
        if 4 <= number <= 103:
            row.attrib.pop("ht", None)
            row.attrib.pop("customHeight", None)
    page_setup = root.find(f"{{{NS}}}pageSetup")
    if page_setup is None:
        page_setup = ET.SubElement(root, f"{{{NS}}}pageSetup")
    page_setup.attrib.clear()
    page_setup.attrib.update({
        "paperSize": "8",
        "orientation": "landscape",
        "scale": str(scale),
        "horizontalDpi": "300",
        "verticalDpi": "300",
    })
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def patch_instruction(xml_bytes: bytes) -> bytes:
    root = ET.fromstring(xml_bytes)
    setup_pr = root.find(f"{{{NS}}}sheetPr/{{{NS}}}pageSetUpPr")
    if setup_pr is not None:
        setup_pr.attrib.pop("fitToPage", None)
    row = root.find(f".//{{{NS}}}sheetData/{{{NS}}}row[@r='3']")
    if row is None:
        raise ValueError("Instruction row 3 is missing")
    row.attrib.pop("ht", None)
    row.attrib.pop("customHeight", None)
    page_setup = root.find(f"{{{NS}}}pageSetup")
    if page_setup is None:
        page_setup = ET.SubElement(root, f"{{{NS}}}pageSetup")
    page_setup.attrib.clear()
    page_setup.attrib.update({
        "paperSize": "9",
        "orientation": "landscape",
        "scale": "100",
        "horizontalDpi": "300",
        "verticalDpi": "300",
    })
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_one(source: Path, target: Path, scale: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".tmp", dir=target.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(source) as source_zip, zipfile.ZipFile(temporary, "w") as target_zip:
            for info in source_zip.infolist():
                data = source_zip.read(info.filename)
                if info.filename == REGISTER_SHEET:
                    data = patch_register(data, scale)
                elif info.filename == INSTRUCTION_SHEET:
                    data = patch_instruction(data)
                target_zip.writestr(info, data)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory_fd = os.open(target.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def build(source_root: Path, output_dir: Path) -> None:
    source_dir = source_root / SOURCE_REL
    for name, spec in SPECS.items():
        source = source_dir / name
        if sha256(source.read_bytes()) != spec["input_sha256"]:
            raise ValueError(f"Pinned input hash mismatch: {name}")
        target = output_dir / name
        if target.resolve() == source.resolve():
            raise ValueError("Output must not replace source")
        build_one(source, target, spec["scale"])
        if sha256(target.read_bytes()) != spec["output_sha256"]:
            raise ValueError(f"Unexpected deterministic output hash: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    build(args.source_root, args.output_dir)
