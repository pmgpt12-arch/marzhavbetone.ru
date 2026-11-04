from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
import json,hashlib
Q=Path(__file__).resolve().parents[1];R=Q.parent/'next-corrections/products-storage';ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};N='{'+ns['s']+'}';records=[]
for pp in sorted((Q/'plans').glob('*.json')):
 p=json.loads(pp.read_text());source=R/p['path'];auth=Q/'authored'/(p['issue']+'.xlsx')
 if not auth.exists():continue
 assert hashlib.sha256(source.read_bytes()).hexdigest()==p['base_sha256']
 with ZipFile(source)as z,ZipFile(auth)as a:
  parts={n:z.read(n)for n in z.namelist()};ss=[''.join(x.itertext())for x in E.fromstring(a.read('xl/sharedStrings.xml'))]if 'xl/sharedStrings.xml'in a.namelist()else[]
  sheetnames=[x.get('name')for x in E.fromstring(parts['xl/workbook.xml']).find('s:sheets',ns)];changes={}
  for e in p['edits']:changes.setdefault('xl/worksheets/sheet%d.xml'%(sheetnames.index(e['sheet'])+1),[]).append(e)
  for part,edits in changes.items():
   old=E.fromstring(parts[part]);new=E.fromstring(a.read(part))
   for e in edits:
    ref=e['cell'];c=old.find(f'.//s:c[@r="{ref}"]',ns);ac=new.find(f'.//s:c[@r="{ref}"]',ns);assert ac is not None,(p['issue'],ref)
    if c is None:
     row=old.find(f's:sheetData/s:row[@r="{int("".join(filter(str.isdigit,ref)))}"]',ns);assert row is not None,(p['issue'],ref,'row missing');c=E.SubElement(row,N+'c',r=ref)
    style=c.get('s');c.clear();c.set('r',ref)
    if style:c.set('s',style)
    v=e['value']
    if isinstance(v,str)and v.startswith('='):
     af=ac.findtext('s:f',namespaces=ns);assert af is not None and af.lstrip('=')==v[1:],(p['issue'],ref,'AUTHORED_FORMULA_DIFF',af,v)
     E.SubElement(c,N+'f').text=af
     av=ac.find('s:v',ns)
     if av is not None:c.append(deepcopy(av))
     if ac.get('t'):c.set('t',ac.get('t'))
    else:
     txt=ss[int(ac.findtext('s:v',namespaces=ns))]if ac.get('t')=='s'else ''.join(ac.xpath('.//s:t/text()',namespaces=ns))if ac.get('t')=='inlineStr'else ac.findtext('s:v',namespaces=ns)
     assert txt==v,(p['issue'],ref,'AUTHORED_TEXT_DIFF',txt,v)
     c.set('t','inlineStr');E.SubElement(E.SubElement(c,N+'is'),N+'t').text=txt
   parts[part]=E.tostring(old,encoding='utf-8',xml_declaration=True)
  target=Q/'candidates/products-storage'/p['path'];target.parent.mkdir(parents=True,exist_ok=True)
  with ZipFile(target,'w',ZIP_DEFLATED)as out:
   for info in z.infolist():out.writestr(deepcopy(info),parts[info.filename])
  with ZipFile(target)as out:
   assert out.testzip()is None
   for n in z.namelist():
    if n not in changes:assert z.read(n)==out.read(n),(p['issue'],'NON_TARGET_PART',n)
    if n.endswith(('.xml','.rels')):E.fromstring(out.read(n))
  records.append({'sku':p['sku'],'path':'products-storage/'+p['path'],'issue':p['issue'],'source_sha256':p['base_sha256'],'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(target.stat().st_size).encode()+b'\0'+target.read_bytes()).hexdigest(),'changed_parts':list(changes),'other_parts_byte_exact':True,'status':'CANDIDATE_BUILT','native_office':'BLOCKED_NO_FRESH_OFFICE_WORKER'})
  print(p['issue'],'STITCHED',flush=True)
(Q/'new-workbook-manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
