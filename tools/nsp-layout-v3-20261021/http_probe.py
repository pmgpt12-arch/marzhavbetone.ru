"""Exact independent HTTPS checks for the complete final nine-file release."""
from pathlib import Path
import concurrent.futures,json,hashlib,urllib.request,urllib.parse
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
rows=json.loads((HERE/'first-release-manifest.json').read_text());current=json.loads((ROOT/'tools/nsp-final/manifest.json').read_text());expected={r['path']:r['after'] for r in rows};expected.update({r['path']:r['after'] for r in current})
def probe(item):
 name,wanted=item;url='https://nastoronepodryadchika.ru/'+name
 req=urllib.request.Request(url+'?nsp_layout_final=20261021',headers={'Cache-Control':'no-cache','Accept-Encoding':'identity','User-Agent':'NSP-Layout-Verification/1.0'})
 with urllib.request.urlopen(req,timeout=20) as r:
  data=r.read(2000001);assert r.status==200 and urllib.parse.urlsplit(r.url).hostname=='nastoronepodryadchika.ru';assert len(data)<=2000000
 assert hashlib.sha256(data).hexdigest()==wanted and data==(ROOT/name).read_bytes(),name
 return {'path':name,'status':200,'sha256':wanted,'exact_bytes':'MATCH'}
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:out=list(pool.map(probe,expected.items()))
 assert len(out)==9;(HERE/'http-result.json').write_text(json.dumps({'status':'PASS','files':out},indent=2)+'\n');print('FINAL_LAYOUT_HTTPS=PASS; exactfiles=9')
