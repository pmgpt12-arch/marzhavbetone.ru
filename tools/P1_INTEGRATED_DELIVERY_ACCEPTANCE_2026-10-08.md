# Независимая техническая приёмка интегрированного P1: выдача

Дата: 2026-10-08.
Проверенный worktree: /home/denis/projects/marzhavbetone.ru/.worktrees/codex-p1-final-20261008.
Фактически проверенный HEAD: 7a448066a4e9cac6fed724e5403ac54610e1ba0f.

## Результат

Локальная техническая приёмка изданий P1 на интегрированном HEAD пройдена. Эти проверки выполнены заново на интегрированном коде, а не перенесены с авторской ветки.

На начало и конец запуска git status --porcelain проверяемого worktree был пустой. Тесты использовали временные файлы, localhost и локальный mock платёжного API. PHPRC временного php.ini задавал sendmail_path=/bin/false для основного и дочерних PHP-процессов. Реальных платежей и писем не было.

| Тест | Фактический результат |
|---|---|
| tools/test_p1_immutable_edition.php | rc=0, 14 проверок PASS |
| tools/test_delivery_all_or_nothing.php | rc=0 |
| tools/test_delivery_cache_freshness.php | rc=0 |
| tools/test_download_limit.php | rc=0, HTTP 200×30/429×10, downloads=30 |
| tools/test_status_key.php | rc=0 |
| tools/test_price_authority.php | rc=0 |
| tools/test_order_lock.php | rc=0, 8 конкурирующих процессов |

Ограничение существующего test_download_limit: сквозной отрицательный chattr+i сценарий пропущен; функциональные сценарии ошибок записи пройдены. Это не полная проверка реального провайдера и доставки продукта покупателю.

## Что подтверждено

- Edition и SHA записаны в pending-заказ до первого запроса к локальному mock API; клиентская подделка edition и price не используется.
- Старый pending-заказ после изменения мастеров получает OLD_EDITION.
- Изменение в одну секунду и удаление файлов создают новый снимок; изменение только mtime не меняет edition.
- Повторный callback сохраняет edition, token, expires_at, downloads и email_sent_at.
- HTTP download.php возвращает точные байты закреплённого старого архива.
- Missing/corrupt закреплённого архива даёт отказ без увеличения счётчика и без сборки текущего издания.
- Legacy issued P1 не получает придуманного исторического pin; legacy unissued без edition блокируется.
- Конкурирующая сборка не обходит блокировку и не оставляет частичный staging; payment при занятой блокировке не создаёт заказ и не обращается к API.
- Остальные SKU не получили поведение P1: issued-кэш P3 после изменения мастеров пересобирается; постороннее edition не блокирует callback и HTTP download.

## Production legacy gate: BLOCKED, факты неизвестны

Read-only наблюдения:

- /home/denis/projects/marzhavbetone.ru/config.php является tracked-файлом. В нём YOOKASSA_MODE=test, идентификатор/ключ кассы являются placeholders. Значения секретов не выводились.
- Там ORDERS_DIR указывает на локальную orders рядом с файлом. PRODUCTS_DIR содержит только закомментированный пример, а не подтверждённый путь production.
- Локальные orders основного репозитория и интегрированного worktree содержат 0 order_*.json. Это факт о локальных папках, не вывод о покупателях production.
- .github/workflows/deploy.yml использует secrets.DEPLOY_HOST, secrets.DEPLOY_USER, secrets.DEPLOY_SSH_KEY. Default SITE_PATH=www/marzhavbetone.ru, PRODUCTS_PATH=products-marzhavbetone; действующие пути могут быть переопределены secrets.
- /home/denis/.ssh/config отсутствует; DEPLOY_* переменные в процессе отсутствуют. .openai/hosting.json отсутствует.
- Подтверждённого production endpoint/конфигурации/авторизованного транспорта в проверенных входах нет. Соединение с предполагаемым хостом не выполнялось.

Количество production P1 pending/waiting_for_capture/paid заказов без edition: НЕ УСТАНОВЛЕНО.
Наличие авторитетного прежнего ZIP и его соответствие покупкам: НЕ УСТАНОВЛЕНО.

Для снятия gate нужны read-only доступ к фактическим ORDERS_DIR/DELIVERY_DIR и подтверждённые исторические архивы. Далее — dry-run перечень состояний/изданий, проверка SHA и покрытие legacy pending-заказов. Ни токены, ни контакты, ни платёжные реквизиты в отчёт включать не следует.

При отсутствии подтверждённого исходного издания: BLOCKED до решения владельца по конкретному восстановленному составу/SHA или ручной выдаче. Восстановление из текущих мастеров не доказывает исторический состав и запрещено как автоматическая миграция.

## Граница приёмки

Подтверждена локальная техническая корректность интегрированного контура изданий P1. Реальные заказы не изменялись. Production inventory/migration не выполнены; deploy/push не выполнялись. Это не юридическая приёмка и не SALE_READY.
