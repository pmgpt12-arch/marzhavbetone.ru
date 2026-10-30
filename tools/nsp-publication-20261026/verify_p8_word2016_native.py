#!/usr/bin/env python3
"""Verify immutable P8 Word2016 print evidence, independent of product release."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROWS = {
    "07":"07-trebovanie-o-vyplate-avansa.docx",
    "08":"08-algoritm-s-vas-trebuyut-vernut-avans.docx",
    "10":"10-otvet-na-trebovanie-o-vozvrate-avansa.docx",
}

def sha(data): return hashlib.sha256(data).hexdigest()

def verify(root, receipt, reconciliation, owner):
    errors=[]
    def require(test,label):
        if not test: errors.append(label)
    require(receipt.get("schema")=="NSP_P8_WORD2016_NATIVE_QA_V1","receipt_schema")
    require(receipt.get("native_print_status")=="PASS","native_print_pass")
    require(receipt.get("files_total")==3 and receipt.get("files_passed")==3,"exact_three_passed")
    require(receipt.get("release_permission")=="HOLD" and reconciliation.get("release_permission")=="HOLD","HOLD_unchanged")
    require(receipt.get("archive_edition_status")=="EDITION_NOT_ACCEPTED","edition_not_accepted")
    require(owner.get("release_permission")=="HOLD" and owner.get("public_release_authorized") is False,"owner_not_releasing")
    require(receipt.get("editorial_content_owner_acceptance")=="PENDING","editorial_content_pending")
    byname={row["filename"]:row for row in reconciliation["per_file_decisions"]}
    candidate=receipt.get("files",[])
    require(len(candidate)==3,"three_rows")
    for key,name in ROWS.items():
        entries=[x for x in candidate if x.get("tag")==key and x.get("filename")==name]
        require(len(entries)==1, "row_exact_"+key)
        if len(entries)!=1:continue
        item=entries[0];x=byname.get(name,{})
        require(item.get("source_sha256")==x.get("qa01_candidate_sha256"),"sha_vs_reconciliation_"+key)
        l=owner["owner_layout_approvals"].get(name,{})
        require(item.get("source_sha256")==l.get("reviewed_sha256"),"sha_vs_owner_visual_"+key)
        require(l.get("editorial_content_acceptance")=="PENDING_SEPARATE_OWNER_DECISION","not_content_accepted_"+key)
        require(item.get("native_worker",{}).get("status")=="PASS","worker_pass_"+key)
        require(item.get("native_worker",{}).get("source_sha256")==item.get("source_sha256"),"worker_sha_"+key)
        require(item.get("native_worker",{}).get("word_version")=="16.0","word_version_"+key)
        require(item.get("pdf_pages")==1 and "A4" in item.get("pdf_page_size",""),"pdf_pages_"+key)
        require("Microsoft" in item.get("pdf_producer","") and "Word 2016" in item.get("pdf_producer",""),"pdf_producer_"+key)
        require(item.get("lo_to_word_printed_text_similarity")==1.0,"printed_text_full_match_"+key)
        require(all(item.get("checks",{}).values()) and bool(item.get("checks",{})),"source_checks_"+key)
        require(item.get("pass") is True and not item.get("bbox_overflow"),"print_visual_bounds_"+key)
        filename="P8-"+key+"-Word2016.pdf"
        require(item.get("native_pdf_file")==filename,"pdf_name_"+key)
        f=root/filename
        require(f.is_file(),"pdf_exists_"+key)
        if f.is_file():
            b=f.read_bytes()
            require(b.startswith(b"%PDF-") and len(b)>10000,"pdf_signature_"+key)
            require(sha(b)==item.get("native_pdf_sha256"),"pdf_sha_"+key)
    require(candidate[1].get("native_worker",{}).get("pages")=="2","counter_mismatch_explicitly_documented")
    return errors

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--root",type=Path,default=HERE)
    arg.add_argument("--output",type=Path)
    opts=arg.parse_args()
    root=opts.root
    evidence=json.loads((root/"P8_WORD2016_NATIVE_PRINT_RECEIPT.json").read_text(encoding="utf-8"))
    reconciliation=json.loads((root/"P8_EDITION_RECONCILIATION.json").read_text(encoding="utf-8"))
    owner=json.loads((root/"P8_OWNER_COMPONENT_DECISIONS_20261027.json").read_text(encoding="utf-8"))
    errors=verify(root,evidence,reconciliation,owner)
    # Negative regression checks must reject a changed PDF, a re-labeled SHA,
    # and any attempt to infer an accepted whole edition from native print pass.
    tests=[]
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix="nsp-p8-native-verify-") as temp:
        t=Path(temp)
        for n in ("07","08","10"):
            (t/("P8-"+n+"-Word2016.pdf")).write_bytes((root/("P8-"+n+"-Word2016.pdf")).read_bytes())
        mutated=copy.deepcopy(evidence)
        (t/"P8-07-Word2016.pdf").write_bytes((t/"P8-07-Word2016.pdf").read_bytes()+b"QA_MUTATION")
        tests.append({"name":"tampered_pdf_refused","pass":any("pdf_sha_07"==v for v in verify(t,mutated,reconciliation,owner))})
    modified_owner=copy.deepcopy(owner)
    modified_owner["owner_layout_approvals"]["07-trebovanie-o-vyplate-avansa.docx"]["reviewed_sha256"]="0"*64
    tests.append({"name":"forged_owner_layout_sha_refused","pass":"sha_vs_owner_visual_07" in verify(root,evidence,reconciliation,modified_owner)})
    released=copy.deepcopy(reconciliation)
    released["release_permission"]="ALLOW"
    tests.append({"name":"altered_release_gate_refused","pass":"HOLD_unchanged" in verify(root,evidence,released,owner)})
    result={
        "schema":"NSP_P8_WORD2016_EVIDENCE_GATE_V1",
        "verified_utc":datetime.now(timezone.utc).isoformat(),
        "source_receipt":"P8_WORD2016_NATIVE_PRINT_RECEIPT.json",
        "native_evidence_files":3,
        "status":"PASS" if not errors and all(x["pass"] for x in tests) else "FAIL",
        "failures":errors,
        "negative_tests":tests,
        "release_permission":"HOLD",
        "edition_gate":"EDITION_NOT_ACCEPTED",
        "editorial_owner_acceptance":"PENDING",
    }
    if opts.output:opts.output.parent.mkdir(parents=True,exist_ok=True);opts.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"pdf_count":3,"negative_tests_passed":sum(x["pass"] for x in tests),"checks_failed":len(errors),"release":"HOLD"},ensure_ascii=False))
    if result["status"]!="PASS":raise SystemExit(2)
if __name__=="__main__":main()
