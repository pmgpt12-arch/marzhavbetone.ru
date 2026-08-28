#!/usr/bin/env python3
"""Собирает rss.xml из статей в articles/ по требованиям Дзена.

Источник истины — сами страницы статей, поэтому фид не может разойтись
с сайтом. Запуск после добавления или правки статьи:

    python3 tools/build_rss.py

Требования Дзена, которые учитывает генератор:
- обязательные элементы channel: title, link, description, language;
- обязательные элементы item: title, link, guid, pubDate (RFC-822),
  content:encoded с полным текстом;
- namespace content и media;
- обложка не меньше 480x320 (проверяется, при нарушении — ошибка);
- в content:encoded только разрешённая разметка.

Документация: https://dzen.ru/help/ru/export-content/export.html
"""
from __future__ import annotations

import html
import json
import re
import struct
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
DZEN_TITLES = ROOT / "data" / "site" / "dzen-titles.json"
SITE = "https://marzhavbetone.ru"
CHANNEL_TITLE = "Маржа в бетоне"
CHANNEL_DESCRIPTION = (
    "Разборы для строительных подрядчиков: как оформить работы, "
    "защитить допработы и получить оплату."
)
AUTHOR = "Александр Сергеев"
MSK = timezone(timedelta(hours=3))

# Разметка, разрешённая Дзеном внутри content:encoded — список площадки
# дословно: p, a, b, i, u, s, h1-h4, blockquote, ul/li, ol/li, figure, img,
# video (dzen.ru/help/ru/website/rss-modify.html). Наш прежний список был
# написан по памяти и включал strong, em и br, которых там нет.
ALLOWED_TAGS = {
    "p", "a", "b", "i", "u", "s", "h1", "h2", "h3", "h4",
    "blockquote", "ul", "li", "ol", "figure", "img", "video",
}

# Что сайт пишет одним тегом, а Дзен принимает другим. Выкидывать было бы
# потерей смысла: 228 выделений на семнадцать статей — это термины и суммы,
# ради которых абзац и написан.
TAG_SWAP = {"strong": "b", "em": "i"}


# Статьи, опубликованные в Дзене вручную до включения RSS-трансляции.
#
# Дзен привозит из фида всё, чего у него ещё нет, и по одному адресу
# заводит вторую публикацию: накопленные дочитывания и подписчики
# остаются у первой, а показы делятся между двумя. Поэтому исключение
# делается ДО включения трансляции, а не после.
#
# Список снят с экрана Студии 04.08.2026: одиннадцать опубликованных,
# сопоставлены с заготовками content/dzen по заголовку. Репозиторий до
# этого считал девять — счёт вёлся по сверке канала от 27.07 и отстал.
#
# Что заставит пересмотреть: удаление ручной публикации в Студии. Тогда
# статью надо вернуть в фид, иначе она не попадёт в Дзен вовсе.
PUBLISHED_BY_HAND = {
    "genpodryadchik-zarabatyvaet-na-vas",          # материал 01
    "avans-eto-ne-dengi-eto-kryuchok",             # 02
    "bankrotstvo-genpodryadchika-5-markerov",      # 03
    "skidka-15-procentov-na-tendere-eto-otbor-zhertv",  # 04
    "pyat-dokazatelstv-vypolneniya",               # 05
    "podpisannaya-ks2-ne-znachit-chto-zaplatyat",  # 06
    "stroitelnaya-smeta-gde-teryaetsya-marzha",    # 07
    "akt-skrytyh-rabot-obrazec",                   # 08
    "krasnye-flagi-dogovora-subpodryada",          # 09
    "vklyuchenie-v-reestr-trebovaniy-kreditorov",  # 11
    "neotrabotannyy-avans",                        # 15
    "reestr-trebovaniy-kreditorov",                # 10, вышла 05.08
}

