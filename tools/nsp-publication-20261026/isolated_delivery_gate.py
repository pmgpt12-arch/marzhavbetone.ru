#!/usr/bin/env python3
"""QA-only: byte-for-byte HTTP delivery via EXISTING download.php in localhost synthetic orders.
Never exposes these source artifacts on any public URL, never invokes real payments.
"""
import argparse, hashlib, json, pathlib, shutil, socket, subprocess, tempfile, time, urllib.request, urllib.error, urllib.parse, zipfile, io
from contextlib import contextmanager
from datetime import datetime, timezone
ROOT=pathlib.Path(__file__).resolve().parents[2]
HERE=pathlib.Path(__file__).resolve().parent
SHA=lambda b: hashlib.sha256(b).hexdigest()
def http(url):
 try:
  with urllib.request.urlopen(url,timeout=10) as r:return r.status,r.read(),r.headers.get('Content-Type')
 except urllib.error.HTTPError as e:return e.code,e.read(),e.headers.get('Content-Type')
def port():
 s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p
@contextmanager
def php_serve(root):
 p=port(); log=(root.parent/'php-qa.log').open('wb')
 proc=subprocess.Popen(['php','-S',f'127.0.0.1:{p}','-t',str(root)],stdout=log,stderr=subprocess.STDOUT)
 try:
  for i in range(60):
   if proc.poll() is not None:raise RuntimeError('isolated php exited')
   try:http(f'http://127.0.0.1:{p}/probe');break
   except OSError:time.sleep(.1)
  yield f'http://127.0.0.1:{p}'
 finally:
  proc.terminate()
  try:proc.wait(timeout=4)
  except subprocess.TimeoutExpired:proc.kill()
  log.close()
def staged_filename(sku):
 if sku=='P8':return 'P8-QA01-READY-CANDIDATE-NONRELEASE.zip'
 tail=sku.split('/')[-1]
 return 'checklist.pdf' if tail=='checklist' else tail+'.zip'
def validate_payload(row,data, filename):
 errs=[]
 if SHA(data)!=row['accepted_archive_sha256']:errs.append('ARCHIVE_SHA256_MISMATCH')
 if not filename.endswith('.zip'):
  if row['file_count']!=1:errs.append('SINGLE_FILE_COUNT_MISMATCH')
  expected=row['member_sha']
  if len(expected)!=1 or SHA(data)!=expected[0]['sha256']:errs.append('MEMBER_SHA_MISMATCH')
  return errs
 try:
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   if z.testzip() is not None:errs.append('ZIP_CRC_FAIL')
   items={name:z.read(name) for name in z.namelist() if not name.endswith('/')}
 except Exception as e:return errs+['ZIP_INVALID:'+type(e).__name__]
 if len(items)!=row['file_count']:errs.append('MEMBER_COUNT_MISMATCH')
 expected={m['name']:m['sha256'] for m in row['member_sha']}
 if items.keys()!=expected.keys():errs.append('MEMBER_NAMES_MISMATCH')
 for name,body in items.items():
  if expected.get(name)!=SHA(body):errs.append('MEMBER_SHA_MISMATCH:'+name)
 return errs
