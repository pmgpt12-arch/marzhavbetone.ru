from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
from lxml import etree as E
import hashlib,json,subprocess
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';D=P/'paid-print-v4';D.mkdir(exist_ok=True);src=P/'paid-print-v2/29-opis-dokazatelstv-po-defektu.xlsx';dst=D/src.name;N='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
with ZipFile(src)as z:
 infos=z.infolist();base={i.filename:z.read(i)for i in infos};parts=dict(base);w=E.fromstring(base['xl/workbook.xml']);names=w.find(N+'definedNames');plans=[]
 for idx,name,ranges,title in [(1,'Опись',['$A$6:$H$206','$I$6:$O$206','$P$6:$U$206'],'$A:$C,$6:$6'),(5,'Пример заполнения',['$A$5:$H$9','$I$5:$O$9','$P$5:$U$9','$A$13:$F$18'],'$A:$C')]:
  prefix="'"+name+"'!";area=next(n for n in names if n.get('name')=='_xlnm.Print_Area'and n.get('localSheetId')==str(idx));area.text=','.join(prefix+r for r in ranges)
  titles=next(n for n in names if n.get('name')=='_xlnm.Print_Titles'and n.get('localSheetId')==str(idx));titles.text=','.join(prefix+t for t in title.split(','))
  part='xl/worksheets/sheet'+str(idx+1)+'.xml';ws=E.fromstring(base[part]);assert ws.find(N+'headerFooter')is None
  hf=E.Element(N+'headerFooter');E.SubElement(hf,N+'oddHeader').text='&L'+name+' — группы граф; сверяйте № документа';E.SubElement(hf,N+'oddFooter').text='&LПравила статусов и пояснения — в книге под таблицей&C&P / &N'
  setup=ws.find(N+'pageSetup');ws.insert(list(ws).index(setup)+1,hf)
  clean=deepcopy(ws);clean.remove(clean.find(N+'headerFooter'));assert E.tostring(clean,method='c14n')==E.tostring(E.fromstring(base[part]),method='c14n')
  parts[part]=E.tostring(ws,encoding='UTF-8',xml_declaration=True);plans.append({'sheet':name,'print_ranges':ranges,'repeat':title,'excluded_from_table_print':'Long merged introductory and explanatory notes remain in workbook; footer directs reader to them; all data rows and all 21 data columns printed in explicit groups'})
 parts['xl/workbook.xml']=E.tostring(w,encoding='UTF-8',xml_declaration=True)
 with ZipFile(dst,'w')as out:
  for i in infos:out.writestr(deepcopy(i),parts[i.filename])
 with ZipFile(dst)as out:
  assert out.testzip()is None and all(out.read(n)==base[n]for n in base if n not in ('xl/workbook.xml','xl/worksheets/sheet2.xml','xl/worksheets/sheet6.xml'))
r={'file':dst.name,'base_v2_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'new_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'change':'Readable explicit column groups with repeated document identity; no fragmented merged headings from other groups','plans':plans,'cell_formula_style_and_validation_unchanged':True,'status':'PENDING_NATIVE_AND_FULL_VISUAL_REVIEW','native_blocker':'Excel COM activation 0x80080005 before opening source'}
out=P/'rendered-paid-print-v4';out.mkdir(exist_ok=True)
subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/nsp-p5-print-v4-20261023','--headless','--convert-to','pdf','--outdir',str(out),str(dst)],capture_output=True,check=True,timeout=60)
pdf=out/(dst.stem+'.pdf');r['lo_pdf_info']=subprocess.check_output(['pdfinfo',str(pdf)],text=True);r['lo_pdf_sha256']=hashlib.sha256(pdf.read_bytes()).hexdigest()
(D/'MANIFEST.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False),flush=True)
