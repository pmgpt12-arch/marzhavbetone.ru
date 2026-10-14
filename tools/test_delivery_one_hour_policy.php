<?php
/**
 * Owner contract: delivery links live exactly 3600 seconds from first issuance.
 *
 * Isolated local test. It creates temporary product/order directories, does not
 * call YooKassa, SMTP, production storage, or the network.
 */
declare(strict_types=1);

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-one-hour-policy-' . getmypid();
$products = $tmp . '/products';
$orders = $tmp . '/orders';
@mkdir($products, 0777, true);
@mkdir($orders . '/delivery', 0777, true);

foreach ([
    'ORDERS_DIR' => $orders,
    'DELIVERY_DIR' => $orders . '/delivery',
    'PRODUCTS_DIR' => $products,
    'SITE_URL' => 'https://example.invalid',
    'ADMIN_EMAIL' => 'admin@example.invalid',
    'YOOKASSA_SHOP_ID' => 'test',
    'YOOKASSA_SECRET_KEY' => 'test',
    'YOOKASSA_API_URL' => 'https://example.invalid',
    'YOOKASSA_MODE' => 'test',
] as $name => $value) {
    if (!defined($name)) {
        define($name, $value);
    }
}
require $root . '/products-config.php';

$failures = [];
$check = static function (string $name, bool $ok, string $detail = '') use (&$failures): void {
    if ($ok) {
        echo "  ok   {$name}\n";
        return;
    }
    $failures[] = $name . ($detail !== '' ? ': ' . $detail : '');
    echo "  FAIL {$name}" . ($detail !== '' ? ": {$detail}" : '') . "\n";
};

echo "Owner contract: current product, one-hour link\n";

$fixedIssuedAt = 2000000000;
$fixedWindow = mvb_delivery_window([], $fixedIssuedAt);
$fixedCreated = strtotime($fixedWindow['created_at']);
$fixedExpires = strtotime($fixedWindow['expires_at']);
$check('fixed issuance seam uses supplied epoch',
    $fixedCreated === $fixedIssuedAt,
    'created=' . var_export($fixedCreated, true));
$check('fixed issuance seam derives exact 3600-second window',
    $fixedCreated !== false && $fixedExpires !== false
        && ($fixedExpires - $fixedCreated) === DELIVERY_TTL_SECONDS,
    'delta=' . (($fixedCreated !== false && $fixedExpires !== false)
        ? (string)($fixedExpires - $fixedCreated) : 'invalid'));
$preservedWindow = mvb_delivery_window([
    'created_at' => $fixedWindow['created_at'],
    'expires_at' => $fixedWindow['expires_at'],
], $fixedIssuedAt + 9999);
$check('fixed issuance seam preserves replay window', $preservedWindow === $fixedWindow);

$catalog = mvb_products();
$sku = isset($catalog['p3']) ? 'p3' : array_key_first(array_filter(
    $catalog,
    static fn(array $product, string $key): bool => $key !== 'p1',
    ARRAY_FILTER_USE_BOTH
));
if ($sku === null) {
    echo "  BLOCKED no non-P1 catalog product\n";
    exit(2);
}
$dir = $products . '/' . $catalog[$sku]['dir'];
@mkdir($dir, 0777, true);
file_put_contents($dir . '/buyer.txt', "current product\n");

$order = [
    'id' => 'order_20261014_000000_onehour',
    'status' => 'paid',
    'items' => [[
        'sku' => $sku,
        'name' => $catalog[$sku]['name'],
        'price' => $catalog[$sku]['price'],
    ]],
    'total' => $catalog[$sku]['price'],
];

$plan = mvb_prepare_delivery($order);
$check('current product prepares without missing files', $plan['missing'] === [], json_encode($plan['missing']));
$created = strtotime((string)($order['delivery']['created_at'] ?? ''));
$expires = strtotime((string)($order['delivery']['expires_at'] ?? ''));
$check('expiry is exactly issuance plus 3600 seconds',
    $created !== false && $expires !== false && ($expires - $created) === 3600,
    'delta=' . (($created !== false && $expires !== false) ? (string)($expires - $created) : 'invalid'));

if (!function_exists('mvb_delivery_is_expired')) {
    $check('boundary seam exists for deterministic 3599/3600 checks', false, 'mvb_delivery_is_expired missing');
} else {
    $issued = 2000000000;
    $check('age 3599 is permitted', mvb_delivery_is_expired($issued + 3600, $issued + 3599) === false);
    $check('age 3600 is denied', mvb_delivery_is_expired($issued + 3600, $issued + 3600) === true);
}

$first = $order['delivery'] ?? [];
$order['delivery']['downloads'] = 3;
$order['delivery']['email_sent_at'] = 'already-sent';
mvb_prepare_delivery($order);
foreach (['token', 'created_at', 'expires_at'] as $field) {
    $check("callback replay preserves {$field}",
        ($order['delivery'][$field] ?? null) === ($first[$field] ?? null));
}
$check('callback replay preserves download counter', ($order['delivery']['downloads'] ?? null) === 3);
$check('callback replay preserves buyer-mail marker',
    ($order['delivery']['email_sent_at'] ?? null) === 'already-sent');

$email = mvb_delivery_email($order, $plan['links']);
$oneHour = strpos($email, '1 час') !== false || strpos($email, '60 минут') !== false;
$check('buyer message states one hour', $oneHour);
$check('buyer message has no day-based expiry promise', strpos($email, 'дней') === false);

foreach (['payment-delivery.html', 'offer.html', 'success.html'] as $surface) {
    $copy = (string)file_get_contents($root . '/' . $surface);
    $check("{$surface} states one-hour link lifetime", strpos($copy, '1 час') !== false);
    $check("{$surface} has no 30-day link promise",
        strpos($copy, '30 дней') === false && strpos($copy, '30 календарных дней') === false);
}
$offerCopy = (string)file_get_contents($root . '/offer.html');
$check('offer says repeat access does not extend expiry',
    strpos($offerCopy, 'при повторном обращении не продлевается') !== false);

$clean = static function (string $path) use (&$clean): void {
    if (!is_dir($path)) {
        @unlink($path);
        return;
    }
    foreach (new DirectoryIterator($path) as $item) {
        if ($item->isDot()) {
            continue;
        }
        $item->isDir() ? $clean($item->getPathname()) : @unlink($item->getPathname());
    }
    @rmdir($path);
};
$clean($tmp);

if ($failures) {
    echo "\nRED_NOT_ACCEPTED: " . count($failures) . " unmet owner-contract checks\n";
    foreach ($failures as $failure) {
        echo "  - {$failure}\n";
    }
    exit(1);
}
echo "\nPASS: exact one-hour issuance and replay contract\n";
exit(0);
