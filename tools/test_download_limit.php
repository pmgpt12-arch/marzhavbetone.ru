<?php
/**
 * Регресс Д-2: лимит скачиваний атомарен, счётчик не теряется.
 * Запуск: php tools/test_download_limit.php
 *
 * Дефект, ради которого написан тест. `download.php` читал заказ, проверял
 * предел и записывал увеличенный счётчик прямым `file_put_contents()` — мимо
 * `mvb_with_order_lock()` и мимо `mvb_write_order()`. Три шага без общей
 * блокировки: несколько одновременных запросов видели одно и то же значение
 * 29, все проходили проверку, и предел 30 переставал быть пределом. Тот же
 * разрыв давал потерянное обновление (запись поверх полей, проставленных
 * вебхуком) и рваное чтение — конкурент видел половину JSON.
 *
 * Как проверяется. Поднимается встроенный сервер PHP на временном корне с
 * копиями файлов контура и собственным config.php; боевой config.php не
 * читается, касса не вызывается, писем нет. По готовой ссылке выдачи
 * одновременно идут запросы числом больше предела. Требуется: успешных
 * ровно столько, сколько разрешает предел, остальным 429, а счётчик в
 * заказе равен числу успешных — ни больше (обход предела), ни меньше
 * (потерянное обновление).
 *
 * Проверено мутацией: если в download.php вернуть прямую запись файла
 * вместо резерва под блокировкой, тест краснеет обоими признаками.
 */
declare(strict_types=1);

require __DIR__ . '/_test_http.php';

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-download-limit-' . getmypid();
$web = $tmp . '/web';
$products = $tmp . '/products';
@mkdir($web, 0777, true);
@mkdir($products, 0777, true);

$провалов = 0;

// Временный корень: копии файлов контура и свой config.php. Боевой config.php
// не копируется — в нём боевые ключи, и тесту они не нужны.
foreach (['check-payment.php', 'download.php', 'products-config.php', 'payment.php', 'webhook.php'] as $файл) {
    copy($root . '/' . $файл, $web . '/' . $файл);
}
file_put_contents($web . '/config.php', <<<PHP
<?php
define('YOOKASSA_SHOP_ID', 'test-shop');
define('YOOKASSA_SECRET_KEY', 'test-key');
define('YOOKASSA_MODE', 'test');
define('SITE_URL', 'http://127.0.0.1');
define('ADMIN_EMAIL', 'admin@example.invalid');
define('ORDERS_DIR', '{$tmp}/orders');
define('PRODUCTS_DIR', '{$products}');
define('YOOKASSA_API_URL', 'http://127.0.0.1:1/unreachable');
if (!is_dir(ORDERS_DIR)) { mkdir(ORDERS_DIR, 0777, true); }
PHP);

$orders = $tmp . '/orders';
@mkdir($orders . '/delivery', 0777, true);

// Готовый архив выдачи и заказ, который на него ссылается.
$каталогСайта = (static function () use ($root, $tmp, $products, $orders) {
    foreach ([
        'ORDERS_DIR' => $orders, 'PRODUCTS_DIR' => $products,
        'SITE_URL' => 'http://127.0.0.1', 'ADMIN_EMAIL' => 'a@example.invalid',
        'YOOKASSA_SHOP_ID' => 't', 'YOOKASSA_SECRET_KEY' => 't',
        'YOOKASSA_API_URL' => 'http://127.0.0.1:1/x', 'YOOKASSA_MODE' => 'test',
    ] as $n => $v) { if (!defined($n)) define($n, $v); }
    require $root . '/products-config.php';
    return mvb_products();
})();

$sku = 'p1';
$zipИмя = $каталогСайта[$sku]['zip'];
$zip = new ZipArchive();
$zip->open($orders . '/delivery/' . $zipИмя, ZipArchive::CREATE | ZipArchive::OVERWRITE);
$zip->addFromString('01-doc.txt', str_repeat("данные\n", 200));
$zip->close();

