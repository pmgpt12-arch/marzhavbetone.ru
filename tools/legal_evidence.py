#!/usr/bin/env python3
"""Offline-доказательство нормы: текст статьи, его хеш и происхождение.

Зачем отдельный слой. До P0.1 реестр норм хранил ссылку на публикатора и
слова «цитата получена». Ни то ни другое содержимым не является: адрес
говорит, где смотреть, а не что там написано, и молча меняется вместе с
текстом. Проверить в CI, ту ли редакцию видел проверяющий, было нечем.

Доказательством считается сам нормализованный текст статьи, сохранённый в
репозитории, и его хеш. Тогда «норма изменилась» — это изменение хеша, а
не чьё-то воспоминание, и нормативный результат можно привязать к
конкретной редакции.

Хешируется не только текст, но и метка редакции: смена `edition_marker`
обязана обесценивать результат так же, как смена букв. Иначе одна и та же
статья в двух редакциях дала бы один хеш.

Полных кодексов здесь нет: хранится только та статья или пункт, на
которые опирается документ. Каталог — `data/legal/evidence/<norm_id>.yaml`.

Только стандартная библиотека плюс PyYAML: модуль читает гейт, а он
объявлен набором без сети.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / "data" / "legal" / "evidence"

# Классы источника. Официальным считается только текст, прочитанный у
# официального публикатора; всё остальное полного PASS не даёт.
OFFICIAL = "official"
SECONDARY = "secondary"
NOT_VERIFIED = "not_verified"


def normalize(text: str) -> str:
    """Нормализация до хеширования.

    Пробелы схлопываются, юникод приводится к NFC, края обрезаются. Это
    убирает разницу вёрстки между публикаторами и не трогает содержание:
    перенос строки в норме ничего не меняет, а буква меняет.
    """
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def source_hash(edition_marker: str, text: str) -> str:
    body = f"{(edition_marker or '').strip()}\n{normalize(text)}".encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def path_for(norm_id: str) -> Path:
    return EVIDENCE_DIR / f"{norm_id}.yaml"


def load(norm_id: str) -> dict | None:
    path = path_for(norm_id)
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def verify(norm_id: str) -> tuple[str | None, str]:
    """(хеш, причина отказа). Хеш пересчитывается, а не читается.

    Записанный хеш доказательством себя не является: подменивший текст
    подменил бы и его. Поэтому хеш считается из текста при каждой проверке
    и сверяется с записанным — расхождение означает, что файл правили
    мимо инструмента.
    """
    data = load(norm_id)
    if data is None:
        return None, "offline-доказательства нормы нет"
    text = data.get("text") or ""
    if not text.strip():
        return None, "в доказательстве нет текста нормы"
    actual = source_hash(data.get("edition_marker", ""), text)
    stored = data.get("source_text_hash")
    if actual != stored:
        return None, (f"хеш доказательства пересчитан и не сошёлся "
                      f"({actual[7:19]} против {str(stored)[7:19]}) — "
                      "файл правили мимо инструмента")
    if data.get("source_class") != OFFICIAL:
        return actual, (f"класс источника {data.get('source_class') or 'не объявлен'}"
                        " — полного PASS не даёт")
    return actual, ""


def write(norm_id: str, *, official_url: str, edition_marker: str, text: str,
          source_class: str, retrieved_at: str, retrieved_by: str,
          note: str = "") -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "norm_id": norm_id,
        "official_url": official_url,
        "retrieved_at": retrieved_at,
        "retrieved_by": retrieved_by,
        "edition_marker": edition_marker,
        "source_class": source_class,
        "source_text_hash": source_hash(edition_marker, text),
        "normalization": "NFC, пробелы схлопнуты; в хеш входит edition_marker",
        "note": note,
        "text": normalize(text),
    }
    path = path_for(norm_id)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False,
                       width=88, default_flow_style=False),
        encoding="utf-8")
    return path
