#!/usr/bin/env bash
# Scoped, rollback-capable T2 release in the existing deploy workflow.
set -Eeuo pipefail
: "${HOST:?}" "${USER:?}" "${SITE_PATH:?}" "${PRODUCTS_PATH:?}" "${SSH_PORT:?}"
[[ "${T2_ONLY:-false}" == "true" ]] || { echo 'T2_SCOPE_NOT_ENABLED'; exit 2; }
export RSYNC_RSH="ssh -i $HOME/.ssh/deploy_key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=20 -p $SSH_PORT"
T2_ROOT='products-storage/14-peredacha-id-pod-podpis'
T2_LIVE="$PRODUCTS_PATH/14-peredacha-id-pod-podpis"
ZIP='tools/candidates/t2-buyer-review-20261017/T2-peredacha-ID-6-files-business-R2.zip'
ZIP_SHA='f50e64138980e4ad0ad0f262a5201e43464b0c600b4cc023726f50d23cebe195'
TREE='262cc7dfbe39973106806897d958c6f17d6f933c'
SITE_FILES=(
  articles/akt-osvidetelstvovaniya-skrytyh-rabot.html
  articles/pyat-dokazatelstv-vypolneniya.html
  articles/akt-skrytyh-rabot-obrazec.html
  articles/akt-skrytyh-rabot-montazh.html
  articles/akt-peredachi-stroitelnoy-ploshchadki-obrazec.html
  articles/ispolnitelnaya-dokumentaciya-sostav.html
  diagnostika.html
  katalog.html
  materialy/akt-skrytyh-rabot.html
  materialy/ispolnitelnaya-dokumentaciya.html
  products-config.php
  products/t2-peredacha-ispolnitelnoy-dokumentacii.html
)
ssh_run() { ssh -i "$HOME/.ssh/deploy_key" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=20 -p "$SSH_PORT" "$USER@$HOST" "$@"; }
expect_zip="$(sha256sum "$ZIP" | cut -d ' ' -f1)"
[[ "$expect_zip" == "$ZIP_SHA" ]] || { echo 'T2_ZIP_MISMATCH'; exit 3; }
[[ "$(git rev-parse "HEAD:$T2_ROOT")" == "$TREE" ]] || { echo 'T2_MASTER_TREE_MISMATCH'; exit 3; }
php -l products-config.php >/dev/null
php -r 'define("ORDERS_DIR", sys_get_temp_dir()); require "products-config.php"; exit(mvb_products()["t2"]["price"] === 990000 && mvb_resolve_product(["sku"=>"t2"])!==null ? 0 : 3);'
site_list="$(mktemp)"
prod_checks="$(mktemp)"
site_checks="$(mktemp)"
trap 'rm -f "$site_list" "$prod_checks" "$site_checks"' EXIT
printf '%s\n' "${SITE_FILES[@]}" > "$site_list"
( cd "$T2_ROOT" && sha256sum ./* ) > "$prod_checks"
sha256sum "${SITE_FILES[@]}" > "$site_checks"
if [[ "${DRY_RUN:-false}" == 'true' ]]; then
  echo 'T2_ONLY_DRY_RUN_NO_WRITE'
  rsync -az --delete --dry-run --itemize-changes "$T2_ROOT/" "$USER@$HOST:$T2_LIVE/"
  rsync -az --dry-run --itemize-changes --files-from="$site_list" ./ "$USER@$HOST:$SITE_PATH/"
  echo 'T2_ONLY_DRY_RUN_PASS'
  exit 0
fi
ref="$(git rev-parse --short=12 HEAD)"
backup="$PRODUCTS_PATH/../t2-release-backups/$ref"
ssh_run "set -eu; test -d '$T2_LIVE'; test -f '$SITE_PATH/products-config.php'; test ! -e '$backup'; mkdir -p '$backup/site'; cp -a '$T2_LIVE' '$backup/master'; (cd '$SITE_PATH' && tar -cf - ${SITE_FILES[*]}) | (cd '$backup/site' && tar -xf -)"
rollback() {
  echo 'T2_RELEASE_ROLLBACK_ATTEMPT' >&2
  ssh_run "set -eu; if test -d '$backup/master'; then mkdir -p '$T2_LIVE'; rsync -a --delete '$backup/master/' '$T2_LIVE/'; fi; if test -d '$backup/site'; then (cd '$backup/site' && tar -cf - ${SITE_FILES[*]}) | (cd '$SITE_PATH' && tar -xf -); fi" || echo 'T2_ROLLBACK_MANUAL_RECOVERY_REQUIRED' >&2
  ssh_run "bash -se -- '$SITE_PATH' '$PRODUCTS_PATH' '$ref'" <<'T2_ROLLBACK_CACHE' || echo 'T2_CACHE_ROLLBACK_MANUAL_RECOVERY_REQUIRED' >&2
set -eu
site_arg="$1";products_arg="$2";ref="$3"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
case "$products_arg" in /*) products="$products_arg";; *) products="$HOME/$products_arg";; esac
site="$(cd "$site" && pwd -P)"
products="$(cd "$products" && pwd -P)"
backup="$products/../t2-release-backups/$ref"
if test -f "$backup/cache-rotation-started"; then
  delivery="$(php -r 'require $argv[1];require $argv[2];echo DELIVERY_DIR;' "$site/config.php" "$site/products-config.php")"
  cache="$delivery/14-peredacha-id-pod-podpis.zip"
  if test -f "$backup/previous-t2-buyer.zip"; then
    cp -p "$backup/previous-t2-buyer.zip" "$cache"
  else
    rm -f "$cache"
  fi
fi
T2_ROLLBACK_CACHE
}
trap rollback ERR
# Publish masters before changing any public T2 price/checkout surface.
rsync -az --delete --itemize-changes "$T2_ROOT/" "$USER@$HOST:$T2_LIVE/"
ssh_run "cd '$T2_LIVE' && sha256sum -c" < "$prod_checks"
# Archive any previous T2 cached ZIP off-webroot, then build fresh buyer ZIP
# from the exact new masters. Old purchasers: zero. Other product caches untouched.
ssh_run "bash -se -- '$SITE_PATH' '$PRODUCTS_PATH' '$ref'" <<'T2_CACHE_REMOTE'
set -Eeuo pipefail
umask 077
site_arg="$1"; products_arg="$2"; ref="$3"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
case "$products_arg" in /*) products="$products_arg";; *) products="$HOME/$products_arg";; esac
site="$(cd "$site" && pwd -P)"
products="$(cd "$products" && pwd -P)"
backup="$products/../t2-release-backups/$ref"
test -d "$backup/master"
cache_dir="$(php -r 'require $argv[1];require $argv[2];echo DELIVERY_DIR;' "$site/config.php" "$site/products-config.php")"
test -d "$cache_dir"
cache="$cache_dir/14-peredacha-id-pod-podpis.zip"
test ! -L "$cache"
vault="$products/../product-archive-vault/by-sku/t2"
test ! -L "$products/../product-archive-vault"
mkdir -p "$vault";chmod 700 "$vault"
case "$(cd "$vault" && pwd -P)/" in "$site/"*) echo T2_VAULT_WITHIN_WEBROOT >&2;exit 6;; esac
if test -f "$cache"; then
  cp -p "$cache" "$backup/previous-t2-buyer.zip"
  touch "$backup/cache-rotation-started"
  mv "$cache" "$vault/$(date -u +%Y%m%dT%H%M%SZ)-$ref.zip"
  echo T2_OLD_CACHE_REMOVED_FROM_ACTIVE_DELIVERY
else
  echo T2_OLD_CACHE_ABSENT
  touch "$backup/cache-rotation-started"
fi
php -r 'require $argv[1];require $argv[2];$zip=mvb_build_product_zip("t2");if(!is_string($zip)||!is_file($zip))exit(9);echo "T2_NEW_BUYER_ZIP_SHA=".hash_file("sha256",$zip)."\n";' "$site/config.php" "$site/products-config.php"
test -s "$cache"
T2_CACHE_REMOTE
rsync -az --itemize-changes --files-from="$site_list" ./ "$USER@$HOST:$SITE_PATH/"
ssh_run "cd '$SITE_PATH' && sha256sum -c" < "$site_checks"
page="$(curl -fsSL --max-time 20 -H 'Cache-Control: no-cache' -H 'Pragma: no-cache' "https://marzhavbetone.ru/products/t2-peredacha-ispolnitelnoy-dokumentacii.html?t2_release=$ref")"
grep -Fq 'data-price="990000"' <<< "$page" || { echo 'T2_HTTP_PRICE_MISMATCH'; false; }
grep -Fq '9 900' <<< "$page" || { echo 'T2_HTTP_VISIBLE_PRICE_MISMATCH'; false; }
# Read back the live cached ZIP, and compare all six buyer members to the
# exact edition accepted by the owner. Never create or modify an order.
evidence="${RUNNER_TEMP:-/tmp}/t2-live-buyer-evidence"
mkdir -p "$evidence"
ssh_run "cat '$SITE_PATH/orders/delivery/14-peredacha-id-pod-podpis.zip'" > "$evidence/T2-production-buyer.zip"
python3 - "$ZIP" "$evidence/T2-production-buyer.zip" "$evidence/verification.json" <<'T2_VERIFY_PY'
import hashlib,json,sys,zipfile
from pathlib import Path
approved,live,out=map(Path,sys.argv[1:])
with zipfile.ZipFile(approved) as old,zipfile.ZipFile(live) as new:
    names=old.namelist()
    assert len(names)==6 and len(new.namelist())==6
    assert set(names)==set(new.namelist()) and new.testzip() is None
    assert all(hashlib.sha256(old.read(n)).digest()==hashlib.sha256(new.read(n)).digest() for n in names)
record={'status':'PASS_T2_PRODUCTION_EXACT_BUYER_ARCHIVE','files':6,'member_sha':'6/6',
        'live_sha256':hashlib.sha256(live.read_bytes()).hexdigest(),
        'owner_approved_zip_sha256':hashlib.sha256(approved.read_bytes()).hexdigest(),
        'buyer_link_seconds':3600,'real_paid_order':'not invoked'}
out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('T2_LIVE_BUYER_6_OF_6_VERIFIED',record['live_sha256'])
T2_VERIFY_PY
trap - ERR
echo "T2_SCOPED_RELEASE_VERIFIED $ref buyer_zip_source=$ZIP_SHA"
