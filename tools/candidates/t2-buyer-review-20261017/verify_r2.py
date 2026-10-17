from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED,ZipInfo
import hashlib,json,re,subprocess
from io import BytesIO
from lxml import etree as E
P=Path(__file__).resolve().parent
out=P/'r2-files'
old=ZipFile(P/'T2-peredacha-ID-6-files-business-R1.zip')
name='03-opis-peredavaemogo-komplekta.xlsx'
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
a=ZipFile(BytesIO(old.read(name))); b=ZipFile(out/name)
assert a.namelist()==b.namelist()
delta=[n for n in a.namelist() if a.read(n)!=b.read(n)]
assert delta==['xl/worksheets/sheet1.xml'],delta
cell=r'<c\b[^>]*\br="A2"[^>]*>.*?</c>'
assert re.sub(cell,'<A2/>',a.read(delta[0]).decode())==re.sub(cell,'<A2/>',b.read(delta[0]).decode())
f=lambda z:{(p,c.get('r')):E.tostring(c.find('s:f',ns)) for p in z.namelist() if p.startswith('xl/worksheets/') and p.endswith('.xml') for c in E.fromstring(z.read(p)).findall('.//s:c',ns) if c.find('s:f',ns) is not None}
assert f(a)==f(b)
files=sorted(out.iterdir()); assert len(files)==6 and set(x.name for x in files)==set(old.namelist())
zipout=P/'T2-peredacha-ID-6-files-business-R2-DRAFT.zip'
with ZipFile(zipout,'w',ZIP_DEFLATED,compresslevel=9) as z:
 for p in files:
  i=ZipInfo(p.name,(2026,10,17,0,0,0));i.compress_type=ZIP_DEFLATED;i.external_attr=0o100644<<16
  z.writestr(i,p.read_bytes())
with ZipFile(zipout) as z:
 assert z.testzip() is None
 for p in files: assert z.read(p.name)==p.read_bytes()
gate=subprocess.run(['python3',str(P.parents[1]/'editorial_business_style_gate.py'),str(zipout)],capture_output=True,text=True,timeout=30)
assert gate.returncode==1 and 'Что эта опись не делает' in gate.stderr, (gate.returncode,gate.stdout,gate.stderr)
manifest={'status':'DRAFT_BLOCKED_SEMANTIC_EDITORIAL_AND_PRINT_REVIEW','source_commit':'c648867bcc698f49f2da1bedaa14438e039ceeab','source_zip_sha256':hashlib.sha256((P/'T2-peredacha-ID-6-files-business-R1.zip').read_bytes()).hexdigest(),'zip_name':zipout.name,'zip_sha256':hashlib.sha256(zipout.read_bytes()).hexdigest(),'zip_bytes':zipout.stat().st_size,'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'changed_vs_R1':p.read_bytes()!=old.read(p.name)} for p in files],'checks':{'crc':'PASS','exact_six_names':'PASS','excel_only_A2_changed':'PASS','formula_xml_identical':'PASS','formula_count':len(f(a)),'other_cells_and_native_features':'BYTE_IDENTICAL','automatic_editorial':gate.stdout.strip(),'semantic_editorial':'BLOCKED: unchanged sheet Как заполнять contains Что эта опись не делает and explanatory disclaimers','print':'PENDING_RENDER','production':'NOT_TOUCHED'}}
manifest['checks']['automatic_editorial']=gate.stderr.strip()
manifest['checks']['print']={'status':'FAIL_EXISTING_IN_R1','engine':'LibreOffice via documents/render_docx.py','R1_workbook_pages':13,'R2_workbook_pages':13,'expected_workbook_pages':6,'original_print_areas':[],'original_print_titles':[],'observation':'Опись spans eight pages across two horizontal sections; empty pages and split columns observed. Other cells and print OOXML remain byte-identical.'}
manifest['checks']['word_render']={'01':3,'02':1,'04':1,'05':5,'empty_pages':0}
manifest['checks']['pdf_instruction']={'unchanged_sha256':'298fa091c81f491669439a33251fac4e9165da14c48c481a3840193732df1357','pages':1,'file_index_00_05':'matches exact six members; no filename hyperlinks present'}
(P/'r2-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps(manifest,ensure_ascii=False,indent=2))
