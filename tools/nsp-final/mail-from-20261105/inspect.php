<?php
declare(strict_types=1);
// NSP sender: READ-ONLY production preflight. Never load config.php or print its values.
if (PHP_SAPI !== 'cli' || $argc !== 2) { fwrite(STDERR, "NSP_MAIL_ARGS\n"); exit(2); }
$root = realpath($argv[1]);
if (!is_string($root) || basename($root) !== 'nastoronepodryadchika.ru') {
    fwrite(STDERR, "NSP_MAIL_WRONG_ROOT\n"); exit(2);
}
$old = 'From: site@marzhavbetone.ru';
$new = 'From: site@nastoronepodryadchika.ru';
$active = ['lead.php', 'webhook.php', 'products-config.php'];
$protected = ['config.php', 'payment.php', 'check-payment.php', 'download.php', 'contact.php'];
$files = [];
$valid = true;
foreach (array_merge($active, $protected) as $name) {
    $path = $root . '/' . $name;
    if (!is_file($path) || is_link($path)) {
        fwrite(STDERR, "NSP_MAIL_PATH_MISSING_OR_LINK_" . $name . "\n"); exit(3);
    }
    $bytes = file_get_contents($path);
    if (!is_string($bytes)) { fwrite(STDERR, "NSP_MAIL_CANNOT_READ\n"); exit(3); }
    $row = ['sha256' => hash('sha256', $bytes), 'bytes' => strlen($bytes)];
    if (in_array($name, $active, true)) {
        $row['old_from_count'] = substr_count($bytes, $old);
        $row['new_from_count'] = substr_count($bytes, $new);
        $row['status'] = ($row['old_from_count'] === 1 && $row['new_from_count'] === 0)
            ? 'READY_FOR_SINGLE_LITERAL_PATCH' : 'UNEXPECTED_SENDER_STATE';
        if ($row['status'] !== 'READY_FOR_SINGLE_LITERAL_PATCH') $valid = false;
    }
    $files[$name] = $row;
}
echo json_encode([
    'schema' => 'NSP_SENDER_PRODUCTION_PREFLIGHT_v1',
    'mode' => 'READ_ONLY', 'production_writes' => 0, 'emails_sent' => 0,
    'payments_created' => 0, 'orders_modified' => 0,
    'status' => $valid ? 'PASS' : 'BLOCKED_SENDER_DRIFT',
    'files' => $files,
], JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR), "\n";
exit($valid ? 0 : 4);
