<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') exit(3);
function check(bool $v,string $label):void { if(!$v) throw new RuntimeException($label); }
function shas(string $folder):array {
    check(is_dir($folder) && !is_link($folder),'INVALID_SOURCE_DIR');
    $v=[];
    foreach(new DirectoryIterator($folder) as $f){
        if($f->isDot()) continue;
        check($f->isFile() && !$f->isLink(),'NONFLAT_OR_UNSAFE_SOURCE');
        $v[$f->getFilename()] = hash_file('sha256',$f->getPathname());
    }
    ksort($v);
    return $v;
}
try {
    $site=realpath($argv[1]??'');
    check(is_string($site) && basename($site)==='nastoronepodryadchika.ru','INVALID_SITE');
    require $site.'/config.php';
    require $site.'/products-config.php';
    $private=realpath(PRODUCTS_DIR);
    $cache=realpath(DELIVERY_DIR);
    check(is_string($private) && is_string($cache) && !str_starts_with($private,$site.'/'),'PRIVATE_DIR_CONTRACT');
    $products=mvb_products();
    $result=['status'=>'P4_P7_PRODUCTION_READ_ONLY','scope'=>['p4','p7'],
        'site_php_sha'=>hash_file('sha256',$site.'/products-config.php'),
        'payment_php_sha'=>hash_file('sha256',$site.'/payment.php'),
        'private_products_location'=>basename($private),
        'delivery_ttl'=>defined('DELIVERY_TTL_SECONDS') ? DELIVERY_TTL_SECONDS : null,
        'products'=>[]];
    foreach(['p4','p7'] as $sku){
        $p=$products[$sku]??null;
        check(is_array($p),'SKU_ABSENT_'.$sku);
        $src=$private.'/'.$p['dir'];
        $target=$cache.'/'.$p['zip'];
        $rows=shas($src);
        check(is_file($target) && !is_link($target),'CACHE_MISSING_'.$sku);
        $masters=[];
        $pattern=$sku==='p4'?'P4*.zip':'P7*.zip';
        foreach(glob($private.'/'.$pattern)?:[] as $candidate){
            if(is_file($candidate) && !is_link($candidate)){
                $masters[basename($candidate)]=hash_file('sha256',$candidate);
            }
        }
        ksort($masters);
        $result['products'][$sku]=[
            'name'=>$p['name'],'dir'=>$p['dir'],'zip'=>$p['zip'],'price'=>$p['price'],
            'source_count'=>count($rows),'sources'=>$rows,
            'cache_sha256'=>hash_file('sha256',$target),
            'master_archives'=>$masters
        ];
    }
    $attempt=getenv('HOME').'/nsp-p4p7-releases/style-41628988319';
    $result['previous_attempt_probe']=[
       'stage_present'=>is_dir($attempt),
       'config_prepared'=>is_file($attempt.'/config-after.php'),
       'rollback_dir'=>is_dir($attempt.'/rollback'),
       'backup_config'=>is_file($attempt.'/rollback/products-config.php'),
       'backup_cache_p4'=>is_file($attempt.'/rollback/cache-p4.zip'),
       'backup_cache_p7'=>is_file($attempt.'/rollback/cache-p7.zip'),
       'fresh_p4'=>is_dir($attempt.'/source-p4'),
       'fresh_p7'=>is_dir($attempt.'/source-p7'),
       'discard_p4'=>is_dir($attempt.'/rollback/discard-p4'),
       'discard_p7'=>is_dir($attempt.'/rollback/discard-p7'),
       'old_source_backup_p4'=>is_dir($attempt.'/rollback/source-p4'),
       'old_source_backup_p7'=>is_dir($attempt.'/rollback/source-p7')
    ];
    echo json_encode($result,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR),"\n";
}catch(Throwable $e){
    fwrite(STDERR,'P4P7_INSPECT_FAIL='.$e->getMessage()."\n");exit(2);
}
