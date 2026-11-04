from pathlib import Path
import subprocess,json,shutil,hashlib,time,xml.etree.ElementTree as E
Q=Path(__file__).resolve().parents[1];O=Q/'native-recovery-20261022';R=Q.parent/'integration-20261022/repo';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env);assert env['previous_is_complete'](N,'native')
jid='nsp-free-print-v2-reopen-20261022';d=O/'frozen-inputs'/jid;d.mkdir(exist_ok=False);rt=E.Element('job',id=jid,qa_only='true',scope='Reopen saved native copies of final free print versions and verify print persistence')
for tag,sheet,ex in [('fp10','Реестр допработ',{'G5':127500,'I5':'Расчёт заполнен'}),('fp11','Реестр приложений к КС',{'E7':11,'G7':'Листаж проверен'})]:
 src=N/'results/native/nsp-free-print-v2-20261022'/(tag+'-filled.xlsx');name='reopen-'+tag+'.xlsx';shutil.copyfile(src,d/name);f=E.SubElement(rt,'file',name=name,tag='r'+tag,sheet=sheet,sha256=sha(src),export_source_first='true',print_preflight='true');c=E.SubElement(f,'case',name='saved-print-output')
 for cell,v in ex.items():E.SubElement(c,'expect',cell=cell,kind='number'if isinstance(v,int)else'text',value=str(v))
E.ElementTree(rt).write(d/'job.xml',encoding='utf-8',xml_declaration=True);dest=N/'native'/jid;assert not dest.exists();shutil.copytree(d,dest);env['submit'](N,'native',dest);print('SUBMITTED',jid,flush=True)
rp=N/'results/native'/jid/'report.xml';until=time.monotonic()+240
while time.monotonic()<until:
 assert E.parse(N/'native/current.xml').getroot().get('id')==jid
 if rp.exists():break
 time.sleep(3)
assert rp.exists(),'NO_RECEIPT_AFTER_240S';r=E.parse(rp).getroot();assert r.get('job')==jid;shutil.copytree(rp.parent,O/'evidence/native'/jid,dirs_exist_ok=True)
out={'job':jid,'status':r.get('status'),'report_sha256':sha(rp),'checks':len(r.findall('check')),'failed':[dict(x.attrib)for x in r.findall('check')if x.get('pass','').lower()!='true'],'pdfs':[]}
for tag in ['rfp10','rfp11']:
 p=rp.parent/(tag+'-filled.pdf');info=subprocess.check_output(['pdfinfo',str(p)],text=True);out['pdfs'].append({'name':p.name,'sha256':sha(p),'pdf_info':info})
(O/'FREE_EXCEL_PRINT_V2_REOPEN.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False),flush=True)
