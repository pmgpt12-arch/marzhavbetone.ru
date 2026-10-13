#!/usr/bin/env python3
"""One native Excel 2016 test of the NEW metadata-only candidate; no retries."""
from pathlib import Path
from xml.etree import ElementTree as ET
from datetime import datetime, timezone
import hashlib, json, os, shutil, sys, time, zipfile

ROOT = Path("/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011")
D = Path("/home/denis/.local/state/claude-dispatcher/recovery-20261006/postreconnect-product-gates/p1-395-corexml-compat-20261013")
SRC = D / "14-raschet-procentov-395-gk-corexml-compat.xlsx"
SHA = "044d9aa899b2278c9fe6c525f4b54e3f8ea07d4b12d755a8df145741756ee8c2"
JOB = "p1-395-corexml-native-20261013-v1"
NAME = "p1-395-corexml.xlsx"
TAG = "p1395core"
CURRENT = ROOT / "native/current.xml"
REPORT = ROOT / "results/native" / JOB / "report.xml"
STATUS = D / "native-report.json"

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def record(status, **extras):
    doc = {"job_id": JOB, "status": status, "source_sha256": SHA,
           "utc": datetime.now(timezone.utc).isoformat(),
           "scope": "EXACT_NATIVE_EXCEL_2016_OPEN_AND_EXPORT_ONLY",
           "buyer_legal_g1_g8": "NOT_ACCEPTED", "release": "BLOCKED", **extras}
    temp = D / "native-report.tmp"
    temp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, STATUS)
    print(json.dumps(doc, ensure_ascii=False), flush=True)
def main():
    assert SRC.is_file() and digest(SRC) == SHA, "CANDIDATE_SHA_DRIFT"
    with zipfile.ZipFile(SRC) as z:
        assert z.testzip() is None and b"+00:00Z" not in z.read("docProps/core.xml"), "METADATA_REPAIR_NOT_PRESENT"
    assert not STATUS.exists() and not REPORT.exists() and not (ROOT/"native"/JOB).exists(), "DUPLICATE_JOB_STOP"
    log = ROOT / "transport-7h-20261013.log"
    assert time.time() - log.stat().st_mtime < 90, "NO_FRESH_POLL_STOP"
    recent = log.read_text(errors="replace")[-12000:]
    assert 'GET /native/current.xml HTTP/1.0" 204' in recent, "EXCEL_NOT_IDLE_STOP"
    old = CURRENT.read_bytes()
    old_id = ET.fromstring(old).get("id")
    assert old_id == "p1-395-fixture-20261011-v1", "OTHER_ACTIVE_JOB_STOP"
    assert (ROOT/"results/native"/old_id/"report.xml").exists(), "PREVIOUS_JOB_UNFINISHED"
    folder = ROOT / "native" / JOB
    folder.mkdir()
    shutil.copyfile(SRC, folder / NAME)
    assert digest(folder / NAME) == SHA
    job = ET.Element("job", {"id": JOB})
    ET.SubElement(job, "file", {"name": NAME, "tag": TAG, "sha256": SHA,
                                "sheet": "Расчёт", "protect_contents": "false"})
    payload = ET.tostring(job, encoding="UTF-8", xml_declaration=True)
    assert ET.fromstring(payload).get("id") == JOB
    (folder / "job.xml").write_bytes(payload)
    stage = CURRENT.with_name("current.xml.p1395core-temp")
    assert not stage.exists(), "OLD_STAGE_STOP"
    stage.write_bytes(payload)
    assert CURRENT.read_bytes() == old, "CONCURRENT_QUEUE_MUTATION_STOP"
    os.replace(stage, CURRENT)
    try:
        record("QUEUED_NEW_SHA", prior_job=old_id)
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline and not REPORT.exists():
            time.sleep(3)
        if not REPORT.exists():
            record("NO_REPORT_BY_150S", prior_job=old_id)
            return 2
        r = ET.parse(REPORT).getroot()
        info = {"report_status":r.get("status"), "excel_version":r.get("excel_version"),
                "excel_build":r.get("excel_build"), "report_sha256":digest(REPORT),
                "checks":[{"name":c.get("name"),"pass":c.get("pass"),"actual":c.get("actual")}
                          for c in r.findall("check")],
                "errors":[e.text[:1600] for e in r.findall("error") if e.text]}
        if info["report_status"] != "PASS" or any(c["pass"] != "True" for c in info["checks"]):
            record("NATIVE_FAIL", **info)
            return 1
        record("NATIVE_AGENT_PASS_ONLY", **info)
        return 0
    finally:
        try:
            if ET.fromstring(CURRENT.read_bytes()).get("id") == JOB:
                back = CURRENT.with_name("current.xml.p1395core-restore")
                back.write_bytes(old)
                os.replace(back, CURRENT)
        except Exception as exc:
            print("RESTORE_ERROR:" + repr(exc), file=sys.stderr)
if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        record("ERROR_OR_BLOCKED", error=repr(exc))
        sys.exit(1)
