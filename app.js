const dialog = document.querySelector('#checklist-dialog');
const openChecklist = document.querySelector('#open-checklist');
const closeChecklist = document.querySelector('#close-checklist');
if (dialog && openChecklist && closeChecklist) {
  openChecklist.addEventListener('click', () => dialog.showModal());
  closeChecklist.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });
}

const form = document.querySelector('#contact-form');
const formStatus = document.querySelector('#form-status');
// Реализация переехала в attribution.js: он подключён на всех страницах, а
// app.js — только на двадцати пяти, и статей среди них нет. Здесь остался
// вызов, чтобы места вызова целей ниже не переписывать. Запасная ветка нужна
// на случай, если attribution.js не загрузился: тогда цель просто не уйдёт.
function trackGoal(name) {
  if (typeof window.mvbTrackGoal === 'function') window.mvbTrackGoal(name);
}
// Клик по ссылке на Дзен считает attribution.js делегированием — здесь
// обработчика больше нет, иначе одно событие уходило бы дважды.

// ===================== КОРЗИНА =====================
const cartPanel = document.querySelector('#cart-panel');
const cartBackdrop = document.querySelector('#cart-backdrop');
const cartItems = document.querySelector('#cart-items');
const cartEmpty = document.querySelector('#cart-empty');
const cartTotal = document.querySelector('#cart-total');
const cartCount = document.querySelector('#cart-count');
const cartCheckout = document.querySelector('#cart-checkout');
let cart = [];
try { cart = JSON.parse(localStorage.getItem('marzhavbetone-cart') || '[]'); } catch (_) { cart = []; }

function money(value) { return new Intl.NumberFormat('ru-RU').format(value / 100) + '\u00a0₽'; }
function saveCart() { localStorage.setItem('marzhavbetone-cart', JSON.stringify(cart)); }
function openCart() {
  cartPanel.hidden = false;
  cartBackdrop.hidden = false;
  if (cartToggle) cartToggle.setAttribute('aria-expanded', 'true');
}
function closeCart() {
  cartPanel.hidden = true;
  cartBackdrop.hidden = true;
  if (cartToggle) cartToggle.setAttribute('aria-expanded', 'false');
}
function renderCart() {
  cartItems.replaceChildren();
  cart.forEach(item => {
    const row = document.createElement('li'); row.className = 'cart-item';
    const name = document.createElement('strong'); name.textContent = item.name;
    const price = document.createElement('span'); price.className = 'cart-item-price'; price.textContent = money(item.price);
    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'cart-remove'; remove.textContent = 'Удалить';
    remove.addEventListener('click', () => { cart = cart.filter(product => product.name !== item.name); saveCart(); renderCart(); });
    row.append(name, price, remove); cartItems.append(row);
  });
  const total = cart.reduce((sum, item) => sum + item.price, 0);
  cartCount.textContent = String(cart.length);
  cartTotal.textContent = money(total);
  cartEmpty.hidden = cart.length > 0;
  cartCheckout.disabled = cart.length === 0;
  document.querySelectorAll('.add-to-cart').forEach(button => {
    const added = cart.some(item => item.name === button.dataset.product);
    button.classList.toggle('added', added);
    button.textContent = added ? 'В корзине' : 'Добавить в корзину';
  });
}

// Разметки корзины нет на страницах лид-магнитов: там нечего покупать.
// Без этой проверки первое же обращение к отсутствующей кнопке роняло весь
// файл — вместе с ним не навешивался обработчик формы ниже, форма уходила
// обычным POST, и человек, оставивший контакт, видел сырой JSON вместо
// ссылки на файл. Цель checklist_download при этом не срабатывала никогда.
const cartToggle = document.querySelector('#cart-toggle');
const cartClose = document.querySelector('#cart-close');
if (cartToggle) cartToggle.addEventListener('click', openCart);
if (cartClose) cartClose.addEventListener('click', closeCart);
if (cartBackdrop) cartBackdrop.addEventListener('click', closeCart);
document.querySelectorAll('.add-to-cart').forEach(button => button.addEventListener('click', () => {
  if (!cart.some(item => item.name === button.dataset.product)) cart.push({ sku: button.dataset.sku || '', name: button.dataset.product, price: Number(button.dataset.price) });
  saveCart(); renderCart(); openCart();
  trackGoal('add_to_cart');
}));

