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

    // Адрес приводится к абсолютному, а не сверяется подстрокой в атрибуте.
    //
    // Замер 16.08.2026: `grep -ohE 'href="(\.\./)?products/[^"]*"'` по всем
    // страницам сайта — 63 ссылки на товар и 27 на бесплатный материал
    // записаны относительно (`products/p1-…`, `../materialy/…`), и подстроки
    // '/products/' в них нет. Слепыми оказались обе точки витрины: главная
    // (18 ссылок) и katalog.html (18) — то есть весь путь «каталог → товар».
    // Ноль product_opened в снимке 14.08 при 28 просмотрах главной из 51
    // означает «прибор не подключён», а не «никто не дошёл».
    //
    // Сверка по хосту, а не по подстроке 'dzen.ru', закрывает вторую
    // сторону: внешний адрес с /products/ в пути больше не считается
    // открытием своего товара.
    var url;
    try {
      url = new URL(link.getAttribute('href') || '', location.href);
    } catch (error) {
      return;
    }

    if (url.host !== location.host) {
      if (url.hostname === 'dzen.ru' || /\.dzen\.ru$/.test(url.hostname)) {
        window.mvbTrackGoal('dzen_click');
      }
      return;
    }

    var fromArticle = /^\/articles\//.test(location.pathname);

    if (url.pathname.indexOf('/products/') === 0) {
      window.mvbTrackGoal(fromArticle ? 'article_to_product' : 'product_opened');
    } else if (url.pathname.indexOf('/materialy/') === 0) {
      window.mvbTrackGoal(fromArticle ? 'article_to_magnet' : 'magnet_opened');
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
/* Устойчивый анонимный идентификатор посетителя и идентификатор посещения.
 *
 * ЗАЧЕМ. Метки источника этот файл собирает давно, и они доезжают до заказа.
 * Чего не было — ключа, по которому событие связывается с событием: путь
 * одного человека от ролика до покупки не склеивался ничем. Здесь этот ключ.
 *
 * ЧТО ЭТО НЕ ЕСТЬ. Не идентификация человека: случайные 128 бит, ни одного
 * его признака. Почты, телефона и имени здесь нет и быть не может.
 *
 * ДВА ИДЕНТИФИКАТОРА, А НЕ ОДИН. `mvb_aid` живёт год и означает браузер;
 * идентификатор посещения живёт в sessionStorage и означает один заход.
 * Один ключ на оба смысла отвечал бы на два разных вопроса одним числом —
 * «сколько людей» и «сколько заходов» перестали бы различаться.
 *
 * ГЛАВНОЕ: НИЧЕГО НЕ ЛОМАТЬ. Приватный режим, запрещённые cookie,
 * переполненное хранилище, отсутствие window.crypto — каждый из случаев
 * оставляет страницу работающей. Наблюдаемость не становится условием
 * работы сайта: обращение к cookie обёрнуто целиком, а не «на всякий
 * случай», и при отказе функция отдаёт null, а не бросает.
 */
(function () {
  'use strict';

  var COOKIE = 'mvb_aid';
  var SESSION_KEY = 'mvb_sid';
  var ГОД = 365 * 24 * 60 * 60;

  /* UUIDv4. randomUUID есть не везде, getRandomValues — почти везде;
     Math.random остаётся последним рубежом и назван так прямо: он не
     криптографический, и на нём идентификатор всё же лучше, чем никакой. */
  function uuid4() {
    try {
      if (window.crypto && typeof window.crypto.randomUUID === 'function') {
        return window.crypto.randomUUID();
      }
      if (window.crypto && typeof window.crypto.getRandomValues === 'function') {
        var байты = new Uint8Array(16);
        window.crypto.getRandomValues(байты);
        байты[6] = (байты[6] & 0x0f) | 0x40;
        байты[8] = (байты[8] & 0x3f) | 0x80;
        var hex = [];
        for (var i = 0; i < 16; i++) hex.push((байты[i] + 0x100).toString(16).slice(1));
        return hex.slice(0, 4).join('') + '-' + hex.slice(4, 6).join('') + '-'
             + hex.slice(6, 8).join('') + '-' + hex.slice(8, 10).join('') + '-'
             + hex.slice(10, 16).join('');
      }
    } catch (error) {
      /* Ниже запасной путь */
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      return (c === 'x' ? r : ((r & 0x3) | 0x8)).toString(16);
    });
  }

  function читатьCookie(имя) {
    try {
      var строки = String(document.cookie || '').split(';');
      for (var i = 0; i < строки.length; i++) {
        var пара = строки[i];
        var знак = пара.indexOf('=');
        if (знак < 0) continue;
        if (пара.slice(0, знак).trim() === имя) return пара.slice(знак + 1).trim();
      }
    } catch (error) {
      /* Приватный режим: чтение cookie бросает — это не наша беда */
    }
    return null;
  }

  function писатьCookie(имя, значение) {
    try {
      var защита = location.protocol === 'https:' ? '; Secure' : '';
      document.cookie = имя + '=' + значение + '; Max-Age=' + ГОД
        + '; Path=/; SameSite=Lax' + защита;
      return true;
    } catch (error) {
      return false;
    }
  }

  var анонимный = null;
  try {
    анонимный = читатьCookie(COOKIE);
    if (!анонимный) {
      var свежий = uuid4();
      анонимный = писатьCookie(COOKIE, свежий) ? свежий : null;
      /* Записали и тут же перечитали: браузер мог cookie отвергнуть молча,
         и тогда «идентификатор есть» было бы неправдой. */
      if (анонимный && читатьCookie(COOKIE) !== свежий) анонимный = null;
    }
  } catch (error) {
    анонимный = null;
  }

  var посещение = null;
  try {
    посещение = window.sessionStorage.getItem(SESSION_KEY);
    if (!посещение) {
      посещение = uuid4();
      window.sessionStorage.setItem(SESSION_KEY, посещение);
    }
  } catch (error) {
    /* Хранилище недоступно — идентификатор посещения живёт в памяти
       страницы. Для одного перехода этого достаточно, для отчёта — нет,
       и «нет» здесь честнее выдуманной устойчивости. */
    посещение = посещение || uuid4();
  }

  /* Возвращает null, когда устойчивого идентификатора нет. Выдуманное
     значение выглядело бы измерением, не будучи им. */
  window.mvbAnonymousId = function () { return анонимный; };
  window.mvbSessionId = function () { return посещение; };
})();

