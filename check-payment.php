<?php
/**
 * Проверка статуса заказа
 * Используется со страницы success.html для получения данных о заказе
 */
declare(strict_types=1);

require __DIR__ . '/config.php';

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'message' => 'Метод не поддерживается'], JSON_UNESCAPED_UNICODE);
    exit;
}

$orderId = trim((string)($_GET['order'] ?? ''));
if ($orderId === '') {
    http_response_code(422);
    echo json_encode(['ok' => false, 'message' => 'Не указан ID заказа'], JSON_UNESCAPED_UNICODE);
    exit;
}

// Проверяем безопасность ID заказа
if (!preg_match('/^order_\d{8}_\d{6}_[a-z0-9]{6}$/', $orderId)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'message' => 'Некорректный ID заказа'], JSON_UNESCAPED_UNICODE);
    exit;
}

$orderFile = ORDERS_DIR . '/' . $orderId . '.json';
if (!file_exists($orderFile)) {
    http_response_code(404);
    echo json_encode(['ok' => false, 'message' => 'Заказ не найден'], JSON_UNESCAPED_UNICODE);
    exit;
}

$order = json_decode(file_get_contents($orderFile), true);
if (!$order) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'message' => 'Ошибка чтения заказа'], JSON_UNESCAPED_UNICODE);
    exit;
}

// Если платёж ожидает подтверждения — проверим статус в ЮКассе
if (!empty($order['payment_id']) && in_array($order['status'] ?? '', ['pending', 'waiting_for_capture'])) {
    $ch = curl_init(YOOKASSA_API_URL . '/payments/' . $order['payment_id']);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_USERPWD => YOOKASSA_SHOP_ID . ':' . YOOKASSA_SECRET_KEY,
        CURLOPT_TIMEOUT => 15,
    ]);
    $response = curl_exec($ch);
    curl_close($ch);
    
    if ($response) {
        $payment = json_decode($response, true);
        if (!empty($payment['status'])) {
            $order['payment_status'] = $payment['status'];
            
            if ($payment['status'] === 'succeeded') {
                $order['status'] = 'paid';
                $order['paid_at'] = $order['paid_at'] ?? date('c');
            } elseif ($payment['status'] === 'canceled') {
                $order['status'] = 'canceled';
            }
            
            file_put_contents($orderFile, json_encode($order, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        }
    }
}

// Возвращаем данные заказа (без чувствительных полей)
echo json_encode([
    'ok' => true,
    'order' => [
        'id' => $order['id'],
        'status' => $order['status'],
        'total' => $order['total'],
        'items' => $order['items'],
        'email' => $order['email'],
        'paid_at' => $order['paid_at'] ?? null,
    ],
], JSON_UNESCAPED_UNICODE);
