# P13: отдельная корректировка печати

Исходная зависимость — independently accepted style-only checkpoint PR #494, head `20188af5a9dd391d41256aac2118f0e632722d4a`, candidate SHA256 `643ec9ffd2ab6d3285445ae3d2dfc93db470ef4661db41f30d5fedbb1d3df968`. Независимый verdict `ACCEPT_STYLE_ONLY_WITH_PRINT_STOP`, report SHA256 `7d250ae17f31f864bfcea66e5d1b21e887c0145e54f3c9abf08c97a295c04e6e`, сохранён в proof packet. Новый print-only scope отдельно разрешён координатором в рамках полной переупаковки и согласованного Excel-дизайна.

Print candidate: `63-reestr-zatrat-po-obektu-Business_Print_candidate.xlsx`, SHA256 `2262235a4f2d3513bed99c58a261053181bf5510af684e9a22453ac529c63e52`. Style checkpoint и первоначальный продукт не заменяются.

## Что исправлено

Фактический предыдущий PDF на 8 A4 страницах делил реестр по группам столбцов, а labels/instructions выводил раздельно. Новый паспорт заранее выбрал A3 landscape для десяти существующих столбцов шириной224 characters: A4 fit рискует уменьшить font ниже заданного8pt. «Как заполнять» — A4 landscape. FitToWidth=1, FitToHeight=0, exact print areas A1:J56 и A1:B9; первая строка повторяется как print title.

Изменены только pageSetup, pageSetUpPr fitToPage и print area/title defined names. Widths/heights, cell styles, формулы, input values/text, validation, protections, number formats, names вне print, остальные ZIP parts сохранены. Gate сравнил native XML после удаления только объявленных print nodes; styles.xml побайтово неизменен. Дополнительного Calc-пересчёта не делали: style checkpoint уже имеет фактические4/4 fixtures, новая единица не меняет вычисления.

## Фактическая проверка

Один bounded PDF export в отдельном профиле, timeout45s. Получено3 страницы: две A3 landscape (full-width registry и summary), одна A4 landscape (labels вместе с instructions). Все три страницы экспортированы в PNG и осмотрены автором. Минимальный фактически извлечённый font size8.705pt >=8pt; ноль text bbox за границами страниц. Графы реестра больше не разбиты горизонтально. Полная таблица51 строк находится на первой странице; summary на второй. A3 бумага нужна для сохранения этой разборчивости.

Все184 непустые source literal cells найдены целиком после whitespace normalization хотя бы одним из двух PDF extractors; каждый используемый extractor указан в per-cell coverage. Формулы и cached-output сценарии защищены native preservation и accepted Calc proof предыдущей единицы. Source checkpoint и новый candidate SHA до/после rendering совпали.

Первичная PyMuPDF coverage ошибочно пропустила colon C54 из-за mixed fallback fonts и порядка spans; фактический PNG показывает полный label, Poppler layout извлекает его полностью. Poppler layout в свою очередь вставляет labels между wrapped lines длинных instructions; PyMuPDF сохраняет полные instruction strings. Класс `TEXT_EXTRACTOR_READING_ORDER`; правило — проверять exact whole-cell text двумя независимыми extraction layouts, не удалять пропущенные слова/пунктуацию из требований. Проверка исправлена на уже созданном exact PDF; Office повторно не запускался, timeout не увеличивался.

Статус: авторский `TEXT_READABILITY_GEOMETRY_PASS`, native print-only preservation PASS, независимая print QA требуется. Native Microsoft Excel approval, правовая/currentness/full product/SaleReady приёмка здесь не заявляется. Продуктовые пути, main и deploy не меняются.
