# P1: узкая правка первого блока страницы

Проверка actual base `0e6290d98a37e75917794403bf732662db3eb227`, isolated worktree `/home/denis/projects/marzhavbetone.ru/.worktrees/codex-p1-hero-layout-20261008`, branch `codex/p1-hero-layout-20261008`.

До правки ошибка GitHubRenderCI воспроизведена: `.product-fit` bottom1185,296875 при1366×768, допустимый округлённый bottom≤1152. Правка затрагивает только P1desktop≥1100: явный класс на main,20px между lead/hero и14px перед/внутри product-fit. Кегль, текст, цена, SKU, пороги и тесты не изменены. Queryhash product.css обновлён только на P1.

| Viewport | Fit before→after | Button after | Результат |
|---|---|---|---|
|1366×768 |1185,30→1145,30 |544,88 |PASS, предел1152 |
|1440×900 |1190,08→1150,08 |548,38 |PASS, предел1350 |
|1600×900 |1192,84→1152,84 |548,38 |PASS, предел1350 |
|1920×1080 |1264,56→1224,56 |548,38 |PASS, предел1620 |
|390×844 |2170,89→2170,89 |853,63→853,63 |Без изменения: screenshot byte-identical |

Объём проверок: настоящий cachedChromium1234 (`Chrome/151.0.7922.34`) через Node22 native CDP; импортированы неизменные JS-проверки OVERFLOW/ORPHAN/WORDBREAK/REALBREAK/CARDBOX из существующего tools/check_desktop.py. Тот же смысл/селекторы/rounding first_screen для fit/buy/price. На всех5 viewport эти проверки и горизонтальное переполнение пусты; first_screen пороги применены к четырём desktop viewport, как в существующей проверке. Для390 подтверждены та же геометрия и побайтно идентичный PNG. Полный26-страничный прогон не заявлен; корзина/PHP не проверялись этой единицей.

Playwright в окружении отсутствовал; два ограниченных ожиданием подхода установки не завершили download пакета. Дополнительные browser binaries не устанавливались. Для рендера использован существующий Chromium и native CDP, без обхода порогов.

Скриншоты после правки1366 и390 фактически просмотрены: текст читается, строки не обрезаны, отступы не сливают блоки. Root независимо просмотрел точный diff двух файлов, comparison receipt и PNG1366/390 и принял правку до commit. По его поручению закоммичены patch и этот узкий report/JSON; push этой единицей не выполнен.

Два dirty файла: product.css SHA `820ffea43d9773492a6e568e105963b4c2cfbbbb6fe769a95946cc79f0ee3e99`; products/p1-oplata-po-ks2.html SHA `385937fc93dfe15c36f8a98d3fcf4a865fd0eefc9e3cef87f78a016235cf1489`. git diff --check rc0. Visible body text SHA совпал до/после на каждом viewport.

Серверные доказательства: `/tmp/p1-hero-layout-qa/before-receipt.json`, `after-receipt.json`, `comparison-receipt.json`; patch `/tmp/p1-hero-layout-qa/p1-first-screen.patch`; screenshots `before/after-{1366,1440,1600,1920,390}.png`; harness `targeted_cdp.js`, неизменные импортированные проверки `checks.json`. Первый пробный after дал1153px из-за схлопывания отступа hero с прежним lead28px; сохранён как attempt1, затем исправлен lead и фактически выполнен новый проход всех5 viewport.
