#!/usr/bin/env python3
"""One new cross-order probe; does not rerun the 59 accepted checks."""
import base64, hashlib, json, os, subprocess, tempfile, zipfile
from pathlib import Path
R='repos/pmgpt12-arch/marzhavbetone.ru'
H='8311bb2dc7b497415952d03630e4a477f8bf9d7c'

def api(path):
    return json.loads(subprocess.check_output(['gh','api',R+path],timeout=12))
def get(sha):
    return base64.b64decode(api('/git/blobs/'+sha)['content'])
def read(path):
    return base64.b64decode(api('/contents/'+path+'?ref='+H)['content'])

def main():
    ns={'__name__':'candidate_builder'}
    exec(compile(get('972f044aab5e8427927a5a55362486cd3f6639e5'),'build_candidate.py','exec'),ns)
    inputs={p:read(p) for p in ['products-config.php','download.php']}
    outputs,_=ns['build'](inputs,get('ea91f05178d77261e28616985056993750272725').decode())
    with tempfile.TemporaryDirectory(prefix='p11-legacy-crossorder-') as td:
        p=Path(td)
        (p/'orders').mkdir(); (p/'delivery').mkdir()
        master=p/'masters'/'13-raschet-metrami'; master.mkdir(parents=True)
        (master/'new.txt').write_text('changed legacy masters')
        os.utime(master/'new.txt',(2100000000,2100000000))
        archive=p/'delivery'/'13-raschet-metrami.zip'
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr('original.txt','old purchase exact bytes')
        original=archive.read_bytes()
        (p/'products-config.php').write_bytes(outputs['products-config.php'])
        php='''<?php
        define('ORDERS_DIR',__DIR__.'/orders');
        define('DELIVERY_DIR',__DIR__.'/delivery');
        define('PRODUCTS_DIR',__DIR__.'/masters');
        define('SITE_URL','https://fixture.invalid');
        require __DIR__.'/products-config.php';
        $order=['id'=>'order_20261014_9_test','status'=>'paid','items'=>[['sku'=>'p11']]];
        echo json_encode(mvb_prepare_delivery($order));
        '''
        (p/'probe.php').write_text(php)
        run=subprocess.run(['php','-d','disable_functions=mail','-d','allow_url_fopen=0',
            '-d','open_basedir='+td,str(p/'probe.php')],capture_output=True,timeout=8)
        if run.returncode or run.stderr:
            raise RuntimeError(run.stderr.decode())
        actual=archive.read_bytes()
        result={'id':'P11-CROSS-ORDER-LEGACY-CACHE-PROBE-20261014',
            'candidate_head':'f0efb917e98b82eb4d751686da887c10753ac6a7',
            'scenario':'New unmarked P11 order with newer legacy masters and an existing issued shared archive',
            'original_sha256':hashlib.sha256(original).hexdigest(),
            'after_sha256':hashlib.sha256(actual).hexdigest(),
            'legacy_archive_preserved':original==actual,
            'prepare_result':json.loads(run.stdout),
            'real_customers_or_production_touched':False,
            'transport_diagnosis':'Prior inline command stopped at Python SyntaxError before execution; use retained script blob instead of nested shell quoting'}
        result['status']='PASS' if original==actual else 'FAIL_CROSS_ORDER_LEGACY_CACHE_OVERWRITE'
    result['temporary_sandbox_removed']=not Path(td).exists()
    data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    uploaded=json.loads(subprocess.check_output(['gh','api','--method','POST',R+'/git/blobs','--input','-'],
        input=json.dumps({'encoding':'base64','content':base64.b64encode(data).decode()}).encode(),timeout=12))['sha']
    assert get(uploaded)==data
    print(json.dumps({'probe':result,'retained_blob':uploaded,'sha256':hashlib.sha256(data).hexdigest()},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
