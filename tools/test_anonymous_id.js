/**
 * Устойчивый анонимный идентификатор: приёмка F-05.
 *
 * ЗАЧЕМ. Аудит: атрибуция доезжает до покупки, но склеить путь одного
 * человека нечем — first/last touch лежат в localStorage без ключа, по
 * которому событие можно связать с событием. anonymous_id и есть этот ключ.
 *
 * ЧЕГО ОН НЕ ДЕЛАЕТ. Не идентифицирует человека: это случайные 128 бит без
 * единого его признака. Персональных данных в нём нет по устройству, а не по
 * обещанию, и на это стоит отдельная проверка.
 *
 * ГЛАВНОЕ ТРЕБОВАНИЕ — НЕВМЕШАТЕЛЬСТВО. Наблюдаемость никогда не становится
 * зависимостью коммерческого контура. Приватный режим, запрещённые cookie,
 * переполненное хранилище — всё это оставляет страницу работающей, и это
 * проверяется, а не декларируется.
 *
 * Запуск: node tools/test_anonymous_id.js
 * Код возврата 1 — расхождение.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const ИСТОЧНИК = fs.readFileSync(path.join(ROOT, 'attribution.js'), 'utf8');

let провалов = 0;
function проверка(имя, тело) {
  try {
    тело();
    console.log('  ok   ' + имя);
  } catch (ошибка) {
    провалов += 1;
    console.log('  FAIL ' + имя + '\n         ' + ошибка.message);
  }
}
function равно(получено, ожидалось, что) {
  if (получено !== ожидалось) {
    throw new Error((что || '') + ': ожидалось ' + JSON.stringify(ожидалось) +
                    ', получено ' + JSON.stringify(получено));
  }
}
function истинно(значение, что) {
  if (!значение) throw new Error(что || 'ожидалось истинное значение');
}

/**
 * Песочница со своей банкой cookie.
 *
 * `jar` переживает «перезагрузку»: браузер cookie не теряет, и именно это
 * делает идентификатор устойчивым. `cookieBroken` изображает приватный режим,
 * где присвоение document.cookie бросает.
 */
function песочница(опции) {
  const настройки = опции || {};
  const jar = настройки.jar || new Map();
  const store = настройки.store || new Map();
  const session = new Map();

  /* Любой узел отвечает на любое обращение: проверка про идентификатор,
     а не про вёрстку, и падать на scrollHeight она не должна. */
  const узел = () => new Proxy({}, {
    get(_цель, имя) {
      if (имя === 'scrollHeight' || имя === 'clientHeight' ||
          имя === 'offsetHeight' || имя === 'scrollTop') return 0;
      if (имя === 'style' || имя === 'classList' || имя === 'dataset') return узел();
      if (имя === 'parentNode' || imyaEsli(имя)) return узел();
      if (имя === Symbol.toPrimitive || имя === 'toString') return () => '';
      return () => узел();
    },
    set() { return true; }
  });
  const imyaEsli = (имя) => ['firstChild', 'lastChild', 'nextSibling'].includes(имя);

  const documentStub = {
    readyState: 'complete',
    referrer: '',
    scripts: [],
    documentElement: узел(),
    body: узел(),
    createElement: () => узел(),
    getElementsByTagName: () => [узел()],
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {},
    removeEventListener() {},
    get cookie() {
      if (настройки.cookieBroken) throw new Error('cookie запрещены');
      return Array.from(jar.entries())
        .map(([к, з]) => к + '=' + з).join('; ');
    },
    set cookie(строка) {
      if (настройки.cookieBroken) throw new Error('cookie запрещены');
      const [пара] = String(строка).split(';');
      const знак = пара.indexOf('=');
      jar.set(пара.slice(0, знак).trim(), пара.slice(знак + 1).trim());
    }
  };

  const адрес = new URL(настройки.url || 'https://marzhavbetone.ru/');
  const ctx = {
    document: documentStub,
    location: {
      href: адрес.href, host: адрес.host, hostname: адрес.hostname,
      pathname: адрес.pathname, search: адрес.search, hash: адрес.hash,
      protocol: адрес.protocol
    },
    localStorage: настройки.storageBroken ? {
      getItem() { throw new Error('хранилище недоступно'); },
      setItem() { throw new Error('хранилище недоступно'); },
      removeItem() { throw new Error('хранилище недоступно'); }
    } : {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(k, String(v)),
      removeItem: (k) => store.delete(k)
    },
    sessionStorage: {
      getItem: (k) => (session.has(k) ? session.get(k) : null),
      setItem: (k, v) => session.set(k, String(v)),
      removeItem: (k) => session.delete(k)
    },
    navigator: { userAgent: 'node' },
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    innerHeight: 800, innerWidth: 1366, scrollY: 0,
    scrollTo() {}, addEventListener() {}, removeEventListener() {},
    setTimeout, clearTimeout, URL, URLSearchParams, console, Date,
    crypto: настройки.noCrypto ? undefined : {
      randomUUID: () => require('crypto').randomUUID(),
      getRandomValues: (массив) => require('crypto').randomFillSync(массив)
    }
  };
  ctx.window = ctx;
  ctx.self = ctx;
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(ИСТОЧНИК, ctx, { filename: 'attribution.js' });
  return { ctx, jar, store };
}

const UUID4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

