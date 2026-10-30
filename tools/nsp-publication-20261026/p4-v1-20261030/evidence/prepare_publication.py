from pathlib import Path
import sys,json,hashlib,re
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024')
import prepare_p1_publication_20261030 as c
D=Path('/home/denis/projects/nsp-qa16-p4-20261030/publication');D.mkdir(exist_ok=True)
PREFIX='tools/nsp-publication-20261026/p4-v1-20261030';SHA='a581a2174e65184573fb56747431fd8afd37862ef418a84ffa613d1a630b05ea';H=lambda b:hashlib.sha256(b).hexdigest()
assert not (D/'SNAPSHOT_REQUEST.json').exists()
archive=(D.parent/'review-v1/P4_PTO_bez_zamechaniy_v1.zip').read_bytes();assert H(archive)==SHA
(D/'current.zip').write_bytes(archive)
base=c.api('GET','git/ref/heads/'+c.BR)['object']['sha']
w=c.fetch('.github/workflows/nsp-cutover-final.yml',base).decode();assert 'p4-snapshot'not in w
w=w.replace('"p3-publish"]','"p3-publish","p4-snapshot","p4-publish"]',1).replace('|| "$action" == p3-publish ]]; fi','|| "$action" == p3-publish || "$action" == p4-snapshot || "$action" == p4-publish ]]; fi',1)
marker='      - name: Approved P3 targeted publication';assert w.count(marker)==1
w=w.replace(marker,"      - name: Approved P4 targeted publication\n        if: startsWith(env.NSP_ACTION, 'p4-') && github.ref_name == '"+c.BR+"'\n        run: python3 "+PREFIX+"/operate.py \"$NSP_ACTION\"\n"+marker,1)
cat=c.fetch('katalog.html',base).decode();cards=[x for x in re.findall(r'<article\b[^>]*>.*?</article>',cat,re.S)if 'data-sku="p4"'in x];assert len(cards)==1
page=re.search(r'href="(products/[^"]+)"',cards[0])[1]
old=Path('/home/denis/projects/nsp-qa15-p3-20261030/publication/tools/nsp-publication-20261026/p3-v1-20261030')
inspect=(old/'inspect.php').read_text().replace('products/p3-shablony-ks2-ks3.html',page).replace('NSP_P3','NSP_P4').replace('05-ks-bez-vozvrata','08-pto-bez-zamechaniy').replace('p3_files','p4_files')
op=Path('/home/denis/projects/nsp-qa15-p3-20261030/publication/operate.py').read_text();op=op[:op.index("assert request['delivery_policy']")];op=op.replace('54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b',SHA).replace('p3','p4').replace('P3','P4')
compile(op,'operate.py','exec')
approval={'sku':'p4','edition':'P4-layout-v1','owner_quote':'Принято размещаем','owner_product_acceptance':'APPROVED','release_permission':'ALLOW_EXACT_EDITION_ONLY','archive_sha256':SHA,'file_count':26,'review_evidence_commit':'869e1f56edc349fc62f69f6a52ac0cc72287a78e','approved_at_local_date':'2026-10-30','delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY'}
review=c.fetch('tools/nsp-qa16-p4-20261030/internal/REVIEW_MANIFEST.json',approval['review_evidence_commit']);assert json.loads(review)['archive']['sha256']==SHA
req={**approval,'action':'p4-snapshot','approved_archive_sha256':SHA,'request_id':'P4-OWNER-APPROVED-SNAPSHOT-20261030'}
files={'.github/workflows/nsp-cutover-final.yml':w.encode(),PREFIX+'/inspect.php':inspect.encode(),PREFIX+'/operate.py':op.encode(),PREFIX+'/OWNER_APPROVAL.json':(json.dumps(approval,ensure_ascii=False,indent=2)+'\n').encode(),PREFIX+'/REVIEW_MANIFEST.json':review,'tools/nsp-final/request.json':(json.dumps(req,ensure_ascii=False,indent=2)+'\n').encode()}
for p,b in files.items():
 out=D/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
sha=c.commit(files,'P4: owner approval and exact 26-file archive; read-only release snapshot [skip deploy]',base)
r={'status':'P4_OWNER_APPROVED_SNAPSHOT_REQUESTED','base':base,'commit':sha,'branch':c.BR,'prefix':PREFIX,'page':page,'archive_sha256':SHA}
(D/'SNAPSHOT_REQUEST.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
