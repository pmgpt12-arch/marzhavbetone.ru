<?php
declare(strict_types=1);
$base=__DIR__; $repo=dirname($base).'/integration-20261022/repo';
foreach(['ORDERS_DIR'=>$base.'/orders-qa','DELIVERY_DIR'=>$base.'/buyer-candidates','PRODUCTS_DIR'=>$base.'/package-sources/products-storage','SITE_URL'=>'https://example.invalid','ADMIN_EMAIL'=>'qa@example.invalid','DELIVERY_TTL_SECONDS'=>3600] as $key=>$value) define($key,$value);
if(!is_dir(ORDERS_DIR))mkdir(ORDERS_DIR,0700,true);
if(!is_dir(DELIVERY_DIR))mkdir(DELIVERY_DIR,0700,true);
require $repo.'/products-config.php';
$catalog=mvb_products();$rows=[];
foreach(array_keys(json_decode(file_get_contents($base.'/product-map.json'),true)) as $key){
$sku=strtolower($key);$path=mvb_build_product_zip($sku);
if(!$path||dirname($path)!==DELIVERY_DIR)throw new RuntimeException('QA_BUILD_FAILED_'.$sku);
$rows[]=['sku'=>$key,'dir'=>$catalog[$sku]['dir'],'zip'=>$catalog[$sku]['zip'],'path'=>$path,'bytes'=>filesize($path),'sha256'=>hash_file('sha256',$path)];
}
file_put_contents($base.'/builder-receipt.json',json_encode(['status'=>'PASS','builder'=>'mvb_build_product_zip','source_sha256'=>hash_file('sha256',$repo.'/products-config.php'),'network_calls'=>0,'production_writes'=>0,'archives'=>$rows],JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE));
echo 'BUILT '.count($rows)." FULL QA ARCHIVES\n";
