#!/usr/bin/env python3
"""Число файлов берётся из своей папки, а не у соседа по странице.

ЗАЧЕМ. Инструмент определяет хозяина числа соседством, и на странице
бесплатного материала это давало ложь: бейдж «БЕСПЛАТНО · N ФАЙЛОВ» стоит в
шапке, до первого блока, своей ссылки рядом не имеет — и доставался ближайшей
карточке платной ступени. Четыре верных бейджа инструмент предлагал сделать
ложными: dengi 5→6 (счёт T1), akt-skrytyh-rabot 5→6 и
ispolnitelnaya-dokumentaciya 5→6 (счёт T2), raschet-metrami 2→5 (счёт T6).

ЧТО СТЕРЕЖЁТСЯ. Не «инструмент не падает», а правило источника истины: у
платного комплекта число берётся из папки выдачи его SKU, у бесплатного
материала — только из его собственной папки `00-free-*`. Ни то ни другое не
выводится из соседней карточки или ссылки на платный товар.

`--write` на рабочем дереве не запускается ни одним тестом. Запись
проверяется в изолированной временной копии, которую создаёт и удаляет сам
pytest.

    python3 -m pytest tools/test_sync_kit_file_counts.py -q
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

КОРЕНЬ = Path(__file__).resolve().parent.parent
ИНСТРУМЕНТ = КОРЕНЬ / "tools" / "sync_kit_file_counts.py"

# Четыре бейджа, которые инструмент ломал. Ожидаемое число — не переписанная
# сюда константа, а то, что лежит в собственной папке материала: тест сверяет
# страницу с диском, а не с этим файлом.
БЕСПЛАТНЫЕ_СТРАНИЦЫ = (
    "dengi",
    "akt-skrytyh-rabot",
    "ispolnitelnaya-dokumentaciya",
    "raschet-metrami",
)


def модуль():
    описание = importlib.util.spec_from_file_location("sync_kit", ИНСТРУМЕНТ)
    м = importlib.util.module_from_spec(описание)
    описание.loader.exec_module(м)
    return м


@pytest.fixture(scope="module")
def инструмент():
    return модуль()


def прогон(корень: Path, *аргументы: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(корень / "tools" / "sync_kit_file_counts.py"), *аргументы],
        capture_output=True, text=True, cwd=корень)


def хеши(пути) -> dict[str, str]:
    return {str(п): hashlib.sha256(п.read_bytes()).hexdigest() for п in пути}


# --- Правило источника истины -------------------------------------------------


def test_у_бесплатного_материала_своя_папка_а_не_соседний_sku(инструмент):
    """Связь «ключ → папка» берётся из сборщика архивов, а не пишется руками."""
    материалы = инструмент.материалы()
    assert материалы, "связь ключ → папка не прочиталась"
    for ключ, папка in материалы.items():
        assert папка.startswith("00-free-"), f"{ключ}: папка {папка} не бесплатная"
        assert (инструмент.СКЛАД / папка).is_dir(), f"{ключ}: папки {папка} нет"
    # Платные и бесплатные — разные множества имён, пересечься не могут.
    assert not (set(материалы) & set(инструмент.папки()))


@pytest.mark.parametrize("ключ", БЕСПЛАТНЫЕ_СТРАНИЦЫ)
def test_бейдж_материала_сходится_с_его_папкой(инструмент, ключ):
    """Бейдж на странице равен числу файлов в своей папке — и так и остаётся."""
    страница = (КОРЕНЬ / "materialy" / f"{ключ}.html").read_text(encoding="utf-8")
    заявлено = [int(m.group(1)) for m in инструмент.ЧИСЛО.finditer(страница)
                if m.group(3) == "ФАЙЛ"]
    assert len(заявлено) == 1, f"{ключ}: бейджей {len(заявлено)}, ожидался один"
    assert заявлено[0] == инструмент.счёт_материалов()[ключ]


@pytest.mark.parametrize("ключ", БЕСПЛАТНЫЕ_СТРАНИЦЫ)
def test_хозяин_бейджа_это_материал_а_не_платная_ступень(инструмент, ключ):
    """Тот самый дефект: до правки здесь возвращалась платная ступень."""
    страница = (КОРЕНЬ / "materialy" / f"{ключ}.html").read_text(encoding="utf-8")
    бейдж = next(m for m in инструмент.ЧИСЛО.finditer(страница)
                 if m.group(3) == "ФАЙЛ")
    владелец = инструмент.хозяин(страница, бейдж.start(), None, ключ)
    assert владелец == ("материал", ключ), (
        f"{ключ}: бейдж достался {владелец}, а он про сам материал")


@pytest.mark.parametrize("ключ", БЕСПЛАТНЫЕ_СТРАНИЦЫ)
def test_check_не_предлагает_править_бейдж_материала(ключ):
    """Проверка не называет страницу материала — предлагать там нечего."""
    итог = прогон(КОРЕНЬ, "--check")
    строки = [s for s in итог.stdout.splitlines()
              if s.startswith(f"страница materialy/{ключ}.html:")]
    # On FREE pages there can be PAID cross-sell cards whose count IS stale.
    # Only the FREE material's own count must never be corrected from a paid SKU.
    ложные = [s for s in строки if re.search(
        rf"(?<![\w-]){re.escape(ключ)}: \d+→\d+", s)]
    assert not ложные, f"{ключ}: проверка пытается изменить число бесплатного комплекта: {ложные}"


def test_карточка_платного_на_странице_материала_по_прежнему_разбирается(инструмент):
    """Правка не должна была ослепить инструмент на cross-sell карточках.

    На `materialy/uderzhaniya.html` рядом с бейджем материала стоит карточка
    P5, и её число обязано сверяться с выдачей P5. Если бы страницу материала
    целиком отдали материалу, настоящее расхождение 12→11 потерялось бы.
    """
    страница = (КОРЕНЬ / "materialy" / "uderzhaniya.html").read_text(encoding="utf-8")
    карточные = [m for m in инструмент.ЧИСЛО.finditer(страница)
                 if инструмент.хозяин(страница, m.start(), None, "uderzhaniya")
                 == ("товар", "p5")]
    assert карточные, "карточка P5 на странице материала перестала опознаваться"


@pytest.mark.parametrize(
    "материал,sku,старое",
    [("dengi", "p1", 20), ("raschet-metrami", "p11", 8)],
)
def test_платная_карточка_с_бесплатной_страницы_имеет_верный_счёт(
        копия, инструмент, материал, sku, старое):
    """Paid cross-sell claims use pinned buyer ZIP counts, never FREE badge counts."""
    страница = копия / "materialy" / (материал + ".html")
    html = страница.read_text(encoding="utf-8")
    блоки = re.findall(r'<article class="product-card"[^>]*>[\s\S]*?</article>', html)
    подходящие = [b for b in блоки if f"/products/{sku}-" in b]
    assert len(подходящие) == 1, f"{sku}: paid card missing or ambiguous"
    current = инструмент.счёт()[sku]
    card = подходящие[0]
    assert card.count(f"{current} файлов") == 1, f"{sku}: cross-sell count disagrees with pinned ZIP"

    # Deliberately reintroduce the old number INSIDE the paid card only.
    outdated = card.replace(f"{current} файлов", f"{старое} файлов")
    assert outdated != card
    страница.write_text(html.replace(card, outdated, 1), encoding="utf-8")
    check = прогон(копия, "--check")
    assert check.returncode == 1
    assert f"{sku}: {старое}→{current}" in check.stdout, check.stdout
    assert outdated in страница.read_text(encoding="utf-8"), "--check modified source"


# --- Настоящее расхождение P5 -------------------------------------------------


def test_расхождение_p5_обнаруживается(копия, инструмент):
    """Force a stale P5 card in a disposable copy; must not rely on stale live files."""
    факт = инструмент.счёт()["p5"]
    assert факт == 30, "P5 count drifted from accepted protected master ZIP"
    карточка = копия / "materialy" / "uderzhaniya.html"
    было = карточка.read_text(encoding="utf-8")
    assert было.count("30 файлов") == 1, "P5 source must match the published edition"
    карточка.write_text(было.replace("30 файлов", "29 файлов"), encoding="utf-8")
    итог = прогон(копия, "--check")
    assert итог.returncode == 1 and "p5: 29→30" in итог.stdout, итог.stdout
    assert карточка.read_text(encoding="utf-8").count("29 файлов") == 1, "--check modified a source file"


def test_платный_счёт_совпадает_с_sha_пинованным_реестром(инструмент):
    """All 11 paid SKU counts must follow the independently verified buyer ZIPs."""
    registry = json.loads(
        (КОРЕНЬ / "tools/reports/nsp-paid-master-counts-20261106.json")
        .read_text(encoding="utf-8"))
    факт = инструмент.счёт()
    assert set(registry["count_by_sku"]) == {
        "p1", "p2", "p3", "p4", "p5", "p7", "p8", "p9", "p10", "p11", "p13"
    }
    assert all(факт[k] == v for k, v in registry["count_by_sku"].items())
    assert факт["p5"] == 30 and факт["p1"] == 18


def test_пропажа_платного_реестра_останавливает_проверку(копия):
    """Fail closed rather than falling back to obsolete unpacked paid directories."""
    registry = копия / "tools/reports/nsp-paid-master-counts-20261106.json"
    registry.unlink()
    result = прогон(копия, "--check")
    assert result.returncode != 0
    assert "Нет проверенного реестра платных ZIP" in result.stderr


# --- Изолированная копия: --write не трогает бесплатные страницы --------------


@pytest.fixture
def копия(tmp_path):
    """Минимальное дерево: инструмент, конфиг, имена файлов склада, страницы.

    Файлы склада создаются пустыми — инструмент считает их количество, а не
    содержимое, и копировать мегабайты .docx ради счёта незачем. Копия живёт
    в tmp_path и удаляется pytest вместе с ним.
    """
    корень = tmp_path / "site"
    (корень / "tools").mkdir(parents=True)
    for имя in ("sync_kit_file_counts.py", "build_free_zips.py"):
        shutil.copy2(КОРЕНЬ / "tools" / имя, корень / "tools" / имя)
    shutil.copy2(КОРЕНЬ / "products-config.php", корень / "products-config.php")
    # Paid 11-SKU contract must exist in isolated tests; no silent fallback.
    (корень / "tools" / "reports").mkdir()
    shutil.copy2(КОРЕНЬ / "tools/reports/nsp-paid-master-counts-20261106.json",
                 корень / "tools/reports/nsp-paid-master-counts-20261106.json")

    for папка in (КОРЕНЬ / "products-storage").iterdir():
        if not папка.is_dir():
            continue
        цель = корень / "products-storage" / папка.name
        цель.mkdir(parents=True)
        for файл in папка.rglob("*"):
            if файл.is_file():
                назначение = цель / файл.relative_to(папка)
                назначение.parent.mkdir(parents=True, exist_ok=True)
                # MANIFEST.md копируется как есть: инструмент правит в нём
                # строку «Покупателю уходит N файлов».
                if файл.name == "MANIFEST.md":
                    shutil.copy2(файл, назначение)
                else:
                    назначение.touch()

    for каталог in ("materialy", "articles", "products"):
        (корень / каталог).mkdir(exist_ok=True)
        for стр in (КОРЕНЬ / каталог).glob("*.html"):
            shutil.copy2(стр, корень / каталог / стр.name)
    for стр in КОРЕНЬ.glob("*.html"):
        shutil.copy2(стр, корень / стр.name)
    return корень


def test_write_в_копии_не_меняет_бесплатный_комплект_и_форму(копия):
    """Only embedded PAID cross-sell card text may change in a FREE page.

    The free eyebrow, form, consent, all non-paid content and page links remain
    byte-identical. No --write is ever run in the real repository tree.
    """
    страницы = [копия / "materialy" / f"{к}.html" for к in БЕСПЛАТНЫЕ_СТРАНИЦЫ]
    было = {p: p.read_text(encoding="utf-8") for p in страницы}
    итог = прогон(копия, "--write")
    assert итог.returncode == 0, итог.stdout + итог.stderr

    paid_card = re.compile(r'<article\s+class="product-card"[^>]*>[\s\S]*?</article>')
    def outside_paid_cards(text):
        return paid_card.sub("[PAID_PRODUCT_CARD_ONLY]", text)

    for страница, original in было.items():
        current = страница.read_text(encoding="utf-8")
        assert len(paid_card.findall(original)) == len(paid_card.findall(current)), (
            f"paid card count changed on FREE page: {страница}")
        assert outside_paid_cards(original) == outside_paid_cards(current), (
            f"FREE material, lead form or non-product text modified: {страница}")


def test_write_в_копии_правит_расхождение_платного(копия, инструмент):
    """Инструмент не онемел: настоящее расхождение он по-прежнему пишет.

    Расхождение вносится в копию намеренно, а не берётся со страницы рабочего
    дерева. Первая редакция теста опиралась на живое «12 файлов» в статье — и
    протухла в тот же заход, когда это число исправили. Тест обязан проверять
    инструмент, а не состояние дерева на минуту написания.
    """
    факт = инструмент.счёт()["p5"]
    устаревшее = факт + 1
    страница = копия / "materialy" / "uderzhaniya.html"
    текст = страница.read_text(encoding="utf-8")
    карточка = f"{факт} файлов"
    assert карточка in текст, "в копии нет карточки P5 — фикстура не та"
    страница.write_text(текст.replace(карточка, f"{устаревшее} файлов"),
                        encoding="utf-8")

    прогон(копия, "--write")

    после = страница.read_text(encoding="utf-8")
    assert карточка in после, "инструмент не вернул число карточки P5 к факту"
    assert f"{устаревшее} файлов" not in после


def test_после_правок_проверка_становится_зелёной(копия, инструмент):
    """Полный цикл: расхождение есть → --write → --check зелёный.

    Расхождение вносится в копию самим тестом. Первая редакция опиралась на
    то, что в дереве осталось что чинить, — и упала в тот же час, когда
    последнее устаревшее число исправили. Это второй раз, когда тест в этом
    файле был привязан к состоянию дерева, и оба раза он ловил не дефект
    инструмента, а момент времени.
    """
    факт = инструмент.счёт()["p5"]
    страница = копия / "materialy" / "uderzhaniya.html"
    текст = страница.read_text(encoding="utf-8")
    assert f"{факт} файлов" in текст, "в копии нет карточки P5 — фикстура не та"
    страница.write_text(текст.replace(f"{факт} файлов", f"{факт + 1} файлов"),
                        encoding="utf-8")

    первый = прогон(копия, "--check")
    assert первый.returncode == 1, "внесённое расхождение не замечено"
    assert "p5" in первый.stdout

    запись = прогон(копия, "--write")
    assert запись.returncode == 0, запись.stdout + запись.stderr

    второй = прогон(копия, "--check")
    assert второй.returncode == 0, второй.stdout + второй.stderr
    assert "мест исправлено: 0" in второй.stdout


def test_проверка_возвращает_fail_если_есть_правки():
    """Unit contract, not a false assertion that the source tree is release-ready.

    Real clean-source acceptance remains the BLOCKING sync_kit_file_counts --check.
    """
    итог = прогон(КОРЕНЬ, "--check")
    match = re.search(r"мест исправлено: (\d+)", итог.stdout)
    assert match is not None, итог.stdout
    исправлений = int(match.group(1))
    assert итог.returncode == (1 if исправлений else 0), "check exit code masked source drift"


def test_правовая_фикстура_с_не_utf8_кодировкой_не_ломает_витринный_гейт(копия):
    """Legal binary fixture must not affect counted source pages or exit status."""
    прежний = прогон(копия, "--check")
    фикстура = копия / "data" / "legal" / "fixtures" / "pages" / "source.html"
    фикстура.parent.mkdir(parents=True)
    фикстура.write_bytes(b"\xce\xff")
    итог = прогон(копия, "--check")
    assert итог.returncode == прежний.returncode
    assert итог.stdout == прежний.stdout
    assert итог.stderr == прежний.stderr


# --- Детерминированность и безопасность ---------------------------------------


def test_check_не_меняет_рабочее_дерево():
    """Проверка обязана быть читающей. Сверяются хеши, а не намерения."""
    следим = sorted(
        [КОРЕНЬ / "materialy" / f"{к}.html" for к in БЕСПЛАТНЫЕ_СТРАНИЦЫ]
        + list((КОРЕНЬ / "articles").glob("*garantiyn*.html"))
        + [ИНСТРУМЕНТ])
    было = хеши(следим)
    прогон(КОРЕНЬ, "--check")
    assert хеши(следим) == было


def test_инструмент_не_ходит_в_сеть():
    """Разбор импортов: сетевых модулей в инструменте быть не должно."""
    дерево = ast.parse(ИНСТРУМЕНТ.read_text(encoding="utf-8"))
    имена = set()
    for узел in ast.walk(дерево):
        if isinstance(узел, ast.Import):
            имена.update(a.name.split(".")[0] for a in узел.names)
        elif isinstance(узел, ast.ImportFrom) and узел.module:
            имена.add(узел.module.split(".")[0])
    запрещены = {"urllib", "http", "requests", "socket", "ftplib", "smtplib"}
    assert not (имена & запрещены), f"сетевые импорты: {имена & запрещены}"


def test_check_и_write_вместе_отвергаются():
    итог = прогон(КОРЕНЬ, "--check", "--write")
    assert итог.returncode != 0
    assert "не имеют смысла" in итог.stderr


def test_повторная_проверка_даёт_тот_же_вывод():
    первый, второй = прогон(КОРЕНЬ, "--check"), прогон(КОРЕНЬ, "--check")
    assert первый.stdout == второй.stdout
    assert первый.returncode == второй.returncode


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
