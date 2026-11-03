<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') exit(9);
function gate(bool $yes, string $why):void {if (!$yes) throw new RuntimeException($why);}
function digest(string $path):string {
    gate(is_file($path) && !is_link($path),'UNSAFE_FILE:'.basename($path));
    return (string)hash_file('sha256',$path);
}
function inventory(string $path):array {
    gate(is_dir($path) && !is_link($path),'INVALID_SOURCE_DIR');
    $r=[];
    foreach (new DirectoryIterator($path) as $f) {
        if ($f->isDot()) continue;
        gate($f->isFile() && !$f->isLink(),'NONFLAT_SOURCE');
        $r[$f->getFilename()]=digest($f->getPathname());
    }
    ksort($r);return $r;
}
function atomic_write(string $path,string $data):void {
    $tmp=tempnam(dirname($path),'.nsp-p4p7-');
    gate(is_string($tmp),'TEMP_FAILED');
    try {
        $mode=is_file($path)?fileperms($path)&0777:0644;
        gate(file_put_contents($tmp,$data,LOCK_EX)===strlen($data),'TEMP_WRITE_FAILED');
        chmod($tmp,$mode);
        gate(rename($tmp,$path),'ATOMIC_RENAME_FAILED');
    }finally {if(is_file($tmp)) unlink($tmp);}
}
$mode=$argv[1]??'';
gate(in_array($mode,['preflight','apply','verify','rollback','read-current'],true),'INVALID_MODE');
$site=realpath($argv[2]??'');
$stage=realpath($argv[3]??'');
gate(is_string($site) && basename($site)==='nastoronepodryadchika.ru','SITE_IDENTITY');
gate(is_string($stage) && !str_starts_with($stage,$site.'/'),'PRIVATE_STAGE');
$m=json_decode((string)file_get_contents($stage.'/release.json'),true,512,JSON_THROW_ON_ERROR);
gate(($m['schema']??'')==='NSP_P4P7_PALETTE_RELEASE_V1','MANIFEST_SCHEMA');
gate(array_keys($m['products']??[])===['p4','p7'] && $m['ttl']===3600,'SCOPE');
require $site.'/config.php';
require $site.'/products-config.php';
$root=realpath(PRODUCTS_DIR);$delivery=realpath(DELIVERY_DIR);
gate(is_string($root) && is_string($delivery) && !str_starts_with($root,$site.'/'),'PRIVATE_PRODUCT_ROOT');
gate(DELIVERY_TTL_SECONDS===3600,'DELIVERY_TTL_DRIFT');
$catalog=mvb_products();$backup=$stage.'/rollback';
function paths(string $sku):array {
    global $m,$root,$delivery,$stage,$backup;
    $p=$m['products'][$sku];
    return ['source'=>$root.'/'.$p['dir'],'cache'=>$delivery.'/'.$p['zip'],
        'oldmaster'=>$root.'/'.$p['old_master'],'newmaster'=>$root.'/'.$p['new_master'],
        'fresh'=>$stage.'/source-'.$sku,'previous'=>$backup.'/source-'.$sku,
        'oldcache'=>$backup.'/cache-'.$sku.'.zip'];
}
function final_config(string $source):array {
    global $m;
    $binding=[];
    foreach (['p4','p7'] as $sku) {
        $p=$m['products'][$sku];
        $oldsha=$p['before_sha'];$newsha=$p['after_sha'];
        $oldname='/'.$p['old_master'];$newname='/'.$p['new_master'];
        $a=substr_count($source,$oldsha);$b=substr_count($source,$oldname);
        gate(($a===0&&$b===0)||($a===1&&$b===1),'EDITION_BINDING_AMBIGUOUS:'.$sku);
        if($a===1) {
            $source=str_replace($oldsha,$newsha,$source,$n);
            gate($n===1,'EDITION_SHA_PATCH');
            $source=str_replace($oldname,$newname,$source,$n);
            gate($n===1,'EDITION_MASTER_PATCH');
            $binding[$sku]='REBOUND';
        }else {$binding[$sku]='NO_EXPLICIT_EDITION_BINDING';}
    }
    token_get_all($source,TOKEN_PARSE);
    return [$source,$binding];
}
function before():array {
    global $m,$site,$catalog,$stage,$backup;
    gate(!is_dir($backup),'ATTEMPT_ALREADY_STARTED');
    gate(digest($site.'/products-config.php')===$m['config_before'],'CONFIG_CHANGED');
    gate(digest($site.'/payment.php')===$m['payment_before'],'PAYMENT_CHANGED');
    $checks=[];
    foreach(['p4','p7'] as $sku) {
        $p=$m['products'][$sku];$x=paths($sku);
        $c=$catalog[$sku]??null;
        gate(is_array($c)&&$c['price']===$p['price']&&$c['dir']===$p['dir']&&$c['zip']===$p['zip'],'SKU_DRIFT:'.$sku);
        $orig=$p['before_members'];ksort($orig);
        gate(inventory($x['source'])===$orig,'SOURCE_DRIFT:'.$sku);
        gate(digest($x['cache'])===$p['before_sha'],'CACHE_DRIFT:'.$sku);
        gate(digest($x['oldmaster'])===$p['before_sha'],'MASTER_DRIFT:'.$sku);
        gate(!is_file($x['newmaster'])&&!file_exists($x['fresh']),'TARGET_ALREADY_EXISTS:'.$sku);
        $zip=$stage.'/'.$sku.'.zip';
        gate(digest($zip)===$p['after_sha'],'NEW_ARCHIVE_SHA:'.$sku);
        $z=new ZipArchive();
        gate($z->open($zip)===true,'NEW_ZIP_BAD');
        gate($z->numFiles===$p['count'],'MEMBER_COUNT:'.$sku);
        $found=[];
        for($i=0;$i<$z->numFiles;$i++){
            $name=$z->getNameIndex($i);
            gate(is_string($name)&&basename($name)===$name&&!isset($found[$name]),'UNSAFE_ARCHIVE_MEMBER');
            $data=$z->getFromIndex($i);
            gate(is_string($data),'ZIP_MEMBER_READ');
            $found[$name]=hash('sha256',$data);
        }
        $z->close();ksort($found);
        $target=$p['after_members'];ksort($target);
        gate($found===$target,'NEW_MEMBER_SHA_DRIFT:'.$sku);
        $checks[$sku]=['files'=>count($orig),'new_sha256'=>$p['after_sha']];
    }
    return $checks;
}
function verify():array {
    global $m,$site,$stage,$backup;
    gate(is_dir($backup),'BACKUP_ABSENT');
    gate(digest($site.'/products-config.php')===digest($stage.'/config-after.php'),'CONFIG_FINAL_DRIFT');
    gate(digest($site.'/payment.php')===$m['payment_before'],'PAYMENT_MUTATED');
    $out=[];
    foreach(['p4','p7'] as $sku) {
        $p=$m['products'][$sku];$x=paths($sku);
        $target=$p['after_members'];ksort($target);
        $old=$p['before_members'];ksort($old);
        gate(inventory($x['source'])===$target,'NEW_SOURCE_NOT_EXACT:'.$sku);
        gate(inventory($x['previous'])===$old,'PREVIOUS_SOURCE_BACKUP_DRIFT:'.$sku);
        gate(digest($x['oldmaster'])===$p['before_sha'],'HISTORIC_MASTER_DRIFT:'.$sku);
        gate(digest($x['newmaster'])===$p['after_sha'],'NEW_MASTER_DRIFT:'.$sku);
        gate(digest($x['cache'])===$p['after_sha'],'DELIVERY_CACHE_DRIFT:'.$sku);
        $effective=mvb_build_product_zip($sku);
        gate(is_string($effective)&&digest($effective)===$p['after_sha'],'BUYER_BUILDER_DRIFT:'.$sku);
        $out[$sku]=['sha256'=>$p['after_sha'],'files'=>count($target),'delivery_builder'=>'PASS'];
    }
    return $out;
}
function rollback():void {
    global $backup,$stage,$site,$m;
    gate(is_dir($backup),'NO_ROLLBACK_STAGE');
    foreach(['p4','p7'] as $sku){
        $p=$m['products'][$sku];$x=paths($sku);
        if (is_dir($x['previous'])) {
            if (is_dir($x['source'])) {
                $current=inventory($x['source']);
                $old=$p['before_members'];ksort($old);
                $new=$p['after_members'];ksort($new);
                gate($current===$old||$current===$new,'FOREIGN_SOURCE_CHANGE:'.$sku);
                if ($current===$new) gate(rename($x['source'],$backup.'/discard-'.$sku),'PARK_NEW_SOURCE_FAILED');
            }
            if (!is_dir($x['source'])) gate(rename($x['previous'],$x['source']),'RESTORE_SOURCE_FAILED:'.$sku);
        }
        if(is_file($x['oldcache'])) {
            $current=digest($x['cache']);
            gate($current===$p['before_sha']||$current===$p['after_sha'],'FOREIGN_CACHE_CHANGE');
            atomic_write($x['cache'],(string)file_get_contents($x['oldcache']));
        }
        if(is_file($x['newmaster'])) {
            gate(digest($x['newmaster'])===$p['after_sha'],'FOREIGN_NEW_MASTER');
            unlink($x['newmaster']);
        }
        gate(digest($x['oldmaster'])===$p['before_sha'],'HISTORIC_MASTER_CHANGED');
    }
    if (is_file($backup.'/products-config.php')) {
        $current=digest($site.'/products-config.php');
        gate(in_array($current,[$m['config_before'],digest($stage.'/config-after.php')],true),'FOREIGN_CONFIG_CHANGE');
        atomic_write($site.'/products-config.php',(string)file_get_contents($backup.'/products-config.php'));
    }
    gate(digest($site.'/products-config.php')===$m['config_before'],'ROLLBACK_CONFIG_FAIL');
    gate(digest($site.'/payment.php')===$m['payment_before'],'ROLLBACK_PAYMENT_FAIL');
}
try {
    if($mode==='preflight'||$mode==='apply'){
        $checks=before();
        [$next,$pins]=final_config((string)file_get_contents($site.'/products-config.php'));
        if($mode==='preflight'){
            file_put_contents($stage.'/config-after.php',$next,LOCK_EX);
            echo json_encode(['status'=>'PREFLIGHT_PASS','scope'=>$checks,'pins'=>$pins,'production_writes'=>false],JSON_THROW_ON_ERROR),"\n";
            exit(0);
        }
        gate(is_file($stage.'/config-after.php')&&
             digest($stage.'/config-after.php')===hash('sha256',$next),'CONFIG_PREFLIGHT_CHANGED');
        gate(mkdir($backup,0700),'BACKUP_EXISTS');
        gate(copy($site.'/products-config.php',$backup.'/products-config.php'),'BACKUP_CONFIG');
        foreach(['p4','p7'] as $sku){
            $p=$m['products'][$sku];$x=paths($sku);
            gate(copy($x['cache'],$x['oldcache']),'BACKUP_CACHE');
            gate(digest($x['oldcache'])===$p['before_sha'],'BACKUP_CACHE_CORRUPT');
            gate(mkdir($x['fresh'],0755),'STAGE_DIR_FAILED');
            $z=new ZipArchive();gate($z->open($stage.'/'.$sku.'.zip')===true,'STAGE_ARCHIVE_OPEN');
            foreach($p['after_members'] as $name=>$expected){
                $data=$z->getFromName($name);
                gate(is_string($data)&&hash('sha256',$data)===$expected,'STAGE_MEMBER_BAD');
                gate(file_put_contents($x['fresh'].'/'.$name,$data)===strlen($data),'STAGE_MEMBER_WRITE');
                chmod($x['fresh'].'/'.$name,0644);
            }
            $z->close();$new=$p['after_members'];ksort($new);
            gate(inventory($x['fresh'])===$new,'STAGED_DIR_MISMATCH');
        }
        foreach(['p4','p7'] as $sku){
            $p=$m['products'][$sku];$x=paths($sku);
            atomic_write($x['newmaster'],(string)file_get_contents($stage.'/'.$sku.'.zip'));
            gate(rename($x['source'],$x['previous']),'MOVE_OLD_SOURCE');
            gate(rename($x['fresh'],$x['source']),'MOVE_NEW_SOURCE');
            atomic_write($x['cache'],(string)file_get_contents($stage.'/'.$sku.'.zip'));
        }
        atomic_write($site.'/products-config.php',$next);
        $result=verify();
        echo json_encode(['status'=>'APPLIED_AND_VERIFIED','products'=>$result],JSON_THROW_ON_ERROR),"\n";
        exit(0);
    }
    if($mode==='verify') {
        echo json_encode(['status'=>'PRODUCTION_VERIFIED','products'=>verify()],JSON_THROW_ON_ERROR),"\n";exit(0);
    }
    if($mode==='read-current'){
        $sku=$argv[4]??'';gate(in_array($sku,['p4','p7'],true),'SKU_SCOPE');
        verify();$x=paths($sku);
        readfile($x['cache']);exit(0);
    }
    if($mode==='rollback'){
        rollback();echo "{\"status\":\"ROLLBACK_VERIFIED\"}\n";exit(0);
    }
}catch(Throwable $ex){
    if($mode==='apply'&&is_dir($backup)){
        try {rollback();fwrite(STDERR,"AUTOMATIC_ROLLBACK_OK\n");}
        catch(Throwable $rb){fwrite(STDERR,"MANUAL_RECOVERY_REQUIRED=".$rb->getMessage()."\n");}
    }
    fwrite(STDERR,"NSP_SCOPED_RELEASE_ERROR=".$ex->getMessage()."\n");exit(2);
}
