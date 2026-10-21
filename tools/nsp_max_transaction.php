<?php
declare(strict_types=1);
// Two public HTML files only. Payment/configuration files are read for hashes only.
function ok(bool $value, string $message): void { if (!$value) throw new RuntimeException($message); }
function digest(string $path): string { ok(is_file($path) && !is_link($path), 'MISSING_OR_SYMLINK'); $hash=hash_file('sha256',$path); ok(is_string($hash),'HASH_FAILED'); return $hash; }
function atomic(string $path, string $bytes): void {
    $mode=fileperms($path)&0777; $tmp=tempnam(dirname($path),'.nsp-max-'); ok($tmp!==false,'TEMP_FAILED');
    try { ok(file_put_contents($tmp,$bytes,LOCK_EX)===strlen($bytes),'WRITE_FAILED'); ok(chmod($tmp,$mode),'CHMOD_FAILED'); ok(rename($tmp,$path),'RENAME_FAILED'); }
    finally { if(is_file($tmp)) unlink($tmp); }
}
function protected_hashes(string $root): array {
    $out=[]; foreach(['config.php','payment.php','webhook.php','products-config.php'] as $name) $out[$name]=digest($root.'/'.$name); return $out;
}
function restore(string $root,string $dir,array $manifest,array $only): void {
    foreach($manifest as $row) {
        $name=$row['path']; if(!in_array($name,$only,true)) continue;
        $current=digest($root.'/'.$name);
        if($current===$row['before']) continue;
        ok($current===$row['after'],'ROLLBACK_CONCURRENT_EDIT_'.$name);
        ok(digest($dir.'/original/'.$name)===$row['before'],'ROLLBACK_BACKUP_MISMATCH');
        atomic($root.'/'.$name,(string)file_get_contents($dir.'/original/'.$name));
        ok(digest($root.'/'.$name)===$row['before'],'ROLLBACK_VERIFY_FAILED');
    }
}
$changed=[]; $manifest=[]; $root=''; $dir='';
try {
    ok($argc===4 && in_array($argv[1],['apply','verify','rollback'],true),'INVALID_ARGUMENTS');
    $mode=$argv[1]; $root=realpath($argv[2]); $dir=realpath($argv[3]);
    ok(is_string($root)&&is_string($dir),'MISSING_DIRECTORY');
    ok(basename($root)==='nastoronepodryadchika.ru','WRONG_SITE');
    ok(strpos($dir,$root.'/')!==0 && $dir!==$root,'BACKUP_INSIDE_WEBROOT');
    $manifest=json_decode((string)file_get_contents($dir.'/manifest.json'),true,512,JSON_THROW_ON_ERROR);
    ok(is_array($manifest)&&count($manifest)===2,'WRONG_MANIFEST_COUNT');
    ok(array_column($manifest,'path')===['index.html','katalog.html'],'WRONG_MANIFEST_PATHS');
    foreach($manifest as $row) foreach(['before','after'] as $field) ok((bool)preg_match('/^[a-f0-9]{64}$/',$row[$field]??''),'INVALID_HASH');
    if($mode==='rollback') {
        $baseline=json_decode((string)file_get_contents($dir.'/protected.json'),true,512,JSON_THROW_ON_ERROR);
        restore($root,$dir,$manifest,['index.html','katalog.html']);
        ok(protected_hashes($root)===$baseline,'PROTECTED_FILES_CHANGED');
        echo "MAX_ROLLBACK=PASS\nPAYMENT_CONFIG_BYTES_UNCHANGED=PASS\n"; exit(0);
    }
    if($mode==='verify') {
        $baseline=json_decode((string)file_get_contents($dir.'/protected.json'),true,512,JSON_THROW_ON_ERROR);
        foreach($manifest as $row) ok(digest($root.'/'.$row['path'])===$row['after'],'LIVE_HASH_MISMATCH');
        ok(protected_hashes($root)===$baseline,'PROTECTED_FILES_CHANGED');
        echo "MAX_LIVE_HASHES=PASS\nPAYMENT_CONFIG_BYTES_UNCHANGED=PASS\n"; exit(0);
    }
    ok(!file_exists($dir.'/protected.json')&&!file_exists($dir.'/original'),'BACKUP_ALREADY_EXISTS');
    $baseline=protected_hashes($root); $candidates=[];
    foreach($manifest as $row) {
        $name=$row['path']; ok(digest($root.'/'.$name)===$row['before'],'LIVE_CONCURRENT_EDIT_'.$name);
        ok(digest($dir.'/candidate/'.$name)===$row['after'],'CANDIDATE_HASH_MISMATCH');
        $bytes=file_get_contents($dir.'/candidate/'.$name); ok(is_string($bytes),'READ_FAILED');
        ok(!preg_match('~(?:https?:)?//(?:www\.)?max\.ru(?:[/?#\x22\x27]|$)~i',$bytes),'MAX_URL_REMAINS');
        $candidates[$name]=$bytes;
    }
    ok(mkdir($dir.'/original',0700),'BACKUP_CREATE_FAILED');
    foreach($manifest as $row) {
        $name=$row['path']; ok(copy($root.'/'.$name,$dir.'/original/'.$name),'BACKUP_COPY_FAILED');
        ok(chmod($dir.'/original/'.$name,0600),'BACKUP_CHMOD_FAILED');
        ok(digest($dir.'/original/'.$name)===$row['before'],'BACKUP_HASH_MISMATCH');
    }
    $json=json_encode($baseline,JSON_THROW_ON_ERROR);
    ok(file_put_contents($dir.'/protected.json',$json)===strlen($json),'SNAPSHOT_WRITE_FAILED'); chmod($dir.'/protected.json',0600);
    foreach($manifest as $row) {
        $name=$row['path']; ok(digest($root.'/'.$name)===$row['before'],'LIVE_CONCURRENT_EDIT_'.$name);
        if($row['before']!==$row['after']) { atomic($root.'/'.$name,$candidates[$name]); $changed[]=$name; }
        ok(digest($root.'/'.$name)===$row['after'],'LIVE_WRITE_MISMATCH');
    }
    ok(protected_hashes($root)===$baseline,'PROTECTED_FILES_CHANGED');
    echo 'MAX_LIVE_FILES_CHANGED='.count($changed)."\nMAX_APPLY=PASS\nPAYMENT_CONFIG_BYTES_UNCHANGED=PASS\n";
} catch(Throwable $error) {
    if($changed) {
        try { restore($root,$dir,$manifest,$changed); echo "MAX_AUTO_ROLLBACK=PASS\n"; }
        catch(Throwable $rollback) { fwrite(STDERR,'MAX_ROLLBACK_FAILED='.$rollback->getMessage()."\n"); }
    }
    fwrite(STDERR,'MAX_TRANSACTION_FAILED='.$error->getMessage()."\n"); exit(1);
}
