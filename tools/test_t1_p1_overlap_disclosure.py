#!/usr/bin/env python3
"""Сверяет утверждение о пересечении T1/P1 с текстами фактических DOCX."""
from __future__ import annotations

import difflib
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "products-config.php").read_text(encoding="utf-8")
PAGE = (ROOT / "products/t1-pervyy-shag-pri-neoplate.html").read_text(encoding="utf-8")
SAME_THRESHOLD = 0.95
WORDS = {1: "один", 2: "два", 3: "три", 4: "четыре", 5: "пять"}


def source_dir(sku: str) -> Path:
    match = re.search(r"^\s*'" + sku + r"'\s*=>\s*\[.*?'dir'\s*=>\s*'([^']+)'",
                      CONFIG, re.S | re.M)
    assert match, f"нет каталога {sku} в products-config.php"
    return ROOT / "products-storage" / match.group(1)


def texts(sku: str) -> dict[str, str]:
    result = {}
    for path in sorted(source_dir(sku).glob("*.docx")):
        if path.name.startswith("00-"):
            continue
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("word/document.xml").decode("utf-8", "replace")
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw)).strip()
        if len(text) >= 200:
            result[path.name] = text
    assert result, f"нет DOCX для {sku}"
    return result


def main() -> None:
    t1, p1 = texts("t1"), texts("p1")
    exact = sum(any(difflib.SequenceMatcher(None, a, b).ratio() >= SAME_THRESHOLD
                    for b in p1.values()) for a in t1.values())
    note_match = re.search(r'<p class="overlap-note">(.*?)</p>', PAGE, re.S)
    assert note_match, "нет оговорки T1/P1"
    note = note_match.group(1).lower()
    assert "акты выполненных работ, кс-2 и кс-3" in note
    working = sum(f.suffix.lower() in {".docx", ".xlsx"} and not f.name.startswith("00-")
                  for f in source_dir("t1").iterdir())
    assert f"{working} рабочих" in note or (working == 5 and "пять рабочих" in note)
    if exact == 0:
        assert "дословных повторов нет" in note
        assert "совпадают дословно" not in note
        assert "теми же файлами" not in note
        assert "всё отсюда" not in PAGE.lower()
    else:
        assert WORDS.get(exact, str(exact)) in note, (
            f"T1/P1: {exact} одинаковых DOCX, оговорка не называет их число")
        assert "дословных повторов нет" not in note
    print(f"T1/P1: {len(t1)} против {len(p1)} DOCX, дословно совпало {exact}; оговорка PASS")


if __name__ == "__main__":
    main()
