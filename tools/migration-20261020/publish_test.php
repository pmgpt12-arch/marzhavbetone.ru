<?php
/** CLI transaction for new-domain testing only. Old site is never written.
 * Live keys are absent. The original new root is parked for instant rollback. */
declare(strict_types=1);
ini_set('display_errors','0');error_reporting(E_ALL);set_time_limit(150);umask(0077);
function gate(bool $ok,string $code):void{if(!$ok)throw new RuntimeException($code);}
function nsp_tree(string $root):array{
    $out=[];$it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS));
    foreach($it as $f){gate(!$f->isLink(),'TREE_SYMLINK');if(!$f->isFile())continue;
        $out[substr($f->getPathname(),strlen($root)+1)]=['size'=>$f->getSize(),'sha256'=>hash_file('sha256',$f->getPathname())];}
    ksort($out,SORT_STRING);return $out;
}
function nsp_digest(array $a):string{return hash('sha256',json_encode($a,JSON_UNESCAPED_SLASHES));}
function nsp_save(string $file,array $data):void{
    gate(file_put_contents($file,json_encode($data,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_PRETTY_PRINT|JSON_THROW_ON_ERROR))!==false,'STATE_SAVE_FAILED');chmod($file,0600);
}
try{
    gate(PHP_SAPI==='cli'&&count($argv)===2,'CLI_ONLY');$phase=$argv[1];
    gate(in_array($phase,['publish','links','expire','rollback'],true),'INVALID_PHASE');
    $p=json_decode(base64_decode('__PAYLOAD__',true),true,512,JSON_THROW_ON_ERROR);
    $home=realpath((string)getenv('HOME'));gate($home===$p['paths']['home'],'HOME_CHANGED');
    $work=$p['workspace'];
    gate((bool)preg_match('~^'.preg_quote($home,'~').'/nsp-migration-private/run-[0-9]+-stage$~D',$work),'WORKSPACE_INVALID');
    gate(realpath($work)===$work&&!is_link($work),'WORKSPACE_RESOLUTION');
    $new=$p['paths']['new_site'];$old=$p['paths']['old_site'];$stage=$work.'/site';$parked=$work.'/new-root-before-http-test';
    gate($new===$home.'/www/'.$p['new_domain']&&realpath($old)===$old&&$old!==$new,'PUBLIC_PATH_CONTRACT');
    gate(!is_link($new)&&!is_link($parked),'PUBLIC_ROOT_SYMLINK');
    $stateFile=$work.'/http-switch-state.json';
    if($phase==='rollback'){
        if(!is_file($stateFile)){
            echo json_encode(['status'=>'NO_PUBLIC_SWITCH_ATTEMPTED','old_site_untouched'=>true]);exit;
        }
        $state=json_decode(file_get_contents($stateFile),true,512,JSON_THROW_ON_ERROR);
        if($state['status']==='ROLLED_BACK'){
            gate(is_dir($new)&&nsp_digest(nsp_tree($new))===$p['original_new_tree_sha256'],'RESTORED_ROOT_DRIFT');
            echo json_encode(['status'=>'ALREADY_ROLLED_BACK','old_site_untouched'=>true]);exit;
        }
        if(is_dir($parked)){
            if(is_dir($new)){
                gate(is_file($new.'/config.php')&&hash_file('sha256',$new.'/config.php')===$state['test_config_sha256'],'CONFIG_ACTIVATED_BY_ANOTHER_SESSION');
                gate(nsp_digest(nsp_tree($new))===$state['test_tree_sha256'],'TEST_ROOT_CHANGED_BEFORE_ROLLBACK');
                $rejected=$work.'/rejected-http-site';gate(!file_exists($rejected),'REJECTED_ROOT_EXISTS');
                gate(rename($new,$rejected),'PARK_FAILED_TEST_ROOT');
            }
            gate(!file_exists($new)&&rename($parked,$new),'RESTORE_ORIGINAL_ROOT');
        }
        gate(is_dir($new)&&nsp_digest(nsp_tree($new))===$p['original_new_tree_sha256'],'ROLLBACK_TREE_MISMATCH');
        $state['status']='ROLLED_BACK';$state['rollback_at']=gmdate('c');nsp_save($stateFile,$state);
        echo json_encode(['status'=>'PASS_NEW_ROOT_ROLLBACK','old_site_untouched'=>true,'real_orders_restored'=>false]);exit;
    }
    $accepted=json_decode(file_get_contents($work.'/private-stage-receipt.json'),true,512,JSON_THROW_ON_ERROR);
    gate($accepted['status']==='PASS_PRIVATE_HOST_CANDIDATE_AND_13_ARCHIVES'&&$accepted['buyer_files']===172,'PRIVATE_ACCEPTANCE_MISSING');
    if($phase==='publish'){
        gate(is_dir($new)&&is_dir($stage)&&!file_exists($parked)&&!file_exists($stateFile),'PUBLICATION_ALREADY_ATTEMPTED');
        gate(nsp_digest(nsp_tree($new))===$p['original_new_tree_sha256'],'NEW_ROOT_CHANGED_SINCE_BACKUP');
        gate(nsp_digest(nsp_tree($stage))===$accepted['stage_tree_sha256'],'PRIVATE_STAGE_HASH_DRIFT');
        gate(stat($new)['dev']===stat($stage)['dev'],'NONATOMIC_CROSS_DEVICE_MOVE');
        foreach($p['old_code_sha256'] as $name=>$hash)gate(hash_file('sha256',$old.'/'.$name)===$hash,'OLD_SITE_CODE_CHANGED');
        gate(hash_file('sha256',$old.'/config.php')===$p['old_config_sha256'],'OLD_CONFIG_CHANGED');
        $notice='<div data-nsp-staging="true" role="status" style="padding:12px 24px;text-align:center;border-bottom:1px solid currentColor">Проверочная версия нового сайта. Оплата временно отключена. <a href="https://marzhavbetone.ru/">Действующий магазин</a></div>';
        $htmlCount=0;
        foreach($p['shipping'] as $r){
            $rel=$r['file'];if(!str_ends_with($rel,'.html'))continue;
            gate(!str_contains($rel,'..')&&!str_starts_with($rel,'/'),'HTML_PATH_INVALID');
            $file=$stage.'/'.$rel;$text=file_get_contents($file);gate(is_string($text),'HTML_NOT_READABLE');
            gate(!str_contains($text,'data-nsp-staging="true"'),'STAGE_BANNER_ALREADY_EXISTS');
            $text=preg_replace_callback('~<body\b[^>]*>~i',fn($m)=>$m[0].$notice,$text,1,$count);gate($count===1,'BODY_ANCHOR_MISSING');
            $text=preg_replace('~<meta\s+name="robots"[^>]*>~i','<meta name="robots" content="noindex,nofollow,noarchive">',$text,-1,$metaCount);
            if($metaCount===0)$text=str_replace('</head>','<meta name="robots" content="noindex,nofollow,noarchive"></head>',$text,$headCount);
            gate(str_contains($text,'noindex,nofollow,noarchive'),'STAGE_NOINDEX_MISSING');
            gate(file_put_contents($file,$text)!==false,'STAGE_HTML_WRITE');chmod($file,0644);$htmlCount++;
        }
        gate($htmlCount===88,'STAGE_HTML_COUNT');
        $testTree=nsp_tree($stage);nsp_save($work.'/http-test-site-manifest.json',$testTree);
        $state=['status'=>'PREPARED','new_site'=>$new,'parked_original'=>$parked,'workspace'=>$work,
          'test_config_sha256'=>hash_file('sha256',$stage.'/config.php'),'test_tree_sha256'=>nsp_digest($testTree),
          'original_new_tree_sha256'=>$p['original_new_tree_sha256'],'created_at'=>gmdate('c'),
          'old_site_modified'=>false,'real_orders_modified'=>false];nsp_save($stateFile,$state);
        gate(rename($new,$parked),'PARK_ORIGINAL_NEW_ROOT');
        if(!rename($stage,$new)){
            gate(rename($parked,$new),'ROLLBACK_AFTER_RENAME_FAILURE');
            $state['status']='ROLLED_BACK';nsp_save($stateFile,$state);throw new RuntimeException('PUBLISH_RENAME_FAILED_ROLLED_BACK');
        }
        $state['status']='PUBLISHED_DISABLED_COMMERCE';nsp_save($stateFile,$state);
        echo json_encode(['status'=>'PASS_PUBLISHED_NEW_DOMAIN_TEST_MODE','new_domain'=>$p['new_domain'],
          'html_pages'=>$htmlCount,'site_tree_sha256'=>$state['test_tree_sha256'],
          'rollback_original_parked'=>true,'old_site_modified'=>false,'real_payment_enabled'=>false]);exit;
    }
    gate(is_file($stateFile),'NO_PUBLIC_STAGING_RECEIPT');
    $state=json_decode(file_get_contents($stateFile),true,512,JSON_THROW_ON_ERROR);
    gate($state['status']==='PUBLISHED_DISABLED_COMMERCE'&&is_dir($new)&&is_dir($parked),'NOT_IN_PUBLIC_TEST_MODE');
    gate(hash_file('sha256',$new.'/config.php')===$state['test_config_sha256'],'TEST_CONFIG_CHANGED');
    $probes=json_decode(file_get_contents($work.'/private-probe-links.json'),true,512,JSON_THROW_ON_ERROR);
    gate(count($probes)===13,'PROBE_SCOPE_CHANGED');
    if($phase==='links'){
        // Consumed in memory by Actions; NEVER put URLs/tokens in public evidence.
        echo json_encode($probes,JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);exit;
    }
    require $new.'/config.php';require $new.'/products-config.php';
    gate(YOOKASSA_SHOP_ID==='migration-disabled'&&ORDERS_DIR===$work.'/synthetic-orders','NOT_SANDBOX_CONFIG');
    foreach($probes as $sku=>$probe){
        $id=$probe['id'];gate((bool)preg_match('/^order_[0-9_]+_nspmig[a-f0-9]+$/D',$id),'PROBE_ORDER_ID_INVALID');
        $file=ORDERS_DIR.'/'.$id.'.json';
        $result=mvb_with_order_lock_strict($file,static function(array &$order){
            gate(($order['migration_probe']??false)===true&&($order['provider_payment_performed']??true)===false,'NOT_A_SYNTHETIC_ORDER');
            $order['delivery']['expires_at']=date('c',time()-1);return true;
        });gate($result['ok']&&$result['result']===true,'PROBE_EXPIRY_UPDATE_FAILED');
    }
    echo json_encode(['status'=>'PASS_13_SYNTHETIC_LINKS_EXPIRED','orders'=>count($probes),'real_orders_modified'=>false]);
}catch(Throwable $e){
    $m=$e instanceof RuntimeException?$e->getMessage():'STAGING_HTTP_RUNTIME_ERROR';
    if(!preg_match('/^[A-Z0-9_]+$/D',$m))$m='SANITIZED_STAGING_HTTP_ERROR';
    fwrite(STDERR,$m."\n");exit(2);
}
