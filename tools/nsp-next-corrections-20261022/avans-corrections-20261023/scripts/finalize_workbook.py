from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
from lxml import etree as E
import json,hashlib
B=Path(__file__).resolve().parent;P=B/'output/02-reestr-izyatiy-po-obektu.xlsx'
M='http://schemas.openxmlformats.org/spreadsheetml/2006/main';ns={'m':M};tag=lambda n:'{'+M+'}'+n
sha=lambda b:hashlib.sha256(b).hexdigest()
before=P.read_bytes();(B/'proof/authored-before-metadata.xlsx').write_bytes(before)
with ZipFile(P)as z:parts={n:z.read(n)for n in z.namelist()};infos=[deepcopy(x)for x in z.infolist()]
styles=E.fromstring(parts['xl/styles.xml']);xfs=styles.find(tag('cellXfs'));original_xfs=[E.tostring(x,method='c14n')for x in xfs];unlocked={}
def unlock(style):
 if style in unlocked:return unlocked[style]
 e=deepcopy(xfs[style]);p=e.find(tag('protection'))
 if p is None:p=E.SubElement(e,tag('protection'))
 p.set('locked','0');e.set('applyProtection','1');idx=len(xfs);xfs.append(e);unlocked[style]=idx;return idx
book=E.fromstring(parts['xl/workbook.xml']);names=book.find(tag('definedNames'))
if names is None:names=E.SubElement(book,tag('definedNames'))
for n in list(names):
 if n.get('name')in ['_xlnm.Print_Area','_xlnm.Print_Titles']:names.remove(n)
order=['sheetPr','dimension','sheetViews','sheetFormatPr','cols','sheetData','sheetCalcPr','sheetProtection','protectedRanges','scenarios','autoFilter','sortState','dataConsolidate','customSheetViews','mergeCells','phoneticPr','conditionalFormatting','dataValidations','hyperlinks','printOptions','pageMargins','pageSetup','headerFooter','rowBreaks','colBreaks','customProperties','cellWatches','ignoredErrors','smartTags','drawing','legacyDrawing','legacyDrawingHF','picture','oleObjects','controls','webPublishItems','tableParts','extLst']
def insert(root,node):
 root.append(node);children=list(root)
 children.sort(key=lambda x:order.index(E.QName(x).localname)if E.QName(x).localname in order else len(order))
 for x in list(root):root.remove(x)
 for x in children:root.append(x)
def replace_node(root,n,attrs):
 for e in root.findall(tag(n)):root.remove(e)
 e=E.Element(tag(n),**attrs);insert(root,e);return e
changed=[]
for i,(sheet_name,area,paper,orientation)in enumerate([('Изъятия','$A$1:$G$19','8','landscape'),('Как считать','$A$1:$C$14','9','portrait')],1):
 path=f'xl/worksheets/sheet{i}.xml';root=E.fromstring(parts[path]);oldroot=deepcopy(root)
 unlocked_cells={}
 if i==1:
  for c in root.findall('.//m:sheetData/m:row/m:c',ns):
   a=c.get('r');num=int(''.join(x for x in a if x.isdigit()))
   if a=='D2'or (a[0]in 'BDG'and a[1:].isdigit()and 4<=num<=11):
    old=c.get('s','0');unlocked_cells[a]=old;c.set('s',str(unlock(int(old))))
  assert set(unlocked_cells)=={'D2'}|{f'{c}{r}'for c in 'BDG'for r in range(4,12)},unlocked_cells
 replace_node(root,'sheetProtection',{'sheet':'1','objects':'1','scenarios':'1'})
 if i==1:
  dv=replace_node(root,'dataValidations',{'count':'2'})
  for addr,formula in [('D2','OR(ISBLANK(D2),AND(ISNUMBER(D2),D2>=1))'),('D4:D11','OR(ISBLANK(D4),AND(ISNUMBER(D4),D4>=0))')]:
   v=E.SubElement(dv,tag('dataValidation'),type='custom',allowBlank='1',showErrorMessage='1',errorStyle='stop',sqref=addr,errorTitle='Проверьте значение',error='Введите число. Суммы не могут быть отрицательными.')
   E.SubElement(v,tag('formula1')).text=formula
 margins=replace_node(root,'pageMargins',{'left':'0.3','right':'0.3','top':'0.3','bottom':'0.3','header':'0.1','footer':'0.1'})
 setup=replace_node(root,'pageSetup',{'paperSize':paper,'orientation':orientation,'fitToWidth':'1','fitToHeight':'0'})
 prop=root.find(tag('sheetPr'))
 if prop is None:prop=E.Element(tag('sheetPr'));insert(root,prop)
 fit=prop.find(tag('pageSetUpPr'))
 if fit is None:fit=E.SubElement(prop,tag('pageSetUpPr'))
 fit.set('fitToPage','1')
 for kind,ref in [('Print_Area',area),('Print_Titles','$3:$3')]:E.SubElement(names,tag('definedName'),name='_xlnm.'+kind,localSheetId=str(i-1)).text="'"+sheet_name+"'!"+ref
 # Metadata gate: every source cell's value/formula and its address are exact.
 def contents(r):
  out={}
  for c in r.findall('.//m:sheetData/m:row/m:c',ns):
   cp=deepcopy(c);cp.attrib.pop('s',None);out[c.get('r')]=E.tostring(cp,method='c14n')
  return out
 assert contents(root)==contents(oldroot),path
 for c in root.findall('.//m:sheetData/m:row/m:c',ns):
  old=oldroot.find('.//m:c[@r="'+c.get('r')+'"]',ns)
  if c.get('r')not in unlocked_cells:assert c.get('s')==old.get('s')
 parts[path]=E.tostring(root,encoding='UTF-8',xml_declaration=True)
 changed.append({'sheet':sheet_name,'print_area':area,'paper':paper,'orientation':orientation,'unlocked_cells':sorted(unlocked_cells),'cells_and_formulas_unchanged':True})
assert all(E.tostring(xfs[i],method='c14n')==x for i,x in enumerate(original_xfs))
xfs.set('count',str(len(xfs)));parts['xl/styles.xml']=E.tostring(styles,encoding='UTF-8',xml_declaration=True)
calc=book.find(tag('calcPr'))
if calc is not None:calc.set('fullCalcOnLoad','1')
parts['xl/workbook.xml']=E.tostring(book,encoding='UTF-8',xml_declaration=True)
tmp=P.with_suffix('.tmp')
with ZipFile(tmp,'w')as z:
 for info in infos:z.writestr(info,parts[info.filename])
with ZipFile(tmp)as z:assert z.testzip()is None
tmp.replace(P)
(B/'proof/XLSX_METADATA_GATE.json').write_text(json.dumps({'scope':'Only file-level input protection, validation and print metadata after Artifact Tool authoring. Public API protection lookup matched no entries; no application settings changed.','before_sha256':sha(before),'after_sha256':sha(P.read_bytes()),'sheets':changed,'native_acceptance':'PENDING'},ensure_ascii=False,indent=2))
print('METADATA_GATE_PASS',sha(P.read_bytes()))
