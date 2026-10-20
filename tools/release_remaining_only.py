#!/usr/bin/env python3
"""Scoped R3 release in deploy.yml, with read-only dry-run and rollback."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
from urllib.parse import urlparse
import base64,json,os,shlex,subprocess,sys,tempfile

R=Path(__file__).resolve().parents[1];B=R/'tools/candidates/remaining-batch-r3-20261018';O=B/'release-20261020'
plan=json.loads((O/'release-plan.json').read_text());encoded=base64.b64encode(json.dumps(plan).encode()).decode()
assert os.environ.get('REMAINING_ONLY')=='true','explicit scope required'
for k in ['HOST','USER','SITE_PATH','PRODUCTS_PATH','SSH_PORT','REMAINING_SSH_DIR','RUNNER_TEMP']:assert os.environ.get(k),k
sshdir=Path(os.environ['REMAINING_SSH_DIR'])
ssh=['ssh','-i',str(sshdir/'deploy_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(sshdir/'known_hosts'),'-o','ConnectTimeout=20','-p',os.environ['SSH_PORT']]
host=os.environ['USER']+'@'+os.environ['HOST'];evidence=Path(os.environ['RUNNER_TEMP'])/'remaining-live-buyer-evidence';evidence.mkdir(exist_ok=True)
def run(args,**kw):return subprocess.run(args,cwd=R,check=True,timeout=90,**kw)
def ops(phase):
 code=(R/'tools/remaining_live_ops.php').read_text()
 anchor='[$script,$siteArg,$productsArg,$phase,$encoded] = $argv;'
 assert code.count(anchor)==1
 code=code.replace(anchor,'[$script,$siteArg,$productsArg,$phase] = $argv; $encoded="'+encoded+'";')
 # Send the plan and PHP over stdin; hosting SSH exec-request packets are bounded.
 cmd='php -- /dev/stdin '+' '.join(map(shlex.quote,[os.environ['SITE_PATH'],os.environ['PRODUCTS_PATH'],phase]))
 assert len(cmd.encode())<4096,'remote command must exclude code and plan payload'
 try:
  result=run([*ssh,host,cmd],input=code,capture_output=True,text=True)
 except subprocess.CalledProcessError as error:
  raise RuntimeError('REMOTE_PHASE '+phase+' exit='+str(error.returncode)+' stderr='+error.stderr[-3000:]) from None
 return json.loads(result.stdout)
def rsync(source,target,extra=(),dry=False):
 run(['rsync','-az','--itemize-changes',*(['--dry-run'] if dry else []),*extra,'-e',shlex.join(ssh),str(source),host+':'+target])
def write(name,obj):(evidence/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def main():
 run(['python3','tools/verify_remaining_release_20261020.py'])
 run(['php','-l','products-config.php']);run(['php','-l','tools/remaining_live_ops.php'])
 transport=run([*ssh,host,"php -r 'echo \"SSH_PHP_READY\";'"],capture_output=True,text=True)
 assert transport.stdout=='SSH_PHP_READY';print('PASS_SMALL_SSH_PHP_TRANSPORT',flush=True)
 receipt=ops('preflight');write('preflight.json',receipt);print('PASS_READ_ONLY_LIVE_BASELINES',flush=True)
 dry=os.environ.get('DRY_RUN')=='true'
 with tempfile.NamedTemporaryFile(mode='w',suffix='.files') as names:
  names.write('\n'.join(x['file'] for x in plan['site_files'] if x['file']!='products-config.php')+'\n');names.flush()
  if dry:
   for p in plan['packages']:rsync(str(R/'products-storage'/p['dir'])+'/',os.environ['PRODUCTS_PATH']+'/'+p['dir']+'/',extra=['--delete'],dry=True)
   rsync('./',os.environ['SITE_PATH']+'/',extra=['--files-from='+names.name],dry=True)
   rsync('products-config.php',os.environ['SITE_PATH']+'/products-config.php',dry=True)
   write('dry-run.json',{'status':'PASS_SCOPED_DRY_RUN_NO_PRODUCTION_WRITE','approved_outer_zip_sha256':plan['approved_outer_zip_sha256'],'products':9,'buyer_files':123,'site_files':len(plan['site_files'])})
   print('PASS_SCOPED_DRY_RUN_NO_PRODUCTION_WRITE',flush=True);return
  write('backup.json',ops('backup'));backup=True;probes=[]
  try:
   for p in plan['packages']:rsync(str(R/'products-storage'/p['dir'])+'/',os.environ['PRODUCTS_PATH']+'/'+p['dir']+'/',extra=['--delete'])
   print(ops('cache'),flush=True)
   rsync('./',os.environ['SITE_PATH']+'/',extra=['--files-from='+names.name])
   rsync('products-config.php',os.environ['SITE_PATH']+'/products-config.php')
   server=ops('verify');write('server-sha-verification.json',server);print(server,flush=True)
   # Actual HTTPS page bytes; no proxy/session or payment dependency.
   from bs4 import BeautifulSoup
   for p in plan['packages']:
    if 'page' not in p:continue
    url='https://marzhavbetone.ru/'+p['page']+'?remaining_release='+plan['approved_outer_zip_sha256'][:12]
    page=run(['curl','-fsSL','--max-time','25','-H','Cache-Control: no-cache',url],capture_output=True,text=True).stdout
    soup=BeautifulSoup(page,'html.parser');buttons=soup.select('button[data-sku="'+p['sku']+'"]')
    assert soup.h1.get_text()==p['name'] and buttons and all(int(b['data-price'])==p['price'] for b in buttons),p['sku']
    assert {c.get_text() for c in soup.select('.document-list code')}==set(p['members']),p['sku']
   catalog=run(['curl','-fsSL','--max-time','25','-H','Cache-Control: no-cache','https://marzhavbetone.ru/katalog.html?remaining_release='+plan['approved_outer_zip_sha256'][:12]],capture_output=True,text=True).stdout
   cards=BeautifulSoup(catalog,'html.parser').select('.product-card button[data-sku]');assert len(cards)==13 and len({b['data-sku'] for b in cards})==13
   probes=ops('create-probes');assert len(probes)==9
   verification=[]
   for probe in probes:
    p=next(p for p in plan['packages'] if p['sku']==probe['sku']);url=probe['url'];assert urlparse(url).hostname in {'marzhavbetone.ru','nastoronepodryadchika.ru'}
    dst=evidence/(p['sku'].upper()+'-production-buyer.zip')
    run(['curl','-fsSL','--max-time','35','-o',str(dst),url])
    with ZipFile(dst) as z:
     assert z.testzip() is None and len(z.namelist())==p['count']
     assert {n:sha256(z.read(n)).hexdigest() for n in z.namelist()}==p['members'],p['sku']
    verification.append({'sku':p['sku'],'files':p['count'],'member_SHA':'PASS','CRC':'PASS','active_HTTP':200,'ttl_seconds':probe['ttl'],'email_render':probe['email_render'],'production_zip':dst.name,'production_sha256':sha256(dst.read_bytes()).hexdigest(),'approved_zip_sha256':p['approved_zip_sha256']})
   ops('expire-probes')
   for probe in probes:
    status=run(['curl','-sSL','--max-time','20','-o','/dev/null','-w','%{http_code}',probe['url']],capture_output=True,text=True).stdout
    assert status=='410',(probe['sku'],status)
    next(v for v in verification if v['sku']==probe['sku'])['expired_HTTP']=410
   ops('cleanup-probes');probes=[]
   final=ops('verify');assert final['status']=='PASS_LIVE_MASTER_SITE_CATALOG_AND_UNRELATED_SHA'
   write('production-verification.json',{'status':'PASS_SCOPED_RELEASE_ACTUAL_HTTP_BUYER_ARCHIVES','buyer_files':123,'archives':9,'catalog_positions':13,'approval':plan['approved_outer_zip_sha256'],'publication_commit':os.environ.get('GITHUB_SHA'),'real_payment':'NOT_INVOKED','email':'RENDERED_NOT_SENT','synthetic_orders':'CLEANED_UP','checks':verification})
   print('PASS_SCOPED_RELEASE_9_HTTP_ARCHIVES_123_MEMBERS_TTL_AND_EXPIRED',flush=True)
  except BaseException:
   try:print(ops('cleanup-probes'),flush=True)
   except Exception as e:print('PROBE_CLEANUP_REQUIRES_INSPECTION',type(e).__name__,file=sys.stderr)
   try:write('rollback.json',ops('rollback'));print('ROLLBACK_COMPLETE',file=sys.stderr)
   except Exception as e:print('ROLLBACK_REQUIRES_MANUAL_RECOVERY',type(e).__name__,file=sys.stderr)
   raise
if __name__=='__main__':main()
