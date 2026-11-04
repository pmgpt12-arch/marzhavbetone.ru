from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from copy import deepcopy
import hashlib,json,subprocess
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';D=P/'paid-print-v3';D.mkdir(exist_ok=True);src=P/'paid-print-v2/29-opis-dokazatelstv-po-defektu.xlsx';dst=D/src.name;N='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
with ZipFile(src)as z:
 infos=z.infolist();parts={i.filename:z.read(i)for i in infos};w=E.fromstring(parts['xl/workbook.xml']);names=w.find(N+'definedNames')
 for idx,name,lastrow,header in [(1,'Опись',208,6),(5,'Пример заполнения',28,5)]:
  prefix="'"+name+"'!"
  area=next(n for n in names if n.get('name')=='_xlnm.Print_Area'and n.get('localSheetId')==str(idx));area.text=','.join(prefix+a for a in ['$A$1:$H$'+str(lastrow),'$I$1:$O$'+str(lastrow),'$P$1:$U$'+str(lastrow)])
  title=next(n for n in names if n.get('name')=='_xlnm.Print_Titles'and n.get('localSheetId')==str(idx));title.text=prefix+'$A:$C,'+prefix+'$'+str(header)+':$'+str(header)
 parts['xl/workbook.xml']=E.tostring(w,encoding='UTF-8',xml_declaration=True)
 with ZipFile(dst,'w')as out:
  for i in infos:out.writestr(deepcopy(i),parts[i.filename])
 with ZipFile(dst)as out:
  assert out.testzip()is None
  assert all(out.read(n)==z.read(n)for n in z.namelist()if n!='xl/workbook.xml')
r={'file':dst.name,'base_v2_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'new_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'change':'Three explicit groups A:H / I:O / P:U; repeated document identity A:C and table header rows; avoid unreadable 21-column shrink','all_worksheet_parts_and_other_parts_byte_exact':True,'status':'LO_AND_NATIVE_REVIEW_PENDING','native_blocker':'Excel COM activation 0x80080005 before opening source'}
(D/'MANIFEST.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
out=P/'rendered-paid-print-v3';out.mkdir(exist_ok=True)
subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/nsp-p5-print-v3-20261023','--headless','--convert-to','pdf','--outdir',str(out),str(dst)],check=True,capture_output=True,timeout=60)
pdf=out/(dst.stem+'.pdf');info=subprocess.check_output(['pdfinfo',str(pdf)],text=True);r['lo_pdf_info']=info;r['lo_pdf_sha256']=hashlib.sha256(pdf.read_bytes()).hexdigest()
(D/'MANIFEST.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False),flush=True)
