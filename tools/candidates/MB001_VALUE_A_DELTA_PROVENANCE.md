# MB001-VALUE-A-DELTA: provenance цены и остаток P2/P3/P4

Issue #346, родитель #291. Поправка к паспорту
`tools/candidates/MB001_VALUE_PASSPORTS_A.md` (PR #336,
`b5e284e01ef731c81e976399a9786823cfc0ffad`) по независимой проверке PR #342
(`103b5b4ff0de9167a5642346ae999aacfa57fed1`). Аудит продуктов не повторялся.
Исторический отчёт #342 не редактировался.

**Статус: STOP / REVIEW_REQUIRED.** Автор свою поправку не принимает.
Решения D-P3, D-T2, D-PKG, D-PRICE не принимались.

## 0. Исполнитель и входы

| Поле | Значение |
|---|---|
| requested / actual model | `anthropic/claude-opus-5.5` — как объявляет среда; ответ транспорта изнутри не виден |
| provider / transport | по контракту OpenRouter / `openrouter_api`; изнутри — NOT VERIFIED |
| attempt | 1 из 1, продолжение после обрыва API-соединения (не содержательный отказ); fallback не использовался |
| duration, tokens, cost | UNKNOWN изнутри захода |
| Ветка / база | `codex/mb001-346-recovery-20261004`, `HEAD` = `b5e284e01ef731c81e976399a9786823cfc0ffad` |
| `origin/main` | `64b210e5ed4d631f74aee8f0e345fcc87ff1760e` («Merge pull request #310») |
| Входы | `context-index.json` #346: 50 файлов, сверены координатором 2026-10-04T13:34:02Z по размеру и sha256 |
| Инструменты | Read, `sha256sum`, `python3` + `zipfile`/`re` (ограниченно), `pytest`, `git diff --check`. Дополнительной модели нет |

## 1. Состояние PR (снимок метаданных 03.10.2026, `metadata/…/pr-N.json`)

| PR | Голова | Состояние | В main? |
|---|---|---|---|
| #310 (P4 R2/R3/R4) | — | merged | **да**, `64b210e` |
| #312 (P2) | `82a051e42056a8455bb885d6005965dca4adde00` | open, draft, merged=false | нет — готовый кандидат |
| #314 (P3) | `c7f1e87e5daa8e585dfcb5abf566ec82b8854baa` | open, draft, merged=false | нет — готовый кандидат |
| #316 (P3, первичная нормативная сверка) | `e414b41c3949211befec76d522da06ffa57e713c` | open, draft, merged=false | нет — исторический, замещён перечитом в #314 |
| #300 (аудит baseline) | `c5e8461415e8da08701f75d4e665ea018c42683b` | open, draft, merged=false | нет — аудит, не fix |
| #336 (паспорт) | `b5e284e01ef731c81e976399a9786823cfc0ffad` | open, draft | нет |
| #342 (проверка) | `103b5b4ff0de9167a5642346ae999aacfa57fed1` | open, draft | нет |

## 2. Исправления: correction → source → check → residual gate

| # | Исправление | Source path @ full SHA | Check | Residual gate |
|---|---|---|---|---|
| C-PRICE (R-1 #342) | Паспорт §6.1, новый §6.5: provenance 29 900 ₽; memo 27.09 (9 900 ₽) названо историческим и отменённым | Issue #291 body, «Зафиксированная ценовая политика» (`owner291.json`, sha256 `23a816855acb073ceb5fba80c752a3aa8d46f824828b1c7a6021ce6036d558a3`, `updated_at` 2026-10-02T13:09:52Z); Issue #329 body (`issue329.json`, sha256 `6056d905bed0139902ee0b855907e83413b6eda66e90cd5b0d546bfc9bca53ef`); `tools/candidates/S1-EDITION-SKU-DECISION-MEMO.md:268` @ `b5e284e01ef731c81e976399a9786823cfc0ffad` | Цитаты прочитаны; grep комментариев #291 (sha256 `1e0594ba…01bf7b`) и #329 (`fbd51357…840145`): цифр цены нет | 29 900 ₽ — цель **после** всех гейтов; в конфиг не вводится до приёмки. 24 900 ₽ систем — предложение до D-PRICE |
| C-P2 (D-00) | Новый §3.10: «дефект → main → готово в #312 → остаток → задача» | `tools/candidates/MB001_R2_P2_KIT_INSTRUCTION.md`, `MB001_R2_P2_FORMS_R3.md` @ `82a051e42056a8455bb885d6005965dca4adde00`; #300 §3.1 @ `c5e8461415e8da08701f75d4e665ea018c42683b` | `sha256sum` `00-INSTRUKCIYA.pdf` на голове #312 = `7110eeaaeccca1e8aa4a9041d1ed40abfdf191cdda4be29bcce05285b6b70182` = индекс и `FORMS_R3` §5; `07` в #312 = main `b38587d9…` | STOP-P2-R3-1..3 (`02`, `04`, `05`) — не PASS; `11`/`12`, `07`, `08`, содержание `01`–`06`, страница и бесплатные — D-01…D-07; слияние #312 до D-02 |
| C-P3 (P3-00) | Новый §4.9; строка `10` в §4.4 | `MB001_R2_P3_AOSR_FORMS_REPORT.md`, `MB001_R2_P3_T3_AOSR_WORDING_REPORT.md`, `MB001_R026_P3_AOSR_RECHECK.md` @ `c7f1e87e5daa8e585dfcb5abf566ec82b8854baa`; #316 только как историческая база @ `e414b41c3949211befec76d522da06ffa57e713c` | `sha256sum` `03` = `0897f32b805b5eae9519331d5ec9a70cdf92b6147f82ff0ccabb957331ffe685` (= перечит, `document_source_commit` `e461a5de53709fccffdfab8943e0f8a02ec05992`); смысловой хеш `6037e3331eb65d2f5bfa1759bc698ed6304152e1343c1d3122d62ff3fc014498` взят из перечита (не пересчитывался); `10` = `5f2b9f1d…320ef`; regex по `01`, `07`, `09` на голове #314 — вхождения остались | `03` CLEARED / PASS_WITH_CORRECTIONS только для этого хеша и только после слияния #314 (+ ai-business-os #532). Остаток `01`, `02`, `04`–`09`, страница — P3-03/P3-02; D-P3 за владельцем |
| C-P4 (I-00) | Новый §5.10; строка §5.5 | #300 §3.2 @ `c5e8461415e8da08701f75d4e665ea018c42683b`; main `64b210e5ed4d631f74aee8f0e345fcc87ff1760e` (#310) | P4-01…P4-04 #300 сопоставлены с §0.2/§5.5 паспорта (уже PASS в #342 по main) | `08`, `09`, `03` (обоснования), `06`, `31`–`38`, инструкция — открыты; план §5.9 без изменений. ACCEPT #342 ≠ готовность P4 |
| C-GATES | §7: источник перечня шести гейтов | Issue #329 body; Issue #291 body п. 7 | Перечень совпадает дословно с #329 | Ни один гейт не PASS; оценки §7 — по main |
| C-0.2 | §0.2, §3.8, §9: NOT VERIFIED по головам PR снят, main отделён от кандидатов | см. §1 | — | — |

## 3. R-1 из #342: адресный ответ

#342 (§9, §10) записал CORRECTION: «Цена S1 — 9 900 ₽ (решение №2 от
27.09.2026)», а 29 900 ₽ «в репозитории нет». Факт о memo верен. Вывод
устарел: у проверяющего не было Issue #291/#329. Актуализация #291 от
02.10.2026 прямо фиксирует 29 900 ₽ как целевую цену P1 после всех quality
gates и отменяет 9 900/19 900; #329 повторяет это. **R-1 снят актуальным
источником.** Цифра 29 900 ₽ не выдумана и не снижается. Цены других систем
не утверждены. Отчёт #342 не правился.

## 4. Не повторялось и не решалось

- Дефекты I-1…I-21, R-1/R-2 первичной сверки #316 — закрыты перечитом в #314.
- Аудит продуктов, рендер Writer/Word, пересборка бинарников.
- Решения D-P3, D-T2, D-PKG, D-PRICE, D-ORDER.
- Продукты, страницы, генераторы, конфиг, SKU, оплата, CI — не менялись.

## 5. Фактические проверки

| Проверка | Результат |
|---|---|
| `python3 -m pytest tools/test_delivery_artifacts.py -q` (rootdir = worktree) | `9 passed in 0.18s` |
| `git diff --check` | пустой вывод, код 0 (tracked-файл паспорта) |
| Хвостовые пробелы в новом отчёте (Grep `[ \t]+$`) | 0 |
| `git status --porcelain --untracked-files=all` | ` M tools/candidates/MB001_VALUE_PASSPORTS_A.md`; `?? tools/candidates/MB001_VALUE_A_DELTA_PROVENANCE.md` — только два разрешённых файла |
| `sha256sum` 9 файлов | 5 входов индекса (P3 `03`, `10`, P2 `00-INSTRUKCIYA.pdf`, отчёт #342, перечит) равны `context-index.json`; 4 снимка Issue #291/#329 (body и comments) записаны в §2 — в индексе их хешей нет |

STOP / REVIEW_REQUIRED. Draft PR создаёт координатор.
