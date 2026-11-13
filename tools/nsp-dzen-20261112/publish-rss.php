<?php
$root=getenv('HOME').'/www/nastoronepodryadchika.ru';
$path=$root.'/rss.xml';
$old='62f921f7d72fba7596a430e25a51d639d9fc29fdf50b22496de6a09207416dc9';
$new='29d60ab71d520539164105a2182b8b704e27833b10dfa44b668ccecc5f2e512a';
$body=base64_decode('__RSS_BASE64__',true);
if ($body===false || hash('sha256',$body)!==$new) throw new Exception('PAYLOAD_HASH_FAILED');
if (is_link($path) || !is_file($path)) throw new Exception('TARGET_UNSAFE');
$backupdir=getenv('HOME').'/nsp-rss-backups';
if (!is_dir($backupdir) && !mkdir($backupdir,0700)) throw new Exception('BACKUP_DIRECTORY_FAILED');
$backup=$backupdir.'/'.$old.'.xml';
$index=hash_file('sha256',$root.'/index.html');
$rollback=getenv('NSP_ROLLBACK')==='1';
$current=hash_file('sha256',$path);
if ($rollback) {
 if ($current!==$new || !is_file($backup) || hash_file('sha256',$backup)!==$old) throw new Exception('ROLLBACK_CONCURRENT_DRIFT');
 $body=file_get_contents($backup);$expected=$old;
} else {
 if ($current!==$old) throw new Exception('FEED_CONCURRENT_DRIFT');
 if (!file_exists($backup)) {
  $h=fopen($backup,'x');if (!$h) throw new Exception('BACKUP_CREATE_FAILED');
  try { if (fwrite($h,file_get_contents($path))!==filesize($path)) throw new Exception('BACKUP_WRITE_FAILED'); } finally { fclose($h); }
  chmod($backup,0600);
 }
 if (hash_file('sha256',$backup)!==$old) throw new Exception('BACKUP_HASH_FAILED');
 $expected=$new;
}
$tmp=tempnam($root,'.rss-release-');
try {
 if (file_put_contents($tmp,$body)!==strlen($body)) throw new Exception('WRITE_FAILED');
 chmod($tmp,0644);
 if (hash_file('sha256',$path)!==$current) throw new Exception('CONCURRENT_DRIFT_BEFORE_RENAME');
 if (!rename($tmp,$path)) throw new Exception('ATOMIC_RENAME_FAILED');
} finally { if (is_file($tmp)) unlink($tmp); }
if (hash_file('sha256',$path)!==$expected) throw new Exception('RESULT_HASH_FAILED');
if (hash_file('sha256',$root.'/index.html')!==$index) throw new Exception('INDEX_CHANGED');
echo json_encode(['action'=>$rollback?'rolled_back':'published','rss_sha256'=>$expected,'backup_verified'=>true,'index_unchanged'=>true])."\n";
