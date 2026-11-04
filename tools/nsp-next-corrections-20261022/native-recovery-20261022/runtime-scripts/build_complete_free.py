from pathlib import Path
import json,hashlib,zipfile,io,threading,urllib.request,functools
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from lxml import etree as E
Q=Path(__file__).resolve().parents[1];O=Q/'native-recovery-20261022';A=Q.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
out=O/'complete-free-candidates';out.mkdir(exist_ok=True)
wm=json.loads((O/'FREE_WORD_NATIVE_V2.json').read_text())+json.loads((O/'FREE_CONTENT_NATIVE_V2.json').read_text())
assert len(wm)==6 and all(x['status']=='PASS'for x in wm)
for x in wm:x['visual_review']='PASS_ALL_NATIVE_PAGES';x['visual_checks']=['readable text','no clipped content','no unsupported link icon','table rows and headers where applicable','form body separated from buyer guide']
(O/'FREE_WORD_EFFECTIVE_REVIEW.json').write_text(json.dumps(wm,ensure_ascii=False,indent=2))
pm=json.loads((O/'FREE_EXCEL_PRINT_V2_NATIVE.json').read_text());rm=json.loads((O/'FREE_EXCEL_PRINT_V2_REOPEN.json').read_text());assert pm['status']==rm['status']=='PASS'
sources={}
for x in json.loads((O/'FREE_CONTENT_DOCX_V2_MANIFEST.json').read_text()):sources[x['path'].split('/')[1]+'/'+Path(x['path']).name]=(O/'free-content-v2'/x['path'],x['new_sha256'])
for x in wm[:2]:sources['vozvrat-ks/'+x['file']]=(O/'additional-candidates/free/vozvrat-ks'/x['file'],x['sha256'])
for x in pm['pdfs']:
 pack='dop-raboty'if x['file'].startswith('04-')else'vozvrat-ks';sources[pack+'/'+x['file']]=(O/'free-print-v2'/x['file'],x['source_sha256'])
report=[]
for pack in ('vozvrat-ks','dop-raboty'):
 src=A/'qa/remaining-audit-20261022/free-sources/downloads'/(pack+'.zip');assert src.exists(),src
 dst=out/(pack+'.zip');members=[]
 with zipfile.ZipFile(src)as z,zipfile.ZipFile(dst,'w',compression=zipfile.ZIP_DEFLATED)as o:
  assert z.testzip()is None and len(z.namelist())==5
  for n in z.namelist():
   old=z.read(n);key=pack+'/'+n;rep=sources.get(key);data=rep[0].read_bytes()if rep else old
   if rep:assert sha(data)==rep[1]
   else:assert n=='99-chto-dalshe.pdf'
   if n.endswith(('.docx','.xlsx')):
    with zipfile.ZipFile(io.BytesIO(data))as b:
     assert b.testzip()is None
     for part in b.namelist():
      if part.endswith(('.xml','.rels')):E.fromstring(b.read(part))
     txt='\n'.join(b.read(part).decode('utf-8')for part in b.namelist()if part.endswith(('.xml','.rels')))
     assert 'marzhavbetone'not in txt.lower()and '🔗'not in txt
   o.writestr(n,data);members.append({'name':n,'base_sha256':sha(old),'sha256':sha(data),'changed':data!=old,'native_office':'PASS'if rep else'UNCHANGED_PDF_VISUALLY_REVIEWED'})
 with zipfile.ZipFile(dst)as z:assert z.testzip()is None and z.namelist()==[m['name']for m in members]
 report.append({'archive':str(dst.relative_to(O)),'sha256':sha(dst.read_bytes()),'source_sha256':sha(src.read_bytes()),'members':members,'status':'QA_CANDIDATE_NATIVE_VISUAL_PACKAGE_PASS','limits':['Only existing data rows tested: 3 additional-work rows, 5 attachment rows; extending structure not accepted by this gate.','Local HTTP byte transfer is not production delivery acceptance.','Public download switching not authorized or performed.']})
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(out)));t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
try:
 for r in report:
  with urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port)+'/'+Path(r['archive']).name,timeout=10)as response:
   data=response.read();assert response.status==200 and sha(data)==r['sha256']
  with zipfile.ZipFile(io.BytesIO(data))as z:assert z.testzip()is None and len(z.namelist())==5
  r['local_http_download']='PASS_HASH_CRC_5_MEMBERS'
finally:server.shutdown();server.server_close();t.join(timeout=2)
(O/'FREE_COMPLETE_ARCHIVES.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
