# P2 independent model output — Issue #528

Provenance: exact OpenRouter anthropic/claude-opus-5.5 one attempt, recorded 2026-10-09. This is recovered model output from the dispatcher log; the original detailed JSON was ignored by git and not committed. For form 01, this verdict covers the earlier semantic version; the corrected version requires a fresh review.

```text
[Reading 37 lines from start (total: 37 lines, 0 remaining)]

2026-10-09T02:44:55Z executor: attempt=1 requested=OpenRouter/anthropic/claude-opus-5.5 actual=OpenRouter/anthropic/claude-opus-5.5 timeout=600s
Using the OpenRouter credential from the unencrypted global credential file /home/denis/.ori/credentials.json; run `ori auth migrate` to use OS credential storage.
Отчёт по форме 12 написан, вердикт **PASS**. Но в git он не попал: песочница не пропустила `git add -f`, поэтому коммита нет. Сейчас отчёт лежит только в игнорируемом каталоге worktree. Диспетчеру нужно выполнить:

```
git add -f tools/reports/p2-normative-12-20261009/review.json
git commit -m "P2: normative review of form 12"
```

**Результат проверки**

Существенных противоречий со ст. 708, 452 и 160 ГК РФ нет, эскалация не нужна:
- Документ действительно является соглашением сторон, его подписывают обе стороны с основанием полномочий.
- График прилагается к соглашению и тоже подписывается сторонами.
- Конечный срок фиксируется явно. Промежуточные сроки, которые не названы, прямо сохраняются.
- Цену и оплату форма не меняет и оплату не обещает.
- Подписывать документ задним числом форма не предлагает. Освобождения от ответственности за прошлую просрочку не утверждает.

Своего выбора маршрута в форме нет, по инструкции она применяется и в маршруте А, и в маршруте Б.

Два второстепенных замечания, на вердикт не влияют. Форму по условию задачи не правил.
1. **Ст. 708, п. 2.** Сроки меняются в порядке, который предусмотрен договором, а в форме нет поля для пункта договора об этом порядке. Рекомендую добавить фразу «Сроки изменяются в порядке п. [___] договора».
2. **Инструкция.** В её таблице форма 05 помечена только маршрутом «А». При этом в маршруте Б инструкция ведёт к форме 12, а форма 12 требует обоснование 05. Нужно пометить 05 как «А, Б» и упомянуть её в шаге 7 маршрута Б.

Приложение 3 к приказу № 344/пр к форме 12 не относится: форма на приказ не ссылается и актом скрытых работ не является. Поэтому его редакцию я не сверял.

**Чем проверено**
- **Документ.** Semantic hash, посчитанный `python3 tools/semantic_hash.py`, совпадает с заданием: `sha256:7e448aef…53f8`. Сырой sha256 файла DOCX совпадает с `receipt.json`.
- **Текст формы.** Распаковать DOCX песочница не дала. Поэтому текст я восстановил из генератора формы и посчитал его хеш: получилось ровно `7e448aef…53f8`, то есть проверялся именно текущий документ. Все 11 проверенных фраз в этом тексте найдены дословно.
- **Нормы.** Все три `source_hash` пересчитаны и совпадают с сохранёнными источниками. Каждая правовая фраза формы сверена с полным текстом статьи в КонсультантПлюс.
- **Отчёт.** Строгий JSON, разбирается через `jq`.

**Что изменено.** Создан только `tools/reports/p2-normative-12-20261009/review.json`. Временные файлы удалены. В память добавлено, что `git add -f` в таких заходах тоже требует разрешения.

**Что не проверено.** Песочница не дала прочитать стандарт языка и P0 фабрики из `~/.config/ai-business-os/`. Поэтому язык отчёта по стандарту не сверен; это сказано и в самом отчёте, в `acceptance_note`.
2026-10-09T02:49:24Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
2026-10-09T02:49:24Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
```
