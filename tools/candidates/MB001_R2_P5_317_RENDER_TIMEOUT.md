# MB001-R2-P5 · #317 · падение `render`: классификация

Дата: 29.09.2026. Draft PR #317 не менялся. #298, #309, генератор P5,
страницы, CI-конфигурация и выдача не менялись. CI не перезапускался.
Исправление `tools/check_desktop.py` внесено отдельным ТЗ — раздел
«Исправление» ниже.

## Вывод

**Не дефект #317.** Это унаследованный от `main` латентный дефект
`tools/check_desktop.py`: он проявляется недетерминированно, в зависимости
от поведения браузера и раннера.

- Проверка поднимает сайт однопоточным `socketserver.TCPServer`: одно
  соединение за раз, таймаута чтения нет.
- Если Chromium открывает к серверу соединение и ничего по нему не шлёт
  (так бывает с предварительными соединениями), сервер блокируется на
  чтении из него. Остальные запросы страницы ждут в очереди, событие
  `load` не наступает, и `page.goto` падает по таймауту 30 с.
- Тот же сервер стоит в `tools/check_mobile.py`.

Механизм воспроизведён локально детерминированно, и ошибка совпала с CI до
текста. Что в прогоне CI сработал именно он, напрямую не наблюдалось: логов
сокетов в CI нет. Для этого прогона это самое вероятное объяснение, и
остальные объяснения данные исключают (таблица ниже).

Итог по категориям ТЗ:
- дефект #317 — **исключён**;
- унаследованный дефект main — **да**, в коде проверки;
- инфраструктура — **да**, как недетерминированный триггер;
- CI не зелёный: повторного прогона не было.

## Доказательства

