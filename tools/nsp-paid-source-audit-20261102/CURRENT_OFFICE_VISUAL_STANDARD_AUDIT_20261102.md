# НСП — контроль оформления текущих Word и Excel, 02.11.2026

**Режим:** READ_ONLY / NO_BUYER_FILE_CHANGE / NATIVE_VISUAL_REVIEW_PENDING. Дата относится к снимку файлов, а не к свежему запуску нативного Office.

## Исходные решения
- `products-storage/VISUAL-STANDARD.md`: белый фон, графит **#262F37**, сдержанное золото **#8E6F32**, нейтральная заливка полей **#F2EFE9**, тонкие границы **#D9D9D9**. Эталон — P2 от 09.10.2026.
- `tools/EDITORIAL_BUSINESS_STANDARD.md`: официальные формы должны **сохранять оригинальное оформление**; их нельзя менять ради фирменного стиля. Шрифт, реквизиты, сетка и печать имеют приоритет.
- Решение владельца 28–29.10: таблицы в одном Word-документе должны иметь одинаковые левую/правую границы; блоки «передача / ответ / подписи» при необходимости разделены и выровнены; проверять ширину с учётом реальных полей листа.
- Для собственных рабочих Word-форм используется преимущественно Arial, основной текст обычно 10 пт, компактные таблицы 8–10 пт; абсолютного единого кегля для всех официальных форм нет.
- Для Excel различать ввод/формулы/результат. Жёлтая заливка ввода, синий текст исходных данных, чёрный текст формул и зелёные межлистовые ссылки являются отдельной функциональной кодировкой некоторых книг, **не** оправданием старых синих заливок шапок.

## Точная проверенная библиотека
`/mnt/server-data/nsp/product-library/accepted-current-20261102/`: **11 платных ZIP + 10 ознакомительных ZIP**, дополнительно имеется один отдельный ознакомительный PDF (в аудит DOCX/XLSX не входит). Основание состава: `PORTFOLIO_RELEASE_ARCHIVE_CHECKPOINT.json` текущей ветки.

| Метрика | Наблюдение |
|---|---:|
| DOCX | 141, из них 113 платных и 28 ознакомительных |
| XLSX | 37, из них 28 платных и 9 ознакомительных |
| Ячеек XLSX с формулами (OOXML, не тест-кейсы) | 5 434 |
| Таблиц верхнего уровня Word | 344 |
| Фиксированных таблиц Word в платных продуктах | **295/295**: `9866 twips` |
| Автоматическая ширина Word в ознакомительных материалах | **49 таблиц в 16 DOCX**, 8 комплектов |

В 16 DOCX указано `tblW=auto`; их `tblGrid` — 8640 либо примерно 9693–9695 twips. Соответствующая доступная ширина страницы 8640 либо 9752 twips. Статическая геометрия **не доказывает визуального нарушения**; класс `AUTO_WIDTH_RELAYOUT_RISK`. Не навязывать ширину 9866 на страницах с доступными 8640 twips.

По наследованию и темам Word обнаружены применяемые Arial, Cambria, Calibri, Times New Roman. В части ознакомительных документов имеются старые синие цвета заголовков. Тема Word должна раскрываться прежде, чем объявлять шрифт несоответствующим.

## Адресные кандидаты Excel
**Оранжевая заливка `#E85D22`:**
- P4: `35A-rabochiy-zhurnal-proizvodstva-rabot.xlsx`, `36A-rabochiy-reestr-vhodnogo-kontrolya.xlsx`, `37-reestr-pasportov.xlsx`, `38-reestr-id.xlsx`.
- P7: `02-perechen-rabot.xlsx`, `03-kalendarnyy-plan.xlsx`, `05-grafik-platezhey.xlsx`.

**Синяя заливка `#366092` / `#1F4E78`:**
- P4: `06-reestr-zamechaniy.xlsx`, `07-grafik-ustraneniya.xlsx`.
- P5: `04-raschet-ubytkov.xlsx`, `05-reestr-uderzhaniy.xlsx`.
- P13: `63-reestr-zatrat-po-obektu.xlsx`.
- 6 ознакомительных книг в `FREE_akt-skrytyh-rabot`, `FREE_avans`, `FREE_dogovor`, `FREE_dop-raboty`, `FREE_ispolnitelnaya-dokumentaciya`, `FREE_vozvrat-ks`.

