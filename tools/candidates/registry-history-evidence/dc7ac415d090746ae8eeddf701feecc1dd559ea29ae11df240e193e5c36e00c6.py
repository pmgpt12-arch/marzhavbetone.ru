#!/usr/bin/env python3
"""Recover EXISTING Word job by normalizing manifest encoding and re-advertising same ID.
No new job ID or re-run; prerequisite: target has never fetched a source or produced a report.
"""
from pathlib import Path
from xml.etree import ElementTree as ET
from datetime import datetime, timezone
import hashlib, json, os, sys, time

ROOT=Path("/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011")
D=Path("/home/denis/.local/state/claude-dispatcher/recovery-20261006/postreconnect-product-gates/p2-instruction-business-style-20261013")
WORD=ROOT/"word"
JOB="p2-instruction-style-word-20261013-v1"
OLDJOB="p2-a4-native-word-20261013-v1"
SHA="0f3882fae04bd8bf32a9c368abc24e6d4c1c41fad5d008d37bfc522098148b11"
CURRENT=WORD/"current.xml"
JOBFILE=WORD/JOB/"job.xml"
SOURCE=WORD/JOB/"p2-instruction.docx"
REPORT=ROOT/"results/word"/JOB/"report.xml"
OLDREPORT=ROOT/"results/word"/OLDJOB/"report.xml"
OUT=D/"word-existing-job-recovery-result.json"
ORIGINAL=D/"word-existing-job-recovery-prior-current.xml"
LOG=ROOT/"transport-7h-20261013.log"

def h(data): return hashlib.sha256(data).hexdigest()
def emit(status, **more):
    obj={"job_id":JOB,"status":status,"candidate_sha256":SHA,
         "time_utc":datetime.now(timezone.utc).isoformat(),
         "changed_buyer_documents":False,"new_job_created":False,
         "G1_G8":"HOLD","release":"BLOCKED",**more}
    tmp=D/"word-existing-job-recovery.tmp"
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,OUT)
    print(json.dumps(obj,ensure_ascii=False),flush=True)
def main():
    assert not OUT.exists() and not ORIGINAL.exists(),"RECOVERY_ALREADY_ATTEMPTED_STOP"
    assert SOURCE.exists() and h(SOURCE.read_bytes())==SHA,"SOURCE_DRIFT_STOP"
    assert not REPORT.exists() and OLDREPORT.exists(),"COMPLETED_OR_OLD_JOB_NOT_FINAL"
    old=CURRENT.read_bytes(); manifest=JOBFILE.read_bytes()
    assert ET.fromstring(old).get("id")==OLDJOB,"OTHER_ACTIVE_JOB_STOP"
    assert ET.fromstring(manifest).get("id")==JOB,"JOB_ID_DRIFT_STOP"
    inp=ET.fromstring(manifest).find("file")
    assert inp is not None and inp.get("sha256")==SHA and inp.get("name")=="p2-instruction.docx" and inp.get("tag")=="p2style","MANIFEST_DRIFT"
    assert manifest.count(b"encoding='utf8'")==1,"ENCODING_NOT_AS_EXPECTED"
    repaired=manifest.replace(b"encoding='utf8'",b"encoding='UTF-8'",1)
    assert ET.fromstring(repaired).find("file").get("sha256")==SHA
    assert time.time()-LOG.stat().st_mtime<90,"WORD_LAPTOP_POLL_NOT_FRESH"
    recent=LOG.read_text(errors="replace")[-20000:]
    assert 'GET /word/current.xml HTTP/1.0" 204' in recent,"WORD_AGENT_NOT_IDLE"
    assert "GET /word/input/"+JOB+"/" not in LOG.read_text(errors="replace"),"ALREADY_ATTEMPTED_INPUT_STOP"
    ORIGINAL.write_bytes(old)
    newjob=JOBFILE.with_suffix(".xml.word-recovery-temp")
    stage=CURRENT.with_suffix(".xml.word-recovery-temp")
    assert not newjob.exists() and not stage.exists(),"TEMP_EXISTS_STOP"
    newjob.write_bytes(repaired)
    assert CURRENT.read_bytes()==old and JOBFILE.read_bytes()==manifest,"CONCURRENT_WRITE_STOP"
    os.replace(newjob,JOBFILE)
    stage.write_bytes(repaired)
    assert CURRENT.read_bytes()==old,"CONCURRENT_CURRENT_STOP"
    os.replace(stage,CURRENT)
    assert CURRENT.read_bytes()==JOBFILE.read_bytes()==repaired,"PUBLICATION_MISMATCH"
    emit("SAME_JOB_REPUBLISHED_VALID_UTF8",old_job=OLDJOB,
         original_manifest_sha256=h(manifest),new_manifest_sha256=h(repaired))
    return 0
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("WORD_RECOVERY_STOP:"+repr(e),file=sys.stderr)
        sys.exit(1)
