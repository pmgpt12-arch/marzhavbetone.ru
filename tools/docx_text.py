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
import xml.etree.ElementTree as ET
from pathlib import Path

PARA = re.compile(r"<w:p[ >].*?</w:p>", re.S)
TEXT = re.compile(r"<w:t[^>]*>(.*?)</w:t>", re.S)
UNESCAPE = (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
            ("&quot;", '"'), ("&apos;", "'"), ("&#8212;", "—"))


def paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", "replace")
    # Match namespace-qualified elements, not tag prefixes: the old <w:t[^>]*>
    # also matched <w:top .../> and swallowed paragraph properties as text.
    ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    out = []
    for block in ET.fromstring(xml).iter(ns + 'p'):
        text = ''.join(node.text or '' for node in block.iter(ns + 't'))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(text)
    return out
