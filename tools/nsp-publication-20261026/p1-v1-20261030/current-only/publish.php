<?php
/** Replace only the current P1 product files, cache and two public pages.
 * Payment, download, configuration, orders and other products are never edited.
 * Rollback copies exist only during this one deployment; finalize deletes them.
 */
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { exit(1); }
$mode=$argv[1]??''; $site=realpath($argv[2]??''); $stage=realpath($argv[3]??'');
if (!in_array($mode,['preflight','apply','verify','read-current','finalize','rollback'],true)
    || !$site || !$stage || basename($site)!=='nastoronepodryadchika.ru'
    || strpos($stage,$site.DIRECTORY_SEPARATOR)===0) throw new RuntimeException('INVALID_SCOPE');
$m=json_decode((string)file_get_contents($stage.'/release.json'),true,512,JSON_THROW_ON_ERROR);
$sha='99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada';
if (($m['archive_sha256']??'')!==$sha || ($m['sku']??'')!=='p1' || count($m['members']??[])!==18) throw new RuntimeException('NOT_APPROVED_P1');
foreach ($m['protected'] as $name=>$expected) {
    if (!hash_equals($expected,(string)hash_file('sha256',$site.'/'.$name))) throw new RuntimeException('PROTECTED_DRIFT:'.$name);
}
require $site.'/config.php'; require $site.'/products-config.php';
$p=mvb_products()['p1'];
if ($p['dir']!=='01-zakrytie-rabot' || $p['zip']!=='01-ks-podpisany-deneg-net.zip'
    || $p['price']!==2990000 || DELIVERY_TTL_SECONDS!==3600) throw new RuntimeException('CATALOG_OR_TTL_DRIFT');
