#!/usr/bin/env bash
# Scoped, rollback-capable P11 release in the existing deploy workflow.
set -Eeuo pipefail
: "${HOST:?}" "${USER:?}" "${SITE_PATH:?}" "${PRODUCTS_PATH:?}" "${SSH_PORT:?}"
[[ "${P11_ONLY:-false}" == "true" ]] || { echo 'P11_SCOPE_NOT_ENABLED'; exit 2; }
export RSYNC_RSH="ssh -i $HOME/.ssh/deploy_key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=20 -p $SSH_PORT"
P11_ROOT='products-storage/13-raschet-metrami'
P11_LIVE="$PRODUCTS_PATH/13-raschet-metrami"
ZIP='tools/candidates/p11-buyer-editorial-20261016/P11-raschety-v-nedenezhnoy-forme-8-files-R1.zip'
ZIP_SHA='5f1ea256b4eec178e6cf13072e9b9b6c30104d5ad78194efd8afd60702671f5f'
TREE='95e8aaeb3a28ed44ba66ffa6e7d40b40353db0df'
SITE_FILES=(
  articles/dostraivali-za-metry-otkaz-v-zos.html
  articles/raschet-metrami.html
  diagnostika.html
  katalog.html
  materialy/raschet-metrami.html
  products-config.php
  products/p11-raschet-metrami.html
  products/t6-kvartiry-vmesto-deneg.html
)
ssh_run() { ssh -i "$HOME/.ssh/deploy_key" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=20 -p "$SSH_PORT" "$USER@$HOST" "$@"; }
expect_zip="$(sha256sum "$ZIP" | cut -d ' ' -f1)"
[[ "$expect_zip" == "$ZIP_SHA" ]] || { echo 'P11_ZIP_MISMATCH'; exit 3; }
[[ "$(git rev-parse "HEAD:$P11_ROOT")" == "$TREE" ]] || { echo 'P11_MASTER_TREE_MISMATCH'; exit 3; }
php -l products-config.php >/dev/null
php -r 'define("ORDERS_DIR", sys_get_temp_dir()); require "products-config.php"; exit(mvb_products()["p11"]["price"] === 2490000 && mvb_resolve_product(["sku"=>"t6"])===null ? 0 : 3);'
site_list="$(mktemp)"
prod_checks="$(mktemp)"
site_checks="$(mktemp)"
trap 'rm -f "$site_list" "$prod_checks" "$site_checks"' EXIT
printf '%s\n' "${SITE_FILES[@]}" > "$site_list"
( cd "$P11_ROOT" && sha256sum ./* ) > "$prod_checks"
sha256sum "${SITE_FILES[@]}" > "$site_checks"
if [[ "${DRY_RUN:-false}" == 'true' ]]; then
  echo 'P11_ONLY_DRY_RUN_NO_WRITE'
  rsync -az --delete --dry-run --itemize-changes "$P11_ROOT/" "$USER@$HOST:$P11_LIVE/"
  rsync -az --dry-run --itemize-changes --files-from="$site_list" ./ "$USER@$HOST:$SITE_PATH/"
  echo 'P11_ONLY_DRY_RUN_PASS'
  exit 0
fi
ref="$(git rev-parse --short=12 HEAD)"
backup="$PRODUCTS_PATH/../p11-release-backups/$ref"
ssh_run "set -eu; test -d '$P11_LIVE'; test -f '$SITE_PATH/products-config.php'; test ! -e '$backup'; mkdir -p '$backup/site'; cp -a '$P11_LIVE' '$backup/master'; (cd '$SITE_PATH' && tar -cf - ${SITE_FILES[*]}) | (cd '$backup/site' && tar -xf -)"
rollback() {
  echo 'P11_RELEASE_ROLLBACK_ATTEMPT' >&2
  ssh_run "set -eu; if test -d '$backup/master'; then mkdir -p '$P11_LIVE'; rsync -a --delete '$backup/master/' '$P11_LIVE/'; fi; if test -d '$backup/site'; then (cd '$backup/site' && tar -cf - ${SITE_FILES[*]}) | (cd '$SITE_PATH' && tar -xf -); fi" || echo 'P11_ROLLBACK_MANUAL_RECOVERY_REQUIRED' >&2
  ssh_run "bash -se -- '$SITE_PATH' '$PRODUCTS_PATH' '$ref'" <<'P11_ROLLBACK_CACHE' || echo 'P11_CACHE_ROLLBACK_MANUAL_RECOVERY_REQUIRED' >&2
set -eu
site_arg="$1";products_arg="$2";ref="$3"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
case "$products_arg" in /*) products="$products_arg";; *) products="$HOME/$products_arg";; esac
site="$(cd "$site" && pwd -P)"
products="$(cd "$products" && pwd -P)"
backup="$products/../p11-release-backups/$ref"
if test -f "$backup/cache-rotation-started"; then
  delivery="$(php -r 'require $argv[1];require $argv[2];echo DELIVERY_DIR;' "$site/config.php" "$site/products-config.php")"
  cache="$delivery/13-raschet-metrami.zip"
  if test -f "$backup/previous-p11-buyer.zip"; then
    cp -p "$backup/previous-p11-buyer.zip" "$cache"
  else
    rm -f "$cache"
  fi
fi
P11_ROLLBACK_CACHE
}
trap rollback ERR
# Publish masters before changing any public P11 price/checkout surface.
rsync -az --delete --itemize-changes "$P11_ROOT/" "$USER@$HOST:$P11_LIVE/"
ssh_run "cd '$P11_LIVE' && sha256sum -c" < "$prod_checks"
# Archive any previous P11 cached ZIP off-webroot, then build fresh buyer ZIP
# from the exact new masters. Old purchasers: zero. Other product caches untouched.
ssh_run "bash -se -- '$SITE_PATH' '$PRODUCTS_PATH' '$ref'" <<'P11_CACHE_REMOTE'
set -Eeuo pipefail
umask 077
site_arg="$1"; products_arg="$2"; ref="$3"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
case "$products_arg" in /*) products="$products_arg";; *) products="$HOME/$products_arg";; esac
site="$(cd "$site" && pwd -P)"
products="$(cd "$products" && pwd -P)"
backup="$products/../p11-release-backups/$ref"
test -d "$backup/master"
cache_dir="$(php -r 'require $argv[1];require $argv[2];echo DELIVERY_DIR;' "$site/config.php" "$site/products-config.php")"
test -d "$cache_dir"
cache="$cache_dir/13-raschet-metrami.zip"
test ! -L "$cache"
vault="$products/../product-archive-vault/by-sku/p11"
test ! -L "$products/../product-archive-vault"
mkdir -p "$vault";chmod 700 "$vault"
case "$(cd "$vault" && pwd -P)/" in "$site/"*) echo P11_VAULT_WITHIN_WEBROOT >&2;exit 6;; esac
if test -f "$cache"; then
  cp -p "$cache" "$backup/previous-p11-buyer.zip"
  touch "$backup/cache-rotation-started"
  mv "$cache" "$vault/$(date -u +%Y%m%dT%H%M%SZ)-$ref.zip"
  echo P11_OLD_CACHE_REMOVED_FROM_ACTIVE_DELIVERY
else
  echo P11_OLD_CACHE_ABSENT
  touch "$backup/cache-rotation-started"
fi
php -r 'require $argv[1];require $argv[2];$zip=mvb_build_product_zip("p11");if(!is_string($zip)||!is_file($zip))exit(9);echo "P11_NEW_BUYER_ZIP_SHA=".hash_file("sha256",$zip)."\n";' "$site/config.php" "$site/products-config.php"
test -s "$cache"
P11_CACHE_REMOTE
rsync -az --itemize-changes --files-from="$site_list" ./ "$USER@$HOST:$SITE_PATH/"
ssh_run "cd '$SITE_PATH' && sha256sum -c" < "$site_checks"
page="$(curl -fsSL --max-time 20 -H 'Cache-Control: no-cache' -H 'Pragma: no-cache' "https://marzhavbetone.ru/products/p11-raschet-metrami.html?p11_release=$ref")"
grep -Fq 'data-price="2490000"' <<< "$page" || { echo 'P11_HTTP_PRICE_MISMATCH'; false; }
grep -Fq '24 900' <<< "$page" || { echo 'P11_HTTP_VISIBLE_PRICE_MISMATCH'; false; }
# Read back the live cached ZIP, and compare all eight buyer members to the
# exact edition accepted by the owner. Never create or modify an order.
evidence="${RUNNER_TEMP:-/tmp}/p11-live-buyer-evidence"
mkdir -p "$evidence"
ssh_run "cat '$SITE_PATH/orders/delivery/13-raschet-metrami.zip'" > "$evidence/P11-production-buyer.zip"
python3 - "$ZIP" "$evidence/P11-production-buyer.zip" "$evidence/verification.json" <<'P11_VERIFY_PY'
import hashlib,json,sys,zipfile
from pathlib import Path
approved,live,out=map(Path,sys.argv[1:])
with zipfile.ZipFile(approved) as old,zipfile.ZipFile(live) as new:
    names=old.namelist()
    assert len(names)==8 and len(new.namelist())==8
    assert set(names)==set(new.namelist()) and new.testzip() is None
    assert all(hashlib.sha256(old.read(n)).digest()==hashlib.sha256(new.read(n)).digest() for n in names)
record={'status':'PASS_P11_PRODUCTION_EXACT_BUYER_ARCHIVE','files':8,'member_sha':'8/8',
        'live_sha256':hashlib.sha256(live.read_bytes()).hexdigest(),
        'owner_approved_zip_sha256':hashlib.sha256(approved.read_bytes()).hexdigest(),
        'buyer_link_seconds':3600,'real_paid_order':'not invoked'}
out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('P11_LIVE_BUYER_8_OF_8_VERIFIED',record['live_sha256'])
P11_VERIFY_PY
trap - ERR
echo "P11_SCOPED_RELEASE_VERIFIED $ref buyer_zip_source=$ZIP_SHA"
