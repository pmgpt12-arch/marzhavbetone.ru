# Проверка пользовательского маршрута НСП

Статус: **P0 исправлены в отдельной локальной staging-версии; НЕ ОПУБЛИКОВАНО.** Основная сессия и её продуктовая ветка не изменялись. Никаких merge/deploy, реальных заказов, платежей, писем, записей в секреты или системные настройки.

База: `c7e32ecc7ad5d8d4b0a3e425ccfe8eeccafe8433`. Ветка: `fix/nsp-customer-route-20261022`. Проверенный исходный commit: `e7ae51361c16054ae2961ffd23946ca33d0d3c6d`. Полный состав изменений и SHA-256 — PUBLIC_FILES.json; сохранность — PROTECTED_RECEIPT.json.

## Подтверждённая исходная точка

16/16 HTTP-файлов опубликованного сайта совпали побайтно с main; app-script.php совпал с app.js. Свежие live DOM и 14 скриншотов для шести P0-страниц получены только чтением: LIVE_DOM_BASELINE.json, screens/live-before. Исторические ff3d97c и продуктовая ветка не использованы как база. Дополнительные снимки исходного main — screens/before.

## Изменения и приёмка

| ID | Файл | До → после | Проверенный результат | Статус | Скриншот |
|---|---|---|---|---|---|
| WEB-01 | diagnostika.html | Риск сразу давал диагноз неплатёжеспособности | Судебная стадия → проверенные источники и даты → характер требования; 25 исходов, максимум 8 вопросов | PASS | [после](screens/after/D01-desktop.png) |
| WEB-02 | materialy/dengi.html | T1/T4/T5 продавались за 990 ₽ | Три страницы ведут к P1/P9/P8 по актуальной цене; по одной основной карточке | PASS | [после](screens/after/money-desktop.png) |
| WEB-03 | products/t2-peredacha-ispolnitelnoy-dokumentacii.html | P4 за 2 990 ₽: 3 видимых места + JSON-LD FAQ | Название из каталога и 24 900 ₽ во всех четырёх местах; T2 9 900 ₽ | PASS | [после](screens/after/t2-desktop.png) |
| WEB-04 | products/p11-raschet-metrami.html | w:top распознавался как w:t; свойства Word попадали в текст | Namespace-aware XML parser; пересобран только P11, мастер-файлы не записывались; необоснованный вывод о неплатёжеспособности убран | PASS | [после](screens/after/p11-mobile.png) |
| WEB-05 | materialy/dengi.html | P1 объявлялся непригодным для спорной ситуации | Входные документы → сверка остатка → расчёт и претензия; похожих фраз на остальных страницах materials/products не найдено | PASS | [после](screens/after/money-mobile.png) |
| WEB-06 | app.js | checklist_download считался при появлении ссылки | lead_submit / lead_ready / download_click, тема и UTM; ошибочный ответ не создаёт ready/click | PASS_FRONTEND | [после](screens/after/lead-ready-desktop.png) |
| WEB-07 | materialy/dengi.html | Обязательный общий контакт, нет короткого перехода к форме | 10 страниц: email обязателен, Telegram/телефон необязателен; якорь на Деньгах; серверный contact совместим | PARTIAL_HOME_PROTECTED | [после](screens/after/money-desktop.png) |
| WEB-08 | app.js | Старый localStorage мог хранить цену и неактивный SKU; идентичность по названию | Ключ сохранён; обновление по 13 SKU из server config, удаление снятых/дубликатов, цена и название нормализованы; Escape и фокус | PASS | [после](screens/after/checkout-mobile.png) |
| WEB-09 | success.html | Без ID: заказ сохранён; title утверждал успешную оплату | Нейтральные title/description, noindex, условный текст; pending проверен на локальном ответе | PASS | [после](screens/after/success-desktop.png) |
| WEB-10 | products/p3-shablony-ks2-ks3.html | Каталог под сгибом, неточный состав P3 и назначение реестра | Карточка на y=452.19; P3 6 DOCX/2 XLSX/2 PDF + TXT, АОСР 4 страницы, различие КС-6/КС-6а; главная идентична | PASS | [после](screens/after/p3-mobile.png) |

## Побайтный контроль публичных файлов

