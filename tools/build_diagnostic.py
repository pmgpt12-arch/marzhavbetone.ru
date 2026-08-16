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


def шапка() -> str:
    """Канонная шапка из data/site/navigation.yaml, а не своя копия.

    Здесь стояла собственная разметка шапки с навигацией «Главная, Каталог,
    Бесплатно, Калькулятор». Пока она жила своей жизнью, любой прогон
    `--write` возвращал странице ту навигацию, от которой сайт уже ушёл:
    файл на диске правил `build_nav.py`, а генератор при следующем запуске
    молча откатывал правку. Такой откат не виден ни в диффе данных, ни в
    проверке — он случается только при следующей пересборке.
    """
    import yaml

    from build_nav import собрать

    данные = yaml.safe_load(
        (ROOT / "data" / "site" / "navigation.yaml").read_text(encoding="utf-8"))
    return собрать(данные, "diagnostika.html", None)


def load_tree() -> tuple[list[dict], list[dict]]:
    """Узкий разбор: файл читает и правит человек."""
    questions: list[dict] = []
    scenarios: list[dict] = []
    section = None
    cur: dict | None = None
    field: str | None = None
    block_indent: int | None = None
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
            block_indent = None
        if cur is None:
            continue
        # Продолжение свёрнутого блока (`>`), определяемое отступом.
        #
        # Здесь стояло условие «строка без двоеточия — продолжение», и оно
        # молча теряло текст. Замер 16.08.2026: у сценария S-7 поле `means`
        # пришло на страницу пустым, потому что его вторая строка —
        # «…здесь не работает: требование» — содержит двоеточие и была
        # разобрана как новый ключ. Пустым при этом оказался самый частый
        # сценарий: банкротство спрашивается первым вопросом, и на него
        # приходится половина всех путей. В YAML продолжение блока задаётся
        # отступом, двоеточие внутри текста ничего не значит.
        if field and block_indent is not None and indent > block_indent:
            if field == "when":
                cur["when"].update({
                    k: (v.strip() == "yes") for k, v in
                    re.findall(r"(\w+):\s*(yes|no)", text)})
            else:
                cur[field] = (cur.get(field, "") + " " + text).strip()
            continue
        if indent >= 4 and ":" in text and not text.startswith("- "):
            name, _, rest = text.partition(":")
            name, rest = name.strip(), rest.strip()
            if name == "when":
                cur["when"] = {
                    k: (v.strip() == "yes") for k, v in
                    re.findall(r"(\w+):\s*(yes|no)", rest)}
                field = "when"
                block_indent = indent
            elif rest in (">", "|"):
                cur[name] = ""
                field = name
                block_indent = indent
            else:
                cur[name] = rest
                field = name
                block_indent = None
        elif field and field != "when":
            cur[field] = (cur.get(field, "") + " " + text).strip()
        elif field == "when":
            cur["when"].update({
                k: (v.strip() == "yes") for k, v in
                re.findall(r"(\w+):\s*(yes|no)", text)})
    return questions, scenarios


