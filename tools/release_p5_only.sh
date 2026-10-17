#!/usr/bin/env bash
# Scoped, rollback-capable P5 release in the existing deploy workflow.
set -Eeuo pipefail
: "${HOST:?}" "${USER:?}" "${SITE_PATH:?}" "${PRODUCTS_PATH:?}" "${SSH_PORT:?}"
[[ "${P5_ONLY:-false}" == "true" ]] || { echo 'P5_SCOPE_NOT_ENABLED'; exit 2; }
export RSYNC_RSH="ssh -i $HOME/.ssh/deploy_key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=20 -p $SSH_PORT"
P5_ROOT='products-storage/07-uderzhaniya-shtrafy-zachety'
P5_LIVE="$PRODUCTS_PATH/07-uderzhaniya-shtrafy-zachety"
ZIP='tools/candidates/p5-release-20261017/P5_P12_30_files_executive_language_R6_2026-10-16.zip'
ZIP_SHA='76a908cf4c575c0423b2bbe639182f44856518ae8466bd03bc2f38aad86de359'
TREE='9bf5632d81054c1343bdc3819f6ec546f0d4bb84'
SITE_FILES=(
  articles/pretenziya-za-chuzhuyu-kommunalku.html
  diagnostika.html
  katalog.html
  products-config.php
  products/p5-shtrafy-uderzhaniya.html
  products/p12-spor-s-summoy.html
  products/t3-odnostoronniy-akt-i-zachet.html
)
ssh_run() { ssh -i "$HOME/.ssh/deploy_key" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=20 -p "$SSH_PORT" "$USER@$HOST" "$@"; }
expect_zip="$(sha256sum "$ZIP" | cut -d ' ' -f1)"
[[ "$expect_zip" == "$ZIP_SHA" ]] || { echo 'P5_ZIP_MISMATCH'; exit 3; }
[[ "$(git rev-parse "HEAD:$P5_ROOT")" == "$TREE" ]] || { echo 'P5_MASTER_TREE_MISMATCH'; exit 3; }
php -l products-config.php >/dev/null
php -r 'define("ORDERS_DIR", sys_get_temp_dir()); require "products-config.php"; exit(mvb_products()["p5"]["price"] === 2990000 && mvb_resolve_product(["sku"=>"p12"])===null ? 0 : 3);'
site_list="$(mktemp)"
prod_checks="$(mktemp)"
site_checks="$(mktemp)"
trap 'rm -f "$site_list" "$prod_checks" "$site_checks"' EXIT
printf '%s\n' "${SITE_FILES[@]}" > "$site_list"
( cd "$P5_ROOT" && sha256sum ./* ) > "$prod_checks"
sha256sum "${SITE_FILES[@]}" > "$site_checks"
if [[ "${DRY_RUN:-false}" == 'true' ]]; then
  echo 'P5_ONLY_DRY_RUN_NO_WRITE'
  rsync -az --delete --dry-run --itemize-changes "$P5_ROOT/" "$USER@$HOST:$P5_LIVE/"
  rsync -az --dry-run --itemize-changes --files-from="$site_list" ./ "$USER@$HOST:$SITE_PATH/"
  echo 'P5_ONLY_DRY_RUN_PASS'
  exit 0
fi
ref="$(git rev-parse --short=12 HEAD)"
backup="$PRODUCTS_PATH/../p5-release-backups/$ref"
ssh_run "set -eu; test -d '$P5_LIVE'; test -f '$SITE_PATH/products-config.php'; test ! -e '$backup'; mkdir -p '$backup/site'; cp -a '$P5_LIVE' '$backup/master'; (cd '$SITE_PATH' && tar -cf - ${SITE_FILES[*]}) | (cd '$backup/site' && tar -xf -)"
rollback() {
  echo 'P5_RELEASE_ROLLBACK_ATTEMPT' >&2
  ssh_run "set -eu; if test -d '$backup/master'; then mkdir -p '$P5_LIVE'; rsync -a --delete '$backup/master/' '$P5_LIVE/'; fi; if test -d '$backup/site'; then (cd '$backup/site' && tar -cf - ${SITE_FILES[*]}) | (cd '$SITE_PATH' && tar -xf -); fi" || echo 'P5_ROLLBACK_MANUAL_RECOVERY_REQUIRED' >&2
  ssh_run "bash -se -- '$SITE_PATH' '$PRODUCTS_PATH' '$ref'" <<'P5_ROLLBACK_CACHE' || echo 'P5_CACHE_ROLLBACK_MANUAL_RECOVERY_REQUIRED' >&2
set -eu
site_arg="$1";products_arg="$2";ref="$3"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
case "$products_arg" in /*) products="$products_arg";; *) products="$HOME/$products_arg";; esac
site="$(cd "$site" && pwd -P)"
products="$(cd "$products" && pwd -P)"
backup="$products/../p5-release-backups/$ref"
if test -f "$backup/cache-rotation-started"; then
  delivery="$(php -r 'require $argv[1];require $argv[2];echo DELIVERY_DIR;' "$site/config.php" "$site/products-config.php")"
  cache="$delivery/07-uderzhaniya-shtrafy-zachety.zip"
  if test -f "$backup/previous-p5-buyer.zip"; then
    cp -p "$backup/previous-p5-buyer.zip" "$cache"
  else
    rm -f "$cache"
  fi
fi
if test -f "$backup/p12-cache-rotation-started" && test -f "$backup/previous-p12-buyer.zip"; then
  cp -p "$backup/previous-p12-buyer.zip" "$delivery/12-otvet-na-pretenziyu.zip"
fi
P5_ROLLBACK_CACHE
}
trap rollback ERR
# Publish masters before changing any public P5 price/checkout surface.
rsync -az --delete --itemize-changes "$P5_ROOT/" "$USER@$HOST:$P5_LIVE/"
ssh_run "cd '$P5_LIVE' && sha256sum -c" < "$prod_checks"
# Archive any previous P5 cached ZIP off-webroot, then build fresh buyer ZIP
# from the exact new masters. Old purchasers: zero. Other product caches untouched.
ssh_run "bash -se -- '$SITE_PATH' '$PRODUCTS_PATH' '$ref'" <<'P5_CACHE_REMOTE'
set -Eeuo pipefail
umask 077
site_arg="$1"; products_arg="$2"; ref="$3"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
case "$products_arg" in /*) products="$products_arg";; *) products="$HOME/$products_arg";; esac
site="$(cd "$site" && pwd -P)"
products="$(cd "$products" && pwd -P)"
backup="$products/../p5-release-backups/$ref"
test -d "$backup/master"
cache_dir="$(php -r 'require $argv[1];require $argv[2];echo DELIVERY_DIR;' "$site/config.php" "$site/products-config.php")"
test -d "$cache_dir"
cache="$cache_dir/07-uderzhaniya-shtrafy-zachety.zip"
test ! -L "$cache"
vault="$products/../product-archive-vault/by-sku/p5"
test ! -L "$products/../product-archive-vault"
mkdir -p "$vault";chmod 700 "$vault"
case "$(cd "$vault" && pwd -P)/" in "$site/"*) echo P5_VAULT_WITHIN_WEBROOT >&2;exit 6;; esac
if test -f "$cache"; then
  cp -p "$cache" "$backup/previous-p5-buyer.zip"
  touch "$backup/cache-rotation-started"
  mv "$cache" "$vault/$(date -u +%Y%m%dT%H%M%SZ)-$ref.zip"
  echo P5_OLD_CACHE_REMOVED_FROM_ACTIVE_DELIVERY
else
  echo P5_OLD_CACHE_ABSENT
  touch "$backup/cache-rotation-started"
fi
# P12 is now merged into P5: remove its retired cached ZIP too.
cache12="$cache_dir/12-otvet-na-pretenziyu.zip"
test ! -L "$cache12"
vault12="$products/../product-archive-vault/by-sku/p12"
mkdir -p "$vault12";chmod 700 "$vault12"
case "$(cd "$vault12" && pwd -P)/" in "$site/"*) echo P12_VAULT_WITHIN_WEBROOT >&2;exit 6;; esac
if test -f "$cache12"; then
  cp -p "$cache12" "$backup/previous-p12-buyer.zip"
  mv "$cache12" "$vault12/$(date -u +%Y%m%dT%H%M%SZ)-$ref.zip"
  touch "$backup/p12-cache-rotation-started"
  echo P12_OLD_CACHE_REMOVED_FROM_ACTIVE_DELIVERY
fi
php -r 'require $argv[1];require $argv[2];$zip=mvb_build_product_zip("p5");if(!is_string($zip)||!is_file($zip))exit(9);echo "P5_NEW_BUYER_ZIP_SHA=".hash_file("sha256",$zip)."\n";' "$site/config.php" "$site/products-config.php"
test -s "$cache"
P5_CACHE_REMOTE
rsync -az --itemize-changes --files-from="$site_list" ./ "$USER@$HOST:$SITE_PATH/"
ssh_run "cd '$SITE_PATH' && sha256sum -c" < "$site_checks"
page="$(curl -fsSL --max-time 20 -H 'Cache-Control: no-cache' -H 'Pragma: no-cache' "https://marzhavbetone.ru/products/p5-shtrafy-uderzhaniya.html?p5_release=$ref")"
grep -Fq 'data-price="2990000"' <<< "$page" || { echo 'P5_HTTP_PRICE_MISMATCH'; false; }
grep -Fq '29 900' <<< "$page" || { echo 'P5_HTTP_VISIBLE_PRICE_MISMATCH'; false; }
# Read back the live cached ZIP, and compare all thirty buyer members to the
# exact edition accepted by the owner. Never create or modify an order.
evidence="${RUNNER_TEMP:-/tmp}/p5-live-buyer-evidence"
mkdir -p "$evidence"
ssh_run "cat '$SITE_PATH/orders/delivery/07-uderzhaniya-shtrafy-zachety.zip'" > "$evidence/P5-production-buyer.zip"
python3 - "$ZIP" "$evidence/P5-production-buyer.zip" "$evidence/verification.json" <<'P5_VERIFY_PY'
import hashlib,json,sys,zipfile
from pathlib import Path
approved,live,out=map(Path,sys.argv[1:])
with zipfile.ZipFile(approved) as old,zipfile.ZipFile(live) as new:
    names=old.namelist()
    assert len(names)==30 and len(new.namelist())==30
    assert set(names)==set(new.namelist()) and new.testzip() is None
    assert all(hashlib.sha256(old.read(n)).digest()==hashlib.sha256(new.read(n)).digest() for n in names)
record={'status':'PASS_P5_PRODUCTION_EXACT_BUYER_ARCHIVE','files':30,'member_sha':'30/30',
        'live_sha256':hashlib.sha256(live.read_bytes()).hexdigest(),
        'owner_approved_zip_sha256':hashlib.sha256(approved.read_bytes()).hexdigest(),
        'buyer_link_seconds':3600,'real_paid_order':'not invoked'}
out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('P5_LIVE_BUYER_30_OF_30_VERIFIED',record['live_sha256'])
P5_VERIFY_PY
trap - ERR
echo "P5_SCOPED_RELEASE_VERIFIED $ref buyer_zip_source=$ZIP_SHA"
