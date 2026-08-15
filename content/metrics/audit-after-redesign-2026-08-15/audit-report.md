# Приёмочный аудит боевого сайта

Адрес: https://marzhavbetone.ru/. Замер: 2026-08-15T05:01:56+00:00.

Внешний контур — обычный раннер GitHub Actions, настоящий рендер Chromium. Он и есть источник истины по доступности, вёрстке, ссылкам и поисковому слою. SSH к reg.ru идёт отдельным разделом и отвечает только на вопрос, та ли версия лежит на origin: origin, проверяющий сам себя, о внешней доступности не говорит ничего.

## Размеры страницы

| viewport | scrollHeight | viewportHeight | screens | horizontal overflow |
|---|---|---|---|---|
| mobile-390 (390×844) | 17876 | 844 | 21.18 | нет |
| mobile-430 (430×932) | 17537 | 932 | 18.82 | нет |
| desktop-1366 (1366×768) | 9481 | 768 | 12.35 | нет |
| desktop-1440 (1440×900) | 9451 | 900 | 10.5 | нет |
| desktop-1920 (1920×1080) | 9515 | 1080 | 8.81 | нет |

`scrollWidth` / `clientWidth` документа по ширинам:

- mobile-390: 390 / 390
- mobile-430: 430 / 430
- desktop-1366: 1366 / 1366
- desktop-1440: 1440 / 1440
- desktop-1920: 1920 / 1920

## Вёрстка: настольная или растянутая мобильная

Признак меряется, а не оценивается: доля окна под контентом и число сеток, которые на этой ширине встали в две колонки и больше.

| viewport | main, px | доля окна | самый широкий текст | сетки 2+ колонок |
|---|---|---|---|---|
| mobile-390 | 390 | 1 | 346px (0.887) | 1 из 47 |
| mobile-430 | 430 | 1 | 386px (0.898) | 1 из 47 |
| desktop-1366 | 1366 | 1 | 1175px (0.86) | 11 из 47 |
| desktop-1440 | 1440 | 1 | 1238px (0.86) | 12 из 47 |
| desktop-1920 | 1920 | 1 | 1440px (0.75) | 12 из 47 |

## Порядок блоков сверху вниз (1440×900)

| # | экранов от верха | высота | блок | заголовок |
|---|---|---|---|---|
| 0 | 0 | 75 | `topbar` | — |
| 1 | 0.08 | 730 | `hero` | ДЛЯ СТРОИТЕЛЬНЫХ ПОДРЯДЧИКОВ И СУБПОДРЯДЧИКОВ / Система получения оплаты за выполненные строительные работы |
| 2 | 0.89 | 915 | `situations` | НАЧНИТЕ ОТСЮДА / Что происходит на вашем объекте? |
| 3 | 1.91 | 819 | `cases` | ИЗНУТРИ СТРОЙКИ / То, что не написано в договоре |
| 4 | 2.82 | 901 | `materials` | СВЕЖИЕ РАЗБОРЫ / Разбираем, где подрядчик теряет деньги |
| 5 | 3.82 | 1624 | `catalog` | ГОТОВЫЕ РЕШЕНИЯ / Комплект под вашу ситуацию |
| 6 | 5.63 | 1139 | `checklist` | БЕСПЛАТНЫЙ ЧЕК-ЛИСТ / Работы выполнены.Теперь давайте их оплатим. |
| 7 | 6.89 | 1539 | `author` | 19 ЛЕТ В СТРОИТЕЛЬСТВЕ / Знаю обе стороны приёмки |
| 8 | 8.6 | 312 | `section next-steps` | TELEGRAM |
| 9 | 8.95 | 776 | `faq` | ВОПРОСЫ ДО ПОКУПКИ / Оплата, получение и использование |
| 10 | 9.81 | 487 | `contact` | ЗАКАЗ ПАКЕТА / Оставьте контакт — мы свяжемся |
| 11 | 10.35 | 133 | `footer` | — |

## Вылет элементов

Скрытая ветка — элемент под `hidden` или `aria-hidden`: он в потоке не участвует и страницу не расширяет. Считается отдельно, чтобы закрытая панель корзины не выдавалась за дефект.

| viewport | всего | в видимой ветке |
|---|---|---|
| mobile-390 | 19 | 18 |
| mobile-430 | 19 | 18 |
| desktop-1366 | 20 | 19 |
| desktop-1440 | 21 | 20 |
| desktop-1920 | 21 | 20 |

