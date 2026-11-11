#!/usr/bin/env python3
"""NSP live-anchored SEO date patch: 32 editorial Article.dateModified + sitemap lastmod only.

READ-ONLY preparation; publish requires a signed-off exact request and hosting secrets.
No checkout, customer, product, legal or article body changes. Fail closed on live drift.
"""
import datetime
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tarfile
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = "https://nastoronepodryadchika.ru/"
DATE = b"2026-11-11"
ORIGINAL_SITEMAP_SHA = "3db0c9f7f2b402b2366e074cb0af6e00eeffc93cf6064fbaa67689efbaa993bb"
MANIFEST = ROOT / "docs/editorial/NSP_LEGACY_32_RELEASE_MANIFEST_20261111.json"
EVIDENCE = pathlib.Path("/tmp/nsp-seo-32-evidence")
EVIDENCE.mkdir(parents=True, exist_ok=True)
META = re.compile(rb'("dateModified"\s*:\s*")(\d{4}-\d{2}-\d{2})(")')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def command(argv, timeout=35):
    r = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=False, timeout=timeout)
    need(r.returncode == 0, "COMMAND_FAILED " + str(r.returncode) + " " +
         r.stderr.decode(errors="replace")[-850:])
    return r.stdout.decode(errors="replace").strip()


def http(path):
    need(re.fullmatch(r"(?:articles/[a-z0-9-]+\.html|sitemap\.xml)", path) is not None,
         "UNSAFE_HTTP_PATH")
    req = urllib.request.Request(SITE + path, headers={
        "Accept-Encoding": "identity",
        "Cache-Control": "no-cache",
        "User-Agent": "NSP-SEO-32-VerifiedRelease/1.0",
    })
    with urllib.request.urlopen(req, timeout=15) as response:
        need(response.status == 200, "HTTP_NOT_200:" + path)
        body = response.read(180_000)
        need(100 < len(body) < 180_000, "LIVE_SIZE:" + path)
        return body


