from pathlib import Path
import sys,json,hashlib,re,subprocess
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024')
import prepare_p1_publication_20261030 as c
D=Path('/home/denis/projects/nsp-qa20-p9-20261030/publication');D.mkdir(exist_ok=True)
P='tools/nsp-publication-20261026/p9-v1-20261030';SHA='34bf03bcd3ed2e31d731dd8ac4c316cf9f94a8bb5dde1e4c9fc1aa3a7b7b23d9';H=lambda b:hashlib.sha256(b).hexdigest()
assert not (D/'SNAPSHOT_REQUEST.json').exists()
a=D.parent/'review-v1/output/P9_Genpodryadchik_bankrotitsya_v1.zip';assert H(a.read_bytes())==SHA;(D/'current.zip').write_bytes(a.read_bytes())
base=c.api('GET','git/ref/heads/'+c.BR)['object']['sha'];w=c.fetch('.github/workflows/nsp-cutover-final.yml',base).decode();assert 'p9-snapshot'not in w
w=w.replace('"p7-publish"]','"p7-publish","p9-snapshot","p9-publish"]',1).replace('|| "$action" == p7-publish ]]; fi','|| "$action" == p7-publish || "$action" == p9-snapshot || "$action" == p9-publish ]]; fi',1)
assert '"p9-publish"'in w
marker='      - name: Approved P4 targeted publication';assert w.count(marker)==1;w=w.replace(marker,"      - name: Approved P9 targeted publication\n        if: startsWith(env.NSP_ACTION, 'p9-') && github.ref_name == '"+c.BR+"'\n        run: python3 "+P+"/operate.py \"$NSP_ACTION\"\n"+marker,1)
cat=c.fetch('katalog.html',base).decode();card=[x for x in re.findall(r'<article\b[^>]*>.*?</article>',cat,re.S)if 'data-sku="p9"'in x];assert len(card)==1;page=re.search(r'href="(products/[^"]+)"',card[0])[1]
old=Path('/home/denis/projects/nsp-qa16-p4-20261030/publication')
inspect=(old/'tools/nsp-publication-20261026/p4-v1-20261030/inspect.php').read_text().replace('products/p4-ispolnitelnaya-dokumentaciya-pto.html',page).replace('NSP_P4','NSP_P9').replace('08-pto-bez-zamechaniy','11-bankrotstvo-genpodryadchika').replace('p4_files','p9_files')
op=(old/'operate.py').read_text();op=op[:op.index("assert request['delivery_policy']")];op=op.replace('a581a2174e65184573fb56747431fd8afd37862ef418a84ffa613d1a630b05ea',SHA).replace('p4','p9').replace('P4','P9')
op=op.replace('P9-layout-v1','P9-review-v1')
approval={'sku':'p9','edition':'P9-review-v1','owner_quote':'Публикуй','owner_product_acceptance':'APPROVED','release_permission':'ALLOW_EXACT_EDITION_ONLY','archive_sha256':SHA,'file_count':12,'review_evidence_commit':'2f8727dcb11d3760e5b92a09b70b474419c85f40','approved_at_local_date':'2026-10-30','delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY'}
review=c.fetch('tools/nsp-qa20-p9-20261030/review-v1/internal/REVIEW_MANIFEST.json',approval['review_evidence_commit']);assert json.loads(review)['archive']['sha256']==SHA
req={**approval,'action':'p9-snapshot','approved_archive_sha256':SHA,'request_id':'P9-OWNER-APPROVED-SNAPSHOT-20261030'}
files={'.github/workflows/nsp-cutover-final.yml':w.encode(),P+'/inspect.php':inspect.encode(),P+'/operate.py':op.encode(),P+'/OWNER_APPROVAL.json':json.dumps(approval,ensure_ascii=False,indent=2).encode(),P+'/REVIEW_MANIFEST.json':review,'tools/nsp-final/request.json':json.dumps(req,ensure_ascii=False,indent=2).encode()}
for p,b in files.items():
 out=D/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
sha=c.commit(files,'P9: owner accepts exact 13-file edition; read-only production snapshot [skip deploy]',base)
r={'commit':sha,'base':base,'branch':c.BR,'prefix':P,'page':page,'archive_sha256':SHA};(D/'SNAPSHOT_REQUEST.json').write_text(json.dumps(r));print(json.dumps(r),flush=True)
# Push starts the existing workflow. Inspect matching head SHA; never dispatch without a supported trigger.
