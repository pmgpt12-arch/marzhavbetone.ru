# P2 independent model output — Issue #523

Provenance: exact OpenRouter anthropic/claude-opus-5.5 one attempt, recorded 2026-10-09. This is recovered model output from the dispatcher log; the original detailed JSON was ignored by git and not committed. For form 01, this verdict covers the earlier semantic version; the corrected version requires a fresh review.

```text
[Reading 24 lines from start (total: 24 lines, 0 remaining)]

2026-10-09T02:11:58Z executor: attempt=1 requested=OpenRouter/anthropic/claude-opus-5.5 actual=OpenRouter/anthropic/claude-opus-5.5 timeout=600s
Using the OpenRouter credential from the unencrypted global credential file /home/denis/.ori/credentials.json; run `ori auth migrate` to use OS credential storage.
Форма 03 прошла нормативную проверку без противоречий: вердикт **PASS**, эскалация не нужна. Есть одно некритичное замечание (minor). Языковую проверку по стандарту P0 сделать не удалось: файлы стандарта мне недоступны, подробности ниже.

**Изменено:** создан только `tools/reports/p2-normative-03-20261009/review.json`. Форма и остальные файлы не менялись, коммита нет.

**Итог проверки:**
- **Нормы ст. 743, 709 и 716 ГК РФ.** Для каждой полный текст есть в сохранённых источниках КонсультантПлюс. Хеши источников я пересчитал по правилу репозитория, все три совпали с записанными. Тексты статей полные, редакция у всех одна: ред. от 24.06.2025, с изм. от 09.06.2026.
- **Проверено 13 фрагментов формы.** Это оба маршрута, срок в десять дней с оговоркой об ином сроке, приостановка соответствующих работ, меры сохранности и блок подписи. Автоматической оплаты форма не обещает и изменением договора себя не называет. Цену и сроки она отсылает к соглашениям 11 и 12. Маршруты А и Б совпадают с разделами 2, 3 и 6 инструкции.
- **Замечание.** Фраза о десяти днях по п. 3 ст. 743 стоит после обоих маршрутов, хотя к уже выполненным работам (маршрут Б) она неприменима. В отчёте предложена правка: привязать эту фразу к маршруту А, а для маршрута Б дать нейтральный срок ответа.
- **Приказ № 344/пр** не проверялся: форма 03 на него не ссылается, в список норм задачи он не входит, относится к форме 04.

**Чем проверено:**
- `python3 tools/semantic_hash.py` по форме 03 дал `sha256:5160952055…aa4`, это совпадает с хешем из задачи.
- Распаковать DOCX песочница не дала. Поэтому текст формы я восстановил из генератора `products-storage/build_paid_02_remaining_forms.py`. Его хеш совпал со смысловым хешем файла, то есть проверен именно текст текущей версии.
- Хеши источников норм пересчитаны через `jq` и `sha256sum`.
- `jq` подтвердил, что отчёт — корректный JSON.

**Чего не хватило и что нужно знать диспетчеру:**
- Файлы `Marzha_Factory_P0.md` и `Marzha_Communication_Standard.md` из `~/.config/ai-business-os/` песочница не дала прочитать. Языковая проверка по ним не выполнена, и это записано в `acceptance_note`. Готовым по языку отчёт считать нельзя.
- Инструкцию `00-INSTRUKCIYA.docx` я читал по её генератору, а не по самому файлу, и хеш файла с генератором не сверял. Поэтому она использована только как общий контекст.
- Каталог `tools/reports/` попадает под `.gitignore` (правило `reports/`), поэтому новый отчёт не виден в `git status`. При коммите его нужно добавить через `git add -f tools/reports/p2-normative-03-20261009/review.json`.
2026-10-09T02:17:38Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
2026-10-09T02:17:38Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
```
