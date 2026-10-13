#!/usr/bin/env python3
"""Bounded new numeric scope for an immutable P1 candidate, using existing Office transport.
Only numeric values authored with artifact_tool are overlaid on blank fixture cells.
No candidate/source, formulas, styles, runtime, VPN, production or prices are changed.
"""
from pathlib import Path
from xml.etree import ElementTree as E
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import calendar, hashlib, importlib.util, io, json, os, re, shutil, sys, time, zipfile

BASE=Path('/home/denis/.local/state/claude-dispatcher/recovery-20261006/postreconnect-product-gates')
PLAN=BASE/'p1-native-numeric-plan-20261013.json'
D=BASE/'p1-395-native-numeric-20261013'
SOURCE=Path('/home/denis/projects/mb001-p1-395-copy-correction-20261012/tools/candidates/p1-395-content-20261012/14-raschet-procentov-395-gk.xlsx')
REGREPO=Path('/home/denis/projects/mb001-registry-history-20261013')
TRANSPORT=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
JOB='p1-395-numeric-four-20261013-v1'
CURRENT=TRANSPORT/'native/current.xml'
REPORT=TRANSPORT/'results/native'/JOB/'report.xml'
N='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
PARTS={'input':'xl/worksheets/sheet1.xml','calc':'xl/worksheets/sheet2.xml'}

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(o): return (json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
def atomic(p,b):
    t=p.with_name(p.name+'.tmp')
    with t.open('xb') as f: f.write(b); f.flush(); os.fsync(f.fileno())
    os.replace(t,p)
def save(name,o): atomic(D/name,canonical(o))
def read_parts(b):
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist())), 'ZIP_INTEGRITY'
        return {n:z.read(n) for n in z.namelist()}
def formula_map(parts):
    return {(n,c.get('r')):E.tostring(c.find(N+'f')) for n,b in parts.items() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n) for c in E.fromstring(b).iter(N+'c') if c.find(N+'f') is not None}