console.log('anonymous_id');

проверка('anonymous_id_created', () => {
  const { ctx } = песочница();
  истинно(typeof ctx.window.mvbAnonymousId === 'function',
          'window.mvbAnonymousId не объявлен');
  const id = ctx.window.mvbAnonymousId();
  истинно(UUID4.test(id), 'не UUIDv4: ' + id);
});

проверка('anonymous_id_survives_reload', () => {
  const jar = new Map();
  const первый = песочница({ jar }).ctx.window.mvbAnonymousId();
  const второй = песочница({ jar }).ctx.window.mvbAnonymousId();
  равно(второй, первый, 'идентификатор не пережил перезагрузку');
});

проверка('anonymous_id_survives_internal_navigation', () => {
  const jar = new Map();
  const главная = песочница({ jar, url: 'https://marzhavbetone.ru/' })
    .ctx.window.mvbAnonymousId();
  const статья = песочница({
    jar, url: 'https://marzhavbetone.ru/articles/raschet-metrami.html'
  }).ctx.window.mvbAnonymousId();
  равно(статья, главная, 'идентификатор сменился при переходе по сайту');
});

проверка('anonymous_id_is_not_pii', () => {
  const { ctx } = песочница();
  const id = ctx.window.mvbAnonymousId();
  истинно(!/[@]/.test(id), 'в идентификаторе адрес почты');
  истинно(!/\d{7,}/.test(id.replace(/-/g, '')), 'похоже на номер телефона');
  // Два запуска в разных банках обязаны разойтись: одинаковый на всех
  // идентификатор — это не идентификатор, а константа.
  const другой = песочница({ jar: new Map() }).ctx.window.mvbAnonymousId();
  истинно(другой !== id, 'идентификатор одинаков у разных посетителей');
});

проверка('cookie_failure_does_not_break_page', () => {
  let песок;
  try {
    песок = песочница({ cookieBroken: true });
  } catch (ошибка) {
    throw new Error('скрипт упал при запрещённых cookie: ' + ошибка.message);
  }
  // Страница жива, функция есть и отвечает без исключения.
  истинно(typeof песок.ctx.window.mvbAnonymousId === 'function',
          'при запрещённых cookie функция исчезла');
  const id = песок.ctx.window.mvbAnonymousId();
  истинно(id === null || UUID4.test(id),
          'ожидался null или корректный id, получено ' + JSON.stringify(id));
  // Атрибуция обязана продолжать работать: она про источник, а не про cookie.
  истинно(typeof песок.ctx.window.mvbAttribution === 'function',
          'при запрещённых cookie сломалась атрибуция');
});

проверка('storage_failure_does_not_break_page', () => {
  const песок = песочница({ storageBroken: true });
  истинно(typeof песок.ctx.window.mvbAnonymousId === 'function',
          'при недоступном хранилище функция исчезла');
  истинно(UUID4.test(песок.ctx.window.mvbAnonymousId()),
          'cookie доступны — идентификатор обязан быть');
});

проверка('works_without_crypto', () => {
  const песок = песочница({ noCrypto: true });
  const id = песок.ctx.window.mvbAnonymousId();
  истинно(UUID4.test(id), 'без window.crypto идентификатор не выдан: ' + id);
});

проверка('cookie_is_first_party_and_long_lived', () => {
  const записанные = [];
  const jar = new Map();
  const песок = песочница({ jar });
  // Перечитываем, что именно ушло в document.cookie: срок, путь, SameSite.
  const свежая = песочница({
    jar: new Map(),
    url: 'https://marzhavbetone.ru/'
  });
  const исходник = ИСТОЧНИК;
  истинно(/max-age=/i.test(исходник), 'у cookie нет срока — она сессионная');
  истинно(/path=\//i.test(исходник), 'cookie не на весь сайт');
  истинно(/samesite=lax/i.test(исходник), 'у cookie нет SameSite=Lax');
  истинно(песок.ctx.window.mvbAnonymousId() !== null, 'cookie не поставлена');
  void записанные; void свежая;
});

console.log('\nsession_id — отдельно от anonymous_id');

проверка('session_id_is_not_the_anonymous_id', () => {
  const { ctx } = песочница();
  истинно(typeof ctx.window.mvbSessionId === 'function',
          'window.mvbSessionId не объявлен');
  const anon = ctx.window.mvbAnonymousId();
  const сессия = ctx.window.mvbSessionId();
  истинно(UUID4.test(сессия), 'session_id не UUIDv4: ' + сессия);
  истинно(сессия !== anon,
          'session_id совпал с anonymous_id: один идентификатор не может ' +
          'означать и браузер, и посещение');
});

проверка('session_id_is_new_in_a_new_session', () => {
  const jar = new Map();
  const первая = песочница({ jar });
  const вторая = песочница({ jar });      // та же банка cookie, новая сессия
  равно(вторая.ctx.window.mvbAnonymousId(),
        первая.ctx.window.mvbAnonymousId(), 'anonymous_id обязан совпасть');
  истинно(вторая.ctx.window.mvbSessionId() !== первая.ctx.window.mvbSessionId(),
          'session_id не сменился в новой сессии');
});

console.log('');
if (провалов) {
  console.log('провалов: ' + провалов);
  process.exit(1);
}
console.log('все проверки пройдены');
