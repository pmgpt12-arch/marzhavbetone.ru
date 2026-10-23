from pathlib import Path
import json,hashlib,base64,subprocess
p=Path('/tmp/nsp-avans-20261023');d=p/'print-diagnostic';rows=[]
for tag in ['latin','cyrillic']:
 f=d/'lo'/(tag+'.pdf');txt=subprocess.check_output(['pdftotext',str(f),'-'],text=True,timeout=20)
 assert 'INCLUDED-'+tag in txt and 'OUTSIDE-AREA-'not in txt
 rows.append({'tag':tag,'source_sha256':hashlib.sha256((d/(tag+'.xlsx')).read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'outside_marker_printed':False,'status':'PASS','text':txt})
(d/'LO_VERIFICATION.json').write_text(json.dumps({'engine':'bundled LibreOffice via soffice','native_excel_acceptance':False,'files':rows},ensure_ascii=False,indent=2))
files=[p/'print_diag.mjs',p/'patch_print_diag.py',Path(__file__),d/'LO_VERIFICATION.json']+[d/(tag+suffix)for tag in ['latin','cyrillic']for suffix in ['.png','-base.xlsx','-inspect.json']]+[d/'lo'/(tag+'.pdf')for tag in ['latin','cyrillic']]
pack=[{'path':str(f.relative_to(p)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'base64':base64.b64encode(f.read_bytes()).decode()}for f in files]
(p/'print-proof-transfer.json').write_text(json.dumps(pack))
print(len(pack))
