<?php
/**
 * RED contract: immutable closed payment_record in the existing order JSON.
 *
 * Deterministic and offline: no YooKassa, SMTP, production storage, deploy,
 * archive creation, model, or paid API calls.
 */
declare(strict_types=1);

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-payment-record-' . getmypid();
@mkdir($tmp . '/orders/delivery', 0777, true);
@mkdir($tmp . '/products', 0777, true);

foreach ([
    'ORDERS_DIR' => $tmp . '/orders',
    'DELIVERY_DIR' => $tmp . '/orders/delivery',
    'PRODUCTS_DIR' => $tmp . '/products',
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
$expectReject = static function (string $name, callable $fn) use ($check): void {
    try {
        $fn();
        $check($name, false, 'accepted conflicting immutable fact');
    } catch (Throwable $error) {
        $check($name, true);
    }
};

echo "Closed payment_record contract\n";

if (!function_exists('mvb_build_payment_record')) {
    $check('runtime exposes mvb_build_payment_record', false, 'function missing');
} else {
    $order = [
        'id' => 'order_20261014_ledger',
        'email' => 'buyer@example.invalid',
        'delivery' => [
            'expires_at' => '2026-10-14T11:15:30+00:00',
            'token' => 'must-not-enter-ledger',
            'items' => [['sku' => 'p3', 'path' => '/private/archive.zip']],
        ],
    ];
    $payment = [
        'id' => '2f7f0000-000f-5000-9000-1eadbeef0001',
        'status' => 'succeeded',
        'amount' => ['value' => '29900.00', 'currency' => 'RUB'],
        'captured_at' => '2026-10-14T10:15:30.123Z',
        'metadata' => ['order_id' => $order['id']],
    ];

    $record = mvb_build_payment_record($order, $payment);
    $check('exact closed-ledger keys', array_keys($record) === [
        'schema_version',
        'order_id',
        'payment_id',
        'email',
        'amount_value',
        'amount_currency',
        'provider_paid_at',
        'delivery_expires_at',
    ], json_encode(array_keys($record), JSON_UNESCAPED_UNICODE));
    $check('schema version is 1', ($record['schema_version'] ?? null) === 1);
    $check('order id preserved', ($record['order_id'] ?? null) === $order['id']);
    $check('payment id preserved', ($record['payment_id'] ?? null) === $payment['id']);
    $check('buyer email preserved', ($record['email'] ?? null) === $order['email']);
    $check('actual provider amount preserved', ($record['amount_value'] ?? null) === '29900.00');
    $check('provider currency preserved', ($record['amount_currency'] ?? null) === 'RUB');
    $check('provider captured time preserved', ($record['provider_paid_at'] ?? null) === $payment['captured_at']);
    $check('delivery expiry preserved', ($record['delivery_expires_at'] ?? null) === $order['delivery']['expires_at']);

    $replay = $order;
    $replay['payment_record'] = $record;
    $replay['delivery']['expires_at'] = '2026-10-14T12:15:30+00:00';
    $check('same payment replay is byte-identical and cannot extend expiry',
        mvb_build_payment_record($replay, $payment) === $record);

    $changedAmount = $payment;
    $changedAmount['amount']['value'] = '29901.00';
    $expectReject('changed accepted amount fails closed',
        static fn() => mvb_build_payment_record($replay, $changedAmount));

    $changedPayment = $payment;
    $changedPayment['id'] = '2f7f0000-000f-5000-9000-1eadbeef0002';
    $expectReject('changed payment id fails closed',
        static fn() => mvb_build_payment_record($replay, $changedPayment));

    $wrongOrder = $payment;
    $wrongOrder['metadata']['order_id'] = 'order_20261014_other';
    $expectReject('mismatched provider order id fails closed',
        static fn() => mvb_build_payment_record($order, $wrongOrder));

    $encoded = json_encode($record, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    $check('record contains no token/archive/document payload',
        strpos((string)$encoded, 'token') === false
        && strpos((string)$encoded, 'archive') === false
        && strpos((string)$encoded, 'items') === false
        && strpos((string)$encoded, '/private/') === false);
}

if ($failures) {
    echo "\nRED_NOT_ACCEPTED: " . count($failures) . " unmet payment_record checks\n";
    foreach ($failures as $failure) {
        echo "  - {$failure}\n";
    }
    exit(1);
}
echo "\nPASS: immutable closed payment_record contract\n";
exit(0);
