#!/usr/bin/env python3
"""Размеченные случаи контентного маршрутизатора.

Проверка на пустых базах зеленеет всегда. Здесь у каждого запрета есть
случай, который обязан быть пойман, и парный, который ловиться не должен.

Парные случаи важнее прямых: первая версия проверки разметки объявила
дефектом пятнадцать исправных постов Телеграма, потому что требовала
метку в тексте, а `post_telegram.py` приделывает её при отправке из шапки.

Запуск без pytest: python3 tools/test_content_router.py
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "data" / "content"
TG = ROOT / "content" / "telegram"
TOOL = ROOT / "tools" / "content_router.py"


def run(*args: str) -> tuple[int, str]:
    done = subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, cwd=ROOT)
    return done.returncode, done.stdout + done.stderr


def with_row(name: str, row: dict):
    path = CONTENT / name
    original = path.read_bytes()

    class Ctx:
        def __enter__(self):
            cols = path.read_text(encoding="utf-8").splitlines()[0].split(",")
            with path.open("a", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=cols).writerow(row)

        def __exit__(self, *exc):
            path.write_bytes(original)
    return Ctx()


def hook(**over) -> dict:
    row = {"hook_id": "PROBE-H1", "hook_type": "NUMBER",
           "text": "Мы разобрали 37 споров по дополнительным работам",
           "money_cluster": "MI-3", "evidence_ids": "", "used": "",
           "views": "", "completion_rate": "", "saves": "", "shares": "",
           "profile_visits": "", "site_clicks": "", "performance_status": ""}
    row.update(over)
    return row


def test_baseline_is_clean() -> None:
    code, out = run("--check")
    assert code == 0, f"база уже не чиста:\n{out}"


def test_hook_with_number_needs_evidence() -> None:
    """Крючок с числом без доказательства — блок (§18)."""
    with with_row("hooks.csv", hook()):
        code, out = run("--check")
    assert code == 1 and "без ссылки на доказательство" in out, out


def test_hook_without_number_passes() -> None:
    """Парный случай: крючок-вопрос числа не содержит и проходить обязан."""
    with with_row("hooks.csv", hook(
            hook_type="QUESTION",
            text="Что делать, если генподрядчик подписал КС и перестал платить")):
        code, out = run("--check")
    assert code == 0, f"ложное срабатывание:\n{out}"


def test_unknown_status_is_blocked() -> None:
    row = {"content_id": "PROBE-C1", "source_insight": "", "content_type": "",
           "channel": "telegram", "priority": "", "status": "ГОТОВО",
           "scheduled_date": "", "published_url": "", "campaign": "",
           "target_page": "/articles/raboty-ne-prinyaty.html",
           "target_product": "", "owner": "", "created_at": ""}
    with with_row("publication-queue.csv", row):
        code, out = run("--check")
    assert code == 1 and "неизвестный статус" in out, out


def test_approved_without_target_is_blocked() -> None:
    """Материал без цели: ни страницы, ни комплекта — публиковать некуда."""
    row = {"content_id": "PROBE-C2", "source_insight": "", "content_type": "",
           "channel": "dzen", "priority": "", "status": "APPROVED",
           "scheduled_date": "", "published_url": "", "campaign": "",
           "target_page": "", "target_product": "", "owner": "",
           "created_at": ""}
    with with_row("publication-queue.csv", row):
        code, out = run("--check")
    assert code == 1 and "без цели" in out, out


def test_telegram_front_matter_utm_is_enough() -> None:
    """Метку приделывает отправка — требовать её в тексте нельзя.

    Этим случаем закрыт дефект первой версии проверки: пятнадцать
    исправных постов были объявлены дефектными.
    """
    probe = TG / "_probe.md"
    probe.write_text(
        "---\npublish_at: 2026-01-01 10:00\n"
        "link: https://marzhavbetone.ru/articles/raboty-ne-prinyaty.html\n"
        "utm_campaign: probe\n---\nТекст поста.\n", encoding="utf-8")
    try:
        code, out = run("--check")
    finally:
        probe.unlink(missing_ok=True)
    assert code == 0, f"исправный пост объявлен дефектным:\n{out}"


def test_telegram_without_campaign_is_blocked() -> None:
    probe = TG / "_probe.md"
    probe.write_text(
        "---\npublish_at: 2026-01-01 10:00\n"
        "link: https://marzhavbetone.ru/articles/raboty-ne-prinyaty.html\n"
        "---\nТекст поста.\n", encoding="utf-8")
    try:
        code, out = run("--check")
    finally:
        probe.unlink(missing_ok=True)
    assert code == 1 and "utm_campaign" in out, out


def test_router_prefers_existing_page() -> None:
    """По умолчанию — усилить существующее, а не завести новый адрес."""
    code, out = run("гарантийное удержание не возвращают")
    assert code == 0, out
    assert "UPDATE_EXISTING" in out, out
    assert "garantiynoe-uderzhanie" in out, out


def test_router_says_nothing_to_strengthen() -> None:
    """Незнакомая тема: усиливать нечего, и это говорится прямо."""
    code, out = run("аренда башенного крана посуточно")
    assert code == 0, out
    assert "усиливать нечего" in out, out


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {str(e)[:180]}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
