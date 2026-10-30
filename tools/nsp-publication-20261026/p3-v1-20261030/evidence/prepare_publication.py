from pathlib import Path
import sys,base64,json,hashlib
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024')
import prepare_p1_publication_20261030 as c
D=Path('/home/denis/projects/nsp-qa15-p3-20261030/publication');D.mkdir(exist_ok=True)
PREFIX='tools/nsp-publication-20261026/p3-v1-20261030'
SHA='54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b'
assert not (D/'SNAPSHOT_REQUEST.json').exists()
archive=base64.b64decode((D.parent/'P3_approved.b64').read_text());assert hashlib.sha256(archive).hexdigest()==SHA
(D/'current.zip').write_bytes(archive)
base=c.api('GET','git/ref/heads/'+c.BR)['object']['sha']
workflow=c.fetch('.github/workflows/nsp-cutover-final.yml',base).decode()
assert 'p3-snapshot'not in workflow
workflow=workflow.replace('"p1-publish"]','"p1-publish","p3-snapshot","p3-publish"]',1)
workflow=workflow.replace('|| "$action" == p1-publish ]]; fi','|| "$action" == p1-publish || "$action" == p3-snapshot || "$action" == p3-publish ]]; fi',1)
marker='      - name: Approved P1 targeted publication'
assert workflow.count(marker)==1
workflow=workflow.replace(marker,"      - name: Approved P3 targeted publication\n        if: startsWith(env.NSP_ACTION, 'p3-') && github.ref_name == '"+c.BR+"'\n        run: python3 "+PREFIX+"/operate.py \"$NSP_ACTION\"\n"+marker,1)
inspect=c.fetch('tools/nsp-publication-20261026/p1-v1-20261030/inspect.php',base).decode().replace('p1-oplata-po-ks2','p3-ks-2-bez-vozvrata').replace('NSP_P1','NSP_P3').replace('01-zakrytie-rabot','05-ks-bez-vozvrata').replace('p1_files','p3_files')
# Resolve the actual published product page path from current catalog source.
catalog=c.fetch('katalog.html',base).decode()
import re
card=[a for a in re.findall(r'<article\b[^>]*>.*?</article>',catalog,re.S) if 'data-sku="p3"' in a];assert len(card)==1
page=re.search(r'href="(products/[^"]+)"',card[0])[1]
inspect=inspect.replace('products/p3-ks-2-bez-vozvrata.html',page)
op=c.fetch('tools/nsp-publication-20261026/p1-v1-20261030/operate.py',base).decode()
op=op[:op.index("assert request['delivery_policy']")]
op=op.replace('p1-snapshot','p3-snapshot').replace('p1-publish','p3-publish').replace('P1-layout-v1','P3-layout-v1').replace("'p1'","'p3'").replace('99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada',SHA).replace('p1-production','p3-production').replace('p1-before','p3-before').replace('P1_SNAPSHOT','P3_SNAPSHOT')
approval={'sku':'p3','edition':'P3-layout-v1','owner_quote':'Проверил все ок, размещаем','owner_product_acceptance':'APPROVED','release_permission':'ALLOW_EXACT_EDITION_ONLY','archive_sha256':SHA,'file_count':11,'review_evidence_commit':'529cc931f235bdf67a4b46eff06ad861efae89aa','approved_at_local_date':'2026-10-30','delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY'}
review=c.fetch('tools/nsp-qa15-p3-20261030/internal/REVIEW_MANIFEST.json','529cc931f235bdf67a4b46eff06ad861efae89aa')
assert json.loads(review)['archive']['sha256']==SHA
request={**approval,'action':'p3-snapshot','approved_archive_sha256':SHA,'request_id':'P3-OWNER-APPROVED-SNAPSHOT-20261030'}
files={'.github/workflows/nsp-cutover-final.yml':workflow.encode(),PREFIX+'/inspect.php':inspect.encode(),PREFIX+'/operate.py':op.encode(),PREFIX+'/OWNER_APPROVAL.json':(json.dumps(approval,ensure_ascii=False,indent=2)+'\n').encode(),PREFIX+'/REVIEW_MANIFEST.json':review,PREFIX+'/approved/P3_KS_bez_vozvrata_v1.zip':archive,'tools/nsp-final/request.json':(json.dumps(request,ensure_ascii=False,indent=2)+'\n').encode()}
compile(op,'operate.py','exec')
for p,b in files.items():
 out=D/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
sha=c.commit(files,'P3: record owner approval and exact archive; inspect production before release [skip deploy]',base)
receipt={'status':'P3_OWNER_APPROVED_SNAPSHOT_REQUESTED','base':base,'commit':sha,'branch':c.BR,'prefix':PREFIX,'page':page,'archive_sha256':SHA}
(D/'SNAPSHOT_REQUEST.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
