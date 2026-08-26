#!/usr/bin/env python3
"""Снимок таксономии на сайте: сторож против четвёртой таксономии.

ЗАЧЕМ ЭТОТ ФАЙЛ ЗДЕСЬ, ЕСЛИ ТАКОЙ ЖЕ ЕСТЬ В BUSINESS OS. Расхождение ловится
с обеих сторон. Со стороны канона — что снимок пересобран; здесь — что сайт
не завёл своего соответствия мимо снимка. Второе первым не проверяется:
`lead.php` живёт в этом репозитории, и канон о нём ничего не знает.

Запуск: python3 tools/test_taxonomy_snapshot.py
Код возврата 1 — расхождение.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
СНИМОК = ROOT / "taxonomy" / "pains.generated.json"
LEAD = ROOT / "lead.php"
МАТЕРИАЛЫ = ROOT / "materialy"

# Версия формата, которую этот сайт умеет читать. Старший номер обязан
# совпасть: смена состава полей — это несовместимость, а не улучшение.
ПОДДЕРЖИВАЕМАЯ_ВЕРСИЯ = "1"

провалов = 0


def проверка(имя: str) -> callable:
    def обёртка(тело):
        global провалов
        try:
            тело()
            print(f"  ok   {имя}")
        except AssertionError as ошибка:
            провалов += 1
            print(f"  FAIL {имя}\n         {ошибка}")
        return тело
    return обёртка


снимок = json.loads(СНИМОК.read_text(encoding="utf-8")) if СНИМОК.exists() else {}
таксономия = снимок.get("taxonomy") or {}
мета = снимок.get("meta") or {}


def ключи_материалов() -> set[str]:
    """Ключи из закрытого словаря `lead.php`, а не из имён файлов.

    Именно они приезжают из формы, и именно их придётся сопоставлять боли.
    """
    текст = LEAD.read_text(encoding="utf-8")
    начало = текст.index("const MVB_MATERIALS")
    конец = текст.index("];", начало)
    return set(re.findall(r"^\s+'([a-z0-9-]+)'\s*=>\s*\[",
                          текст[начало:конец], re.M))


print("снимок таксономии")


@проверка("test_snapshot_exists_and_parses")
def _():
    assert СНИМОК.exists(), f"снимка нет: {СНИМОК}"
    assert таксономия, "раздел taxonomy пуст"


@проверка("test_snapshot_is_marked_generated")
def _():
    assert мета.get("generated") is True, "снимок не помечен сгенерированным"
    assert "DO NOT EDIT" in str(мета.get("warning", "")), "нет предупреждения"
    assert "Pains.yaml" in str(мета.get("source", "")), "не назван источник"
    assert "export_taxonomy.py" in str(мета.get("generator", ""))


@проверка("test_snapshot_source_commit_present")
def _():
    коммит = str(мета.get("source_commit", ""))
    assert коммит, "нет source_commit"
    assert коммит == "unknown" or re.fullmatch(r"[0-9a-f]{40}", коммит), коммит


@проверка("test_snapshot_schema_version_supported")
def _():
    версия = str(мета.get("schema_version", ""))
    assert версия, "нет schema_version"
    assert версия.split(".")[0] == ПОДДЕРЖИВАЕМАЯ_ВЕРСИЯ, (
        f"снимок версии {версия}, сайт умеет {ПОДДЕРЖИВАЕМАЯ_ВЕРСИЯ}.x — "
        "состав полей несовместим, читать наполовину нельзя")


@проверка("test_every_site_magnet_maps_to_pain")
def _():
    """Каждый ключ материала либо сопоставлен боли, либо объявлен несопоставленным."""
    указатель = таксономия.get("magnet_to_pain") or {}
    объявленные = таксономия.get("unmapped_magnets") or {}
    потерянные = sorted(ключи_материалов() - set(указатель) - set(объявленные))
    assert not потерянные, (
        f"ключи материалов без боли и без объявления: {потерянные}. "
        "Либо сопоставить в Pains.yaml, либо объявить в unmapped_magnets "
        "с причиной — молча слать событие без боли нельзя")


@проверка("test_every_magnet_page_is_known_to_canon")
def _():
    """Страница материала, о которой канон не знает, — тоже расхождение."""
    страницы = {п.stem for п in МАТЕРИАЛЫ.glob("*.html") if п.stem != "index"}
    указатель = таксономия.get("magnet_to_pain") or {}
    неизвестные = sorted(страницы - set(указатель))
    assert not неизвестные, f"страницы материалов вне канона: {неизвестные}"


@проверка("test_no_second_taxonomy_in_php")
def _():
    """`lead.php` не заводит своего перечня болей.

    Именно ради этого снимок и существует. Проверка ищет имена болей,
    записанные в PHP литералами мимо снимка.
    """
    текст = LEAD.read_text(encoding="utf-8")
    боли = set(таксономия.get("pains") or {})
    магниты = set(таксономия.get("magnet_to_pain") or {})

    # Часть имён болей СОВПАДАЕТ с ключами материалов — `bankrotstvo`,
    # `dogovor`. Их присутствие в PHP законно: это ключ формы, а не имя
    # боли, и запретить его значило бы запретить сам словарь материалов.
    # Найдено ложным срабатыванием этой же проверки при её написании.
    подозрительные = {и for и in боли - магниты
                      if re.search(rf"['\"]{re.escape(и)}['\"]", текст)}
    assert not подозрительные, (
        f"в lead.php записаны имена болей: {sorted(подозрительные)}. "
        "Соответствие обязано читаться из снимка, иначе это четвёртая "
        "таксономия")


@проверка("test_pain_ids_are_url_safe")
def _():
    """Идентификатор поедет в UTM и в имена файлов."""
    for имя in таксономия.get("pains") or {}:
        assert re.fullmatch(r"[a-z][a-z_]*", имя), имя


print("")
if провалов:
    print(f"провалов: {провалов}")
    sys.exit(1)
print("снимок согласован с каноном и с сайтом")
