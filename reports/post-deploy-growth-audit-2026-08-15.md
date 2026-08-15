# Post-deploy verification — 15.08.2026

## EXECUTIVE SUMMARY

Аудит **не смог** выполнить свою главную задачу в том виде, в каком она
поставлена: **production из этой сессии недоступен**. Замер, а не оценка:

```
curl https://marzhavbetone.ru/          → CONNECT tunnel failed, 403
curl https://marzhavbetone.ru/robots.txt → CONNECT tunnel failed, 403
WebFetch https://marzhavbetone.ru/      → EGRESS_BLOCKED
```

Егресс-политику шлюза задаёт владелец среды; из сессии она не меняется.
Поэтому **все пункты, требующие HTTP-ответа боевого сайта, помечены
`UNVERIFIED`, а не `PASS`** — включая коды ответов, canonical на проде,
поведение под Googlebot/YandexBot/OAI-SearchBot, реальный платёж и живую
доставку письма. Это ограничение среды, а не пропущенная работа, и
подменять его чтением репозитория было бы ровно той ошибкой, против
которой написано задание.

Второе, что аудит обнаружил сразу и что важнее первого: **аудировать
предлагалось разошедшуюся версию**. `origin/main` ушёл на 7 коммитов
вперёд рабочей ветки и принёс три новых товара (t4, t5, t6). Слияние дало
конфликт, а после разрешения выяснилось, что **три новых товара
отсутствовали в каталоге** — их карточки жили в `index.html`, откуда
каталог был перенесён. `sync_catalog.py` назвал это тремя строками
«в кассе есть t4/t5/t6, на витрине его нет». Товар, которого нет на
витрине, не покупают.

Третье — подтверждён и закрыт P0, который вы назвали: «Девять материалов»
при десяти карточках.

## PRODUCTION VERSION

```
LOCAL HEAD:              8165017 (merge origin/main → рабочая ветка)
ORIGIN/MAIN:             4c50adc
PRODUCTION DEPLOY COMMIT: UNVERIFIED — прод недоступен, коммит выкладки
                         из сессии не читается
AUDIT DATE/TIME:         2026-08-15 04:00–04:30 UTC
TOTAL HTML FILES:        85
TOTAL SITEMAP URLS:      82
TOTAL ARTICLES:          39
TOTAL PRODUCTS:          18
TOTAL MATERIALS:         10
TOTAL DEMO:              4
```

Расхождение версий на момент начала аудита: ветка была **9 впереди / 7
позади** `origin/main`. Слито, конфликты разрешены, потери восстановлены.

## P0 — НАЙДЕНО И ЗАКРЫТО

### P0-1. Три товара пропали с витрины при слиянии

**Evidence:** `python3 tools/sync_catalog.py` →
`РАСХОЖДЕНИЕ: в кассе есть t4, на витрине его нет` (и t5, t6).
`grep -c 't4-\|t5-\|t6-' katalog.html` → `0`.

**Impact:** три оплачиваемых товара недостижимы из каталога.

**Fix:** карточки перенесены из `origin/main:index.html` в `katalog.html`,
пересобраны группы (`catalog_groups.py`), разметка синхронизирована.

**Acceptance:** `sync_catalog.py` → `платных 18, бесплатных 10`,
расхождений 0; `check_products.py` → `18 продуктов на продаже`.

### P0-2. «Девять материалов» при десяти

**Evidence:** `katalog.html:687` — `<p class="lead">Девять материалов…`,
при `ls materialy/*.html | grep -v index | wc -l` → `10` и полосе
переходов `Бесплатные<span>10</span>`.

**Причина, а не симптом:** полосу переходов собирает инструмент, а лид
писали рукой. Два счёта одного и того же из разных источников расходятся
молча — ничем не ловилось.

**Fix:** счёт выведен в `sync_catalog.py` из того же значения, что и
разметка, с числительным прописью. Хардкода больше нет.

**Acceptance:** `sync_catalog.py` до правки печатал
`РАСХОЖДЕНИЕ: в лиде бесплатных стоит «Девять», а материалов 10 — надо
«Десять»`; после `--write` — код 0.

### P0-3. Переполнение метки товара на каталоге

**Evidence:** `check_desktop.py` → `katalog.html @1366: div.product-number:
содержимое шире коробки на 3px` — длинные метки новых ступеней входа
(«ТРЕБУЮТ ВЕРНУТЬ АВАНС») в разрядке .13em.
**Fix:** перенос по словам. **Acceptance:** 9 страниц, расхождений 0.

