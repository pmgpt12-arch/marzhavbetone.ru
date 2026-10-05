# S1-02B — финансовая проверка сохранённого кандидата

Issue #327, parent #291. 04.10.2026. **STOP / REVIEW_REQUIRED**, не SALE_READY.

На принятой базе 02А e7404eff02a53717613f2d2cbf763ad072d5aace разделены общий долг, спорная и бесспорная части; добавлен печатаемый акт сверки. В книгу 395 передаются только бесспорный долг на первый день просрочки и текущий бесспорный остаток. Правомерность начисления на спорное не определяется: L24 остаётся отдельным нормативным gate.

## Preflight и происхождение

Исходный worktree issue-327 не изменялся. Изолированный codex/mb001-327-recovery-20261004 создан от e7404ef; сохранённые незавершённые source/evidence перенесены в checkpoint f4edf5bb9a2736b48fe0aa9a92f103ec3e7b7585d. Exact requested/actual model по init: anthropic/claude-opus-5.5, OpenRouter через Ori, openrouter_api, fallback не было. Один запуск до 1200 секунд, harness cap USD10. Он остановлен по лимиту времени после реализации и генерации кандидата; финальный result с tokens/cost отсутствует, **UNKNOWN**, отдельно не измерялся. Затем координатор выполнил обязательные механические проверки Python/CLI без нового inference. Таймаут не скрыт и не интерпретируется как MODEL_CAPABILITY или готовность продукта.

| Источник | Path | Commit SHA | File SHA256 |
|---|---|---|---|
| contract | `tools/candidates/MB001_S1_ACCEPTANCE_CONTRACT.md` | `b8d041abca6dee536d6e4c2407314e5e6222cc89` | `0251784c4c05558c079076d5609d757309a1c6c424727c1aedd93674038eaece` |
| buyer | `tools/candidates/S1-02A-INDEPENDENT-BUYER-CHECK.md` | `73e9da5ca0eca5235453937041675d4b61e45b75` | `9c22817a8f2d1b684493f5505e53d539062ee895d4954d4548c68cf9ea65ef76` |
| financial | `tools/candidates/S1-FINANCIAL-VERIFICATION.md` | `5ffaae178c71670c6db966c630d3e316d8e8e66c` | `3adce3d4a9279328626b3f2c436924b986cdeee7343dab15ec4736c41b044fe8` |
| acceptance | `tools/candidates/S1-02A-INDEPENDENT-ACCEPTANCE.md` | `841d3402d3cd0107f393e7b62e4a92ad0de38fcf` | `ab51bea4dc6235e87ca622293cadf0b43ed0e4bc31a37e0b25c528444ffbb291` |

Дополнительные существующие проверки взяты из PR #320 a587b928d3d0593eb1ed60f54944cca3feaf2f97: calc_edges.py blob 73449cc5950ba0d8757ca5de69292401aa58bcc0, cycles.py blob 30c872ad20aa5497e03b414d8a7288f66fb889e3. В calc_edges_02B.py адаптировано только имя книги 14→08; сценарии/ожидания/независимый подневный эталон не менялись. Сравнение с T1 относится к файлу pinned worktree, не к проверке текущего production.

## Проверяемое поведение §9.2

| Требование | Фактическая проверка | Результат |
|---|---|---|
| Общий долг / спорная / бесспорная | Calc, исходные данные #286 | 779934 / 50000 / 729934 |
| Передача только бесспорной части | Calc + независимый эталон процентов + static transfer | D книги 08 ← J листа «Долг по актам», F ← M; итог процентов соответствует 729934 |
| Допработы без соглашения (спорно) | Calc, начисление1000000 и спорные200000 | 1000000 / 200000 / 800000, выход B5 |
| Спорная операция без акта / сверх общего | Calc negative cases | БЛОК; отрицательная бесспорная сумма не отдаётся |
| Акт сверки | Calc сценарий C; удержание; двойной аванс | общий500000, отдельная спорная50000; двойной аванс блокирует итог |
| Частичная оплата / несколько актов / округление | Existing full tests + independent calc_edges | 55/55 tests, 15/15 edge cases; 0 пропусков; 0 cell errors в edge cases |
| Циклы | Existing cycles.py на 04 и08 | 2867/36244 формул; 144326/15804403 связей; циклов нет |
| Сборка и состав | Existing reproducibility tests + actual PHP builder | 11 файлов, content SHA совпали с кандидатом; CRC PASS |
| Фактическая печать | Calc ru-RU, учебный акт779934/50000/729934 | 2 страницы, повтор заголовка на второй, суммы и подписи видны |
| Writer | Фактическая конверсия изменённых 01/03 | 6/10 страниц, текст извлечён; полного visual review этих документов нет |
| Repository public gate | Existing run_checks.py --class public | 39/39 PASS, 0 пропусков |

Полный test suite выполнен после содержательной правки. После него исправлена только обрезавшаяся подпись B8 акта: «Сверка по состоянию на» → «Дата сверки». Пересобрана книга04; XML сравнение подтвердило ровно это изменение в sheet3.xml, без изменения формул/данных/форматов/других листов. Затем акт заново распечатан ru-RU, ZIP пересобран и public gate выполнен на текущем кандидате. Повтор 55 числовых сценариев при неизменных формулах не делался.

Проверки используют временные книги/отдельные профили Calc/Writer. Статический cycles.py возвращает exit0 даже при найденном цикле, поэтому дополнительно прочитан текст: оба «цикл: нет». Первое сравнение печатных чисел не учитывало en-US разделитель тысяч; исправлен harness и проверен ru-RU. Первый CI снимок без .git дал технический FAIL test_published_data; добавлен изолированный Git index с read-only object alternate, полный повтор 39/39. Ни assertion, ни продуктовый gate не ослаблялись.

## Артефакты и scope

Evidence в tools/candidates/evidence/S1_02B/: full-tests-55.out.txt, calc-edges.out.txt, cycles.out.txt, run-checks-git-aware.out.txt, ci-correction-proof.json, print-zip-proof.json, caption-proof.json; учебный акт PDF, два Writer PDF; candidate-02B.zip.

ZIP SHA256 `2def6ee0f1637f598c3a57242f011abe66f019cae79439a91bce791f5439b982`; content hashes в print-zip-proof.json. Generator SHA256 `3593190a5b91cac043ae354e81453e87341338a3e6160a3a7ef1adf3b20b3fd2`.

Только tools/build_s1_candidate.py, tools/s1_route.py, tools/test_s1_candidate.py и candidate/evidence/report. Live products-storage, config, сайт, SKU, цены, оплата, CI definitions, deploy не менялись. Ветка stacked на claude/issue-326. Файлы 05/06/07/09/10 выдачи сохранены. Неблокирующая печатная правка затронула только новый акт02B.

## Остаток и handoff

Нужны независимые С-1…С-5, в частности С-2 и С-5 §10.3, на **новом полном SHA**, исполнителем, не писавшим02B. Публикация этого отчёта и Draft PR не принимают продукт. Независимый результат должен заполнить предусмотренный §9.2 S1-02B-FINANCIAL-BOUNDARY.md. L24 и L22/L23 — NOT VERIFIED, не закрываются вычислениями; Excel NOT VERIFIED. Продажи/релиз P1 не разрешены этими результатами. Целевая29 900 ₽ применяется только после всех gates.
