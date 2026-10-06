"""Cached baseline factual lexical inventory. No product execution or legal judgment."""
from pathlib import Path
import subprocess,json,hashlib,re,zipfile,xml.etree.ElementTree as ET
import collections,datetime,time,bisect,posixpath,os,sys,concurrent.futures
R=Path(__file__).resolve().parent;REPO=Path("/home/denis/projects/marzhavbetone.ru");PIN="264d75a06d59de82602dc1bcef347913c44cc648"
W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}";X="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}";REL="{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
exec(compile((R/"lexical-grammar.py").read_text(),str(R/"lexical-grammar.py"),"exec"))
fullcode=re.compile(r"\b(?:Гражданск\w*|Градостроительн\w*|Налогов\w*|Трудов\w*|Земельн\w*|Жилищн\w*|Семейн\w*|Бюджетн\w*|Уголовн\w*|Арбитражн\w*|Гражданск\w*[- ]процессуальн\w*)\s+(?:процессуальн\w*\s+)?кодекс\w*(?:\s+(?:РФ|Российск\w*\s+Федераци\w*))?",re.I)
def h(b):return hashlib.sha256(b).hexdigest()
def save(path,d):path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
def git(*args):return subprocess.check_output(["git",*args],cwd=REPO,timeout=15)
def xmlpath(root,node):
 parent={c:p for p in root.iter() for c in p};parts=[]
 while node in parent:
  p=parent[node];sib=[c for c in p if c.tag==node.tag];parts.append(node.tag.split("}")[-1]+"["+str(sib.index(node)+1)+"]");node=p
 return "/"+root.tag.split("}")[-1]+"/"+"/".join(reversed(parts))
def extract_native(src):
 started=time.monotonic();file=Path(src["local_path"]);raw=file.read_bytes();assert h(raw)==src["sha256"]
 units=[];commands=[];metadata={"sha256":src["sha256"],"suffix":src["suffix"],"worker_pid":os.getpid(),"limitations":[]}
 def add(loc,text):
  if text and str(text).strip():units.append({"native_unit_index":len(units)+1,"location":loc,"text":str(text)})
 def cmd(argv):
  p=subprocess.run(argv,capture_output=True,timeout=25);commands.append({"argv":argv,"exit":p.returncode,"stdout_sha256":h(p.stdout),"stderr":p.stderr.decode(errors="replace")});assert p.returncode==0,(argv,p.stderr);return p.stdout
 if src["suffix"]==".docx":
  with zipfile.ZipFile(file) as z:
   parts=[n for n in z.namelist() if n=="word/document.xml" or re.fullmatch(r"word/(?:header\d+|footer\d+|footnotes|endnotes|comments)\.xml",n)]
   for part in parts:
    root=ET.fromstring(z.read(part));nonempty=0
    for ordinal,p in enumerate(root.iter(W+"p"),1):
     text="".join(t.text or "" for t in p.iter(W+"t"))
     if not text.strip():continue
     nonempty+=1;add({"kind":"docx_xml_paragraph","part":part,"xml_path":xmlpath(root,p),"global_paragraph_ordinal_including_empty":ordinal,"nonempty_paragraph_ordinal":nonempty},text)
   metadata["read_xml_parts"]=parts
   media=[n for n in z.namelist() if n.startswith("word/media/")]
   if media:metadata["limitations"].append({"kind":"EMBEDDED_MEDIA_NOT_OCR","members":media})
 elif src["suffix"]==".xlsx":
  with zipfile.ZipFile(file) as z:
   shared=[]
   if "xl/sharedStrings.xml" in z.namelist():shared=["".join(t.text or "" for t in si.iter(X+"t")) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(X+"si")]
   book=ET.fromstring(z.read("xl/workbook.xml"));targets={e.attrib["Id"]:e.attrib["Target"] for e in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))};sheets=[]
   for sheet in book.iter(X+"sheet"):
    target=targets[sheet.attrib[REL+"id"]];part=target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/"+target);name=sheet.attrib["name"];root=ET.fromstring(z.read(part))
    sheets.append({"sheet":name,"part":part,"state":sheet.attrib.get("state","visible")});add({"kind":"xlsx_sheet_title","sheet":name,"part":"xl/workbook.xml","xml_path":xmlpath(book,sheet),"attribute":"name"},name)
    for c in root.iter(X+"c"):
     dtype=c.attrib.get("t","n");v=c.find(X+"v");f=c.find(X+"f");loc={"kind":"xlsx_cell","sheet":name,"cell":c.attrib["r"],"part":part,"xml_path":xmlpath(root,c),"data_type":dtype}
     if f is not None:
      add(dict(loc,value_mode="stored_formula_no_recalculation"),"="+str(f.text or ""))
      if v is not None and v.text:add(dict(loc,kind="xlsx_cell_cache",value_mode="stored_cache_not_verified"),v.text)
     elif dtype=="s" and v is not None:add(dict(loc,value_mode="stored_shared_string"),shared[int(v.text)])
     elif dtype=="inlineStr":add(dict(loc,value_mode="stored_inline_string"),"".join(t.text or "" for t in c.iter(X+"t")))
     elif v is not None and v.text:add(dict(loc,value_mode="stored_value"),v.text)
    for tag in ["oddHeader","oddFooter","evenHeader","evenFooter","firstHeader","firstFooter"]:
     for e in root.iter(X+tag):add({"kind":"xlsx_header_footer","sheet":name,"part":part,"xml_path":xmlpath(root,e)},e.text)
    for e in root.iter(X+"dataValidation"):
     for attr in ["promptTitle","prompt","errorTitle","error"]:
      add({"kind":"xlsx_validation_text","sheet":name,"part":part,"xml_path":xmlpath(root,e),"attribute":attr,"sqref":e.attrib.get("sqref")},e.attrib.get(attr))
   for part in z.namelist():
    if re.fullmatch(r"xl/comments/comment\d+\.xml|xl/comments\d+\.xml",part):
     root=ET.fromstring(z.read(part))
     for e in root.iter(X+"comment"):add({"kind":"xlsx_comment","part":part,"cell":e.attrib.get("ref"),"xml_path":xmlpath(root,e)},"".join(t.text or "" for t in e.iter(X+"t")))
    if re.fullmatch(r"xl/(?:drawings/drawing\d+|charts/chart\d+)\.xml",part):
     root=ET.fromstring(z.read(part))
     for e in root.iter():
      if e.tag.split("}")[-1]=="t":add({"kind":"xlsx_drawing_chart_text","part":part,"xml_path":xmlpath(root,e)},e.text)
   for e in book.iter(X+"definedName"):add({"kind":"xlsx_defined_name","part":"xl/workbook.xml","xml_path":xmlpath(book,e),"name":e.attrib.get("name")},e.text)
   metadata["read_sheets"]=sheets;metadata["read_mode"]="native ZIP/XML; stored values/formulas/caches only"
   media=[n for n in z.namelist() if n.startswith("xl/media/")]
   if media:metadata["limitations"].append({"kind":"EMBEDDED_MEDIA_NOT_OCR","members":media})
 elif src["suffix"]==".txt":
  for line,text in enumerate(raw.decode("utf-8").splitlines(),1):add({"kind":"txt_line","physical_line":line},text)
 elif src["suffix"]==".pdf":
  out=R/"unique-pdf";out.mkdir(exist_ok=True);prefix=out/src["sha256"]
  info=cmd(["pdfinfo",str(file)]).decode();Path(str(prefix)+"-pdfinfo.txt").write_text(info);n=int(re.search(r"^Pages:\s*(\d+)",info,re.M).group(1))
  images=cmd(["pdfimages","-list",str(file)]).decode();Path(str(prefix)+"-pdfimages.txt").write_text(images);image_rows=[l for l in images.splitlines() if re.match(r"^\s*\d+\s+\d+\s+",l)]
  text=cmd(["pdftotext","-layout","-enc","UTF-8",str(file),"-"]).decode();Path(str(prefix)+"-raw-pdftotext.txt").write_text(text)
  pages=text.split("\f")
  if pages and pages[-1]=="":pages.pop()
  assert len(pages)==n,(len(pages),n);metadata["pdf_pages"]=[]
  for page,t in enumerate(pages,1):
   metadata["pdf_pages"].append({"page":page,"text_sha256":h(t.encode()),"characters":len(t),"physical_lines":len(t.splitlines()),"text_empty":not bool(t.strip())})
   add({"kind":"pdf_pdftotext_page","page":page,"extraction":"pdftotext -layout -enc UTF-8","text_sha256":h(t.encode()),"line_numbering":"1-based physical lines in this exact raw extracted page"},t)
  metadata["pdf_raw_text_sha256"]=h(text.encode());metadata["limitations"].append({"kind":"PDF_TEXT_LAYER_ONLY_NO_LAYOUT_OR_OCR_REVIEW","image_rows":image_rows,"empty_pages":[d["page"] for d in metadata["pdf_pages"] if d["text_empty"]]})
 else:raise ValueError(src["suffix"])
 if src["suffix"] in [".docx",".xlsx"]:
  with zipfile.ZipFile(file) as z:
   if "docProps/core.xml" in z.namelist():
    root=ET.fromstring(z.read("docProps/core.xml"))
    for e in root:
     if e.tag.split("}")[-1] in ["title","subject","description","keywords","category"]:add({"kind":"ooxml_core_titlefield","part":"docProps/core.xml","xml_path":xmlpath(root,e),"field":e.tag.split("}")[-1]},e.text)
 assert h(file.read_bytes())==src["sha256"];metadata["text_units"]=len(units);metadata["elapsed_seconds"]=time.monotonic()-started
 return {"sha256":src["sha256"],"units":units,"metadata":metadata,"commands":commands}
