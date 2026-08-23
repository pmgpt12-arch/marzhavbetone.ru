# Индекс знания: где лежит вердикт

Маршрутизатор, а не хранилище. Полный индекс — `docs/KNOWLEDGE_INDEX.md`
репозитория `pmgpt12-arch/ai-business-os`; здесь то, что живёт на сайте,
и адрес остального.

## Перед новым исследованием

1. Найти тему ниже.
2. Открыть источник и найти вердикт.
3. Вердикт есть, а условие пересмотра не сработало — **исследование не
   повторяется.** Называются вердикт, дата и условие.

## Здесь, в репозитории сайта

| Тема | Источник |
| --- | --- |
| Воронка: числа | `docs/FUNNEL.md` (собирает `tools/funnel_report.py`) |
| Поисковый спрос | `data/seo/search-demand.csv`, `content/strategy/keyword-map.csv` |
| Маршруты «поиск → продажа» | `docs/SEARCH_TO_SALE_SPRINT_2026-08-16.md` |
| Что делать под поиск | скил `marzha-seo` |
| Материал и публикация | скил `marzha-content` |
| Позиционирование и персона | `content/strategy/positioning.md` |
| Instagram: доступ и публикация | `docs/INSTAGRAM_SETUP.md` |
| Автовыдача по слову в комментарии | `docs/INSTAGRAM_SETUP.md`, `ig-webhook.php` |
| Ролики: конвейер, стоимость, дефекты | `docs/INSTAGRAM_SPRINT_2026-08-16.md` |
| Ролики: стандарт производства | `content/reels/STANDARD-V2.md` |
| Ролики: формат сценария и учёт | `content/reels/README.md` |
| Готовые mp4 и почему они в репозитории | `media/README.md` |
| Задачи и ворота фаз | `data/ops/backlog.csv`, `docs/EXECUTION-90.md` |
| Текущее состояние | `docs/PROJECT_STATE.md` |

## В соседнем репозитории `ai-business-os`

Чужие инструменты и скилы — `docs/Skills_Import.md`. Решения —
`docs/Decisions.md`. Факты среды — `docs/Environment_Facts.yaml`. Инсайты
контента — `projects/marzha_v_betone/research/insights.md`. Модели —
`docs/Model_Ladder.yaml`.

Короткий ролик, знание сверх `content/reels/`: разбор трендовых сервисов
и вердикт по Virale (ChatPlace) — `docs/research/VIRALE_INTELLIGENCE.md`;
переносимая часть (отбор референса, схема разбора, крючки, раскадровка,
диагностика по метрикам, петля обучения) —
`docs/specs/REELS_INTELLIGENCE_SPEC.md`. Оба от 23.08.2026. Там же
записано, какие метрики Reels официальный API Meta отдаёт, а какие нет:
кривой удержания по секундам в нём нет вовсе.

Из сессии, открытой на одном сайте, они не видны. Репозиторий
подключается, а не объявляется отсутствующим.
