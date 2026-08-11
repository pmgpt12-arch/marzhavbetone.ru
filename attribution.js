/**
 * Яндекс.Метрика.
 *
 * Стоит здесь, а не в app.js, потому что attribution.js подключён на всех
 * тридцати страницах, включая статьи без корзины — а именно статьи служат
 * точками входа по UTM-ссылкам. app.js грузят только девять страниц.
 *
 * Условие на METRIKA_ID оставлено сознательно: обнулив его, счётчик можно
 * выключить целиком одной правкой, не разбирая код. `trackGoal` в app.js
 * молчит по тому же условию.
 *
 * Настройки взяты из кода, выданного Яндексом при создании счётчика. Пиксель
 * <noscript> из того кода не переносился: он считает посетителей с
 * отключённым JavaScript, а их доля здесь неизмеримо мала — при том что
 * вставка потребовала бы правки тридцати трёх файлов и добавила бы запрос к
 * внешнему адресу на каждой странице.
 */
window.METRIKA_ID = 111149105;

if (window.METRIKA_ID) {
  (function (m, e, t, r, i, k, a) {
    m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
    m[i].l = 1 * new Date();
    for (var j = 0; j < document.scripts.length; j++) {
      if (document.scripts[j].src === r) { return; }
    }
    k = e.createElement(t); a = e.getElementsByTagName(t)[0];
    k.async = 1; k.src = r; a.parentNode.insertBefore(k, a);
  })(window, document, 'script',
     'https://mc.yandex.ru/metrika/tag.js?id=' + window.METRIKA_ID, 'ym');

  ym(window.METRIKA_ID, 'init', {
    ssr: true,
    webvisor: true,
    clickmap: true,
    ecommerce: 'dataLayer',
    referrer: document.referrer,
    url: location.href,
    accurateTrackBounce: true,
    trackLinks: true
  });
}

/**
 * Цели Метрики.
 *
 * Живут здесь, а не в app.js, по замеру 11.08.2026: `grep -l 'app-script.php'
 * articles/*.html | wc -l` → 0. Ни одна страница в articles/ не грузит app.js,
 * а именно статья служит точкой входа по UTM-ссылкам из Дзена и Телеграма.
 * Пока цели жили в app.js, переход «статья → товар» не считался нигде: 39
 * ссылок на товары и 32 врезки магнитов работали вслепую.
 *
 * app.js вызывает эту же функцию через window.mvbTrackGoal — своей копии у
 * него больше нет, иначе одно событие считалось бы дважды.
 */
window.mvbTrackGoal = function (name) {
  if (typeof window.ym === 'function' && window.METRIKA_ID) {
    window.ym(window.METRIKA_ID, 'reachGoal', name);
  }
};

(function () {
  'use strict';

  // Делегирование, а не обход ссылок при загрузке: врезки магнитов и блоки
  // товаров вставляются сборкой, и обработчик не должен зависеть от того,
  // существовал ли элемент на момент готовности документа.
  document.addEventListener('click', function (event) {
    var link = event.target.closest && event.target.closest('a[href]');
    if (!link) return;

    var href = link.getAttribute('href') || '';
    var fromArticle = /^\/articles\//.test(location.pathname);

    if (href.indexOf('/products/') !== -1) {
      window.mvbTrackGoal(fromArticle ? 'article_to_product' : 'product_opened');
    } else if (href.indexOf('/materialy/') !== -1) {
      window.mvbTrackGoal(fromArticle ? 'article_to_magnet' : 'magnet_opened');
    } else if (href.indexOf('dzen.ru') !== -1) {
      window.mvbTrackGoal('dzen_click');
    }
  });
})();

/**
 * Мобильное меню.
 *
 * Замер 11.08.2026: `grep -o 'topbar nav{display:none}' styles.css` и
 * `grep -o 'article-nav .links{display:none}' styles.css` — оба правила есть,
 * а `grep -o 'hamburger\|menu-toggle\|nav-toggle\|burger' *.css *.js` пуст.
 * До 900px навигация пряталась и ничем не заменялась: читатель, пришедший из
 * Дзена или Телеграма с телефона, не имел ни одного пути в каталог.
 *
 * Кнопка создаётся здесь, а не врезается в разметку, потому что шапок две
 * (.topbar на 26 страницах, .article-nav на 33) и любая новая страница
 * получит меню без отдельной правки. Разметку меню это не меняет: ссылки
 * остаются в HTML и видны обходчику как раньше.
 */
