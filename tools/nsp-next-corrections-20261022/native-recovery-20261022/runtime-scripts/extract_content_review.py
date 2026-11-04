from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import subprocess,json,hashlib
Q=Path(__file__).resolve().parents[1];S=Q/'package-sources/products-storage';O=Q/'native-recovery-20261022/content';O.mkdir(exist_ok=True)
records=[]
for folder in ['11-bankrotstvo-genpodryadchika','13-raschet-metrami','07-uderzhaniya-shtrafy-zachety','03-dogovor-podryada','14-peredacha-id-pod-podpis','15-otvet-na-pretenziyu-baza','17-odnostoronniy-akt-i-zachet']:
 lines=[]
 for p in sorted((S/folder).iterdir()):
  if p.suffix not in ['.txt','.docx','.pdf']or p.name in ['MANIFEST.md','00-PISMO-POSLE-POKUPKI.txt']:continue
  if p.suffix=='.txt':t=p.read_text()
  elif p.suffix=='.pdf':t=subprocess.check_output(['pdftotext','-layout',str(p),'-'],text=True)
  else:
   with ZipFile(p)as z:
    n={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    rt=E.fromstring(z.read('word/document.xml'));t='\n'.join(''.join(x.xpath('.//w:t/text()',namespaces=n))for x in rt.xpath('//w:p',namespaces=n))
  lines+=['FILE: '+p.name,t,'']
  records.append({'folder':folder,'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'characters':len(t)})
 (O/(folder+'.txt')).write_text('\n'.join(lines))
(O/'INDEX.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print(json.dumps([{'folder':p.stem,'chars':p.stat().st_size}for p in O.glob('*.txt')],ensure_ascii=False))
