from pathlib import Path
import sys,json,subprocess,time,shutil
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024')
import prepare_p1_publication_20261030 as c
D=Path('/home/denis/projects/nsp-qa20-p9-20261030');PUB=D/'publication';PUB.mkdir(exist_ok=True)
old=Path('/home/denis/projects/nsp-qa18-p7-20261030')
s=(old/'prepare_publication.py').read_text()
s=s.replace('nsp-qa18-p7','nsp-qa20-p9').replace('p7-v2','p9-v1').replace('p7','p9').replace('P7','P9')
s=s.replace('99e877fc851843a79c8524f508529ecab7da049aa6886590fcbce68a97676e24','34bf03bcd3ed2e31d731dd8ac4c316cf9f94a8bb5dde1e4c9fc1aa3a7b7b23d9')
s=s.replace('review-v2','review-v1').replace('P9-review-v2','P9-review-v1').replace('P9_Dogovor_v_interesah_ispolnitelya_v2.zip','P9_Genpodryadchik_bankrotitsya_v1.zip').replace('03-dogovor-podryada','11-bankrotstvo-genpodryadchika')
s=s.replace('8dfde54d57b9a5416e367cd4c189c73cb787acb9','2f8727dcb11d3760e5b92a09b70b474419c85f40').replace("'file_count':13","'file_count':12").replace("'owner_quote':'Размещаем на сайте'","'owner_quote':'Публикуй'")
s=s.replace('.replace(\'"p5-publish"]\',\'"p5-publish","p9-snapshot","p9-publish"]\',1)', '.replace(\'"p7-publish"]\',\'"p7-publish","p9-snapshot","p9-publish"]\',1)')
s=s.replace(".replace('|| \"$action\" == p5-publish ]]; fi','|| \"$action\" == p5-publish || \"$action\" == p9-snapshot || \"$action\" == p9-publish ]]; fi',1)",".replace('|| \"$action\" == p7-publish ]]; fi','|| \"$action\" == p7-publish || \"$action\" == p9-snapshot || \"$action\" == p9-publish ]]; fi',1)")
s=s.replace("review-v1/P9_Genpodryadchik_bankrotitsya_v1.zip","review-v1/output/P9_Genpodryadchik_bankrotitsya_v1.zip")
(D/'prepare_publication.py').write_text(s)
exec(compile(s,str(D/'prepare_publication.py'),'exec'),{})
r=json.loads((PUB/'SNAPSHOT_REQUEST.json').read_text())
for i in range(35):
 runs=c.api('GET','actions/workflows/nsp-cutover-final.yml/runs?per_page=12')['workflow_runs']
 matching=[x for x in runs if x['head_sha']==r['commit']]
 if matching:
  run=matching[0]
  if run['status']=='completed':
   assert run['conclusion']=='success',run
   break
 time.sleep(8)
else:raise RuntimeError('Snapshot workflow pending; resume existing request')
r['run_id']=run['id'];(PUB/'SNAPSHOT_REQUEST.json').write_text(json.dumps(r))
out=PUB/'snapshot-artifact';out.mkdir(exist_ok=True)
subprocess.run(['gh','run','download',str(run['id']),'-R','pmgpt12-arch/marzhavbetone.ru','-n','nsp-final-evidence-'+str(run['id']),'-D',str(out)],check=True,timeout=60)
shutil.copytree(out/'p9-before',PUB/'snapshot',dirs_exist_ok=True)
shutil.copyfile(out/'p9-production-snapshot.json',PUB/'snapshot/p9-production-snapshot.json')
print('SNAPSHOT_READY',json.dumps(r),flush=True)
print((PUB/'snapshot'/r['page']).read_text(),flush=True)
