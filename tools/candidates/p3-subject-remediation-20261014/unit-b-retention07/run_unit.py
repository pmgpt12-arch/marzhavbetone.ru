#!/usr/bin/env python3
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "run.log"
EXIT = ROOT / "exit.code"
RECEIPT = ROOT / "wrapper-result.json"
RENDER = ROOT / "render"
DOCX = ROOT / "candidate/07-sroki-hraneniya.docx"
PDF = RENDER / "07-sroki-hraneniya.pdf"

def atomic_bytes(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    os.fsync(fd)
    os.close(fd)

def atomic_json(path, payload):
    atomic_bytes(path, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode())

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(cmd, timeout):
    with open(LOG, "ab") as log:
        log.write(("$ " + " ".join(cmd) + "\n").encode())
        log.flush()
        os.fsync(log.fileno())
        return subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=True)

started = datetime.now(timezone.utc).isoformat()
payload = {
    "unit_id": "P3-RETENTION07-REMEDIATION-20261014",
    "started_at": started,
    "status": "RUNNING",
    "pid": os.getpid(),
    "stages": []
}
atomic_json(RECEIPT, payload)
try:
    run(["python3", "build_retention07.py"], 120)
    payload["stages"].append("author_build")
    atomic_json(RECEIPT, payload)

    RENDER.mkdir(exist_ok=True)
    profile = ROOT / (".lo-profile-" + str(os.getpid()))
    profile.mkdir(exist_ok=True)
    run(["soffice", "--headless", "-env:UserInstallation=file://" + str(profile),
         "--convert-to", "pdf", "--outdir", str(RENDER), str(DOCX)], 180)
    payload["stages"].append("libreoffice_pdf")
    atomic_json(RECEIPT, payload)

    run(["pdftoppm", "-png", "-r", "150", str(PDF), str(RENDER / "page")], 120)
    payload["stages"].append("poppler_png")
    pages = sorted(RENDER.glob("page-*.png"))
    if not pages:
        raise RuntimeError("no rendered PNG pages")

    info = subprocess.check_output(["pdfinfo", str(PDF)], text=True, timeout=30)
    page_line = next((line for line in info.splitlines() if line.startswith("Pages:")), "")
    pdf_pages = int(page_line.split(":", 1)[1].strip())
    if pdf_pages != len(pages):
        raise RuntimeError(f"page mismatch pdf={pdf_pages} png={len(pages)}")

    payload.update({
        "status": "AUTHOR_RENDER_PASS_VISUAL_REVIEW_PENDING",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "docx_sha256": sha256(DOCX),
        "pdf_sha256": sha256(PDF),
        "page_count": len(pages),
        "page_sha256": {p.name: sha256(p) for p in pages},
        "visual_review": "PENDING",
        "native_microsoft_word": "NOT_RUN",
        "independent_review": "PENDING",
        "release": "HOLD"
    })
    atomic_json(RECEIPT, payload)
    atomic_bytes(EXIT, b"0\n")
except Exception as exc:
    payload.update({
        "status": "FAIL",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "error_class": "RUNTIME_OR_CONTENT_GATE",
        "error": repr(exc),
        "next_step": "Inspect run.log and author-result.json; change hypothesis/fingerprint before retry."
    })
    atomic_json(RECEIPT, payload)
    atomic_bytes(EXIT, b"1\n")
    raise
