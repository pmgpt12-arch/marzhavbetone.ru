"""Overlay artifact-tool-authored cells/features onto the accepted print package.

No spreadsheet authoring library is used here. Unchanged package parts remain
byte-identical; original cell styles, column widths and print setup are retained.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
import hashlib, json
BASE = Path(__file__).parent
NS = {'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
Q = '{'+NS['x']+'}'
with ZipFile(BASE/'print-source.xlsx') as z:
    parts={n:z.read(n) for n in z.namelist()}
with ZipFile(BASE/'authored.xlsx') as z:
    authored={n:z.read(n) for n in z.namelist()}
strings=[]
if 'xl/sharedStrings.xml' in authored:
    strings=[''.join(e.itertext()) for e in E.fromstring(authored['xl/sharedStrings.xml'])]
changed=[]
for sn, addresses in [(1,['H1','C53','C54','H54','C56','H56']),
                      (2,['A6']+[f'B{i}' for i in range(2,10)]+[f'D{i}' for i in range(1,9)])]:
    name=f'xl/worksheets/sheet{sn}.xml'
    old=E.fromstring(parts[name]); new=E.fromstring(authored[name])
    data=old.find('x:sheetData',NS)
    for addr in addresses:
        src=new.find(f'.//x:c[@r="{addr}"]',NS); assert src is not None,addr
        dst=old.find(f'.//x:c[@r="{addr}"]',NS)
        rowno=''.join(filter(str.isdigit,addr))
        row=data.find(f'x:row[@r="{rowno}"]',NS)
        if row is None: row=E.SubElement(data,Q+'row',r=rowno)
        replacement=deepcopy(src)
        replacement.attrib.pop('s',None)
        if dst is not None and dst.get('s'):replacement.set('s',dst.get('s'))
        elif sn==1 and addr=='C53':
            replacement.set('s',old.find('.//x:c[@r="C56"]',NS).get('s','0'))
        if src.get('t')=='s':
            text=strings[int(src.find('x:v',NS).text)]
            for c in list(replacement):replacement.remove(c)
            replacement.set('t','inlineStr');E.SubElement(E.SubElement(replacement,Q+'is'),Q+'t').text=text
        if dst is None:row.append(replacement)
        else:row.replace(dst,replacement)
    if sn==1:
        for tag in ['mergeCells','dataValidations']:
            feature=new.find('x:'+tag,NS);assert feature is not None,tag
            # OOXML order: merges and validations precede page settings.
            index=list(old).index(old.find('x:printOptions',NS)) if old.find('x:printOptions',NS) is not None else list(old).index(old.find('x:pageMargins',NS))
            copied=deepcopy(feature)
            if tag=='dataValidations':
                # Compatibility repair: artifact export drops the documented errorAlert.
                for rule in copied:
                    rule.set('allowBlank','1');rule.set('showErrorMessage','1');rule.set('errorStyle','stop')
                    rule.set('errorTitle','Проверьте значение')
                    rule.set('error','Выберите значение из списка; для денежной графы введите число не меньше нуля.')
            old.insert(index,copied)
    for row in data:
        ar=new.find(f'x:sheetData/x:row[@r="{row.get("r")}"]',NS)
        if ar is not None and ar.get('ht'):
            row.set('ht',ar.get('ht'));row.set('customHeight','1')
    # Cell order matters to Excel readers.
    for row in data:
        def col(c):
            n=0
            for a in ''.join(filter(str.isalpha,c.get('r'))):n=n*26+ord(a)-64
            return n
        row[:]=sorted(row,key=col)
    for tag in ['cols','pageMargins','pageSetup','printOptions','sheetPr']:
        a=E.fromstring(parts[name]).find('x:'+tag,NS);b=old.find('x:'+tag,NS)
        assert (E.tostring(a) if a is not None else None)==(E.tostring(b) if b is not None else None),tag
    parts[name]=E.tostring(old,encoding='utf-8',xml_declaration=True)
    changed.append(name)
out=BASE/'63-reestr-zatrat-po-obektu.xlsx'
with ZipFile(out,'w',ZIP_DEFLATED) as z:
    for name,content in parts.items():z.writestr(name,content)
with ZipFile(BASE/'print-source.xlsx') as z:
    identical=[n for n in z.namelist() if z.read(n)==parts[n]]
report={'status':'PASS','source_sha256':hashlib.sha256((BASE/'print-source.xlsx').read_bytes()).hexdigest(),
 'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'changed_parts':changed,
 'byte_identical_parts':identical,'cell_edits':{'sheet1':6,'sheet2':17},
 'preserved':'All original styles, column widths, source categories, print areas, repeat headers, page setup, margins and other package parts',
 'new_features':'One warning formula, five validation ranges, C53:J53 merge, validation dictionary outside print area; input row heights increased to prevent a summary-only second page; guide heights adjusted'}
(BASE/'preservation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
