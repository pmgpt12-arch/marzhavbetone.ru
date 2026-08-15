#!/usr/bin/env python3
"""Блок «Изнутри стройки» — из data/business/cases.yaml, а не из разметки.

Прежний вид блока был сеткой блог-карточек: картинка сверху, заголовок,
лид, ссылка. Это самый обычный паттерн карточки контента в вебе, и он
ровно ничего не сообщает о том, что за материалом стоит реальная
практика. Хуже: карточки были светлее и легче продуктовых, то есть
читались как менее важные.

Здесь карточка — досье: номер дела, маркер типа, период, стороны, сумма
и точка ошибки. Крупная фотография снята намеренно — она и делала блок
похожим на блог, а стоковая иллюстрация подлинности не добавляет.

Про честность маркеров. Из трёх материалов документированный случай
один; два других — расчёт и архетип. `kind` в данных различает их, и
маркер «РЕАЛЬНЫЕ СОБЫТИЯ» ставится только настоящему делу. Единый
премиальный вид у блока при этом остаётся: расходятся подписи, а не
оформление.

    python3 tools/build_cases.py           # показать
    python3 tools/build_cases.py --write   # собрать блок на главной
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "business" / "cases.yaml"
PAGE = ROOT / "index.html"

OPEN = '    <section class="section cases" id="cases">'


def esc(text: str) -> str:
    return (text or "").strip().replace("&", "&amp;").replace("<", "&lt;")


def card(item: dict) -> str:
    slug = item["slug"]
    parts = [
        f'        <a class="case-card case-{item["kind"]}" href="articles/{slug}.html">',
        '          <div class="case-head">',
        f'            <span class="case-label">{esc(item["label"])}</span>',
        f'            <span class="case-marker">{esc(item["marker"])}</span>',
        "          </div>",
        f'          <p class="case-tag">{esc(item["tag"])}</p>',
        f'          <h3>{esc(item["title"])}</h3>',
        '          <dl class="case-facts">',
    ]
    if item.get("period"):
        parts.append(f'            <div><dt>Период</dt><dd>{esc(item["period"])}</dd></div>')
    if item.get("parties"):
        parts.append(f'            <div><dt>Стороны</dt><dd>{esc(item["parties"])}</dd></div>')
    if item.get("figure"):
        note = esc(item.get("figure_note") or "")
        parts.append(f'            <div><dt>{note or "Сумма"}</dt>'
                     f'<dd class="case-figure">{esc(item["figure"])}</dd></div>')
    parts += [
        "          </dl>",
        '          <p class="case-error"><span>Точка ошибки</span>'
        f'{esc(item["error_point"])}</p>',
        '          <span class="case-open">Открыть разбор →</span>',
        "        </a>",
    ]
    return "\n".join(parts)


def block(items: list[dict]) -> str:
    cards = "\n".join(card(i) for i in items)
    return (
        f"{OPEN}\n"
        '      <div class="section-head row">\n'
        '        <div><p class="eyebrow">ИЗНУТРИ СТРОЙКИ</p>'
        "<h2>То, что не написано в договоре</h2>\n"
        '        <p class="lead">Как деньги подрядчика уходят на стороне: кто принимал '
        "решения, чем они обосновывались и в какой момент спор было уже не выиграть.</p></div>\n"
        '        <a class="text-link" href="articles/">Все разборы →</a>\n'
        "      </div>\n"
        f'      <div class="case-grid">\n{cards}\n      </div>\n'
        "    </section>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    import yaml
    items = yaml.safe_load(DATA.read_text(encoding="utf-8"))["cases"]

    missing = [i["slug"] for i in items
               if not (ROOT / "articles" / f"{i['slug']}.html").exists()]
    if missing:
        print(f"Статьи не найдены: {', '.join(missing)}")
        return 1

    real = sum(1 for i in items if i["kind"] == "case")
    print(f"Карточек: {len(items)}; из них документированных случаев: {real}")
    for i in items:
        print(f"   {i['label']:<10} {i['marker']:<20} {i['slug']}")
    if real < len(items):
        print(f"\n  Маркер «реальные события» стоит только у {real}: остальные — "
              f"расчёт и архетип, и называть их делом было бы неправдой.")

    if not args.write:
        print("\nпоказ, файл не изменён. Собрать — с --write")
        return 0

    text = PAGE.read_text(encoding="utf-8")
    old = re.search(re.escape(OPEN) + r".*?\n    </section>\n", text, re.S)
    if not old:
        print("Блок кейсов на главной не найден")
        return 1
    PAGE.write_text(text.replace(old.group(0), block(items)), encoding="utf-8")
    print("\nзаписано: index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