(function () {
  'use strict';

  function setup() {
    var header = document.querySelector('.topbar, .article-nav');
    if (!header) return;

    var menu = header.querySelector('nav[aria-label="Основная навигация"], nav.links');
    if (!menu || header.querySelector('.nav-toggle')) return;

    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'nav-toggle';
    toggle.setAttribute('aria-label', 'Меню');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.appendChild(document.createElement('span'));

    toggle.addEventListener('click', function () {
      var open = menu.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    // Закрывается по выбору пункта: на телефоне переход по якорю не
    // перезагружает страницу, и раскрытое меню осталось бы поверх текста.
    menu.addEventListener('click', function (event) {
      if (event.target.closest('a')) {
        menu.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });

    header.appendChild(toggle);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();

/**
 * Запоминает, откуда пришёл посетитель.
 *
 * Отдельный файл, а не часть app.js, по двум причинам: точками входа по
 * UTM-ссылкам служат страницы разборов, где нет корзины (и потому нет app.js),
 * а сам захват не зависит от вёрстки — значит, его можно безопасно подключить
 * на любую страницу.
 *
 * Заказ сам по себе не знает источник: метки живут в адресе страницы входа, а
 * оплата происходит на другой. Поэтому источник сохраняется здесь, а
 * app.js отправляет его вместе с заказом.
 */
(function () {
  'use strict';

  var KEY = 'marzhavbetone-attribution';
  var LIMIT = 200;

  function clip(value) {
    return String(value).slice(0, LIMIT);
  }

  function read() {
    try {
      return JSON.parse(localStorage.getItem(KEY)) || {};
    } catch (error) {
      return {};
    }
  }

  function currentTouch() {
    var params = new URLSearchParams(location.search);
    var touch = {};
    ['source', 'medium', 'campaign', 'content'].forEach(function (field) {
      var value = params.get('utm_' + field);
      if (value) touch[field] = clip(value);
    });

    if (Object.keys(touch).length) {
      touch.landing = clip(location.pathname);
      touch.at = new Date().toISOString();
      return touch;
    }

    // Без меток источник определяем по переходу — так видно органику из поиска
    if (document.referrer) {
      try {
        var host = new URL(document.referrer).hostname.replace(/^www\./, '');
        if (host && host !== location.hostname) {
          return {
            source: clip(host),
            medium: /(^|\.)(yandex|google|bing|duckduckgo|mail)\./.test(host + '.')
              ? 'organic' : 'referral',
            landing: clip(location.pathname),
            at: new Date().toISOString()
          };
        }
      } catch (error) {
        // Некорректный referrer просто игнорируем
      }
    }
    return null;
  }

  var touch = currentTouch();
  if (touch) {
    var stored = read();
    // Первое касание показывает, кто привёл; последнее — что подтолкнуло купить
    try {
      localStorage.setItem(KEY, JSON.stringify({
        first: stored.first || touch,
        last: touch
      }));
    } catch (error) {
      // Приватный режим или переполненное хранилище — просто не запоминаем
    }
  }

  // app.js берёт источник отсюда при оформлении заказа
  window.mvbAttribution = read;
})();

/* Свёртка групп каталога на телефоне и кнопка возврата наверх.
 *
 * Замер 11.08.2026 на 390px (playwright, viewport 390×844):
 *   главная      31 214px = 37 экранов, секция каталога 20 экранов из них
 *   витрина      20 638px = 24,5 экрана, 36 карточек подряд
 *
 * Группы приезжают в разметке открытыми — так страница без JS остаётся
 * ровно такой, как была. Здесь они закрываются, и только на телефоне:
 * на десктопе каталог идёт сеткой в три колонки, и прятать там нечего.
 */
(function () {
  var PHONE = 600;

  function foldGroups() {
    var groups = document.querySelectorAll('.product-group');
    if (!groups.length) return;
    var phone = window.matchMedia('(max-width:' + PHONE + 'px)').matches;
    // Первая группа остаётся открытой: свёрнутый целиком каталог не
    // показывает, что вообще внутри, и читается как пустой раздел.
    for (var i = 0; i < groups.length; i++) {
      if (phone && i > 0) groups[i].removeAttribute('open');
      if (!phone) groups[i].setAttribute('open', '');
    }
  }

  // Переход по полосе разделов открывает группу: без этого якорь ведёт
  // к закрытому заголовку, и тап выглядит как «ничего не произошло».
  function openOnJump() {
    document.addEventListener('click', function (e) {
      var link = e.target.closest && e.target.closest('.catalog-jump a');
      if (!link) return;
      var group = document.querySelector(link.getAttribute('href'));
      if (group) group.setAttribute('open', '');
    });
    if (location.hash) {
      var target = document.querySelector(location.hash);
      if (target && target.classList.contains('product-group')) {
        target.setAttribute('open', '');
      }
    }
  }

  /* Кнопка «наверх». Ставится только там, где страница длиннее четырёх
   * экранов: на короткой она мешает, а не помогает. Порог взят от замера —
   * четыре экрана это уже больше, чем помещается в память о том, откуда
   * начал листать. */
  function backToTop() {
    if (document.querySelector('.to-top')) return;
    if (document.documentElement.scrollHeight < window.innerHeight * 4) return;
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'to-top';
    button.setAttribute('aria-label', 'Наверх');
    button.textContent = '↑';
    button.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    document.body.appendChild(button);
    var show = function () {
      button.classList.toggle('is-visible', window.scrollY > window.innerHeight * 2);
    };
    window.addEventListener('scroll', show, { passive: true });
    show();
  }

  function setup() {
    foldGroups();
    openOnJump();
    backToTop();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
  window.addEventListener('resize', foldGroups);
})();

/* Фильтр тем и показ по частям на витрине разборов.
 *
 * Замер 11.08.2026 на 390px: `articles/index.html` — 20 638px, 24,5
 * экрана, 36 карточек подряд. Чтобы понять, есть ли на сайте разбор про
 * удержания, надо было пролистать всю ленту и запомнить, что видел.
 *
 * Разметка приезжает со всеми карточками: без JS витрина остаётся такой
 * же, как была, — полной лентой, а не пустой страницей. Здесь добавляются
 * отбор по теме и порция показа.
 */
(function () {
  var STEP = 9;              // порция показа: три экрана телефона
  var shown = STEP;
  var active = '';

  var grid = document.querySelector('.showcase-grid');
  var bar = document.querySelector('.topic-filter');
  if (!grid || !bar) return;

  var cards = [].slice.call(grid.querySelectorAll('.showcase-card'));
  var more = document.createElement('button');
  more.type = 'button';
  more.className = 'showcase-more';

  function render() {
    var matched = 0;
    for (var i = 0; i < cards.length; i++) {
      var fits = !active || cards[i].getAttribute('data-cluster') === active;
      var visible = fits && matched < shown;
      if (fits) matched++;
      cards[i].hidden = !visible;
    }
    var left = matched - shown;
    more.hidden = left <= 0;
    more.textContent = 'Показать ещё ' + (left > STEP ? STEP : left);
  }

  more.addEventListener('click', function () {
    shown += STEP;
    render();
  });

  bar.addEventListener('click', function (e) {
    var button = e.target.closest && e.target.closest('button[data-cluster]');
    if (!button) return;
    active = button.getAttribute('data-cluster');
    // Порция считается заново от выбранной темы: иначе после «показать
    // ещё» на «Всех» узкая тема открывалась бы сразу целиком, и кнопка
    // переставала значить одно и то же.
    shown = STEP;
    for (var i = 0; i < bar.children.length; i++) {
      bar.children[i].classList.toggle('is-active', bar.children[i] === button);
    }
    render();
    grid.scrollIntoView({ block: 'start', behavior: 'smooth' });
  });

  grid.parentNode.insertBefore(more, grid.nextSibling);
  render();
})();
