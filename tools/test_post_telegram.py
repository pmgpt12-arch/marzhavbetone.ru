#!/usr/bin/env python3
"""Разметка ссылки при отправке поста в Telegram.

Проверяется то, из-за чего переход из канала перестаёт считаться: ссылка
собирается на отправке, в тексте поста её нет, и увидеть ошибку глазами
нельзя — только прогоном.

Стандарт меток закреплён в data/content/rules.yaml: source telegram,
medium post, campaign — слаг темы, content необязателен. Второго формата
быть не должно: 46-52 уже ушли в канал с medium=post, и смена medium
разорвала бы ряд отчётности пополам.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from post_telegram import parse_post  # noqa: E402

HEADER = """---
publish_at: 2026-09-15 10:00
link: https://marzhavbetone.ru/articles/nekotoraya-statya.html
{extra}---
<b>Заголовок</b>

Текст поста. {{link}}
"""

failures = []


def check(name: str, ok: bool, detail: str) -> None:
    print(f"{'OK  ' if ok else 'ДЕФЕКТ'} {name}\n       {detail}")
    if not ok:
        failures.append(name)


def render(extra: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "2026-09-15-proba.md"
        path.write_text(HEADER.format(extra=extra), encoding="utf-8")
        return parse_post(path)["text"]


text = render("utm_campaign: nekotoraya-statya\n")
check("метка канала стоит на ссылке",
      "utm_source=telegram&utm_medium=post&utm_campaign=nekotoraya-statya" in text,
      text.splitlines()[-1])

check("medium остался post, а не подменён",
      "utm_medium=organic" not in text and "utm_medium=post" in text,
      "ряд 46-52 размечен medium=post, второй формат развёл бы отчётность")

text = render("utm_campaign: nekotoraya-statya\nutm_content: msg-53-anons\n")
check("utm_content из шапки доезжает до ссылки",
      "utm_content=msg-53-anons" in text,
      text.splitlines()[-1])

text = render("utm_campaign: nekotoraya-statya\n")
check("без utm_content в шапке параметра нет",
      "utm_content" not in text,
      "необязательный параметр не выдумывается за автора поста")

# Уже опубликованные: разметка держится шапкой, и пустая шапка молча
# отправила бы ссылку без меток — такой переход не считается вовсе.
posts_dir = Path(__file__).resolve().parent.parent / "content" / "telegram"
unmarked = []
for path in sorted(posts_dir.glob("*.md")):
    if path.name.upper().startswith("README"):
        continue
    head = path.read_text(encoding="utf-8", errors="replace")[:600]
    if "marzhavbetone.ru" in head and "utm_campaign:" not in head:
        unmarked.append(path.name)
check("у каждого поста с ссылкой на сайт есть utm_campaign",
      not unmarked, f"без метки: {unmarked or 'нет'}")

print()
if failures:
    print(f"ДЕФЕКТОВ — {len(failures)}: {', '.join(failures)}")
    sys.exit(1)
print("Разметка ссылок Telegram: расхождений нет.")
