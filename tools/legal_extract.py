#!/usr/bin/env python3
"""Извлечение нормы из фактического ответа публикатора. Чистые функции.

Отделено от `fetch_legal_evidence.py` намеренно. Сеть из рабочей среды к
официальным публикаторам закрыта (замер 16.08.2026: `pravo.gov.ru` — 403 на
CONNECT, `vsrf.ru` не резолвится), поэтому исправление, проверяемое только
живым прогоном, здесь непроверяемо в принципе. Разбор вынесен в функции без
сети: тело ответа на входе, разобранное на выходе, и на этом стоят тесты.

Три вещи, которых не было в первой версии и из-за которых прогон владельца
16.08.2026 дал 17 отказов подряд.

**Единиц бывает несколько, а бралась последняя.** `article: 196, 200`
разбирался как `split()[-1]` → искалась только статья 200. Норма при этом
опирается на обе, и «доказательство» без 196 доказывало бы половину. То же
на `125, 126` и `128, 148`.

**Постановление Пленума статей не имеет.** У него пункты. Поиск «Статья 84»
в тексте, где написано «84.», не находил ничего и не мог найти.

**Короткое вхождение принималось за норму.** Оглавление публикатора
повторяет заголовки статей, первое вхождение попадает в него, и на выходе
получалась строка «Статья 191. Начало срока» в 25 знаков — с виду успех,
по существу заголовок. Такое доказательство хешируется и выглядит
проверенным. Поэтому берётся не первое вхождение, а самое длинное, и ниже
порога в знаках результат отвергается с названной причиной.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urljoin

# Ниже этого порога вхождение считается заголовком из оглавления, а не
# текстом нормы. Самая короткая норма реестра — ГК 193 (окончание срока в
# нерабочий день), около 180 знаков вместе с заголовком. Порог взят с
# запасом вниз и назван здесь, а не спрятан в условии.
MIN_UNIT_CHARS = 120

# Ответ короче этого — заведомо не текст акта, а карточка документа,
# страница ошибки или заглушка. Отличать их по коду ответа нельзя: карточка
# отдаётся с кодом 200.
MIN_PAGE_CHARS = 500

ARTICLE, POINT = "article", "point"

_NUM = r"\d+(?:\.\d+)*"
_PLENUM = re.compile(r"пленум", re.I)
_ST = re.compile(r"ст(?:ать[яи]|\.)\s*", re.I)
_NOT_FOUND_PAGE = re.compile(
    r"документ не найден|страница не найдена|ничего не найдено"
    r"|доступ (?:запрещ|ограни)|404", re.I)


@dataclass
class Extraction:
    """Разобранное вместе с тем, как оно разобрано. Диагностика — часть ответа."""
    text: str = ""
    kind: str = ARTICLE
    wanted: list[str] = field(default_factory=list)
    found: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    subdivisions: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.text) and not self.missing


def sniff_charset(raw: bytes) -> str:
    """Кодировка из самой страницы, когда заголовок её не назвал.

    Замер 16.08.2026 на семнадцати слепках с машины владельца:
    `pravo.gov.ru` отдаёт `Content-Type: text/html` **без charset**, а сами
    страницы в windows-1251. `get_content_charset()` возвращает None,
    прежний код молча брал utf-8 с `errors="replace"` — и вся кириллица
    превращалась в U+FFFD. Соответствие точное, один байт на один знак
    замены: «от» → 2, «№» → 1, «ФЗ» → 2, «ред» → 3. Слово «Статья» после
    такого декодирования не существует, и найтись не могло ни при какой
    регулярке.

    Метатег ищется в первых килобайтах и по ASCII: до выбора кодировки
    читать страницу как текст нельзя.
    """
    head = raw[:4096].decode("ascii", "ignore").lower()
    m = re.search(r'<meta[^>]+charset=["\']?\s*([\w-]+)', head)
    return m.group(1) if m else ""


def decode_body(raw: bytes, header_charset: str = "") -> tuple[str, str]:
    """(текст, чем декодировано). Порядок: заголовок, метатег, проба.

    `errors="replace"` здесь не применяется ни на одном шаге, кроме
    последнего, и последний называет себя в ответе. Молчаливая порча —
    ровно то, что стоило семнадцати отказов подряд: инструмент сообщал
    «статья не найдена», хотя статья была, а испорчен был алфавит.
    """
    for name in (header_charset, sniff_charset(raw)):
        if not name:
            continue
        try:
            return raw.decode(name), name
        except (LookupError, UnicodeDecodeError):
            continue
    # utf-8 строго — он ломается на однобайтовой кириллице, и это признак,
    # а не помеха: сломался — значит перед нами cp1251.
    try:
        return raw.decode("utf-8"), "utf-8 (проба)"
    except UnicodeDecodeError:
        pass
    return raw.decode("cp1251", "replace"), "cp1251 (проба)"


def looks_damaged(text: str) -> bool:
    """Признак испорченного декодирования: знаки замены при живом ASCII."""
    return text.count("�") > max(20, len(text) // 200)


_IPS_FRAME = re.compile(
    r'<iframe[^>]*\bid=["\']list["\'][^>]*\bsrc=["\']([^"\']+)["\']', re.I)


def ips_document_url(html: str, base_url: str, page: str = "all") -> str:
    """Адрес самого текста акта в оболочке ИПС «Законодательство России».

    Взято из фактического ответа, а не из документации портала. Замер
    16.08.2026 по шести сохранённым страницам: то, что отдаёт
    `?docbody=&nd=<id>`, текстом акта не является — это оболочка со списком
    редакций и поисковой панелью, слова «Статья» в ней ноль раз. Текст
    лежит во фрейме, и адрес фрейма стоит в самой оболочке:

        <iframe id="list" src="?doc_itself=&nd=102033239&page=1&rdk=156">

    Значение `page=all` тоже не выдумано: тем же ответом рядом объявлен
    `?savertf=&nd=...&page=all`, то есть словарь параметров портала его
    знает. Не сработает — вызывающий обходит страницы по одной.
    """
    m = _IPS_FRAME.search(html)
    if not m:
        return ""
    src = m.group(1).replace("&amp;", "&")
    if page:
        src = re.sub(r"(?<=[?&])page=[^&]*", f"page={page}", src)
    return urljoin(base_url, src)


def find_document_links(html: str, base_url: str,
                        terms: list[str]) -> list[str]:
    """Ссылки страницы, чей текст называет искомый документ.

    Нужно там, где официальный адрес ведёт не на акт, а на перечень или
    оболочку. Замер 16.08.2026: `vsrf.ru/documents/own/` — страница списка
    документов (UTF-8, кириллица целая, текста постановления нет), а
    `?nd=102078170` отдаёт 27 740 байт при 598 знаках текста, то есть
    навигацию, а не кодекс.

    Адрес не угадывается: он берётся из фактического ответа официального
    источника по совпадению с реквизитами из реестра. Гадание про
    параметры портала и разбор его ответа — разные вещи.
    """
    if not terms:
        return []
    needles = [t.lower() for t in terms]
    out: list[str] = []
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         html, re.S | re.I):
        href, label = m.group(1), normalize(re.sub(r"<[^>]+>", " ", m.group(2)))
        if not label or href.startswith(("#", "javascript:", "mailto:")):
            continue
        low = label.lower()
        if all(n in low for n in needles):
            out.append(urljoin(base_url, href))
    seen, uniq = set(), []
    for url in out:
        if url not in seen:
            seen.add(url)
            uniq.append(url)
    return uniq[:5]


def normalize(text: str) -> str:
    """NFC, пробелы схлопнуты. Неразрывный пробел — обычный пробел.

    Публикаторы ставят `&nbsp;` внутри «Статья 191» произвольно, и без этой
    замены маркер не находится по причине, которую в выводе не видно.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def strip_html(html: str) -> str:
    html = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", html,
                  flags=re.S | re.I)
    html = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", " ", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    for entity, char in (("&nbsp;", " "), ("&laquo;", "«"), ("&raquo;", "»"),
                         ("&mdash;", "—"), ("&ndash;", "–"), ("&quot;", '"'),
                         ("&#39;", "'"), ("&amp;", "&")):
        html = html.replace(entity, char)
    return normalize(html)


