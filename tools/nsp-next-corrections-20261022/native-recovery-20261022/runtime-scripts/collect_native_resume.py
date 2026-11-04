from pathlib import Path
from zipfile import ZipFile
from PIL import Image,ImageDraw,ImageOps
from copy import deepcopy
import subprocess,json,hashlib,re,shutil,xml.etree.ElementTree as E,time
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';H=R/'tools/nsp-next-corrections-20261022';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011');D=Q/'native-resume-20261022';O=D/'visual';O.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
word=[];native=[]
for c in ['word','native']:
 for rp in sorted((N/'results'/c).glob('nsp-next-*/report.xml')):
  dest=D/'evidence'/c/rp.parent.name;shutil.copytree(rp.parent,dest,dirs_exist_ok=True);rt=E.parse(rp).getroot()
  if c=='word':
   job=E.parse(H/'prepared-office'/c/rp.parent.name/'job.xml').getroot()
   for f in rt.findall('file'):
    tag=f.get('tag');src=next(x for x in job.findall('file')if x.get('tag')==tag);assert f.find('result').get('source_sha256')==src.get('sha256');p=rp.parent/(tag+'.pdf');assert sha(p)==f.get('pdf_sha256');info=subprocess.check_output(['pdfinfo',str(p)],text=True);pages=int(re.search(r'Pages:\s+(\d+)',info)[1]);subprocess.run(['pdftoppm','-scale-to','1050','-png',str(p),str(O/tag)],capture_output=True,check=True,timeout=30)
    ims=[]
    for png in sorted(O.glob(tag+'-*.png')):
     if png.name.endswith('-contact.png'):continue
     im=Image.open(png).convert('RGB');im=ImageOps.expand(im,border=(5,22,5,5),fill='white');ImageDraw.Draw(im).text((10,3),png.stem,fill='black');ims.append(im)
    cw=max(x.width for x in ims);ch=max(x.height for x in ims);cols=min(2,len(ims));canvas=Image.new('RGB',(cols*cw,((len(ims)+cols-1)//cols)*ch),'#999999')
    for i,im in enumerate(ims):canvas.paste(im,((i%cols)*cw,(i//cols)*ch))
    canvas.save(O/(tag+'-contact.png'));word.append({'job':rp.parent.name,'tag':tag,'source_file':src.get('name'),'source_sha256':src.get('sha256'),'technical_status':f.get('status'),'reported_pages':f.find('result').get('pages'),'actual_pdf_pages':pages,'pdf_sha256':sha(p),'visual_review':'PENDING','link_targets':subprocess.run(['pdfinfo','-url',str(p)],capture_output=True,text=True).stdout})
  else:
   pdfs=[]
   for p in rp.parent.glob('*.pdf'):
    text=subprocess.check_output(['pdftotext','-layout',str(p),'-'],text=True);pages=text.split('\f')[:-1];pdfs.append({'name':p.name,'sha256':sha(p),'pages':len(pages),'text_empty_pages':[i+1 for i,x in enumerate(pages)if not x.strip()],'print_acceptance':'BLOCKED_UNTIL_VISUAL_REVIEW_AND_NATIVE_OPENING_MODE_DIAGNOSIS'})
   native.append({'job':rp.parent.name,'technical_status':rt.get('status'),'scope':rt.get('scope'),'excel_version':rt.get('excel_version'),'report_sha256':sha(rp),'checks':[x.attrib for x in rt.findall('check')],'open_mode_proven':rt.find('open_mode')is not None,'pdfs':pdfs})
(D/'WORD_NATIVE_REVIEW.json').write_text(json.dumps(word,ensure_ascii=False,indent=2));(D/'EXCEL_NATIVE_REVIEW.json').write_text(json.dumps(native,ensure_ascii=False,indent=2))
# Revised harness only; immutable candidate bytes are copied exactly, not authored again.
src=H/'prepared-office/native/nsp-next-excel-5-20261022';rt=E.parse(src/'job.xml').getroot();rt.set('id','nsp-next-excel-5-coercion-v2-20261022');rt.set('hypothesis','Distinguish Excel numeric-string coercion from truly nonnumeric input; candidate unchanged');f=rt.find('file');case=next(x for x in f.findall('case')if x.get('name')=='text');case.set('name','numeric-string-coercion');ex=case.find('expect');ex.set('kind','number');ex.set('value','20');E.SubElement(case,'expect',sheet='Реестр',cell='D4',kind='number',value='2');neg=deepcopy(case);neg.set('name','nonnumeric-text');next(x for x in neg.findall('set')if x.get('cell')=='D4'and x.get('kind')=='text').set('value','два')
for x in list(neg.findall('expect')):neg.remove(x)
E.SubElement(neg,'expect',sheet='Реестр',cell='I4',kind='text',value='НЕ ЗАВЕРШЕНО');f.append(neg);job=D/'prepared-native'/rt.get('id');job.mkdir(parents=True,exist_ok=True);E.ElementTree(rt).write(job/'job.xml',encoding='utf-8',xml_declaration=True);shutil.copyfile(src/f.get('name'),job/f.get('name'));assert sha(job/f.get('name'))==f.get('sha256')
(D/'P2_HARNESS_DIAGNOSIS.json').write_text(json.dumps({'old_job':'nsp-next-excel-5-20261022','old_receipt':'FAIL','actual':'System.Double:20','expected':'НЕ ЗАВЕРШЕНО','diagnosis':'Numeric string 2 entered through Excel COM can be coerced to number; no formula edit justified until separate nonnumeric control','new_hypothesis_job':rt.get('id'),'status':'PREPARED_NOT_SUBMITTED_CURRENT_JOB_6_UNACKNOWLEDGED','candidate_sha256_unchanged':f.get('sha256')},ensure_ascii=False,indent=2))
print('COLLECTED_WORD',[(x['tag'],x['actual_pdf_pages'])for x in word],flush=True);print('COLLECTED_EXCEL',[(x['job'],x['technical_status'])for x in native],flush=True);print('PDF_PRINT_FLAGS',[(x['job'],x['pdfs'])for x in native],flush=True)