| Файл | Исходный SHA-256 | Новый SHA-256 |
|---|---|---|
| app.js | `9924f5c20b4046f0eecabaea8be47c0342adaf67cb1d25c0155dc3d7b33bc6fc` | `08d5b398445d5b83abcdc4d827b73b3a4e8109631c8fdfa43a997dbe81d38361` |
| diagnostika.html | `00ed4c4f6e3bd51939923cbd0be9f156f484a5b9a64ec5a618ea9aa56f72e028` | `11c029b4640e0d93805fd80607e9524480676ffa500019b23922f2d0cfc51232` |
| katalog.html | `a4346219b8d1c266f25cac8f93787dbebfe2a127b9c5a0c884648b9b5d8cd340` | `b1a52136d21f4db078cd4b16e36d39ce6fd4e25fdd1e5978c256464ecaf0cb30` |
| materialy/akt-skrytyh-rabot.html | `40dfd613150ba9569c8c5ecfbbd9b3dc40989db1dea70ca37e97dbbf49dfdd10` | `5c6aa7329f7346a2681455e75a022c20190e26e50ad648a83c013d9a717a4a93` |
| materialy/avans.html | `42c4e0d9b4ee8e565385dd089d5e953e25bfd3bab58ecb681403b7260a95a590` | `9f51c6f57ca8d86f6cb25b37552cb4ea6d945e4fbe49c79ffbb646fcb194b33b` |
| materialy/bankrotstvo.html | `ad366b640731ad16a0e38dd08e0236034dc564405dbbc9ce4f2ad61f2087ed63` | `94df1632287d948d26c6341dae8853ca98e5413e00226605f741e7888f62270a` |
| materialy/dengi.html | `be1ed489a3d19bd42a510ef15918c507684f7e05a4294f9bd02495c805ffd09e` | `435dd9a2b3ae70c4f0378c4f79ab4430f478881174ade1c8b2d85181c0e801e3` |
| materialy/dogovor.html | `785dcd1bc6a7d41896b9f0ceba92c000613db9b3669889852e6e43c609bbdd8c` | `ff653d20416e46536db97102c3de98a87df333aeb719bed3ef22c00be0cc5997` |
| materialy/dop-raboty.html | `847d448ffcd917a22a6c49b69039cf825a0b2c672846685eab745a9bfc28e414` | `cd674adf34b450fbcc7282b521ac8f42eac6c8c848f824e9113eb21d1b396b35` |
| materialy/ispolnitelnaya-dokumentaciya.html | `5a5bb905cb0468915378d04786e16c11a9053b782a22bf84b48d6ead7f20e53c` | `c23a434b6d99174137be2af25b8c35dadd663c03c6bc85b1243def4baf1e24d2` |
| materialy/raschet-metrami.html | `e56e44338b31b3ed84d6faba03f34d10c2eb8be062ba58854fdd12f80d06a5ff` | `96a9b70413947fa2ad7e80d5be887c90e265b67813e37447524dcdb88170799b` |
| materialy/uderzhaniya.html | `5e3d776f5e184ebf98db4b7b993d00622a40591fb558428297f98ae46cfae9c6` | `7488a4a5fb61c8ad2c4ad7cfa4ec25f633a15447e932c65fcc4f5f5b88b0cf48` |
| materialy/vozvrat-ks.html | `fcdfdc8e7092be48da964f737abbac062541dc7dad9f1cc1f516fa4d73acfcfa` | `0a1694430e77ef6689fca6f9fd6bcaf58a448bcb51ef861814471bf329e31c36` |
| products/p11-raschet-metrami.html | `c58684948b8b5573694e60010e15193592e238bd3115d7c2f2d56374575fff88` | `ef83b6f3cb51feb4a9fd1157f270440c3b2a3562dc9e260fe5717d29468f47ba` |
| products/p3-shablony-ks2-ks3.html | `28a3614e8824610fba76470fe902a98c559c1c8e9414bde472aef77254521945` | `568593e0610bfbdd786783ef1845d6fb206c5642279c52f7dd9315577cb164dc` |
| products/t2-peredacha-ispolnitelnoy-dokumentacii.html | `da3367b12c0ef939d096ac6266b67538554328bbb07395809733d764b1a65180` | `47dce084410772f7cd74c2841842912f85f832061fc79113c50819524f066a4b` |
| success.html | `7bb1d05cbb3a297e5969a27d756c22cfb3d0c3fbec01dd12868ada9ce457db42` | `986fb2b3a21d22c7c923d535cc279685e40badd3a1fea8ba9af2f5e06242b59d` |

## Проверки

