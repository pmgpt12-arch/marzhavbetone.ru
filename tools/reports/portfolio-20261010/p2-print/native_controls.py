"""Narrow native XLSX features requested by MB001; no values/formulas rewritten."""
import argparse, copy, hashlib, json, re, zipfile
from pathlib import Path
from lxml import etree as E
N='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
q=lambda s:f'{{{N}}}{s}'
def run(src,out):
    out.mkdir(parents=True,exist_ok=True)
    report=[]
    for filename,last,total in [('07-raschet-stoimosti.xlsx','J',104),('08-zhurnal-doprabot.xlsx','L',103)]:
        path=src/filename
        with zipfile.ZipFile(path) as z: parts={n:z.read(n) for n in z.namelist()}
        styles=E.fromstring(parts['xl/styles.xml']); xfs=styles.find(q('cellXfs')); cache={}
        def unlocked(style):
            if style not in cache:
                xf=copy.deepcopy(xfs[int(style)])
                for p in xf.findall(q('protection')): xf.remove(p)
                E.SubElement(xf,q('protection'),locked='0'); xf.set('applyProtection','1')
                cache[style]=str(len(xfs)); xfs.append(xf)
            return cache[style]
        for index in [1,2]:
            key=f'xl/worksheets/sheet{index}.xml'; root=E.fromstring(parts[key])
            if index==1:
                for c in root.findall('.//'+q('c')):
                    col,row=re.fullmatch(r'([A-Z]+)(\d+)',c.get('r')).groups()
                    if 4<=int(row)<=103 and not(filename.startswith('07') and col in ['F','I']):
                        c.set('s',unlocked(c.get('s','0')))
            protection=E.Element(q('sheetProtection'),sheet='1',objects='1',scenarios='1',selectLockedCells='1',selectUnlockedCells='0')
            root.insert(list(root).index(root.find(q('sheetData')))+1,protection)
            props=root.find(q('sheetPr'))
            if props is None: props=E.Element(q('sheetPr')); root.insert(0,props)
            for child in props.findall(q('pageSetUpPr')): props.remove(child)
            E.SubElement(props,q('pageSetUpPr'),fitToPage='1')
            for name in ['printOptions','pageMargins','pageSetup']:
                for child in root.findall(q(name)): root.remove(child)
            E.SubElement(root,q('printOptions'),horizontalCentered='1')
            E.SubElement(root,q('pageMargins'),left='0.25',right='0.25',top='0.35',bottom='0.35',header='0.15',footer='0.15')
            E.SubElement(root,q('pageSetup'),paperSize='8' if index==1 else '9',orientation='landscape',fitToWidth='1',fitToHeight='0')
            parts[key]=E.tostring(root,xml_declaration=True,encoding='utf-8')
        xfs.set('count',str(len(xfs))); parts['xl/styles.xml']=E.tostring(styles,xml_declaration=True,encoding='utf-8')
        book=E.fromstring(parts['xl/workbook.xml']); names=E.SubElement(book,q('definedNames'))
        E.SubElement(names,q('definedName'),name='_xlnm.Print_Area',localSheetId='0').text=f"'Реестр'!$A$1:${last}${total}"
        E.SubElement(names,q('definedName'),name='_xlnm.Print_Titles',localSheetId='0').text="'Реестр'!$1:$3"
        # Instruction extent is derived from populated cells, rather than a guessed crop.
        inst=E.fromstring(parts['xl/worksheets/sheet2.xml'])
        cells=[c.get('r') for c in inst.findall('.//'+q('c')) if len(c)]
        endrow=max(int(re.search(r'\d+',r)[0]) for r in cells)
        endcol=max((re.match('[A-Z]+',r)[0] for r in cells),key=lambda c:(len(c),c))
        for merge in inst.findall('.//'+q('mergeCell')):
            endcol=max(endcol,re.match('[A-Z]+',merge.get('ref').split(':')[-1])[0],key=lambda c:(len(c),c))
        E.SubElement(names,q('definedName'),name='_xlnm.Print_Area',localSheetId='1').text=f"'Инструкция'!$A$1:${endcol}${endrow}"
        parts['xl/workbook.xml']=E.tostring(book,xml_declaration=True,encoding='utf-8')
        target=out/filename
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
            for n,b in parts.items(): z.writestr(n,b)
        report.append({'file':filename,'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'unlocked_style_variants':len(cache),'sheet_protection':'accidental-edit prevention, no password/security claim','print':'A3 landscape registry, A4 landscape instruction; one page wide, unlimited height; repeat rows 1:3'})
    (out/'native-controls.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('source',type=Path); p.add_argument('output',type=Path); a=p.parse_args(); run(a.source,a.output)
