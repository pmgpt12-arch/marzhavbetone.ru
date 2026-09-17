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

/**
 * Все проверки доступа и резерв скачивания — одной операцией под
 * исключительной блокировкой, по свежему состоянию заказа.
 *
 * Прежде заказ читался здесь, а записывался в конце прямым
 * file_put_contents() — мимо блокировки и мимо атомарной замены. Это давало
 * три разных неверных результата: потерянное обновление (запись поверх
 * того, что успел проставить вебхук), рваное чтение (конкурент видел
 * половину JSON, mvb_with_order_lock() возвращал null, а webhook.php всё
 * равно отвечал кассе 200 и та переставала повторять) и обход предела
 * скачиваний (несколько запросов читали одно и то же значение 29 и все
 * проходили проверку).
 *
 * Отдача файла вынесена НАРУЖУ блокировки намеренно: readfile() на архиве в
 * сотни килобайт держал бы на себе и вебхук, и страницу успеха. Под
 * блокировкой — только решение и счётчик.
 */
$reserve = mvb_with_order_lock_strict($orderFile, function (array &$locked) use ($token, $sku) {
    if (($locked['status'] ?? '') !== 'paid') {
        return ['deny' => [403, 'Оплата по заказу ещё не подтверждена. Если вы уже оплатили — подождите пару минут и обновите страницу.']];
    }

    $delivery = is_array($locked['delivery'] ?? null) ? $locked['delivery'] : [];

    if (empty($delivery['token']) || !hash_equals((string)$delivery['token'], $token)) {
        return ['deny' => [403, 'Ссылка недействительна.']];
    }

    if (!empty($delivery['expires_at']) && strtotime((string)$delivery['expires_at']) < time()) {
        return ['deny' => [410, 'Срок действия ссылки истёк.']];
    }

    if ((int)($delivery['downloads'] ?? 0) >= DELIVERY_MAX_DOWNLOADS) {
        return ['deny' => [429, 'Превышен лимит скачиваний по этой ссылке.']];
    }

    if (empty($delivery['items'][$sku])) {
        return ['deny' => [404, 'Этот материал не входит в ваш заказ.']];
    }

    // Резерв: счётчик растёт здесь, до отдачи файла. Не отданный архив
    // возвращает резерв обратно (см. ниже) — потерять скачивание покупателя
    // из-за нашей ошибки нельзя.
    $locked['delivery']['downloads'] = (int)($delivery['downloads'] ?? 0) + 1;
    $locked['delivery']['last_download_at'] = date('c');

    return ['zip' => basename((string)$delivery['items'][$sku])];
});

// Блокировку не взяли или заказ не читается как массив. Отвечать 200 и
// отдавать файл в этом состоянии нельзя: проверки не выполнялись.
if (!$reserve['ok']) {
    deny(503, 'Заказ сейчас обрабатывается. Обновите страницу через минуту.');
}

$decision = $reserve['result'];
if (isset($decision['deny'])) {
    deny($decision['deny'][0], $decision['deny'][1]);
}

$zipPath = DELIVERY_DIR . '/' . $decision['zip'];
if (!is_file($zipPath)) {
    // Архив мог быть очищен — пересобираем из исходников. Вне блокировки:
    // сборка идёт по диску и держать на ней заказ незачем.
    $zipPath = mvb_build_product_zip($sku) ?? '';
}

if ($zipPath === '' || !is_file($zipPath)) {
    // Файла нет и собрать не вышло. Резерв снимаем: скачивания не было.
    mvb_with_order_lock_strict($orderFile, function (array &$locked) {
        $locked['delivery']['downloads'] = max(0, (int)($locked['delivery']['downloads'] ?? 1) - 1);
        return null;
    });
    deny(500, 'Файл временно недоступен. Напишите нам — вышлем архив вручную.');
}

header('Content-Type: application/zip');
header('Content-Disposition: attachment; filename="' . basename($zipPath) . '"');
header('Content-Length: ' . filesize($zipPath));
header('X-Content-Type-Options: nosniff');
readfile($zipPath);
