#!/usr/bin/env python3
"""Independent GET, ZIP CRC and 47 component source hashes; no form submission."""
from pathlib import Path
import concurrent.futures,hashlib,json,zipfile,io,urllib.request
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
rows=json.loads((ROOT/'tools/nsp-final/manifest.json').read_text())
def inspect(row):
 p=row['path'];req=urllib.request.Request('https://nastoronepodryadchika.ru/'+p,headers={'Cache-Control':'no-cache','Accept-Encoding':'identity','User-Agent':'NSP-Free-Final-Verification/1.0'})
 with urllib.request.urlopen(req,timeout=20) as response:
  data=response.read(2000001);assert response.status==200 and response.url=='https://nastoronepodryadchika.ru/'+p
  assert len(data)<=2000000
 sha=hashlib.sha256(data).hexdigest();assert sha==row['after'] and data==(ROOT/p).read_bytes(),p
 with zipfile.ZipFile(io.BytesIO(data)) as actual,zipfile.ZipFile(ROOT/p) as expected:
  assert actual.testzip() is None and actual.namelist()==expected.namelist()
  members=[{'name':n,'sha256':hashlib.sha256(actual.read(n)).hexdigest()} for n in actual.namelist()]
  assert all(actual.read(n)==expected.read(n) for n in actual.namelist())
 return {'path':p,'status':200,'sha256':sha,'crc':'PASS','components':members}
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:result=list(pool.map(inspect,rows))
 assert len(result)==10 and sum(len(r['components']) for r in result)==47
 out={'status':'PASS','archives':10,'components':47,'files':result};(HERE/'http-result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('HTTPS_FREE_DOWNLOADS=PASS; ZIP=10; COMPONENTS=47')
