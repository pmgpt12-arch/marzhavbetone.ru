<?php
declare(strict_types=1);
/**
 * NSP mail sender: one-shot exact-SHA transaction for three production files.
 * No config includes, orders, payments, network, mail(), or product writes.
 * Use only via the existing nsp-cutover-final deploy-locked workflow.
 */
const NSP_OLD_FROM = 'From: site@marzhavbetone.ru';
const NSP_NEW_FROM = 'From: site@nastoronepodryadchika.ru';
const NSP_ACTIVE = ['lead.php', 'webhook.php', 'products-config.php'];
const NSP_BEFORE = [
    'lead.php' => '9a37f0cd34efddddcbbc16ede01789ceea54fcefbd50395995c1e7115b046c8e',
    'webhook.php' => 'c8d758c1234e47466b212dbe91ddd3466aa24b64f6d50ecd669a16bc6655cb2d',
    'products-config.php' => 'a5fff1609fc75ec5738b5ea1ebe4a6bed8900e774652e4ed6ebcc0e23282423c',
    'config.php' => 'd5ca6b6fa2b8a4660c493e8e3891f6eb4feafc44a54326c3800affd31af6b9db',
    'payment.php' => '4a1d765280b08f1babe4aaa94502729c111989670e024e0c1273ff8dbc1a55cf',
    'check-payment.php' => 'd19d4961857eb90ae68753db0c8ca7be3e465cc267a184eb15c4c916df8caea5',
    'download.php' => '8c90c5abf5900d1ab7e14d663a584e304fcf9ef8e37a953a4ac5b231e1b6ec55',
    'contact.php' => '607998cf64f596c361788f9830c78a1f783e07576d2e5a62752325ea21e78d2e',
];
function nsp_need(bool $ok, string $error): void { if (!$ok) throw new RuntimeException($error); }
function nsp_sha(string $path): string {
    nsp_need(is_file($path) && !is_link($path), 'INVALID_FILE');
    $sha = hash_file('sha256', $path);
    nsp_need(is_string($sha) && strlen($sha) === 64, 'SHA_FAILED');
    return $sha;
}
function nsp_root(string $root): string {
    $real = realpath($root);
    nsp_need(is_string($real) && basename($real) === 'nastoronepodryadchika.ru'
        && !is_link($root), 'WRONG_SITE_ROOT');
    return $real;
}
function nsp_stage(string $root, string $stage): string {
    nsp_need((bool)preg_match('/^mail-from-20261105-[0-9]+-[0-9]+$/D', basename($stage)), 'STAGE_NAME');
    $parent = realpath(dirname($stage));
    nsp_need(is_string($parent) && basename($parent) === 'nsp-migration-private'
        && !is_link($parent) && ($parent !== $root)
        && !str_starts_with($parent.'/', $root.'/')
        && (fileperms($parent) & 0077) === 0, 'PRIVATE_STAGE_PARENT');
    return $parent . '/' . basename($stage);
}
function nsp_expected_state(string $root, array $baseline): array {
    nsp_need(count($baseline) === 8 && count(array_diff(NSP_ACTIVE, array_keys($baseline))) === 0, 'BASELINE_SCOPE');
    $rows = [];
    foreach ($baseline as $name => $want) {
        nsp_need((bool)preg_match('/^[a-z-]+\.php$/D', $name), 'BASELINE_FILENAME');
        $p = $root . '/' . $name;
        nsp_need(nsp_sha($p) === $want, 'PREIMAGE_DRIFT_' . $name);
        if (in_array($name, NSP_ACTIVE, true)) {
            $text = file_get_contents($p);
            nsp_need(is_string($text) && substr_count($text, NSP_OLD_FROM) === 1
                && substr_count($text, NSP_NEW_FROM) === 0, 'SENDER_LITERAL_DRIFT_' . $name);
            $replacement = str_replace(NSP_OLD_FROM, NSP_NEW_FROM, $text);
            $rows[$name] = [
                'before' => $want,
                'after' => hash('sha256', $replacement),
                'mode' => fileperms($p) & 0777,
                'uid' => fileowner($p),
                'gid' => filegroup($p),
            ];
        }
    }
    nsp_need(count($rows) === 3, 'TARGET_SCOPE');
    return $rows;
}
function nsp_verify_state(string $root, array $baseline, array $rows, bool $after): void {
    foreach ($baseline as $name => $sha) {
        $want = $after && isset($rows[$name]) ? $rows[$name]['after'] : $sha;
        nsp_need(nsp_sha($root . '/' . $name) === $want, 'STATE_DRIFT_' . $name);
    }
}
function nsp_write_atomic(string $path, string $bytes, array $meta, string $expected): void {
    nsp_need(function_exists('posix_geteuid')
        && posix_geteuid() === $meta['uid'], 'OWNER_NOT_VERIFIED');
    nsp_need(is_file($path) && !is_link($path) && fileowner($path) === $meta['uid']
        && filegroup($path) === $meta['gid'], 'FILE_OWNERSHIP_DRIFT');
    $tmp = tempnam(dirname($path), '.nsp-mail-');
    nsp_need(is_string($tmp), 'TEMP_CREATE');
    try {
        nsp_need(file_put_contents($tmp, $bytes, LOCK_EX) === strlen($bytes), 'TEMP_WRITE');
        nsp_need(chmod($tmp, $meta['mode']), 'TEMP_MODE');
        if (filegroup($tmp) !== $meta['gid']) {
            nsp_need(chgrp($tmp, $meta['gid']), 'TEMP_GROUP');
        }
        nsp_need(fileowner($tmp) === $meta['uid'] && filegroup($tmp) === $meta['gid']
            && nsp_sha($tmp) === $expected, 'TEMP_VERIFY');
        nsp_need(rename($tmp, $path), 'ATOMIC_RENAME');
        nsp_need(nsp_sha($path) === $expected && (fileperms($path) & 0777) === $meta['mode']
            && fileowner($path) === $meta['uid'] && filegroup($path) === $meta['gid'], 'POSTWRITE_VERIFY');
    } finally { if (is_file($tmp)) unlink($tmp); }
}
function nsp_store_json(string $path, array $v): void {
    $text = json_encode($v, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR) . "\n";
    nsp_need(file_put_contents($path, $text, LOCK_EX) === strlen($text), 'RECEIPT_WRITE');
    nsp_need(chmod($path, 0600), 'RECEIPT_MODE');
}
function nsp_restore(string $root, string $stage, array $rows, array $names): void {
    foreach (array_reverse($names) as $name) {
        $p = $root . '/' . $name;
        $current = nsp_sha($p);
        if ($current === $rows[$name]['before']) continue;
        nsp_need($current === $rows[$name]['after'], 'ROLLBACK_FOREIGN_EDIT_' . $name);
        $backup = $stage . '/original/' . $name;
        nsp_need(nsp_sha($backup) === $rows[$name]['before'], 'ROLLBACK_BACKUP_HASH_' . $name);
        $bytes = file_get_contents($backup);
        nsp_need(is_string($bytes), 'ROLLBACK_BACKUP_READ');
        nsp_write_atomic($p, $bytes, $rows[$name], $rows[$name]['before']);
    }
}
function nsp_operate(string $action, string $rootArg, string $stageArg, array $baseline): array {
    nsp_need(in_array($action, ['dry-run','publish','verify','rollback'], true), 'UNSUPPORTED_ACTION');
    $root = nsp_root($rootArg);
    $stage = nsp_stage($root, $stageArg);
    if ($action === 'dry-run' || $action === 'publish') {
        nsp_need(!file_exists($stage) && !is_link($stage), 'SINGLE_USE_STAGE_EXISTS');
        $rows = nsp_expected_state($root, $baseline);
        if ($action === 'dry-run') {
            return ['status'=>'PASS','mode'=>'dry-run','target_files'=>array_keys($rows),
                'before_after_sha256'=>$rows,'protected_files_unchanged'=>5,
                'production_writes'=>0,'emails_sent'=>0,'orders_modified'=>0];
        }
        foreach ($rows as $name => $meta) {
            nsp_need(function_exists('posix_geteuid')
                && posix_geteuid() === $meta['uid'], 'CANNOT_PRESERVE_OWNER_' . $name);
        }
        nsp_need(mkdir($stage, 0700) && mkdir($stage.'/original', 0700), 'STAGE_CREATE');
        nsp_store_json($stage.'/manifest.json', ['status'=>'PREPARED','baseline'=>$baseline,'targets'=>$rows]);
        foreach (NSP_ACTIVE as $name) {
            $p=$root.'/'.$name;
            $bytes=file_get_contents($p);
            nsp_need(is_string($bytes) && hash('sha256',$bytes)===$rows[$name]['before'],
                'BACKUP_SOURCE_DRIFT_'.$name);
            nsp_need(file_put_contents($stage.'/original/'.$name, $bytes, LOCK_EX)===strlen($bytes),
                'BACKUP_WRITE_'.$name);
            nsp_need(chmod($stage.'/original/'.$name,0600)
                && nsp_sha($stage.'/original/'.$name)===$rows[$name]['before'], 'BACKUP_VERIFY_'.$name);
        }
        $changed=[];
        try {
            foreach (NSP_ACTIVE as $name) {
                $p=$root.'/'.$name;
                nsp_need(nsp_sha($p)===$rows[$name]['before'], 'CONCURRENT_EDIT_'.$name);
                $bytes=file_get_contents($stage.'/original/'.$name);
                nsp_need(is_string($bytes), 'CANNOT_READ_BACKUP');
                $next=str_replace(NSP_OLD_FROM,NSP_NEW_FROM,$bytes);
                nsp_need(hash('sha256',$next)===$rows[$name]['after'], 'CANDIDATE_MISMATCH');
                // Include the current path even if the post-rename validation fails.
                $changed[]=$name;
                nsp_write_atomic($p,$next,$rows[$name],$rows[$name]['after']);
            }
            nsp_verify_state($root,$baseline,$rows,true);
            nsp_store_json($stage.'/result.json',['status'=>'APPLIED_VERIFIED','targets'=>$rows]);
            return ['status'=>'PASS','mode'=>'publish','files'=>count($changed),
                'protected_files_unchanged'=>5,'backup'=>'PRIVATE_ONLY','real_emails_sent'=>0];
        } catch(Throwable $e) {
            try {
                nsp_restore($root,$stage,$rows,$changed);
                nsp_verify_state($root,$baseline,$rows,false);
                nsp_store_json($stage.'/result.json',['status'=>'FAILED_ROLLED_BACK','reason'=>$e->getMessage()]);
            } catch(Throwable $rollback) {
                nsp_store_json($stage.'/result.json',['status'=>'FAIL_ROLLBACK_REQUIRED',
                    'reason'=>$e->getMessage(),'rollback_error'=>$rollback->getMessage()]);
            }
            throw $e;
        }
    }
    nsp_need(is_file($stage.'/manifest.json') && !is_link($stage.'/manifest.json'), 'NO_STAGE_MANIFEST');
    $manifest=json_decode((string)file_get_contents($stage.'/manifest.json'),true,512,JSON_THROW_ON_ERROR);
    nsp_need($manifest['baseline'] === $baseline && array_keys($manifest['targets']) === NSP_ACTIVE, 'MANIFEST_DRIFT');
    $rows=$manifest['targets'];
    if ($action === 'verify') {
        nsp_verify_state($root,$baseline,$rows,true);
        return ['status'=>'PASS','mode'=>'verify','files'=>count($rows),
            'protected_files_unchanged'=>5,'real_emails_sent'=>0];
    }
    nsp_need(is_file($stage.'/result.json'), 'NO_APPLY_RECEIPT');
    $receipt=json_decode((string)file_get_contents($stage.'/result.json'),true,512,JSON_THROW_ON_ERROR);
    nsp_need($receipt['status']==='APPLIED_VERIFIED', 'NOT_APPLIED');
    nsp_restore($root,$stage,$rows,NSP_ACTIVE);
    nsp_verify_state($root,$baseline,$rows,false);
    nsp_store_json($stage.'/result.json',['status'=>'ROLLBACK_VERIFIED','source'=>'manual_safe_rollback']);
    return ['status'=>'PASS','mode'=>'rollback','files'=>count($rows),'protected_files_unchanged'=>5];
}
if (!defined('NSP_MAIL_LIBRARY_ONLY')) {
    try {
        nsp_need(PHP_SAPI==='cli' && $argc===4, 'CLI_ARGS');
        $receipt=nsp_operate($argv[1],$argv[2],$argv[3],NSP_BEFORE);
        echo json_encode($receipt,JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR),"\n";
    } catch(Throwable $e) {
        fwrite(STDERR,"NSP_SENDER_TRANSACTION_BLOCKED=".$e->getMessage()."\n");
        exit(1);
    }
}
