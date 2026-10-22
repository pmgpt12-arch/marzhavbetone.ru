"""Read-only, bounded HTTP baseline. Run before editing public sources."""
import concurrent.futures, datetime, hashlib, json, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent / 'baseline'
OUT.mkdir(exist_ok=True)
FILES = ['index.html','diagnostika.html','materialy/dengi.html','materialy/bankrotstvo.html','materialy/avans.html','products/t2-peredacha-ispolnitelnoy-dokumentacii.html','products/p11-raschet-metrami.html','products/p3-shablony-ks2-ks3.html','products/p8-avans-po-dogovoru-subpodryada.html','katalog.html','success.html','app-script.php','app.js','attribution.js','catalog.css','brand-approved-2026.css']
def fetch(name):
    target = OUT/name; target.parent.mkdir(parents=True,exist_ok=True)
    result = subprocess.run(['curl','--fail','--silent','--show-error','--max-time','35','-D',str(target)+'.headers','https://nastoronepodryadchika.ru/'+name,'-o',str(target)],capture_output=True,text=True,timeout=40)
    data = target.read_bytes() if result.returncode == 0 else b''
    source = ROOT/('app.js' if name=='app-script.php' else name)
    return {'path':name,'url':'https://nastoronepodryadchika.ru/'+name,'exit':result.returncode,'error':result.stderr,'bytes':len(data),'live_sha256':hashlib.sha256(data).hexdigest() if data else None,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'equals_main_source':data==source.read_bytes()}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(fetch,FILES))
(OUT/'HTTP_BASELINE.json').write_text(json.dumps({'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':'c7e32ecc7ad5d8d4b0a3e425ccfe8eeccafe8433','files':rows},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(rows,ensure_ascii=False,indent=2))