// ===================== ОПЛАТА ЧЕРЕЗ ЮКАССА =====================
// Native modal semantics keep focus inside checkout and restore its opener.
let checkoutOpener = null;
function createCheckoutModal() {
  if (document.getElementById('checkout-modal')) return;
  const modal = document.createElement('dialog');
  modal.id = 'checkout-modal';
  modal.setAttribute('aria-labelledby', 'checkout-title');
  modal.innerHTML = `
    <div class="checkout-panel">
      <div class="checkout-head"><h2 id="checkout-title">Оформление заказа</h2><button type="button" class="checkout-close" aria-label="Закрыть оформление">×</button></div>
      <div class="checkout-body">
        <div id="checkout-items"></div><div class="checkout-total" id="checkout-total"></div>
        <form id="checkout-form">
          <label class="checkout-field"><span>Email для получения документов</span><input type="email" name="email" autocomplete="email" placeholder="your@email.com" required autofocus></label>
          <fieldset class="checkout-optional"><legend>Дополнительный контакт · необязательно</legend><p>Удобный способ связаться с вами по заказу.</p><label class="checkout-field"><span>Telegram или телефон</span><input type="text" name="phone" maxlength="120" placeholder="@username или +7 900 000-00-00"></label></fieldset>
          <label class="checkout-consent"><input type="checkbox" name="consent" value="yes" required><span>Принимаю <a href="/offer.html" target="_blank" rel="noopener">условия оферты</a> и соглашаюсь с <a href="/privacy.html" target="_blank" rel="noopener">обработкой персональных данных</a>.</span></label>
          <button type="submit" class="button checkout-submit">Перейти к оплате</button>
          <p class="checkout-fine">Оплата на защищённой странице ЮKassa.</p><p id="checkout-error" class="checkout-error" role="alert"></p>
        </form>
      </div>
      <div class="checkout-loading" id="checkout-loading" hidden><div class="spinner" aria-hidden="true"></div><p role="status">Создаём платёж…</p></div>
    </div>`;
  document.body.appendChild(modal);
  const style = document.createElement('style');
  style.textContent = `
    #checkout-modal{position:fixed;inset:0;margin:auto;padding:0;border:0;border-radius:12px;width:min(540px,calc(100vw - 32px));max-width:none;max-height:calc(100dvh - 32px);height:fit-content;overflow:auto;background:#fff;color:#24292f;box-shadow:0 24px 80px #0004}
    #checkout-modal:not([open]){display:none}#checkout-modal::backdrop{background:#24292fb3}
    #checkout-modal *{box-sizing:border-box}.checkout-panel{position:relative;padding:clamp(20px,4vw,28px);min-width:0}
    .checkout-head{display:flex;gap:16px;justify-content:space-between;align-items:flex-start;margin-bottom:16px}.checkout-head h2{margin:0;font-size:22px;line-height:1.25}.checkout-close{flex:0 0 40px;width:40px;height:40px;border:0;background:none;font-size:32px;line-height:1;cursor:pointer;color:#4b535b}
    .checkout-item{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;padding:10px 0;border-bottom:1px solid #ddd;font-size:15px}.checkout-item strong{font-weight:600;overflow-wrap:anywhere}.checkout-item>span,.checkout-total>span:last-child{white-space:nowrap}
    .checkout-total{display:flex;justify-content:space-between;gap:16px;padding:16px 0;margin-bottom:12px;font-size:18px;font-weight:700;border-top:2px solid #24292f}
    #checkout-modal .checkout-field{display:block;margin:0 0 16px;font-size:14px}#checkout-modal .checkout-field>span{display:block;margin-bottom:6px;font-weight:600}#checkout-modal .checkout-field input{display:block;width:100%;min-width:0;padding:12px 14px;border:1px solid #8b9196;border-radius:6px;background:#fff;color:#24292f;font:inherit;font-size:16px}
    #checkout-modal input:focus-visible,#checkout-modal button:focus-visible,#checkout-modal a:focus-visible{outline:3px solid #806238;outline-offset:3px}
    .checkout-optional{min-width:0;margin:0 0 20px;padding:14px;border:1px solid #d4d5d5;border-radius:6px}.checkout-optional legend{padding:0 5px;font-size:14px;font-weight:600}.checkout-optional p{margin:0 0 12px;color:#4b535b;font-size:13px;line-height:1.45}.checkout-optional .checkout-field:last-child{margin-bottom:0!important}
    #checkout-modal .checkout-consent{display:grid;grid-template-columns:20px minmax(0,1fr);align-items:start;gap:10px;margin:0 0 20px;font-size:14px;font-weight:400;line-height:1.5;color:#4b535b}
    #checkout-modal .checkout-consent>input{width:20px;height:20px;min-width:20px;margin:1px 0 0}#checkout-modal .checkout-consent>span{display:block;min-width:0}#checkout-modal .checkout-consent a{display:inline;text-decoration:underline;color:#24292f}
    .checkout-submit{width:100%;padding:14px;font-size:16px}.checkout-fine{margin:12px 0 0;font-size:13px;color:#4b535b;text-align:center}.checkout-error{color:#a51c1c;font-size:14px;margin:10px 0 0;text-align:center}
    .checkout-loading[hidden]{display:none}.checkout-loading{position:absolute;inset:0;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:12px}.checkout-loading .spinner{width:40px;height:40px;border:3px solid #ddd;border-top-color:#24292f;border-radius:50%;animation:spin 1s linear infinite;margin-bottom:16px}@keyframes spin{to{transform:rotate(360deg)}}`;
  document.head.appendChild(style);
  modal.querySelector('.checkout-close').addEventListener('click', () => modal.close());
  modal.addEventListener('click', event => { if (event.target === modal) modal.close(); });
  modal.addEventListener('close', () => { if (checkoutOpener?.isConnected) checkoutOpener.focus(); });
  modal.addEventListener('keydown', event => {
    if(event.key!=='Tab') return;
    const focusable=[...modal.querySelectorAll('a[href],button,input')].filter(el=>!el.disabled&&el.getClientRects().length);
    const first=focusable[0],last=focusable[focusable.length-1];
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  });
  modal.querySelector('#checkout-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form=event.target, errorEl=modal.querySelector('#checkout-error'), loadingEl=modal.querySelector('#checkout-loading'), submitBtn=form.querySelector('.checkout-submit');
    if (!form.reportValidity() || cart.length===0) return;
    errorEl.textContent=''; submitBtn.disabled=true; loadingEl.hidden=false;
    const data={items:cart,email:form.elements.email.value.trim(),phone:form.elements.phone.value.trim(),attribution:typeof window.mvbAttribution==='function'?window.mvbAttribution():{}};
    try {
      const res=await fetch('/payment.php',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
      const text=await res.text(); let result;
      try { result=JSON.parse(text); } catch { throw new Error('Сервер вернул ошибку (код '+res.status+'). Повторите попытку позднее или напишите нам в Telegram.'); }
      if(result.ok&&result.payment_url) window.location.href=result.payment_url;
      else throw new Error(result.message||'Не удалось создать платёж');
    } catch(error) { errorEl.textContent=error.message; submitBtn.disabled=false; loadingEl.hidden=true; }
  });
}
function openCheckout() {
  if(cart.length===0) return;
  trackGoal('checkout_open'); createCheckoutModal();
  const modal=document.getElementById('checkout-modal'), itemsEl=modal.querySelector('#checkout-items'), totalEl=modal.querySelector('#checkout-total');
  checkoutOpener=document.activeElement;
  itemsEl.replaceChildren();
  cart.forEach(item=>{const row=document.createElement('div'), name=document.createElement('strong'), price=document.createElement('span');row.className='checkout-item';name.textContent=item.name;price.textContent=money(item.price);row.append(name,price);itemsEl.append(row);});
  totalEl.replaceChildren();const label=document.createElement('span'),value=document.createElement('span');label.textContent='Итого';value.textContent=money(cart.reduce((sum,item)=>sum+item.price,0));totalEl.append(label,value);
  if(!modal.open) modal.showModal();
  modal.querySelector('input[name=email]').focus();
}

