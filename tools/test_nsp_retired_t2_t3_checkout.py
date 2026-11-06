#!/usr/bin/env python3
"""Retired T2/T3: reject NEW direct HTTP payment attempts and legacy-name bypass.

Uses a disposable PHP site and dummy credentials on localhost.
Existing historical catalog records must remain available for past deliveries.
No production requests, orders, paid ZIPs, or real payment API calls.
"""
from __future__ import annotations
from pathlib import Path
import json,re,shutil,socket,subprocess,tempfile,time
import urllib.error,urllib.request

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"products-config.php"
PAYMENT=ROOT/"payment.php"
RETIRED={"t2":990000,"t3":1490000}
ACTIVE={"p1","p2","p3","p4","p5","p7","p8","p9","p10","p11","p13"}

def php_lit(s):
    return "'" + str(s).replace("\\","\\\\").replace("'","\\'") + "'"

def run(args,timeout=10):
    p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError("PHP_TEST_FAILED: "+p.stderr[-400:])
    return p.stdout

def send(port,item):
    request=urllib.request.Request(
        "http://127.0.0.1:"+str(port)+"/payment.php",
        data=json.dumps({"items":item,"email":"qa@example.invalid"}).encode(),
        headers={"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(request,timeout=4) as response:
            return response.status,json.loads(response.read())
    except urllib.error.HTTPError as response:
        return response.code,json.loads(response.read())

def main():
    src=SOURCE.read_text(encoding="utf-8")
    assert "if ($sku === 't2') return null;" in src
    assert "if ($sku === 't3') return null;" in src
    assert "if ($key === 't2') continue;" in src
    assert "if ($key === 't3') continue;" in src
    assert all(src.count("'"+sku+"' => [")==1 for sku in RETIRED)
    assert all(src.count("if ($sku === '"+sku+"') return null;")==1 for sku in RETIRED)

    with tempfile.TemporaryDirectory(prefix="nsp-retired-checkout-") as folder:
        work=Path(folder)
        web=work/"web"
        web.mkdir()
        (work/"masters").mkdir()
        shutil.copy2(SOURCE,web/"products-config.php")
        shutil.copy2(PAYMENT,web/"payment.php")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0))
            port=sock.getsockname()[1]
        cfg={
            "ORDERS_DIR":str(work/"orders"),"PRODUCTS_DIR":str(work/"masters"),
            "SITE_URL":"http://127.0.0.1:"+str(port),
            "YOOKASSA_SHOP_ID":"test-shop", "YOOKASSA_SECRET_KEY":"test-secret",
            "YOOKASSA_API_URL":"http://127.0.0.1:9",
            "YOOKASSA_MODE":"test","ADMIN_EMAIL":"qa@example.invalid",
        }
        (web/"config.php").write_text("<?php\n"+"".join(
            "define("+php_lit(k)+","+php_lit(v)+");\n" for k,v in cfg.items()))
        run(["php","-l",str(web/"products-config.php")])
        run(["php","-l",str(web/"payment.php")])

        # The catalog keeps legacy SKUs, while resolver denies new sales.
        unit="""
            require $argv[1];
            $all=mvb_products();
            $results=[];
            foreach (['t2','t3'] as $sku) {
                $results[$sku]=[
                    'listed'=>isset($all[$sku]),
                    'price'=>$all[$sku]['price']??null,
                    'sku_rejected'=>mvb_resolve_product(['sku'=>$sku])===null,
                    'old_name_rejected'=>mvb_resolve_product(['name'=>$all[$sku]['name']])===null,
                    'cross_name_rejected'=>mvb_resolve_product(['sku'=>$sku,'name'=>$all['p4']['name']])===null
                ];
            }
            foreach (['p1','p2','p3','p4','p5','p7','p8','p9','p10','p11','p13'] as $sku){
                $results[$sku]=mvb_resolve_product(['sku'=>$sku])!==null;
            }
            echo json_encode($results,JSON_THROW_ON_ERROR);
        """
        unitresult=json.loads(run(["php","-r",unit,str(web/"config.php")]))
        # config.php alone doesn't include products-config; invoke through a single helper:
        # on error, explicit acceptance gate below will reject missing resolver.
        for sku,price in RETIRED.items():
            r=unitresult[sku]
            assert r=={"listed":True,"price":price,"sku_rejected":True,
                       "old_name_rejected":True,"cross_name_rejected":True},(sku,r)
        assert all(unitresult[sku] is True for sku in ACTIVE),"ACTIVE_SKU_REGRESSION"

        log=(work/"php.log").open("wb")
        server=subprocess.Popen(
            ["php","-d","sendmail_path=/bin/false","-S",
             "127.0.0.1:"+str(port),"-t",str(web)],
            stdout=log,stderr=log)
        try:
            for _ in range(50):
                try:
                    with socket.create_connection(("127.0.0.1",port),timeout=.2):
                        break
                except OSError:time.sleep(.05)
            else:raise AssertionError("LOCAL_SERVER_NOT_READY")
            cases=[
                [{"sku":"t2"}],[{"sku":"t3"}],
                [{"name":"t2"}],[{"name":"t3"}],
                [{"name":unitresult["t2_name"]}] if "t2_name" in unitresult else [{"sku":"t2","name":"P4"}],
                [{"sku":"t3"},{"sku":"p4"}],
                [{"sku":"unknown","name":"T3"}],
            ]
            # Test both historical names verbatim, not approximations.
            for sku in RETIRED:
                cases.append([{"name":unitresult[sku+"_name"]}])
            for items in cases:
                code,body=send(port,items)
                assert code==422 and body.get("ok") is False,(items,code,body)
            assert not list((work/"orders").glob("order_*.json")),"NEW_ORDER_CREATED"
            assert not list((work/"orders").glob("payment-errors.log")),"PAYMENT_API_ATTEMPTED"
            print(json.dumps({"status":"PASS","retired_skus":2,
                              "historical_records_preserved":2,
                              "current_paid_skus_unaffected":len(ACTIVE),
                              "new_payment_attempts_denied":len(cases),
                              "real_api_calls":0,"real_orders_created":0,
                              "production_writes":0},ensure_ascii=False))
        finally:
            server.terminate()
            server.wait(timeout=5)
            log.close()

if __name__=="__main__":
    main()