def oracle_check(spec):
    for o in spec['oracle']:
        a=(Decimal(o['principal'])*Decimal(o['rate_percent'])*Decimal(o['days'])/(100*Decimal(o['year_days']))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        assert a==Decimal(o['rounded_interest']), 'ORACLE_ROUNDING'
    if spec['oracle']:
        total=sum((Decimal(o['rounded_interest']) for o in spec['oracle']),Decimal(0))
        assert total==Decimal(spec['expected_calc']['G45']['value'])==Decimal(spec['expected_result']['B10']['value']), 'ORACLE_TOTAL'
        for row,o in enumerate(spec['oracle'],4):
            start=date(1899,12,30)+timedelta(days=spec['calc']['A'+str(row)])
            days=spec['calc']['B'+str(row)]-spec['calc']['A'+str(row)]+1
            assert days==o['days'] and (366 if calendar.isleap(start.year) else 365)==o['year_days'], 'ORACLE_DATES'

def build(plan):
    assert not D.exists() and not (TRANSPORT/'native'/JOB).exists() and not REPORT.exists(), 'EXISTING_UNIT_RECONCILE_NO_REPLAY'
    assert len(plan['fixtures'])==4 and plan['limits']['native_attempts']==1
    source=SOURCE.read_bytes(); assert sha(source)==plan['source_sha256'], 'SOURCE_SHA_DRIFT'
    old=read_parts(source); assert len(old)==15 and len(formula_map(old))==251
    D.mkdir(); atomic(D/'plan.json',PLAN.read_bytes()); atomic(D/'source.xlsx',source)
    contract={'scope':plan['native_scope'],'plan_sha256':sha(PLAN.read_bytes()),'native_value_assertions':42,'output_assertions':24,'source_sha256':sha(source)}
    spec=importlib.util.spec_from_file_location('accepted_registry',REGREPO/'tools/build_artifact_registry.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    registry=json.loads((REGREPO/'products-storage/ARTIFACT-REGISTRY.json').read_text())
    history=registry['change_history']['records']
    record=next(r for r in history if r['output']['sha256']==plan['source_sha256'])
    gate=next(g for g in record['gates'] if g['gate_id']=='native_open_export')
    request={'record_id':record['record_id'],'gate_id':gate['gate_id'],'actual_input_path':str(SOURCE),'contract_sha256':mod.stable_digest(contract),'environment_fingerprint':gate['environment_fingerprint'],'dependency_fingerprint':gate['dependency_fingerprint']}
    decision=mod.plan_checkpoint_reuse(registry,request,REGREPO)
    save('reuse-preflight.json',{'request':request,'decision':decision,'reason':'New numeric contract, not a repetition of accepted open/export; target environment is rechecked from returned native report','old_contract':gate['contract'],'new_contract':contract})
    assert 'DELTA_RECHECK_REQUIRED' in json.dumps(decision), 'NO_NEW_SCOPE_ADMISSION'
    items=[]; job=E.Element('job',{'id':JOB,'scope':plan['native_scope'],'source_commit':plan['source_commit']})
    for index,sp in enumerate(plan['fixtures'],1):
        oracle_check(sp); new=dict(old); edits=[]
        for key,part in PARTS.items():
            text=old[part].decode('utf-8')
            for address,value in sp['authored_numeric_xml_values'][key].items():
                assert re.fullmatch(r'[A-Z]+[1-9][0-9]*',address) and re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',value)
                assert Decimal(value)==Decimal(str(sp[key][address]))
                pattern=r'<c\b(?=[^>]*\br="'+address+r'")[^>]*(?:/>|>.*?</c>)'
                found=list(re.finditer(pattern,text,re.S)); assert len(found)==1, ('SOURCE_CELL_NOT_UNIQUE',address)
                before=found[0].group(); el=E.fromstring(before)
                assert not len(el) and el.get('t')=='n', ('NOT_BLANK_NUMERIC_INPUT',address)
                attrs=before[:before.find('>')].rstrip('/')
                after=attrs+'><v>'+value+'</v></c>'
                text=text[:found[0].start()]+after+text[found[0].end():]
                edits.append({'part':part,'address':address,'before_xml':before,'after_xml':after,'value':value})
            new[part]=text.encode('utf-8')
        assert formula_map(new)==formula_map(old), 'FORMULA_DRIFT'
        assert [n for n in old if old[n]!=new[n]]==list(PARTS.values()), 'UNEXPECTED_PACKAGE_CHANGE'
        for e in reversed(edits):
            new_check=new[e['part']].decode(); assert new_check.count(e['after_xml'])==1
        for part in PARTS.values():
            back=new[part].decode()
            for e in edits:
                if e['part']==part:back=back.replace(e['after_xml'],e['before_xml'],1)
            assert back.encode()==old[part], 'NON_INPUT_EDIT'
        output=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(source)) as za,zipfile.ZipFile(output,'w') as zb:
            zb.comment=za.comment
            for info in za.infolist():zb.writestr(info,new[info.filename])
        raw=output.getvalue(); path=D/('p1-'+sp['id']+'.xlsx');atomic(path,raw)
        assert read_parts(raw)==new
        tag='p1n'+str(index)
        f=E.SubElement(job,'file',{'name':path.name,'tag':tag,'sha256':sha(raw),'sheet':'Расчёт','protect_contents':'false'})
        c=E.SubElement(f,'case',{'name':sp['id']})
        for address,v in sp['expected_calc'].items():E.SubElement(c,'expect',{'cell':address,**v})
        item={'id':sp['id'],'tag':tag,'path':str(path),'sha256':sha(raw),'bytes':len(raw),'edits':edits,'formula_count':251,'all_formulas_exact':True,'other_13_parts_byte_identical':True}
        items.append(item)
    xml=E.tostring(job,encoding='UTF-8',xml_declaration=True)
    assert len(E.fromstring(xml).findall('file'))==4 and len(E.fromstring(xml).findall('.//expect'))==42
    assert not E.fromstring(xml).findall('.//set'), 'NO_UNSUPPORTED_MULTI_SHEET_WRITES'
    atomic(D/'job.xml',xml)
    result={'status':'BUILT_NUMERIC_FIXTURES_ONLY','source_sha256':sha(source),'plan_sha256':sha(PLAN.read_bytes()),'script_sha256':sha(Path(__file__).read_bytes()),'job_sha256':sha(xml),'fixtures':items,'model_calls':0,'source_modified':False}
    save('build.json',result); print(json.dumps({'status':result['status'],'fixtures':4,'source_sha256':sha(source)},ensure_ascii=False),flush=True)
    return result

def native(plan,built):
    assert not (D/'submitted.json').exists() and not REPORT.exists(), 'ALREADY_SUBMITTED_STOP'
    log=TRANSPORT/'transport-7h-20261013.log'
    tail=log.read_text(errors='replace')[-14000:]
    polls=re.findall(r'\[([^]]+)\] "GET /native/current.xml HTTP/1.0" 204',tail)
    assert polls and (datetime.now()-datetime.strptime(polls[-1],'%d/%b/%Y %H:%M:%S')).total_seconds()<90, 'NO_FRESH_IDLE_EXCEL_POLL'
    old=CURRENT.read_bytes(); old_id=E.fromstring(old).get('id')
    assert old_id=='p1-395-fixture-20261011-v1' and (TRANSPORT/'results/native'/old_id/'report.xml').is_file(), 'EXISTING_JOB_NOT_TERMINAL'
    folder=TRANSPORT/'native'/JOB; folder.mkdir()
    for item in built['fixtures']:
        p=Path(item['path']); data=p.read_bytes(); assert sha(data)==item['sha256'];atomic(folder/p.name,data)
    payload=(D/'job.xml').read_bytes();atomic(folder/'job.xml',payload)
    assert CURRENT.read_bytes()==old, 'QUEUE_CHANGED_BEFORE_SUBMISSION'
    save('submitted.json',{'job_id':JOB,'source_sha256':plan['source_sha256'],'job_sha256':sha(payload),'prior_job':old_id,'utc':datetime.now(timezone.utc).isoformat(),'wait_seconds':180,'attempts':1})
    atomic(CURRENT,payload)
    try:
        deadline=time.monotonic()+180
        while not REPORT.exists() and time.monotonic()<deadline:time.sleep(3)
        if not REPORT.exists():
            save('native-timeout.json',{'status':'WAIT_LATE_RESULT_NO_RESUBMISSION','job_id':JOB});return False
        raw=REPORT.read_bytes(); atomic(D/'native-report.xml',raw)
        root=E.fromstring(raw)
        assert root.get('job')==JOB and root.get('excel_version')=='16.0' and root.get('excel_build')=='4324', 'NATIVE_ENV_OR_JOB_DRIFT'
        checks=[dict(c.attrib) for c in root.findall('check')]
        ok=root.get('status')=='PASS' and len(checks)==58 and all(c.get('pass')=='True' for c in checks)
        result={'status':'PASS_NATIVE_42_VALUES_PLUS_16_SAFETY' if ok else 'FAIL_NATIVE_NUMERIC','job_id':JOB,'report_sha256':sha(raw),'application':root.attrib,'checks':checks,'errors':[e.text for e in root.findall('error')],'source_sha256':plan['source_sha256'],'expected_checks':58}
        save('native-result.json',result);return ok
    finally:
        if CURRENT.read_bytes()==payload:atomic(CURRENT,old)

def verify(plan,built):
    checks=[];outputs=[]
    for sp,item in zip(plan['fixtures'],built['fixtures']):
        folder=TRANSPORT/'results/native'/JOB
        for ext in ('xlsx','pdf'):
            p=folder/(item['tag']+'-filled.'+ext);raw=p.read_bytes();assert raw
            if ext=='pdf':assert raw.startswith(b'%PDF-')
            atomic(D/p.name,raw);outputs.append({'path':p.name,'sha256':sha(raw),'bytes':len(raw)})
        parts=read_parts((D/(item['tag']+'-filled.xlsx')).read_bytes())
        strings=[''.join(x.itertext()) for x in E.fromstring(parts['xl/sharedStrings.xml'])] if 'xl/sharedStrings.xml' in parts else []
        for part,expected in [('xl/worksheets/sheet2.xml',sp['expected_calc']),('xl/worksheets/sheet3.xml',sp['expected_result'])]:
            cells={c.get('r'):c for c in E.fromstring(parts[part]).iter(N+'c')}
            for addr,want in expected.items():
                cell=cells[addr]; v=cell.find(N+'v'); actual=v.text if v is not None else ''
                if cell.get('t')=='s':actual=strings[int(actual)]
                if cell.get('t')=='inlineStr':actual=''.join(cell.find(N+'is').itertext())
                if want['kind']=='number':ok=abs(Decimal(actual)-Decimal(want['value']))<=Decimal('0.0000001')
                elif want['kind']=='blank':ok=actual in ('',None)
                else:ok=actual==want['value']
                checks.append({'fixture':sp['id'],'part':part,'cell':addr,'expected':want,'actual':actual,'pass':ok})
    assert len(checks)==66 and all(c['pass'] for c in checks), 'NATIVE_OUTPUT_CACHED_VALUES_MISMATCH'
    assert sha(SOURCE.read_bytes())==plan['source_sha256'], 'SOURCE_MUTATED'
    result={'status':'PASS_FOUR_DERIVED_NATIVE_NUMERIC_FIXTURES_ONLY','source_commit':plan['source_commit'],'source_sha256':plan['source_sha256'],'job_id':JOB,'native_checks':58,'cached_value_checks':66,'unique_business_assertions':66,'do_not_add_native_and_cached_counts_as_unique':True,'fixtures':4,'checks':checks,'outputs':outputs,'completed_utc':datetime.now(timezone.utc).isoformat(),'source_mutations':0,'native_attempts':1,'runtime_changes':0,'scope_exclusions':plan['excluded'],'G1_G8':'OPEN','release':'BLOCKED'}
    save('verification.json',result)
    print(json.dumps({k:result[k] for k in ['status','fixtures','native_checks','cached_value_checks','source_sha256','G1_G8','release']},ensure_ascii=False),flush=True)

if __name__=='__main__':
    try:
        plan=json.loads(PLAN.read_text());built=build(plan)
        if not native(plan,built):raise RuntimeError('NATIVE_NOT_PASS_READ_REPORT_BEFORE_RECOVERY')
        verify(plan,built)
    except Exception as exc:
        if D.is_dir():save('failure.json',{'status':'STOP_CLASSIFY_BEFORE_RETRY','error':repr(exc),'source_modified':False,'do_not_repeat_job':JOB,'utc':datetime.now(timezone.utc).isoformat()})
        raise
