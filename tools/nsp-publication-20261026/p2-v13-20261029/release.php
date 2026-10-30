<?php
declare(strict_types=1);
// P2-only bounded transaction. Runs in existing GitHub Actions SSH workflow.
function req(bool $ok,string $why): void { if (!$ok) throw new RuntimeException($why); }
function h(string $p): string { req(is_file($p)&&!is_link($p),'FILE_NOT_REGULAR:'.basename($p)); return (string)hash_file('sha256',$p); }
function atomic(string $from,string $to): void {
  req(is_file($from)&&is_dir(dirname($to))&&!is_link(dirname($to)),'ATOMIC_PATH');
  $tmp=tempnam(dirname($to),'.p2-v13-'); req($tmp!==false,'TEMP');
  req(chmod($tmp,is_file($to)?(fileperms($to)&0777):0644),'FILE_MODE');
  try { req(copy($from,$tmp),'COPY'); req(h($tmp)===h($from),'COPY_HASH'); req(rename($tmp,$to),'RENAME'); }
  finally { if (is_file($tmp)) unlink($tmp); }
}
function result(array $x): void {echo json_encode($x,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR)."\n";}
try {
 req($argc===4 && in_array($argv[1],['preflight','apply','verify','rollback'],true),'ARGS');
 $mode=$argv[1];$site=realpath($argv[2]);$stage=realpath($argv[3]);
 req(is_string($site)&&basename($site)==='nastoronepodryadchika.ru'&&is_string($stage)&&strpos($stage,$site.'/')!==0,'SCOPE');
 $manifest=json_decode((string)file_get_contents($stage.'/manifest.json'),true,512,JSON_THROW_ON_ERROR);
 req($manifest['sku']==='p2'&&$manifest['edition']==='P2-v13','EDITION');
 $expected='42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da';
 req($manifest['archive_sha256']===$expected,'OWNER_ARCHIVE');
 $zipName='P2-NSP-v13-13-files-20261029.zip';$source=$stage.'/'.$zipName;
 req(h($source)===$expected,'STAGE_ARCHIVE_SHA');
 $z=new ZipArchive();req($z->open($source)===true,'ZIP_OPEN');$members=[];
 for($i=0;$i<$z->numFiles;$i++) {$name=$z->getNameIndex($i);req(!isset($members[$name])&&strpos($name,'../')===false,'ZIP_NAME');
   $members[$name]=hash('sha256',(string)$z->getFromIndex($i));}
 $z->close();req(count($members)===13,'MEMBER_COUNT');
 foreach($manifest['members'] as $r) req(isset($members[$r['name']])&&$members[$r['name']]===$r['sha256'],'MEMBER_SHA');
 req(count($manifest['members'])===13,'MANIFEST_COUNT');
 require_once $site.'/config.php';
 require_once $site.'/products-config.php';
 req(defined('DELIVERY_TTL_SECONDS')&&DELIVERY_TTL_SECONDS===3600,'ONE_HOUR_TTL');
 req(defined('PRODUCTS_DIR')&&defined('DELIVERY_DIR'),'RUNTIME_PATHS');
 $masterRoot=realpath(PRODUCTS_DIR);$deliveryRoot=realpath(DELIVERY_DIR);
 req(is_string($masterRoot)&&is_string($deliveryRoot)&&strpos($masterRoot,$site.'/')!==0&&strpos($deliveryRoot,$site.'/')!==0,'PRIVATE_ONLY');
 $master=$masterRoot.'/P2-v13-current.zip';$out=$deliveryRoot.'/02-dopy-ne-v-podarok.zip';
 $names=['products/p2-dopolnitelnye-raboty.html','katalog.html','products-config.php'];
 foreach($names as $name) {
   req(isset($manifest['files'][$name]['before'],$manifest['files'][$name]['after']),'MANIFEST_PATH');
   $current=$site.'/'.$name;$candidate=$stage.'/candidate/'.$name;
   req(h($candidate)===$manifest['files'][$name]['after'],'CANDIDATE_SHA:'.$name);
 }
 if($mode==='preflight') {
   foreach($names as $name)req(h($site.'/'.$name)===$manifest['files'][$name]['before'],'BASELINE_DRIFT:'.$name);
   req(is_writable($masterRoot)&&is_writable($deliveryRoot),'PRIVATE_WRITE_PERMISSIONS');
   result(['status'=>'P2_PREFLIGHT_PASS','sku'=>'p2','members'=>13,'ttl'=>3600,'production_changed'=>false]);exit;
 }
 if($mode==='rollback') {
   foreach($names as $name) {
     $before=$stage.'/backup/'.$name;$target=$site.'/'.$name;
     req(h($before)===$manifest['files'][$name]['before'],'BACKUP_SHA:'.$name);
     req(in_array(h($target),[$manifest['files'][$name]['before'],$manifest['files'][$name]['after']],true),'ROLLBACK_CONCURRENT_EDIT');
     if(h($target)!==$manifest['files'][$name]['before'])atomic($before,$target);
   }
   foreach([$master,$out] as $target)if(is_file($target)&&h($target)===$expected)req(unlink($target),'ROLLBACK_ZIP');
   result(['status'=>'P2_ROLLBACK_PASS','sku'=>'p2']);exit;
 }
 if($mode==='apply') {
   foreach($names as $name) {
     req(h($site.'/'.$name)===$manifest['files'][$name]['before'],'LIVE_CONCURRENT_EDIT');
     $backup=$stage.'/backup/'.$name;req(!file_exists($backup),'BACKUP_EXISTS');
     req(is_dir(dirname($backup))||mkdir(dirname($backup),0700,true),'BACKUP_DIR');
     req(copy($site.'/'.$name,$backup),'BACKUP_COPY');
     req(h($backup)===$manifest['files'][$name]['before'],'BACKUP_HASH');
   }
   // Current edition only: a canonical private file and a replaceable delivery cache.
   atomic($source,$master);req(h($master)===$expected,'MASTER_SHA');
   atomic($source,$out);req(h($out)===$expected,'DELIVERY_SHA');
   // PHP configuration is switched last; the existing buyer path/sku/price stay unchanged.
   foreach($names as $name) {
     req(h($site.'/'.$name)===$manifest['files'][$name]['before'],'CONCURRENT_EDIT:'.$name);
     atomic($stage.'/candidate/'.$name,$site.'/'.$name);
     req(h($site.'/'.$name)===$manifest['files'][$name]['after'],'APPLY_SHA:'.$name);
   }
   result(['status'=>'P2_APPLY_PASS','sku'=>'p2','archive_sha256'=>$expected,'files'=>count($names)]);exit;
 }
 foreach($names as $name)req(h($site.'/'.$name)===$manifest['files'][$name]['after'],'VERIFY_SITE:'.$name);
 req(h($master)===$expected&&h($out)===$expected,'VERIFY_ARCHIVE');
 // Safe runtime readback from the actual existing product builder.
 req(mvb_build_product_zip('p2')===$out,'P2_BUILDER_PATH');
 req(h($out)===$expected,'P2_BUILDER_BYTES');
 req(mvb_products()['p2']['price']===2490000,'PRICE_CHANGED');
 result(['status'=>'P2_NATIVE_DELIVERY_PASS','sku'=>'p2','archive_sha256'=>$expected,'files'=>13,'ttl_seconds'=>3600,'release_edition'=>'P2-v13']);
} catch(Throwable $e) {
 fwrite(STDERR,"P2_PUBLICATION_GATE_FAILED=".$e->getMessage()."\n");exit(2);
}
