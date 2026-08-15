#!/usr/bin/env python3
"""Абзацы .docx без внешних зависимостей.

Отдельным модулем, потому что читают документы комплектов уже двое:
предпросмотр на странице товара и сборка. Второй разборщик того же
формата рядом с первым — гарантия, что они разойдутся.

Разбор нарочно грубый: .docx это zip с XML, абзац — `<w:p>`, текст —
`<w:t>`. Ни стилей, ни таблиц отсюда не нужно, нужен видимый текст по
абзацам в порядке документа.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

PARA = re.compile(r"<w:p[ >].*?</w:p>", re.S)
TEXT = re.compile(r"<w:t[^>]*>(.*?)</w:t>", re.S)
UNESCAPE = (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
            ("&quot;", '"'), ("&apos;", "'"), ("&#8212;", "—"))


def paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", "replace")
    out = []
    for block in PARA.findall(xml):
        text = "".join(TEXT.findall(block))
        for src, dst in UNESCAPE:
            text = text.replace(src, dst)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(text)
    return out