if (cartCheckout) cartCheckout.addEventListener('click', openCheckout);

// ===================== СТАРАЯ ЛОГИКА (оставлена для совместимости) =====================
// Проверка на существование корзины обязательна: страницы лид-магнитов и
// статьи её не содержат, и обращение к null здесь роняло весь остаток
// файла — включая обработчик формы бесплатного материала ниже. Форма
// уходила обычным POST, браузер показывал JSON вместо кнопки скачивания,
// а цель checklist_download не срабатывала никогда.
if (cartCheckout) {
  cartCheckout.addEventListener('click', () => {
    // Если корзина пуста — ничего не делаем
    if (cart.length === 0) return;
  });
}

if (cartItems && cartCount && cartTotal && cartEmpty && cartCheckout) renderCart();

document.querySelectorAll('.product-select').forEach(link => link.addEventListener('click', () => {
  document.querySelector('#product').value = link.dataset.product;
  const selectedProduct = document.querySelector('#selected-product');
  selectedProduct.textContent = `Вы выбрали: ${link.dataset.product}`;
  selectedProduct.hidden = false;
  trackGoal('product_selected');
}));

if (form) {
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    formStatus.textContent = 'Отправляем…';
    try {
      const response = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.message || 'Не удалось отправить обращение');
      const selectedProduct = document.querySelector('#product').value;
      form.reset();
      document.querySelector('#product').value = selectedProduct;
      formStatus.textContent = 'Обращение отправлено. Свяжемся с вами по указанному контакту.';
      formStatus.className = 'form-status success';
      trackGoal('lead_sent');
    } catch (error) {
      formStatus.textContent = `${error.message}. Напишите напрямую: nastoronepodryadchika@yandex.ru`;
      formStatus.className = 'form-status error';
    } finally { button.disabled = false; }
  });
}

