#!/usr/bin/env python3
"""Сверяет, что один документ во всех папках выдачи лежит одной редакцией.

Дефект, ради которого написана проверка, случился 11.08.2026 и стоил денег
покупателя. Комплект «Ответ на претензию» разделили на два товара; папку
нового товара собрали копированием с витрины — то есть взяли ту редакцию,
что лежала на витрине, а не ту, что прошла нормативную сверку. Файлы 34 и 39
с формулировками, снятыми сверкой как расходящиеся с нормой, стали
продаваться в двух товарах вместо одного, включая комплект за 9 900 ₽.

Обнаружилось это случайно, при разведении конфликта слияния. Ни одна из семи
проверок сайта такого не ловит: `check_packages` смотрит, что файл на месте,
`check_products` — что витрина совпадает с конфигом. Что внутри файла — не
смотрит никто.

Правило простое: **файл с одним именем в двух папках выдачи обязан быть
одним файлом**. У правила есть законные исключения — у каждого комплекта
своя инструкция, свой словарь полей, а бесплатный образец нарочно короче
платного. Каждое исключение объявлено ниже вместе с причиной; необъявленное
расхождение — дефект.

Сверяются байты целиком, а не текст: правка стиля в документе меняет
`word/document.xml`, и это тоже разные редакции одного товара.

Запуск: python3 tools/check_editions.py
"""
from __future__ import annotations

import collections
import hashlib
import pathlib
import sys

SITE = pathlib.Path(__file__).resolve().parents[1]
STORAGE = SITE / "products-storage"
SUFFIXES = {".docx", ".xlsx", ".pdf"}

# Имена, у которых расхождение законно, и причина по каждому. Причина — не
# формальность: она и есть то, что отличает исключение от незамеченного
# дефекта. Имя без причины сюда не добавляется.
EXPECTED_TO_DIFFER = {
    "00-INSTRUKCIYA.docx":
        "инструкция пишется под свой комплект и называет его состав",
    "00-INSTRUKCIYA.pdf":
        "то же, в PDF",
    "01-slovar-poley.docx":
        "словарь описывает поля своего комплекта: у неоплаты и у передачи ИД "
        "наборы полей разные",
    "01-proverochnyy-list-komplekta-ks.docx":
        "бесплатный образец нарочно короче платного",
    "02-reestr-prilozheniy.xlsx":
        "то же: бесплатный образец короче платного",
    "10-sravnitelnaya-tablica.docx":
        "таблица сравнивает документы своего кластера — у «КС без возврата» и "
        "у «ИД блокирует оплату» сравнивается разное",
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def main() -> int:
    if not STORAGE.is_dir():
        print("Каталога products-storage нет — сверять нечего")
        return 0

    by_name: dict[str, list[pathlib.Path]] = collections.defaultdict(list)
    for path in STORAGE.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUFFIXES:
            by_name[path.name].append(path)

    shared = {n: p for n, p in by_name.items() if len(p) > 1}
    problems = 0
    explained = 0

    for name, paths in sorted(shared.items()):
        groups: dict[str, list[pathlib.Path]] = collections.defaultdict(list)
        for path in paths:
            groups[digest(path)].append(path)
        if len(groups) == 1:
            continue

        reason = EXPECTED_TO_DIFFER.get(name)
        if reason:
            explained += 1
            print(f"{name}: {len(groups)} редакции — объявлено, {reason}")
            continue

        problems += 1
        print(f"{name}: РАСХОЖДЕНИЕ, {len(groups)} редакции в {len(paths)} папках")
        for code, where in sorted(groups.items()):
            for path in sorted(where):
                print(f"    {code}  {path.relative_to(SITE)}")
        print("    один документ продаётся в двух редакциях: либо выровнять "
              "файлы, либо объявить исключение с причиной в EXPECTED_TO_DIFFER")

    stale = sorted(set(EXPECTED_TO_DIFFER) - set(shared))
    for name in stale:
        problems += 1
        print(f"{name}: объявлено исключением, но такого файла в двух папках "
              "больше нет — строку надо снять")

    print(f"\nИмён в двух и более папках: {len(shared)}, "
          f"объявленных расхождений: {explained}, дефектов: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
