#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
STATE=/home/denis/.local/state/claude-dispatcher/coordinator/2026-10-14-p3-subject-remediation/unit-c-xlsx02-06
finish() {
  rc=$?
  if [[ $rc -ne 0 ]]; then
    printf '{"status":"FAIL_OR_INTERRUPTED","exit_code":%s,"stage":"unit-c-author-acceptance"}\n' "$rc" > "$STATE/failure-receipt.json.tmp"
    sync -f "$STATE/failure-receipt.json.tmp"
    mv "$STATE/failure-receipt.json.tmp" "$STATE/failure-receipt.json"
    sync -f "$STATE"
  fi
  printf '%s\n' "$rc" > "$STATE/acceptance-exit.code.tmp"
  sync -f "$STATE/acceptance-exit.code.tmp"
  mv "$STATE/acceptance-exit.code.tmp" "$STATE/acceptance-exit.code"
  sync -f "$STATE"
}
trap finish EXIT
for name in 02-reestr-prilozheniy.xlsx 06-zhurnal-peredachi.xlsx; do
  if [[ -f "$ROOT/candidate/$name.b64" ]]; then
    base64 -d "$ROOT/candidate/$name.b64" > "$ROOT/candidate/$name.tmp"
    sync -f "$ROOT/candidate/$name.tmp"
    mv "$ROOT/candidate/$name.tmp" "$ROOT/candidate/$name"
    rm "$ROOT/candidate/$name.b64"
  else
    test -s "$ROOT/candidate/$name"
  fi
done
python3 -m py_compile "$ROOT/postprocess_workbooks.py" "$ROOT/verify_candidates.py"
python3 "$ROOT/postprocess_workbooks.py"
rm -rf "$STATE/candidate-recalc" "$STATE/scenario-recalc"
mkdir -p "$STATE/candidate-recalc" "$STATE/scenario-recalc"
for name in 02-reestr-prilozheniy.xlsx 06-zhurnal-peredachi.xlsx; do
  profile=$(mktemp -d /tmp/p3-unitc-candidate-lo-XXXXXX)
  timeout 120s libreoffice --headless "-env:UserInstallation=file://$profile" --convert-to xlsx --outdir "$STATE/candidate-recalc" "$ROOT/candidate/$name"
  rm -rf "$profile"
  test -s "$STATE/candidate-recalc/$name"
  mv "$STATE/candidate-recalc/$name" "$ROOT/candidate/$name"
  sync -f "$ROOT/candidate/$name"
done
for name in 02-scenarios.xlsx 06-scenarios.xlsx; do
  profile=$(mktemp -d /tmp/p3-unitc-scenario-lo-XXXXXX)
  timeout 120s libreoffice --headless "-env:UserInstallation=file://$profile" --convert-to xlsx --outdir "$STATE/scenario-recalc" "$STATE/scenario-fixtures/$name"
  rm -rf "$profile"
  test -s "$STATE/scenario-recalc/$name"
  sync -f "$STATE/scenario-recalc/$name"
done
rm -rf "$ROOT/preview"
mkdir -p "$ROOT/preview"
for name in 02-reestr-prilozheniy.xlsx 06-zhurnal-peredachi.xlsx; do
  profile=$(mktemp -d /tmp/p3-unitc-render-lo-XXXXXX)
  timeout 120s libreoffice --headless "-env:UserInstallation=file://$profile" --convert-to pdf --outdir "$ROOT/preview" "$ROOT/candidate/$name"
  rm -rf "$profile"
  pdf="$ROOT/preview/${name%.xlsx}.pdf"
  test -s "$pdf"
  dir="$ROOT/preview/${name%.xlsx}"
  mkdir -p "$dir"
  timeout 60s pdftoppm -scale-to 1400 -png "$pdf" "$dir/page"
  sync -f "$pdf"
  sync -f "$dir"
done
python3 "$ROOT/verify_candidates.py"
sha256sum "$ROOT"/candidate/*.xlsx "$ROOT"/preview/*.pdf "$ROOT"/author-acceptance.json
sync -f "$ROOT"