def annotate(sku,doc,filehash,units):
 occurrences=[];markers=[];kept=set()
 for i,u in enumerate(units,1):
  text=u["text"];uid=sku+":"+doc+":"+str(i);matches=list(article.finditer(text))
  def location(a,b):
   loc=dict(u["location"])
   if loc["kind"]=="pdf_pdftotext_page":
    loc.update(page_character_span=[a,b],physical_line_start=text.count("\n",0,a)+1,physical_line_end=text.count("\n",0,max(a,b-1))+1)
   return loc
  def row(a,b):
   qa,qb=max(0,a-70),min(len(text),b+100);kept.add(i)
   return {"sku":sku,"document":doc,"file_sha256":filehash,"unit_id":uid,"native_unit_index":i,"location":location(a,b),"span":[a,b],"short_quote":text[qa:qb],"quote_span":[qa,qb],"registry_norm_id":None,"normative_verdict":"NOT_VERIFIED"}
  for m in matches:
   literal=m.group();explicit=codepat.findall(literal);context=text
   bind="one_explicit_code_in_same_native_text_unit"
   if u["location"]["kind"]=="pdf_pdftotext_page":
    a=text.rfind("\n",0,m.start())+1;b=text.find("\n",m.end());b=len(text) if b<0 else b
    context=text[a:b] if "\n" not in literal else "";bind="one_explicit_code_in_same_pdf_physical_line"
   ctx=sorted(set(canonical[c.lower()] for c in codepat.findall(context)));code=canonical[explicit[-1].lower()] if explicit else ctx[0] if len(ctx)==1 else None
   after=re.split(articleword,literal,maxsplit=1,flags=re.I)[-1];numbers=re.findall(number,re.split(codepat,after,maxsplit=1)[0]);variants=[]
   if code is None:variants.append("UNRESOLVED_CODE_BINDING")
   if re.search(r"\d\s*[–-]\s*\d",after):variants.append("RANGE_RETAINED_AS_WRITTEN_NOT_EXPANDED")
   if len(numbers)>1:variants.append("LIST_OR_RANGE_RETAINED_AS_ONE_LITERAL_NOT_SPLIT_INTO_NORMS")
   o=row(m.start(),m.end());o.update(occurrence_id=sku+"-ref-"+str(len(occurrences)+1).zfill(4),literal=literal,code=code,code_binding="explicit_literal" if explicit else bind if code else "UNRESOLVED_NO_OR_MULTIPLE_EXPLICIT_CODE",articles_as_written=numbers,ranges_or_variants=variants);occurrences.append(o)
  seen=set()
  for pattern,classification in [(fullcode,"UNRESOLVED_FULL_CODE_NAME"),(standard,"UNRESOLVED_STANDARD_OR_OTHER_NORMATIVE_MARKER"),(law,"UNRESOLVED_OR_NON_ARTICLE_LEGAL_MARKER"),(numeric,"UNRESOLVED_NUMBERED_REFERENCE_SIGNAL")]:
   for m in pattern.finditer(text):
    if classification.endswith("LEGAL_MARKER") and any(a.start()<=m.start() and m.end()<=a.end() for a in matches):continue
    if (m.start(),m.end()) in seen:continue
    seen.add((m.start(),m.end()));o=row(m.start(),m.end());o.update(marker_id=sku+"-marker-"+str(len(markers)+1).zfill(4),marker=m.group(),classification=classification,reason="Raw lexical signal only; not normative identity, edition, applicability, currentness, legal completeness or defect");markers.append(o)
  for o in occurrences+markers:
   if o["unit_id"]!=uid:continue
   a,b=o["span"];qa,qb=o["quote_span"];assert text[a:b]==o.get("literal",o.get("marker")) and text[qa:qb]==o["short_quote"]
 return occurrences,markers,[dict(u,unit_id=sku+":"+doc+":"+str(i),sku=sku,document=doc,file_sha256=filehash) for i,u in enumerate(units,1) if i in kept]
