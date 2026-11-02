#!/usr/bin/env python3
"""Bounded, exact-SHA, versioned P4v3/P5v2 release using existing NSP GitHub Actions SSH.
Does not contact YuKassa. Uses production before-SHAs and automatic rollback on failed post-apply checks.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
import base64
import json
import os
import re
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request

BUNDLE=Path("tools/nsp-final/p4p5-20261102/p4p5-release-20261102.tar.gz")
EXPECTED_BUNDLE_SHA256="8dd926ed331daa33e852d0934a117bccd507c73ce8f91a57b34c9dd7a8d11e55"
EXPECTED_PUBLISH_PHP_SHA256="91f9714c60fb1e1eb98957ce722621da88708437cd9d7ede1ee880882e85273b"
EXPECTED_P4_SHA256="bcba234220c0f52e5a86b5ba3c70c527d086146301030d1f32197e9fa6e264fc"
EXPECTED_P5_SHA256="25ce378ee8fd84079b0edd2d57d816a2aaa77585a2a7e7172666e1f846f7dc05"
EVIDENCE=Path("/tmp/nsp-final-evidence")
EVIDENCE.mkdir(parents=True,exist_ok=True)
ACTION=os.environ.get("NSP_ACTION","")
RUN_ID=os.environ.get("GITHUB_RUN_ID","")
assert ACTION in ("p4p5-preflight","p4p5-publish"),"UNAUTHORIZED_ACTION"
assert re.fullmatch(r"[0-9]{5,20}",RUN_ID),"UNEXPECTED_RUN_ID"
MODE="preflight" if ACTION=="p4p5-preflight" else "publish"
TAG="nsp-p4p5-20261102-"+RUN_ID
HOST=os.environ.get("HOST","")
SSH_USER=os.environ.get("SSH_USER","")
PORT=os.environ.get("PORT","")
assert re.fullmatch(r"[a-zA-Z0-9.-]{3,200}",HOST),"INVALID_DEPLOY_HOST"
assert re.fullmatch(r"[a-zA-Z0-9_-]{2,90}",SSH_USER),"INVALID_DEPLOY_USER"
assert PORT.isdigit() and 1<=int(PORT)<=65535,"INVALID_DEPLOY_PORT"
KEY=Path.home()/".ssh/nsp_final_key"
assert KEY.is_file(),"EXISTING_DEPLOY_KEY_NOT_PREPARED"
SSH=["ssh","-p",PORT,"-i",str(KEY),"-o","BatchMode=yes","-o","IdentitiesOnly=yes",
     "-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=12","-o","ServerAliveInterval=8",
     "-o","ServerAliveCountMax=3",SSH_USER+"@"+HOST]
RECEIPT=EVIDENCE/"p4p5-production-result.json"
assert not RECEIPT.exists(),"EXISTING_RELEASE_RECEIPT"
state={
  "schema":"NSP_P4V3_P5V2_LIVE_EXECUTION_RECEIPT_V1",
  "mode":MODE,"run_id":RUN_ID,"status":"STARTED","stage":"INPUT_GATE",
  "candidate_shas":{"p4":EXPECTED_P4_SHA256,"p5":EXPECTED_P5_SHA256},
  "source_bundle_sha256":EXPECTED_BUNDLE_SHA256,
  "production_applied":False,"rollback_attempted":False,"rollback_verified":False,
  "private_zip_deliveries_verified":False,"public_http_status":"NOT_STARTED",
  "events":[],"error":None
}
def save():
    RECEIPT.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n")
def h(b:bytes)->str:
    return sha256(b).hexdigest()
def runssh(command:str, payload:bytes|None=None, timeout:int=70)->bytes:
    p=subprocess.run(SSH+[command],input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if p.returncode:
        # Limit stderr to error classification, never print credentials or user content.
        raise RuntimeError("SSH_COMMAND_FAILED rc="+str(p.returncode)+" detail="+p.stderr.decode("utf-8","replace")[-600:])
    return p.stdout
def remote_php(mode:str, sku:str|None=None, timeout:int=65)->bytes:
    cmd=("set -eu; php \"$HOME/"+TAG+"/publish.php\" "+mode+
         " \"$HOME/www/nastoronepodryadchika.ru\" \"$HOME/"+TAG+"\"")
    if sku is not None:
        assert sku in ("p4","p5")
        cmd+=" "+sku
    return runssh(cmd,timeout=timeout)
def parse_receipt(raw:bytes,expected:str)->dict:
    data=json.loads(raw.decode("utf-8"))
    assert data.get("status")==expected,("UNEXPECTED_STATUS",data.get("status"),expected)
    return data
def inspect_zip(blob:bytes,sha:str,sku:str,expected_members:dict)->None:
    assert h(blob)==sha,("BUYER_ZIP_SHA_MISMATCH",sku)
    with ZipFile(BytesIO(blob)) as z:
        assert z.testzip() is None and len(z.namelist())==30,("INVALID_ZIP",sku)
        assert len(set(z.namelist()))==30
        members={name:h(z.read(name)) for name in z.namelist()}
        assert members==expected_members,("BUYER_ZIP_MEMBERS_MISMATCH",sku)
def optional_http():
    # Public CDN connectivity may be restricted by geography; origin path/SHA is authoritative.
    import urllib.parse
    statuses={}
    for path in ("katalog.html","products/p4-ispolnitelnaya-dokumentaciya-pto.html","products/p5-shtrafy-uderzhaniya.html"):
        url="https://nastoronepodryadchika.ru/"+path+"?nsp_release="+RUN_ID
        try:
            req=urllib.request.Request(url,headers={"Cache-Control":"no-cache","User-Agent":"NSP-release-verifier/1.0"})
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req,timeout=10) as reply:
                data=reply.read(350000)
                statuses[path]={"http":reply.status,"bytes":len(data)}
        except Exception as exc:
            statuses[path]={"http":"UNAVAILABLE","error_type":type(exc).__name__}
    state["public_http_status"]=statuses
def prepare_bundle()->tuple[bytes,dict]:
    blob=BUNDLE.read_bytes()
    assert h(blob)==EXPECTED_BUNDLE_SHA256,"P4P5_BUNDLE_SHA_DRIFT"
    with tarfile.open(fileobj=BytesIO(blob),mode="r:gz") as z:
        items=z.getmembers()
        assert len(items)==22
        names=[x.name for x in items]
        assert len(set(names))==22 and all(x.isfile() and x.name==x.name.lstrip("/") and ".." not in Path(x.name).parts for x in items)
        rows={x.name:z.extractfile(x).read() for x in items}
    manifest=json.loads(rows["release.json"])
    assert manifest["schema"]=="NSP_P4P5_SCOPED_RELEASE_V1"
    assert len(manifest["static"])==18
    assert h(rows["publish.php"])==EXPECTED_PUBLISH_PHP_SHA256
    for sku,want in (("p4",EXPECTED_P4_SHA256),("p5",EXPECTED_P5_SHA256)):
        assert manifest["products"][sku]["new_zip_sha256"]==want
        inspect_zip(rows["archives/"+sku+".zip"],want,sku,manifest["products"][sku]["new_members"])
    for page in manifest["static"]:
        assert h(rows["pages/"+page["path"]])==page["after"],page["path"]
    assert set(rows)=={"release.json","publish.php","archives/p4.zip","archives/p5.zip"}|{"pages/"+p["path"] for p in manifest["static"]}
    return blob,manifest
save()
applied_attempt=False
try:
    bundle,manifest=prepare_bundle()
    state["stage"]="STAGE_PRIVATE"
    save()
    # Exact single fresh private stage per run, never replace an existing remote directory.
    runssh("set -eu; umask 077; test ! -e \"$HOME/"+TAG+"\"; mkdir -m 700 \"$HOME/"+TAG+"\"",timeout=25)
    runssh("set -eu; tar -xzf - -C \"$HOME/"+TAG+"\"",payload=bundle,timeout=70)
    state["events"].append("PRIVATE_STAGE_UPLOADED")
    state["stage"]="PRODUCTION_PREFLIGHT"
    preflight=parse_receipt(remote_php("preflight"),"PREFLIGHT_PASS")
    assert preflight.get("production_writes") is False
    assert preflight.get("new_zip_members")==60
    state["events"].append("FRESH_LIVE_BEFORE_SHA_AND_60_MEMBER_PREFLIGHT_PASS")
    save()
    if MODE=="preflight":
        state["status"]="PREFLIGHT_PASS_NO_PRODUCTION_CHANGE"
    else:
        state["stage"]="APPLY"
        applied_attempt=True
        save()
        applied=parse_receipt(remote_php("apply",timeout=105),"APPLIED_PENDING_INDEPENDENT_VERIFY")
        state["production_applied"]=True
        state["events"].append("PRODUCTION_APPLY_RETURNED_PASS")
        state["stage"]="VERIFY"
        save()
        result=parse_receipt(remote_php("verify",timeout=100),"PRODUCTION_SOURCES_BUILDER_AND_PAGES_VERIFIED")
        assert result["p4"]==EXPECTED_P4_SHA256 and result["p5"]==EXPECTED_P5_SHA256
        assert result.get("ttl")==3600
        state["events"].append("LIVE_ORIGIN_PAGES_AND_BUILDERS_VERIFIED")
        state["stage"]="READBACK_ZIPS"
        save()
        for sku,want in (("p4",EXPECTED_P4_SHA256),("p5",EXPECTED_P5_SHA256)):
            blob=remote_php("read-current",sku=sku,timeout=90)
            inspect_zip(blob,want,sku,manifest["products"][sku]["new_members"])
            state["events"].append("DELIVERY_"+sku.upper()+"_30_MEMBERS_EXACT_SHA_PASS")
            save()
        state["private_zip_deliveries_verified"]=True
        state["stage"]="EXTERNAL_HTTP_DIAGNOSTIC"
        optional_http()
        state["status"]="PUBLISHED_AND_ORIGIN_ZIP_VERIFIED"
        state["stage"]="COMPLETE"
    save()
    print("NSP_P4P5_RELEASE_RESULT",json.dumps({"status":state["status"],"mode":MODE,"sha_p4":EXPECTED_P4_SHA256,
      "sha_p5":EXPECTED_P5_SHA256,"private_zip_verification":state["private_zip_deliveries_verified"],
      "public_http":state["public_http_status"]},ensure_ascii=False),flush=True)
except Exception as exc:
    state["error"]=type(exc).__name__+": "+str(exc)[:900]
    state["status"]="FAILED_"+state["stage"]
    if MODE=="publish" and applied_attempt:
        state["rollback_attempted"]=True
        try:
            check=parse_receipt(remote_php("rollback",timeout=100),"ROLLBACK_VERIFIED")
            state["rollback_verified"]=True
            state["status"]="FAILED_ROLLBACK_VERIFIED"
        except Exception as roll:
            state["rollback_error"]=type(roll).__name__+": "+str(roll)[:500]
            state["status"]="FAILED_ROLLBACK_UNVERIFIED_URGENT"
    save()
    print("NSP_P4P5_RELEASE_FAILED",json.dumps({"status":state["status"],"stage":state["stage"],"error":state["error"],
       "rollback_verified":state["rollback_verified"]},ensure_ascii=False),flush=True)
    sys.exit(2)
