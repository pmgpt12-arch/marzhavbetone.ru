<?php
/** Read-only YooKassa webhook inventory. Runs over existing authorized SSH.
 * No payment creation, secret output, provider mutation or live file writes. */
declare(strict_types=1);
ini_set('display_errors','0');error_reporting(E_ALL);set_time_limit(35);
function gate(bool $ok,string $code):void{if(!$ok)throw new RuntimeException($code);}
try{
    gate(PHP_SAPI==='cli','CLI_ONLY');
    $p=json_decode(base64_decode('__PAYLOAD__',true),true,512,JSON_THROW_ON_ERROR);
    $home=realpath((string)getenv('HOME'));
    $old=realpath($p['old_site']);
    gate(is_string($home)&&$old===$p['old_site']&&str_starts_with($old,$home.'/www/'),'OLD_ROOT_INVALID');
    gate(is_file($old.'/config.php')&&!is_link($old.'/config.php'),'LIVE_CONFIG_MISSING');
    gate(hash_file('sha256',$old.'/config.php')===$p['old_config_sha256'],'LIVE_CONFIG_DRIFT');
    ob_start();require $old.'/config.php';ob_end_clean();
    gate(defined('YOOKASSA_SHOP_ID')&&defined('YOOKASSA_SECRET_KEY')&&defined('YOOKASSA_API_URL'),'PROVIDER_CONFIG_MISSING');
    gate(YOOKASSA_SHOP_ID!==''&&YOOKASSA_SECRET_KEY!==''&&str_starts_with(YOOKASSA_API_URL,'https://'),'PROVIDER_CONFIG_INVALID');
    $ch=curl_init(rtrim(YOOKASSA_API_URL,'/').'/webhooks');
    gate($ch!==false,'CURL_INIT');
    curl_setopt_array($ch,[
        CURLOPT_RETURNTRANSFER=>true,CURLOPT_CONNECTTIMEOUT=>8,CURLOPT_TIMEOUT=>20,
        CURLOPT_HTTPAUTH=>CURLAUTH_BASIC,
        CURLOPT_USERPWD=>YOOKASSA_SHOP_ID.':'.YOOKASSA_SECRET_KEY,
        CURLOPT_HTTPHEADER=>['Accept: application/json'],
        CURLOPT_FOLLOWLOCATION=>false,
    ]);
    $body=curl_exec($ch);$status=(int)curl_getinfo($ch,CURLINFO_HTTP_CODE);
    $err=curl_errno($ch);curl_close($ch);
    gate($body!==false&&$err===0,'PROVIDER_TRANSPORT_ERROR');
    $out=['status'=>'READ_ONLY_PROVIDER_WEBHOOK_AUDIT','http_status'=>$status,
        'provider_request'=>'GET /v3/webhooks','mutation'=>false,
        'payment_created'=>false,'credentials_logged'=>false];
    if($status===200){
        $json=json_decode($body,true,512,JSON_THROW_ON_ERROR);
        gate(is_array($json),'WEBHOOK_RESPONSE_INVALID');
        $items=$json['items']??[];
        gate(is_array($items),'WEBHOOK_ITEMS_INVALID');
        $out['webhooks']=[];
        foreach($items as $item){
            $url=(string)($item['url']??'');
            $u=parse_url($url);
            $out['webhooks'][]=['event'=>(string)($item['event']??''),
                'scheme'=>$u['scheme']??'','host'=>$u['host']??'','path'=>$u['path']??'',
                'enabled'=>isset($item['status'])?$item['status']:null];
        }
        $out['webhook_count']=count($out['webhooks']);
        $out['status']='PASS_PROVIDER_WEBHOOK_INVENTORY';
    }else{
        // Do not echo provider error body: it may contain request identifiers.
        $out['status']='PROVIDER_WEBHOOK_INVENTORY_BLOCKED';
        $out['classification']=in_array($status,[401,403],true)?'PROVIDER_PERMISSION_OR_AUTH':'PROVIDER_HTTP_ERROR';
    }
    echo json_encode($out,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);
}catch(Throwable $e){
    while(ob_get_level()>0)ob_end_clean();
    $m=$e instanceof RuntimeException?$e->getMessage():'SANITIZED_PROVIDER_AUDIT_ERROR';
    if(!preg_match('/^[A-Z0-9_]+$/D',$m))$m='SANITIZED_PROVIDER_AUDIT_ERROR';
    fwrite(STDERR,$m."\n");exit(2);
}