def run_preflight():
    m = json.loads(MANIFEST.read_text(encoding="utf8"))
    rows = m["changed_files"]
    protected = m["protected_approved_articles"]
    need(m["schema"] == "NSP_ARTICLE_ONLY_RELEASE_MANIFEST_v1", "BAD_MANIFEST")
    need(len(rows) == 32 and len(protected) == 11, "SCOPE_COUNT")
    need(len({x["path"] for x in rows}) == 32, "DUP_ARTICLE")
    need(all(re.fullmatch(r"articles/[a-z0-9-]+\.html", x["path"]) for x in rows),
         "UNEXPECTED_ARTICLE_PATH")
    tx = ROOT / "tools/nsp-editorial/transaction.php"
    need(tx.is_file() and tx.read_text().count("T2 and T3 were retired by owner") == 1,
         "TRANSACTION_IDENTITY")
    command(["php", "-l", str(tx)])
    artifacts = {}
    changes = []
    for x in rows:
        name = x["path"]
        before = http(name)
        need(sha(before) == x["after_sha256"], "LIVE_DRIFT_ARTICLE:" + name)
        matches = list(META.finditer(before))
        need(len(matches) == 1, "ARTICLE_DATE_COUNT:" + name)
        old = matches[0].group(2)
        need(old < DATE, "ARTICLE_DATE_NOT_OLDER:" + name + ":" + old.decode())
        after = META.sub(lambda m: m.group(1) + DATE + m.group(3), before)
        need(after != before and after.count(b'"dateModified"') == 1,
             "ARTICLE_PATCH_NOT_ATOMIC:" + name)
        need(META.sub(lambda m: m.group(1) + old + m.group(3), after) == before,
             "ARTICLE_UNRELATED_MUTATION:" + name)
        artifacts[name] = after
        changes.append({"path": name, "before": sha(before), "after": sha(after),
                        "old_date_modified": old.decode(), "date_modified": DATE.decode()})
    raw = http("sitemap.xml")
    need(sha(raw) == ORIGINAL_SITEMAP_SHA, "LIVE_SITEMAP_DRIFT")
    before_root = ET.fromstring(raw)
    before_xml = [ET.tostring(n) for n in before_root]
    updated = raw
    for x in rows:
        u = (SITE + x["path"]).encode()
        old = b"<loc>" + u + b"</loc><lastmod>2026-10-21</lastmod>"
        new = b"<loc>" + u + b"</loc><lastmod>" + DATE + b"</lastmod>"
        need(updated.count(old) == 1, "SITEMAP_SCOPE_NOT_EXACT:" + x["path"])
        updated = updated.replace(old, new)
    root = ET.fromstring(updated)
    entries = []
    for element in root:
        data = {n.tag.rsplit("}", 1)[-1]: n.text for n in element}
        entries.append(data)
    need(len(entries) == 82, "SITEMAP_URL_COUNT")
    want = {SITE + x["path"] for x in rows}
    got = {e["loc"] for e in entries if e["lastmod"] == DATE.decode()}
    prior_old = {x.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                 for x in before_root
                 if x.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod") == DATE.decode()}
    need(got == want | prior_old, "SITEMAP_OTHER_PAGE_MODIFIED")
    need(len(before_xml) == len(entries), "SITEMAP_STRUCTURE_CHANGED")
    for x in protected:
        need(sha(http(x["path"])) == x["sha256"],
             "PROTECTED_APPROVED_ARTICLE_DRIFT:" + x["path"])
    artifacts["sitemap.xml"] = updated
    changes.append({"path": "sitemap.xml", "before": sha(raw),
                    "after": sha(updated), "updated_lastmod": 32})
    need(len(changes) == 33 and len(set(artifacts)) == 33, "RELEASE_COUNT")
    return changes, artifacts, tx


def stage():
    rows, artifacts, tx = run_preflight()
    out = EVIDENCE / "release.tar"
    with tarfile.open(out, "w") as t:
        manifest = (json.dumps([{"path": x["path"], "before": x["before"],
                                "after": x["after"]} for x in rows], indent=2) + "\n").encode()
        head = tarfile.TarInfo("manifest.json")
        head.size = len(manifest)
        head.mode = 0o600
        t.addfile(head, io.BytesIO(manifest))
        t.add(tx, arcname="transaction.php")
        for path, content in artifacts.items():
            info = tarfile.TarInfo("candidate/" + path)
            info.size = len(content)
            info.mode = 0o600
            t.addfile(info, io.BytesIO(content))
    receipt = {"schema": "NSP_32_SEO_METADATA_RELEASE_PREPARED_v1",
               "source_release": str(MANIFEST.relative_to(ROOT)),
               "scope": "32_ARTICLE_DATE_MODIFIED_PLUS_SITEMAP",
               "date_modified": DATE.decode(), "file_count": 33,
               "live_source_sha_checked": 32, "protected_approved_sha_checked": 11,
               "sitemap_before_sha": ORIGINAL_SITEMAP_SHA,
               "tar_sha256": sha(out.read_bytes()), "changes": rows,
               "production_writes": 0}
    (EVIDENCE / "prepared-manifest.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return out, rows


def release():
    request = json.loads((ROOT / "tools/nsp-editorial/seo-request.json").read_text())
    need(request == {"action": "publish", "scope": "32_ARTICLE_DATES_PLUS_SITEMAP",
                     "date": "2026-11-11"}, "UNAPPROVED_REQUEST")
    payload, rows = stage()
    print(json.dumps({"status": "PREPARE_PASS", "files": len(rows),
                      "sitemap_changes": 32}), flush=True)
    host = os.environ["HOST"]
    user = os.environ["SSH_USER"]
    port = os.environ.get("PORT", "22")
    need(re.fullmatch(r"[A-Za-z0-9._-]+", host) and
         re.fullmatch(r"[A-Za-z0-9._-]+", user) and
         re.fullmatch(r"[0-9]{1,5}", port), "SSH_ARGUMENTS")
    ident = os.environ["GITHUB_RUN_ID"] + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    need(re.fullmatch(r"[0-9]+-[0-9]+", ident), "RUN_IDENTIFIER")
    rel = "nsp-migration-private/seo-date-" + ident
    private_dir = '"$HOME/' + rel + '"'
    site_dir = '"$HOME/www/nastoronepodryadchika.ru"'
    opts = ["-i", str(pathlib.Path.home() / ".ssh/nsp_final_key"),
            "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
            "-o", "ConnectTimeout=12", "-o", "ServerAliveInterval=10",
            "-o", "ServerAliveCountMax=3"]
    ssh = ["ssh", "-p", port, *opts, user + "@" + host]
    scp = ["scp", "-P", port, *opts]
    command(ssh + ['umask 077; test -d "$HOME/nsp-migration-private" && ' +
                   "test -d " + site_dir + " && mkdir " + private_dir], timeout=32)
    command(scp + [str(payload), user + "@" + host + ":" + rel + "/release.tar"], timeout=90)
    command(ssh + ["umask 077; cd " + private_dir +
                   " && tar -xf release.tar && chmod -R go-rwx ."], timeout=45)

    def tx(action):
        raw = command(ssh + ["php " + private_dir + "/transaction.php " + action +
                             " " + site_dir + " " + private_dir], timeout=95)
        result = json.loads(raw.splitlines()[-1])
        need(result["status"] == "PASS" and result["mode"] == action,
             "REMOTE_TRANSACTION_" + action)
        return result

    dry = tx("dry-run")
    need(dry["files"] == 33 and dry["writes_to_public"] == 0, "DRY_RUN_FAIL")
    (EVIDENCE / "remote-dry-run.json").write_text(json.dumps(dry, indent=2) + "\n")
    applied = False
    try:
        applied_result = tx("apply")
        applied = True
        need(applied_result["files"] == 33 and
             applied_result["masters"] == "UNCHANGED" and
             applied_result["protected_php"] == "UNCHANGED", "APPLY_PROTECTION")
        (EVIDENCE / "remote-apply.json").write_text(
            json.dumps(applied_result, indent=2) + "\n")
        # Independent public post-check of all 33 files.
        expected = {x["path"]: x["after"] for x in rows}
        for path, h in expected.items():
            need(sha(http(path)) == h, "POST_PUBLIC_SHA_MISMATCH:" + path)
        verified = tx("verify")
        need(verified["protected_php"] == "UNCHANGED" and
             verified["masters"] == "UNCHANGED", "FINAL_PROTECTION_FAIL")
        (EVIDENCE / "remote-verify.json").write_text(
            json.dumps(verified, indent=2) + "\n")
        applied = False
        print(json.dumps({"status": "VERIFIED_RELEASE",
                          "articles": 32, "sitemap": 1,
                          "updated_lastmod": 32,
                          "independent_public_sha": "33/33 PASS",
                          "protected_articles": 11,
                          "php": "UNCHANGED", "masters": "UNCHANGED"}), flush=True)
    except BaseException:
        if applied:
            try:
                recovered = tx("rollback")
                (EVIDENCE / "remote-rollback.json").write_text(
                    json.dumps(recovered, indent=2) + "\n")
                print("AUTO_ROLLBACK=PASS", file=sys.stderr)
            except BaseException as error:
                print("ROLLBACK_FAILED:" + str(error), file=sys.stderr)
        raise


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else "validate"
    need(action in {"validate", "publish"}, "BAD_MODE")
    if action == "validate":
        _, rows = stage()
        print(json.dumps({"status": "PASS", "mode": action, "files": len(rows),
                          "public_writes": 0}))
    else:
        release()


if __name__ == "__main__":
    main()
