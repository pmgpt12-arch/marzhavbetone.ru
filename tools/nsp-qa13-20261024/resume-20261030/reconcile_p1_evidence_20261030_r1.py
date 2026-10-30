#!/usr/bin/env python3
"""Bind unchanged calculations and preserved Word text to the P1 layout candidate."""
from pathlib import Path
from io import BytesIO
import hashlib,json,re,subprocess,zipfile
import xml.etree.ElementTree as ET
B=Path("/home/denis/projects/nsp-qa13-20261024")
D=B/"owner-layout-review-20261029"
O=B/"resume-20261030/P1_EVIDENCE_RECONCILIATION_R1.json"
assert not O.exists(),"Inspect existing reconciliation"
H=lambda b:hashlib.sha256(b).hexdigest()
W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
z=zipfile.ZipFile(D/"QA13_P1_V1_18_FILES_NONRELEASE_20261029.zip")
old=zipfile.ZipFile(B/"delivery/P1-QA13-20-FILES-CALC-V4-NONRELEASE.zip")
R={"schema":"NSP_P1_LAYOUT_INHERITED_EVIDENCE_v1","archive_sha256":H(Path(z.filename).read_bytes()),"new_native_jobs":0,"new_legal_review":False,"files":[],"checks":{},"release_allowed":False,"owner_acceptance":"PENDING"}
def ok(k,v):
    R["checks"][k]=bool(v)
    assert v,k
def textnodes(raw):
    return [x.text or "" for x in ET.fromstring(zipfile.ZipFile(BytesIO(raw)).read("word/document.xml")).iter(W+"t")]
