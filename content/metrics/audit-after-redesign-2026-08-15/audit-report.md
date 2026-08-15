# Приёмочный аудит боевого сайта

Адрес: https://marzhavbetone.ru/. Замер: 2026-08-15T04:55:28+00:00.

Внешний контур — обычный раннер GitHub Actions, настоящий рендер Chromium. Он и есть источник истины по доступности, вёрстке, ссылкам и поисковому слою. SSH к reg.ru идёт отдельным разделом и отвечает только на вопрос, та ли версия лежит на origin: origin, проверяющий сам себя, о внешней доступности не говорит ничего.

## Размеры страницы

| viewport | scrollHeight | viewportHeight | screens | horizontal overflow |
|---|---|---|---|---|
| mobile-390 (390×844) | 25696 | 844 | 30.45 | нет |
| mobile-430 (430×932) | 24908 | 932 | 26.73 | нет |
| desktop-1366 (1366×768) | 27668 | 768 | 36.03 | ДА, +33px |
| desktop-1440 (1440×900) | 27472 | 900 | 30.52 | ДА, +32px |
| desktop-1920 (1920×1080) | 26236 | 1080 | 24.29 | нет |

`scrollWidth` / `clientWidth` документа по ширинам:

- mobile-390: 390 / 390
- mobile-430: 430 / 430
- desktop-1366: 1399 / 1366
- desktop-1440: 1472 / 1440
- desktop-1920: 1920 / 1920

## Вёрстка: настольная или растянутая мобильная

Признак меряется, а не оценивается: доля окна под контентом и число сеток, которые на этой ширине встали в две колонки и больше.

| viewport | main, px | доля окна | самый широкий текст | сетки 2+ колонок |
|---|---|---|---|---|
| mobile-390 | 390 | 1 | 346px (0.887) | 2 из 60 |
| mobile-430 | 430 | 1 | 386px (0.898) | 2 из 60 |
| desktop-1366 | 1366 | 1 | 1175px (0.86) | 14 из 60 |
| desktop-1440 | 1440 | 1 | 1238px (0.86) | 14 из 60 |
| desktop-1920 | 1920 | 1 | 1440px (0.75) | 14 из 60 |

## Порядок блоков сверху вниз (1440×900)

| # | экранов от верха | высота | блок | заголовок |
|---|---|---|---|---|
| 0 | 0 | 75 | `topbar` | — |
| 1 | 0.08 | 992 | `hero` | ДЛЯ СТРОИТЕЛЬНЫХ ПОДРЯДЧИКОВ И СУБПОДРЯДЧИКОВ / Система получения оплаты за сданные работы. |
| 2 | 1.19 | 1320 | `situations` | НАЧНИТЕ ОТСЮДА / Что происходит на вашем объекте? |
| 3 | 2.65 | 1425 | `results` | КАК УСТРОЕНА СИСТЕМА / Деньги подрядчика теряются не в момент оплаты |
| 4 | 4.23 | 695 | `practice` | НА ЧЁМ ПОСТРОЕНА СИСТЕМА / Система построена на практике строительного подряда |
| 5 | 5.01 | 14819 | `catalog` | КАТАЛОГ ДОКУМЕНТОВ / Шаблоны и чек-листы для субподрядчиков |
| 6 | 21.47 | 898 | `checklist` | БЕСПЛАТНЫЙ ЧЕК-ЛИСТ / Работы выполнены.Теперь давайте их оплатим. |
| 7 | 22.47 | 790 | `how-to-buy` | КАК КУПИТЬ / Четыре шага — и документы у вас |
| 8 | 23.35 | 54 | `ticker` | — |
| 9 | 23.41 | 756 | `topics` | ГДЕ ИСЧЕЗАЮТ ДЕНЬГИ / Бетон виден.Риски — не всегда. |
| 10 | 24.25 | 1255 | `author` | 19 ЛЕТ В СТРОИТЕЛЬСТВЕ / Знаю обе стороны приёмки |
| 11 | 25.64 | 1537 | `materials` | СВЕЖИЕ РАЗБОРЫ / Бумага сильнее бетона |
| 12 | 27.35 | 586 | `telegram` | TELEGRAM / Разборы ошибок, новые формы и стройка без официоза |
| 13 | 28 | 550 | `section personal-review` | ДОПОЛНИТЕЛЬНАЯ УСЛУГА / Не уверены, какой пакет нужен? |
| 14 | 28.61 | 949 | `faq` | ВОПРОСЫ ДО ПОКУПКИ / Оплата, получение и использование |
| 15 | 29.67 | 639 | `contact` | ЗАКАЗ ПАКЕТА / Оставьте контакт — мы свяжемся |
| 16 | 30.38 | 133 | `footer` | — |

