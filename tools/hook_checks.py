#!/usr/bin/env python3
"""Запускает проверки репозитория после правки файла.

Проверки перечислены в CLAUDE.md, и до сих пор они запускались по памяти —
то есть иногда. Хук делает это без участия человека: правка попала в файл,
относящийся к проверке, — проверка прошла.

На вход подаётся JSON хука из stdin. Скрипт ничего не блокирует: он выводит
результат в поле systemMessage, чтобы расхождение стало видно сразу, а не на
коммите.

    echo '{"tool_input":{"file_path":"products-config.php"}}' | \
        python3 tools/hook_checks.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Какая правка какую проверку запускает. Порядок важен: первая подошедшая
# запись выигрывает, поэтому частные шаблоны стоят выше общих.
ROUTES: list[tuple[tuple[str, ...], str]] = [
    (("products-config.php", "content/strategy/products.csv"), "check_products.py"),
    (("lead.php", "materialy/", "downloads/", "build_free_zips.py",
      "insert_lead_blocks.py"), "check_free_materials.py"),
    (("products-storage/",), "check_packages.py"),
    (("content/reels/",), "check_reel.py"),
    (("articles/", "assets/", "content/covers/"), "check_covers.py"),
    (("articles/", "tools/build_rss.py"), "check_rss.py"),
]

TIMEOUT = 60


def checks_for(path: str) -> list[str]:
    return [script for patterns, script in ROUTES if any(p in path for p in patterns)]


def run(script: str) -> tuple[int, str]:
    try:
        done = subprocess.run(
            [sys.executable, str(ROOT / "tools" / script)],
            capture_output=True, text=True, timeout=TIMEOUT, cwd=ROOT,
        )
    except subprocess.TimeoutExpired:
        return 1, f"{script}: не уложился в {TIMEOUT} с"
    except OSError as exc:
        return 1, f"{script}: не запустился ({exc})"
    return done.returncode, (done.stdout or done.stderr).strip()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_input = payload.get("tool_input") or {}
    response = payload.get("tool_response") or {}
    path = str(response.get("filePath") or tool_input.get("file_path") or "")
    if not path:
        return 0

    failures = []
    for script in checks_for(path):
        code, output = run(script)
        if code != 0:
            failures.append(f"{script}:\n{output}")

    if failures:
        print(json.dumps({
            "systemMessage": "Проверки не прошли:\n\n" + "\n\n".join(failures),
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n\n".join(failures),
            },
        }, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
