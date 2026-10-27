#!/usr/bin/env python3
"""Reproducible P8 edition/acceptance negative QA; no release or archive writes.

Run:
python3 tools/nsp-publication-20261026/test_p8_edition_binding.py \
    --output nsp-publication-staging-evidence/P8_EDITION_GATE_TEST_RECEIPT.json
"""
import argparse
import copy
import hashlib
import io
import json
import pathlib
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone

from p8_edition_binding import (
    ACCEPTED_EDITION_ID, ACCEPTED_ZIP_SHA, HERE, OWNER_ARCHIVE,
    OWNER_COMMIT, ROOT, accepted_contract, archive_members,
    check_p8_edition, original_git_bytes, sha,
)

QA01_BRANCH = "origin/qa/nsp-qa01-products-20261023"


def git_bytes(commit, path):
    p=subprocess.run(["git","-C",str(ROOT),"show",commit+":"+path],
                     capture_output=True,timeout=40)
    if p.returncode:
        raise RuntimeError("SOURCE_COMMIT_NOT_AVAILABLE:"+commit+":"+path)
    return p.stdout


def qa01_fixture():
    matrix=json.loads((HERE/"NSP_ACCEPTED_ARTIFACTS_MATRIX.json").read_text("utf-8"))
    record=next(row for row in matrix["rows"] if row["SKU"]=="P8")
    assert record["release_permission"]=="HOLD"
    archive=git_bytes(QA01_BRANCH,record["archive_source_name"])
    assert sha(archive)==record["accepted_archive_sha256"]
    assert record["accepted_archive_sha256"]=="07a16f0d80fe9d3bfdc435acdc513aa4df45029450f0f7afe951d8c19819e038"
    src=json.loads(git_bytes(QA01_BRANCH,record["member_manifest"]))
    raw=next(x for x in src["paid"] if x["sku"]=="P8")
    self_member_sha={m["name"]:m["sha256"] for m in raw["members"]}
    assert len(self_member_sha)==11 and archive_members(archive)==self_member_sha
    return archive,self_member_sha


