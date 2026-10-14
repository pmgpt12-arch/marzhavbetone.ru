"""Repair the observed P3-01 table-width/row-splitting defect, text unchanged."""
import hashlib,io,json,shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree
ROOT=Path(__file__).resolve().parent
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
name='01-proverochnyy-list-komplekta-ks.docx'
source=ROOT/'candidate'/name
before=source.read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(before)=='873aa2144b5a142817bae487b089e4f9b46975a46237307a4a3590cad39d8efd','Layout input drift'
history=ROOT/'rejected-layout-01';history.mkdir(exist_ok=True)
(history/name).write_bytes(before)
shutil.copyfile(ROOT/'render'/(Path(name).stem+'.pdf'),history/(Path(name).stem+'.pdf'))
shutil.copyfile(ROOT/'render-index.json',history/'render-index-v1.json')
with ZipFile(io.BytesIO(before)) as z:
    xml=etree.fromstring(z.read('word/document.xml'))
    texts=[n.text for n in xml.iter(W+'t')]
    tables=list(xml.iter(W+'tbl'));assert len(tables)==5
    for table in tables:
        rows=table.findall(W+'tr');cols=len(rows[0].findall(W+'tc'))
        widths=[.7,2.65,6.4,1.25,4.24] if cols==5 else [.7,9.05,1.25,4.24]
        assert len(widths)==cols
        twips=[round(c/2.54*1440) for c in widths]
        props=table.find(W+'tblPr')
        if props is None:props=etree.Element(W+'tblPr');table.insert(0,props)
        layout=props.find(W+'tblLayout')
        if layout is None:layout=etree.SubElement(props,W+'tblLayout')
        layout.set(W+'type','fixed')
        width=props.find(W+'tblW')
        if width is None:width=etree.SubElement(props,W+'tblW')
        width.set(W+'type','dxa');width.set(W+'w',str(sum(twips)))
        grid=table.find(W+'tblGrid');assert grid is not None
        for child in list(grid):grid.remove(child)
        for val in twips:etree.SubElement(grid,W+'gridCol').set(W+'w',str(val))
        for rindex,row in enumerate(rows):
            rp=row.find(W+'trPr')
            if rp is None:rp=etree.Element(W+'trPr');row.insert(0,rp)
            if rp.find(W+'cantSplit') is None:etree.SubElement(rp,W+'cantSplit')
            if rindex==0 and rp.find(W+'tblHeader') is None:etree.SubElement(rp,W+'tblHeader')
            for cell,val in zip(row.findall(W+'tc'),twips):
                cp=cell.find(W+'tcPr')
                if cp is None:cp=etree.Element(W+'tcPr');cell.insert(0,cp)
                cw=cp.find(W+'tcW')
                if cw is None:cw=etree.SubElement(cp,W+'tcW')
                cw.set(W+'type','dxa');cw.set(W+'w',str(val))
    assert [n.text for n in xml.iter(W+'t')]==texts
    buffer=io.BytesIO()
    with ZipFile(buffer,'w',ZIP_DEFLATED) as dest:
        for item in z.infolist():dest.writestr(item,etree.tostring(xml,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
after=buffer.getvalue()
with ZipFile(io.BytesIO(before)) as a,ZipFile(io.BytesIO(after)) as b:
    changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
    assert changed==['word/document.xml'] and b.testzip() is None
source.write_bytes(after)
result={'id':'P3-01-TABLE-LAYOUT-RECOVERY-20261014','class':'EQUAL_WIDTH_TABLE_WITH_LONG_INSTRUCTIONS','observed':'Narrow instruction cells break words; row 5.2 split between pages 3 and 4. Four pages reviewed.','root_cause':'Source gives number/status and long instruction equal widths; no row keep-together. Longer corrected text exposes the existing geometry defect.','rule':'Allocate widths by column role; prohibit row splitting; repeat table headers and inspect every changed page.','input_sha256':sha(before),'output_sha256':sha(after),'unchanged_text':True,'only_changed_parts':changed,'row_keep_applied':sum(len(t.findall(W+'tr')) for t in tables),'header_repeat_applied':5,'visual_after':'PENDING','native_word':'NOT_RUN','independent_review':'PENDING','release':'HOLD'}
(ROOT/'layout-recovery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