/* События воронки: начало посещения и просмотр страницы.
 *
 * КУДА ШЛЁМ. На свой домен, /event.php. Приёмник Control Plane закрыт
 * токеном, а класть токен в браузерный JS нельзя — его прочтёт любой.
 * Посредник на своём домене решает это и заодно снимает CORS.
 *
 * БОЛЬ ЗДЕСЬ НЕ ВЫВОДИТСЯ. Браузер сообщает только то, что видно из адреса:
 * ключ материала или артикул товара. Сопоставить их боли — дело Control
 * Plane, у которого канон и лежит. Таблица «адрес → боль» в JS была бы
 * четвёртой таксономией, ради устранения которой всё это и затевалось.
 *
 * НИЧЕГО НЕ ЖДЁМ И НИЧЕГО НЕ ЛОМАЕМ. sendBeacon по устройству не задерживает
 * переход; там, где его нет, fetch с keepalive и молча проглоченным отказом.
 * Любая поломка — отсутствующий sendBeacon, брошенное исключение, отвергнутый
 * промис, офлайн — оставляет страницу работающей. Проверяется отдельными
 * случаями в tools/test_browser_events.js.
 */
(function () {
  'use strict';

  var АДРЕС = '/event.php';
  var НАЧАЛО = 'mvb_session_started';

  function послать(тип, поля) {
    try {
      var тело = { event_type: тип };
      тело.anonymous_id = window.mvbAnonymousId ? window.mvbAnonymousId() : null;
      тело.session_id = window.mvbSessionId ? window.mvbSessionId() : null;
      var метки = window.mvbAttribution ? window.mvbAttribution() : null;
      if (метки && метки.last) {
        тело.utm = {
          source: метки.last.source, medium: метки.last.medium,
          campaign: метки.last.campaign, content: метки.last.content
        };
        if (метки.last.source) тело.source = метки.last.source;
      }
      for (var ключ in поля) {
        if (Object.prototype.hasOwnProperty.call(поля, ключ)) тело[ключ] = поля[ключ];
      }
      var текст = JSON.stringify(тело);

      if (typeof navigator.sendBeacon === 'function') {
        var кусок = new Blob([текст], { type: 'application/json' });
        if (navigator.sendBeacon(АДРЕС, кусок)) return;
        /* false означает «браузер не взял» — например офлайн. Падать
           обратно на fetch незачем: он тоже не уйдёт. */
        return;
      }
      if (typeof fetch === 'function') {
        var обещание = fetch(АДРЕС, {
          method: 'POST', body: текст, keepalive: true,
          headers: { 'Content-Type': 'application/json' }
        });
        if (обещание && typeof обещание.catch === 'function') {
          обещание.catch(function () { /* отказ доставки — не наша беда */ });
        }
      }
    } catch (error) {
      /* Наблюдаемость не имеет права ломать страницу. Тишина намеренна. */
    }
  }

  /* Что видно из адреса. Ключ материала — имя страницы в /materialy/,
     артикул — первый кусок имени в /products/. Это соглашение о путях, а
     не таблица: незнакомое значение отвергнет приёмник по канону. */
  function изАдреса() {
    var поля = { content_id: location.pathname };
    var материал = location.pathname.match(/^\/materialy\/([a-z0-9-]+)\.html$/);
    if (материал) { поля.magnet_id = материал[1]; return поля; }
    var товар = location.pathname.match(/^\/products\/((?:p|t)\d+)-[a-z0-9-]+\.html$/);
    if (товар) { поля.sku = товар[1]; }
    return поля;
  }

  try {
    var новая = false;
    try {
      if (!window.sessionStorage.getItem(НАЧАЛО)) {
        window.sessionStorage.setItem(НАЧАЛО, '1');
        новая = true;
      }
    } catch (error) {
      /* Хранилище недоступно: начало посещения не отмечается, и повторов
         мы не увидим. Считать каждую страницу новой сессией хуже —
         это врёт числом, а не молчит. */
    }
    if (новая) послать('funnel.session_started', {});
    послать('funnel.content_viewed', изАдреса());
  } catch (error) {
    /* см. выше */
  }

  /* Форма материала уходит FormData, собранной из полей формы. Скрытое поле
     кладётся в разметку заранее — тогда его подберёт любой обработчик
     отправки, и править app.js не нужно. Без него lead.php не свяжет
     выдачу с посетителем. */
  try {
    var свои = {
      anonymous_id: window.mvbAnonymousId ? window.mvbAnonymousId() : null,
      session_id: window.mvbSessionId ? window.mvbSessionId() : null
    };
    if (свои.anonymous_id || свои.session_id) {
      var формы = document.querySelectorAll('form[action]') || [];
      for (var i = 0; i < формы.length; i++) {
        var форма = формы[i];
        var куда = String(форма.getAttribute('action') || '');
        if (куда.indexOf('lead.php') < 0) continue;
        for (var имя in свои) {
          if (!Object.prototype.hasOwnProperty.call(свои, имя)) continue;
          if (!свои[имя]) continue;
          if (форма.querySelector('input[name="' + имя + '"]')) continue;
          var поле = document.createElement('input');
          поле.type = 'hidden';
          поле.name = имя;
          поле.value = свои[имя];
          форма.appendChild(поле);
        }
      }
    }
  } catch (error) {
    /* Нет формы, нет DOM, нет идентификатора — страница всё равно жива. */
  }
})();

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
  // Переход по допродаже считается отдельно от обычного открытия товара:
  // product_opened не отличает его от клика по любой другой ссылке, а
  // именно этот переход показывает, работает ли блок «если ваша ситуация
  // также включает».
  document.addEventListener('click', function (event) {
    if (!event.target.closest) return;
    if (event.target.closest('.cross-sell a[href]')) {
      window.mvbTrackGoal('cross_sell_click');
    }
  });

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

