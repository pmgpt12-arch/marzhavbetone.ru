#!/usr/bin/env python3
"""NSP P4/P7-only owner-approved release; native Office QA verified.

Preflight -> private stage -> apply -> delivery bytes -> receipt, or rollback.
Works only on exact currently live P4 v3 and P7 review-v2 source identities.
"""
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import tarfile
import zipfile
from datetime import datetime, timezone

ROOT=pathlib.Path("/mnt/server-data/nsp")
BASE=ROOT/"product-library/accepted-current-20261102/paid"
CAND=ROOT/"operations/qa-product-staging-20261104"
EVIDENCE=pathlib.Path(os.environ["RUNNER_TEMP"])/"nsp-p4p7-evidence"
HERE=pathlib.Path(__file__).resolve().parent
SHA=lambda b:hashlib.sha256(b).hexdigest()
EXPECT={
  "p4":{"sku":"P4","old_zip":"PAID_P4_current.zip","new_zip":"PAID_P4_v3_PALETTE_V3_QA_HOLD.zip",
        "old_sha":"bcba234220c0f52e5a86b5ba3c70c527d086146301030d1f32197e9fa6e264fc",
        "new_sha":"70a728babb810d6277388a5337decce6bfdf21a7e216bc0a512870860a3d3451",
        "old_master":"P4-v3-current.zip","new_master":"P4-v3-palette-v3-20261104.zip",
        "name":"08-pto-bez-zamechaniy","zip":"08-pto-bez-zamechaniy.zip","price":2490000,"members":30,"changed":4},
  "p7":{"sku":"P7","old_zip":"PAID_P7_current.zip","new_zip":"PAID_P7_review-v2_PALETTE_V3_QA_HOLD.zip",
        "old_sha":"99e877fc851843a79c8524f508529ecab7da049aa6886590fcbce68a97676e24",
        "new_sha":"6df6abf578c240ba9e76c9b0e40c7c4cb3bca34c65029e4260b97d82a25ca8a6",
        "old_master":"P7-v2-current.zip","new_master":"P7-v2-palette-v3-20261104.zip",
        "name":"03-dogovor-podryada","zip":"03-dogovor-podryada.zip","price":2490000,"members":13,"changed":3}
}
def now(): return datetime.now(timezone.utc).isoformat()
def archive_members(path, expected_sha, count):
    data=path.read_bytes()
    assert SHA(data)==expected_sha, "ARCHIVE_PIN_DRIFT:"+path.name
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None, "ZIP_CRC_FAIL:"+path.name
        names=z.namelist()
        assert len(names)==count and len(set(names))==len(names),"ARCHIVE_COUNT_DRIFT"
        assert all(pathlib.PurePosixPath(x).name==x for x in names),"ARCHIVE_PATH_NOT_FLAT"
        members={name:SHA(z.read(name)) for name in names}
    return members
