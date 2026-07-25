<?php
/**
 * Выдача купленных материалов по одноразовой ссылке из письма.
 * Параметры: o — ID заказа, t — токен выдачи, f — sku продукта.
 */
declare(strict_types=1);

require __DIR__ . '/config.php';
require __DIR__ . '/products-config.php';

function deny(int $code, string $message): void
{
    http_response_code($code);
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><meta charset="utf-8"><title>Скачивание недоступно</title>'
        . '<body style="font-family:sans-serif;max-width:560px;margin:80px auto;padding:0 16px">'
        . '<h1 style="font-size:22px">Скачивание недоступно</h1>'
        . '<p>' . htmlspecialchars($message, ENT_QUOTES) . '</p>'
        . '<p>Напишите нам: <a href="mailto:' . ADMIN_EMAIL . '">' . ADMIN_EMAIL . '</a> — поможем.</p>';
    exit;
}

$orderId = (string)($_GET['o'] ?? '');
$token   = (string)($_GET['t'] ?? '');
$sku     = (string)($_GET['f'] ?? '');

if (!preg_match('/^order_[0-9_]+_[a-z0-9]+$/i', $orderId) || $token === '' || $sku === '') {
    deny(400, 'Некорректная ссылка. Проверьте, что скопировали её из письма целиком.');
}

$orderFile = ORDERS_DIR . '/' . $orderId . '.json';
if (!is_file($orderFile)) {
    deny(404, 'Заказ не найден.');
}

$order = json_decode((string)file_get_contents($orderFile), true);
if (!$order) {
    deny(500, 'Не удалось прочитать данные заказа.');
}

if (($order['status'] ?? '') !== 'paid') {
    deny(403, 'Оплата по заказу ещё не подтверждена. Если вы уже оплатили — подождите пару минут и обновите страницу.');
}

$delivery = $order['delivery'] ?? [];
if (empty($delivery['token']) || !hash_equals((string)$delivery['token'], $token)) {
    deny(403, 'Ссылка недействительна.');
}

if (!empty($delivery['expires_at']) && strtotime((string)$delivery['expires_at']) < time()) {
    deny(410, 'Срок действия ссылки истёк.');
}

if ((int)($delivery['downloads'] ?? 0) >= DELIVERY_MAX_DOWNLOADS) {
    deny(429, 'Превышен лимит скачиваний по этой ссылке.');
}

if (empty($delivery['items'][$sku])) {
    deny(404, 'Этот материал не входит в ваш заказ.');
}

$zipPath = DELIVERY_DIR . '/' . basename((string)$delivery['items'][$sku]);
if (!is_file($zipPath)) {
    // Архив мог быть очищен — пересобираем из исходников
    $zipPath = mvb_build_product_zip($sku) ?? '';
    if ($zipPath === '' || !is_file($zipPath)) {
        deny(500, 'Файл временно недоступен. Напишите нам — вышлем архив вручную.');
    }
}

// Считаем скачивание
$order['delivery']['downloads'] = (int)($delivery['downloads'] ?? 0) + 1;
$order['delivery']['last_download_at'] = date('c');
file_put_contents($orderFile, json_encode($order, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

header('Content-Type: application/zip');
header('Content-Disposition: attachment; filename="' . basename($zipPath) . '"');
header('Content-Length: ' . filesize($zipPath));
header('X-Content-Type-Options: nosniff');
readfile($zipPath);
