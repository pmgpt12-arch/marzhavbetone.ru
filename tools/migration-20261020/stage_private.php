<?php
/** CLI only. Private candidate, fake payment credentials, synthetic orders.
 * Never changes either public root, current orders, live config or masters. */
declare(strict_types=1);
ini_set('display_errors','0');error_reporting(E_ALL);set_time_limit(180);umask(0077);
function gate(bool $ok,string $code):void{if(!$ok)throw new RuntimeException($code);}
function inside(string $p,string $root):bool{return $p===$root||str_starts_with($p,$root.'/');}
function tree_hashes(string $root):array{
    $out=[];$it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS));
    foreach($it as $f){gate(!$f->isLink(),'TREE_SYMLINK');if(!$f->isFile())continue;
        $out[substr($f->getPathname(),strlen($root)+1)]=['size'=>$f->getSize(),'sha256'=>hash_file('sha256',$f->getPathname())];}
    ksort($out,SORT_STRING);return $out;
}
function copy_public_tree(string $from,string $to):void{
    if(!is_dir($to))gate(mkdir($to,0755),'PUBLIC_COPY_MKDIR');chmod($to,0755);
    foreach(new DirectoryIterator($from) as $f){if($f->isDot())continue;gate(!$f->isLink(),'PUBLIC_COPY_SYMLINK');
        $dest=$to.'/'.$f->getFilename();
        if($f->isDir())copy_public_tree($f->getPathname(),$dest);
        else{gate(copy($f->getPathname(),$dest),'PUBLIC_COPY_FILE');chmod($dest,0644);}}
}
function save_json(string $path,array $data):void{
    gate(file_put_contents($path,json_encode($data,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_PRETTY_PRINT|JSON_THROW_ON_ERROR))!==false,'PRIVATE_WRITE_FAILED');
    chmod($path,0600);
}
try{
    gate(PHP_SAPI==='cli'&&count($argv)===2,'CLI_CONTRACT');$phase=$argv[1];
    gate(in_array($phase,['init','verify-build'],true),'PHASE_INVALID');
    $p=json_decode(base64_decode('__PAYLOAD__',true),true,512,JSON_THROW_ON_ERROR);
    $paths=$p['paths'];$home=realpath((string)getenv('HOME'));
    gate($home===$paths['home'],'AUTHORIZED_HOME_CHANGED');
    gate((bool)preg_match('/^run-[0-9]+$/D',$p['run']),'RUN_INVALID');
    $parent=$home.'/nsp-migration-private';$work=$parent.'/'.$p['run'].'-stage';$site=$work.'/site';
    gate(!is_link($parent)&&is_dir($parent)&&inside($work,$parent),'PRIVATE_PARENT_INVALID');
    $new=realpath($paths['new_site']);$old=realpath($paths['old_site']);
    gate($new===$paths['new_site']&&$old===$paths['old_site']&&$old!==$new,'PUBLIC_ROOT_CHANGED');
    gate(!file_exists($new.'/config.php'),'PUBLIC_CONFIG_APPEARED');
    $newTree=tree_hashes($new);
    gate(hash_equals($p['new_root_tree_sha256'],hash('sha256',json_encode($newTree,JSON_UNESCAPED_SLASHES))),'NEW_ROOT_CHANGED_SINCE_DRY_RUN');
    if($phase==='init'){
        gate(!file_exists($work),'PRIVATE_STAGE_ALREADY_EXISTS');gate(mkdir($work,0700),'STAGE_CREATE');
        copy_public_tree($new,$site);
        save_json($work.'/stage-contract.json',$p);
        echo json_encode(['status'=>'PASS_PRIVATE_STAGE_CREATED','workspace'=>$work,'site'=>$site,
            'preserved_new_root_files'=>count($newTree),'live_webroots_modified'=>false]);exit;
    }
    gate(is_dir($site)&&is_file($work.'/stage-contract.json')&&!is_link($work),'STAGE_NOT_INITIALIZED');
    $saved=json_decode(file_get_contents($work.'/stage-contract.json'),true,512,JSON_THROW_ON_ERROR);
    gate($saved===$p,'PRIVATE_STAGE_CONTRACT_DRIFT');
    foreach($p['shipping'] as $r){
        $rel=$r['file'];gate(!str_contains($rel,'..')&&!str_starts_with($rel,'/'),'SHIPPING_PATH_INVALID');
        gate($rel!=='config.php'&&!preg_match('~^(orders|delivery|products-storage|tools)/~',$rel),'SHIPPING_PRIVATE_DATA');
        $file=$site.'/'.$rel;$resolved=realpath($file);
        gate(is_string($resolved)&&inside($resolved,$site)&&!is_link($file),'SHIPPING_MISSING_OR_SYMLINK');
        gate(filesize($file)===$r['size']&&hash_equals($r['sha256'],hash_file('sha256',$file)),'SHIPPING_HASH_MISMATCH');chmod($file,0644);
    }
    $masters=realpath($paths['masters']);gate($masters===$paths['masters']&&!inside($masters,$site),'MASTER_PATH_DRIFT');
    $orders=$work.'/synthetic-orders';$delivery=$orders.'/delivery';
    gate(!file_exists($orders)&&!file_exists($site.'/config.php'),'SANDBOX_ALREADY_INITIALIZED');
    gate(mkdir($orders,0700)&&mkdir($delivery,0700),'SANDBOX_CREATE');
    $constants=[
        'SITE_URL'=>$p['site_url'],'ADMIN_EMAIL'=>$p['support_email'],
        'ORDERS_DIR'=>$orders,'DELIVERY_DIR'=>$delivery,'PRODUCTS_DIR'=>$masters,
        'DELIVERY_TTL_SECONDS'=>3600,'YOOKASSA_SHOP_ID'=>'migration-disabled',
        'YOOKASSA_SECRET_KEY'=>'migration-disabled','YOOKASSA_MODE'=>'test',
        'YOOKASSA_API_URL'=>'https://disabled.invalid','NSP_MIGRATION_STAGE'=>true,
    ];
    $config="<?php\ndeclare(strict_types=1);\n// Isolated migration sandbox: no production keys or orders.\n";
    foreach($constants as $k=>$v)$config.='define('.var_export($k,true).', '.var_export($v,true).");\n";
    gate(file_put_contents($site.'/config.php',$config)!==false,'SANDBOX_CONFIG_WRITE');chmod($site.'/config.php',0600);
    $overlay=<<<'HT'
# Temporary acceptance mode. Remove only after real-payment activation gate.
<IfModule mod_headers.c>
    Header always set X-Robots-Tag "noindex, nofollow, noarchive"
    Header always set Cache-Control "no-store"
</IfModule>
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteRule ^(?:payment|webhook|check-payment|contact)\.php$ - [R=503,L]
</IfModule>

HT;
    $originalHt=file_get_contents($site.'/.htaccess');gate(is_string($originalHt),'HTACCESS_MISSING');
    gate(file_put_contents($site.'/.htaccess',$overlay.$originalHt)!==false,'HTACCESS_STAGE_WRITE');chmod($site.'/.htaccess',0644);
    gate(file_put_contents($site.'/robots.txt',"User-agent: *\nDisallow: /\n")!==false,'ROBOTS_STAGE_WRITE');chmod($site.'/robots.txt',0644);
    require $site.'/config.php';require $site.'/products-config.php';
    gate(DELIVERY_TTL_SECONDS===3600&&function_exists('mvb_capture_p1_edition'),'RUNTIME_CONTRACT');
    $catalog=mvb_products();$active=[];
    foreach($catalog as $sku=>$item)if($sku!=='test1'&&mvb_resolve_product(['sku'=>$sku])!==null)$active[]=$sku;
    sort($active);$expected=array_keys($p['products']);sort($expected);gate($active===$expected&&count($active)===13,'ACTIVE_CATALOG_DRIFT');
    foreach(['t1','t4','t5','t6','p12'] as $retired)gate(mvb_resolve_product(['sku'=>$retired])===null,'RETIRED_SKU_AVAILABLE');
    $results=[];$probes=[];$total=0;
    foreach($p['products'] as $sku=>$accepted){
        foreach(['name','price','dir','zip'] as $key)gate($catalog[$sku][$key]===$accepted[$key],'CATALOG_METADATA_DRIFT');
        foreach($accepted['files'] as $member=>$meta){
            $file=$masters.'/'.$accepted['dir'].'/'.$member;
            gate(is_file($file)&&!is_link($file)&&filesize($file)===$meta['size']&&hash_equals($meta['sha256'],hash_file('sha256',$file)),'MASTER_SHA_DRIFT');
        }
        $position=['sku'=>$sku];
        if($sku==='p1'){$position['edition']=mvb_capture_p1_edition();gate(is_array($position['edition']),'P1_EDITION_CAPTURE_FAILED');}
        $id='order_'.date('Ymd_His').'_nspmig'.bin2hex(random_bytes(8));
        $order=['id'=>$id,'status'=>'paid','email'=>'','items'=>[$position],
            'total'=>$accepted['price'],'migration_probe'=>true,'provider_payment_performed'=>false];
        $prepared=mvb_prepare_delivery($order);
        gate(count($prepared['links'])===1&&!$prepared['missing']&&$prepared['links'][0]['sku']===$sku,'DELIVERY_PREPARATION_FAILED');
        $ttl=strtotime($order['delivery']['expires_at'])-strtotime($order['delivery']['created_at']);
        gate($ttl===3600,'TTL_NOT_EXACTLY_3600');
        $url=$prepared['links'][0]['url'];gate(parse_url($url,PHP_URL_HOST)===parse_url($p['site_url'],PHP_URL_HOST),'DOWNLOAD_WRONG_HOST');
        $mail=mvb_delivery_email($order,$prepared['links']);
        gate(str_contains($mail,'1 час')&&str_contains($mail,$p['site_url']),'EMAIL_RENDER_WRONG_DOMAIN_OR_TTL');
        $beforeDelivery=$order['delivery'];$again=mvb_prepare_delivery($order);
        gate($order['delivery']===$beforeDelivery&&$again['links']===$prepared['links'],'REPEATED_PREPARATION_CHANGES_TOKEN');
        $name=$order['delivery']['items'][$sku];gate(basename($name)===$name,'ZIP_PATH_ESCAPE');
        $zipPath=$delivery.'/'.$name;$zip=new ZipArchive();
        gate($zip->open($zipPath,ZipArchive::CHECKCONS)===true,'ZIP_CRC_OPEN_FAILED');
        gate($zip->numFiles===count($accepted['files']),'ZIP_MEMBER_COUNT_DRIFT');
        $seen=[];
        for($i=0;$i<$zip->numFiles;$i++){
            $st=$zip->statIndex($i);gate(is_array($st),'ZIP_STAT_FAILED');$n=$st['name'];
            gate(isset($accepted['files'][$n])&&!isset($seen[$n]),'ZIP_UNEXPECTED_OR_DUPLICATE_MEMBER');
            $bytes=$zip->getFromIndex($i);gate(is_string($bytes),'ZIP_READ_FAILED');$meta=$accepted['files'][$n];
            gate(strlen($bytes)===$meta['size']&&hash_equals($meta['sha256'],hash('sha256',$bytes)),'ZIP_MEMBER_SHA_DRIFT');
            gate(sprintf('%u',crc32($bytes))===sprintf('%u',$st['crc']),'ZIP_MEMBER_CRC_DRIFT');$seen[$n]=true;
        }
        $zip->close();chmod($zipPath,0600);
        save_json($orders.'/'.$id.'.json',$order);
        $probes[$sku]=['id'=>$id,'url'=>$url,'zip'=>$name,'expected_download_name'=>$accepted['zip']];
        $results[$sku]=['files'=>count($seen),'member_sha256_pass'=>true,'crc_pass'=>true,
            'zip_sha256'=>hash_file('sha256',$zipPath),'ttl_seconds'=>$ttl,'download_host'=>parse_url($url,PHP_URL_HOST),
            'email_render'=>'PASS_NOT_SENT','token_reuse_pass'=>true,'p1_edition_captured'=>$sku==='p1'];
        $total+=count($seen);
    }
    gate($total===172,'TOTAL_BUYER_FILE_COUNT');
    save_json($work.'/private-probe-links.json',$probes);
    $stageTree=tree_hashes($site);save_json($work.'/stage-site-manifest.json',$stageTree);
    $out=['status'=>'PASS_PRIVATE_HOST_CANDIDATE_AND_13_ARCHIVES','workspace'=>$work,'site'=>$site,
        'source_candidate'=>$p['candidate_commit'],'shipping_files'=>count($p['shipping']),
        'synthetic_order_count'=>count($probes),'active_skus'=>count($results),'buyer_files'=>$total,
        'products'=>$results,'stage_tree_sha256'=>hash('sha256',json_encode($stageTree,JSON_UNESCAPED_SLASHES)),
        'staged_total_files'=>count($stageTree),'public_files_not_modified'=>true,
        'masters_read_only'=>true,'live_orders_or_caches_modified'=>false,'real_payment'=>false,'emails_sent'=>0,
        'credentials'=>'DUMMY_DISABLED_NO_LIVE_SECRETS','payment_endpoints'=>'STAGING_503',
        'next'=>'Controlled publication of this candidate for real HTTPS download and privacy checks; old store unchanged'];
    save_json($work.'/private-stage-receipt.json',$out);
    echo json_encode($out,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);
}catch(Throwable $e){
    $m=$e instanceof RuntimeException?$e->getMessage():'PRIVATE_STAGE_RUNTIME_ERROR';
    if(!preg_match('/^[A-Z0-9_]+$/D',$m))$m='SANITIZED_STAGE_ERROR';
    fwrite(STDERR,$m."\n");exit(2);
}
