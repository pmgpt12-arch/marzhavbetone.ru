<?php
declare(strict_types=1);
define('ORDERS_DIR', __DIR__ . '/isolated-orders');
define('DELIVERY_DIR', __DIR__ . '/isolated-delivery');
define('PRODUCTS_DIR', __DIR__ . '/exact-source/products-storage');
require __DIR__ . '/exact-source/products-config.php';
$path = mvb_build_product_zip('p5');
if ($path === null) { fwrite(STDERR, "ZIP_NULL
"); exit(2); }
echo json_encode(['path'=>$path,'php_version'=>PHP_VERSION,'zip_extension'=>phpversion('zip'),'creator'=>'mvb_build_product_zip(p5)'],JSON_UNESCAPED_SLASHES);
