#!/usr/bin/env python3
"""Single new SHA-bound P1 Excel metadata candidate; no source, CI or runtime changes."""
from pathlib import Path
from xml.etree import ElementTree as ET
import hashlib, json, os, zipfile

SRC = Path("/home/denis/projects/mb001-p1-395-copy-correction-20261012/tools/candidates/p1-395-content-20261012/14-raschet-procentov-395-gk.xlsx")
DIR = Path("/home/denis/.local/state/claude-dispatcher/recovery-20261006/postreconnect-product-gates/p1-395-corexml-compat-20261013")
OUT = DIR / "14-raschet-procentov-395-gk-corexml-compat.xlsx"
REPORT = DIR / "report.json"
SOURCE_SHA = "f7bd3a6fc8cfbb9e478448b2d217c6c4e3b667a5548f421373a7816978e5874e"
CORE = "docProps/core.xml"
SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

def sha(value):
    return hashlib.sha256(value).hexdigest()

def inspect(path):
    data = path.read_bytes()
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, "ZIP_CRC_FAIL"
        names = z.namelist()
        assert len(names) == len(set(names)) == 15, "PACKAGE_OR_DUPLICATE_DRIFT"
        return sha(data), names, {n: z.read(n) for n in names}

def formula_total(parts):
    return sum(len(list(ET.fromstring(v).iter(SHEET_NS + "f")))
               for k, v in parts.items() if k.startswith("xl/worksheets/sheet") and k.endswith(".xml"))

def main():
    assert not OUT.exists() and not REPORT.exists(), "DUPLICATE_CANDIDATE_STOP"
    oldhash, names, old = inspect(SRC)
    assert oldhash == SOURCE_SHA, "SOURCE_SHA_DRIFT"
    before = old[CORE]
    assert before.count(b"+00:00Z") == 2, "INVALID_TIMESTAMPS_NOT_AS_EXPECTED"
    corrected = before.replace(b"+00:00Z", b"Z")
    assert corrected != before and corrected.count(b"+00:00Z") == 0
    ET.fromstring(corrected)
    assert formula_total(old) == 251, "BASE_FORMULA_COUNT_DRIFT"
    tmp = DIR / "candidate.tmp.xlsx"
    assert not tmp.exists(), "EXISTING_TEMP_STOP"
    try:
        with zipfile.ZipFile(SRC, "r") as zsrc, zipfile.ZipFile(tmp, "w") as zout:
            zout.comment = zsrc.comment
            for info in zsrc.infolist():
                payload = corrected if info.filename == CORE else zsrc.read(info.filename)
                zout.writestr(info, payload)
        newhash, newnames, new = inspect(tmp)
        assert names == newnames, "PACKAGE_ORDER_DRIFT"
        changed = [n for n in names if old[n] != new[n]]
        assert changed == [CORE], ("UNEXPECTED_CHANGE", changed)
        assert formula_total(new) == 251, "CANDIDATE_FORMULA_COUNT_DRIFT"
        assert SRC.is_file() and sha(SRC.read_bytes()) == SOURCE_SHA, "SOURCE_CHANGED"
        os.replace(tmp, OUT)
        receipt = {
          "status": "PASS_METADATA_ONLY_STRUCTURAL_CANDIDATE",
          "source_path": str(SRC),
          "candidate_path": str(OUT),
          "source_sha256": SOURCE_SHA,
          "candidate_sha256": newhash,
          "candidate_bytes": OUT.stat().st_size,
          "changed_zip_parts": changed,
          "original_invalid_double_zone_count": 2,
          "candidate_invalid_double_zone_count": 0,
          "other_14_parts_byte_identical": True,
          "formulas_before": 251,
          "formulas_after": 251,
          "zip_parts": 15,
          "native_excel_2016": "NOT_RUN",
          "legal_buyer_g1_g8": "NOT_ACCEPTED",
          "release": "BLOCKED",
          "production_modified": False
        }
        REPORT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        assert json.loads(REPORT.read_text(encoding="utf-8")) == receipt
        print(json.dumps(receipt,ensure_ascii=False))
    finally:
        if tmp.exists():
            tmp.unlink()

if __name__ == "__main__":
    main()
