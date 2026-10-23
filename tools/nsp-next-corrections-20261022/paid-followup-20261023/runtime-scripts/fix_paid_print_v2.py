from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from copy import deepcopy
import json,hashlib
Q=Path(__file__).resolve().parents[1];O=Q/'native-recovery-20261022';P=Q/'paid-followup-20261023';D=P/'paid-print-v2';D.mkdir(exist_ok=True)
N='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}';ns={'s':N[1:-1]};sha=lambda b:hashlib.sha256(b).hexdigest()
plans={2:[('N',158,6),('I',28,None),('N',28,5)],3:[('L',158,6),('I',28,None),('I',28,None),('L',28,5)],4:[('I',28,None),('U',208,6),('J',65,4),('I',28,None),('I',28,None),('U',28,5)]}
order='sheetPr dimension sheetViews sheetFormatPr cols sheetData sheetCalcPr sheetProtection protectedRanges scenarios autoFilter sortState dataConsolidate customSheetViews mergeCells phoneticPr conditionalFormatting dataValidations hyperlinks printOptions pageMargins pageSetup headerFooter rowBreaks colBreaks customProperties cellWatches ignoredErrors smartTags drawing legacyDrawing legacyDrawingHF picture oleObjects controls webPublishItems tableParts extLst'.split()
def add(root,node):
 rank=order.index(E.QName(node).localname)
 idx=next((i for i,n in enumerate(root)if E.QName(n).localname in order and order.index(E.QName(n).localname)>rank),len(root));root.insert(idx,node)
records=[]
for job,plan in plans.items():
 fdir=O/'frozen-inputs'/('nsp-next-excel-'+str(job)+'-20261022');src=next(fdir.glob('*.xlsx'));dst=D/src.name
 with ZipFile(src)as z:
  parts={i.filename:z.read(i)for i in z.infolist()};w=E.fromstring(parts['xl/workbook.xml']);bw=deepcopy(w);sheets=w.find(N+'sheets');assert len(sheets)==len(plan)
  names=w.find(N+'definedNames');had_names=names is not None
  if names is None:
   names=E.Element(N+'definedNames');idx=list(w).index(sheets);w.insert(idx+1,names)
  updates={};srows=[];added=[]
  for idx,((lastcol,lastrow,title),sh)in enumerate(zip(plan,sheets)):
   part='xl/worksheets/sheet'+str(idx+1)+'.xml';s=E.fromstring(parts[part]);bs=deepcopy(s)
   assert s.find(N+'pageSetup')is None
   sp=s.find(N+'sheetPr')
   if sp is None:sp=E.Element(N+'sheetPr');add(s,sp)
   assert sp.find(N+'pageSetUpPr')is None
   E.SubElement(sp,N+'pageSetUpPr',fitToPage='1')
   margins=s.find(N+'pageMargins')
   if margins is None:margins=E.Element(N+'pageMargins');add(s,margins)
   margins.attrib.update({'left':'0.3','right':'0.3','top':'0.4','bottom':'0.4','header':'0.2','footer':'0.2'})
   paper='8'if lastcol in ('L','N','U')else'9'
   add(s,E.Element(N+'pageSetup',paperSize=paper,orientation='landscape',fitToWidth='1',fitToHeight='0'))
   area="'"+sh.get('name').replace("'","''")+"'!$A$1:$"+lastcol+'$'+str(lastrow)
   matches=[n for n in names if n.get('name')=='_xlnm.Print_Area'and n.get('localSheetId')==str(idx)]
   if matches:assert len(matches)==1 and matches[0].text==area
   else:n=E.SubElement(names,N+'definedName',name='_xlnm.Print_Area',localSheetId=str(idx));n.text=area;added.append(n)
   if title is not None:
    n=E.SubElement(names,N+'definedName',name='_xlnm.Print_Titles',localSheetId=str(idx));n.text="'"+sh.get('name').replace("'","''")+"'!$"+str(title)+':$'+str(title);added.append(n)
   # Inverse patch gate: all cells/formulas/styles/validation/merges and other sheet data exact.
   clean=deepcopy(s)
   for name in ('pageSetup','pageMargins'):
    v=clean.find(N+name)
    if v is not None:clean.remove(v)
    v=bs.find(N+name)
    if v is not None:add(clean,deepcopy(v))
   csp=clean.find(N+'sheetPr');csp.remove(csp.find(N+'pageSetUpPr'))
   if bs.find(N+'sheetPr')is None:clean.remove(csp)
   assert E.tostring(clean,method='c14n')==E.tostring(bs,method='c14n'),(job,sh.get('name'))
   updates[part]=E.tostring(s,encoding='UTF-8',xml_declaration=True)
   srows.append({'sheet':sh.get('name'),'area':area,'paper':'A3'if paper=='8'else'A4','orientation':'landscape','repeat_header_row':title,'fit_width':1,'fit_height':0})
  cw=deepcopy(w);cn=cw.find(N+'definedNames')
  # Remove only newly added printing names, preserving original defined names.
  for n in list(cn):
   if not any(E.tostring(n)==E.tostring(b)for b in (bw.find(N+'definedNames')or[])):cn.remove(n)
  if not had_names:cw.remove(cn)
  assert E.tostring(cw,method='c14n')==E.tostring(bw,method='c14n')
  updates['xl/workbook.xml']=E.tostring(w,encoding='UTF-8',xml_declaration=True)
  with ZipFile(dst,'w')as out:
   for i in z.infolist():out.writestr(i,updates.get(i.filename,parts[i.filename]))
  with ZipFile(dst)as out:
   assert out.testzip()is None
   assert all(out.read(n)==parts[n]for n in parts if n not in updates)
   for n in out.namelist():
    if n.endswith(('.xml','.rels')):E.fromstring(out.read(n))
 records.append({'source_job':job,'file':src.name,'source_sha256':sha(src.read_bytes()),'new_sha256':sha(dst.read_bytes()),'sheets':srows,'cell_formula_style_validation_and_other_parts_unchanged':True,'status':'CANDIDATE_NATIVE_VISUAL_PENDING','tool_limit':'No documented print/pageSetup authoring API; bounded native metadata-only patch with inverse XML equality gate'})
(D/'MANIFEST.json').write_text(json.dumps(records,ensure_ascii=False,indent=2));print(json.dumps(records,ensure_ascii=False),flush=True)
