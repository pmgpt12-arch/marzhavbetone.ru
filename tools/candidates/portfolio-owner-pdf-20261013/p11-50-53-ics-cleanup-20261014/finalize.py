#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
R=Path('/home/denis/projects/mb001-p11-ics-cleanup-20261014');E=R/'tools/candidates/portfolio-owner-pdf-20261013/p11-50-53-ics-cleanup-20261014'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,o):
 b=(json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode();t=p.with_name(p.name+'.tmp')
 with t.open('wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p);d=os.open(p.parent,os.O_RDONLY);os.fsync(d);os.close(d)
files=['passport.json','patch-report.json','native-passport.json','native-receipt.json','regression-report.json','native/50.pdf','native/50-1.png','native/50-2.png','native/53.pdf','native/53-1.png','native/53-2.png','native/53-3.png','native/report.xml']
for f in files:assert (E/f).exists(),f
o={'schema_version':1,'id':'P11-50-53-ICS-CLEANUP-AUTHOR-ACCEPTANCE','status':'PASS_AUTHOR_CANDIDATE_ONLY','finished_at':datetime.now(timezone.utc).isoformat(),'base_head':'58ed5fe199dbcdecf6261eca634fe73b712c73fd','github_observed_after_base':'dade5a80aa1a9fe4271b40b24a1d7c45dc8ab579','github_delta_after_base':'two evidence/archive files only; product 50/53 unchanged','candidate_sha256':{'50':'6f40e5d3757d77d6460efb990f459167220f5fb9f3f36a6a6bcfb92b415869d5','53':'c3fccbdc5e7e6841ca8c48b5ab1c199bdebe0d2f4990c232040d20f70bfc023e'},'native':{'job':'p11-50-53-ics-cleanup-word-20261014-v1','status':'PASS','pages':{'50':2,'53':3},'pdf_sha256':{'50':'d97f0684082df389ce4424ed898f4b93c2451e51412b803f3cf392b0590f2071','53':'2df51ae45b802d8e62f2ed2232be0a3808642db015cb3ff5794beaafc90652bd'}},'visual_review':{'pages_reviewed':5,'status':'PASS_AUTHOR_VISUAL_ONLY','facts':['50 compact two-page dictionary, 8pt table text readable','53 three pages unchanged in layout','graphite headings','no visible italic','no clipping or overlap','page-2 dictionary header repeats']},'regression':{'status':'PASS','report_sha256':sha(E/'regression-report.json')},'evidence_sha256':{f:sha(E/f) for f in files},'limitations':['author cannot independently accept own correction','existing eight-file archive at dade5a80 predates corrected SHA and becomes stale','archive/full buyer replay, exact-head CI and independent delta review required','release HOLD','G1-G8 0/13'],'next_step':'commit/rebase on current PR head, publish Draft correction, run CI, independent review, rebuild/review archive'}
atomic(E/'author-acceptance.json',o);print(json.dumps({'status':o['status'],'sha256':sha(E/'author-acceptance.json')},ensure_ascii=False))
