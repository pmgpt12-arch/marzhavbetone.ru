#!/usr/bin/env python3
"""Отчёт приёмочного аудита из замеров: числа в таблицы, без оценок.

Читает то, что снял `audit_after_redesign.py`, и складывает `audit-report.md`.
Вердикт и баллы здесь не выставляются намеренно: инструмент не умеет
смотреть на снимок, а «выглядит ли это настольной вёрсткой» — суждение.
Отчёт даёт основание для суждения и называет, чем каждое число померено.

Запуск:
    python3 tools/audit_report.py --dir audit-after-redesign
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text("utf-8")) if path.exists() else {}


def build(out: Path) -> str:
    m = load(out / "measurements.json")
    ov = load(out / "overflow.json")
    links = load(out / "links.json")
    seo = load(out / "seo.json")
    origin = (out / "origin-probe.txt").read_text("utf-8", "replace") \
        if (out / "origin-probe.txt").exists() else "НЕ ИЗМЕРЕНО"

    L: list[str] = []
    add = L.append

    add("# Приёмочный аудит боевого сайта")
    add("")
    add(f"Адрес: {m.get('url', '—')}. Замер: {m.get('measured_at', '—')}.")
    add("")
    add("Внешний контур — обычный раннер GitHub Actions, настоящий рендер "
        "Chromium. Он и есть источник истины по доступности, вёрстке, "
        "ссылкам и поисковому слою. SSH к reg.ru идёт отдельным разделом "
        "и отвечает только на вопрос, та ли версия лежит на origin: "
        "origin, проверяющий сам себя, о внешней доступности не говорит "
        "ничего.")
    add("")

    add("## Размеры страницы")
    add("")
    add("| viewport | scrollHeight | viewportHeight | screens | horizontal overflow |")
    add("|---|---|---|---|---|")
    for name, vp in m.get("viewports", {}).items():
        d = vp["doc"]
        flag = f"ДА, +{d['horizontal_overflow_px']}px" if d["horizontal_overflow"] else "нет"
        add(f"| {name} ({vp['width']}×{vp['height']}) | {d['scrollHeight']} | "
            f"{d['innerHeight']} | {d['screens']} | {flag} |")
    add("")
    add("`scrollWidth` / `clientWidth` документа по ширинам:")
    add("")
    for name, vp in m.get("viewports", {}).items():
        d = vp["doc"]
        add(f"- {name}: {d['scrollWidth']} / {d['clientWidth']}")
    add("")

    add("## Вёрстка: настольная или растянутая мобильная")
    add("")
    add("Признак меряется, а не оценивается: доля окна под контентом и "
        "число сеток, которые на этой ширине встали в две колонки и больше.")
    add("")
    add("| viewport | main, px | доля окна | самый широкий текст | сетки 2+ колонок |")
    add("|---|---|---|---|---|")
    for name, vp in m.get("viewports", {}).items():
        lay = vp["layout"]
        multi = [g for g in lay["grids"] if g["columns_per_row"] >= 2]
        add(f"| {name} | {lay['main_width']} | {lay['main_width_share']} | "
            f"{lay['widest_text_block']}px ({lay['widest_text_share']}) | "
            f"{len(multi)} из {len(lay['grids'])} |")
    add("")

    ref = m.get("viewports", {}).get("desktop-1440", {})
    add("## Порядок блоков сверху вниз (1440×900)")
    add("")
    add("| # | экранов от верха | высота | блок | заголовок |")
    add("|---|---|---|---|---|")
    for b in ref.get("blocks", []):
        label = b["id"] or (b["class"] or b["tag"])
        head = " / ".join(x for x in (b["eyebrow"], b["heading"]) if x) or "—"
        add(f"| {b['order']} | {b['screens_from_top']} | {b['height']} | "
            f"`{label}` | {head} |")
    add("")

    add("## Вылет элементов")
    add("")
    add("Скрытая ветка — элемент под `hidden` или `aria-hidden`: он в потоке "
        "не участвует и страницу не расширяет. Считается отдельно, чтобы "
        "закрытая панель корзины не выдавалась за дефект.")
    add("")
    add("| viewport | всего | в видимой ветке |")
    add("|---|---|---|")
    for name, items in ov.items():
        visible = [i for i in items if not i["hidden_branch"]]
        add(f"| {name} | {len(items)} | {len(visible)} |")
    add("")
    for name, items in ov.items():
        visible = [i for i in items if not i["hidden_branch"]]
        if not visible:
            continue
        add(f"### {name}")
        add("")
        add("| причина | категория | элемент | текст |")
        add("|---|---|---|---|")
        for i in visible[:40]:
            cats = ", ".join(i["categories"]) or "—"
            text = (i["text"] or "").replace("|", "\\|")[:60]
            add(f"| {' + '.join(i['reasons'])} | {cats} | `{i['path']}` | {text} |")
        if len(visible) > 40:
            add("")
            add(f"…ещё {len(visible) - 40}, полностью — в `overflow.json`.")
        add("")

    add("## Ссылки главной")
    add("")
    add(f"- якорей всего: {links.get('total_anchors', '—')}")
    add(f"- уникальных внутренних целей: {links.get('unique_internal', '—')}")
    add(f"- внешних: {links.get('external_count', '—')}")
    add(f"- пустой `href`: {len(links.get('empty_href', []))}")
    add(f"- якорь на несуществующий id: {len(links.get('bad_fragment', []))}")
    add(f"- битых (404/5xx/не ответил): {len(links.get('broken', []))}")
    add(f"- с переадресацией: {len(links.get('redirects', []))}")
    add("")
    if links.get("broken"):
        add("| код | адрес | где на странице |")
        add("|---|---|---|")
        for c in links["broken"]:
            add(f"| {c['status']} | {c['url']} | {', '.join(c['found_in'])} |")
        add("")
    if links.get("redirects"):
        add("| цепочка | адрес | конец |")
        add("|---|---|---|")
        for c in links["redirects"]:
            hops = " → ".join(str(h["status"]) for h in c["chain"])
            add(f"| {hops} | {c['url']} | {c['final']} |")
        add("")
    if links.get("bad_fragment"):
        add("Якоря в никуда: " + ", ".join(
            f"`{a['href']}` ({a['text']})" for a in links["bad_fragment"]))
        add("")

    add("### Все проверенные внутренние цели")
    add("")
    add("| код | адрес | раздел |")
    add("|---|---|---|")
    for c in links.get("checked", []):
        add(f"| {c['status']} | {c['url']} | {', '.join(c['found_in'])} |")
    add("")

    add("## Поисковый слой")
    add("")
    if seo:
        add(f"- `/` → {seo['home']['status']}")
        add(f"- `/index.html` → {seo['index_html']['status']}")
        add(f"- `robots.txt` → {seo['robots_txt']['status']}, строка Sitemap: "
            f"{seo['robots_txt']['has_sitemap_line']}, `Disallow: /`: "
            f"{seo['robots_txt']['disallow_all']}")
        add(f"- `sitemap.xml` → {seo['sitemap_xml']['status']}, адресов "
            f"{seo['sitemap_xml']['url_count']}")
        add(f"- canonical: `{seo['canonical']}`, совпадает с главной: "
            f"{seo['canonical_matches_home']}")
        add(f"- meta robots: `{seo['meta_robots']}`, noindex: {seo['noindex']}")
        add(f"- H1 на главной: {seo['h1_count']} — {seo['h1']}")
        add(f"- title ({seo['title_length']}): {seo['title']}")
        add(f"- description ({seo['description_length']}): {seo['description']}")
        add(f"- в карте сайта, но не в репозитории: {len(seo['sitemap_only_live'])}")
        add(f"- в репозитории, но не в карте: {len(seo['sitemap_only_repo'])}")
        for u in seo["sitemap_only_live"][:20]:
            add(f"  - только на бою: {u}")
        for u in seo["sitemap_only_repo"][:20]:
            add(f"  - только в репозитории: {u}")
    else:
        add("НЕ ИЗМЕРЕНО.")
    add("")

    add("## Клиентский интерфейс: продукты и внутренние коды")
    add("")
    ui = m.get("client_ui", {})
    add(f"- карточек продуктов на главной: {ui.get('product_cards')}")
    add(f"- строк таблиц внутри `main`: {ui.get('table_rows_in_main')}")
    add(f"- упоминаний файлов (`.docx`/`.xlsx`/`.pdf`) в видимом тексте: "
        f"{ui.get('file_extension_mentions')}")
    add(f"- внутренние коды линейки в тексте страницы: "
        f"{ui.get('internal_codes_found') or 'не найдены'}")
    add("")

    add("## Origin по SSH (дополнительная проверка)")
    add("")
    add("Не доказательство внешней доступности. Отвечает на один вопрос: "
        "лежит ли на origin та же версия, что отдаётся наружу.")
    add("")
    add("```")
    add(origin.rstrip())
    add("```")
    add("")

    add("## Снимки")
    add("")
    for name, vp in m.get("viewports", {}).items():
        add(f"- `{vp['screenshot']}` — {vp['width']}×{vp['height']}")
    add("")
    return "\n".join(L) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="audit-after-redesign")
    args = parser.parse_args()
    out = Path(args.dir)
    report = build(out)
    (out / "audit-report.md").write_text(report, "utf-8")
    print(f"Отчёт: {out / 'audit-report.md'}, {len(report)} знаков")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
