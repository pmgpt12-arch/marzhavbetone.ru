from pathlib import Path
import json,hashlib,shutil,xml.etree.ElementTree as E,subprocess
Q=Path(__file__).resolve().parents[1];O=Q/'native-recovery-20261022';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
selected=[('native','nsp-next-excel-'+str(i)+'-20261022')for i in (1,2,3,4,6,7,9)]
selected += [('native','nsp-next-excel-'+str(i)+'-coercion-v2-20261022')for i in (5,8)]
selected += [('native','nsp-free-print-v2-20261022')]
jobs=set(selected+[('native','nsp-next-excel-'+str(i)+'-20261022')for i in (5,8,10,11)]+[('word','nsp-next-word-b'+str(i)+'-20261022')for i in (1,2)])
coverage=[]
for channel,jid in sorted(jobs):
 src=N/'results'/channel/jid;report=E.parse(src/'report.xml').getroot();assert report.get('job')==jid
 dst=O/'evidence'/channel/jid;shutil.copytree(src,dst,dirs_exist_ok=True)
 inp=N/channel/jid
 if not inp.exists():inp=Q/'prepared-office'/channel/jid
 assert inp.exists(),inp
 shutil.copytree(inp,O/'frozen-inputs'/jid,dirs_exist_ok=True)
 if (channel,jid)in selected:
  assert report.get('status')=='PASS',(jid,report.get('status'))
  job=E.parse(inp/'job.xml').getroot()
  coverage.append({'job':jid,'files':len(job.findall('file')),'scenarios':len(job.findall('file/case')),'checks':len(report.findall('.//check')),'report_sha256':sha(src/'report.xml'),'report_status':report.get('status')})
(O/'EFFECTIVE_EXCEL_COVERAGE.json').write_text(json.dumps({'jobs':coverage,'files':sum(x['files']for x in coverage),'scenarios':sum(x['scenarios']for x in coverage),'checks':sum(x['checks']for x in coverage),'limits':['9 paid books print gate still open','Numeric-string COM conversion is not rejected as nonnumeric input','Only latest free print-v2 source SHA used for final 2 free books','Read-only/locale telemetry absent; no worker or Office setting changes']},ensure_ascii=False,indent=2))
print('COVERAGE',json.dumps(coverage,ensure_ascii=False))
print('TOTAL',sum(x['files']for x in coverage),sum(x['scenarios']for x in coverage),sum(x['checks']for x in coverage))
