#!/usr/bin/env python3
"""Разовая пересборка главной: порядок блоков, а не косметика.

Замер 15.08.2026 после переноса каталога (playwright, 1440×900, высота
каждой секции `main > section`):

    catalog  1816   materials 1537   results  1425   situations 1320
    author   1255   hero       992   faq       949   checklist   898
    how-to-buy 790  topics     756   practice  695   telegram    586
    personal-review 550  contact 550  ticker    54
    ВСЕГО  14380px = 16,0 экрана

Из этого видно три вещи, которых не видно чтением разметки.

Первая: `#topics` («Бетон виден. Риски — не всегда»: договор, допработы,
закрытие, оплата) и `#results` («Деньги теряются не в момент оплаты»:
договор, выполнение, документация, КС, оплата) перечисляют одни и те же
этапы процесса разными словами. Это один блок, набранный дважды, — 756px
из них лишние.

Вторая: `#practice` (19 лет, 3 стороны, 12+ объектов) повторяет `#author`,
где те же 19 лет стоят надзаголовком, а 12+ объектов — строкой биографии.
Уникален там один факт — три стороны процесса, — и он переезжает в блок
доверия.

Третья: лента тем `.ticker` — 54px чистого украшения.

Что делает скрипт помимо снятия повторов:

  · заводит блок «Изнутри стройки» из трёх материалов и ставит его сразу
    после блока ситуаций — до сих пор разборы стояли одиннадцатым блоком
    из пятнадцати, ниже каталога и порядка покупки;
  · отделяет их от обычных разборов: было пять карточек в одном блоке,
    стало три и три под разными заголовками;
  · переносит «Как купить» на страницу каталога — там, где покупают;
  · сводит два промо-блока (Телеграм и персональный разбор) в один;
  · ужимает `#results` до одной лестницы этапов вместо двух перечней.

Ни один факт не сочиняется. Карточки «Изнутри стройки» собраны из того,
что уже опубликовано: надзаголовок и заголовок берутся из самой статьи,
подпись — из её описания или из текста карточки, которая уже стоит на
главной. Ни одной страницы не удаляется и ни один адрес не меняется.

    python3 tools/rebuild_home_2026-08-15.py           # показать
    python3 tools/rebuild_home_2026-08-15.py --write   # пересобрать
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
KATALOG = ROOT / "katalog.html"

# Три материала «изнутри стройки». Надзаголовок и заголовок — из статьи,
# подпись — из её описания либо из карточки, уже стоящей на главной.
# Ничего нового здесь не утверждается: каждая строка уже опубликована.
CASES = [
    ("pretenziya-za-chuzhuyu-kommunalku",
     "ПРЕТЕНЗИИ / НАВЯЗАННАЯ ВИНА",
     "Претензия за чужую коммуналку",
     "Долг застройщика перед управляющей компанией разложили на подрядчиков "
     "«пропорционально замечаниям по качеству»."),
    ("genpodryadchik-zarabatyvaet-na-vas",
     "УДЕРЖАНИЕ / МАРЖА В МОРОЗИЛКЕ",
     "Генподрядчик зарабатывает на вас больше, чем на стройке",
     "Как 5–10% удержания превращаются в сотни миллионов чужих денег."),
    ("podpisannaya-ks2-ne-znachit-chto-zaplatyat",
     "ОПЛАТА / КС-2 ПОДПИСАНА, ДЕНЕГ НЕТ",
     "Подписанная КС-2 не значит, что вам заплатят",
     "Почему акты подписаны, а деньги можно не платить годами."),
]

# Обычные разборы: те же карточки, что стояли в блоке, минус ушедшие в
# «Изнутри стройки». Разметка карточек берётся из страницы как есть.
KEEP_MATERIALS = [
    "avans-eto-ne-dengi-eto-kryuchok",
    "bankrotstvo-genpodryadchika-5-markerov",
    "skidka-15-procentov-na-tendere-eto-otbor-zhertv",
]


def fail(message: str) -> None:
    print(f"Пересборка не сделана: {message}", file=sys.stderr)
    raise SystemExit(1)


def take_section(text: str, marker: str) -> tuple[str, str]:
    """Вырезает секцию по её открывающей метке до закрывающего тега."""
    start = text.find(marker)
    if start < 0:
        fail(f"секция не найдена: {marker[:60]}")
    end = text.find("</section>", start)
    if end < 0:
        fail(f"секция не закрыта: {marker[:60]}")
    end += len("</section>\n")
    block = text[start:end]
    # Отступ перед секцией снимается вместе с ней, чтобы не копить пустые строки.
    before = text[:start].rstrip(" ")
    return block, before + text[end:]


def card_for(text: str, slug: str) -> str:
    m = re.search(r'<a class="material-card" href="articles/' + re.escape(slug)
                  + r'\.html">.*?</a>', text, re.S)
    if not m:
        fail(f"карточка разбора не найдена: {slug}")
    return m.group(0)


def image_of(card: str) -> str:
    m = re.search(r"<img [^>]*>", card)
    return m.group(0) if m else ""


def build_cases(index_text: str) -> str:
    items = []
    for number, (slug, tag, title, point) in enumerate(CASES, start=1):
        art = (ROOT / "articles" / f"{slug}.html")
        if not art.exists():
            fail(f"статья не найдена: {slug}")
        cover = ROOT / "assets" / f"{slug}.jpg"
        img = (f'<img src="assets/{slug}.jpg" alt="{title}" width="1536" '
               f'height="954" loading="lazy" decoding="async">'
               if cover.exists() else "")
        items.append(
            f'        <a class="case-card" href="articles/{slug}.html">\n'
            f"          {img}\n"
            f'          <div class="case-body">\n'
            f'            <p class="case-no">{number:02d}</p>\n'
            f'            <p class="case-tag">{tag}</p>\n'
            f"            <h3>{title}</h3>\n"
            f'            <p class="case-point">{point}</p>\n'
            f'            <span class="case-open">Открыть разбор →</span>\n'
            f"          </div>\n"
            f"        </a>"
        )
    cards = "\n".join(items)
    return (
        '    <section class="section cases" id="cases">\n'
        '      <div class="section-head row">\n'
        '        <div><p class="eyebrow">ИЗНУТРИ СТРОЙКИ</p>'
        "<h2>То, что не написано в договоре</h2></div>\n"
        '        <a class="text-link" href="articles/">Все разборы →</a>\n'
        "      </div>\n"
        f'      <div class="case-grid">\n{cards}\n      </div>\n'
        "    </section>\n\n"
    )


def build_materials(old: str) -> str:
    cards = "\n        ".join(card_for(old, slug) for slug in KEEP_MATERIALS)
    return (
        '    <section class="section dark" id="materials">\n'
        '      <div class="section-head row">\n'
        '        <div><p class="eyebrow">СВЕЖИЕ РАЗБОРЫ</p>'
        "<h2>Разбираем, где подрядчик теряет деньги</h2></div>\n"
        '        <a class="text-link light" href="articles/">Витрина разборов →</a>\n'
        "      </div>\n"
        f'      <div class="cards">\n        {cards}\n      </div>\n'
        "    </section>\n\n"
    )


RESULTS = """    <section class="section sales-result" id="results">
      <div><p class="eyebrow">КАК УСТРОЕНА СИСТЕМА</p><h2>Деньги теряются не в момент оплаты</h2><p class="lead">Основание для оплаты формируется намного раньше — от условий договора до оформленной сдачи. Ошибка на любом этапе становится основанием задержать, уменьшить или не платить.</p></div>
      <div class="result-list"><p><b>01</b> Договор</p><p><b>02</b> Выполнение и допработы</p><p><b>03</b> Исполнительная документация</p><p><b>04</b> КС-2 и КС-3</p><p><b>05</b> Оплата</p></div>
      <p><a class="text-link" href="#catalog">Посмотреть решения по этапам →</a></p>
    </section>

