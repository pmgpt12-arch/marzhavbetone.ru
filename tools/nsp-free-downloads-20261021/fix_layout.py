import json,hashlib
from pathlib import Path
from docx import Document
r=Path(__file__).resolve().parents[2];h=r/'tools/nsp-free-downloads-20261021';rows=json.loads((h/'docx-changes.json').read_text());changes=[]
for i in [5,6,7,11,13]:
 p=r/rows[i]['path'];d=Document(p)
 for para in d.paragraphs:
  if para.text.startswith('С Переход к'):
   for run in para.runs:
    if 'С Переход' in run.text:run.text=run.text.replace('С Переход','Переход',1);break
  if 'Переход к полному комплекту' in para.text:para.paragraph_format.keep_with_next=True
  if 'Стоимость:' in para.text or 'Страница комплекта:' in para.text:para.paragraph_format.keep_together=True
 d.save(p);rows[i]['after']=hashlib.sha256(p.read_bytes()).hexdigest();changes.append({'index':i,'path':rows[i]['path'],'change':'Keep cross-sell paragraph together; remove stray C from heading where present'})
(h/'docx-changes.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');(h/'layout-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
b=json.loads((h/'file-revisions.json').read_text());print(type(b).__name__);print(str(b)[:300])
