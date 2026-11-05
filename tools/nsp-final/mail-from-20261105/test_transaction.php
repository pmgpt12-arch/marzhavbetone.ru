<?php
declare(strict_types=1);
define('NSP_MAIL_LIBRARY_ONLY', true);
require __DIR__ . '/transaction.php';
function t_assert(bool $v,string $s): void { if(!$v)throw new RuntimeException('TEST_'.$s); }
function t_delete(string $dir): void {
    if (!is_dir($dir)) return;
    foreach(new FilesystemIterator($dir) as $p) {
        if ($p->isDir() && !$p->isLink()) t_delete($p->getPathname()); else unlink($p->getPathname());
    }
    rmdir($dir);
}
$base = sys_get_temp_dir().'/nsp-mail-qa-'.bin2hex(random_bytes(6));
$root = $base.'/nastoronepodryadchika.ru';
$private = $base.'/nsp-migration-private';
mkdir($base,0700); mkdir($root,0700); mkdir($private,0700);
$stage=$private.'/mail-from-20261105-999999-1';
$baseline=[];
try {
    foreach (NSP_BEFORE as $name=>$sha) {
        $body = in_array($name,NSP_ACTIVE,true)
            ? "<?php\n\$headers = ['".NSP_OLD_FROM."'];\n"
            : "<?php\n// synthetic protected fixture ".$name."\n";
        file_put_contents($root.'/'.$name,$body);
        chmod($root.'/'.$name,0644);
        $baseline[$name]=hash('sha256',$body);
    }
    $dry=nsp_operate('dry-run',$root,$stage,$baseline);
    t_assert($dry['status']==='PASS' && $dry['production_writes']===0,'DRY_RUN');
    t_assert(!is_dir($stage),'DRY_RUN_WROTE_STAGE');

    // A changed protected file invalidates the entire candidate before any write.
    file_put_contents($root.'/payment.php', "<?php\n// foreign edit\n");
    $blocked=false;
    try{ nsp_operate('publish',$root,$stage,$baseline); }
    catch(Throwable $e){ $blocked=str_contains($e->getMessage(),'PREIMAGE_DRIFT_payment.php'); }
    t_assert($blocked && !is_dir($stage),'PROTECTED_DRIFT_FAIL_CLOSED');
    file_put_contents($root.'/payment.php',"<?php\n// synthetic protected fixture payment.php\n");

    // Reject two matching old sender literals instead of mutating both.
    $lead=file_get_contents($root.'/lead.php');
    file_put_contents($root.'/lead.php',$lead.$lead);
    $blocked=false;
    try{nsp_operate('dry-run',$root,$stage,$baseline);}
    catch(Throwable $e){$blocked=str_contains($e->getMessage(),'PREIMAGE_DRIFT_lead.php');}
    t_assert($blocked,'DUPLICATE_SENDER_FAIL_CLOSED');
    file_put_contents($root.'/lead.php',$lead);

    $publish=nsp_operate('publish',$root,$stage,$baseline);
    t_assert($publish['status']==='PASS' && $publish['files']===3,'PUBLISH');
    foreach (NSP_ACTIVE as $name) {
        $data=file_get_contents($root.'/'.$name);
        t_assert(substr_count($data,NSP_NEW_FROM)===1 && substr_count($data,NSP_OLD_FROM)===0,'SENDER_'.$name);
        t_assert(fileperms($root.'/'.$name)&0777 ? (fileperms($root.'/'.$name)&0777)===0644 : false,'MODE_'.$name);
    }
    t_assert(nsp_operate('verify',$root,$stage,$baseline)['status']==='PASS','VERIFY');
    $blocked=false;
    try{nsp_operate('publish',$root,$stage,$baseline);}catch(Throwable $e){$blocked=true;}
    t_assert($blocked,'NO_DOUBLE_PUBLISH');

    $rollback=nsp_operate('rollback',$root,$stage,$baseline);
    t_assert($rollback['status']==='PASS' && $rollback['files']===3,'ROLLBACK');
    foreach ($baseline as $name=>$sha) t_assert(nsp_sha($root.'/'.$name)===$sha,'RESTORED_'.$name);
    $blocked=false;
    try{nsp_operate('rollback',$root,$stage,$baseline);}catch(Throwable $e){$blocked=true;}
    t_assert($blocked,'NO_DOUBLE_ROLLBACK');
    echo json_encode(['status'=>'PASS','cases'=>[
        'read_only_dry_run','protected_drift_rejection','sender_drift_rejection',
        'exact_three_file_publish','permission_preservation','postflight_verify',
        'single_use_stage','exact_rollback','no_duplicate_rollback'
    ],'real_emails_sent'=>0,'real_orders_modified'=>0], JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR),"\n";
} finally {
    t_delete($base);
}
