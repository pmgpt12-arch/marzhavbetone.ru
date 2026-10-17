#!/usr/bin/env python3
"""Блокирующая проверка запрещённой самооправдательной лексики в новой редакции.

Использование: python3 tools/editorial_business_style_gate.py path/to/buyer.zip [path/to/page.html]
Проверяет DOCX, PDF, XLSX, HTML, TXT, MD; без изменения входных файлов.
Лексическая проверка дополняет, но не заменяет содержательную редакторскую приёмку.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

FORBIDDEN = {
    "зачем_документ": r"зачем\s+(?:этот|данный)\s+документ",
    "зачем_комплект": r"зачем\s+нужен\s+(?:этот|данный)\s+комплект",
    "что_файл_закрывает": r"что\s+этот\s+файл\s+закрывает",
    "чего_комплект_не_делает": r"(?:что|чего)\s+(?:этот|эта|данный|данная)\s+(?:документ|комплект|файл|опись)\s+не\s+делает",
    "продавец_оправдывается": r"не\s+юридическая\s+консультация|не\s+гарантия\s+(?:взыскания|результата)",
    "типовые_шаблоны": r"типовые\s+шаблоны",
    "непроверенное_заявление_о_юристе": r"тексты\s+прошли\s+вычитку\s+юристом",
    "оправдательный_блок": r"важно,\s*прочитайте\s+до\s+использования",
    "самооправдание_через_сравнение": r"это\s+зеркало\s+алгоритма",
    "отсутствие_значений_как_оправдание": r"числа,\s+которых\s+в\s+файле\s+нет\s+намеренно",
    "внутренняя_фраза_ссылки": r"скачивание\s+по\s+ссылке\s+покупателя\s+доступно",
    "до_подписи": r"до\s+подписи",
    "молчание_зафиксировано": r"молчание\s+зафиксировано",
    "правьте_весь_договор": r"правьте\s+весь\s+договор",
    "оправдание_письменных_возражений": r"почему\s+возражать\s+надо\s+письменно",
}
CHECKS = {name: re.compile(pattern, re.I | re.U) for name, pattern in FORBIDDEN.items()}

class HtmlText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.blocked = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self.blocked += 1

    def handle_endtag(self, tag):
        if tag in ("style", "script") and self.blocked:
            self.blocked -= 1

    def handle_data(self, data):
        if not self.blocked:
            self.parts.append(data)

def extract(name: str, data: bytes) -> str:
    lower = name.lower()
    if lower.endswith(".docx"):
        with ZipFile(BytesIO(data)) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        return "\n".join(
            "".join(node.text or "" for node in para.iter(ns + "t"))
            for para in root.iter(ns + "p")
        )
    if lower.endswith(".xlsx"):
        parts = []
        with ZipFile(BytesIO(data)) as archive:
            for path in archive.namelist():
                if path == "xl/sharedStrings.xml" or (
                    path.startswith("xl/worksheets/") and path.endswith(".xml")
                ):
                    root = ET.fromstring(archive.read(path))
                    parts += [
                        element.text or ""
                        for element in root.iter()
                        if element.tag.rsplit("}", 1)[-1] in ("t", "v")
                    ]
        return " ".join(parts)
    if lower.endswith(".pdf"):
        process = subprocess.run(
            ["pdftotext", "-", "-"], input=data,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
        )
        if process.returncode:
            raise RuntimeError(f"PDF text unavailable: {name}")
        return process.stdout.decode("utf-8", "replace")
    if lower.endswith((".html", ".htm")):
        parser = HtmlText()
        parser.feed(data.decode("utf-8", "replace"))
        return " ".join(parser.parts)
    if lower.endswith((".txt", ".md")):
        return data.decode("utf-8", "replace")
    return ""

def check(name: str, data: bytes):
    text = " ".join(extract(name, data).split())
    return [(name, label, match.group(0))
            for label, regex in CHECKS.items()
            for match in regex.finditer(text)]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    failures = []
    files = 0
    for path in args.paths:
        if path.suffix.lower() == ".zip":
            with ZipFile(path) as archive:
                if archive.testzip() is not None:
                    raise RuntimeError(f"Buyer ZIP CRC failed: {path}")
                for member in archive.namelist():
                    failures += check(member, archive.read(member))
                    files += 1
        else:
            failures += check(str(path), path.read_bytes())
            files += 1
    for name, label, text in failures:
        print(f"EDITORIAL_FAIL {name} [{label}] {text}", file=sys.stderr)
    if failures:
        return 1
    print(f"EDITORIAL_PASS files={files} forbidden_occurrences=0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
