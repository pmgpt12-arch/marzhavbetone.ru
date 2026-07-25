<?php
/**
 * Создание платежа через ЮКасса
 * Принимает POST-запрос с данными корзины
 */
declare(strict_types=1);

require __DIR__ . '/config.php';
require __DIR__ . '/products-config.php';

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

// Проверка, что ключи ЮKassa заполнены в config.php
if (YOOKASSA_SHOP_ID === 'ВАШ_SHOP_ID' || YOOKASSA_SECRET_KEY === 'ВАШ_SECRET_KEY') {
    http_response_code(500);
    echo json_encode(['ok' => false, 'message' => 'Оплата временно недоступна. Напишите нам в Telegram — поможем оформить заказ.'], JSON_UNESCAPED_UNICODE);
    @file_put_contents(ORDERS_DIR . '/payment-errors.log', date('c') . " config: не заполнены YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY\n", FILE_APPEND);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'message' => 'Метод не поддерживается'], JSON_UNESCAPED_UNICODE);
    exit;
}

// Получаем данные
$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    http_response_code(422);
    echo json_encode(['ok' => false, 'message' => 'Некорректные данные'], JSON_UNESCAPED_UNICODE);
    exit;
}

$items = $input['items'] ?? [];
$email = trim((string)($input['email'] ?? ''));
$phone = trim((string)($input['phone'] ?? ''));

if (empty($items)) {
    http_response_code(422);
    echo json_encode(['ok' => false, 'message' => 'Корзина пуста'], JSON_UNESCAPED_UNICODE);
    exit;
}

if ($email === '' && $phone === '') {
    http_response_code(422);
    echo json_encode(['ok' => false, 'message' => 'Укажите email или телефон'], JSON_UNESCAPED_UNICODE);
    exit;
}

// Сверяем позиции с каталогом: цена берётся с сервера, а не из запроса клиента
$total = 0;
$descriptionParts = [];
$validatedItems = [];
foreach ($items as $item) {
    $product = mvb_resolve_product((array)$item);
    if (!$product) {
        http_response_code(422);
        echo json_encode(['ok' => false, 'message' => 'Товар не найден в каталоге. Обновите страницу и соберите корзину заново.'], JSON_UNESCAPED_UNICODE);
        exit;
    }
    $total += $product['price'];
    $descriptionParts[] = $product['name'];
    $validatedItems[] = [
        'sku'   => $product['sku'],
        'name'  => $product['name'],
        'price' => $product['price'],
    ];
}
$items = $validatedItems;

if ($total <= 0) {
    http_response_code(422);
    echo json_encode(['ok' => false, 'message' => 'Некорректная сумма заказа'], JSON_UNESCAPED_UNICODE);
    exit;
}

// Описание платежа (макс 128 символов)
$description = implode(', ', $descriptionParts);
if (mb_strlen($description) > 120) {
    $description = mb_substr($description, 0, 120) . '...';
}

// Генерируем ID заказа
$orderId = 'order_' . date('Ymd_His') . '_' . substr(uniqid(), -6);

// Сохраняем заказ
$orderData = [
    'id' => $orderId,
    'created_at' => date('c'),
    'status' => 'pending',
    'email' => $email,
    'phone' => $phone,
    'items' => $items,
    'total' => $total,
    'description' => $description,
    'payment_id' => null,
    'paid_at' => null,
];

file_put_contents(ORDERS_DIR . '/' . $orderId . '.json', json_encode($orderData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

// Создаём платеж в ЮКассе
$paymentData = [
    'amount' => [
        'value' => number_format($total / 100, 2, '.', ''),
        'currency' => 'RUB',
    ],
    'capture' => true,
    'confirmation' => [
        'type' => 'redirect',
        'return_url' => SITE_URL . '/success.html?order=' . urlencode($orderId),
    ],
    'description' => $description,
    'metadata' => [
        'order_id' => $orderId,
        'customer_email' => $email,
        'customer_phone' => $phone,
    ],
    'receipt' => [
        'customer' => [
            'email' => $email ?: 'no-email@example.com',
        ],
        'items' => [],
    ],
];

// Добавляем позиции для чека
foreach ($items as $item) {
    $paymentData['receipt']['items'][] = [
        'description' => $item['name'] ?? 'Товар',
        'quantity' => '1.00',
        'amount' => [
            'value' => number_format((int)$item['price'] / 100, 2, '.', ''),
            'currency' => 'RUB',
        ],
        'vat_code' => 1, // Без НДС
        'payment_subject' => 'commodity',
        'payment_mode' => 'full_payment',
    ];
}

// Отправляем запрос в ЮКасса
$ch = curl_init(YOOKASSA_API_URL . '/payments');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => json_encode($paymentData),
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'Idempotence-Key: ' . $orderId,
    ],
    CURLOPT_USERPWD => YOOKASSA_SHOP_ID . ':' . YOOKASSA_SECRET_KEY,
    CURLOPT_CONNECTTIMEOUT => 10,
    CURLOPT_TIMEOUT => 30,
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curlError = curl_error($ch);
curl_close($ch);

// Логируем ошибки для диагностики
if ($curlError || $httpCode !== 200) {
    $logLine = date('c') . ' order=' . $orderId . ' http=' . $httpCode . ' curl=' . $curlError . ' response=' . mb_substr((string)$response, 0, 500) . "\n";
    @file_put_contents(ORDERS_DIR . '/payment-errors.log', $logLine, FILE_APPEND);
}

if ($curlError) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'message' => 'Ошибка соединения с платёжной системой. Попробуйте ещё раз через минуту.'], JSON_UNESCAPED_UNICODE);
    exit;
}

$payment = json_decode($response, true);

if ($httpCode !== 200 || empty($payment['id'])) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'message' => 'Не удалось создать платёж',
        'debug' => YOOKASSA_MODE === 'test' ? $payment : null,
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// Сохраняем payment_id
$orderData['payment_id'] = $payment['id'];
file_put_contents(ORDERS_DIR . '/' . $orderId . '.json', json_encode($orderData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

// Возвращаем URL для оплаты
$confirmationUrl = $payment['confirmation']['confirmation_url'] ?? null;

if (!$confirmationUrl) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'message' => 'Не получен URL для оплаты'], JSON_UNESCAPED_UNICODE);
    exit;
}

echo json_encode([
    'ok' => true,
    'payment_url' => $confirmationUrl,
    'order_id' => $orderId,
], JSON_UNESCAPED_UNICODE);
