#!/usr/bin/env python3
"""Показывает, каким разборам нужна обложка, и ловит повтор обложек.

Обложка живёт в трёх местах сразу: страница разбора, список разборов и
материал для Дзена. Пока её нет, статью можно публиковать — но в ленте
Дзена и в превью ссылки она проигрывает соседям, а это первое, что видит
читатель.

    python3 tools/check_covers.py

Код возврата 1, если есть разборы без нормальной обложки или если одна и
та же картинка стоит у нескольких разборов.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
INDEX = ARTICLES / "index.html"
PROMPTS = ROOT / "content" / "covers"

# Заглушку из build_cover.py опознаём по её формату, а не по весу.
# Вес обманывает: 01.08.2026 сгенерированная ночная сцена уложилась в
# 167 КБ — тёмный кадр жмётся, — и проверка объявила её заглушкой, которой
# «не хватает промпта». Ложная тревога в проверке стоит доверия ко всем
# остальным её строкам.
#
# build_cover.py рисует ровно 1200x630 PNG (см. WIDTH, HEIGHT в нём) —
# это og:image по стандарту и ни один прогон генератора такого размера не
# даёт: у него 16:9. Пара «PNG и точно 1200x630» и есть подпись заглушки.
PLACEHOLDER_SIZE = (1200, 630)
# Вес остался вторым признаком, но уже не самостоятельным
PLACEHOLDER_LIMIT_KB = 200
# Ниже этого обложка мылит на ретине. Порог Дзена — 480x320, он ниже,
# поэтому ограничивает нас именно экран, а не площадка
MIN_LONG_SIDE = 1200

# Порог похожести для dHash: расстояние Хэмминга по 64 битам. Ниже —
# кадры считаются подозрительно похожими. Порог намеренно мягкий и ничего
# не блокирует: доля ложных срабатываний не измерена, а проверка, которая
# врёт, перестаёт читаться целиком. Сделать предупреждение блокирующим
# можно только после того, как доля будет известна
NEAR_DUPLICATE_DISTANCE = 10


def article_title(text: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    if not match:
        return "без заголовка"
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", match.group(1))).strip()


def file_hash(path: Path) -> str:
    """Хеш содержимого, а не имени.

    Имя ничего не доказывает: одну и ту же картинку можно положить под
    двумя именами, и по путям такой повтор не виден. Сверяются байты.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def perceptual_hash(path: Path) -> int:
    """dHash 8x8: сравнение соседних пикселей по строке.

    Своими руками, чтобы не тащить зависимость ради одной функции: в
    гейте стоит только pillow. Ловит пережатую, обрезанную или слегка
    перекрашенную копию — то, мимо чего sha256 проходит.
    """
    with Image.open(path) as image:
        small = image.convert("L").resize((9, 8), Image.LANCZOS)
        # tobytes, а не getdata: в режиме «L» это ровно строка яркостей по
        # строкам, и оно не устарело в pillow 14
        pixels = small.tobytes()

    bits = 0
    for row in range(8):
        for col in range(8):
            left = pixels[row * 9 + col]
            right = pixels[row * 9 + col + 1]
            bits = (bits << 1) | int(left > right)
    return bits


def index_covers() -> dict[str, str]:
    """Обложка каждой карточки в списке разборов.

    Список читается отдельно от страниц не для полноты, а по замеру:
    16.08.2026 владелец увидел на боевом сайте три карточки подряд с одной
    картинкой. На самих страницах обложки к тому времени уже были свои —
    расходились именно карточки, а проверка в них не смотрела и молчала.
    Обложка, которую видит читатель в ленте, стоит здесь, а не только в
    статье.
    """
    if not INDEX.is_file():
        return {}

    text = INDEX.read_text(encoding="utf-8", errors="replace")
    covers: dict[str, str] = {}
    pattern = r'<a[^>]+href="([a-z0-9\-]+\.html)"[^>]*>.*?<img[^>]+src="\.\./(assets/[^"]+)"'
    for name, asset in re.findall(pattern, text, re.S):
        covers.setdefault(name, asset)
    return covers


