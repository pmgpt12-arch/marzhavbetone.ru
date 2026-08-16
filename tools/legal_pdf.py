#!/usr/bin/env python3
"""Текстовый слой PDF без внешних зависимостей.

Зачем свой разбор, а не библиотека. Официальный ответ Верховного Суда по
адресу `/documents/own/8478/` — PDF, а не HTML, и опознавать его как
разметку нельзя: identity-проверка честно докладывала «по адресу лежит
другой документ», хотя документ был верный. Значит нужен путь для PDF.

`pypdf` ставится, но в рабочей среде не импортируется: он тянет
`cryptography`, а тот падает `pyo3_runtime.PanicException`. Библиотека,
которую нельзя прогнать здесь, в доказательном контуре хуже своего кода —
её путь остался бы непроверенным, а «не запускалась» это не «прошла».
`zlib` в стандартной библиотеке есть, и этого достаточно.

Что разбирается: несжатые и `FlateDecode`-потоки, текстовые операторы
`Tj`, `TJ`, `'`, `"`, кодовые таблицы `ToUnicode` (`bfchar`, `bfrange`).
Чего нет и не будет: OCR. PDF без текстового слоя честно отдаёт пусто, и
доказательством не становится — распознавание картинки это уже толкование,
а не цитата.

Ограничение названо прямо: разбор проверен на собранных здесь PDF двух
устройств — простой шрифт с однобайтовой кодировкой и составной шрифт с
`ToUnicode`. Настоящего ответа ВС в репозитории пока нет, и на нём разбор
не прогонялся.
"""
from __future__ import annotations

import re
import zlib

TEXT_OPS = re.compile(rb"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]+>")
_BFCHAR = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
_BFRANGE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)
_HEX = re.compile(rb"<([0-9A-Fa-f\s]+)>")


def is_pdf(raw: bytes) -> bool:
    return raw[:5] == b"%PDF-"


def _streams(raw: bytes) -> list[bytes]:
    """Все потоки документа, по возможности распакованные."""
    out = []
    for m in re.finditer(rb"stream\r?\n", raw):
        end = raw.find(b"endstream", m.end())
        if end < 0:
            continue
        chunk = raw[m.end():end].rstrip(b"\r\n")
        try:
            out.append(zlib.decompress(chunk))
        except zlib.error:
            out.append(chunk)
    return out


def _hex_codes(blob: bytes) -> list[int]:
    digits = re.sub(rb"\s+", b"", blob)
    if len(digits) % 2:
        digits = digits[:-1]
    step = 4 if len(digits) % 4 == 0 and len(digits) >= 4 else 2
    return [int(digits[i:i + step], 16) for i in range(0, len(digits), step)]


def _utf16(blob: bytes) -> str:
    digits = re.sub(rb"\s+", b"", blob)
    try:
        return bytes.fromhex(digits.decode("ascii")).decode("utf-16-be", "ignore")
    except ValueError:
        return ""


def to_unicode_map(streams: list[bytes]) -> dict[int, str]:
    """Кодовые таблицы всех шрифтов, слитые в одну.

    Слияние огрубляет: у разных шрифтов один код может значить разные
    буквы. Для документа с одним основным шрифтом — а нормативные акты
    такие — это верно, и цена ошибки видна сразу: текст выйдет
    нечитаемым, а не тихо неверным.
    """
    cmap: dict[int, str] = {}
    for data in streams:
        for block in _BFCHAR.findall(data):
            pairs = _HEX.findall(block)
            for src, dst in zip(pairs[::2], pairs[1::2]):
                codes = _hex_codes(src)
                if codes:
                    cmap[codes[0]] = _utf16(dst)
        for block in _BFRANGE.findall(data):
            for lo, hi, dst in re.findall(
                    rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
                    block):
                start, stop = int(lo, 16), int(hi, 16)
                base = _utf16(dst)
                if not base or stop - start > 65535:
                    continue
                for offset in range(stop - start + 1):
                    cmap[start + offset] = chr(ord(base[0]) + offset) + base[1:]
    return cmap


def _literal(blob: bytes) -> bytes:
    body = blob[1:-1]
    body = re.sub(rb"\\([nrtbf])",
                  lambda m: {b"n": b"\n", b"r": b"\r", b"t": b"\t",
                             b"b": b"\b", b"f": b"\f"}[m.group(1)], body)
    body = re.sub(rb"\\([0-7]{1,3})",
                  lambda m: bytes([int(m.group(1), 8) & 0xFF]), body)
    return re.sub(rb"\\(.)", rb"\1", body)


def _decode(raw_bytes: bytes, cmap: dict[int, str]) -> str:
    if cmap:
        wide = "".join(cmap.get(int.from_bytes(raw_bytes[i:i + 2], "big"), "")
                       for i in range(0, len(raw_bytes) - 1, 2))
        if wide.strip():
            return wide
        narrow = "".join(cmap.get(b, "") for b in raw_bytes)
        if narrow.strip():
            return narrow
    # Простой шрифт без таблицы: кириллица в таких PDF лежит однобайтовой.
    text = raw_bytes.decode("cp1251", "replace")
    return text if text.count("�") <= len(text) // 10 else \
        raw_bytes.decode("latin-1", "replace")


def pdf_text(raw: bytes) -> str:
    """Весь текстовый слой документа одной строкой.

    Порядок операторов сохраняется, разделителем ставится пробел: для
    поиска статьи или пункта разбиение на строки значения не имеет, а
    склейка слов без пробела ломала бы его.
    """
    if not is_pdf(raw):
        return ""
    streams = _streams(raw)
    cmap = to_unicode_map(streams)
    parts = []
    for data in streams:
        if b"Tj" not in data and b"TJ" not in data:
            continue
        for m in TEXT_OPS.finditer(data):
            token = m.group(0)
            if token.startswith(b"<"):
                codes = _hex_codes(token[1:-1])
                parts.append("".join(cmap.get(c, "") for c in codes)
                             if cmap else "")
            else:
                parts.append(_decode(_literal(token), cmap))
    return re.sub(r"\s+", " ", " ".join(parts)).strip()
