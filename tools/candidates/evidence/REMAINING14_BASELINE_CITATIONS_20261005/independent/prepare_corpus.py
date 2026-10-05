from pathlib import Path
import json,hashlib,subprocess,zipfile,io,xml.etree.ElementTree as E,re,posixpath,collections,time
R=Path(__file__).resolve().parent;SITE='/home/denis/projects/marzhavbetone.ru';plan=json.loads((R/'source-plan.json').read_text());bindings=json.loads((R/'source-bindings.json').read_text());SHA=plan['source_sha'];started=time.monotonic()
def dump(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def digest(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.run(['git',*a],cwd=SITE,capture_output=True,check=True,timeout=10).stdout
wn={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};sn={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
broad=re.compile(r'(?i)(?:\bст\.\s*\d|\bстать(?:я|и|ю|е|ей|ями)\b|\b(?:ГрК|ГК|АПК|НК|ГПК|ТК|КоАП|БК|СК|ЗК|ЖК)\b|Пленум\w*|Верховн\w*\s+суд\w*|Федеральн\w*\s+закон(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b|\bзакон(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b|\bкодекс\w*|№\s*\d+(?:[./–-]\d+)*(?:/[A-Za-zА-Яа-я]+)?|\d+\s*[-–]\s*ФЗ\b|\b(?:ГОСТ|СП|СНиП|ФСБУ|СанПиН|СН|ВСН|РД)\b|\bприказ\w*|\bпостановлен\w*|\bположени\w*|Минстро\w*|Ростехнадзор\w*)')
def local(t):return t.rsplit('}',1)[-1]
def paths(root):
 out={}
 def walk(node,p):
  out[id(node)]=p;counts=collections.Counter()
  for child in node:
   name=local(child.tag);counts[name]+=1;walk(child,p+'/'+name+'['+str(counts[name])+']')
 walk(root,'/'+local(root.tag));return out
units={};corpus={};checks=[];pdfcommands=[];pins=[]
def check(ok,label,detail=None):
 checks.append({'check':label,'pass':bool(ok),'detail':detail})
 if not ok:raise AssertionError((label,detail))
(R/'pdf').mkdir(exist_ok=True);(R/'corpus').mkdir(exist_ok=True)
for b in bindings:
 content=git('show',SHA+':'+b['path']);h=digest(content);blob=git('rev-parse',SHA+':'+b['path']).decode().strip()
 check(h==b['sha256'] and len(content)==b['size'] and blob==b['git_blob'],'Manifest exact sourcehash/size/blob per module/path',{'sku':b['sku'],'path':b['path']})
 pins.append({'sku':b['sku'],'path':b['path'],'source_sha':SHA,'sha256':h,'size':len(content),'git_blob':blob})
 ext=Path(b['path']).suffix.lower()
 if h in corpus:
  check(corpus[h]['suffix']==ext,'FullSHA dedup suffix/nativecontext exact',h);continue
 us=[];extra=[];meta={'sha256':h,'suffix':ext,'source_reference_path':b['path'],'limitation':[]}
 def add(kind,text,**loc):
  if text is not None and str(text).strip():
   text=str(text);us.append({'kind':kind,'location':loc,'text':text,'text_sha256':digest(text.encode()),'broad_tokens':[{'token':m.group(),'span':[m.start(),m.end()]} for m in broad.finditer(text)]})
 if ext=='.docx':
  with zipfile.ZipFile(io.BytesIO(content)) as z:
   meta['media_parts']=[x for x in z.namelist() if x.startswith('word/media/')]
   if meta['media_parts']:meta['limitation'].append('Embedded image/media contents not OCR-extracted or visually reviewed')
   for part in z.namelist():
    if part.startswith('word/') and part.endswith('.xml'):
     root=E.fromstring(z.read(part));pm=paths(root);n=0
     for i,p in enumerate(root.findall('.//w:p',wn),1):
      text=''.join(t.text or '' for t in p.findall('.//w:t',wn))
      if text.strip():n+=1;add('docx_paragraph',text,part=part,xml_path=pm[id(p)],global_paragraph_ordinal_including_empty=i,nonempty_paragraph_ordinal=n)
     for node in root.iter():
      if local(node.tag) in ['instrText','delText'] and broad.search(node.text or ''):extra.append({'kind':'DOCX_NATIVE_NONVISIBLE_TEXT_SIGNAL','part':part,'xml_path':pm[id(node)],'text':node.text})
    elif part.startswith('docProps/') and part.endswith('.xml'):
     root=E.fromstring(z.read(part));pm=paths(root)
     for node in root.iter():
      if node.text and node.text.strip() and not len(node):add('native_xml_leaf',node.text,part=part,xml_path=pm[id(node)],field=local(node.tag))
 elif ext=='.xlsx':
  with zipfile.ZipFile(io.BytesIO(content)) as z:
   meta['media_parts']=[x for x in z.namelist() if x.startswith('xl/media/')]
   if meta['media_parts']:meta['limitation'].append('Embedded image/media contents not OCR-extracted or visually reviewed')
   shared=[]
   if 'xl/sharedStrings.xml' in z.namelist():shared=[''.join(t.text or '' for t in si.findall('.//s:t',sn)) for si in E.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',sn)]
   rel={x.attrib['Id']:x.attrib['Target'] for x in E.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
   for sheet in E.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',sn):
    target=rel[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']];part=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target);root=E.fromstring(z.read(part));pm=paths(root)
    for c in root.findall('.//s:c',sn):
     typ=c.attrib.get('t','n');v=c.find('s:v',sn);f=c.find('s:f',sn);text=(v.text or '') if v is not None else ''
     if typ=='s':text=shared[int(text)] if text else ''
     elif typ=='inlineStr':text=''.join(t.text or '' for t in c.findall('.//s:t',sn));typ='s'
     base={'sheet':sheet.attrib['name'],'cell':c.attrib['r'],'part':part,'xml_path':pm[id(c)],'data_type':typ}
     if f is not None:add('xlsx_cell','='+(f.text or ''),**{**base,'value_mode':'formula','data_type':'f'});add('xlsx_cell',text,**{**base,'value_mode':'cached_value'})
     else:add('xlsx_cell',text,**{**base,'value_mode':'stored_value'})
    for node in root.iter():
     if local(node.tag) in ['oddHeader','evenHeader','firstHeader','oddFooter','evenFooter','firstFooter','formula1','formula2']:
      add('native_xml_leaf',node.text,part=part,xml_path=pm[id(node)],sheet=sheet.attrib['name'],field=local(node.tag))
   for part in z.namelist():
    if part.startswith('xl/') and part.endswith('.xml') and ('comment' in part.lower() or 'drawing' in part.lower()):
     root=E.fromstring(z.read(part));pm=paths(root)
     for node in root.iter():
      if local(node.tag)=='comment':add('xlsx_comment',''.join(t.text or '' for t in node.iter() if local(t.tag)=='t'),part=part,xml_path=pm[id(node)],cell=node.attrib.get('ref'))
      elif local(node.tag)=='p' and 'drawing' in part.lower():add('native_xml_leaf',''.join(t.text or '' for t in node.iter() if local(t.tag)=='t'),part=part,xml_path=pm[id(node)],field='drawing_paragraph')
    elif part.startswith('docProps/') and part.endswith('.xml'):
     root=E.fromstring(z.read(part));pm=paths(root)
     for node in root.iter():
      if node.text and node.text.strip() and not len(node):add('native_xml_leaf',node.text,part=part,xml_path=pm[id(node)],field=local(node.tag))
 elif ext=='.txt':
  n=0
  for i,text in enumerate(content.decode('utf-8-sig').splitlines(),1):
   if text.strip():n+=1;add('txt_line',text,physical_line=i,nonempty_line=n)
 elif ext=='.pdf':
  p=R/'pdf'/(h+'.pdf');p.write_bytes(content);out=p.with_suffix('.txt');cmd=['pdftotext','-layout','-enc','UTF-8',str(p),str(out)];result=subprocess.run(cmd,capture_output=True,check=True,timeout=15);pdfcommands.append({'sha256':h,'command':cmd,'returncode':result.returncode})
  raw=out.read_bytes();pages=raw.decode('utf-8').split('\f')
  if pages[-1]=='':pages.pop()
  info=subprocess.run(['pdfinfo',str(p)],capture_output=True,text=True,check=True,timeout=10).stdout;num=int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1]);check(len(pages)==num,'All physical PDF pages text extracted',h)
  images=subprocess.run(['pdfimages','-list',str(p)],capture_output=True,text=True,check=True,timeout=10).stdout;imrows=[x for x in images.splitlines() if re.match(r'^\s*\d+\s+\d+',x)]
  meta.update({'physical_pages':num,'raw_text_sha256':digest(raw),'raw_text_path':str(out),'image_rows':len(imrows),'pages':[]})
  meta['limitation'].append('Exact PDF text layer only; no image OCR or visual layout/reading order acceptance')
  for page,text in enumerate(pages,1):
   meta['pages'].append({'physical_page':page,'characters':len(text),'lines':len(text.splitlines()),'text_sha256':digest(text.encode()),'empty_or_image_only_text_scope':not bool(text.strip())})
   # Empty page kept explicitly even with no paragraph text unit.
   if text.strip():add('pdf_page',text,physical_page=page,extraction='pdftotext -layout -enc UTF-8')
 else:raise AssertionError('Unsupported '+ext)
 meta['units']=len(us);meta['extra_native_signals']=extra;corpus[h]=meta;units[h]=us;dump('corpus/'+h+'.json',us)
 if time.monotonic()-started>110:raise TimeoutError('Independent bounded source prep >110s')
for b in bindings:check(digest(git('show',SHA+':'+b['path']))==b['sha256'],'Exact source unchanged after independent prep',{'sku':b['sku'],'path':b['path']})
summary={'status':'VERIFIED_INDEPENDENT_BASELINE_CORPUS_PREP_ONLY','source_sha':SHA,'module_count':14,'input_bindings':len(bindings),'unique_inputs':len(corpus),'unique_native_text_units':sum(len(x) for x in units.values()),'unique_broad_signal_units':sum(bool(u['broad_tokens']) for us in units.values() for u in us),'unique_broad_tokens':sum(len(u['broad_tokens']) for us in units.values() for u in us),'PDF_unique_inputs':len(pdfcommands),'PDF_extraction_calls_once_each':len(pdfcommands),'PDF_physical_pages':sum(x.get('physical_pages',0) for x in corpus.values()),'checks':len(checks),'errors':[],'elapsed_seconds':time.monotonic()-started,'scope':'Cached configured dry-eligible source baseline only; not actual approved PHP delivery membership, current buyer repackaging, legal/currentness/human/release approval. Author maps NOT_YET_REVIEWED.','model_calls':0,'USD':0}
dump('independent-source-hash-pins.json',pins);dump('independent-corpus-index.json',corpus);dump('independent-pdf-execution.json',pdfcommands);dump('independent-prep-checks.json',checks);dump('independent-prep-receipt.json',summary);print(json.dumps(summary,ensure_ascii=False))
