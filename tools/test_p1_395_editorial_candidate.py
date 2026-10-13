#!/usr/bin/env python3
"""Fail-closed lexical/OOXML gate for the P1 395 GK candidate (no legal/native claims).

Regression reason: previous value-language check inspected numeric-escaped XLSX XML
as text, so it missed buyer-visible 'юрист' and 'Что это не заменяет'.
"""
import hashlib
import copy
from datetime import datetime
import io
import json
import re
import sys
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/"products-storage/01-zakrytie-rabot/14-raschet-procentov-395-gk.xlsx"
CANDIDATE = ROOT/"tools/candidates/p1-395-content-20261012/14-raschet-procentov-395-gk.xlsx"
REPORT = CANDIDATE.parent/"editorial-v3-20261013.json"
QA_REPORT = CANDIDATE.parent/"qa-native-header-20261013.json"
NATIVE_REPORT = CANDIDATE.parent/"native-header-report-20261013.xml"
NATIVE_PDF = CANDIDATE.parent/"native-header-preview-20261013.pdf"
V3_SHA = "f7bd3a6fc8cfbb9e478448b2d217c6c4e3b667a5548f421373a7816978e5874e"
RECEIPT = CANDIDATE.parent/"receipt.json"
SOURCE_SHA = "0e3fd94bcb4023652d40de96c22890ef494f0d089d565b1ef6017374c19923fe"
CANDIDATE_SHA = "8ec79d20d15a8d4888b2ae69130f374d1a8c6039cfdf2ba71044d7010ff5ce34"
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


def valid_core(payload):
    root=ET.fromstring(payload)
    for e in root:
        if e.tag.rsplit("}",1)[-1] in ("created","modified"):
            try:
                assert e.text and e.text.endswith("Z")
                datetime.fromisoformat(e.text.replace("Z","+00:00"))
            except (AssertionError,ValueError):
                raise AssertionError("INVALID_CORE_TIMESTAMP")

def valid_height(payload):
    row=next(r for r in ET.fromstring(payload).iter(NS+"row") if r.get("r")=="15")
    assert row.get("ht")=="54" and row.get("customHeight")=="1", "NATIVE_HEADER_HEIGHT_REGRESSION"

