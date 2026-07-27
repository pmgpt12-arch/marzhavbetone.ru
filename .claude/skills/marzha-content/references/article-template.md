# Скелет страницы разбора

Структура не косметика: от метатегов зависят превью в соцсетях и сниппет в
поиске, а от `datePublished` и обложки — соберётся ли фид Дзена. Генератор
фида (`tools/build_rss.py`) останавливает деплой, если чего-то не хватает.

Проще всего скопировать существующий разбор близкой темы и заменить
содержимое — так гарантированно не потеряются мелочи. Хороший образец:
`articles/vsyo-vklyucheno-v-cenu.html`.

## Обязательный минимум

| Элемент | Зачем |
|---|---|
| `<meta name="description">` | сниппет в поиске |
| `<meta name="keywords">` | поисковые запросы темы |
| `og:title`, `og:description`, `og:image`, `og:type=article`, `og:url` | превью при пересылке; `og:title` и `og:image` читает генератор фида |
| `<link rel="canonical">` | защита от дублей |
| JSON-LD `Article` с `datePublished` и `dateModified` | **без `datePublished` фид не собирается** |
| JSON-LD `BreadcrumbList` | навигационный сниппет |
| `<p class="eyebrow">` | рубрика; попадает в `category` фида |
| `<img class="article-cover">` | обложка ≥ 480×320, иначе деплой упадёт |
| `<p class="lead">` | первый абзац с конкретной ситуацией |

Подключаемые стили: `../styles.css` и `../article.css`.

## Каркас

```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="…">
  <meta name="keywords" content="…">
  <meta property="og:title" content="Заголовок — Маржа в бетоне">
  <meta property="og:description" content="…">
  <meta property="og:image" content="https://marzhavbetone.ru/assets/<slug>.png">
  <meta property="og:type" content="article">
  <meta property="og:url" content="https://marzhavbetone.ru/articles/<slug>.html">
  <meta name="twitter:card" content="summary_large_image">
  <title>Заголовок — Маржа в бетоне</title>
  <link rel="canonical" href="https://marzhavbetone.ru/articles/<slug>.html">
  <link rel="stylesheet" href="../styles.css">
  <link rel="stylesheet" href="../article.css">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Article",
        "@id": "https://marzhavbetone.ru/articles/<slug>.html#article",
        "headline": "Заголовок",
        "description": "…",
        "image": "https://marzhavbetone.ru/assets/<slug>.png",
        "author": {"@type": "Person", "name": "Александр Сергеев", "url": "https://marzhavbetone.ru/#author"},
        "publisher": {"@id": "https://marzhavbetone.ru/#organization"},
        "datePublished": "ГГГГ-ММ-ДД",
        "dateModified": "ГГГГ-ММ-ДД",
        "mainEntityOfPage": {"@type": "WebPage", "@id": "https://marzhavbetone.ru/articles/<slug>.html"}
      },
      {
        "@type": "BreadcrumbList",
        "itemListElement": [
          {"@type": "ListItem", "position": 1, "name": "Главная", "item": "https://marzhavbetone.ru/"},
          {"@type": "ListItem", "position": 2, "name": "Разборы", "item": "https://marzhavbetone.ru/articles/"},
          {"@type": "ListItem", "position": 3, "name": "Короткое имя темы", "item": "https://marzhavbetone.ru/articles/<slug>.html"}
        ]
      }
    ]
  }
  </script>
</head>
<body>
  <header class="article-nav">
    <a class="brand" href="/"><span class="brand-mark">М</span><span>маржа в бетоне</span></a>
    <nav class="links">
      <a href="/articles/">Все разборы</a>
      <a href="/package.html">Пакет</a>
      <a href="https://t.me/marzhavbetone">Telegram</a>
    </nav>
    <a class="button button-small" href="/#contact">Разобрать объект</a>
  </header>

  <main class="section article-page">
    <nav aria-label="Хлебные крошки" class="breadcrumbs">
      <ol>
        <li><a href="/">Главная</a></li>
        <li><a href="/articles/">Разборы</a></li>
        <li aria-current="page">Короткое имя темы</li>
      </ol>
    </nav>

    <p class="eyebrow">РУБРИКА / УТОЧНЕНИЕ</p>
    <h1>Заголовок</h1>
    <img class="article-cover" src="../assets/<slug>.png" alt="Обложка: …">

    <p class="lead">Конкретная ситуация потери денег.</p>

    <h2>…</h2>
    <p>…</p>

    <table>
      <tr><th>…</th><th>…</th></tr>
      <tr><td>…</td><td>…</td></tr>
    </table>

    <h2>Что делать</h2>
    <ol>
      <li><strong>…</strong> …</li>
    </ol>

    <!-- CTA-блоки: сначала бесплатный, затем платный -->
    <div class="article-cta" style="margin:60px 0;padding:40px;background:#f5f2ea;border-radius:8px;">
      <p class="eyebrow">БЕСПЛАТНО</p>
      <h3>Название лид-магнита</h3>
      <p>Что внутри и чем поможет по теме этой статьи.</p>
      <a class="button" href="/index.html#checklist">Скачать бесплатно →</a>
    </div>

    <div class="article-cta" style="margin:40px 0;padding:40px;background:var(--ink);color:var(--paper);border-radius:8px;">
      <p class="eyebrow" style="color:var(--orange);">ПЛАТНЫЙ КОМПЛЕКТ</p>
      <h3 style="color:#fff;">Название комплекта</h3>
      <p style="color:#bbb;">Состав комплекта. 10 файлов.</p>
      <p style="font-size:28px;font-weight:900;color:var(--orange);">19 900 ₽</p>
      <a class="button" href="/products/pN-….html">Купить комплект →</a>
    </div>

    <section class="article-links" style="margin-top:40px;">
      <h2>Читайте также</h2>
      <ul>
        <li><a href="/articles/….html">…</a></li>
      </ul>
    </section>

    <section class="channel-banner" style="margin-top:60px;">
      <div><small>TELEGRAM / БЕЗ ОФИЦИОЗА</small><h2>Новые разборы — в канале</h2></div>
      <a class="button" href="https://t.me/marzhavbetone">Перейти в Telegram →</a>
    </section>
  </main>
</body>
</html>
```

## Что генератор фида выбрасывает из текста

В `content:encoded` попадают только `p`, `h2`, `h3`, `ul`, `ol`, `blockquote`.
Навигация, хлебные крошки, `eyebrow`, CTA-блоки и «Читайте также» отрезаются.
Поэтому **таблицы в фид не попадают** — если ключевая мысль живёт только в
таблице, продублируй её абзацем, иначе читатель Дзена её не увидит.

## Карточка в списке разборов

В `articles/index.html`, в начало `showcase-grid`:

```html
      <a class="showcase-card" href="<slug>.html">
        <img src="../assets/<slug>.png" alt="Короткое описание">
        <div><small>РУБРИКА</small><h2>Заголовок</h2><p>Одно предложение — за чем идти в материал.</p></div>
      </a>
```

И позиция в `ItemList` того же файла. При вставке в начало сдвинь нумерацию
остальных позиций — иначе в разметке будут два элемента с `position: 1`.

## Запись в sitemap.xml

```xml
  <url><loc>https://marzhavbetone.ru/articles/<slug>.html</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>
```

## Переносы строк

Файлы сайта используют CRLF. Читай и пиши их как байты, сохраняя переносы:
переключение на LF даёт дифф на весь файл, в котором не видно смысловых
правок.
