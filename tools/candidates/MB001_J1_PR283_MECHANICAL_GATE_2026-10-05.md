# PR #283: механическая проверка кандидата J1 — 05.10.2026

Проверенный кандидат: `14c5a562c93ad7f7c28aa73588d9ca2d8b35fea3`, PR https://github.com/pmgpt12-arch/marzhavbetone.ru/pull/283.
Фактическая среда: ai-workstation; отдельный detached worktree `/home/denis/.local/state/claude-dispatcher/recovery-20261005/mechanical/pr283`.
Момент сверки: 2026-10-05T11:35:27Z.


execution_pattern: one_shot
primary_result: PR283_exact_head_mechanical_verification
feedback_loop_required: false
checkpoint_policy: verified_only
frozen_input_sha: 14c5a562c93ad7f7c28aa73588d9ca2d8b35fea3

## Результат

Механический публичный gate PASS: 39 проверок из 39, ноль падений, ноль пропусков на уровне реестра. Команда завершилась с exit 0 за 20,45 секунды, предел 180 секунд. Статья технически готова к ручной приёмке владельцем. Это не разрешение на публикацию.

Текущее описание PR устарело: утверждения «обложки нет», «og:image пусто», «twitter:card=summary», «37 из 39» не соответствуют проверенному SHA.

| Критерий | Фактический результат |
|---|---|
| Канонический текст issue #282 | H1 и все 8 абзацев совпадают после разрешённой нормализации пробелов/NBSP и снятия Markdown **. Ни факты, ни формулировки не изменены |
| Источник канона | issue #282 updatedAt 2026-09-28T04:50:17Z; SHA256 body 7fd18e3e9fc77c04646d989c418ebdf7cd0f68be9b8fbf3a0dacd755ec116d98 |
| JPEG обложка | Существует, декодируется: 1672×941, 201619 bytes; SHA256 e8cba74869bd3ee8161d907050c239621a5f935f74eb41688c12e346979281e0 |
| Подключение обложки | article-cover, одна карточка индекса, og:image, Article.image; twitter:card summary_large_image; HTML width/height совпадают с изображением |
| Метаданные | title/H1/description/canonical/og:url и JSON-LD присутствуют и согласованы; check_meta PASS, новых замечаний к этой статье нет |
| Sitemap | Ровно одна запись будущего URL; canonical и og:url равны этому адресу; check_seo PASS |
| Ссылки | link_audit PASS: 89 страниц, ноль битых локальных целей; три собираемых при деплое файла явно пропущены |
| Платная связка | Ссылок на P1/S1 в основном содержимом нет |
| Обложки всего сайта | check_covers и test_covers PASS; 42 разбора с обложками, ноль проблем и дубликатов |
| RSS | check_rss PASS; при выпуске статья попадёт в ленту согласно действующим правилам |

Будущий URL: https://marzhavbetone.ru/articles/ks-2-ks-3-podpisany-zakazchik-ne-oplachivaet.html.

## Оставшиеся ограничения приёмки

1. Даты datePublished/dateModified/видимая дата/lastmod согласованы, но стоят 2026-09-28. Перед фактическим разрешённым выпуском поставить принятую дату публикации.
2. Канонический текст говорит о разделе «Судебная практика», фактическая навигация — «Разборы». Это источник владельца, механическая проверка его не переписывает.
3. Спорная скобка в абзаце о документах и двоеточие перед «с» совпадают с каноном. Нужна редакционная приёмка владельца, а не автоматическая правка.
4. Новый визуальный рендер в этой единице не выполнялся. Предыдущее описание PR сообщает о рендере без обложки; это не доказательство вида страницы с текущей обложкой. Декодирование и подключение актива проверены.
5. В общем публичном gate test_manifest_rebuild возвращает PASS, но внутри сообщает, что build_all.py не компилируется и update_manifests.py завершился с кодом 1, поэтому соответствующие генераторы не запускались. Это ограничение общего покрытия; генераторный rebuild не считается проверенным этой единицей. Статья и её обложка эти файлы не меняют.
6. Прочие предупреждения check_meta и sync_kit_file_counts относятся к существующим страницам; общего аудита и исправлений здесь нет.

## Выполненные команды и доказательства

```text
git fetch origin 14c5a562c93ad7f7c28aa73588d9ca2d8b35fea3
git worktree add --detach /home/denis/.local/state/claude-dispatcher/recovery-20261005/mechanical/pr283 14c5a562c93ad7f7c28aa73588d9ca2d8b35fea3
gh issue view 282 --repo pmgpt12-arch/marzhavbetone.ru --json body,title,updatedAt
timeout 180 python3 tools/run_checks.py --class public
timeout 45 python3 /home/denis/.local/state/claude-dispatcher/recovery-20261005/mechanical/verify_pr283.py
git status --short
```

После проверок рабочее дерево оставалось чистым. Последняя focused-команда читает канон issue #282, выделяет H1/8 основных абзацев HTML, сравнивает их после NFC/whitespace нормализации, декодирует JPEG через Pillow, проверяет карточку/метатеги/JSON-LD и запись sitemap. Машинный результат: `MB001_J1_PR283_MECHANICAL_GATE_2026-10-05.json`; полный публичный лог: `MB001_J1_PR283_PUBLIC_CHECKS_2026-10-05.log`.

Исходный PR/статья/цены/продукты не изменены. Main merge, deploy, внешние формы, письма и генерация изображений не выполнялись. Изменения этой ветки — только доказательства проверки.
