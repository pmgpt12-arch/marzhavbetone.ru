from pathlib import Path
import json,subprocess,zipfile,io,xml.etree.ElementTree as E,collections,hashlib,re
R=Path(__file__).resolve().parent;SITE='/home/denis/projects/marzhavbetone.ru';SHA=json.loads((R/'source-plan.json').read_text())['source_sha'];idx=json.loads((R/'independent-corpus-index.json').read_text());S='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
# Same own independent broad vocabulary from prep; no author regex executed.
text=(R/'prepare_corpus.py').read_text();start=text.index("broad=re.compile(");end=text.index("\ndef local",start);ns={'re':re};exec(text[start:end],ns);broad=ns['broad'];alladded=[];counts=[]
def local(t):return t.rsplit('}',1)[-1]
def paths(root):
 out={}
 def walk(node,p):
  out[id(node)]=p;cs=collections.Counter()
  for c in node:cs[local(c.tag)]+=1;walk(c,p+'/'+local(c.tag)+'['+str(cs[local(c.tag)])+']')
 walk(root,'/'+local(root.tag));return out
for h,meta in idx.items():
 if meta['suffix']!='.xlsx':continue
 b=subprocess.run(['git','show',SHA+':'+meta['source_reference_path']],cwd=SITE,capture_output=True,check=True).stdout;assert hashlib.sha256(b).hexdigest()==h
 units=json.loads((R/'corpus'/f'{h}.json').read_text());added=[]
 def add(kind,txt,**loc):
  if txt and str(txt).strip():
   txt=str(txt);added.append({'kind':kind,'location':loc,'text':txt,'text_sha256':hashlib.sha256(txt.encode()).hexdigest(),'broad_tokens':[{'token':m.group(),'span':[m.start(),m.end()]} for m in broad.finditer(txt)]})
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  book=E.fromstring(z.read('xl/workbook.xml'));pm=paths(book)
  for sheet in book.iter(S+'sheet'):add('native_xml_attribute',sheet.attrib['name'],part='xl/workbook.xml',xml_path=pm[id(sheet)],attribute='name',sheet=sheet.attrib['name'])
  for node in book.iter(S+'definedName'):add('native_xml_leaf',node.text,part='xl/workbook.xml',xml_path=pm[id(node)],field='definedName',name=node.attrib.get('name'))
  for part in z.namelist():
   if part.startswith('xl/worksheets/') and part.endswith('.xml'):
    root=E.fromstring(z.read(part));pm=paths(root)
    for node in root.iter(S+'dataValidation'):
     for attr in ['promptTitle','prompt','errorTitle','error']:add('native_xml_attribute',node.attrib.get(attr),part=part,xml_path=pm[id(node)],attribute=attr,sqref=node.attrib.get('sqref'))
   elif re.fullmatch(r'xl/(?:drawings/drawing\d+|charts/chart\d+)\.xml',part):
    root=E.fromstring(z.read(part));pm=paths(root)
    for node in root.iter():
     if local(node.tag)=='t':add('native_xml_leaf',node.text,part=part,xml_path=pm[id(node)],field='t')
 existing={(u['kind'],json.dumps(u['location'],sort_keys=True),u['text']) for u in units};added=[u for u in added if (u['kind'],json.dumps(u['location'],sort_keys=True),u['text']) not in existing]
 units+=added;(R/'corpus'/f'{h}.json').write_text(json.dumps(units,ensure_ascii=False,indent=2));meta['units']=len(units);meta['supplemental_metadata_units']=len(added)
 alladded.extend({'sha256':h,**u} for u in added);counts.append({'sha256':h,'added_units':len(added),'broad_signal_units':sum(bool(u['broad_tokens']) for u in added)})
(R/'independent-corpus-index.json').write_text(json.dumps(idx,ensure_ascii=False,indent=2));(R/'independent-extra-xlsx-metadata-units.json').write_text(json.dumps(alladded,ensure_ascii=False,indent=2));summary={'status':'VERIFIED_NEW_NATIVE_METADATA_SCOPE_ONLY','XLSX_unique_inputs_inspected':len(counts),'added_units':len(alladded),'added_signal_units':sum(bool(u['broad_tokens']) for u in alladded),'no_PDF_reextraction':True,'previous_native_cell_paragraph_text_not_reextracted':True,'type':'Previously omitted sheet title/validation attribute/chart leaf/definedName fields only','details':counts};(R/'independent-extra-xlsx-metadata-receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False))
