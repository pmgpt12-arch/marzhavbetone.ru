<?php
/**
 * 11 SHA-pinned paid SKU delivery paths, SYNTHETIC archive contract only.
 * No commercial ZIP is read or published. All mutations are under sys_get_temp_dir().
 * The pinned SHA is replaced only in a disposable PHP copy.
 */
declare(strict_types=1);
$source = dirname(__DIR__) . '/products-config.php';
$acceptedSha = '12abc5750cc7f1d223cbeb002628338e2261e85e4bd4c3d6b8988cd7da295934';
function nsp_assert(bool $ok, string $label): void {
    if (!$ok) throw new RuntimeException('PINNED_ZIP_TEST_' . $label);
}
nsp_assert(hash_file('sha256', $source) === $acceptedSha, 'SOURCE_SHA_DRIFT');
nsp_assert(class_exists(ZipArchive::class), 'ZIP_EXTENSION_MISSING');
$specs = [
    'p1'  => ['P1-v1-current.zip', '99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada'],
    'p2'  => ['P2-v13-current.zip', '42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da'],
    'p3'  => ['P3-v1-current.zip', '54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b'],
    'p4'  => ['P4-v3-palette-v3-20261104.zip', '70a728babb810d6277388a5337decce6bfdf21a7e216bc0a512870860a3d3451'],
    'p5'  => ['P5-v2-current.zip', '25ce378ee8fd84079b0edd2d57d816a2aaa77585a2a7e7172666e1f846f7dc05'],
    'p7'  => ['P7-v2-palette-v3-20261104.zip', '6df6abf578c240ba9e76c9b0e40c7c4cb3bca34c65029e4260b97d82a25ca8a6'],
    'p8'  => ['P8-v1-current.zip', '31b4e22e5e3e006b0e1c5a1d40892efb2eff2cc8a582f4baa8cbbb2232e865aa'],
    'p9'  => ['P9-v1-current.zip', '34bf03bcd3ed2e31d731dd8ac4c316cf9f94a8bb5dde1e4c9fc1aa3a7b7b23d9'],
    'p10' => ['P10-v1-current.zip', '90f9b78ba53e1fb59d751e0972594f4e7135e599946935a3c32d00b3fa9d2594'],
    'p11' => ['P11-v1-current.zip', 'ff6cf9a7056cab90ee1203a93ddb964e0308b8bd418394f4ebd672a9b8b860da'],
    'p13' => ['P13-v1-current.zip', '0b1f777b9fb65952cd219d5e61e6b8500cdcd5f1c0039ceba80e3c8f6e67f955'],
];
nsp_assert(count($specs) === 11, 'SKU_COVERAGE');
$original = file_get_contents($source);
nsp_assert(is_string($original), 'READ_SOURCE');
$base = sys_get_temp_dir() . '/nsp-pinned-zips-' . bin2hex(random_bytes(8));
$site = $base . '/site';
$masters = $base . '/masters';
$orders = $base . '/orders';
foreach ([$site, $masters, $orders . '/delivery'] as $p) {
    nsp_assert(mkdir($p, 0700, true), 'MKDIR');
}
$synthetic = [];
$changed = $original;
$passed = 0;
$corruptRejected = 0;
$missingRejected = 0;
$cacheRepaired = 0;
try {
    // Exactly one source literal per production SHA and each master path.
    foreach ($specs as $sku => [$masterName, $liveSha]) {
        nsp_assert(substr_count($changed, "'" . $liveSha . "'") === 1, 'PIN_IDENTITY_' . $sku);
        nsp_assert(substr_count($changed, "'/" . $masterName . "'") === 1, 'MASTER_PATH_' . $sku);
        $path = $masters . '/' . $masterName;
        $zip = new ZipArchive();
        nsp_assert($zip->open($path, ZipArchive::CREATE | ZipArchive::OVERWRITE) === true, 'ZIP_CREATE_' . $sku);
        nsp_assert($zip->addFromString('00-INSTRUKCIYA.pdf', '%PDF-1.4 SYNTHETIC INSTRUCTION ' . $sku),
            'INSTRUCTION_ENTRY_' . $sku);
        nsp_assert($zip->addFromString('01-synthetic.txt', 'FIXTURE ONLY: ' . $sku),
            'BUYER_ENTRY_' . $sku);
        nsp_assert($zip->addFromString('02-synthetic.txt', 'NO COMMERCIAL MATERIAL ' . $sku),
            'SECOND_ENTRY_' . $sku);
        nsp_assert($zip->close(), 'ZIP_CLOSE_' . $sku);
        $bytes = file_get_contents($path);
        nsp_assert(is_string($bytes) && strlen($bytes) > 100, 'ZIP_BYTES_' . $sku);
        $fixtureSha = hash('sha256', $bytes);
        $changed = str_replace("'" . $liveSha . "'", "'" . $fixtureSha . "'", $changed);
        $synthetic[$sku] = ['path'=>$path, 'sha'=>$fixtureSha, 'bytes'=>$bytes];
    }
    nsp_assert(substr_count($changed, 'From: site@nastoronepodryadchika.ru') === 1, 'BUYER_FROM');
    nsp_assert(file_put_contents($site . '/products-config.php', $changed) === strlen($changed), 'STAGE_PHP_COPY');
    $lint = [];
    exec(escapeshellarg(PHP_BINARY) . ' -l ' . escapeshellarg($site . '/products-config.php') . ' 2>&1',
        $lint, $lintStatus);
    nsp_assert($lintStatus === 0, 'TEMP_PHP_LINT');

    define('ORDERS_DIR', $orders);
    define('DELIVERY_DIR', $orders . '/delivery');
    define('PRODUCTS_DIR', $masters);
    define('SITE_URL', 'https://example.invalid');
    define('ADMIN_EMAIL', 'synthetic@example.invalid');
    require $site . '/products-config.php';

    $catalog = mvb_products();
    foreach ($specs as $sku => [$masterName, $originalSha]) {
        nsp_assert(isset($catalog[$sku]), 'CATALOG_SKU_' . $sku);
        $want = $synthetic[$sku];
        $masterPath = $want['path'];
        // First issuance: identical bytes, current SHA, exact buyer filename.
        $built = mvb_build_product_zip($sku);
        nsp_assert(is_string($built) && is_file($built), 'FIRST_DELIVERY_' . $sku);
        nsp_assert(hash_file('sha256', $built) === $want['sha'], 'ISSUED_SHA_' . $sku);
        nsp_assert(file_get_contents($built) === $want['bytes'], 'ISSUED_BYTES_' . $sku);
        if ($sku === 'p1') {
            nsp_assert(basename($built) === 'p1-' . $want['sha'] . '.zip', 'P1_EDITION_NAME');
        } else {
            nsp_assert(basename($built) === $catalog[$sku]['zip'], 'SKU_BUYER_NAME_' . $sku);
        }
        $zip = new ZipArchive();
        nsp_assert($zip->open($built) === true, 'ISSUED_ZIP_OPEN_' . $sku);
        nsp_assert($zip->numFiles === 3, 'FILE_COUNT_' . $sku);
        nsp_assert($zip->getFromName('01-synthetic.txt') === 'FIXTURE ONLY: ' . $sku, 'FILE_CONTENT_' . $sku);
        nsp_assert($zip->getFromName('00-INSTRUKCIYA.pdf') !== false, 'INSTRUCTION_' . $sku);
        for ($i=0; $i<$zip->numFiles; $i++) {
            $entry = $zip->statIndex($i);
            nsp_assert(is_array($entry) && $entry['size'] > 0, 'NO_ZERO_BYTE_ENTRY_' . $sku);
            nsp_assert($zip->getFromIndex($i) !== false, 'ZIP_CRC_READ_' . $sku);
        }
        $zip->close();
        $passed++;

        // A corrupt master MUST reject the product, even with a cached ZIP.
        nsp_assert(file_put_contents($masterPath, 'CORRUPT_MASTER') !== false, 'MASTER_CORRUPT_SETUP');
        nsp_assert(mvb_build_product_zip($sku) === null, 'CORRUPT_MASTER_WAS_ACCEPTED_' . $sku);
        $corruptRejected++;
        // A missing master MUST reject (no fallback to unpacked source).
        unlink($masterPath);
        nsp_assert(mvb_build_product_zip($sku) === null, 'MISSING_MASTER_WAS_ACCEPTED_' . $sku);
        $missingRejected++;

        // Original signed master may restore a corrupted cached copy, but
        // ONLY to exactly approved SHA/bytes, never a fabricated edition.
        file_put_contents($masterPath, $want['bytes']);
        file_put_contents($built, 'CORRUPT_CACHE');
        $repaired = mvb_build_product_zip($sku);
        nsp_assert($repaired === $built, 'CACHE_REPAIR_PATH_' . $sku);
        nsp_assert(hash_file('sha256', $repaired) === $want['sha'], 'CACHE_REPAIR_SHA_' . $sku);
        nsp_assert(file_get_contents($repaired) === $want['bytes'], 'CACHE_REPAIR_BYTES_' . $sku);
        $cacheRepaired++;
    }
    nsp_assert(hash_file('sha256', $source) === $acceptedSha, 'REAL_SOURCE_UNMODIFIED');
    echo json_encode([
        'status'=>'PASS_SYNTHETIC_ONLY', 'paid_sku_covered'=>$passed,
        'corrupt_master_rejected'=>$corruptRejected,
        'missing_master_rejected'=>$missingRejected,
        'exact_cache_repaired'=>$cacheRepaired,
        'real_paid_archives_read'=>0,'production_orders'=>0,'real_payment_calls'=>0,
        'real_emails_sent'=>0,'business_php_changes'=>0
    ],JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR), "\n";
} finally {
    $remove = function (string $dir) use (&$remove): void {
        if (!is_dir($dir)) return;
        foreach (new DirectoryIterator($dir) as $f) {
            if ($f->isDot()) continue;
            $p = $f->getPathname();
            $f->isDir() && !$f->isLink() ? $remove($p) : unlink($p);
        }
        rmdir($dir);
    };
    $remove($base);
}
