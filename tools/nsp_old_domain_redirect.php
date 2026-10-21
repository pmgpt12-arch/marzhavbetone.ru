<?php
declare(strict_types=1);
// Narrow old-domain 301 cutover; preserve old robots, sitemap and ACME challenge.
if ($argc !== 4 || !in_array($argv[1], ['apply','rollback'],true)) exit(2);
[$script,$mode,$site,$backup]=$argv;
$file=rtrim($site,'/').'/.htaccess';
$marker='# NSP-301-DOMAIN-MIGRATION-20261021';
$block=<<<'APACHE'
# NSP-301-DOMAIN-MIGRATION-20261021
# Keep old robots/sitemap for discovery, and ACME for SSL renewal.
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteCond %{HTTP_HOST} ^(www\.)?marzhavbetone\.ru$ [NC]
    RewriteCond %{REQUEST_METHOD} ^(GET|HEAD)$
    RewriteCond %{REQUEST_URI} !^/robots\.txt$ [NC]
    RewriteCond %{REQUEST_URI} !^/sitemap\.xml$ [NC]
    RewriteCond %{REQUEST_URI} !^/\.well-known/acme-challenge/ [NC]
    RewriteRule ^(.*)$ https://nastoronepodryadchika.ru/$1 [R=301,L]
</IfModule>

APACHE;
function must(bool $ok,string $msg):void {if(!$ok)throw new RuntimeException($msg);}
function atomic(string $file,string $text):void {
    $tmp=tempnam(dirname($file),'.redirect-next-');
    must($tmp!==false,'TEMP_FAILED');
    try {
        must(file_put_contents($tmp,$text,LOCK_EX)!==false,'WRITE_FAILED');
        chmod($tmp,0644);
        must(rename($tmp,$file),'RENAME_FAILED');
    } finally {if(is_file($tmp))unlink($tmp);}
}
try {
    must(is_file($file),'OLD_HTACCESS_MISSING');
    if($mode==='rollback') {
        must(is_file($backup),'BACKUP_MISSING');
        atomic($file,(string)file_get_contents($backup));
        echo "OLD_REDIRECT_ROLLBACK=PASS\n";
        exit(0);
    }
    $original=file_get_contents($file);
    must($original!==false,'READ_FAILED');
    if(str_contains($original,$marker)) {
        echo "OLD_REDIRECT_ALREADY_PRESENT\n";
        exit(0);
    }
    must(str_contains($original,'marzhavbetone.ru'),'WRONG_OLD_HOST');
    must(!file_exists($backup),'BACKUP_ALREADY_EXISTS');
    must(copy($file,$backup),'BACKUP_FAILED');
    chmod($backup,0600);
    must(hash_file('sha256',$file)===hash_file('sha256',$backup),'BACKUP_HASH_MISMATCH');
    atomic($file,$block.$original);
    $after=file_get_contents($file);
    must($after!==false && str_starts_with($after,$block) && substr_count($after,$marker)===1,'VERIFY_FAILED');
    echo "OLD_DOMAIN_301_CONFIG=VERIFIED\n";
} catch(Throwable $e) {
    fwrite(STDERR,"REDIRECT_CUTOVER_FAILED=".$e->getMessage()."\n");
    exit(1);
}
