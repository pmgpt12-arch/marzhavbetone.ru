#!/usr/bin/env python3
"""Bounded inspect -> exact source/live manifest -> private backups; no cutover."""
from __future__ import annotations
import base64,datetime,hashlib,json,os,shlex,socket,ssl,subprocess,tempfile,urllib.request,urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DIR=Path(__file__).resolve().parent
CONTRACT=json.loads((DIR/'contract.json').read_text())
OUT=DIR/'evidence'
OUT.mkdir(exist_ok=True)
SKIP={'.htaccess','00-PISMO-POSLE-POKUPKI.txt','MANIFEST.md'}


def command(args,timeout=90,**kwargs):
    return subprocess.run(args,cwd=ROOT,timeout=timeout,check=True,**kwargs)


def write(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')


def remote(phase):
    key=Path(os.environ['MIGRATION_SSH_DIR'])
    ssh=['ssh','-i',str(key/'deploy_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(key/'known_hosts'),'-o','ConnectTimeout=15','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=3','-p',os.environ['SSH_PORT']]
    script=(DIR/'probe.php').read_text()
    marker='__CONTRACT_B64__'
    assert script.count(marker)==1
    script=script.replace(marker,base64.b64encode(json.dumps(CONTRACT).encode()).decode())
    tag='run-'+os.environ['GITHUB_RUN_ID']
    cmd='php -f /dev/stdin -- '+' '.join(shlex.quote(v) for v in [os.environ['SITE_PATH'],os.environ['PRODUCTS_PATH'],phase,tag])
    assert len(cmd)<4096
    try:
        r=command([*ssh,os.environ['USER']+'@'+os.environ['HOST'],cmd],input=script,text=True,capture_output=True,timeout=210)
    except subprocess.CalledProcessError as e:
        # Known SSH errors only; remote code never prints secret constants.
        raise RuntimeError('REMOTE_'+phase.upper()+'_FAILED exit='+str(e.returncode)+' '+e.stderr[-500:]) from None
    return json.loads(r.stdout)


def repo_manifest():
    expected=CONTRACT['active_skus']
    assert len(expected)==13 and sum(p['files'] for p in expected.values())==172
    assert all(p['dir'].isascii() for p in expected.values()),'TECHNICAL_DIR_NON_ASCII'
    with tempfile.TemporaryDirectory(prefix='nsp-catalog-') as td:
        code='define("ORDERS_DIR",'+json.dumps(td+'/orders')+'); define("PRODUCTS_DIR",'+json.dumps(str(ROOT/'products-storage'))+'); require '+json.dumps(str(ROOT/'products-config.php'))+'; $a=[];foreach(mvb_products() as $s=>$p){if($s!=="test1"&&mvb_resolve_product(["sku"=>$s])!==null)$a[$s]=$p;}echo json_encode($a,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);'
        catalog=json.loads(command(['php','-r',code],text=True,capture_output=True,timeout=15).stdout)
    assert set(catalog)==set(expected),'REPO_ACTIVE_SKU_DRIFT'
    products={}
    for sku,spec in expected.items():
        p=catalog[sku]
        assert p['price']==spec['price'] and p['dir']==spec['dir'],f'REPO_CATALOG_DRIFT_{sku}'
        root=ROOT/'products-storage'/p['dir'];files={}
        assert root.is_dir(),f'MASTER_SOURCE_MISSING_{sku}'
        for f in sorted(root.rglob('*')):
            if not f.is_file() or f.name in SKIP:continue
            assert not f.is_symlink(),f'REPO_BUYER_SYMLINK_{sku}'
            assert f.resolve().is_relative_to(root.resolve())
            files[f.relative_to(root).as_posix()]={'size':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
        assert len(files)==spec['files'],f'REPO_FILE_COUNT_{sku}:{len(files)}'
        products[sku]={'name':p['name'],'price':p['price'],'dir':p['dir'],'zip':p['zip'],'files':files}
    return products


def site_state():
    rows=[]
    for domain in [CONTRACT['old_domain'],CONTRACT['new_domain']]:
        for host in [domain,'www.'+domain]:
            item={'host':host}
            try:
                item['addresses']=sorted({v[4][0] for v in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)})
                ctx=ssl.create_default_context()
                with socket.create_connection((host,443),timeout=8) as sock:
                    with ctx.wrap_socket(sock,server_hostname=host) as tls:
                        cert=tls.getpeercert();item['tls_verified']=True;item['certificate_not_after']=cert.get('notAfter');item['san']=cert.get('subjectAltName',[])
                req=urllib.request.Request('https://'+host+'/',headers={'User-Agent':'NSP-Migration-Audit/1.0'})
                with urllib.request.urlopen(req,timeout=12) as response:
                    data=response.read(1000000)
                    item.update(status=response.status,final_url=response.url,root_sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),new_brand='На стороне подрядчика'.encode() in data,hosting_placeholder='Домен успешно привязан'.encode() in data)
            except Exception as e:
                item['error']=type(e).__name__+':'+str(e)[:180]
            rows.append(item)
    return rows


def main():
    # This first job must not overwrite or roll back somebody else's main.
    command(['git','fetch','--no-tags','--depth=1','origin','main'],timeout=35,capture_output=True,text=True)
    main_sha=command(['git','rev-parse','FETCH_HEAD'],capture_output=True,text=True).stdout.strip()
    assert main_sha==CONTRACT['approved_base_commit'],'MAIN_ADVANCED_RECONCILIATION_REQUIRED_'+main_sha
    actual_sha=command(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()
    source=repo_manifest()
    write('repository-full-13sku-manifest.json',{'source_main_commit':main_sha,'sku_count':13,'buyer_files':172,'products':source})
    classification_path=ROOT/CONTRACT['existing_check_classification']
    classes=json.loads(classification_path.read_text())
    summary=[{'id':r.get('id'),'classification':r.get('classification'),'exit':r.get('current',{}).get('exit')} for r in classes.get('checks',[])]
    write('preexisting-check-classification-summary.json',{'file':CONTRACT['existing_check_classification'],'sha256':hashlib.sha256(classification_path.read_bytes()).hexdigest(),'original_status':classes.get('status'),'checks':summary,'historical_failures_not_relabelled_pass':True})
    live=remote('inspect')
    write('live-before-inspection.json',live)
    assert source==live['products'],'LIVE_DOCUMENTS_OR_CATALOG_NOT_IDENTICAL_TO_REPOSITORY'
    assert live['buyer_files']==172 and len(live['active_skus'])==13
    print('PASS_COMPLETE_MAIN_VS_PRODUCTION_MANIFEST 13_SKUS 172_FILES',flush=True)
    public=site_state();write('public-before-state.json',public)
    assert all(x.get('tls_verified') for x in public if x['host'].endswith(CONTRACT['new_domain'])),'NEW_DOMAIN_TLS_NOT_VERIFIED'
    saved=remote('backup');write('private-backup-receipt.json',saved)
    assert saved['products']==source,'LIVE_MANIFEST_CHANGED_DURING_BACKUP'
    assert saved['config_sha256_not_contents']==live['config_sha256_not_contents'],'LIVE_CONFIG_CHANGED_DURING_BACKUP'
    assert saved['code_sha256']==live['code_sha256'],'LIVE_SITE_CHANGED_DURING_BACKUP'
    write('checkpoint.json',{'status':'PASS_INSPECT_PRIVATE_BACKUPS_FULL_13SKU_MANIFEST','source_main':main_sha,'execution_commit':actual_sha,'github_run':int(os.environ['GITHUB_RUN_ID']),'sku_count':13,'buyer_files':172,'production_code_changed':False,'backup_path':saved['backup_location'],'next':'PREPARE_FROM_CURRENT_MAIN; scoped dry-run; validate handlers; real payment gate explicitly separated','historical_ci_classification_preserved':True})
    print('PASS_INSPECT_AND_PRIVATE_BACKUPS_NO_CUTOVER',flush=True)

if __name__=='__main__':main()
