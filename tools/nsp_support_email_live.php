<?php
declare(strict_types=1);
// Scoped migration of public support email. No buyer orders, SMTP or payment code.
if ($argc !== 4 || !in_array($argv[1], ['apply','rollback'], true)) exit(2);
$mode=$argv[1];$root=realpath($argv[2]);$backup=rtrim($argv[3],'/');
if (!$root || !is_dir($root)) exit(3);
$old='marzhavbetone@yandex.ru';
$new='nastoronepodryadchika@yandex.ru';
function require_ok(bool $ok,string $reason):void { if(!$ok) throw new RuntimeException($reason); }
function atomic_write(string $path,string $data):void {
    $tmp=tempnam(dirname($path),'.support-next-');
    require_ok($tmp!==false,'TEMP_FAILED');
    try {
        require_ok(file_put_contents($tmp,$data,LOCK_EX)===strlen($data),'WRITE_FAILED');
        chmod($tmp,0644);
        require_ok(rename($tmp,$path),'RENAME_FAILED');
    } finally { if(is_file($tmp))unlink($tmp); }
}
try {
    $xml=file_get_contents($root.'/sitemap.xml');
    require_ok($xml!==false,'SITEMAP_MISSING');
    preg_match_all('~<loc>([^<]+)</loc>~',$xml,$m);
    $files=[];
    foreach($m[1] as $loc) {
        $url=html_entity_decode($loc,ENT_QUOTES|ENT_XML1,'UTF-8');
        require_ok(str_starts_with($url,'https://nastoronepodryadchika.ru/'),'FOREIGN_URL');
        $rel=ltrim(rawurldecode((string)parse_url($url,PHP_URL_PATH)),'/');
        if($rel==='' || str_ends_with($rel,'/'))$rel.='index.html';
        require_ok(!str_contains($rel,'..') && str_ends_with($rel,'.html'),'UNSAFE_PATH');
        $files[$rel]=$root.'/'.$rel;
    }
    foreach(['404.html','test-pokupka.html'] as $p)$files[$p]=$root.'/'.$p;
    require_ok(count($files)>=80 && count($files)<=100,'UNEXPECTED_PAGE_COUNT');
    foreach($files as $file)require_ok(is_file($file),'PUBLIC_FILE_MISSING');
    if($mode==='rollback') {
        $manifest=$backup.'/.manifest.json';
        require_ok(is_file($manifest),'BACKUP_MANIFEST_MISSING');
        $names=json_decode((string)file_get_contents($manifest),true,512,JSON_THROW_ON_ERROR);
        foreach($names as $rel) {
            require_ok(isset($files[$rel]) && is_file($backup.'/'.$rel),'BACKUP_INCOMPLETE');
            atomic_write($files[$rel],(string)file_get_contents($backup.'/'.$rel));
        }
        echo "PUBLIC_SUPPORT_ROLLBACK=PASS\n";
        exit(0);
    }
    $changes=[];
    foreach($files as $rel=>$file) {
        $body=file_get_contents($file);
        require_ok($body!==false,'READ_FAILED');
        if(str_contains($body,$old))$changes[$rel]=str_replace($old,$new,$body);
    }
    if(!$changes) {
        echo "PUBLIC_SUPPORT_ALREADY_UPDATED=YES\n";
        exit(0);
    }
    require_ok(!file_exists($backup),'BACKUP_ALREADY_EXISTS');
    require_ok(mkdir($backup,0700,true),'BACKUP_CREATE_FAILED');
    chmod($backup,0700);
    foreach($changes as $rel=>$body) {
        $dst=$backup.'/'.$rel;
        $dir=dirname($dst);
        if(!is_dir($dir))require_ok(mkdir($dir,0700,true),'BACKUP_SUBDIR_FAILED');
        require_ok(copy($files[$rel],$dst),'BACKUP_COPY_FAILED');
        chmod($dst,0600);
        require_ok(hash_file('sha256',$files[$rel])===hash_file('sha256',$dst),'BACKUP_HASH_MISMATCH');
    }
    $manifest=json_encode(array_keys($changes),JSON_THROW_ON_ERROR);
    require_ok(file_put_contents($backup.'/.manifest.json',$manifest)!==false,'MANIFEST_WRITE_FAILED');
    chmod($backup.'/.manifest.json',0600);
    try {
        foreach($changes as $rel=>$body)atomic_write($files[$rel],$body);
        foreach($files as $rel=>$file)require_ok(!str_contains((string)file_get_contents($file),$old),'OLD_EMAIL_REMAINS');
    } catch(Throwable $e) {
        foreach($changes as $rel=>$body)atomic_write($files[$rel],(string)file_get_contents($backup.'/'.$rel));
        throw $e;
    }
    echo "PUBLIC_SUPPORT_FILES_UPDATED=".count($changes)."\n";
    echo "PUBLIC_SUPPORT_PAGES_CHECKED=".count($files)."\n";
    echo "PUBLIC_SUPPORT_EMAIL=VERIFIED\n";
} catch(Throwable $e) {
    fwrite(STDERR,"SUPPORT_EMAIL_CHANGE_FAILED=".$e->getMessage()."\n");
    exit(1);
}
