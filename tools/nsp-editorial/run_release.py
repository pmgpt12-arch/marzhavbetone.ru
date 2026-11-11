#!/usr/bin/env python3
"""Targeted, rollback-capable NSP editorial release: exactly 32 HTML + article.css.

No products, checkout handlers, secrets, order data, or approved article content
are included in the candidate. Reuses the existing nsp-final PHP transaction.
"""
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/editorial/NSP_LEGACY_32_RELEASE_MANIFEST_20261111.json"
EVIDENCE = pathlib.Path("/tmp/nsp-editorial-evidence")
EVIDENCE.mkdir(parents=True, exist_ok=True)
ROOT_SITE = '\"$HOME/www/nastoronepodryadchika.ru\"'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(args, timeout=45):
    result = subprocess.run(args, check=False, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=timeout)
    if result.returncode:
        raise RuntimeError("COMMAND_FAILED_" + str(result.returncode) + ": " +
                           result.stderr.decode(errors="replace")[-1100:])
    return result.stdout.decode(errors="replace").strip()


def validate():
    m = json.loads(MANIFEST.read_text(encoding="utf8"))
    changed = m["changed_files"]
    approved = m["protected_approved_articles"]
    assert m["schema"] == "NSP_ARTICLE_ONLY_RELEASE_MANIFEST_v1"
    assert m["target_host"] == "nastoronepodryadchika.ru"
    assert len(changed) == 32 and len(approved) == 11
    assert m["image_uploads"] == 0
    assert m["style_asset"]["path"] == "article.css"
    rows = []
    for x in [*changed, m["style_asset"]]:
        p = x["path"]
        assert p == "article.css" or re.fullmatch(r"articles/[a-z0-9-]+\.html", p), p
        f = ROOT / p
        assert f.is_file() and not f.is_symlink()
        data = f.read_bytes()
        assert sha(data) == x["after_sha256"], "CANDIDATE_DRIFT: " + p
        assert len(data) == x["bytes"], "BYTES_DRIFT: " + p
        assert re.fullmatch(r"[0-9a-f]{64}", x["before_sha256"]), p
        assert x["before_sha256"] != x["after_sha256"], p
        rows.append({"path": p, "before": x["before_sha256"], "after": x["after_sha256"]})
    assert len({r["path"] for r in rows}) == 33
    assert not any(r["path"] in {x["path"] for x in approved} for r in rows)
    tx = ROOT / "tools/nsp-final/transaction.php"
    assert tx.is_file()
    # A previously qualified deploy executor from the project, unmodified.
    command(["php", "-l", str(tx)])
    command(["python3", str(ROOT / "tools/nsp_editorial_release_preflight.py"), "--mode", "static"])
    return rows, tx


