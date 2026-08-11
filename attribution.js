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