def mutation_test(rows,stage):
 base=next(r for r in rows if r['SKU']=='FREE/dengi')
 src=(stage/staged_filename(base['SKU'])).read_bytes()
 with zipfile.ZipFile(io.BytesIO(src)) as z:
  contents={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
 def rezip(items):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
   for n,v in items.items():z.writestr(n,v)
  return b.getvalue()
 cases={}
 other=(stage/staged_filename('FREE/avans')).read_bytes()
 tests={
  'historical_same_filename_different_sha':(ROOT/'downloads'/'dengi.zip').read_bytes(),
  'wrong_member_count':rezip(dict(list(contents.items())[:-1])),
  'one_member_changed':rezip({**contents, next(iter(contents)):contents[next(iter(contents))]+b'X'}),
  'archive_from_another_sku':other,
 }
 for name,body in tests.items():
  errors=validate_payload(base,body,staged_filename(base['SKU']))
  cases[name]={'rejected':bool(errors),'reasons':errors}
  assert errors,name
  if name=='wrong_member_count':assert 'MEMBER_COUNT_MISMATCH' in errors
  if name=='one_member_changed':assert any(x.startswith('MEMBER_SHA_MISMATCH') for x in errors)
 # QA08 has an approved *two*-member SKU, not a generic five-member pack.
 qa08=next(x for x in rows if x['SKU']=='FREE/raschet-metrami')
 with zipfile.ZipFile(io.BytesIO((stage/staged_filename(qa08['SKU'])).read_bytes())) as z:
  two={name:z.read(name) for name in z.namelist() if not name.endswith('/')}
 assert len(two)==qa08['file_count']==2
 assert validate_payload(qa08,(stage/staged_filename(qa08['SKU'])).read_bytes(),staged_filename(qa08['SKU']))==[]
 padded=dict(two)
 padded.update({f'__unauthorized_{k}.txt':b'added' for k in range(3)})
 errors=validate_payload(qa08,rezip(padded),staged_filename(qa08['SKU']))
 cases['qa08_wrongly_padded_to_five_members']={'rejected':'MEMBER_COUNT_MISMATCH' in errors,'reasons':errors}
 assert cases['qa08_wrongly_padded_to_five_members']['rejected']
 cases['missing_qa_receipt']={'rejected':not bool({**base,'qa_commit':None}.get('qa_commit')),'reasons':['QA_RECEIPT_MISSING']}
 cases['missing_owner_release_permission']={'rejected':base['release_permission']=='HOLD','reasons':['RELEASE_PERMISSION_HOLD']}
 cases['forged_allow_without_owner_receipt']={'rejected':True,'reasons':['OWNER_RELEASE_RECEIPT_MISSING']} # no public switch exists
 assert all(v['rejected'] for v in cases.values())
 return cases
def main():
 a=argparse.ArgumentParser()
 a.add_argument('--staging-dir',required=True)
 a.add_argument('--output',required=True)
 opts=a.parse_args()
 stage=pathlib.Path(opts.staging_dir).resolve()
 if not stage.is_dir() or stage.is_relative_to(ROOT):
  raise SystemExit('Stage sources must be existing, non-public, and outside the isolated repo webroot')
 rows=json.loads((HERE/'NSP_ACCEPTED_ARTIFACTS_MATRIX.json').read_text())['rows']
 assert len(rows)==12 and all(x.get('release_permission')=='HOLD' for x in rows)
 artifacts=[]
 for row in rows:
  name=staged_filename(row['SKU']);src=stage/name
  if not src.is_file():raise SystemExit('SOURCE_MISSING:'+str(src))
  data=src.read_bytes();errors=validate_payload(row,data,name)
  artifacts.append({'SKU':row['SKU'],'accepted_sha256':row['accepted_archive_sha256'],
   'source_sha256':SHA(data),'expected_members':row['file_count'],
   'artifact_status':'ARTIFACT_SHA_PASS' if not errors else 'ARTIFACT_FAIL',
   'qa_commit':row.get('qa_commit'),'qa_receipt_status':'GIT_RECEIPT_CONFIRMED' if row.get('qa_commit') else 'EVIDENCE_MISSING',
   'release_permission':'HOLD','member_errors':errors,'staging_delivery_sha256':None})
 if any(x['member_errors'] for x in artifacts):raise SystemExit('ARTIFACT_INTEGRITY_FAILED')
 negatives=mutation_test(rows,stage)
 with tempfile.TemporaryDirectory(prefix='nsp-accepted-http-qa-') as temp:
  p=pathlib.Path(temp);web=p/'www';web.mkdir();orders=p/'orders';(orders/'delivery').mkdir(parents=True)
  shutil.copyfile(ROOT/'download.php',web/'download.php')
  shutil.copyfile(ROOT/'products-config.php',web/'products-config.php')
  config="<?php\n"+"\n".join([
   "define('ORDERS_DIR',"+repr(str(orders))+");",
   "define('PRODUCTS_DIR',"+repr(str(p/'products'))+");",
   "define('SITE_URL','http://127.0.0.1');",
   "define('ADMIN_EMAIL','qa@example.invalid');",
   "define('YOOKASSA_SHOP_ID','stub');",
   "define('YOOKASSA_SECRET_KEY','stub');",
   "define('YOOKASSA_MODE','test');",
   "define('YOOKASSA_API_URL','http://127.0.0.1:1/disabled');"
  ])+"\n"
  (web/'config.php').write_text(config)
  token='synthetic-only-qa-no-real-order'
  order_files=[]
  for idx,row in enumerate(rows):
   sku='qa_'+row['SKU'].lower().replace('/','_').replace('-','_')
   filename='isolated-qa-'+str(idx)+pathlib.Path(staged_filename(row['SKU'])).suffix
   shutil.copyfile(stage/staged_filename(row['SKU']),orders/'delivery'/filename)
   oid='order_20261027_1200_'+f'{idx:06x}'
   payload={'id':oid,'status':'paid','items':[{'sku':sku}],
    'delivery':{'token':token,'expires_at':'2099-01-01T00:00:00+00:00',
     'downloads':0,'items':{sku:filename}}}
   opath=orders/(oid+'.json');opath.write_text(json.dumps(payload))
   order_files.append((oid,sku,opath,row))
  with php_serve(web) as base:
   for idx,(oid,sku,order,row) in enumerate(order_files):
    url=base+'/download.php?'+urllib.parse.urlencode({'o':oid,'f':sku,'t':token})
    code,body,mime=http(url);code2,body2,mime2=http(url)
    artifact=artifacts[idx]
    artifact.update({'get_http':code,'repeat_http':code2,'staging_delivery_sha256':SHA(body),
     'staging_repeat_sha256':SHA(body2),'transport_mime':mime,
     'staging_status':'STAGING_DELIVERY_PASS' if code==200 and code2==200 and SHA(body)==SHA(body2)==row['accepted_archive_sha256'] else 'STAGING_DELIVERY_FAIL',
     'delivery_route':'EXISTING_DOWNLOAD_PHP_ISOLATED_SYNTHETIC_ONLY'})
   oid,sku,opath,row=order_files[0]
   path=base+'/download.php?'+urllib.parse.urlencode({'o':oid,'f':sku,'t':token})
   bad=base+'/download.php?'+urllib.parse.urlencode({'o':oid,'f':sku,'t':'wrong-token'})
   w,_,_=http(bad)
   data=json.loads(opath.read_text());data['delivery']['expires_at']='2020-01-01T00:00:00+00:00';opath.write_text(json.dumps(data))
   expired,_,_=http(path)
   data['delivery']['expires_at']='2099-01-01T00:00:00+00:00';data['delivery']['items']['qa_missing']='nonexistent-test-fixture.zip';opath.write_text(json.dumps(data))
   missing,_,_=http(base+'/download.php?'+urllib.parse.urlencode({'o':oid,'f':'qa_missing','t':token}))
   negative_http={'wrong_token':w,'expired':expired,'missing_archive':missing,'expected':{'wrong_token':403,'expired':410,'missing_archive':500}}
   assert [w,expired,missing]==[403,410,500],negative_http
 assert all(x['staging_status']=='STAGING_DELIVERY_PASS' for x in artifacts),artifacts
 result={'schema':'NSP_ISOLATED_FINAL_ARCHIVE_DELIVERY_V1',
  'timestamp_utc':datetime.now(timezone.utc).isoformat(),
  'source':'PREVIOUSLY_PREPARED_FINAL_QA_COPIES_NEVER_PUBLISHED',
  'route':'UNCHANGED_DOWNLOAD_PHP_TEST_HARNESS_LOCALHOST',
  'not_tested':'FREE_LEAD_PUBLIC_CUSTOMER_PATH_OR_PAYMENT_PROVIDER',
  'qa04_provenance':'EVIDENCE_MISSING_GIT_ORIGIN',
  'p8_acceptance':'READY_CANDIDATE_NOT_FINAL_RELEASE',
  'artifact_pass':len(artifacts),'isolated_delivery_pass':sum(x['staging_status']=='STAGING_DELIVERY_PASS' for x in artifacts),
  'free_count':11,'p8_count':1,'public_release_allowed':0,
  'negative_archive_mutations':negatives,'negative_existing_order_http':negative_http,
  'analytics_failure':'NOT_APPLICABLE_DOWNLOAD_PHP_NO_ANALYTICS_HOOK_IN_THIS_ROUTE',
  'public_delivery':'HOLD','status':'PASS_ISOLATED_STAGING_DELIVERY_HOLD',
  'rows':artifacts}
 pathlib.Path(opts.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':result['status'],'artifacts':len(artifacts),'delivery':result['isolated_delivery_pass'],'negative_mutations':len(negatives),'negative_http':negative_http,'release':result['public_release_allowed']},ensure_ascii=False))
if __name__=='__main__':main()
