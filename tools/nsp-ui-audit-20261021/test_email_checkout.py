#!/usr/bin/env python3
"""Isolated email-only checkout against a loopback fake provider. No delivery or emails."""
import json, shutil, socket, subprocess, tempfile, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='nsp-email-checkout-') as td:
    base=Path(td); web=base/'web'; orders=base/'orders'; masters=base/'masters'
    for p in [web,orders,masters]:p.mkdir()
    for name in ['payment.php','products-config.php']:shutil.copy2(ROOT/name,web/name)
    calls=[]
    class Mock(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            assert self.path=='/payments'
            data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            order=json.loads((orders/(data['metadata']['order_id']+'.json')).read_text())
            assert order['email']=='qa@example.invalid' and order['phone']==''
            expected=sum({'p7':2490000,'p2':2490000}[item['sku']] for item in order['items'])
            assert order['total']==expected
            assert data['amount']=={'value':format(expected/100,'.2f'),'currency':'RUB'}
            calls.append({'sku':[i['sku'] for i in order['items']],'total':expected,'email_only':True})
            body=json.dumps({'id':'mock_'+str(len(calls)),'status':'pending','confirmation':{'confirmation_url':'https://example.invalid/mock'}}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    api=ThreadingHTTPServer(('127.0.0.1',0),Mock);threading.Thread(target=api.serve_forever,daemon=True).start()
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    cfg={'ORDERS_DIR':str(orders),'PRODUCTS_DIR':str(masters),'SITE_URL':'http://127.0.0.1:'+str(port),'ADMIN_EMAIL':'nobody@example.invalid','YOOKASSA_SHOP_ID':'mock','YOOKASSA_SECRET_KEY':'mock','YOOKASSA_MODE':'test','YOOKASSA_API_URL':'http://127.0.0.1:'+str(api.server_port)}
    (web/'config.php').write_text('<?php\n'+'\n'.join('define(%s,%s);'%(json.dumps(k),json.dumps(v)) for k,v in cfg.items()))
    with (base/'php.log').open('wb') as log:
        proc=subprocess.Popen(['php','-d','sendmail_path=/bin/false','-S','127.0.0.1:'+str(port),'-t',str(web)],stdout=log,stderr=log)
        try:
            for attempt in range(50):
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=.1):break
                except OSError:time.sleep(.05)
            for skus in [['p7'],['p7','p2']]:
                # False client prices verify the server still chooses the accepted prices.
                payload={'items':[{'sku':sku,'price':1,'name':'client'} for sku in skus],'email':'qa@example.invalid','phone':''}
                req=urllib.request.Request('http://127.0.0.1:'+str(port)+'/payment.php',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=5) as res:
                    result=json.loads(res.read());assert res.status==200 and result['ok'] and result['payment_url']=='https://example.invalid/mock',result
            assert len(calls)==2
            print(json.dumps({'status':'PASS','cases':calls,'real_payments':0,'emails_sent':0,'production_writes':0}))
        finally:proc.terminate();proc.wait(timeout=5);api.shutdown()
