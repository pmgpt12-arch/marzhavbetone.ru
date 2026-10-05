<?php
declare(strict_types=1);
define('ORDERS_DIR', __DIR__ . '/isolated-orders');
define('DELIVERY_DIR', __DIR__ . '/isolated-delivery');
define('PRODUCTS_DIR', __DIR__ . '/exact-source/products-storage');
require __DIR__ . '/exact-source/products-config.php';
if (!class_exists('ZipArchive')) {throw new RuntimeException('ZipArchive unavailable');}
$catalog = mvb_products();
$zip = mvb_build_product_zip('p3');
if (!$zip || !is_file($zip)) {throw new RuntimeException('P3 actual ZIP not produced');}
echo json_encode(['catalog'=>$catalog['p3'],'zip_path'=>$zip,'products_dir'=>PRODUCTS_DIR,'orders_dir'=>ORDERS_DIR,'delivery_dir'=>DELIVERY_DIR,'php'=>PHP_VERSION],JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE), "\n";