$orderId = 'order_20260917_120000_ddd444';
$токен = bin2hex(random_bytes(16));
file_put_contents($orders . '/' . $orderId . '.json', json_encode([
    'id' => $orderId,
    'status' => 'paid',
    'email' => 'buyer@example.invalid',
    'items' => [['sku' => $sku, 'name' => 'Комплект', 'price' => 249000]],
    'total' => 249000,
    'paid_at' => date('c'),
    'status_key_hash' => hash('sha256', 'ключ-теста'),
    'delivery' => [
        'token' => $токен,
        'created_at' => date('c'),
        'expires_at' => date('c', time() + 7 * 86400),
        'downloads' => 0,
        'items' => [$sku => $zipИмя],
    ],
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

$порт = mvb_free_port();
// Встроенный сервер по умолчанию обрабатывает запросы по одному. Без
// воркеров «одновременных» запросов не бывает, и тест проверял бы
// последовательный случай, который проходил и до правки.
putenv('PHP_CLI_SERVER_WORKERS=8');
$сервер = mvb_serve($web, $порт);

$предел = 30;      // DELIVERY_MAX_DOWNLOADS в products-config.php
$запросов = 40;    // заведомо больше предела

echo "Д-2: лимит скачиваний атомарен\n";

$адрес = "http://127.0.0.1:{$порт}/download.php?o=" . rawurlencode($orderId)
    . '&t=' . $токен . '&f=' . $sku;

$multi = curl_multi_init();
$ручки = [];
for ($i = 0; $i < $запросов; $i++) {
    $ch = curl_init($адрес);
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 30]);
    curl_multi_add_handle($multi, $ch);
    $ручки[] = $ch;
}
$активных = null;
do {
    curl_multi_exec($multi, $активных);
    curl_multi_select($multi, 0.2);
} while ($активных > 0);

$коды = [];
foreach ($ручки as $ch) {
    $коды[] = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_multi_remove_handle($multi, $ch);
    curl_close($ch);
}
curl_multi_close($multi);
mvb_kill($сервер);

$успешных = count(array_filter($коды, static fn(int $c): bool => $c === 200));
$отказов  = count(array_filter($коды, static fn(int $c): bool => $c === 429));
$прочих   = count($коды) - $успешных - $отказов;

$заказ = json_decode((string)file_get_contents($orders . '/' . $orderId . '.json'), true);
$счётчик = (int)($заказ['delivery']['downloads'] ?? -1);

mvb_check('успешных не больше предела', function () use ($успешных, $предел) {
    mvb_true($успешных <= $предел, "успешных {$успешных} при пределе {$предел}");
});
mvb_check('лишние получили 429, а не 200', function () use ($успешных, $отказов, $запросов, $предел) {
    mvb_equal($успешных + $отказов, $запросов, 'сумма 200 и 429');
    mvb_equal($отказов, $запросов - $предел, 'число отказов');
});
mvb_check('других кодов не было', function () use ($прочих, $коды) {
    mvb_equal($прочих, 0, 'коды ответа: ' . implode(',', $коды));
});
mvb_check('счётчик равен числу успешных — обновления не потеряны',
    function () use ($счётчик, $успешных) {
        mvb_equal($счётчик, $успешных, 'delivery.downloads');
    });
mvb_check('заказ читается как JSON после конкурентной записи',
    function () use ($заказ) { mvb_true(is_array($заказ), 'файл заказа повреждён'); });
mvb_check('в download.php нет прямой записи заказа', function () use ($root) {
    $src = (string)file_get_contents($root . '/download.php');
    $код = preg_replace('~/\*.*?\*/|//[^\n]*~s', '', $src);
    mvb_true(strpos((string)$код, 'file_put_contents') === false,
        'file_put_contents остался в коде download.php');
});
mvb_check('проверки доступа выполняются внутри блокировки', function () use ($root) {
    $src = (string)file_get_contents($root . '/download.php');
    $начало = strpos($src, 'mvb_with_order_lock_strict');
    $конец = strpos($src, "\n});", (int)$начало);
    $внутри = substr($src, (int)$начало, (int)$конец - (int)$начало);
    foreach (["!== 'paid'", 'hash_equals', 'expires_at', 'DELIVERY_MAX_DOWNLOADS', "items'][\$sku]"] as $признак) {
        mvb_true(strpos($внутри, $признак) !== false, "внутри блокировки нет проверки: {$признак}");
    }
});

echo "\n  коды ответов: 200×{$успешных}, 429×{$отказов}, прочих {$прочих}; "
    . "delivery.downloads = {$счётчик}\n";

// Уборка
foreach (glob($orders . '/delivery/*') ?: [] as $f) { @unlink($f); }
@rmdir($orders . '/delivery');
foreach (glob($orders . '/*') ?: [] as $f) { if (is_file($f)) { @unlink($f); } }
@rmdir($orders);
foreach (glob($web . '/*') ?: [] as $f) { @unlink($f); }
@rmdir($web);
@rmdir($products);
@rmdir($tmp);

mvb_finish();