$root=realpath(PRODUCTS_DIR); $delivery=realpath(DELIVERY_DIR);
if (!$root || !$delivery || strpos($root,$site.DIRECTORY_SEPARATOR)===0) throw new RuntimeException('PRIVATE_PRODUCT_ROOT_REQUIRED');
$source=$root.'/'.$p['dir']; $cache=$delivery.'/p1-'.$sha.'.zip';
$master=$root.'/P1-v1-current.zip';
$new=$root.'/.p1-current-v1-stage'; $old=$root.'/.p1-current-v1-rollback';
$backup=$stage.'/rollback'; $journal=$stage.'/apply-state.json';
function hash_ok(string $path,string $sha): bool { return is_file($path)&&hash_equals($sha,(string)hash_file('sha256',$path)); }
function inventory(string $dir): array {
    if (!is_dir($dir) || is_link($dir)) throw new RuntimeException('SOURCE_DIRECTORY_INVALID');
    $out=[]; foreach (new DirectoryIterator($dir) as $entry) {
        if($entry->isDot())continue;
        if(!$entry->isFile()||$entry->isLink())throw new RuntimeException('UNEXPECTED_NESTED_SOURCE');
        $out[$entry->getFilename()]=hash_file('sha256',$entry->getPathname());
    } ksort($out); return $out;
}
function clear_exact_dir(string $dir,array $expected): void {
    ksort($expected); if(inventory($dir)!==$expected)throw new RuntimeException('REFUSE_DELETE_CHANGED_SOURCE');
    foreach(array_keys($expected)as $name)if(!unlink($dir.'/'.$name))throw new RuntimeException('SOURCE_CLEANUP_FAILED');
    if(!rmdir($dir))throw new RuntimeException('SOURCE_DIRECTORY_CLEANUP_FAILED');
}
$expected=[];foreach($m['members']as $row){
    $name=$row['name'];if(basename($name)!==$name || isset($expected[$name]))throw new RuntimeException('BAD_MEMBER');
    $expected[$name]=$row['sha256'];
}ksort($expected);
$before=$m['old_members'];ksort($before);
$pages=$m['pages'];
if(array_keys($pages)!==['products/p1-oplata-po-ks2.html','katalog.html','products-config.php'])throw new RuntimeException('PAGE_ALLOWLIST');
function verify_current(): array {
    global $source,$cache,$master,$sha,$expected,$pages,$site,$p;
    clearstatcache();
    if(inventory($source)!==$expected || !hash_ok($cache,$sha) || !hash_ok($master,$sha))throw new RuntimeException('CURRENT_PRODUCT_MISMATCH');
    foreach($pages as $name=>$row)if(!hash_ok($site.'/'.$name,$row['after']))throw new RuntimeException('PAGE_MISMATCH:'.$name);
    $edition=mvb_capture_p1_edition();
    if(!is_array($edition)||$edition['sha256']!==$sha||mvb_p1_edition_path($edition)!==$cache)throw new RuntimeException('EDITION_BINDING');
    $built=mvb_build_product_zip('p1');clearstatcache();
    if($built!==$cache || !hash_ok($cache,$sha))throw new RuntimeException('EXISTING_BUILDER_BYTE_MISMATCH');
    return ['status'=>'P1_CURRENT_FILES_VERIFIED','archive_sha256'=>$sha,'files'=>18,'price_kopeks'=>$p['price'],'ttl_seconds'=>DELIVERY_TTL_SECONDS,'builder_exact_archive'=>true,'payment_and_download_code_changed'=>false];
}
if($mode==='preflight'){
    if(inventory($source)!==$before)throw new RuntimeException('CURRENT_MASTER_DRIFT');
    foreach($pages as $name=>$row){
        if(!hash_ok($site.'/'.$name,$row['before']) || !hash_ok($stage.'/pages/'.$name,$row['after']))throw new RuntimeException('PAGE_PREFLIGHT:'.$name);
    }
    if(!hash_ok($stage.'/current.zip',$sha))throw new RuntimeException('ARCHIVE_SHA');
    $z=new ZipArchive();if($z->open($stage.'/current.zip')!==true||$z->numFiles!==18)throw new RuntimeException('ARCHIVE_COUNT');
    $actual=[];for($i=0;$i<$z->numFiles;$i++){$n=$z->getNameIndex($i);$actual[$n]=hash('sha256',(string)$z->getFromIndex($i));}
    $z->close();ksort($actual);if($actual!==$expected)throw new RuntimeException('ARCHIVE_MEMBER_SHA');
    if(file_exists($new)||file_exists($old)||file_exists($journal))throw new RuntimeException('PREVIOUS_DEPLOYMENT_PRESENT');
    echo json_encode(['status'=>'PREFLIGHT_PASS','scope'=>'CURRENT_P1_ONLY','ttl_seconds'=>3600,'files'=>18,'production_writes'=>false]),"\n";exit;
}
if($mode==='apply'){
    if(file_exists($journal)||file_exists($new)||file_exists($old))throw new RuntimeException('NO_REAPPLY');
    if(inventory($source)!==$before)throw new RuntimeException('SOURCE_CHANGED_AFTER_PREFLIGHT');
    foreach($pages as $name=>$row)if(!hash_ok($site.'/'.$name,$row['before']))throw new RuntimeException('PAGE_CHANGED_AFTER_PREFLIGHT');
    mkdir($backup,0700);$state=['source_swapped'=>false,'cache_written'=>false,'pages'=>[],'had_cache'=>is_file($cache)];
    $state['old_caches']=[];foreach(array_merge(glob($delivery.'/p1-*.zip')?:[],[$delivery.'/'.$p['zip']])as $file){if(is_file($file)&&$file!==$cache)$state['old_caches'][$file]=hash_file('sha256',$file);}
    if($state['had_cache']){copy($cache,$backup.'/previous-cache.zip');$state['old_cache_sha']=hash_file('sha256',$cache);}
    foreach($pages as $name=>$row)copy($site.'/'.$name,$backup.'/'.str_replace('/','__',$name));
    file_put_contents($journal,json_encode($state));
    mkdir($new,0755);$z=new ZipArchive();$z->open($stage.'/current.zip');
    foreach($expected as $name=>$hash){$b=$z->getFromName($name);if($b===false||hash('sha256',$b)!==$hash)throw new RuntimeException('EXTRACT_SHA');file_put_contents($new.'/'.$name,$b);chmod($new.'/'.$name,0644);touch($new.'/'.$name,946684800);}
    $z->close();if(inventory($new)!==$expected)throw new RuntimeException('EXTRACT_INVENTORY');
    if(!rename($source,$old))throw new RuntimeException('SOURCE_SWAP_1');
    $state['source_swapped']=true;file_put_contents($journal,json_encode($state));
    if(!rename($new,$source))throw new RuntimeException('SOURCE_SWAP_2');
    $tmp=$cache.'.p1-v1-tmp';if(file_exists($tmp))throw new RuntimeException('CACHE_STAGE_EXISTS');
    if(!copy($stage.'/current.zip',$tmp)||!hash_ok($tmp,$sha))throw new RuntimeException('CACHE_COPY');
    chmod($tmp,0644);touch($tmp);if(!rename($tmp,$cache))throw new RuntimeException('CACHE_REPLACE');
    $state['cache_written']=true;file_put_contents($journal,json_encode($state));
    if(file_exists($master))throw new RuntimeException('MASTER_ALREADY_PRESENT');
    if(!copy($stage.'/current.zip',$master)||!hash_ok($master,$sha))throw new RuntimeException('MASTER_COPY');
    chmod($master,0644);
    foreach($pages as $name=>$row){$tmp=$site.'/'.$name.'.p1-v1-tmp';if(file_exists($tmp))throw new RuntimeException('PAGE_STAGE_EXISTS');if(!copy($stage.'/pages/'.$name,$tmp)||!hash_ok($tmp,$row['after']))throw new RuntimeException('PAGE_COPY');chmod($tmp,0644);if(!rename($tmp,$site.'/'.$name))throw new RuntimeException('PAGE_REPLACE');$state['pages'][]=$name;file_put_contents($journal,json_encode($state));}
    echo json_encode(['status'=>'P1_APPLIED_PENDING_FRESH_VERIFY']),"\n";exit;
}
if($mode==='verify'){echo json_encode(verify_current()),"\n";exit;}
if($mode==='read-current'){verify_current();readfile($cache);exit;}
if($mode==='rollback'){
    if(!is_file($journal)){echo "{\"status\":\"NO_APPLY_TO_ROLLBACK\"}\n";exit;}
    $state=json_decode((string)file_get_contents($journal),true);
    foreach(array_reverse($state['pages'])as $name){$tmp=$site.'/'.$name.'.p1-v1-rollback';copy($backup.'/'.str_replace('/','__',$name),$tmp);rename($tmp,$site.'/'.$name);}
    if($state['cache_written']){if($state['had_cache']){copy($backup.'/previous-cache.zip',$cache);touch($cache);}elseif(is_file($cache)){unlink($cache);}}
    if(is_file($master)&&hash_ok($master,$sha))unlink($master);
    if($state['source_swapped']){if(is_dir($source))clear_exact_dir($source,$expected);if(!rename($old,$source))throw new RuntimeException('ROLLBACK_SOURCE_FAILED');}
    if(is_dir($new))clear_exact_dir($new,$expected);
    foreach($pages as $name=>$row)if(!hash_ok($site.'/'.$name,$row['before']))throw new RuntimeException('ROLLBACK_PAGE_FAILED');
    if(inventory($source)!==$before)throw new RuntimeException('ROLLBACK_SOURCE_MISMATCH');
    echo "{\"status\":\"ROLLBACK_VERIFIED\"}\n";exit;
}
if($mode==='finalize'){
    $result=verify_current();
    $state=json_decode((string)file_get_contents($journal),true);
    foreach($state['old_caches']as $file=>$expectedHash){if(is_file($file)){if(!hash_ok($file,$expectedHash))throw new RuntimeException('OLD_CACHE_CHANGED');if(!unlink($file))throw new RuntimeException('OLD_CACHE_CLEANUP');}}
    clear_exact_dir($old,$before);
    // Only this transaction's temporary rollback copies are removed, never orders.
    $remove=[];foreach(array_keys($pages)as $n)$remove[]=$backup.'/'.str_replace('/','__',$n);
    if(is_file($backup.'/previous-cache.zip'))$remove[]=$backup.'/previous-cache.zip';
    foreach($remove as $file)if(!unlink($file))throw new RuntimeException('BACKUP_CLEANUP_FAILED');
    if(!rmdir($backup))throw new RuntimeException('BACKUP_DIRECTORY_NOT_EMPTY');
    $result['previous_product_files_retained']=false;$result['previous_cache_retained']=false;$result['temporary_rollback_removed']=true;
    echo json_encode($result),"\n";exit;
}
