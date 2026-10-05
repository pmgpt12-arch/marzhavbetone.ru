from pathlib import Path
import subprocess, json, hashlib, zipfile, io, zlib, time, datetime, xml.etree.ElementTree as ET, re
ROOT = Path(__file__).resolve().parent
REPO = Path('/home/denis/projects/marzhavbetone.ru')
SHA = '302d2e4d44bea16508b8e6e64211a2d10953aa51'
BRANCH = 'refs/heads/claude/cool-bardeen-pbwfsx'
PRODUCT = 'products-storage/05-ks-bez-vozvrata/'
NATIVE = {'02-reestr-prilozheniy.xlsx':'7d3a10560614401c36ef854cd3aead16961864479a9bfcb7d38dc78ab743c7f3','06-zhurnal-peredachi.xlsx':'98f20a51a39c41d5cf0e0fd6766cbeb1e8906bbad087956b736b1482f18ab73d'}
def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git',*args],cwd=REPO,timeout=30)
def save(n,v): (ROOT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
started=time.monotonic()
receipt={'execution_pattern':'one_shot','primary_result':'P3_exact_302d_actual_PHP_ZIP_membership_hash_CRC_and_02_06_metadata','feedback_loop_required':False,'checkpoint_policy':'verified_only','frozen_input_sha':SHA,'usd':0,'llm_calls':0,'release_pass':False,'sale_ready':False,'body_legal_review':'NOT_PERFORMED','native_application_run':'NOT_PERFORMED','status':'STARTED'}
try:
    assert json.loads((ROOT/'passport.json').read_text())['frozen_input_sha']==SHA
    live=git('ls-remote','origin',BRANCH).decode().split()[0]
    assert live==SHA,live
    paths=git('ls-tree','-r','--name-only',SHA,PRODUCT).decode().splitlines()
    assert len(paths)==12,len(paths)
    paths += ['products-config.php','products-storage/build_paid_05.py','tools/candidates/MB001_P3_METADATA_REPRODUCTION_2026-10-05.md']
    source=ROOT/'exact-source'
    assert not source.exists(),'existing input/output: do not repeat'
    index=[]
    for p in paths:
        data=git('show',SHA+':'+p)
        dest=source/p; dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        blob=git('rev-parse',SHA+':'+p).decode().strip()
        index.append({'path':p,'git_blob':blob,'sha256':sha(data),'bytes':len(data)})
    save('input-blobs.json',index)
    producer=(source/'products-storage/build_paid_05.py').read_text()
    canonical='Microsoft Excel'
    assert 'r"\\g<1>Microsoft Excel\\g<2>"' in producer
    php=ROOT/'build.php'
    php.write_text("""<?php
declare(strict_types=1);
define('ORDERS_DIR', __DIR__ . '/isolated-orders');
define('DELIVERY_DIR', __DIR__ . '/isolated-delivery');
define('PRODUCTS_DIR', __DIR__ . '/exact-source/products-storage');
require __DIR__ . '/exact-source/products-config.php';
if (!class_exists('ZipArchive')) {throw new RuntimeException('ZipArchive unavailable');}
$catalog = mvb_products();
$zip = mvb_build_product_zip('p3');
if (!$zip || !is_file($zip)) {throw new RuntimeException('P3 actual ZIP not produced');}
echo json_encode(['catalog'=>$catalog['p3'],'zip_path'=>$zip,'products_dir'=>PRODUCTS_DIR,'orders_dir'=>ORDERS_DIR,'delivery_dir'=>DELIVERY_DIR,'php'=>PHP_VERSION],JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE), "\\n";
""")
    cmd=['timeout','--kill-after=5s','30s','php',str(php)]
    t=time.monotonic(); proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=40)
    (ROOT/'php.stdout.log').write_text(proc.stdout);(ROOT/'php.stderr.log').write_text(proc.stderr)
    run={'command':cmd,'cwd':str(ROOT),'exit_code':proc.returncode,'elapsed_seconds':time.monotonic()-t}
    save('php-execution.json',run)
    assert proc.returncode==0,proc.stderr
    actual=json.loads(proc.stdout)
    catalog=actual['catalog'];directory=source/'products-storage'/catalog['dir']
    assert directory==source/PRODUCT.rstrip('/'),catalog
    archive=Path(actual['zip_path'])
    assert archive.parent==ROOT/'isolated-delivery'
    assert archive.name==catalog['zip']
    service={'.htaccess','00-PISMO-POSLE-POKUPKI.txt','MANIFEST.md'}
    assert "$service = ['.htaccess', '00-PISMO-POSLE-POKUPKI.txt', 'MANIFEST.md'];" in (source/'products-config.php').read_text()
    expected={str(p.relative_to(directory)):p for p in directory.rglob('*') if p.is_file() and p.name not in service}
    rows=[];native=[]
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        assert len(names)==len(set(names)), 'duplicate ZIP entries'
        assert sorted(names)==sorted(expected),(names,sorted(expected))
        assert z.testzip() is None, 'ZIP CRC failure'
        for name in sorted(names):
            info=z.getinfo(name);data=z.read(name);original=expected[name].read_bytes()
            assert data==original,name
            assert info.CRC==(zlib.crc32(data)&0xffffffff),name
            assert Path(name).name not in service and not any(p in ['tools','templates'] for p in Path(name).parts),name
            rows.append({'name':name,'bytes':len(data),'sha256':sha(data),'source_equal':True,'crc32':f'{info.CRC:08x}','crc_valid':True})
            if name in NATIVE:
                assert sha(data)==NATIVE[name],name
                with zipfile.ZipFile(io.BytesIO(data)) as x:
                    assert x.testzip() is None
                    app=x.read('docProps/app.xml');xml=ET.fromstring(app)
                    ns={'e':'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'}
                    application=xml.findtext('e:Application',namespaces=ns)
                    version=xml.findtext('e:AppVersion',namespaces=ns)
                    assert application==canonical and version=='3.1',(application,version)
                    with zipfile.ZipFile(expected[name]) as orig: assert app==orig.read('docProps/app.xml')
                    native.append({'file':name,'raw_source_exact':True,'accepted_sha256':NATIVE[name],'Application':application,'producer_canonical_exact':True,'AppVersion':version,'app_xml_sha256':sha(app),'app_xml_bytes':app.decode()})
    assert len(native)==2
    for entry in index: assert sha((source/entry['path']).read_bytes())==entry['sha256'],entry
    assert git('ls-remote','origin',BRANCH).decode().split()[0]==SHA,'branch changed'
    receipt.update(status='VERIFIED_ACTUAL_PHP_ZIP_EXACT_ACCEPTED_INPUTS',timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),live_branch_before_after=SHA,actual_php=actual,run=run,zip={'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),'members':len(rows),'membership_exact':True,'crc_all_valid':True,'all_member_source_bytes_exact':True,'service_template_files_absent':True},members=rows,native_02_06=native,input_blob_count=len(index),input_blobs_manifest='input-blobs.json',source_before_after_exact=True,source_repository_edited=False,php_builder_calls=1,general_tests_rerun=0,Calc_Excel_calls=0,merge_or_deploy=False)
except Exception as e:
    receipt.update(status='BLOCKED',block_type=type(e).__name__,block_reason=str(e))
    raise
finally:
    receipt['elapsed_seconds']=time.monotonic()-started
    save('receipt.json',receipt)
    sums=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.name!='SHA256SUMS.txt':
            sums.append(sha(p.read_bytes())+'  '+str(p.relative_to(ROOT)))
    (ROOT/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n')
    print(json.dumps({k:receipt[k] for k in ['status','frozen_input_sha','elapsed_seconds']}))