# Выпуск по одной в день. Дзен привозит из фида всё, чего у него ещё нет,
# поэтому лента, отданная целиком, даёт залп: семнадцать публикаций разом и
# сломанная калибровка. Решение владельца 05.08.2026 — фид отдаёт только то,
# чему пришёл срок, и растёт на одну статью в сутки.
#
# Даты и порядок — из content/dzen/README.md, чередование денежных узлов.
# Статья без записи здесь попадает в фид сразу: правило про придержанные, а
# не про все.
#
# Чего это стоило, замерено по часам. 05.08 в 21:47 МСК придержание слилось в
# main и срезало фид с восемнадцати материалов до одного. В 21:57 подана
# заявка на разметку ленты — площадка ответила «приняли, проверим за
# несколько дней». 06.08 в 15:02 пришёл отказ: «Содержимое RSS ленты не
# соответствует требованиям Дзена к контенту».
#
# Здесь стояла запись, что порога в десять материалов нет — раз заявку
# приняли при одном. Она неверна дважды. «Приняли» означало «поставили в
# очередь», а не «проверили»; а порог записан у площадки прямо: «При первой
# разметке лента должна содержать минимум 10 материалов»
# (dzen.ru/help/ru/website/rss-modify.html).
#
# Отсюда порядок: до подключения фид держит десять и больше, посуточный
# выпуск идёт хвостом. Темп нужен каналу, а не приёмной комиссии.
RELEASE = {
    # Первые десять открыты одной датой: 06.08.2026 Дзен отказал в разметке
    # ленты, и посуточное придержание — прямая причина отказа. Требование
    # площадки: «При первой разметке лента должна содержать минимум 10
    # материалов» (dzen.ru/help/ru/website/rss-modify.html). Придержание
    # оставило в фиде один материал, его модерация и увидела.
    "vozvrat-avansa-po-dogovoru-podryada": "2026-08-07",
    "garantiynoe-uderzhanie-chto-eto": "2026-08-07",
    "ispolnitelnaya-dokumentaciya-sostav": "2026-08-07",
    "bankovskaya-garantiya-na-vozvrat-avansa": "2026-08-07",
    "protokol-raznoglasiy-k-dogovoru": "2026-08-07",
    "akt-osvidetelstvovaniya-skrytyh-rabot": "2026-08-07",
    "srok-vklyucheniya-v-reestr-trebovaniy-kreditorov": "2026-08-07",
    "stroitelnyy-musor-v-smete": "2026-08-07",
    "dogovor-subpodryada-obrazec": "2026-08-07",
    "vozvrat-garantiynogo-uderzhaniya": "2026-08-07",
    # Остальные семь идут посуточно: темп нужен уже подключённому каналу, а
    # не приёмной комиссии. Цена первых десяти названа — при включении
    # трансляции они приедут одним заходом.
    "zayavlenie-o-vklyuchenii-v-reestr-trebovaniy": "2026-08-08",
    "akt-peredachi-stroitelnoy-ploshchadki-obrazec": "2026-08-09",
    "vsyo-vklyucheno-v-cenu": "2026-08-10",
    "zapros-arbitrazhnomu-upravlyayushchemu": "2026-08-11",
    "srok-garantiynogo-uderzhaniya": "2026-08-12",
    "dopraboty-bez-soglasheniya": "2026-08-13",
    "raboty-ne-prinyaty": "2026-08-14",
}

def meta(source: str, prop: str) -> str | None:
    """Значение og:/name-метатега."""
    pattern = rf'<meta\s+(?:property|name)="{re.escape(prop)}"\s+content="([^"]*)"'
    found = re.search(pattern, source)
    return html.unescape(found.group(1)) if found else None


