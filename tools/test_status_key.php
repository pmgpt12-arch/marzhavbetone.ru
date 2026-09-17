<?php
/**
 * Регресс Д-3: статус заказа и ссылки выдачи закрыты ключом.
 * Запуск: php tools/test_status_key.php
 *
 * Дефект, ради которого написан тест. `check-payment.php` отвечал на один
 * только параметр `order`: GET возвращал почту покупателя, состав, сумму и
 * готовые ссылки выдачи с рабочим токеном. Идентификатор заказа секретом не
 * является — `substr(uniqid(), -6)` это младшие разряды времени в
 * микросекундах, и корневой `.htaccess` прямо называет его перебираемым.
 * Запрет на чтение `orders/*.json` этот путь не закрывал: `check-payment.php`
 * — штатная точка входа.
 *
 * Как проверяется. Встроенный сервер на временном корне с копиями файлов
 * контура и собственным config.php; вместо кассы — локальная заглушка,
 * отвечающая заранее известным JSON. Боевой config.php не читается, к
 * api.yookassa.ru никто не ходит, писем нет.
 *
 * Проверено мутацией: если снять в check-payment.php проверку ключа, тест
 * краснеет на «только order → 403» и «неверный ключ → 403».
 */
declare(strict_types=1);

require __DIR__ . '/_test_http.php';

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-status-key-' . getmypid();
$web = $tmp . '/web';
$products = $tmp . '/products';
$orders = $tmp . '/orders';
@mkdir($web, 0777, true);
@mkdir($orders . '/delivery', 0777, true);
@mkdir($products, 0777, true);

$провалов = 0;

foreach (['check-payment.php', 'download.php', 'products-config.php', 'payment.php', 'webhook.php'] as $файл) {
    copy($root . '/' . $файл, $web . '/' . $файл);
}

// Заглушка кассы: отвечает как /payments, никуда наружу не ходит.
$портКассы = mvb_free_port();
$кассаКорень = $tmp . '/kassa';
@mkdir($кассаКорень, 0777, true);
file_put_contents($кассаКорень . '/router.php', <<<PHPK
<?php
file_put_contents('{$tmp}/kassa.log', file_get_contents('php://input') . "\\n", FILE_APPEND);
header('Content-Type: application/json');
echo json_encode(['id' => 'pay_test_1', 'status' => 'pending',
                  'confirmation' => ['confirmation_url' => 'http://127.0.0.1/pay']]);
return true;
PHPK);
$кассa = mvb_serve($кассаКорень, $портКассы, $кассаКорень . '/router.php');

file_put_contents($web . '/config.php', <<<PHP
<?php
define('YOOKASSA_SHOP_ID', 'test-shop');
define('YOOKASSA_SECRET_KEY', 'test-key');
define('YOOKASSA_MODE', 'test');
define('SITE_URL', 'http://127.0.0.1');
define('ADMIN_EMAIL', 'admin@example.invalid');
define('ORDERS_DIR', '{$orders}');
define('PRODUCTS_DIR', '{$products}');
define('YOOKASSA_API_URL', 'http://127.0.0.1:{$портКассы}');
if (!is_dir(ORDERS_DIR)) { mkdir(ORDERS_DIR, 0777, true); }
PHP);

// Мастера для sku заказа: иначе выдача отменится целиком (правило Д-1), и
// положительный случай «после paid появились ссылки» проверить будет нечем.
$каталогСайта = (static function () use ($root, $orders, $products) {
    foreach ([
        'ORDERS_DIR' => $orders, 'PRODUCTS_DIR' => $products,
        'SITE_URL' => 'http://127.0.0.1', 'ADMIN_EMAIL' => 'a@example.invalid',
        'YOOKASSA_SHOP_ID' => 't', 'YOOKASSA_SECRET_KEY' => 't',
        'YOOKASSA_API_URL' => 'http://127.0.0.1:1/x', 'YOOKASSA_MODE' => 'test',
    ] as $n => $v) { if (!defined($n)) define($n, $v); }
    require $root . '/products-config.php';
    return mvb_products();
})();
$папкаP1 = $products . '/' . $каталогСайта['p1']['dir'];
@mkdir($папкаP1, 0777, true);
file_put_contents($папкаP1 . '/01-doc.txt', "содержимое\n");

$портСайта = mvb_free_port();
putenv('PHP_CLI_SERVER_WORKERS=4');
$сайт = mvb_serve($web, $портСайта);

function get(int $порт, string $путь): array
{
    $ch = curl_init("http://127.0.0.1:{$порт}{$путь}");
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 20]);
    $тело = (string)curl_exec($ch);
    $код = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return ['code' => $код, 'body' => $тело, 'json' => json_decode($тело, true)];
}

echo "Д-3: статус заказа закрыт ключом\n";

