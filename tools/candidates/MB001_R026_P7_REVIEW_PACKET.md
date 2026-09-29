# MB001 · Р-026 · P7 — проверочный пакет для нормативного перечита

Дата сборки пакета: 29.09.2026. Пакет собран скриптом `tools/candidates/evidence/MB001_R026_P7_PACKET/_tools/build_packet.py`, проверен `verify_packet.py` рядом с ним.

## 1. Режим и границы

- Только подготовка материалов для независимого перечита по Р-026. Юридических выводов, оценок «верно / неверно», предложений правок в пакете нет.
- Продукт, договор, протокол, инструкция, страница товара, генератор, цены, SKU, #315, `main` и другие ветки не менялись. Коммит пакета добавляет только `tools/candidates/MB001_R026_P7_REVIEW_PACKET.md` и каталог `tools/candidates/evidence/MB001_R026_P7_PACKET/`.
- В таблицах записаны факты: текст, место, источник, связь либо отсутствие источника. Слова «совпал / не совпал» в картах означают побайтовое или построчное сравнение двух текстов, а не оценку содержания.
- Полные извлечения лежат в каталоге доказательств; здесь — индекс и сводки.

## 2. Preflight и версия #315

| Что | Команда | Результат |
|---|---|---|
| PR | GitHub API `pull_request_read get #315` | Draft, open; ветка `claude/gifted-wright-otl19h-p7`; голова `38a47a505b48a46d6c8f663588b255af20aa1fc9`; база `main` `b89f081fe94249231896bcf40b8a188824ac9301` |
| Ветка пакета | `git checkout -B <ветка пакета> 38a47a505b48a46d6c8f663588b255af20aa1fc9` | пакет стоит на голове #315: `git merge-base --is-ancestor 38a47a5 HEAD` → да |
| Рабочее дерево до создания файлов | `git status --porcelain \| wc -l` | 0 (измерено 29.09.2026 до первого файла пакета) |
| Файлы продукта не изменены относительно #315 | `git diff --quiet 38a47a5 -- products-storage products products-config.php tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md` | изменений нет |
| PHP | `php -r 'echo PHP_VERSION;'` | 8.4.19 |
| ZipArchive | `php -r "echo class_exists('ZipArchive');"` | да |
| Реальная выдача | `php tools/candidates/evidence/MB001_R026_P7_PACKET/_tools/build_p7.php . <tmp>` → `mvb_build_product_zip('p7')` (`products-config.php:456`) | архив собран, 13 записей |
| Каталог продукта | `products-config.php`: `'p7' => dir 03-dogovor-podryada, zip 03-dogovor-podryada.zip` | `products-storage/03-dogovor-podryada/` |
| Страница P7 | — | `products/p7-dogovor-podryada.html` |
| START-HERE | — | `products-storage/03-dogovor-podryada/00-START-HERE.txt` (в ZIP) |
| MANIFEST | — | `products-storage/03-dogovor-podryada/MANIFEST.md` (служебный, в ZIP не идёт) |
| Генератор | `ls products-storage/build_paid_03.py` | `products-storage/build_paid_03.py` — пишет 01, 10, 00-INSTRUKCIYA.docx/.pdf, 00-START-HERE.txt |
| Отчёт реализации #315 | — | `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md` (в дереве головы #315) |
| Gap-отчёт (#307) | `git fetch origin claude/gifted-wright-otl19h`; `git cat-file -e a1633c2:tools/candidates/MB001_R2_P7_GAP_SPEC.md` | найден: ветка `claude/gifted-wright-otl19h`, коммит `a1633c2bc0c4261a7d9653d1c3876f40dea0ed18`; в дереве #315 файла нет |
| Исходный договор / референс владельца | поиск по `git ls-files` обоих репозиториев (раздел 7) | в репозиториях не найден; отчёт реализации #315 §0: «В репозиторий файл не кладётся» |

## 3. Состав реального ZIP с SHA-256

Архив: `03-dogovor-podryada.zip`, 485643 байт, SHA-256 `c7912334663f5f3fe34c76986e5da504e4794870e80c32e65d90cd3cb5afd6fc`.
Повторная сборка в чистый каталог: SHA-256 `c7912334663f5f3fe34c76986e5da504e4794870e80c32e65d90cd3cb5afd6fc` — байты архива совпали; имена и SHA-256 записей совпали.

| # | Файл в ZIP | Тип | Байт | SHA-256 записи | SHA-256 мастера на диске |
|---|---|---|---|---|---|
| 1 | `00-INSTRUKCIYA.docx` | DOCX | 40556 | `903ef5cdec976142ceae87911435d494f81b5692598454f0afe074fd5ce4cf06` | = запись |
| 2 | `00-INSTRUKCIYA.pdf` | PDF | 62640 | `64b79196dd4592bcc7fe18c88ca8272ab9002d1c9ea281bac22a3424538f18f6` | = запись |
| 3 | `00-START-HERE.txt` | TXT | 4275 | `5d09af3ec368dc39f81f36a451d264255301a98dfc55966abb6be7c49de544df` | = запись |
| 4 | `01-dogovor-subpodryada.docx` | DOCX | 59194 | `a408ba81b7809712abe8e12287e319a4ebfaaead7fb5bbe25f7800108ff284f8` | = запись |
| 5 | `02-perechen-rabot.xlsx` | XLSX | 8792 | `ad2d7f995b6bd276de6e9051b7cc5a93ef4032546001a3b95a8db43e707f719d` | = запись |
| 6 | `03-kalendarnyy-plan.xlsx` | XLSX | 8728 | `a7e559ba286c9a5b17114504f5db60d6483e6d7e7c4f272119c097d1426926ab` | = запись |
| 7 | `04-poryadok-priemki.docx` | DOCX | 38965 | `6d535c76822d74a4cfc4af40977090afb93fe82c66a8a964e023f2cfae1c8864` | = запись |
| 8 | `05-grafik-platezhey.xlsx` | XLSX | 8914 | `a2d147b4830eec42ff75752bd06fd3ab38b5dedb444cd46e0dd39064b28b94e7` | = запись |
| 9 | `06-dopsoglashenie-obem.docx` | DOCX | 38907 | `6667ce895ab8721becb41911323555499d3106afa35c283428d3561e771b7c96` | = запись |
| 10 | `07-dopsoglashenie-sroki.docx` | DOCX | 38879 | `46eecec0d400ec72a50053a2f2d6a33c69a5033d7869968199b53a9bb5505012` | = запись |
| 11 | `08-krasnye-flagi.pdf` | PDF | 86337 | `64b29355a98feaa3838f224d1bb9019998cdeb06357b64d637fa6f6bd0fd6cc9` | = запись |
| 12 | `09-checklist-dogovora.pdf` | PDF | 85622 | `3ec9b05fc1c9f35ed7904910013c39d7d97904b07710cc2d52eaa88315425c07` | = запись |
| 13 | `10-protokol-raznoglasiy.docx` | DOCX | 52474 | `1299ec0cdf1d88bf982a91db03ed79986e255f4917ee19ee4a94b8e7c704c28b` | = запись |

По типам: DOCX — 6 (00-INSTRUKCIYA.docx, 01-dogovor-subpodryada.docx, 04-poryadok-priemki.docx, 06-dopsoglashenie-obem.docx, 07-dopsoglashenie-sroki.docx, 10-protokol-raznoglasiy.docx); PDF — 3 (00-INSTRUKCIYA.pdf, 08-krasnye-flagi.pdf, 09-checklist-dogovora.pdf); TXT — 1 (00-START-HERE.txt); XLSX — 3 (02-perechen-rabot.xlsx, 03-kalendarnyy-plan.xlsx, 05-grafik-platezhey.xlsx).

Служебные и лишние файлы:
- Каталог `products-storage/03-dogovor-podryada/` на диске: 15 файлов. В ZIP не вошли: `00-PISMO-POSLE-POKUPKI.txt`, `MANIFEST.md` — это список `$service` функции выдачи (`.htaccess`, `00-PISMO-POSLE-POKUPKI.txt`, `MANIFEST.md`).
- Записей-каталогов в ZIP: 0; вложенных путей: 0; скрытых и системных имён (`.`, `__MACOSX`, `~$`, `Thumbs.db`): 0.
- Состав ZIP = файлы каталога минус `$service`: да.
- Перечень START-HERE §4 (13 имён) = состав ZIP: да; «файлов в архиве: 13».
- Таблица состава инструкции (`KIT_FILES`, 13 имён) = состав ZIP: да.
- Перечень `MANIFEST.md` (13 имён) = состав ZIP: да.
- Числа файлов, названные на странице (шаблон «N файл…/N готовых файл…»): 13.

## 4. Полный индекс текстов и мест в документах

Каждой записи ZIP — полное извлечение. Метки мест: DOCX — `B<блок> P` или `B<блок> T<таблица> R<строка> C<колонка> p<абзац>`, плюс части колонтитулов, сносок, примечаний; XLSX — `Лист!Ячейка` с формулой и кэшем; PDF — страницы; TXT — `L<строка>`.

| Файл в ZIP | Тип | Сводка извлечения | Полный текст |
|---|---|---|---|
| `00-INSTRUKCIYA.docx` | DOCX | абзацев/ячеек тела: 69; таблиц: 1; слов тела: 773; колонтитулов: 0 (без текста); сносок: нет; примечаний: нет; полей {{…}}: 7 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/00-INSTRUKCIYA.docx.txt` |
| `00-INSTRUKCIYA.pdf` | PDF | страниц: 2; Producer: LibreOffice 24.2; символов текста: 6417 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/00-INSTRUKCIYA.pdf.txt` |
| `00-START-HERE.txt` | TXT | строк: 84; кодировка UTF-8 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/00-START-HERE.txt.txt` |
| `01-dogovor-subpodryada.docx` | DOCX | абзацев/ячеек тела: 253; таблиц: 3; слов тела: 6230; колонтитулов: 1 ([поле: PAGE]); сносок: нет; примечаний: нет; полей {{…}}: 110 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/01-dogovor-subpodryada.docx.txt` |
| `02-perechen-rabot.xlsx` | XLSX | листов: 2 (Реестр A1:I103, Инструкция A1:A3); непустых ячеек: 13; текстовых: 13; формул: 0; ошибок: 0 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/02-perechen-rabot.xlsx.txt` |
| `03-kalendarnyy-plan.xlsx` | XLSX | листов: 2 (Реестр A1:I103, Инструкция A1:A3); непустых ячеек: 13; текстовых: 13; формул: 0; ошибок: 0 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/03-kalendarnyy-plan.xlsx.txt` |
| `04-poryadok-priemki.docx` | DOCX | абзацев/ячеек тела: 26; таблиц: 1; слов тела: 95; колонтитулов: 2 (Приложение: порядок сдачи и приёмки  •  версия 21.07.2026  •  marzhavbetone.ru; МАРЖА В БЕТОНЕ  /  РАБОЧИЙ ШАБЛОН); сносок: нет; примечаний: нет; полей {{…}}: 0 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/04-poryadok-priemki.docx.txt` |
| `05-grafik-platezhey.xlsx` | XLSX | листов: 2 (Реестр A1:J103, Инструкция A1:A3); непустых ячеек: 14; текстовых: 14; формул: 0; ошибок: 0 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/05-grafik-platezhey.xlsx.txt` |
| `06-dopsoglashenie-obem.docx` | DOCX | абзацев/ячеек тела: 21; таблиц: 1; слов тела: 80; колонтитулов: 2 (Дополнительное соглашение об изменении объёма и цены  •  версия 21.07.2026  •  marzhavbetone.ru; МАРЖА В БЕТОНЕ  /  РАБОЧИЙ ШАБЛОН); сносок: нет; примечаний: нет; полей {{…}}: 0 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/06-dopsoglashenie-obem.docx.txt` |
| `07-dopsoglashenie-sroki.docx` | DOCX | абзацев/ячеек тела: 21; таблиц: 1; слов тела: 77; колонтитулов: 2 (Дополнительное соглашение об изменении сроков  •  версия 21.07.2026  •  marzhavbetone.ru; МАРЖА В БЕТОНЕ  /  РАБОЧИЙ ШАБЛОН); сносок: нет; примечаний: нет; полей {{…}}: 0 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/07-dopsoglashenie-sroki.docx.txt` |
| `08-krasnye-flagi.pdf` | PDF | страниц: 1; Producer: ReportLab PDF Library - (opensource); символов текста: 750 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/08-krasnye-flagi.pdf.txt` |
| `09-checklist-dogovora.pdf` | PDF | страниц: 1; Producer: ReportLab PDF Library - (opensource); символов текста: 803 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/09-checklist-dogovora.pdf.txt` |
| `10-protokol-raznoglasiy.docx` | DOCX | абзацев/ячеек тела: 213; таблиц: 3; слов тела: 4978; колонтитулов: 1 ([поле: PAGE]); сносок: нет; примечаний: нет; полей {{…}}: 81 | `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/10-protokol-raznoglasiy.docx.txt` |

Способ извлечения: DOCX — разбор `word/document.xml`, `word/header*.xml`, `word/footer*.xml`, `word/footnotes.xml`, `word/endnotes.xml`, `word/comments.xml` (lxml), включая таблицы и вложенные таблицы; XLSX — openpyxl дважды (формулы и кэшированные значения), ошибкой считается тип `e` или значение из набора `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#N/A`, `#NUM!`, `#NULL!`; PDF — `pdfinfo`, `pdftotext -layout -enc UTF-8`.

## 5. Карта происхождения разделов договора

Договор `01-dogovor-subpodryada.docx` пишет `build_contract()` (`products-storage/build_paid_03.py:1476`) из списка `CONTRACT` (`products-storage/build_paid_03.py:148`). Порядок блоков тела смоделирован по коду `build_contract` и сверен с извлечением: блоков 210, модель совпала (первый абзац каждого пункта и каждый заголовок раздела сравнены с текстом генератора). Пересборка генератором во временный каталог (`build(out, pdf=False)`): `01-dogovor-subpodryada.docx` — байты совпали; `10-protokol-raznoglasiy.docx` — байты совпали; `00-INSTRUKCIYA.docx` — байты совпали; `00-START-HERE.txt` — байты совпали.

Референс владельца, по которому написан текст (отчёт реализации §0, §2.1), в репозиториях отсутствует: столбец «Источник» называет файлы, которые в дереве есть, и строку отчёта реализации, где записано, что взято из референса и что обобщено полями.

| Фрагмент / раздел | Выдаваемый файл и место | Источник в репозитории | Генератор / ручной файл | Связанная страница или инструкция |
|---|---|---|---|---|
| Файл `01-dogovor-subpodryada.docx` целиком | `01-dogovor-subpodryada.docx` (весь файл) | `products-storage/build_paid_03.py` | генератор | страница `products/p7-dogovor-podryada.html`: L207, L230; START-HERE: L0025, L0037; `00-INSTRUKCIYA.docx`: B0003 P, B0007 P, B0013 P, B0014 P, B0019 T1 R5 C1 |
| Файл `10-protokol-raznoglasiy.docx` целиком | `10-protokol-raznoglasiy.docx` (весь файл) | `products-storage/build_paid_03.py` | генератор | страница `products/p7-dogovor-podryada.html`: L160, L216, L228, L229; START-HERE: L0026, L0046; `00-INSTRUKCIYA.docx`: B0003 P, B0007 P, B0008 P, B0014 P, B0019 T1 R14 C1, B0019 T1 R14 C2 |
| Служебные строки, заголовок, место и дата, преамбула | `01` B0001–B0007 (B0004 — таблица T1 место/дата) | `products-storage/build_paid_03.py:1476` (`service_lines`, `place_and_date` `:1438`, `parties_preamble` `:1426`); отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:33` | генератор | инструкция «Как заполнять» (служебные строки, имена полей сторон): `tools/candidates/evidence/MB001_R026_P7_PACKET/zip/00-INSTRUKCIYA.docx.txt` |
| 1. ПРЕДМЕТ ДОГОВОРА | `01` B0008–B0014, пункты 1.1–1.4 (4 блоков `CONTRACT`); протокол `10`: позиций нет | `products-storage/build_paid_03.py:149-181`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:34` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0019 T1 R6 C3 p1 (п. 1.1); 00-INSTRUKCIYA.pdf: с.2 L9 (п. 1.1) |
| 2. СТОИМОСТЬ РАБОТ И ПОРЯДОК РАСЧЕТОВ | `01` B0015–B0056, пункты 2.1–2.14 (14 блоков `CONTRACT`); протокол `10`: 8 поз. (новая редакция 5, редакция: пункт без последнего абзаца 1, Исключить 2), строки R2, R3, R4, R5, R6, R7, R8, R9 | `products-storage/build_paid_03.py:182-282`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:35` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0013 P (разд. 2), B0015 P (п. 2.7), B0019 T1 R9 C3 p1 (п. 2.7); 00-INSTRUKCIYA.pdf: с.1 L31 (разд. 2), с.1 L39 (п. 2.7) |
| 3. СРОКИ ВЫПОЛНЕНИЯ РАБОТ | `01` B0057–B0063, пункты 3.1–3.4 (4 блоков `CONTRACT`); протокол `10`: 4 поз. (новая редакция 3, новый пункт 1), строки R10, R11, R12, R13 | `products-storage/build_paid_03.py:283-306`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:36` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0013 P (разд. 3), B0017 P (п. 3.3), B0019 T1 R7 C3 p1 (п. 3.1), B0019 T1 R11 C3 p1 (п. 3.3); 00-INSTRUKCIYA.pdf: с.1 L31 (разд. 3), с.1 L44 (п. 3.3), с.2 L11 (п. 3.1), с.2 L19 (п. 3.3) |
| 4. ОБЯЗАННОСТИ ПОДРЯДЧИКА | `01` B0064–B0083, пункты 4.1–4.9 (16 блоков `CONTRACT`); протокол `10`: 9 поз. (Исключить 4, новая редакция 3, новый пункт 2), строки R14, R15, R16, R17, R18, R19, R20, R21, R22 | `products-storage/build_paid_03.py:307-415`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:37` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0014 P (п. 4.9), B0015 P (п. 4.8), B0024 P (п. 4.6), B0024 P (п. 4.7); 00-INSTRUKCIYA.pdf: с.1 L34 (п. 4.9), с.1 L38 (п. 4.8), с.2 L38 (п. 4.6), с.2 L38 (п. 4.7) |
| 5. ОБЯЗАННОСТИ ЗАКАЗЧИКА | `01` B0084–B0092, пункты 5.0–5.6 (8 блоков `CONTRACT`); протокол `10`: 1 поз. (Исключить 1), строки R23 | `products-storage/build_paid_03.py:416-452`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:38` | генератор (`CONTRACT`) | явных ссылок на номер раздела или пункта нет |
| 6. СДАЧА И ПРИЕМКА ВЫПОЛНЕННЫХ РАБОТ | `01` B0093–B0106, пункты 6.1–6.10 (10 блоков `CONTRACT`); протокол `10`: 6 поз. (новая редакция 2, Исключить 4), строки R24, R25, R26, R27, R28, R29 | `products-storage/build_paid_03.py:453-573`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:39` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0013 P (разд. 6), B0014 P (п. 6.7); 00-INSTRUKCIYA.pdf: с.1 L31 (разд. 6), с.1 L34 (п. 6.7) |
| 7. БЕЗОПАСНОСТЬ РАБОТ И ОХРАНА ТРУДА | `01` B0107–B0132, пункты 7.1–7.13 (13 блоков `CONTRACT`); протокол `10`: 2 поз. (новая редакция 1, Исключить 1), строки R30, R31 | `products-storage/build_paid_03.py:574-707`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:40` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0013 P (разд. 7), B0015 P (п. 7.1), B0015 P (п. 7.13), B0024 P (п. 7.2), B0024 P (п. 7.3); 00-INSTRUKCIYA.pdf: с.1 L31 (разд. 7), с.1 L38 (п. 7.1), с.1 L38 (п. 7.13), с.2 L38 (п. 7.2) |
| 8. ГАРАНТИЙНЫЕ ОБЯЗАТЕЛЬСТВА ПОДРЯДЧИКА | `01` B0133–B0146, пункты 8.1–8.8 (8 блоков `CONTRACT`); таблица возврата гарантийного удержания B0141; протокол `10`: 4 поз. (новая редакция 1, Исключить 3), строки R32, R33, R34, R35 | `products-storage/build_paid_03.py:708-763`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:41` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0013 P (разд. 8), B0014 P (разд. 8); 00-INSTRUKCIYA.pdf: с.1 L31 (разд. 8), с.1 L35 (разд. 8) |
| 9. ОТВЕТСТВЕННОСТЬ СТОРОН | `01` B0147–B0171, пункты 9.1–9.9 (22 блоков `CONTRACT`); протокол `10`: 18 поз. (Исключить 17, новая редакция 1), строки R36, R37, R38, R39, R40, R41, R42, R43, R44, R45, R46, R47, R48, R49, R50, R51, R52, R53 | `products-storage/build_paid_03.py:764-917`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:42` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0013 P (разд. 9); 00-INSTRUKCIYA.pdf: с.1 L31 (разд. 9) |
| 10. ПОРЯДОК РАЗРЕШЕНИЯ СПОРОВ | `01` B0172–B0174, пункты 10.1–10.2 (2 блоков `CONTRACT`); протокол `10`: 1 поз. (новая редакция 1), строки R54 | `products-storage/build_paid_03.py:918-929`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:43` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0013 P (разд. 10); 00-INSTRUKCIYA.pdf: с.1 L31 (разд. 10) |
| 11. ПОРЯДОК ИЗМЕНЕНИЯ И ДОПОЛНЕНИЯ ДОГОВОРА | `01` B0175–B0193, пункты 11.1–11.7 (13 блоков `CONTRACT`); протокол `10`: 3 поз. (новая редакция 2, Исключить 1), строки R55, R56, R57 | `products-storage/build_paid_03.py:930-1032`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:44` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0013 P (разд. 11), B0017 P (п. 11.1), B0019 T1 R10 C3 p1 (п. 11.1), B0019 T1 R11 C3 p1 (п. 11.1); 00-INSTRUKCIYA.pdf: с.1 L31 (разд. 11), с.1 L44 (п. 11.1), с.2 L17 (п. 11.1), с.2 L19 (п. 11.1) |
| 12. КОНТРОЛЬ И НАДЗОР ЗА РЕАЛИЗАЦИЕЙ ДОГОВОРА | `01` B0194–B0197, пункты 12.1–12.3 (3 блоков `CONTRACT`); протокол `10`: позиций нет | `products-storage/build_paid_03.py:1033-1049`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:45` | генератор (`CONTRACT`) | явных ссылок на номер раздела или пункта нет |
| 13. ПРОЧИЕ УСЛОВИЯ | `01` B0198–B0208, пункты 13.1–13.7 (7 блоков `CONTRACT`); протокол `10`: позиций нет | `products-storage/build_paid_03.py:1050-1087`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:46` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0015 P (п. 13.7); 00-INSTRUKCIYA.pdf: с.1 L40 (п. 13.7) |
| 14. АДРЕСА, БАНКОВСКИЕ РЕКВИЗИТЫ И ПОДПИСИ СТОРОН | `01` B0209–B0210, нумерованных пунктов нет; таблица реквизитов и подписей B0210; протокол `10`: позиций нет | `products-storage/build_paid_03.py:1088-1090`; отчёт реализации `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md:47` | генератор (`CONTRACT`) | 00-INSTRUKCIYA.docx: B0013 P (разд. 14); 00-INSTRUKCIYA.pdf: с.1 L31 (разд. 14) |

Полная карта по каждому пункту — `tools/candidates/evidence/MB001_R026_P7_PACKET/maps/contract_clauses.md`; по каждой позиции протокола — `tools/candidates/evidence/MB001_R026_P7_PACKET/maps/protocol_rows.md`.

Протокол разногласий `10-protokol-raznoglasiy.docx`: `build_protocol()` (`products-storage/build_paid_03.py:1515`), таблица `B0009 T2`, позиций 56: новая редакция — 19, редакция: пункт без последнего абзаца — 1, Исключить — 33, новый пункт — 3. Левая колонка всех позиций совпала с текстом пункта из генератора: да; правая колонка совпала с `PROTOCOL`: да.

Остальные выдаваемые файлы и их источник:

| Файл | Генератор / ручной файл | Первое появление в git | Последнее изменение | Упоминания имени в *.py/*.php/*.sh |
|---|---|---|---|---|
| `00-INSTRUKCIYA.docx` | генератор `products-storage/build_paid_03.py` | be4c235 2026-08-27 | fe263df 2026-09-29 | `products-storage/build_paid_03.py`, `products-storage/update_manifests.py`, `tools/check_editions.py`, `tools/test_p7_contract_kit.py` |
| `00-INSTRUKCIYA.pdf` | генератор `products-storage/build_paid_03.py` (PDF печатает LibreOffice из 00-INSTRUKCIYA.docx, `build_pdf`) | be4c235 2026-08-27 | fe263df 2026-09-29 | `products-storage/build_paid_03.py`, `products-storage/update_manifests.py`, `tools/check_editions.py`, `tools/test_p7_contract_kit.py` |
| `00-START-HERE.txt` | генератор `products-storage/build_paid_03.py` | 059a4c8 2026-08-27 | fe263df 2026-09-29 | `products-storage/build_paid_03.py`, `tools/build_s1_candidate.py`, `tools/s1_route.py`, `tools/test_delivery_artifacts.py`, `tools/test_p7_contract_kit.py`, `tools/test_products_dir.php`, `tools/test_s1_candidate.py`, `tools/verify_delivery_zips.php` |
| `01-dogovor-subpodryada.docx` | генератор `products-storage/build_paid_03.py` | be4c235 2026-08-27 | fe263df 2026-09-29 | `products-storage/build_paid_03.py`, `products-storage/create_analysis.py`, `tools/test_p7_contract_kit.py` |
| `02-perechen-rabot.xlsx` | генератор в репозитории не найден: файл лежит готовым | be4c235 2026-08-27 | be4c235 2026-08-27 | `products-storage/build_paid_03.py`, `products-storage/create_analysis.py` |
| `03-kalendarnyy-plan.xlsx` | генератор в репозитории не найден: файл лежит готовым | be4c235 2026-08-27 | be4c235 2026-08-27 | `products-storage/build_paid_03.py`, `products-storage/create_analysis.py` |
| `04-poryadok-priemki.docx` | генератор в репозитории не найден: файл лежит готовым | be4c235 2026-08-27 | be4c235 2026-08-27 | `products-storage/build_paid_03.py`, `products-storage/create_analysis.py` |
| `05-grafik-platezhey.xlsx` | генератор в репозитории не найден: файл лежит готовым | be4c235 2026-08-27 | be4c235 2026-08-27 | `products-storage/build_paid_03.py`, `products-storage/create_analysis.py` |
| `06-dopsoglashenie-obem.docx` | генератор в репозитории не найден: файл лежит готовым | be4c235 2026-08-27 | be4c235 2026-08-27 | `products-storage/build_paid_03.py`, `products-storage/create_analysis.py` |
| `07-dopsoglashenie-sroki.docx` | генератор в репозитории не найден: файл лежит готовым | be4c235 2026-08-27 | be4c235 2026-08-27 | `products-storage/build_paid_03.py`, `products-storage/create_analysis.py` |
| `08-krasnye-flagi.pdf` | генератор в репозитории не найден: файл лежит готовым | be4c235 2026-08-27 | be4c235 2026-08-27 | `products-storage/build_paid_03.py`, `products-storage/create_analysis.py` |
| `09-checklist-dogovora.pdf` | генератор в репозитории не найден: файл лежит готовым | be4c235 2026-08-27 | be4c235 2026-08-27 | `products-storage/build_paid_03.py`, `products-storage/create_analysis.py` |
| `10-protokol-raznoglasiy.docx` | генератор `products-storage/build_paid_03.py` | be4c235 2026-08-27 | fe263df 2026-09-29 | `products-storage/build_paid_03.py`, `products-storage/create_analysis.py`, `tools/test_p7_contract_kit.py` |

## 6. Тексты страницы, START-HERE и MANIFEST

Страница `products/p7-dogovor-podryada.html` (SHA-256 `5dec362fb3387e2bd5650e7bb07531577c5f612cf7057771541df270bf491fb4`):
- видимый текст по блокам с номерами строк исходника — `tools/candidates/evidence/MB001_R026_P7_PACKET/site/p7-dogovor-podryada.visible.txt` (105 блоков, из них с пометкой [скрыт] 6);
- FAQ: видимый блок `section.faq` и `FAQPage` из JSON-LD — `tools/candidates/evidence/MB001_R026_P7_PACKET/site/p7-dogovor-podryada.faq.txt` (вопросов в JSON-LD: 6);
- JSON-LD целиком — `tools/candidates/evidence/MB001_R026_P7_PACKET/site/p7-dogovor-podryada.jsonld.json` (1 блок(а)).
- Блок «Как это выглядит внутри» генерируется `tools/build_preview.py` из файлов комплекта (описание PR #315, коммит `38a47a5`).

START-HERE (`products-storage/03-dogovor-podryada/00-START-HERE.txt`, SHA-256 `5d09af3ec368dc39f81f36a451d264255301a98dfc55966abb6be7c49de544df`), полный текст:

```text
С ЧЕГО НАЧАТЬ
============================================================================

Комплект «Договор субподряда: образец, красные флаги, протокол разногласий»
2 490 ₽ · файлов в архиве: 13


1. ДЛЯ КАКОЙ ЭТО СИТУАЦИИ

   Договор субподряда ещё не подписан. Условия оплаты, приёмки и удержаний
   правятся только сейчас; после подписи каждая строка стоит денег.


2. ОТКРОЙТЕ ПЕРВЫМ

   00-INSTRUKCIYA.pdf

   Она разводит два случая и для каждого называет порядок файлов:
   «Вам прислали договор на подпись» и «Договор предлагаете вы».


3. КОГДА НУЖНЫ ОСТАЛЬНЫЕ

   Чек-лист (09) и красные флаги (08) — по присланному договору. Шаблон
   договора (01) — эталон для сравнения по разделам и основа, если договор
   предлагаете вы. Протокол разногласий (10) собран к пунктам шаблона: в
   левой колонке редакция заказчика, в правой — подрядчика. Перечень работ,
   календарный план и график платежей (02, 03, 05) — приложения, которые
   подписывают вместе с договором. Допсоглашения (06, 07) — по ходу работ.


4. ЧТО В АРХИВЕ

   00-INSTRUKCIYA.docx
   00-INSTRUKCIYA.pdf
   00-START-HERE.txt   ← вы читаете его сейчас
   01-dogovor-subpodryada.docx
   02-perechen-rabot.xlsx
   03-kalendarnyy-plan.xlsx
   04-poryadok-priemki.docx
   05-grafik-platezhey.xlsx
   06-dopsoglashenie-obem.docx
   07-dopsoglashenie-sroki.docx
   08-krasnye-flagi.pdf
   09-checklist-dogovora.pdf
   10-protokol-raznoglasiy.docx

   Файлы пронумерованы в том порядке, в котором их обычно применяют. Word и
   Excel редактируются, PDF — инструкция и чек-листы.


5. ЗАДАЧА ВЫПОЛНЕНА, КОГДА

   Договор подписан в редакции протокола разногласий — либо от сделки
   отказались осознанно и с записанной причиной.


6. ЧЕГО ЭТОТ КОМПЛЕКТ НЕ ДЕЛАЕТ

   Он не проверяет смету, не считает аванс и не разбирает расчёт метрами —
   это три отдельные проверки. И он бесполезен после подписи: тогда условия
   меняются только соглашением сторон.

   И он не заменяет проверку профильным специалистом: шаблон адаптируется
   под ваш договор и объект, а решения по спорным суммам принимаются после
   такой проверки.


7. ЕСЛИ СИТУАЦИЯ ИЗМЕНИЛАСЬ

   До подписи проверяют не только договор: аванс, расчёт метрами и смета —
   три отдельные проверки со своими документами, и какая из них ваша,
   зависит от условий сделки. Подставлять одну из трёх наугад мы не будем.


8. ДРУГАЯ СИТУАЦИЯ НА ОБЪЕКТЕ

   Разбор по семи вопросам называет ситуацию и материалы под неё:
   https://marzhavbetone.ru/diagnostika.html?utm_source=product&utm_medium=post-purchase&utm_campaign=dogovor_do_podpisi&utm_content=p7-diagnostika


----------------------------------------------------------------------------
Вопросы по составу комплекта: marzhavbetone@yandex.ru
«Маржа в бетоне»
```

MANIFEST (`products-storage/03-dogovor-podryada/MANIFEST.md`, SHA-256 `61fca869cc1a12b8fdee25d6289c9a2a331f0f3c962dbe166a1b0abe1b2c0e93`, в ZIP не выдаётся), полный текст:

```text
# Договор подряда

Версия: 21.07.2026

## Состав
- `00-START-HERE.txt` — Текст
- `00-INSTRUKCIYA.docx` — Word
- `00-INSTRUKCIYA.pdf` — PDF
- `01-dogovor-subpodryada.docx` — Word
- `04-poryadok-priemki.docx` — Word
- `06-dopsoglashenie-obem.docx` — Word
- `07-dopsoglashenie-sroki.docx` — Word
- `10-protokol-raznoglasiy.docx` — Word
- `02-perechen-rabot.xlsx` — Excel
- `03-kalendarnyy-plan.xlsx` — Excel
- `05-grafik-platezhey.xlsx` — Excel
- `08-krasnye-flagi.pdf` — PDF
- `09-checklist-dogovora.pdf` — PDF

## Ограничение
Материалы являются редактируемыми шаблонами и требуют адаптации под договор, проект, систему документооборота и фактические обстоятельства объекта.
```

Второй служебный файл каталога — `00-PISMO-POSLE-POKUPKI.txt` (в ZIP не выдаётся): `tools/candidates/evidence/MB001_R026_P7_PACKET/kit-service/00-PISMO-POSLE-POKUPKI.txt.txt`; копия MANIFEST с номерами строк — `tools/candidates/evidence/MB001_R026_P7_PACKET/kit-service/MANIFEST.md.txt`.

## 7. Найденные исходники и отчёты

| Что | Путь | Коммит / ветка | SHA-256 | Копия в пакете |
|---|---|---|---|---|
| Генератор P7 | `products-storage/build_paid_03.py` | #315, `38a47a5` | `82e0d6b9398764204fd3ed134c1d5f3976c4d9cf34769ad678aa9db5187dd43d` | нет (в дереве) |
| Сборка выдачи | `products-config.php` (`mvb_products`, `mvb_build_product_zip`) | `38a47a5` | `7f7cca1e7344a3ad69041049b926e2a9766de1ba93d9de3de70641875261f7fb` | нет (в дереве) |
| Тест комплекта | `tools/test_p7_contract_kit.py` | #315 | `5a389799cd5d8b701695baee35d8d1b8e62e6bcfbb200503f0730a5cce5f687e` | нет (в дереве) |
| Страница P7 | `products/p7-dogovor-podryada.html` | #315 | `5dec362fb3387e2bd5650e7bb07531577c5f612cf7057771541df270bf491fb4` | извлечения в `site/` |
| Отчёт реализации #315 | `tools/candidates/MB001_R2_P7_IMPLEMENTATION_REPORT.md` | `claude/gifted-wright-otl19h-p7` | `136678349419622510eb5b3cd138bf485ce3cf1ed00297709ed82e89481ec80a` | `tools/candidates/evidence/MB001_R026_P7_PACKET/source-reports/MB001_R2_P7_IMPLEMENTATION_REPORT.md` (байт в байт) |
| Gap-отчёт (спецификация пробелов, #307) | `tools/candidates/MB001_R2_P7_GAP_SPEC.md` | `claude/gifted-wright-otl19h` `a1633c2bc0c4261a7d9653d1c3876f40dea0ed18` | `ba1c3b5e154cbf912cd97f1b0670b1f3bc0274219ccb41e8d3b6f3f8fceef1ed` | `tools/candidates/evidence/MB001_R026_P7_PACKET/source-reports/MB001_R2_P7_GAP_SPEC.md` (байт в байт из `git show`) |
| Исходный договор / референс владельца | не найден | — | — | — |

Поиск референса: `git ls-files` сайта по шаблону имён «referens|reference|skan|scan|original|obrazec» рядом с «dogovor|protokol» — совпадений: 0; `git ls-files` ai-business-os по шаблону «dogovor-pod|subpodr|protokol-razn|contract_ref|referens» — совпадений: 7 (projects/marzha_v_betone/product/build/12-protokol-raznoglasiy.js, projects/marzha_v_betone/production/covers/articles/dogovor-subpodryada-obrazec.png, projects/marzha_v_betone/production/covers/articles/krasnye-flagi-dogovora-subpodryada.png, projects/marzha_v_betone/production/covers/articles/protokol-raznoglasiy-k-dogovoru.png, projects/marzha_v_betone/production/covers/web/dogovor-subpodryada-obrazec.jpg, projects/marzha_v_betone/production/covers/web/krasnye-flagi-dogovora-subpodryada.jpg, projects/marzha_v_betone/production/covers/web/protokol-raznoglasiy-k-dogovoru.jpg).

Копии файлов P7 вне каталога продукта: в `products-storage/04-polnyy-komplekt-pto/01-30-bazovye-pakety/03-dogovor-podryada/` найдено 14 файлов с именами из P7; SHA-256 совпадает с текущим мастером у 8 (02-perechen-rabot.xlsx, 03-kalendarnyy-plan.xlsx, 04-poryadok-priemki.docx, 05-grafik-platezhey.xlsx, 06-dopsoglashenie-obem.docx, 07-dopsoglashenie-sroki.docx, 08-krasnye-flagi.pdf, 09-checklist-dogovora.pdf), отличается у 6 (00-INSTRUKCIYA.docx, 00-INSTRUKCIYA.pdf, 00-PISMO-POSLE-POKUPKI.txt, 00-START-HERE.txt, 01-dogovor-subpodryada.docx, 10-protokol-raznoglasiy.docx). Этот каталог не адресуется sku `p7` и в ZIP p7 не входит.

## 8. Ограничения пакета

- **Референса владельца нет в репозиториях.** Отчёт реализации #315 называет его сканом на 23 страницы, переданным 29.09.2026, и прямо говорит, что файл не кладётся в репозиторий. Поэтому дословное происхождение каждого пункта от референса этим пакетом не проверяется: карта доходит до генератора и до строки отчёта реализации, а не до страницы референса.
- Файлы 02–09 генератора в репозитории не имеют: их текст извлечён, происхождение — только история git.
- SHA-256 архива зависит от времени правки файлов в рабочей копии и от порядка обхода каталога (`ZipArchive` пишет mtime, `RecursiveDirectoryIterator` не сортирует). В другой рабочей копии хеш архива будет иным; стабильны имена и SHA-256 записей.
- Вёрстка не проверялась: извлечён текст, а не вид страниц. Скрытость блоков страницы определена по атрибутам `hidden` / `aria-hidden`, CSS не вычислялся. Страница не открывалась в браузере.
- PDF извлечён `pdftotext`: переносы и колонки восстановлены по раскладке, а не по структуре документа.
- В XLSX формул нет; значения, которые покупатель введёт сам, пакет не моделирует.
- Связь «раздел договора → инструкция / страница / другие файлы» установлена только по явным ссылкам на номер пункта или раздела. Тематические совпадения без номера не сопоставлялись.
- Нормативные акты, на которые ссылаются тексты, в пакет не входят: пакет не сверяет текст с нормой, это работа перечита.

## 9. Команды фактической проверки и их результаты

```bash
# голова #315 и ветка пакета
git fetch origin claude/gifted-wright-otl19h-p7 && git rev-parse FETCH_HEAD    # 38a47a505b48a46d6c8f663588b255af20aa1fc9
git merge-base --is-ancestor 38a47a5 HEAD && echo ok     # ok
# реальная выдача
php tools/candidates/evidence/MB001_R026_P7_PACKET/_tools/build_p7.php "$PWD" "$(mktemp -d)"
unzip -Z1 <архив> | sort                                   # 13 имён, см. раздел 3
# пересборка пакета и проверка готовности
python3 tools/candidates/evidence/MB001_R026_P7_PACKET/_tools/build_packet.py --pr-head-sha 38a47a505b48a46d6c8f663588b255af20aa1fc9 --pr-head-ref claude/gifted-wright-otl19h-p7 --pr-base-sha b89f081fe94249231896bcf40b8a188824ac9301
python3 tools/candidates/evidence/MB001_R026_P7_PACKET/_tools/verify_packet.py --pr-head-sha 38a47a505b48a46d6c8f663588b255af20aa1fc9
```

Результаты сборки (этот прогон):

- `mvb_build_product_zip('p7')` дважды: 13 записей; архив `c7912334663f5f3f…` / `c7912334663f5f3f…`; записи совпали.
- Состав ZIP = каталог минус `$service`: да; = START-HERE §4: да; = `KIT_FILES`: да.
- Пересборка генератором: `01-dogovor-subpodryada.docx` =; `10-protokol-raznoglasiy.docx` =; `00-INSTRUKCIYA.docx` =; `00-START-HERE.txt` =.
- Модель блоков договора сверена с извлечением: да; протокол: левая колонка 56/56, правая 56/56.

Результаты проверки готовности (DONE) — вывод `verify_packet.py` на момент коммита:

<!-- VERIFY:BEGIN -->
- PASS — 1. Список и SHA-256 = заново собранный ZIP p7
  - записей собрано 13, в отчёте 13; SHA-256 и размеры записей совпали; SHA-256 архива c7912334663f5f3f… = отчёт
- PASS — 2. Каждый файл архива есть в индексе
  - записей в разделе 3: 13; строк индекса: 13; у всех есть извлечение с тем же SHA-256: да
- PASS — 3. Ссылки отчёта и карт существуют в текущем дереве
  - ссылок на пути проверено: 388; все существуют в текущем дереве: да; вне дерева, но в названном рядом коммите: tools/candidates/MB001_R2_P7_GAP_SPEC.md
- PASS — 4. Нет правовых вердиктов и рекомендаций
  - слов правовой оценки и рекомендаций в авторском тексте: нет (проверено: tools/candidates/MB001_R026_P7_REVIEW_PACKET.md, tools/candidates/evidence/MB001_R026_P7_PACKET/maps/contract_clauses.md, tools/candidates/evidence/MB001_R026_P7_PACKET/maps/protocol_rows.md; раздел 1 и блоки ``` исключены)
- PASS — 5. Изменения — только пакет материалов
  - изменено относительно 38a47a5 (коммиты + рабочее дерево): 27 файлов; вне пакета: 0
  - файлов пакета под .gitignore (не попали бы в коммит): 0
- Итог: PASS (5/5)
<!-- VERIFY:END -->

