<?php
/**
 * Сборка архива S1 штатным mvb_build_product_zip('p1') без правки каталога.
 *
 * S1 кладётся во временный PRODUCTS_DIR под именем папки p1
 * (`01-zakrytie-rabot`) — ровно то, что значит «S1 заменяет P1».
 *
 *   mkdir -p $WORK/products $WORK/orders/delivery
 *   cp -r <дерево с S1>/tools/candidates/s1-oplata-za-raboty $WORK/products/01-zakrytie-rabot
 *   SITE=<корень сайта> WORK=$WORK php build_zip.php
 *
 * Печатает имя архива и строки «имя размер sha256» по каждой записи.
 */
define('ORDERS_DIR', getenv('WORK') . '/orders');
define('PRODUCTS_DIR', getenv('WORK') . '/products');
define('DELIVERY_DIR', ORDERS_DIR . '/delivery');
require getenv('SITE') . '/products-config.php';
$zip = mvb_build_product_zip('p1');
echo $zip, "\n";
$z = new ZipArchive(); $z->open($zip);
$rows = [];
for ($i = 0; $i < $z->numFiles; $i++) { $s = $z->statIndex($i);
  $rows[] = sprintf("%-45s %8d %s", $s['name'], $s['size'], hash('sha256', $z->getFromIndex($i))); }
sort($rows); echo implode("\n", $rows), "\n";