def invoke(cmd,timeout=45,inp=None):
    r=subprocess.run(cmd,input=inp,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if r.returncode:
        stderr=r.stderr.decode("utf-8","replace")
        safe_gate=re.search(r"NSP_SCOPED_RELEASE_ERROR=([A-Z0-9_:-]{1,128})",stderr)
        if safe_gate:
            raise RuntimeError("REMOTE_RELEASE_GATE_"+safe_gate.group(1))
        raise RuntimeError("EXECUTOR_FAILED_CODE_"+str(r.returncode))
    return r.stdout
def write(name,body):
    (EVIDENCE/name).write_text(json.dumps(body,ensure_ascii=False,indent=2)+"\n")
def main():
    runid=os.environ["GITHUB_RUN_ID"]
    assert re.fullmatch(r"[0-9]{6,16}",runid)
    assert os.uname().nodename=="ai-workstation","NOT_APPROVED_RUNNER"
    request=json.loads((HERE/"request.json").read_text())
    assert request=={"action":"publish","revision":6},"WRONG_REQUEST"
    before=json.loads((EVIDENCE/"live-before.json").read_text())
    assert before["status"]=="P4_P7_PRODUCTION_READ_ONLY" and before["delivery_ttl"]==3600
    assert set(before["products"])=={"p4","p7"}
    assert before["site_php_sha"] and before["payment_php_sha"]
    staging_path=CAND/"P4P7_V3_PRIVATE_BUYER_QA_RECEIPT.json"
    staging=json.loads(staging_path.read_text())
    independent=json.loads((CAND/"INDEPENDENT_BUYER_QA_RECEIPT_V3.json").read_text())
    assert staging["status"]=="STAGING_PRIVATE_NOT_PUBLISHED"
    assert independent["status"]=="PRIVATE_FULL_43_OF_43_STRUCTURAL_QA_PASS_NOT_PUBLISHED"
    assert set(staging["products"])==set(independent["products"])=={"P4","P7"}
    assert sum(x["members"] for x in staging["products"].values())==43
    assert sum(len(x["changed"]) for x in staging["products"].values())==4
    assert sum(len(x["changed_exact"]) for x in independent["products"].values())==4
    assert sum(x["unchanged_exact"] for x in independent["products"].values())==39
    assert independent["staging_receipt_sha256"]==SHA(staging_path.read_bytes())
    visual=ROOT/"operations/qa-style-candidates-v2-20261103/native-p4p7-header-v3-20261104/VISUAL_REVIEW_V3_20261104.json"
    assert SHA(visual.read_bytes())=="66451e165f725ef3cee3d35d8fd43cc0fceb6cbb44a323db038e324646e05c3a"
    assert json.loads(visual.read_text())["status"]=="TARGETED_5_HEADER_FIXES_PASS_34_PAGE_NO_GROSS_DEFECTS"
    assert staging["visual_receipt_sha256"]==SHA(visual.read_bytes())
    products={}
    files={}
    for sku,p in EXPECT.items():
        local=before["products"][sku]
        assert local["dir"]==p["name"] and local["zip"]==p["zip"]
        assert local["price"]==p["price"] and local["source_count"]==p["members"]
        assert local["cache_sha256"]==p["old_sha"]
        assert local["master_archives"].get(p["old_master"])==p["old_sha"]
        assert p["new_master"] not in local["master_archives"]
        originals=archive_members(BASE/p["old_zip"],p["old_sha"],p["members"])
        target=CAND/p["new_zip"]
        changed=archive_members(target,p["new_sha"],p["members"])
        diff=[n for n in originals if originals[n]!=changed[n]]
        assert sorted(originals)==sorted(changed)==sorted(local["sources"]),"EXACT_SOURCE_MEMBERS"
        assert originals==local["sources"],"LIVE_SOURCE_SHA_MISMATCH"
        assert len(diff)==p["changed"] and all(n.lower().endswith(".xlsx") for n in diff),"DIFF_SCOPE"
        seen=independent["products"][p["sku"]]
        stage_seen=staging["products"][p["sku"]]
        assert seen["sha256"]==p["new_sha"] and stage_seen["new_sha256"]==p["new_sha"],"STAGING_SHA_DRIFT"
        assert sorted(seen["changed_exact"])==sorted(stage_seen["changed"]),"V3_QUALITY_DIFF_DRIFT"
        assert set(seen["changed_exact"]).issubset(set(diff)),"V3_EDIT_OUTSIDE_LIVE_DIFF"
        assert seen["files"]==stage_seen["members"]==p["members"],"V3_MEMBERS_COUNT"
        products[sku]={
          "dir":p["name"],"zip":p["zip"],"price":p["price"],"count":p["members"],
          "before_sha":p["old_sha"],"after_sha":p["new_sha"],
          "old_master":p["old_master"],"new_master":p["new_master"],
          "before_members":originals,"after_members":changed
        }
        files[sku+".zip"]=target.read_bytes()
    manifest={"schema":"NSP_P4P7_PALETTE_RELEASE_V1","run_id":runid,"ttl":3600,
              "config_before":before["site_php_sha"],"payment_before":before["payment_php_sha"],
              "products":products,"owner_release_override_native_qa":False,
              "scope":"7 Excel style/header fixes, 36 unchanged vs live; native Excel 2024 7/7 PASS; prices/payment/orders unchanged"}
    assert sum(p["count"] for p in products.values())==43
    assert sum(x["changed"] for x in EXPECT.values())==7
    files["release.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    files["apply.php"]=(HERE/"apply.php").read_bytes()
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode="w:gz") as tf:
        for name,raw in files.items():
            t=tarfile.TarInfo(name)
            t.size=len(raw);t.mode=0o600
            tf.addfile(t,io.BytesIO(raw))
    tar=output.getvalue()
    assert len(tar)<4_000_000,"STAGE_PACKAGE_TOO_LARGE"
    user=os.environ["SSH_USER"];host=os.environ["HOST"];port=os.environ["PORT"]
    assert user and host and re.fullmatch(r"[0-9]{1,5}",port),"REMOTE_IDENTITY"
    key=pathlib.Path(os.environ["RUNNER_TEMP"])/"nsp-p4p7-ssh/key"
    known=key.parent/"known_hosts"
    assert key.is_file() and known.is_file(),"SSH_KEY_MISSING"
    ssh=["ssh","-p",port,"-i",str(key),"-o","IdentitiesOnly=yes",
        "-o","BatchMode=yes","-o","StrictHostKeyChecking=yes",
        "-o","UserKnownHostsFile="+str(known),"-o","ConnectTimeout=12",
        "-o","ServerAliveInterval=10","-o","ServerAliveCountMax=3",user+"@"+host]
    staging_name="style-"+runid
    stage='"$HOME/nsp-p4p7-releases/'+staging_name+'"'
    command='set -eu; umask 077; mkdir -p "$HOME/nsp-p4p7-releases"; test ! -e '+stage+'; mkdir -m 700 '+stage+'; tar -xzf - -C '+stage
    receipt={"schema":"NSP_P4P7_PRODUCTION_RUN_v1","run_id":runid,
             "status":"NOT_STARTED","started_utc":now(),"source_shas":{k:p["before_sha"] for k,p in products.items()},
             "target_shas":{k:p["after_sha"] for k,p in products.items()},
             "changes":7,"unchanged":36,"no_real_checkout":True,"owner_accepted_qa_override":False}
    applied=False
    try:
        invoke(ssh+[command],timeout=80,inp=tar)
        receipt["status"]="STAGED_PRIVATE"
        write("release-state.json",receipt)
        def phase(name,sku=None,timeout=70):
            cmd="php "+stage+"/apply.php "+name+' "$HOME/www/nastoronepodryadchika.ru" '+stage
            if sku:cmd+=" "+sku
            return invoke(ssh+[cmd],timeout=timeout)
        pre=json.loads(phase("preflight",timeout=75))
        assert pre["status"]=="PREFLIGHT_PASS" and pre["production_writes"] is False
        assert set(pre["scope"])=={"p4","p7"}
        write("preflight-release.json",pre)
        receipt["status"]="LIVE_PREFLIGHT_PASS"
        write("release-state.json",receipt)
        applied=True
        result=json.loads(phase("apply",timeout=110))
        assert result["status"]=="APPLIED_AND_VERIFIED"
        assert set(result["products"])=={"p4","p7"}
        write("live-apply.json",result)
        ver=json.loads(phase("verify",timeout=70))
        assert ver["status"]=="PRODUCTION_VERIFIED"
        write("live-verify.json",ver)
        for sku,p in EXPECT.items():
            actual=phase("read-current",sku,timeout=75)
            assert SHA(actual)==p["new_sha"],"DELIVERED_CACHE_SHA_MISMATCH:"+sku
            with zipfile.ZipFile(io.BytesIO(actual)) as z:
                assert z.testzip() is None and len(z.namelist())==p["members"],"DELIVERED_ZIP_CRC_OR_COUNT"
            receipt.setdefault("delivery",{})[sku]={"sha256":SHA(actual),"files":p["members"],"crc":"PASS"}
        receipt["status"]="PUBLISHED_AND_DELIVERY_VERIFIED"
        receipt["production_changes"]=True
        applied=False
        write("release-state.json",receipt)
        print("P4_P7_PUBLISHED_AND_DELIVERY_VERIFIED",json.dumps({"sha":receipt["target_shas"],"delivery":receipt["delivery"]}))
    except BaseException as e:
        receipt["status"]="FAILED_NEEDS_CLASSIFICATION"
        receipt["exception_class"]=type(e).__name__
        if applied:
            try:
                rollback=json.loads(phase("rollback",timeout=75))
                assert rollback["status"]=="ROLLBACK_VERIFIED"
                receipt["status"]="FAILED_ROLLBACK_VERIFIED"
            except BaseException as error:
                receipt["status"]="MANUAL_RECOVERY_REQUIRED"
                receipt["rollback_exception"]=type(error).__name__
        write("release-state.json",receipt)
        raise
if __name__=="__main__":
    main()
