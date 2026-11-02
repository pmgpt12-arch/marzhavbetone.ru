# QA24 — контрольная точка Word/Excel и публикации P4/P5

Дата: 02.11.2026 (Красноярск). Ветка: `qa/nsp-t2-t3-consolidation-20261101`, Draft PR #681. Режим: **VM_ONLY_NO_LAPTOP**. Статус: `WORD_NATIVE_VISUAL_PASS; EXCEL_COM_SMOKE_NOT_RUN; RELEASE_HOLD`.

## Исходные утверждённые кандидаты

| Комплект | Архив | SHA-256 | Файлов |
|---|---|---|---:|
| P4 + содержание T2 | `P4_PTO_s_peredachey_ID_v2.zip` | `e99f2a8f7b968c19f9d81224fdc9bc4f149ba502caec87c7c9746f0159be0b26` | 30 |
| P5 + содержание T3 | `P5_Zashchita_s_vozrazheniyami_T3_v2.zip` | `25ce378ee8fd84079b0edd2d57d816a2aaa77585a2a7e7172666e1f846f7dc05` | 30 |

Оба ZIP загружены в этот PR. 25 исходных файлов P4 и 26 исходных файлов P5 сохранены побайтно. Новая редакция P4: дополнение XLSX 44 и DOCX 45–47, обновлён PDF 00. Новая редакция P5: изменены DOCX 12/15/20 и PDF 00; самостоятельные дубли T3 не добавлялись.

## Проверенный результат Microsoft Word 2024

**6 из 6 изменённых DOCX: NATIVE PASS + VISUAL PASS.**

- P4: `45-soprovoditelnoe-pismo-peredachi.docx`, `46-slovar-poley-peredachi.docx`, `47-poryadok-peredachi-id.docx`.
- P5: `12-algoritm-pri-navyazannoy-vine.docx`, `15-vozrazhenie-na-odnostoronniy-akt.docx`, `20-vozrazhenie-na-zachet-uderzhanie.docx`.

Все 6 DOCX действительно открыты в Word LTSC 2024 на ВМ, сохранены в отдельные копии, повторно открыты, проверено совпадение текста и количества таблиц, получены PDF. Исходные SHA совпадают. Нативная квитанция находится на `ai-workstation:/home/denis/projects/nsp-t2-t3-overlap-20261031/native-qa/r5/QA24_NATIVE_EVIDENCE_R5.zip`; SHA-256 `9678ca1a8dd51370daba2314aa2f530b808e930df592b421d73944d9f3e5850c`. Общий статус этого архива `FAIL` исключительно из-за последующей проверки Excel; **конкретные шесть строк Word имеют `NATIVE_PASS_VISUAL_PENDING`** и проверенные выходные SHA.

Визуальная приёмка Word завершена отдельно: все **16 из 16 страниц A4** просмотрены в трёх контактных листах; не обнаружены обрезания, пустые страницы или неправильные глифы. Технически проверены размеры листов, наличие текста и правые границы. Квитанция `ai-workstation:/home/denis/projects/nsp-t2-t3-overlap-20261031/native-qa/word-visual-20261102/WORD_NATIVE_VISUAL_ACCEPTANCE.json`, SHA-256 `2ee4f2df15ad9c8ec75dfac8a7c1415b916ef680612a5c21e47a5a4ae4022bb7`.

**Word повторно не прогонять**, пока конкретный дефект изменённого документа не докажет необходимость.

## Остаток — XLSX P4 №44

Выполнена структурная проверка `44-opis-peredavaemogo-komplekta.xlsx`: 4 листа, 124 формулы, итоги C132/E132/C133/E133. Однако нативная Excel-проверка не принята.

Последовательность наблюдавшихся причин:

