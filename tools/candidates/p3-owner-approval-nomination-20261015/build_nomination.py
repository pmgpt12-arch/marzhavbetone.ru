#!/usr/bin/env python3
"""Read-only exact-source nominal P3 candidate passport. Does not mutate live registry."""
import hashlib,io,json,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
HEAD="2732bf2456fc5e0dada47d7dac710b284f7fc689"
PARENT_PR=652
ZIP_PATH="tools/candidates/p3-aosr-form-layout-20261015/P3-11-buyer-AOSR-formatted-20261015.zip"
DOC_PATH="tools/candidates/p3-aosr-form-layout-20261015/03-akt-skrytyh-rabot.docx"
OLD_MANIFEST="tools/candidates/p3-buyer-final-v2-20261015/manifest.json"
EXPECTED_ZIP="955e6e0ee686f5f9e03a0dc8141c021db5667e35f195c3886f630555acd2a5b1"
EXPECTED_DOC="b6ec767ecccb73a842c6432c61efc0441f9decf83ab50fb964372daf0dfe0c05"
def git(*args):
    return subprocess.check_output(["git","-C",str(ROOT),*args]).strip().decode()
def blob_at(path):
    return git("rev-parse",f"{HEAD}:{path}")
def sha(data):
    return hashlib.sha256(data).hexdigest()
assert subprocess.run(["git","-C",str(ROOT),"merge-base","--is-ancestor",HEAD,git("rev-parse","HEAD")],check=False).returncode==0, "SOURCE_COMMIT_NOT_ANCESTOR"
old=json.loads((ROOT/OLD_MANIFEST).read_text())
assert len(old["files"])==11
zipdata=(ROOT/ZIP_PATH).read_bytes()
assert sha(zipdata)==EXPECTED_ZIP
raw=(ROOT/DOC_PATH).read_bytes()
assert sha(raw)==EXPECTED_DOC
assert blob_at(ZIP_PATH)==git("hash-object",str(ROOT/ZIP_PATH))
assert blob_at(DOC_PATH)==git("hash-object",str(ROOT/DOC_PATH))
with zipfile.ZipFile(io.BytesIO(zipdata)) as z:
    assert z.testzip() is None
    assert len(z.namelist())==11
    assert z.read("03-akt-skrytyh-rabot.docx")==raw
    rows=[]
    for r in old["files"]:
        name=r["name"]
        path=DOC_PATH if name=="03-akt-skrytyh-rabot.docx" else r["relative_source_path"]
        member=z.read(name)
        assert sha(member)==sha(subprocess.check_output(["git","-C",str(ROOT),"show",f"{HEAD}:{path}"]))
        rows.append({
          "registry_id":f"P3-NOM-20261015-{name}",
          "target_sku":"P3","runtime_sku":"p3",
          "member":name,"relative_path":path,
          "commit":HEAD,"git_blob":blob_at(path),
          "sha256":sha(member),"bytes":len(member),
          "format":name.split(".")[-1],
          "role":"nominated_candidate","nomination_source":"owner-approved AOSR #619:6190381029",
          "content_status":"PASS_INSPECTED_SCOPE",
          "office_status":("NATIVE_WORD_CURRENT_EXACT_SHA_PASS" if name=="03-akt-skrytyh-rabot.docx" else "NATIVE_WORD_PREVIOUS_EXACT_SHA_PASS" if name.endswith(".docx") else "NATIVE_EXCEL_OPEN_EXACT_SHA_OWNER_SCENARIOS_REPORTED_PASS" if name.endswith(".xlsx") else "PREVIOUS_PDF_VISUAL_PASS" if name.endswith(".pdf") else "NOT_APPLICABLE_TXT"),
          "release_status":"HOLD_NOT_LIVE"
        })
assert rows[3]["sha256"]==EXPECTED_DOC
assert len({v["member"] for v in rows})==11
nom={
 "schema_version":1,
 "type":"P3_FORMAL_CANDIDATE_NOMINATION_EVIDENCE_ONLY",
 "target_sku":"P3","runtime_sku":"p3",
 "title":"Система подготовки и проверки документов КС-2 и КС-3 перед сдачей",
 "owner_approved_scope":"AOSR 03 five acts visual/form content only",
 "owner_approval_issue_comment":"https://github.com/pmgpt12-arch/marzhavbetone.ru/issues/619#issuecomment-6190381029",
 "approved_docx_sha256":EXPECTED_DOC,
 "source_pr":PARENT_PR,"source_head":HEAD,
 "candidate_archive":{"relative_path":ZIP_PATH,"sha256":EXPECTED_ZIP,"git_blob":blob_at(ZIP_PATH),
   "bytes":len(zipdata),"file_count":11,"role":"nominated_candidate","release_status":"HOLD"},
 "member_artifacts":rows,
 "evidence":{
  "native_word_job":"p3-652-03-role-native-20261015-v1",
  "native_word_pdf_sha256":"a97baf76a208f672bb375799d678f399985c45f38f0b789ed0663375a07ee8b6",
  "native_word_report_sha256":"b4775bb1bb626439ef996b99434e461fe1236feba22c219cf1187223b6cc9be0",
  "independent_new_zip_gate_receipt_sha256":"d3e4b0ec3d941705149ccbbb4d1afcd4a8bea1b6327d0e802c274355a19bcb9d",
  "owner_excel_feedback":"OWNER_REPORTED_PASS_02_06; exact laptop-local SHA unverified",
  "normative_pass":"PR646 18/18 same normative baseline; P3 new role-label delta retained legal descriptors",
  "terminology_check":"PASS_CURRENT_ZIP_11_OF_11",
  "exact_head_actions":"PR652 2/2 SUCCESS"
 },
 "gates":{
   "G1":"PASS_EXACT_ARCHIVE_INTEGRITY",
   "G2":"PASS_INSPECTED_PRACTICAL_CONTENT",
   "G3":"PASS_INSPECTED_CROSS_DOCUMENT_WORKFLOW",
   "G4":"OWNER_AOSR_APPROVED; OWNER_EXCEL_REPORTED_PASS; FINAL_END_TO_END_BUYER_GATE_OPEN",
   "G5":"PR646_NORMATIVE_REUSED; NEW_LABEL_DELTA_ACCEPTED_BY_OWNER_NOT_NEW_LEGAL_OPINION",
   "G6":"CURRENT_DOC03_NATIVE_WORD_PASS; OTHER_EXACT_SHA_REUSED",
   "G7":"PASS_CURRENT_NATIVE_PRINT_11_A4_AND_OWNER_FORM_APPROVAL",
   "G8":"HOLD_FORMAL_RELEASE_NOT_AUTHORIZED"
 },
 "release":{
  "product_full_G1_G8_accepted":False,
  "production_deploy":False,
  "canonical_files_changed":False,
  "price_sku_payment_changes":False,
  "remaining":["independent complete end-to-end buyer/release acceptance","separate owner release authorization"]
 }}
target=HERE/"nomination.json"
if target.exists():
    assert json.loads(target.read_text())==nom,"EXISTING_NOMINATION_DRIFT"
else:
    target.write_text(json.dumps(nom,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"status":"PASS_NOMINATION_CANDIDATE_ONLY","source_head":HEAD,"zip_sha256":EXPECTED_ZIP,
 "members":len(rows),"new_docx_sha256":EXPECTED_DOC,
 "registry_role":"nominated_candidate","G1_G8_full":False,"nomination_sha256":sha(target.read_bytes())},ensure_ascii=False))
