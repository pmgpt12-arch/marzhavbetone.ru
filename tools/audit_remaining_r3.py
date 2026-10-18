#!/usr/bin/env python3
"""Read-only inventory and text extraction for the eight exact review inputs."""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json, subprocess
ROOT=Path('/tmp/mb-r3/input')
OUT=Path('/tmp/mb-r3/audit');OUT.mkdir(parents=True,exist_ok=True)
W={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
X={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
for folder in sorted(ROOT.iterdir()):
    data=[]
    for f in sorted(folder.iterdir()):
        rows=[]
        if f.suffix=='.docx':
            with ZipFile(f) as z:
                for part in z.namelist():
                    if part=='word/document.xml' or part.startswith(('word/header','word/footer')) and part.endswith('.xml'):
                        r=E.fromstring(z.read(part))
                        rows += [{'loc':part+':p'+str(i),'text':''.join(p.xpath('.//w:t/text()',namespaces=W))} for i,p in enumerate(r.xpath('//w:p',namespaces=W)) if p.xpath('.//w:t',namespaces=W)]
        elif f.suffix=='.xlsx':
            with ZipFile(f) as z:
                strings=[]
                if 'xl/sharedStrings.xml' in z.namelist():strings=[''.join(s.itertext()) for s in E.fromstring(z.read('xl/sharedStrings.xml'))]
                for part in z.namelist():
                    if part.startswith('xl/worksheets/sheet') and part.endswith('.xml'):
                        r=E.fromstring(z.read(part))
                        for c in r.xpath('//x:c',namespaces=X):
                            text=''.join(c.xpath('.//x:t/text()',namespaces=X))
                            if c.get('t')=='s':text=strings[int(c.find('x:v',X).text)]
                            if c.get('t')=='str' and c.find('x:f',X) is None:
                                v=c.find('x:v',X)
                                text=v.text if v is not None and v.text else ''
                            if text:rows.append({'loc':part+':'+c.get('r'),'text':text})
        elif f.suffix=='.txt':rows=[{'loc':str(i),'text':s} for i,s in enumerate(f.read_text().splitlines()) if s]
        elif f.suffix=='.pdf':rows=[{'loc':'pdf','text':subprocess.check_output(['pdftotext','-layout',str(f),'-'],text=True)}]
        data.append({'file':f.name,'rows':rows})
    (OUT/(folder.name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2))
    (OUT/(folder.name+'.txt')).write_text('\n\n'.join('## '+d['file']+'\n'+'\n'.join(r['loc']+' '+r['text'] for r in d['rows']) for d in data if not d['file'].endswith('.pdf')))
    print(folder.name,len(data),sum(len(d['rows']) for d in data))
