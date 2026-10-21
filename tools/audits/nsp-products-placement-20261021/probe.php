<?php
$expected=EXPECTED_JSON;
$run='AUDIT_RUN_ID';if(!ctype_digit($run))throw new RuntimeException('run id');
$phase=$argv[1]??'';$root=rtrim(getenv('HOME'),'/').'/www/nastoronepodryadchika.ru';
require $root.'/config.php';require $root.'/products-config.php';
$prefix='order_20261021_'.$run.'_nspprobe';$out=[];
if($phase==='create'){
foreach($expected as $sku=>$want){
$id=$prefix.$sku;$f=ORDERS_DIR.'/'.$id.'.json';if(file_exists($f))throw new RuntimeException('probe already exists');
$position=['sku'=>$sku];if($sku==='p1'){$position['edition']=mvb_capture_p1_edition();if(!$position['edition'])throw new RuntimeException('P1 edition');}
$o=['id'=>$id,'status'=>'paid','email'=>'','items'=>[$position],'total'=>$want['price'],'audit_only'=>true];$delivery=mvb_prepare_delivery($o);
if(count($delivery['links'])!==1||$delivery['links'][0]['sku']!==$sku)throw new RuntimeException('delivery '.$sku);
$ttl=strtotime($o['delivery']['expires_at'])-time();if($ttl<3597||$ttl>3600)throw new RuntimeException('TTL '.$sku);
$url=$delivery['links'][0]['url'];if(parse_url($url,PHP_URL_HOST)!=='nastoronepodryadchika.ru')throw new RuntimeException('wrong URL host');
$mail=mvb_delivery_email($o,$delivery['links']);if(strpos($mail,'1 час')===false)throw new RuntimeException('email TTL');
if(file_put_contents($f,json_encode($o))===false)throw new RuntimeException('probe save');chmod($f,0600);
$out[]=['sku'=>$sku,'url'=>$url,'ttl_seconds'=>$ttl,'email_render'=>'PASS_NO_SEND'];
}
}elseif($phase==='expire'||$phase==='cleanup'){
foreach($expected as $sku=>$want){$f=ORDERS_DIR.'/'.$prefix.$sku.'.json';
if(!is_file($f))continue;$o=json_decode(file_get_contents($f),true,512,JSON_THROW_ON_ERROR);
if(empty($o['audit_only'])||$o['id']!==$prefix.$sku)throw new RuntimeException('scope guard');
if($phase==='expire'){$o['delivery']['expires_at']=date('c',time()-1);file_put_contents($f,json_encode($o));}
else{unlink($f);if(is_file($f.'.lock'))unlink($f.'.lock');}
$out[]=$sku;}
}else throw new RuntimeException('phase');
echo json_encode($out,JSON_UNESCAPED_SLASHES),"\n";
