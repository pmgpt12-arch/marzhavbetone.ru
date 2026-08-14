#!/usr/bin/env python3
"""Сверяет состав комплектов с тем, что лежит в папках.

MANIFEST.md — это то, что покупатель видит внутри архива. Если там написано
«PDF», а внутри Word, человек считает, что ему прислали не то. Расхождение
возникает молча: манифесты собраны генератором один раз, файлы менялись
отдельно.

Вторая сверка — вложенные пакеты. «Полный комплект» обещает базовые
комплекты целиком, но держит это обещание копией файлов, а не ссылкой.
Копия не отстаёт от оригинала ровно до первой правки любого из шести:
манифест при этом сходится с папкой, потому что папка и правда такая,
какой её описали, — расходятся между собой два места на диске. Поэтому
копия сверяется с оригиналом по содержимому, а не по перечню имён.

Третья сверка — дубликаты внутри одного комплекта. Первые две проходят
зелёными, когда файл лежит в комплекте дважды: с манифестом папка сходится,
копия от оригинала не отстаёт, — а покупатель получает в архиве один и тот
же документ по двум путям. Так и вышло с полным комплектом: файлы 31–40
лежали в корне и внутри вложенного пакета ПТО, побайтово одинаковые, и
страница обещала 96 файлов при 86 документах. Сверяется содержимое: два
разных документа с одинаковым именем — не дубликат, а два одинаковых с
разными именами — дубликат.

Четвёртая — обещанное число против фактического. Число файлов покупатель
читает в двух местах: в манифесте («Покупателю уходит N файлов») и на
странице товара (`<p class="eyebrow">КОМПЛЕКТ P6 / N ФАЙЛОВ</p>`). Оба
писались руками и оба отставали: страница полного комплекта одновременно
держала 78 в шапке и 96 в описании при 86 на диске.

    python3 tools/check_packages.py

Код возврата 1, если комплект расходится с манифестом, вложенная копия
расходится с отдельным комплектом, внутри комплекта есть дубликаты или
обещанное число файлов не совпало с фактическим.
"""
from __future__ import annotations

import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORAGE = ROOT / "products-storage"
CONFIG = ROOT / "products-config.php"
PAGES = ROOT / "products"

# Файлы, которые не попадают в архив покупателю (см. mvb_build_product_zip)
NOT_DELIVERED = {"00-PISMO-POSLE-POKUPKI.txt", ".htaccess"}
# Манифест описывает состав, себя он не описывает
NOT_LISTED = {"MANIFEST.md"}

LISTED = re.compile(r"^\s*[-*]\s*`([^`]+)`", re.M)
# «Покупателю уходит 86 файлов» — объявленное в манифесте число
PROMISED = re.compile(r"Покупателю уходит\s+(\d+)\s+файл")
# sku → папка выдачи в products-config.php
CATALOG = re.compile(
    r"'(?P<sku>[a-z0-9]+)'\s*=>\s*\[\s*'name'\s*=>\s*'(?:[^'\\]|\\.)*'\s*,"
    r"\s*'price'\s*=>\s*\d+\s*,\s*'dir'\s*=>\s*'(?P<dir>[^']+)'",
    re.S,
)
# Шапка страницы товара: «ПОЛНЫЙ КОМПЛЕКТ P6 / 86 ФАЙЛОВ»
EYEBROW = re.compile(r'class="eyebrow"[^>]*>[^<]*?/\s*(\d+)\s*ФАЙЛ[А-Я]*\s*<')
PAGE_SKU = re.compile(r'data-sku="([a-z0-9]+)"')
# Вложенная копия и комплект-источник: `путь/копии/` ← `имя-комплекта`.
# Стрелка нужна там, где имена разошлись: папка ПТО внутри полного комплекта
# называется 06-id-blokiruet-oplatu, а лежит в ней 08-pto-bez-zamechaniy.
# Переименовать её нельзя — это имя уже в выданных покупателям архивах.
SOURCE = re.compile(r"^\s*[-*]\s*`([^`]+/)`\s*←\s*`([^`]+)`", re.M)


