from pathlib import Path
from lxml import etree as ET
import hashlib,json,subprocess,shutil,re,datetime
R=Path('/home/denis/projects/mb001-p11-normative-delta-20261013')
C=R/'tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami'
E=C.parent/'p11-f02-f03-20261014'
B=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
JOB='p11-f02-f03-word-20261014-v1'
D=B/'results/word'/JOB
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert (D/'report.xml').exists(),'WAIT: no result; do not re-submit'
r=ET.parse(str(D/'report.xml')).getroot();j=ET.parse(str(B/'word'/JOB/'job.xml')).getroot()
assert r.get('status')=='PASS' and len(r.findall('file'))==len(j.findall('file'))==3
records=[]
N=E/'native';assert not N.exists();N.mkdir()
shutil.copy2(D/'report.xml',N/'report.xml');shutil.copy2(B/'word'/JOB/'job.xml',N/'job.xml')
(N/'.gitattributes').write_text('report.xml -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n')
for f in j.findall('file'):
 tag=f.get('tag');name=f.get('name');p=D/(tag+'.pdf');entry=next(x for x in r.findall('file') if x.get('tag')==tag)
 assert sha(C/name)==f.get('sha256')==sha(B/'word'/JOB/name)
 assert entry.get('status')=='PASS' and sha(p)==entry.get('pdf_sha256')
 folder=N/tag;folder.mkdir();shutil.copy2(p,folder/'output.pdf')
 info=subprocess.run(['pdfinfo',str(p)],capture_output=True,text=True,check=True,timeout=6).stdout
 t=subprocess.run(['pdftotext','-layout',str(p),'-'],capture_output=True,text=True,check=True,timeout=6).stdout
 pages=[x for x in t.split('\f') if x.strip()];count=int(re.search(r'^Pages:\s*(\d+)',info,re.M).group(1))
 assert len(pages)==count and 'A4' in info
 (folder/'pdfinfo.txt').write_text(info);(folder/'text.txt').write_text(t)
 subprocess.run(['pdftoppm','-scale-to','1800','-png',str(p),str(folder/'page')],capture_output=True,check=True,timeout=25)
 images=sorted(folder.glob('page-*.png'));assert len(images)==count
 records.append({'name':name,'tag':tag,'docx_sha256':sha(C/name),'pdf_sha256':sha(p),'pages':count,'page_chars':[len(x) for x in pages],'last_page_start':pages[-1][:350],'pngs':[{'path':str(x.relative_to(E)),'sha256':sha(x)} for x in images],'visual_status':'AWAITING_PAGE_REVIEW'})
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'job':JOB,'raw_report_sha256':sha(D/'report.xml'),'records':records,'scope':'NATIVE_OPEN_EXPORT_AND_RENDER_IDENTITY_ONLY','render_engine':subprocess.run(['pdftoppm','-v'],capture_output=True,text=True,timeout=4).stderr.strip()}
(E/'native-inspection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('job','raw_report_sha256')},ensure_ascii=False))
print(json.dumps([{k:v for k,v in x.items() if k!='pngs'} for x in records],ensure_ascii=False))