В 6 ознакомительных XLSX отсутствует именованная область `Print_Area`: это запрос на проверку печати, **не доказательство обрезки**. A3 является допустимым форматом широких ведомостей; не менять его на A4 автоматически. В книгах встречаются Arial, Calibri и Times New Roman; роль шрифта и официальный статус файла должны проверяться адресно.

## Вывод и следующий этап
1. Платные Word-таблицы по **номинальной внешней ширине** статическую проверку прошли. Визуальный контроль отступов, переносов, длинных строк и подписей — отдельный gate.
2. Следующая атомарная задача: **P4/35A**, затем P4/36A, 37, 38 и P7/02, 03, 05. Проверить в Excel исходный вид оранжевых элементов; при подтверждении — кандидат *только со сменой служебных цветов*, при сохранении формул, XML-значений, валидации, печати и read-back SHA.
3. Следом P4/P5/P13 — выяснить семантику синих заливок. Не трогать функциональную синюю окраску вводимых значений.
4. Ознакомительные DOCX с автошириной — проверить только там, где есть неравные реальные границы или риск с длинным заполнением; сохранить узкие оригинальные поля.
5. Новый `FULL_QA_PASS` и выпуск **не присваивать** до сравнения исходной и новой редакции и нативного Word/Excel-испытания точного кандидата.

**Ограничения:** проверены OOXML, ZIP CRC, оформительские свойства и формульные адреса, но не проведён новый full native Office visual QA. Никакие текущие ZIP, цены, SKU, сайт и платёжный контур не менялись. Инструментальная среда Desktop Commander `db` при последней проверке 03.11 оказалась offline; новый файл Excel в этом этапе не исправлен.

Локальные machine-readable evidence (созданы в предыдущем этапе): `CURRENT_DOCX_TABLE_GEOMETRY_AUDIT_20261102.json` и `CURRENT_OFFICE_PALETTE_FONT_EXCEL_AUDIT_20261102.json` в `/home/denis/projects/nsp-paid-source-audit-20261102/tools/nsp-paid-source-audit-20261102/`.


## 03.11.2026 — targeted deterministic P4/P7 color gate (new evidence)

Prior read-only XLSX OOXML sample recorded the legacy orange `#E85D22` as *assigned cell-fill styles* in exactly seven scoped workbooks. Breakdown by workbook (counts refer to styled XML cells, **not** verified native Excel-visible cells):

| SKU | Workbook | Assigned orange cells |
|---|---|---:|
| P4 | 35A-rabochiy-zhurnal-proizvodstva-rabot.xlsx | 11 |
| P4 | 36A-rabochiy-reestr-vhodnogo-kontrolya.xlsx | 10 |
| P4 | 37-reestr-pasportov.xlsx | 10 |
| P4 | 38-reestr-id.xlsx | 17 |
| P7 | 02-perechen-rabot.xlsx | 9 |
| P7 | 03-kalendarnyy-plan.xlsx | 9 |
| P7 | 05-grafik-platezhey.xlsx | 10 |
| **Total** | **7 workbooks** | **76 cells** |

A separate **read-only** Python stdlib OOXML checker `nsp_p4_p7_excel_palette_gate.py` was created and tested in the conversation artifact space, SHA-256 `02da173fd47834a7ea0215a6df1beb50bd000ba19e681a0381f5d3f3a78341fd`. Local acceptance: `--selftest` **PASS** (assigned style, unassigned style, neutral substitution, wrong source archive SHA, exact member path) and Python compilation **PASS**.

The checker pins the exact **P4 v3** archive SHA `bcba234220c0f52e5a86b5ba3c70c527d086146301030d1f32197e9fa6e264fc` and **P7** archive SHA `99e877fc851843a79c8524f508529ecab7da049aa6886590fcbce68a97676e24`. It counts only *actually assigned* solid-fill `cellXfs` styles, not unused palette definitions. It does **not** verify conditional formatting, actual Excel rendering, formulas or production, and was **not** run against current exact archives in this turn because `ai-workstation` was OFFLINE in Desktop Commander `db`.

**Next gate:** after the existing server connection is restored, run this one tool against the two SHA-pinned current archives, then the native Microsoft Excel visual check for **P4/35A** only. If visibly off-standard, prepare an isolated style-only candidate; exact formula, cell-value, validation and print-feature equality and final native preview must pass before nomination. Do not modify published ZIP/SKU or release from a static result alone.


## 03.11.2026 — exact native visual P4/35A

**Executed and verified on restored Desktop Commander db / ai-workstation; this is new evidence, not an inferred result from OOXML.**

