/**
 * Цели перехода: ссылка на странице против того, что считает счётчик.
 *
 * Почему проверка появилась. `check_goals.py` сверяет имена целей — код против
 * объявленного списка — и на этом останавливается: имя есть в обоих местах,
 * расхождений ноль. Чем цель вызывается и на каких ссылках она молчит, он не
 * смотрит. Замер 16.08.2026: обработчик искал подстроку '/products/' в
 * атрибуте href, а 63 ссылки на товар и 27 на бесплатный материал записаны
 * относительно — `products/p1-…`, `../materialy/…`. Подстроки в них нет.
 * Слепыми были обе точки витрины: главная (18 ссылок) и katalog.html (18).
 * Ноль product_opened в снимке 14.08 при 28 просмотрах главной из 51 читался
 * как поведение людей, а означал неподключённый прибор.
 *
 * Как устроено. Оракул здесь не повторяет логику обработчика, иначе проверка
 * доказывала бы сама себя. Ожидаемая цель берётся из файловой системы: ссылка
 * разрешается от каталога страницы, и если она приводит к файлу внутри
 * products/ — переход обязан считаться переходом на товар, как бы он ни был
 * записан в разметке. Потом тот же клик прогоняется через настоящий
 * attribution.js в песочнице, и вердикты сравниваются.
 *
 * Запуск: node tools/test_attribution_goals.js
 * Код возврата 1 — расхождение.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const ORIGIN = 'https://marzhavbetone.ru';

/* Каталоги витрины. content/ не деплоится и в счёт не идёт. */
const PAGE_DIRS = ['.', 'articles', 'materialy', 'products', 'demo'];

/* ------------------------------------------------------------------ *
 * Песочница: столько браузера, сколько нужно attribution.js, и ни на
 * строку больше. Настоящий DOM не поднимается — проверяется решение
 * обработчика, а не отрисовка.
 * ------------------------------------------------------------------ */
function loadHandlers(locationHref) {
  const url = new URL(locationHref);
  const documentListeners = [];

  const noopElement = () => ({
    className: '',
    style: {},
    textContent: '',
    innerHTML: '',
    dataset: {},
    children: [],
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {},
    getAttribute() { return null; },
    removeAttribute() {},
    appendChild() {},
    insertBefore() {},
    addEventListener() {},
    removeEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    closest() { return null; },
    contains() { return false; },
    focus() {},
    click() {},
    remove() {},
    get parentNode() { return noopElement(); }
  });

  const documentStub = {
    readyState: 'complete',
    referrer: '',
    scripts: [],
    documentElement: noopElement(),
    body: noopElement(),
    createElement: () => noopElement(),
    getElementsByTagName: () => [noopElement()],
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener(type, handler) {
      if (type === 'click') documentListeners.push(handler);
    },
    removeEventListener() {}
  };

  const storage = new Map();

  const ctx = {
    document: documentStub,
    location: {
      href: url.href,
      host: url.host,
      hostname: url.hostname,
      pathname: url.pathname,
      search: url.search,
      hash: url.hash,
      protocol: url.protocol
    },
    localStorage: {
      getItem: (k) => (storage.has(k) ? storage.get(k) : null),
      setItem: (k, v) => storage.set(k, String(v)),
      removeItem: (k) => storage.delete(k)
    },
    navigator: { userAgent: 'node' },
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    innerHeight: 800,
    innerWidth: 1366,
    scrollY: 0,
    scrollTo() {},
    addEventListener() {},
    removeEventListener() {},
    setTimeout,
    clearTimeout,
    URL,
    URLSearchParams,
    console,
    Date
  };
  ctx.window = ctx;
  ctx.self = ctx;
  ctx.globalThis = ctx;

  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'attribution.js'), 'utf8'), ctx, {
    filename: 'attribution.js'
  });

  /* Счётчик не грузится, поэтому window.ym — заглушка загрузчика Метрики.
     Цели снимаем на mvbTrackGoal: он и есть единственная точка отправки. */
  const fired = [];
  const original = ctx.mvbTrackGoal;
  ctx.mvbTrackGoal = (name) => { fired.push(name); };
  ctx.window.mvbTrackGoal = ctx.mvbTrackGoal;
  if (typeof original !== 'function') {
    throw new Error('attribution.js не объявил window.mvbTrackGoal — проверка не применима');
  }

  return { documentListeners, fired };
}

/** Клик по ссылке с заданным href. Возвращает список сработавших целей. */
function clickGoals(sandbox, href) {
  sandbox.fired.length = 0;
  const link = {
    getAttribute: (name) => (name === 'href' ? href : null),
    href
  };
  link.closest = (selector) => (selector === 'a[href]' ? link : null);
  const event = {
    target: {
      closest: (selector) => (selector === 'a[href]' ? link : null)
    }
  };
  for (const handler of sandbox.documentListeners) handler(event);
  return sandbox.fired.slice();
}

/* ------------------------------------------------------------------ *
 * Оракул: куда ссылка ведёт на самом деле — по файловой системе.
 * ------------------------------------------------------------------ */
