# P13: кандидат согласованного делового оформления

Одна книга: `63-reestr-zatrat-po-obektu.xlsx`, исходный SHA256 `b7b1e9377095d0d8b28213401a66bdb868817584c677f38edcda94380ce477c2`. Исходник не изменялся. Candidate SHA256 `643ec9ffd2ab6d3285445ae3d2dfc93db470ef4661db41f30d5fedbb1d3df968`.

Эталон: owner-approved `P1_04_Uchet_Business_Design_v1.xlsx`, SHA256 `93252d5711cbbd33e682b3f9400fe6ee9aa9ed02c49cf8302ae89976ffc20d77`. Metadata contract PR #491, exact accepted head `6d1f6979b24d8d7331f29bd2d306de6a1bab3eb1`; независимый review SHA256 `1cbf2a2cf22e2821e9c9fb9e3751f62094cfa9c358fc17a6973492de843c28b3` сохранён. Эта приёмка не является приёмкой целевой книги.

## Изменение

Адресная карта ролей создана до переноса по фактическим labels/formulas и тексту листа «Как заполнять». Цвет и защита не используются как источник semantic role. 544 уже существующие ячейки получили font/fill/border/alignment по согласованным образцам: графитовые header, светлый фиксированный каталог, приглушённый кремовый ввод, серые formula outputs, спокойные инструкции. Новых текстов, сводок, формул или ячеек нет. Summary labels сохраняют исходный font/размер/bold с точным графитовым color reference.

Native ZIP overlay меняет только `xl/styles.xml` (append компонентов и cellXfs) и cell `s` attributes двух worksheets. Все прочие parts побайтово сохранены; worksheet XML после удаления только `c/@s` совпадает. Все исходные style records сохранены. Формулы, constants/text, input instructions/status text, validation (включая отсутствие правил), number formats, protection, names, print/layout settings, widths/heights не изменяются. Проверка openpyxl сравнивает значения атрибутов protection.locked/hidden, а не equality StyleProxy: сравнение proxy разных книг возвращает false даже при одинаковых свойствах. Ошибка harness обнаружена и исправлена; native preservation gate прошёл.

## Фактическая проверка

Два изолированных профиля LibreOfficeDev 26.8.0.0.alpha0, оба процесса в пределах 45 секунд: Calc 18.75 с, PDF 18.77 с. Применены существующие P13 fixtures (вымышленные суммы, как в baseline): H2=10000/H3=20000/H4=15000; H55=60000 либо 0. Четыре checks PASS: H54=45000 в обоих случаях, H56=.75 и blank при нулевой прибыли. Формулы обоих outputs после Calc сохранились. Исходник, candidate и reference SHA остались неизменными. Нет model calls/paid API.

Семь target-specific in-memory negative gates фактически обнаружили изменения formula, text/input, validation, sheet protection, print settings, number format и cell protection. Подробности в `negative-preservation-gates.json`.

## Визуальное наблюдение и открытый gate

Фактические PDF созданы для candidate и exact approved reference. Осмотрены candidate pages 1,7,8 и reference page1 (PNG в proof ZIP). Палитра и разделение ролей согласуются с raw reference components; это наблюдение, не native Excel approval.

Candidate PDF содержит 8 A4 страниц. Сохранённые исходные default print/layout settings и ширины дают горизонтальные полосы: таблица разбита по группам столбцов; «Как заполнять» labels на странице7, instructions на странице8. Полная печатная приёмка НЕ ПРОЙДЕНА. Baseline PDF исходной P13 в этой задаче не экспортировался; происхождение limitation установлено по сохранённым настройкам и ширинам, не сравнением двух baseline renders.

Нельзя исправлять это внутри style-only паспорта, который требует exact print preservation. Следующая отдельная задача: разрешённая print-layout корректировка одной книги (fitToWidth, page orientation/print areas, readable scale/row heights по конкретному контракту), без изменения semantics; actual PDF render и независимая приёмка. До этого candidate не называется готовым продуктом. Другие открытые gates: независимая target QA и native Excel owner review; юридическая/currentness/release/SaleReady здесь не заявляются.