## Вылет элементов

Скрытая ветка — элемент под `hidden` или `aria-hidden`: он в потоке не участвует и страницу не расширяет. Считается отдельно, чтобы закрытая панель корзины не выдавалась за дефект.

| viewport | всего | в видимой ветке |
|---|---|---|
| mobile-390 | 39 | 38 |
| mobile-430 | 39 | 38 |
| desktop-1366 | 181 | 180 |
| desktop-1440 | 146 | 145 |
| desktop-1920 | 86 | 85 |

### mobile-390

| причина | категория | элемент | текст |
|---|---|---|---|
| fixed-height-clip | — | `main#top > section.hero > div.hero-copy > h1` | Система получения оплаты за сданные работы. |
| fixed-height-clip | — | `main#top > section.hero > figure.hero-visual` | Устная договорённость.В бетоне. |
| fixed-height-clip | — | `section#situations > div.section-head > h2` | Что происходит на вашем объекте? |
| fixed-height-clip | — | `section#results > div > h2` | Деньги подрядчика теряются не в момент оплаты |
| fixed-height-clip | — | `section#results > p` | Посмотреть решения по этапам → |
| fixed-height-clip | — | `section#practice > div.section-head` | НА ЧЁМ ПОСТРОЕНА СИСТЕМАСистема построена на практике строит |
| fixed-height-clip | — | `section#practice > div.section-head > h2` | Система построена на практике строительного подряда |
| fixed-height-clip | — | `section#practice > p` | Кто стоит за проектом → |
| fixed-height-clip | — | `section#catalog > div.section-head > h2` | Шаблоны и чек-листы для субподрядчиков |
| right>viewport | — | `section#catalog > nav.catalog-jump > a` | Закрытие и оплата5 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a > span` | 5 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a` | Удержания и споры3 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a > span` | 3 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a` | Банкротство заказчика3 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a > span` | 3 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a` | Бесплатные10 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a > span` | 10 |
| fixed-height-clip | — | `section#checklist > div > h2` | Работы выполнены.Теперь давайте их оплатим. |
| fixed-height-clip | — | `section#how-to-buy > div.section-head` | КАК КУПИТЬЧетыре шага — и документы у вас |
| fixed-height-clip | — | `section#how-to-buy > div.section-head > h2` | Четыре шага — и документы у вас |
| scrollWidth>clientWidth | — | `main#top > section.ticker` | КС-2 / КС-3 ДОПРАБОТЫ ИСПОЛНИТЕЛЬНАЯ ДОКУМЕНТАЦИЯ УДЕРЖАНИЯ  |
| right>viewport + left<0 | — | `main#top > section.ticker > div` | КС-2 / КС-3 ДОПРАБОТЫ ИСПОЛНИТЕЛЬНАЯ ДОКУМЕНТАЦИЯ УДЕРЖАНИЯ  |
| left<0 | — | `main#top > section.ticker > div > i` |  |
| right>viewport | — | `main#top > section.ticker > div > i` |  |
| right>viewport | — | `main#top > section.ticker > div > i` |  |
| right>viewport | — | `main#top > section.ticker > div > i` |  |
| fixed-height-clip | — | `section#topics > div.section-head` | ГДЕ ИСЧЕЗАЮТ ДЕНЬГИ Бетон виден.Риски — не всегда. |
| fixed-height-clip | — | `section#topics > div.section-head > h2` | Бетон виден.Риски — не всегда. |
| fixed-height-clip | — | `section#author > div.author-copy > h2` | Знаю обе стороны приёмки |
| fixed-height-clip | — | `section#materials > div.section-head.row > div` | СВЕЖИЕ РАЗБОРЫБумага сильнее бетона |
| fixed-height-clip | — | `section#materials > div.section-head.row > div > h2` | Бумага сильнее бетона |
| fixed-height-clip | — | `section#telegram > div > h2` | Разборы ошибок, новые формы и стройка без официоза |
| fixed-height-clip | — | `main#top > section.section.personal-review > div > h2` | Не уверены, какой пакет нужен? |
| fixed-height-clip | — | `section#faq > div.section-head` | ВОПРОСЫ ДО ПОКУПКИОплата, получение и использование |
| fixed-height-clip | — | `section#faq > div.section-head > h2` | Оплата, получение и использование |
| fixed-height-clip | — | `section#contact > div.contact-copy > h2` | Оставьте контакт — мы свяжемся |
| scrollWidth>clientWidth | — | `form#contact-form > label.consent > a` | условия оферты |
| scrollWidth>clientWidth | — | `form#contact-form > label.consent > a` | обработкой персональных данных |

