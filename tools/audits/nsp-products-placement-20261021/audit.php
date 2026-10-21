<?php
$expected=EXPECTED_JSON;
$root=rtrim(getenv('HOME'),'/').'/www/nastoronepodryadchika.ru';
require $root.'/config.php';
if(!is_dir(ORDERS_DIR)||!is_dir(ORDERS_DIR.'/delivery')||!is_file(ORDERS_DIR.'/.htaccess')||!is_file(ORDERS_DIR.'/delivery/.htaccess'))throw new RuntimeException('Existing protected order directories required');
require $root.'/products-config.php';
$catalog=mvb_products();$r=['site'=>'https://nastoronepodryadchika.ru','checked_at'=>gmdate('c'),'scope'=>'read-only masters and existing cached archives; no order/payment/mail operations','expected_files'=>172,'products'=>[],'errors'=>[],'disabled_sku_resolution'=>[]];
foreach($expected as $sku=>$want){
$p=$catalog[$sku]??null;
if(!$p){$r['errors'][]=$sku.': missing backend product';continue;}
$dir=PRODUCTS_DIR.'/'.$p['dir'];$actual=[];
foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir,FilesystemIterator::SKIP_DOTS)) as $f){
if($f->isLink())throw new RuntimeException('Symlink in product master');
if($f->isFile()&&!in_array($f->getFilename(),['.htaccess','MANIFEST.md','00-PISMO-POSLE-POKUPKI.txt'],true))$actual[substr($f->getPathname(),strlen($dir)+1)]=hash_file('sha256',$f->getPathname());
}
ksort($actual);$ok=$actual===$want['members'];$price=(int)$p['price']===$want['price'];
$row=['sku'=>$sku,'files'=>count($actual),'master_sha'=>$ok?'PASS':'FAIL','price'=>$price?'PASS':'FAIL','members'=>$actual];
if(!$ok||!$price||$p['dir']!==$want['dir'])$r['errors'][]=$sku.': approved master/price/directory mismatch';
$paths=[DELIVERY_DIR.'/'.$p['zip']];
if($sku==='p1'){$extra=glob(DELIVERY_DIR.'/p1-*.zip')?:[];usort($extra,fn($a,$b)=>filemtime($b)<=>filemtime($a));$paths=array_merge($paths,array_slice($extra,0,10));}
$found=false;$matched=false;
foreach(array_unique($paths) as $zp){
if(!is_file($zp))continue;$found=true;$z=new ZipArchive();
if($z->open($zp,ZipArchive::CHECKCONS)!==true)continue;
$members=[];$crc=true;
for($i=0;$i<$z->numFiles;$i++){$name=$z->getNameIndex($i);$b=$z->getFromIndex($i);$st=$z->statIndex($i);if($b===false){$crc=false;continue;}$members[$name]=hash('sha256',$b);if(sprintf('%u',crc32($b))!==sprintf('%u',$st['crc']))$crc=false;}
$z->close();ksort($members);
if($crc&&$members===$want['members']){$matched=true;$row['existing_archive_sha256']=hash_file('sha256',$zp);$row['existing_archive_name']=basename($zp);break;}
}
$row['existing_archive']=$matched?'PASS_MEMBERS_AND_CRC':($found?'FAIL_MEMBERS_OR_CRC':'NOT_PRESENT');
if($found&&!$matched)$r['errors'][]=$sku.': existing cached archive does not match accepted edition';
$r['products'][]=$row;
}
foreach(['t1','t4','t5','t6','p12'] as $sku){$ok=mvb_resolve_product(['sku'=>$sku])===null;$r['disabled_sku_resolution'][$sku]=$ok?'PASS':'FAIL';if(!$ok)$r['errors'][]=$sku.': retired SKU still resolvable';}
$r['ttl_seconds']=DELIVERY_TTL_SECONDS;$r['site_url']=SITE_URL;$r['products_outside_webroot']=!str_starts_with(realpath(PRODUCTS_DIR),realpath($root).'/');
if(DELIVERY_TTL_SECONDS!==3600||SITE_URL!=='https://nastoronepodryadchika.ru'||!$r['products_outside_webroot'])$r['errors'][]='Domain, TTL or storage placement mismatch';
$r['status']=$r['errors']?'FAIL':'PASS_APPROVED_172_MASTERS_PRICES_RESOLVER_AND_EXISTING_ARCHIVES';
echo json_encode($r,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE),"\n";
exit($r['errors']?3:0);