def stage(rows, tx):
    payload = EVIDENCE / "candidate.tar"
    with tarfile.open(payload, mode="w") as t:
        data = (json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(data)
        info.mode = 0o600
        t.addfile(info, io.BytesIO(data))
        t.add(tx, arcname="transaction.php")
        for r in rows:
            t.add(ROOT / r["path"], arcname="candidate/" + r["path"], recursive=False)
    members = [x.name for x in tarfile.open(payload).getmembers()]
    assert len(members) == 35 and len(set(members)) == 35
    assert all(x in {"manifest.json", "transaction.php"} or
               x.startswith("candidate/articles/") or
               x == "candidate/article.css" for x in members)
    (EVIDENCE / "stage-receipt.json").write_text(
        json.dumps({"files": len(rows), "tar_sha256": sha(payload.read_bytes()),
                    "tar_bytes": payload.stat().st_size}, indent=2))
    return payload


def production(mode, rows, payload):
    assert mode in {"dry-run", "publish"}
    host = os.environ["HOST"]
    user = os.environ["SSH_USER"]
    port = os.environ.get("PORT", "22")
    run = os.environ["GITHUB_RUN_ID"]
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    assert re.fullmatch(r"[0-9]+", run) and re.fullmatch(r"[0-9]+", attempt)
    assert re.fullmatch(r"[0-9]{1,5}", port)
    assert re.fullmatch(r"[a-zA-Z0-9._-]+", host)
    assert re.fullmatch(r"[a-zA-Z0-9._-]+", user)
    assert host not in {"localhost", "127.0.0.1"}
    rel = "nsp-migration-private/editorial-" + run + "-" + attempt
    ssh_opts = ["-i", str(pathlib.Path.home() / ".ssh/nsp_final_key"),
                "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=12", "-o", "ServerAliveInterval=10",
                "-o", "ServerAliveCountMax=3"]
    ssh = ["ssh", "-p", port, *ssh_opts, user + "@" + host]
    scp = ["scp", "-P", port, *ssh_opts]
    remote = '\"$HOME/' + rel + '\"'
    command(["python3", str(ROOT / "tools/nsp_editorial_release_preflight.py"),
             "--mode", "live-pre"], timeout=90)
    command(ssh + ['umask 077; test -d "$HOME/nsp-migration-private" && ' +
                   'test -d ' + ROOT_SITE + ' && mkdir ' + remote], timeout=35)
    command(scp + [str(payload), user + "@" + host + ":" + rel + "/candidate.tar"], timeout=90)
    command(ssh + ["umask 077; cd " + remote +
                   " && tar -xf candidate.tar && chmod -R go-rwx ."], timeout=45)

    def transaction(action):
        output = command(ssh + ["php " + remote + "/transaction.php " + action +
                                " " + ROOT_SITE + " " + remote], timeout=100)
        result = json.loads(output.splitlines()[-1])
        assert result["status"] == "PASS" and result["mode"] == action
        return result

    check = transaction("dry-run")
    assert check["files"] == 33 and check["writes_to_public"] == 0
    (EVIDENCE / "remote-dry-run.json").write_text(json.dumps(check, indent=2) + "\n")
    if mode == "dry-run":
        print(json.dumps({"status": "PASS", "mode": mode, "files": 33,
                          "public_writes": 0, "remote_preflight": "PASS"}))
        return
    applied = False
    try:
        # Atomic writes, exact backup on shared hosting, and protected PHP/master
        # checks are implemented by the already-qualified project transaction.
        check = transaction("apply")
        assert check["files"] == 33 and check["protected_php"] == "UNCHANGED"
        applied = True
        (EVIDENCE / "remote-apply.json").write_text(json.dumps(check, indent=2) + "\n")
        command(["python3", str(ROOT / "tools/nsp_editorial_release_preflight.py"),
                 "--mode", "live-post"], timeout=95)
        verify = transaction("verify")
        assert verify["protected_php"] == "UNCHANGED"
        (EVIDENCE / "remote-verify.json").write_text(json.dumps(verify, indent=2) + "\n")
        applied = False
        print(json.dumps({"status": "VERIFIED_RELEASE", "mode": mode,
                          "files": 33, "articles": 32, "css": 1,
                          "protected_articles": 11, "image_uploads": 0,
                          "buyer_masters": "UNCHANGED", "protected_php": "UNCHANGED"}))
    except BaseException:
        if applied:
            try:
                recovered = transaction("rollback")
                (EVIDENCE / "remote-rollback.json").write_text(
                    json.dumps(recovered, indent=2) + "\n")
                print("NSP_EDITORIAL_ROLLBACK=PASS", flush=True)
            except BaseException as error:
                print("NSP_EDITORIAL_ROLLBACK_ERROR=" + str(error), file=sys.stderr)
        raise


def main():
    mode = sys.argv[1]
    assert mode in {"validate", "dry-run", "publish"}, "BAD_ACTION"
    rows, tx = validate()
    payload = stage(rows, tx)
    if mode == "validate":
        print(json.dumps({"status": "PASS", "mode": mode, "files": len(rows),
                          "candidate_sha256": sha(payload.read_bytes())}))
        return
    production(mode, rows, payload)


if __name__ == "__main__":
    main()