def image_type(path: Path) -> str:
    """MIME-тип по содержимому файла, а не по расширению: часть обложек
    лежит с расширением .jpg, но фактически является PNG."""
    signature = path.read_bytes()[:8]
    if signature[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if signature[:3] == b"GIF":
        return "image/gif"
    return "image/jpeg"


def image_size(path: Path) -> tuple[int, int] | None:
    """Размер PNG или JPEG без внешних зависимостей."""
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height, width = struct.unpack(">HH", data[i + 5:i + 9])
                return width, height
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            (segment,) = struct.unpack(">H", data[i + 2:i + 4])
            i += 2 + segment
    return None


def strip_tags(fragment: str) -> str:
    return re.sub(r"<[^>]+>", "", fragment).strip()


def table_to_list(fragment: str) -> str:
    """Таблицу — в список: Дзен внутри content:encoded таблиц не принимает.

    Раньше таблица не вырезалась, а просто не попадала в разбор: цикл идёт
    по p, h2, h3, спискам и цитатам, table в этот перечень не входит, и
    текст молча смыкался. В восемнадцати статьях из двадцати девяти это от
    трёх до двадцати одного процента текста, а в разборах формулировок —
    вся суть: колонка «что делает с деньгами» и есть материал.

    Заголовок таблицы становится подписью к каждой строке: «Формулировка —
    что делает: …; что спросить: …». Многословнее таблицы, зато читается
    подряд и на телефоне лучше, чем таблица в семь колонок.
    """
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", fragment, re.S)
    if not rows:
        return ""
    cells = [re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S) for row in rows]
    cells = [[strip_tags(c).strip() for c in row] for row in cells if row]
    if not cells:
        return ""

    head, body = ([], cells) if len(cells) == 1 else (cells[0], cells[1:])
    # Шапкой считаем первую строку, только если она из th
    if "<th" not in rows[0]:
        head, body = [], cells

    items = []
    for row in body:
        if not any(row):
            continue
        first, rest = row[0], row[1:]
        parts = []
        for i, value in enumerate(rest, start=1):
            if not value:
                continue
            label = head[i] if i < len(head) and head[i] else ""
            parts.append(f"{label}: {value}" if label else value)
        tail = "; ".join(parts)
        items.append(f"<li><strong>{first}</strong>{' — ' + tail if tail else ''}</li>")
    return "<ul>" + "".join(items) + "</ul>" if items else ""


def article_body(source: str) -> str:
    """Текст статьи для content:encoded: лид, заголовки, абзацы, списки."""
    main = re.search(r"<main[^>]*>(.*?)</main>", source, re.S)
    if not main:
        return ""
    body = main.group(1)

    # Конец текста — «Читайте также». Рекламные блоки убираются по классу,
    # а не по положению: прежде границей служил блок кнопок, но он есть не у
    # всех статей, и у тех, где его нет, карточка комплекта с ценой уезжала
    # в фид. Замер 04.08.2026: цена стояла в тексте 16 материалов из 18.
    #
    # Классы перечислены поимённо, а не маской: маска однажды съест раздел
    # статьи. Вложенных div внутри этих блоков нет — проверено, поэтому
    # закрывающий тег ищется первый.
    body = body.split('<section class="article-links"')[0]
    for promo in ("article-cta", "article-lead", "article-actions"):
        body = re.sub(rf'<div class="{promo}".*?</div>', "", body, flags=re.S)

    # Короткая врезка товара в первой трети (article_ui.py) — реклама сайта,
    # и в чужой ленте ей делать нечего. Оглавление вырезается ниже вместе со
    # всеми <nav>: его ссылки — якоря страницы сайта, в Дзене они мертвы.
    body = re.sub(r'<aside class="article-cta-inline".*?</aside>', "", body, flags=re.S)

    # Навигация (хлебные крошки) в текст статьи не идёт
    body = re.sub(r"<nav\b.*?</nav>", "", body, flags=re.S)

    # UTM-метки снимаются со ВСЕХ оставшихся ссылок, а не только с тех, что
    # лежат в вырезанных выше блоках. Площадка требует ЧПУ без параметров, а
    # `robots.txt` запрещает `/*?utm_` — помеченная ссылка в фиде и на чужой
    # площадке лишняя, и от индексации закрыта.
    #
    # Появилось не из осторожности: заходом P1-2 вторая ссылка на комплект в
    # статье про состав ИД поставлена простым текстовым переходом с метками,
    # а не блоком `article-cta`. Вырезалка блоков её не видит, и метка доехала
    # до `rss.xml`. Ловится это `tools/check_rss.py`; снимать метки по месту
    # надёжнее, чем помнить про класс обёртки в каждой новой статье.
    def _без_utm(совпадение: re.Match) -> str:
        адрес = совпадение.group(1)
        если_есть = адрес.split("?", 1)
        if len(если_есть) == 1:
            return совпадение.group(0)
        основа, запрос = если_есть
        оставшиеся = [ч for ч in запрос.replace("&amp;", "&").split("&")
                      if ч and not ч.startswith("utm_")]
        хвост = "?" + "&amp;".join(оставшиеся) if оставшиеся else ""
        return f'href="{основа}{хвост}"'

    body = re.sub(r'href="([^"]*)"', _без_utm, body)

    # Таблицы — в списки до разбора по блокам: иначе они не попадут в него
    # вовсе и исчезнут молча
    body = re.sub(r"<table\b.*?</table>", lambda m: table_to_list(m.group(0)),
                  body, flags=re.S)

    blocks: list[str] = []
    pattern = re.compile(
        r"<(p|h2|h3|ul|ol|blockquote)(\s[^>]*)?>(.*?)</\1>", re.S
    )
    for match in pattern.finditer(body):
        tag, attrs, inner = match.group(1), match.group(2) or "", match.group(3)
        # Хлебные крошки, рубрика и дата обновления в текст статьи не идут:
        # дата материала в фиде задаётся полем pubDate, а не строкой в тексте
        if "breadcrumbs" in attrs or "eyebrow" in attrs or "article-date" in attrs:
            continue
        inner = inner.strip()
        if not inner or not strip_tags(inner):
            continue
        # Сначала переводим теги-синонимы в те, что принимает Дзен, потом
        # выкидываем всё, чего в его списке нет. Порядок важен: наоборот
        # strong и em были бы вырезаны раньше, чем заменены.
        inner = re.sub(
            r"<(/?)(strong|em)(\s[^>]*)?>",
            lambda m: f"<{m.group(1)}{TAG_SWAP[m.group(2).lower()]}>",
            inner,
            flags=re.I,
        )
        inner = re.sub(
            r"</?([a-zA-Z0-9]+)([^>]*)>",
            lambda m: m.group(0) if m.group(1).lower() in ALLOWED_TAGS else "",
            inner,
        )
        blocks.append(f"<{tag}>{inner}</{tag}>")
    return "\n".join(blocks)


