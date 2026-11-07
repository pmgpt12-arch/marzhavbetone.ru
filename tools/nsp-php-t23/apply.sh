#!/usr/bin/env bash
set -euo pipefail
umask 077
EXPECTED_BEFORE='12abc5750cc7f1d223cbeb002628338e2261e85e4bd4c3d6b8988cd7da295934'
EXPECTED_AFTER="$1"
RUN_ID="$2"
[[ "$RUN_ID" =~ ^[0-9]+$ ]] || { echo 'BAD_RUN_ID' >&2; exit 5; }
[[ "$EXPECTED_AFTER" =~ ^[a-f0-9]{64}$ ]] || { echo 'BAD_CANDIDATE_SHA' >&2; exit 5; }
ROOT="$HOME/www/nastoronepodryadchika.ru"
LIVE="$ROOT/products-config.php"
STAGE="$HOME/nsp-migration-private/php-t23-$RUN_ID"
BACKUP="$STAGE/original.php"
CANDIDATE="$STAGE/candidate.php"
test -d "$ROOT" && test -d "$STAGE"
test -f "$LIVE" && test ! -L "$LIVE"
test -f "$CANDIDATE" && test ! -L "$CANDIDATE"
CURRENT="$(sha256sum "$LIVE" | cut -d' ' -f1)"
[[ "$CURRENT" == "$EXPECTED_BEFORE" ]] || { echo 'STOP_LIVE_SHA_DRIFT' >&2; exit 7; }
[[ "$(sha256sum "$CANDIDATE" | cut -d' ' -f1)" == "$EXPECTED_AFTER" ]] || { echo 'STOP_CANDIDATE_SHA_DRIFT' >&2; exit 7; }
test ! -e "$BACKUP"
cp -p -- "$LIVE" "$BACKUP"
chmod 600 "$BACKUP"
[[ "$(sha256sum "$BACKUP" | cut -d' ' -f1)" == "$EXPECTED_BEFORE" ]] || { echo 'BACKUP_VERIFY_FAIL' >&2; exit 7; }
php -l "$CANDIDATE" >/dev/null
TMP=""
WROTE=0
restore_on_error() {
  local code=$?
  if [[ "$code" -ne 0 && "$WROTE" -eq 1 ]]; then
    local current
    current="$(sha256sum "$LIVE" | cut -d' ' -f1)" || true
    if [[ "$current" == "$EXPECTED_AFTER" && -f "$BACKUP" &&
          "$(sha256sum "$BACKUP" | cut -d' ' -f1)" == "$EXPECTED_BEFORE" ]]; then
      local rb
      rb="$(mktemp "$ROOT/.nsp-t23-rollback.XXXXXX")"
      cp "$BACKUP" "$rb"; chmod --reference="$LIVE" "$rb"
      mv -f -- "$rb" "$LIVE"
      echo 'ROLLBACK_PASS' >&2
    else
      echo 'CRITICAL_ROLLBACK_BLOCKED_BY_SHA_CONFLICT' >&2
    fi
  fi
  if [[ -n "$TMP" && -e "$TMP" ]]; then rm -f -- "$TMP"; fi
  exit "$code"
}
trap restore_on_error EXIT
[[ "$(sha256sum "$LIVE" | cut -d' ' -f1)" == "$EXPECTED_BEFORE" ]] || { echo 'PRE_RENAME_SHA_DRIFT' >&2; exit 8; }
TMP="$(mktemp "$ROOT/.nsp-t23.XXXXXX")"
cp "$CANDIDATE" "$TMP"
chmod --reference="$LIVE" "$TMP"
[[ "$(sha256sum "$TMP" | cut -d' ' -f1)" == "$EXPECTED_AFTER" ]] || exit 8
mv -f -- "$TMP" "$LIVE"
TMP=""
WROTE=1
[[ "$(sha256sum "$LIVE" | cut -d' ' -f1)" == "$EXPECTED_AFTER" ]] || exit 9
php -l "$LIVE" >/dev/null
php -r '
define("ORDERS_DIR", $argv[2]."/synthetic-orders");
define("PRODUCTS_DIR", $argv[2]."/synthetic-master");
require $argv[1];
foreach (["t2","t3"] as $sku) {
  if (array_key_exists($sku,mvb_products())) throw new Exception("T_IN_CATALOG");
  if (mvb_resolve_product(["sku"=>$sku])!==null) throw new Exception("T_RESOLVES");
  if (mvb_resolve_product(["sku"=>$sku,"name"=>mvb_products()["p1"]["name"]])!==null)
    throw new Exception("MIXED_SKU");
}
foreach (["p1"=>2990000,"p4"=>2490000,"p5"=>2990000,"test1"=>100] as $sku=>$price) {
  $item=mvb_resolve_product(["sku"=>$sku]);
  if (!is_array($item)||$item["price"]!==$price) throw new Exception("ACTIVE_REGRESSION");
}
echo "PHP_RUNTIME_SYNTHETIC_PASS";
' "$LIVE" "$STAGE"
echo
printf 'PHP_T23_DEPLOY_PASS old=%s new=%s private_backup_sha=%s\n' "$EXPECTED_BEFORE" "$EXPECTED_AFTER" "$EXPECTED_BEFORE"
