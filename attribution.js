/**
 * Яндекс.Метрика.
 *
 * Стоит здесь, а не в app.js, потому что attribution.js подключён на всех
 * тридцати страницах, включая статьи без корзины — а именно статьи служат
 * точками входа по UTM-ссылкам. app.js грузят только девять страниц.
 *
 * Пока номер счётчика равен нулю, ничего не происходит: скрипт не грузится,
 * а `trackGoal` в app.js молчит по своему же условию на window.METRIKA_ID.
 * Так эта правка безопасна до того, как счётчик заведён.
 */
window.METRIKA_ID = 0;   // ← сюда номер счётчика из metrika.yandex.ru

if (window.METRIKA_ID) {
  (function (m, e, t, r, i, k, a) {
    m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
    m[i].l = 1 * new Date();
    for (var j = 0; j < document.scripts.length; j++) {
      if (document.scripts[j].src === r) { return; }
    }
    k = e.createElement(t); a = e.getElementsByTagName(t)[0];
    k.async = 1; k.src = r; a.parentNode.insertBefore(k, a);
  })(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym');

  ym(window.METRIKA_ID, 'init', {
    webvisor: true,
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    ecommerce: 'dataLayer'
  });
}

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
