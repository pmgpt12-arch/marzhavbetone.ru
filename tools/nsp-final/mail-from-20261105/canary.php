<?php
declare(strict_types=1);
/**
 * One explicit NSP sender delivery control, no payment/checkout/order action.
 * Loaded using the actual PHP 8.3 virtual-host wrapper environment.
 * A private, exclusive marker prevents duplicate messages on reruns.
 */
try {
    if (PHP_SAPI !== 'cli' || $argc !== 3) throw new RuntimeException('ARGS');
    $root = realpath($argv[1]);
    $private = realpath($argv[2]);
    if (!is_string($root) || basename($root) !== 'nastoronepodryadchika.ru'
        || !is_string($private) || basename($private) !== 'nsp-migration-private'
        || is_link($argv[1]) || is_link($argv[2])
        || str_starts_with($private.'/', $root.'/')
        || ($private === $root) || (fileperms($private) & 0077) !== 0) {
        throw new RuntimeException('PRIVATE_ROOT_OR_SITE');
    }
    // Source acceptances from independent read-only production run 42054807473.
    $accepted = [
        'lead.php'=>'44033788dffc232f8694074c6508f5c056834a3c05b0837b1ec0222771a0dcd9',
        'webhook.php'=>'239b4433934b59647315ae8728b582cdc83a34d01a0be7dc85f513c163dc60d5',
        'products-config.php'=>'12abc5750cc7f1d223cbeb002628338e2261e85e4bd4c3d6b8988cd7da295934',
        'config.php'=>'d5ca6b6fa2b8a4660c493e8e3891f6eb4feafc44a54326c3800affd31af6b9db',
    ];
    foreach ($accepted as $name=>$sha) {
        $p=$root.'/'.$name;
        if (!is_file($p) || is_link($p) || hash_file('sha256',$p) !== $sha) {
            throw new RuntimeException('SOURCE_SHA_DRIFT_'.$name);
        }
    }
    $loaded = (string)php_ini_loaded_file()."\n".(string)php_ini_scanned_files();
    if (!str_contains($loaded,'/nastoronepodryadchika.ru/')) {
        throw new RuntimeException('WRONG_PHP_SITE_CONFIGURATION');
    }
    $senderPath = (string)ini_get('sendmail_path');
    if (!preg_match('/(?:^|\s)-f\s*(?:site|info)@nastoronepodryadchika\.ru(?:\s|$)/D',$senderPath)) {
        throw new RuntimeException('NEW_DOMAIN_ENVELOPE_NOT_VERIFIED');
    }
    $marker = $private.'/nsp-sender-canary-20261105-v1.json';
    if (file_exists($marker) || is_link($marker)) {
        echo json_encode(['status'=>'ALREADY_ATTEMPTED_NO_RESEND','messages_sent'=>0],JSON_THROW_ON_ERROR),"\n";
        exit(0);
    }
    $handle = fopen($marker,'x');
    if ($handle === false) throw new RuntimeException('MARKER_ALREADY_CLAIMED');
    if (!chmod($marker,0600)) throw new RuntimeException('MARKER_PRIVATE_MODE');
    $row=[
        'status'=>'ATTEMPT_CLAIMED','message_id'=>'<nsp-sender-canary-20261105-v1@nastoronepodryadchika.ru>',
        'from'=>'site@nastoronepodryadchika.ru','to'=>'pmgpt12@gmail.com',
        'sender_domain'=>'nastoronepodryadchika.ru',
        'accepted_source_sha'=>$accepted,'orders_created'=>0,
        'production_php_files_modified'=>0,'payment_requests'=>0,
        'mail_attempts'=>1,'delivery'=>'NOT_YET_VERIFIED',
    ];
    $write=function(array $v)use($handle):void {
        rewind($handle);ftruncate($handle,0);
        $json=json_encode($v,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);
        if (fwrite($handle,$json) !== strlen($json) || !fflush($handle)) throw new RuntimeException('RECEIPT_WRITE');
    };
    $write($row);
    $headers=[
        'From: '.$row['from'],
        'Reply-To: nastoronepodryadchika@yandex.ru',
        'Message-ID: '.$row['message_id'],
        'Date: '.gmdate('r'),
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
    ];
    $subject='NSP sender canary 20261105 v1';
    $body="Контроль нового адреса отправителя проекта «На стороне подрядчика».\n";
    $ok=mail($row['to'],$subject,$body,implode("\r\n",$headers));
    $row['attempted_utc']=gmdate('c');
    $row['status']=$ok?'ACCEPTED_BY_LOCAL_MAIL_TRANSPORT':'MAIL_TRANSPORT_REJECTED';
    foreach($accepted as $name=>$sha) {
        if(hash_file('sha256',$root.'/'.$name)!==$sha) $row['status']='SOURCE_DRIFT_AFTER_ATTEMPT';
    }
    $write($row);fclose($handle);
    echo json_encode($row,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR),"\n";
    if($row['status']!=='ACCEPTED_BY_LOCAL_MAIL_TRANSPORT')exit(1);
} catch(Throwable $e) {
    fwrite(STDERR,'NSP_MAIL_CANARY_BLOCKED='.$e->getMessage()."\n");
    exit(1);
}
