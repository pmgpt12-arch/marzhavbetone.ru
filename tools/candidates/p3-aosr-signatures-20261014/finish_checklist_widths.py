"""Second layout delta: retain sufficient width for row IDs and the status heading."""
import hashlib,io,json,shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree
ROOT=Path(__file__).resolve().parent;W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
name='01-proverochnyy-list-komplekta-ks.docx';path=ROOT/'candidate'/name
before=path.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(before)=='fbab630d202d1501191f5b82461f923af062c78614c8b4ec13609b1255565339'
history=ROOT/'rejected-layout-01';(history/'v2.docx').write_bytes(before)
shutil.copyfile(ROOT/'render-v2'/name.replace('.docx','.pdf'),history/'v2.pdf')
with ZipFile(io.BytesIO(before)) as z:
    xml=etree.fromstring(z.read('word/document.xml'));text=[x.text for x in xml.iter(W+'t')]
    for table in xml.iter(W+'tbl'):
        rows=table.findall(W+'tr');cols=len(rows[0].findall(W+'tc'))
        widths=[1.1,3.0,6.0,1.8,3.34] if cols==5 else [1.1,9.0,1.8,3.34]
        twips=[round(c/2.54*1440) for c in widths]
        assert widths[0]>=1.1 and widths[-2]>=1.8
        for col,value in zip(table.find(W+'tblGrid'),twips):col.set(W+'w',str(value))
        table.find(W+'tblPr').find(W+'tblW').set(W+'w',str(sum(twips)))
        for row in rows:
            for cell,value in zip(row.findall(W+'tc'),twips):cell.find(W+'tcPr').find(W+'tcW').set(W+'w',str(value))
    assert [x.text for x in xml.iter(W+'t')]==text
    buffer=io.BytesIO()
    with ZipFile(buffer,'w',ZIP_DEFLATED) as dest:
        for item in z.infolist():dest.writestr(item,etree.tostring(xml,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
after=buffer.getvalue();path.write_bytes(after)
result={'id':'P3-01-LABEL-WIDTH-RECOVERY','input_sha256':sha(before),'output_sha256':sha(after),'observed_v2':'Instruction cells fixed, but row identifiers and status heading wrapped. All three pages inspected; not accepted.','minimal_fix':'Number 1.1 cm and status 1.8 cm; instruction remains 9.0 cm in four-column tables; no text change.','gate':'Minimum width plus all-page visual inspection; no row splits, repeated headers.','unchanged_text':True,'native_word':'NOT_RUN','visual_after':'PENDING','release':'HOLD'}
(ROOT/'layout-recovery-v3.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
