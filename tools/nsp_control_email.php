<?php
/** One explicitly authorized synthetic mail, with a private no-repeat receipt. */
declare(strict_types=1);
function need(bool $ok,string $why):void{if(!$ok)throw new RuntimeException($why);}
function php_hashes(string $root):array{$out=[];foreach(glob($root.'/*.php') as $p){need(!is_link($p),'PHP_SYMLINK');$out[basename($p)]=hash_file('sha256',$p);}ksort($out);return $out;}
try{
 need($argc===4&&in_array($argv[1],['dry-run','send','inspect'],true),'ARGS');
 $mode=$argv[1];$root=realpath($argv[2]);$private=realpath($argv[3]);
 need(is_string($root)&&basename($root)==='nastoronepodryadchika.ru','SITE_ROOT');
 need(is_string($private)&&!is_link($argv[3])&&strpos($private,$root.'/')!==0&&$private!==$root,'PRIVATE_ROOT');
 need((fileperms($private)&0077)===0,'PRIVATE_PERMISSIONS');
 $before=php_hashes($root);require $root.'/config.php';
 need(SITE_URL==='https://nastoronepodryadchika.ru'&&ADMIN_EMAIL==='nastoronepodryadchika@yandex.ru','RUNTIME_IDENTITY');
 $marker=$private.'/control-email-new-from-20261022-v1.json';
 if(is_file($marker)){
  $saved=json_decode(file_get_contents($marker),true,512,JSON_THROW_ON_ERROR);
  echo json_encode(['status'=>'EXISTING_NO_RESEND','receipt'=>$saved],JSON_UNESCAPED_UNICODE).PHP_EOL;exit;
 }
 need($mode!=='inspect','NO_PRIOR_RECEIPT');need(function_exists('mail'),'MAIL_UNAVAILABLE');
 $receipt=['status'=>'READY','from'=>'site@nastoronepodryadchika.ru','to'=>'nastoronepodryadchika@yandex.ru','reply_to'=>'nastoronepodryadchika@yandex.ru','message_id'=>'<nsp-control-new-from-20261022-v1@nastoronepodryadchika.ru>','subject'=>'НСП: проверка нового адреса отправителя','actual_delivery'=>'NOT_VERIFIED','production_sender'=>'UNCHANGED','orders_created'=>0,'public_writes'=>0];
 if($mode==='dry-run'){echo json_encode($receipt+['mail_attempts'=>0],JSON_UNESCAPED_UNICODE).PHP_EOL;exit;}
 $claim=fopen($marker,'x');need($claim!==false,'ALREADY_CLAIMED_NO_RETRY');chmod($marker,0600);
 $receipt['status']='ATTEMPT_CLAIMED';$receipt['attempted_at_utc']=gmdate('c');$receipt['mail_attempts']=1;
 need(fwrite($claim,json_encode($receipt,JSON_UNESCAPED_UNICODE))!==false,'CLAIM_WRITE');fflush($claim);
 $body="Контрольное письмо проекта «На стороне подрядчика» для проверки доставки с нового адреса отправителя.\nhttps://nastoronepodryadchika.ru/\n";
 $headers=['From: '.$receipt['from'],'Reply-To: '.$receipt['reply_to'],'Message-ID: '.$receipt['message_id'],'Date: '.gmdate('r'),'MIME-Version: 1.0','Content-Type: text/plain; charset=UTF-8'];
 $accepted=@mail($receipt['to'],'=?UTF-8?B?'.base64_encode($receipt['subject']).'?=',$body,implode("\r\n",$headers));
 $receipt['status']=$accepted?'ACCEPTED_BY_LOCAL_MAIL_TRANSPORT':'REJECTED_BY_LOCAL_MAIL_TRANSPORT';
 $receipt['protected_php']=php_hashes($root)===$before?'UNCHANGED':'CHANGED';
 rewind($claim);ftruncate($claim,0);fwrite($claim,json_encode($receipt,JSON_UNESCAPED_UNICODE));fflush($claim);fclose($claim);
 echo json_encode($receipt,JSON_UNESCAPED_UNICODE).PHP_EOL;
 need($receipt['protected_php']==='UNCHANGED','PHP_CHANGED');need($accepted,'MAIL_TRANSPORT_REJECTED_NO_AUTO_RETRY');
}catch(Throwable $e){fwrite(STDERR,$e->getMessage().PHP_EOL);exit(1);}
