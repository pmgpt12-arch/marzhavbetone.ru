# P5 native integration — исправление source placement, PR449

05.10.2026. Parent #291, author PR449 frozen `218c4f8705f9ea2e805b7197f2f4463432686545`. Новая отдельная ветка `codex/p5-owner-native-layout-ci-20261005`. Frozen worktree/PR не менялись во время независимого #452. API cost0.

## Ошибка → первопричина → класс → правило → gate → подтверждение

CI public run37305164702/job111746964983: 38 из39 checks PASS, один blockingFAIL `check_packages`: `НЕТ МАНИФЕСТА templates`. Полный failure log прочитан `gh run view ... --log-failed`; точное сообщение независимо воспроизведено локально на frozen218c.

Первопричина — автор разместил reusable native inputs в `products-storage/templates`. Существующий inventory правильно считает каждую прямую подпапку products-storage продуктовым пакетом и требует manifest. Это **PRODUCT_SCOPE_DISCOVERY / source placement**, собственная регрессия размещения, не legacy baseline, не модель и не инфраструктура.

Правило: reusable generator assets располагаются по существующей convention `tools/templates`, вне product-package discovery. Перед передачей такой source integration обязательно выполнять неизменённый `check_packages` и public checks. Не маскировать служебную папку новым product manifest/SKU и не ослаблять checker.

## Узкое исправление

Три файла `products-storage/templates/p5-owner-excel/` перенесены в `tools/templates/p5-owner-excel/` с сохранением точных байтов. Locator существующего P5 builder заменён на `Path(BASE_DIR).parent / tools / templates / p5-owner-excel`. Паспорт/основной report обновлены адресно. Финансовые формулы, source semantic gate, negative tests, канонические buyer04/05, конфиг и все чужие исходники неизменны относительно218c.

| Файл | SHA256 до/после, одинаковый |
|---|---|
| 04-raschet-ubytkov.xlsx | 20165a12e04cf37dee98ac8d528cb78026d5a342e24231f69a09bd70c6bedc31 |
| 05-reestr-uderzhaniy.xlsx | db0d99f745e460b29654c3079483103e1bcc39d65ad9e8c36d002288ed5df9ae |
| README.md | 72577430c956fe7173dc790be5c74d52fa22f1fe8a3e5ccca9508757166315a1 |

`tools/check_packages.py` и `tools/test_check_packages.py` не изменены. Frozen218c сохранён.

## Проверки

Контракт iterative/verified_only записан в паспорт до перемещения. Четыре bounded CLI результата сохранены в `evidence/P5_NATIVE_CI_LAYOUT/`; совокупное наблюдаемое время21,84с.

1. Frozen218c: `python3 -B tools/check_packages.py` → exit1, `НЕТ МАНИФЕСТА templates`, 31package/1broken. Это ожидаемый отрицательный источник.
2. Corrected source: та же неизменённая команда → exit0, 30package/0broken. Исторические неадресуемые копии остаются только сообщениями к сведению.
3. `python3 -B -m pytest -q -p no:cacheprovider tools/test_p5_owner_native.py` → 13PASS,0,50с. Actual generator выдаёт те же exact owner bytes; negative formula/DV/name/merge/hash guards сохранены.
4. `python3 -B tools/run_checks.py --class public` → 39/39PASS,0failed,0skipped,exit0.

Move receipt подтверждает побайтную неизменность templates. Machine CI receipt фиксирует команды и ожидаемые/фактические коды. Frozen input был диагностирован, затем исправлен известный layout cause; blind CI rerun не выполнялся. 19 финансовых Calc проверок не повторялись: покупательские файлы/формулы и код вычислений не менялись, их предыдущая проверка остаётся в основном evidence.

## Следующий gate

Независимый sourceguard #452 проверяет frozen218c; этот механический placement patch передаётся отдельно по новому head для координации. После результата452 и зелёного CI возможна интеграция только в working P5 цепочку. Owner native cosmetics повторно не спрашиваются; main/deploy/live price/SKU/payment/legal gates сохраняются.
