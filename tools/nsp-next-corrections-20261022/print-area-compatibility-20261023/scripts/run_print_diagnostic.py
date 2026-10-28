from pathlib import Path
import base64,json,hashlib,shutil,subprocess,xml.etree.ElementTree as E,time,fcntl,zipfile
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');R=Q.parent/'integration-20261022/repo';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
D=Q/'print-area-diagnostic-20261023';D.mkdir(exist_ok=False);jid='nsp-print-area-diagnostic-v1-20261023';d=D/'inputs'/jid;d.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=E.Element('job',id=jid,qa_only='true');ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
for i,x in enumerate(json.loads((Q/'print-diagnostic-transfer.json').read_text()),1):
 p=d/x['name'];p.write_bytes(base64.b64decode(x['base64'],validate=True));assert sha(p)==x['sha256']
 with zipfile.ZipFile(p)as z:
  w=E.fromstring(z.read('xl/workbook.xml'));names=w.findall('s:definedNames/s:definedName',ns);assert len(names)==2
  assert names[0].get('name')=='_xlnm.Print_Area'and names[0].get('localSheetId')=='0'and names[0].text=="'"+x['sheet']+"'!$A$1:$A$3"
 f=E.SubElement(j,'file',name=x['name'],sheet=x['sheet'],tag='pd'+str(i),sha256=x['sha256'],export_source_first='true',print_preflight='true')
 c=E.SubElement(f,'case',name='fixed-control');E.SubElement(c,'expect',cell='A2',kind='number',value='123');E.SubElement(c,'expect',cell='B2',kind='number',value='456')
E.ElementTree(j).write(d/'job.xml',encoding='utf-8',xml_declaration=True)
lock=(N/'diagnostics/office-access-20261021-222308/check.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
assert all(env['previous_is_complete'](N,c)for c in ['native','word']);dest=N/'native'/jid;assert not dest.exists();shutil.copytree(d,dest);env['submit'](N,'native',dest);print('SUBMITTED',jid,flush=True)
rp=N/'results/native'/jid/'report.xml';deadline=time.monotonic()+240
while time.monotonic()<deadline:
 assert E.parse(N/'native/current.xml').getroot().get('id')==jid
 if rp.exists():break
 time.sleep(3)
if not rp.exists():(D/'NO_RECEIPT.txt').write_text('Timed out after 240 seconds; do not duplicate this job.');raise SystemExit(2)
shutil.copytree(rp.parent,D/'evidence');rt=E.parse(rp).getroot();assert rt.get('job')==jid
result={'job':jid,'runtime':rt.get('status'),'checks':[dict(c.attrib)for c in rt.findall('check')],'scope':'QA-only print-area import diagnostic; no product or worker changes','files':[]}
(D/'RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
if rt.get('status')!='PASS':print('RUNTIME_FAILURE',rt.findtext('error'),flush=True);raise SystemExit(3)
for i in [1,2]:
 pdf=rp.parent/('pd'+str(i)+'-filled.pdf');txt=subprocess.check_output(['pdftotext',str(pdf),'-'],text=True,timeout=20);assert 'INCLUDED-'in txt
 row={'tag':'pd'+str(i),'outside_marker_printed':'OUTSIDE-AREA-'in txt,'native_pdf_sha256':sha(pdf),'pdf_info':subprocess.check_output(['pdfinfo',str(pdf)],text=True,timeout=20)}
 result['files'].append(row);v=D/'visual'/row['tag'];v.mkdir(parents=True);subprocess.run(['pdftoppm','-scale-to','1600','-png',str(pdf),str(v/'page')],check=True,capture_output=True,timeout=40)
 (D/(row['tag']+'-text.txt')).write_text(txt)
result['print_scope']='FAIL'if any(x['outside_marker_printed']for x in result['files'])else'PASS'
(D/'RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('FINISHED',json.dumps(result['files']),result['print_scope'],flush=True)
