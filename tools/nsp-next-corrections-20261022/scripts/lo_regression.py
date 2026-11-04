from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
import json,subprocess,os,hashlib
Q=Path(__file__).resolve().parents[1];ROOT=Q.parent/'integration-20261022/repo';ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};N='{'+ns['s']+'}'
tests=json.loads((Q/'regression-cases.json').read_text());inputs=Q/'lo-cases/input';outputs=Q/'lo-cases/output';inputs.mkdir(parents=True,exist_ok=True);outputs.mkdir(parents=True,exist_ok=True)
meta=[]
def edit_copy(source,target,changes):
 with ZipFile(source)as z:
  parts={i.filename:z.read(i.filename)for i in z.infolist()};wb=E.fromstring(parts['xl/workbook.xml']);shs=[s.get('name')for s in wb.find('s:sheets',ns)]
  cp=wb.find('s:calcPr',ns)
  if cp is not None:cp.set('fullCalcOnLoad','1');cp.set('forceFullCalc','1');cp.set('calcMode','auto')
  parts['xl/workbook.xml']=E.tostring(wb,encoding='utf-8',xml_declaration=True)
  for sh,cs in changes.items():
   part='xl/worksheets/sheet%d.xml'%(shs.index(sh)+1);r=E.fromstring(parts[part]);data=r.find('s:sheetData',ns)
   for a,v in cs.items():
    c=r.find(f'.//s:c[@r="{a}"]',ns)
    if c is None:
     rowno=int(''.join(filter(str.isdigit,a)));row=data.find(f's:row[@r="{rowno}"]',ns)
     if row is None:row=E.SubElement(data,N+'row',r=str(rowno))
     c=E.SubElement(row,N+'c',r=a)
    for child in list(c):c.remove(child)
    c.attrib.pop('t',None)
    if v is None:continue
    if isinstance(v,(float,int)):E.SubElement(c,N+'v').text=str(v)
    else:c.set('t','inlineStr');E.SubElement(E.SubElement(c,N+'is'),N+'t').text=v
   parts[part]=E.tostring(r,encoding='utf-8',xml_declaration=True)
  # Every scenario must calculate from formulas, never consume cached authoring results.
  for part in list(parts):
   if part.startswith('xl/worksheets/')and part.endswith('.xml'):
    rr=E.fromstring(parts[part])
    for cc in rr.findall('.//s:c',ns):
     if cc.find('s:f',ns)is not None:
      for vv in cc.findall('s:v',ns):cc.remove(vv)
      cc.attrib.pop('t',None)
    parts[part]=E.tostring(rr,encoding='utf-8',xml_declaration=True)
  with ZipFile(target,'w',ZIP_DEFLATED)as out:
   for i in z.infolist():out.writestr(deepcopy(i),parts[i.filename])
for index,pp in enumerate(sorted((Q/'plans').glob('*.json'))):
 p=json.loads(pp.read_text());source=ROOT/'products-storage'/p['path'];assert hashlib.sha256(source.read_bytes()).hexdigest()==p['base_sha256'];candidate=Q/'candidates/products-storage'/p['path']
 for ci,c in enumerate(tests[p['issue']]):
  filename=f'new-{index:02}-{ci:02}.xlsx';edit_copy(candidate,inputs/filename,c['inputs']);meta.append({'name':filename,'issue':p['issue'],'case':c['name'],'expect':c['expect'],'phase':'after'})
 chosen=next((c for c in tests[p['issue']]if c['name'] in ['missing-date','same-date-select-open','unknown-ks','only-type','incomplete','empty','one-complete','negative','contradiction']),tests[p['issue']][0]);filename=f'old-{index:02}.xlsx';edit_copy(source,inputs/filename,chosen['inputs']);meta.append({'name':filename,'issue':p['issue'],'case':chosen['name'],'expect':chosen['expect'],'phase':'before'})
(Q/'lo-cases/manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
cmd=['libreoffice','-env:UserInstallation='+str((Q/'lo-case-profile').resolve().as_uri()),'--headless','--convert-to','xlsx','--outdir',str(outputs),*map(str,sorted(inputs.glob('*.xlsx')))];p=subprocess.run(cmd,capture_output=True,text=True,timeout=70);(Q/'proof/lo-convert.log').write_text(p.stdout+'\n'+p.stderr);assert p.returncode==0,p.stderr
results=[]
for rec in meta:
 f=outputs/rec['name'];assert f.is_file(),('MISSING_RESULT',f)
 with ZipFile(f)as z:
  ss=[''.join(x.itertext())for x in E.fromstring(z.read('xl/sharedStrings.xml'))]if 'xl/sharedStrings.xml'in z.namelist()else[];names=[x.get('name')for x in E.fromstring(z.read('xl/workbook.xml')).find('s:sheets',ns)];checks=[]
  for ref,expected in rec['expect'].items():
   sh,a=ref.rsplit('!',1);r=E.fromstring(z.read('xl/worksheets/sheet%d.xml'%(names.index(sh)+1)));c=r.find(f'.//s:c[@r="{a}"]',ns);v=c.findtext('s:v',namespaces=ns)if c is not None else None;t=c.get('t')if c is not None else None;actual=ss[int(v)]if t=='s'else ''.join(c.xpath('.//s:t/text()',namespaces=ns))if t=='inlineStr'else float(v)if v is not None and t in (None,'n')else v or ''
   passed=expected['contains']in str(actual)if isinstance(expected,dict)else abs(actual-expected)<1e-6 if isinstance(expected,(int,float))and isinstance(actual,(int,float))else expected==actual
   checks.append({'cell':ref,'expected':expected,'actual':actual,'pass':passed})
  results.append({**rec,'checks':checks,'expectations_pass':all(x['pass']for x in checks)})
(Q/'lo-regression-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps({'after_pass':sum(x['expectations_pass']for x in results if x['phase']=='after'),'after_total':sum(x['phase']=='after'for x in results),'before_fail':sum(not x['expectations_pass']for x in results if x['phase']=='before'),'engine':'LibreOffice, NOT Microsoft Excel'},ensure_ascii=False),flush=True)
for x in results:
 if x['phase']=='after'and not x['expectations_pass']:print(json.dumps(x,ensure_ascii=False),flush=True)

