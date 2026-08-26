/**
 * События браузера: приёмка F-05b.
 *
 * ЧТО ПРОВЕРЯЕТСЯ. session_started ровно один раз на посещение,
 * content_viewed на каждой странице, и — главное — что ни один отказ
 * доставки не мешает странице работать.
 *
 * ОТКУДА БЕРЁТСЯ БОЛЬ. Ниоткуда: браузер её не выводит. Он сообщает то, что
 * знает из адреса, — ключ материала или артикул товара, — а сопоставление
 * боли делает Control Plane, у которого канон и лежит. Ручной таблицы
 * «адрес → боль» в JS нет и не заводится.
 *
 * Запуск: node tools/test_browser_events.js
 */

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const ИСТОЧНИК = fs.readFileSync(path.join(ROOT, 'attribution.js'), 'utf8');

let провалов = 0;
function проверка(имя, тело) {
  try { тело(); console.log('  ok   ' + имя); }
  catch (о) { провалов += 1; console.log('  FAIL ' + имя + '\n         ' + о.message); }
}
function равно(п, о, ч) {
  if (п !== о) throw new Error((ч || '') + ': ожидалось ' + JSON.stringify(о) +
                               ', получено ' + JSON.stringify(п));
}
function истинно(з, ч) { if (!з) throw new Error(ч || 'ожидалось истинное'); }

function песочница(опции) {
  const н = опции || {};
  const jar = н.jar || new Map();
  const session = н.session || new Map();
  const отправленные = [];
  const формы = н.формы || [];

  const узел = () => new Proxy({}, {
    get(_ц, имя) {
      if (['scrollHeight', 'clientHeight', 'offsetHeight', 'scrollTop'].includes(имя)) return 0;
      if (['style', 'classList', 'dataset', 'parentNode'].includes(имя)) return узел();
      if (имя === Symbol.toPrimitive || имя === 'toString') return () => '';
      return () => узел();
    },
    set() { return true; }
  });

  const адрес = new URL(н.url || 'https://marzhavbetone.ru/');
  const documentStub = {
    readyState: 'complete', referrer: н.referrer || '', scripts: [],
    documentElement: узел(), body: узел(),
    createElement: (тег) => (тег === 'input'
      ? { tagName: 'INPUT', type: '', name: '', value: '', setAttribute() {} }
      : узел()),
    getElementsByTagName: () => [узел()],
    querySelector: () => null,
    querySelectorAll: (селектор) => (String(селектор).includes('form') ? формы : []),
    addEventListener() {}, removeEventListener() {},
    get cookie() {
      if (н.cookieBroken) throw new Error('cookie запрещены');
      return Array.from(jar.entries()).map(([к, з]) => к + '=' + з).join('; ');
    },
    set cookie(строка) {
      if (н.cookieBroken) throw new Error('cookie запрещены');
      const [пара] = String(строка).split(';');
      const з = пара.indexOf('=');
      jar.set(пара.slice(0, з).trim(), пара.slice(з + 1).trim());
    }
  };

  const ctx = {
    document: documentStub,
    location: { href: адрес.href, host: адрес.host, hostname: адрес.hostname,
                pathname: адрес.pathname, search: адрес.search, hash: адрес.hash,
                protocol: адрес.protocol },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    sessionStorage: {
      getItem: (k) => (session.has(k) ? session.get(k) : null),
      setItem: (k, v) => session.set(k, String(v)),
      removeItem: (k) => session.delete(k)
    },
    navigator: {
      userAgent: 'node',
      sendBeacon: н.beaconBroken
        ? () => { throw new Error('sendBeacon недоступен'); }
        : (н.noBeacon ? undefined : (адр, тело) => {
            отправленные.push({ how: 'beacon', url: адр, body: String(тело && тело.__text || тело) });
            return н.beaconRefuses ? false : true;
          })
    },
    fetch: н.fetchBroken
      ? () => { throw new Error('fetch сломан'); }
      : (адр, опц) => {
          отправленные.push({ how: 'fetch', url: адр, body: (опц || {}).body });
          return н.fetchRejects
            ? Promise.reject(new Error('сеть недоступна'))
            : Promise.resolve({ ok: true, status: 204 });
        },
    Blob: function (части, опции) {
      this.__text = (части || []).join('');
      this.type = (опции || {}).type || '';
    },
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    innerHeight: 800, innerWidth: 1366, scrollY: 0,
    scrollTo() {}, addEventListener() {}, removeEventListener() {},
    setTimeout, clearTimeout, URL, URLSearchParams, console, Date, JSON, Object,
    crypto: { randomUUID: () => require('crypto').randomUUID(),
              getRandomValues: (м) => require('crypto').randomFillSync(м) }
  };
  ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(ИСТОЧНИК, ctx, { filename: 'attribution.js' });
  return { ctx, jar, session, отправленные };
}

function события(песок) {
  return песок.отправленные
    .filter((з) => String(з.url).indexOf('/event.php') >= 0)
    .map((з) => { try { return JSON.parse(з.body); } catch (о) { return { сырое: з.body }; } });
}

console.log('события браузера');

проверка('test_session_started_once_per_session', () => {
  const session = new Map(), jar = new Map();
  const первая = песочница({ jar, session, url: 'https://marzhavbetone.ru/' });
  const начала = события(первая).filter((с) => с.event_type === 'funnel.session_started');
  равно(начала.length, 1, 'session_started на первой странице');

  // Вторая страница ТОЙ ЖЕ сессии: начало сессии повторяться не должно.
  const вторая = песочница({ jar, session,
    url: 'https://marzhavbetone.ru/materialy/dengi.html' });
  равно(события(вторая).filter((с) => с.event_type === 'funnel.session_started').length,
        0, 'session_started повторился внутри сессии');
});