### mobile-390

| причина | категория | элемент | текст |
|---|---|---|---|
| fixed-height-clip | — | `main#top > section.hero > div.hero-copy > h1` | Система получения оплаты за выполненные строительные работы |
| fixed-height-clip | — | `section#situations > div.section-head > h2` | Что происходит на вашем объекте? |
| fixed-height-clip | — | `section#cases > div.section-head.row > div` | ИЗНУТРИ СТРОЙКИТо, что не написано в договоре |
| fixed-height-clip | — | `section#cases > div.section-head.row > div > h2` | То, что не написано в договоре |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 01 |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 02 |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 03 |
| fixed-height-clip | — | `section#materials > div.section-head.row > div` | СВЕЖИЕ РАЗБОРЫРазбираем, где подрядчик теряет деньги |
| fixed-height-clip | — | `section#materials > div.section-head.row > div > h2` | Разбираем, где подрядчик теряет деньги |
| fixed-height-clip | — | `section#catalog > div.section-head.row > div > h2` | Комплект под вашу ситуацию |
| fixed-height-clip | product-card | `section#catalog > p.solutions-more` | Полный каталог: комплекты, отдельные документы и бесплатные  |
| fixed-height-clip | — | `section#checklist > div > h2` | Работы выполнены.Теперь давайте их оплатим. |
| fixed-height-clip | — | `section#author > div.author-copy > h2` | Знаю обе стороны приёмки |
| fixed-height-clip | — | `main#top > section.section.next-steps > div` | TELEGRAMРазборы ошибок и стройка без официозаДля тех, кто по |
| fixed-height-clip | — | `main#top > section.section.next-steps > div` | ДОПОЛНИТЕЛЬНАЯ УСЛУГАНе уверены, какой пакет нужен?Персональ |
| fixed-height-clip | — | `section#faq > div.section-head` | ВОПРОСЫ ДО ПОКУПКИОплата, получение и использование |
| fixed-height-clip | — | `section#faq > div.section-head > h2` | Оплата, получение и использование |
| fixed-height-clip | — | `section#contact > div.contact-copy > h2` | Оставьте контакт — мы свяжемся |

### mobile-430

| причина | категория | элемент | текст |
|---|---|---|---|
| fixed-height-clip | — | `main#top > section.hero > div.hero-copy > h1` | Система получения оплаты за выполненные строительные работы |
| fixed-height-clip | — | `section#situations > div.section-head > h2` | Что происходит на вашем объекте? |
| fixed-height-clip | — | `section#cases > div.section-head.row > div` | ИЗНУТРИ СТРОЙКИТо, что не написано в договоре |
| fixed-height-clip | — | `section#cases > div.section-head.row > div > h2` | То, что не написано в договоре |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 01 |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 02 |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 03 |
| fixed-height-clip | — | `section#materials > div.section-head.row > div` | СВЕЖИЕ РАЗБОРЫРазбираем, где подрядчик теряет деньги |
| fixed-height-clip | — | `section#materials > div.section-head.row > div > h2` | Разбираем, где подрядчик теряет деньги |
| fixed-height-clip | — | `section#catalog > div.section-head.row > div > h2` | Комплект под вашу ситуацию |
| fixed-height-clip | product-card | `section#catalog > p.solutions-more` | Полный каталог: комплекты, отдельные документы и бесплатные  |
| fixed-height-clip | — | `section#checklist > div > h2` | Работы выполнены.Теперь давайте их оплатим. |
| fixed-height-clip | — | `section#author > div.author-copy > h2` | Знаю обе стороны приёмки |
| fixed-height-clip | — | `main#top > section.section.next-steps > div` | TELEGRAMРазборы ошибок и стройка без официозаДля тех, кто по |
| fixed-height-clip | — | `main#top > section.section.next-steps > div` | ДОПОЛНИТЕЛЬНАЯ УСЛУГАНе уверены, какой пакет нужен?Персональ |
| fixed-height-clip | — | `section#faq > div.section-head` | ВОПРОСЫ ДО ПОКУПКИОплата, получение и использование |
| fixed-height-clip | — | `section#faq > div.section-head > h2` | Оплата, получение и использование |
| fixed-height-clip | — | `section#contact > div.contact-copy > h2` | Оставьте контакт — мы свяжемся |

### desktop-1366

