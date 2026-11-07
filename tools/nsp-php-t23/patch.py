#!/usr/bin/env python3
"""Derive smallest T2/T3 PHP fix from the exact privately fetched LIVE bytes."""
import difflib
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

PREIMAGE = "12abc5750cc7f1d223cbeb002628338e2261e85e4bd4c3d6b8988cd7da295934"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def patch(live):
    if sha(live) != PREIMAGE:
        raise ValueError("LIVE_SHA_DRIFT")
    before = live.decode("utf-8")
    after = before
    for sku in ("t2", "t3"):
        pattern = rf"(?ms)^        '{sku}' => \[\r?\n.*?^        \],\r?\n"
        after, count = re.subn(pattern, "", after)
        if count != 1:
            raise ValueError("SKU_BLOCK_COUNT_" + sku + "_" + str(count))
    resolver = "    if ($sku === 't1') return null;"
    if after.count(resolver) != 1:
        raise ValueError("RESOLVER_ANCHOR_NOT_UNIQUE")
    after = after.replace(
        resolver, resolver + "\n    if ($sku === 't2' || $sku === 't3') return null;", 1
    )
    candidate = after.encode("utf-8")
    if candidate == live or "'t2' => [" in after or "'t3' => [" in after:
        raise ValueError("INCOMPLETE_PATCH")
    diff = list(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="LIVE/products-config.php", tofile="CANDIDATE/products-config.php"))
    hunks = [line for line in diff if line.startswith("@@")]
    if len(hunks) not in (2, 3):
        raise ValueError("TOO_MANY_HUNKS_" + str(len(hunks)))
    return candidate, len(hunks)


def php_validation(candidate_path):
    lint = subprocess.run(
        ["php", "-l", str(candidate_path)], text=True,
        capture_output=True, timeout=12)
    if lint.returncode:
        raise ValueError("PHP_LINT_FAIL")
    with tempfile.TemporaryDirectory(prefix="nsp-php-test-") as tmp:
        code = r'''
define("ORDERS_DIR", $argv[2]."/orders");
define("PRODUCTS_DIR", $argv[2]."/master-not-web");
require $argv[1];
$catalog = mvb_products();
foreach (["t2","t3"] as $sku) {
  if (isset($catalog[$sku])) throw new Exception("CATALOG_".$sku);
  if (mvb_resolve_product(["sku"=>$sku]) !== null) throw new Exception("RESOLVER_".$sku);
  if (mvb_resolve_product(["sku"=>$sku,"name"=>$catalog["p1"]["name"]]) !== null)
    throw new Exception("MIXED_".$sku);
}
$expected = ["p1"=>2990000,"p4"=>2490000,"p5"=>2990000,"test1"=>100];
foreach ($expected as $sku=>$price) {
  $item = mvb_resolve_product(["sku"=>$sku]);
  if (!is_array($item)||$item["price"]!==$price)
    throw new Exception("ACTIVE_".$sku);
}
foreach (["t1","t4","t5","t6","p12"] as $sku) {
  if (mvb_resolve_product(["sku"=>$sku])!==null) throw new Exception("RETIRED_".$sku);
}
if (DELIVERY_TTL_SECONDS !== 3600) throw new Exception("TTL");
echo "T23_DENIED_ACTIVE_P1_P4_P5_TEST1_PASS";
'''
        run = subprocess.run(
            ["php", "-r", code, str(candidate_path), tmp],
            text=True, capture_output=True, timeout=20)
        if run.returncode or "T23_DENIED_ACTIVE_P1_P4_P5_TEST1_PASS" not in run.stdout:
            raise ValueError("PHP_SYNTHETIC_FAIL_"+run.stderr[-220:])
    return {"php_lint": "PASS", "synthetic": "PASS",
            "cases": ["catalog_t2_t3_removed", "resolver_t2_t3_denied",
                      "mixed_sku_denied", "p1_p4_p5_test1_prices",
                      "existing_archive_denial", "delivery_ttl"]}


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: patch.py LIVE_PRIVATE_FILE CANDIDATE_PRIVATE_FILE RECEIPT_PRIVATE_FILE")
    src, dst, receipt = (pathlib.Path(s) for s in sys.argv[1:])
    if dst.exists() or receipt.exists():
        raise ValueError("DEST_ALREADY_EXISTS")
    live = src.read_bytes()
    candidate, hunks = patch(live)
    dst.write_bytes(candidate)
    tests = php_validation(dst)
    result = {"live_sha256": sha(live), "candidate_sha256": sha(candidate),
              "diff_hunks": hunks, "tests": tests,
              "scope": "products-config.php only",
              "sensitive_source_not_exported": True}
    receipt.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    print("PHP_T23_PREPARED_PASS source="+result["live_sha256"]+
          " candidate="+result["candidate_sha256"]+
          " lint=PASS synthetic=PASS")


if __name__ == "__main__":
    main()
