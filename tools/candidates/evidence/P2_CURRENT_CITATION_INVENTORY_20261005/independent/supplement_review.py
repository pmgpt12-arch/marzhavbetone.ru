from pathlib import Path
import json,subprocess,zipfile,io,xml.etree.ElementTree as E,hashlib,re
R=Path(__file__).resolve().parent;C=json.loads((R/'config.json').read_text());S=Path(C['author']);SITE='/home/denis/projects/marzhavbetone.ru';W={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
load=lambda p:json.loads(p.read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
frags=load(R/'independent-visible-fragments.json');inputs=load(R/'independent-input-hashes.json');author=load(S/'citation-inventory.json');extras=[];checks=[]
broad=re.compile(r'(?i)(?:\bст\.\s*\d|\bстать(?:я|и|ю|е|ей|ями)\b|\b(?:ГрК|ГК|АПК|НК|ГПК|ТК|КоАП|БК|СК|ЗК|ЖК)\b|Пленум|Федеральн\w*\s+закон\w*|\bзакон(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b|\bкодекс\w*|№\s*\d+|\b(?:ГОСТ|СП|СНиП|ФСБУ|СанПиН|ВСН|РД)\b|приказ\w*|постановлен\w*|положени\w*)')
def check(ok,label,detail):checks.append({'check':label,'pass':bool(ok),'detail':detail})
for f in inputs['buyers']:
 if not f['path'].endswith('.docx'):continue
 b=subprocess.run(['git','show',C['sha']+':'+f['path']],cwd=SITE,capture_output=True,check=True).stdout
 check(sha(b)==f['sha256'],'Supplemental DOCX exact source hash',f['path'])
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  for part in z.namelist():
   if not(part.startswith('word/') and part.endswith('.xml')) or part=='word/document.xml':continue
   root=E.fromstring(z.read(part));n=0
   for ordinal,p in enumerate(root.findall('.//w:p',W),1):
    text=''.join(t.text or '' for t in p.findall('.//w:t',W))
    if text.strip():
     n+=1;extras.append({'document':f['path'],'part':part,'physical_paragraph_ordinal':ordinal,'nonempty_paragraph_ordinal':n,'text':text,'source_sha256':f['sha256'],'broad_signals':[m.group() for m in broad.finditer(text)]})
check(len(extras)==6,'Exact six additional native XML text units',len(extras))
check(not any(x['broad_signals'] for x in extras),'All six headers/footer units without unrepresented law/standard signals',extras)
pdfchecks=[]
for d in author['pdf_limitations']:
 f=next(x for x in frags if x['path']==d['document'] and x['kind']=='pdf' and x['ordinal']==d['page'])
 ok=sha(f['text'].encode())==d['text_sha256'] and len(f['text'])==d['characters'] and len(f['text'].splitlines())==d['physical_lines'] and (not bool(f['text'].strip()))==d['text_empty']
 check(ok,'Exact independent PDF page text hash/char/line/empty binding',{'document':d['document'],'page':d['page']});pdfchecks.append({'document':d['document'],'page':d['page'],'pass':ok})
check(len(pdfchecks)==6,'All six physical pages checked',len(pdfchecks))
supp={'status':'ACCEPT_SUPPLEMENTAL_NATIVE_TEXT_SCOPE' if all(x['pass'] for x in checks) else 'FAIL','main_native_units':len(frags),'additional_native_xml_units':len(extras),'total_native_text_units':len(frags)+len(extras),'checks':checks,'pdf_page_checks':pdfchecks}
(R/'independent-extra-native-text-units.json').write_text(json.dumps(extras,ensure_ascii=False,indent=2));(R/'independent-supplemental-scope-receipt.json').write_text(json.dumps(supp,ensure_ascii=False,indent=2))
assert supp['status']=='ACCEPT_SUPPLEMENTAL_NATIVE_TEXT_SCOPE'
main=load(R/'independent-review-receipt.json');main['additional_native_xml_text_units']=len(extras);main['total_independent_native_text_units']=len(frags)+len(extras);main['supplemental_scope_receipt']='independent-supplemental-scope-receipt.json';main['supplemental_checks']=len(checks);main['supplemental_errors']=[];main['pdf_page_hashes_checked']=6
(R/'independent-review-receipt.json').write_text(json.dumps(main,ensure_ascii=False,indent=2))
(R/'independent-review-report.md').write_text('# Independent P2 factual citation inventory review\n\n'+json.dumps(main,ensure_ascii=False,indent=2)+'\n\n444 native body/cell/formula/TXT/PDF-page units plus six separately extracted header/footer units cover all 450 text units. No extra law/standard signal in those six units. All six PDF page-text hashes/character/line counts independently match frozen map metadata. Generic Приказ and Заключительные положения are raw markers, not identified norms.\n')
print(json.dumps({'status':supp['status'],'total_units':supp['total_native_text_units'],'supplemental_checks':len(checks),'errors':[]},ensure_ascii=False))