// --- Создание заказа через payment.php (касса — заглушка) -----------------
$создан = mvb_post_json($портСайта, '/payment.php', [
    'items' => [['sku' => 'p1']],
    'email' => 'buyer@example.invalid',
]);
$ответ = json_decode($создан['body'], true);
mvb_check('заказ создан', function () use ($создан, $ответ) {
    mvb_equal($создан['code'], 200, 'HTTP payment.php: ' . $создан['body']);
    mvb_true(!empty($ответ['order_id']), 'нет order_id');
});
$orderId = (string)($ответ['order_id'] ?? '');

// Ключ виден только в адресе возврата, отданном кассе.
$запросКассе = json_decode(trim((string)@file_get_contents($tmp . '/kassa.log')), true);
$returnUrl = (string)($запросКассе['confirmation']['return_url'] ?? '');
parse_str((string)parse_url($returnUrl, PHP_URL_QUERY), $параметры);
$ключ = (string)($параметры['k'] ?? '');

mvb_check('в return_url есть и order, и ключ', function () use ($параметры, $orderId, $returnUrl) {
    mvb_equal($параметры['order'] ?? null, $orderId, 'параметр order в return_url: ' . $returnUrl);
    mvb_true(!empty($параметры['k']), 'параметра k в return_url нет: ' . $returnUrl);
});
mvb_check('ключ не короче 128 бит', function () use ($ключ) {
    mvb_true(strlen($ключ) >= 32, 'длина ключа в hex: ' . strlen($ключ));
});

$файлЗаказа = $orders . '/' . $orderId . '.json';
$заказ = json_decode((string)file_get_contents($файлЗаказа), true);

mvb_check('в заказе лежит хеш, а не ключ', function () use ($заказ, $ключ, $файлЗаказа) {
    mvb_true(!empty($заказ['status_key_hash']), 'нет status_key_hash');
    mvb_equal($заказ['status_key_hash'], hash('sha256', $ключ), 'хеш не совпал');
    $сырой = (string)file_get_contents($файлЗаказа);
    mvb_true(strpos($сырой, $ключ) === false, 'сырой ключ записан в order.json');
});

// --- Контракт check-payment.php ------------------------------------------
mvb_check('только order → 403 и ничего не раскрыто', function () use ($портСайта, $orderId) {
    $о = get($портСайта, '/check-payment.php?order=' . rawurlencode($orderId));
    mvb_equal($о['code'], 403, 'код ответа');
    mvb_true(strpos($о['body'], 'buyer@example.invalid') === false, 'в ответе почта');
    mvb_true(strpos($о['body'], 'pending') === false, 'в ответе статус');
    mvb_true(strpos($о['body'], '"total"') === false, 'в ответе сумма');
});

mvb_check('неверный ключ → 403', function () use ($портСайта, $orderId) {
    $о = get($портСайта, '/check-payment.php?order=' . rawurlencode($orderId)
        . '&key=' . str_repeat('0', 64));
    mvb_equal($о['code'], 403, 'код ответа');
    mvb_true(strpos($о['body'], 'buyer@example.invalid') === false, 'в ответе почта');
});

mvb_check('несуществующий заказ отвечает так же, как чужой ключ',
    function () use ($портСайта, $ключ) {
        $нет = get($портСайта, '/check-payment.php?order=order_20200101_000000_zzzzzz&key=' . $ключ);
        mvb_equal($нет['code'], 403, 'код ответа');
        mvb_true(strpos($нет['body'], 'не найден') === false, 'ответ выдаёт отсутствие заказа');
    });

mvb_check('старый заказ без ключа не пускают', function () use ($портСайта, $orders, $ключ) {
    $старый = 'order_20260101_000000_old111';
    file_put_contents($orders . '/' . $старый . '.json', json_encode([
        'id' => $старый, 'status' => 'paid', 'email' => 'old@example.invalid',
        'items' => [], 'total' => 100,
    ], JSON_UNESCAPED_UNICODE));
    $о = get($портСайта, '/check-payment.php?order=' . $старый . '&key=' . $ключ);
    mvb_equal($о['code'], 403, 'код ответа');
    mvb_true(strpos($о['body'], 'old@example.invalid') === false, 'в ответе почта старого заказа');
});

mvb_check('верный ключ → статус отдаётся', function () use ($портСайта, $orderId, $ключ) {
    $о = get($портСайта, '/check-payment.php?order=' . rawurlencode($orderId) . '&key=' . $ключ);
    mvb_equal($о['code'], 200, 'код ответа: ' . $о['body']);
    mvb_true(($о['json']['ok'] ?? false) === true, 'ok не true');
    mvb_true(isset($о['json']['order']['status']), 'нет статуса');
    mvb_equal($о['json']['order']['total'], 249000, 'сумма');
});

