#!/usr/bin/env python3
"""Сквозной путь покупателя: бесплатная выдача → оплата → письмо → что дальше.

Проверка написана под разрывы, найденные аудитом MB001 (отчёт
`docs/reports/MB001_COMMERCIAL_JOURNEY_ROADMAP.md`, ветка
`claude/marzhavbetone-customer-journey-audit-u58x43`, коммит 8576587), и
каждый раздел ниже назван номером разрыва оттуда. Все пять разрывов жили на
зелёном CI: ни одна прежняя проверка не сравнивала то, что обещает один шаг
пути, с тем, что делает следующий.

  G-01  форма главной без ключа `material` выдавала PDF, рекламирующий
        снятый с продажи «Полный комплект ПТО — 40 документов»;
  G-05  страница успеха и `00-START-HERE.txt` в архиве называли разные
        следующие товары (12 из 18);
  G-06  таблицу «что дальше» нельзя было пересобрать: её источник удалён;
  G-32  «что дальше» вело в товар, который сам не готов (RED, BLOCKED);
  G-07  письмо отправляло к `00-INSTRUKCIYA`, которой нет у 15 из 18
        комплектов, и не называло `00-START-HERE.txt`;
  G-30  «Ответ на претензию» (p10) лежал в группе каталога «Банкротство»;
  G-31  точной формулировки «НДС не начисляется в связи с применением УСН»
        не было ни в оферте, ни в условиях оплаты.

    python3 tools/test_commercial_journey.py

Код возврата 1, если хоть один шаг пути противоречит соседнему.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

# sha256 PDF, который выдавался главной до правки: стр. 2 рекламирует
# «Полный комплект ПТО — 40 документов» (снят 11.08.2026) и `/#catalog`.
# Файл остаётся в `downloads/` — из него собирается шаблон бота в
# ai-business-os, — но сайт его больше выдавать не должен.
УСТАРЕВШИЙ_PDF = "downloads/checklist-zakrytiya-rabot.pdf"
СНЯТАЯ_ЛИНЕЙКА = re.compile(r"Полный комплект|40 документов|10 документов|#catalog")

провалов = 0


def проверка(имя: str, тело) -> None:
    global провалов
    try:
        тело()
        print(f"  ok   {имя}")
    except Exception as ошибка:  # noqa: BLE001 — любое исключение это провал строки
        провалов += 1
        текст = str(ошибка) if isinstance(ошибка, AssertionError) else repr(ошибка)
        print(f"  FAIL {имя}\n         {текст}")


def читать(путь: str) -> str:
    return (ROOT / путь).read_text(encoding="utf-8")


def видимый_текст(html: str) -> str:
    html = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


# ---------------------------------------------------------------- G-01

def материалы_lead() -> tuple[dict[str, str], str]:
    """Ключ → файл из lead.php и ключ, который берётся без параметра."""
    текст = читать("lead.php")
    файлы = dict(re.findall(r"'([a-z0-9-]+)'\s*=>\s*\[\s*'file'\s*=>\s*'([^']+)'", текст))
    # Ключ по умолчанию — объявленный или, в прежней редакции, вписанный
    # прямо в разбор запроса. Проверяется то, что уходит человеку, а не имя.
    умолчание = (re.search(r"const MVB_DEFAULT_MATERIAL\s*=\s*'([a-z0-9-]+)'", текст)
                 or re.search(r"\$_POST\['material'\]\s*\?\?\s*'([a-z0-9-]+)'", текст))
    assert умолчание, "в lead.php не найден ключ по умолчанию: ответ без ключа не определён"
    return файлы, умолчание.group(1)


def pdf_без_снятой_линейки(веб_путь: str) -> None:
    путь = ROOT / веб_путь.lstrip("/")
    assert путь.is_file(), f"{веб_путь}: файла нет"
    устаревший = hashlib.sha256((ROOT / УСТАРЕВШИЙ_PDF).read_bytes()).hexdigest()
    assert hashlib.sha256(путь.read_bytes()).hexdigest() != устаревший, \
        f"{веб_путь}: это прежний PDF со снятой линейкой"
    if путь.suffix != ".pdf":
        return
    # Текст PDF — если pdftotext есть. Без него остаётся счёт страниц:
    # снятая линейка жила ровно на второй странице.
    if shutil.which("pdftotext"):
        текст = subprocess.run(["pdftotext", str(путь), "-"], capture_output=True,
                               text=True, check=True).stdout
        найдено = СНЯТАЯ_ЛИНЕЙКА.findall(текст)
        assert not найдено, f"{веб_путь}: в тексте {найдено}"
    страниц = len(re.findall(rb"/Type\s*/Page(?!s)", путь.read_bytes()))
    assert страниц == 1, f"{веб_путь}: страниц {страниц}, ожидалась одна (без листа линейки)"


def g01_умолчание() -> None:
    файлы, ключ = материалы_lead()
    assert ключ in файлы, f"MVB_DEFAULT_MATERIAL = {ключ!r}, такого материала нет"
    pdf_без_снятой_линейки(файлы[ключ])


def g01_главная() -> None:
    файлы, _ = материалы_lead()
    форма = re.search(r'<form class="lead-form" id="lead-form".*?</form>', читать("index.html"), re.S)
    assert форма, "форма главной не найдена"
    ключ = re.search(r'<input name="material" type="hidden" value="([a-z0-9-]+)">', форма.group(0))
    assert ключ, "форма главной не несёт ключ material — ответ берётся по умолчанию"
    assert ключ.group(1) in файлы, f"ключ формы {ключ.group(1)!r} не объявлен в lead.php"
    pdf_без_снятой_линейки(файлы[ключ.group(1)])


def g01_все_формы_с_ключом() -> None:
    без_ключа = []
    for путь in sorted(ROOT.glob("**/*.html")):
        if {"node_modules", "products-storage", ".git"} & set(путь.parts):
            continue
        for форма in re.findall(r'<form class="lead-form".*?</form>', путь.read_text(encoding="utf-8"), re.S):
            if 'name="material"' not in форма:
                без_ключа.append(str(путь.relative_to(ROOT)))
    assert not без_ключа, f"формы без ключа material: {без_ключа}"


# ---------------------------------------------------------- G-05, G-06, G-32

def таблица_success() -> dict:
    текст = читать("success.html")
    м = re.search(r"window\.MVB_UPSELL = (\{.*?\n\});", текст, re.S)
    assert м, "в success.html нет таблицы window.MVB_UPSELL"
    return json.loads(м.group(1))


def стартовый_шаг(каталог: str) -> dict:
    """Что называет сам START-HERE, прочитанный независимо от сборщика."""
    текст = (ROOT / "products-storage" / каталог / "00-START-HERE.txt").read_text(encoding="utf-8")
    следующий = re.search(r"https://marzhavbetone\.ru(/products/[a-z0-9-]+\.html)\?[^\s]*utm_content=[a-z0-9]+-next", текст)
    нейтральный = re.search(r"https://marzhavbetone\.ru(/[a-z0-9/-]*\.html)\?[^\s]*utm_content=[a-z0-9]+-diagnostika", текст)
    return {"next": следующий.group(1) if следующий else "",
            "neutral": нейтральный.group(1) if нейтральный else ""}


def g05_совпадает_со_start_here() -> None:
    import build_upsell
    таблица = таблица_success()
    каталог = build_upsell.catalog()
    статусы = build_upsell.readiness()
    беды = []
    for sku, товар in каталог.items():
        предложение = таблица.get(sku)
        if not предложение:
            беды.append(f"{sku}: нет строки — после покупки следующего шага нет")
            continue
        старт = стартовый_шаг(товар["dir"])
        цель = старт["next"]
        цель_sku = build_upsell.sku_by_url(каталог).get(цель, "")
        годится = цель and статусы.get(цель_sku) not in build_upsell.NOT_READY
        ожидается = цель if годится else старт["neutral"]
        if предложение["url"] != ожидается:
            беды.append(f"{sku}: success → {предложение['url']}, START-HERE → {цель or 'нет товара'}"
                        f" ({статусы.get(цель_sku, '—')}), ожидалось {ожидается}")
    assert not беды, "\n         ".join(беды)


def g06_таблица_из_сборщика() -> None:
    import build_upsell
    собранная = build_upsell.build_table()
    assert таблица_success() == собранная, \
        "success.html разошёлся со сборщиком: python3 tools/build_upsell.py --write"


def g32_не_ведёт_в_неготовое() -> None:
    import build_upsell
    каталог = build_upsell.catalog()
    по_адресу = build_upsell.sku_by_url(каталог)
    статусы = build_upsell.readiness()
    assert set(статусы) == set(каталог), \
        f"статусы готовности не на всех товарах: нет {sorted(set(каталог) - set(статусы))}, " \
        f"лишние {sorted(set(статусы) - set(каталог))}"
    беды = [f"{sku} → {п['url']} ({статусы[по_адресу[п['url']]]})"
            for sku, п in таблица_success().items()
            if п["url"] in по_адресу and статусы[по_адресу[п["url"]]] in build_upsell.NOT_READY]
    assert not беды, f"«что дальше» ведёт в неготовый товар: {беды}"


# ---------------------------------------------------------------- G-07

def письмо() -> str:
    tmp = tempfile.mkdtemp()
    try:
        код = (
            "define('ORDERS_DIR', getenv('ORD')); define('ADMIN_EMAIL', 'admin@example.test');"
            "require getenv('CFG');"
            "echo mvb_delivery_email(['items' => [['sku' => 'p8']]],"
            " [['name' => 'Архив', 'url' => 'https://example.test/d']]);"
        )
        вывод = subprocess.run(["php", "-r", код], capture_output=True, text=True, check=True,
                               env={**os.environ, "ORD": tmp, "CFG": str(ROOT / "products-config.php")})
        return вывод.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def g07_письмо_ведёт_в_start_here() -> None:
    текст = письмо()
    assert "00-START-HERE.txt" in текст, "письмо не называет 00-START-HERE.txt"
    assert "INSTRUKCIYA" not in текст, "письмо по умолчанию отправляет к 00-INSTRUKCIYA"
    шаги = текст.split("Что делать дальше:", 1)
    assert len(шаги) == 2, "в письме нет раздела «Что делать дальше»"
    первый_файл = re.search(r"«?(0\d-[A-Z-]+(?:\.txt)?)", шаги[1])
    assert первый_файл and первый_файл.group(1) == "00-START-HERE.txt", \
        f"первым письмо называет {первый_файл.group(1) if первый_файл else 'ничего'}"


def g07_start_here_есть_у_всех() -> None:
    import build_upsell
    нет = [sku for sku, т in build_upsell.catalog().items()
           if not (ROOT / "products-storage" / т["dir"] / "00-START-HERE.txt").is_file()]
    assert not нет, f"письмо обещает 00-START-HERE.txt, а его нет у {нет}"


# ---------------------------------------------------------------- G-30

def g30_p10_в_спорах() -> None:
    import catalog_groups
    группы = {slug: skus for slug, _, _, skus in catalog_groups.GROUPS}
    assert "p10" not in группы["bankrotstvo"], "p10 «Ответ на претензию» в группе «Банкротство»"
    спор = [slug for slug, skus in группы.items() if "p12" in skus]
    assert спор and "p10" in группы[спор[0]], "p10 не в одной группе со своим старшим товаром p12"
    # Разметка страницы — то, что видит покупатель, а не только данные.
    каталог = читать("katalog.html")
    блок = re.search(r'<details class="product-group"[^>]*id="group-bankrotstvo".*?</details>', каталог, re.S)
    assert блок, "группа «Банкротство» не найдена в katalog.html"
    assert 'data-sku="p10"' not in блок.group(0), "в katalog.html p10 всё ещё в «Банкротстве»"


# ---------------------------------------------------------------- G-31

def g31_усн() -> None:
    фраза = "НДС не начисляется в связи с применением УСН"
    где = [путь for путь in ("offer.html", "payment-delivery.html") if фраза in видимый_текст(читать(путь))]
    assert где, f"«{фраза}» нет ни в оферте, ни в условиях оплаты"


def main() -> int:
    print("Путь покупателя (MB001, Phase 0)")
    проверка("G-01 без ключа material выдаётся PDF без снятой линейки", g01_умолчание)
    проверка("G-01 форма главной несёт ключ и получает PDF без снятой линейки", g01_главная)
    проверка("G-01 у каждой формы лида есть ключ material", g01_все_формы_с_ключом)
    проверка("G-05 success ведёт туда же, куда START-HERE, или в его нейтральный шаг", g05_совпадает_со_start_here)
    проверка("G-06 таблица success.html собирается сборщиком, а не руками", g06_таблица_из_сборщика)
    проверка("G-32 «что дальше» не ведёт в RED/BLOCKED", g32_не_ведёт_в_неготовое)
    проверка("G-07 письмо первым называет 00-START-HERE.txt", g07_письмо_ведёт_в_start_here)
    проверка("G-07 00-START-HERE.txt есть у всех продаваемых товаров", g07_start_here_есть_у_всех)
    проверка("G-30 p10 лежит в группе споров вместе с p12", g30_p10_в_спорах)
    проверка("G-31 УСН/НДС раскрыты точной формулировкой", g31_усн)
    print(f"\nпровалов: {провалов}")
    return 1 if провалов else 0


if __name__ == "__main__":
    sys.exit(main())