"""

NEXT_STEPS = """    <section class="section next-steps">
      <div><p class="eyebrow">TELEGRAM</p><h3>Разборы ошибок и стройка без официоза</h3><p>Для тех, кто пока не готов покупать: еженедельные разборы договоров, допработ, приёмки и оплаты.</p><a class="text-link" href="https://t.me/marzhavbetone" target="_blank" rel="noopener">Подписаться на канал →</a></div>
      <div><p class="eyebrow">ДОПОЛНИТЕЛЬНАЯ УСЛУГА</p><h3>Не уверены, какой пакет нужен?</h3><p>Персональный разбор объекта: договорная схема, карта рисков и приоритеты действий. Стоимость укажем после утверждения формата и объёма проверки.</p><a class="text-link product-select" href="#contact" data-product="Персональный разбор объекта">Запросить разбор →</a></div>
    </section>

"""

# Три стороны процесса — единственный факт, которого нет в блоке доверия.
# Он переезжает туда, а не пропадает вместе с секцией.
AUTHOR_FACTS = ('<dl class="hero-facts author-facts"><div><dt>19</dt><dd>лет в '
                'строительстве</dd></div><div><dt>3</dt><dd>стороны процесса: '
                'технический заказчик, генподрядчик, субподрядчик</dd></div>'
                '<div><dt>12+</dt><dd>объектов введено в эксплуатацию</dd></div></dl>')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    text = INDEX.read_text(encoding="utf-8")
    katalog = KATALOG.read_text(encoding="utf-8")
    before = len(text)

    cases_block = build_cases(text)

    # 1. Снимаются повторы и украшение.
    _, text = take_section(text, '<section class="ticker" aria-label="Темы проекта">')
    _, text = take_section(text, '<section class="section" id="topics">')
    _, text = take_section(text, '<section class="section" id="practice">')

    # 2. Блоки, которые переставляются или переписываются, вынимаются.
    materials_old, text = take_section(text, '<section class="section dark" id="materials">')
    _, text = take_section(text, '<section class="section sales-result" id="results">')
    steps, text = take_section(text, '<section class="section order-steps" id="how-to-buy">')
    _, text = take_section(text, '<section class="section telegram-promo" id="telegram">')
    _, text = take_section(text, '<section class="section personal-review">')

    materials_block = build_materials(materials_old)

    # 3. Порядок: ситуации → изнутри стройки → разборы → схема → решения.
    anchor = '    <section class="section solutions" id="catalog">'
    if anchor not in text:
        fail("блок решений не найден")
    text = text.replace(anchor, cases_block + materials_block + RESULTS + anchor, 1)

    # 4. Доверие получает факт о трёх сторонах; следом — что дальше.
    marker = '<p class="eyebrow">19 ЛЕТ В СТРОИТЕЛЬСТВЕ</p>'
    if marker not in text:
        fail("блок доверия не найден")
    text = text.replace(marker, marker, 1)
    author_close = '</div>\n    </section>'
    pos = text.find('id="author"')
    end = text.find("</section>", pos)
    text = text[:end] + f"      {AUTHOR_FACTS}\n    " + text[end:]

    faq_anchor = '    <section class="section faq" id="faq">'
    if faq_anchor not in text:
        fail("блок вопросов не найден")
    text = text.replace(faq_anchor, NEXT_STEPS + faq_anchor, 1)

    # 5. «Как купить» уезжает на страницу каталога — туда, где покупают.
    steps = steps.replace('id="how-to-buy"', 'id="how-to-buy"')
    kat_anchor = "  <footer>"
    if kat_anchor not in katalog:
        fail("подвал каталога не найден")
    if 'id="how-to-buy"' not in katalog:
        katalog = katalog.replace(kat_anchor, steps + "\n" + kat_anchor, 1)

    # 6. Ссылки на снятые якоря с главной ведут туда, где содержимое теперь.
    text = text.replace('href="#how-to-buy"', 'href="katalog.html#how-to-buy"')

    print(f"главная: {before} → {len(text)} знаков")
    print("снято: .ticker, #topics (повтор #results), #practice (повтор #author)")
    print("заведено: #cases — 3 материала изнутри стройки")
    print(f"разборы: 5 карточек → {len(KEEP_MATERIALS)}")
    print("перенесено на katalog.html: #how-to-buy")
    print("сведено в один блок: #telegram + .personal-review")

    if not args.write:
        print("\nпоказ, файлы не изменены. Записать — с --write")
        return 0

    INDEX.write_text(text, encoding="utf-8")
    KATALOG.write_text(katalog, encoding="utf-8")
    print("\nзаписано: index.html, katalog.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
