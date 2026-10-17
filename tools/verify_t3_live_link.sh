#!/usr/bin/env bash
# Scoped production HTTP probe for a synthetic T3 order; no payment or email.
set -Eeuo pipefail
: "${HOST:?}" "${USER:?}" "${SITE_PATH:?}" "${SSH_PORT:?}"
export RSYNC_RSH="ssh -i $HOME/.ssh/deploy_key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts -o ConnectTimeout=20 -p $SSH_PORT"
ssh_run() { ssh -i "$HOME/.ssh/deploy_key" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$HOME/.ssh/known_hosts" -o ConnectTimeout=20 -p "$SSH_PORT" "$USER@$HOST" "$@"; }
id=''; tmp="$(mktemp)"
cleanup() {
  rm -f "$tmp"
  if [[ "$id" =~ ^order_[0-9_]+_t3probe[a-f0-9]+$ ]]; then
    ssh_run "bash -se -- '$SITE_PATH' '$id'" <<'CLEAN' >/dev/null || echo 'T3_PROBE_CLEANUP_FAILED' >&2
set -eu
site_arg="$1"; id="$2"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
site="$(cd "$site" && pwd -P)"
case "$id" in order_*_t3probe*) rm -f "$site/orders/$id.json" "$site/orders/$id.json.lock";; *) exit 2;; esac
CLEAN
  fi
}
trap cleanup EXIT
result="$(ssh_run "bash -se -- '$SITE_PATH'" <<'CREATE'
set -Eeuo pipefail
umask 077
site_arg="$1"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
site="$(cd "$site" && pwd -P)"
php -r '
require $argv[1]."/config.php";
require $argv[1]."/products-config.php";
$id="order_".date("Ymd_His")."_t3probe".bin2hex(random_bytes(5));
$order=["id"=>$id,"status"=>"paid","email"=>"","items"=>[["sku"=>"t3"]],"total"=>1490000];
$result=mvb_prepare_delivery($order);
if(count($result["links"])!==1 || $result["links"][0]["sku"]!=="t3")exit(3);
$delta=strtotime($order["delivery"]["expires_at"])-time();
$file=ORDERS_DIR."/".$id.".json";
if(file_exists($file) || file_put_contents($file,json_encode($order,JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT))===false)exit(4);
chmod($file,0600);
echo $id."|".$order["delivery"]["token"]."|".$delta;
' "$site"
CREATE
)"
IFS='|' read -r id token ttl <<< "$result"
[[ "$id" =~ ^order_[0-9_]+_t3probe[a-f0-9]+$ && "$token" =~ ^[a-f0-9]{32}$ && "$ttl" -ge 3598 && "$ttl" -le 3600 ]] || { echo 'T3_LINK_PROBE_BAD_CREATION'; exit 5; }
url="https://marzhavbetone.ru/download.php?o=$id&t=$token&f=t3"
code="$(curl -sS -L --max-time 30 -o "$tmp" -w '%{http_code}' "$url")"
[[ "$code" == '200' ]] || { echo "T3_LINK_PROBE_HTTP_$code"; exit 6; }
got="$(sha256sum "$tmp" | cut -d ' ' -f1)"
[[ "$got" == '1f2b09c4e060e4e7310fd8d1f48461282b99fad7793b6acb3bc3267f2d69d2fb' ]] || { echo 'T3_LINK_PROBE_ZIP_MISMATCH'; exit 7; }
ssh_run "bash -se -- '$SITE_PATH' '$id'" <<'EXPIRE'
set -Eeuo pipefail
site_arg="$1"; id="$2"
case "$site_arg" in /*) site="$site_arg";; *) site="$HOME/$site_arg";; esac
site="$(cd "$site" && pwd -P)"
php -r '
$file=$argv[1]."/orders/".$argv[2].".json";
$order=json_decode(file_get_contents($file),true,512,JSON_THROW_ON_ERROR);
$order["delivery"]["expires_at"]=date("c",time()-1);
file_put_contents($file,json_encode($order,JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT));
' "$site" "$id"
EXPIRE
expired="$(curl -sS -L --max-time 20 -o /dev/null -w '%{http_code}' "$url")"
[[ "$expired" == '410' ]] || { echo "T3_LINK_PROBE_EXPIRED_HTTP_$expired"; exit 8; }
echo "T3_PRODUCTION_LINK_PASS ttl_seconds=$ttl active_http=200 active_zip_sha=$got expired_http=410 synthetic_order_cleanup=armed"
