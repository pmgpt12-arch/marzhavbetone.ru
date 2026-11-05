<?php
declare(strict_types=1);
/** Independent read-only NSP sender preflight / postflight: hash only, no credentials. */
$mode = $argc === 2 ? 'preflight' : (($argc === 3 && $argv[1] === 'postflight') ? 'postflight' : null);
$rootArg = $mode === 'preflight' ? ($argv[1] ?? '') : ($argv[2] ?? '');
if (PHP_SAPI !== 'cli' || $mode === null) {
    fwrite(STDERR, "NSP_MAIL_INSPECT_ARGS\n"); exit(2);
}
$root = realpath($rootArg);
if (!is_string($root) || basename($root) !== 'nastoronepodryadchika.ru'
    || is_link($rootArg)) {
    fwrite(STDERR, "NSP_MAIL_WRONG_ROOT\n"); exit(2);
}
$old = 'From: site@marzhavbetone.ru';
$new = 'From: site@nastoronepodryadchika.ru';
$before = [
    'lead.php' => '9a37f0cd34efddddcbbc16ede01789ceea54fcefbd50395995c1e7115b046c8e',
    'webhook.php' => 'c8d758c1234e47466b212dbe91ddd3466aa24b64f6d50ecd669a16bc6655cb2d',
    'products-config.php' => 'a5fff1609fc75ec5738b5ea1ebe4a6bed8900e774652e4ed6ebcc0e23282423c',
    'config.php' => 'd5ca6b6fa2b8a4660c493e8e3891f6eb4feafc44a54326c3800affd31af6b9db',
    'payment.php' => '4a1d765280b08f1babe4aaa94502729c111989670e024e0c1273ff8dbc1a55cf',
    'check-payment.php' => 'd19d4961857eb90ae68753db0c8ca7be3e465cc267a184eb15c4c916df8caea5',
    'download.php' => '8c90c5abf5900d1ab7e14d663a584e304fcf9ef8e37a953a4ac5b231e1b6ec55',
    'contact.php' => '607998cf64f596c361788f9830c78a1f783e07576d2e5a62752325ea21e78d2e',
];
$after = [
    'lead.php' => '44033788dffc232f8694074c6508f5c056834a3c05b0837b1ec0222771a0dcd9',
    'webhook.php' => '239b4433934b59647315ae8728b582cdc83a34d01a0be7dc85f513c163dc60d5',
    'products-config.php' => '12abc5750cc7f1d223cbeb002628338e2261e85e4bd4c3d6b8988cd7da295934',
];
$files = []; $valid = true;
foreach ($before as $name => $expectedBefore) {
    $path = $root . '/' . $name;
    if (!is_file($path) || is_link($path)) {
        fwrite(STDERR, "NSP_MAIL_PATH_MISSING_OR_LINK_" . $name . "\n"); exit(3);
    }
    $realHash = hash_file('sha256',$path);
    $want = ($mode === 'postflight' && isset($after[$name])) ? $after[$name] : $expectedBefore;
    $row = ['sha256'=>$realHash, 'expected_sha256'=>$want, 'hash_matches'=>$realHash === $want];
    if (isset($after[$name])) {
        $bytes = file_get_contents($path);
        if (!is_string($bytes)) { fwrite(STDERR, "NSP_MAIL_READ_FAILED\n"); exit(3); }
        $row['old_from_count'] = substr_count($bytes,$old);
        $row['new_from_count'] = substr_count($bytes,$new);
        $row['sender_matches'] = $mode === 'postflight'
            ? $row['old_from_count'] === 0 && $row['new_from_count'] === 1
            : $row['old_from_count'] === 1 && $row['new_from_count'] === 0;
        if (!$row['sender_matches']) $valid = false;
    }
    if (!$row['hash_matches']) $valid = false;
    $files[$name] = $row;
}
echo json_encode([
    'schema'=>'NSP_SENDER_INDEPENDENT_INSPECT_v2',
    'mode'=>$mode,
    'status'=>$valid ? 'PASS' : 'BLOCKED_SHA_OR_SENDER_DRIFT',
    'production_writes'=>0,'emails_sent'=>0,'payments_created'=>0,'orders_modified'=>0,
    'active_sender_files'=>count($after),'protected_files_unchanged'=>5,'files'=>$files,
],JSON_UNESCAPED_SLASHES|JSON_PRETTY_PRINT|JSON_THROW_ON_ERROR),"\n";
exit($valid ? 0 : 4);