# Заголовок статьи на сайте и заголовок той же статьи в Дзене решают разные
# задачи, и это не вкусовщина, а замер: «Гарантийное удержание: что это такое
# и сколько оно стоит субподрядчику» написано под запрос «гарантийное
# удержание» 4 917 в месяц, а «Пять процентов, которые вы больше не увидите» —
# под ленту, где заголовок конкурирует за клик, а не за позицию.
#
# Побочно это разводит две наши же страницы по разным запросам: за
# «гарантийное удержание» отвечает статья сайта, она каноническая, а копия в
# Дзене больше не встаёт с ней в один запрос.
#
# ОТКУДА ОНИ БЕРУТСЯ ТЕПЕРЬ. Прежде — из заготовок `content/dzen/*.md`, по
# двум регулярным выражениям поверх текста черновика. Каталог удалён из
# публичного репозитория коммитом a1373b0, и фид на это не упал: функция
# возвращала пустой словарь, а сборка молча уходила на поисковые заголовки.
# Замер 28.08.2026: 17 элементов ленты из 29 несли поисковый заголовок вместо
# написанного под ленту, и ни одна проверка этого не показала.
#
# Отсюда правило: источник объявлен файлом данных, а не выводится из наличия
# каталога. Файла нет — сборка падает, а не деградирует. Восстановление
# значений и разбор — projects/marzha_v_betone/DZEN_RSS_TITLE_CONTRACT_REPORT.md
# в каноне.
#
# Вернуть поисковые заголовки в фид — снять этот флаг. Он остаётся ручкой на
# один случай: Дзен потребует совпадения заголовков. Гейт при этом требует,
# чтобы флаг стоял поднятым, — снятие его перестаёт быть незаметным.
USE_DZEN_TITLES = True