## P0 — ПРОВЕРЕНО, ДЕФЕКТА НЕТ

### Серверная цена (усиленный вами пункт)

Это единственное место, где ошибка стоит денег напрямую, поэтому
проверено не чтением, а тестом.

`mvb_resolve_product()` возвращает `['sku' => $sku] + $catalog[$sku]`.
Оператор `+` отдаёт приоритет левому операнду, в котором только `sku`, —
`price` и `name` приходят **из каталога сервера**. В `payment.php`
клиентский массив затем отбрасывается целиком (`$items = $validatedItems`).

`tools/test_price_authority.php` подаёт подделанные позиции:

| случай | результат |
|---|---|
| верный sku + `price: 1` | цена каталога 249000 |
| опознание по названию + `price: 100` | цена каталога |
| `price: -500000` | цена каталога |
| несуществующий sku | отвергнут (`null`) |
| подменённое `name` | имя каталога — в чек ЮKassa чужой текст не уйдёт |

**Мутация:** замена объединения на `$item + [...] + $catalog[$sku]`
красит тест на трёх случаях. Проверка живая.

**STATUS: PASS (CODE VERIFIED).** Живой платёж не проводился.

## ОБЯЗАТЕЛЬНАЯ ТАБЛИЦА — задачи прошлого спринта

| ID | TASK | STATUS | REPO EVIDENCE | PRODUCTION EVIDENCE | TEST |
|---|---|---|---|---|---|
| P0-1 | Юридические ошибки в статье | PASS | 3 утверждения переписаны, `docs/LEGAL_AUDIT.md` | UNVERIFIED | поиск по ГАРАНТ/КонсультантПлюс |
| P0-2 | Legal audit всего сайта | PARTIAL | 588 мест, разобрано 6 | UNVERIFIED | `legal_claim_audit.py` |
| P0-3 | Legal lint | PASS | `tools/legal_claim_audit.py`, в CI как WARNING | н/д | прогон код 0 |
| P0-4 | Две битые ссылки | PASS | обе цели верны в `materialy/akt-skrytyh-rabot.html` | UNVERIFIED | `link_audit --verify` |
| P0-5 | Link audit по всему сайту | PASS | 82 страницы, 0 битых | UNVERIFIED | `test_link_audit.py`, 7 проверок |
| P1-1 | Разбор checkout | PASS | `docs/CURRENT_CHECKOUT_FLOW.md` | UNVERIFIED | чтение кода |
| P1-2 | Убрать ручной шаг | PASS | ручного шага в покупке не было; убран в калькуляторе | UNVERIFIED | — |
| P1-3 | Автовыдача + гонка | PASS (CODE) | `flock` + атомарная запись | NOT LIVE-VERIFIED | `test_order_lock.php`, мутация 8→1 |
| P1-4 | Калькулятор → товары | PASS | роутинг по сценариям, выход на диагностику | UNVERIFIED | — |
| P1-5 | События калькулятора | PARTIAL | 3 из 4; имена не совпадают со спецификацией | UNVERIFIED | `check_goals.py` |
| P1-6…8 | Диагностика | PARTIAL | страница есть, маршруты в YAML а не JSON | UNVERIFIED | — |
| P1-9 | product-map.csv | FAIL | файла нет; эквивалент — `money-pains.yaml` без полей stage/status | н/д | — |
| P1-10 | PRODUCT_PAGE_AUDIT | FAIL | не создан | н/д | — |
| P1-11 | Bundles | FAIL | `bundle_candidates` в YAML, не опубликованы → **DESIGNED NOT LIVE** | н/д | — |
| P1-12 | Thank-you upsell | FAIL | `success.html` без следующего товара | UNVERIFIED | — |
| P1-13 | Cross-sell на товарах | FAIL | контекстного блока нет | н/д | — |
| P1-14 | /materialy/ hub | PASS | есть, BreadcrumbList, в sitemap | UNVERIFIED | `check_free_materials.py` |
| P1-16 | Money graph | PARTIAL | `data/seo/money-graph.yaml`, не `.csv` | н/д | `money_graph.py` код 0 |
| P1-17 | MONEY_GRAPH_AUDIT | FAIL | не создан | н/д | — |
| P1-18 | Дубли description у demo | PASS | дублей 0 | UNVERIFIED | `check_meta.py` |
| P1-21 | BreadcrumbList | PARTIAL | products 18/18, materialy 11/11, articles 40/40, demo 0/4 | UNVERIFIED | — |
| P1-22 | События Метрики | PASS | 16 целей, расхождений 0 | UNVERIFIED | `check_goals.py`, мутация |
| P1-23 | Purchase event | PARTIAL | `order_id`, `order_price`, `currency` есть; `source`/`landing_page` нет | UNVERIFIED | — |
| P1-25 | Sales dashboard | FAIL | структура есть (`money-impact.csv`), метрик нет | н/д | — |
| P2-4 | PR #152 | UNVERIFIED | в этой сессии не открывался | н/д | — |