| причина | категория | элемент | текст |
|---|---|---|---|
| fixed-height-clip | — | `main#top > section.hero > div.hero-copy > h1` | Система получения оплаты за выполненные строительные работы |
| fixed-height-clip | — | `section#situations > div.section-head > h2` | Что происходит на вашем объекте? |
| fixed-height-clip | — | `section#cases > div.section-head.row` | ИЗНУТРИ СТРОЙКИТо, что не написано в договоре Все разборы → |
| fixed-height-clip | — | `section#cases > div.section-head.row > div` | ИЗНУТРИ СТРОЙКИТо, что не написано в договоре |
| fixed-height-clip | — | `section#cases > div.section-head.row > div > h2` | То, что не написано в договоре |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 01 |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 02 |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 03 |
| fixed-height-clip | — | `section#materials > div.section-head.row` | СВЕЖИЕ РАЗБОРЫРазбираем, где подрядчик теряет деньги Витрина |
| fixed-height-clip | — | `section#materials > div.section-head.row > div` | СВЕЖИЕ РАЗБОРЫРазбираем, где подрядчик теряет деньги |
| fixed-height-clip | — | `section#materials > div.section-head.row > div > h2` | Разбираем, где подрядчик теряет деньги |
| fixed-height-clip | — | `section#catalog > div.section-head.row > div > h2` | Комплект под вашу ситуацию |
| fixed-height-clip | product-card | `section#catalog > p.solutions-more` | Полный каталог: комплекты, отдельные документы и бесплатные  |
| fixed-height-clip | — | `section#checklist > div > h2` | Работы выполнены.Теперь давайте их оплатим. |
| fixed-height-clip | — | `section#author > div.author-copy > h2` | Знаю обе стороны приёмки |
| fixed-height-clip | — | `main#top > section.section.next-steps > div` | ДОПОЛНИТЕЛЬНАЯ УСЛУГАНе уверены, какой пакет нужен?Персональ |
| fixed-height-clip | — | `section#faq > div.section-head` | ВОПРОСЫ ДО ПОКУПКИОплата, получение и использование |
| fixed-height-clip | — | `section#faq > div.section-head > h2` | Оплата, получение и использование |
| fixed-height-clip | — | `section#contact > div.contact-copy > h2` | Оставьте контакт — мы свяжемся |

### desktop-1440

| причина | категория | элемент | текст |
|---|---|---|---|
| fixed-height-clip | — | `main#top > section.hero > div.hero-copy > h1` | Система получения оплаты за выполненные строительные работы |
| fixed-height-clip | — | `section#situations > div.section-head > h2` | Что происходит на вашем объекте? |
| fixed-height-clip | — | `section#cases > div.section-head.row` | ИЗНУТРИ СТРОЙКИТо, что не написано в договоре Все разборы → |
| fixed-height-clip | — | `section#cases > div.section-head.row > div` | ИЗНУТРИ СТРОЙКИТо, что не написано в договоре |
| fixed-height-clip | — | `section#cases > div.section-head.row > div > h2` | То, что не написано в договоре |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 01 |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 02 |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 03 |
| fixed-height-clip | — | `section#materials > div.section-head.row` | СВЕЖИЕ РАЗБОРЫРазбираем, где подрядчик теряет деньги Витрина |
| fixed-height-clip | — | `section#materials > div.section-head.row > div` | СВЕЖИЕ РАЗБОРЫРазбираем, где подрядчик теряет деньги |
| fixed-height-clip | — | `section#materials > div.section-head.row > div > h2` | Разбираем, где подрядчик теряет деньги |
| fixed-height-clip | — | `section#catalog > div.section-head.row > div > h2` | Комплект под вашу ситуацию |
| fixed-height-clip | product-card | `section#catalog > p.solutions-more` | Полный каталог: комплекты, отдельные документы и бесплатные  |
| fixed-height-clip | — | `section#checklist > div > h2` | Работы выполнены.Теперь давайте их оплатим. |
| fixed-height-clip | — | `section#author > div.author-copy > h2` | Знаю обе стороны приёмки |
| fixed-height-clip | — | `main#top > section.section.next-steps > div` | TELEGRAMРазборы ошибок и стройка без официозаДля тех, кто по |
| fixed-height-clip | — | `main#top > section.section.next-steps > div` | ДОПОЛНИТЕЛЬНАЯ УСЛУГАНе уверены, какой пакет нужен?Персональ |
| fixed-height-clip | — | `section#faq > div.section-head` | ВОПРОСЫ ДО ПОКУПКИОплата, получение и использование |
| fixed-height-clip | — | `section#faq > div.section-head > h2` | Оплата, получение и использование |
| fixed-height-clip | — | `section#contact > div.contact-copy > h2` | Оставьте контакт — мы свяжемся |

