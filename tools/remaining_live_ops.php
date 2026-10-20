<?php
// Invoked only through the existing deploy SSH channel; never a web endpoint.
declare(strict_types=1);
[$script,$siteArg,$productsArg,$phase,$encoded] = $argv;
function absolute_path(string $p):string{return $p[0]==='/'?$p:getenv('HOME').'/'.$p;}
$site=realpath(absolute_path($siteArg));$products=realpath(absolute_path($productsArg));
if(!$site||!$products||!is_file($site.'/index.html'))throw new RuntimeException('wrong deployment roots');
$plan=json_decode(base64_decode($encoded,true),true,512,JSON_THROW_ON_ERROR);
require $site.'/config.php';require $site.'/products-config.php';
if(realpath(PRODUCTS_DIR)!==$products)throw new RuntimeException('wrong resolved PRODUCTS_DIR');
function inventory(string $dir):array{
 $out=[];if(!is_dir($dir))return $out;
 foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir,FilesystemIterator::SKIP_DOTS)) as $f){
  if($f->isLink())throw new RuntimeException('symlink in product scope');
  if($f->isFile())$out[substr($f->getPathname(),strlen($dir)+1)]=hash_file('sha256',$f->getPathname());
 }ksort($out);return $out;
}
function same_map(array $a,array $b):bool{ksort($a);ksort($b);return $a===$b;}
function copy_tree(string $from,string $to):void{
 if(!is_dir($to)&&!mkdir($to,0700,true))throw new RuntimeException('mkdir');
 foreach(new DirectoryIterator($from) as $f){if($f->isDot())continue;if($f->isLink())throw new RuntimeException('symlink');$dst=$to.'/'.$f->getFilename();if($f->isDir())copy_tree($f->getPathname(),$dst);elseif(!copy($f->getPathname(),$dst))throw new RuntimeException('copy');}
}
function clear_tree(string $dir):void{
 if(!is_dir($dir))return;foreach(new DirectoryIterator($dir) as $f){if($f->isDot())continue;if($f->isLink())throw new RuntimeException('symlink');if($f->isDir()){clear_tree($f->getPathname());rmdir($f->getPathname());}else unlink($f->getPathname());}
}
$ref=substr(hash('sha256',json_encode($plan)),0,16);$backup=dirname($products).'/remaining-release-backups/'.$ref;
$catalog=mvb_products();$scoped=array_column($plan['packages'],'sku');
$protected=[];foreach($catalog as $sku=>$p){if(!in_array($sku,$scoped,true))$protected[$sku]=['masters'=>inventory($products.'/'.$p['dir']),'cache'=>is_file(DELIVERY_DIR.'/'.$p['zip'])?hash_file('sha256',DELIVERY_DIR.'/'.$p['zip']):null];}
if($phase==='preflight'){
 foreach($plan['site_files'] as $f){$p=$site.'/'.$f['file'];if(!is_file($p)||hash_file('sha256',$p)!==$f['before_sha256'])throw new RuntimeException('LIVE_BASELINE_MISMATCH '.$f['file']);}
 foreach($plan['protected_catalog'] as $sku=>$p){if($catalog[$sku]!==$p)throw new RuntimeException('protected catalog '.$sku);}
 if(DELIVERY_TTL_SECONDS!==3600)throw new RuntimeException('TTL');
 foreach($plan['packages'] as $p){if(!is_dir($products.'/'.$p['dir']))throw new RuntimeException('missing master '.$p['sku']);}
 foreach($plan['packages'] as $p){if($p['sku']==='p3'){foreach($p['members'] as $n=>$h){if(in_array($n,['00-START-HERE.txt','03-akt-skrytyh-rabot.pdf'],true))continue;$live=$products.'/'.$p['dir'].'/'.$n;if(!is_file($live)||hash_file('sha256',$live)!==$h)throw new RuntimeException('unrelated P3 member differs '.$n);}}}
 echo json_encode(['status'=>'PASS_READ_ONLY_PREFLIGHT','backup'=>$backup,'protected'=>$protected],JSON_UNESCAPED_UNICODE);exit;
}
if($phase==='backup'){
 if(file_exists($backup))throw new RuntimeException('backup already exists');mkdir($backup,0700,true);mkdir($backup.'/site',0700);mkdir($backup.'/cache',0700);
 foreach($plan['packages'] as $p){copy_tree($products.'/'.$p['dir'],$backup.'/masters/'.$p['dir']);$cache=DELIVERY_DIR.'/'.$p['zip'];if(is_file($cache))copy($cache,$backup.'/cache/'.$p['zip']);}
 foreach($plan['site_files'] as $f){$dst=$backup.'/site/'.$f['file'];if(!is_dir(dirname($dst)))mkdir(dirname($dst),0700,true);if(!copy($site.'/'.$f['file'],$dst))throw new RuntimeException('backup site');}
 file_put_contents($backup.'/protected.json',json_encode($protected));echo json_encode(['status'=>'BACKUP_COMPLETE','backup'=>$backup]);exit;
}
if($phase==='rollback'){
 if(!is_file($backup.'/protected.json'))throw new RuntimeException('incomplete backup');
 foreach($plan['packages'] as $p){$target=$products.'/'.$p['dir'];clear_tree($target);copy_tree($backup.'/masters/'.$p['dir'],$target);$cache=DELIVERY_DIR.'/'.$p['zip'];if(is_file($backup.'/cache/'.$p['zip']))copy($backup.'/cache/'.$p['zip'],$cache);elseif(is_file($cache))unlink($cache);}
 foreach($plan['site_files'] as $f)if(!copy($backup.'/site/'.$f['file'],$site.'/'.$f['file']))throw new RuntimeException('rollback site');
 echo json_encode(['status'=>'ROLLBACK_COMPLETE']);exit;
}
if($phase==='cache'){
 foreach($plan['packages'] as $p){
  if(!same_map(inventory($products.'/'.$p['dir']),$p['master_files']))throw new RuntimeException('master hash '.$p['sku']);
  $cache=DELIVERY_DIR.'/'.$p['zip'];if(is_link($cache))throw new RuntimeException('cache symlink');if(is_file($cache))unlink($cache);
  $zip=mvb_build_product_zip($p['sku']);if(!$zip||!is_file($zip))throw new RuntimeException('cache build '.$p['sku']);
 }echo json_encode(['status'=>'CACHE_REBUILT']);exit;
}
if($phase==='verify'){
 $old=json_decode(file_get_contents($backup.'/protected.json'),true,512,JSON_THROW_ON_ERROR);if(!same_map($old,$protected))throw new RuntimeException('unrelated masters/cache changed');
 foreach($plan['protected_catalog'] as $sku=>$p)if($catalog[$sku]!==$p)throw new RuntimeException('protected catalog changed');
 foreach($plan['site_files'] as $f)if(hash_file('sha256',$site.'/'.$f['file'])!==$f['sha256'])throw new RuntimeException('site hash '.$f['file']);
 foreach($plan['packages'] as $p){foreach(['name','price','dir','zip'] as $k)if($catalog[$p['sku']][$k]!==$p[$k])throw new RuntimeException('catalog '.$p['sku'].' '.$k);if(!same_map(inventory($products.'/'.$p['dir']),$p['master_files']))throw new RuntimeException('master');}
 foreach(['t1','t4','t5','t6','p12'] as $sku)if(mvb_resolve_product(['sku'=>$sku])!==null)throw new RuntimeException('retired still sells');
 echo json_encode(['status'=>'PASS_LIVE_MASTER_SITE_CATALOG_AND_UNRELATED_SHA','buyer_files'=>123,'TTL'=>DELIVERY_TTL_SECONDS]);exit;
}
if($phase==='create-probes'){
 $out=[];
 foreach($plan['packages'] as $p){
  $sku=$p['sku'];$id='order_'.date('Ymd_His').'_r3probe'.bin2hex(random_bytes(5));$position=['sku'=>$sku];if($sku==='p1'){$position['edition']=mvb_capture_p1_edition();if(!$position['edition'])throw new RuntimeException('P1 edition capture');}$order=['id'=>$id,'status'=>'paid','email'=>'','items'=>[$position],'total'=>$p['price']];$result=mvb_prepare_delivery($order);
  if(count($result['links'])!==1||$result['links'][0]['sku']!==$sku)throw new RuntimeException('delivery '.$sku);
  $ttl=strtotime($order['delivery']['expires_at'])-time();if($ttl<3598||$ttl>3600)throw new RuntimeException('TTL');
  $mail=mvb_delivery_email($order,$result['links']);if(strpos($mail,'1 час')===false)throw new RuntimeException('mail TTL');
  if($sku!=='p3'){$start=in_array($sku,['p10','p13'],true)?'00-START-HERE.pdf':(in_array($sku,['p1','p2','p7'],true)?'00-INSTRUKCIYA.pdf':'00-START-HERE.txt');if(strpos($mail,$start)===false)throw new RuntimeException('mail entry');}
  $file=ORDERS_DIR.'/'.$id.'.json';if(file_exists($file)||file_put_contents($file,json_encode($order))===false)throw new RuntimeException('probe save');chmod($file,0600);
  $out[]=['sku'=>$sku,'id'=>$id,'url'=>$result['links'][0]['url'],'ttl'=>$ttl,'email_render'=>'PASS_NO_SEND'];
  file_put_contents($backup.'/probe-ids.json',json_encode(array_column($out,'id')));
 }
 file_put_contents($backup.'/probe-ids.json',json_encode(array_column($out,'id')));echo json_encode($out);exit;
}
if(in_array($phase,['expire-probes','cleanup-probes'],true)){
 $ids=is_file($backup.'/probe-ids.json')?json_decode(file_get_contents($backup.'/probe-ids.json'),true):[];
 foreach($ids as $id){if(!preg_match('/^order_[0-9_]+_r3probe[a-f0-9]+$/D',$id))throw new RuntimeException('probe id');$file=ORDERS_DIR.'/'.$id.'.json';if($phase==='cleanup-probes'){if(is_file($file))unlink($file);if(is_file($file.'.lock'))unlink($file.'.lock');}else{$o=json_decode(file_get_contents($file),true,512,JSON_THROW_ON_ERROR);$o['delivery']['expires_at']=date('c',time()-1);file_put_contents($file,json_encode($o));}}
 echo json_encode(['status'=>strtoupper($phase),'orders'=>count($ids)]);exit;
}
throw new RuntimeException('unknown phase');
