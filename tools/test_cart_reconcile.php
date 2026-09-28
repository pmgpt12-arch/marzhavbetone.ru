<?php
/**
 * Регресс корзины перед оплатой: списывается ровно то, что показано.
 * Запуск: php tools/test_cart_reconcile.php
 *
 * Дефект (аудит MB001, PR #290). Корзина живёт в localStorage и переживает
 * правку каталога. `payment.php` брал цену из каталога — это верно, — но
 * ничего не сверял с тем, что видел покупатель:
 *  1. в корзине показана старая цена, а касса получала новую — покупатель
 *     видел одну сумму, а платил другую;
 *  2. один и тот же цифровой sku дважды (старая позиция по названию без sku
 *     плюс новая с sku) уходил в кассу двумя строками и оплачивался дважды;
 *  3. снятый с продажи sku ронял весь заказ ответом 422 без выхода: из
 *     корзины его не убирал никто, и действующие товары купить было нельзя.
 *
 * Как проверяется. Настоящий `payment.php` на встроенном сервере во
 * временном корне с собственным config.php; вместо ЮKassa — локальная
 * заглушка, пишущая каждый запрос в журнал. Наружу никто не ходит, платежей
 * нет. Товары берутся из каталога по правилу (первые платные sku), а не по
 * именам — тест не привязан ни к t1, ни к s1.
 */
declare(strict_types=1);

require __DIR__ . '/_test_http.php';

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-cart-reconcile-' . getmypid();
$web = $tmp . '/web';
$orders = $tmp . '/orders';
$products = $tmp . '/products';
$kassaLog = $tmp . '/kassa.log';
@mkdir($web, 0777, true);
@mkdir($orders, 0777, true);
@mkdir($products, 0777, true);

$провалов = 0;

foreach (['payment.php', 'products-config.php'] as $файл) {
    copy($root . '/' . $файл, $web . '/' . $файл);
}

$портКассы = mvb_free_port();
$кассаКорень = $tmp . '/kassa';
@mkdir($кассаКорень, 0777, true);
file_put_contents($кассаКорень . '/router.php', <<<PHPK
<?php
file_put_contents('{$kassaLog}', file_get_contents('php://input') . "\\n", FILE_APPEND);
header('Content-Type: application/json');
echo json_encode(['id' => 'pay_test_' . uniqid(), 'status' => 'pending',
                  'confirmation' => ['confirmation_url' => 'http://127.0.0.1/pay']]);
return true;
PHPK);
$касса = mvb_serve($кассаКорень, $портКассы, $кассаКорень . '/router.php');

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
PHP);

// Каталог читается тем же кодом, что у кассы; товары — по правилу.
$каталог = (static function () use ($root, $orders, $products) {
    foreach ([
        'ORDERS_DIR' => $orders, 'PRODUCTS_DIR' => $products,
        'SITE_URL' => 'http://127.0.0.1', 'ADMIN_EMAIL' => 'a@example.invalid',
        'YOOKASSA_SHOP_ID' => 't', 'YOOKASSA_SECRET_KEY' => 't',
        'YOOKASSA_API_URL' => 'http://127.0.0.1:1/x', 'YOOKASSA_MODE' => 'test',
    ] as $n => $v) { if (!defined($n)) define($n, $v); }
    require $root . '/products-config.php';
    return mvb_products();
})();
$платные = array_keys(array_filter($каталог, static fn($p) => ($p['price'] ?? 0) > 100));
if (count($платные) < 2) {
    echo "Тест не запускался: в каталоге меньше двух платных товаров\n";
    exit(2);
}
[$a, $b] = $платные;
$позиция = static fn(string $sku) => ['sku' => $sku, 'name' => $каталог[$sku]['name'],
                                      'price' => $каталог[$sku]['price']];
$снятый = 'retired-' . substr(md5((string)getmypid()), 0, 6);
while (isset($каталог[$снятый])) { $снятый .= 'x'; }

$портСайта = mvb_free_port();
$сайт = mvb_serve($web, $портСайта);

/** Оформление: ответ payment.php и то, что ушло в кассу. */
function checkout(int $порт, array $items, string $kassaLog, string $orders): array
{
    @unlink($kassaLog);
    $до = count(glob($orders . '/order_*.json') ?: []);
    $r = mvb_post_json($порт, '/payment.php', ['items' => $items, 'email' => 'buyer@example.invalid']);
    $строки = is_file($kassaLog) ? array_filter(explode("\n", (string)file_get_contents($kassaLog))) : [];
    return [
        'code'   => $r['code'],
        'json'   => json_decode($r['body'], true) ?: [],
        'body'   => $r['body'],
        'kassa'  => array_map(static fn($с) => json_decode($с, true), array_values($строки)),
        'orders' => count(glob($orders . '/order_*.json') ?: []) - $до,
    ];
}

function shown_total(array $items): int
{
    return array_sum(array_map(static fn($i) => (int)($i['price'] ?? 0), $items));
}

function charged(array $запрос): int
{
    return (int)round((float)($запрос['amount']['value'] ?? 0) * 100);
}

/** Контракт: в кассу не уходит ничего, что расходится с показанной корзиной. */
function assert_no_divergent_charge(array $r, array $shown, string $что): void
{
    foreach ($r['kassa'] as $запрос) {
        mvb_equal(charged($запрос), shown_total($shown), "{$что}: в кассу ушла сумма, отличная от показанной");
        $skus = [];
        foreach ($запрос['receipt']['items'] ?? [] as $строка) { $skus[] = $строка['description'] ?? ''; }
        mvb_equal(count($skus), count(array_unique($skus)), "{$что}: одна позиция в чеке дважды");
    }
}