def main() -> int:
    todo: list[tuple[str, str, str]] = []
    ratios: dict[str, list[str]] = {}
    # Кто чью обложку использует. Переиспользованный кадр проходит все
    # проверки ниже — он существует, он тяжёлый, он большой, — и проверка
    # молча зеленеет на статье, у которой своей обложки нет. 01.08.2026
    # так и вышло: восемь новых разборов взяли по одной картинке на
    # кластер, а check_covers отчитался «требуют внимания: 0»
    users: dict[str, list[str]] = {}
    # Разбор → его картинки (страница и карточка в списке). Ключ — хеш
    # содержимого, поэтому повтор виден и под разными именами файлов
    by_hash: dict[str, set[str]] = {}
    assets: dict[str, Path] = {}
    checked = 0

    cards = index_covers()

    for path in sorted(ARTICLES.glob("*.html")):
        if path.name == "index.html":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        title = article_title(text)
        cover = re.search(r'article-cover[^>]*src="\.\./(assets/[^"]+)"', text)

        if not cover:
            todo.append((path.name, title, "обложка не подключена"))
            continue

        asset = ROOT / cover.group(1)
        if not asset.is_file():
            todo.append((path.name, title, f"файл {cover.group(1)} отсутствует"))
            continue

        checked += 1
        size_kb = asset.stat().st_size / 1024
        with Image.open(asset) as image:
            width, height = image.size

        if (width, height) == PLACEHOLDER_SIZE and size_kb < PLACEHOLDER_LIMIT_KB:
            prompt = PROMPTS.glob(f"*{asset.stem[:12]}*")
            has_prompt = any(prompt)
            note = "заглушка из build_cover.py"
            # Запасные промпты лежат здесь, рабочие — в prompts-articles.yaml
            # репозитория ai-business-os, куда этой проверке не дотянуться.
            # Поэтому «ПРОМПТА НЕТ» означает «здесь нет», а не «нигде нет»
            note += ", запасной промпт есть" if has_prompt else (
                ", запасного промпта нет — рабочие в prompts-articles.yaml "
                "репозитория ai-business-os")
            todo.append((asset.name, title, note))
        elif max(width, height) < MIN_LONG_SIDE:
            todo.append((asset.name, title,
                         f"{width}x{height} — мылит на ретине, нужно от "
                         f"{MIN_LONG_SIDE} px по длинной стороне"))

        ratios.setdefault(f"{width}x{height}", []).append(asset.name)
        users.setdefault(asset.name, []).append(title)

        # Считаем и страницу, и карточку: читателю повтор виден в списке,
        # даже когда на самих страницах обложки разные
        for candidate in {cover.group(1), cards.get(path.name)}:
            if not candidate:
                continue
            found = ROOT / candidate
            if not found.is_file():
                todo.append((path.name, title,
                             f"карточка в списке ссылается на {candidate} — файла нет"))
                continue
            digest = file_hash(found)
            by_hash.setdefault(digest, set()).add(path.name)
            assets.setdefault(digest, found)

    if todo:
        print("Нужна обложка:\n")
        for asset_name, title, note in todo:
            print(f"  {title}")
            print(f"      {asset_name} — {note}")
    else:
        print("Все разборы с обложками.")

    # Дефект, а не замечание. До 16.08.2026 повтор печатался «к сведению»,
    # проверка возвращала ноль, и три карточки с одной картинкой доехали
    # до боевого сайта. Строка, которая ничего не роняет, дефект не держит
    repeated = {digest: names for digest, names in by_hash.items() if len(names) > 1}
    if repeated:
        print("\nДЕФЕКТ — одна картинка у нескольких разборов:")
        for digest, names in sorted(repeated.items(), key=lambda item: -len(item[1])):
            print(f"  {assets[digest].name} ({digest[:12]}) — разборов {len(names)}:")
            for name in sorted(names):
                print(f"      {name}")

    shared = {name: titles for name, titles in users.items() if len(titles) > 1}
    if shared and not repeated:
        print("\nК сведению — одна обложка на несколько разборов:")
        for name, titles in sorted(shared.items(), key=lambda item: -len(item[1])):
            print(f"  {name} — {len(titles)}:")
            for title in titles:
                print(f"      {title}")

    # Похожие, но не совпадающие кадры. Не роняет: порог выбран на глаз, а
    # доля ложных срабатываний не измерена. Пока это подсказка живому
    # глазу, а не приговор
    near: list[tuple[int, str, str]] = []
    phashes = {digest: perceptual_hash(path) for digest, path in assets.items()}
    ordered = sorted(phashes)
    for i, left in enumerate(ordered):
        for right in ordered[i + 1:]:
            distance = bin(phashes[left] ^ phashes[right]).count("1")
            if distance <= NEAR_DUPLICATE_DISTANCE:
                near.append((distance, assets[left].name, assets[right].name))
    if near:
        print("\nПРЕДУПРЕЖДЕНИЕ — кадры подозрительно похожи (не блокирует):")
        for distance, left, right in sorted(near):
            print(f"  расстояние {distance}: {left} ~ {right}")

    if len(ratios) > 1:
        # Это замечание, а не задача: пропорция не мешает публикации, но
        # вертикальный кадр в превью ссылки обрезается по центру
        print("\nК сведению — разные пропорции. В превью ссылки вертикальные")
        print("обложки обрезаются по центру и теряют композицию:")
        for size, names in sorted(ratios.items(), key=lambda item: -len(item[1])):
            print(f"  {size}: {len(names)} — {', '.join(sorted(names)[:3])}"
                  + (" и др." if len(names) > 3 else ""))

    print(f"\nРазборов с обложками: {checked}, требуют внимания: {len(todo)}, "
          f"повторов обложек: {len(repeated)}")
    return 1 if todo or repeated else 0


if __name__ == "__main__":
    sys.exit(main())
