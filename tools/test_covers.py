#!/usr/bin/env python3
"""Регресс на сторожа повторных обложек.

Появился из замера 16.08.2026: владелец увидел на боевом сайте одну
картинку у трёх разборов и ещё одну у двух. Проверка при этом была
зелёной — повтор печатался строкой «к сведению», код возврата оставался
нулевым, а в список разборов она не смотрела вовсе: три одинаковые
карточки жили именно там, страницы к тому моменту уже разошлись.

Тест держит три вещи, и ни одна из них не «сегодня на сайте ноль
повторов»:

1. повтор роняет проверку, а не печатается к сведению;
2. повтор ловится по байтам — переименованная копия не спасает;
3. порог похожести разделяет пережатую копию и два разных кадра.

Запуск без pytest: python3 tools/test_covers.py
"""
from __future__ import annotations

import itertools
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_covers import (NEAR_DUPLICATE_DISTANCE, ROOT,  # noqa: E402
                          file_hash, perceptual_hash)

CHECK = Path(__file__).resolve().parent / "check_covers.py"
ASSETS = ROOT / "assets"


def distance(left: Path, right: Path) -> int:
    return bin(perceptual_hash(left) ^ perceptual_hash(right)).count("1")


def run_check(root: Path) -> subprocess.CompletedProcess:
    """Запускается копия в песочнице, а не оригинал.

    check_covers берёт корень сайта от собственного пути, поэтому запуск
    оригинала проверил бы рабочее дерево и был бы зелёным всегда — тест
    молча превратился бы в заглушку.
    """
    return subprocess.run([sys.executable, str(root / "tools" / "check_covers.py")],
                          cwd=root, capture_output=True, text=True)


def sandbox() -> tempfile.TemporaryDirectory:
    """Копия сайта во временном каталоге.

    Проверка ходит от корня репозитория, поэтому подсунуть ей повтор можно
    только на копии — портить рабочее дерево тест не имеет права.
    """
    box = tempfile.TemporaryDirectory()
    root = Path(box.name) / "site"
    (root / "tools").mkdir(parents=True)
    shutil.copytree(ROOT / "articles", root / "articles")
    shutil.copytree(ROOT / "assets", root / "assets")
    shutil.copy(CHECK, root / "tools" / "check_covers.py")
    return box, root


def test_clean_tree_passes() -> list[str]:
    """На нетронутой копии проверка обязана быть зелёной."""
    box, root = sandbox()
    with box:
        done = run_check(root)
        if done.returncode != 0:
            return [f"чистое дерево уронило проверку:\n{done.stdout}{done.stderr}"]
    return []


def test_duplicate_fails() -> list[str]:
    """Одна картинка у двух разборов — код возврата 1.

    Именно этого не было: повтор печатался, проверка возвращала ноль,
    и гейт пропускал его на боевой сайт.
    """
    box, root = sandbox()
    problems = []
    with box:
        victim = root / "articles" / "zos-v-stroitelstve.html"
        text = victim.read_text(encoding="utf-8")
        text = text.replace("assets/zos-v-stroitelstve.jpg",
                            "assets/raschet-metrami.jpg")
        victim.write_text(text, encoding="utf-8")

        done = run_check(root)
        if done.returncode == 0:
            problems.append("повтор обложки не уронил проверку")
        if "ДЕФЕКТ" not in done.stdout:
            problems.append("повтор не назван дефектом в выводе")
    return problems


def test_duplicate_under_new_name_fails() -> list[str]:
    """Переименованная копия — тот же повтор.

    Требование владельца дословно: уникальность считается по содержимому,
    а не по имени файла. Копия под новым именем обязана падать так же.
    """
    box, root = sandbox()
    problems = []
    with box:
        shutil.copy(root / "assets" / "raschet-metrami.jpg",
                    root / "assets" / "sovsem-drugaya-kartinka.jpg")
        victim = root / "articles" / "zos-v-stroitelstve.html"
        text = victim.read_text(encoding="utf-8")
        text = text.replace("assets/zos-v-stroitelstve.jpg",
                            "assets/sovsem-drugaya-kartinka.jpg")
        victim.write_text(text, encoding="utf-8")

        done = run_check(root)
        if done.returncode == 0:
            problems.append("копия под другим именем не уронила проверку")
    return problems


