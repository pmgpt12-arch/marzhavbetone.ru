from pathlib import Path
import json,hashlib,zipfile,copy
from lxml import etree as E
Q=Path(__file__).resolve().parents[1];O=Q/'native-recovery-20261022';ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+ns['w']+'}'
rows=json.loads((O/'FREE_CONTENT_DOCX_MANIFEST.json').read_text())
for i,r in enumerate(rows):
 src=O/'additional-candidates'/r['path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==r['new_sha256']
 with zipfile.ZipFile(src)as z: infos=z.infolist();parts={x.filename:z.read(x)for x in infos}
 root=E.fromstring(parts['word/document.xml'])
 for p in root.findall('.//w:body/w:p',ns):
  txt=''.join(p.itertext()) if False else ''.join(p.xpath('.//w:t/text()',namespaces=ns))
  if txt in ('Как применять внутренние сроки','Развилка по дополнительным работам') and i<3:
   pp=p.find(W+'pPr')
   if pp is None:pp=E.Element(W+'pPr');p.insert(0,pp)
   if pp.find(W+'pageBreakBefore')is None:E.SubElement(pp,W+'pageBreakBefore')
 changes={}
 if i==2:
  changes={
   "Принимать устные обещания 'потом все подпишем'":"Не принимайте устные обещания 'потом все подпишем' как достаточное согласование объёма, цены и срока.",
   "Работать 'в надежде' - надежда не является доказательством в суде":"До начала работ сохраните доказательства поручения и согласования; одной надежды на последующую оплату недостаточно.",
   "Без подтверждения работы не начинаю.":"До начала работ согласуем условия; вопрос неотложных действий проверим отдельно."
  }
 if i==3:changes={"М.П.":"[Печать — если применяется]"}
 for a,b in changes.items():
  found=0
  for p in root.findall('.//w:p',ns):
   ts=p.findall('.//w:t',ns);txt=''.join(t.text or ''for t in ts)
   if a in txt:
    nt=txt.replace(a,b);assert ts;ts[0].text=nt
    for t in ts[1:]:t.text=''
    found+=1
  assert found==1,(a,found)
 parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
 dst=O/'free-content-v2'/r['path'];dst.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(dst,'w')as z:
  for info in infos:z.writestr(info,parts[info.filename])
 with zipfile.ZipFile(src)as a,zipfile.ZipFile(dst)as b:
  assert all(a.read(x)==b.read(x)for x in a.namelist()if x!='word/document.xml')
 r['previous_sha256']=r['new_sha256'];r['new_sha256']=hashlib.sha256(dst.read_bytes()).hexdigest();r['native_office']='PENDING';r['visual_revision']='Explicit guide page break; corrected imperative list; conditional seal.'
(O/'FREE_CONTENT_DOCX_V2_MANIFEST.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
s=(Q/'scripts/native_free_content.py').read_text()
for a,b in {'nsp-free-content-docx-20261022':'nsp-free-content-v2-20261022','FREE_CONTENT_DOCX_MANIFEST.json':'FREE_CONTENT_DOCX_V2_MANIFEST.json',"'additional-candidates'":"'free-content-v2'","tag='fc'":"tag='fg'",'visual-free-content':'visual-free-content-v2','FREE_CONTENT_NATIVE.json':'FREE_CONTENT_NATIVE_V2.json'}.items():
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
compile(s,'native_free_content_v2.py','exec');(Q/'scripts/native_free_content_v2.py').write_text(s)
print('PREPARED_V2',[(r['path'],r['new_sha256'])for r in rows])