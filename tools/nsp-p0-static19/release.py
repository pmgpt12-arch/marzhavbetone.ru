#!/usr/bin/env python3
"""Strictly scoped NSP static-19 release using the existing atomic transaction.php.

Runner-only transport. Never deploys PHP, ZIPs, orders, or unrelated website files.
"""
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "tools/nsp-p0-static19"
EVIDENCE = Path("/tmp/nsp-p0-static19-evidence")
EXPECTED_SHA = "d1b9c5711b26845e124813e812b5ded16640852b0f8b2b8446530d0192a4f12e"
SCOPED_RE = re.compile(r"^(?:articles|materialy)/[a-z0-9-]+\.html$")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(args, *, timeout=120):
    p = subprocess.run(args, capture_output=True, timeout=timeout, check=False)
    if p.returncode:
        raise RuntimeError("EXIT_%d: %s" % (
            p.returncode, p.stderr.decode(errors="replace")[-900:]))
    return p.stdout


def report(name, obj):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def manifest_gate():
    data = (PKG / "manifest.json").read_bytes()
    if sha(data) != EXPECTED_SHA:
        raise ValueError("OWNER_APPROVED_MANIFEST_HASH_CHANGED")
    rows = json.loads(data)
    if len(rows) != 19 or len({x["path"] for x in rows}) != 19:
        raise ValueError("OWNER_APPROVED_19_PATHS_CHANGED")
    if sum(x["path"].startswith("articles/") for x in rows) != 13:
        raise ValueError("ARTICLE_SCOPE_NOT_13")
    if sum(x["path"].startswith("materialy/") for x in rows) != 6:
        raise ValueError("FREE_SCOPE_NOT_6")
    for x in rows:
        path = x["path"]
        if not SCOPED_RE.fullmatch(path):
            raise ValueError("OUT_OF_SCOPE_PATH")
        if any(re.fullmatch("[a-f0-9]{64}", x[k]) is None
               for k in ("before", "after")):
            raise ValueError("HASH_SCHEMA")
        if sha((PKG / "candidate" / path).read_bytes()) != x["after"]:
            raise ValueError("CANDIDATE_SHA_DRIFT_" + path)
        if x["before"] == x["after"]:
            raise ValueError("NO_OP_" + path)
    return rows