def dzen_titles(файл: Path = DZEN_TITLES,
                статьи: Path | None = None) -> dict[str, str]:
    """slug статьи → заголовок для ленты Дзена из `data/site/dzen-titles.json`.

    Договор жёсткий во все стороны, кроме одной. Ошибка сборки:

      * файла нет или он не читается как JSON;
      * раздел «заголовки» не объект или значения не строки;
      * один slug объявлен дважды (JSON молча оставил бы последний);
      * запись указывает на статью, которой нет в articles/.

    Единственный мягкий случай — статья без записи здесь: она уходит в ленту
    со своим заголовком. Это объявленный откат, он назван в выводе сборки, и
    иначе новая статья не могла бы выйти до того, как ей написан заголовок
    под ленту.
    """
    статьи = ARTICLES if статьи is None else статьи
    if not USE_DZEN_TITLES:
        return {}
    if not файл.is_file():
        # `relative_to` здесь ошибся бы на подставном файле из проверок:
        # он лежит во временном каталоге, а не под корнем репозитория.
        где = файл.relative_to(ROOT) if файл.is_relative_to(ROOT) else файл
        raise SystemExit(
            f"нет файла заголовков Дзена {где}. "
            "Это источник истины для заголовков ленты; без него фид уходит на "
            "поисковые заголовки молча, поэтому сборка остановлена."
        )

    def без_дубликатов(пары: list[tuple[str, object]]) -> dict:
        видел: set[str] = set()
        for ключ, _ in пары:
            if ключ in видел:
                raise SystemExit(
                    f"{файл.name}: slug {ключ} объявлен дважды — JSON оставил "
                    "бы последнее значение, и в ленту ушёл бы заголовок, "
                    "который никто не выбирал"
                )
            видел.add(ключ)
        return dict(пары)

    try:
        данные = json.loads(файл.read_text(encoding="utf-8"),
                            object_pairs_hook=без_дубликатов)
    except json.JSONDecodeError as ошибка:
        raise SystemExit(f"{файл.name}: не читается как JSON — {ошибка}")

    заголовки = данные.get("заголовки")
    if not isinstance(заголовки, dict):
        raise SystemExit(
            f"{файл.name}: нет раздела «заголовки» или он не объект "
            f"(получено {type(заголовки).__name__})"
        )

    битые = [f"{k!r}: {type(v).__name__}" for k, v in заголовки.items()
             if not isinstance(v, str) or not v.strip()]
    if битые:
        raise SystemExit(
            f"{файл.name}: заголовок должен быть непустой строкой — "
            + "; ".join(sorted(битые))
        )

    # Запись на несуществующую статью — почти всегда переименование slug,
    # после которого переопределение потерялось. Молчание здесь стоило бы
    # ровно того же, что стоило удаление каталога: заголовок исчезает, а
    # сборка зелёная.
    потеряны = sorted(s for s in заголовки if not (статьи / f"{s}.html").is_file())
    if потеряны:
        raise SystemExit(
            f"{файл.name}: заголовок объявлен для статьи, которой нет в "
            f"{статьи.name}/ — {', '.join(потеряны)}. Переименован slug или "
            "удалена статья: запись надо поправить или снять."
        )

    return {slug: заголовки[slug].strip() for slug in sorted(заголовки)}


def collect() -> list[dict]:
    items = []
    skipped = []
    held: list[tuple[str, str]] = []
    headlines = dzen_titles()
    adapted: list[str] = []
    fallback: list[str] = []
    today = datetime.now(MSK).date().isoformat()
    for path in sorted(ARTICLES.glob("*.html")):
        if path.name == "index.html":
            continue
        if path.stem in PUBLISHED_BY_HAND:
            skipped.append(path.stem)
            continue
        due = RELEASE.get(path.stem)
        if due and due > today:
            held.append((due, path.stem))
            continue
        source = path.read_text(encoding="utf-8")

        title = meta(source, "og:title") or ""
        title = re.sub(r"\s*—\s*Маржа в бетоне$", "", title)
        if not title:
            found = re.search(r"<title>(.*?)</title>", source, re.S)
            title = html.unescape(found.group(1)) if found else path.stem

        # Заголовок из файла соответствий главнее поискового: он написан
        # под ленту. Нет записи — идёт заголовок сайта, и это объявленный
        # откат: он назван поимённо в конце сборки.
        headline = headlines.get(path.stem)
        if headline and headline != title:
            adapted.append(path.stem)
            title = headline
        elif not headline:
            fallback.append(path.stem)

        published = re.search(r'"datePublished":\s*"([^"]+)"', source)
        if not published:
            raise SystemExit(f"{path.name}: нет datePublished в разметке JSON-LD")
        date = datetime.fromisoformat(published.group(1)).replace(tzinfo=MSK)

        image = meta(source, "og:image") or ""
        image_mime = "image/jpeg"
        if image:
            local = ROOT / image.replace(f"{SITE}/", "")
            if not local.is_file():
                raise SystemExit(f"{path.name}: обложка не найдена — {local}")
            image_mime = image_type(local)
            size = image_size(local)
            if size and (size[0] < 480 or size[1] < 320):
                raise SystemExit(
                    f"{path.name}: обложка {size[0]}x{size[1]} меньше минимума Дзена 480x320"
                )

        eyebrow = re.search(r'<p class="eyebrow">(.*?)</p>', source, re.S)
        category = strip_tags(eyebrow.group(1)).split("/")[0].strip().capitalize() if eyebrow else "Разбор"

        body = article_body(source)
        if len(strip_tags(body)) < 200:
            raise SystemExit(f"{path.name}: слишком короткий текст для фида")

        items.append({
            "title": title,
            "image_type": image_mime,
            "link": f"{SITE}/articles/{path.name}",
            "description": meta(source, "og:description") or "",
            "date": date,
            "image": image,
            "category": category,
            "body": body,
        })

    items.sort(key=lambda item: item["date"], reverse=True)
    # Число называется всегда, включая ноль: молчание здесь читалось бы как
    # «заголовки адаптированы», а означало бы «заготовки не нашлись».
    print(f"заголовок из data/site/dzen-titles.json: {len(adapted)} из {len(items)}")
    if fallback:
        print(f"откат на заголовок статьи ({len(fallback)}): "
              + ", ".join(sorted(fallback)))
    if skipped:
        print(f"исключено как опубликованное вручную: {len(skipped)}")
    if held:
        nearest = min(held)
        print(f"придержано до срока: {len(held)}, ближайшая {nearest[1]} "
              f"выходит {nearest[0]}")
    return items


