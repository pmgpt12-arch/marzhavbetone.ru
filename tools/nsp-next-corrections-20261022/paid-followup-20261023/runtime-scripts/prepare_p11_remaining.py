from pathlib import Path
import json,hashlib,shutil
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';P.mkdir(exist_ok=True);S=Q/'package-sources/products-storage/13-raschet-metrami';D=P/'p11-remaining-sources';D.mkdir(exist_ok=True)
rows=[]
for n in ['50-slovar-poley-raschet-metrami.docx','53-zapros-status-obekta.docx']:
 shutil.copy2(S/n,D/n);rows.append({'path':n,'new_sha256':hashlib.sha256((D/n).read_bytes()).hexdigest(),'content_changes':'NONE_NATIVE_REVIEW_ONLY'})
(P/'P11_REMAINING_DOCX.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
s=(Q/'scripts/native_free_content.py').read_text()
changes={"native-recovery-20261022":"paid-followup-20261023",'nsp-free-content-docx-20261022':'nsp-p11-remaining-word-20261023','FREE_CONTENT_DOCX_MANIFEST.json':'P11_REMAINING_DOCX.json',"'additional-candidates'":"'p11-remaining-sources'","tag='fc'":"tag='pm'",'visual-free-content':'visual-p11-remaining','FREE_CONTENT_NATIVE.json':'P11_REMAINING_NATIVE.json'}
for a,b in changes.items():assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
compile(s,'native_p11_remaining.py','exec');(Q/'scripts/native_p11_remaining.py').write_text(s)
print('P11_NATIVE_REMAINING_PREPARED',rows)