### mobile-430

| причина | категория | элемент | текст |
|---|---|---|---|
| fixed-height-clip | — | `main#top > section.hero > div.hero-copy > h1` | Система получения оплаты за сданные работы. |
| fixed-height-clip | — | `main#top > section.hero > figure.hero-visual` | Устная договорённость.В бетоне. |
| fixed-height-clip | — | `section#situations > div.section-head > h2` | Что происходит на вашем объекте? |
| fixed-height-clip | — | `section#results > div > h2` | Деньги подрядчика теряются не в момент оплаты |
| fixed-height-clip | — | `section#results > p` | Посмотреть решения по этапам → |
| fixed-height-clip | — | `section#practice > div.section-head` | НА ЧЁМ ПОСТРОЕНА СИСТЕМАСистема построена на практике строит |
| fixed-height-clip | — | `section#practice > div.section-head > h2` | Система построена на практике строительного подряда |
| fixed-height-clip | — | `section#practice > p` | Кто стоит за проектом → |
| fixed-height-clip | — | `section#catalog > div.section-head > h2` | Шаблоны и чек-листы для субподрядчиков |
| right>viewport | — | `section#catalog > nav.catalog-jump > a` | Закрытие и оплата5 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a > span` | 5 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a` | Удержания и споры3 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a > span` | 3 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a` | Банкротство заказчика3 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a > span` | 3 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a` | Бесплатные10 |
| right>viewport | — | `section#catalog > nav.catalog-jump > a > span` | 10 |
| fixed-height-clip | — | `section#checklist > div > h2` | Работы выполнены.Теперь давайте их оплатим. |
| fixed-height-clip | — | `section#how-to-buy > div.section-head` | КАК КУПИТЬЧетыре шага — и документы у вас |
| fixed-height-clip | — | `section#how-to-buy > div.section-head > h2` | Четыре шага — и документы у вас |
| scrollWidth>clientWidth | — | `main#top > section.ticker` | КС-2 / КС-3 ДОПРАБОТЫ ИСПОЛНИТЕЛЬНАЯ ДОКУМЕНТАЦИЯ УДЕРЖАНИЯ  |
| right>viewport + left<0 | — | `main#top > section.ticker > div` | КС-2 / КС-3 ДОПРАБОТЫ ИСПОЛНИТЕЛЬНАЯ ДОКУМЕНТАЦИЯ УДЕРЖАНИЯ  |
| left<0 | — | `main#top > section.ticker > div > i` |  |
| right>viewport | — | `main#top > section.ticker > div > i` |  |
| right>viewport | — | `main#top > section.ticker > div > i` |  |
| right>viewport | — | `main#top > section.ticker > div > i` |  |
| fixed-height-clip | — | `section#topics > div.section-head` | ГДЕ ИСЧЕЗАЮТ ДЕНЬГИ Бетон виден.Риски — не всегда. |
| fixed-height-clip | — | `section#topics > div.section-head > h2` | Бетон виден.Риски — не всегда. |
| fixed-height-clip | — | `section#author > div.author-copy > h2` | Знаю обе стороны приёмки |
| fixed-height-clip | — | `section#materials > div.section-head.row > div` | СВЕЖИЕ РАЗБОРЫБумага сильнее бетона |
| fixed-height-clip | — | `section#materials > div.section-head.row > div > h2` | Бумага сильнее бетона |
| fixed-height-clip | — | `section#telegram > div > h2` | Разборы ошибок, новые формы и стройка без официоза |
| fixed-height-clip | — | `main#top > section.section.personal-review > div > h2` | Не уверены, какой пакет нужен? |
| fixed-height-clip | — | `section#faq > div.section-head` | ВОПРОСЫ ДО ПОКУПКИОплата, получение и использование |
| fixed-height-clip | — | `section#faq > div.section-head > h2` | Оплата, получение и использование |
| fixed-height-clip | — | `section#contact > div.contact-copy > h2` | Оставьте контакт — мы свяжемся |
| scrollWidth>clientWidth | — | `form#contact-form > label.consent > a` | условия оферты |
| scrollWidth>clientWidth | — | `form#contact-form > label.consent > a` | обработкой персональных данных |

