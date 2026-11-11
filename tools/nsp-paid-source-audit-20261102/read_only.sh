#!/usr/bin/env bash
set -euo pipefail
base="$HOME/products-marzhavbetone"
site="$HOME/www/nastoronepodryadchika.ru"
for record in 'p8|10-avans-usloviya-i-pribyl|10-avans-usloviya-i-pribyl.zip' 'p13|16-chto-v-smete-ne-oplatyat|16-chto-v-smete-ne-oplatyat.zip'; do
  IFS='|' read -r sku folder zipname <<< "$record"
  dir="$base/$folder"
  echo "BEGIN $sku"
  if [ ! -d "$dir" ]; then
    echo "SOURCE_NOT_FOUND $sku"
  else
    count=0
    while IFS= read -r -d '' f; do
      hash=$(sha256sum "$f" | cut -d' ' -f1)
      bytes=$(wc -c < "$f" | tr -d ' ')
      rel="${f#"$dir"/}"
      printf 'SOURCE\t%s\t%s\t%s\t%s\n' "$sku" "$hash" "$bytes" "$rel"
      count=$((count+1))
    done < <(find "$dir" -type f -print0)
    echo "SOURCE_FILES $sku $count"
  fi
  cache="$site/orders/delivery/$zipname"
  if [ -f "$cache" ]; then
    printf 'CACHE\t%s\t%s\t%s\n' "$sku" "$(sha256sum "$cache" | cut -d' ' -f1)" "$(wc -c < "$cache" | tr -d ' ')"
    if command -v unzip >/dev/null 2>&1; then
      printf 'CACHE_MEMBERS\t%s\t%s\n' "$sku" "$(unzip -Z -1 "$cache" | wc -l | tr -d ' ')"
    fi
  else
    echo "CACHE_ABSENT $sku"
  fi
  echo "END $sku"
done
