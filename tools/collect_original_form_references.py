#!/usr/bin/env python3
"""Fetch identified legal originals and preserve selected pages without restyling."""
from pathlib import Path
from urllib.request import urlopen
import hashlib,json,fitz
B=Path(__file__).resolve().parents[1]/'tools/candidates/remaining-batch-r3-20261018/form-originals-audit'
C=Path('/tmp/mb-r3/official');C.mkdir(exist_ok=True,parents=True);B.mkdir(exist_ok=True,parents=True)
sources={
 '344-minjust.pdf':('https://minjust.consultant.ru/files/47785','072085858e13ca0869b14dfbaf1f8b69649d2ff25786c359fe9c82491c8aee73'),
 '1026-minjust.pdf':('https://minjust.consultant.ru/files/28915','5c72286eb37303c187f1dd415d2e5595e32cfd07003b464667345861c73111d9'),
 '100-album.pdf':('https://www.stroysmeta.ru/download/1259/269','75da8368ba95ec79cd5085b97f403963c249880be8c7a5127e554e4ad78e1079'),
 '24297.pdf':('https://files.stroyinf.ru/Data/562/56263.pdf','a09f9a9988841ee844b42f8fa169e1023b348693e3ebc3e98d0a4f4e4461402d')}
for name,(url,sha) in sources.items():
 p=C/name
 if not p.exists():p.write_bytes(urlopen(url,timeout=30).read())
 assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,(name,'source changed; stop')
tasks=[('aosr-344-original.pdf','344-minjust.pdf',12,15),('general-journal-1026-original.pdf','1026-minjust.pdf',1,11),('ks2-reference.pdf','100-album.pdf',0,1),('ks3-reference.pdf','100-album.pdf',2,2),('ks6a-reference.pdf','100-album.pdf',3,5),('incoming-verification-24297-original.pdf','24297.pdf',11,11)]
rows=[]
for name,source,start,end in tasks:
 original=fitz.open(C/source);selected=fitz.open(C/source);selected.select(list(range(start,end+1)))
 target=B/name
 if target.exists():target.unlink()
 selected.save(target,garbage=4,deflate=True,no_new_id=True);selected.close()
 result=fitz.open(target)
 identity=all(original[start+i].get_pixmap().samples==result[i].get_pixmap().samples and original[start+i].rect==result[i].rect for i in range(len(result)))
 assert identity,(name,'visual change during page extraction')
 rows.append({'file':name,'source_url':sources[source][0],'source_sha256':sources[source][1],'source_pages_1based':[start+1,end+1],'pages':len(result),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_page_pixels_unchanged':True})
(B/'reference-manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print('LEGAL_REFERENCE_PAGES_UNCHANGED',sum(r['pages'] for r in rows))

