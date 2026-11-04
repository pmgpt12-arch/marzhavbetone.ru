from pathlib import Path
import subprocess,os,signal,tempfile,json,hashlib
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';D=P/'rendered-paid-print-v2';D.mkdir(exist_ok=True);out=[]
for src in sorted((P/'paid-print-v2').glob('*.xlsx')):
 profile=Path(tempfile.mkdtemp(prefix='nsp-paid-print-'))
 args=['libreoffice','-env:UserInstallation='+profile.as_uri(),'--headless','--convert-to','pdf','--outdir',str(D),str(src)]
 p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,text=True)
 try:a,b=p.communicate(timeout=60)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.communicate()
  raise
 assert p.returncode==0,(src.name,a,b);pdf=D/(src.stem+'.pdf');assert pdf.exists()
 info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
 out.append({'file':src.name,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'engine':'LibreOffice fallback render; NOT Excel native acceptance','pdf_info':info})
 print(src.name,info,flush=True)
(P/'P5_PRINT_V2_LO_RENDER.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
