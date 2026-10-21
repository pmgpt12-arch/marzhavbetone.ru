<?php
/** Narrow recipient/copy migration for two form handlers; sender stays unchanged. */
declare(strict_types=1);
function nsp_form_need(bool $ok,string $why): void { if(!$ok) throw new RuntimeException($why); }
function nsp_form_hash(string $p): string { nsp_form_need(is_file($p)&&!is_link($p),'NOT_REGULAR'); return hash_file('sha256',$p); }
function nsp_form_php(string $root): array { $a=[];foreach(glob($root.'/*.php') as $p)$a[basename($p)]=nsp_form_hash($p);ksort($a);return $a; }
function nsp_form_write(string $p,string $bytes,int $mode): void {
 $tmp=tempnam(dirname($p),'.nsp-form-mail-');nsp_form_need($tmp!==false,'STAGE_CREATE');
 try { nsp_form_need(file_put_contents($tmp,$bytes,LOCK_EX)===strlen($bytes),'STAGE_WRITE');nsp_form_need(chmod($tmp,$mode),'STAGE_MODE');nsp_form_need(rename($tmp,$p),'ATOMIC_INSTALL'); }
 finally { if(is_file($tmp))@unlink($tmp); }
}
function nsp_form_next(string $name,string $source): string {
 $pairs=[["mail('marzhavbetone@yandex.ru',","mail('nastoronepodryadchika@yandex.ru',"]];
 if($name==='contact.php')$pairs=array_merge($pairs,[['Новый заказ с marzhavbetone.ru','Новый заказ с nastoronepodryadchika.ru'],['Reply-To: marzhavbetone@yandex.ru','Reply-To: nastoronepodryadchika@yandex.ru']]);
 foreach($pairs as [$old,$new]){nsp_form_need(substr_count($source,$old)===1,'PATCH_NOT_UNIQUE');$source=str_replace($old,$new,$source);}
 nsp_form_need(substr_count($source,'From: site@marzhavbetone.ru')===1,'SENDER_MUST_BE_PRESERVED');return $source;
}
$applied=[];$plan=[];$root='';$backup='';
try {
 nsp_form_need($argc===4&&in_array($argv[1],['dry-run','apply'],true),'ARGS');$action=$argv[1];$root=realpath($argv[2]);nsp_form_need(is_string($root)&&basename($root)==='nastoronepodryadchika.ru','WRONG_ROOT');
 $before=nsp_form_php($root);$expected=$before;
 $sources=['contact.php'=>'c60e2ce81a490959bf0efe808d404fc5dc4ee668bd038a84dd689072aeb7c8e6','lead.php'=>'11a9f76f4786ce80b350534ab145e0fc8abe69c2d27b875a62b3c75cfb426c32'];
 foreach($sources as $name=>$sha){$p=$root.'/'.$name;nsp_form_need(nsp_form_hash($p)===$sha,'SOURCE_DRIFT_'.$name);$bytes=file_get_contents($p);$next=nsp_form_next($name,$bytes);$plan[$name]=['before'=>$bytes,'after'=>$next,'mode'=>fileperms($p)&0777];$expected[$name]=hash('sha256',$next);}
 if($action==='dry-run'){echo json_encode(['status'=>'PASS','action'=>$action,'files'=>array_keys($plan),'public_writes'=>0,'sender'=>'UNCHANGED']).PHP_EOL;exit;}
 $backup=realpath($argv[3]);nsp_form_need(is_string($backup)&&!is_link($argv[3])&&$backup!==$root&&strpos($backup,$root.'/')!==0,'PRIVATE_BACKUP_REQUIRED');nsp_form_need((fileperms($backup)&0777)===0700,'BACKUP_DIRECTORY_MODE');
 foreach($plan as $name=>$row){$b=$backup.'/'.$name;nsp_form_need(!file_exists($b),'BACKUP_EXISTS');nsp_form_need(file_put_contents($b,$row['before'],LOCK_EX)===strlen($row['before']),'BACKUP_WRITE');chmod($b,0600);nsp_form_need(nsp_form_hash($b)===$sources[$name],'BACKUP_HASH');$candidate=$backup.'/next-'.$name;file_put_contents($candidate,$row['after']);chmod($candidate,0600);$proc=proc_open([PHP_BINARY,'-l',$candidate],[1=>['pipe','w'],2=>['pipe','w']],$pipes);nsp_form_need(is_resource($proc),'LINT_START');stream_get_contents($pipes[1]);stream_get_contents($pipes[2]);fclose($pipes[1]);fclose($pipes[2]);nsp_form_need(proc_close($proc)===0,'LINT_FAILED');}
 nsp_form_need(nsp_form_php($root)===$before,'PHP_CHANGED_BEFORE_APPLY');
 foreach($plan as $name=>$row){$p=$root.'/'.$name;nsp_form_need(nsp_form_hash($p)===$sources[$name],'CONCURRENT_EDIT');nsp_form_write($p,$row['after'],$row['mode']);$applied[]=$name;nsp_form_need(nsp_form_hash($p)===$expected[$name]&&(fileperms($p)&0777)===$row['mode'],'INSTALL_VERIFY');}
 nsp_form_need(nsp_form_php($root)===$expected,'UNRELATED_PHP_CHANGED');
 echo json_encode(['status'=>'PASS','action'=>$action,'files'=>array_intersect_key($expected,$plan),'all_other_php'=>'UNCHANGED','sender'=>'UNCHANGED','private_backups'=>'VERIFIED','permissions'=>'UNCHANGED']).PHP_EOL;
}catch(Throwable $error){
 foreach(array_reverse($applied) as $name){$row=$plan[$name];$p=$root.'/'.$name;if(nsp_form_hash($p)!==hash('sha256',$row['after'])){fwrite(STDERR,'ROLLBACK_CONFLICT_'.$name.PHP_EOL);exit(2);}nsp_form_write($p,$row['before'],$row['mode']);}
 fwrite(STDERR,$error->getMessage().PHP_EOL);exit(1);
}
