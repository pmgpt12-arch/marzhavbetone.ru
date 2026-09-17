#!/usr/bin/env python3
"""Отставшая копия — ошибка там, где копию получает покупатель.

Причина замером (17.09.2026). В `products-storage` лежат две папки, на
которые не ссылается ни один sku: `04-polnyy-komplekt-pto` и
`06-id-blokiruet-oplatu`. Это исторические архивы — то, что уже выдано
покупателям, сохранённое как есть. Отдать их сегодня нечем:
`mvb_build_product_zip()` ищет папку по имени из `products-config.php`, а
там этих имён нет.

После правки актуальных комплектов P3 и P4 вложенные копии внутри
`04-polnyy-komplekt-pto` разошлись с ними, и `check_packages.py` дал код 1
со строками «КОПИЯ ОТСТАЛА». Прибор считал не то: он мерил расхождение на
пути, по которому никто ничего не получает, и требовал переписать архив,
который менять нельзя.

Что проверяется здесь: расхождение вложенной копии внутри неадресуемой
папки не идёт в счёт отставших копий и не даёт кода 1, а точно такое же
расхождение внутри комплекта, адресованного sku, остаётся ошибкой с
ненулевым кодом. Оба случая собираются одним и тем же деревом, отличие —
одна строка в конфигурации каталога.

Запуск без pytest: python3 tools/test_check_packages.py
"""
from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

КАТАЛОГ = """<?php
$MVB_PRODUCTS = [
    'p3' => [ 'name' => 'КС без возврата', 'price' => 1990,
              'dir' => '05-ks-bez-vozvrata' ],
%s];
"""
ПОЛНЫЙ = ("    'p6' => [ 'name' => 'Полный комплект', 'price' => 9900,\n"
          "              'dir' => '04-polnyy-komplekt-pto' ],\n")

МАНИФЕСТ_КОМПЛЕКТА = """# КС без возврата

## Состав

- `01-algoritm.txt`
"""

МАНИФЕСТ_ПОЛНОГО = """# Полный комплект

## Состав

- `01-30-bazovye-pakety/05-ks-bez-vozvrata/`
"""


def модуль(корень: Path):
    """Свежий экземпляр check_packages, смотрящий в подсунутое дерево.

    Пути проверка вычисляет на импорте от своего файла, поэтому копии
    модуля переопределяются константами, а не подменой рабочего каталога:
    так в одном прогоне живут два разных дерева.
    """
    спец = importlib.util.spec_from_file_location(
        f"check_packages_{корень.name}", ROOT / "tools" / "check_packages.py")
    м = importlib.util.module_from_spec(спец)
    спец.loader.exec_module(м)
    м.ROOT = корень
    м.STORAGE = корень / "products-storage"
    м.CONFIG = корень / "products-config.php"
    м.PAGES = корень / "products"        # каталога нет: страницы не сверяются
    return м


def дерево(корень: Path, *, полный_адресован: bool) -> None:
    """Комплект, копия этого комплекта внутри полного, и они разошлись."""
    склад = корень / "products-storage"

    комплект = склад / "05-ks-bez-vozvrata"
    комплект.mkdir(parents=True)
    (комплект / "MANIFEST.md").write_text(МАНИФЕСТ_КОМПЛЕКТА, encoding="utf-8")
    (комплект / "01-algoritm.txt").write_text("редакция 2026-09\n",
                                              encoding="utf-8")

    полный = склад / "04-polnyy-komplekt-pto"
    копия = полный / "01-30-bazovye-pakety" / "05-ks-bez-vozvrata"
    копия.mkdir(parents=True)
    (полный / "MANIFEST.md").write_text(МАНИФЕСТ_ПОЛНОГО, encoding="utf-8")
    (копия / "01-algoritm.txt").write_text("редакция 2026-07\n",
                                           encoding="utf-8")

    (корень / "products-config.php").write_text(
        КАТАЛОГ % (ПОЛНЫЙ if полный_адресован else ""), encoding="utf-8")


def прогон(*, полный_адресован: bool) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        корень = Path(tmp)
        дерево(корень, полный_адресован=полный_адресован)
        вывод = io.StringIO()
        with redirect_stdout(вывод):
            код = модуль(корень).main()
        return код, вывод.getvalue()


def test_расхождение_в_неадресуемой_папке_не_ломает_проверку() -> None:
    код, вывод = прогон(полный_адресован=False)
    assert код == 0, f"неадресуемый архив дал код {код}:\n{вывод}"
    assert "КОПИЯ ОТСТАЛА" not in вывод, вывод
    assert "ИСТОРИЧЕСКИЙ АРХИВ  04-polnyy-komplekt-pto" in вывод, вывод
    assert "не адресуется ни одним sku" in вывод, вывод
    assert "отставших копий: 0" in вывод, вывод
    assert "расхождений в неадресуемых папках (к сведению): 1" in вывод, вывод


def test_расхождение_в_выдаваемом_комплекте_остаётся_ошибкой() -> None:
    код, вывод = прогон(полный_адресован=True)
    assert код == 1, f"отставшая копия у sku дала код {код}:\n{вывод}"
    assert "КОПИЯ ОТСТАЛА  04-polnyy-komplekt-pto" in вывод, вывод
    assert "01-algoritm.txt — содержимое разное" in вывод, вывод
    assert "ИСТОРИЧЕСКИЙ АРХИВ" not in вывод, вывод
    assert "отставших копий: 1" in вывод, вывод
    assert "расхождений в неадресуемых папках (к сведению): 0" in вывод, вывод


def main() -> int:
    провал = 0
    for имя, проверка in sorted(globals().items()):
        if not имя.startswith("test_"):
            continue
        try:
            проверка()
        except AssertionError as ошибка:
            провал += 1
            print(f"ПРОВАЛ  {имя}\n{ошибка}")
        else:
            print(f"ок  {имя}")
    return 1 if провал else 0


if __name__ == "__main__":
    sys.exit(main())
