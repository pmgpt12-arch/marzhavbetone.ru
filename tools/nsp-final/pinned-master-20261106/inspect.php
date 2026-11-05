<?php
declare(strict_types=1);
/**
 * Read-only acceptance of actual private paid ZIP masters.
 * Outputs only SKU + SHA/CRC/count booleans. Never reads/prints order data or
 * sends materials. Run only via the existing authorized deploy-locked workflow.
 */
function check(bool $condition, string $code): void {
    if (!$condition) throw new RuntimeException($code);
}
function file_sha(string $p): string {
    check(is_file($p) && !is_link($p), 'MISSING_OR_SYMLINK');
    $hash = hash_file('sha256', $p);
    check(is_string($hash) && strlen($hash) === 64, 'HASH_FAILED');
    return $hash;
}
try {
    check(PHP_SAPI === 'cli' && $argc === 2, 'CLI_ARGS');
    $site = realpath($argv[1]);
    check(is_string($site) && basename($site) === 'nastoronepodryadchika.ru'
        && !is_link($argv[1]), 'WRONG_SITE');
    $sourceSha = '12abc5750cc7f1d223cbeb002628338e2261e85e4bd4c3d6b8988cd7da295934';
    check(file_sha($site . '/products-config.php') === $sourceSha, 'SOURCE_PHP_SHA_DRIFT');
    // Only this prior-verified config may be loaded. Its credentials are never printed.
    check(file_sha($site . '/config.php') ===
        'd5ca6b6fa2b8a4660c493e8e3891f6eb4feafc44a54326c3800affd31af6b9db',
        'SITE_CONFIG_SHA_DRIFT');
    require $site . '/config.php';
    check(defined('ORDERS_DIR') && is_dir(ORDERS_DIR)
        && is_file(ORDERS_DIR . '/.htaccess')
        && is_dir(ORDERS_DIR . '/delivery')
        && is_file(ORDERS_DIR . '/delivery/.htaccess'), 'ORDER_DIR_PRECHECK');
    require $site . '/products-config.php';
    $root = realpath(PRODUCTS_DIR);
    $cacheRoot = realpath(DELIVERY_DIR);
    check(is_string($root) && is_string($cacheRoot)
        && !str_starts_with($root . '/', $site . '/')
        && !str_starts_with($cacheRoot . '/', $site . '/products-storage/'),
        'PRIVATE_STORE_NOT_VERIFIED');
    check(class_exists('ZipArchive'), 'ZIP_EXTENSION_MISSING');
    check(DELIVERY_TTL_SECONDS === 3600, 'BUYER_TTL_CHANGED');

    // Exact contract from accepted, whole-file SHA-pinned production source.
    $specs = [
        'p1' => ['P1-v1-current.zip','99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada',2990000],
        'p2' => ['P2-v13-current.zip','42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da',2490000],
        'p3' => ['P3-v1-current.zip','54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b',1790000],
        'p4' => ['P4-v3-palette-v3-20261104.zip','70a728babb810d6277388a5337decce6bfdf21a7e216bc0a512870860a3d3451',2490000],
        'p5' => ['P5-v2-current.zip','25ce378ee8fd84079b0edd2d57d816a2aaa77585a2a7e7172666e1f846f7dc05',2990000],
        'p7' => ['P7-v2-palette-v3-20261104.zip','6df6abf578c240ba9e76c9b0e40c7c4cb3bca34c65029e4260b97d82a25ca8a6',2490000],
        'p8' => ['P8-v1-current.zip','31b4e22e5e3e006b0e1c5a1d40892efb2eff2cc8a582f4baa8cbbb2232e865aa',2490000],
        'p9' => ['P9-v1-current.zip','34bf03bcd3ed2e31d731dd8ac4c316cf9f94a8bb5dde1e4c9fc1aa3a7b7b23d9',2490000],
        'p10'=> ['P10-v1-current.zip','90f9b78ba53e1fb59d751e0972594f4e7135e599946935a3c32d00b3fa9d2594',1790000],
        'p11'=> ['P11-v1-current.zip','ff6cf9a7056cab90ee1203a93ddb964e0308b8bd418394f4ebd672a9b8b860da',2490000],
        'p13'=> ['P13-v1-current.zip','0b1f777b9fb65952cd219d5e61e6b8500cdcd5f1c0039ceba80e3c8f6e67f955',1790000],
    ];
    check(count($specs) === 11, 'SKU_COVERAGE');
    $products = mvb_products();
    $rows = []; $passed = 0;
    foreach ($specs as $sku => [$name,$want,$price]) {
        $row = ['sku'=>$sku,'master_filename'=>$name,'master_sha256_expected'=>$want,
            'master_present'=>false,'master_sha256_pass'=>false,
            'zip_members'=>0,'zip_integrity_pass'=>false,
            'cache'=> 'NOT_CHECKED','price_kopeks_match'=>($products[$sku]['price'] ?? null) === $price];
        $error = null;
        try {
            check(isset($products[$sku]), 'SKU_MISSING');
            check($row['price_kopeks_match'], 'PRICE_DRIFT');
            $master = $root . '/' . $name;
            check(is_file($master) && !is_link($master), 'MASTER_MISSING_OR_SYMLINK');
            $row['master_present']=true;
            $real = realpath($master);
            check(is_string($real) && str_starts_with($real, $root . '/'),
                'MASTER_OUTSIDE_PRIVATE_ROOT');
            $row['master_sha256_pass'] = file_sha($master) === $want;
            check($row['master_sha256_pass'], 'MASTER_SHA_MISMATCH');
            check(filesize($master) > 1024 && filesize($master) < 50*1024*1024,
                'MASTER_SIZE');
            $zip=new ZipArchive();
            check($zip->open($master) === true, 'MASTER_ZIP_OPEN');
            try {
                $entryNames = []; $seen = [];
                check($zip->numFiles >= 2 && $zip->numFiles <= 200, 'ZIP_MEMBER_COUNT');
                for ($i=0; $i<$zip->numFiles; $i++) {
                    $meta=$zip->statIndex($i);
                    check(is_array($meta) && isset($meta['name'],$meta['size'],$meta['crc'])
                        && $meta['size'] > 0 && $meta['size'] <= 30*1024*1024,
                        'UNEXPECTED_ZIP_ENTRY');
                    $entryName=$meta['name'];
                    check(!isset($seen[$entryName]) && !str_starts_with($entryName,'/')
                        && !str_contains($entryName,'\\')
                        && !in_array('..',explode('/',$entryName),true),
                        'ZIP_ENTRY_PATH');
                    $seen[$entryName]=true;
                    $entryNames[]=$entryName;
                    $data=$zip->getFromIndex($i);
                    check(is_string($data) && strlen($data)===$meta['size']
                        && sprintf('%u',crc32($data)) === sprintf('%u',$meta['crc']),
                        'ENTRY_CRC');
                }
                check(count(array_intersect(
                    ['00-INSTRUKCIYA.pdf','00-START-HERE.pdf','00-START-HERE.txt'],$entryNames)) >= 1,
                    'NO_BUYER_INSTRUCTION');
                foreach (['.htaccess','00-PISMO-POSLE-POKUPKI.txt','MANIFEST.md'] as $svc) {
                    check(!in_array($svc,$entryNames,true), 'SERVICE_FILE_IN_BUYER_ZIP');
                }
                $row['zip_members']=$zip->numFiles;
                $row['zip_integrity_pass']=true;
            } finally { $zip->close(); }
            $cachePath = $cacheRoot . '/' . ($sku === 'p1'
                ? 'p1-' . $want . '.zip' : $products[$sku]['zip']);
            if (is_file($cachePath) && !is_link($cachePath)) {
                $row['cache'] = file_sha($cachePath) === $want ? 'EXACT_SHA_PASS' : 'CACHE_SHA_DRIFT';
                check($row['cache'] === 'EXACT_SHA_PASS', 'CACHE_SHA_DRIFT');
            } elseif (file_exists($cachePath) || is_link($cachePath)) {
                throw new RuntimeException('CACHE_NONREGULAR');
            } else {
                $row['cache'] = 'NOT_BUILT_YET';
            }
            $passed++;
        } catch(Throwable $e) { $error=$e->getMessage(); }
        if ($error !== null) $row['error']=$error;
        $rows[$sku]=$row;
    }
    $status = $passed === 11 ? 'PASS_ALL_11_REAL_PRIVATE_PINNED_ZIPS' : 'BLOCKED_SOME_REAL_PRIVATE_ZIPS';
    echo json_encode([
        'schema'=>'NSP_PINNED_PAID_ZIP_PRIVATE_INTEGRITY_V1',
        'mode'=>'READ_ONLY','status'=>$status,'sku_expected'=>11,'sku_passed'=>$passed,
        'products_php_sha256'=>$sourceSha,'server_price_gate'=>'VERIFIED_WITH_CATALOG',
        'payment_requests'=>0,'email_attempts'=>0,'orders_read'=>0,'orders_modified'=>0,
        'public_file_writes'=>0,'real_paid_zips_exposed'=>0,
        'products'=>$rows
    ], JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_PRETTY_PRINT|JSON_THROW_ON_ERROR), "\n";
    exit($passed===11 ? 0 : 3);
} catch(Throwable $e) {
    fwrite(STDERR,'NSP_PINNED_PRIVATE_QA_BLOCKED='.$e->getMessage()."\n");
    exit(2);
}
