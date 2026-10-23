"""Immutable, SHA-bound Office 2016 jobs for QA-02; no production files."""
from pathlib import Path
import json,hashlib,shutil,xml.etree.ElementTree as E
O=Path(__file__).resolve().parent
D=json.loads((O/'CASES.json').read_text());M=D['main_sheet'];jobs=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def typed(v):return ('boolean',str(v).lower())if isinstance(v,bool)else('number',str(v))if isinstance(v,(int,float))else('text',str(v))
def put(parent,tag,s,c,v):
    k,t=typed(v);return E.SubElement(parent,tag,sheet=s,cell=c,kind=k,value=t)
def flatten(d):return {(s,c):v for s,cs in d.items()for c,v in cs.items()}
def save(root,ch):
    ident=root.get('id');p=O/'native-jobs'/ch/ident;p.mkdir(parents=True,exist_ok=True)
    E.indent(root);E.ElementTree(root).write(p/'job.xml',encoding='utf-8',xml_declaration=True)
    for f in root.findall('file'):shutil.copyfile(O/'candidate'/f.get('name'),p/f.get('name'))
    jobs.append(dict(channel=ch,id=ident,job_sha256=sha(p/'job.xml')))
worked=next(c for c in D['cases']if c['name']=='partial-during-period')
for n in range(7):
    root=E.Element('job',id=f'nsp-qa02-excel-b{n+1}-v1-20261023',qa_only='true')
    fn='02-kalkulyator-sroka-oplaty.xlsx'
    f=E.SubElement(root,'file',name=fn,tag='q2x',sheet=M,sha256=sha(O/'candidate'/fn),export_source_first='true',print_preflight='true')
    prev={}
    for c in D['cases'][8*n:8*n+8]:
        cs=E.SubElement(f,'case',name=c['name']);now=flatten(c['inputs'])
        for s,a in sorted(prev.keys()-now.keys()):E.SubElement(cs,'set',sheet=s,cell=a,kind='blank',value='')
        for(s,a),v in now.items():put(cs,'set',s,a,v)
        for(s,a),v in flatten(c['expected']).items():put(cs,'expect',s,a,v)
        prev=now
    if n==6:
        pr=E.SubElement(f,'print')
        for(s,a),v in flatten(worked['inputs']).items():put(pr,'set',s,a,v)
    save(root,'native')
root=E.Element('job',id='nsp-qa02-word-v1-20261023',qa_only='true')
for n,fn in enumerate(sorted(p.name for p in(O/'candidate').glob('*.docx')),1):E.SubElement(root,'file',name=fn,tag='q2d'+str(n),sha256=sha(O/'candidate'/fn))
save(root,'word')
(O/'native-jobs/PLAN.json').write_text(json.dumps(dict(jobs=jobs,reopen_expected=worked['expected'],filled_source_job=jobs[6]['id']),ensure_ascii=False,indent=2)+'\n')
print('Prepared',len(jobs),'SHA-bound jobs; Excel scenarios:',len(D['cases']))