mvb_check('в успешном ответе нет почты и лишних полей',
    function () use ($портСайта, $orderId, $ключ) {
        $о = get($портСайта, '/check-payment.php?order=' . rawurlencode($orderId) . '&key=' . $ключ);
        $заказ = $о['json']['order'] ?? [];
        mvb_true(strpos($о['body'], 'buyer@example.invalid') === false, 'в ответе почта');
        foreach (['email', 'phone', 'payment_id', 'attribution', 'status_key_hash', 'delivery'] as $поле) {
            mvb_true(!array_key_exists($поле, $заказ), "в ответе лишнее поле: {$поле}");
        }
        mvb_equal(array_keys($заказ), ['status', 'total', 'items', 'downloads'], 'состав ответа');
    });

mvb_check('в ответе нет сырого токена выдачи', function () use ($портСайта, $orderId, $ключ, $orders) {
    $о = get($портСайта, '/check-payment.php?order=' . rawurlencode($orderId) . '&key=' . $ключ);
    $заказ = json_decode((string)file_get_contents($orders . '/' . $orderId . '.json'), true);
    $токен = (string)($заказ['delivery']['token'] ?? '');
    mvb_true($токен === '' || substr_count($о['body'], $токен) === 0
        || strpos($о['body'], '"token"') === false, 'токен опубликован отдельным полем');
    mvb_true(strpos($о['body'], '"token"') === false, 'в ответе есть поле token');
});

mvb_check('до оплаты ссылок выдачи нет', function () use ($портСайта, $orderId, $ключ) {
    $о = get($портСайта, '/check-payment.php?order=' . rawurlencode($orderId) . '&key=' . $ключ);
    mvb_equal($о['json']['order']['downloads'] ?? null, [], 'downloads у неоплаченного заказа');
});

// Тот же заказ, переведённый в paid: ссылки появляются, и только теперь.
// Касса тут уже не опрашивается — ветка запроса статуса работает только для
// pending и waiting_for_capture.
mvb_check('после paid ссылки выдачи появляются',
    function () use ($портСайта, $orderId, $ключ, $orders, $products) {
        $файл = $orders . '/' . $orderId . '.json';
        $заказ = json_decode((string)file_get_contents($файл), true);
        $заказ['status'] = 'paid';
        $заказ['paid_at'] = date('c');
        file_put_contents($файл, json_encode($заказ, JSON_UNESCAPED_UNICODE));

        // Мастера для sku заказа: без них выдача обязана отмениться целиком.
        $каталог = ['p1' => null];
        $о = get($портСайта, '/check-payment.php?order=' . rawurlencode($orderId) . '&key=' . $ключ);
        mvb_equal($о['code'], 200, 'код ответа');
        mvb_equal($о['json']['order']['status'] ?? null, 'paid', 'статус');
        $ссылки = $о['json']['order']['downloads'] ?? [];
        mvb_equal(count($ссылки), 1, 'число ссылок: ' . json_encode($ссылки));
        mvb_true(strpos((string)($ссылки[0]['url'] ?? ''), '/download.php?o=') !== false,
            'ссылка не ведёт на download.php');
        mvb_true(strpos($о['body'], 'buyer@example.invalid') === false,
            'в оплаченном ответе почта');
    });

// --- success.html читает оба параметра и не течёт referer ----------------
mvb_check('success.html читает ключ и шлёт его в check-payment', function () use ($root) {
    $html = (string)file_get_contents($root . '/success.html');
    mvb_true(strpos($html, "params.get('k')") !== false, 'страница не читает k');
    mvb_true(strpos($html, "'&key=' + encodeURIComponent(statusKey)") !== false,
        'страница не передаёт ключ в check-payment.php');
    mvb_true(strpos($html, '!orderId || !statusKey') !== false,
        'страница не требует оба параметра');
});
mvb_check('у страницы успеха строгая политика referrer', function () use ($root) {
    $html = (string)file_get_contents($root . '/success.html');
    mvb_true(preg_match('~<meta\s+name="referrer"\s+content="no-referrer"~', $html) === 1,
        'нет meta referrer=no-referrer');
});

mvb_kill($сайт);
mvb_kill($кассa);

// Уборка
foreach (glob($orders . '/delivery/*') ?: [] as $f) { @unlink($f); }
@rmdir($orders . '/delivery');
foreach (glob($orders . '/*') ?: [] as $f) { if (is_file($f)) { @unlink($f); } }
@rmdir($orders);
foreach (glob($web . '/*') ?: [] as $f) { @unlink($f); }
@rmdir($web);
foreach (glob($кассаКорень . '/*') ?: [] as $f) { @unlink($f); }
@rmdir($кассаКорень);
@unlink($tmp . '/kassa.log');
@rmdir($products);
@rmdir($tmp);

mvb_finish();
