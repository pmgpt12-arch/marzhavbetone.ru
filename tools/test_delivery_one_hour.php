<?php
/**
 * R3 delivery acceptance: approved one-hour download window, synthetic data only.
 * Run: php tools/test_delivery_one_hour.php
 * Does NOT send email, access real orders, use a payment API or change production.
 */
declare(strict_types=1);

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-hour-qa-' . getmypid() . '-' . bin2hex(random_bytes(3));
$masters = $tmp . '/masters';
@mkdir($masters, 0700, true);
function hour_qa_rm(string $path): void {
    if (!file_exists($path)) return;
    if (is_dir($path)) {
        foreach (scandir($path) ?: [] as $item) {
            if ($item !== '.' && $item !== '..') hour_qa_rm($path . '/' . $item);
        }
        @rmdir($path);
    } else @unlink($path);
}
register_shutdown_function(static function () use ($tmp): void { hour_qa_rm($tmp); });
foreach ([
    'ORDERS_DIR' => $tmp . '/orders',
    'PRODUCTS_DIR' => $masters,
    'SITE_URL' => 'https://example.invalid',
    'ADMIN_EMAIL' => 'qa@example.invalid',
    'YOOKASSA_SHOP_ID' => 'test',
    'YOOKASSA_SECRET_KEY' => 'test',
    'YOOKASSA_API_URL' => 'https://example.invalid',
    'YOOKASSA_MODE' => 'test',
] as $key => $value) {
    if (!defined($key)) define($key, $value);
}
require $root . '/products-config.php';

$assertions = 0;
function hour_qa_check(bool $condition, string $label): void {
    global $assertions;
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$label}\n");
        exit(1);
    }
    $assertions++;
    echo "PASS: {$label}\n";
}
hour_qa_check(defined('DELIVERY_TTL_SECONDS') && DELIVERY_TTL_SECONDS === 3600, '3600 second TTL');
hour_qa_check(mvb_delivery_link_expired([]), 'missing expiry blocks access');
hour_qa_check(mvb_delivery_link_expired(['expires_at' => 'broken-date']), 'malformed expiry blocks access');
$reference = time();
hour_qa_check(!mvb_delivery_link_expired(['expires_at' => date('c', $reference + 1)], $reference), 'future expiry permits');
hour_qa_check(mvb_delivery_link_expired(['expires_at' => date('c', $reference)], $reference), 'exact deadline blocks');
hour_qa_check(mvb_delivery_link_expired(['expires_at' => date('c', $reference - 1)], $reference), 'past expiry blocks');

$catalog = mvb_products();
$sku = 'p7';
hour_qa_check(isset($catalog[$sku]['dir'], $catalog[$sku]['price']), 'catalog sku p7 exists');
$folder = $masters . '/' . $catalog[$sku]['dir'];
@mkdir($folder, 0700, true);
file_put_contents($folder . '/01-example.txt', "Synthetic nonbuyer data\n");
$order = [
    'id' => 'order_20261016_080000_abc123',
    'status' => 'paid',
    'items' => [[
        'sku' => $sku,
        'name' => $catalog[$sku]['name'],
        'price' => $catalog[$sku]['price']
    ]],
    'total' => $catalog[$sku]['price']
];
$planned = mvb_prepare_delivery($order);
hour_qa_check(!$planned['missing'] && count($planned['links']) === 1, 'one paid item fully prepared');
$delivery = $order['delivery'] ?? [];
$created = strtotime((string)($delivery['created_at'] ?? ''));
$expires = strtotime((string)($delivery['expires_at'] ?? ''));
hour_qa_check($created !== false && $expires !== false && ($expires-$created)===3600, 'issued link expires exactly one hour after creation');
hour_qa_check(strlen((string)($delivery['token'] ?? ''))===32, 'random 128-bit token');
hour_qa_check(!mvb_delivery_link_expired($delivery, $created+3599), 'valid through second 3599');
hour_qa_check(mvb_delivery_link_expired($delivery, $created+3600), 'blocked at second 3600');
hour_qa_check(str_contains($planned['links'][0]['url'], 'example.invalid/download.php?'), 'correct download route');
$email = mvb_delivery_email($order, $planned['links']);
hour_qa_check(str_contains($email, 'Ссылки действуют 1 час'), 'buyer email promises one hour');
hour_qa_check(!str_contains($email, '30 дней'), 'buyer email does not promise 30 days');
hour_qa_check(str_contains($email, 'На стороне подрядчика'), 'buyer email uses approved brand');

// An already issued link with an explicit expiry is NEVER extended on a
// repeated webhook, regardless of whether it predates the rebrand.
$already = $order;
$already['delivery']['expires_at'] = date('c', $reference + 86400);
$already['delivery']['downloads'] = 2;
$token = $already['delivery']['token'];
$replayed = mvb_prepare_delivery($already);
hour_qa_check(!$replayed['missing'] && count($replayed['links'])===1, 'existing unexpired order reusable');
hour_qa_check($already['delivery']['expires_at'] === date('c', $reference + 86400), 'historical absolute expiry preserved');
hour_qa_check($already['delivery']['token'] === $token && $already['delivery']['downloads'] === 2, 'existing token and download counter unchanged');
$expiredOrder = $order;
$expiredOrder['delivery']['expires_at'] = date('c', $reference - 1);
$original = $expiredOrder;
$blocked = mvb_prepare_delivery($expiredOrder);
hour_qa_check($blocked['links'] === [] && count($blocked['missing']) > 0, 'expired token cannot be silently reissued');
hour_qa_check($expiredOrder === $original, 'expired order record not mutated');
$missingDate = $order;
unset($missingDate['delivery']['expires_at']);
$before = $missingDate;
$blockedMissing = mvb_prepare_delivery($missingDate);
hour_qa_check($blockedMissing['links'] === [] && $missingDate === $before, 'legacy token without expiry cannot be renewed');

echo "\nTOTAL_PASS={$assertions} ONE_HOUR_DELIVERY_VERIFIED\n";