### desktop-1366

| причина | категория | элемент | текст |
|---|---|---|---|
| scrollWidth>clientWidth | — | `main#top` | ДЛЯ СТРОИТЕЛЬНЫХ ПОДРЯДЧИКОВ И СУБПОДРЯДЧИКОВ Система получе |
| fixed-height-clip | — | `main#top > section.hero > div.hero-copy > h1` | Система получения оплаты за сданные работы. |
| fixed-height-clip | — | `main#top > section.hero > figure.hero-visual` | Устная договорённость.В бетоне. |
| fixed-height-clip | — | `section#situations > div.section-head > h2` | Что происходит на вашем объекте? |
| fixed-height-clip | — | `section#results > div > h2` | Деньги подрядчика теряются не в момент оплаты |
| fixed-height-clip | — | `section#results > p` | Посмотреть решения по этапам → |
| fixed-height-clip | — | `section#practice > div.section-head` | НА ЧЁМ ПОСТРОЕНА СИСТЕМАСистема построена на практике строит |
| fixed-height-clip | — | `section#practice > div.section-head > h2` | Система построена на практике строительного подряда |
| fixed-height-clip | — | `section#practice > p` | Кто стоит за проектом → |
| scrollWidth>clientWidth | product-card | `section#catalog` | КАТАЛОГ ДОКУМЕНТОВШаблоны и чек-листы для субподрядчиковГото |
| fixed-height-clip | — | `section#catalog > div.section-head > h2` | Шаблоны и чек-листы для субподрядчиков |
| scrollWidth>clientWidth | product-card | `section#catalog > div.product-grid` | До подписанияДоговор, аванс, смета, расчёт метрами — пока ус |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya` | До подписанияДоговор, аванс, смета, расчёт метрами — пока ус |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner` | ДОГОВОРКомплект «Договор субподряда: образец, красные флаги, |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card` | ДОГОВОРКомплект «Договор субподряда: образец, красные флаги, |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Договор субподряда: образец, красные флаги, проток |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > ul.product-documents` | Договор субподрядаПеречень работКалендарный планПорядок приё |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Договор субподряда |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Календарный план |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Допсоглашение на объём |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Допсоглашение на сроки |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Протокол разногласий |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card` | АВАНС И ВОЗВРАТКомплект «Аванс по договору подряда и неотраб |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Аванс по договору подряда и неотработанный остаток |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > ul.product-documents` | Калькулятор условий авансаРазбор четырёх условийАлгоритм пер |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Калькулятор условий аванса |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Алгоритм переговоров об авансе |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Протокол разногласий: авансовые пункты |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Допсоглашение о порядке погашения |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Требование о выплате аванса |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Расчёт отработанной части аванса и сальдо |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Ответ на требование о возврате аванса |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card` | СМЕТАКомплект «Что в смете не оплатят: проверка сметы субпод |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Что в смете не оплатят: проверка сметы субподрядчи |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > ul.product-documents` | Алгоритм: семь шагов проверки сметыЧек-лист выпадающих затра |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Чек-лист выпадающих затрат, девять разделов |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Протокол разногласий по смете |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Памятка: зимнее удорожание и временные здания |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Памятка: мусор, транспорт и непредвиденные |
| fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Расчёт метрами: проверка до подписи» |