- Основной Chromium smoke: 62/62, desktop 1366×850 и mobile 390×844; 0 JS errors. Финальный прогон использует настоящий локальный PHP. DOM и скриншоты сохранены по сценариям.
- Дополнительная регрессия: 34/34. Все 13 SKU дают правильные название/цену; повторный клик не удваивает позицию; исторические T1/T4/T5 работают через свои существующие ссылки. Автоматические редиректы им не добавлялись.
- Главная: исходник, CSS и attribution.js побайтно прежние; геометрия и computed styles hero/заголовка/кнопок/этапов/следующего блока совпали на обеих ширинах. На ноутбуке следующий блок виден без прокрутки.
- P8: 24 900 ₽, один товар, «В корзине», обязательный email и согласие, необязательный контакт; пустая форма не инициирует POST. Escape, закрытие и возврат фокуса проверены.
- Серверный PHP: тест авторитетной цены; 16 случаев обработчиков с локальным перехватчиком почты; 11 бесплатных маршрутов; HTTP app-script.php отдаёт точный app.js и прежние no-store headers. Это локальные проверки исходников, не тест отправки с рабочего хостинга.
- 8 контрактных тестов новой задачи и существующие preview/diagnostic/attribution/browser-events/run_checks tests — PASS. build_preview.py --check — без расхождений на всей линейке.
- Новые проверки подключены к существующему tools/ci_checks.yaml. Полный remote CI и полный гейт публикации в этой задаче не заявляются пройденными.
- Не менялись products-storage, downloads, покупательские ZIP, 13 принятых файлов, 19 кандидатов и held-six. Основная продуктовая ветка по повторной проверке сохранила HEAD 0cce946a2c0937ca30867231674ab9ba2432bf2d.

## Остаточные блокеры и пределы приёмки

1. **WEB-07 / ACTION_BLOCKED_OWNER_SCOPE.** Форма PDF на самой главной сохранила старый общий contact «Telegram или email». ТЗ одновременно требует сохранить мобильную главную; её HTML не менялся. Новая email-форма реализована на всех десяти отдельных страницах материалов. Для формы главной необходимо отдельно разрешить это узкое изменение и повторить её визуальную приёмку.
2. **download_served / NOT_EXECUTED.** Реальный ответ lead.php на хостинге, фактическая выдача байтов, доставка почты покупателю и оплаченный E2E не проверялись. Ответы для клиентской формы и pending локально подменялись. Серверное подтверждение download_served требует отдельной согласованной задачи; оно не подменяется download_click.
3. **Боевые цели Метрики / NOT_EXECUTED.** Отправка новых целей проверена в локальном перехватчике; настройки целей и KPI не менялись. Прежнее серверное magnet_delivered не считать подтверждением скачивания. EVENT_CONTRACT.md фиксирует смысл событий.
4. **Публикация / NOT_AUTHORIZED.** Онлайн staging не создавался. Готовая версия проверена локально; рабочий сайт остаётся с исходными ошибками до отдельного решения о публикации. Перед будущим выпуском повторить сравнение live SHA с PUBLIC_FILES.json: параллельные сессии могут менять сайт.

## Ошибки проверки и устранение причин

- Playwright не имел браузерного бинарника; CDN вернул HTML Site Unavailable вместо ZIP. Это инфраструктурная ошибка, не дефект сайта. Chromium получен отдельным локальным пакетом, системная установка не выполнялась.
- Первые два ложных падения smoke: success.html ошибочно проверялся как индексируемая страница; число ссылок P4 было принято за три, хотя их шесть. Проверки уточнены по фактической структуре; отдельно исправлены неверные success metadata.
- Исторические T1/T4/T5 проверялись как автоматические редиректы, хотя это страницы с кнопкой перехода. Приёмка исправлена на реальный clickpath; сами исторические страницы не изменялись.
- PHP отсутствовал; бинарник и mbstring извлечены только во временную папку. После устранения зависимости нативные локальные проверки прошли; настройки сервера и ОС не менялись.

## Источники правовой развилки

Проверены тексты ст. 5 и 63 Закона № 127-ФЗ: текущие платежи отделяются от реестровых требований, а риск неплатежа не подменяет судебную стадию. Точные сроки для всех процедур не унифицировались.

- https://www.consultant.ru/document/cons_doc_LAW_39331/b98b0fa41fd3af9378e035703cf9c55508b074fe/
- https://klerk.systems/docs/fz_127_2002/article/63/
- https://kad.arbitr.ru/
- https://bankrot.fedresurs.ru/
