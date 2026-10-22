<?php
/** One explicitly authorized synthetic mail, with a private no-repeat receipt. */
declare(strict_types=1);
function need(bool $ok,string $why):void{if(!$ok)throw new RuntimeException($why);}
function php_hashes(string $root):array{$out=[];foreach(glob($root.'/*.php') as $p){need(!is_link($p),'PHP_SYMLINK');$out[basename($p)]=hash_file('sha256',$p);}ksort($out);return $out;}
try{
 need(($argc===4||($argc===5&&$argv[4]==='site-config-v2'))&&in_array($argv[1],['dry-run','send','inspect','diagnose'],true),'ARGS');
 $version=$argc===5?'v2':'v1';
 $mode=$argv[1];$root=realpath($argv[2]);$private=realpath($argv[3]);
 need(is_string($root)&&basename($root)==='nastoronepodryadchika.ru','SITE_ROOT');
 need(is_string($private)&&!is_link($argv[3])&&strpos($private,$root.'/')!==0&&$private!==$root,'PRIVATE_ROOT');
 need((fileperms($private)&0077)===0,'PRIVATE_PERMISSIONS');
 $before=php_hashes($root);require $root.'/config.php';
 need(SITE_URL==='https://nastoronepodryadchika.ru'&&ADMIN_EMAIL==='nastoronepodryadchika@yandex.ru','RUNTIME_IDENTITY');
 $marker=$private.'/control-email-new-from-20261022-'.$version.'.json';
 if($mode==='diagnose'){echo json_encode(diagnose_mail($root,$private,$before,$version),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES).PHP_EOL;exit;}
 if(is_file($marker)){
  $saved=json_decode(file_get_contents($marker),true,512,JSON_THROW_ON_ERROR);
  echo json_encode(['status'=>'EXISTING_NO_RESEND','receipt'=>$saved],JSON_UNESCAPED_UNICODE).PHP_EOL;exit;
 }
 need($mode!=='inspect','NO_PRIOR_RECEIPT');need(function_exists('mail'),'MAIL_UNAVAILABLE');
 $loaded=(string)php_ini_loaded_file()."\n".(string)php_ini_scanned_files();
 need(strpos($loaded,'/nastoronepodryadchika.ru/')!==false,'SITE_PHP_CONFIG_NOT_LOADED');
 preg_match_all('/(?:^|\s)-f\s*(\S+)/',(string)ini_get('sendmail_path'),$envelope);
 need($envelope[1]===['site@nastoronepodryadchika.ru']&&(string)ini_get('mail.force_extra_parameters')==='','SITE_ENVELOPE_MISMATCH');
 $receipt=['status'=>'READY','from'=>'site@nastoronepodryadchika.ru','to'=>'nastoronepodryadchika@yandex.ru','reply_to'=>'nastoronepodryadchika@yandex.ru','message_id'=>'<nsp-control-new-from-20261022-'.$version.'@nastoronepodryadchika.ru>','subject'=>$version==='v2'?'НСП: проверка отправителя №2':'НСП: проверка нового адреса отправителя','actual_delivery'=>'NOT_VERIFIED','production_sender'=>'UNCHANGED','orders_created'=>0,'public_writes'=>0,'site_php_config_loaded'=>true,'envelope_sender'=>'site@nastoronepodryadchika.ru'];
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

function diagnose_mail(string $root,string $private,array $before,string $version='v1'):array{
 $home=dirname($private);$id='nsp-control-new-from-20261022-'.$version;$to='nastoronepodryadchika@yandex.ru';
 $clean=static function(string $line)use($home,$to):string{
  $line=str_replace($home,'[HOME]',$line);
  $line=preg_replace('/\bU=\S+/','U=[hosting-user]',$line);
  return preg_replace_callback('/[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}/i',static function($m)use($to){return in_array(strtolower($m[0]),[$to,'site@nastoronepodryadchika.ru','site@marzhavbetone.ru'],true)?$m[0]:'[OTHER_EMAIL]';},$line);
 };
 $path=trim((string)ini_get('sendmail_path'));$binary=preg_split('/\s+/',$path)[0]??'';
 $result=['status'=>'READ_ONLY_DIAGNOSTIC','mail_attempts'=>0,'public_writes'=>0,'sendmail_binary'=>$binary,'sendmail_realpath'=>realpath($binary)?:null,'envelope_override_configured'=>(bool)preg_match('/(?:^|\s)-f/',$path),'marker_exists'=>is_file($private.'/control-email-new-from-20261022-'.$version.'.json'),'logs'=>[],'queue'=>[],'dns'=>[]];
 foreach([$home.'/logs/mail.log',$home.'/logs/exim.log','/var/log/mail.log','/var/log/maillog','/var/log/exim4/mainlog','/var/log/exim/mainlog'] as $log){
  $row=['path'=>$clean($log),'readable'=>is_readable($log)];
  if($row['readable']&&is_file($log)){
   $f=fopen($log,'r');$size=filesize($log);if($size>2097152)fseek($f,-2097152,SEEK_END);$raw=stream_get_contents($f,2097152);fclose($f);
   $lines=explode("\n",$raw);$ids=[];$matches=[];
   foreach($lines as $line)if(strpos($line,$id)!==false){$matches[]=$clean($line);if(preg_match('/^\S+\s+\S+\s+([A-Za-z0-9-]{8,})/',$line,$m))$ids[]=$m[1];}
   foreach($lines as $line)foreach($ids as $queueId)if(strpos($line,$queueId)!==false)$matches[]=$clean($line);
   $row['control_matches']=array_slice(array_values(array_unique($matches)),0,30);
  }
  $result['logs'][]=$row;
 }
 if(function_exists('proc_open')&&is_executable('/usr/bin/timeout'))foreach(['/usr/sbin/exim4','/usr/sbin/exim','/usr/lib/sendmail'] as $candidate){
  if(!is_executable($candidate))continue;
  $real=realpath($candidate)?:$candidate;if(stripos($real,'exim')===false)continue;
  $p=proc_open(['/usr/bin/timeout','6s',$candidate,'-bp'],[0=>['pipe','r'],1=>['pipe','w'],2=>['pipe','w']],$pipes);
  if(!is_resource($p))continue;fclose($pipes[0]);$out=stream_get_contents($pipes[1],262144);$error=stream_get_contents($pipes[2],4096);fclose($pipes[1]);fclose($pipes[2]);$exit=proc_close($p);
  $blocks=[];foreach(preg_split('/\n\s*\n/',$out) as $block)if(strpos($block,$to)!==false||strpos($block,$id)!==false)$blocks[]=$clean($block);
  $result['queue']=['binary'=>$candidate,'exit'=>$exit,'matching_blocks'=>array_slice($blocks,0,5),'error'=>$clean(trim($error)),'output_empty'=>trim($out)===''];break;
 }
 foreach(['nastoronepodryadchika.ru','marzhavbetone.ru'] as $domain){
  $mx=[];$txt=[];foreach(@dns_get_record($domain,DNS_MX)?:[] as $r)$mx[]=['priority'=>$r['pri'],'host'=>$r['target']];
  foreach(@dns_get_record($domain,DNS_TXT)?:[] as $r)if(stripos($r['txt']??'','v=spf1')===0)$txt[]=$r['txt'];
  $dmarc=[];foreach(@dns_get_record('_dmarc.'.$domain,DNS_TXT)?:[] as $r)if(stripos($r['txt']??'','v=DMARC1')===0)$dmarc[]=$r['txt'];
  $result['dns'][$domain]=['mx'=>$mx,'spf'=>$txt,'dmarc'=>$dmarc,'default_dkim_txt_present'=>count(@dns_get_record('default._domainkey.'.$domain,DNS_TXT)?:[])>0];
 }
 $result['protected_php']=php_hashes($root)===$before?'UNCHANGED':'CHANGED';return $result;
}
