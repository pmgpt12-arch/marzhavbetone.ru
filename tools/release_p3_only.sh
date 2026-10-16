#!/usr/bin/env bash
# Scoped, rollback-capable P3 release in the existing deploy workflow.
set -Eeuo pipefail
: "${HOST:?}" "${USER:?}" "${SITE_PATH:?}" "${PRODUCTS_PATH:?}" "${SSH_PORT:?}"
[[ "${P3_ONLY:-false}" == "true" ]] || { echo 'P3_SCOPE_NOT_ENABLED'; exit 2; }
export RSYNC_RSH="ssh -i $HOME/.ssh/deploy_key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=20 -p $SSH_PORT"
P3_ROOT='products-storage/05-ks-bez-vozvrata'
P3_LIVE="$PRODUCTS_PATH/05-ks-bez-vozvrata"
ZIP='tools/candidates/p3-aosr-form-layout-20261015/P3-11-buyer-AOSR-formatted-20261015.zip'
ZIP_SHA='955e6e0ee686f5f9e03a0dc8141c021db5667e35f195c3886f630555acd2a5b1'
TREE='00aca2f4e4163f39e329f4dd14e5b23a813d448e'
SITE_FILES=(
  articles/proverka-ks-2-pered-sdachey.html
  articles/raboty-ne-prinyaty.html
  diagnostika.html
  download.php
  index.html
  katalog.html
  products/p3-shablony-ks2-ks3.html
  products-config.php
)
ssh_run() { ssh -i "$HOME/.ssh/deploy_key" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=20 -p "$SSH_PORT" "$USER@$HOST" "$@"; }
expect_zip="$(sha256sum "$ZIP" | cut -d ' ' -f1)"
[[ "$expect_zip" == "$ZIP_SHA" ]] || { echo 'P3_ZIP_MISMATCH'; exit 3; }
[[ "$(git rev-parse "HEAD:$P3_ROOT")" == "$TREE" ]] || { echo 'P3_MASTER_TREE_MISMATCH'; exit 3; }
php -l products-config.php >/dev/null
php -r 'define("ORDERS_DIR", sys_get_temp_dir()); require "products-config.php"; exit(mvb_products()["p3"]["price"] === 1790000 ? 0 : 3);'
site_list="$(mktemp)"
prod_checks="$(mktemp)"
site_checks="$(mktemp)"
trap 'rm -f "$site_list" "$prod_checks" "$site_checks"' EXIT
printf '%s\n' "${SITE_FILES[@]}" > "$site_list"
( cd "$P3_ROOT" && sha256sum ./* ) > "$prod_checks"
sha256sum "${SITE_FILES[@]}" > "$site_checks"
if [[ "${DRY_RUN:-false}" == 'true' ]]; then
  echo 'P3_ONLY_DRY_RUN_NO_WRITE'
  rsync -az --dry-run --itemize-changes "$P3_ROOT/" "$USER@$HOST:$P3_LIVE/"
  rsync -az --dry-run --itemize-changes --files-from="$site_list" ./ "$USER@$HOST:$SITE_PATH/"
  echo 'P3_ONLY_DRY_RUN_PASS'
  exit 0
fi
ref="$(git rev-parse --short=12 HEAD)"
backup="$PRODUCTS_PATH/../p3-release-backups/$ref"
ssh_run "set -eu; test -d '$P3_LIVE'; test -f '$SITE_PATH/products-config.php'; test ! -e '$backup'; mkdir -p '$backup/site'; cp -a '$P3_LIVE' '$backup/master'; (cd '$SITE_PATH' && tar -cf - ${SITE_FILES[*]}) | (cd '$backup/site' && tar -xf -)"
rollback() {
  echo 'P3_RELEASE_ROLLBACK_ATTEMPT' >&2
  ssh_run "set -eu; if test -d '$backup/master'; then mkdir -p '$P3_LIVE'; rsync -a --delete '$backup/master/' '$P3_LIVE/'; fi; if test -d '$backup/site'; then (cd '$backup/site' && tar -cf - ${SITE_FILES[*]}) | (cd '$SITE_PATH' && tar -xf -); fi" || echo 'P3_ROLLBACK_MANUAL_RECOVERY_REQUIRED' >&2
}
trap rollback ERR
# Publish masters before changing any public P3 price/checkout surface.
rsync -az --itemize-changes "$P3_ROOT/" "$USER@$HOST:$P3_LIVE/"
ssh_run "cd '$P3_LIVE' && sha256sum -c" < "$prod_checks"
rsync -az --itemize-changes --files-from="$site_list" ./ "$USER@$HOST:$SITE_PATH/"
ssh_run "cd '$SITE_PATH' && sha256sum -c" < "$site_checks"
page="$(curl -fsSL --max-time 20 -H 'Cache-Control: no-cache' -H 'Pragma: no-cache' "https://marzhavbetone.ru/products/p3-shablony-ks2-ks3.html?p3_release=$ref")"
grep -Fq 'data-price="1790000"' <<< "$page" || { echo 'P3_HTTP_PRICE_MISMATCH'; false; }
grep -Fq '17 900' <<< "$page" || { echo 'P3_HTTP_VISIBLE_PRICE_MISMATCH'; false; }
trap - ERR
echo "P3_SCOPED_RELEASE_VERIFIED $ref zip=$ZIP_SHA"
