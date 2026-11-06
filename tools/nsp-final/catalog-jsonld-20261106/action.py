#!/usr/bin/env python3
"""NSP one-file JSON-LD count preflight / owner-approved publication.

Uses the EXISTING tools/nsp-final/transaction.php (SHA pin, private backup,
rollback and buyer/price hash gates). Does not create another transaction engine.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path("/tmp/nsp-final-evidence")
EVIDENCE.mkdir(parents=True, exist_ok=True)
PR_HEAD = "bfea3b08b08a257b10277b3b295ec3d0af5d310e"
BEFORE = "5074803de3aa2b2e78cbc40db0b2503699b627703a60325ce701d65c71064788"
AFTER = "d538b110da721b4349daa3e98615eba4095c37e24582dbbb154a0f4a4c34261c"
TARGET = "katalog.html"
EXPECTED = {"p4":(25,30),"p8":(11,12),"p9":(10,12),
            "p10":(8,10),"p11":(8,10),"p13":(10,12)}
SHA = lambda b:sha256(b).hexdigest()

def call(args, *, data=None, timeout=60):
    p=subprocess.run(args,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if p.returncode:
        raise RuntimeError("COMMAND_FAILED_"+str(args[0])+"_"+str(p.returncode)+"_"+
                           p.stderr.decode("utf-8","replace")[-350:])
    return p.stdout

def evidence(filename, data):
    path=EVIDENCE/filename
    if path.exists():raise RuntimeError("EVIDENCE_FILE_ALREADY_EXISTS_"+filename)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    return path

def preflight_source():
    before=(ROOT/TARGET).read_bytes()
    if SHA(before)!=BEFORE:raise RuntimeError("BRANCH_BASE_CATALOG_PREIMAGE_DRIFT")
    # Git fetch from this worker can block on unrelated git transport/auth.
    # The exact immutable commit and complete SHA are both required.
    url="https://raw.githubusercontent.com/pmgpt12-arch/marzhavbetone.ru/"+PR_HEAD+"/"+TARGET
    req=Request(url,headers={"User-Agent":"NSP-JSONLD-SourceSHA-QA/1.0"})
    with urlopen(req,timeout=15) as response:
        if response.status!=200:raise RuntimeError("CANDIDATE_HTTP_NOT_200")
        after=response.read(300001)
    if len(after)>300000:raise RuntimeError("CANDIDATE_TOO_LARGE")
    if SHA(after)!=AFTER:raise RuntimeError("EXACT_PR_CANDIDATE_SHA_MISMATCH")
    oldlines=before.decode("utf-8").splitlines()
    newlines=after.decode("utf-8").splitlines()
    if len(oldlines)!=len(newlines):raise RuntimeError("UNEXPECTED_CATALOG_LINE_COUNT")
    deltas=[(i,a,b) for i,(a,b) in enumerate(zip(oldlines,newlines),1) if a!=b]
    if len(deltas)!=6 or any('"description"' not in a or '"description"' not in b for _,a,b in deltas):
        raise RuntimeError("UNEXPECTED_CATALOG_DELTA_SCOPE")
    # Verify expected old/new counts are unique and change only inside JSON-LD.
    source_jsonld=re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                            before.decode("utf-8"), re.I|re.S)
    target_jsonld=re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                            after.decode("utf-8"), re.I|re.S)
    if not source_jsonld or not target_jsonld:raise RuntimeError("CATALOG_JSONLD_MISSING")
    def products(obj):
        if isinstance(obj,list):
            for x in obj:yield from products(x)
        if isinstance(obj,dict):
            if obj.get("@type")=="Product":yield obj
            for v in obj.values():yield from products(v)
    def keyed(data):
        out={}
        for p in products(json.loads(data)):
            offered=p.get("offers")
            url=offered.get("url","") if isinstance(offered,dict) else p.get("url","")
            match=re.search(r'/products/(p\d+)-',str(url))
            if match:out[match[1]]=p
        return out
    old=keyed(source_jsonld[1]);new=keyed(target_jsonld[1])
    if set(old)!=set(new) or len(old)!=11:raise RuntimeError("CATALOG_11_SKU_DRIFT")
    edits=[]
    for sku in old:
        before_entry=old[sku];after_entry=new[sku]
        if sku in EXPECTED:
            old_n,new_n=EXPECTED[sku]
            expected_desc=before_entry["description"].replace(
                str(old_n)+" файлов",str(new_n)+" файлов")
            if expected_desc==before_entry["description"] or expected_desc!=after_entry["description"]:
                raise RuntimeError("PRODUCT_DESCRIPTION_DELTA_"+sku)
            edits.append(sku)
        elif before_entry!=after_entry:
            raise RuntimeError("NON_TARGET_PRODUCT_CHANGED_"+sku)
    if len(edits)!=6:raise RuntimeError("TARGET_PRODUCT_COUNT")
    return before,after,sorted(edits)

def main(action):
    if action not in ("catalog-jsonld-preflight","catalog-jsonld-publish"):
        raise RuntimeError("UNSUPPORTED_ACTION")
    if os.environ.get("GITHUB_REF_NAME")!="fix/nsp-cutover-final-20261021":
        raise RuntimeError("RELEASE_BRANCH_MISMATCH")
    run=os.environ["GITHUB_RUN_ID"];attempt=os.environ["GITHUB_RUN_ATTEMPT"]
    if not run.isdigit() or not attempt.isdigit():raise RuntimeError("RUN_ID_MISSING")
    before,after,edits=preflight_source()
    # Existing general static transaction only permits HTML/JS; no PHP.
    transaction=ROOT/"tools/nsp-final/transaction.php"
    call(["php","-l",str(transaction)],timeout=10)
    call(["python3",str(ROOT/"tools/nsp-final/test_transaction.py")],timeout=25)
    port=os.environ["PORT"];user=os.environ["SSH_USER"];host=os.environ["HOST"]
    if not host or not user or not port.isdecimal():raise RuntimeError("REMOTE_NOT_CONFIGURED")
    key=Path.home()/".ssh/nsp_final_key"
    known=Path.home()/".ssh/known_hosts"
    if not key.is_file() or not known.is_file():raise RuntimeError("SSH_IDENTITY_NOT_READY")
    ssh=["ssh","-p",port,"-i",str(key),"-o","IdentitiesOnly=yes","-o","BatchMode=yes",
         "-o","StrictHostKeyChecking=yes","-o","UserKnownHostsFile="+str(known),
         "-o","ConnectTimeout=12","-o","ServerAliveInterval=10","-o","ServerAliveCountMax=3",
         user+"@"+host]
    stage='$HOME/nsp-migration-private/jsonld-'+run+'-'+attempt
    site='$HOME/www/nastoronepodryadchika.ru'
    row={"path":TARGET,"before":BEFORE,"after":AFTER}
    bundle=io.BytesIO()
    with tarfile.open(fileobj=bundle,mode="w:gz") as tar:
        for name,content in (("manifest.json",json.dumps([row]).encode()),
                             ("transaction.php",transaction.read_bytes()),
                             ("candidate/katalog.html",after)):
            info=tarfile.TarInfo(name);info.mode=0o600;info.size=len(content)
            tar.addfile(info,io.BytesIO(content))
    if len(bundle.getvalue())>160000:raise RuntimeError("UNEXPECTED_STAGE_SIZE")
    remote=('"'+stage+'"')
    cmd='set -eu; umask 077; test -d "$HOME/nsp-migration-private"; test ! -e '+remote+'; mkdir -m 700 '+remote+'; tar -xzf - -C '+remote
    call(ssh+[cmd],data=bundle.getvalue(),timeout=50)
    def phase(which,timeout=65):
        raw=call(ssh+['php '+remote+'/transaction.php '+which+' "'+site+'" '+remote],timeout=timeout)
        try:return json.loads(raw)
        except json.JSONDecodeError:raise RuntimeError("INVALID_TRANSACTION_RECEIPT_"+which)
    dry=phase("dry-run")
    if not (dry["status"]=="PASS" and dry["mode"]=="dry-run"
            and dry["files"]==1 and dry["writes_to_public"]==0):
        raise RuntimeError("LIVE_PREFLIGHT_FAILED")
    evidence("catalog-jsonld-dry-run.json",{"status":"PASS","source_head":PR_HEAD,
        "before_sha256":BEFORE,"after_sha256":AFTER,"target_skus":edits,"mode":action,
        "protected_price_gate":"PASS","production_writes":0,"transaction":dry})
    if action=="catalog-jsonld-preflight":
        print("NSP_CATALOG_JSONLD_PREFLIGHT_PASS; EXACT_6_DESCRIPTIONS; NO_PUBLIC_WRITE")
        return
    applied=False
    try:
        applied=True
        receipt=phase("apply",timeout=90)
        if receipt["status"]!="PASS" or receipt["files"]!=1:raise RuntimeError("APPLY_RECEIPT_FAILED")
        evidence("catalog-jsonld-apply.json",receipt)
        verified=phase("verify")
        if verified["status"]!="PASS" or verified["mode"]!="verify":
            raise RuntimeError("POSTFLIGHT_TRANSACTION_FAILED")
        req=Request("https://nastoronepodryadchika.ru/katalog.html?nsp_jsonld="+run,
                    headers={"Accept-Encoding":"identity","Cache-Control":"no-cache",
                             "User-Agent":"NSP-JSONLD-CountQA/1.0"})
        with urlopen(req,timeout=15) as response:
            if response.status!=200:raise RuntimeError("PUBLIC_HTTP_NOT_200")
            bytes_out=response.read(150001)
        if SHA(bytes_out)!=AFTER:raise RuntimeError("PUBLIC_HTTP_SHA_MISMATCH")
        verified_again=phase("verify")
        if verified_again["status"]!="PASS":raise RuntimeError("POSTFLIGHT_SECOND_VERIFY")
        evidence("catalog-jsonld-acceptance.json",{"status":"PUBLISHED_AND_HTTPS_VERIFIED",
            "candidate_head":PR_HEAD,"http_sha256":AFTER,"sku":edits,
            "protected_backend":"UNCHANGED","file_count":1})
        print("NSP_CATALOG_JSONLD_ONE_FILE_RELEASE_PASS")
    except BaseException:
        if applied:
            try:
                rollback=phase("rollback",timeout=80)
                evidence("catalog-jsonld-rollback.json",rollback)
                if rollback["status"]!="PASS":raise RuntimeError("ROLLBACK_RECEIPT_FAILED")
                print("NSP_CATALOG_JSONLD_ROLLED_BACK")
            except BaseException as exc:
                print("MANUAL_RECOVERY_REQUIRED_"+type(exc).__name__,file=sys.stderr)
        raise

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit(4)
    main(sys.argv[1])