def verify_receipt(record, qa, source_parts, candidate_parts, changed_parts):
    assert record.get("schema_version")==3, "RECEIPT_SCHEMA_DRIFT"
    assert record.get("source_path")==str(SOURCE.relative_to(ROOT)), "RECEIPT_SOURCE_PATH_DRIFT"
    assert record.get("candidate_path")==str(CANDIDATE.relative_to(ROOT)), "RECEIPT_CANDIDATE_PATH_DRIFT"
    assert record.get("source_sha256")==SOURCE_SHA, "RECEIPT_SOURCE_SHA_DRIFT"
    assert record.get("candidate_sha256")==CANDIDATE_SHA, "RECEIPT_CANDIDATE_SHA_DRIFT"
    assert record.get("candidate_bytes")==CANDIDATE.stat().st_size==20192, "RECEIPT_BYTES_DRIFT"
    assert record.get("changed_zip_parts")==sorted(changed_parts), "RECEIPT_PARTS_DRIFT"
    expected_cells={n.rsplit("/",1)[-1].replace(".xml",""):sorted(v) for n,v in EXPECTED.items()}
    assert record.get("corrected_cells")==qa.get("corrected_cells")==expected_cells, "RECEIPT_CELLS_DRIFT"
    for key,parts in (("formulas_before",source_parts),("formulas_after",candidate_parts)):
        assert record.get(key)=={n:len(v) for n,v in formulas(parts).items()}, "RECEIPT_FORMULAS_DRIFT"
    assert record.get("formula_count")==qa.get("formulas_preserved")==251, "RECEIPT_FORMULA_COUNT_DRIFT"
    assert record.get("zip_parts_total")==len(candidate_parts)==15, "RECEIPT_PACKAGE_COUNT_DRIFT"
    assert record.get("other_package_parts_byte_identical") is True, "RECEIPT_PRESERVATION_DRIFT"
    assert record.get("non_text_xml_structure_identical") is False, "NON_TEXT_CHANGES_MUST_BE_DISCLOSED"
    assert record.get("permitted_non_text_edits")==["docProps/core.xml: two timezone corrections","sheet4.xml: row 15 height 38 to 54"], "NON_TEXT_EDIT_SCOPE_DRIFT"
    assert qa.get("canonical_source_sha256")==SOURCE_SHA and qa.get("candidate_sha256")==CANDIDATE_SHA, "QA_FINGERPRINT_DRIFT"
    assert qa.get("zip_parts_changed")==sorted(changed_parts), "QA_CHANGED_PARTS_DRIFT"
    assert record.get("qa_report_path")==str(QA_REPORT.relative_to(ROOT)), "RECEIPT_QA_PATH_DRIFT"
    assert record.get("native_report_path")==str(NATIVE_REPORT.relative_to(ROOT)), "RECEIPT_NATIVE_REPORT_PATH"
    assert record.get("native_pdf_path")==str(NATIVE_PDF.relative_to(ROOT)), "RECEIPT_NATIVE_PDF_PATH"
    assert sha(NATIVE_REPORT.read_bytes())==qa["native_report_sha256"], "NATIVE_REPORT_HASH_DRIFT"
    assert sha(NATIVE_PDF.read_bytes())==qa["native_pdf_sha256"], "NATIVE_PDF_HASH_DRIFT"
    assert NATIVE_PDF.read_bytes().startswith(b"%PDF-"), "NATIVE_PDF_HEADER"
    native=ET.parse(NATIVE_REPORT).getroot()
    assert native.get("job")==qa["native_job_id"] and native.get("status")=="PASS", "NATIVE_REPORT_JOB_DRIFT"
    assert native.get("excel_version")=="16.0" and native.get("excel_build")=="4324", "NATIVE_EXCEL_VERSION"
    assert native.get("scope")=="NATIVE_OPEN_EXPORT_AND_HEADER_REPAIR_ONLY; numeric scenarios, UI typing/paste, legal/buyer acceptance not performed", "NATIVE_SCOPE_OVERCLAIM"
    checks={c.get("name"):c.attrib for c in native.findall("check")}
    assert len(checks)==4 and all(c.get("pass")=="True" for c in checks.values()), "NATIVE_CHECKS_DRIFT"
    assert checks["p1395header:input_sha"]["actual"]==CANDIDATE_SHA, "NATIVE_INPUT_SHA_DRIFT"
    assert checks["p1395header:source_unchanged"]["actual"]==CANDIDATE_SHA, "NATIVE_SOURCE_MUTATION"
    assert checks["p1395header:sheet_protected"]["actual"]==checks["p1395header:sheet_protected"]["expected"]=="False", "NATIVE_PROTECTION_CONTRACT"
    assert record.get("visual")=={"status":"PASS_HEADER_FIX_ONLY_WITH_OPEN_PAGINATION","pdf_sha256":qa["native_pdf_sha256"],"page_count":5,"page_format":"A4, mixed portrait/landscape"}, "RECEIPT_VISUAL_EVIDENCE_DRIFT"
    assert record.get("office")=="PASS_NATIVE_OPEN_EXPORT_ONLY", "RECEIPT_NATIVE_OFFICE_MISCLAIM"
    assert record.get("normative_legal")==record.get("buyer")=="NOT_ACCEPTED", "RECEIPT_ACCEPTANCE_MISCLAIM"
    assert record.get("g1_g8")=="HOLD" and record.get("release")=="BLOCKED", "RECEIPT_RELEASE_MISCLAIM"
    assert record.get("scope")=="EDITORIAL_METADATA_NATIVE_OPEN_EXPORT_HEADER_ONLY_NOT_PRODUCT_ACCEPTANCE", "RECEIPT_SCOPE_DRIFT"
    assert record.get("production_modified") is False, "RECEIPT_PRODUCTION_MISCLAIM"