/* Бесплатные материалы на телефоне — порцией, а не десятью карточками
 * подряд. Замер 11.08.2026: десять одинаковых по виду карточек занимали
 * около 5 000px, то есть шесть экранов, и стояли между каталогом и
 * остальной страницей.
 *
 * Прячем только на телефоне и только сверх трёх: на десктопе они идут
 * сеткой в три колонки и в порции не нуждаются. Разметка приезжает
 * полной — без JS всё видно, как сегодня.
 */
(function () {
  var STEP = 3;
  var cards = [].slice.call(
    document.querySelectorAll('#catalog .product-card.free'));
  if (cards.length <= STEP) return;

  var grid = cards[0].parentNode;
  var more = document.createElement('button');
  more.type = 'button';
  more.className = 'showcase-more free-more';
  grid.parentNode.insertBefore(more, grid.nextSibling);

  var shown = STEP;

  function render() {
    var phone = window.matchMedia('(max-width:600px)').matches;
    for (var i = 0; i < cards.length; i++) {
      cards[i].hidden = phone && i >= shown;
    }
    var left = cards.length - shown;
    more.hidden = !phone || left <= 0;
    more.textContent = 'Показать ещё ' + left + ' из ' + cards.length;
  }

  more.addEventListener('click', function () {
    shown = cards.length;
    render();
  });
  window.addEventListener('resize', render);
  render();
})();
