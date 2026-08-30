<?php
/**
 * Конфигурация ЮКасса
 * 
 * 1. Получите shopId и secretKey в личном кабинете ЮКасса:
 *    https://yookassa.ru/my
 * 
 * 2. Для тестового режима используйте данные тестового магазина
 * 3. Укажите URL для webhook'ов в личном кабинете:
 *    https://marzhavbetone.ru/webhook.php
 */

// === ЗАПОЛНИТЕ ЭТИ ДАННЫЕ ===
define('YOOKASSA_SHOP_ID', 'ВАШ_SHOP_ID');           // Например: '123456'
define('YOOKASSA_SECRET_KEY', 'ВАШ_SECRET_KEY');       // Например: 'test_...' или 'live_...'

// Режим: 'test' для тестирования, 'live' для реальных платежей
define('YOOKASSA_MODE', 'test');

// Базовый URL сайта (без слэша в конце)
define('SITE_URL', 'https://marzhavbetone.ru');

// Email для уведомлений о новых заказах
define('ADMIN_EMAIL', 'marzhavbetone@yandex.ru');

// Папка для хранения заказов (должна быть доступна для записи)
define('ORDERS_DIR', __DIR__ . '/orders');

// Папка с мастерами продуктов — то, из чего собирается архив покупателю.
// Задавать здесь НЕ обязательно: products-config.php сам находит её среди
// известных раскладок (рядом с сайтом в репозитории; ~/products-marzhavbetone
// вне webroot на боевом сервере — туда её кладёт deploy.yml).
//
// Раскомментируйте и укажите полный путь, только если мастера лежат в
// нестандартном месте — например, когда задан секрет DEPLOY_PRODUCTS_PATH.
// Путь должен вести ВНЕ webroot: иначе архивы можно будет скачать без оплаты.
// define('PRODUCTS_DIR', '/var/www/uXXXXXXX/data/products-marzhavbetone');

// Создаём папку для заказов если её нет
if (!is_dir(ORDERS_DIR)) {
    mkdir(ORDERS_DIR, 0755, true);
}

// API endpoint
define('YOOKASSA_API_URL', 'https://api.yookassa.ru/v3');
