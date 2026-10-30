from pathlib import Path
import sys,json,hashlib,re,subprocess
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024')
import prepare_p1_publication_20261030 as c
D=Path('/home/denis/projects/nsp-qa17-p5-20261030/publication');D.mkdir(exist_ok=True)
P='tools/nsp-publication-20261026/p5-v1-20261030';SHA='1a0ab501a008c9cae1b1baaaa6570d1123291630ac8ecff1db74fad411431286';H=lambda b:hashlib.sha256(b).hexdigest()
assert not (D/'SNAPSHOT_REQUEST.json').exists()
a=D.parent/'review-v1/P5_Uderzhaniya_shtrafy_zachety_v1.zip';assert H(a.read_bytes())==SHA;(D/'current.zip').write_bytes(a.read_bytes())
base=c.api('GET','git/ref/heads/'+c.BR)['object']['sha'];w=c.fetch('.github/workflows/nsp-cutover-final.yml',base).decode();assert 'p5-snapshot'not in w
w=w.replace('"p4-publish"]','"p4-publish","p5-snapshot","p5-publish"]',1).replace('|| "$action" == p4-publish ]]; fi','|| "$action" == p4-publish || "$action" == p5-snapshot || "$action" == p5-publish ]]; fi',1)
assert '"p5-publish"'in w
marker='      - name: Approved P4 targeted publication';assert w.count(marker)==1;w=w.replace(marker,"      - name: Approved P5 targeted publication\n        if: startsWith(env.NSP_ACTION, 'p5-') && github.ref_name == '"+c.BR+"'\n        run: python3 "+P+"/operate.py \"$NSP_ACTION\"\n"+marker,1)
cat=c.fetch('katalog.html',base).decode();card=[x for x in re.findall(r'<article\b[^>]*>.*?</article>',cat,re.S)if 'data-sku="p5"'in x];assert len(card)==1;page=re.search(r'href="(products/[^"]+)"',card[0])[1]
old=Path('/home/denis/projects/nsp-qa16-p4-20261030/publication')
inspect=(old/'tools/nsp-publication-20261026/p4-v1-20261030/inspect.php').read_text().replace('products/p4-ispolnitelnaya-dokumentaciya-pto.html',page).replace('NSP_P4','NSP_P5').replace('08-pto-bez-zamechaniy','07-uderzhaniya-shtrafy-zachety').replace('p4_files','p5_files')
op=(old/'operate.py').read_text();op=op[:op.index("assert request['delivery_policy']")];op=op.replace('a581a2174e65184573fb56747431fd8afd37862ef418a84ffa613d1a630b05ea',SHA).replace('p4','p5').replace('P4','P5')
approval={'sku':'p5','edition':'P5-layout-v1','owner_quote':'Размещай','owner_product_acceptance':'APPROVED','release_permission':'ALLOW_EXACT_EDITION_ONLY','archive_sha256':SHA,'file_count':30,'review_evidence_commit':'e0a8f10fe5fa94c55a25c0a170b0ab3ed5a613c0','approved_at_local_date':'2026-10-30','delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY'}
review=c.fetch('tools/nsp-qa17-p5-20261030/internal/REVIEW_MANIFEST.json',approval['review_evidence_commit']);assert json.loads(review)['archive']['sha256']==SHA
req={**approval,'action':'p5-snapshot','approved_archive_sha256':SHA,'request_id':'P5-OWNER-APPROVED-SNAPSHOT-20261030'}
files={'.github/workflows/nsp-cutover-final.yml':w.encode(),P+'/inspect.php':inspect.encode(),P+'/operate.py':op.encode(),P+'/OWNER_APPROVAL.json':json.dumps(approval,ensure_ascii=False,indent=2).encode(),P+'/REVIEW_MANIFEST.json':review,'tools/nsp-final/request.json':json.dumps(req,ensure_ascii=False,indent=2).encode()}
for p,b in files.items():
 out=D/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
sha=c.commit(files,'P5: owner accepts exact 30-file edition; read-only production snapshot [skip deploy]',base)
r={'commit':sha,'base':base,'branch':c.BR,'prefix':P,'page':page,'archive_sha256':SHA};(D/'SNAPSHOT_REQUEST.json').write_text(json.dumps(r));print(json.dumps(r),flush=True)
subprocess.run(['gh','workflow','run','nsp-cutover-final.yml','--repo','pmgpt12-arch/marzhavbetone.ru','--ref',c.BR],check=True,timeout=20)
