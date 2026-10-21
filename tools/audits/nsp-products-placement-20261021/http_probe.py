from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
from urllib.parse import urlparse
import json,subprocess,os,tempfile
base=Path('tools/audits/nsp-products-placement-20261021')
expected={}
for sku,(directory,count,price) in json.loads('{"p1":["01-zakrytie-rabot",20,2990000],"p2":["02-dopraboty-bez-poter",15,2490000],"p3":["05-ks-bez-vozvrata",11,1790000],"p4":["08-pto-bez-zamechaniy",25,2490000],"p5":["07-uderzhaniya-shtrafy-zachety",30,2990000],"p7":["03-dogovor-podryada",13,2490000],"p8":["10-avans-usloviya-i-pribyl",11,2490000],"p9":["11-bankrotstvo-genpodryadchika",10,2490000],"p10":["15-otvet-na-pretenziyu-baza",8,1790000],"p11":["13-raschet-metrami",8,2490000],"p13":["16-chto-v-smete-ne-oplatyat",10,1790000],"t2":["14-peredacha-id-pod-podpis",6,990000],"t3":["17-odnostoronniy-akt-i-zachet",5,1490000]}').items():
 root=Path('products-storage')/directory
 expected[sku]={'members':{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name not in {'.htaccess','MANIFEST.md','00-PISMO-POSLE-POKUPKI.txt'}}}
code=Path('/tmp/nsp-probe.php').read_text()
ssh=['ssh','-i',os.environ['NSP_AUDIT_KEY'],'-p',os.environ['PORT'],'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','UserKnownHostsFile='+os.environ['NSP_AUDIT_HOSTS'],os.environ['USER']+'@'+os.environ['HOST']]
def phase(name):
 p=subprocess.run(ssh+['php -f /dev/stdin -- '+name],input=code,text=True,capture_output=True,timeout=90)
 if p.returncode:raise RuntimeError('Remote phase '+name+' failed; '+p.stderr[-1000:])
 return json.loads(p.stdout)
report={'domain':'nastoronepodryadchika.ru','run':os.environ['GITHUB_RUN_ID'],'real_payment':'NOT_INVOKED','email':'RENDERED_NOT_SENT','checks':[]}
try:
 probes=phase('create');assert len(probes)==13
 with tempfile.TemporaryDirectory() as tmp:
  for probe in probes:
   sku=probe['sku'];assert urlparse(probe['url']).hostname=='nastoronepodryadchika.ru'
   dst=Path(tmp)/(sku+'.zip')
   p=subprocess.run(['curl','-sS','--max-time','35','-o',str(dst),'-w','%{http_code}',probe['url']],capture_output=True,text=True,timeout=40)
   assert p.returncode==0 and p.stdout=='200',(sku,'HTTP',p.stdout)
   with ZipFile(dst) as z:
    assert z.testzip() is None,sku
    members={n:sha256(z.read(n)).hexdigest() for n in z.namelist()}
    assert len(z.namelist())==len(members) and members==expected[sku]['members'],sku
   report['checks'].append({'sku':sku,'files':len(members),'sha256_all_members':'PASS','CRC':'PASS','active_HTTP':200,'ttl_seconds':probe['ttl_seconds'],'zip_sha256':sha256(dst.read_bytes()).hexdigest(),'email_render':probe['email_render']})
 phase('expire')
 for probe in probes:
  p=subprocess.run(['curl','-sS','--max-time','20','-o','/dev/null','-w','%{http_code}',probe['url']],capture_output=True,text=True,timeout=25)
  assert p.returncode==0 and p.stdout=='410',(probe['sku'],'expiry HTTP',p.stdout)
  next(x for x in report['checks'] if x['sku']==probe['sku'])['expired_HTTP']=410
 assert sum(x['files'] for x in report['checks'])==172
 report['status']='PASS_13_ACTUAL_HTTP_ARCHIVES_172_FILES_SHA_CRC_TTL'
except BaseException as e:
 report['status']='FAIL';report['error']=str(e);raise
finally:
 cleaned=phase('cleanup');report['synthetic_orders_cleaned']=len(cleaned)
 (base/'http-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(report['status'])
 for row in report['checks']:print(row['sku'],row['files'],row.get('sha256_all_members'),row.get('expired_HTTP'))
