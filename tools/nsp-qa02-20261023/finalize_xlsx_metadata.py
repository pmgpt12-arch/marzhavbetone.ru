"""Set native print, hyperlink and cell-lock metadata after Artifact Tool authoring.
No formula/value is authored by this pass. Verify cell payloads and keep an input copy.
"""
from pathlib import Path
import zipfile,copy,json,hashlib,io,xml.etree.ElementTree as E
O=Path(__file__).resolve().parent;P=O/'candidate/02-kalkulyator-sroka-oplaty.xlsx'
N='http://schemas.openxmlformats.org/spreadsheetml/2006/main';R='http://schemas.openxmlformats.org/officeDocument/2006/relationships';PK='http://schemas.openxmlformats.org/package/2006/relationships'
E.register_namespace('',N);E.register_namespace('r',R)
tag=lambda n:'{'+N+'}'+n
sha=lambda b:hashlib.sha256(b).hexdigest()
before=P.read_bytes();(O/'proof/pre-metadata.xlsx').write_bytes(before)
with zipfile.ZipFile(io.BytesIO(before))as z:parts={n:z.read(n)for n in z.namelist()};infos=z.infolist()
styles=E.fromstring(parts['xl/styles.xml']);xfs=styles.find(tag('cellXfs'));stylemap={}
def unlock(style):
    if style not in stylemap:
        xf=copy.deepcopy(xfs[int(style)]);xf.set('applyProtection','1');pr=xf.find(tag('protection'))
        if pr is None:pr=E.SubElement(xf,tag('protection'))
        pr.set('locked','0');stylemap[style]=str(len(xfs));xfs.append(xf)
    return stylemap[style]
def cellpayload(root):
    return {c.get('r'):E.tostring(c.find(tag('f')),encoding='unicode')if c.find(tag('f'))is not None else (c.get('t'),E.tostring(c.find(tag('v')),encoding='unicode')if c.find(tag('v'))is not None else E.tostring(c.find(tag('is')),encoding='unicode')if c.find(tag('is'))is not None else None)for c in root.iter(tag('c'))}
main_inputs={'B2','B3','B4','B5','B6','B9','B10','B11','B13','B14','B15','B16','B17','B18'}
specs=[('Калькулятор срока оплаты','A1:C32',9,'portrait',main_inputs),
       ('Периоды','A1:M30',8,'landscape',{'A'+str(r)for r in range(6,25)}|{c+str(r)for c in ['D','E']for r in range(5,25)}),
       ('Платежи','A1:F28',8,'landscape',{c+str(r)for c in ['A','B','C']for r in range(5,25)}),
       ('Календарь','A1:C22',9,'portrait',set())]
receipts=[]
for i,(name,area,paper,orientation,inputs)in enumerate(specs,1):
    path=f'xl/worksheets/sheet{i}.xml';root=E.fromstring(parts[path]);cells_before=cellpayload(root)
    for c in root.iter(tag('c')):
        if c.get('r')in inputs:c.set('s',unlock(c.get('s','0')))
    pr=root.find(tag('sheetPr'))
    if pr is None:pr=E.Element(tag('sheetPr'));root.insert(0,pr)
    setuppr=pr.find(tag('pageSetUpPr'))
    if setuppr is None:setuppr=E.SubElement(pr,tag('pageSetUpPr'))
    setuppr.set('fitToPage','1');setuppr.set('autoPageBreaks','0')
    # Keep schema order: protection before validations, margins and page setup.
    for n in ['sheetProtection','pageMargins','pageSetup','printOptions']:
        old=root.find(tag(n))
        if old is not None:root.remove(old)
    protected=E.Element(tag('sheetProtection'),sheet='1',objects='1',scenarios='1',selectLockedCells='0',selectUnlockedCells='0')
    after=['sheetData','sheetCalcPr'];insert_after=max(j for j,e in enumerate(root)if e.tag in [tag(n)for n in after]);root.insert(insert_after+1,protected)
    E.SubElement(root,tag('printOptions'),horizontalCentered='1')
    E.SubElement(root,tag('pageMargins'),left='0.25',right='0.25',top='0.3',bottom='0.3',header='0.1',footer='0.1')
    E.SubElement(root,tag('pageSetup'),paperSize=str(paper),orientation=orientation,fitToWidth='1',fitToHeight='1')
    assert cellpayload(root)==cells_before
    if name=='Календарь':
        links=json.loads((O/'proof/XLSX_HYPERLINKS.json').read_text())
        hp=E.Element(tag('hyperlinks'));relroot=E.Element('{'+PK+'}Relationships')
        for j,l in enumerate(links,1):
            ident='qa02link'+str(j);E.SubElement(hp,tag('hyperlink'),ref=l['cell'],attrib={'{'+R+'}id':ident})
            E.SubElement(relroot,'{'+PK+'}Relationship',Id=ident,Type=R+'/hyperlink',Target=l['url'],TargetMode='External')
        # Hyperlinks precede printOptions / margins in worksheet schema.
        root.insert(list(root).index(root.find(tag('printOptions'))),hp)
        parts[f'xl/worksheets/_rels/sheet{i}.xml.rels']=E.tostring(relroot,encoding='utf-8',xml_declaration=True)
    parts[path]=E.tostring(root,encoding='utf-8',xml_declaration=True)
    receipts.append(dict(sheet=name,print_area=area,paper=paper,orientation=orientation,input_cells=sorted(inputs),cells_formulas_values_unchanged=True,source_print='actual blank source and filled native PDFs must be reviewed'))
xfs.set('count',str(len(xfs)));parts['xl/styles.xml']=E.tostring(styles,encoding='utf-8',xml_declaration=True)
root=E.fromstring(parts['xl/workbook.xml']);names=root.find(tag('definedNames'))
if names is None:names=E.SubElement(root,tag('definedNames'))
for old in list(names):
    if old.get('name')in ['_xlnm.Print_Area','_xlnm.Print_Titles']:names.remove(old)
for i,(name,area,*_)in enumerate(specs):
    cells=area.split(':');addr=':'.join('$'+''.join(c for c in x if c.isalpha())+'$'+''.join(c for c in x if c.isdigit())for x in cells)
    E.SubElement(names,tag('definedName'),name='_xlnm.Print_Area',localSheetId=str(i)).text="'"+name+"'!"+addr
cp=root.find(tag('calcPr'))
if cp is None:cp=E.SubElement(root,tag('calcPr'))
cp.set('calcMode','auto');cp.set('fullCalcOnLoad','1');cp.set('forceFullCalc','1')
parts['xl/workbook.xml']=E.tostring(root,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(P,'w',zipfile.ZIP_DEFLATED)as z:
    for info in infos:z.writestr(info,parts.pop(info.filename))
    for n,b in parts.items():z.writestr(n,b)
with zipfile.ZipFile(P)as z:
    assert z.testzip()is None
    for n in z.namelist():
        if n.endswith(('.xml','.rels')):E.fromstring(z.read(n))
result=dict(status='METADATA_SET_NATIVE_PENDING',before_sha256=sha(before),after_sha256=sha(P.read_bytes()),sheets=receipts,scope='Only native print/protection/hyperlink metadata and input style locking; formula/value payloads unchanged',builtin_print_name_recognition='NOT_ASSUMED; verify actual exported pages')
(O/'proof/XLSX_METADATA_GATE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(result['after_sha256'])
