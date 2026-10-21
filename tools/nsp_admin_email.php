<?php
/** Change exactly one ADMIN_EMAIL literal, guarded by source and backup hashes. */
declare(strict_types=1);

function nsp_admin_literal(string $text): array {
    $pattern = <<<'REGEX'
~\bdefine\s*\(\s*(['"])ADMIN_EMAIL\1\s*,\s*(['"])([^'"\r\n]+)\2\s*\)\s*;~
REGEX;
    if (preg_match_all($pattern, $text, $m, PREG_OFFSET_CAPTURE) !== 1) {
        throw new RuntimeException('ADMIN_LITERAL_NOT_UNIQUE');
    }
    return [$m[3][0][0], $m[3][0][1]];
}

function nsp_admin_runtime(string $file, string $email): void {
    $code = 'require $argv[1]; echo json_encode([ADMIN_EMAIL,SITE_URL,YOOKASSA_SHOP_ID,DELIVERY_TTL_SECONDS]);';
    $process = proc_open([PHP_BINARY, '-r', $code, $file], [1=>['pipe','w'],2=>['pipe','w']], $pipes);
    if (!is_resource($process)) throw new RuntimeException('RUNTIME_START_FAILED');
    $out=stream_get_contents($pipes[1]); stream_get_contents($pipes[2]);
    fclose($pipes[1]); fclose($pipes[2]); $rc=proc_close($process);
    if ($rc!==0 || json_decode($out,true)!==[$email,'https://nastoronepodryadchika.ru','1502106',3600]) {
        throw new RuntimeException('RUNTIME_INVARIANTS_FAILED');
    }
}

function nsp_admin_stage(string $file, string $bytes, int $mode): string {
    $tmp=tempnam(dirname($file), '.nsp-admin-');
    if ($tmp===false) throw new RuntimeException('STAGE_CREATE_FAILED');
    if (file_put_contents($tmp,$bytes,LOCK_EX)!==strlen($bytes) || !chmod($tmp,$mode)) {
        @unlink($tmp); throw new RuntimeException('STAGE_WRITE_FAILED');
    }
    return $tmp;
}

function nsp_admin_main(array $args): void {
    if (count($args)!==5) throw new RuntimeException('ARGUMENTS');
    [, $action, $file, $expected, $backup]=$args;
    if (!in_array($action,['dry-run','apply'],true) || !preg_match('/^[a-f0-9]{64}$/D',$expected)) throw new RuntimeException('CONTRACT');
    if (!is_file($file) || is_link($file)) throw new RuntimeException('CONFIG_NOT_REGULAR');
    $before=file_get_contents($file); $mode=fileperms($file)&0777;
    if ($before===false || hash('sha256',$before)!==$expected) throw new RuntimeException('SOURCE_DRIFT');
    [$value,$offset]=nsp_admin_literal($before);
    if ($value!=='marzhavbetone@yandex.ru' || substr_count($before,$value)!==1) throw new RuntimeException('UNEXPECTED_ADMIN_EMAIL');
    $new='nastoronepodryadchika@yandex.ru';
    $next=substr_replace($before,$new,$offset,strlen($value));
    [$nextValue,$nextOffset]=nsp_admin_literal($next);
    $normalizedBefore=substr_replace($before,'<ADMIN_EMAIL>',$offset,strlen($value));
    $normalizedAfter=substr_replace($next,'<ADMIN_EMAIL>',$nextOffset,strlen($nextValue));
    if ($normalizedBefore!==$normalizedAfter) throw new RuntimeException('NON_ADMIN_BYTES_CHANGED');
    nsp_admin_runtime($file,$value);
    $receipt=['status'=>'PASS','action'=>$action,'before_sha256'=>$expected,'after_sha256'=>hash('sha256',$next),'non_admin_sha256'=>hash('sha256',$normalizedAfter),'non_admin_bytes'=>'UNCHANGED','shop_id'=>'1502106','ttl'=>3600,'admin_email'=>$new];
    if ($action==='dry-run') { echo json_encode($receipt,JSON_UNESCAPED_SLASHES).PHP_EOL; return; }
    $backupReal=realpath($backup); $siteReal=realpath(dirname($file));
    if ($backupReal===false || is_link($backup) || !is_file($backup) || strpos($backupReal,$siteReal.DIRECTORY_SEPARATOR)===0 || hash_file('sha256',$backup)!==$expected || (fileperms($backup)&0777)!==0600) throw new RuntimeException('PRIVATE_BACKUP_INVALID');
    $tmp=nsp_admin_stage($file,$next,$mode); $installed=false;
    try {
        $lint=proc_open([PHP_BINARY,'-l',$tmp],[1=>['pipe','w'],2=>['pipe','w']],$pipes);
        if (!is_resource($lint)) throw new RuntimeException('LINT_START_FAILED');
        stream_get_contents($pipes[1]); stream_get_contents($pipes[2]); fclose($pipes[1]); fclose($pipes[2]);
        if (proc_close($lint)!==0) throw new RuntimeException('CANDIDATE_LINT_FAILED');
        nsp_admin_runtime($tmp,$new);
        if (hash_file('sha256',$file)!==$expected) throw new RuntimeException('CONCURRENT_CONFIG_EDIT');
        if (!rename($tmp,$file)) throw new RuntimeException('ATOMIC_INSTALL_FAILED');
        $installed=true;
        if (hash_file('sha256',$file)!==$receipt['after_sha256'] || (fileperms($file)&0777)!==$mode) throw new RuntimeException('INSTALL_VERIFY_FAILED');
        nsp_admin_runtime($file,$new);
        $receipt['private_backup']='VERIFIED'; $receipt['file_mode']='UNCHANGED';
        echo json_encode($receipt,JSON_UNESCAPED_SLASHES).PHP_EOL;
    } catch (Throwable $error) {
        if ($installed) {
            if (hash_file('sha256',$file)!==$receipt['after_sha256']) throw new RuntimeException('ROLLBACK_CONFLICT');
            $restore=nsp_admin_stage($file,$before,$mode);
            if (!rename($restore,$file) || hash_file('sha256',$file)!==$expected) throw new RuntimeException('ROLLBACK_FAILED');
        }
        throw $error;
    } finally { if (is_file($tmp)) @unlink($tmp); }
}

try { nsp_admin_main($argv); }
catch (Throwable $error) { fwrite(STDERR,$error->getMessage().PHP_EOL); exit(1); }