def page_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return normalize(re.sub(r"<[^>]+>", " ", m.group(1)))[:200] if m else ""


def is_plenum(act: str) -> bool:
    return bool(_PLENUM.search(act or ""))


def parse_units(article_field, act: str) -> tuple[str, list[str], list[str]]:
    """Поле `article` реестра → (вид единицы, номера единиц, подразделы).

    Подразделы (часть, пункт внутри статьи) возвращаются отдельно и в поиске
    не участвуют: сохраняется статья целиком. Вырезать из неё часть по
    номеру значило бы разбирать структуру акта регулярным выражением, а
    ошибка там даёт доказательство не той нормы — хуже, чем его отсутствие.
    """
    raw = article_field
    # YAML без кавычек делает из `333.40` число, и номер молча становится
    # `333.4`. Поймано замером 16.08.2026: искалась «Статья 333.4.», которой
    # в НК нет. Кавычки в реестре проставлены, здесь — вторая застава.
    if isinstance(raw, float):
        text = f"{raw:.10f}".rstrip("0").rstrip(".")
    else:
        text = str(raw)

    numbers = re.findall(_NUM, text)
    if is_plenum(act):
        return POINT, numbers, []

    marker = _ST.search(text)
    if marker:
        units = re.findall(_NUM, text[marker.end():])
        subs = re.findall(_NUM, text[: marker.start()])
        return ARTICLE, units, subs
    return ARTICLE, numbers, []


