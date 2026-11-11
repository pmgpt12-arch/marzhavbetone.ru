<?php
declare(strict_types=1);
/**
 * NSP editorial 32 article transaction. Private stage only; no checkout, PHP,
 * orders, masters or public file deletion. Reuses NSP final's hash-CAS,
 * private backup, atomic write and rollback strategy.
 * Usage: php article_transaction.php dry-run|apply|verify|rollback WEBROOT STAGE
 */
function guard(bool $valid, string $reason): void { if (!$valid) throw new RuntimeException($reason); }
function digest(string $p): string {
    guard(is_file($p) && !is_link($p), 'MISSING_OR_LINK:'.$p);
    return (string)hash_file('sha256', $p);
}
function exactPath(string $p): bool {
    return $p === 'article.css' || (bool)preg_match('~^articles/[a-z0-9-]+\.html$~D', $p);
}
function atomicCopy(string $dest, string $bytes): void {
    $tmp = tempnam(dirname($dest), '.nsp-article-');
    guard($tmp !== false, 'TEMP_CREATE');
    try {
        guard(file_put_contents($tmp, $bytes, LOCK_EX) === strlen($bytes), 'TEMP_WRITE');
        chmod($tmp, is_file($dest) ? (fileperms($dest) & 0777) : 0644);
        guard(rename($tmp, $dest), 'ATOMIC_RENAME');
    } finally {
        if (is_file($tmp)) unlink($tmp);
    }
}
function readManifest(string $privateDir): array {
    $m = json_decode((string)file_get_contents($privateDir.'/manifest.json'), true, 512, JSON_THROW_ON_ERROR);
    guard(is_array($m) && ($m['schema'] ?? '') === 'NSP_ARTICLE_ONLY_RELEASE_MANIFEST_v1', 'SCHEMA');
    guard(($m['target_host'] ?? '') === 'nastoronepodryadchika.ru', 'TARGET_HOST');
    guard(($m['release_status'] ?? '') === 'PREFLIGHT_ONLY_NO_PRODUCTION_WRITE', 'NOT_APPROVED_MANIFEST');
    guard(count($m['changed_files'] ?? []) === 32 && count($m['protected_approved_articles'] ?? []) === 11, 'COUNT');
    guard(($m['style_asset']['path'] ?? '') === 'article.css', 'CSS_PATH');
    guard(($m['image_uploads'] ?? 1) === 0, 'IMAGE_SCOPE');
    return $m;
}
function protectedHashes(string $root, array $protected): array {
    $hashes = [];
    foreach ($protected as $row) {
        $path = $row['path'];
        guard($path !== 'article.css' && (bool)preg_match('~^articles/[a-z0-9-]+\.html$~D', $path), 'PROTECTED_PATH');
        guard(!isset($hashes[$path]), 'DUPLICATE_PROTECTED');
        $sha = digest($root.'/'.$path);
        guard(hash_equals($row['sha256'], $sha), 'APPROVED_ARTICLE_CHANGED:'.$path);
        $hashes[$path] = $sha;
    }
    foreach (glob($root.'/*.php') ?: [] as $p) $hashes[basename($p)] = digest($p);
    ksort($hashes);
    return $hashes;
}
function restoreBackups(string $root, string $stage, array $rows, array $written): void {
    foreach ($rows as $row) {
        $path=$row['path'];
        if (!in_array($path, $written, true)) continue;
        $current=digest($root.'/'.$path);
        if (hash_equals($row['before_sha256'], $current)) continue;
        guard(hash_equals($row['after_sha256'], $current), 'ROLLBACK_CONCURRENT_EDIT:'.$path);
        $saved=$stage.'/original/'.$path;
        guard(hash_equals($row['before_sha256'], digest($saved)), 'BACKUP_SHA:'.$path);
        atomicCopy($root.'/'.$path, (string)file_get_contents($saved));
        guard(hash_equals($row['before_sha256'], digest($root.'/'.$path)), 'ROLLBACK_VERIFY:'.$path);
    }
}
$written=[];
try {
    guard($argc===4 && in_array($argv[1], ['dry-run','apply','verify','rollback'], true), 'ARGS');
    [$self, $mode, $rootName, $stageName] = $argv;
    $root=realpath($rootName); $stage=realpath($stageName);
    guard(is_string($root) && is_string($stage), 'DIRECTORY');
    guard(basename($root)==='nastoronepodryadchika.ru', 'WRONG_WEBROOT');
    guard(!str_starts_with($stage.'/', $root.'/') && $stage!==$root, 'STAGE_INSIDE_WEBROOT');
    guard(is_file($stage.'/manifest.json') && !is_link($stage.'/manifest.json'), 'MANIFEST_MISSING');
    $manifest=readManifest($stage); $rows=$manifest['changed_files'];
    $rows[]=$manifest['style_asset']; $seen=[];
    foreach ($rows as $row) {
        $path=$row['path'];
        guard(exactPath($path) && !isset($seen[$path]), 'UNSAFE_OR_DUPLICATE_PATH:'.$path);
        $seen[$path]=true;
        foreach (['before_sha256','after_sha256'] as $key)
            guard(isset($row[$key]) && preg_match('/^[a-f0-9]{64}$/D',$row[$key])===1, 'SHA_FORMAT:'.$path);
        $dest=$root.'/'.$path; $candidate=$stage.'/candidate/'.$path;
        guard(is_dir(dirname($dest)) && !is_link(dirname($dest)), 'PARENT_NOT_DIRECTORY:'.$path);
        guard(str_starts_with((string)realpath(dirname($dest)).'/', $root.'/'), 'PATH_ESCAPE:'.$path);
        guard(is_file($dest) && !is_link($dest), 'LIVE_MISSING_OR_LINK:'.$path);
        if ($mode==='dry-run' || $mode==='apply') {
            guard(hash_equals($row['before_sha256'], digest($dest)), 'LIVE_BEFORE_DRIFT:'.$path);
            guard(hash_equals($row['after_sha256'], digest($candidate)), 'CANDIDATE_SHA_DRIFT:'.$path);
            guard(filesize($candidate)===$row['bytes'], 'CANDIDATE_BYTES:'.$path);
        }
    }
    guard(count($seen)===33, 'SCOPE_NOT_33');
    foreach ($manifest['protected_approved_articles'] as $row)
        guard(!isset($seen[$row['path']]), 'PROTECTED_OVERLAP');
    $protected=protectedHashes($root, $manifest['protected_approved_articles']);
    $receipt=$stage.'/protected.json';
    if ($mode==='verify' || $mode==='rollback') {
        guard(is_file($receipt), 'MISSING_TRANSACTION_RECEIPT');
        $baseline=json_decode((string)file_get_contents($receipt),true,512,JSON_THROW_ON_ERROR);
        guard($protected===$baseline, 'PROTECTED_RUNTIME_CHANGED');
        if ($mode==='rollback') restoreBackups($root,$stage,$rows,array_keys($seen));
        else foreach ($rows as $row)
            guard(hash_equals($row['after_sha256'],digest($root.'/'.$row['path'])), 'LIVE_AFTER_SHA:'.$row['path']);
        guard(protectedHashes($root,$manifest['protected_approved_articles'])===$baseline,'PROTECTED_RUNTIME_CHANGED_AFTER');
        echo json_encode(['status'=>'PASS','mode'=>$mode,'files'=>33,'protected_articles'=>11,'protected_runtime'=>'UNCHANGED'],JSON_THROW_ON_ERROR)."\n";
        exit(0);
    }
    if ($mode==='dry-run') {
        echo json_encode(['status'=>'PASS','mode'=>'dry-run','files'=>33,'protected_articles'=>11,'production_writes'=>0],JSON_THROW_ON_ERROR)."\n";
        exit(0);
    }
    $approval=getenv('NSP_EDITORIAL_APPROVED_MANIFEST_SHA256');
    guard(is_string($approval) && $approval!=='' && hash_equals(digest($stage.'/manifest.json'), $approval), 'OWNER_LEGAL_RELEASE_APPROVAL_REQUIRED');
    guard(!file_exists($stage.'/original') && !file_exists($receipt), 'STAGE_ALREADY_USED');
    guard(mkdir($stage.'/original',0700), 'PRIVATE_BACKUP_DIRECTORY');
    foreach ($rows as $row) {
        $dest=$root.'/'.$row['path']; $save=$stage.'/original/'.$row['path'];
        if (!is_dir(dirname($save))) guard(mkdir(dirname($save),0700,true), 'BACKUP_PARENT');
        guard(copy($dest,$save), 'BACKUP_COPY:'.$row['path']); chmod($save,0600);
        guard(hash_equals($row['before_sha256'],digest($save)), 'BACKUP_HASH:'.$row['path']);
    }
    guard(file_put_contents($receipt,json_encode($protected,JSON_THROW_ON_ERROR))!==false,'RECEIPT_WRITE');
    chmod($receipt,0600);
    foreach ($rows as $row) {
        $path=$row['path']; $dest=$root.'/'.$path;
        guard(hash_equals($row['before_sha256'],digest($dest)), 'LIVE_CONCURRENT_EDIT:'.$path);
        atomicCopy($dest,(string)file_get_contents($stage.'/candidate/'.$path));
        $written[]=$path;
        guard(hash_equals($row['after_sha256'],digest($dest)), 'APPLY_HASH:'.$path);
    }
    guard(protectedHashes($root,$manifest['protected_approved_articles'])===$protected, 'PROTECTED_STATE_CHANGED');
    echo json_encode(['status'=>'PASS','mode'=>'apply','files'=>33,'protected_articles'=>11,'protected_runtime'=>'UNCHANGED'],JSON_THROW_ON_ERROR)."\n";
} catch (Throwable $e) {
    if ($written) {
        try { restoreBackups($root,$stage,$rows ?? [],$written); fwrite(STDERR,"AUTO_ROLLBACK=PASS\n"); }
        catch(Throwable $other) { fwrite(STDERR,"ROLLBACK_FAILED=".$other->getMessage()."\n"); }
    }
    fwrite(STDERR,'NSP_EDITORIAL_TRANSACTION_FAILED='.$e->getMessage()."\n");
    exit(1);
}