def main():
    request = json.loads((PKG / "request.json").read_text())
    mode = request.get("action")
    if mode not in ("dry-run", "publish"):
        raise ValueError("REQUEST_ACTION_NOT_APPROVED")
    if request.get("owner_approval_issue") != 707:
        raise ValueError("OWNER_GATE_MISSING")
    if request.get("approved_matrix_sha256") != (
        "578157c15043ace0cb05a5518dc30945939b233dea228f223f7b649678adf004"
    ):
        raise ValueError("MATRIX_GATE_CHANGED")
    rows = manifest_gate()
    report("source.json", {
        "status": "PREPARED", "action": mode, "files": len(rows),
        "manifest_sha256": EXPECTED_SHA,
        "owner_gate": "AI Business OS #707 static19 only",
    })
    print("STATIC19_LOCAL_MANIFEST_PASS files=19 sha=" + EXPECTED_SHA)
    run(["php", "-l", str(ROOT / "tools/nsp-final/transaction.php")], timeout=12)
    run(["python3", str(ROOT / "tools/nsp-final/test_transaction.py")],
        timeout=50)

    host, user, port = os.environ["HOST"], os.environ["SSH_USER"], os.environ["PORT"]
    if not re.fullmatch(r"[0-9]{1,5}", port):
        raise ValueError("SSH_PORT")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", user):
        raise ValueError("SSH_USER")
    run_id, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
    if not run_id.isdigit() or not attempt.isdigit():
        raise ValueError("RUN_ID")
    stage = "nsp-migration-private/p0static19-" + run_id + "-" + attempt
    ssh_common = ["-i", str(Path.home() / ".ssh/nsp_p0_key"),
                  "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                  "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=12",
                  "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=3"]
    ssh = ["ssh", "-p", port, *ssh_common, user + "@" + host]
    scp = ["scp", "-P", port, *ssh_common]
    remote_dir = '"$HOME/' + stage + '"'
    site_dir = '"$HOME/www/nastoronepodryadchika.ru"'

    archive = Path("/tmp/nsp-p0-static19.tar")
    with tarfile.open(archive, "w") as out:
        out.add(PKG / "manifest.json", arcname="manifest.json")
        out.add(ROOT / "tools/nsp-final/transaction.php", arcname="transaction.php")
        for row in rows:
            out.add(PKG / "candidate" / row["path"],
                    arcname="candidate/" + row["path"])
    run(ssh + ["umask 077; mkdir -p " + remote_dir +
               " && test -d " + remote_dir], timeout=30)
    run(scp + [str(archive), user + "@" + host + ":" + stage + "/candidate.tar"],
        timeout=90)
    run(ssh + ["umask 077; cd " + remote_dir +
               " && tar -xf candidate.tar && chmod -R go-rwx ."], timeout=45)

    def transaction(action):
        raw = run(ssh + ["php " + remote_dir +
                         "/transaction.php " + shlex.quote(action) +
                         " " + site_dir + " " + remote_dir], timeout=120)
        return raw.decode(errors="replace").strip()

    dry = transaction("dry-run")
    report("dry-run.json", {"action": mode, "result": dry})
    print("STATIC19_REMOTE_DRY_RUN " + dry[-350:])
    if mode == "dry-run":
        print("DRY_RUN_ONLY_NO_PUBLIC_WRITES")
        return

    # Refetch every source HTML just before ANY production write. Transaction
    # separately compares actual filesystem SHA for all 19 files before apply.
    for row in rows:
        url = "https://nastoronepodryadchika.ru/" + row["path"] + "?p0=" + run_id
        req = urllib.request.Request(
            url, headers={"Cache-Control": "no-cache", "Accept-Encoding": "identity"})
        with urllib.request.urlopen(req, timeout=12) as response:
            current = response.read(2000001)
            if response.status != 200 or len(current) > 2000000:
                raise ValueError("PREPUBLIC_HTTP_" + row["path"])
            if sha(current) != row["before"]:
                raise ValueError("PREPUBLIC_HTTPS_SHA_DRIFT_" + row["path"])
    print("STATIC19_PREPUBLIC_HTTPS_PREIMAGES_19_PASS")

    applied = False
    try:
        result = transaction("apply")
        applied = True
        report("apply.json", {"result": result})
        print("STATIC19_APPLY " + result[-300:])
        checks = []
        for row in rows:
            url = ("https://nastoronepodryadchika.ru/" +
                   row["path"] + "?p0_after=" + run_id)
            req = urllib.request.Request(
                url, headers={"Cache-Control": "no-cache",
                              "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=15) as response:
                body = response.read(2000001)
                if response.status != 200 or len(body) > 2000000:
                    raise ValueError("POSTPUBLIC_HTTP_" + row["path"])
                if sha(body) != row["after"]:
                    raise ValueError("POSTPUBLIC_HTTPS_SHA_" + row["path"])
            checks.append({"path": row["path"], "sha256": row["after"],
                           "http_status": 200})
        verification = transaction("verify")
        report("postflight.json", {"status": "PASS", "files": checks,
                                   "production_verify": verification})
        print("STATIC19_PUBLISHED_VERIFIED_PASS files=19")
    except BaseException:
        if applied:
            try:
                rollback = transaction("rollback")
                report("rollback.json", {"result": rollback})
                print("STATIC19_ROLLBACK_PERFORMED")
            except BaseException as e:
                print("CRITICAL_STATIC19_ROLLBACK_FAILED " + str(e)[-450:],
                      file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