def declared(manifest: Path) -> list[str]:
    """Состав комплекта. Другие разделы манифеста могут ссылаться на файлы,
    которых в папке нет намеренно — например перечислять смежные бесплатные
    материалы, — и составом они не являются."""
    text = manifest.read_text(encoding="utf-8")
    section = re.search(r"^## Состав\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return LISTED.findall(section.group(1) if section else "")


def sources(manifest: Path) -> dict[str, str]:
    """Откуда скопирован каждый вложенный пакет.

    Умолчание — комплект того же имени: `.../03-dogovor-podryada/` берётся
    из `03-dogovor-podryada`. Стрелкой объявляются исключения, и объявлены
    они в манифесте, а не в этом файле: состав комплекта решает манифест,
    проверка его только читает.
    """
    text = manifest.read_text(encoding="utf-8")
    section = re.search(r"^## Состав\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return dict(SOURCE.findall(section.group(1) if section else ""))


def delivered(root: Path) -> dict[str, str]:
    """Что покупатель получит из этой папки: путь внутри неё → хэш файла.

    Служебные файлы исключаются на любой глубине — так же, как в
    `mvb_build_product_zip`, где отбор идёт по `basename`. Поэтому
    MANIFEST.md внутри вложенной копии на сверку не влияет: покупатель его
    не видит, и требовать его наличия значило бы сравнивать то, чего
    в архиве нет.
    """
    skip = NOT_DELIVERED | NOT_LISTED
    return {
        item.relative_to(root).as_posix():
            hashlib.sha256(item.read_bytes()).hexdigest()
        for item in root.rglob("*")
        if item.is_file() and item.name not in skip
    }


def catalog() -> dict[str, str]:
    """sku → имя папки выдачи. Пустой словарь, если конфига нет: проверка
    состава папок от каталога не зависит и падать из-за него не должна."""
    if not CONFIG.is_file():
        return {}
    text = CONFIG.read_text(encoding="utf-8")
    return {m.group("sku"): m.group("dir") for m in CATALOG.finditer(text)}


def check_duplicates(package: Path) -> int:
    """Ищет файлы, лежащие в комплекте дважды. Возвращает число повторов.

    Сравнивается содержимое, а не имя: одинаковые имена в разных пакетах —
    норма (`05-sluzhebnaya-zapiska.docx` есть у нескольких), а одинаковое
    содержимое по двум путям покупатель видит как один документ, присланный
    два раза, и считает его дважды в обещанном числе файлов.
    """
    by_hash: dict[str, list[str]] = defaultdict(list)
    for path, digest in delivered(package).items():
        by_hash[digest].append(path)

    repeats = 0
    for paths in sorted(by_hash.values()):
        if len(paths) < 2:
            continue
        repeats += len(paths) - 1
        print(f"ДУБЛИКАТ  {package.name}: один файл по {len(paths)} путям")
        for path in sorted(paths):
            print(f"    {path}")
    return repeats


def check_promised(package: Path, manifest: Path) -> int:
    """Сверяет объявленное в манифесте число файлов с фактическим."""
    found = PROMISED.search(manifest.read_text(encoding="utf-8"))
    if not found:
        return 0                # число объявлено не в каждом манифесте
    promised, actual = int(found.group(1)), len(delivered(package))
    if promised == actual:
        return 0
    print(f"ЧИСЛО В МАНИФЕСТЕ  {package.name}: обещано {promised}, "
          f"на диске {actual}")
    return 1


def check_pages(dirs: dict[str, str]) -> int:
    """Сверяет число файлов в шапке страницы товара с папкой выдачи.

    Страницу и папку правят в разное время и разными руками. Шапка выбрана
    потому, что она единственное место страницы, где число стоит в
    машиночитаемом виде; остальные упоминания — проза, и их сверяет человек,
    когда шапка покраснела.
    """
    if not PAGES.is_dir():
        return 0
    broken = 0
    for page in sorted(PAGES.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        skus = set(PAGE_SKU.findall(text))
        number = EYEBROW.search(text)
        if len(skus) != 1 or not number:
            continue            # страница без кнопки или без шапки со счётом
        sku = skus.pop()
        folder = dirs.get(sku)
        if folder is None:
            print(f"НЕТ SKU  {page.name}: {sku} не найден в products-config.php")
            broken += 1
            continue
        package = STORAGE / folder
        if not package.is_dir():
            print(f"НЕТ ПАПКИ  {page.name}: {folder}")
            broken += 1
            continue
        promised, actual = int(number.group(1)), len(delivered(package))
        if promised == actual:
            continue
        broken += 1
        print(f"ЧИСЛО НА СТРАНИЦЕ  {page.name}: обещано {promised}, "
              f"в {folder} лежит {actual}")
    return broken


def check_copies(package: Path, manifest: Path) -> int:
    """Сверяет вложенные копии базовых пакетов с отдельными комплектами.

    Возвращает число разошедшихся копий. Сравнивается содержимое: файл,
    переписанный в отдельном комплекте и не перенесённый в копию, по именам
    неотличим от целого, а покупатель полного получает старую редакцию.
    """
    broken = 0
    explicit = sources(manifest)
    nested = [name for name in declared(manifest) if name.endswith("/")]
    for name in nested:
        copy = package / name.rstrip("/")
        origin = STORAGE / explicit.get(name, Path(name.rstrip("/")).name)
        if not copy.is_dir():
            continue          # отсутствие папки ловит основная проверка
        if not origin.is_dir():
            print(f"НЕТ ИСТОЧНИКА  {package.name}: {name} ← {origin.name}")
            broken += 1
            continue

        here, there = delivered(copy), delivered(origin)
        missing = sorted(set(there) - set(here))
        extra = sorted(set(here) - set(there))
        changed = sorted(key for key in set(here) & set(there)
                         if here[key] != there[key])
        if not (missing or extra or changed):
            continue

        broken += 1
        print(f"КОПИЯ ОТСТАЛА  {package.name}: {name} ← {origin.name}")
        for item in missing:
            print(f"    {item} — есть в комплекте, нет в копии")
        for item in extra:
            print(f"    {item} — есть в копии, нет в комплекте")
        for item in changed:
            print(f"    {item} — содержимое разное")
    return broken


def main() -> int:
    # __pycache__ появляется рядом со сборками при первом импорте между
    # ними и комплектом не является: 11.08.2026 он дал ложное
    # расхождение «нет манифеста».
    packages = sorted(p for p in STORAGE.iterdir()
                      if p.is_dir() and p.name != "__pycache__")
    if not packages:
        print("Комплектов не найдено", file=sys.stderr)
        return 1

    dirs = catalog()
    broken = 0
    stale = 0
    doubled = 0
    counted = 0
    for package in packages:
        manifest = package / "MANIFEST.md"
        if not manifest.is_file():
            print(f"НЕТ МАНИФЕСТА  {package.name}")
            broken += 1
            continue

        # До проверки состава: комплект может сойтись с манифестом и при этом
        # отставать от оригиналов — это два разных расхождения.
        stale += check_copies(package, manifest)
        doubled += check_duplicates(package)
        counted += check_promised(package, manifest)

        actual = {
            item.name for item in package.iterdir()
            if item.is_file() and item.name not in NOT_DELIVERED | NOT_LISTED
        }
        listed = declared(manifest)

        # Запись со слэшем — вложенный пакет, а не файл: так «Полный комплект»
        # ссылается на базовые. Проверяем существование папки по этому пути
        missing = [
            name for name in listed
            if name.endswith("/")
            and not (package / name.rstrip("/")).is_dir()
        ]
        listed = [name for name in listed if not name.endswith("/")]
        actual -= {name for name in actual if (package / name).is_dir()}

        missing += [name for name in listed if name not in actual]
        extra = sorted(actual - set(listed))

        if not missing and not extra:
            continue

        broken += 1
        print(f"РАСХОЖДЕНИЕ  {package.name}")
        for name in missing:
            # Самый частый случай: в манифесте .pdf, на диске .docx
            stem = Path(name).stem
            near = [item for item in extra if Path(item).stem == stem]
            if near:
                print(f"    {name} → на диске {near[0]}")
            else:
                print(f"    {name} — обещан, но файла нет")
        for name in extra:
            if any(Path(name).stem == Path(item).stem for item in missing):
                continue
            print(f"    {name} — есть на диске, но не описан")

    counted += check_pages(dirs)

    # Папка, на которую не ссылается ни один sku, покупателю не отдаётся
    # никогда: mvb_build_product_zip() ищет папку по имени из конфигурации.
    # Это не расхождение, а вопрос к составу каталога — решение владельца,
    # поэтому строкой к сведению, а не красным.
    if dirs:
        used = set(dirs.values())
        orphans = [p.name for p in packages
                   if p.name not in used and not p.name.startswith("00-free-")]
        if orphans:
            print("\nК сведению — папки, не адресуемые ни одним sku "
                  "(покупателю не отдаются):")
            for name in orphans:
                print(f"  {name}")

    print(f"\nКомплектов: {len(packages)}, с расхождениями: {broken}, "
          f"отставших копий: {stale}, дубликатов внутри комплекта: {doubled}, "
          f"расхождений в числе файлов: {counted}")
    return 1 if broken or stale or doubled or counted else 0


if __name__ == "__main__":
    sys.exit(main())
