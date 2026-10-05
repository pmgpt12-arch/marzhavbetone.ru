# P5: принятые формулы и нативное оформление владельца в генераторе

05.10.2026. Scope: только две Excel-книги P5, их текущий генератор и проверки воспроизводимости. API/LLM cost: 0. Статус: VERIFIED_AUTHOR_CANDIDATE; отдельная приёмка нового кода до working merge. Не SALE_READY.

## Входы и заранее заданный контракт

Паспорт до реализации: `MB001_P5_OWNER_NATIVE_PASSPORT.json`, execution_pattern=iterative, primary_result=сохранение принятых бизнес-ячеек и точных нативных owner bytes в выпуске генератора, feedback_loop_required=true, checkpoint_policy=verified_only.

Принятый source: correction PR369 `7c202189d27f3ec05a0b8ae55364ccc0a06002f1`, working merge `57e694f7b112c7649112f0aaa469f30ccbc1fb5f`. Independent PR375 `cb48eb65719bf85c5cf3420db5a0946efd44bea9` принят в узком scope процентного ввода (переданный координатором checkpoint). Текущий remote base `codex/mb001-independent-354-20261004` фактически подтверждён равным 57e694f.

Owner snapshot: `87dc3b8e9c2b30fdb3fe18cb312b2ef5c1b35ce2:tools/owner-excel/2026-10-05-1310/`. Владелец подтвердил проверку пяти косметических файлов в настоящем Excel; повторное подтверждение оформления не требуется. Explicit read-only mapping `/home/denis/.local/state/claude-dispatcher/recovery-20261004/owner-format-transfer-map-20261005-1412/receipt.json` содержит semantic differences=0 и совпавшие листы/merge sets для обеих P5 книг. Имена и пути взяты из этой карты.

| Книга | Принятый source SHA256 | Owner SHA256 |
|---|---|---|
| 04-raschet-ubytkov.xlsx | 367f24227db11c2a6043beda6e7b22522904b53d3646ddbc32588c7872dff85a | 20165a12e04cf37dee98ac8d528cb78026d5a342e24231f69a09bd70c6bedc31 |
| 05-reestr-uderzhaniy.xlsx | ba9bbf6a91eeedd1d50ef97da7edd96279eee4cba2f6b9240e7449b8b0321a5d | db0d99f745e460b29654c3079483103e1bcc39d65ad9e8c36d002288ed5df9ae |

Каноническая инструкция `/home/denis/projects/ai-business-os/docs/Task_Setting_Protocol.md` прочитана; file SHA256 `337fe8864579a95dd4af53e44ad036016145a4be82aac5560e535a09fa56e686`, фактический локальный AIOS HEAD `4f383f5c9b6a1808d7b9e053fc53d6fd94ba5361` отличается от более раннего checkpoint 614cf59. Execution pattern задан до реализации; позднее получение точного пути инструкции не заявляется ретроспективным preflight.

## Минимальное исправление

В `tools/templates/p5-owner-excel/` сохранены точные owner bytes под каноническими именами. Покупательские 04/05 в изолированной ветке заменены этими же байтами. Исходные owner snapshots и принятые source ветки не менялись.

В существующий `build_paid_07.py` добавлен локальный P5 gate. Генератор строит свои актуальные ячейки в памяти. Gate проверяет pinned SHA шаблона, имена листов, все непустые значения и развёрнутые shared formulas, объединения, отсутствие validation и равенство именованных диапазонов. Пустая строка и пустая ячейка сравниваются как эквивалентные. При расхождении останавливается до изменения существующего выходного файла. После PASS точные нативные bytes записываются через временный файл с atomic replace.

Обе нативные P5 книги не содержат normal/x14 dataValidation. Новое правило validation в генераторе или в нативном OOXML явно блокируется, чтобы оно не исчезло молча. Косметические dimensions/styles/печать остаются из утверждённых owner bytes. Даты и формулы не переписываются.

Для 05 существующий `create_excel` получил `defer_save`: промежуточная модель возвращается в памяти. Две P5 книги не проходят через openpyxl.save даже промежуточно. Поведение остальных вызовов create_excel сохраняется. P1/S1 builder/helper не менялись; новый framework не создавался.

## Реальное feedback и устранение класса

Первый author run не объявлен PASS:

1. Positive generator fixture не создала обязательный каталог P5 во временной папке: FileNotFoundError до проверки. Класс test-fixture dependency, не продукт/модель. В fixture добавлено mkdir; builder не расширялся.
2. Excel сохраняет литеральные точки формата как `dd\\.mm\\.yyyy`; прежний тест требовал только буквальное DD.MM.YYYY. Реальный показ и печать полной даты в Calc уже проходили. Класс test-format representation false negative. Проверка принимает ровно два эквивалента; отрицательные DD.MM.YY, General и MM/DD/YYYY отвергаются. Нативный файл не изменён ради теста.

Правило: сравнивать смысл допустимой нативной записи формата с узким списком эквивалентов и сохранять отдельную фактическую проверку показа/печати. Gate/test закреплены в `test_p5_owner_native.py` и текущем Calc test.

## Фактическая проверка

Команды из изолированного worktree `codex-p5-owner-native-generator-20261005`:

```bash
timeout -k 5s 120s python3 -B -m pytest -q -p no:cacheprovider tools/test_p5_owner_native.py
timeout -k 5s 180s python3 -B tools/test_p5_calc_results.py
```

- 13 native/source gate tests PASS, 0,49 с. Positive вызывает настоящий текущий generator во временной папке и подтверждает exact owner bytes обоих выходов. PDF-функция заглушена только в этой fixture; DOCX/XLSX генерируются временно, рабочие файлы не перезаписываются.
- Negative изменённая формула / validation / defined-name / merged range / corrupt template остановлены с ожидаемым ValueError; существующий output остаётся побайтно прежним, `.tmp` не появляется.
- 19 текущих Calc/PHP regression checks PASS, exit0, 19,37 с после адресного feedback. Полный вывод сохранён `evidence/P5_OWNER_NATIVE/calc.out.txt`. Сценарии наследуют принятые percent-input corrections; Calc ru-RU ввод, сохранённые результаты, дата и PDF проверены на копиях с отдельными профилями.
- Настоящий PHP ZIP: 11 файлов; 04/05 SHA точно равны owner SHA; все девять остальных файлов побайтно равны accepted 57e694f. Machine receipt `evidence/P5_OWNER_NATIVE/delivery-receipt.json`.
- `git diff --check` PASS. Source integration затрагивает только declared P5 paths.

## Остаток и следующий атомарный шаг

Нужен отдельный reviewer gate нового generator/native integration по result head: позитивная exact byte выдача, отрицательные formula/DV/name guards, отсутствие посторонних source изменений. После такого gate возможен только working merge в P5 ветку. Визуальную приёмку неизменённых owner bytes заново не запрашивать.

Правовая актуальность и все остальные buyer/legal блокеры P5 сохраняются. Этот шаг не проверяет DOCX/PDF генерацию всего комплекта, не вводит цену/SKU и не меняет SITE main, живую выдачу, оплату, сервисы или публикацию.
