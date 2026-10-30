from pathlib import Path
import base64,datetime,hashlib,json,subprocess,time
D=Path('/home/denis/projects/nsp-qa13-20261024/p1-publication-20261030');D.mkdir(exist_ok=True)
R='repos/pmgpt12-arch/marzhavbetone.ru';BR='codex/nsp-publication-catalog-20261026';PREFIX='tools/nsp-publication-20261026/p1-v1-20261030'
def api(method,path,payload=None):
 a=['gh','api','--method',method,R+'/'+path];data=None
 if payload is not None:a+=['--input','-'];data=json.dumps(payload,ensure_ascii=False).encode()
 return json.loads(subprocess.run(a,input=data,capture_output=True,check=True,timeout=18).stdout)
def fetch(path,ref):
 return base64.b64decode(api('GET','contents/'+path+'?ref='+ref)['content'])
def commit(files,message,base):
 entries=[]
 for p,b in files.items():
  blob=api('POST','git/blobs',{'content':base64.b64encode(b).decode(),'encoding':'base64'})['sha']
  assert blob==hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
  entries.append({'path':p,'mode':'100644','type':'blob','sha':blob})
 tree=api('POST','git/trees',{'base_tree':api('GET','git/commits/'+base)['tree']['sha'],'tree':entries})['sha']
 c=api('POST','git/commits',{'message':message,'tree':tree,'parents':[base]})['sha']
 assert api('GET','git/ref/heads/'+BR)['object']['sha']==base
 api('PATCH','git/refs/heads/'+BR,{'sha':c,'force':False})
 assert api('GET','git/ref/heads/'+BR)['object']['sha']==c
 return c
if __name__=='__main__':
 assert not (D/'SNAPSHOT_REQUEST.json').exists()
 base=api('GET','git/ref/heads/'+BR)['object']['sha']
 workflow=fetch('.github/workflows/nsp-cutover-final.yml',base).decode()
 assert 'p1-snapshot' not in workflow
 workflow=workflow.replace('"p2-publish"]','"p2-publish","p1-snapshot","p1-publish"]',1)
 workflow=workflow.replace('|| "$action" == p2-publish ]]; fi','|| "$action" == p2-publish || "$action" == p1-snapshot || "$action" == p1-publish ]]; fi',1)
 marker='      - name: Approved P2 v13 targeted publication'
 workflow=workflow.replace(marker,"      - name: Approved P1 targeted publication\n        if: startsWith(env.NSP_ACTION, 'p1-') && github.ref_name == '"+BR+"'\n        run: python3 "+PREFIX+"/operate.py \"$NSP_ACTION\"\n"+marker,1)
 inspect=fetch('tools/nsp-publication-20261026/p2-v13-20261029/inspect.php',base).decode().replace('p2-dopolnitelnye-raboty','p1-oplata-po-ks2').replace('NSP_P2','NSP_P1').replace('02-dopraboty-bez-poter','01-zakrytie-rabot').replace('p2_files','p1_files')
 operate="""from pathlib import Path
import json,os,subprocess,sys
assert sys.argv[1]=='p1-snapshot'
E=Path('/tmp/nsp-final-evidence');E.mkdir(exist_ok=True)
ssh=['ssh','-p',os.environ['PORT'],'-i',str(Path.home()/'.ssh/nsp_final_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=12',os.environ['SSH_USER']+'@'+os.environ['HOST']]
raw=subprocess.run(ssh+['php /dev/stdin "$HOME/www/nastoronepodryadchika.ru"'],input=(Path(__file__).parent/'inspect.php').read_bytes(),capture_output=True,check=True,timeout=45).stdout
x=json.loads(raw);assert x['read_only']
(E/'p1-production-snapshot.json').write_bytes(raw)
print(json.dumps({'status':'P1_READ_ONLY_SNAPSHOT_PASS','files':list(x['files']),'product_locations':x['product_locations']}))
"""
 approval={'sku':'p1','edition':'P1-layout-v1','owner_quote':'Все отлично ! Размещаем на сайте','owner_product_acceptance':'APPROVED','release_permission':'ALLOW_EXACT_EDITION_ONLY','archive_sha256':'99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada','file_count':18,'source_commit':'574eb0d7fa10106339d9c9d71f9f1dc3f378a386','approved_at_local_date':'2026-10-30','delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY'}
 request={**approval,'action':'p1-snapshot','approved_archive_sha256':approval['archive_sha256'],'request_id':'P1-SNAPSHOT-20261030'}
 files={'.github/workflows/nsp-cutover-final.yml':workflow.encode(),PREFIX+'/inspect.php':inspect.encode(),PREFIX+'/operate.py':operate.encode(),PREFIX+'/OWNER_APPROVAL.json':(json.dumps(approval,ensure_ascii=False,indent=2)+'\n').encode(),'tools/nsp-final/request.json':(json.dumps(request,ensure_ascii=False,indent=2)+'\n').encode()}
 for p,b in files.items():
  out=D/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
 c=commit(files,'P1: record owner approval and snapshot current production before release [skip deploy]',base)
 (D/'SNAPSHOT_REQUEST.json').write_text(json.dumps({'commit':c,'base':base,'branch':BR},indent=2))
 print(c)
