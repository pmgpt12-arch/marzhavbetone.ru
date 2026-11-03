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
    echo json_encode($result,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR),"\n";
}catch(Throwable $e){
    fwrite(STDERR,'P4P7_INSPECT_FAIL='.$e->getMessage()."\n");exit(2);
}