def main():
 started=time.monotonic();manifest=json.loads((R/"input-hashes.json").read_text());assert manifest["source_sha"]==PIN and len(manifest["bindings"])==135
 versions={"python":sys.version,"xml":"stdlib ElementTree","native_IO":"ZIP readonly, no save/recalculate"}
 for argv in [["pdftotext","-v"],["pdfinfo","-v"],["pdfimages","-v"]]:
  p=subprocess.run(argv,capture_output=True,text=True,timeout=5);versions[argv[0]]={"exit":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
 save(R/"executor-versions.json",versions)
 results={};checkpoint={"status":"RUNNING","pid":os.getpid(),"workers":4,"overall_limit_seconds":120,"unique_expected":125,"source_bindings":135,"completed_unique":0};save(R/"process-checkpoint.json",checkpoint);print("ACTUAL_JOB",os.getpid(),"4workers125unique",flush=True)
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
  futures={pool.submit(extract_native,s):s for s in manifest["unique_inputs"]}
  for future in concurrent.futures.as_completed(futures):
   src=futures[future]
   try:result=future.result()
   except Exception as e:
    save(R/"failure-receipt.json",{"status":"BLOCKED_NATIVE_EXTRACTION","source":src,"error":repr(e),"completed_unique":len(results),"no_retry":True});raise
   results[result["sha256"]]=result;checkpoint["completed_unique"]=len(results);checkpoint["worker_pids"]=sorted(set(x["metadata"]["worker_pid"] for x in results.values()));save(R/"process-checkpoint.json",checkpoint)
 save(R/"unique-source-text-units.json",{"source_sha":PIN,"unique_inputs":results})
 aggregate=[];modulemaps={};(R/"modules").mkdir(exist_ok=True);commands=[c for x in results.values() for c in x["commands"]];save(R/"extract-commands.json",commands)
 for mod in manifest["modules"]:
  sku=mod["sku"];MR=R/"modules"/sku;MR.mkdir(exist_ok=True);occurrences=[];markers=[];documents=[];compact=[]
  for f in mod["members"]:
   native=results[f["sha256"]];o,m,u=annotate(sku,f["path"],f["sha256"],native["units"]);occurrences.extend(o);markers.extend(m);compact.extend(u)
   documents.append(dict(f,native_metadata=native["metadata"],native_corpus_key=f["sha256"],text_units=len(native["units"])))
  # Per-file annotation counters are made module-unique while every file/native locator remains bound.
  for i,o in enumerate(occurrences,1):o["occurrence_id"]=sku+"-ref-"+str(i).zfill(4)
  for i,m in enumerate(markers,1):m["marker_id"]=sku+"-marker-"+str(i).zfill(4)
  groups=collections.OrderedDict()
  for o in occurrences:
   key=(re.sub(r"\s+"," ",o["literal"]).strip().lower(),o["code"],tuple(o["articles_as_written"]));groups.setdefault(key,{"literal_normalized":re.sub(r"\s+"," ",o["literal"]).strip(),"code":o["code"],"articles_as_written":o["articles_as_written"],"occurrence_ids":[]})["occurrence_ids"].append(o["occurrence_id"])
  dedup=[dict(group_id=sku+"-group-"+str(i).zfill(3),registry_norm_id=None,group_is_not_norm=True,**v) for i,v in enumerate(groups.values(),1)]
  assert sorted(i for g in dedup for i in g["occurrence_ids"])==sorted(o["occurrence_id"] for o in occurrences)
  inv={"source_sha":PIN,"source_status":"CACHED_CONFIGURED_BASELINE_NOT_ACCEPTED_DELIVERY","sku":sku,"execution_pattern":"iterative","primary_result":"baseline_literal_source_index_for_future_lawyer","feedback_loop_required":True,"checkpoint_policy":"verified_only","documents":documents,"parser":{"article_regex":article.pattern,"law_marker_regex":law.pattern,"standard_regex":standard.pattern,"numbered_reference_regex":numeric.pattern,"full_code_name_regex":fullcode.pattern,"code_binding":"Explicit abbreviation or unique abbreviation in same unit; PDF physical line only; full names retained raw without semantic resolution","lists_ranges":"As written; not expanded into norms"},"literal_occurrences":occurrences,"deduplicated_groups":dedup,"unresolved_legal_and_standard_markers":markers,"source_currentness":"NOT_VERIFIED","human_legal":"NOT_PERFORMED","normative_verdict":"NOT_VERIFIED","membership":"SOURCE_ELIGIBLE_DRY_INVENTORY_NOT_ACTUAL_PHP_ZIP","scope_limit":"Native textual lexical scope only, not legal completeness/layout/formula/sale/currentacceptedrepackaging"}
  save(MR/"citation-inventory.json",inv);save(MR/"citation-source-units.json",{"source_sha":PIN,"sku":sku,"units":compact,"full_unique_units_server_only":"../../unique-source-text-units.json"})
  row={"sku":sku,"files":len(documents),"native_units_bound":sum(d["text_units"] for d in documents),"article_literals":len(occurrences),"groups_not_norms":len(dedup),"raw_markers_not_defects":len(markers),"compact_units":len(compact),"map_sha256":h((MR/"citation-inventory.json").read_bytes()),"compact_units_sha256":h((MR/"citation-source-units.json").read_bytes())};aggregate.append(row);modulemaps[sku]=row
  report=["# "+sku+" cached baseline factual citation index","",PIN+"; source_currentness NOT_VERIFIED; human_legal NOT_PERFORMED; no accepted delivery or legal completeness claim.","","|Source file|SHA256|Text units|","|---|---|---|"]+["|"+Path(d["path"]).name+"|"+d["sha256"]+"|"+str(d["text_units"])+"|" for d in documents]+["","Article literals: "+str(len(occurrences))+"; lexical groups (not norms): "+str(len(dedup))+"; raw unresolved markers (not defects): "+str(len(markers))+".",""]
  for o in occurrences:report.append("- "+o["occurrence_id"]+" · "+o["document"]+" · "+json.dumps(o["location"],ensure_ascii=False)+" · "+json.dumps(o["literal"],ensure_ascii=False)+" · "+json.dumps(o["short_quote"],ensure_ascii=False))
  for m in markers:report.append("- "+m["marker_id"]+" · "+m["document"]+" · "+json.dumps(m["location"],ensure_ascii=False)+" · "+m["classification"]+" · "+json.dumps(m["short_quote"],ensure_ascii=False))
  (MR/"citation-inventory-report.md").write_text("\n".join(report)+"\n")
 for f in manifest["bindings"]:
  b=git("show",PIN+":"+f["path"]);assert h(b)==f["sha256"] and len(b)==f["size"] and h(Path(f["local_path"]).read_bytes())==f["sha256"]
 assert len(results)==125 and len(aggregate)==14
 save(R/"aggregate-coverage.json",{"source_sha":PIN,"modules":aggregate,"bindings":135,"unique_inputs_extracted":125,"duplicate_bindings_reused":10,"unique_pdf_extractions":sum(x["metadata"]["suffix"]==".pdf" for x in results.values()),"unique_pdf_pages":sum(len(x["metadata"].get("pdf_pages",[])) for x in results.values()),"native_units_unique":sum(len(x["units"]) for x in results.values()),"baseline_only":True})
 receipt={"status":"READY_BASELINE_FACTUAL_INVENTORY_PENDING_ROOT_INDEPENDENT_REVIEW","source_sha":PIN,"source_status":"CACHED_BASELINE_NOT_ACCEPTED_DELIVERY","modules":14,"bindings_verified_before_after":135,"unique_inputs":125,"workers":4,"worker_pids":checkpoint["worker_pids"],"unique_pdf_extractions":8,"article_literals":sum(x["article_literals"] for x in aggregate),"groups_not_norms":sum(x["groups_not_norms"] for x in aggregate),"raw_markers_not_defects":sum(x["raw_markers_not_defects"] for x in aggregate),"elapsed_seconds":time.monotonic()-started,"script_sha256":h(Path(__file__).read_bytes()),"grammar_fragment_sha256":h((R/"lexical-grammar.py").read_bytes()),"source_product_writes":0,"ZIP_builds":0,"Calc_or_tests_or_LLM_or_official_lookups":0,"source_currentness":"NOT_VERIFIED","human_legal":"NOT_PERFORMED","normative_verdict":"NOT_VERIFIED","all_quotes_spans_native_bindings_verified":True};save(R/"verification-receipt.json",receipt)
 checkpoint["status"]="READY_PENDING_REVIEW";save(R/"process-checkpoint.json",checkpoint)
 allfiles=sorted(p for p in R.rglob("*") if p.is_file() and p.name not in ["READY.json","SHA256SUMS"]);(R/"SHA256SUMS").write_text("\n".join(h(p.read_bytes())+"  "+str(p.relative_to(R)) for p in allfiles)+"\n")
 save(R/"READY.json",{"status":receipt["status"],"source_sha":PIN,"script_sha256":receipt["script_sha256"],"receipt_sha256":h((R/"verification-receipt.json").read_bytes()),"aggregate_sha256":h((R/"aggregate-coverage.json").read_bytes()),"manifest_sha256":h((R/"SHA256SUMS").read_bytes()),"modulemaps":modulemaps,"large_server_retained":{"path":str(R/"unique-source-text-units.json"),"bytes":(R/"unique-source-text-units.json").stat().st_size,"sha256":h((R/"unique-source-text-units.json").read_bytes())},"Git_commit_push":"NOT_PERFORMED"})
 print("READY",json.dumps(receipt),flush=True)
if __name__=="__main__":main()