def longest_path(questions: list[dict], scenarios: list[dict]) -> int:
    """Сколько вопросов человек ответит в худшем случае.

    Считается перебором всех сочетаний ответов по той же логике, что и на
    странице: следующий вопрос задаётся, только если он ещё встречается в
    условиях сценариев. Число нужно в тексте страницы, и брать его из головы
    нельзя — прежняя редакция обещала «восемь вопросов», приняв за путь
    размер словаря вопросов.
    """
    import itertools

    ids = [q["id"] for q in questions]
    самый_длинный = 0
    for сочетание in itertools.product([True, False], repeat=len(ids)):
        ответы_истины = dict(zip(ids, сочетание))
        ответы: dict[str, bool] = {}
        шагов = 0
        while True:
            if any(all(ответы.get(k) == v for k, v in s["when"].items())
                   for s in scenarios):
                break
            дальше = next((q for q in ids if q not in ответы
                           and any(q in s["when"] for s in scenarios)), None)
            if дальше is None:
                break
            ответы[дальше] = ответы_истины[дальше]
            шагов += 1
        самый_длинный = max(самый_длинный, шагов)
    return самый_длинный


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
        f'          <fieldset class="dq" data-q="{q["id"]}">\n'
        f'            <legend>{html.escape(q["text"])}</legend>\n'
        + (f'            <p class="dq-hint">{html.escape(q["hint"])}</p>\n'
           if q.get("hint") else "")
        + '            <div class="dopts">\n'
          '              <button type="button" data-a="yes" aria-pressed="false">Да</button>\n'
          '              <button type="button" data-a="no" aria-pressed="false">Нет</button>\n'
          '            </div>\n'
          '          </fieldset>' for q in questions)

    # Длина пути считается по самому дереву, а не берётся из головы. Прежний
    # текст обещал «восемь вопросов», хотя восемь — это размер словаря
    # вопросов, а не путь: следующий вопрос задаётся только если он ещё может
    # изменить исход. Перебор всех 2^8 сочетаний ответов даёт путь от одного
    # до пяти вопросов, и половина сочетаний заканчивается после первого.
    самый_длинный = longest_path(questions, scenarios)

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
    /* Композиция: слева — что это и что человек получит, справа — сам
       вопрос. До этого страница была узкой колонкой по центру, и на 1366px
       её содержимое занимало 846px при экране 768 — то есть пол-экрана
       пустоты под маленькой формой. Форму при этом на всю ширину не тянем:
       строка ответа шириной в экран читается хуже, а не лучше. */
    .dpage{{max-width:1180px;margin:0 auto;padding:44px 24px 80px}}
    .dgrid{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.05fr);
      gap:clamp(32px,4vw,64px);align-items:start}}
    .dintro h1{{margin:10px 0 14px;font-size:clamp(30px,3.2vw,46px);line-height:1.04;letter-spacing:-.03em}}
    .dintro .lead{{margin:0 0 22px;font-size:clamp(16px,1.3vw,19px);line-height:1.5;color:#4f5154}}
    /* Условия — списком, а не абзацем: их читают взглядом, а не по словам. */
    .dfacts{{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 24px;padding:0;list-style:none}}
    .dfacts li{{padding:7px 13px;background:#242629;color:#e9e5dc;font-size:13.5px;font-weight:700}}
    .dpromise{{margin:0;padding:20px 22px;background:#fff;border-left:5px solid #ff5a00}}
    .dpromise p{{margin:0 0 10px;font-size:13px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;color:#65676a}}
    .dpromise ol{{margin:0;padding-left:20px;line-height:1.65}}
    .dpromise li{{margin-bottom:4px}}

    .dcard{{padding:clamp(24px,2.4vw,34px);background:#fff;border:1px solid #a9a49a;box-shadow:8px 8px 0 #c8c3b9}}
    .dstep{{display:flex;align-items:center;gap:12px;margin-bottom:18px}}
    .dstep span{{font-size:13px;font-weight:900;letter-spacing:.06em;color:#65676a;white-space:nowrap}}
    .dbar{{flex:1;height:4px;background:#e2ddd3}}
    .dbar i{{display:block;height:100%;background:#ff5a00;transition:width .25s ease}}
    .dq{{margin:0;padding:0;border:0}}
    .dq[hidden]{{display:none}}
    .dq legend{{padding:0;font-size:clamp(21px,1.9vw,27px);font-weight:900;line-height:1.18;letter-spacing:-.02em}}
    .dq-hint{{margin:12px 0 0;color:#65676a;font-size:14.5px;line-height:1.55}}
    .dq .dopts{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:22px}}
    .dq button{{padding:17px 20px;border:2px solid #242629;background:#e9e5dc;
      font:900 17px Arial;cursor:pointer;transition:background-color .12s,color .12s}}
    .dq button:hover{{background:#242629;color:#e9e5dc}}
    .dq button:focus-visible{{outline:3px solid #ff5a00;outline-offset:2px}}
    .dq button[aria-pressed="true"]{{background:#242629;color:#e9e5dc;border-color:#ff5a00}}
    .dback{{margin-top:18px;background:none;border:0;padding:0;color:#65676a;
      font:14px Arial;text-decoration:underline;cursor:pointer}}
    .dback[hidden]{{display:none}}

    .dresult{{margin-top:0;padding:clamp(24px,2.4vw,34px);background:#242629;color:#e9e5dc}}
    .dresult h2{{margin:0 0 8px;color:#c7ff2e;font-size:clamp(23px,2.4vw,32px);line-height:1.1}}
    .dresult .dpain{{margin:0 0 16px;color:#a9a49a;font-size:13px;text-transform:uppercase;letter-spacing:.05em}}
    .dresult p{{line-height:1.6}}
    .dsteps{{margin:20px 0 0;padding-left:20px;line-height:1.6}}
    .dsteps li{{margin-bottom:7px}}
    .dnext{{margin-top:22px;padding-top:20px;border-top:1px solid rgba(233,229,220,.25)}}
    .dnext a{{color:#c7ff2e}}
    .dnext .button{{margin-top:12px}}
    .dagain{{margin-top:20px;background:none;border:0;color:#a9a49a;font:14px Arial;text-decoration:underline;cursor:pointer}}
    /* На узком экране вопрос идёт первым. В одну колонку карточка иначе
       уезжает под весь рассказ о пользе: замер на 390px — до первого
       вопроса около тысячи пикселей прокрутки, то есть человек листает
       мимо самого действия. Объяснение остаётся ниже, для тех, кому оно
       нужно до начала. */
    @media(max-width:1000px){{.dgrid{{grid-template-columns:1fr;gap:28px}}
      .dside{{order:-1}}}}
    @media(max-width:700px){{.dpage{{padding:30px 18px 64px}}
      .dq .dopts{{grid-template-columns:1fr}}}}
  </style>
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
  </script>
</head>
<body>
  {шапка()}

  <main class="dpage">
    <nav aria-label="Хлебные крошки" class="breadcrumbs">
      <a href="/">Главная</a> · <span>Диагностика</span>
    </nav>

    <div class="dgrid">
      <div class="dintro">
        <p class="eyebrow">БЕСПЛАТНО · БЕЗ РЕГИСТРАЦИИ</p>
        <h1>Где на вашем объекте застряли деньги</h1>
        <p class="lead">Объём сделан, а оплаты нет — и причина у каждого случая своя: договор, допработы, документация, приёмка или удержание. Ответьте на несколько вопросов о положении дел, и мы назовём сценарий и документы, которые его закрывают.</p>
        <ul class="dfacts">
          <li>{самый_длинный} вопросов максимум</li>
          <li>меньше минуты</li>
          <li>без регистрации</li>
          <li>ответы остаются в браузере</li>
        </ul>
        <div class="dpromise">
          <p>Что вы получите</p>
          <ol>
            <li>Название сценария — как эта ситуация называется на деле.</li>
            <li>Что в ней решает исход и чем рискуют деньги.</li>
            <li>Первый шаг — что сделать раньше остального.</li>
            <li>Документы, которые этот случай закрывают.</li>
          </ol>
        </div>
      </div>

      <div class="dside">
        <div class="dcard" id="dcard">
          <div class="dstep" id="dstep">
            <span id="dstep-label">Вопрос 1</span>
            <span class="dbar"><i id="dbar" style="width:0%"></i></span>
          </div>
          <form id="dform">
{qs}
          </form>
          <button type="button" class="dback" id="dback" hidden>← Вернуться к предыдущему вопросу</button>
        </div>
        <div id="dresult" class="dresult" hidden></div>
      </div>
    </div>
  </main>

  <footer><div class="footer-inner"><p>© «Маржа в бетоне»</p><p><a href="/contacts.html">Реквизиты</a> · <a href="/offer.html">Оферта</a> · <a href="/payment-delivery.html">Оплата и получение</a> · <a href="/refund.html">Возврат</a></p></div></footer>

  <script>
  // Сценарии собраны из data/business/diagnostic.yaml и money-pains.yaml
  // прогоном tools/build_diagnostic.py. Руками этот блок не правится:
  // маршрут обязан вести в комплект, который продаётся сейчас.
  const SCENARIOS = {json.dumps(payload, ensure_ascii=False)};
  const answers = {{}};
  const order = [];            // порядок ответов — чтобы можно было вернуться
  const MAXQ = {самый_длинный};
  const form = document.getElementById('dform');
  const out = document.getElementById('dresult');
  const card = document.getElementById('dcard');
  const back = document.getElementById('dback');
  const stepLabel = document.getElementById('dstep-label');
  const bar = document.getElementById('dbar');

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

  function finish(block) {{
    form.querySelectorAll('.dq').forEach(b => b.hidden = true);
    card.hidden = true;
    out.innerHTML = block + '<button type="button" class="dagain" id="dagain">Пройти заново</button>';
    out.hidden = false;
    document.getElementById('dagain').addEventListener('click', reset);
    out.scrollIntoView({{behavior: 'smooth', block: 'nearest'}});
  }}

  function render() {{
    const hit = match();
    if (hit) {{
      let block = '<p class="dpain">' + hit.pain + '</p>';
      block += '<h2>' + hit.verdict + '</h2><p>' + hit.means + '</p>';
      block += '<div class="dnext">';
      if (hit.free) block += '<p><b>Первый шаг</b> — проверить у себя по <a href="' + hit.free + '">бесплатным материалам этого сценария</a>.</p>';
      if (hit.entry) block += '<p>Нужен один документ, а не весь комплект — <a href="' + hit.entry.url + '">от ' + hit.entry.price + ' ₽</a>.</p>';
      block += '<p><a class="button" href="' + hit.core.url + '">Комплект по этому сценарию — ' + hit.core.price + ' ₽</a></p>';
      block += '</div>';
      finish(block);
      if (typeof window.mvbTrackGoal === 'function') window.mvbTrackGoal('diagnostic_complete');
      return;
    }}
    const box = nextUnanswered();
    if (!box) {{
      // Сочетание ответов, под которое сценария не написано. Перебор всех
      // сочетаний даёт такие в 32 случаях из 256, и до этой правки страница
      // просто гасила последний вопрос и не показывала ничего: пустой экран
      // вместо ответа. Тупик закрыт выходом в разделы, а не выдуманным
      // вердиктом — сочинить диагноз там, где его нет, хуже пустого экрана.
      let block = '<p class="dpain">Смешанный случай</p>';
      block += '<h2>Ситуация не сводится к одному сценарию</h2>';
      block += '<p>По вашим ответам сошлись признаки сразу нескольких случаев, и одного маршрута для них нет. Это не тупик: ниже разделы, где сценарии разобраны по отдельности.</p>';
      block += '<div class="dnext">';
      block += '<p><b>Первый шаг</b> — <a href="/materialy/">бесплатные материалы</a>: проверочные листы по каждому этапу.</p>';
      block += '<p>Разборы по темам — <a href="/articles/">все разборы</a>.</p>';
      block += '<p><a class="button" href="/katalog.html">Открыть каталог комплектов</a></p>';
      block += '</div>';
      finish(block);
      if (typeof window.mvbTrackGoal === 'function') window.mvbTrackGoal('diagnostic_complete');
      return;
    }}
    form.querySelectorAll('.dq').forEach(b => b.hidden = b !== box);
    card.hidden = false;
    out.hidden = true;
    const n = order.length + 1;
    stepLabel.textContent = 'Вопрос ' + n;
    bar.style.width = Math.round((order.length / MAXQ) * 100) + '%';
    back.hidden = order.length === 0;
  }}

  function reset() {{
    for (const k of Object.keys(answers)) delete answers[k];
    order.length = 0;
    form.querySelectorAll('button[data-a]').forEach(b => b.setAttribute('aria-pressed', 'false'));
    out.hidden = true;
    card.hidden = false;
    render();
  }}

  back.addEventListener('click', () => {{
    const last = order.pop();
    if (!last) return;
    delete answers[last];
    form.querySelectorAll('.dq[data-q="' + last + '"] button[data-a]')
        .forEach(b => b.setAttribute('aria-pressed', 'false'));
    out.hidden = true;
    card.hidden = false;
    render();
  }});

  form.addEventListener('click', e => {{
    const btn = e.target.closest('button[data-a]');
    if (!btn) return;
    const box = btn.closest('.dq');
    const q = box.dataset.q;
    const first = order.length === 0;
    if (!(q in answers)) order.push(q);
    answers[q] = btn.dataset.a === 'yes';
    box.querySelectorAll('button[data-a]').forEach(b =>
      b.setAttribute('aria-pressed', String(b === btn)));
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
