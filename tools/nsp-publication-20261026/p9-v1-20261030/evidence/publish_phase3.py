from pathlib import Path
import sys,json,subprocess,time,re
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024');import prepare_p1_publication_20261030 as c
D=Path('/home/denis/projects/nsp-qa20-p9-20261030');PUB=D/'publication'
s=Path('/home/denis/projects/nsp-qa18-p7-20261030/commit_publication.py').read_text().replace('nsp-qa18-p7','nsp-qa20-p9').replace('p7-v2','p9-v1').replace('p7-dogovor-podryada','p9-bankrotstvo-genpodryadchika').replace('P7','P9').replace('p7','p9').replace('==18','==19').replace('exact 13 files','exact 12 files')
s=s.replace("['prepare_publication.py','build_publication.py','test_publication.py']","['prepare_publication.py','publish_phase1.py','publish_phase2.py','publish_phase3.py','test_publication.py']")
(D/'commit_publication.py').write_text(s)
assert "review-v1/output/P9_Genpodryadchik_bankrotitsya_v1.zip" in (PUB/'operate.py').read_text()
assert "len(z.namelist())==12" in (PUB/'operate.py').read_text()
exec(compile(s,str(D/'commit_publication.py'),'exec'),{})
r=json.loads((PUB/'PUBLISH_REQUEST.json').read_text())
for i in range(45):
 runs=c.api('GET','actions/workflows/nsp-cutover-final.yml/runs?per_page=12')['workflow_runs']
 xs=[x for x in runs if x['head_sha']==r['commit']]
 if xs:
  run=xs[0]
  if run['status']=='completed':break
 time.sleep(8)
else:raise RuntimeError('Publication pending; resume existing request')
E=PUB/'live-evidence';E.mkdir(exist_ok=True)
subprocess.run(['gh','run','download',str(run['id']),'-R','pmgpt12-arch/marzhavbetone.ru','-n','nsp-final-evidence-'+str(run['id']),'-D',str(E)],check=True,timeout=60)
print('WORKFLOW',json.dumps({'run_id':run['id'],'conclusion':run['conclusion']}),flush=True)
if run['conclusion']!='success':
 logs=subprocess.run(['gh','run','view',str(run['id']),'-R','pmgpt12-arch/marzhavbetone.ru','--log-failed'],capture_output=True,timeout=40).stdout.decode()
 print(logs[-15000:],flush=True);raise RuntimeError('Workflow unsuccessful; inspect evidence')
print((E/'P9_PUBLICATION_RECEIPT.json').read_text(),flush=True)
