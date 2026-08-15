#!/usr/bin/env python3
"""Собирает /diagnostika.html из лестницы боли и дерева сценариев.

Страница генерируется, а не пишется рукой, по одной причине: маршрут
обязан вести в тот комплект, который действительно продаётся сейчас. Цена
и состав каталога меняются решением владельца, и страница, набранная
руками, разойдётся с кассой молча.

Источники истины:
  data/business/diagnostic.yaml   — вопросы и сценарии;
  data/business/money-pains.yaml  — боль → бесплатник, вход, комплект;
  products-config.php             — название и цена, истина по каталогу.

    python3 tools/build_diagnostic.py           # показать, что изменится
    python3 tools/build_diagnostic.py --write   # записать
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_offer import catalogue, load_pains  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TREE = ROOT / "data" / "business" / "diagnostic.yaml"
OUT = ROOT / "diagnostika.html"
SITE = "https://marzhavbetone.ru"


def load_tree() -> tuple[list[dict], list[dict]]:
    """Узкий разбор: файл читает и правит человек."""
    questions: list[dict] = []
    scenarios: list[dict] = []
    section = None
    cur: dict | None = None
    field: str | None = None
    for raw in TREE.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        text = line.strip()
        if indent == 0 and text.endswith(":"):
            section = text[:-1]
            cur = None
            continue
        if indent == 2 and text.startswith("- "):
            cur = {}
            (questions if section == "questions" else scenarios).append(cur)
            text = text[2:].strip()
            indent = 4
        if cur is None:
            continue
        if indent >= 4 and ":" in text and not text.startswith("- "):
            name, _, rest = text.partition(":")
            name, rest = name.strip(), rest.strip()
            if name == "when":
                cur["when"] = {
                    k: (v.strip() == "yes") for k, v in
                    re.findall(r"(\w+):\s*(yes|no)", rest)}
                field = "when"
            elif rest in (">", "|"):
                cur[name] = ""
                field = name
            else:
                cur[name] = rest
                field = name
        elif field and field != "when":
            cur[field] = (cur.get(field, "") + " " + text).strip()
        elif field == "when":
            cur["when"].update({
                k: (v.strip() == "yes") for k, v in
                re.findall(r"(\w+):\s*(yes|no)", text)})
    return questions, scenarios


def build() -> str:
    questions, scenarios = load_tree()
    pains = load_pains()
    skus = catalogue()

    payload = []
    for s in scenarios:
        pain = pains.get(s["pain"])
        if not pain:
            raise SystemExit(f"{s['id']}: боли {s['pain']} нет в лестнице")
        core = pain["core"]
        entry = pain.get("entry")
        if core["sku"] not in skus:
            raise SystemExit(f"{s['id']}: комплект {core['sku']} не продаётся")

        def page(sku: str) -> str:
            hits = sorted((ROOT / "products").glob(f"{sku}-*.html"))
            if not hits:
                raise SystemExit(f"{s['id']}: страницы {sku} нет")
            return "/products/" + hits[0].name

        item = {
            "id": s["id"],
            "when": s["when"],
            "verdict": s["verdict"],
            "means": s["means"],
            "pain": pain["title"],
            "free": "/" + pain["free"][0] if pain["free"] else "",
            "core": {"url": page(core["sku"]), "price": skus[core["sku"]]},
        }
        if entry and entry["sku"] in skus:
            item["entry"] = {"url": page(entry["sku"]),
                             "price": skus[entry["sku"]]}
        payload.append(item)

    qs = "\n".join(
        f'      <fieldset class="dq" data-q="{q["id"]}">\n'
        f'        <legend>{html.escape(q["text"])}</legend>\n'
        + (f'        <p class="dq-hint">{html.escape(q["hint"])}</p>\n'
           if q.get("hint") else "")
        + '        <button type="button" data-a="yes">Да</button>\n'
          '        <button type="button" data-a="no">Нет</button>\n'
          '      </fieldset>' for q in questions)

    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebApplication", "name": "Диагностика ситуации подрядчика",
         "applicationCategory": "BusinessApplication", "operatingSystem": "Any",
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "RUB"},
         "url": f"{SITE}/diagnostika.html"},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Главная",
             "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Диагностика",
             "item": f"{SITE}/diagnostika.html"}]}]}

    desc = ("Восемь вопросов о вашей ситуации на объекте — и понятный "
            "сценарий: что происходит, что проверить и какие документы "
            "закрывают именно этот случай.")

    return f'''<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{desc}">
  <meta property="og:title" content="Диагностика: что происходит и что делать">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{SITE}/diagnostika.html">
  <link rel="canonical" href="{SITE}/diagnostika.html">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <title>Диагностика ситуации подрядчика: что происходит и что делать — Маржа в бетоне</title>
  <link rel="stylesheet" href="styles.css">
  <style>
    .dpage{{max-width:820px;margin:0 auto;padding:56px 24px 90px}}
    .dq{{margin:0 0 18px;padding:22px 24px;background:#fff;border:1px solid #a9a49a;border-left:5px solid #ff5a00}}
    .dq[hidden]{{display:none}}
    .dq legend{{padding:0;font:700 18px/1.3 Arial}}
    .dq-hint{{margin:8px 0 0;color:#65676a;font-size:14px;line-height:1.5}}
    .dq button{{margin:16px 10px 0 0;padding:12px 26px;border:1px solid #242629;background:#e9e5dc;font:700 15px Arial;cursor:pointer}}
    .dq button:hover{{background:#242629;color:#e9e5dc}}
    .dresult{{margin-top:28px;padding:28px;background:#242629;color:#e9e5dc}}
    .dresult h2{{margin:0 0 6px;color:#c7ff2e;font-size:clamp(22px,4vw,30px)}}
    .dresult .dpain{{margin:0 0 16px;color:#a9a49a;font-size:14px;text-transform:uppercase;letter-spacing:.04em}}
    .dresult p{{line-height:1.6}}
    .dnext{{margin-top:22px;padding-top:20px;border-top:1px solid rgba(233,229,220,.25)}}
    .dnext a{{color:#c7ff2e}}
    .dnext .button{{margin-top:12px}}
    .dagain{{margin-top:20px;background:none;border:0;color:#65676a;font:14px Arial;text-decoration:underline;cursor:pointer}}
    @media(max-width:700px){{.dpage{{padding:34px 18px 70px}}.dq{{padding:18px}}.dq button{{width:100%;margin:12px 0 0}}}}
  </style>
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
  </script>
</head>
<body>
  <header class="topbar">
    <a class="brand" href="/" aria-label="Маржа в бетоне, на главную"><span class="brand-mark">М</span><span>маржа в бетоне</span></a>
    <nav aria-label="Основная навигация"><a href="/">Главная</a><a href="/#catalog">Каталог</a><a href="/materialy/">Бесплатно</a><a href="/kalkulyator.html">Калькулятор</a></nav>
  </header>

  <main class="dpage">
    <nav aria-label="Хлебные крошки" class="breadcrumbs">
      <a href="/">Главная</a> · <span>Диагностика</span>
    </nav>

    <p class="eyebrow">БЕСПЛАТНО · БЕЗ РЕГИСТРАЦИИ</p>
    <h1>Что у вас происходит и что с этим делать</h1>
    <p class="lead">Восемь вопросов о положении на объекте. На выходе — название сценария, что в нём решает исход и какие документы его закрывают. Ни почты, ни телефона, ни названия компании: ответы никуда не отправляются и остаются в браузере.</p>

    <form id="dform">
{qs}
    </form>

    <div id="dresult" class="dresult" hidden></div>
  </main>

  <footer><div class="footer-inner"><p>© «Маржа в бетоне»</p><p><a href="/contacts.html">Реквизиты</a> · <a href="/offer.html">Оферта</a> · <a href="/payment-delivery.html">Оплата и получение</a> · <a href="/refund.html">Возврат</a></p></div></footer>

  <script>
  // Сценарии собраны из data/business/diagnostic.yaml и money-pains.yaml
  // прогоном tools/build_diagnostic.py. Руками этот блок не правится:
  // маршрут обязан вести в комплект, который продаётся сейчас.
  const SCENARIOS = {json.dumps(payload, ensure_ascii=False)};
  const answers = {{}};
  const form = document.getElementById('dform');
  const out = document.getElementById('dresult');

  function match() {{
    return SCENARIOS.find(s =>
      Object.entries(s.when).every(([q, v]) => answers[q] === v));
  }}

  function nextUnanswered() {{
    // Спрашиваем только то, что ещё может изменить исход.
    const asked = new Set(Object.keys(answers));
    for (const box of form.querySelectorAll('.dq')) {{
      const q = box.dataset.q;
      if (asked.has(q)) continue;
      if (SCENARIOS.some(s => q in s.when)) return box;
    }}
    return null;
  }}

  function render() {{
    const hit = match();
    if (hit) {{
      form.querySelectorAll('.dq').forEach(b => b.hidden = true);
      let block = '<p class="dpain">' + hit.pain + '</p>';
      block += '<h2>' + hit.verdict + '</h2><p>' + hit.means + '</p>';
      block += '<div class="dnext">';
      if (hit.free) block += '<p>Проверить у себя бесплатно — <a href="' + hit.free + '">материалы по этому сценарию</a>.</p>';
      if (hit.entry) block += '<p>Один документ по делу — <a href="' + hit.entry.url + '">от ' + hit.entry.price + ' ₽</a>.</p>';
      block += '<p><a class="button" href="' + hit.core.url + '">Комплект по этому сценарию — ' + hit.core.price + ' ₽</a></p>';
      block += '</div>';
      block += '<button type="button" class="dagain" id="dagain">Пройти заново</button>';
      out.innerHTML = block;
      out.hidden = false;
      if (typeof window.mvbTrackGoal === 'function') window.mvbTrackGoal('diagnostic_complete');
      document.getElementById('dagain').addEventListener('click', reset);
      out.scrollIntoView({{behavior: 'smooth', block: 'nearest'}});
      return;
    }}
    const box = nextUnanswered();
    form.querySelectorAll('.dq').forEach(b => b.hidden = b !== box);
    out.hidden = true;
  }}

  function reset() {{
    for (const k of Object.keys(answers)) delete answers[k];
    out.hidden = true;
    render();
  }}

  form.addEventListener('click', e => {{
    const btn = e.target.closest('button[data-a]');
    if (!btn) return;
    const first = Object.keys(answers).length === 0;
    answers[btn.closest('.dq').dataset.q] = btn.dataset.a === 'yes';
    if (first && typeof window.mvbTrackGoal === 'function') window.mvbTrackGoal('diagnostic_start');
    render();
  }});

  render();
  </script>
  <script src="/attribution.js"></script>
</body>
</html>
'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    page = build()
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if page == old:
        print("страница уже собрана и совпадает")
        return 0
    if not args.write:
        print(f"будет записано: {OUT.relative_to(ROOT)}, {len(page)} байт")
        print("прогон без записи; чтобы записать — --write")
        return 0
    OUT.write_text(page, encoding="utf-8")
    print(f"записано: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