/** Повторная отправка той корзины, что вернул сервер, обязана оплатиться. */
function assert_corrected_cart_pays(int $порт, array $r, array $ожидаемые, string $kassaLog, string $orders): void
{
    mvb_equal($r['json']['cart_changed'] ?? null, true, 'ответ не сообщает, что корзина обновлена: ' . $r['body']);
    mvb_true(is_array($r['json']['cart'] ?? null), 'ответ не содержит исправленную корзину: ' . $r['body']);
    mvb_equal(array_column($r['json']['cart'], 'sku'), $ожидаемые, 'состав исправленной корзины');
    mvb_true(trim((string)($r['json']['message'] ?? '')) !== '', 'нет сообщения покупателю');
    $повтор = checkout($порт, $r['json']['cart'], $kassaLog, $orders);
    mvb_equal($повтор['code'], 200, 'исправленная корзина не оплачивается: ' . $повтор['body']);
    mvb_equal(count($повтор['kassa']), 1, 'запросов в кассу на исправленную корзину');
    mvb_equal(charged($повтор['kassa'][0]), shown_total($r['json']['cart']), 'сумма оплаты исправленной корзины');
}

echo "Корзина перед оплатой: списывается ровно то, что показано\n";

// 1. Устаревшая цена в корзине.
mvb_check('1. цена в корзине расходится с каталогом — платёж не создаётся, корзина исправлена', function () use ($портСайта, $позиция, $a, $каталог, $kassaLog, $orders) {
    $устаревшая = $позиция($a);
    $устаревшая['price'] = $каталог[$a]['price'] + 750000;
    $r = checkout($портСайта, [$устаревшая], $kassaLog, $orders);
    assert_no_divergent_charge($r, [$устаревшая], 'устаревшая цена');
    mvb_equal($r['code'], 409, 'HTTP при устаревшей цене: ' . $r['body']);
    mvb_equal($r['orders'], 0, 'заказов создано при расхождении цены');
    mvb_equal($r['json']['cart'][0]['price'] ?? null, $каталог[$a]['price'], 'цена в исправленной корзине');
    assert_corrected_cart_pays($портСайта, $r, [$a], $kassaLog, $orders);
});

// 2. Один sku дважды: по названию без sku и по sku.
mvb_check('2. один цифровой sku дважды — в кассу не уходит, повтор убран', function () use ($портСайта, $позиция, $a, $kassaLog, $orders) {
    $поНазванию = $позиция($a);
    $поНазванию['sku'] = '';
    $r = checkout($портСайта, [$позиция($a), $поНазванию], $kassaLog, $orders);
    foreach ($r['kassa'] as $запрос) {
        mvb_equal(count($запрос['receipt']['items'] ?? []), 1, 'строк в чеке за один товар');
    }
    mvb_equal($r['code'], 409, 'HTTP при повторе sku: ' . $r['body']);
    mvb_equal($r['orders'], 0, 'заказов создано при повторе sku');
    assert_corrected_cart_pays($портСайта, $r, [$a], $kassaLog, $orders);
});

// 3. Снятый sku не блокирует действующие товары.
mvb_check('3. снятый sku исключается с сообщением, действующие товары оплачиваются', function () use ($портСайта, $позиция, $a, $b, $снятый, $kassaLog, $orders) {
    $мёртвый = ['sku' => $снятый, 'name' => 'Снятый с продажи комплект', 'price' => 990000];
    $показано = [$позиция($a), $мёртвый, $позиция($b)];
    $r = checkout($портСайта, $показано, $kassaLog, $orders);
    assert_no_divergent_charge($r, $показано, 'снятый sku');
    mvb_equal($r['code'], 409, 'HTTP при снятом sku: ' . $r['body']);
    mvb_true(mb_strpos((string)($r['json']['message'] ?? ''), 'Снятый с продажи комплект') !== false,
             'сообщение не называет исключённую позицию: ' . $r['body']);
    assert_corrected_cart_pays($портСайта, $r, [$a, $b], $kassaLog, $orders);
});

// Контроль: согласованная корзина оплачивается с первого раза.
mvb_check('согласованная корзина из двух товаров оплачивается сразу', function () use ($портСайта, $позиция, $a, $b, $kassaLog, $orders) {
    $показано = [$позиция($a), $позиция($b)];
    $r = checkout($портСайта, $показано, $kassaLog, $orders);
    mvb_equal($r['code'], 200, 'HTTP: ' . $r['body']);
    mvb_equal(count($r['kassa']), 1, 'запросов в кассу');
    mvb_equal(charged($r['kassa'][0]), shown_total($показано), 'сумма оплаты');
});

// Контроль: корзина только из снятых товаров не создаёт платёж и очищается.
mvb_check('корзина только из снятых товаров — платежа нет, корзина пуста', function () use ($портСайта, $снятый, $kassaLog, $orders) {
    $r = checkout($портСайта, [['sku' => $снятый, 'name' => 'Снятый', 'price' => 100000]], $kassaLog, $orders);
    mvb_equal(count($r['kassa']), 0, 'запросов в кассу');
    mvb_equal($r['orders'], 0, 'заказов создано');
    mvb_equal($r['json']['cart'] ?? null, [], 'корзина в ответе: ' . $r['body']);
});

mvb_kill($сайт);
mvb_kill($касса);
exec('rm -rf ' . escapeshellarg($tmp));
mvb_finish();