…ещё 140, полностью — в `overflow.json`.

### desktop-1440

| причина | категория | элемент | текст |
|---|---|---|---|
| scrollWidth>clientWidth | — | `main#top` | ДЛЯ СТРОИТЕЛЬНЫХ ПОДРЯДЧИКОВ И СУБПОДРЯДЧИКОВ Система получе |
| fixed-height-clip | — | `main#top > section.hero > div.hero-copy > h1` | Система получения оплаты за сданные работы. |
| fixed-height-clip | — | `main#top > section.hero > figure.hero-visual` | Устная договорённость.В бетоне. |
| fixed-height-clip | — | `section#situations > div.section-head > h2` | Что происходит на вашем объекте? |
| fixed-height-clip | — | `section#results > div > h2` | Деньги подрядчика теряются не в момент оплаты |
| fixed-height-clip | — | `section#results > p` | Посмотреть решения по этапам → |
| fixed-height-clip | — | `section#practice > div.section-head` | НА ЧЁМ ПОСТРОЕНА СИСТЕМАСистема построена на практике строит |
| fixed-height-clip | — | `section#practice > div.section-head > h2` | Система построена на практике строительного подряда |
| fixed-height-clip | — | `section#practice > p` | Кто стоит за проектом → |
| scrollWidth>clientWidth | product-card | `section#catalog` | КАТАЛОГ ДОКУМЕНТОВШаблоны и чек-листы для субподрядчиковГото |
| fixed-height-clip | — | `section#catalog > div.section-head > h2` | Шаблоны и чек-листы для субподрядчиков |
| scrollWidth>clientWidth | product-card | `section#catalog > div.product-grid` | До подписанияДоговор, аванс, смета, расчёт метрами — пока ус |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya` | До подписанияДоговор, аванс, смета, расчёт метрами — пока ус |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner` | ДОГОВОРКомплект «Договор субподряда: образец, красные флаги, |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card` | ДОГОВОРКомплект «Договор субподряда: образец, красные флаги, |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Договор субподряда: образец, красные флаги, проток |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > ul.product-documents` | Договор субподрядаПеречень работКалендарный планПорядок приё |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Календарный план |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Допсоглашение на объём |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Допсоглашение на сроки |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card` | АВАНС И ВОЗВРАТКомплект «Аванс по договору подряда и неотраб |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Аванс по договору подряда и неотработанный остаток |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > ul.product-documents` | Калькулятор условий авансаРазбор четырёх условийАлгоритм пер |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Калькулятор условий аванса |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Алгоритм переговоров об авансе |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Протокол разногласий: авансовые пункты |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Допсоглашение о порядке погашения |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Расчёт отработанной части аванса и сальдо |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card` | СМЕТАКомплект «Что в смете не оплатят: проверка сметы субпод |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Что в смете не оплатят: проверка сметы субподрядчи |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > ul.product-documents` | Алгоритм: семь шагов проверки сметыЧек-лист выпадающих затра |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Чек-лист выпадающих затрат, девять разделов |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Памятка: мусор, транспорт и непредвиденные |
| fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Расчёт метрами: проверка до подписи» |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Предлагают квартиры вместо денег: запросы до подписи |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > ul.product-documents` | Порядок дня, когда просят подписатьЗапрос о состоянии счёта  |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Запрос застройщику о статусе объекта |
| scrollWidth>clientWidth | product-card | `details#group-po-hodu-rabot` | Пока идут работыИсполнительная документация и дополнительные |
| scrollWidth>clientWidth | product-card | `details#group-po-hodu-rabot > div.product-grid-inner` | ПТОКомплект «Акты скрытых работ и исполнительная документаци |
| scrollWidth>clientWidth | product-card | `details#group-po-hodu-rabot > div.product-grid-inner > article.product-card` | ПТОКомплект «Акты скрытых работ и исполнительная документаци |