def repack(original, change=None):
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        elements=[(n,z.read(n)) for n in z.namelist() if not n.endswith("/")]
    if change is not None:
        elements=[(n,b+b"__QA_MUTATION_DO_NOT_RELEASE" if n==change else b) for n,b in elements]
    dest=io.BytesIO()
    with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as out:
        for n,b in elements:out.writestr(n,b)
    return dest.getvalue()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    opts=ap.parse_args()
    scenarios=[]
    def record(name, condition, result, **extra):
        scenarios.append({"test":name,"pass":bool(condition),"observed":result,**extra})
        assert condition, name + " " + json.dumps(result,ensure_ascii=False,default=str)

    contract=accepted_contract()
    r3=original_git_bytes(OWNER_ARCHIVE)
    qa01,own_members=qa01_fixture()
    assert sha(r3)==ACCEPTED_ZIP_SHA and sha(qa01)!=sha(r3)
    assert len(archive_members(r3))==len(archive_members(qa01))==11

    historical=check_p8_edition(r3,ACCEPTED_EDITION_ID)
    record("historical_whole_R3_acceptance_but_release_HOLD",
           historical["status"]=="HISTORICAL_EDITION_ACCEPTED_HOLD" and
           not historical["eligible_for_new_sales"] and
           historical["RELEASE_PERMISSION"]=="HOLD",
           historical)

    qa01check=check_p8_edition(qa01,"P8-QA01-20261023-READY_CANDIDATE")
    record("QA01_correct_self_SHA_and_members_still_EDITION_NOT_ACCEPTED",
           sha(qa01)=="07a16f0d80fe9d3bfdc435acdc513aa4df45029450f0f7afe951d8c19819e038" and
           archive_members(qa01)==own_members and
           qa01check["status"]=="EDITION_NOT_ACCEPTED" and
           not qa01check["archive_sha_match"] and not qa01check["member_sha_match"],
           qa01check,qa01_own_sha_pass=True,qa01_own_11_member_sha_pass=True)

    mislabeled=check_p8_edition(qa01,ACCEPTED_EDITION_ID)
    record("QA01_forged_R3_edition_label_rejected",
           mislabeled["status"]=="EDITION_NOT_ACCEPTED" and mislabeled["edition_id_match"] and
           not mislabeled["archive_sha_match"],mislabeled)

    wrong_id=check_p8_edition(r3,"P8-QA01-20261023-READY_CANDIDATE")
    record("R3_bytes_but_wrong_edition_id_rejected",
           wrong_id["status"]=="EDITION_NOT_ACCEPTED" and wrong_id["archive_sha_match"] and
           wrong_id["member_sha_match"] and not wrong_id["edition_id_match"],wrong_id)

    historical_production_path="tools/candidates/remaining-batch-r3-20261018/release-20261020/production/P8-production-buyer.zip"
    different_outer=original_git_bytes(historical_production_path)
    repacked=check_p8_edition(different_outer,ACCEPTED_EDITION_ID)
    record("R3_repacked_same_11_members_but_different_outer_sha_rejected",
           archive_members(different_outer)==archive_members(r3) and
           sha(different_outer)!=sha(r3) and
           repacked["status"]=="EDITION_NOT_ACCEPTED" and repacked["member_sha_match"] and
           not repacked["archive_sha_match"],repacked)

    target="02-kalkulyator-usloviy-avansa.xlsx"
    tampered_zip=repack(r3,target)
    modified=check_p8_edition(tampered_zip,ACCEPTED_EDITION_ID)
    record("one_member_changed_and_archive_rehashed_rejected",
           modified["status"]=="EDITION_NOT_ACCEPTED" and not modified["member_sha_match"] and
           not modified["archive_sha_match"],modified)

    for key,mutator in [
        ("owner_evidence_commit_forged",lambda x:x["ACCEPTANCE_EVIDENCE"].update({"commit":"0"*40})),
        ("owner_evidence_path_forged",lambda x:x["ACCEPTANCE_EVIDENCE"].update({"path":"tools/unknown.json"})),
        ("owner_evidence_sha_forged",lambda x:x["ACCEPTANCE_EVIDENCE"].update({"sha256":"0"*64})),
        ("accepted_edition_id_forged",lambda x:x.update({"ACCEPTED_EDITION_ID":"P8-QA01-20261023-READY_CANDIDATE"})),
        ("accepted_outer_sha_forged",lambda x:x.update({"ARCHIVE_SHA256":sha(qa01)})),
        ("accepted_member_sha_forged",lambda x:x["MEMBER_SHA256"].update({target:own_members[target]})),
        ("owner_evidence_absent",lambda x:x.update({"ACCEPTANCE_EVIDENCE":{}}))
    ]:
        anchor=json.loads((HERE/"P8_ACCEPTED_EDITION_ANCHOR.json").read_text("utf-8"))
        mutator(anchor)
        answer=check_p8_edition(qa01,"P8-QA01-20261023-READY_CANDIDATE",anchor=anchor)
        record(key,answer["status"]=="ACCEPTANCE_EVIDENCE_INVALID",answer)

    # Per-file reconciliation must be complete and pinned to exact bytes.
    recon=json.loads((HERE/"P8_EDITION_RECONCILIATION.json").read_text("utf-8"))
    by_name={x["filename"]:x for x in recon["per_file_decisions"]}
    accepted_members=archive_members(r3)
    assert len(by_name)==11 and set(by_name)==set(own_members)==set(accepted_members)
    roles={}
    for name,item in by_name.items():
        assert item["r3_whole_approved_sha256"]==accepted_members[name]
        assert item["qa01_candidate_sha256"]==own_members[name]
        roles[item["approval_classification"]]=roles.get(item["approval_classification"],0)+1
    exact_roles={
        "R3_UNCHANGED_INHERITS_WHOLE_OWNER_APPROVAL":5,
        "LATER_OWNER_ACCEPTED_SINGLE_FILE_NOT_NEW_ZIP":2,
        "DRAFT_EDITORIAL_QA_ONLY_NO_WHOLE_OWNER_ACCEPTANCE":3,
        "QA01_PACKAGED_TEXT_NOT_OWNER_ACCEPTED_AND_NOT_QA01_MASTER_BYTES":1}
    record("all_11_file_reconciliation_SHA_and_acceptance_roles_match",
           roles==exact_roles and recon["release_permission"]=="HOLD"
           and recon["selected_new_release_edition"] is None,
           {"files":len(by_name),"acceptance_classes":roles,
            "overall_release":recon["release_permission"]})
    master=git_bytes(QA01_BRANCH,"products-storage/10-avans-usloviya-i-pribyl/00-START-HERE.txt")
    record("QA01_start_here_candidate_differs_from_own_QA01_git_master",
           sha(master)!=own_members["00-START-HERE.txt"] and
           by_name["00-START-HERE.txt"]["qa01_zip_member_matches_git_master"] is False,
           {"QA01_member_sha":own_members["00-START-HERE.txt"],
            "QA01_git_master_sha":sha(master),
            "owner_acceptance_for_changed_candidate":"NOT_FOUND"})

    # The real gate's P8 row performs its own technical source SHA+member checks
    # before the independently anchored owner-edition rejection.
    from archive_version_gate import verify
    matrix=json.loads((HERE/"NSP_ACCEPTED_ARTIFACTS_MATRIX.json").read_text("utf-8"))
    candidate=next(x for x in matrix["rows"] if x["SKU"]=="P8")
    gate=verify(candidate)
    record("archive_version_gate_P8_technical_pass_semantic_EDITION_NOT_ACCEPTED",
           gate.get("technical_source_verified") is True and
           gate["source_sha256"]==candidate["accepted_archive_sha256"] and
           "EDITION_NOT_ACCEPTED" in gate["failures"] and
           gate["status"]=="SOURCE_VERIFIED_EDITION_BLOCKED",gate)

    # The strict exit is nonzero even when QA01 outer SHA and member manifest
    # are internally correct. Default reporting mode remains nonrelease-only.
    with tempfile.TemporaryDirectory(prefix="nsp-p8-gate-test-") as temp:
        output=pathlib.Path(temp)/"receipt.json"
        process=subprocess.run(["python3",str(HERE/"archive_version_gate.py"),
                                "--require-edition-accepted","--output",str(output)],
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=65)
        strict=json.loads(output.read_text())
        record("strict_accepted_edition_gate_refuses_QA01_exit_2",
               process.returncode==2 and
               strict["p8_edition_status"]=="EDITION_NOT_ACCEPTED" and
               strict["technical_source_verified"]==11 and strict["release_allowed"]==0,
               {"exit_code":process.returncode,"p8_edition_status":strict["p8_edition_status"],
                "source_technical_verified":strict["technical_source_verified"],
                "public_release_allowed":strict["release_allowed"]})
    receipt={
        "schema":"NSP_P8_ACCEPTED_EDITION_GATE_REGRESSION_V1",
        "run_utc":datetime.now(timezone.utc).isoformat(),
        "source":"IMMUTABLE_2026_10_20_OWNER_APPROVAL_GIT_COMMIT_AND_EXACT_ZIP",
        "accepted_edition_id":ACCEPTED_EDITION_ID,
        "owner_receipt_commit":OWNER_COMMIT,
        "r3_accepted_zip_sha256":sha(r3),
        "qa01_own_valid_archive_sha256":sha(qa01),
        "qa01_own_valid_member_count":len(own_members),
        "tests":scenarios,"count":len(scenarios),
        "passed":sum(t["pass"] for t in scenarios),
        "release_permission":"HOLD","production_modified":False,
        "source_archives_modified":False,"verdict":"PASS_ALL_TESTS_QA01_EDITION_NOT_ACCEPTED"}
    pathlib.Path(opts.output).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":receipt["verdict"],"passes":receipt["passed"],"tests":receipt["count"],
        "qa01_technical_sha":sha(qa01),"qa01_accepted_edition":"EDITION_NOT_ACCEPTED",
        "strict_gate_exit":2,"release":"HOLD"},ensure_ascii=False))


if __name__=="__main__":
    main()
