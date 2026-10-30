from pathlib import Path
import json,os,subprocess,sys
assert sys.argv[1]=='p1-snapshot'
E=Path('/tmp/nsp-final-evidence');E.mkdir(exist_ok=True)
ssh=['ssh','-p',os.environ['PORT'],'-i',str(Path.home()/'.ssh/nsp_final_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=12',os.environ['SSH_USER']+'@'+os.environ['HOST']]
raw=subprocess.run(ssh+['php /dev/stdin "$HOME/www/nastoronepodryadchika.ru"'],input=(Path(__file__).parent/'inspect.php').read_bytes(),capture_output=True,check=True,timeout=45).stdout
x=json.loads(raw);assert x['read_only']
(E/'p1-production-snapshot.json').write_bytes(raw)
print(json.dumps({'status':'P1_READ_ONLY_SNAPSHOT_PASS','files':list(x['files']),'product_locations':x['product_locations']}))
