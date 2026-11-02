#!/usr/bin/env bash
set -euo pipefail
run_id="$1"
site="$2"
stage="$HOME/.nsp-free11-stage-$run_id"
backup="$HOME/.nsp-free11-backup-$run_id"
target="$HOME/$site/downloads"
test -d "$target" && test -f "$stage/expected.tsv"
test ! -e "$backup"
mkdir -m 700 "$backup"
rollback_needed=0
rollback() {
  if [ "$rollback_needed" = 1 ]; then
    while read -r name old new; do
      test -f "$backup/$name" && cp -p "$backup/$name" "$target/$name.nsp-rollback" && mv -f "$target/$name.nsp-rollback" "$target/$name"
    done < "$stage/expected.tsv"
  fi
}
trap rollback ERR
while read -r name old new; do
  test -f "$stage/$name" && test -f "$target/$name"
  test "$(sha256sum "$target/$name" | cut -d' ' -f1)" = "$old" || { echo "BASELINE_DRIFT:$name"; exit 3; }
  test "$(sha256sum "$stage/$name" | cut -d' ' -f1)" = "$new" || { echo "CANDIDATE_DRIFT:$name"; exit 4; }
done < "$stage/expected.tsv"
while read -r name old new; do cp -p "$target/$name" "$backup/$name"; done < "$stage/expected.tsv"
rollback_needed=1
while read -r name old new; do
  cp -p "$stage/$name" "$target/$name.nsp-new"
  mv -f "$target/$name.nsp-new" "$target/$name"
  test "$(sha256sum "$target/$name" | cut -d' ' -f1)" = "$new"
done < "$stage/expected.tsv"
rollback_needed=0
trap - ERR
echo "FREE11_ATOMIC_REPLACE_PASS"
while read -r name old new; do sha256sum "$target/$name"; done < "$stage/expected.tsv"
echo "BACKUP_DIR=$backup"
