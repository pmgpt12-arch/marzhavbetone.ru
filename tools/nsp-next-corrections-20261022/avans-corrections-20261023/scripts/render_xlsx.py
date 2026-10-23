from pathlib import Path
import subprocess,json
P=Path(__file__).resolve().parent;out=P/'rendered-xlsx';out.mkdir(exist_ok=True)
r=subprocess.run(['soffice','-env:UserInstallation=file://'+str(P/'lo-xlsx-profile'),'--headless','--convert-to','pdf','--outdir',str(out),str(P/'output/02-reestr-izyatiy-po-obektu.xlsx')],capture_output=True,text=True,timeout=90)
(P/'proof/XLSX_LO_RENDER.json').write_text(json.dumps({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},ensure_ascii=False,indent=2))
assert r.returncode==0,(r.stdout,r.stderr)
pdf=out/'02-reestr-izyatiy-po-obektu.pdf';assert pdf.is_file()
info=subprocess.check_output(['pdfinfo',str(pdf)],text=True);print(info)
subprocess.run(['pdftoppm','-scale-to','1800','-png',str(pdf),str(out/'page')],check=True,capture_output=True,timeout=45)
