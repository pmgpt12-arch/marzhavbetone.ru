#!/usr/bin/env python3
"""Read-only resume gate: artifact identity, buyer contract, current P2 evidence."""
from pathlib import Path
from io import BytesIO
from collections import Counter
import datetime, hashlib, json, re, subprocess, time, urllib.request, zipfile
import xml.etree.ElementTree as ET
B=Path("/home/denis/projects/nsp-qa13-20261024")
D=B/"resume-20261030"
D.mkdir(exist_ok=True)
OUT=D/"RESUME_VERIFICATION.json"
assert not OUT.exists(), "Inspect prior result before another run"
deadline=time.monotonic()+65
H=lambda b:hashlib.sha256(b).hexdigest()
R={"schema":"NSP_QA_SESSION3_RESUME_v1","observed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"checks":{},"native_jobs_started":0,"production_writes":False,"buyer_artifacts_modified":False}
def check(name,condition):
    R["checks"][name]=bool(condition)
    if not condition: raise AssertionError(name)
def get(url):
    remaining=deadline-time.monotonic()
    assert remaining>1,"Budget exhausted"
    req=urllib.request.Request(url,headers={"User-Agent":"NSP-QA-artifact-check"})
    with urllib.request.urlopen(req,timeout=min(12,remaining)) as response:
        assert response.status==200
        return response.read(2000001)
try:
    P=B/"owner-layout-review-20261029"
    m=json.loads((P/"QA13_P1_V1_REVIEW_MANIFEST_20261029.json").read_text())
    a=P/"QA13_P1_V1_18_FILES_NONRELEASE_20261029.zip"
    raw=a.read_bytes()
    check("p1_local_archive_sha",H(raw)=="99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada")
    check("p1_manifest_sha",H((P/"QA13_P1_V1_REVIEW_MANIFEST_20261029.json").read_bytes())=="77a4d9a0bbed8faa2c0b02ef52ac38bbe08566ee8d83be0ee390dc0bad6177f2")
    z=zipfile.ZipFile(BytesIO(raw))
    names=z.namelist()
    check("p1_exact_18_unique_members",len(names)==len(set(names))==18 and set(names)=={x["name"] for x in m["files"]})
    check("p1_zip_crc",z.testzip() is None)
    check("p1_all_member_sha_and_sizes",all(H(z.read(f["name"]))==f["sha256"] and len(z.read(f["name"]))==f["bytes"] for f in m["files"]))
    check("p1_single_pdf_instruction",[n for n in names if n.startswith("00-")]==["00-INSTRUKCIYA.pdf"])
    check("p1_expected_formats",dict(Counter(Path(n).suffix for n in names))=={".docx":8,".xlsx":4,".xls":3,".pdf":3})
    W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    tables=0
    for name in names:
        if not name.endswith(".docx"): continue
        doc=ET.fromstring(zipfile.ZipFile(BytesIO(z.read(name))).read("word/document.xml"))
        for t in doc.iter(W+"tbl"):
            prop=t.find(W+"tblPr"); pref=prop.find(W+"tblW"); layout=prop.find(W+"tblLayout")
            grid=t.find(W+"tblGrid")
            check("p1_table_%02d_fixed_width"%tables,pref is not None and pref.get(W+"w")=="9866" and pref.get(W+"type")=="dxa" and layout is not None and layout.get(W+"type")=="fixed" and sum(int(c.get(W+"w")) for c in grid)==9866)
            tables+=1
    check("p1_twelve_word_tables",tables==12)
    old=zipfile.ZipFile(B/"delivery/P1-QA13-20-FILES-CALC-V4-NONRELEASE.zip")
    excel=[n for n in names if Path(n).suffix in (".xls",".xlsx")]
    check("p1_seven_excel_unchanged",len(excel)==7 and all(z.read(n)==old.read(n) for n in excel))
    ready=json.loads((P/"OWNER_REVIEW_READY_20261029.json").read_text())
    check("p1_owner_pending_no_release",ready["owner_approval"]=="PENDING" and ready["release_allowed"] is False)
    pdf=P/"QA13_P1_V1_WORD_PREVIEW_20P_20261029.pdf"
    pdfraw=pdf.read_bytes()
    check("p1_pdf_sha",H(pdfraw)=="73977aa4feb4d1543ec182e26f863f0afd501082588fba4867b3956ce3f203bf")
    info=subprocess.run(["pdfinfo",str(pdf)],capture_output=True,text=True,check=True,timeout=5).stdout
    check("p1_preview_twenty_pages",re.search(r"^Pages:\s+20\s*$",info,re.M) is not None)
    C="574eb0d7fa10106339d9c9d71f9f1dc3f378a386"
    root="https://raw.githubusercontent.com/pmgpt12-arch/marzhavbetone.ru/"+C+"/tools/nsp-qa13-20261024/owner-review-v1-20261029/"
    for file in (a,pdf):
        downloaded=get(root+file.name)
        check("p1_remote_exact_"+file.suffix[1:],downloaded==file.read_bytes())
    R["p1"]={"edition":"P1-layout-v1","status":"READY_FOR_OWNER_REVIEW","archive_sha256":H(raw),"file_count":18,"word_tables":tables,"excel_unchanged":7,"preview_pages":20,"download_commit":C,"archive_url":root+a.name,"preview_url":root+pdf.name,"owner_acceptance":"PENDING","release_allowed":False}
    live_url="https://raw.githubusercontent.com/pmgpt12-arch/marzhavbetone.ru/60d317e989c57f035fbe4f9bdcea482b78f1cc64/tools/nsp-publication-20261026/p2-v13-20261029/P2_V13_LIVE_RECEIPT_20261029.json"
    live=json.loads(get(live_url))
    check("p2_live_exact_accepted_edition",live["deployment_status"]=="VERIFIED_LIVE" and live["archive_sha256"]=="42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da" and live["archive_members"]==13 and live["evidence"]["ttl_seconds"]==3600)
    R["p2"]={"edition":"P2-v13","status":"VERIFIED_LIVE_PER_PINNED_RECEIPT","archive_sha256":live["archive_sha256"],"file_count":13,"ttl_seconds":3600,"receipt_url":live_url,"workflow":live["release_github_action"],"full_payment_email_download_e2e":"NOT_RUN","fresh_live_delivery_test":False}
    R["status"]="ARTIFACT_IDENTITY_AND_OWNER_REVIEW_HANDOFF_PASS"
except BaseException as e:
    R["status"]="STOP_REVIEW_REQUIRED"
    R["error"]=type(e).__name__+": "+str(e)
    raise
finally:
    R["elapsed_seconds"]=round(time.monotonic()-(deadline-65),2)
    OUT.write_text(json.dumps(R,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(R,ensure_ascii=False,indent=2))
