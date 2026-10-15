#!/usr/bin/env python3
"""Independent structural regression for P3 PR646 validation-alert remediation."""
import hashlib
import io
import json
import pathlib
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASE = "2d15f145d162c1042cd06e624561a21b276d7276"
SOURCE_PATH = "tools/candidates/p3-full-11-preflight-20261015/candidate/06-zhurnal-peredachi.xlsx"
SOURCE_SHA = "862daec8caad602c044f147f64768ed65cbb7497072d95c55df5d390acea14f3"
OUTPUT_SHA = "7cd0cb3e939909e6a1fffc32766136423ca6d5cb6e63f7575b4720fef004e3c8"
PART = "xl/worksheets/sheet1.xml"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
TAGS = re.compile(rb"<dataValidation\b[^>]*>")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def rule_gate(sheet):
    rules = list(ET.fromstring(sheet).iter(NS + "dataValidation"))
    assert len(rules) == 7, "validation-count"
    assert all(x.get("showErrorMessage") == "1" and x.get("errorStyle") == "stop" for x in rules), "alerts-not-blocking"
    return tuple(x.get("sqref") for x in rules)

def main():
    baseline = subprocess.check_output(["git", "-C", str(REPO), "show", BASE + ":" + SOURCE_PATH])
    candidate = (HERE / "06-zhurnal-peredachi.xlsx").read_bytes()
    receipt = json.loads((HERE / "receipt.json").read_text())
    assert sha(baseline) == SOURCE_SHA, "source-drift"
    assert sha(candidate) == OUTPUT_SHA == receipt["output_sha256"], "output-drift"
    with zipfile.ZipFile(io.BytesIO(baseline)) as old, zipfile.ZipFile(io.BytesIO(candidate)) as new:
        assert old.testzip() is None and new.testzip() is None, "zip-integrity"
        assert old.namelist() == new.namelist(), "member-inventory"
        assert all(old.read(p) == new.read(p) for p in old.namelist() if p != PART), "unrelated-member-modified"
        before, after = old.read(PART), new.read(PART)
        assert TAGS.sub(b"<TAG>", before) == TAGS.sub(b"<TAG>", after), "unrelated-worksheet-changed"
        names = rule_gate(after)
        assert len(TAGS.findall(before)) == len(TAGS.findall(after)) == 7, "xml-tag-count"
        assert b"IF(FALSE" in after, "first-row-formula-changed"
        for bad in (
            after.replace(b'showErrorMessage="1"', b'showErrorMessage="0"', 1),
            after.replace(b'errorStyle="stop"', b'errorStyle="warning"', 1),
        ):
            try:
                rule_gate(bad)
            except AssertionError:
                pass
            else:
                raise AssertionError("negative-fixture-escaped")
    print(json.dumps({
        "verdict": "PASS_STRUCTURAL_ONLY", "source_sha256": SOURCE_SHA,
        "candidate_sha256": OUTPUT_SHA, "alert_rules": list(names),
        "negative_mutations_rejected": 2,
        "native_excel": "PENDING", "independent_buyer_acceptance": "PENDING"
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
