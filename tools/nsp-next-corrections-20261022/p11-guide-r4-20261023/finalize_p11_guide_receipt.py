from pathlib import Path
import json,hashlib,subprocess,xml.etree.ElementTree as E,shutil
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');D=Q/'p11-guide-r4-20261023';jid='nsp-p11-guide-r4-20261023';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rp=D/'evidence/report.xml';rt=E.parse(rp).getroot();assert rt.get('job')==jid and rt.get('status')=='PASS'and len(rt.findall('file'))==4
# Previous post-processing expected a signature marker used by another template.
# Reuse the exact existing receipt; there is no submission or source mutation here.
shutil.copy2(Q/'p11-guide-r4.log',D/'POSTPROCESS_FAILURE_ORIGINAL.log.txt')
(D/'ERROR_LEDGER.json').write_text(json.dumps([{'error':'Postprocessor signature assertion failed after native PASS','root':'Blank P11 forms use {{ФИО_ПОДПИСАНТА}}, not the [подпись] marker of the free advance form','class':'QA_EXPECTATION_MISMATCH','rule':'Signature expectation must follow the exact form role; blank placeholders and filled signatures are separate expected cases','gate':'Exact source SHA, all sendable text on page 1, signature marker appropriate to source, guide starts after page 1','action':'Correct post-processing only; native job is not resubmitted'}],ensure_ascii=False,indent=2)+'\n')
j=E.parse(D/'inputs'/jid/'job.xml').getroot();result={'job':jid,'status':'PASS','receipt_sha256':sha(rp),'files':[]}
for f in j.findall('file'):
 fr=next(x for x in rt.findall('file')if x.get('tag')==f.get('tag'));assert fr.get('status')=='PASS'and fr.find('result').get('source_sha256')==f.get('sha256');pdf=D/'evidence'/(f.get('tag')+'.pdf');assert sha(pdf)==fr.get('pdf_sha256')
 alltext=' '.join(subprocess.check_output(['pdftotext',str(pdf),'-'],text=True,timeout=20).split());assert 'Адресату направляется заполненная форма'in alltext and 'Заказчику направляется заполненная форма'not in alltext
 first=subprocess.check_output(['pdftotext','-f','1','-l','1',str(pdf),'-'],text=True,timeout=20)
 expected='Иванов И. И.'if f.get('name').startswith('example-')else'{{ФИО_ПОДПИСАНТА}}'
 assert expected in first and 'Как пользоваться этим документом'not in first and 'Адресату направляется'not in first
 v=D/'visual'/f.get('tag');v.mkdir(parents=True,exist_ok=False);subprocess.run(['pdftoppm','-scale-to','1600','-png',str(pdf),str(v/'page')],check=True,capture_output=True,timeout=60);count=len(list(v.glob('*.png')));assert count==3
 result['files'].append({'file':f.get('name'),'sha256':f.get('sha256'),'pdf_sha256':sha(pdf),'native_pages':count,'sendable_first_page_gate':'PASS','visual_review':'PENDING'})
(D/'RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('FINALIZED_EXISTING_RECEIPT',len(result['files']),'FILES',sum(x['native_pages']for x in result['files']),'PAGES',flush=True)
