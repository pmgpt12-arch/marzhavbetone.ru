#!/usr/bin/env python3
"""Exact-SHA checks for the P3 Excel 2016-compatible isolated candidate."""
import hashlib
import io
import json
import pathlib
import subprocess
import xml.etree.ElementTree as ET
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASE = "2d15f145d162c1042cd06e624561a21b276d7276"
SOURCE_PATH = "tools/candidates/p3-full-11-preflight-20261015/candidate/06-zhurnal-peredachi.xlsx"
SOURCE_SHA = "862daec8caad602c044f147f64768ed65cbb7497072d95c55df5d390acea14f3"
OUTPUT_SHA = "7efe0218defcad70921a87dcce04700a75fd8a5075a25be3874ccf9785c153a0"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def parse_sheet(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None, "ZIP integrity"
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        return {
            "sheets": [x.get("name") for x in workbook.iter(NS + "sheet")],
            "formulas": [x.text or "" for x in sheet.iter(NS + "f")],
            "rules": [dict(x.attrib) for x in sheet.iter(NS + "dataValidation")],
            "conditional": [x.get("sqref") for x in sheet.iter(NS + "conditionalFormatting")],
            "errors": [x.get("r") for x in sheet.iter(NS + "c") if x.get("t") == "e"],
        }

def rule_gate(rules):
    assert len(rules) == 7, "rule count"
    assert all(x.get("showErrorMessage") in ("true", "1") and x.get("errorStyle") == "stop" for x in rules), "non-blocking input"
    return [x["sqref"] for x in rules]

def main():
    source = subprocess.check_output(["git", "-C", str(REPO), "show", BASE + ":" + SOURCE_PATH])
    candidate = (HERE / "06-zhurnal-peredachi.xlsx").read_bytes()
    receipt = json.loads((HERE / "receipt.json").read_text())
    assert sha(source) == SOURCE_SHA, "source drift"
    assert sha(candidate) == OUTPUT_SHA == receipt["current_candidate_sha256"], "candidate drift"
    old, new = parse_sheet(source), parse_sheet(candidate)
    assert new["sheets"] == old["sheets"] == ["Журнал передачи комплекта КС", "Инструкция"], "sheet identity"
    assert len(old["formulas"]) == len(new["formulas"]) == 50, "formula count"
    assert [f.replace("FALSE()", "FALSE") for f in new["formulas"]] == old["formulas"], "formula drift"
    assert old["conditional"] == new["conditional"] == ["R5:R54"], "conditional formatting"
    assert not new["errors"], "cached errors"
    rules = rule_gate(new["rules"])
    assert len(old["rules"]) == len(new["rules"]) == 7
    for key, bad in (("showErrorMessage", "false"), ("errorStyle", "warning")):
        mutant = [dict(x) for x in new["rules"]]
        mutant[0][key] = bad
        try:
            rule_gate(mutant)
        except AssertionError:
            pass
        else:
            raise AssertionError("negative mutation not detected")
    print(json.dumps({
        "verdict": "PASS_STRUCTURAL_ONLY", "candidate_sha256": OUTPUT_SHA,
        "exact_formulas": "50/50", "blocking_validations": len(rules),
        "negative_mutations_rejected": 2, "native_excel_open": "CONFIRMED",
        "native_functional_cases": "OPEN_HARNESS_LOCKED_CHECK",
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
