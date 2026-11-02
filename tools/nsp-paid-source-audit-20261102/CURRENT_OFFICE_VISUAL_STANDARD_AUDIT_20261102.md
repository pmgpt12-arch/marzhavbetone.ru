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
