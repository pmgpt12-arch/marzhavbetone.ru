<?php
/**
 * Регресс на гонку выдачи. Запуск: php tools/test_order_lock.php
 *
 * Что проверяется. Выдачу оплаченного заказа зовут два независимых
 * процесса — webhook.php по уведомлению ЮKassa и check-payment.php по
 * заходу покупателя на success.html. Это не редкий случай: покупатель
 * возвращается на сайт ровно тогда, когда касса шлёт уведомление.
 *
 * Защита от повторной выдачи стоит на поле внутри самого заказа. Против
 * последовательных вызовов она работает, против одновременных — нет:
 * оба процесса читают файл до того, как любой успел записать, оба видят
 * пустое поле, оба выполняют однократное действие.
 *
 * Тест поднимает восемь процессов одновременно и требует, чтобы
 * однократное действие случилось ровно один раз, а поля, проставленные
 * разными процессами, не потерялись.
 *
 * Проверен мутацией 15.08.2026: если в mvb_with_order_lock() снять flock,
 * тест краснеет обоими признаками — «выдач 8 вместо 1» и «в заказе
 * отметился 1 процесс из 8». Без такой проверки тест доказывал бы только
 * то, что код запускается.
 */
declare(strict_types=1);

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-order-lock-' . getmypid();
@mkdir($tmp, 0777, true);

// Константы, которых ждёт products-config.php. Боевой config.php не
// читается и не нужен: проверяется блокировка, а не касса.
foreach ([
    'ORDERS_DIR' => $tmp,
    'SITE_URL' => 'https://example.invalid',
    'ADMIN_EMAIL' => 'admin@example.invalid',
    'DELIVERY_TTL_DAYS' => 7,
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

$orderFile = $tmp . '/order_20260815_120000_abc123.json';
file_put_contents($orderFile, json_encode([
    'id' => 'order_20260815_120000_abc123',
    'status' => 'paid',
    'email' => 'buyer@example.invalid',
    'items' => [],
    'total' => 249000,
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

$deliveryLog = $tmp . '/deliveries.log';
touch($deliveryLog);

// Дочерний процесс: берёт блокировку и выполняет «однократное действие».
$childScript = $tmp . '/child.php';
file_put_contents($childScript, <<<'PHP'
<?php
declare(strict_types=1);
[$script, $root, $orderFile, $deliveryLog, $tmpDir, $tag] = $argv;
foreach ([
    'ORDERS_DIR' => $tmpDir, 'SITE_URL' => 'https://example.invalid',
    'ADMIN_EMAIL' => 'a@example.invalid', 'DELIVERY_TTL_DAYS' => 7,
    'YOOKASSA_SHOP_ID' => 't', 'YOOKASSA_SECRET_KEY' => 't',
    'YOOKASSA_API_URL' => 'https://example.invalid', 'YOOKASSA_MODE' => 'test',
] as $n => $v) { if (!defined($n)) define($n, $v); }
require $root . '/products-config.php';

mvb_with_order_lock($orderFile, function (array &$order) use ($deliveryLog, $tag) {
    // Ровно та же форма защиты, что и в mvb_deliver_and_notify().
    if (empty($order['delivery']['email_sent_at'])) {
        // Пауза внутри критической секции: без блокировки она
        // гарантированно разводит процессы по разным чтениям, с
        // блокировкой — ничего не меняет.
        usleep(120000);
        file_put_contents($deliveryLog, $tag . "\n", FILE_APPEND);
        $order['delivery']['email_sent_at'] = date('c');
    }
    // Каждый процесс пишет своё поле: так видно потерянное обновление.
    $order['seen_by_' . $tag] = 1;
    return null;
});
PHP);

$workers = 8;
$procs = [];
for ($i = 0; $i < $workers; $i++) {
    $cmd = escapeshellcmd(PHP_BINARY) . ' ' . escapeshellarg($childScript) . ' '
        . escapeshellarg($root) . ' ' . escapeshellarg($orderFile) . ' '
        . escapeshellarg($deliveryLog) . ' ' . escapeshellarg($tmp) . ' ' . escapeshellarg((string)$i);
    $procs[] = proc_open($cmd, [1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes[$i]);
}
foreach ($procs as $k => $proc) {
    if (is_resource($proc)) {
        stream_get_contents($pipes[$k][1]);
        stream_get_contents($pipes[$k][2]);
        proc_close($proc);
    }
}

$deliveries = array_filter(explode("\n", (string)file_get_contents($deliveryLog)), 'strlen');
$order = json_decode((string)file_get_contents($orderFile), true);
$seen = 0;
for ($i = 0; $i < $workers; $i++) {
    if (!empty($order['seen_by_' . $i])) {
        $seen++;
    }
}

$failures = [];
if (count($deliveries) !== 1) {
    $failures[] = 'выдач ' . count($deliveries) . ' вместо 1 при ' . $workers
        . ' одновременных процессах — защита от повторной выдачи не держит гонку';
}
if ($seen !== $workers) {
    $failures[] = 'потеряно обновление: в заказе отметились ' . $seen
        . ' процессов из ' . $workers . ' — запись затирает чужую';
}
if (!is_array($order)) {
    $failures[] = 'файл заказа не разбирается — запись не атомарна';
}

// Выдача создаёт свои подкаталоги, поэтому уборка рекурсивная.
$rmrf = function (string $dir) use (&$rmrf): void {
    foreach (glob($dir . '/*') ?: [] as $path) {
        is_dir($path) ? $rmrf($path) : @unlink($path);
    }
    @rmdir($dir);
};
$rmrf($tmp);

if ($failures) {
    echo "Гонка выдачи: НЕ ЗАКРЫТА\n";
    foreach ($failures as $f) {
        echo "  ✗ {$f}\n";
    }
    exit(1);
}
echo "Гонка выдачи закрыта: {$workers} одновременных процессов, выдача одна, "
   . "обновления не теряются.\n";
exit(0);
