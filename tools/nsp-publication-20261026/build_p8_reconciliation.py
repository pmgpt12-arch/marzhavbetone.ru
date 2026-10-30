#!/usr/bin/env python3
"""Read-only reconstruction of P8 accepted member history; no nomination/release."""
import hashlib, io, json, pathlib, subprocess, zipfile
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[2]
HERE=pathlib.Path(__file__).resolve().parent
R3="tools/candidates/remaining-batch-r3-20261018/"
OWNER_COMMIT="bf40053356b8bc1ab81eaab197dbbebf4068c752"
QA01_COMMIT="5361c80125107d9bb47d355bd5730f8b6e2da2c1"
MASTER_ROOT="products-storage/10-avans-usloviya-i-pribyl/"
STAGED=pathlib.Path("/home/denis/.local/state/nsp-publication-20261026/repo/tools/nsp-publication-20261026/staging-accepted/P8-QA01-READY-CANDIDATE-NONRELEASE.zip")

def sha(x):return hashlib.sha256(x).hexdigest()
def git_bytes(commit,path):
    result=subprocess.run(["git","-C",str(ROOT),"show",commit+":"+path],capture_output=True,timeout=45)
    if result.returncode:raise RuntimeError("GIT_SOURCE_NOT_FOUND:"+commit+":"+path+":"+result.stderr.decode("utf-8","replace")[:130])
    return result.stdout
def data_zip(content):
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        assert z.testzip() is None
        return {name:{"sha256":sha(z.read(name)),"bytes":len(z.read(name))}
                for name in z.namelist() if not name.endswith("/")}

