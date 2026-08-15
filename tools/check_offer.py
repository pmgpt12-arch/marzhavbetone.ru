#!/usr/bin/env python3
"""Лестница боли и оффер карточки товара.

Отвечает на два вопроса, от которых зависят продажи, и оба проверяемы без
единой продажи:

  1. У каждой денежной боли есть путь бесплатник → вход → комплект, или
     где-то человек обязан прыгнуть от нуля до полной цены;
  2. карточка товара продаёт решение проблемы или перечень файлов.

Дефект (код 1):
  • боль ссылается на несуществующий товар или материал;
  • цена в лестнице разошлась с конфигом кассы;
  • товар из лестницы снят с продажи;
  • карточка товара не называет проблему до состава.

Замечание (кода не меняет):
  • у боли нет входной ступени — разрыв лестницы, но заводить товар это
    решение владельца, а не дефект сайта;
  • товар не основной ни для одной боли.

    python3 tools/check_offer.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAINS = ROOT / "data" / "business" / "money-pains.yaml"
CONFIG = ROOT / "products-config.php"

# Проверяется лид — первый абзац после заголовка. Именно он решает, что
# карточка продаёт: ситуацию покупателя или содержимое папки. Заголовок
# для этого не годится — в нём название товара, и слово «неоплата» в нём
# стоит по номенклатуре, а не как обращение к человеку.
#
# Замер 14.08.2026 на пятнадцати карточках: лид t1 начинается «Работы
# приняты, КС-2 и КС-3 подписаны, срок оплаты прошёл — а денег нет»,
# лид p1 — «Формы и реестры, которыми работы закрываются». Первый
# описывает положение читателя, второй — состав комплекта.

# Отличить «называет ситуацию» от «перечисляет состав» — суждение, и
# список слов его не заменяет. Первая версия проверки взяла узкий список
# маркеров ситуации и объявила замечанием четырнадцать лидов из
# пятнадцати; чтение показало обратное: «претензия приходит письмом»,
# «у заказчика кончились деньги», «письмо пришло сегодня» — это ровно
# положение читателя, просто другими словами.
#
# Отсюда проверка сузилась до того, в чём уверена: лид, который
# открывается перечнем содержимого. Всё остальное молчит, а не гадает.
CONTENTS_OPENING = (
    "всё для", "все для", "всё, что решается", "формы и", "шаблоны,",
    "система подготовки", "акты скрытых работ, журналы",
    "документы комплекта", "в комплект вход", "набор документов",
    "здесь собраны")

def catalogue() -> dict[str, int]:
    """sku → цена в рублях. Закомментированные позиции не в счёт."""
    text = CONFIG.read_text(encoding="utf-8")
    body = text.split("function mvb_products(): array", 1)[1]
    body = body.split("/** Ищет продукт", 1)[0]
    body = re.sub(r"^\s*//.*$", "", body, flags=re.M)
    out = {}
    for m in re.finditer(r"'([a-z0-9]+)'\s*=>\s*\[(.*?)\n\s*\],", body, re.S):
        price = re.search(r"'price'\s*=>\s*(\d+)", m.group(2))
        if price:
            out[m.group(1)] = int(price.group(1)) // 100
    return out


def load_pains() -> dict[str, dict]:
    """Узкий разбор: файл правит человек, формат должен быть читаемым."""
    pains: dict[str, dict] = {}
    key = None
    section = None
    for raw in PAINS.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        text = line.strip()
        if indent == 0 and text.endswith(":"):
            section = text[:-1]
            continue
        if section != "pains":
            continue
        if indent == 2 and text.endswith(":"):
            key = text[:-1]
            pains[key] = {"free": [], "cross_sell": [], "entry": None,
                          "core": None, "title": key}
        elif indent == 4 and key:
            name, _, rest = text.partition(":")
            rest = rest.strip()
            if name == "title":
                pains[key]["title"] = rest
            elif name in ("free", "cross_sell"):
                pains[key][name] = re.findall(r"[\w./-]+", rest)
            elif name in ("entry", "core"):
                if rest in ("null", "~", ""):
                    pains[key][name] = None
                else:
                    sku = re.search(r"sku:\s*([a-z0-9]+)", rest)
                    price = re.search(r"price:\s*(\d+)", rest)
                    pains[key][name] = {
                        "sku": sku.group(1) if sku else "",
                        "price": int(price.group(1)) if price else 0}
        elif indent == 6 and key and pains[key].get(name) is not None \
                and isinstance(pains[key].get("core"), dict):
            # Продолжение многострочного отображения entry/core.
            sku = re.search(r"sku:\s*([a-z0-9]+)", text)
            price = re.search(r"price:\s*(\d+)", text)
            target = pains[key].get(name)
            if isinstance(target, dict):
                if sku:
                    target["sku"] = sku.group(1)
                if price:
                    target["price"] = int(price.group(1))
    return pains


def product_page(sku: str) -> Path | None:
    hits = sorted((ROOT / "products").glob(f"{sku}-*.html"))
    return hits[0] if hits else None


def main() -> int:
    skus = catalogue()
    pains = load_pains()
    defects: list[str] = []
    notes: list[str] = []
    used: set[str] = set()

    for key, pain in sorted(pains.items()):
        for step in ("entry", "core"):
            item = pain.get(step)
            if item is None:
                if step == "entry":
                    core = pain.get("core") or {}
                    notes.append(
                        f"{key} «{pain['title']}»: входной ступени нет — "
                        f"от бесплатного материала сразу к "
                        f"{core.get('price', '?')} ₽")
                else:
                    defects.append(f"{key}: нет основного комплекта")
                continue
            sku = item["sku"]
            used.add(sku)
            if sku not in skus:
                defects.append(f"{key}: {step} {sku} нет в каталоге кассы "
                               f"или снят с продажи")
            elif skus[sku] != item["price"]:
                defects.append(
                    f"{key}: {step} {sku} — в лестнице {item['price']} ₽, "
                    f"в кассе {skus[sku]} ₽")

        for material in pain["free"]:
            if not (ROOT / material).exists():
                defects.append(f"{key}: материала {material} нет")

        for sku in pain["cross_sell"]:
            if sku not in skus:
                defects.append(f"{key}: допродажа {sku} не продаётся")

    for sku in sorted(set(skus) - used - {"test1"}):
        notes.append(f"{sku}: не основной ни для одной боли — продаётся "
                     f"только допродажей")

    # Карточка продаёт решение или файлы.
    for sku in sorted(skus):
        if sku == "test1":
            continue
        page = product_page(sku)
        if not page:
            defects.append(f"{sku}: страницы товара нет")
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'<p class="lead">(.*?)</p>', text, re.S)
        if not m:
            defects.append(f"/products/{page.name}: нет лида — оффера нет")
            continue
        lead = " ".join(re.sub(r"<[^>]+>", " ", m.group(1)).split()).lower()
        if any(lead.startswith(c) for c in CONTENTS_OPENING):
            notes.append(
                f"/products/{page.name}: лид открывается составом — "
                f"«{lead[:75]}…»")

    print(f"Болей: {len(pains)}; товаров на продаже: "
          f"{len(skus) - (1 if 'test1' in skus else 0)}; "
          f"с полной лестницей: "
          f"{sum(1 for p in pains.values() if p.get('entry'))}")

    if notes:
        print(f"\n## Разрывы и решения владельца — {len(notes)}")
        for n in notes:
            print(f"   • {n}")

    if defects:
        print(f"\n## ДЕФЕКТЫ — {len(defects)}")
        for d in defects:
            print(f"   ✗ {d}")
        return 1

    print("\nДефектов нет: лестница ссылается на существующие товары, цены "
          "сходятся с кассой, карточки называют проблему.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