1. R5 Word 6/6 PASS; Excel ошибка на попытке установки `Application.Calculation` перед открытием.
2. R6 вызов `Workbooks.Open([string]$path,0,$true)` не подтвердил `ReadOnly`.
3. R7 остановлен защитой: обнаружен оставшийся процесс R6.
4. R8 даже с атрибутом «только чтение» у копии не смог подтвердить `ReadOnly`; `FullName` возвращалось пустым.
5. Независимая диагностика COM на оставшемся процессе R8 (PID 2856, точное совпадение времени старта с control) дала `Excel.Application.Workbooks = null`, без изменения файлов или процессов. Квитанция `native-qa/QA24_EXCEL_COM_DIAG_RECEIPT.zip`, SHA `7da8143abc5fcd3a30144c8b030640ce1b6142044fdf39e15b4b66aa3d25d5ce`. Это **COM/runtime**, не доказанный дефект XLSX.
6. PID 1900 (R6) и PID 2856 (R8) завершены адресно, после совпадения PID, UTC-времени старта, Session 1 и проверки `Local\NSP-Office-COM-v1`; чужие PID не затронуты. R8 cleanup receipt SHA `64a09d0263e5d789df18b0449f07cecbe0472ebb6d5419d82df5abbe79500d09`.
7. Применено ранее принимавшееся (29.10) восстановление пользовательского `HKCU\Software\Microsoft\Office\16.0\Common`: создан backup `Common_Backup_QA24_20261102T002115`, восстановлена новая Common с сохранением Identity, Licensing, Privacy, TrustCenter, LanguageResources и проверкой числа подразделов. **COMMON_CACHE_RESET_VERIFIED**; лицензия не изменялась. Receipt SHA `54b7355a7381919f3ce6ccd16a18c5e469f0559f6d42bc136b7acb09a5d8fa72`.
8. Подготовлен **новый минимальный** Excel COM smoke: создать временную книгу, вычислить 10+5=15, сохранить XLSX, открыть read-only, сверить 15 и завершить свой PID. Исходник: `native-qa/excel-min-smoke/start.ps1`, SHA `a1a3fac3fe03285b1030963de8abb1442f1bce179f57c91c32f3e4e8413106ed`. Вызов запуска `excel-min-smoke/launch.py` был **заблокирован системой безопасности удалённого инструмента ДО исполнения**. Нет ни smoke receipt, ни основания объявлять Office восстановленным для Excel. Запуск через обходной инструмент не предпринимался.

Класс текущего блокера: `TOOL_SAFETY_BLOCK_FOR_EXECUTION`; предшествовавшая неисправность: `EXCEL_COM_COLLECTION_UNAVAILABLE`. Не классифицировать её как `MODEL_CAPABILITY` или неисправность продукта.

## Следующее действие после восстановления разрешённого выполнения

1. Убедиться, что task ID `qa24-excel-min-smoke-20261102` ещё не исполнен; проверить отсутствие прежнего host receipt и существующего `active_office_job`. Только после этого **один** ограниченный smoke уже подготовленным скриптом, без новой очереди и ноутбука.
2. Если `EXCEL_COM_SMOKE_PASS` с 15 при reopen — выполнить **только один XLSX №44** на изолированной копии, проверить 0/0/0/0 (пустая), 3/3/1/1 (заполненная), повторное открытие, PDF/печать, MapPaperSize=false и SHA. Подтвердить визуально.
3. Если smoke FAIL — классифицировать точную ошибку, STOP. Не увеличивать timeout и не делать blind retry.
4. Только после Excel native PASS + визуальной QA проводить scoped production preflight. P4/P5 текущие архивы всё ещё прежних редакций; новый publisher не готов. Старая реализация P4 жёстко привязана к 26 файлам и старому SHA, повторно использовать её без версии и проверок нельзя.
5. После выпуска новых P4/P5 удалить T2/T3 из новых предложений/новых оплат, **сохранив обработку исторических заказов и выданных ссылок**. Проверить live ZIP байт-в-байт, HTTP, негативный checkout и квитанцию публикации.

**Production в ходе этой QA не изменялся. FULL_QA_PASS=false; RELEASE_ALLOWED=false.**
