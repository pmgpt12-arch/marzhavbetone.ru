#!/usr/bin/env python3
"""«Что дальше» на success.html — из того же файла, что покупатель получает в архиве.

Замер 15.08.2026: страница благодарности показывала состав заказа и ссылки
на скачивание и ничем не заканчивалась. Тогда таблицу «что дальше» стали
собирать из `data/sales/product-map.csv`.

Замер 30.09.2026 (аудит MB001, G-05, G-06, G-32): карты товаров в
репозитории больше нет (удалена при открытии, `a1373b0`), таблица стояла
руками, и у 12 из 18 товаров страница успеха и `00-START-HERE.txt` в архиве
называли РАЗНЫЕ следующие товары. Для t5 страница обещала «весь порядок по
этой ситуации» и вела в чужой комплект p7. Ещё семь предложений вели в
товары, которые сами не готовы к продаже.

Поэтому источник теперь один — раздел «Если ситуация изменилась» в
`00-START-HERE.txt` каждого товара. Это тот текст, который покупатель
держит в руках; его собирает `ai-business-os/tools/build_start_here.py`
из `data/onboarding/post_purchase.yaml`. Страница успеха его не
пересказывает своими словами, а повторяет:

  · товар из раздела «Если ситуация изменилась» — если он есть и его статус
    в `tools/product_readiness.yaml` не RED и не BLOCKED;
  · иначе — раздел «Другая ситуация на объекте» того же файла: разбор по
    семи вопросам (диагностика). Он есть в каждом START-HERE, поэтому
    страница успеха не предлагает того, чего нет в архиве, и не выдумывает
    рекомендацию, которой нет нигде.

Случайных товаров блок не показывает никогда.

    python3 tools/build_upsell.py           # показать
    python3 tools/build_upsell.py --write   # вставить в success.html
    python3 tools/build_upsell.py --check   # код 1, если success.html разошёлся
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "success.html"
CONFIG = ROOT / "products-config.php"
STORAGE = ROOT / "products-storage"
READINESS = ROOT / "tools" / "product_readiness.yaml"
START_HERE = "00-START-HERE.txt"

BEGIN = "  <!-- upsell:begin -->"
END = "  <!-- upsell:end -->"

# Статусы, в которые «что дальше» не ведёт (аудит MB001, раздел 4).
NOT_READY = {"RED", "BLOCKED"}

# Заголовки разделов START-HERE, из которых берётся шаг. Номер раздела не
# закрепляется: он зависит от числа разделов выше.
CHANGED = "ЕСЛИ СИТУАЦИЯ ИЗМЕНИЛАСЬ"
OTHER = "ДРУГАЯ СИТУАЦИЯ НА ОБЪЕКТЕ"

# Запись каталога: только незакомментированные — снятый p6 в продаже не
# участвует и следующим шагом быть не может.
ENTRY = re.compile(
    r"^\s+'([a-z0-9]+)'\s*=>\s*\[\s*\n"
    r"\s*'name'\s*=>\s*'((?:[^'\\]|\\.)*)',\s*\n"
    r"\s*'price'\s*=>\s*\d+,\s*\n"
    r"\s*'dir'\s*=>\s*'([^']+)'", re.M)
HEADING = re.compile(r"^\d+\. ([А-ЯЁA-Z ,—-]+)$", re.M)
LINK = re.compile(r"https://marzhavbetone\.ru(/[a-z0-9/-]*\.html)\?\S*")


def catalog() -> dict[str, dict]:
    """sku → название, папка, адрес страницы — из конфига кассы."""
    text = CONFIG.read_text(encoding="utf-8")
    out = {}
    for sku, name, folder in ENTRY.findall(text):
        if sku == "test1":
            continue
        pages = sorted((ROOT / "products").glob(f"{sku}-*.html"))
        out[sku] = {"name": name.replace("\\'", "'"), "dir": folder,
                    "url": f"/products/{pages[0].name}" if pages else ""}
    return out


def sku_by_url(items: dict[str, dict]) -> dict[str, str]:
    return {item["url"]: sku for sku, item in items.items() if item["url"]}


def readiness() -> dict[str, str]:
    import yaml
    data = yaml.safe_load(READINESS.read_text(encoding="utf-8"))
    return {sku: row["статус"] for sku, row in (data.get("статусы") or {}).items()}


def short_name(name: str) -> str:
    inner = re.search(r"«(.+)»", name)
    text = inner.group(1) if inner else name
    return text.split(":")[0].strip()


def sections(text: str) -> dict[str, str]:
    """Заголовок раздела START-HERE → его тело до следующего заголовка."""
    marks = list(HEADING.finditer(text))
    out = {}
    for i, mark in enumerate(marks):
        stop = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[mark.group(1).strip()] = text[mark.end():stop]
    return out


def first_paragraph(body: str) -> str:
    """Первый абзац раздела без строк-ссылок: ссылку страница даёт кнопкой."""
    for block in re.split(r"\n\s*\n", body.strip()):
        lines = [line for line in block.splitlines() if not LINK.search(line)]
        text = re.sub(r"\s+", " ", " ".join(lines)).strip()
        if text and not text.startswith("---"):
            # «…материалы под неё:» — двоеточие стояло перед ссылкой.
            return text[:-1] + "." if text.endswith(":") else text
    return ""


def step_for(sku: str, item: dict, items: dict[str, dict], status: dict[str, str]) -> dict:
    path = STORAGE / item["dir"] / START_HERE
    if not path.is_file():
        raise SystemExit(f"{sku}: нет {path.relative_to(ROOT)} — шаг после покупки не из чего взять")
    parts = sections(path.read_text(encoding="utf-8"))
    for title in (CHANGED, OTHER):
        if title not in parts:
            raise SystemExit(f"{sku}: в {START_HERE} нет раздела «{title}»")

    by_url = sku_by_url(items)
    changed = parts[CHANGED]
    target = next((m.group(1) for m in LINK.finditer(changed) if m.group(1) in by_url), "")
    target_sku = by_url.get(target, "")
    if target_sku and target_sku not in status:
        raise SystemExit(f"{target_sku}: нет статуса в {READINESS.relative_to(ROOT)}")

    if target_sku and status[target_sku] not in NOT_READY:
        return {
            "kind": "product",
            "sku": target_sku,
            "url": target,
            "title": CHANGED.capitalize(),
            "lead": first_paragraph(changed),
            "name": short_name(items[target_sku]["name"]),
            "held": "",
        }

    other = parts[OTHER]
    neutral = next((m.group(1) for m in LINK.finditer(other)), "")
    if not neutral:
        raise SystemExit(f"{sku}: в разделе «{OTHER}» нет ссылки")
    return {
        "kind": "neutral",
        "sku": "",
        "url": neutral,
        "title": OTHER.capitalize(),
        "lead": first_paragraph(other),
        "name": "Пройти разбор ситуации",
        # Какой товар START-HERE называет, но страница успеха не ведёт в
        # него из-за статуса. В интерфейс не выводится — только в показ.
        "held": f"{target_sku} ({status[target_sku]})" if target_sku else "",
    }


def build_table() -> dict[str, dict]:
    items = catalog()
    status = readiness()
    missing = sorted(set(items) - set(status))
    if missing:
        raise SystemExit(f"нет статуса готовности у {missing}: {READINESS.relative_to(ROOT)}")
    return {sku: step_for(sku, item, items, status) for sku, item in sorted(items.items())}


BLOCK = """  <!-- upsell:begin -->
  <script>
    // Таблица собирается tools/build_upsell.py из 00-START-HERE.txt товаров
    // и tools/product_readiness.yaml. Руками не правится: разойдётся с
    // архивом покупателя (проверка — tools/test_commercial_journey.py).
    window.MVB_UPSELL = %(map)s;
  </script>
  <!-- upsell:end -->
"""


def render(text: str, table: dict) -> str:
    block = BLOCK % {"map": json.dumps(table, ensure_ascii=False, indent=2)}
    if BEGIN in text:
        start = text.index(BEGIN)
        finish = text.index(END) + len(END) + 1
        return text[:start] + block + text[finish:]
    anchor = text.rindex("</body>")
    return text[:anchor] + block + text[anchor:]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    table = build_table()
    text = PAGE.read_text(encoding="utf-8")
    fresh = render(text, table)

    print(f"Шаг после покупки: {len(table)} товаров")
    for sku, item in table.items():
        note = f", START-HERE называет {item['held']}" if item["held"] else ""
        print(f"   {sku:<4}→ {item['url']} ({item['kind']}{note})")

    if args.check:
        if fresh != text:
            print("\nsuccess.html разошёлся с источником: python3 tools/build_upsell.py --write")
            return 1
        print("\nsuccess.html совпадает с источником")
        return 0
    if not args.write:
        print("\nпоказ, файл не изменён. Вставить — с --write")
        return 0
    PAGE.write_text(fresh, encoding="utf-8")
    print("\nзаписано: success.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
