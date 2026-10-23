from pathlib import Path
from lxml import etree as E
import zipfile,hashlib,json,copy,subprocess
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';src=P/'p11-remaining-sources/53-zapros-status-obekta.docx';ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+ns['w']+'}'
assert hashlib.sha256(src.read_bytes()).hexdigest()=='9a88f1f249016093415811c1bf4ec470e8ac974a00bd4c4b5391e2d2bea89182'
with zipfile.ZipFile(src)as z:infos=z.infolist();parts={i.filename:z.read(i)for i in infos}
root=E.fromstring(parts['word/document.xml']);body=root.find(W+'body');nodes=list(body)
text=lambda n:''.join(n.xpath('.//w:t/text()',namespaces=ns))
start=next(i for i,n in enumerate(nodes)if text(n).startswith('Кому:'));guide=next(i for i,n in enumerate(nodes)if text(n)=='Как пользоваться этим документом');sect=nodes[-1];assert sect.tag==W+'sectPr'
beforetexts=sorted(root.xpath('.//w:t/text()',namespaces=ns))
preface=nodes[:start];letter=nodes[start:guide];manual=nodes[guide:-1]
# Preserve every word and all runs/styles; move buyer preface behind the sendable letter.
for n in nodes[:-1]:
 for br in n.xpath('.//w:br[@w:type="page"]',namespaces=ns):br.getparent().remove(br)
 for pb in n.xpath('.//w:pageBreakBefore',namespaces=ns):pb.getparent().remove(pb)
for n in list(body):body.remove(n)
for n in letter+preface+manual+[sect]:body.append(n)
first=next(n for n in preface if n.tag==W+'p'and text(n).strip());pp=first.find(W+'pPr')
if pp is None:pp=E.Element(W+'pPr');first.insert(0,pp)
E.SubElement(pp,W+'pageBreakBefore')
assert sorted(root.xpath('.//w:t/text()',namespaces=ns))==beforetexts
assert text(next(n for n in body if text(n).strip())).startswith('Кому:')
parts['word/document.xml']=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
D=P/'p11-layout-v2';D.mkdir(exist_ok=True);dst=D/src.name
with zipfile.ZipFile(dst,'w')as z:
 for i in infos:z.writestr(i,parts[i.filename])
with zipfile.ZipFile(src)as a,zipfile.ZipFile(dst)as b:assert all(a.read(n)==b.read(n)for n in a.namelist()if n!='word/document.xml')
row={'path':src.name,'base_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'new_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'change':'Move buyer preface behind sendable letter; only page breaks and node order; all text, runs/styles and other OOXML parts preserved','visual_review':'PENDING'}
(P/'P11_LAYOUT_V2.json').write_text(json.dumps([row],ensure_ascii=False,indent=2))
out=P/'rendered-p11-layout-v2'
subprocess.run(['/home/denis/projects/nsp-audit-fixes-20261021/.render-venv/bin/python','/home/denis/projects/nsp-audit-fixes-20261021/render_docx.py',str(dst),'--output_dir',str(out),'--emit_pdf'],check=True,capture_output=True,text=True,timeout=90)
s=(Q/'scripts/native_p11_remaining.py').read_text()
for a,b in {'nsp-p11-remaining-word-20261023':'nsp-p11-letter-layout-v2-20261023','P11_REMAINING_DOCX.json':'P11_LAYOUT_V2.json',"'p11-remaining-sources'":"'p11-layout-v2'","tag='pm'":"tag='pl'",'visual-p11-remaining':'visual-p11-layout-v2','P11_REMAINING_NATIVE.json':'P11_LAYOUT_NATIVE_V2.json'}.items():
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
compile(s,'native_p11_layout_v2.py','exec');(Q/'scripts/native_p11_layout_v2.py').write_text(s)
print('P11_LAYOUT_CANDIDATE',row,flush=True)