def build(items: list[dict]) -> str:
    def esc(text: str) -> str:
        return html.escape(text, quote=False)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"',
        # Именно http, а не https: пространство имён — это строка-имя, а не
        # адрес, по которому ходят. Парсер сверяет её посимвольно, и по
        # https-варианту content:encoded для него просто не существует —
        # материал уходит без полного текста. Так в примере площадки.
        '     xmlns:content="http://purl.org/rss/1.0/modules/content/"',
        '     xmlns:media="http://search.yahoo.com/mrss/">',
        "  <channel>",
        f"    <title>{esc(CHANNEL_TITLE)}</title>",
        f"    <link>{SITE}/</link>",
        f"    <description>{esc(CHANNEL_DESCRIPTION)}</description>",
        "    <language>ru</language>",
    ]
    for item in items:
        # Ссылка без параметров. UTM здесь стоял ради атрибуции, но наш же
        # robots.txt запрещает `/*?utm_`: мы звали Дзен туда, куда сами
        # закрыли вход, а площадка требует адреса «без UTM-меток и других
        # параметров». Переходы остаются видны в Метрике по источнику
        # dzen.ru — это грубее, чем метка, и это осознанная потеря.
        cta = (
            f'<p><a href="{SITE}/">Комплекты документов для подрядчиков '
            f"на «Марже в бетоне»</a></p>"
        )
        parts += [
            "    <item>",
            f"      <title>{esc(item['title'])}</title>",
            f"      <link>{item['link']}</link>",
            f"      <guid isPermaLink=\"true\">{item['link']}</guid>",
            f"      <pubDate>{item['date'].strftime('%a, %d %b %Y %H:%M:%S %z')}</pubDate>",
            f"      <author>{esc(AUTHOR)}</author>",
            f"      <category>{esc(item['category'])}</category>",
            f"      <description>{esc(item['description'])}</description>",
        ]
        if item["image"]:
            parts.append(
                f'      <enclosure url="{item["image"]}" type="{item["image_type"]}" />'
            )
            parts.append(f'      <media:content url="{item["image"]}" medium="image" />')
        parts += [
            f"      <content:encoded><![CDATA[{item['body']}\n{cta}]]></content:encoded>",
            "    </item>",
        ]
    parts += ["  </channel>", "</rss>", ""]
    return "\n".join(parts)


def main() -> int:
    items = collect()
    (ROOT / "rss.xml").write_text(build(items), encoding="utf-8")
    print(f"rss.xml собран: {len(items)} материалов")
    if len(items) < 10:
        print(
            f"ВНИМАНИЕ: в фиде {len(items)} материалов при требовании "
            f"площадки в десять на первой разметке. С таким фидом ленту на "
            f"проверку подавать нечего — 06.08.2026 по этой причине отказали."
        )
    for item in items:
        print(f"  {item['date']:%d.%m.%Y}  {item['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