### desktop-1920

| причина | категория | элемент | текст |
|---|---|---|---|
| fixed-height-clip | — | `main#top > section.hero > div.hero-copy > h1` | Система получения оплаты за выполненные строительные работы |
| fixed-height-clip | — | `section#situations > div.section-head > h2` | Что происходит на вашем объекте? |
| fixed-height-clip | — | `section#cases > div.section-head.row` | ИЗНУТРИ СТРОЙКИТо, что не написано в договоре Все разборы → |
| fixed-height-clip | — | `section#cases > div.section-head.row > div` | ИЗНУТРИ СТРОЙКИТо, что не написано в договоре |
| fixed-height-clip | — | `section#cases > div.section-head.row > div > h2` | То, что не написано в договоре |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 01 |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 02 |
| fixed-height-clip | case-card | `div.case-grid > a.case-card > div.case-body > p.case-no` | 03 |
| fixed-height-clip | — | `section#materials > div.section-head.row` | СВЕЖИЕ РАЗБОРЫРазбираем, где подрядчик теряет деньги Витрина |
| fixed-height-clip | — | `section#materials > div.section-head.row > div` | СВЕЖИЕ РАЗБОРЫРазбираем, где подрядчик теряет деньги |
| fixed-height-clip | — | `section#materials > div.section-head.row > div > h2` | Разбираем, где подрядчик теряет деньги |
| fixed-height-clip | — | `section#catalog > div.section-head.row > div > h2` | Комплект под вашу ситуацию |
| fixed-height-clip | product-card | `section#catalog > p.solutions-more` | Полный каталог: комплекты, отдельные документы и бесплатные  |
| fixed-height-clip | — | `section#checklist > div > h2` | Работы выполнены.Теперь давайте их оплатим. |
| fixed-height-clip | — | `section#author > div.author-copy > h2` | Знаю обе стороны приёмки |
| fixed-height-clip | — | `main#top > section.section.next-steps > div` | TELEGRAMРазборы ошибок и стройка без официозаДля тех, кто по |
| fixed-height-clip | — | `main#top > section.section.next-steps > div` | ДОПОЛНИТЕЛЬНАЯ УСЛУГАНе уверены, какой пакет нужен?Персональ |
| fixed-height-clip | — | `section#faq > div.section-head` | ВОПРОСЫ ДО ПОКУПКИОплата, получение и использование |
| fixed-height-clip | — | `section#faq > div.section-head > h2` | Оплата, получение и использование |
| fixed-height-clip | — | `section#contact > div.contact-copy > h2` | Оставьте контакт — мы свяжемся |

## Ссылки главной

- якорей всего: 60
- уникальных внутренних целей: 22
- внешних: 9
- пустой `href`: 0
- якорь на несуществующий id: 0
- битых (404/5xx/не ответил): 0
- с переадресацией: 0

### Все проверенные внутренние цели

| код | адрес | раздел |
|---|---|---|
| 200 | https://marzhavbetone.ru/articles/ | cases, materials, topbar |
| 200 | https://marzhavbetone.ru/articles/avans-eto-ne-dengi-eto-kryuchok.html | materials |
| 200 | https://marzhavbetone.ru/articles/bankrotstvo-genpodryadchika-5-markerov.html | materials |
| 200 | https://marzhavbetone.ru/articles/genpodryadchik-zarabatyvaet-na-vas.html | cases |
| 200 | https://marzhavbetone.ru/articles/podpisannaya-ks2-ne-znachit-chto-zaplatyat.html | cases |
| 200 | https://marzhavbetone.ru/articles/pretenziya-za-chuzhuyu-kommunalku.html | cases |
| 200 | https://marzhavbetone.ru/articles/skidka-15-procentov-na-tendere-eto-otbor-zhertv.html | materials |
| 200 | https://marzhavbetone.ru/contacts.html | footer |
| 200 | https://marzhavbetone.ru/diagnostika.html | checklist, topbar |
| 200 | https://marzhavbetone.ru/kalkulyator.html | checklist, topbar |
| 200 | https://marzhavbetone.ru/katalog.html | catalog, topbar |
| 200 | https://marzhavbetone.ru/materialy/ | checklist |
| 200 | https://marzhavbetone.ru/offer.html | contact, footer |
| 200 | https://marzhavbetone.ru/payment-delivery.html | footer |
| 200 | https://marzhavbetone.ru/privacy.html | contact |
| 200 | https://marzhavbetone.ru/products/p1-oplata-po-ks2.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/p2-dopolnitelnye-raboty.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/p3-shablony-ks2-ks3.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/p5-shtrafy-uderzhaniya.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/p7-dogovor-podryada.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/p9-bankrotstvo-genpodryadchika.html | catalog, situations |
| 200 | https://marzhavbetone.ru/refund.html | faq, footer |