проверка('test_session_started_again_in_new_session', () => {
  const jar = new Map();
  const первая = песочница({ jar, session: new Map() });
  const вторая = песочница({ jar, session: new Map() });
  равно(события(первая).filter((с) => с.event_type === 'funnel.session_started').length, 1, 'первая');
  равно(события(вторая).filter((с) => с.event_type === 'funnel.session_started').length, 1, 'вторая');
});

проверка('test_content_viewed_emitted', () => {
  const песок = песочница({ url: 'https://marzhavbetone.ru/materialy/dengi.html' });
  const просмотры = события(песок).filter((с) => с.event_type === 'funnel.content_viewed');
  равно(просмотры.length, 1, 'content_viewed');
  равно(просмотры[0].content_id, '/materialy/dengi.html', 'content_id');
  равно(просмотры[0].magnet_id, 'dengi', 'ключ материала из адреса');
  истинно(просмотры[0].anonymous_id, 'нет anonymous_id');
  истинно(просмотры[0].session_id, 'нет session_id');
});

проверка('test_content_viewed_carries_sku_on_product_page', () => {
  const песок = песочница({
    url: 'https://marzhavbetone.ru/products/t1-pervyy-shag-pri-neoplate.html' });
  const п = события(песок).filter((с) => с.event_type === 'funnel.content_viewed')[0];
  равно(п.sku, 't1', 'артикул из адреса');
  истинно(!('magnet_id' in п), 'на странице товара проставлен ключ материала');
});

проверка('test_browser_does_not_invent_pain', () => {
  /* Браузер боли не знает и знать не должен: сопоставление живёт в каноне.
     Ручная таблица «адрес → боль» в JS — четвёртая таксономия. */
  const песок = песочница({ url: 'https://marzhavbetone.ru/materialy/dengi.html' });
  for (const с of события(песок)) {
    истинно(!('pain_id' in с), 'браузер прислал pain_id: ' + JSON.stringify(с));
  }
  истинно(!/pain_id/.test(ИСТОЧНИК.replace(/\/\*[\s\S]*?\*\//g, '')),
          'в attribution.js упоминается pain_id вне комментариев');
});

проверка('test_events_carry_no_pii', () => {
  const песок = песочница({ url: 'https://marzhavbetone.ru/materialy/dengi.html' });
  const текст = JSON.stringify(события(песок));
  истинно(!/@/.test(текст), 'в событиях есть @');
  for (const поле of ['email', 'phone', 'name', 'contact']) {
    истинно(текст.indexOf('"' + поле + '"') < 0, 'поле ' + поле + ' в событии');
  }
});

проверка('test_beacon_failure_does_not_break_navigation', () => {
  let песок;
  try { песок = песочница({ beaconBroken: true }); }
  catch (о) { throw new Error('страница упала при сломанном sendBeacon: ' + о.message); }
  истинно(typeof песок.ctx.window.mvbAnonymousId === 'function', 'страница жива');
  истинно(typeof песок.ctx.window.mvbAttribution === 'function', 'атрибуция жива');
});

проверка('test_offline_receiver_does_not_break_page', () => {
  // sendBeacon отвечает false (браузер офлайн), fetch отвергается.
  const песок = песочница({ beaconRefuses: true, fetchRejects: true });
  истинно(typeof песок.ctx.window.mvbAnonymousId === 'function', 'страница жива');
});

проверка('test_no_beacon_falls_back_without_throwing', () => {
  const песок = песочница({ noBeacon: true, url: 'https://marzhavbetone.ru/' });
  истинно(typeof песок.ctx.window.mvbAnonymousId === 'function', 'страница жива');
  // Запасной путь есть: событие ушло хоть чем-то.
  истинно(события(песок).length > 0, 'без sendBeacon не ушло ничего');
});

проверка('test_everything_broken_still_leaves_page_usable', () => {
  const песок = песочница({ cookieBroken: true, beaconBroken: true,
                            fetchBroken: true });
  истинно(typeof песок.ctx.window.mvbAnonymousId === 'function', 'страница жива');
  равно(песок.ctx.window.mvbAnonymousId(), null, 'при запрещённых cookie — null');
});

проверка('test_lead_form_gets_anonymous_id', () => {
  /* Форма материала уходит FormData, и anonymous_id обязан в неё попасть —
     иначе lead.php не свяжет выдачу с посетителем. */
  const поля = [];
  const форма = {
    action: 'https://marzhavbetone.ru/lead.php',
    getAttribute: () => '../lead.php',
    appendChild: (узел) => поля.push(узел),
    querySelector: () => null
  };
  const песок = песочница({ формы: [форма],
    url: 'https://marzhavbetone.ru/materialy/dengi.html' });
  const анон = поля.filter((п) => п && п.name === 'anonymous_id');
  равно(анон.length, 1, 'скрытое поле anonymous_id в форме');
  равно(анон[0].value, песок.ctx.window.mvbAnonymousId(), 'значение anonymous_id');

  // Посещение тоже: без него выдача не встаёт в ту же сессию, что просмотр.
  const сессия = поля.filter((п) => п && п.name === 'session_id');
  равно(сессия.length, 1, 'скрытое поле session_id в форме');
  равно(сессия[0].value, песок.ctx.window.mvbSessionId(), 'значение session_id');
});

console.log('');
if (провалов) { console.log('провалов: ' + провалов); process.exit(1); }
console.log('все проверки пройдены');
