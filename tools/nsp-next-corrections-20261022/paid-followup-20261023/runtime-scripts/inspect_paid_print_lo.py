from pathlib import Path
import subprocess,json,xml.etree.ElementTree as E,statistics,re
P=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022/paid-followup-20261023');V=P/'visual-paid-print-lo';V.mkdir(exist_ok=True);out=[]
for i,p in enumerate(sorted((P/'rendered-paid-print-v2').glob('*.pdf')),1):
 pages=subprocess.check_output(['pdftotext','-layout',str(p),'-'],text=True).split('\f')
 bbox=E.fromstring(subprocess.check_output(['pdftotext','-bbox',str(p),'-']))
 rows=[]
 for j,page in enumerate([x for x in bbox.iter()if x.tag.endswith('page')],1):
  words=[w for w in page.iter()if w.tag.endswith('word')and(w.text or'').strip()];heights=[float(w.get('yMax'))-float(w.get('yMin'))for w in words]
  rows.append({'page':j,'width_pt':page.get('width'),'height_pt':page.get('height'),'word_count':len(words),'min_word_bbox_height_pt':round(min(heights),2)if heights else None,'median_word_bbox_height_pt':round(statistics.median(heights),2)if heights else None,'start':pages[j-1].strip()[:180]})
 subprocess.run(['pdftoppm','-scale-to','1400','-png',str(p),str(V/('b'+str(i)))],capture_output=True,check=True,timeout=40)
 out.append({'file':p.name,'pages':rows})
(P/'P5_PRINT_LO_LAYOUT_METRICS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