const leadForm = document.querySelector('#lead-form');
const leadStatus = document.querySelector('#lead-status');
if (leadForm) {
  leadForm.addEventListener('submit', async event => {
    event.preventDefault();
    const button = leadForm.querySelector('button');
    button.disabled = true;
    leadStatus.textContent = 'Готовим ссылку…';
    try {
      const response = await fetch(leadForm.action, { method: 'POST', body: new FormData(leadForm), headers: { Accept: 'application/json' } });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.message || 'Не удалось получить чек-лист');
      // Второй строкой — один ненавязчивый переход по этой же ситуации.
      // Адрес объявлен на самой форме (data-continue) и собирается из
      // страницы набора: своей таблицы соответствий здесь не заводится.
      // Ровно один переход, а не три: экран выдачи — не витрина.
      const дальше = leadForm.dataset.continue;
      const продолжение = дальше
        ? `<p class="lead-continue"><a class="text-link" href="${дальше}">Разобраться, что делать дальше →</a></p>`
        : '';
      leadStatus.innerHTML = `<p class="lead-ready">Материал готов.</p><a class="button" href="${result.download}" download>${result.label || 'Скачать материалы'}</a> <a class="text-link" href="https://t.me/nastoronepodryadchika" target="_blank">Разборы выходят в Telegram</a>${продолжение}`;
      leadForm.reset();
      trackGoal('checklist_download');
    } catch (error) { leadStatus.textContent = error.message; }
    finally { button.disabled = false; }
  });
}
