import pathlib,json,hashlib,zipfile,copy,re,subprocess,time,datetime
from lxml import etree as E
import fitz
from PIL import Image,ImageDraw
R=pathlib.Path('/workspace/scratch/f25d74acc3f7');O=R/'p13-checkbox-candidate-20261006';I=R/'daywork-next-queue-20261006/p13';p=json.loads((I/'passport.json').read_text())['required_inputs'][0];src=pathlib.Path(p['local_path']);N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+N['w']+'}';XML='{http://www.w3.org/XML/1998/namespace}'
def sha(x):return hashlib.sha256(x.read_bytes()).hexdigest()
assert sha(src)==p['sha256'];sourcebefore=sha(src);new=O/'p13-62-checkbox-explicit-font-candidate.docx'
with zipfile.ZipFile(src)as z:
 raw=z.read('word/document.xml');tree=E.fromstring(raw);ps=tree.findall('.//w:p',N);para=ps[16];assert len(para)==1 and para[0].tag==W+'r';run=para[0];assert len(run)==1 and run[0].tag==W+'t';txt=run[0].text;assert txt.startswith('☐  ');before=E.tostring(para);run[0].text=txt[1:];run[0].set(XML+'space','preserve');glyph=E.Element(W+'r');pr=E.SubElement(glyph,W+'rPr');fonts=E.SubElement(pr,W+'rFonts')
 for k in ['ascii','hAnsi','eastAsia','cs']:fonts.set(W+k,'DejaVu Sans')
 t=E.SubElement(glyph,W+'t');t.text='☐';para.insert(0,glyph);changed=E.tostring(tree,encoding='UTF-8',xml_declaration=True,standalone=True)
 with zipfile.ZipFile(new,'w')as out:
  for info in z.infolist():out.writestr(copy.copy(info),changed if info.filename=='word/document.xml'else z.read(info.filename))
 sourceparts={n:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()}
with zipfile.ZipFile(new)as z:
 candidateparts={n:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()};assert sourceparts.keys()==candidateparts.keys();assert [n for n in sourceparts if sourceparts[n]!=candidateparts[n]]==['word/document.xml'];ct=E.fromstring(z.read('word/document.xml'));cp=ct.findall('.//w:p',N);sp=E.fromstring(raw).findall('.//w:p',N);assert len(cp)==len(sp)
 for j in range(len(cp)):
  if j!=16:assert E.tostring(cp[j],method='c14n',exclusive=True)==E.tostring(sp[j],method='c14n',exclusive=True),j
 assert ''.join(cp[16].itertext())==''.join(sp[16].itertext());reversedpara=copy.deepcopy(cp[16]);reversedpara.remove(reversedpara[0]);reversedpara[0][0].text='☐'+reversedpara[0][0].text;del reversedpara[0][0].attrib[XML+'space'];assert E.tostring(reversedpara,method='c14n',exclusive=True)==E.tostring(sp[16],method='c14n',exclusive=True)
