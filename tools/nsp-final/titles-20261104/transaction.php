<?php
declare(strict_types=1);
/* NSP 2026-11-04: scoped 8 public HTML title release. No payment, product, or order writes. */
if (PHP_SAPI !== 'cli') exit(9);
function gate(bool $ok, string $why): void { if (!$ok) throw new RuntimeException($why); }
function sha(string $path): string {
    gate(is_file($path) && !is_link($path), 'MISSING_OR_LINK:'.basename($path));
    $h=hash_file('sha256',$path);
    gate(is_string($h),'HASH_FAIL');
    return $h;
}
function atomic_write(string $path, string $bytes): void {
    $tmp=tempnam(dirname($path),'.nsp-title-');
    gate(is_string($tmp),'TMP_FAILED');
    try {
        $mode=fileperms($path)&0777;
        gate(file_put_contents($tmp,$bytes,LOCK_EX)===strlen($bytes),'WRITE_FAILED');
        gate(chmod($tmp,$mode),'CHMOD_FAILED');
        gate(rename($tmp,$path),'RENAME_FAILED');
    } finally { if (is_file($tmp)) @unlink($tmp); }
}
$mode=$argv[1]??'';
gate(in_array($mode,['preflight','apply','verify','rollback'],true),'UNSUPPORTED_ACTION');
$site=realpath($argv[2]??'');$stage=realpath($argv[3]??'');
gate(is_string($site)&&basename($site)==='nastoronepodryadchika.ru','WRONG_SITE');
gate(is_string($stage)&&!str_starts_with($stage,$site.'/')&&$stage!==$site,'PRIVATE_STAGE_REQUIRED');
$m=json_decode((string)file_get_contents($stage.'/manifest.json'),true,512,JSON_THROW_ON_ERROR);
gate(($m['schema']??'')==='NSP_TITLES_8_STATIC_V1','MANIFEST_SCHEMA');
gate(($m['count']??0)===8&&count($m['files']??[])===8,'COUNT_MUST_BE_8');
$allowed=[
 'katalog.html','products/p3-shablony-ks2-ks3.html',
 'products/p7-dogovor-podryada.html','products/p8-avans-po-dogovoru-subpodryada.html',
 'products/p9-bankrotstvo-genpodryadchika.html','products/p10-otvet-na-pretenziyu.html',
 'products/p11-raschet-metrami.html','products/p13-chto-v-smete-ne-oplatyat.html'
];
sort($allowed);
$rows=[];
foreach ($m['files'] as $r) {
    gate(is_array($r),'ROW_FORMAT');
    $path=$r['path']??'';
    gate(in_array($path,$allowed,true)&&!isset($rows[$path]),'UNSAFE_OR_DUPLICATE_PATH');
    foreach(['before','after'] as $key) gate(is_string($r[$key]??null)&&preg_match('/^[a-f0-9]{64}$/D',$r[$key])===1,'SHA_FORMAT');
    $rows[$path]=$r;
}
$selected=array_keys($rows);sort($selected);
gate($selected===$allowed,'SCOPE_MISMATCH');
require_once $site.'/config.php';
require_once $site.'/products-config.php';
gate(defined('PRODUCTS_DIR')&&defined('DELIVERY_DIR')&&defined('DELIVERY_TTL_SECONDS'),'BACKEND_CONFIG_MISSING');
gate(DELIVERY_TTL_SECONDS===3600,'TTL_CHANGED');
$products=realpath(PRODUCTS_DIR);$delivery=realpath(DELIVERY_DIR);
gate(is_string($products)&&is_string($delivery)&&!str_starts_with($products,$site.'/'),'PRIVATE_BUYER_DIR');
$prices=['p1'=>2990000,'p2'=>2490000,'p3'=>1790000,'p4'=>2490000,'p5'=>2990000,'p7'=>2490000,'p8'=>2490000,'p9'=>2490000,'p10'=>1790000,'p11'=>2490000,'p13'=>1790000];
$catalog=mvb_products();
foreach($prices as $sku=>$price) gate(isset($catalog[$sku])&&$catalog[$sku]['price']===$price,'PRODUCT_PRICE_DRIFT:'.$sku);
function zip_inventory(string $dir): array {
    gate(is_dir($dir)&&!is_link($dir),'ZIP_DIRECTORY_UNSAFE');
    $rows=[];
    foreach(glob($dir.'/*.zip')?:[] as $file) {
        gate(!is_link($file),'ZIP_LINK_UNSAFE');
        $rows[basename($file)]=sha($file);
        gate(count($rows)<=150,'ZIP_INVENTORY_LIMIT');
    }
    ksort($rows);
    return $rows;
}
function protected_state(): array {
    global $site,$products,$delivery,$prices;
    $php=[];
    foreach(glob($site.'/*.php')?:[] as $f) {
        $php[basename($f)]=sha($f);
        gate(count($php)<100,'PHP_INVENTORY_LIMIT');
    }
    ksort($php);
    gate(isset($php['config.php'],$php['products-config.php'],$php['payment.php']),'PROTECTED_PHP_MISSING');
    return ['php'=>$php,
            'masters'=>zip_inventory($products),
            'buyer_cache'=>zip_inventory($delivery),
            'sku_prices'=>$prices,'ttl'=>DELIVERY_TTL_SECONDS];
}
function check_files(bool $after): array {
    global $site,$stage,$rows;
    $out=[];
    foreach($rows as $path=>$r) {
        $p=$site.'/'.$path;
        gate(is_file($p)&&!is_link($p)&&realpath(dirname($p))===dirname($p),'PUBLIC_PATH_UNSAFE:'.$path);
        $expected=$r[$after?'after':'before'];
        gate(sha($p)===$expected,'PUBLIC_SOURCE_DRIFT:'.$path);
        if(!$after) {
            $candidate=$stage.'/candidate/'.$path;
            gate(sha($candidate)===$r['after'],'CANDIDATE_DRIFT:'.$path);
            gate(filesize($candidate)<300000&&filesize($candidate)>2000,'UNEXPECTED_CANDIDATE_SIZE');
        }
        $out[$path]=$expected;
    }
    return $out;
}
$backup=$stage.'/rollback';
function restore(): array {
    global $site,$stage,$rows,$backup;
    gate(is_dir($backup)&&is_file($backup.'/protected.json'),'ROLLBACK_ABSENT');
    $protected=json_decode((string)file_get_contents($backup.'/protected.json'),true,512,JSON_THROW_ON_ERROR);
    $done=[];
    foreach($rows as $path=>$r) {
        $current=sha($site.'/'.$path);
        gate($current===$r['before']||$current===$r['after'],'CONCURRENT_MODIFICATION:'.$path);
        $saved=$backup.'/original/'.$path;
        gate(sha($saved)===$r['before'],'BACKUP_CORRUPTED:'.$path);
        if($current===$r['after']) atomic_write($site.'/'.$path,(string)file_get_contents($saved));
        gate(sha($site.'/'.$path)===$r['before'],'RESTORE_FAILED:'.$path);
        $done[]=$path;
    }
    gate(protected_state()===$protected,'BACKEND_MUTATED_DURING_ROLLBACK');
    return $done;
}
try {
    if($mode==='preflight'||$mode==='apply') {
        gate(!file_exists($backup),'STAGE_ALREADY_USED');
        $old=protected_state();$checks=check_files(false);
        if($mode==='preflight') {
            echo json_encode(['status'=>'PREFLIGHT_PASS','scope'=>count($checks),
                'production_writes'=>false,'prices'=>count($prices),'buyer_cache_count'=>count($old['buyer_cache'])],JSON_THROW_ON_ERROR),"\n";
            exit(0);
        }
        gate(mkdir($backup,0700),'BACKUP_DIR_FAILED');
        gate(mkdir($backup.'/original',0700),'BACKUP_TREE_FAILED');
        foreach($rows as $path=>$r){
            $target=$backup.'/original/'.$path;
            if(!is_dir(dirname($target))) gate(mkdir(dirname($target),0700,true),'BACKUP_SUBDIR_FAILED');
            gate(copy($site.'/'.$path,$target),'BACKUP_COPY_FAIL:'.$path);
            gate(chmod($target,0600)&&sha($target)===$r['before'],'BACKUP_VERIFY_FAIL:'.$path);
        }
        gate(file_put_contents($backup.'/protected.json',json_encode($old,JSON_THROW_ON_ERROR),LOCK_EX)!==false,'BACKUP_PROTECTED_FAIL');
        chmod($backup.'/protected.json',0600);
        foreach($rows as $path=>$r) {
            gate(sha($site.'/'.$path)===$r['before'],'CONCURRENT_SOURCE_CHANGE:'.$path);
            atomic_write($site.'/'.$path,(string)file_get_contents($stage.'/candidate/'.$path));
            gate(sha($site.'/'.$path)===$r['after'],'WRITE_SHA_FAIL:'.$path);
        }
        gate(protected_state()===$old,'PROTECTED_BACKEND_CHANGED');
        $done=check_files(true);
        echo json_encode(['status'=>'APPLIED_AND_VERIFIED','files'=>count($done),
             'backend'=>'UNCHANGED','payment'=>'UNCHANGED','master_zips'=>'UNCHANGED'],JSON_THROW_ON_ERROR),"\n";exit(0);
    }
    gate(is_dir($backup),'ROLLBACK_STATE_MISSING');
    $old=json_decode((string)file_get_contents($backup.'/protected.json'),true,512,JSON_THROW_ON_ERROR);
    if($mode==='verify') {
        gate(protected_state()===$old,'PROTECTED_DRIFT');
        $checks=check_files(true);
        echo json_encode(['status'=>'VERIFIED','files'=>count($checks),'backend'=>'UNCHANGED',
            'payment'=>'UNCHANGED','buyer_caches'=>'UNCHANGED'],JSON_THROW_ON_ERROR),"\n";exit(0);
    }
    $restored=restore();
    echo json_encode(['status'=>'ROLLBACK_VERIFIED','files'=>count($restored)],JSON_THROW_ON_ERROR),"\n";
}catch(Throwable $e) {
    if($mode==='apply'&&is_dir($backup)) {
        try {restore();fwrite(STDERR,"AUTOMATIC_ROLLBACK_PASS\n");}
        catch(Throwable $rb){fwrite(STDERR,"MANUAL_RECOVERY_REQUIRED=".$rb->getMessage()."\n");}
    }
    fwrite(STDERR,"NSP_TITLES_RELEASE_ERROR=".$e->getMessage()."\n");exit(2);
}
