#!/usr/bin/env python3
"""Сверяет открытые куски документов с самими документами.

Страница в `demo/` показывает часть платного документа до оплаты. У неё два
свойства, которые ломаются молча и в разные стороны.

Первое: документ пересобирают сборщиком, текст в нём меняется, а страница
остаётся прежней — и открытый кусок начинает показывать то, чего в
покупаемом файле уже нет. Это обещание, которого товар не выполняет.

Второе: кусок разрастается. Каждая отдельная добавка выглядит безобидно, а
вместе они однажды составляют весь документ, и платить становится не за что.
Порог здесь — не вкус: доля считается по знакам и называется числом.

Проверяется только то, что помечено. Блок с атрибутом
`data-verbatim="<путь от products-storage>"` объявлен дословной выдержкой, и
каждый его абзац обязан найтись в этом файле. Всё остальное на странице —
свой текст сайта, и сверять его не с чем.

Запуск: python3 tools/check_demo.py
"""
from __future__ import annotations

import html
import pathlib
import re
import sys

SITE = pathlib.Path(__file__).resolve().parents[1]
DEMO = SITE / "demo"
STORAGE = SITE / "products-storage"

# Доля документа, выше которой открытый кусок перестаёт быть куском. Число
# выбрано так, чтобы вместить вводную часть и один раздел текста: на
# 10.08.2026 претензия отдаёт 38%, и это уже близко к границе
MAX_SHARE = 0.55

BLOCK = re.compile(
    r'<(section|div)[^>]*\sdata-verbatim="([^"]+)"[^>]*>(.*?)</\1>', re.S | re.I)
PARA = re.compile(r"<(p|li)\b[^>]*>(.*?)</\1>", re.S | re.I)


def flat(raw: str) -> str:
    """Текст без разметки и без разницы в пробелах и неразрывных пробелах."""
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw)).replace(" ", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:)\]])", r"\1", text)
    return re.sub(r"([(\[])\s+", r"\1", text).strip()


def document_text(path: pathlib.Path) -> tuple[str, int]:
    """Весь текст документа одной строкой и число знаков в нём."""
    import docx

    paragraphs = [flat(p.text) for p in docx.Document(path).paragraphs]
    kept = [p for p in paragraphs if p]
    return "   ".join(kept), sum(len(p) for p in kept)


def main() -> int:
    if not DEMO.is_dir():
        print("Каталога demo/ нет — открытых кусков не заведено")
        return 0

    pages = sorted(DEMO.glob("*.html"))
    problems = 0
    for page in pages:
        raw = page.read_text(encoding="utf-8")
        blocks = BLOCK.findall(raw)
        if not blocks:
            print(f"{page.name}: ни один кусок не помечен data-verbatim — "
                  "сверять нечего, а страница объявлена выдержкой")
            problems += 1
            continue

        shown: dict[str, int] = {}
        for _, source, body in blocks:
            target = STORAGE / source
            if not target.is_file():
                print(f"{page.name}: {source} — файла нет в products-storage")
                problems += 1
                continue
            whole, size = document_text(target)
            for _, chunk in PARA.findall(body):
                line = flat(chunk)
                if not line:
                    continue
                if line not in whole:
                    print(f"{page.name}: абзац не найден в {source}")
                    print(f"    {line[:120]}")
                    problems += 1
                    continue
                shown[source] = shown.get(source, 0) + len(line)

        for source, size_shown in sorted(shown.items()):
            _, size = document_text(STORAGE / source)
            share = size_shown / size if size else 1.0
            mark = "" if share <= MAX_SHARE else "  ← ВЫШЕ ПОРОГА"
            print(f"{page.name}: {source} — открыто {share:.0%} документа{mark}")
            if share > MAX_SHARE:
                print(f"    порог {MAX_SHARE:.0%}: кусок перестал быть куском")
                problems += 1

    print(f"\nСтраниц с открытыми кусками: {len(pages)}, расхождений: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