| # | Факт | Как получен |
|---|---|---|
| 1 | CI проверял merge-ref `e239f5c` = `4d7f2a6` (#317) поверх `5bd51d7` (#298) | лог job `109405294865`, шаг checkout |
| 2 | #317 меняет только `07.pdf`, `08.docx`, `10.docx`, `build_paid_07.py`, два отчёта и `tools/test_p5_documents.py`. HTML, CSS, JS, PHP, `.github/` и `tools/check_desktop.py` не менял | `git diff --name-only 5bd51d7 4d7f2a6` и тот же diff с фильтром `'*.html' '*.css' '*.js' '*.php' assets .github tools/check_desktop.py` — 0 файлов |
| 3 | Блобы одинаковы в `main` `b89f081`, #298 `5bd51d7` и #317 `4d7f2a6`: `tools/check_desktop.py` `447b8394cf31`, `render-checks.yml` `b73fe4635ee5`, `katalog.html` `f66e4bef97f5` | `git rev-parse <ref>:<path>` |
| 4 | Окружение CI одинаково у #298 (success) и #317 (failure): образ `ubuntu-24.04 20260920.314.1`, Chrome for Testing 153.0.8010.12 (playwright chromium v1243), Python 3.11.16 | логи job `108915518338` (#298) и `109405294865` (#317) |
| 5 | В #317 `check_mobile` прошёл (8 страниц). `check_desktop` за 43 с прошёл `index.html` на 4 ширинах и завис на первой ширине `katalog.html`, второй странице списка. У #298 тот же шаг прошёл 26 страниц × 4 ширины за 3 мин 20 с. Одиночная страница так медленно не грузится: это зависание | лог job, временные метки 12:29:00 → 12:29:43 |
| 6 | Из последних 100 прогонов `Проверки рендером` (с 17.09.2026) упал один — этот | `actions_list list_workflow_runs render-checks.yml`: 99 success, 1 failure |
| 7 | Локально на голове #317 `check_desktop.py` проходит три раза подряд: 26 страниц, расхождений нет, 76–82 с. Chromium 141 (`/opt/pw-browsers/chromium-1194`), playwright 1.56.0 | worktree `4d7f2a6`, `build_sitemap --write`, `build_rss --write`, `python3 tools/check_desktop.py` ×3 |
| 8 | Механизм воспроизводится детерминированно: одно молчащее TCP-соединение к `serve()` из `check_desktop.py` → `TimeoutError: Page.goto: Timeout … exceeded` на `katalog.html`, `wait_until="load"`. Без такого соединения — load за 1,0 с. На `main` `b89f081` результат тот же | скрипт ниже |
| 9 | Тот же обработчик в `http.server.ThreadingHTTPServer` к молчащему соединению нечувствителен: load за 1,2 с | скрипт ниже, режим `threaded idle` |

## Воспроизведение

Из корня репозитория, на любой из трёх голов (`main`, #298, #317). Нужен
playwright с хромиумом.

```bash
python3 repro_idle_socket.py single none     # load за ~1 с
python3 repro_idle_socket.py single idle     # TimeoutError: Page.goto: Timeout 10000ms exceeded.
python3 repro_idle_socket.py threaded none   # load за ~1 с
python3 repro_idle_socket.py threaded idle   # load за ~1 с
```

`repro_idle_socket.py` (в репозиторий не добавлялся):

```python
import functools, http.server, socket, sys, threading, time
sys.path.insert(0, "tools")
import check_desktop as cd
from playwright.sync_api import sync_playwright

mode, idle = sys.argv[1], sys.argv[2] == "idle"
if mode == "single":
    httpd, port = cd.serve()          # сервер ровно как в check_desktop.py
else:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    port = cd.free_port()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port),
        functools.partial(Quiet, directory=str(cd.ROOT)))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

s = socket.create_connection(("127.0.0.1", port)) if idle else None
time.sleep(0.2)
t = time.time()
with sync_playwright() as p:
    near = cd.chromium_nearby()
    b = p.chromium.launch(executable_path=str(near)) if near else p.chromium.launch()
    page = b.new_page(viewport={"width": 1366, "height": 768})
    try:
        page.goto(f"http://127.0.0.1:{port}/katalog.html", wait_until="load", timeout=10000)
        print(f"{mode} idle={idle}: load за {time.time()-t:.1f}s")
    except Exception as e:
        print(f"{mode} idle={idle}: {type(e).__name__}: {str(e).splitlines()[0]}")
    b.close()
```

Условие отказа в CI: Chromium держит к серверу соединение, по которому не
пришёл запрос, в момент загрузки страницы. Задать это условие снаружи
нельзя, поэтому отказ редкий (пункт 6 таблицы).

## Исправление (внесено в `tools/check_desktop.py`)

Сделано по отдельному ТЗ. Scope: только `tools/check_desktop.py`,
регрессионный тест и этот отчёт.

- `serve()`: `socketserver.TCPServer` заменён на
  `http.server.ThreadingHTTPServer`, `daemon_threads = True`. Обработчик,
  корень сайта, порт, `shutdown()`, список страниц, ширины и все проверки
  страницы не менялись. Неиспользуемый импорт `socketserver` удалён.
- Таймаут Playwright не менялся.
- Тест — `tools/test_check_desktop_server.py`, только стандартная
  библиотека, без браузера:
  1. при открытом молчащем TCP-соединении `katalog.html` отдаётся
     (статус 200, тело не пустое) за 3 с;
  2. при том же соединении `shutdown()` возвращается за 3 с;
  3. сторож: однопоточный `TCPServer` с тем же обработчиком обязан
     упереться в лимит.

  У каждого сетевого шага свой таймаут, так что тест не зависает сам.

### Прогоны

| Что | На прежней реализации (`5253e57`) | После правки |
|---|---|---|
| `python3 tools/test_check_desktop_server.py` | **exit 1**: `katalog.html` — нет ответа за 3 с (`TimeoutError`); `shutdown()` не вернулся за 3 с; сторож — ок. Тест завершился сам за 19 с | exit 0, 3/3, 8 с; `pytest` — 3 passed |
| Браузер: `repro_idle_socket.py single idle` (через `cd.serve()`) | `TimeoutError: Page.goto` | load за 1,6 с |
| `python3 tools/check_desktop.py` ×3, после `build_sitemap --write` и `build_rss --write`, как в CI | — | 3 из 3: «Десктоп (1366, 1440, 1600, 1920): 26 страниц, расхождений нет», 78–86 с. Замечания о длине `index.html` те же, что в успешном CI #298 |
| `python3 tools/run_checks.py --class public` | — | PASS 39/39 |

### Что осталось

- **`tools/check_mobile.py`** поднимал такой же однопоточный `serve()`.
  Исправлен следующим ТЗ так же: `ThreadingHTTPServer`, `daemon_threads`.
  Тест — `tools/test_check_mobile_server.py`, детектор общий с тестом
  десктопа.
  - На прежней реализации (`21625ff`) тест дал exit 1: нет ответа за 3 с,
    `shutdown()` не вернулся. Завершился сам за 13 с.
  - После правки — 2/2; вместе с тестом десктопа — 5 passed.
  - `python3 tools/check_mobile.py` ×3: «Проверено страниц: 8 на 390px
    плюс десктоп. Расхождений нет».
  - `run_checks.py --class public` — PASS 39/39.
- **Тесты не внесены в `tools/ci_checks.yaml`.** Конфигурацию CI это ТЗ
  менять запрещает. Предложение — строка класса `public`: браузер тесту не
  нужен.
- **#317.** После попадания правки в `main` ветку #298/#317 нужно обновить
  от `main`: только тогда новый `render` что-то покажет. Слепой перезапуск
  #317 не делался.

## Что с #317

- Код #317 не меняется: исправлять в нём нечего.
- Красный `render` на `4d7f2a6` остаётся красным, пока job не пройдёт
  заново. Зелёным этот CI здесь не объявляется, слепой перезапуск не
  делался.
- Перезапускать `render` у #317 или сначала внести правку выше — решение
  владельца.
