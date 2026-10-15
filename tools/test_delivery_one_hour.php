<?php
declare(strict_types=1);
require __DIR__ . '/_test_http.php';
$root=dirname(__DIR__);
$tmp=sys_get_temp_dir().'/mvb-ttl-boundary-'.getmypid();
$web=$tmp.'/web';$orders=$tmp.'/orders';$products=$tmp.'/products';
foreach([$web,$orders.'/delivery',$products.'/05-ks-bez-vozvrata'] as $d) mkdir($d,0777,true);
foreach(['download.php','products-config.php'] as $f) copy($root.'/'.$f,$web.'/'.$f);
file_put_contents($products.'/05-ks-bez-vozvrata/01.txt','fixture');
file_put_contents($web.'/config.php',"<?php\ndefine('ORDERS_DIR',".var_export($orders,true).");\ndefine('PRODUCTS_DIR',".var_export($products,true).");\ndefine('ADMIN_EMAIL','qa@example.invalid');\n");
$archive=$orders.'/delivery/05-ks-bez-vozvrata.zip';
$z=new ZipArchive();$z->open($archive,ZipArchive::CREATE);$z->addFromString('01.txt','fixture');$z->close();
$id='order_20261015_230000_aaa111';$token=str_repeat('f',32);
$file=$orders.'/'.$id.'.json';
$order=['id'=>$id,'status'=>'paid','delivery'=>['token'=>$token,'items'=>['p3'=>basename($archive)],'downloads'=>0]];
$port=mvb_free_port();$server=mvb_serve($web,$port);
$url="http://127.0.0.1:$port/download.php?o=$id&t=$token&f=p3";
$failed=0;
foreach([['future',60,200],['boundary',0,410],['expired',-1,410]] as [$label,$shift,$want]){
  $order['delivery']['expires_at']=date('c',time()+$shift);
  file_put_contents($file,json_encode($order));
  $ch=curl_init($url);curl_setopt_array($ch,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>5]);
  $body=curl_exec($ch);$actual=curl_getinfo($ch,CURLINFO_HTTP_CODE);curl_close($ch);
  $state=json_decode(file_get_contents($file),true);
  $count=$state['delivery']['downloads']??-1;
  $pass=$actual===$want && $count===($want===200?1:0) && ($want!==200 || substr($body,0,2)==='PK');
  echo "$label HTTP=$actual downloads=$count ".($pass?'PASS':'FAIL')."\n";if(!$pass)$failed++;
  $order['delivery']['downloads']=0;
}
mvb_kill($server);
foreach(glob($orders.'/delivery/*')?:[] as $p)unlink($p);
@unlink($orders.'/delivery/.htaccess');
foreach(glob($orders.'/*')?:[] as $p)if(is_file($p))unlink($p);
@unlink($orders.'/.htaccess');
foreach(glob($web.'/*')?:[] as $p)unlink($p);
unlink($products.'/05-ks-bez-vozvrata/01.txt');
rmdir($orders.'/delivery');rmdir($orders);rmdir($products.'/05-ks-bez-vozvrata');rmdir($products);rmdir($web);rmdir($tmp);
exit($failed?1:0);
