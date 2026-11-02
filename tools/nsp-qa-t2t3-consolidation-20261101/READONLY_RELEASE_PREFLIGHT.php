<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { exit(1); }
$site = realpath($argv[1] ?? '');
if (!$site || basename($site) !== 'nastoronepodryadchika.ru') { throw new RuntimeException('WRONG_SITE'); }
require $site.'/config.php';
require $site.'/products-config.php';
$rows = [];
foreach (['p4','p5','t2','t3'] as $sku) {
    $p = mvb_products()[$sku] ?? null;
    if (!$p) { throw new RuntimeException('MISSING_SKU'); }
    $dir = PRODUCTS_DIR.'/'.$p['dir'];
    $cache = DELIVERY_DIR.'/'.$p['zip'];
    $names = [];
    foreach (glob($dir.'/*') ?: [] as $f) {
        if (!is_file($f) || is_link($f)) { throw new RuntimeException('SOURCE_TYPE'); }
        $names[basename($f)] = hash_file('sha256',$f);
    }
    ksort($names);
    $rows[$sku] = ['dir'=>$p['dir'],'zip'=>$p['zip'],'price'=>$p['price'],
        'files'=>$names,'cache_sha256'=>is_file($cache)?hash_file('sha256',$cache):null];
}
$masters = [];
foreach (['P4-v1-current.zip','P5-v1-current.zip','P4-v3-current.zip','P5-v2-current.zip'] as $name) {
    $f=PRODUCTS_DIR.'/'.$name;
    $masters[$name]=is_file($f)?hash_file('sha256',$f):null;
}
echo json_encode(['read_only'=>true,'sku'=>$rows,'masters'=>$masters,
    'ttl'=>DELIVERY_TTL_SECONDS,'payment_sha256'=>hash_file('sha256',$site.'/payment.php'),
    'products_config_sha256'=>hash_file('sha256',$site.'/products-config.php')],JSON_THROW_ON_ERROR),"\n";
