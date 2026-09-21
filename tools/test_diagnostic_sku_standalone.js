/**
 * Диагностика: ступень и комплект — два самостоятельных товара, показанные
 * как параллельные варианты по ситуации, а не последовательность покупки.
 *
 * Решение владельца MB007 (после MB005/MB006): в сценариях S-0/S-1 пара
 * t1+p1 остаётся, но пользовательская семантика «entry → core», «сначала
 * меньший продукт → потом больший» снята. Выбор — по ситуации и объёму
 * задачи, не по цене и не по порядку покупки.
 *
 * Проверяется не отсутствие отдельных слов, а смысловой инвариант на
 * НАСТОЯЩЕМ рендере страницы: сценарий с парой обязан показать оба товара
 * одновременно, каждый — отдельным законченным предложением, открытым
 * собственным условием («Если …»), и условия этих двух предложений
 * различны. Вернуть чтение «сначала ступень — потом комплект» нельзя, не
 * сломав одно из этих свойств: слияние предложений, общий код условия
 * или выпавший вариант краснят прогон.
 *
 * Рендер не пересобирается по образцу: страница прогоняется как есть —
 * её inline-скрипт исполняется в песочнице, разметка вопросов берётся из
 * самой страницы, сценарий доводится кликами до вердикта, и инвариант
 * проверяется на том HTML, который получит пользователь.
 *
 * Цена пары сверяется с products-config.php: витрина и сервер обязаны
 * называть одно число.
 *
 * Запуск: node tools/test_diagnostic_sku_standalone.js
 */

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const СТРАНИЦА = fs.readFileSync(path.join(ROOT, 'diagnostika.html'), 'utf8');
const КОНФИГ = fs.readFileSync(path.join(ROOT, 'products-config.php'), 'utf8');

let провалов = 0;
let пройдено = 0;
function проверка(имя, тело) {
  try { тело(); пройдено += 1; console.log('  ok   ' + имя); }
  catch (о) { провалов += 1; console.log('  FAIL ' + имя + '\n         ' + о.message); }
}
function равно(п, о, ч) {
  if (п !== о) throw new Error((ч || '') + ': ожидалось ' + JSON.stringify(о) +
                               ', получено ' + JSON.stringify(п));
}

// ---------------------------------------------------------------- разметка

function сценарии() {
  const m = СТРАНИЦА.match(/const SCENARIOS = (\[.*?\]);/s);
  if (!m) throw new Error('на странице не найден const SCENARIOS');
  return JSON.parse(m[1]);
}

function вопросы() {
  /** Вопросы страницы: data-q → список data-a, из её же разметки. */
  const форма = СТРАНИЦА.match(/<form id="dform">([\s\S]*?)<\/form>/);
  if (!форма) throw new Error('на странице не найдена форма вопросов');
  const out = [];
  const re = /<fieldset class="dq" data-q="([^"]+)">([\s\S]*?)<\/fieldset>/g;
  let m;
  while ((m = re.exec(форма[1]))) {
    const ответы = [...m[2].matchAll(/data-a="([^"]+)"/g)].map(x => x[1]);
    if (!ответы.length) throw new Error('у вопроса ' + m[1] + ' нет вариантов ответа');
    out.push({ q: m[1], ответы });
  }
  return out;
}

function цена_из_конфига(sku) {
  const блок = КОНФИГ.slice(КОНФИГ.indexOf('function mvb_products()'));
  const m = блок.match(new RegExp(
    "'" + sku + "'\\s*=>\\s*\\[\\s*\\n\\s*'name'\\s*=>\\s*'[^']*',\\s*\\n\\s*'price'\\s*=>\\s*(\\d+)"));
  if (!m) throw new Error(sku + ' не найден в products-config.php');
  return parseInt(m[1], 10) / 100;   // в конфиге — копейки, на витрине — рубли
}

function sku_из_адреса(url) {
  const m = url.match(/\/products\/([a-z]\d+)-/);
  if (!m) throw new Error('адрес без sku: ' + url);
  return m[1];
}

// ---------------------------------------------------------------- рендер

/**
 * Прогоняет страницу как есть: собирает песочницу из её же разметки,
 * отвечает на вопросы заданного сценария кликами по его обработчику и
 * возвращает HTML блока результата, который увидит пользователь.
 */
function отрендерить(сценарий) {
  const список = вопросы();
  const коробки = список.map(({ q, ответы }) => {
    const box = { dataset: { q }, hidden: false };
    box.querySelectorAll = (sel) => (sel === 'button[data-a]')
      ? ответы.map(a => кнопка(a, box)) : [];
    return box;
  });
  function кнопка(a, box) {
    const b = { dataset: { a }, setAttribute() {} };
    b.closest = (sel) => sel === 'button[data-a]' ? b
      : (sel === '.dq' ? box : null);
    return b;
  }

  const out = { innerHTML: '', hidden: false, scrollIntoView() {} };
  const элементы = {
    dform: {
      hidden: false,
      querySelectorAll: (sel) => (sel === '.dq') ? коробки.slice() : [],
      addEventListener(тип, fn) { if (тип === 'click') клики.push(fn); },
    },
    dresult: out,
    dcard: { hidden: false },
    dback: { hidden: false, addEventListener() {} },
    'dstep-label': { textContent: '' },
    dbar: { style: {} },
  };
  const клики = [];
  const документ = {
    getElementById(id) {
      return элементы[id] || { addEventListener() {} };   // dagain создаётся рендером
    },
  };

  const script = СТРАНИЦА.match(/<script>\n([\s\S]*?)\n  <\/script>/s);
  if (!script || !script[1].includes('const SCENARIOS')) {
    throw new Error('inline-скрипт со сценариями не найден');
  }
  const ctx = vm.createContext({ document: документ, window: {} });
  vm.runInContext(script[1], ctx);

  // Ответы кликаются в порядке страницы; значения — как их хранит сценарий.
  const ответ = (v) => (v === true ? 'yes' : v === false ? 'no' : v);
  for (const box of коробки) {
    if (!(box.dataset.q in сценарий.when)) continue;
    const a = ответ(сценарий.when[box.dataset.q]);
    const btn = box.querySelectorAll('button[data-a]').find(b => b.dataset.a === a);
    if (!btn) throw new Error('у вопроса ' + box.dataset.q + ' нет варианта ' + a);
    for (const fn of клики) fn({ target: btn });
  }
  if (!out.innerHTML) throw new Error('сценарий ' + сценарий.id + ' не дал вердикта');
  return out.innerHTML;
}