def main():
    owner_evidence_path=R3+"release-20261020/owner-acceptance.json"
    owner_raw=git_bytes(OWNER_COMMIT,owner_evidence_path)
    owner=json.loads(owner_raw)
    assert owner["status"]=="OWNER_ACCEPTED_AND_RELEASE_AUTHORIZED"
    accepted=next(x for x in owner["packages"] if x["sku"]=="P8")
    reviewed_zip_path=R3+"final-buyer-review-20261020/"+accepted["archive"]
    accepted_zip=git_bytes(OWNER_COMMIT,reviewed_zip_path)
    assert sha(accepted_zip)==accepted["sha256"]
    approved=data_zip(accepted_zip)
    manifest_path=R3+"final-buyer-review-20261020/P8-manifest-R3.json"
    manifest=json.loads(git_bytes(OWNER_COMMIT,manifest_path))
    assert manifest["sha256"]==sha(accepted_zip) and manifest["file_count"]==accepted["file_count"]==len(approved)==11
    assert approved=={m["file"]:{"sha256":m["sha256"],"bytes":m["bytes"]} for m in manifest["members"]}
    prod_path=R3+"release-20261020/production/P8-production-buyer.zip"
    prod=git_bytes(OWNER_COMMIT,prod_path)
    assert data_zip(prod)==approved
    current=STAGED.read_bytes()
    assert sha(current)=="07a16f0d80fe9d3bfdc435acdc513aa4df45029450f0f7afe951d8c19819e038"
    current_members=data_zip(current)
    assert set(current_members)==set(approved)
    # Owner specifically accepted only workbook revisions on 22 October, never the new 11-file package.
    owner_cases={}
    for suffix,commit,name in [
        ("02","111f12f45ff5bce98ffbd37391b9b637ae8a1ac8","02-kalkulyator-usloviy-avansa.xlsx"),
        ("09","281097a72dbba67a4563b4ad850d03808b66b365","09-raschet-otrabotannoy-chasti-avansa.xlsx")]:
        path="tools/nsp-product-audit-fixes-20261021/p8-"+suffix+"-candidate/OWNER_ACCEPTANCE.json"
        receipt=json.loads(git_bytes(commit,path))
        assert receipt["status"]=="OWNER_MANUAL_ACCEPTANCE_PASS"
        assert receipt["accepted_sha256"]==current_members[name]["sha256"]
        owner_cases[name]={"acceptance_status":receipt["status"],
          "owner_statement":receipt["owner_statement"],
          "accepted_date":receipt["reported_date"],"acceptance_record_commit":commit,
          "acceptance_record_path":path,"accepted_sha256":receipt["accepted_sha256"],
          "scope":"SINGLE_FILE_ONLY_NOT_COMPLETE_ZIP"}

    # Later owner decisions are component-scoped and do NOT supersede R3 whole-edition gate.
    review=json.loads((HERE/"P8_OWNER_COMPONENT_DECISIONS_20261027.json").read_text("utf-8"))
    assert review["release_permission"]=="HOLD"
    assert review["qa01_candidate_archive_sha256"]==sha(current)
    approved_start=review["owner_component_acceptances"]["00-START-HERE.txt"]
    assert approved_start["accepted_sha256"]==current_members["00-START-HERE.txt"]["sha256"]
    assert approved_start["scope"]=="SINGLE_FILE_CONTENT_AND_APPEARANCE_ONLY"
    assert sha((HERE/"p8-owner-reviewed/00-START-HERE.txt").read_bytes())==approved_start["accepted_sha256"]
    for name,layout in review["owner_layout_approvals"].items():
        assert name.startswith(("07-","08-","10-")) and name in current_members
        assert layout["reviewed_sha256"]==current_members[name]["sha256"]
        assert layout["scope"]=="VISUAL_LAYOUT_ONLY"
        assert layout["editorial_content_acceptance"]=="PENDING_SEPARATE_OWNER_DECISION"
    qa01_pack=json.loads(git_bytes(QA01_COMMIT,"tools/nsp-qa01-20261023/CURRENT_CANDIDATE_PACKAGES.json"))
    candidate=next(x for x in qa01_pack["paid"] if x.get("sku")=="P8")
    assert candidate["sha256"]==sha(current)
    assert candidate["member_count"]==11
    candidate_manifest={m["name"]:m["sha256"] for m in candidate["members"]}
    assert candidate_manifest=={n:x["sha256"] for n,x in current_members.items()}
    matrix=json.loads(git_bytes(QA01_COMMIT,"tools/nsp-qa01-20261023/READINESS_MATRIX.json"))
    qa_row=next(x for x in matrix["paid"] if x["sku"]=="P8")
    assert qa_row["status"]=="READY_CANDIDATE" and qa_row["candidate_sha256"]==sha(current)
    p8_fixes_commit="cd051f422ba5899999f6099fae1de689b089dbe7"
    fixes={n for n in current_members if n.startswith(("07-","08-","10-"))}
    branch_replacement_checks=[]
    for name in sorted(current_members):
        command=["git","-C",str(ROOT),"show",QA01_COMMIT+":"+MASTER_ROOT+name]
        res=subprocess.run(command,capture_output=True,timeout=20)
        present=res.returncode==0
        current_matches_master=present and sha(res.stdout)==current_members[name]["sha256"]
        old_sha=approved[name]["sha256"];current_sha=current_members[name]["sha256"]
        if old_sha==current_sha:
            role="R3_UNCHANGED_INHERITS_WHOLE_OWNER_APPROVAL"
            approved_component=old_sha;basis={"date":"2026-10-20","record":owner_evidence_path,
              "commit":OWNER_COMMIT,"status":"OWNER_ACCEPTED_WHOLE_R3"}
        elif name in owner_cases:
            role="LATER_OWNER_ACCEPTED_SINGLE_FILE_NOT_NEW_ZIP"
            approved_component=current_sha;basis=owner_cases[name]
        elif name in fixes:
            role="DRAFT_EDITORIAL_QA_ONLY_NO_WHOLE_OWNER_ACCEPTANCE"
            approved_component=None;basis={"date":"2026-10-21","commit":p8_fixes_commit,
              "pull_request":675,"state":"DRAFT_NOT_MERGED",
              "evidence":"tools/nsp-product-audit-fixes-20261021/REPORT_RU.md",
              "status":"33_SCOPED_TESTS_NOT_WHOLE_PRODUCT_ACCEPTANCE",
              "owner_layout_approval":review["owner_layout_approvals"][name],
              "editorial_content_owner_acceptance":"PENDING"}
        elif name=="00-START-HERE.txt":
            role="OWNER_ACCEPTED_SINGLE_FILE_FROM_QA01_ZIP_NOT_GIT_MASTER"
            approved_component=current_sha
            basis=dict(approved_start)
            basis.update({"date":"2026-10-27",
                "record":"tools/nsp-publication-20261026/P8_OWNER_COMPONENT_DECISIONS_20261027.json",
                "status":"OWNER_ACCEPTED_EXACT_QA01_MEMBER_NOT_WHOLE_EDITION"})
        else:raise AssertionError("Unexpected unapproved changed member "+name)
        branch_replacement_checks.append({
            "filename":name,
            "r3_whole_approved_sha256":old_sha,
            "qa01_candidate_sha256":current_sha,
            "r3_production_member_sha256":data_zip(prod)[name]["sha256"],
            "qa01_git_master_sha256":sha(res.stdout) if present else None,
            "qa01_zip_member_matches_git_master":current_matches_master,
            "changed_since_approved_R3":old_sha!=current_sha,
            "owner_accepted_latest_component_sha256":approved_component,
            "owner_acceptance_basis":basis,
            "approval_classification":role,
            "current_complete_zip_accepted":False,
            "release_permission":"HOLD"})
    counts={}
    for x in branch_replacement_checks:counts[x["approval_classification"]]=counts.get(x["approval_classification"],0)+1
    assert sorted(counts.values())==[1,2,3,5],counts
    changes=[x for x in branch_replacement_checks if x["changed_since_approved_R3"]]
    assert len(changes)==6
    alias="P8-R3-20261020-WHOLE-OWNER-ACCEPTED"
    anchor={
        "schema":"P8_ACCEPTED_EDITION_ANCHOR_V1",
        "SKU":"P8",
        "ACCEPTED_EDITION_ID":alias,
        "ACCEPTANCE_EVIDENCE":{
           "commit":OWNER_COMMIT,"path":owner_evidence_path,
           "sha256":sha(owner_raw),"type":"OWNER_ACCEPTED_WHOLE_BUYER_ZIP",
           "accepted_at":owner["at"],"approved_outer_zip_sha256":owner["approved_outer_zip_sha256"],
           "scope":"HISTORICAL_RELEASE_2026_10_20_ONLY"},
        "ARCHIVE_SHA256":accepted["sha256"],
        "ARCHIVE_SOURCE_GIT":{"commit":OWNER_COMMIT,"path":reviewed_zip_path},
        "MEMBER_MANIFEST_GIT":{"commit":OWNER_COMMIT,"path":manifest_path},
        "MEMBER_SHA256":{n:x["sha256"] for n,x in approved.items()},
        "MEMBER_COUNT":11,
        "CURRENT_STAGING_EDITION_ID":"P8-QA01-20261023-READY_CANDIDATE",
        "CURRENT_STAGING_SHA256":sha(current),
        "LAST_FULL_WHOLE_PACKAGE_DECISION":"R3_ACCEPTED_HISTORICAL_ONLY",
        "NEW_EDITIONS_AFTER_R3":"NO_WHOLE_PRODUCT_OWNER_ACCEPTANCE",
        "RELEASE_PERMISSION":"HOLD",
        "ALLOW_NEW_SALES":False,
        "CONTRACT_PURPOSE":"READ_ONLY_SOURCE_EDITION_GATING_NOT_PUBLIC_RELEASE"}
    result={
        "schema":"P8_EDITION_RECONCILIATION_V1","SKU":"P8",
        "prepared_utc":datetime.now(timezone.utc).isoformat(),
        "status":"RELEASE_BLOCKED",
        "PRODUCT_QA_STATUS":"NOT_FULLY_CONFIRMED_FOR_NEW_COMBINED_EDITION",
        "last_accepted_complete_edition_id":alias,
        "accepted_complete_edition":{"date":owner["at"],
            "git_commit":OWNER_COMMIT,"archive_sha256":accepted["sha256"],
            "member_count":11,"acceptance_evidence_path":owner_evidence_path,
            "acceptance_evidence_sha256":sha(owner_raw),
            "scope":"HISTORICAL_R3_ACCEPTED_ONLY_NOT_NEW_RELEASE_AUTHORIZATION"},
        "reviewed_revisions":[
          {"date":"before_2026_10_20","id":"P8-R2","status":"REJECTED_AND_WITHDRAWN","sha256":None,
           "evidence":"tools/candidates/remaining-batch-r3-20261018/WORK-STATUS.md"},
          {"date":"2026-10-20","id":alias,"git_commit":OWNER_COMMIT,
           "archive_sha256":sha(accepted_zip),"members":11,
           "status":"WHOLE_ARCHIVE_OWNER_ACCEPTED_HISTORIC"},
          {"date":"2026-10-20","id":"P8-R3-PRODUCTION-REPACK",
           "archive_sha256":sha(prod),"members":11,
           "status":"REPACK_MATCHES_ALL_R3_MEMBER_SHA_BUT_OUTER_ZIP_DIFFERS",
           "source":prod_path},
          {"date":"2026-10-21","id":"P8-07-08-10-DOCX-AUDIT-PR675",
           "git_commit":p8_fixes_commit,"files":sorted(fixes),
           "status":"TARGETED_EDIT_TEST_PASS_NOT_OWNER_WHOLE_ACCEPTANCE"},
          {"date":"2026-10-22","id":"P8-09-OWNER-ACCEPTED",
           "git_commit":owner_cases["09-raschet-otrabotannoy-chasti-avansa.xlsx"]["acceptance_record_commit"],
           "status":"SINGLE_FILE_OWNER_ACCEPTED_NOT_WHOLE"},
          {"date":"2026-10-22","id":"P8-02-OWNER-ACCEPTED",
           "git_commit":owner_cases["02-kalkulyator-usloviy-avansa.xlsx"]["acceptance_record_commit"],
           "status":"SINGLE_FILE_OWNER_ACCEPTED_NOT_WHOLE"},
          {"date":"2026-10-23","id":"P8-QA01-20261023-READY_CANDIDATE",
           "git_commit":QA01_COMMIT,"archive_sha256":sha(current),"members":11,
           "status":"TECHNICAL_SHA_CRC_MEMBER_PASS_READY_CANDIDATE_NOT_OWNER_ACCEPTED"}],
        "per_file_decisions":branch_replacement_checks,
        "component_acceptance_summary":counts,
        "r3_to_qa01_changed_members":len(changes),
        "r3_to_qa01_unchanged_members":len(branch_replacement_checks)-len(changes),
        "qa01_accepted_sha_by_its_own_manifest":True,
        "qa01_archive_sha256":sha(current),
        "qa01_archive_status":"TECHNICALLY_INTACT_BUT_EDITION_NOT_ACCEPTED",
        "staging_sha256":sha(current),
        "staging_edition_id":"P8-QA01-20261023-READY_CANDIDATE",
        "edition_gate_expected_result":"EDITION_NOT_ACCEPTED",
        "selected_new_release_edition":None,
        "selected_new_release_archive_sha256":None,
        "final_whole_package_qa_gate":"MISSING_AFTER_LATER_2026_10_21_22_COMPONENT_EDITS",
        "necessary_owner_decisions":[
          {"id":"P8-DECISION-01","subject":"00-START-HERE.txt","required":"Accept exact QA01 filename/content SHA (currently does not match QA01 Git master), or approve an exact corrected instruction file and verify all buyer references."},
          {"id":"P8-DECISION-02","subject":"07/08/10 DOCX","required":"Review and accept legal/editorial changes from draft PR #675 and their exact SHA or reject and nominate corrected files."},
          {"id":"P8-DECISION-03","subject":"P8/02 and P8/09","required":"Acknowledge individual accepted SHA 0ca0/33c5 as inputs to the new whole package; no repeat native QA merely because of the earlier candidate."},
          {"id":"P8-DECISION-04","subject":"all 11 files","required":"Nominate exact combined FINAL_QA archive after component approvals; independently accept entire 11-file buyer package and record a new edition ID, outer ZIP SHA, member SHA and evidence commit."},
          {"id":"P8-DECISION-05","subject":"release","required":"A separate new-site publication permission after whole-package QA and product route QA; historical R3 permission cannot be reused."}],
        "edition_anchor_path":"tools/nsp-publication-20261026/P8_ACCEPTED_EDITION_ANCHOR.json",
        "release_permission":"HOLD",
        "production_changed":False,"protected_archives_changed":False}
    result["reviewed_revisions"].append({
        "date":"2026-10-27","id":"P8-00-QA01-MEMBER-OWNER-ACCEPTED",
        "member_sha256":approved_start["accepted_sha256"],
        "source":approved_start["reviewed_source"],"status":"SINGLE_FILE_CONTENT_AND_LAYOUT_ACCEPTED_NOT_WHOLE"})
    result["reviewed_revisions"].append({
        "date":"2026-10-27","id":"P8-07-08-10-OWNER-LAYOUT-ACCEPTED",
        "status":"VISUAL_LAYOUT_ONLY_CONTENT_ACCEPTANCE_PENDING","files":sorted(review["owner_layout_approvals"])})
    result["necessary_owner_decisions"]=[
        item for item in result["necessary_owner_decisions"]
        if item["id"] not in ("P8-DECISION-01","P8-DECISION-03")]
    for item in result["necessary_owner_decisions"]:
        if item["id"]=="P8-DECISION-02":
            item["required"]="Owner already approved the displayed layout. Remaining: owner content/editorial acceptance of exact 07/08/10 DOCX SHA from draft PR #675; no layout rework is requested."
    result["completed_owner_decisions"]=[
        {"subject":"00-START-HERE.txt","date":"2026-10-27","scope":"SINGLE_FILE_CONTENT_AND_APPEARANCE_ONLY",
         "sha256":approved_start["accepted_sha256"],"evidence":"P8_OWNER_COMPONENT_DECISIONS_20261027.json"},
        {"subject":"P8/02 and P8/09 XLSX","date":"2026-10-22",
         "scope":"TWO_INDIVIDUAL_FILE_ACCEPTANCES","evidence":"OWNER_ACCEPTANCE.json at pinned historic commits"},
        {"subject":"07/08/10 DOCX","date":"2026-10-27","scope":"VISUAL_LAYOUT_ONLY",
         "evidence":"P8_OWNER_COMPONENT_DECISIONS_20261027.json"}]
    result["unresolved_owner_content_files"]=sorted(review["owner_layout_approvals"])
    result["owner_decisions_evidence_path"]="tools/nsp-publication-20261026/P8_OWNER_COMPONENT_DECISIONS_20261027.json"
    assert result["component_acceptance_summary"]=={
        "R3_UNCHANGED_INHERITS_WHOLE_OWNER_APPROVAL":5,
        "LATER_OWNER_ACCEPTED_SINGLE_FILE_NOT_NEW_ZIP":2,
        "DRAFT_EDITORIAL_QA_ONLY_NO_WHOLE_OWNER_ACCEPTANCE":3,
        "OWNER_ACCEPTED_SINGLE_FILE_FROM_QA01_ZIP_NOT_GIT_MASTER":1}
    assert result["selected_new_release_edition"] is None and result["release_permission"]=="HOLD"
    (HERE/"P8_ACCEPTED_EDITION_ANCHOR.json").write_text(json.dumps(anchor,ensure_ascii=False,indent=2)+"\n")
    (HERE/"P8_EDITION_RECONCILIATION.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"r3":accepted["sha256"],
      "qa01":sha(current),"matches_R3":5,"changes":len(changes),
      "owner_accepted_individual":len(owner_cases),
      "unresolved_components":[x["filename"] for x in changes if x["owner_accepted_latest_component_sha256"] is None],
      "qa01_member_master_mismatches":[x["filename"] for x in branch_replacement_checks if not x["qa01_zip_member_matches_git_master"]]},ensure_ascii=False))
if __name__=="__main__":main()
