# НСП — ТЗ №4.2. Руководящая матрица выпуска

**PARTIAL_READY_WITH_BLOCKERS**. Реальный локальный HTTP и браузерный staging GitHub Actions **PASS**; production, платежи и ранее оплаченные заказы не изменены. **Release HOLD** остаётся.

| SKU | QA | Принятый архив (SHA12) | Изолированный staging | Release | Решение | Блокер |
|---|---|---|---|---|---|---|
| P1 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| P2 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| P3 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | page/browser PASS; checkout E2E OPEN | PREVIOUS_RELEASE_PRESERVED | NEEDS_CORRECTION | Provider checkout E2E not run |
| P4 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| P5 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | page/browser PASS; checkout E2E OPEN | PREVIOUS_RELEASE_PRESERVED | NEEDS_CORRECTION | Provider checkout E2E not run |
| P7 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| P8 | READY_CANDIDATE | 07a16f0d80fe | GET 200; POST 409; browser PASS | HOLD | BLOCKED | QA01 READY_CANDIDATE; later approval missing |
| P9 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| P10 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| P11 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| P13 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| T2 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| T3 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION | — | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| FREE/checklist | FULL_QA_PASS | bd50ad14084f | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| FREE/dengi | FULL_QA_PASS | 024fe485d70b | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| FREE/dop-raboty | FULL_QA_PASS | e09176633507 | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| FREE/vozvrat-ks | FULL_QA_PASS | f0ffd8d55a44 | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| FREE/uderzhaniya | FULL_QA_PASS | 77ef9381b960 | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| FREE/dogovor | FULL_QA_PASS | b9a3fd2bb0e9 | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| FREE/bankrotstvo | FULL_QA_PASS | 68a1d82c16fb | GET 200; POST 409; browser PASS | HOLD | BLOCKED | QA04 Git origin EVIDENCE_MISSING |
| FREE/avans | FULL_QA_PASS | 06d8e851d8bc | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| FREE/raschet-metrami | FULL_QA_PASS | bacf5f6cfacb | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| FREE/ispolnitelnaya-dokumentaciya | FULL_QA_PASS | 10c811a26bf0 | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |
| FREE/akt-skrytyh-rabot | FULL_QA_PASS | 85836ca18e58 | GET 200; POST 409; browser PASS | HOLD | ANNOUNCEMENT_READY | Release HOLD; new accepted ZIP not fetched via buyer route |

## Фактическая проверка

- Workflow [#40435072668](https://github.com/pmgpt12-arch/marzhavbetone.ru/actions/runs/40435072668) — SUCCESS. 24/24 страницы HTTP 200; 22/22 запрещённых POST — 409.
- 24 продукта × 5 разрешений (390, 430, 1280, 1366, 1920) = 120/120 сохранённых снимков. Горизонтальное переполнение = 0; H1/Title/Description/canonical уникальны.
- Синтетический ранее оплаченный заказ: GET 200 и повтор 200 с одинаковым SHA; чужой токен 403; истёкший 410. Реальные заказы не затронуты.
- QA-источники: точный архив SHA и все member SHA подтверждены для 11/12 Git-источников; QA04 остаётся EVIDENCE_MISSING для Git-происхождения. Release allowed: 0.
- Главная, P3 и P5 полностью совпали с контрольной версией main по SHA.

## Подтверждённые блокеры

- Direct GET существующих `/downloads/dengi.zip`, `/downloads/avans.zip`, `/downloads/checklist-zakrytiya-rabot.pdf` всё ещё HTTP 200 с прежними историческими SHA. Это старый статический маршрут; закрывать его без проверки уже выданных ссылок нельзя.
- В утверждённом новом маршруте `/lead.php` архивы предыдущих версий не выдаются: POST всех 11 = 409. Для платных незавершённых SKU `/payment.php` отклоняет все 11 POST = 409.
- Не пройдена тестовая выдача **нового** принятого архивного SHA через законно открытый покупательский маршрут, потому что выпуск HOLD.
- Отдельный внешний staging-хост не развернут: проверен локальный HTTP на отдельном GitHub Actions runner.
- QA04: нет Git-квитанции исходной FULL_QA_PASS; P8: после QA01 последняя принятая версия не доказана; провайдерская регрессия P3/P5 не проводилась.
- Ряд старых workflow требуют до-HOLD кнопку покупки и 10 бесплатных карточек, другие сравнивают сайт с устаревшим P3 baseline. Это не доказательство неспособности модели или отказа новых маршрутов; необходима отдельная адаптация контрактов.

## Решение

**Ничего не выпускать автоматически.** Доступные страницы оставить в draft PR #677. Руководящую приёмку и разрешение конкретных архивов оформить отдельно. Не изменять `main`, production, платежи и старые заказы.

**Доказательства:** [GitHub Actions #40435072668](https://github.com/pmgpt12-arch/marzhavbetone.ru/actions/runs/40435072668), artifact ID `12703497984`, SHA-256 ZIP `562e5f98e00ce96736fc6a4b4ccb7c926d809de732e3422730db9b57d16d0bbb`.