def _slice_candidates(body: str, starts, boundary: re.Pattern) -> list[str]:
    out = []
    for m in starts:
        tail = body[m.start():]
        nxt = boundary.search(tail, m.end() - m.start())
        out.append(tail[: nxt.start()] if nxt else tail[:20000])
    return out


def _best(candidates: list[str]) -> str:
    """Самое длинное вхождение, а не первое.

    Первое почти всегда оглавление: публикаторы печатают перечень
    заголовков перед текстом. Длина здесь — признак того, что за заголовком
    идёт норма.
    """
    return max(candidates, key=len) if candidates else ""


def find_article(body: str, number: str) -> str:
    # `(?!\d)(?!\.\d)` разделяет точку-конец-заголовка и точку внутри
    # номера: «Статья 191.» брать, «Статья 191.1» и «Статья 1911» — нет.
    # Запрет на точку вообще (первая версия правила) отвергал ровно те
    # заголовки, ради которых поиск и написан.
    starts = list(re.finditer(
        rf"Стать[яи]\s+{re.escape(number)}(?!\d)(?!\.\d)\s*[.．]?", body))
    boundary = re.compile(rf"Стать[яи]\s+{_NUM}\s*[.．]")
    return _best(_slice_candidates(body, starts, boundary))


def find_point(body: str, number: str) -> str:
    """Пункт постановления: «42.» с заглавной буквы после точки."""
    starts = list(re.finditer(
        rf"(?<![\d.]){re.escape(number)}\s*[.．]\s+(?=[А-ЯЁ«\"])", body))
    boundary = re.compile(r"(?<![\d.])\d{1,3}\s*[.．]\s+(?=[А-ЯЁ«\"])")
    return _best(_slice_candidates(body, starts, boundary))


def extract(body: str, norm: dict) -> Extraction:
    """Тело ответа + норма реестра → извлечённое с причиной отказа."""
    body = normalize(body)
    kind, wanted, subs = parse_units(norm.get("article", ""), norm.get("act", ""))
    res = Extraction(kind=kind, wanted=wanted, subdivisions=subs)

    if not wanted:
        res.reason = "в реестре не назван номер статьи или пункта"
        return res
    if len(body) < MIN_PAGE_CHARS:
        res.reason = (f"ответ короче {MIN_PAGE_CHARS} знаков ({len(body)}) — "
                      "это не текст акта, а карточка или заглушка")
        return res
    if _NOT_FOUND_PAGE.search(body[:2000]):
        res.reason = "в ответе страница «не найдено» или отказ в доступе"
        return res

    seek = find_point if kind == POINT else find_article
    chunks, short = [], []
    for number in wanted:
        got = seek(body, number).strip()
        if not got:
            res.missing.append(number)
        elif len(got) < MIN_UNIT_CHARS:
            short.append(f"{number} ({len(got)} зн.)")
            res.missing.append(number)
        else:
            res.found.append(number)
            chunks.append(got)

    if res.missing:
        label = "пункт" if kind == POINT else "статья"
        parts = [f"не найдено ({label}): {', '.join(res.missing)}"]
        if short:
            parts.append("только короткие вхождения — это оглавление, а не "
                         f"текст нормы: {', '.join(short)}")
        res.reason = "; ".join(parts)
        return res

    res.text = "\n\n".join(chunks)
    return res