def verify_registry_change_record(row, source_parts, candidate_parts):
    assert row.get("registry_id")=="P1-CAND-395-NATIVE-HEADER-20261013", "REGISTRY_ID_DRIFT"
    assert row.get("sha256")==CANDIDATE_SHA and row.get("bytes")==CANDIDATE.stat().st_size, "REGISTRY_SHA_DRIFT"
    assert row.get("role")=="nominated_candidate" and row.get("release_status")=="BLOCKED", "REGISTRY_ROLE_OR_RELEASE_DRIFT"
    rec=row["change_record"]
    required=("provenance","identities","lineage","addressable_edits","package_components","preserved_invariants","evidence_files","execution_history","runtime","verification_scopes","block_history","reuse_policy","next_step","unknowns")
    assert all(k in rec for k in required), "REGISTRY_MISSING_GROUP"
    assert len(rec["addressable_edits"])==10, "REGISTRY_EDIT_COUNT"
    assert len(rec["package_components"])==15, "REGISTRY_COMPONENT_COUNT"
    for part in rec["package_components"]:
        assert part["before_sha256"]==sha(source_parts[part["part"]]), "REGISTRY_SOURCE_COMPONENT_DRIFT"
        assert part["after_sha256"]==sha(candidate_parts[part["part"]]), "REGISTRY_TARGET_COMPONENT_DRIFT"
    assert rec["execution_history"].get("commands"), "REGISTRY_MISSING_COMMANDS"
    assert rec["execution_history"]["native_jobs_submitted_for_capture"]==0, "REGISTRY_REPEATED_NATIVE_CAPTURE"
    for proof in rec["evidence_files"]:
        if proof.get("repository_path"):
            ref=proof.get("commit")
            assert ref and re.fullmatch(r"[a-f0-9]{40}",ref), "REGISTRY_EVIDENCE_COMMIT_MISSING"
            data=subprocess.run(["git","-C",str(ROOT),"show",ref+":"+proof["repository_path"]],capture_output=True,check=True,timeout=10).stdout
            assert sha(data)==proof["sha256"] and len(data)==proof["bytes"], "REGISTRY_EVIDENCE_DRIFT"
    for scope in rec["verification_scopes"]:
        payload={k:scope[k] for k in ("scope","candidate_sha256","contract","evidence_sha256","environment")}
        key=sha(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8"))
        assert scope["candidate_sha256"]==CANDIDATE_SHA and scope["reuse_key_sha256"]==key, "REGISTRY_REUSE_KEY_DRIFT"
    assert rec["product_acceptance"]["accepted_products"]==0 and rec["product_acceptance"]["g1_g8_status"]=="OPEN", "REGISTRY_FALSE_PRODUCT_ACCEPTANCE"

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
    assert changes==set(EXPECTED)|{"docProps/core.xml","xl/worksheets/sheet4.xml"}, ("XML_PARTS_CHANGED",sorted(changes))
    assert old["docProps/core.xml"].count(b"+00:00Z")==2, "OLD_CORE_TIMESTAMP_COUNT"
    assert new["docProps/core.xml"]==old["docProps/core.xml"].replace(b"+00:00Z",b"Z"), "CORE_NON_TIMESTAMP_EDIT"
    valid_core(new["docProps/core.xml"])
    valid_height(new["xl/worksheets/sheet4.xml"])
    oldsheet=ET.fromstring(old["xl/worksheets/sheet4.xml"])
    newsheet=ET.fromstring(new["xl/worksheets/sheet4.xml"])
    next(r for r in newsheet.iter(NS+"row") if r.get("r")=="15").set("ht","38")
    assert ET.tostring(oldsheet)==ET.tostring(newsheet), "EXAMPLE_NON_HEIGHT_CHANGE"
    for label,check,payload in (("timestamp",valid_core,old["docProps/core.xml"]),("header_height",valid_height,old["xl/worksheets/sheet4.xml"])):
        try:check(payload)
        except AssertionError:pass
        else:raise AssertionError("NEGATIVE_LAYOUT_NOT_DETECTED:"+label)
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
    assert editorial["candidate_v3_sha256"]==V3_SHA, "EDITORIAL_REPORT_SHA_DRIFT"
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
    registry=json.loads((ROOT/"products-storage/ARTIFACT-REGISTRY.json").read_text(encoding="utf-8"))
    entries=[x for x in registry["artifacts"] if x.get("registry_id")=="P1-CAND-395-NATIVE-HEADER-20261013"]
    assert len(entries)==1, "REGISTRY_NOMINATION_MISSING_OR_DUPLICATE"
    verify_registry_change_record(entries[0],old,new)
    for label in ("stale_sha","evidence_drift","missing_commands","false_acceptance"):
        bad=copy.deepcopy(entries[0])
        if label=="stale_sha":bad["sha256"]="0"*64
        elif label=="evidence_drift":bad["change_record"]["evidence_files"][0]["sha256"]="0"*64
        elif label=="missing_commands":bad["change_record"]["execution_history"]["commands"]=[]
        else:bad["change_record"]["product_acceptance"]["accepted_products"]=1
        try:verify_registry_change_record(bad,old,new)
        except AssertionError:pass
        else:raise AssertionError("REGISTRY_NEGATIVE_NOT_DETECTED:"+label)
    print("P1_395_EDITORIAL_CANDIDATE_PASS: 7 exact corrected cells, 251/251 formulas, "
          "15 ZIP parts, native evidence bound, 13 negative cases detected; "
          "not native numeric scenarios/legal/buyer/G1-G8")
    return 0

if __name__=="__main__":
    try:sys.exit(run())
    except Exception as error:
        print(f"P1_395_EDITORIAL_CANDIDATE_FAIL: {type(error).__name__}: {error}",file=sys.stderr)
        sys.exit(1)