- Exact P4 v3 buyer ZIP SHA-256: `bcba234220c0f52e5a86b5ba3c70c527d086146301030d1f32197e9fa6e264fc`. Current buyer member `35A-rabochiy-zhurnal-proizvodstva-rabot.xlsx`: `54ef5d86e81ab120910cc5ad1889c54ff5253951ec06a180be655eaf4cf65cc4` (9442 bytes).
- Original workbook transferred unchanged using the *existing* loopback HTTP 8784 (observed GET 200). The Windows guest `certutil -hashfile` confirmed exact SHA **before and after** opening the file. Microsoft **Excel LTSC 2024 GUI** opened it successfully under the existing `nspqa` interactive session. No new guest, laptop, activation, production or buyer files changed.
- **VISUAL DEFECT CONFIRMED:** 11 cells with `#E85D22` comprise the bright orange worksheet header. The color is visibly different from the approved restrained graphite/warm-neutral document palette. Spreadsheet column labels including `Рабочие/техника`, `Материалы`, `Ответственный` break awkwardly across lines; header readability needs addressed correction.
- **Print preview inspected:** Microsoft Print to PDF, **A3 landscape**, “Fit All Columns on One Page”, **three print pages** reported. Only page 1 was inspected as a native screenshot. No claim of all-pages print approval or filled-example testing. No formulas are present in this specific P4/35A workbook; the seven-book static scan's formula totals are a different scope.
- The Office LTSC activation dialog was dismissed with Esc; no activation was attempted. Excel closed without saving, Windows `tasklist` returned no remaining `EXCEL.EXE` / `WINWORD.EXE`, exact guest SHA remained unchanged, the existing VM user service remained active, and `active_office_job` returned to null.
- Two native screenshots are preserved in the server QA path `.../p4-35a-visual-20261103/`: visible worksheet SHA `4b72fabfb5c17302e1450ee46775fb6ef6692798e801f8409959cd01b115de07`, print preview SHA `f6c0fbc6631f6e2e0813f21a7067433f1392806a8ab63763ff719e20e374fa86`.
- Durable JSON receipts are in this branch: `P4_P7_PALETTE_EXACT_READONLY_20261103.json` and `P4_35A_NATIVE_VISUAL_RECEIPT_20261103.json`; re-read-back PASS.

**Next atomic work:** `P4/35A-STYLE-ONLY` candidate (not yet modified). Replace only legacy orange header fills with approved `#F2EFE9` and corresponding readable graphite text, or graphite header with white text if the canonical document standard for that table requires; improve row-3 wraps locally. Before accepting any patch, prove preserved input/formulas, workbook structure, data validation, layout/print settings, and perform native Excel visual/print at the *final* SHA. Then progress to the remaining six named files as separate bounded deltas. Do not modify accepted archives or automatically publish them. Status: `ONE_NATIVE_DEFECT_CONFIRMED / 6_STATIC_CANDIDATES / RELEASE_UNCHANGED`.


### Дополнительный gate: белый шрифт, оранжевый фон только строки 3

Read-only квитанция [`P4_P7_ROW3_FONT_FILL_READONLY_20261103.json`](P4_P7_ROW3_FONT_FILL_READONLY_20261103.json) доказала для всех 7 исходных XLSX: **76/76** ячеек `#E85D22` расположены исключительно на листе 1 в строке 3, а текст во всех них уже **белый и полужирный** (`00FFFFFF` / `FFFFFFFF`). Адреса: P4 `A3:K3`, `A3:J3`, `A3:J3`, `A3:Q3`; P7 `A3:I3`, `A3:I3`, `A3:J3`.

**Минимально достаточный style-only патч:** только цвет заливки применяемого заголовочного стиля `#E85D22 → #262F37`. Оставить белый шрифт, формулы, значения, относительные ширины, границы, строку заголовка, проверки ввода и печатные параметры как есть. При таком выборе исходный контраст белого по графиту сохраняется и не нужен массовый рефакторинг форматирования. Вопрос читаемости переноса слов в `P4/35A` вынести в отдельный пункт локальной приёмки; не расширять его на остальные файлы без осмотра. Ни исходная книга, ни действующий архив при проверке не изменялись. **Это утверждённая техническая спецификация кандидата, а не уже применённая правка.**


### Самокоррекция 03.11: residual orange FONT in 7/7

