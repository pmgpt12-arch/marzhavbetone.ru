#!/usr/bin/env python3
"""Bounded continuation of PR618: one exact new Word input; never edits product bytes."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zipfile import ZipFile
import argparse,hashlib,json,os,re,shutil,subprocess,time,xml.etree.ElementTree as ET
R=Path('/home/denis/projects/mb001-p11-normative-delta-20261013')
B=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
O=Path('/home/denis/.local/state/p11-1021fd4-native-review-20261014')
H='1021fd42c1fad898562e75512a0afcbf11318833'
P='tools/candidates/portfolio-owner-pdf-20261013/'
C=P+'13-raschet-metrami/'
J='p11-54-correction-native-20261014-v1'
JD=B/'word'/J; RESULT=B/'results/word'/J
EXPECT={'54-zapros-sostoyanie-escrow.docx':'f0bd1a1d9a16c23c272122e764c9414c848fcc9ea35af121d4e28b3154f680cc','00-START-HERE.txt':'1141927c5cb30b8c4ba2ca69949d560e8591ff27d263b9ae598c930315545210'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
def run(args,seconds=10):
 r=subprocess.run(args,capture_output=True,timeout=seconds)
 if r.returncode:raise RuntimeError(f'COMMAND_FAIL {args[0]} code={r.returncode} stderr={r.stderr.decode(errors="replace")[:1200]}')
 return r.stdout

def writej(path,data):
 tmp=path.with_name(path.name+'.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n'); os.replace(tmp,path)

def prepare():
 assert not O.exists() and not JD.exists() and not RESULT.exists(),'Existing task: inspect instead of duplicate'
 files=['00-START-HERE.txt','50-slovar-poley-raschet-metrami.docx','51-algoritm-raschet-metrami.pdf','52-chek-list-raschet-metrami.docx','53-zapros-status-obekta.docx','54-zapros-sostoyanie-escrow.docx','55-pamyatka-punkt-ustupki-escrow.pdf']
 prior=[]
 for p in (B/'word').glob('*/job.xml'):
  if EXPECT['54-zapros-sostoyanie-escrow.docx'].encode() in p.read_bytes():prior.append(str(p))
 assert not prior,('Existing exact-SHA native job',prior)
 O.mkdir(); inp=O/'input'; inp.mkdir()
 manifest=[]
 for name in files:
  data=run(['git','-C',str(R),'show',H+':'+C+name]);path=inp/name;path.write_bytes(data)
  digest=sha(path)
  if name in EXPECT:assert digest==EXPECT[name]
  path.chmod(0o444)
  blob=run(['git','-C',str(R),'rev-parse',H+':'+C+name]).decode().strip()
  manifest.append({'name':name,'repository_path':C+name,'commit':H,'git_blob':blob,'sha256':digest,'bytes':len(data),'role':'candidate_not_release_nomination'})
 test=O/'test_p11_00_54_regression.py';test.write_bytes(run(['git','-C',str(R),'show',H+':tools/test_p11_00_54_regression.py']))
 assert sha(test)=='42abbf38587f8718f01fa5e7d725ecff314be8856fb7e57ebad720461a8533da'
 stdout=run(['python3',str(test),'--candidate-dir',str(inp),'--report',str(O/'static-regression.json')],20)
 (O/'static-regression.stdout').write_bytes(stdout)
 reg=json.loads(stdout);assert reg['verdict']=='PASS' and len(reg['checks'])==12 and len(reg['negative_tests'])==12
 assert all(reg['checks'].values()) and all(reg['negative_tests'].values())
 W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
 with ZipFile(inp/'54-zapros-sostoyanie-escrow.docx') as z:root=ET.fromstring(z.read('word/document.xml'))
 pars=[''.join(x.text or '' for x in p.iter(W+'t')) for p in root.find(W+'body').findall(W+'p')]
 start=[i for i,t in enumerate(pars) if t.startswith('Кому:')];end=[i for i,t in enumerate(pars) if t=='Как пользоваться этим документом']
 assert len(start)==len(end)==1
 (O/'outgoing-and-start-review.txt').write_text('\n'.join(pars[start[0]:end[0]])+'\n\n=== START HERE ===\n'+(inp/'00-START-HERE.txt').read_text())
 JD.mkdir();source=inp/'54-zapros-sostoyanie-escrow.docx';shutil.copyfile(source,JD/source.name)
 job=ET.Element('job',{'id':J});ET.SubElement(job,'file',{'name':source.name,'tag':'p1154new','sha256':sha(source)})
 (JD/'job.xml').write_bytes(ET.tostring(job,encoding='utf-8',xml_declaration=True))
 stage={'job':J,'utc':now(),'status':'STAGED_NOT_SUBMITTED','scope':'ONE_NEW_EXACT_SHA_WORD_ONLY','source_commit':H,'input_sha256':sha(source),'evidence_root':str(O),'native_jobs_submitted':0}
 writej(JD/'stage-receipt.json',stage);writej(O/'stage-receipt.json',stage)
 writej(O/'input-manifest.json',{'source_commit':H,'files':manifest,'role':'READ_ONLY_QA_INPUTS_NOT_FORMAL_NOMINATION'})
 print(json.dumps({'status':'STAGED_NOT_SUBMITTED','input_files':7,'static_positive':12,'negative_mutations':12,'job':J,'input_sha256':sha(source)},ensure_ascii=False))

def submit():
 assert O.is_dir() and JD.is_dir() and not RESULT.exists()
 stage=json.loads((JD/'stage-receipt.json').read_text());assert stage['status']=='STAGED_NOT_SUBMITTED'
 source=JD/'54-zapros-sostoyanie-escrow.docx';assert sha(source)==EXPECT[source.name]
 job=ET.parse(JD/'job.xml').getroot();assert job.get('id')==J and len(job.findall('file'))==1 and job.find('file').get('sha256')==sha(source)
 assert json.loads((O/'static-regression.json').read_text())['verdict']=='PASS'
 target=B/'word/current.xml';old=target.read_bytes();previous=ET.fromstring(old).get('id');assert previous!=J
 assert (B/'results/word'/previous/'report.xml').is_file(),'Occupied mailbox'
 log=B/'transport-7h-20261014.log';lines=log.read_text(errors='replace').splitlines()[-70:]
 idle=[x for x in lines if '192.168.1.140' in x and 'GET /word/current.xml HTTP/1.0" 204' in x];assert idle
 last=idle[-1];t=datetime.strptime(re.search(r'\[(\d\d/\w+/\d{4} \d\d:\d\d:\d\d)\]',last).group(1),'%d/%b/%Y %H:%M:%S').replace(tzinfo=timezone(timedelta(hours=7)))
 age=(datetime.now(timezone.utc)-t).total_seconds();assert 0<=age<=75,('Stale poll',age)
 # Receipt I/O is preflighted before the single mailbox publication; no post-submit retry.
 stage.update({'status':'PREPARED_FOR_SINGLE_SUBMIT','previous_job':previous,'idle_poll':last,'idle_age_seconds':age,'utc':now()})
 writej(JD/'stage-receipt.json',stage);writej(O/'stage-receipt.json',stage)
 assert target.read_bytes()==old and not RESULT.exists(),'Mailbox changed during preflight'
 new=(JD/'job.xml').read_bytes();tmp=target.with_name('current.xml.'+J+'.tmp');assert not tmp.exists();tmp.write_bytes(new);os.replace(tmp,target)
 assert target.read_bytes()==new
 stage.update({'status':'SUBMITTED_AWAITING_RESULT','native_jobs_submitted':1,'submitted_utc':now()})
 writej(JD/'stage-receipt.json',stage);writej(O/'stage-receipt.json',stage)
 print(json.dumps({'status':stage['status'],'job':J,'idle_poll':last},ensure_ascii=False),flush=True)
 deadline=time.monotonic()+80
 while not (RESULT/'report.xml').exists() and time.monotonic()<deadline:time.sleep(4)
 print('RAW_RESULT_AVAILABLE', (RESULT/'report.xml').exists(),flush=True)
 # No resubmission/automatic rerun on timeout.

def verify():
 assert not (O/'native-verification.json').exists()
 job=ET.parse(JD/'job.xml').getroot();raw=RESULT/'report.xml';report=ET.parse(raw).getroot()
 assert report.get('job')==J and report.get('status')=='PASS' and len(report.findall('file'))==1
 entry=report.find('file');assert entry.get('tag')=='p1154new' and entry.get('status')=='PASS'
 pdf=RESULT/'p1154new.pdf';assert sha(pdf)==entry.get('pdf_sha256') and pdf.read_bytes().startswith(b'%PDF-')
 assert sha(JD/'54-zapros-sostoyanie-escrow.docx')==EXPECT['54-zapros-sostoyanie-escrow.docx']==job.find('file').get('sha256')
 native=O/'native';native.mkdir();shutil.copy2(pdf,native/'output.pdf');shutil.copy2(raw,native/'report.xml');shutil.copy2(JD/'job.xml',native/'job.xml')
 info=run(['pdfinfo',str(pdf)]).decode();text=run(['pdftotext','-layout',str(pdf),'-']).decode();(native/'text.txt').write_text(text);(native/'pdfinfo.txt').write_text(info)
 page_count=int(re.search(r'^Pages:\s*(\d+)',info,re.M).group(1));pages=text.split('\f');pages=pages[:-1] if not pages[-1].strip() else pages
 assert len(pages)==page_count and 'A4' in info and 'Microsoft' in info
 outgoing='\n'.join(pages[:2]);compressed=' '.join(outgoing.split())
 checks={'numbering_one_two_three':re.findall(r'^\s*(\d+)\.\s',outgoing,re.M)==['1','2','3'],'reply_deadline_in_letter':'{{СРОК_ОТВЕТА_НА_ЗАПРОС}}' in compressed,'reply_address_in_letter':'{{АДРЕС_ДЛЯ_ОТВЕТА}}' in compressed,'reply_email_in_letter':'{{ЭЛЕКТРОННАЯ_ПОЧТА}}' in compressed,'guide_separate_page':page_count>=3 and 'Как пользоваться этим документом' in pages[2],'when_applies_restored':'Когда применяется' in text}
 run(['pdftoppm','-scale-to','1600','-png',str(pdf),str(native/'page')],25)
 images=sorted(native.glob('page-*.png'));assert len(images)==page_count
 native_result={'job':J,'source_commit':H,'input_sha256':sha(JD/'54-zapros-sostoyanie-escrow.docx'),'raw_report_sha256':sha(raw),'pdf_sha256':sha(pdf),'pages':page_count,'page_chars':[len(x) for x in pages],'outgoing_pdf_checks':checks,'renderer_version':run(['pdftoppm','-v']).decode(errors='replace'),'images':[{'path':str(x.relative_to(O)),'sha256':sha(x)} for x in images],'scope':'NATIVE_OPEN_EXPORT_AND_OUTGOING_CORRECTION_ONLY','visual_review':'PENDING','F02_F03':'OPEN_UNCHANGED','formal_nomination':'OPEN','G1_G8':'OPEN','release':'HOLD','utc':now(),'product_files_modified':False}
 writej(O/'native-verification.json',native_result)
 print(json.dumps({k:native_result[k] for k in ('job','input_sha256','raw_report_sha256','pdf_sha256','pages','page_chars','outgoing_pdf_checks')},ensure_ascii=False))
 assert all(checks.values()),'PDF_OUTGOING_CHECK_FAIL: inspect, do not rerun native'

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('step',choices=['prepare','submit','verify']);a=ap.parse_args();globals()[a.step]()
