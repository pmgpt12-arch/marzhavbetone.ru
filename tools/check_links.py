#!/usr/bin/env python3
"""Битые локальные цели по всему сайту — коротко, для хука и для правки.

Тот же замер, что в `link_audit.py --verify`, но без графа разборов, HTML и
JSON-LD: хуку нужен ответ за секунду и в две строки. Полный разбор связей —
`python3 tools/link_audit.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from link_audit import link_integrity, site_html_files  # noqa: E402


def main() -> int:
    fails = link_integrity()
    if fails:
        print("РАСХОЖДЕНИЕ: ссылки ведут в никуда")
        for f in fails:
            print("  ✗", f)
        return 1
    print(f"Страниц {len(site_html_files())}, битых локальных целей 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