def test_listing_card_counted() -> list[str]:
    """Карточка в списке разборов считается наравне со страницей.

    Повтор из трёх карточек жил только здесь. Проверка, которая читает
    одни страницы, его не видит.
    """
    box, root = sandbox()
    problems = []
    with box:
        listing = root / "articles" / "index.html"
        text = listing.read_text(encoding="utf-8")
        text = text.replace("../assets/zos-v-stroitelstve.jpg",
                            "../assets/raschet-metrami.jpg")
        listing.write_text(text, encoding="utf-8")

        done = run_check(root)
        if done.returncode == 0:
            problems.append("повтор в карточке списка не уронил проверку")
    return problems


def test_near_duplicate_detected() -> list[str]:
    """Пережатая и уменьшенная копия обязана попадать под порог.

    sha256 такую копию пропускает — на то и добавлен dHash.
    """
    problems = []
    source = ASSETS / "raschet-metrami.jpg"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        image = Image.open(source)

        variants = {
            "пережат q40": lambda p: image.save(p, "JPEG", quality=40),
            "уменьшен вдвое": lambda p: image.resize(
                (image.width // 2, image.height // 2)).save(p, "JPEG", quality=82),
            "обесцвечен": lambda p: image.convert("L").convert("RGB").save(
                p, "JPEG", quality=85),
            "пересохранён в PNG": lambda p: image.save(p, "PNG"),
        }
        for name, make in variants.items():
            copy = tmp / f"{name}.png"
            make(copy)
            if file_hash(copy) == file_hash(source):
                problems.append(f"{name}: байты совпали, случай не тот")
            spread = distance(source, copy)
            if spread > NEAR_DUPLICATE_DISTANCE:
                problems.append(
                    f"{name}: расстояние {spread} выше порога "
                    f"{NEAR_DUPLICATE_DISTANCE} — копия прошла бы молча")
    return problems


def test_no_false_positives_on_real_covers() -> list[str]:
    """Порог не должен ругаться на разные кадры.

    Предупреждение объявлено неблокирующим, пока доля ложных срабатываний
    не измерена. Здесь она и меряется — на всех обложках сайта. Если
    ближайшая пара разных кадров подойдёт к порогу вплотную, тест
    развалится раньше, чем предупреждение начнут игнорировать.
    """
    covers = sorted(p for p in ASSETS.glob("*.jpg"))
    hashes = {p: perceptual_hash(p) for p in covers}
    closest = min(
        (bin(hashes[a] ^ hashes[b]).count("1"), a.name, b.name)
        for a, b in itertools.combinations(covers, 2))
    spread, left, right = closest
    if spread <= NEAR_DUPLICATE_DISTANCE:
        return [f"порог {NEAR_DUPLICATE_DISTANCE} даёт ложное срабатывание: "
                f"{left} ~ {right} на расстоянии {spread}"]
    return []


TESTS = [
    test_clean_tree_passes,
    test_duplicate_fails,
    test_duplicate_under_new_name_fails,
    test_listing_card_counted,
    test_near_duplicate_detected,
    test_no_false_positives_on_real_covers,
]


def main() -> int:
    failures = []
    for test in TESTS:
        problems = test()
        mark = "ok" if not problems else "ПРОВАЛ"
        print(f"  [{mark}] {test.__name__}")
        for problem in problems:
            print(f"        {problem}")
        failures.extend(problems)

    if failures:
        print(f"\nПровалов: {len(failures)}")
        return 1
    print(f"\nВсе проверки сторожа обложек прошли: {len(TESTS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
