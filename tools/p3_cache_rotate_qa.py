#!/usr/bin/env python3
"""Rotate P3 production buyer cache with isolated backup, produce exact buyer ZIP."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NOMINATION = ROOT / "tools/candidates/p3-owner-approval-nomination-20261015/nomination.json"
TREE = "00aca2f4e4163f39e329f4dd14e5b23a813d448e"

def run(command, *, data=None, stdout=None, timeout=65):
    return subprocess.run(command, input=data, stdout=stdout if stdout is not None else subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True, timeout=timeout)
def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> int:
    if os.getenv("P3_CACHE_QA") != "true":
        raise ValueError("P3_CACHE_QA opt-in missing")
    if os.getenv("GITHUB_REF_NAME") != "release/mb001-p3-20261016":
        raise ValueError("unexpected branch")
    actual_tree = run(["git", "rev-parse", "HEAD:products-storage/05-ks-bez-vozvrata"]).stdout.decode().strip()
    if actual_tree != TREE:
        raise ValueError("frozen P3 source tree changed")
    run_id = os.environ["GITHUB_RUN_ID"]
    if not re.fullmatch(r"[0-9]{5,20}", run_id):
        raise ValueError("invalid GitHub run ID")
    local = Path(os.environ["RUNNER_TEMP"]) / "p3-cache-evidence"
    local.mkdir(mode=0o700, parents=True, exist_ok=True)

    env = os.environ
    ident = Path(env["HOME"]) / ".ssh/deploy_key"
    hosts = Path(env["HOME"]) / ".ssh/known_hosts"
    if not ident.is_file() or not hosts.is_file():
        raise ValueError("job-scoped SSH identity missing")
    remote = env["USER"] + "@" + env["HOST"]
    ssh = ["ssh", "-i", str(ident), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
           "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={hosts}",
           "-o", "ConnectTimeout=15", "-p", env["SSH_PORT"]]

    def remote_script(script: str, *args: str, timeout=60) -> str:
        cmdline = "bash -se -- " + shlex.join(args)
        result = run([*ssh, remote, cmdline], data=script.encode(), timeout=timeout)
        return result.stdout.decode().strip()

    def remote_read(path: str, target: Path) -> str:
        with target.open("wb") as stream:
            run([*ssh, remote, "cat " + shlex.quote(path)], stdout=stream, timeout=45)
        return sha(target.read_bytes())

    if os.getenv("P3_CACHE_INSPECT") == "true":
        observe = r'''
set -Eeuo pipefail
site_arg="$1"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
site="$(cd "$site" && pwd -P)"
delivery="$(php -r 'require $argv[1]; require $argv[2]; echo DELIVERY_DIR;' "$site/config.php" "$site/products-config.php")"
cache="$delivery/05-ks-bez-vozvrata.zip"
if test -f "$cache"; then
 echo "LIVE_CACHE_SHA256=$(sha256sum "$cache" | cut -d' ' -f1)"
 echo "LIVE_CACHE_PATH=$cache"
else
 echo "LIVE_CACHE=ABSENT"
fi
for d in "$delivery"/.p3-buyer-qa-*; do
 test -d "$d" || continue
 for f in "$d"/*.zip; do
  test -f "$f" || continue
  echo "STAGED_ZIP_SHA256=$(sha256sum "$f" | cut -d' ' -f1)"
  echo "STAGED_RUN_ID=$(basename "$d")"
 done
done
vault="$HOME/product-archive-vault/by-sku/p3"
for d in "$vault"/*; do
 test -d "$d" || continue
 echo "ARCHIVE_VERSION=$(basename "$d")"
 for f in "$d"/*.zip; do
  test -f "$f" || continue
  echo "ARCHIVED_OLD_ZIP_SHA256=$(sha256sum "$f" | cut -d' ' -f1)"
 done
done
'''
        report = remote_script(observe, env["SITE_PATH"])
        facts = dict(row.split("=", 1) for row in report.splitlines() if "=" in row)
        path = facts.pop("LIVE_CACHE_PATH", None)
        if not path: raise ValueError("live buyer cache missing")
        output = local / "P3-production-buyer-11-files.zip"
        digest = remote_read(path, output)
        if digest != facts.get("LIVE_CACHE_SHA256"): raise ValueError("live cache SHA mismatch")
        nomination = json.loads(NOMINATION.read_text(encoding="utf-8"))
        expected = {x["member"]: x["sha256"] for x in nomination["member_artifacts"]}
        with zipfile.ZipFile(output) as z:
            if z.testzip() or len(z.namelist()) != 11 or set(z.namelist()) != set(expected):
                raise ValueError("unexpected buyer archive members")
            if any(sha(z.read(n)) != expected[n] for n in expected):
                raise ValueError("buyer archive member SHA mismatch")
        receipt = {"status":"PASS_P3_PRODUCTION_BUYER_ZIP", "member_sha":"11/11 PASS", "zip_sha256":digest,
                   "vault":"product-archive-vault/by-sku/p3 outside webroot", "paid_order":"not invoked"}
        (local / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print("P3_PRODUCTION_BUYER_ZIP_VERIFIED " + json.dumps(receipt), flush=True)
        return 0

    preflight = r'''
set -Eeuo pipefail
umask 077
site_arg="$1"; products_arg="$2"; runid="$3"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
case "$products_arg" in /*) products="$products_arg";; *) products="$HOME/$products_arg";; esac
site="$(cd "$site" && pwd -P)"
products="$(cd "$products" && pwd -P)"
test -f "$site/config.php" && test -f "$site/products-config.php"
test -d "$products/05-ks-bez-vozvrata"
case "$products/" in "$site/"*) echo "PRODUCT_MASTER_IN_WEBROOT" >&2; exit 3;; esac
vault="$HOME/product-archive-vault/by-sku/p3"
test ! -L "$HOME/product-archive-vault" && test ! -L "$HOME/product-archive-vault/by-sku" && test ! -L "$vault"
mkdir -p "$vault"
chmod 700 "$HOME/product-archive-vault" "$HOME/product-archive-vault/by-sku" "$vault"
case "$(cd "$vault" && pwd -P)/" in "$site/"*) echo "ARCHIVE_VAULT_IN_WEBROOT" >&2; exit 4;; esac
delivery="$(php -r 'require $argv[1]; require $argv[2]; echo DELIVERY_DIR;' "$site/config.php" "$site/products-config.php")"
test -n "$delivery" && test -d "$delivery"
test ! -L "$delivery/05-ks-bez-vozvrata.zip"
stage="$delivery/.p3-buyer-qa-$runid"
test ! -e "$stage"
mkdir -m 700 "$stage"
php -r 'define("DELIVERY_DIR",$argv[1]);require $argv[2];require $argv[3];$p=mvb_products()["p3"];if($p["price"]!==1790000)exit(18);$z=mvb_build_product_zip("p3");if(!$z || !is_file($z))exit(19);' "$stage" "$site/config.php" "$site/products-config.php"
test -s "$stage/05-ks-bez-vozvrata.zip"
printf 'STAGED_ZIP=%s\nLIVE_ZIP=%s\nVAULT=%s\n' "$stage/05-ks-bez-vozvrata.zip" "$delivery/05-ks-bez-vozvrata.zip" "$vault"
'''
    report = remote_script(preflight, env["SITE_PATH"], env["PRODUCTS_PATH"], run_id)
    props = dict(row.split("=", 1) for row in report.splitlines() if "=" in row)
    if set(props) != {"STAGED_ZIP", "LIVE_ZIP", "VAULT"}:
        raise ValueError("unexpected production staging response")
    stage_file = local / "staged-P3.zip"
    staged_sha = remote_read(props["STAGED_ZIP"], stage_file)

    nomination = json.loads(NOMINATION.read_text(encoding="utf-8"))
    entries = nomination["member_artifacts"]
    expected = {row["member"]: (row["sha256"], row["bytes"]) for row in entries}
    if len(expected) != 11:
        raise ValueError("not 11 nominated buyer files")
    with zipfile.ZipFile(stage_file) as archive:
        if archive.testzip() is not None:
            raise ValueError("damaged production ZIP")
        names = [item.filename for item in archive.infolist()]
        if len(names) != 11 or set(names) != set(expected) or len(set(names)) != 11:
            raise ValueError("wrong production buyer ZIP contents")
        for name in names:
            data = archive.read(name)
            digest, count = expected[name]
            if sha(data) != digest or len(data) != count:
                raise ValueError("mismatched P3 member: " + name)
    print("PRODUCTION_P3_STAGED_ZIP 11/11_SHA_PASS sha256=" + staged_sha, flush=True)

    rotate = r'''
set -Eeuo pipefail
umask 077
stage="$1"; cache="$2"; vault="$3"; runid="$4"; expected="$5"
test -f "$stage" && test ! -L "$stage"
test "$(sha256sum "$stage" | cut -d' ' -f1)" = "$expected"
test ! -L "$cache"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive="$vault/$stamp-run$runid"
test ! -e "$archive"
mkdir -m 700 "$archive"
old="ABSENT"
if test -f "$cache"; then
  old="$(sha256sum "$cache" | cut -d' ' -f1)"
  mv "$cache" "$archive/05-ks-bez-vozvrata-previous.zip"
  chmod 600 "$archive/05-ks-bez-vozvrata-previous.zip"
fi
restore_previous() {
  if test ! -f "$cache" && test -f "$archive/05-ks-bez-vozvrata-previous.zip"; then
    cp -p "$archive/05-ks-bez-vozvrata-previous.zip" "$cache" || true
  fi
}
trap restore_previous ERR
mv "$stage" "$cache"
chmod 600 "$cache"
test "$(sha256sum "$cache" | cut -d' ' -f1)" = "$expected"
printf 'cache_rotated_utc=%s\nsku=p3\nprevious_sha256=%s\ncurrent_sha256=%s\n' "$(date -u +%FT%TZ)" "$old" "$expected" > "$archive/cache-rotation-receipt.txt"
chmod 600 "$archive/cache-rotation-receipt.txt"
trap - ERR
rmdir "$(dirname "$stage")"
printf 'P3_OLD_CACHE_ARCHIVED=%s\nP3_NEW_CACHE_SHA256=%s\nP3_ROTATION_PASS\n' "$old" "$expected"
'''
    rotation = remote_script(rotate, props["STAGED_ZIP"], props["LIVE_ZIP"], props["VAULT"], run_id, staged_sha)
    if "P3_ROTATION_PASS" not in rotation:
        raise ValueError("production did not confirm P3 cache rotation")

    final_path = local / "P3-production-buyer-11-files.zip"
    live_sha = remote_read(props["LIVE_ZIP"], final_path)
    if live_sha != staged_sha:
        raise ValueError("production live cache differs after rotation")
    stage_file.unlink()
    proof = {
        "status": "PASS_PRODUCTION_P3_EXACT_BUYER_CACHE",
        "sku": "p3",
        "price_rub": 17900,
        "file_count": 11,
        "buyer_member_sha256_match": "11/11",
        "production_buyer_zip_sha256": live_sha,
        "nominated_zip_sha256": nomination["candidate_archive"]["sha256"],
        "previous_cache_sha256": next(line.split("=", 1)[1] for line in rotation.splitlines() if line.startswith("P3_OLD_CACHE_ARCHIVED=")),
        "old_archive_location": "private server vault outside webroot: product-archive-vault/by-sku/p3",
        "production_cache_replaced": True,
        "paid_order_emulated": False,
        "live_paid_P3_order_tested": False,
        "time_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    (local / "verification.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("P3_ARCHIVE_ROTATION_AND_BUYER_FILE_VERIFIED " + json.dumps(proof, ensure_ascii=False), flush=True)
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, zipfile.BadZipFile) as exc:
        print("P3_CACHE_QA_BLOCKED " + str(exc), file=sys.stderr)
        raise SystemExit(1)
