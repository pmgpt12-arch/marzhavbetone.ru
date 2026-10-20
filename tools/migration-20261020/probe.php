<?php
/** Run over existing deployment SSH stdin. Never prints credentials or order data. */
declare(strict_types=1);
ini_set('display_errors','0');
error_reporting(E_ALL);
set_time_limit(160);
$contract = json_decode(base64_decode('__CONTRACT_B64__',true),true,512,JSON_THROW_ON_ERROR);
function gate(bool $ok,string $code):void { if(!$ok) throw new RuntimeException($code); }
function contained(string $path,string $root):bool {return $path===$root || str_starts_with($path,$root.'/');}
function inventory(string $root):array {
    gate(is_dir($root),'MASTER_DIRECTORY_MISSING');$files=[];
    $iterator=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS));
    foreach($iterator as $file){
        if(!$file->isFile())continue;
        if(in_array($file->getBasename(),['.htaccess','00-PISMO-POSLE-POKUPKI.txt','MANIFEST.md'],true))continue;
        gate(!$file->isLink(),'BUYER_FILE_SYMLINK');
        $path=$file->getPathname();$real=realpath($path);
        gate(is_string($real)&&contained($real,$root),'BUYER_FILE_ESCAPES_MASTER_ROOT');
        $name=substr($path,strlen($root)+1);$sha=hash_file('sha256',$path);
        gate(is_string($sha),'BUYER_FILE_UNREADABLE');
        $files[$name]=['size'=>filesize($path),'sha256'=>$sha];
    }
    ksort($files,SORT_STRING);return $files;
}
function private_summary(string $root):array {
    $count=0;$size=0;$iterator=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS));
    foreach($iterator as $file){if($file->isFile()){$count++;$size+=$file->getSize();}}
    return ['files'=>$count,'bytes'=>$size];
}
function archive_private(string $source,string $target):array {
    gate(is_dir($source),'BACKUP_SOURCE_NOT_DIRECTORY');gate(!file_exists($target),'BACKUP_ALREADY_EXISTS');
    $cmd='tar -cpf '.escapeshellarg($target).' -C '.escapeshellarg($source).' . 2>/dev/null';
    exec($cmd,$out,$code);gate($code===0,'BACKUP_TAR_FAILED');chmod($target,0600);
    exec('tar -tf '.escapeshellarg($target).' >/dev/null 2>&1',$out,$verify);gate($verify===0,'BACKUP_TAR_VERIFY_FAILED');
    return ['file'=>$target,'size'=>filesize($target),'sha256'=>hash_file('sha256',$target),'mode'=>substr(sprintf('%o',fileperms($target)),-4),'tar_readable'=>true];
}
try {
    gate(PHP_SAPI==='cli'&&count($argv)===5,'ARGUMENT_CONTRACT');
    [$self,$siteArg,$productsArg,$phase,$tag]=$argv;
    gate(in_array($phase,['inspect','backup'],true),'UNSUPPORTED_PHASE');
    gate((bool)preg_match('/^run-[0-9]+$/D',$tag),'INVALID_RUN_TAG');
    $home=realpath((string)getenv('HOME'));$site=realpath($siteArg);$mastersArg=realpath($productsArg);
    gate(is_string($home)&&is_string($site)&&is_string($mastersArg),'PATH_RESOLUTION_FAILED');
    gate(contained($site,$home)&&contained($mastersArg,$home),'PATH_OUTSIDE_AUTHORIZED_HOME');
    gate(!is_link($siteArg)&&!is_link($productsArg),'ROOT_SYMLINK_NOT_ACCEPTED');
    gate(is_file($site.'/index.html')&&is_file($site.'/config.php')&&is_file($site.'/products-config.php'),'SITE_MARKERS_MISSING');
    $new=realpath(dirname($site).'/'.$contract['new_domain']);
    gate(is_string($new)&&$new!==$site&&contained($new,$home),'NEW_SITE_ROOT_NOT_DISTINCT');
    gate(!is_link(dirname($site).'/'.$contract['new_domain']),'NEW_SITE_SYMLINK');
    ob_start();require $site.'/config.php';require $site.'/products-config.php';ob_end_clean();
    $masters=realpath(PRODUCTS_DIR);$orders=realpath(ORDERS_DIR);$delivery=realpath(DELIVERY_DIR);
    gate(is_string($masters)&&is_string($orders)&&is_string($delivery),'RUNTIME_PATH_MISSING');
    gate($masters===$mastersArg,'DEPLOY_PRODUCTS_PATH_DIFFERS_FROM_RUNTIME');
    foreach([$masters,$orders,$delivery] as $p)gate(contained($p,$home),'RUNTIME_PATH_OUTSIDE_HOME');
    gate(!contained($masters,$site)&&!contained($masters,$new),'MASTERS_INSIDE_WEBROOT');
    $catalog=mvb_products();$active=[];
    foreach($catalog as $sku=>$item){if($sku!=='test1'&&mvb_resolve_product(['sku'=>$sku])!==null)$active[]=$sku;}
    sort($active);$wanted=array_keys($contract['active_skus']);sort($wanted);gate($active===$wanted,'ACTIVE_CATALOG_NOT_APPROVED_13_SKUS');
    $items=[];$total=0;
    foreach($contract['active_skus'] as $sku=>$expected){
        $item=$catalog[$sku];gate($item['price']===$expected['price']&&$item['dir']===$expected['dir'],'CATALOG_PRICE_OR_DIRECTORY_DRIFT_'.$sku);
        $dir=realpath($masters.'/'.$item['dir']);gate(is_string($dir)&&contained($dir,$masters),'SKU_DIRECTORY_MISSING_'.$sku);
        $members=inventory($dir);gate(count($members)===$expected['files'],'BUYER_FILE_COUNT_DRIFT_'.$sku);
        $items[$sku]=['name'=>$item['name'],'price'=>$item['price'],'dir'=>$item['dir'],'zip'=>$item['zip'],'files'=>$members];$total+=count($members);
    }
    gate($total===$contract['buyer_files_total'],'BUYER_TOTAL_NOT_172');
    gate(defined('DELIVERY_TTL_SECONDS')&&(int)DELIVERY_TTL_SECONDS===3600,'LIVE_TTL_NOT_3600');
    gate(function_exists('mvb_capture_p1_edition'),'P1_EDITION_FUNCTION_MISSING');
    $code=[];foreach(['index.html','katalog.html','products-config.php','payment.php','webhook.php','check-payment.php','download.php','success.html','.htaccess','robots.txt','sitemap.xml'] as $name){if(is_file($site.'/'.$name))$code[$name]=hash_file('sha256',$site.'/'.$name);}
    $result=[
        'status'=>'PASS_READ_ONLY_LIVE_BASELINE','run'=>$tag,'observed_at'=>gmdate('c'),
        'paths'=>['home'=>$home,'old_site'=>$site,'new_site'=>$new,'masters'=>$masters,'orders'=>$orders,'delivery'=>$delivery],
        'runtime'=>['site_url'=>defined('SITE_URL')?SITE_URL:null,'ttl_seconds'=>DELIVERY_TTL_SECONDS,'payment_mode'=>defined('YOOKASSA_MODE')?YOOKASSA_MODE:null,'http_basic_credentials_present'=>defined('YOOKASSA_SHOP_ID')&&defined('YOOKASSA_SECRET_KEY')&&YOOKASSA_SHOP_ID!==''&&YOOKASSA_SECRET_KEY!=='','support_email'=>defined('ADMIN_EMAIL')?ADMIN_EMAIL:null,'p1_capture_function'=>true,'new_config_exists'=>is_file($new.'/config.php')],
        'orders_counts_only'=>private_summary($orders),'code_sha256'=>$code,'active_skus'=>$active,'buyer_files'=>$total,'products'=>$items,
        'new_root_index_sha256'=>is_file($new.'/index.html')?hash_file('sha256',$new.'/index.html'):null,
        'config_sha256_not_contents'=>hash_file('sha256',$site.'/config.php'),
        'master_directory_private'=>true,'production_changed'=>false
    ];
    if($phase==='backup'){
        $root=$home.'/nsp-migration-backups';if(!is_dir($root))gate(mkdir($root,0700),'BACKUP_ROOT_CREATE_FAILED');chmod($root,0700);
        gate(!contained($root,$site)&&!contained($root,$new),'BACKUP_INSIDE_WEBROOT');
        $dest=$root.'/'.$tag;gate(!file_exists($dest),'BACKUP_TAG_EXISTS');gate(mkdir($dest,0700),'BACKUP_TAG_CREATE_FAILED');
        $need=0;foreach([$site,$new,$masters,$orders] as $folder)$need+=private_summary($folder)['bytes'];
        gate(disk_free_space($root)>$need*1.5+33554432,'INSUFFICIENT_PRIVATE_BACKUP_SPACE');
        $result['backups']=[];
        foreach(['old-site'=>$site,'new-site-before'=>$new,'masters'=>$masters,'orders-and-cache'=>$orders] as $name=>$folder)$result['backups'][$name]=archive_private($folder,$dest.'/'.$name.'.tar');
        $result['backup_location']=$dest;$result['status']='PASS_PRIVATE_BACKUPS_AND_FULL_MANIFEST';
        $safe=['created_at'=>gmdate('c'),'source_paths'=>$result['paths'],'backups'=>$result['backups'],'restore_rule'=>'Never overwrite live orders with an older snapshot. Restore code/config only; preserve current order store. Roll back redirects before reverting active site.'];
        file_put_contents($dest.'/receipt.json',json_encode($safe,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES));chmod($dest.'/receipt.json',0600);
    }
    echo json_encode($result,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);
} catch(Throwable $e) {
    while(ob_get_level()>0)ob_end_clean();
    $m=$e instanceof RuntimeException?$e->getMessage():'RUNTIME_EXCEPTION_'.get_class($e);
    if(!preg_match('/^[A-Z0-9_]+(?:[a-z0-9]+)?$/D',$m))$m='SANITIZED_REMOTE_FAILURE';
    fwrite(STDERR,$m."\n");exit(2);
}
