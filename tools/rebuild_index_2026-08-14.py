#!/usr/bin/env python3
"""Перестройка архитектуры главной. Дизайн не трогается: новые блоки собраны
на классах, у которых уже есть стили (topic-grid, result-list, hero-facts).
"""
import re
import sys
from pathlib import Path

INDEX = Path("/home/user/marzhavbetone.ru/index.html")
t = INDEX.read_text(encoding="utf-8")
orig = t

# ── 1. Шапка: пять разделов и кнопка, предсказывающая результат ────────────
old_nav = """    <nav aria-label="Основная навигация">
      <a href="#catalog">Каталог</a>
      <a href="kalkulyator.html">Калькулятор</a>
      <a href="#checklist">Чек-лист</a>
      <a href="#telegram">Telegram</a>
      <a href="#faq">FAQ</a>
    </nav>"""
new_nav = """    <nav aria-label="Основная навигация">
      <a href="#catalog">Решения</a>
      <a href="#checklist">Бесплатно</a>
      <a href="kalkulyator.html">Калькуляторы</a>
      <a href="articles/">Разборы</a>
      <a href="#author">О проекте</a>
      <a class="button button-small" href="#situations">Найти решение</a>
    </nav>"""
assert old_nav in t, "шапка не найдена"
t = t.replace(old_nav, new_nav)

# ── 2. Первый экран ────────────────────────────────────────────────────────
old_hero_copy = re.search(r'<div class="hero-copy">.*?</div>\s*(?=<figure)', t, re.S)
assert old_hero_copy, "hero-copy не найден"
new_hero_copy = """<div class="hero-copy">
        <p class="eyebrow">ДЛЯ СТРОИТЕЛЬНЫХ ПОДРЯДЧИКОВ И СУБПОДРЯДЧИКОВ</p>
        <h1>Система получения оплаты <em>за выполненные строительные работы.</em></h1>
        <p class="lead">Готовые алгоритмы и документы для каждого этапа: договор, допработы, исполнительная документация, КС-2 и КС-3, удержания и получение оплаты.</p>
        <div class="hero-actions">
          <a class="button" href="#situations">Выбрать свою ситуацию</a>
          <a class="text-link" href="#checklist">Проверить объект бесплатно</a>
        </div>
        <p class="lead">От договора до денег на счёте подрядчика.</p>
      </div>
      """
t = t[: old_hero_copy.start()] + new_hero_copy + t[old_hero_copy.end():]

# ── 3. Диагностический блок: главный интерфейс сайта ───────────────────────
SITUATIONS = [
    ("Договор ещё не подписан",
     "Проверить условия оплаты, приёмки, удержаний и ответственности до начала работ.",
     "products/p7-dogovor-podryada.html", "Проверить договор"),
    ("Появились дополнительные работы",
     "Зафиксировать объём так, чтобы его потом можно было закрыть и предъявить к оплате.",
     "products/p2-dopolnitelnye-raboty.html", "Оформить допработы"),
    ("Не принимают исполнительную или КС-2",
     "Документы возвращают, затягивают подписание или требуют исправления.",
     "products/p3-shablony-ks2-ks3.html", "Разобраться с приёмкой"),
    ("Работы закрыты, но денег нет",
     "КС подписаны, срок оплаты прошёл или заказчик откладывает расчёт.",
     "products/p1-oplata-po-ks2.html", "Получить оплату"),
    ("Удержали деньги или выставили штраф",
     "Гарантийное удержание, неустойка, встречные требования или уменьшение оплаты.",
     "products/p5-shtrafy-uderzhaniya.html", "Проверить удержание"),
    ("У заказчика финансовые проблемы",
     "Определить, как действовать до банкротства или уже внутри процедуры.",
     "products/p9-bankrotstvo-genpodryadchika.html", "Защитить задолженность"),
]
cards = "".join(
    f'<article><h3><a href="{href}">{title}</a></h3><p>{note}</p>'
    f'<p><a class="text-link" href="{href}">{cta} →</a></p></article>'
    for title, note, href, cta in SITUATIONS
)
situations = f"""
    <section class="section" id="situations">
      <div class="section-head"><p class="eyebrow">НАЧНИТЕ ОТСЮДА</p><h2>Что происходит на вашем объекте?</h2><p class="lead">Выберите ситуацию — покажем алгоритм действий и необходимые документы.</p></div>
      <div class="topic-grid">{cards}</div>
    </section>
"""

