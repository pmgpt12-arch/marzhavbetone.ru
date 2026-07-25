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
function trackGoal(name) {
  if (typeof window.ym === 'function' && window.METRIKA_ID) window.ym(window.METRIKA_ID, 'reachGoal', name);
}
document.querySelectorAll('a[href^="https://dzen.ru"]').forEach(link => link.addEventListener('click', () => trackGoal('dzen_click')));

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

function money(value) { return new Intl.NumberFormat('ru-RU').format(value / 100) + ' ₽'; }
function saveCart() { localStorage.setItem('marzhavbetone-cart', JSON.stringify(cart)); }
function openCart() {
  cartPanel.hidden = false;
  cartBackdrop.hidden = false;
  document.querySelector('#cart-toggle').setAttribute('aria-expanded', 'true');
}
function closeCart() {
  cartPanel.hidden = true;
  cartBackdrop.hidden = true;
  document.querySelector('#cart-toggle').setAttribute('aria-expanded', 'false');
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

document.querySelector('#cart-toggle').addEventListener('click', openCart);
document.querySelector('#cart-close').addEventListener('click', closeCart);
cartBackdrop.addEventListener('click', closeCart);
document.querySelectorAll('.add-to-cart').forEach(button => button.addEventListener('click', () => {
  if (!cart.some(item => item.name === button.dataset.product)) cart.push({ name: button.dataset.product, price: Number(button.dataset.price) });
  saveCart(); renderCart(); openCart();
}));

// ===================== ОПЛАТА ЧЕРЕЗ ЮКАССА =====================
function createCheckoutModal() {
  if (document.getElementById('checkout-modal')) return;
  
  const modal = document.createElement('div');
  modal.id = 'checkout-modal';
  modal.innerHTML = `
    <div class="checkout-backdrop"></div>
    <div class="checkout-panel">
      <div class="checkout-head">
        <h2>Оформление заказа</h2>
        <button type="button" class="checkout-close" aria-label="Закрыть">×</button>
      </div>
      <div class="checkout-body">
        <div id="checkout-items"></div>
        <div class="checkout-total" id="checkout-total"></div>
        <form id="checkout-form">
          <label class="checkout-field">
            <span>Email <small>(для отправки документов)</small></span>
            <input type="email" name="email" placeholder="your@email.com" required>
          </label>
          <label class="checkout-field">
            <span>Телефон или Telegram</span>
            <input type="text" name="phone" placeholder="+7 900 000-00-00 или @username">
          </label>
          <label class="checkout-consent">
            <input type="checkbox" name="consent" value="yes" required>
            Принимаю <a href="offer.html" target="_blank">условия оферты</a>
          </label>
          <button type="submit" class="button checkout-submit">Перейти к оплате</button>
          <p class="checkout-fine">🔒 Оплата через защищённый шлюз ЮКасса. Данные карты не сохраняются на нашем сервере.</p>
          <p id="checkout-error" class="checkout-error" role="alert"></p>
        </form>
      </div>
      <div class="checkout-loading" id="checkout-loading" hidden>
        <div class="spinner"></div>
        <p>Создаём платёж...</p>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  
  // Стили
  const style = document.createElement('style');
  style.textContent = `
    #checkout-modal{position:fixed;inset:0;z-index:50;display:none;align-items:center;justify-content:center}
    #checkout-modal.active{display:flex}
    .checkout-backdrop{position:absolute;inset:0;background:rgba(36,38,41,.6)}
    .checkout-panel{position:relative;background:#fff;border-radius:16px;width:min(480px,92vw);max-height:90vh;overflow:auto;padding:28px;box-shadow:0 24px 80px rgba(0,0,0,.25)}
    .checkout-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px}
    .checkout-head h2{margin:0;font-size:22px}
    .checkout-close{border:0;background:none;font-size:32px;line-height:1;cursor:pointer;color:#65676a}
    .checkout-item{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #eee;font-size:15px}
    .checkout-item strong{font-weight:600}
    .checkout-total{display:flex;justify-content:space-between;padding:16px 0;margin-bottom:16px;font-size:18px;font-weight:700;border-top:2px solid #242629}
    .checkout-field{display:block;margin-bottom:16px}
    .checkout-field span{display:block;margin-bottom:6px;font-size:14px;font-weight:500}
    .checkout-field input{width:100%;padding:12px 14px;border:1px solid #c8c3b9;border-radius:8px;font-size:15px;font-family:inherit;box-sizing:border-box}
    .checkout-field input:focus{outline:none;border-color:#242629}
    .checkout-consent{display:flex;align-items:flex-start;gap:8px;margin-bottom:20px;font-size:13px;color:#65676a}
    .checkout-consent input{margin-top:2px}
    .checkout-submit{width:100%;padding:14px;font-size:16px}
    .checkout-fine{margin-top:12px;font-size:12px;color:#65676a;text-align:center}
    .checkout-error{color:#c62828;font-size:14px;margin-top:8px;text-align:center}
    .checkout-loading{position:absolute;inset:0;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:16px}
    .checkout-loading .spinner{width:40px;height:40px;border:3px solid #e0dcd3;border-top-color:#242629;border-radius:50%;animation:spin 1s linear infinite;margin-bottom:16px}
    @keyframes spin{to{transform:rotate(360deg)}}
  `;
  document.head.appendChild(style);
  
  // Закрытие
  modal.querySelector('.checkout-close').addEventListener('click', () => modal.classList.remove('active'));
  modal.querySelector('.checkout-backdrop').addEventListener('click', () => modal.classList.remove('active'));
  
  // Отправка формы
  modal.querySelector('#checkout-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const errorEl = document.getElementById('checkout-error');
    const loadingEl = document.getElementById('checkout-loading');
    const submitBtn = form.querySelector('.checkout-submit');
    
    errorEl.textContent = '';
    submitBtn.disabled = true;
    loadingEl.hidden = false;
    
    const data = {
      items: cart,
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
    };
    
    try {
      const res = await fetch('/payment.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const text = await res.text();
      let result;
      try {
        result = JSON.parse(text);
      } catch {
        throw new Error('Сервер вернул ошибку (код ' + res.status + '). Попробуйте позже или напишите нам в Telegram.');
      }
      
      if (result.ok && result.payment_url) {
        // Редирект на страницу оплаты ЮКасса
        window.location.href = result.payment_url;
      } else {
        throw new Error(result.message || 'Не удалось создать платёж');
      }
    } catch (err) {
      errorEl.textContent = err.message;
      submitBtn.disabled = false;
      loadingEl.hidden = true;
    }
  });
}

function openCheckout() {
  createCheckoutModal();
  const modal = document.getElementById('checkout-modal');
  const itemsEl = document.getElementById('checkout-items');
  const totalEl = document.getElementById('checkout-total');
  
  itemsEl.innerHTML = '';
  cart.forEach(item => {
    const div = document.createElement('div');
    div.className = 'checkout-item';
    div.innerHTML = `<strong>${item.name}</strong><span>${money(item.price)}</span>`;
    itemsEl.appendChild(div);
  });
  
  const total = cart.reduce((sum, item) => sum + item.price, 0);
  totalEl.innerHTML = `<span>Итого</span><span>${money(total)}</span>`;
  
  modal.classList.add('active');
  closeCart();
}

cartCheckout.addEventListener('click', openCheckout);

// ===================== СТАРАЯ ЛОГИКА (оставлена для совместимости) =====================
cartCheckout.addEventListener('click', () => {
  // Если корзина пуста — ничего не делаем
  if (cart.length === 0) return;
});

renderCart();

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
      formStatus.textContent = 'Готово. Обращение отправлено — без торжественной приёмки.';
      formStatus.className = 'form-status success';
      trackGoal('lead_sent');
    } catch (error) {
      formStatus.textContent = `${error.message}. Напишите напрямую: marzhavbetone@yandex.ru`;
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
      leadStatus.innerHTML = `<a class="button" href="${result.download}" download>Скачать чек-лист PDF</a> <a class="text-link" href="https://t.me/marzhavbetone" target="_blank">Перейти в Telegram</a>`;
      leadForm.reset();
      trackGoal('checklist_download');
    } catch (error) { leadStatus.textContent = error.message; }
    finally { button.disabled = false; }
  });
}
