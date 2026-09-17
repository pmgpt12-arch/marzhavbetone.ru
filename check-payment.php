<?php
/**
 * Проверка статуса заказа
 * Используется со страницы success.html для получения данных о заказе
 */
declare(strict_types=1);

require __DIR__ . '/config.php';
require __DIR__ . '/products-config.php';

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'message' => 'Метод не поддерживается'], JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * Отказ одной формы на все случаи: нет ключа, ключ не тот, заказа не
 * существует, идентификатор кривой. Ответ обязан быть неотличим, иначе он
 * сам становится ответом на вопрос «а есть ли такой заказ».
 */
function refuse(): void
{
    http_response_code(403);
    echo json_encode([
        'ok'      => false,
        'message' => 'Ссылка недействительна. Откройте страницу по адресу из письма или обратитесь к нам.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$orderId = trim((string)($_GET['order'] ?? ''));
$statusKey = (string)($_GET['key'] ?? $_GET['k'] ?? '');

// Идентификатор заказа секретом не является (см. комментарий в payment.php),
// поэтому одного его мало. Ключ проверяется ДО чтения заказа и до любого
// обращения к кассе: ни статус, ни сумма, ни состав, ни факт существования
// заказа наружу без ключа не выходят.
if ($orderId === '' || $statusKey === ''
    || !preg_match('/^order_\d{8}_\d{6}_[a-z0-9]{6}$/', $orderId)) {
    refuse();
}

$orderFile = ORDERS_DIR . '/' . $orderId . '.json';
if (!file_exists($orderFile)) {
    refuse();
}

$order = json_decode(file_get_contents($orderFile), true);
if (!is_array($order)) {
    refuse();
}

// Заказы, созданные до появления ключа, ключа не имеют. Небезопасного отката
// «нет ключа — пустим по одному номеру» здесь нет: это вернуло бы ровно ту
// утечку, ради которой ключ и заведён. Покупателю — нейтральный отказ с
// адресом для связи; ранее выданные ссылки скачивания при этом продолжают
// работать, они проверяются своим токеном в download.php и от ключа не
// зависят.
$hash = (string)($order['status_key_hash'] ?? '');
if ($hash === '' || !hash_equals($hash, hash('sha256', $statusKey))) {
    refuse();
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
            
            mvb_with_order_lock($orderFile, function (array &$locked) use ($payment) {
                $locked['payment_status'] = $payment['status'];
                if ($payment['status'] === 'succeeded') {
                    $locked['status'] = 'paid';
                    $locked['paid_at'] = $locked['paid_at'] ?? date('c');
                } elseif ($payment['status'] === 'canceled') {
                    $locked['status'] = 'canceled';
                }
                return null;
            });
        }
    }
}

// Для оплаченного заказа готовим выдачу (подстраховка, если вебхук ещё не
// пришёл). Под блокировкой: этот запрос и webhook.php идут одновременно —
// покупатель возвращается на success.html ровно тогда, когда касса шлёт
// уведомление. Без блокировки оба видели пустое delivery.email_sent_at и
// слали письмо дважды.
$downloadLinks = [];
if (($order['status'] ?? '') === 'paid') {
    $downloadLinks = mvb_with_order_lock($orderFile, function (array &$locked) {
        return mvb_deliver_and_notify($locked);
    }) ?: [];
    // Свежая копия: под блокировкой заказ мог быть дополнен вторым процессом.
    $fresh = json_decode((string)@file_get_contents($orderFile), true);
    if (is_array($fresh)) {
        $order = $fresh;
    }
}

// Наружу идёт только то, что success.html действительно читает: статус,
// сумма, состав (sku, название, цена) и ссылки выдачи. Почта покупателя,
// телефон, номер платежа, атрибуция и хеш ключа со страницы не читаются
// ни одной строкой и в ответе не нужны — проверено по самой странице.
// Сырых токенов здесь нет: токен выдачи существует только внутри готовых
// адресов download.php, отдельным полем не публикуется.
$publicItems = [];
foreach ($order['items'] ?? [] as $item) {
    $publicItems[] = [
        'sku'   => (string)($item['sku'] ?? ''),
        'name'  => (string)($item['name'] ?? ''),
        'price' => (int)($item['price'] ?? 0),
    ];
}

echo json_encode([
    'ok' => true,
    'order' => [
        'status'    => $order['status'] ?? 'pending',
        'total'     => (int)($order['total'] ?? 0),
        'items'     => $publicItems,
        'downloads' => $downloadLinks,
    ],
], JSON_UNESCAPED_UNICODE);
