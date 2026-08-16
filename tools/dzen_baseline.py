#!/usr/bin/env python3
"""Опорный снимок канала Дзена: сырые данные площадки плюс разбор.

Отдельно от `dzen_channel.py --snapshot` и намеренно. Тот пишет короткий
ряд чисел для наблюдения; этот снимается один раз перед изменением фида и
должен ответить на вопросы, схему ответа под которые никто не проверял:
какие у публикаций адреса, какие даты, пришли ли они залпом.

Поэтому здесь сначала печатается **сырой ответ площадки целиком**, и только
потом разбор. Порядок именно такой: разбор опирается на имена полей, а
имена полей — предположение до первого живого ответа. Сырое остаётся в
логе прогона, и если разбор угадал не те ключи, это будет видно.

Запускается с раннера GitHub: dzen.ru из облачной сессии закрыт
(CONNECT 403, замер 16.08.2026 — в журнале прокси хостом dzen.ru:443).

    python3 tools/dzen_baseline.py            # разбор в stdout
    python3 tools/dzen_baseline.py --out ФАЙЛ # плюс сырой JSON в файл
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dzen_channel
from dzen_channel import CHANNEL, fetch_items, normalize

ROOT = Path(__file__).resolve().parent.parent

# Ключи, под которыми площадки обычно отдают адрес и дату. Ни один не
# подтверждён живым ответом — поэтому берётся первый непустой, а найденное
# имя печатается, чтобы разбор можно было проверить по сырому JSON.
LINK_KEYS = ("link", "url", "share_link", "canonical_url", "publication_url")
DATE_KEYS = ("pubDate", "publication_date", "published_at", "date",
             "modTime", "publicationDate", "addTime")


def first_key(item: dict, keys: tuple[str, ...]) -> tuple[str, str]:
    for key in keys:
        value = item.get(key)
        if value:
            return key, str(value)
    return "", ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Опорный снимок канала Дзена")
    parser.add_argument("--out", metavar="ФАЙЛ", help="куда положить сырой JSON")
    args = parser.parse_args()

    try:
        items = fetch_items()
    except RuntimeError as exc:
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        print(
            "Это «не измерено», а не «в канале пусто». Опорный снимок без "
            "живого ответа площадки не составляется.",
            file=sys.stderr,
        )
        return 1

    meta = dzen_channel.channel_meta()
    print("=" * 72)
    print("КАНАЛ ПО ДАННЫМ САМОЙ ПЛОЩАДКИ")
    print("=" * 72)
    for key, value in meta.items():
        print(f"  {key}: {value}")
    if not meta:
        print("  площадка о канале ничего не сказала")

    print()
    print("=" * 72)
    print(f"СЫРОЙ ОТВЕТ ПЛОЩАДКИ, канал {CHANNEL}, публикаций {len(items)}")
    print("=" * 72)
    print(json.dumps(items, ensure_ascii=False, indent=2))

    if args.out:
        Path(args.out).write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nСырой JSON записан: {args.out}")

    print()
    print("=" * 72)
    print("РАЗБОР")
    print("=" * 72)

    if not items:
        print("Публикаций нет. Разбирать нечего.")
        return 0

    print("\n-- Какие ключи вообще отдаёт площадка (по первой публикации)")
    print("   " + ", ".join(sorted(items[0].keys())))

    link_key, _ = first_key(items[0], LINK_KEYS)
    date_key, _ = first_key(items[0], DATE_KEYS)
    print(f"\n-- Адрес читается из ключа: {link_key or 'НЕ НАЙДЕН'}")
    print(f"-- Дата читается из ключа:  {date_key or 'НЕ НАЙДЕН'}")
    if not link_key or not date_key:
        print("   Ненайденное берётся из сырого JSON выше глазами, а не "
              "угадывается разбором.")

    # 1. Сколько всего.
    print(f"\n[1] ВСЕГО ПУБЛИКАЦИЙ В КАНАЛЕ: {len(items)}")

    # 2-3. Что из ленты, что руками. Ручные двенадцать объявлены списком в
    # сборщике фида; статьи ленты — всё остальное, чему пришёл срок.
    sys.path.insert(0, str(ROOT / "tools"))
    from build_rss import PUBLISHED_BY_HAND

    expected = dzen_channel.expected_from_feed()
    delivered = dzen_channel.delivered_slugs(items, expected)
    print(f"\n[2] ПРИВЕЗЕНО ЛЕНТОЙ: {len(delivered)} из {len(expected)}, "
          "которым срок пришёл")
    for slug in delivered:
        print(f"      + {slug}")
    missing = [s for s in sorted(expected) if s not in delivered]
    print(f"    НЕ ПРИВЕЗЕНО: {len(missing)}")
    for slug in missing:
        print(f"      - {slug}")

    # Ручные опознаются по заголовкам заготовок. Брать их из
    # expected_from_feed() нельзя: оттуда ручные исключены по построению, и
    # счёт всегда выходил бы нулевым — поймано прогоном на подставных
    # данных 16.08.2026. Заголовки берутся из заготовок напрямую.
    from build_rss import dzen_titles

    headlines = dzen_titles()
    channel_norm = [normalize(i.get("title") or "") for i in items]
    manual_found, manual_absent = [], []
    for slug in sorted(PUBLISHED_BY_HAND):
        title = headlines.get(slug)
        if title and normalize(title) in channel_norm:
            manual_found.append((slug, title))
        else:
            manual_absent.append((slug, title or "(заготовки нет)"))
    print(f"\n[3] РУЧНЫХ ОБЪЯВЛЕНО СПИСКОМ: {len(PUBLISHED_BY_HAND)}; "
          f"опознано в канале по заголовку заготовки: {len(manual_found)}")
    for slug, title in manual_found:
        print(f"      + {slug}\n          {title}")
    if manual_absent:
        print(f"    Не опознано: {len(manual_absent)} — заголовок в канале не "
              "совпал с заготовкой.")
        for slug, title in manual_absent:
            print(f"      ? {slug}\n          ожидали: {title}")
    print("    Несовпадение здесь не значит «в канале нет»: двенадцать ушли\n"
          "    руками, и заголовок в Студии могли править. Что именно стоит "
          "в\n    канале — видно в перечне [5-7] ниже.")

    # 4. Дубли: один и тот же заголовок дважды.
    print("\n[4] ДУБЛИ ПО ЗАГОЛОВКУ В КАНАЛЕ")
    repeats = {t: n for t, n in Counter(channel_norm).items() if n > 1}
    if repeats:
        for title, count in repeats.items():
            print(f"      {count}x  {title}")
    else:
        print("      нет — все заголовки в канале различны")

    # 5-7. Заголовок, адрес, дата по каждой публикации.
    print("\n[5-7] ПУБЛИКАЦИИ: заголовок / адрес / дата")
    for number, item in enumerate(items, 1):
        title = item.get("title") or "(без заголовка)"
        _, link = first_key(item, LINK_KEYS)
        _, when = first_key(item, DATE_KEYS)
        print(f"  {number:3}. {title}")
        print(f"       адрес: {link or '—'}")
        print(f"       дата:  {when or '—'}")

    # 8. Залп: сколько публикаций пришлось на каждую дату.
    print("\n[8] РАСПРЕДЕЛЕНИЕ ПО ДАТАМ — пришли ли материалы залпом")
    if not date_key:
        print("    Ключа даты в ответе не нашлось: вопрос решается по сырому "
              "JSON выше, а не этим разбором.")
    else:
        from datetime import datetime, timedelta, timezone

        msk = timezone(timedelta(hours=3))
        days, midnight, odd = Counter(), 0, 0
        stamps = []
        for item in items:
            _, when = first_key(item, DATE_KEYS)
            try:
                moment = datetime.fromtimestamp(int(when), msk)
            except (TypeError, ValueError):
                days[str(when)[:10]] += 1
                continue
            days[moment.strftime("%Y-%m-%d")] += 1
            stamps.append((moment, item.get("title") or ""))
            # Привезённое лентой садится ровно на полночь МСК: время берётся
            # из даты статьи в фиде, а не из момента загрузки. Руками так не
            # попадают — у ручных стоит 19:42, 12:47, 09:14.
            if (moment.hour, moment.minute) == (0, 0):
                midnight += 1
            else:
                odd += 1
        for day, count in sorted(days.items()):
            print(f"      {day}: {count}")
        top = max(days.values()) if days else 0
        print(f"\n    Максимум за одну дату: {top} из {len(items)}.")
        print(f"    Ровно в 00:00 МСК: {midnight} — признак привоза лентой.")
        print(f"    В произвольное время: {odd} — признак ручной публикации.")
        print("    Залпом называлось бы почти всё на одной дате; ряд по дням "
              "значит\n    разнесённый привоз. Вывод — по числам выше, а не "
              "по этой строке.")
        if stamps:
            stamps.sort()
            print(f"\n    Самая ранняя: {stamps[0][0]:%d.%m.%Y %H:%M} МСК — "
                  f"{stamps[0][1][:60]}")
            print(f"    Самая поздняя: {stamps[-1][0]:%d.%m.%Y %H:%M} МСК — "
                  f"{stamps[-1][1][:60]}")

    subscribers = meta.get("subscribers")
    print(f"\n[9] ПОДПИСЧИКИ: {subscribers if subscribers is not None else '—'}")
    print("    Из ответа площадки (source.subscribers), а не с экрана Студии.")
    print("    Здесь стояло «в публичном экспорте их нет» — это было неверно и")
    print("    снято первым живым замером 16.08.2026.")

    # Признак источника прямее, чем время публикации. Материал, привезённый
    # лентой, обычно несёт домен сайта-источника; набранный в редакторе —
    # нет. Печатается разбивкой, а не вердиктом: поле не задокументировано,
    # и совпадёт ли оно с разделением по времени — вопрос замера.
    print("\n[10] ПРИЗНАКИ ИСТОЧНИКА В САМИХ ДАННЫХ")
    for field in ("domain", "domain_title", "item_type", "card_type", "type"):
        spread = Counter(str(item.get(field) or "—") for item in items)
        if len(spread) > 1 or field in ("domain", "domain_title"):
            print(f"    {field}:")
            for value, count in spread.most_common():
                print(f"      {count:3}  {value[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
