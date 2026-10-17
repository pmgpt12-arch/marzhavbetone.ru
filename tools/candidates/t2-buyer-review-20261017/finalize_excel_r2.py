"""Preserve native workbook; apply authored text and scoped print layout only."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from io import BytesIO
import re,json,html,shutil,copy
from lxml import etree as E

P=Path(__file__).resolve().parent
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
N='{'+ns['s']+'}'
out=P/'final-files'; out.mkdir(exist_ok=True)
for p in (P/'r2-files').iterdir(): shutil.copy2(p,out/p.name)
source=P/'r2-files/03-opis-peredavaemogo-komplekta.xlsx'
edits=json.loads((P/'r2-excel-text-edits.json').read_text())
authored_values=json.loads((P/'r2-artifact-authored-text.json').read_text())
assert authored_values==edits
names=['Опись','Как заполнять','Виды','Пример заполнения']
changed={}; log=[]
with ZipFile(source) as z:
 styles=E.fromstring(z.read('xl/styles.xml'))
 xfs=styles.find('s:cellXfs',ns)
 styles_raw=z.read('xl/styles.xml').decode()
 original_styles_count=len(xfs)
 style_cache={}
 for i,name in enumerate(names,1):
  part=f'xl/worksheets/sheet{i}.xml'
  raw=z.read(part).decode()
  for address,want in edits[name].items():
   value=authored_values[name][address]
   assert value==want
   pattern=r'(<c\b[^>]*\br="'+address+r'"[^>]*>)(.*?)(</c>)'
   m=re.search(pattern,raw); assert m
   before=''.join(E.fromstring(m[0]).itertext())
   raw=raw[:m.start(2)]+'<is><t>'+html.escape(value,quote=False)+'</t></is>'+raw[m.end(2):]
   log.append({'sheet':name,'cell':address,'before':before,'after':value})
  # Print-only properties are set in OOXML because artifact-tool exposes no
  # pageLayout API. Preserve validation, formula, merge, style and value blocks.
  heights={1:{1:26,2:48,4:24,5:24,6:24,8:28,10:32,132:28,135:38,136:40},
           2:{},3:{},4:{1:26,2:32,4:36,5:48,6:48,7:48,8:48,10:36,12:24,13:24,14:28}}[i]
  for row,height in heights.items():
   def row_update(m):
    tag=re.sub(r'\s(?:ht|customHeight)="[^"]*"','',m[0])
    return tag[:-1]+f' ht="{height}" customHeight="1">'
   raw,n=re.subn(r'<row\b[^>]*\br="'+str(row)+r'"[^>]*>',row_update,raw,count=1)
   assert n==1,(i,row)
  if i==1:
   raw,n=re.subn(r'<col\s+width="5"([^>]*min="1" max="1"[^>]*)/>',r'<col width="9"\1/>',raw,count=1)
   assert n==1
  for address in ({1:['D133','B135','G135'],2:['A4','A5','A6','A7','A8','A9','A12','A13','A14','A15']}.get(i,[])):
   pattern=r'<c\b[^>]*\br="'+address+r'"[^>]*>'
   m=re.search(pattern,raw); assert m
   oldstyle=int(re.search(r'\bs="(\d+)"',m[0])[1])
   if oldstyle not in style_cache:
    xf=copy.deepcopy(xfs[oldstyle]); align=xf.find('s:alignment',ns)
    if align is None: align=E.SubElement(xf,N+'alignment')
    align.set('wrapText','1');align.set('vertical','top');xf.set('applyAlignment','1')
    style_cache[oldstyle]=len(xfs);xfs.append(xf)
   tag=re.sub(r'\bs="\d+"',f's="{style_cache[oldstyle]}"',m[0])
   raw=raw[:m.start()]+tag+raw[m.end():]
  raw,n=re.subn(r'<pageSetUpPr[^>]*/>', '<pageSetUpPr fitToPage="1" autoPageBreaks="0"/>',raw,count=1)
  assert n==1
  raw=re.sub(r'<pageMargins[^>]*/>','<pageMargins left="0.25" right="0.25" top="0.3" bottom="0.3" header="0.15" footer="0.15"/>',raw,count=1)
  setup=f'<pageSetup paperSize="9" orientation="{"landscape" if i in (1,4) else "portrait"}" fitToWidth="1" fitToHeight="{3 if i==1 else 1}" useFirstPageNumber="0"/>'
  raw=re.sub(r'(<pageMargins[^>]*/>)',lambda m:m[0]+setup,raw,count=1)
  changed[part]=raw.encode()
 # Keep all original styles intact; append only the targeted wrapping variants.
 xfs.set('count',str(len(xfs)))
 styles_raw=re.sub(r'<cellXfs\b[^>]*>.*?</cellXfs>',lambda m:E.tostring(xfs,encoding='unicode'),styles_raw,count=1)
 changed['xl/styles.xml']=styles_raw.encode()
 comments=z.read('xl/comments/comment1.xml').decode()
 comment_edits={'A10':'Порядковый номер рассчитывается автоматически. Заполняйте строки последовательно, без пропусков.',
                'E10':'Номер и дата акта выполненных работ, к которому относится передаваемый документ.',
                'H10':'Форма передаваемого документа: оригинал или копия.'}
 for address,text in comment_edits.items():
  pattern=r'(<comment\b[^>]*\bref="'+address+r'"[^>]*><text><t>)(.*?)(</t></text></comment>)'
  comments,n=re.subn(pattern,lambda m:m[1]+html.escape(text,quote=False)+m[3],comments,count=1)
  assert n==1
 changed['xl/comments/comment1.xml']=comments.encode()
 workbook=z.read('xl/workbook.xml').decode()
 defs='<definedNames>'
 for i,(name,area) in enumerate(zip(names,['$A$1:$I$136','$A$1:$B$18','$A$1:$E$15','$A$1:$I$14'])):
  defs+=f'<definedName name="_xlnm.Print_Area" localSheetId="{i}">\'{name}\'!{area}</definedName>'
 defs+='<definedName name="_xlnm.Print_Titles" localSheetId="0">\'Опись\'!$10:$10</definedName></definedNames>'
 workbook,n=re.subn(r'<definedNames\s*/>|<definedNames>.*?</definedNames>',defs,workbook,count=1)
 assert n==1
 changed['xl/workbook.xml']=workbook.encode()
 data=BytesIO()
 with ZipFile(data,'w',ZIP_DEFLATED) as new:
  for info in z.infolist(): new.writestr(info,changed.get(info.filename,z.read(info.filename)))
 (out/source.name).write_bytes(data.getvalue())
(P/'r2-excel-final-change-log.json').write_text(json.dumps({'authorization':'Owner: Исправляй (17.10.2026)','text_changes':log,'comment_changes':comment_edits,'print_changes':{'paper':'A4','Опись':'landscape, fit 1 wide / 3 high, repeated row 10, area A1:I136','Как заполнять':'portrait, one page, area A1:B18','Виды':'portrait, one page, area A1:E15','Пример заполнения':'landscape, one page, area A1:I14','additional':'Scoped row heights and wrapping for clipped instructions/headers/signatures; column A width 9 on Опись to fit labels. Existing style definitions preserved; wrapping variants appended.'}},ensure_ascii=False,indent=2))
print('FINAL_XLSX_TEXT_EDITS',len(log))