# ── 4. Система: цепочка этапов перед результатом ───────────────────────────
results = re.search(r'\n\s*<section class="section sales-result" id="results">.*?</section>', t, re.S)
assert results, "секция результата не найдена"
results_html = """
    <section class="section sales-result" id="results">
      <div><p class="eyebrow">КАК УСТРОЕНА СИСТЕМА</p><h2>Деньги подрядчика теряются не в момент оплаты</h2><p class="lead">Основание для получения денег формируется намного раньше — от условий договора до правильно оформленной сдачи работ.</p></div>
      <div class="result-list"><p><b>01</b> Договор</p><p><b>02</b> Выполнение и допработы</p><p><b>03</b> Исполнительная документация</p><p><b>04</b> КС-2 и КС-3</p><p><b>05</b> Оплата</p></div>
      <p class="lead">Ошибка на любом этапе становится основанием задержать, уменьшить или не платить.</p>
      <div class="result-list"><p><b>01</b> Понятно, какой объём и на каком основании должен быть оплачен</p><p><b>02</b> Выполнение подтверждено документами и доказательствами</p><p><b>03</b> Результат передан, а срок приёмки и оплаты запущен</p><p><b>04</b> При задержке есть следующий законный шаг, а не бесконечное «ждём»</p></div>
      <p><a class="text-link" href="#catalog">Посмотреть решения по этапам →</a></p>
    </section>
"""
t = t[: results.start()] + t[results.end():]          # вынули с прежнего места

# ── 5. Доверие: коротко, числами, которые уже опубликованы ─────────────────
trust = """
    <section class="section" id="practice">
      <div class="section-head"><p class="eyebrow">НА ЧЁМ ПОСТРОЕНА СИСТЕМА</p><h2>Система построена на практике строительного подряда</h2></div>
      <dl class="hero-facts">
        <div><dt>19</dt><dd>лет в строительстве</dd></div>
        <div><dt>3</dt><dd>стороны процесса: технический заказчик, генподрядчик, субподрядчик</dd></div>
        <div><dt>12+</dt><dd>объектов введено в эксплуатацию</dd></div>
      </dl>
      <p><a class="text-link" href="#author">Кто стоит за проектом →</a></p>
    </section>
"""

# Порядок: первый экран → ситуации → система → доверие → решения
anchor = '\n    <section class="section sales-solutions" id="catalog">'
assert anchor in t, "витрина не найдена"
t = t.replace(anchor, situations + results_html + trust + anchor, 1)

# ── 6. Бесплатная проверка сразу после решений ─────────────────────────────
checklist = re.search(r'\n\s*<section class="section checklist" id="checklist">.*?</section>', t, re.S)
assert checklist, "чек-лист не найден"
checklist_html = checklist.group(0)
t = t[: checklist.start()] + t[checklist.end():]
steps = '\n    <section class="section order-steps" id="how-to-buy">'
assert steps in t, "блок покупки не найден"
t = t.replace(steps, checklist_html + steps, 1)

# ── 7. Убрать внутренние коды продуктов с витрины ──────────────────────────
t, codes = re.subn(r'(<div class="product-number">)(?:P\d{1,2}|T\d|L\d) / ', r'\1', t)

# ── 8. «Прогрев без прогрева» — внутренняя кухня, не для покупателя ────────
t = t.replace("TELEGRAM / ПРОГРЕВ БЕЗ ПРОГРЕВА", "TELEGRAM")

INDEX.write_text(t, encoding="utf-8")
print(f"готово. кодов убрано: {codes}; было {len(orig.splitlines())} строк, стало {len(t.splitlines())}")
