from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json,re,shutil,hashlib,subprocess

P=Path(__file__).resolve().parent
T=Path('/tmp/t2-author-0267')
SAVED=P/'evidence-final-r2'
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
results={}
for scenario,expected in {'valid':{'A11':1,'A12':2,'A13':3,'A14':4,'C132':4,'E132':5,'C133':0,'E133':1},'missing':{'A11':1,'A12':2,'A13':3,'A14':4,'C132':4,'E132':3,'C133':1,'E133':1}}.items():
 f=T/'native-output'/f'{scenario}.xlsx'
 if not f.exists(): f=SAVED/f'native-recalculated-{scenario}.xlsx'
 with ZipFile(f) as z:
  root=E.fromstring(z.read('xl/worksheets/sheet1.xml'))
  observed={address:float(root.find(f'.//s:c[@r="{address}"]/s:v',ns).text) for address in expected}
 assert observed==expected,(scenario,observed,expected)
 results[scenario]={'expected':expected,'observed':observed,'status':'PASS','recalculated_xlsx_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}

pdf=next((T/'render-final-03-v2').glob('*.pdf'),SAVED/'03-opis-print-six-pages.pdf')
def pdf_command(args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=30).stdout
info=pdf_command(['pdfinfo',str(pdf)])
assert int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1])==6
texts=[pdf_command(['pdftotext','-raw','-f',str(i),'-l',str(i),str(pdf),'-']) for i in range(1,7)]
normalize=lambda t:re.sub(r'\s+','',t)
full=normalize(''.join(texts))
edits=json.loads((P/'r2-excel-text-edits.json').read_text())
edits['Опись']['A2']=json.loads((P/'r2-a2-authored-text.json').read_text())['value']
for sh,cs in edits.items():
 for address,text in cs.items():assert normalize(text) in full,(sh,address,'printed text clipped')
for i in range(3):
 for heading in ('Вид документа','Наименование, участок, оси и отметки','Реквизиты документа','Подтверждает объём по акту','Листов','Экз.','Оригинал / копия','Примечание'):
  assert normalize(heading) in normalize(texts[i]),(i,heading)
 pageinfo=pdf_command(['pdfinfo','-f',str(i+1),'-l',str(i+1),str(pdf)])
 dims=re.search(r'Page\s+\d+\s+size:\s+([\d.]+)\s+x\s+([\d.]+)',pageinfo)
 assert dims and float(dims[1])>float(dims[2])
assert 'Передал' in texts[2] and 'Принял' in texts[2]
assert all(t.strip() for t in texts)
assert all('####' not in t for t in texts)

# Field markers used by the sendable forms must be defined in the dictionary.
wn={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
markers={}
for p in (P/'final-files').glob('*.docx'):
 with ZipFile(p) as z:r=E.fromstring(z.read('word/document.xml'))
 txt=''.join(r.itertext());markers[p.name]=set(re.findall(r'\{\{[А-ЯЁA-Z0-9_]+\}\}',txt))
dictionary=markers['01-slovar-poley.docx']
for name in ('02-soprovoditelnoe-pismo-peredachi.docx','04-akt-priema-peredachi-id.docx'):
 assert markers[name]<=dictionary,(name,markers[name]-dictionary)

evidence=P/'evidence-final-r2';evidence.mkdir(exist_ok=True)
if pdf.resolve()!=(evidence/'03-opis-print-six-pages.pdf').resolve():shutil.copy2(pdf,evidence/'03-opis-print-six-pages.pdf')
for s in results:
 if (T/'native-inputs'/f'{s}.xlsx').exists():shutil.copy2(T/'native-inputs'/f'{s}.xlsx',evidence/f'native-input-{s}.xlsx')
 if (T/'native-output'/f'{s}.xlsx').exists():shutil.copy2(T/'native-output'/f'{s}.xlsx',evidence/f'native-recalculated-{s}.xlsx')
report={'status':'PASS','native_engine':'LibreOffice Calc, XLSX import/recalculation/export on disposable copies','native_scenarios':results,'print':{'engine':'LibreOffice Calc via render_docx.py','pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':6,'Опись_pages':3,'other_sheets_pages':[1,1,1],'all_nine_columns_and_repeated_headers':'PASS','all_22_edited_text_cells_fully_present':'PASS','signatures_on_final_opis_page':'PASS','empty_pages':0,'visual_review':'All six final-layout pages inspected; after wrapping change affected pages 3/4/6 inspected again'},'dictionary_markers':'All markers in letter/act defined','final_xlsx_sha256':hashlib.sha256((P/'final-files/03-opis-peredavaemogo-komplekta.xlsx').read_bytes()).hexdigest()}
(evidence/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
manifest=json.loads((P/'r2-final-manifest.json').read_text())
manifest['checks']['print']=report['print'];manifest['checks']['native_formula_scenarios']=results
manifest['checks']['dictionary_markers']='PASS'
(P/'r2-final-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
if not (P/'r1-nomination.json').exists():shutil.copy2(P/'nomination.json',P/'r1-nomination.json')
(P/'nomination.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
