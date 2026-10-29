#!/usr/bin/env python3
"""Use the established GitHub Actions SSH transport; scoped P2 snapshot/publish."""
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
E=Path('/tmp/nsp-final-evidence');E.mkdir(exist_ok=True)
action=sys.argv[1];assert action in ('p2-snapshot','p2-publish')
request=json.loads(Path('tools/nsp-final/request.json').read_text())
assert request['sku']=='p2' and request['edition']=='P2-v13'
assert request['approved_archive_sha256']=='42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da'
port=os.environ['PORT'];assert port.isdigit()
ssh=['ssh','-p',port,'-i',str(Path.home()/'.ssh/nsp_final_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2',os.environ['SSH_USER']+'@'+os.environ['HOST']]
def call(args,data=None,timeout=45):
 r=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-1500:])
 return r.stdout
if action=='p2-snapshot':
 raw=call(ssh+['php /dev/stdin "$HOME/www/nastoronepodryadchika.ru"'],(ROOT/'inspect.php').read_bytes())
 snapshot=json.loads(raw);assert snapshot['read_only'] is True
 (E/'p2-production-snapshot.json').write_bytes(raw)
 out=E/'p2-before';out.mkdir(exist_ok=True)
 for name,row in snapshot['files'].items():
  data=base64.b64decode(row['base64']);assert hashlib.sha256(data).hexdigest()==row['sha256'] and len(data)==row['bytes']
  p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 print(json.dumps({'status':'P2_SNAPSHOT_PASS_NO_PRODUCTION_WRITES','files':{k:{x:y for x,y in v.items()if x!='base64'}for k,v in snapshot['files'].items()},'product_locations':snapshot['product_locations']},ensure_ascii=False,indent=2))
else:
 raise RuntimeError('P2_PUBLICATION_IMPLEMENTATION_NOT_PREPARED; no production writes')