…ещё 105, полностью — в `overflow.json`.

### desktop-1920

| причина | категория | элемент | текст |
|---|---|---|---|
| fixed-height-clip | — | `main#top > section.hero > div.hero-copy > h1` | Система получения оплаты за сданные работы. |
| fixed-height-clip | — | `main#top > section.hero > figure.hero-visual` | Устная договорённость.В бетоне. |
| fixed-height-clip | — | `section#situations > div.section-head > h2` | Что происходит на вашем объекте? |
| fixed-height-clip | — | `section#results > div > h2` | Деньги подрядчика теряются не в момент оплаты |
| fixed-height-clip | — | `section#results > p` | Посмотреть решения по этапам → |
| fixed-height-clip | — | `section#practice > div.section-head` | НА ЧЁМ ПОСТРОЕНА СИСТЕМАСистема построена на практике строит |
| fixed-height-clip | — | `section#practice > div.section-head > h2` | Система построена на практике строительного подряда |
| fixed-height-clip | — | `section#practice > p` | Кто стоит за проектом → |
| fixed-height-clip | — | `section#catalog > div.section-head > h2` | Шаблоны и чек-листы для субподрядчиков |
| scrollWidth>clientWidth | product-card | `section#catalog > div.product-grid` | До подписанияДоговор, аванс, смета, расчёт метрами — пока ус |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya` | До подписанияДоговор, аванс, смета, расчёт метрами — пока ус |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner` | ДОГОВОРКомплект «Договор субподряда: образец, красные флаги, |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Договор субподряда: образец, красные флаги, проток |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card` | АВАНС И ВОЗВРАТКомплект «Аванс по договору подряда и неотраб |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Аванс по договору подряда и неотработанный остаток |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card` | СМЕТАКомплект «Что в смете не оплатят: проверка сметы субпод |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Что в смете не оплатят: проверка сметы субподрядчи |
| scrollWidth>clientWidth | product-card | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > ul.product-documents` | Алгоритм: семь шагов проверки сметыЧек-лист выпадающих затра |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Памятка: мусор, транспорт и непредвиденные |
| fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Комплект «Расчёт метрами: проверка до подписи» |
| fixed-height-clip | — | `details#group-do-podpisaniya > div.product-grid-inner > article.product-card > h3` | Предлагают квартиры вместо денег: запросы до подписи |
| scrollWidth>clientWidth | product-card | `details#group-po-hodu-rabot` | Пока идут работыИсполнительная документация и дополнительные |
| scrollWidth>clientWidth | product-card | `details#group-po-hodu-rabot > div.product-grid-inner` | ПТОКомплект «Акты скрытых работ и исполнительная документаци |
| scrollWidth>clientWidth | product-card | `details#group-po-hodu-rabot > div.product-grid-inner > article.product-card` | ПТОКомплект «Акты скрытых работ и исполнительная документаци |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-po-hodu-rabot > div.product-grid-inner > article.product-card > h3` | Комплект «Акты скрытых работ и исполнительная документация» |
| scrollWidth>clientWidth | product-card | `details#group-po-hodu-rabot > div.product-grid-inner > article.product-card` | ДОПРАБОТЫКомплект «Дополнительные работы: как получить оплат |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-po-hodu-rabot > div.product-grid-inner > article.product-card > h3` | Комплект «Дополнительные работы: как получить оплату» |
| scrollWidth>clientWidth | product-card | `details#group-po-hodu-rabot > div.product-grid-inner > article.product-card > ul.product-documents` | Приказ на дополнительный объёмСогласование объёма и стоимост |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Приказ на дополнительный объём |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Журнал дополнительных работ |
| fixed-height-clip | — | `details#group-zakrytie-i-oplata > div.product-grid-inner > article.product-card > h3` | Комплект «КС-2 без возврата: сдайте с первой попытки» |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-zakrytie-i-oplata > div.product-grid-inner > article.product-card > h3` | Комплект «Акты выполненных работ, КС-2 и КС-3: закрытие и вз |
| scrollWidth>clientWidth | product-card | `details#group-zakrytie-i-oplata > div.product-grid-inner > article.product-card` | ПЕРЕДАЧА ИДПередача исполнительной документации: сопроводите |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-zakrytie-i-oplata > div.product-grid-inner > article.product-card > h3` | Передача исполнительной документации: сопроводительное письм |
| scrollWidth>clientWidth | — | `div.product-grid-inner > article.product-card > ul.product-documents > li` | Сопроводительное письмо к передаче |
| fixed-height-clip | — | `details#group-zakrytie-i-oplata > div.product-grid-inner > article.product-card > h3` | Заказчик не оплачивает работы: претензия, расчёт процентов,  |
| scrollWidth>clientWidth | product-card | `details#group-zakrytie-i-oplata > div.product-grid-inner > article.product-card` | ПЕРВЫЙ ДЕНЬОдносторонний акт или зачёт: возражения в срокПри |
| scrollWidth>clientWidth + fixed-height-clip | — | `details#group-zakrytie-i-oplata > div.product-grid-inner > article.product-card > h3` | Односторонний акт или зачёт: возражения в срок |
| scrollWidth>clientWidth | product-card | `details#group-uderzhaniya-i-spory` | Удержания и спорыГарантийное удержание, штрафы, спор о сумме |
| scrollWidth>clientWidth | product-card | `details#group-uderzhaniya-i-spory > div.product-grid-inner` | УДЕРЖАНИЯКомплект «Гарантийное удержание: возврат, оспариван |