protection={'source_sha256':sourcebefore,'candidate_sha256':sha(new),'changed_zip_parts':['word/document.xml'],'all_other_parts_byte_identical':True,'all_other_paragraphs_canonical_identical':True,'all_text_exact':True,'changed_paragraph':16,'source_run_xml':before.decode(),'candidate_run_xml':E.tostring(cp[16],encoding='unicode'),'reverse_declared_change_recovers_exact_original_paragraph':True,'bold_and_paragraph_style_unchanged':True}
(O/'source-protection.json').write_text(json.dumps(protection,ensure_ascii=False,indent=2)+'\n');passport={'task_id':'p13-checkbox-candidate-experiment-20261006','execution_pattern':'one_shot','primary_result':'One minimal explicit-checkbox-font disposable candidate experiment','feedback_loop_required':False,'checkpoint_policy':'verified_only','inputs':[p,{'path':str(R/'p13-checkbox-rootcause-20261006/result.json'),'sha256':sha(R/'p13-checkbox-rootcause-20261006/result.json')}],'scope':'Dedicated candidate/evidence directory only; source immutable; only sourceparagraph16 U2610 explicitDejaVu Sans run declaration plus xml:space preserve for split remainder','new_hypothesis':'Explicit glyph-capable font for first control avoids observed local first-occurrence font fallback/export omission','executor':'Python/nativeWriter/PDF tools; no API/model','budgets':{'subprocess_seconds':45,'Writer_conversions':1,'automatic_retries':0,'api_usd':0},'DONE':'Source62/PDF62checkboxes and93normalized textunits; source unchanged; declared minimal XML diff protection; PNG validation and allpagevisual review; independent acceptance before confirmedfix','not_claimed':['Exact internal renderer cause','Native Word/server compatibility','legal/financial acceptance','SaleReady']};(O/'passport.json').write_text(json.dumps(passport,ensure_ascii=False,indent=2)+'\n');rec={'status':'PREFLIGHT_PASS','commands':[],'source_before':sourcebefore,'source':p,'candidate':protection['candidate_sha256'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def save():(O/'receipt.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
def cmd(a):
 start=time.monotonic()
 try:c=subprocess.run(a,capture_output=True,text=True,timeout=45)
 except subprocess.TimeoutExpired:rec['commands'].append({'argv':a,'status':'TIMEOUT_NO_RETRY','seconds':time.monotonic()-start});rec['status']='STOP';save();raise
 rec['commands'].append({'argv':a,'exit_code':c.returncode,'stdout':c.stdout,'stderr':c.stderr,'seconds':time.monotonic()-start});save();assert c.returncode==0
 return c.stdout
rec['version']=cmd(['soffice','--version']).strip();cmd(['soffice','-env:UserInstallation='+(O/'profile').as_uri(),'--headless','--convert-to','pdf','--outdir',str(O),str(new)]);pdf=O/(new.stem+'.pdf');assert pdf.exists();cmd(['pdftotext','-layout',str(pdf),str(O/'pdf-text.txt')]);cmd(['pdftoppm','-scale-to','1600','-png',str(pdf),str(O/'page')]);f=fitz.open(pdf);units=[]
for j,para in enumerate(sp):
 txt=''.join(x.text or ''for x in para.findall('.//w:t',N))
 if txt.strip():units.append({'locator':f'word/document.xml/paragraph:{j}','source_text':txt})
normalize=lambda s:re.sub(r'\s+','',s).replace('\u00ad','');text=(O/'pdf-text.txt').read_text()
for u in units:u['present_normalized']=normalize(u['source_text'])in normalize(text)
sourcecount=sum(u['source_text'].count('☐')for u in units);pdfcount=sum(chr(c[0])=='☐'for page in f for s in page.get_texttrace()for c in s['chars']);images=[]
for pimg in sorted(O.glob('page-*.png')):
 with Image.open(pimg)as im:im.verify()
 with Image.open(pimg)as im:im.load();images.append({'path':pimg.name,'sha256':sha(pimg),'pixels':list(im.size)})
assert len(images)==len(f);coverage={'units_checked':len(units),'unmatched':[u for u in units if not u['present_normalized']],'source_checkbox_count':sourcecount,'pdf_checkbox_count':pdfcount,'records':units};(O/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n');rec.update({'status':'PASS_PENDING_VISUAL_AND_INDEPENDENT_REVIEW'if not coverage['unmatched']and sourcecount==pdfcount==62 else'STOP_CANDIDATE_FAILED_NO_RETRY','pages':len(f),'png_validation':images,'unmatched_count':len(coverage['unmatched']),'source_checkbox_count':sourcecount,'pdf_checkbox_count':pdfcount,'units_checked':len(units),'source_after':sha(src),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});assert rec['source_after']==sourcebefore;save();pages=sorted(O.glob('page-*.png'));sheet=Image.new('RGB',(len(pages)*600,900),'#aaa');d=ImageDraw.Draw(sheet)
for j,pimg in enumerate(pages):
 im=Image.open(pimg).convert('RGB');im.thumbnail((590,850));sheet.paste(im,(j*600+(600-im.width)//2,30));d.text((j*600+10,8),pimg.name,fill='black')
sheet.save(O/'contact-sheet.png');print(rec['status'],len(f),len(units),len(coverage['unmatched']),sourcecount,pdfcount,flush=True)