function expectedGoal(pageFile, href) {
  if (/^(https?:|mailto:|tel:|javascript:|#|data:)/i.test(href)) return null;

  const clean = href.split('#')[0].split('?')[0];
  if (!clean) return null;

  const target = clean.startsWith('/')
    ? path.join(ROOT, clean)
    : path.resolve(path.dirname(pageFile), clean);

  if (!fs.existsSync(target)) return null;

  const rel = path.relative(ROOT, target);
  const fromArticle = path.relative(ROOT, pageFile).startsWith('articles' + path.sep);

  if (rel.startsWith('products' + path.sep)) {
    return fromArticle ? 'article_to_product' : 'product_opened';
  }
  if (rel.startsWith('materialy' + path.sep)) {
    return fromArticle ? 'article_to_magnet' : 'magnet_opened';
  }
  return null;
}

function pageUrl(pageFile) {
  const rel = path.relative(ROOT, pageFile).split(path.sep).join('/');
  return ORIGIN + '/' + rel;
}

function collectPages() {
  const pages = [];
  for (const dir of PAGE_DIRS) {
    const abs = path.join(ROOT, dir);
    if (!fs.existsSync(abs)) continue;
    for (const name of fs.readdirSync(abs)) {
      if (!name.endsWith('.html')) continue;
      pages.push(path.join(abs, name));
    }
  }
  return pages.sort();
}

/* ------------------------------------------------------------------ *
 * Прогон
 * ------------------------------------------------------------------ */
const failures = [];
let checkedLinks = 0;
let productLinks = 0;
let magnetLinks = 0;
let relativeLinks = 0;

for (const pageFile of collectPages()) {
  const html = fs.readFileSync(pageFile, 'utf8');
  const hrefs = [...html.matchAll(/href="([^"]*)"/g)].map((m) => m[1]);
  if (!hrefs.length) continue;

  const sandbox = loadHandlers(pageUrl(pageFile));

  for (const href of hrefs) {
    const expected = expectedGoal(pageFile, href);
    if (expected === null) continue;

    checkedLinks += 1;
    if (expected.includes('product')) productLinks += 1; else magnetLinks += 1;
    if (!href.startsWith('/')) relativeLinks += 1;

    const goals = clickGoals(sandbox, href);
    if (!goals.includes(expected)) {
      failures.push(
        `${path.relative(ROOT, pageFile)}: href="${href}" ведёт в ` +
        `${expected.includes('product') ? 'products/' : 'materialy/'}, ` +
        `ожидалась цель ${expected}, отправлено: ${goals.length ? goals.join(', ') : '— ничего'}`
      );
    }
  }
}

/* Отрицательные случаи: цель не должна срабатывать там, где перехода нет. */
const NEGATIVE = [
  { page: 'index.html', href: '#top', forbidden: ['product_opened', 'magnet_opened'] },
  { page: 'index.html', href: 'mailto:info@marzhavbetone.ru', forbidden: ['product_opened', 'magnet_opened'] },
  { page: 'index.html', href: 'https://example.com/products/foreign.html', forbidden: ['product_opened', 'article_to_product'] },
  { page: 'articles/raboty-ne-prinyaty.html', href: 'https://example.com/materialy/x.html', forbidden: ['magnet_opened', 'article_to_magnet'] }
];

const POSITIVE_EXTERNAL = [
  { page: 'index.html', href: 'https://dzen.ru/marzhavbetone', expected: 'dzen_click' },
  { page: 'index.html', href: 'https://dzen.ru/marzhavbetone?utm_source=site', expected: 'dzen_click' }
];

for (const testCase of NEGATIVE) {
  const pageFile = path.join(ROOT, testCase.page);
  if (!fs.existsSync(pageFile)) continue;
  const goals = clickGoals(loadHandlers(pageUrl(pageFile)), testCase.href);
  for (const forbidden of testCase.forbidden) {
    if (goals.includes(forbidden)) {
      failures.push(`${testCase.page}: href="${testCase.href}" — цель ${forbidden} не должна отправляться`);
    }
  }
}

for (const testCase of POSITIVE_EXTERNAL) {
  const pageFile = path.join(ROOT, testCase.page);
  if (!fs.existsSync(pageFile)) continue;
  const goals = clickGoals(loadHandlers(pageUrl(pageFile)), testCase.href);
  if (!goals.includes(testCase.expected)) {
    failures.push(
      `${testCase.page}: href="${testCase.href}" — ожидалась цель ${testCase.expected}, ` +
      `отправлено: ${goals.length ? goals.join(', ') : '— ничего'}`
    );
  }
}

console.log(
  `Ссылок под целью: ${checkedLinks} (товар ${productLinks}, бесплатный материал ${magnetLinks}); ` +
  `из них записаны относительно: ${relativeLinks}`
);

if (!checkedLinks) {
  console.log('Дефект: под проверку не попало ни одной ссылки — проверка ничего не доказывает.');
  process.exit(1);
}

if (failures.length) {
  console.log(`Расхождений: ${failures.length}`);
  for (const line of failures.slice(0, 40)) console.log('   • ' + line);
  if (failures.length > 40) console.log(`   … и ещё ${failures.length - 40}`);
  process.exit(1);
}

console.log('Дефектов нет: каждая ссылка на товар и на бесплатный материал считается счётчиком.');