…ещё 45, полностью — в `overflow.json`.

## Ссылки главной

- якорей всего: 92
- уникальных внутренних целей: 41
- внешних: 9
- пустой `href`: 0
- якорь на несуществующий id: 0
- битых (404/5xx/не ответил): 0
- с переадресацией: 0

### Все проверенные внутренние цели

| код | адрес | раздел |
|---|---|---|
| 200 | https://marzhavbetone.ru/articles/ | materials, topbar |
| 200 | https://marzhavbetone.ru/articles/avans-eto-ne-dengi-eto-kryuchok.html | materials |
| 200 | https://marzhavbetone.ru/articles/bankrotstvo-genpodryadchika-5-markerov.html | materials |
| 200 | https://marzhavbetone.ru/articles/genpodryadchik-zarabatyvaet-na-vas.html | materials |
| 200 | https://marzhavbetone.ru/articles/podpisannaya-ks2-ne-znachit-chto-zaplatyat.html | materials |
| 200 | https://marzhavbetone.ru/articles/skidka-15-procentov-na-tendere-eto-otbor-zhertv.html | materials |
| 200 | https://marzhavbetone.ru/contacts.html | footer |
| 200 | https://marzhavbetone.ru/diagnostika.html | topbar |
| 200 | https://marzhavbetone.ru/kalkulyator.html | topbar |
| 200 | https://marzhavbetone.ru/materialy/akt-skrytyh-rabot.html | catalog |
| 200 | https://marzhavbetone.ru/materialy/avans.html | catalog |
| 200 | https://marzhavbetone.ru/materialy/bankrotstvo.html | catalog |
| 200 | https://marzhavbetone.ru/materialy/dengi.html | catalog |
| 200 | https://marzhavbetone.ru/materialy/dogovor.html | catalog |
| 200 | https://marzhavbetone.ru/materialy/dop-raboty.html | catalog |
| 200 | https://marzhavbetone.ru/materialy/ispolnitelnaya-dokumentaciya.html | catalog |
| 200 | https://marzhavbetone.ru/materialy/raschet-metrami.html | catalog |
| 200 | https://marzhavbetone.ru/materialy/uderzhaniya.html | catalog |
| 200 | https://marzhavbetone.ru/materialy/vozvrat-ks.html | catalog |
| 200 | https://marzhavbetone.ru/offer.html | contact, footer |
| 200 | https://marzhavbetone.ru/payment-delivery.html | footer |
| 200 | https://marzhavbetone.ru/privacy.html | contact |
| 200 | https://marzhavbetone.ru/products/p1-oplata-po-ks2.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/p10-otvet-na-pretenziyu.html | catalog |
| 200 | https://marzhavbetone.ru/products/p11-raschet-metrami.html | catalog |
| 200 | https://marzhavbetone.ru/products/p12-spor-s-summoy.html | catalog |
| 200 | https://marzhavbetone.ru/products/p13-chto-v-smete-ne-oplatyat.html | catalog |
| 200 | https://marzhavbetone.ru/products/p2-dopolnitelnye-raboty.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/p3-shablony-ks2-ks3.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/p4-ispolnitelnaya-dokumentaciya-pto.html | catalog |
| 200 | https://marzhavbetone.ru/products/p5-shtrafy-uderzhaniya.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/p7-dogovor-podryada.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/p8-avans-po-dogovoru-subpodryada.html | catalog |
| 200 | https://marzhavbetone.ru/products/p9-bankrotstvo-genpodryadchika.html | catalog, situations |
| 200 | https://marzhavbetone.ru/products/t1-pervyy-shag-pri-neoplate.html | catalog |
| 200 | https://marzhavbetone.ru/products/t2-peredacha-ispolnitelnoy-dokumentacii.html | catalog |
| 200 | https://marzhavbetone.ru/products/t3-odnostoronniy-akt-i-zachet.html | catalog |
| 200 | https://marzhavbetone.ru/products/t4-genpodryadchik-bankrotitsya.html | catalog |
| 200 | https://marzhavbetone.ru/products/t5-trebuyut-vernut-avans.html | catalog |
| 200 | https://marzhavbetone.ru/products/t6-kvartiry-vmesto-deneg.html | catalog |
| 200 | https://marzhavbetone.ru/refund.html | faq, footer |