В дополнительной независимой проверке обнаружено, что семь кандидатов с исправленной заливкой **сохраняют применённый шрифт #E85D22 на втором листе (A1)**. Это отдельная проблема и прежнее обозначение `7/7 color fixed` относится **только к заливкам**, не ко всей палитре. Класс дефекта `PALETTE_QA_COVERAGE_GAP`; причина — первоначальный gate не проверял применённые `cellXfs/fontId`.

Новый негативный тест [p4_p7_full_orange_palette_gate_20261103.py](p4_p7_full_orange_palette_gate_20261103.py) на текущих семи кандидатах дал **ожидаемую блокировку** `BLOCK_RELEASE_APPLIED_ORANGE`, exit **2**, число остаточных шрифтовых нарушений **7**, число нарушений заливки **0**. Полный список адресов и SHA: [SEVEN_PALETTE_APPLIED_FONT_CHECK_20261103.json](SEVEN_PALETTE_APPLIED_FONT_CHECK_20261103.json).

Точная корректировка следующей QA-редакции: только цвет акцентного заголовка A1 листа «Инструкция», `#E85D22 → #8E6F32`. Текущую историческую QA-упаковку (SHA `0312735ccc7789d84ce4c172c11400a7f5f6b8013b5a889279b20e297b704357`) **не заменять и не выпускать**. Новый candidate v2 должен пройти расширенный gate по **обоим классам цветов** и отдельный native Office 2024 / preview конечного SHA. Новые исправленные XLSX v2 пока **не изготовлены**. [Полное дополнение](P4_P7_RESIDUAL_FONT_COLOR_FINDING_20261103.md).


### 03.11.2026 — завершённые QA v2 и окончательный HOLD

**Current QA v2 exact artifact:** [`NSP_P4_P7_GRAPHITE_GOLD_QA_V2_20261103.zip`](NSP_P4_P7_GRAPHITE_GOLD_QA_V2_20261103.zip) (QA branch only, not public product), SHA-256 `739bf32d811f48bd7e3f41d0b45418bddba4eb31e07b1db5d99abc3d30d3fcc6`, Git blob `6440b509e51ac4b5d4d2ad4ddfe7fe6d6492515e`, 60 531 bytes, 11 members including 7 XLSX. The blob's GitHub readback SHA and encoded byte length were verified against the source file; ZIP CRC and every member byte checked against its manifest. Original P4 v3 / P7 review-v2 buyer ZIP SHA unchanged.

**Exactly two approved color-only deltas since original:** 76 applied header *fills* on row 3 of sheet 1: `E85D22 → 262F37`; 7 applied instruction-title *font colors* in sheet 2 cell A1: `E85D22 → 8E6F32`. All 7 resulting workbooks independently verified against exact original ZIP and prior v1: unchanged non-style ZIP members, identical workbook cells/formulas/print settings/validation, and no other `xl/styles.xml` token changed. Original orange applied-font and applied-fill count **0**.

Independent acceptance [`QA_V2_INDEPENDENT_ACCEPTANCE_R2_20261103.json`](QA_V2_INDEPENDENT_ACCEPTANCE_R2_20261103.json) includes two **actually executed negative mutation tests**: unrelated `xl/styles.xml` byte change and worksheet byte change each caused the expected specific gate rejection. The original preliminary verifier's weak negative test is superseded by R2. Exact seven new SHA-256 identities and original provenance are in [`QA_V2_GOLD_FONT_CANDIDATES_MANIFEST_20261103.json`](QA_V2_GOLD_FONT_CANDIDATES_MANIFEST_20261103.json); archive receipt [`QA_V2_ZIP_RECEIPT_20261103.json`](QA_V2_ZIP_RECEIPT_20261103.json).

**Gate still pending:** Microsoft Excel LTSC 2024 native open/print of final v2 SHA, separately for the changed seven files; P4/35A needs an explicit legibility/line-wrap review of its headers (F/G/K) on all print pages. The older visual proof establishes the original orange header only, not print acceptance of v2. The prior tool-safety block on the VM transfer is not a workbook defect. Do not bypass that block by a different transport, do not equate artifact_tool/OOXML checks to native Excel. **No publication, no buyer ZIP replacement, no change to protected SHA, price, SKU or payment.**

**Final atomic status:** `V2_QA_STATIC_FULL_PASS / NATIVE_OFFICE_FINAL_SHA_PENDING / PUBLISH_HOLD`. The QA ZIP is an immutable candidate; the accepted product editions remain unchanged.
