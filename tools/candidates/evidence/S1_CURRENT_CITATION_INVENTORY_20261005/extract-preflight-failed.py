"""Extract factual citations from exact accepted11 buyers; read-only inputs."""
import pathlib,subprocess,json,hashlib,re,zipfile,xml.etree.ElementTree as ET,datetime,collections,shutil,sys
S=pathlib.Path("/home/denis/projects/marzhavbetone.ru");W=S/".worktrees/codex-s1-current-citation-inventory-20261005"
R=pathlib.Path("/home/denis/.local/state/claude-dispatcher/recovery-20261004/s1-current-citation-inventory-20261005")
PIN="a77422195c2c68281a7797ad99f9f6b70426d740";ROOT="tools/candidates/s1-oplata-za-raboty"
OLD=S/".worktrees/codex-s1-legal-inputs-20261005/tools/candidates/evidence/S1_LEGAL_INPUTS_20261005"
def h(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(["git","-C",str(W),*a],timeout=6)
def normalize(s):return re.sub(r"\s+"," ",s).strip()
assert git("rev-parse","HEAD").decode().strip()==PIN
required={"old_literal_reference_map":OLD/"literal-reference-map.json","old_buyer_claims_index":OLD/"buyer-claims-index.json","normative_contract":pathlib.Path("/home/denis/projects/ai-business-os/docs/Normative_Contract.md"),"task_protocol":pathlib.Path("/home/denis/projects/ai-business-os/docs/Task_Setting_Protocol.md")}
input_manifest={"source_sha":PIN,"required_inputs":{},"buyer_files":[]}
for key,p in required.items():
 raw=p.read_bytes();input_manifest["required_inputs"][key]={"path":str(p),"sha256":h(raw),"size":len(raw)}
old=json.loads(required["old_literal_reference_map"].read_text());old_index=json.loads(required["old_buyer_claims_index"].read_text())
files=sorted(p for p in (W/ROOT).iterdir() if re.match(r"^\d{2}-",p.name) and p.suffix in [".txt",".docx",".xlsx"])
assert len(files)==11
known={"02-proverka-i-kontrol-otveta.xlsx":"5918714b4e4e95abc546e1fe7a43f515af50680ecf75352a2949a2ebecac47f0","08-raschet-procentov-395.xlsx":"e0ed0206c17f1b3638bba14dd472c3acad0da80c87dd640169e9c094dec266b4","04-akt-sverki.xlsx":"f735e85286952a2780d413aea7debbe7a7ceda24edf717d79b631a4aad8945d9"}
found_known=set()
sys.path.append("/home/denis/projects/ai-business-os/.venv/lib/python3.12/site-packages")
import openpyxl
# Explicit article grammar; retain non-matching lawmarkers separately rather than treating absence as completeness.
codes=r"ГК|АПК|НК|ГПК|ТК|КоАП|БК|СК|ЗК|ЖК"
num=r"\d+(?:\.\d+)?"
prefix=r"(?:(?:пп?|пункт(?:а|ы|ов|у|ом)?|ч|част(?:ь|и|ью)|абз|абзац(?:а|ы|ев)?)\.?\s*"+num+r"\s*){0,4}"
artword=r"(?:ст\.|стать(?:я|и|ю|е|ей|ями))"
refpat=re.compile(r"(?<![А-Яа-яA-Za-z])"+prefix+artword+r"\s*"+num+r"(?:\s*(?:,|и|–|-)\s*"+num+r")*(?:\s*(?:"+codes+r")(?:\s*РФ)?)?",re.I)
lawpat=re.compile(r"\b(?:"+codes+r")\b|\bст\.\s*\d|\bстать(?:я|и|ю|е|ей|ями)\b|\d+\s*[-–]ФЗ\b|Пленум|Верховн\w*\s+[Сс]уд\w*|[Фф]едеральн\w*\s+закон\w*|[Пп]риказ\w*|[Пп]остановлен\w*|\bзакон\w*",re.I)
codepat=re.compile(r"\b("+codes+r")\b",re.I)
canonical={c.lower():c for c in ["ГК","АПК","НК","ГПК","ТК","КоАП","БК","СК","ЗК","ЖК"]}
WXML="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
units=[];docs=[]
for p in files:
 rel=p.relative_to(W).as_posix();raw=p.read_bytes();assert raw==git("show",PIN+":"+rel)
 item={"path":rel,"source_sha":PIN,"sha256":h(raw),"git_blob":git("rev-parse",PIN+":"+rel).decode().strip(),"size":len(raw)}
 for name,expected in known.items():
  if p.name==name:assert item["sha256"]==expected,(name,item["sha256"]);found_known.add(name)
 input_manifest["buyer_files"].append(item)
 docunits=[]
 if p.suffix==".docx":
  with zipfile.ZipFile(p) as z:
   parts=[n for n in z.namelist() if n=="word/document.xml" or re.fullmatch(r"word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml",n)]
   for part in parts:
    root=ET.fromstring(z.read(part));parent={child:node for node in root.iter() for child in node};nonempty=0
    for ordinal,par in enumerate(root.iter(WXML+"p"),1):
     text="".join(n.text or "" for n in par.iter(WXML+"t"))
     if not text.strip():continue
     nonempty+=1;lineage=[];node=par
     while node in parent:
      up=parent[node];same=[c for c in up if c.tag==node.tag];lineage.append(node.tag.split("}")[-1]+"["+str(same.index(node)+1)+"]");node=up
     location={"kind":"docx_paragraph","part":part,"global_paragraph_ordinal_including_empty":ordinal,"nonempty_paragraph_ordinal":nonempty,"xml_path":"/"+"/".join(reversed(lineage))}
     docunits.append({"document":rel,"location":location,"text":text})
 elif p.suffix==".xlsx":
  book=openpyxl.load_workbook(p,read_only=True,data_only=False)
  for sheet in book.worksheets:
   for row in sheet.iter_rows():
    for cell in row:
     if cell.value is not None:
      text=str(cell.value);docunits.append({"document":rel,"location":{"kind":"xlsx_cell","sheet":sheet.title,"cell":cell.coordinate,"data_type":cell.data_type,"value_mode":"formula" if cell.data_type=="f" else "stored_value"},"text":text})
  book.close()
 else:
  nonempty=0
  for line_no,text in enumerate(p.read_text().splitlines(),1):
   if not text.strip():continue
   nonempty+=1;docunits.append({"document":rel,"location":{"kind":"txt_line","physical_line":line_no,"nonempty_line":nonempty},"text":text})
 units.extend(docunits);item["text_units"]=len(docunits);docs.append(item)
assert len(found_known)==3,(found_known,[p.name for p in files])
occurrences=[];markers=[]
for unit in units:
 text=unit["text"];matches=list(refpat.finditer(text))
 for m in matches:
  literal=m.group();codem=codepat.findall(literal);contextcodes=sorted(set(canonical[c.lower()] for c in codepat.findall(text)))
  code=canonical[codem[-1].lower()] if codem else contextcodes[0] if len(contextcodes)==1 else None
  code_source="explicit_literal" if codem else "one_explicit_code_in_same_text_unit" if code else "UNRESOLVED_NO_OR_MULTIPLE_EXPLICIT_CODE"
  after_article=re.split(artword,literal,maxsplit=1,flags=re.I)[-1]
  articles=re.findall(num,re.split(codepat,after_article,maxsplit=1)[0])
  span=[m.start(),m.end()];a=max(0,m.start()-70);b=min(len(text),m.end()+100);quote=text[a:b]
  occurrences.append({"occurrence_id":"ref-"+str(len(occurrences)+1).zfill(4),"document":unit["document"],"file_sha256":next(d["sha256"] for d in docs if d["path"]==unit["document"]),"location":unit["location"],"literal":literal,"span":span,"short_quote":quote,"quote_span":[a,b],"code":code,"code_binding":code_source,"articles_as_written":articles,"range_or_list_syntax":bool(re.search(r"\d\s*[–-]\s*\d",after_article)),"registry_norm_id":None,"normative_verdict":"NOT_VERIFIED"})
 for marker in lawpat.finditer(text):
  covered=any(m.start()<=marker.start() and marker.end()<=m.end() for m in matches)
  if not covered:
   a=max(0,marker.start()-70);b=min(len(text),marker.end()+100)
   markers.append({"marker_id":"marker-"+str(len(markers)+1).zfill(4),"document":unit["document"],"location":unit["location"],"marker":marker.group(),"span":[marker.start(),marker.end()],"short_quote":text[a:b],"quote_span":[a,b],"classification":"UNRESOLVED_OR_NON_ARTICLE_LEGAL_MARKER","reason":"literal law token outside matched article grammar; may be code-only/general wording, not inferred citation","normative_verdict":"NOT_VERIFIED"})
groups=collections.OrderedDict()
for row in occurrences:
 key=(normalize(row["literal"]).lower(),row["code"],tuple(row["articles_as_written"]))
 groups.setdefault(key,{"literal_normalized":normalize(row["literal"]),"code":row["code"],"articles_as_written":row["articles_as_written"],"occurrence_ids":[]})["occurrence_ids"].append(row["occurrence_id"])
dedup=[dict(group_id="group-"+str(i).zfill(3),**g) for i,g in enumerate(groups.values(),1)]
unitbydoc=collections.defaultdict(list)
for u in units:unitbydoc[u["document"]].append(u)
old_dispositions=[]
for i,row in enumerate(old["references"],1):
 candidates=[o for o in occurrences if o["document"]==row["document"] and normalize(row["literal"]).lower()==normalize(o["literal"]).lower()]
 exact_text_units=[u["location"] for u in unitbydoc[row["document"]] if normalize(row["literal"]).lower() in normalize(u["text"]).lower()]
 old_dispositions.append({"old_reference_index":i,"document":row["document"],"old_file_sha256":row["file_sha256"],"old_location":row["location"],"old_literal":row["literal"],"old_code":row["code"],"old_article":row["article"],"current_file_sha256":next(d["sha256"] for d in docs if d["path"]==row["document"]),"byte_binding_changed":row["file_sha256"]!=next(d["sha256"] for d in docs if d["path"]==row["document"]),"current_occurrence_ids":[o["occurrence_id"] for o in candidates],"current_literal_text_locations":exact_text_units,"status":"CURRENT_LITERAL_RELOCATED" if candidates else "CURRENT_LITERAL_TEXT_PRESENT_GRAMMAR_DIFF" if exact_text_units else "OLD_LITERAL_NOT_PRESENT_EXACTLY_REVIEW_VARIANT_OR_REMOVAL","normative_verdict_not_inherited":True})
inventory={"observed":datetime.datetime.now(datetime.timezone.utc).isoformat(),"execution_pattern":"one_shot","primary_result":"S1_current_factual_citation_inventory","feedback_loop_required":False,"checkpoint_policy":"verified_only","source_sha":PIN,"old_map_source_sha":old_index["source_sha"],"documents":docs,"parser":{"ref_regex":refpat.pattern,"law_marker_regex":lawpat.pattern,"code_binding":"only explicitcode in literal or unique explicitcode in same textunit; ambiguous =>UNRESOLVED","article_list_rule":"numbers_as_written only; ranges not expanded","dedup_key":"normalizedliteral+observedcode+numbersaswritten; retain every occurrence","locator_rule":"DOCX XMLpart+globalparagraph ordinal includingempty+nonemptyordinal+XMLpath; XLSX storedreadonlycell/formula; TXTphysical/nonemptyline","old_locator_rule":"oldparagraphindex counts nonemptyword/document.xmlparagraphs; oldsemantic_partindex XLSX is not a cell coordinate; never copyit ascurrentlocator"},"occurrences":occurrences,"deduplicated_groups":dedup,"unresolved_legal_markers":markers,"old_reference_dispositions":old_dispositions,"source_currentness":"NOT_VERIFIED","human_legal":"NOT_PERFORMED","scope_limit":"literalcitationinventory and explicitlawtoken signals; no completeness oflegalmechanisms or applicability verdict; not a normative registry"}
# Verification of each recorded span and locator against alreadyread pinnedtext, plus exact current Git inputs.
unitindex={(u["document"],json.dumps(u["location"],sort_keys=True)):u["text"] for u in units}
for row in occurrences+markers:
 text=unitindex[(row["document"],json.dumps(row["location"],sort_keys=True))]
 a,b=row["quote_span"];assert text[a:b]==row["short_quote"]
 a,b=row["span"];assert text[a:b]==row.get("literal",row.get("marker"))
assert [x for g in dedup for x in g["occurrence_ids"]]==[o["occurrence_id"] for o in occurrences] or sorted(x for g in dedup for x in g["occurrence_ids"])==sorted(o["occurrence_id"] for o in occurrences)
for d in docs:assert h((W/d["path"]).read_bytes())==d["sha256"] and (W/d["path"]).read_bytes()==git("show",PIN+":"+d["path"])
assert not git("status","--porcelain").decode().strip()
(R/"input-hashes.json").write_text(json.dumps(input_manifest,ensure_ascii=False,indent=2)+"\n")
(R/"citation-inventory.json").write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+"\n")
(R/"source-text-units.json").write_text(json.dumps({"source_sha":PIN,"units":units},ensure_ascii=False,indent=2)+"\n")
counts=collections.Counter(o["document"] for o in occurrences);markcounts=collections.Counter(o["document"] for o in markers)
receipt={"status":"VERIFIED_FACTUAL_INVENTORY_PENDING_INDEPENDENT_ROOT_REVIEW","source_sha":PIN,"buyer_files":11,"text_units":len(units),"literal_occurrences":len(occurrences),"dedup_groups":len(dedup),"unresolved_markers":len(markers),"old_map_rows":len(old["references"]),"old_disposition_counts":dict(collections.Counter(r["status"] for r in old_dispositions)),"current_hashes_changed_from_oldmap":sorted(set(r["document"] for r in old_dispositions if r["byte_binding_changed"])),"02_08_reviewed_04_native_exact":True,"all_span_quote_locator_checks":True,"all11_current_gitbytes_unchanged":True,"model_calls":0,"source_currentness":"NOT_VERIFIED","human_legal":"NOT_PERFORMED","executor":{"python":sys.version,"openpyxl":openpyxl.__version__}}
(R/"verification-receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
lines=["# S1 current factual citation inventory","", "Exact accepted source: "+PIN+". Preparation only; source currentness NOT_VERIFIED; human legal NOT_PERFORMED.","", "execution_pattern:one_shot; primary_result:S1_current_factual_citation_inventory; feedback_loop_required:false; checkpoint_policy:verified_only.","", "Old map source"+old_index["source_sha"]+" is superseded as document hash binding, not overwritten. Full old dispositions retained; no normative verdict inherited.","", "| File | Current SHA256 | Literal occurrences | Unresolved markers |","|---|---|---|---|"]
for d in docs:lines.append("| "+d["path"].split("/")[-1]+" | "+d["sha256"]+" | "+str(counts[d["path"]])+" | "+str(markcounts[d["path"]])+" |")
lines.extend(["","## Deduplication and unresolved cases","", "Dedup groups retain all occurrence IDs and exact locators. Numbers listed/ranged are kept as written; missing or multiple code contexts remain unresolved. Lawmarkers outside regex are explicitly retained, including general wording; they are signals, not legal findings.","", "## Current literal quotes",""])
for o in occurrences:lines.append("- "+o["occurrence_id"]+" · "+o["document"].split("/")[-1]+" · "+json.dumps(o["location"],ensure_ascii=False)+" · "+o["literal"]+" · «"+normalize(o["short_quote"])+"»")
lines.extend(["","## Unresolved tokens",""])
for m in markers:lines.append("- "+m["marker_id"]+" · "+m["document"].split("/")[-1]+" · "+json.dumps(m["location"],ensure_ascii=False)+" · «"+normalize(m["short_quote"])+"»")
lines.extend(["","## Checks","",json.dumps(receipt,ensure_ascii=False,indent=2),"","Original inputs unchanged; no legalregistry/currentedition/PASS invented. Root independentcoverage review required before Gitcommit/push."])
(R/"citation-inventory-report.md").write_text("\n".join(lines)+"\n")
for key,p in required.items():shutil.copyfile(p,R/(key+p.suffix))
manifest_files=[p for p in R.iterdir() if p.is_file() and p.name!="SHA256SUMS"]
(R/"SHA256SUMS").write_text("\n".join(h(p.read_bytes())+"  "+p.name for p in sorted(manifest_files))+"\n")
print(json.dumps(receipt,ensure_ascii=False));print("READY",R)
