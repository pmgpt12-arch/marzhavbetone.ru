<?php
/**
 * Webhook для получения уведомлений от ЮКасса
 * 
 * URL для настройки в личном кабинете ЮКасса:
 * https://marzhavbetone.ru/webhook.php
 */
declare(strict_types=1);

require __DIR__ . '/config.php';
require __DIR__ . '/products-config.php';

header('Content-Type: application/json; charset=utf-8');

// Получаем тело запроса
$body = file_get_contents('php://input');
$event = json_decode($body, true);

if (!$event || empty($event['event']) || empty($event['object'])) {
    http_response_code(400);
    echo json_encode(['ok' => false], JSON_UNESCAPED_UNICODE);
    exit;
}

$paymentId = $event['object']['id'] ?? '';

if (!$paymentId) {
    http_response_code(400);
    echo json_encode(['ok' => false], JSON_UNESCAPED_UNICODE);
    exit;
}

// Проверяем подлинность: запрашиваем платёж напрямую в API ЮKassa.
// Это защищает от поддельных уведомлений — доверяем только данным из API.
$ch = curl_init(YOOKASSA_API_URL . '/payments/' . urlencode($paymentId));
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_USERPWD => YOOKASSA_SHOP_ID . ':' . YOOKASSA_SECRET_KEY,
    CURLOPT_TIMEOUT => 15,
]);
$apiResponse = curl_exec($ch);
$apiCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

$payment = json_decode((string)$apiResponse, true);
if ($apiCode !== 200 || empty($payment['id'])) {
    http_response_code(400);
    echo json_encode(['ok' => false], JSON_UNESCAPED_UNICODE);
    exit;
}

$status = $payment['status'] ?? '';
$orderId = $payment['metadata']['order_id'] ?? '';

if (!$orderId) {
    http_response_code(400);
    echo json_encode(['ok' => false], JSON_UNESCAPED_UNICODE);
    exit;
}

// Находим заказ
$orderFile = ORDERS_DIR . '/' . $orderId . '.json';
if (!file_exists($orderFile)) {
    http_response_code(404);
    echo json_encode(['ok' => false], JSON_UNESCAPED_UNICODE);
    exit;
}

$order = json_decode(file_get_contents($orderFile), true);
if (!$order) {
    http_response_code(500);
    echo json_encode(['ok' => false], JSON_UNESCAPED_UNICODE);
    exit;
}

// Обновляем статус
$order['payment_status'] = $status;
$order['payment_id'] = $paymentId;
$order['updated_at'] = date('c');

// Обработка по реальному статусу платежа из API (а не по типу события)
switch ($status) {
    case 'succeeded':
        $alreadyPaid = ($order['status'] ?? '') === 'paid';
        $order['status'] = 'paid';
        $order['paid_at'] = $order['paid_at'] ?? date('c');
        
        // Отправляем email админу
        $itemsText = [];
        foreach ($order['items'] ?? [] as $item) {
            $price = number_format((int)$item['price'] / 100, 0, '', ' ');
            $itemsText[] = '- ' . ($item['name'] ?? 'Товар') . ' — ' . $price . ' ₽';
        }
        $totalFormatted = number_format($order['total'] / 100, 0, '', ' ');
        
        $subject = '✅ Оплачен заказ ' . $orderId;
        $emailBody = "Новый оплаченный заказ:\n\n";
        $emailBody .= "ID заказа: {$orderId}\n";
        $emailBody .= "Email: " . ($order['email'] ?: 'не указан') . "\n";
        $emailBody .= "Телефон: " . ($order['phone'] ?: 'не указан') . "\n";
        $emailBody .= "Сумма: {$totalFormatted} ₽\n\n";
        $emailBody .= "Товары:\n" . implode("\n", $itemsText) . "\n\n";
        $emailBody .= "Payment ID: {$paymentId}\n";
        $emailBody .= "Дата: " . date('d.m.Y H:i:s') . "\n";
        
        $headers = [
            'From: site@marzhavbetone.ru',
            'Reply-To: ' . ($order['email'] ?: ADMIN_EMAIL),
            'Content-Type: text/plain; charset=UTF-8',
        ];
        // Письмо отправляем только один раз — при первом переходе в «paid»
        if (!$alreadyPaid) {
            mail(ADMIN_EMAIL, '=?UTF-8?B?' . base64_encode($subject) . '?=', $emailBody, implode("\r\n", $headers));
        }

        // Автовыдача: архивы, ссылки, письмо покупателю (однократно)
        mvb_deliver_and_notify($order);
        break;
        
    case 'canceled':
        $order['status'] = 'canceled';
        break;
        
    case 'waiting_for_capture':
        $order['status'] = 'waiting_for_capture';
        break;
}

// Сохраняем обновлённый заказ
file_put_contents($orderFile, json_encode($order, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

// Отвечаем ЮКассе успехом
echo json_encode(['ok' => true], JSON_UNESCAPED_UNICODE);
