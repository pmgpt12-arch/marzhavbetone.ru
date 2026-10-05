from __future__ import annotations
import hashlib
import json
import warnings
import io
import posixpath
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import openpyxl

TEMPLATES = Path(__file__).resolve().parent / "templates" / "s1-owner-excel"
APPROVED = json.loads((TEMPLATES / "approved-sha256.json").read_text())

def _targets(square_reference):
    for area in str(square_reference).split():
        left, top, right, bottom = openpyxl.utils.range_boundaries(area)
        for row in range(top, bottom + 1):
            for column in range(left, right + 1):
                yield openpyxl.utils.get_column_letter(column) + str(row)

def _native_validations(native):
    result = {}
    namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    relationship_namespace = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(io.BytesIO(native)) as archive:
        relationships = {node.attrib["Id"]: node.attrib["Target"] for node in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        for sheet in workbook.findall("{" + namespace + "}sheets/{" + namespace + "}sheet"):
            target = relationships[sheet.attrib["{" + relationship_namespace + "}id"]]
            filename = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            tree = ET.fromstring(archive.read(filename))
            for node in tree.iter():
                if node.tag.rsplit("}", 1)[-1] != "dataValidation":
                    continue
                fields = {child.tag.rsplit("}", 1)[-1]: "".join(child.itertext()).strip() for child in node}
                rule = (node.attrib.get("type", ""), node.attrib.get("operator", ""), node.attrib.get("allowBlank", "0") in ("1", "true"), fields.get("formula1", ""), fields.get("formula2", ""))
                for coordinate in _targets(node.attrib.get("sqref", fields.get("sqref", ""))):
                    result[(sheet.attrib["name"], coordinate)] = rule
    return result

def _generated_validations(generated):
    result = {}
    for sheet in generated.worksheets:
        for validation in sheet.data_validations.dataValidation:
            rule = (validation.type or "", validation.operator or "", bool(validation.allowBlank), str(validation.formula1 or ""), str(validation.formula2 or ""))
            for coordinate in _targets(validation.sqref):
                result[(sheet.title, coordinate)] = rule
    return result

def write_approved_layout(generated, output: Path) -> None:
    """Write native owner bytes only after current generator semantics agree."""
    native = (TEMPLATES / output.name).read_bytes()
    if hashlib.sha256(native).hexdigest() != APPROVED[output.name]:
        raise ValueError("Approved Excel template hash mismatch: " + output.name)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*extension is not supported.*")
        approved = openpyxl.load_workbook(TEMPLATES / output.name)
    if generated.sheetnames != approved.sheetnames:
        raise ValueError("Approved Excel sheet mismatch: " + output.name)
    for name in generated.sheetnames:
        actual, expected = generated[name], approved[name]
        coordinates = set(actual._cells) | set(expected._cells)
        for coordinate in coordinates:
            a, e = actual.cell(*coordinate), expected.cell(*coordinate)
            if (None if a.value == "" else a.value) != (None if e.value == "" else e.value):
                raise ValueError(f"Approved Excel semantic mismatch: {output.name}/{name}!{a.coordinate}")
    if _generated_validations(generated) != _native_validations(native):
        raise ValueError("Approved Excel validation mismatch: " + output.name)
    if {k: v.attr_text for k, v in generated.defined_names.items()} != {k: v.attr_text for k, v in approved.defined_names.items()}:
        raise ValueError("Approved Excel defined-name mismatch: " + output.name)
    temporary = output.with_name(output.name + ".approved.tmp")
    temporary.write_bytes(native)
    temporary.replace(output)