norm=lambda s:re.sub(r"\s+","",s)
try:
    guidepdf=subprocess.run(["pdftotext","-layout",str(D/"buyer/00-INSTRUKCIYA.pdf"),"-"],check=True,capture_output=True,text=True,timeout=5).stdout
    # Remove only the observed repeated page furniture. Keep all body text.
    furniture=lambda line: line.strip()=="НА СТОРОНЕ ПОДРЯДЧИКА / ФОРМЫ И ПОРЯДОК" or re.fullmatch(r"Инструкция — Закрытие работ • редакция \d{2}\.\d{2}\.\d{4} • nastoronepodryadchika\.ru",line.strip()) is not None
    page_lines=guidepdf.splitlines()
    R["pdf_page_furniture_lines_excluded"]=sum(furniture(line) for line in page_lines)
    guidepdf="\n".join(line for line in page_lines if not furniture(line))
    R["checker_recovery"]={"cause":"Repeated header/footer inserted into extracted paragraph at a page break","class":"CHECKER_FALSE_NEGATIVE_PDF_PAGE_FURNITURE","prior_report_preserved":True,"rule":"Ignore only exact observed header/footer lines; require all moved body notes in DOCX and PDF"}
    guidexml="".join(textnodes((D/"internal/00-INSTRUKCIYA.docx").read_bytes()))
    moved=[]
    for name in z.namelist():
        if not name.endswith(".docx"):continue
        before=textnodes(old.read(name));after=textnodes(z.read(name))
        mark="Проверка применения к конкретному объекту (QA-13)"
        expected=before[:before.index(mark)] if mark in before else before
        ok(name+":main_text_unchanged",after==expected)
        notes=before[before.index(mark)+1:] if mark in before else []
        for note in notes:
            if note:
                ok(name+":moved_note_"+str(len(moved)),norm(note) in norm(guidepdf) and norm(note) in norm(guidexml))
                moved.append(note)
        R["files"].append({"file":name,"status":"MAIN_TEXT_PRESERVED_LAYOUT_CHANGED_OWNER_PENDING","original_sha256":H(old.read(name)),"candidate_sha256":H(z.read(name)),"moved_notes":len(notes),"new_word_test":False})
    ok("eight_forms_preserve_main_text",len(R["files"])==8)
    R["unique_moved_notes_present_in_pdf"]=len(set(moved))
    reports=[]
    for p in (B/"native-evidence").rglob("report.xml"):
        root=ET.parse(p).getroot()
        if root.get("status")!="PASS":continue
        shas={c.get("actual") for c in root.iter("check") if c.get("name","").endswith(":input_sha") and c.get("pass")=="True" and c.get("expected")==c.get("actual")}
        reports.append((p,root,shas))
    for name in z.namelist():
        if not name.endswith(".xlsx"):continue
        sha=H(z.read(name));matching=[(p,r) for p,r,shas in reports if sha in shas]
        ok(name+":exact_native_input_sha_bound",bool(matching))
        R["files"].append({"file":name,"status":"UNCHANGED_EXACT_NATIVE_INPUT_BOUND","sha256":sha,"native_receipts":[{"path":str(p),"sha256":H(p.read_bytes()),"job":r.get("job"),"scope":r.get("scope")} for p,r in matching]})
    gate=json.loads((B/"proof/QA13_V4_FINAL_GATE.json").read_text())
    ok("calculator_exact_current_sha",gate["candidate_sha256"]==H(z.read("14-raschet-procentov-395-gk.xlsx")))
    for receipt in gate["native_receipts"]:
        matches=[(p,r) for p,r,shas in reports if r.get("job")==receipt["job"] and H(p.read_bytes())==receipt["receipt_sha256"]]
        ok("calculator_receipt:"+receipt["job"],len(matches)==1)
    R["historical_calculator_receipts_verified"]=len(gate["native_receipts"])
    vm=Path("/home/denis/projects/nsp-office-vm/evidence/ROOT_QA13_NATIVE_20261029.zip")
    ok("vm_xls_evidence_archive_sha",H(vm.read_bytes())=="04bd5942bca86747f15e8f41a838661061d746efff14df9cf4156f4cab76d4fc")
    vmz=zipfile.ZipFile(vm)
    ok("vm_xls_evidence_zip_crc",vmz.testzip() is None)
    blobs=[vmz.read(n) for n in vmz.namelist() if n.endswith((".json",".xml"))]
    for name in z.namelist():
        if not name.endswith(".xls"):continue
        sha=H(z.read(name));matches=[n for n,b in zip([n for n in vmz.namelist() if n.endswith((".json",".xml"))],blobs) if sha.encode() in b]
        ok(name+":vm_exact_sha_evidence",bool(matches))
        R["files"].append({"file":name,"status":"UNCHANGED_VM_EVIDENCE_CONTAINS_EXACT_SHA","sha256":sha,"vm_archive_sha256":H(vm.read_bytes()),"evidence_members":matches})
    for name in ("09-checklist-peredachi.pdf","10-sroki-hraneniya.pdf"):
        ok(name+":unchanged",z.read(name)==old.read(name))
        R["files"].append({"file":name,"status":"BYTE_IDENTICAL_HISTORICAL_PDF_NO_NEW_LEGAL_REVIEW","sha256":H(z.read(name))})
    R["files"].append({"file":"00-INSTRUKCIYA.pdf","status":"SINGLE_GUIDE_CONSOLIDATED_SOURCE_NOTES_PRESENT","sha256":H(z.read("00-INSTRUKCIYA.pdf"))})
    ok("all_eighteen_files_covered",len(R["files"])==18)
    R["status"]="P1_SOURCE_TEXT_AND_INHERITED_CALCULATION_EVIDENCE_RECONCILED_OWNER_PENDING"
    R["limits"]=["No new Office execution or new legal opinion","Word layout changes do not inherit original native layout acceptance","VM XLS exact SHA occurs in saved evidence; no new scenarios are claimed","Owner acceptance and P1 publication remain pending"]
except BaseException as e:
    R["status"]="STOP_REVIEW_REQUIRED";R["error"]=type(e).__name__+": "+str(e);raise
finally:
    O.write_text(json.dumps(R,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":R["status"],"checks":len(R["checks"]),"passed":sum(R["checks"].values()),"files":len(R["files"]),"unique_moved_notes_present_in_pdf":R.get("unique_moved_notes_present_in_pdf"),"historical_calculator_receipts":R.get("historical_calculator_receipts_verified"),"error":R.get("error")},ensure_ascii=False))