## Поисковый слой

- `/` → 200
- `/index.html` → 200
- `robots.txt` → 200, строка Sitemap: True, `Disallow: /`: False
- `sitemap.xml` → 200, адресов 82
- canonical: `https://marzhavbetone.ru/`, совпадает с главной: True
- meta robots: `None`, noindex: False
- H1 на главной: 1 — ['Система получения оплаты за выполненные строительные работы']
- title (66): Шаблоны КС-2, КС-3 и документы для субподрядчиков — Маржа в бетоне
- description (160): Купить шаблоны КС-2, КС-3, акты выполненных работ, претензии и договоры для субподрядчиков. Бесплатные чек-листы. Готовые комплекты документов. 19 лет практики.
- в карте сайта, но не в репозитории: 0
- в репозитории, но не в карте: 0

## Клиентский интерфейс: продукты и внутренние коды

- карточек продуктов на главной: 6
- строк таблиц внутри `main`: 0
- упоминаний файлов (`.docx`/`.xlsx`/`.pdf`) в видимом тексте: 0
- внутренние коды линейки в тексте страницы: не найдены

## Origin по SSH (дополнительная проверка)

Не доказательство внешней доступности. Отвечает на один вопрос: лежит ли на origin та же версия, что отдаётся наружу.

```
--- окружение origin ---
curl:  curl 7.61.1
адрес: 37.140.192.133

--- файл на диске ---
права/размер/дата: -rw-r--r-- 42541 Aug 15 07:56
md5 на диске: 94d5f6ead5b3ba5f74ee9c1b7dba9482
байт:         42541
секций <section: 14
id блоков:
id="author"
id="cart-backdrop"
id="cart-checkout"
id="cart-close"
id="cart-count"
id="cart-empty"
id="cart-items"
id="cart-panel"
id="cart-toggle"
id="cart-total"
id="cases"
id="catalog"
id="checklist"
id="checklist-dialog"
id="close-checklist"
id="contact"
id="contact-form"
id="faq"
id="form-status"
id="lead-form"
id="lead-status"
id="materials"
id="open-checklist"
id="product"
id="selected-product"
id="situations"
id="top"

--- origin отдаёт себе ---
HTTP/2 200 
server: nginx
date: Sat, 15 Aug 2026 05:03:30 GMT
content-type: text/html
content-length: 42541
vary: Accept-Encoding
last-modified: Sat, 15 Aug 2026 04:56:57 GMT
accept-ranges: none
cache-control: public, max-age=3600, must-revalidate
expires: Sat, 15 Aug 2026 06:03:30 GMT
vary: Accept-Encoding
strict-transport-security: max-age=31536000;

размер тела: 42541 байт
md5 тела:    94d5f6ead5b3ba5f74ee9c1b7dba9482

--- сверка версий ---
внешний HTML (раннер):        94d5f6ead5b3ba5f74ee9c1b7dba9482
origin, файл на диске:        94d5f6ead5b3ba5f74ee9c1b7dba9482
origin, тело по curl:         94d5f6ead5b3ba5f74ee9c1b7dba9482
index.html в репозитории:     94d5f6ead5b3ba5f74ee9c1b7dba9482
ВЫВОД: внешняя выдача побайтно совпала с файлом на origin.
Выложена ровно та версия index.html, что лежит в этой ветке.
```

## Снимки

- `mobile-390-full.png` — 390×844
- `mobile-430-full.png` — 430×932
- `desktop-1366-full.png` — 1366×768
- `desktop-1440-full.png` — 1440×900
- `desktop-1920-full.png` — 1920×1080

