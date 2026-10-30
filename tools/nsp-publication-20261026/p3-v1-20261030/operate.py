#!/usr/bin/env python3
"""Existing targeted workflow: current P1 files only; payment code unchanged."""
from pathlib import Path
import base64,hashlib,io,json,os,shlex,subprocess,sys,tarfile,time,urllib.request,urllib.parse,zipfile
ROOT=Path(__file__).resolve().parent;E=Path('/tmp/nsp-final-evidence');E.mkdir(exist_ok=True)
action=sys.argv[1];assert action in ('p3-snapshot','p3-publish')
request=json.loads(Path('tools/nsp-final/request.json').read_text())
SHA='54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b'
assert request['sku']=='p3'and request['edition']=='P3-layout-v1'and request['approved_archive_sha256']==SHA
port=os.environ['PORT'];assert port.isdigit()
common=['-i',str(Path.home()/'.ssh/nsp_final_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2']
remote=os.environ['SSH_USER']+'@'+os.environ['HOST'];ssh=['ssh','-p',port,*common,remote];scp=['scp','-P',port,*common]
def call(args,data=None,timeout=45):
 r=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-1800:]+r.stdout.decode(errors='replace')[-1000:])
 return r.stdout
H=lambda b:hashlib.sha256(b).hexdigest()
if action=='p3-snapshot':
 raw=call(ssh+['php /dev/stdin "$HOME/www/nastoronepodryadchika.ru"'],(ROOT/'inspect.php').read_bytes())
 snapshot=json.loads(raw);assert snapshot['read_only'] is True;(E/'p3-production-snapshot.json').write_bytes(raw)
 out=E/'p3-before';out.mkdir(exist_ok=True)
 for name,row in snapshot['files'].items():
  data=base64.b64decode(row['base64']);assert H(data)==row['sha256']and len(data)==row['bytes']
  p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 print(json.dumps({'status':'P3_SNAPSHOT_PASS_NO_PRODUCTION_WRITES','files':len(snapshot['files'])}));sys.exit(0)

