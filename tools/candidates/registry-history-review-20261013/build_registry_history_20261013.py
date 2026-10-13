#!/usr/bin/env python3
"""Enrich the existing registry only, preserving product roots and prior QA outputs."""
from pathlib import Path
from datetime import datetime,timezone
from xml.etree import ElementTree as E
import base64,hashlib,importlib.util,io,json,os,subprocess,sys,zipfile
D=Path('/home/denis/.local/state/claude-dispatcher/recovery-20261006/postreconnect-product-gates')
B=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
REPO='pmgpt12-arch/marzhavbetone.ru'
GIT=Path('/home/denis/projects/marzhavbetone.ru')
W=Path('/home/denis/projects/mb001-registry-history-20261013')
BRANCH='codex/mb001-registry-history-20261013'
ARCHIVE='tools/candidates/registry-history-evidence/'
S='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
T='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NOW=datetime.now(timezone.utc).isoformat()
def run(args,timeout=20):
    p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if p.returncode: raise RuntimeError('COMMAND_FAILED '+str(args[:4])+': '+p.stderr[-1300:])
    return p.stdout

def api(path): return json.loads(run(['gh','api',path]))
def H(raw): return hashlib.sha256(raw).hexdigest()
def J(value): return H(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def tree(e): return None if e is None else {'tag':e.tag.rsplit('}',1)[-1],'attributes':dict(e.attrib),'text':e.text,'children':[tree(c) for c in e]}
def payloads(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None,'ZIP_CRC_FAIL'
        names=z.namelist();assert len(names)==len(set(names)),'ZIP_DUPLICATES'
        return {n:z.read(n) for n in names}
def texts(raw,tag): return [''.join(t.text or '' for t in p.iter(T+'t')) for p in E.fromstring(raw).iter(tag)]
def snapshot(raw,ext):
    out={'sha256':H(raw),'bytes':len(raw),'format':ext,'capture_method':'read-only ZIP/XML; no Office/model/formula execution'}
    if ext not in ('docx','xlsx'): return out
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        out['zip_members']=[{'name':i.filename,'sha256':H(z.read(i.filename)),'uncompressed_bytes':i.file_size,'compressed_bytes':i.compress_size,'crc32':format(i.CRC,'08x'),'compression':i.compress_type,'timestamp_zip':list(i.date_time)} for i in z.infolist()]
        p={i.filename:z.read(i.filename) for i in z.infolist()}
    out['zip_member_count']=len(p)
    out['metadata']={n:tree(E.fromstring(p[n])) for n in ('docProps/core.xml','docProps/app.xml') if n in p}
    out['relationship_hashes']={n:H(v) for n,v in p.items() if n.endswith('.rels')}
    if ext=='docx':
        doc=E.fromstring(p['word/document.xml']); ps=list(doc.iter(T+'p'))
        paragraphs=[''.join(t.text or '' for t in q.iter(T+'t')) for q in ps]
        out.update({'paragraph_count':len(ps),'nonempty_paragraph_count':sum(bool(s.strip()) for s in paragraphs),'paragraph_text_sha256':J(paragraphs),'table_count':len(list(doc.iter(T+'tbl'))),'sections':[tree(q) for q in doc.iter(T+'sectPr')],'styles_sha256':H(p['word/styles.xml']) if 'word/styles.xml' in p else None,'numbering_sha256':H(p['word/numbering.xml']) if 'word/numbering.xml' in p else None,'settings_sha256':H(p['word/settings.xml']) if 'word/settings.xml' in p else None,'media_hashes':{n:H(v) for n,v in p.items() if n.startswith('word/media/')}})
    else:
        book=E.fromstring(p['xl/workbook.xml']); out['defined_names']=[tree(q) for q in book.iter(S+'definedName')];out['calculation_properties']=[tree(q) for q in book.iter(S+'calcPr')]
        out['sheets']=[]
        rels={q.get('Id'):q.get('Target') for q in E.fromstring(p['xl/_rels/workbook.xml.rels'])}
        for sheet in book.iter(S+'sheet'):
            dest=rels[sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            name=dest.lstrip('/') if dest.startswith('/') else 'xl/'+dest
            xml=E.fromstring(p[name]); cells=list(xml.iter(S+'c')); formulas=[{'cell':c.get('r'),'formula':f.text,'attributes':dict(f.attrib)} for c in cells for f in c.iter(S+'f')]
            rows=[dict(q.attrib) for q in xml.iter(S+'row')]
            values=[{'cell':c.get('r'),'type':c.get('t'),'style':c.get('s'),'value':c.findtext(S+'v'),'inline_text':''.join(t.text or '' for t in c.iter(S+'t'))} for c in cells]
            out['sheets'].append({'name':sheet.get('name'),'sheet_id':sheet.get('sheetId'),'state':sheet.get('state'),'part':name,'dimension':tree(xml.find(S+'dimension')),'cell_count':len(cells),'row_count':len(rows),'formula_count':len(formulas),'formulas_sha256':J(formulas),'values_and_cell_styles_sha256':J(values),'row_attributes':rows,'columns':[tree(q) for q in xml.iter(S+'cols')],'merge_cells':[q.get('ref') for q in xml.iter(S+'mergeCell')],'data_validations':[tree(q) for q in xml.iter(S+'dataValidations')],'conditional_formatting':[tree(q) for q in xml.iter(S+'conditionalFormatting')],'protection':[tree(q) for q in xml.iter(S+'sheetProtection')],'print':{n:[tree(q) for q in xml.iter(S+n)] for n in ('pageSetUpPr','pageSetup','pageMargins','printOptions','headerFooter','rowBreaks','colBreaks')},'hyperlinks':[tree(q) for q in xml.iter(S+'hyperlink')]})
        st=E.fromstring(p['xl/styles.xml']);out['style_definitions']={n:tree(st.find(S+n)) for n in ('numFmts','fonts','fills','borders','cellXfs','cellStyleXfs')};out['styles_sha256']=H(p['xl/styles.xml']);out['formula_count']=sum(q['formula_count'] for q in out['sheets'])
    return out

def archive(raw,ext):
    rel=ARCHIVE+H(raw)+'.'+ext;p=W/rel;p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists(): assert p.read_bytes()==raw,'CONTENT_ADDRESS_COLLISION'
    else: p.write_bytes(raw)
    return rel

def file_ref(raw,ext,path,expected,git_origin=None):
    assert H(raw)==expected,'SOURCE_SHA_DRIFT '+path
    return {'actual_read_path':path,'sha256':H(raw),'bytes':len(raw),'format':ext,'archive_path':archive(raw,ext),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'git_origin':git_origin,'snapshot':snapshot(raw,ext)}
def local_ref(path,expected): return file_ref(path.read_bytes(),path.suffix[1:],str(path),expected)
def git_ref(commit,path,expected):
    raw=subprocess.run(['git','-C',str(GIT),'show',commit+':'+path],capture_output=True,check=True,timeout=8).stdout
    return file_ref(raw,Path(path).suffix[1:],'git://'+REPO+'@'+commit+'/'+path,expected,{'repository':REPO,'commit':commit,'relative_path':path})
def evidence(path,kind):
    raw=path.read_bytes();ext=path.suffix[1:] or 'txt';entry={'evidence_id':kind+'-'+H(raw)[:12],'kind':kind,'actual_read_path':str(path),'archive_path':archive(raw,ext),'sha256':H(raw),'bytes':len(raw)}
    if ext=='json': entry['reported_payload']=json.loads(raw)
    elif ext=='xml': entry['reported_payload']=tree(E.fromstring(raw))
    elif ext=='pdf':
        info=run(['pdfinfo',str(path)],timeout=8)
        entry['pdf_metadata']={line.split(':',1)[0].strip():line.split(':',1)[1].strip() for line in info.splitlines() if ':' in line}
    return entry

def delta(a,b):
    pa=payloads((W/a['archive_path']).read_bytes());pb=payloads((W/b['archive_path']).read_bytes()); changed=[n for n in pa if n in pb and pa[n]!=pb[n]]
    out={'input_sha256':a['sha256'],'output_sha256':b['sha256'],'bytes_before':a['bytes'],'bytes_after':b['bytes'],'zip_order_unchanged':list(pa)==list(pb),'parts_added':sorted(set(pb)-set(pa)),'parts_removed':sorted(set(pa)-set(pb)),'parts_unchanged_count':sum(pa[n]==pb[n] for n in pa if n in pb),'parts_changed':[{'part':n,'before_sha256':H(pa[n]),'after_sha256':H(pb[n]),'bytes_before':len(pa[n]),'bytes_after':len(pb[n])} for n in changed],'cells_changed':[],'rows_changed':[],'paragraphs_changed':[],'metadata_changed':{n:{'before':tree(E.fromstring(pa[n])),'after':tree(E.fromstring(pb[n]))} for n in changed if n.startswith('docProps/')},'snapshot_comparison_scope':'byte/XML comparison only; not formula execution or legal review'}
    if a['format']=='xlsx':
        for n in sorted(set(pa)&set(pb)):
            if not n.startswith('xl/worksheets/sheet') or not n.endswith('.xml'): continue
            x,y=E.fromstring(pa[n]),E.fromstring(pb[n]);ca={c.get('r'):tree(c) for c in x.iter(S+'c')};cb={c.get('r'):tree(c) for c in y.iter(S+'c')}
            for addr in sorted(set(ca)|set(cb)):
                if ca.get(addr)!=cb.get(addr):out['cells_changed'].append({'part':n,'cell':addr,'before':ca.get(addr),'after':cb.get(addr)})
            ra={q.get('r'):dict(q.attrib) for q in x.iter(S+'row')};rb={q.get('r'):dict(q.attrib) for q in y.iter(S+'row')}
            for addr in sorted(set(ra)|set(rb)):
                if ra.get(addr)!=rb.get(addr):out['rows_changed'].append({'part':n,'row':addr,'before':ra.get(addr),'after':rb.get(addr)})
        out['formulas_before']=a['snapshot']['formula_count'];out['formulas_after']=b['snapshot']['formula_count'];out['formula_hashes_unchanged']=[s['formulas_sha256'] for s in a['snapshot']['sheets']]==[s['formulas_sha256'] for s in b['snapshot']['sheets']]
        out['styles_unchanged']=a['snapshot']['styles_sha256']==b['snapshot']['styles_sha256']
    else:
        x=texts(pa['word/document.xml'],T+'p');y=texts(pb['word/document.xml'],T+'p')
        out['paragraph_count_before']=len(x);out['paragraph_count_after']=len(y)
        for i in range(max(len(x),len(y))):
            v=x[i] if i<len(x) else None;w=y[i] if i<len(y) else None
            if v!=w:out['paragraphs_changed'].append({'paragraph_index_zero_based':i,'before':v,'after':w})
    return out

def gate(name,status,out,ev,job=None,engine=None,scope=None):
    return {'gate_id':name,'status':status,'subject_sha256':out['sha256'],'scope':scope or name,'accepted_scope_only':True,'contract':{'gate_id':name,'subject':'exact immutable file','definition':scope or name,'release_not_implied':True},'environment':engine or {'application':'deterministic ZIP/XML comparison','native_office_invoked':False},'dependencies':{'input_and_output_sha256':out['sha256'],'evidence_sha256':sorted(e['sha256'] for e in ev)},'evidence_ids':[e['evidence_id'] for e in ev],'job_id':job}
def record(rid,regid,parent,sku,a,b,ev,gates,next_task,jobids,findings,reason,upstream):
    return {'record_id':rid,'registry_id':regid,'parent_registry_id':parent,'target_sku':sku,'runtime_sku':sku.lower(),'role':'nominated_candidate','recorded_at_utc':NOW,'origin':{'repository':REPO,'parent_issue':291,'control_registry_issue':600,'portfolio_issue':578,'upstream':upstream,'owner_directive':'13.10.2026: preserve maximum observed change parameters to prevent repeated work','reason':reason},'input':a,'output':b,'delta':delta(a,b),'execution':{'capture_executor':'deterministic Python script on ai-workstation','capture_script_path':str(Path(__file__).resolve()),'capture_script_sha256':H(Path(__file__).read_bytes()),'capture_python_version':sys.version,'capture_command':'python3 '+str(Path(__file__).resolve()),'historical_job_ids':jobids,'historical_source_of_facts':'archived raw reports, immutable file bytes, pinned Git objects','new_native_jobs_submitted':0,'new_model_calls':0,'historical_unlogged_parameters':None},'evidence':ev,'gates':gates,'resume':{'do_not_repeat_job_ids':jobids,'next_atomic_task':next_task,'invalidation_triggers':['actual subject SHA changed','gate scope or contract digest changed','relevant application version/build changed','evidence missing or changed','referenced dependency or normative edition changed; recheck affected scope only'],'open_findings':findings,'g1_g8_status':'NOT_FULLY_ACCEPTED','all_product_gates_complete':False},'unknowns':[{'parameter':'historical exact command/stdout/stderr/wall time where not in archived report','value':None,'reason':'not recorded; do not reconstruct as observed'},{'parameter':'deployed native-agent executable digest at historical execution','value':None,'reason':'not attested in returned native report'},{'parameter':'full normative and independent buyer acceptance','value':None,'reason':'not provided by this technical checkpoint'}],'release_status':'BLOCKED'}

def main():
    assert not W.exists(),'EXISTING_WORKTREE_STOP'
    existing=api('repos/'+REPO+'/git/matching-refs/heads/'+BRANCH);assert not existing,'EXISTING_BRANCH_STOP'
    base=api('repos/'+REPO+'/git/ref/heads/main')['object']['sha']
    run(['git','-C',str(GIT),'fetch','origin',base],timeout=25)
    run(['git','-C',str(GIT),'worktree','add','-b',BRANCH,str(W),base],timeout=15)
    registry_path=W/'products-storage/ARTIFACT-REGISTRY.json';data=json.loads(registry_path.read_text())
    assert 'change_history' not in data,'HISTORY_ALREADY_IMPLEMENTED'
    original_registry_sha=H(registry_path.read_bytes())
    module_path=W/'tools/build_artifact_registry.py';src=module_path.read_text();extension=(D/'registry_history_functions_20261013.py').read_text()
    assert 'def validate_change_history' not in src and src.count('    return changed\n')==1,'VALIDATOR_ANCHOR_DRIFT'
    src=src.replace('    roles = set(data.get("allowed_roles", []))','    validate_change_history(data)\n    roles = set(data.get("allowed_roles", []))',1)
    src=src.replace('    return changed\n','    verify_history_files(data, repo)\n    return changed\n',1)
    src=src.replace('    parser.add_argument("--check", action="store_true")','    parser.add_argument("--check", action="store_true")\n    parser.add_argument("--reuse-request", help="JSON current-input/contract/environment request; no job launch")',1)
    src=src.replace('        if changed:\n','        if args.reuse_request:\n            request = json.loads(Path(args.reuse_request).read_text(encoding="utf-8"))\n            print(json.dumps(plan_checkpoint_reuse(data, request, repo), ensure_ascii=False))\n            return 0\n        if changed:\n',1)
    marker='if __name__ == "__main__":';assert src.count(marker)==1
    src=src.replace(marker,extension+'\n\n'+marker)
    module_path.write_text(src)
    spec=importlib.util.spec_from_file_location('new_registry',module_path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    p1=D/'p1-395-corexml-compat-20261013';p2=D/'p2-instruction-business-style-20261013'
    canon=git_ref('b85a2e716d501cbc54c840f58027ecfd6a60964b','products-storage/01-zakrytie-rabot/14-raschet-procentov-395-gk.xlsx','0e3fd94bcb4023652d40de96c22890ef494f0d089d565b1ef6017374c19923fe')
    v3=git_ref('d2934cfc08c16bfcea21ff19d29cdca2c993d55e','tools/candidates/p1-395-content-20261012/14-raschet-procentov-395-gk.xlsx','f7bd3a6fc8cfbb9e478448b2d217c6c4e3b667a5548f421373a7816978e5874e')
    core=local_ref(p1/'14-raschet-procentov-395-gk-corexml-compat.xlsx','044d9aa899b2278c9fe6c525f4b54e3f8ea07d4b12d755a8df145741756ee8c2')
    header=local_ref(p1/'14-raschet-procentov-395-gk-native-header.xlsx','8ec79d20d15a8d4888b2ae69130f374d1a8c6039cfdf2ba71044d7010ff5ce34')
    parent=git_ref('6455d9719e782d1a6819e9b1a1a0f811252ddcdb','tools/candidates/p2-instruction-style-20261013/00-INSTRUKCIYA-parent.docx','0bb84800a2bac43b50f4521db4e6397963f76377aea350b42ea4cc6bc8cf2eb4')
    word=local_ref(B/'word/p2-instruction-style-word-20261013-v1/p2-instruction.docx','0f3882fae04bd8bf32a9c368abc24e6d4c1c41fad5d008d37bfc522098148b11')
    records=[]
    ev=[evidence(B/'results/native/p1-395-editorial-native-20261013-v1/report.xml','native-report'),evidence(D/'p1-395-native-excel-20261013/result.json','native-summary')]
    job='p1-395-editorial-native-20261013-v1';engine={'application':'Microsoft Excel','version':'16.0','build':'4324','observed_in':'native-report'}
    records.append(record('P1-395-V3-NATIVE-FAIL-20261013','P1-CAND-395-PR610-V3',None,'P1',canon,v3,ev,[gate('native_open_export','FAIL',v3,ev,job,engine,'Exact native Workbooks.Open; failure 0x800A03EC after verified input SHA')],'Do not rerun this failed SHA; use metadata-repaired descendant',[job],[{'id':'P1-COREXML-DOUBLE-TIMEZONE','status':'FIXED_IN_DESCENDANT','observed_error':'0x800A03EC','cause_class':'OOXML_METADATA_COMPATIBILITY','basis':'two +00:00Z timestamps; metadata-only descendant opens in same reported Excel build'}],'Preserve original failed result and exact seven-cell editorial delta',[{'pr':610,'head':'d2934cfc08c16bfcea21ff19d29cdca2c993d55e'}]))
    ev=[evidence(p1/'report.json','structural-report'),evidence(p1/'independent-native-verification.json','independent-verification'),evidence(B/'results/native/p1-395-corexml-native-20261013-v1/report.xml','native-report'),evidence(B/'results/native/p1-395-corexml-native-20261013-v1/p1395core-filled.pdf','native-pdf'),evidence(p1/'build.py','builder-script'),evidence(p1/'native_once.py','native-script')]
    job='p1-395-corexml-native-20261013-v1'
    records.append(record('P1-395-COREXML-NATIVE-20261013','P1-CAND-395-COREXML-20261013','P1-CAND-395-PR610-V3','P1',v3,core,ev,[gate('native_open_export','PASS',core,ev,job,engine,'Exact XLSX native open/export; all 251 formulas unchanged; no numeric scenarios')],'Use header-fix descendant; do not re-open metadata-only candidate merely to rediscover PASS',[job],[{'id':'P1-EXAMPLE-G15-CLIPPING','status':'FIXED_IN_DESCENDANT','source':'native-header-candidate.json'}],'Two metadata timestamps normalized; no worksheet payload changes',[{'pr':610,'source_head':'ab13e8b3dc7eca17c56ef06f681d66452003205f'}]))
    ev=[evidence(p1/'native-header-candidate.json','structural-report'),evidence(p1/'native-header-result.json','native-summary'),evidence(p1/'native-header-visual-review.json','visual-review'),evidence(B/'results/native/p1-395-native-header-20261013-v1/report.xml','native-report'),evidence(B/'results/native/p1-395-native-header-20261013-v1/p1395header-filled.pdf','native-pdf'),evidence(p1/'fix_native_header.py','builder-script')]
    job='p1-395-native-header-20261013-v1'
    records.append(record('P1-395-HEADER-NATIVE-20261013','P1-CAND-395-NATIVE-HEADER-20261013','P1-CAND-395-COREXML-20261013','P1',core,header,ev,[gate('native_open_export','PASS',header,ev,job,engine,'Exact XLSX native open/export and source unchanged; not numeric scenario verification'),gate('print_layout','OPEN',header,ev,None,engine,'Five-page visual review: G15 clipping fixed; orphan notes page remains open')],'Resolve P1-PRINT-ORPHAN-NOTES as layout-only delta; run new-SHA native and filled numeric checks only after that delta',[job],[{'id':'P1-PRINT-ORPHAN-NOTES','status':'OPEN','page':3,'description':'Two notes spill onto an otherwise empty landscape page; print compactness not accepted'}],'Only example-sheet row 15 height changed from 38 to 54pt',[{'pr':610,'head':'18294273b42d5359a86a6ad797f50577d39fc858'}]))
    ev=[evidence(p2/'native-word-visual-review.json','visual-review'),evidence(p2/'native-word-pdf-static-gate.json','static-report'),evidence(p2/'word-existing-job-recovery-result.json','recovery-report'),evidence(p2/'word-manifest-repair-receipt.json','schema-repair-report'),evidence(B/'results/word/p2-instruction-style-word-20261013-v1/report.xml','native-report'),evidence(B/'results/word/p2-instruction-style-word-20261013-v1/p2style.pdf','native-pdf'),evidence(B/'word/p2-instruction-style-word-20261013-v1/job.xml','job-manifest'),evidence(p2/'recover_existing_word_job_once.py','recovery-script')]
    job='p2-instruction-style-word-20261013-v1';wordengine={'application':'Microsoft Word 2016','version_source':'native PDF creator metadata','exact_build':None,'exact_build_reason':'not attested by Word report'}
    records.append(record('P2-INSTRUCTION-NATIVE-VISUAL-20261013','P2-CAND-INSTR-PR616-V1',None,'P2',parent,word,ev,[gate('native_open_export','PASS',word,ev,job,wordengine,'Exact DOCX native Word open/export; delivered PDF hash matched'),gate('native_visual_layout','PASS',word,ev,job,wordengine,'Four A4 native Word PDF pages reviewed without clipping, overlap or broken table')],'Do not rerun this Word job. Continue unresolved product-level normative/content/buyer gates and synchronized DOCX/PDF package',[job],[{'id':'P2-PRODUCT-ACCEPTANCE','status':'OPEN','description':'Native/visual result is not full P2 acceptance'}],'13 paragraph edits; recovered existing job by fixing filename and UTF-8 declaration; no new job ID',[{'pr':616,'head':'35fa9e44b94a0b2f0e356020d48e039b996ad192'}]))
    for rec in records:m.append_change_record(data,rec,data.get('change_history',{}).get('head_record_sha256'))
    data['change_history']['policy']={'owner_directive_date':'2026-10-13','reuse_requires':['exact input SHA','exact scope/contract fingerprint','relevant runtime fingerprint','dependency fingerprint','all evidence present and hash verified'],'do_not_reinterpret':['Office PASS as content/legal/buyer PASS','filename filled as executed numeric scenario','timeout as model or document defect'],'unknown_parameter_policy':'null plus source/reason; never silently infer','current_checkpoint_selection':'choose explicit registry ID + SHA, never modification time or filename alone'}
    registry_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    original=json.loads(run(['git','-C',str(W),'show',base+':products-storage/ARTIFACT-REGISTRY.json']))
    assert {k:v for k,v in data.items() if k!='change_history'}==original,'BASELINE_MUTATION'
    m.validate_shape(data);m.verify_history_files(data,W)
    (W/'tools/candidates/MB001_REGISTRY_CHANGE_HISTORY.md').write_text('# MB001: история изменений и возобновление без повторов\n\nКонтрольный реестр: Issue #600. Родитель #291. Записи находятся в существующем products-storage/ARTIFACT-REGISTRY.json, поле change_history; это не новая очередь и не реестр релиза.\n\nКаждая запись: точные версии до/после; SHA-256, Git blob, байты, исходный путь и сохранённая копия; OOXML-параметры и адресный delta; сырые отчёты, PDF и скрипты; результат каждого gate с ограниченным scope; runtime/contract/dependency fingerprints; открытые дефекты; следующий атомарный шаг. Неизвестное отмечено null с причиной.\n\nПеред повторным Office/model заданием: `python3 tools/build_artifact_registry.py --check --reuse-request <request.json>`. JSON запроса содержит record_id, gate_id, actual_input_path, contract_sha256, environment_fingerprint, dependency_fingerprint. Значения текущего контракта/среды/зависимостей поступают из фактического preflight, не копируются автоматически из старой записи. Команда не запускает исполнителей.\n\nREUSE_VERIFIED_RESULT: проверка уже выполнена на этих входах; не запускать повторно. BLOCK_KNOWN_FAILURE: сначала исправление причины. WAIT_EXISTING_JOB: читать существующий результат. DELTA_RECHECK_REQUIRED: проверить только затронутые изменения, не повторять весь аудит. RESOLVE_DEPENDENCY/CHECK_REQUIRED: завершить указанное недостающее звено.\n\nИстория append-only: SHA-цепочка; исправление прежнего вывода оформлять новой записью, не переписывать прошлый результат. Локальные evidence-copy имеют роль доказательств, не становятся canonical автоматически. Исполнители, ещё не вызывающие этот preflight, не считаются автоматически подключёнными к защите повторов.\n',encoding='utf-8')
    (D/'registry-history-build.json').write_text(json.dumps({'status':'BUILT_NOT_PUBLISHED','worktree':str(W),'branch':BRANCH,'base':base,'original_registry_sha256':original_registry_sha,'registry_sha256':H(registry_path.read_bytes()),'history_records':len(records),'archive_files':len(list((W/ARCHIVE).glob('*'))),'new_office_jobs':0,'new_model_calls':0,'product_source_mutations':0},ensure_ascii=False,indent=2)+'\n')
    print((D/'registry-history-build.json').read_text())
if __name__=='__main__':main()