## SCORES

| контур | оценка | основание |
|---|---|---|
| ACQUISITION ENGINE | **STRONG** | 39 разборов, 10 бесплатных, hub, sitemap 82, граф связности зелёный |
| MONETIZATION ENGINE | **PARTIAL** | путь до оплаты цел, но нет cross-sell, upsell и bundles |
| ANALYTICS | **PARTIAL** | 16 целей сходятся; атрибуции в purchase нет, дашборда нет |
| LEGAL ACCURACY | **PARTIAL** | одна статья вычищена, 582 места не смотрены |
| TECHNICAL QUALITY | **STRONG** | 22 проверки в гейте, 3 новых теста с мутацией, 0 битых ссылок |

## END-TO-END FUNNEL STATUS

```
TRAFFIC ENTRY      UNVERIFIED (прод недоступен)
  ↓
MONEY PAIN         PASS — router 6 сценариев, все цели существуют
  ↓
CONTENT            PASS — 39 разборов, money_graph код 0
  ↓
FREE / DIAGNOSTIC  PASS — 10 материалов, диагностика 8 вопросов
  ↓
PRODUCT            PASS — 18 товаров, витрина сходится с кассой
  ↓
CART               CODE VERIFIED — localStorage, итог = сумма позиций
  ↓
PAYMENT            PASS (CODE) — цена серверная, доказано тестом
  ↓
AUTO DELIVERY      NOT LIVE-VERIFIED — гонка закрыта, письмо не отправлялось
  ↓
UPSELL/CROSS-SELL  FAIL — не существует
  ↓
ANALYTICS          PARTIAL — purchase без source/landing_page
```

**Звено, которого нет: UPSELL / CROSS-SELL.** Оно единственное в цепочке
со статусом FAIL, и оно же — единственное, которое поднимает выручку без
нового трафика.

## TOP 5 BOTTLENECKS

Если завтра придут 1 000 целевых субподрядчиков:

1. **Нет допродажи.** Купивший один комплект не видит следующего.
   *Impact:* весь прирост AOV. *Fix:* `product-map.csv` → блок на
   `success.html` и на страницах товаров. *Acceptance:* у каждого товара
   назван следующий, тест на несуществующие ссылки.
2. **Purchase без источника.** Нельзя сказать, какой канал принёс деньги,
   значит нельзя решить, где публиковать. *Fix:* `source`, `landing_page`
   в параметры цели. *Acceptance:* цель приходит с непустым источником.
3. **582 непроверенных юридических места** на продающих страницах.
   *Impact:* репутационный и юридический риск в теме, где ошибка дороже
   охвата. *Fix:* разбор по деньгам — сначала товары.
4. **Bundles спроектированы, но не существуют.** *Fix:* решение владельца
   о цене, затем сборка. *Acceptance:* комплект покупается.
5. **Прод не проверяем автоматически.** Ни один прогон не смотрит боевой
   сайт — расхождение выкладки с репозиторием обнаружится случайно.
   *Fix:* smoke-прогон из Actions (у раннера егресс есть).

## UNVERIFIED ITEMS — почему

Всё ниже требует HTTP-ответа боевого сайта и из этой сессии недостижимо:
коды ответов и canonical на проде; поведение под Googlebot / YandexBot /
OAI-SearchBot; реальное создание платежа; доставка письма; повторный
webhook на живом заказе; фактический коммит выкладки.

Раннер GitHub Actions егресс имеет — прогон, который это закроет, описан
пунктом 5 выше и не сделан.

## RECOMMENDED NEXT SPRINT

1. Cross-sell + upsell по `product-map.csv` (единственный FAIL в воронке).
2. `source` и `landing_page` в purchase.
3. Production smoke из Actions.
4. Разбор юридической очереди по товарам.
5. Bundles — после решения владельца о цене.
