<?php
declare(strict_types=1);
// Bounded static-file transaction; all configuration, orders and masters are excluded.
function demand(bool $ok,string $why): void { if(!$ok) throw new RuntimeException($why); }
function sha(string $p): string { demand(is_file($p)&&!is_link($p),'MISSING_OR_SYMLINK'); return (string)hash_file('sha256',$p); }
function public_download(string $p): bool { return in_array($p,['downloads/checklist-zakrytiya-rabot.pdf','downloads/dengi.zip','downloads/dop-raboty.zip','downloads/vozvrat-ks.zip','downloads/uderzhaniya.zip','downloads/dogovor.zip','downloads/bankrotstvo.zip','downloads/avans.zip','downloads/raschet-metrami.zip','downloads/ispolnitelnaya-dokumentaciya.zip','downloads/akt-skrytyh-rabot.zip'],true); }
function current_sha(string $p): ?string { if(!file_exists($p)&&!is_link($p)) return null; return sha($p); }
function remove_created_dirs(string $root,string $dir): void {
    $p=$dir.'/created-dirs.json'; if(!is_file($p)) return;
    foreach(json_decode((string)file_get_contents($p),true,512,JSON_THROW_ON_ERROR) as $name) {
        demand($name==='downloads','UNSAFE_CREATED_DIRECTORY'); $folder=$root.'/'.$name;
        if(is_dir($folder)&&!is_link($folder)&&count(scandir($folder))===2) demand(rmdir($folder),'REMOVE_EMPTY_DIRECTORY');
    }
}
function write_atomic(string $p,string $bytes): void {
    $mode=is_file($p)?fileperms($p)&0777:0644; $tmp=tempnam(dirname($p),'.nsp-final-'); demand($tmp!==false,'TEMP_FAILED');
    try { demand(file_put_contents($tmp,$bytes,LOCK_EX)===strlen($bytes),'WRITE_FAILED'); chmod($tmp,$mode); demand(rename($tmp,$p),'RENAME_FAILED'); }
    finally { if(is_file($tmp)) unlink($tmp); }
}
function protected_state(string $root): array {
    $php=[]; foreach(glob($root.'/*.php') as $p) $php[basename($p)]=sha($p); ksort($php);
    require_once $root.'/config.php'; require_once $root.'/products-config.php';
    $paths=[]; foreach(['PRODUCTS_DIR','ORDERS_DIR','DELIVERY_DIR'] as $key) {
        demand(defined($key),'MISSING_RUNTIME_PATH'); $path=realpath((string)constant($key)); demand(is_string($path)&&is_dir($path),'MISSING_RUNTIME_DIRECTORY'); $paths[$key]=$path;
    }
    demand(strpos($paths['PRODUCTS_DIR'],$root.'/')!==0,'MASTERS_IN_WEBROOT');
    $masters=[]; $it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($paths['PRODUCTS_DIR'],FilesystemIterator::SKIP_DOTS));
    foreach($it as $p) {
        demand(!$p->isLink(),'MASTER_SYMLINK'); if(!$p->isFile()) continue;
        $masters[substr($p->getPathname(),strlen($paths['PRODUCTS_DIR'])+1)]=sha($p->getPathname());
        demand(count($masters)<2000,'MASTERS_LIMIT');
    }
    ksort($masters); demand(count($masters)>=172,'MASTERS_MISSING');
    $prices=['p1'=>2990000,'p2'=>2490000,'p3'=>1790000,'p4'=>2490000,'p5'=>2990000,'p7'=>2490000,'p8'=>2490000,'p9'=>2490000,'p10'=>1790000,'p11'=>2490000,'p13'=>1790000,'t2'=>990000,'t3'=>1490000];
    foreach($prices as $sku=>$price) { $p=mvb_resolve_product(['sku'=>$sku]); demand(is_array($p)&&$p['price']===$price,'RUNTIME_PRICE_'.$sku); }
    foreach(['t1','t4','t5','t6','p12'] as $sku) demand(mvb_resolve_product(['sku'=>$sku])===null,'ARCHIVED_SALE_'.$sku);
    demand(DELIVERY_TTL_SECONDS===3600,'TTL_CHANGED');
    return ['php'=>$php,'runtime_paths'=>$paths,'masters_count'=>count($masters),'masters_sha256'=>hash('sha256',json_encode($masters,JSON_THROW_ON_ERROR)),'sku_prices'=>$prices,'ttl'=>DELIVERY_TTL_SECONDS];
}
function restore(string $root,string $dir,array $rows,array $names): void {
    foreach($rows as $r) {
        if(!in_array($r['path'],$names,true)) continue;
        $p=$root.'/'.$r['path']; $current=current_sha($p); if($current===$r['before']) continue;
        demand($current===$r['after'],'ROLLBACK_CONCURRENT_EDIT_'.$r['path']);
        if($r['before']===null) { demand(unlink($p),'REMOVE_NEW_FILE'); continue; }
        demand(sha($dir.'/original/'.$r['path'])===$r['before'],'BACKUP_MISMATCH');
        write_atomic($p,(string)file_get_contents($dir.'/original/'.$r['path'])); demand(sha($p)===$r['before'],'ROLLBACK_HASH');
    }
}
$changed=[]; $rows=[]; $root=''; $dir='';
try {
    demand($argc===4&&in_array($argv[1],['dry-run','apply','verify','rollback'],true),'ARGS'); $mode=$argv[1];
    $root=realpath($argv[2]); $dir=realpath($argv[3]); demand(is_string($root)&&is_string($dir),'DIRECTORY');
    demand(basename($root)==='nastoronepodryadchika.ru','WRONG_SITE'); demand(strpos($dir,$root.'/')!==0&&$dir!==$root,'PRIVATE_INSIDE_WEBROOT');
    $rows=json_decode((string)file_get_contents($dir.'/manifest.json'),true,512,JSON_THROW_ON_ERROR);
    demand(is_array($rows)&&count($rows)>0&&count($rows)<=100,'MANIFEST_COUNT'); $seen=[];
    foreach($rows as $r) {
        $p=$r['path']; demand(public_download($p)||(bool)preg_match('~^(?:articles/|materialy/|products/|demo/)?[a-zA-Z0-9_-]+\.(?:html|js|css)$~D',$p),'UNSAFE_PATH');
        demand(!isset($seen[$p]),'DUPLICATE_PATH'); $seen[$p]=true;
        $parent=dirname($root.'/'.$p);
        demand(!is_link($parent),'PARENT_SYMLINK');
        if(public_download($p)&&!file_exists($parent)) demand($parent===$root.'/downloads','MISSING_PARENT');
        else demand(is_dir($parent)&&strpos((string)realpath($parent).'/',$root.'/')===0,'PATH_ESCAPE');
        foreach(['before','after'] as $k) {
            if($k==='before'&&$r[$k]===null){demand(public_download($p),'UNSAFE_CREATION');continue;}
            demand(is_string($r[$k])&&(bool)preg_match('/^[a-f0-9]{64}$/D',$r[$k]),'HASH_FORMAT');
        }
    }
    $state=protected_state($root);
    if($mode==='verify'||$mode==='rollback') {
        $baseline=json_decode((string)file_get_contents($dir.'/protected.json'),true,512,JSON_THROW_ON_ERROR);
        demand($state===$baseline,'PROTECTED_STATE_CHANGED');
        if($mode==='rollback') { restore($root,$dir,$rows,array_keys($seen)); remove_created_dirs($root,$dir); }
        else foreach($rows as $r) demand(sha($root.'/'.$r['path'])===$r['after'],'LIVE_HASH_'.$r['path']);
        echo json_encode(['status'=>'PASS','mode'=>$mode,'protected_php'=>'UNCHANGED','masters'=>'UNCHANGED','masters_count'=>$state['masters_count'],'sku'=>13,'ttl'=>3600],JSON_THROW_ON_ERROR)."\n"; exit;
    }
    foreach($rows as $r) {
        demand(current_sha($root.'/'.$r['path'])===$r['before'],'LIVE_CONCURRENT_EDIT_'.$r['path']);
        demand(sha($dir.'/candidate/'.$r['path'])===$r['after'],'CANDIDATE_HASH');
    }
    if($mode==='dry-run') { echo json_encode(['status'=>'PASS','mode'=>$mode,'files'=>count($rows),'sku'=>13,'masters_count'=>$state['masters_count'],'runtime_paths_read'=>true,'writes_to_public'=>0],JSON_THROW_ON_ERROR)."\n"; exit; }
    demand(!file_exists($dir.'/original')&&!file_exists($dir.'/protected.json'),'TRANSACTION_ALREADY_USED');
    mkdir($dir.'/original',0700);
    foreach($rows as $r) {
        if($r['before']===null) continue;
        $p=$dir.'/original/'.$r['path']; if(!is_dir(dirname($p))) mkdir(dirname($p),0700,true);
        demand(copy($root.'/'.$r['path'],$p),'BACKUP_COPY'); chmod($p,0600); demand(sha($p)===$r['before'],'BACKUP_HASH');
    }
    file_put_contents($dir.'/protected.json',json_encode($state,JSON_THROW_ON_ERROR)); chmod($dir.'/protected.json',0600);
    $createdDirs=[];
    if(count(array_filter(array_keys($seen),'public_download'))>0&&!is_dir($root.'/downloads')) { demand(!file_exists($root.'/downloads')&&!is_link($root.'/downloads'),'DOWNLOADS_CONCURRENT_EDIT'); demand(mkdir($root.'/downloads',0755),'CREATE_DOWNLOADS'); $createdDirs[]='downloads'; }
    file_put_contents($dir.'/created-dirs.json',json_encode($createdDirs,JSON_THROW_ON_ERROR)); chmod($dir.'/created-dirs.json',0600);
    foreach($createdDirs as $name) demand(chmod($root.'/'.$name,0755),'PUBLIC_DIRECTORY_MODE');
    foreach($rows as $r) {
        $p=$root.'/'.$r['path']; demand(current_sha($p)===$r['before'],'LIVE_CONCURRENT_EDIT_'.$r['path']);
        write_atomic($p,(string)file_get_contents($dir.'/candidate/'.$r['path'])); $changed[]=$r['path']; demand(sha($p)===$r['after'],'WRITE_HASH');
    }
    demand(protected_state($root)===$state,'PROTECTED_STATE_CHANGED');
    echo json_encode(['status'=>'PASS','mode'=>'apply','files'=>count($changed),'protected_php'=>'UNCHANGED','masters'=>'UNCHANGED'],JSON_THROW_ON_ERROR)."\n";
} catch(Throwable $e) {
    if($changed) { try { restore($root,$dir,$rows,$changed); echo "AUTO_ROLLBACK=PASS\n"; } catch(Throwable $r) { fwrite(STDERR,'ROLLBACK_FAILED='.$r->getMessage()."\n"); } }
    if($dir&&$root) { try { remove_created_dirs($root,$dir); } catch(Throwable $cleanup) { fwrite(STDERR,'DIRECTORY_CLEANUP_FAILED='.$cleanup->getMessage()."\n"); } }
    fwrite(STDERR,'NSP_TRANSACTION_FAILED='.$e->getMessage()."\n"); exit(1);
}