/** Абзацы блока результата: [текст до первой ссылки, полный HTML]. */
function абзацы(блок) {
  return [...блок.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/g)].map(m => m[1]);
}
function до_ссылки(p) {
  return p.split('<a ')[0].replace(/<[^>]+>/g, '').trim();
}

// ---------------------------------------------------------------- проверки

const СЦЕНАРИИ = сценарии();

проверка('цены пары на странице совпадают с products-config.php', () => {
  const беды = [];
  for (const s of СЦЕНАРИИ) {
    for (const роль of ['entry', 'core']) {
      const узел = s[роль];
      if (!узел) continue;
      const sku = sku_из_адреса(узел.url);
      const конфиг = цена_из_конфига(sku);
      if (узел.price !== конфиг) {
        беды.push(s.id + ' ' + роль + ' (' + sku + '): на странице ' +
                  узел.price + ' ₽, в конфиге ' + конфиг + ' ₽');
      }
    }
  }
  if (беды.length) throw new Error('\n         ' + беды.join('\n         '));
});

проверка('сценарий с парой показывает оба товара одновременно', () => {
  const беды = [];
  for (const s of СЦЕНАРИИ) {
    let блок;
    try { блок = отрендерить(s); }
    catch (о) { беды.push(s.id + ': рендер упал — ' + о.message); continue; }
    const с_ступенью = Boolean(s.entry);
    const есть_ступень = с_ступенью && s.entry.url && блок.includes(s.entry.url);
    const есть_комплект = блок.includes(s.core.url);
    if (с_ступенью && !есть_ступень) беды.push(s.id + ': ступень не показана вместе с комплектом');
    if (!есть_комплект) беды.push(s.id + ': комплект не показан');
    if (!с_ступенью && блок.includes('/products/t')) {
      // Сценарий без ступени не должен приобретать её молча.
      беды.push(s.id + ': у сценария без ступени появилась ссылка на ступень');
    }
  }
  if (беды.length) throw new Error('\n         ' + беды.join('\n         '));
});

проверка('оба варианта открыты собственным условием, условия различны', () => {
  const беды = [];
  for (const s of СЦЕНАРИИ) {
    if (!s.entry) continue;
    const ps = абзацы(отрендерить(s));
    const iСтуп = ps.findIndex(p => p.includes(s.entry.url));
    const iКомпл = ps.findIndex(p => p.includes(s.core.url));
    if (iСтуп < 0 || iКомпл < 0) { беды.push(s.id + ': вариант не найден в абзацах'); continue; }
    if (iСтуп === iКомпл) {
      беды.push(s.id + ': ступень и комплект слились в один абзац');
      continue;
    }
    const услСтуп = до_ссылки(ps[iСтуп]);
    // У ведущего абзаца комплекта условие стоит текстом перед кнопкой.
    const ведущий = iКомпл > 0 ? до_ссылки(ps[iКомпл - 1]) : '';
    const услКомпл = ведущий.endsWith(':') ? ведущий : до_ссылки(ps[iКомпл]);
    if (!/^Если/.test(услСтуп)) беды.push(s.id + ': выбор ступени не открыт условием («' + услСтуп + '»)');
    if (!/^Если/.test(услКомпл)) беды.push(s.id + ': выбор комплекта не открыт условием («' + услКомпл + '»)');
    if (услСтуп === услКомпл) беды.push(s.id + ': у обоих вариантов одно условие — варианта по ситуации нет');
    if (ps[iСтуп].includes(s.core.url)) беды.push(s.id + ': в предложении ступени затесалась ссылка на комплект');
    if (ps[iКомпл].includes(s.entry.url)) беды.push(s.id + ': в предложении комплекта затесалась ссылка на ступень');
  }
  if (беды.length) throw new Error('\n         ' + беды.join('\n         '));
});

проверка('пара S-0/S-1 ведёт t1 и p1 — состав не изменился', () => {
  for (const id of ['S-0', 'S-1']) {
    const s = СЦЕНАРИИ.find(x => x.id === id);
    if (!s) throw new Error(id + ' пропал из сценарииев');
    равно(sku_из_адреса(s.entry.url), 't1', id + ' entry');
    равно(sku_из_адреса(s.core.url), 'p1', id + ' core');
  }
});

console.log('\nПроверок ' + (пройдено + провалов) +
            ', упало ' + провалов + '.');
process.exit(провалов ? 1 : 0);
