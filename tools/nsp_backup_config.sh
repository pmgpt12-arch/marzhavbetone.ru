#!/bin/sh
# One new private snapshot per invocation; never compare live config to history.
set -eu
case "${1:-}:${2:-}" in *[!0-9:]*|:|*:) echo INVALID_RUN_ID_ATTEMPT >&2; exit 1;; esac
src="$HOME/www/nastoronepodryadchika.ru/config.php"
dir="$HOME/nsp-migration-private/config-snapshots"
historic="$HOME/nsp-migration-private/backup-config-before-yookassa-1502106-20261020.php"
test -f "$src" && test ! -L "$src"
test ! -L "$HOME/nsp-migration-private" && test ! -L "$dir"
umask 077
mkdir -p "$dir"
chmod 700 "$HOME/nsp-migration-private" "$dir"
test "$(stat -c %a "$dir")" = 700
history_before=ABSENT
if test -f "$historic"; then history_before=$(sha256sum "$historic"); fi
source_before=$(sha256sum "$src")
dst=$(mktemp "$dir/config-$(date -u +%Y%m%dT%H%M%SZ)-$1-$2-XXXXXX.php")
trap 'rm -f "$dst"' EXIT HUP INT TERM
cat "$src" > "$dst"
chmod 600 "$dst"
test -s "$dst"
cmp -s "$src" "$dst"
test "$(sha256sum "$src")" = "$source_before"
test "$(stat -c %a "$dst")" = 600
history_after=ABSENT
if test -f "$historic"; then history_after=$(sha256sum "$historic"); fi
test "$history_before" = "$history_after"
trap - EXIT HUP INT TERM
echo CONFIG_BACKUP=VERIFIED
echo CONFIG_BACKUP_UNIQUE="$(basename "$dst")"
echo HISTORICAL_CONFIG_BACKUP=UNCHANGED
echo CONFIG_BACKUP_PERMISSIONS=0700_0600
