#!/usr/bin/env python3
"""Повторная сборка не отменяет ручные правки манифестов.

Причина замером (15.08.2026). Сразу после D-02 — двух допсоглашений,
добавленных в комплект «Допы не в подарок», — в `products-storage`
нашлись два генератора, переписывающих манифесты целиком текстом,
застывшим на 23.07–30.07.2026. Прогон `update_manifests.py` в
изолированной копии снимал оба допсоглашения из состава P2, откатывал
версию 15.08 → 23.07 и число файлов полного комплекта 89 → 78, заодно
теряя стрелку `← 08-pto-bez-zamechaniy`, по которой `check_packages`
находит источник вложенной копии.

То есть репозиторий был прав, а одна штатная команда возвращала его в
неправое состояние. `check_packages` такую подмену ловит кодом 1, но
уже после того, как файлы испорчены, и чинить пришлось бы руками.

Что проверяется здесь: каждый скрипт `products-storage`, умеющий писать
MANIFEST.md, запускается в отдельной копии дерева, и после прогона
манифесты обязаны совпасть с репозиторием побайтово. Плюс отдельно —
что состав D-02 на месте: обе формы объявлены в манифесте P2 и лежат в
самом комплекте и во вложенной копии внутри полного комплекта ПТО.

Скрипт, который не удалось запустить, называется «не запускался» и не
засчитывается пройденным: `build_all.py` сегодня не компилируется вовсе
(SyntaxError на строке 375), и это состояние, а не гарантия.

Запуск без pytest: python3 tools/test_manifest_rebuild.py
"""
from __future__ import annotations

import ast
import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORAGE = ROOT / "products-storage"

# Формы, добавленные D-02, и места, где они обязаны быть.
D02_FILES = [
    "11-dopsoglashenie-obem-i-cena.docx",
    "12-dopsoglashenie-sroki-doprabot.docx",
]
D02_PACKAGE = STORAGE / "02-dopraboty-bez-poter"
D02_NESTED = (STORAGE / "04-polnyy-komplekt-pto" / "01-30-bazovye-pakety"
              / "02-dopraboty-bez-poter")


def manifest_writers() -> list[Path]:
    """Скрипты, в исходнике которых есть запись MANIFEST.md.

    Ищется по тексту, а не по имени файла: генератор может называться
    как угодно, а опасен он тем, что открывает манифест на запись.
    """
    found = []
    for path in sorted(STORAGE.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if '"MANIFEST.md"), "w"' in text or 'MANIFEST.md", "w"' in text:
            found.append(path)
    return found


def compiles(path: Path) -> bool:
    try:
        ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        return True
    except SyntaxError:
        return False


def manifests_of(root: Path) -> dict[str, Path]:
    return {str(p.relative_to(root)): p for p in sorted(root.rglob("MANIFEST.md"))}


def test_rebuild_does_not_change_manifests() -> None:
    writers = manifest_writers()
    assert writers, ("ни один скрипт не пишет MANIFEST.md — проверка "
                     "потеряла предмет и молча зеленела бы")

    changed: list[str] = []
    skipped: list[str] = []

    for script in writers:
        if not compiles(script):
            skipped.append(f"{script.name}: не компилируется")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "products-storage"
            shutil.copytree(STORAGE, copy)
            result = subprocess.run(
                [sys.executable, script.name],
                cwd=copy, capture_output=True, text=True, timeout=300,
            )
            before, after = manifests_of(STORAGE), manifests_of(copy)
            for name, original in before.items():
                rebuilt = after.get(name)
                if rebuilt is None:
                    changed.append(f"{script.name} удалил {name}")
                elif not filecmp.cmp(original, rebuilt, shallow=False):
                    changed.append(f"{script.name} переписал {name}")
            if result.returncode != 0 and not changed:
                # Отказ генератора — законный исход: он и должен молчать,
                # пока у него нет источника свежее самих манифестов.
                skipped.append(f"{script.name}: отказался, код "
                               f"{result.returncode}")

    for note in skipped:
        print(f"    не запускался — {note}")

    assert not changed, (
        "повторная сборка отменяет ручные правки:\n  " + "\n  ".join(changed))


def test_d02_documents_survive() -> None:
    """Состав D-02 на месте — в манифесте, в комплекте и во вложенной копии."""
    manifest = (D02_PACKAGE / "MANIFEST.md").read_text(encoding="utf-8")
    missing = []
    for name in D02_FILES:
        if name not in manifest:
            missing.append(f"{name}: не объявлен в манифесте P2")
        if not (D02_PACKAGE / name).exists():
            missing.append(f"{name}: нет в комплекте")
        if not (D02_NESTED / name).exists():
            missing.append(f"{name}: нет во вложенной копии полного комплекта")
    assert not missing, "состав D-02 разошёлся:\n  " + "\n  ".join(missing)


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
