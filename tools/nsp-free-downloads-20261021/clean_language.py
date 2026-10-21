#!/usr/bin/env python3
"""Remove owner-prohibited promotional disclaimers, keep substantive legal body."""
from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph
import json,re,ast,hashlib
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
module=ast.parse((HERE/'edit_docx.py').read_text());fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='paragraph_text');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<helper>','exec'),ns)
def normalize_doc(d):
 changes=[];dropping=False
 for node in list(d.element.body):
  if not node.tag.endswith('}p'):continue
  para=Paragraph(node,d);text=para.text;low=re.sub(r'\s+',' ',text.lower()).strip();heading=para.style.name.startswith('Heading')
  negative=bool(re.search(r'(?:что|чего) (?:этот |этого )?материал.{0,6}не (?:закрывает|обещает)',low))
  if negative:
   dropping=True;changes.append({'removed':text});node.getparent().remove(node);continue
  if dropping:
   if heading or 'переход к' in low:dropping=False
   else:changes.append({'removed':text});node.getparent().remove(node);continue
  if 'граница' in low and ('юрист' in low or 'юрид' in low):
   new='Когда требуется разбор ситуации';ns['paragraph_text'](para,new);changes.append({'before':text,'after':new});continue
  new=text
  # Remove the generic disclaimer sentence/paragraph. Keep specific escalation triggers verbatim.
  if re.match(r'(?:материал|лист) (?:не |носит информационный)',low):
   if 'Юрист нужен' in text:new=text[text.index('Юрист нужен'):]
   elif 'Решение о том' in text:new=text[text.index('Решение о том'):]
   else:new=''
  new=re.sub(r'\n\nКомплект не (?:заменяет|гарантирует|отменяет).*$', '',new,flags=re.S)
  if re.match(r'Комплект не (?:заменяет|гарантирует|отменяет)',new):new=''
  if new!=text:
   changes.append({'before':text,'after':new})
   if new:ns['paragraph_text'](para,new)
   else:node.getparent().remove(node)
 return changes
def main():
 proof=json.loads((HERE/'docx-changes.json').read_text());edits=[]
 for row in proof:
  p=ROOT/row['path'];d=Document(p);changes=normalize_doc(d)
  if changes:d.save(p);edits.append({'path':row['path'],'changes':changes})
  row['after']=hashlib.sha256(p.read_bytes()).hexdigest()
 (HERE/'docx-changes.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');(HERE/'language-changes.json').write_text(json.dumps(edits,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
