#!/usr/bin/env python3
"""Fail-closed lexical/OOXML gate for the P1 395 GK candidate (no legal/native claims).

Regression reason: previous value-language check inspected numeric-escaped XLSX XML
as text, so it missed buyer-visible 'юрист' and 'Что это не заменяет'.
"""
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/"products-storage/01-zakrytie-rabot/14-raschet-procentov-395-gk.xlsx"
CANDIDATE = ROOT/"tools/candidates/p1-395-content-20261012/14-raschet-procentov-395-gk.xlsx"
REPORT = CANDIDATE.parent/"editorial-v3-20261013.json"
SOURCE_SHA = "0e3fd94bcb4023652d40de96c22890ef494f0d089d565b1ef6017374c19923fe"
CANDIDATE_SHA = "f7bd3a6fc8cfbb9e478448b2d217c6c4e3b667a5548f421373a7816978e5874e"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SHEET = re.compile(r"xl/worksheets/sheet\d+\.xml$")
EXPECTED = {
    "xl/worksheets/sheet1.xml": {"A47"},
    "xl/worksheets/sheet2.xml": {"A48"},
    "xl/worksheets/sheet3.xml": {"A15","A16","A17","A18","A19"},
}
FORBIDDEN = ["шаблон","типовой шаблон","юридическая консультация",
             "что это не заменяет","не заменяет юриста","юрист","заключение специалиста"]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def inspect_zip(path):
    content=path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        assert z.testzip() is None, "ZIP_CRC_FAIL"
        names=z.namelist()
        assert len(names)==len(set(names)), "DUPLICATE_MEMBERS"
        return sha(content),{n:z.read(n) for n in names}

def cells(payload):
    root=ET.fromstring(payload)
    return {c.get("r"): c for c in root.iter(NS+"c")}

def celltext(c):
    return "".join(t.text or "" for t in c.iter(NS+"t"))

def formulas(parts):
    return {n: [(c.get("r"),f.text,tuple(sorted(f.attrib.items())))
                 for c in ET.fromstring(data).iter(NS+"c") for f in c.iter(NS+"f")]
            for n,data in parts.items() if SHEET.fullmatch(n)}

def structural_without_text(data):
    root=ET.fromstring(data)
    for t in root.iter(NS+"t"):t.text="<VISIBLE_TEXT>"
    return ET.tostring(root)

def validate_language(text):
    normalized=" ".join(text.casefold().split())
    return [p for p in FORBIDDEN if p in normalized]

def run():
    h0,old=inspect_zip(SOURCE)
    h1,new=inspect_zip(CANDIDATE)
    assert h0==SOURCE_SHA, "SOURCE_VERSION_DRIFT"
    assert h1==CANDIDATE_SHA, "CANDIDATE_SHA_DRIFT"
    assert set(old)==set(new), "PACKAGE_PARTS_DRIFT"
    assert len(old)==15, "PACKAGE_SIZE_DRIFT"
    assert formulas(old)==formulas(new), "FORMULA_DRIFT"
    assert sum(len(q) for q in formulas(new).values())==251, "FORMULA_COUNT_DRIFT"
    changes={n for n in old if old[n]!=new[n]}
    assert changes==set(EXPECTED), ("XML_PARTS_CHANGED",sorted(changes))
    for name,expected_cells in EXPECTED.items():
        a,b=cells(old[name]),cells(new[name])
        assert set(a)==set(b), "WORKSHEET_CELLS_DRIFT"
        found={k for k in a if celltext(a[k])!=celltext(b[k])}
        assert found==expected_cells, ("CHANGED_CELLS_NOT_EXACT",name,found,expected_cells)
        assert structural_without_text(old[name])==structural_without_text(new[name]), "NON_TEXT_XML_CHANGED"
    all_visible="\n".join(celltext(c) for name,raw in new.items() if SHEET.fullmatch(name) for c in cells(raw).values())
    assert not validate_language(all_visible), ("PROHIBITED_VISIBLE_LANGUAGE",validate_language(all_visible))
    assert celltext(cells(new["xl/worksheets/sheet3.xml"])["A15"])=="Условия применения расчёта"
    assert celltext(cells(new["xl/worksheets/sheet3.xml"])["A19"]).startswith("— Сверьте ")
    assert validate_language("Что это не заменяет"), "NEGATIVE_MUTATION_1_NOT_DETECTED"
    assert validate_language("Рекомендуем согласовать с юристом"), "NEGATIVE_MUTATION_2_NOT_DETECTED"
    assert validate_language("Это типовой шаблон"), "NEGATIVE_MUTATION_3_NOT_DETECTED"
    receipt=json.loads(REPORT.read_text(encoding="utf-8"))
    assert receipt["candidate_v3_sha256"]==CANDIDATE_SHA, "RECEIPT_MISMATCH"
    print("P1_395_EDITORIAL_CANDIDATE_PASS: 7 exact corrected cells, 251/251 formulas, "
          "15 ZIP parts, package/validation/styles preserved, 3 negative cases detected; "
          "not native Excel/legal/buyer/G1-G8")
    return 0

if __name__=="__main__":
    try:sys.exit(run())
    except Exception as error:
        print(f"P1_395_EDITORIAL_CANDIDATE_FAIL: {type(error).__name__}: {error}",file=sys.stderr)
        sys.exit(1)
