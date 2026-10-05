<?php
declare(strict_types=1);
$lane = realpath($argv[1]);
$sku = $argv[2];
if ($lane === false || !preg_match('/^(p4|p7|p8|p9|p10|p11|p12|p13|t[1-6])$/', $sku)) { throw new RuntimeException('Invalid isolated input'); }
define('ORDERS_DIR', $lane . '/orders');
define('DELIVERY_DIR', $lane . '/delivery');
define('PRODUCTS_DIR', $lane . '/sources/products-storage');
require $lane . '/products-config.php';
$catalog = mvb_products();
$zip = mvb_build_product_zip($sku);
if ($zip === null) { throw new RuntimeException('ZIP creation failed'); }
echo json_encode(['sku'=>$sku,'dir'=>$catalog[$sku]['dir'],'zip_name'=>$catalog[$sku]['zip'],'path'=>$zip,'php_version'=>PHP_VERSION,'zip_extension'=>phpversion('zip')], JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);
