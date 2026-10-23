<?php
/**
 * Выдача купленных материалов по одноразовой ссылке из письма.
 * Параметры: o — ID заказа, t — токен выдачи, f — sku продукта.
 */
declare(strict_types=1);

require __DIR__ . '/config.php';
require __DIR__ . '/products-config.php';

/** Private, idempotent observations; never a condition of serving the archive. */
function mvb_download_observe(string $orderId, string $requestedSku, array $outcome): void
{
    try {
        $funnel = __DIR__ . '/mvb_funnel.php';
        if (!is_file($funnel)) return;
        require_once $funnel;
        mvb_funnel_release();
        $reason = null;
        if (!mvb_funnel_outbox_usable($reason)) return;
        // This is a receipt journal, not another delivery queue. The existing
        // collector receives only the canonical successful-delivery event.
        $dir = mvb_funnel_outbox_dir() . '/download-receipts';
        if (mvb_funnel_outbox_inside_docroot($dir)) return;
        if (!is_dir($dir) && !@mkdir($dir, 0700, true) && !is_dir($dir)) return;
        $file = $dir . '/' . hash('sha256', $orderId) . '.json';
        // Initialise under the SAME lock used by the existing atomic writer.
        // Never overwrite a receipt created by a concurrent first request.
        $init = @fopen($file . '.lock', 'c');
        if ($init === false) return;
        if (!@flock($init, LOCK_EX)) { fclose($init); return; }
        try {
            if (!is_file($file) && !mvb_write_order($file, ['events' => new stdClass()], false)) return;
        } finally {
            @flock($init, LOCK_UN);
            fclose($init);
        }
        $sku = isset(mvb_products()[$requestedSku]) ? $requestedSku : null;
        mvb_with_order_lock_strict($file, function (array &$receipt) use ($orderId, $sku, $outcome) {
            foreach ([['event_type' => 'download.link_opened', 'status' => null, 'reason' => null], $outcome] as $observation) {
                $type = $observation['event_type'];
                $key = $type . ':' . ($sku ?? 'unknown') . ':' . ($observation['reason'] ?? '');
                if (!isset($receipt['events'][$key])) {
                    $h = hash('sha256', "nsp:download\0" . $orderId . "\0" . $key);
                    $receipt['events'][$key] = [
                        'event_type' => $type,
                        'event_uuid' => substr($h, 0, 8) . '-' . substr($h, 8, 4) . '-4'
                            . substr($h, 13, 3) . '-8' . substr($h, 17, 3) . '-' . substr($h, 20, 12),
                        'occurred_at' => gmdate('c'), 'sku' => $sku,
                        'status' => $observation['status'], 'reason' => $observation['reason'],
                    ];
                }
                $event = &$receipt['events'][$key];
                if ($type === 'download.file_served' && $sku !== null && empty($event['queued'])) {
                    // Stable UUID also protects downstream counting if a process
                    // dies after append but before the receipt's atomic rename.
                    $event['queued'] = mvb_funnel_event('funnel.product_delivered', [
                        'event_uuid' => $event['event_uuid'], 'occurred_at' => $event['occurred_at'],
                        'sku' => $sku, 'source' => 'site',
                    ]);
                }
                unset($event);
            }
            return null;
        });
    } catch (Throwable $ignored) {
        // No telemetry failure changes the file, HTTP response, or access policy.
    }
}

function deny(int $code, string $message): void
{
    global $downloadOutcome;
    $downloadOutcome = ['event_type' => 'download.failed', 'status' => $code,
        'reason' => [400 => 'invalid_link', 403 => 'access_denied', 404 => 'not_found',
                     410 => 'expired', 429 => 'download_limit', 500 => 'file_unavailable',
                     503 => 'server_error'][$code] ?? 'server_error'];
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

// GET means an endpoint was opened, not that a file was received. HEAD is
// excluded. Observe only existing orders, so invented IDs cannot fill storage.
$downloadOutcome = ['event_type' => 'download.failed', 'status' => 500, 'reason' => 'server_error'];
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'GET') {
    register_shutdown_function(function () use ($orderId, $sku, &$downloadOutcome) {
        mvb_download_observe($orderId, $sku, $downloadOutcome);
    });
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

    if (!empty($delivery['expires_at']) && strtotime((string)$delivery['expires_at']) <= time()) {
        return ['deny' => [410, 'Срок действия ссылки истёк.']];
    }

    if ((int)($delivery['downloads'] ?? 0) >= DELIVERY_MAX_DOWNLOADS) {
        return ['deny' => [429, 'Превышен лимит скачиваний по этой ссылке.']];
    }

    if (empty($delivery['items'][$sku])) {
        return ['deny' => [404, 'Этот материал не входит в ваш заказ.']];
    }

    $edition = $sku === 'p1' ? ($delivery['editions'][$sku] ?? null) : null;
    if ($sku === 'p1' && $edition === null) {
        foreach (($locked['items'] ?? []) as $position) {
            if (($position['sku'] ?? '') === $sku && isset($position['edition'])) {
                $edition = $position['edition'];
                break;
            }
        }
    }
    if ($edition !== null) {
        $pinnedPath = mvb_p1_edition_path($edition);
        if ($pinnedPath === null || basename($pinnedPath) !== $delivery['items'][$sku]) {
            return ['deny' => [500, 'Файл временно недоступен. Напишите нам — проверим комплект.']];
        }
    }
    // Legacy P1 без снимка также нельзя восстанавливать из новой редакции.
    if ($sku === 'p1' && !is_file(DELIVERY_DIR . '/' . basename((string)$delivery['items'][$sku]))) {
        return ['deny' => [500, 'Файл временно недоступен. Напишите нам — проверим комплект.']];
    }

    // Резерв: счётчик растёт здесь, до отдачи файла. Не отданный архив
    // возвращает резерв обратно (см. ниже) — потерять скачивание покупателя
    // из-за нашей ошибки нельзя.
    $locked['delivery']['downloads'] = (int)($delivery['downloads'] ?? 0) + 1;
    $locked['delivery']['last_download_at'] = date('c');

    return ['zip' => basename((string)$delivery['items'][$sku]), 'pinned' => $edition !== null];
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
if (!is_file($zipPath) && !$decision['pinned'] && $sku !== 'p1') {
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
$downloadName = $decision['pinned'] ? (mvb_products()[$sku]['zip'] ?? basename($zipPath)) : basename($zipPath);
header('Content-Disposition: attachment; filename="' . $downloadName . '"');
header('Content-Length: ' . filesize($zipPath));
header('X-Content-Type-Options: nosniff');
$sent = readfile($zipPath);
// A full server-side write, not a click or proof of saving on the buyer's device.
if ($sent !== false && $sent === filesize($zipPath) && !connection_aborted()) {
    $downloadOutcome = ['event_type' => 'download.file_served', 'status' => 200, 'reason' => null];
} else {
    $downloadOutcome = ['event_type' => 'download.failed', 'status' => 500, 'reason' => 'read_failed'];
}