## Поисковый слой

- `/` → 200
- `/index.html` → 200
- `robots.txt` → 200, строка Sitemap: True, `Disallow: /`: False
- `sitemap.xml` → 200, адресов 82
- canonical: `https://marzhavbetone.ru/`, совпадает с главной: True
- meta robots: `None`, noindex: False
- H1 на главной: 1 — ['Система получения оплаты за сданные работы.']
- title (66): Шаблоны КС-2, КС-3 и документы для субподрядчиков — Маржа в бетоне
- description (160): Купить шаблоны КС-2, КС-3, акты выполненных работ, претензии и договоры для субподрядчиков. Бесплатные чек-листы. Готовые комплекты документов. 19 лет практики.
- в карте сайта, но не в репозитории: 1
- в репозитории, но не в карте: 0
  - только на бою: https://marzhavbetone.ru/katalog.html

## Клиентский интерфейс: продукты и внутренние коды

- карточек продуктов на главной: 28
- строк таблиц внутри `main`: 0
- упоминаний файлов (`.docx`/`.xlsx`/`.pdf`) в видимом тексте: 0
- внутренние коды линейки в тексте страницы: ['P10']

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
date: Sat, 15 Aug 2026 04:57:27 GMT
content-type: text/html
content-length: 42541
vary: Accept-Encoding
last-modified: Sat, 15 Aug 2026 04:56:57 GMT
accept-ranges: none
cache-control: public, max-age=3600, must-revalidate
expires: Sat, 15 Aug 2026 05:57:27 GMT
vary: Accept-Encoding
strict-transport-security: max-age=31536000;

размер тела: 42541 байт
md5 тела:    94d5f6ead5b3ba5f74ee9c1b7dba9482

--- сверка версий ---
внешний HTML (раннер):        94d5f6ead5b3ba5f74ee9c1b7dba9482
origin, файл на диске:        94d5f6ead5b3ba5f74ee9c1b7dba9482
origin, тело по curl:         94d5f6ead5b3ba5f74ee9c1b7dba9482
index.html в репозитории:     7bed025785878a1748ab5f3f33c8f0a6
ВЫВОД: внешняя выдача побайтно совпала с файлом на origin.
Внешняя выдача отличается от index.html этой ветки —
это норма, если ветка обогнала main или сервер подставляет своё.
```

## Снимки

- `mobile-390-full.png` — 390×844
- `mobile-430-full.png` — 430×932
- `desktop-1366-full.png` — 1366×768
- `desktop-1440-full.png` — 1440×900
- `desktop-1920-full.png` — 1920×1080

