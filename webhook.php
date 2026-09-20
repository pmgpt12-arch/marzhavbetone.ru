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

// Всё изменение заказа — одной операцией под блокировкой. Этот процесс и
// check-payment.php работают одновременно (покупатель возвращается на
// success.html ровно тогда, когда касса шлёт уведомление), и разбиение на
// «прочитали здесь, записали там» — это и есть гонка: оба процесса видели
// пустое delivery.email_sent_at и слали покупателю письмо дважды, а запись,
// сделанная позже, затирала поля первой.
$adminMail = null;
mvb_with_order_lock($orderFile, function (array &$locked) use ($status, $paymentId, $orderId, &$adminMail) {
    $locked['payment_status'] = $status;
    $locked['payment_id'] = $paymentId;
    $locked['updated_at'] = date('c');

    switch ($status) {
        case 'succeeded':
            $locked['status'] = 'paid';
            $locked['paid_at'] = $locked['paid_at'] ?? date('c');

            // Признак «письмо админу уже уходило» лежит в самом заказе, а не
            // в переменной процесса: о повторной доставке вебхука переменная
            // ничего не знает, а поле знает.
            if (empty($locked['admin_notified_at'])) {
                $locked['admin_notified_at'] = date('c');
                $itemsText = [];
                foreach ($locked['items'] ?? [] as $item) {
                    $price = number_format((int)$item['price'] / 100, 0, '', ' ');
                    $itemsText[] = '- ' . ($item['name'] ?? 'Товар') . ' — ' . $price . ' ₽';
                }
                $totalFormatted = number_format($locked['total'] / 100, 0, '', ' ');
                $body  = "Новый оплаченный заказ:\n\n";
                $body .= "ID заказа: {$orderId}\n";
                $body .= 'Email: ' . ($locked['email'] ?: 'не указан') . "\n";
                $body .= 'Телефон: ' . ($locked['phone'] ?: 'не указан') . "\n";
                $body .= "Сумма: {$totalFormatted} ₽\n\n";
                $body .= "Товары:\n" . implode("\n", $itemsText) . "\n\n";
                $body .= "Payment ID: {$paymentId}\n";
                $body .= 'Дата: ' . date('d.m.Y H:i:s') . "\n";
                $adminMail = [
                    'subject' => '=?UTF-8?B?' . base64_encode('✅ Оплачен заказ ' . $orderId) . '?=',
                    'body'    => $body,
                    'headers' => implode("\r\n", [
                        'From: site@marzhavbetone.ru',
                        'Reply-To: ' . ($locked['email'] ?: ADMIN_EMAIL),
                        'Content-Type: text/plain; charset=UTF-8',
                    ]),
                ];
            }

            // Выдача обязана идти под той же блокировкой: её защита от
            // повтора — поле в этом же файле заказа.
            mvb_deliver_and_notify($locked);
            break;

        case 'canceled':
            $locked['status'] = 'canceled';
            break;

        case 'waiting_for_capture':
            $locked['status'] = 'waiting_for_capture';
            break;
    }
    return null;
});

// Письмо админу уходит после снятия блокировки: mail() может ждать SMTP, и
// держать на этом заказ значит держать на нём второй процесс.
if ($adminMail) {
    mail(ADMIN_EMAIL, $adminMail['subject'], $adminMail['body'], $adminMail['headers']);
}

// Отвечаем ЮКассе успехом
echo json_encode(['ok' => true], JSON_UNESCAPED_UNICODE);
