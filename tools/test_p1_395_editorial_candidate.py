#!/usr/bin/env python3
"""Fail-closed lexical/OOXML gate for the P1 395 GK candidate (no legal/native claims).

Regression reason: previous value-language check inspected numeric-escaped XLSX XML
as text, so it missed buyer-visible 'юрист' and 'Что это не заменяет'.
"""
import hashlib
import copy
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
QA_REPORT = CANDIDATE.parent/"qa-v3-20261013.json"
RECEIPT = CANDIDATE.parent/"receipt.json"
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


def verify_receipt(record, qa, source_parts, candidate_parts, changed_parts):
    """Fail closed on stale/misleading evidence for the exact candidate, not on release gates."""
    assert record.get("schema_version")==2, "RECEIPT_SCHEMA_DRIFT"
    assert record.get("source_path")==str(SOURCE.relative_to(ROOT)), "RECEIPT_SOURCE_PATH_DRIFT"
    assert record.get("candidate_path")==str(CANDIDATE.relative_to(ROOT)), "RECEIPT_CANDIDATE_PATH_DRIFT"
    assert record.get("source_sha256")==SOURCE_SHA, "RECEIPT_SOURCE_SHA_DRIFT"
    assert record.get("candidate_sha256")==CANDIDATE_SHA, "RECEIPT_CANDIDATE_SHA_DRIFT"
    assert record.get("changed_zip_parts")==sorted(changed_parts), "RECEIPT_PARTS_DRIFT"
    expected_cells={n.rsplit("/",1)[-1].replace(".xml",""):sorted(v)
                    for n,v in EXPECTED.items()}
    assert record.get("corrected_cells")==expected_cells, "RECEIPT_CELLS_DRIFT"
    before_counts={n:len(v) for n,v in formulas(source_parts).items()}
    after_counts={n:len(v) for n,v in formulas(candidate_parts).items()}
    assert record.get("formulas_before")==before_counts, "RECEIPT_FORMULAS_BEFORE_DRIFT"
    assert record.get("formulas_after")==after_counts, "RECEIPT_FORMULAS_AFTER_DRIFT"
    assert record.get("formula_count")==sum(after_counts.values())==251, "RECEIPT_FORMULA_COUNT_DRIFT"
    assert record.get("zip_parts_total")==len(candidate_parts)==15, "RECEIPT_PACKAGE_COUNT_DRIFT"
    assert record.get("other_package_parts_byte_identical") is True, "RECEIPT_PRESERVATION_DRIFT"
    assert record.get("non_text_xml_structure_identical") is True, "RECEIPT_NON_TEXT_DRIFT"
    visual_expected={"status":"PASS_LIBREOFFICE_A4_PREVIEW_ONLY",
                     "pdf_sha256":qa["libreoffice_pdf_sha256"],
                     "page_count":qa["libreoffice_page_count"],
                     "page_format":qa["libreoffice_page_format"]}
    assert record.get("visual")==visual_expected, "RECEIPT_VISUAL_EVIDENCE_DRIFT"
    assert qa.get("canonical_source_sha256")==SOURCE_SHA, "QA_SOURCE_DRIFT"
    assert qa.get("candidate_sha256")==CANDIDATE_SHA, "QA_CANDIDATE_DRIFT"
    assert qa.get("zip_parts_changed")==sorted(changed_parts), "QA_CHANGED_PARTS_DRIFT"
    assert qa.get("formulas_preserved")==251, "QA_FORMULA_COUNT_DRIFT"
    assert qa.get("corrected_cells")==expected_cells, "QA_CHANGED_CELLS_DRIFT"
    assert record.get("qa_report_path")==str(QA_REPORT.relative_to(ROOT)), "RECEIPT_QA_PATH_DRIFT"
    assert record.get("office")=="NOT_RUN_NATIVE_EXCEL_2016", "RECEIPT_NATIVE_OFFICE_MISCLAIM"
    assert record.get("normative_legal")=="NOT_ACCEPTED", "RECEIPT_LEGAL_MISCLAIM"
    assert record.get("buyer")=="NOT_ACCEPTED", "RECEIPT_BUYER_MISCLAIM"
    assert record.get("g1_g8")=="HOLD", "RECEIPT_G1_G8_MISCLAIM"
    assert record.get("release")=="BLOCKED", "RECEIPT_RELEASE_MISCLAIM"
    assert record.get("scope")=="OOXML_EDITORIAL_AND_PREVIEW_ONLY_NOT_PRODUCT_ACCEPTANCE", "RECEIPT_SCOPE_DRIFT"
    assert record.get("production_modified") is False, "RECEIPT_PRODUCTION_MISCLAIM"

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
    editorial=json.loads(REPORT.read_text(encoding="utf-8"))
    assert editorial["candidate_v3_sha256"]==CANDIDATE_SHA, "EDITORIAL_REPORT_SHA_DRIFT"
    qa=json.loads(QA_REPORT.read_text(encoding="utf-8"))
    receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
    verify_receipt(receipt,qa,old,new,changes)
    for label in ("stale_candidate_sha","missing_changed_part","false_office_pass","stale_visual"):
        invalid=copy.deepcopy(receipt)
        if label=="stale_candidate_sha":
            invalid["candidate_sha256"]="0fbed1858b239bffa713f14b95e7ba07c41742726bc9aa2a221904c3f58aa5f5"
        elif label=="missing_changed_part":
            invalid["changed_zip_parts"]=["xl/worksheets/sheet3.xml"]
        elif label=="false_office_pass":
            invalid["office"]="PASS_NATIVE_EXCEL_2016"
        elif label=="stale_visual":
            invalid["visual"]["status"]="NOT_RUN"
        try:
            verify_receipt(invalid,qa,old,new,changes)
        except AssertionError:
            pass
        else:
            raise AssertionError("RECEIPT_NEGATIVE_GATE_NOT_DETECTED:"+label)
    print("P1_395_EDITORIAL_CANDIDATE_PASS: 7 exact corrected cells, 251/251 formulas, "
          "15 ZIP parts, package/validation/styles preserved, 3 negative cases detected; "
          "not native Excel/legal/buyer/G1-G8")
    return 0

if __name__=="__main__":
    try:sys.exit(run())
    except Exception as error:
        print(f"P1_395_EDITORIAL_CANDIDATE_FAIL: {type(error).__name__}: {error}",file=sys.stderr)
        sys.exit(1)
