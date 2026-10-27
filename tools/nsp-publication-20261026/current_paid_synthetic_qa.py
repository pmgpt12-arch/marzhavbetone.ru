#!/usr/bin/env python3
"""Existing P3/P5 checkout regression with loopback-only fake processor and temp orders."""
import json, pathlib, shutil, tempfile, urllib.request, urllib.error
from datetime import datetime,timezone
from isolated_delivery_gate import ROOT,php_serve
def post(url,skus):
 body=json.dumps({'email':'synthetic@example.invalid','items':[{'sku':s} for s in skus]}).encode()
 req=urllib.request.Request(url+'/payment.php',data=body,headers={'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=10) as r:return r.status,r.read()
 except urllib.error.HTTPError as e:return e.code,e.read()
def main():
 result={'schema':'NSP_ACTIVE_PAID_CHECKOUT_SYNTHETIC_V1','timestamp_utc':datetime.now(timezone.utc).isoformat(),
  'scope':'TEMP_TEST_WEBROOT_FAKE_YOOKASSA_127_0_0_1_PORT_1_NO_PROVIDER','real_orders_accessed':False,'real_payments':False,
  'cases':[],'release_permission_P3_P5':'PREVIOUS_RELEASE_PRESERVED'}
 with tempfile.TemporaryDirectory(prefix='nsp-current-paid-qa-') as tmp:
  p=pathlib.Path(tmp);web=p/'www';web.mkdir();orders=p/'orders';orders.mkdir()
  for name in ['payment.php','products-config.php']:
   shutil.copyfile(ROOT/name,web/name)
  (p/'products').mkdir()
  config="<?php\n"+"\n".join([
   "define('ORDERS_DIR',"+repr(str(orders))+");",
   "define('PRODUCTS_DIR',"+repr(str(p/'products'))+");",
   "define('SITE_URL','http://127.0.0.1');",
   "define('ADMIN_EMAIL','synthetic@example.invalid');",
   "define('YOOKASSA_SHOP_ID','only-synthetic-qa');",
   "define('YOOKASSA_SECRET_KEY','only-synthetic-qa');",
   "define('YOOKASSA_MODE','test');",
   "define('YOOKASSA_API_URL','http://127.0.0.1:1/disabled');"])+"\n"
  (web/'config.php').write_text(config)
  groups=[('P3_EXISTING',['p3'],500,True),('P5_EXISTING',['p5'],500,True),
    ('P8_HOLD',['p8'],409,False),('P1_HOLD',['p1'],409,False),
    ('P3_PLUS_HOLD',['p3','p8'],409,False),('P5_PLUS_HOLD',['p5','p1'],409,False)]
  with php_serve(web) as base:
   for name,skus,want,new_order in groups:
    before=list(orders.glob('order_*.json'))
    code,raw=post(base,skus)
    after=list(orders.glob('order_*.json'))
    body=json.loads(raw.decode('utf-8'))
    # HTTP 500 for previously released SKUs is EXPECTED because processor is a refused loopback socket.
    # It must be the precise gateway-connection error, not a PHP fatal or HOLD result.
    response_ok = not body.get('ok',False) and (
      ('Ошибка соединения с платёжной системой' in body.get('message','')) if new_order else
      ('готовится к выпуску' in body.get('message','')))
    passed=(code==want and len(after)-len(before)==int(new_order) and response_ok)
    result['cases'].append({'case':name,'skus':skus,'http':code,'expected':want,'synthetic_order_created':len(after)-len(before),'pass':passed,'gateway_call':'REFUSED_LOOPBACK_ONLY' if new_order else 'NOT_ATTEMPTED'})
 assert all(x['pass'] for x in result['cases']),result['cases']
 result['status']='PASS_SYNTHETIC_CURRENT_P3_P5_AND_HOLD_MIXED_CART'
 out=ROOT/'tools/nsp-publication-20261026/NSP_PAID_SYNTHETIC_RECEIPT.json'
 out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':result['status'],'cases':result['cases']},ensure_ascii=False))
if __name__=='__main__':main()
