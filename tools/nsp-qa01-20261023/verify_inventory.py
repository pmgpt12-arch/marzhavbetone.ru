"""Read-only source, accepted-file, archive and native-receipt reconciliation."""
from pathlib import Path
import datetime, hashlib, io, json, re, subprocess, zipfile
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
Q = ROOT/'tools/nsp-next-corrections-20261022'
BASE = '65c176aa554397c12652a86fe2393942faa546a7'
sha = lambda b: hashlib.sha256(b).hexdigest()
blob = lambda b: hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
load = lambda p: json.loads(p.read_text())

def write(name, value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def inspect_bytes(name, data):
    result = dict(name=name,bytes=len(data),sha256=sha(data))
    if name.endswith(('.docx','.xlsx')):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert z.testzip() is None
            xmls = [n for n in z.namelist() if n.endswith(('.xml','.rels'))]
            for n in xmls: E.fromstring(z.read(n))
            result.update(crc='PASS',xml_parts=len(xmls),xml='PASS')
    return result

def archive(path, expected_sha, expected_members):
    data=path.read_bytes()
    assert sha(data)==expected_sha, path
    expected={m.get('name',m.get('file')):m['sha256'] for m in expected_members}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None, path
        names=[n for n in z.namelist() if not n.endswith('/')]
        assert len(names)==len(set(names))==len(expected)
        assert set(names)==set(expected),(path,set(names)^set(expected))
        members=[]
        for n in names:
            b=z.read(n);assert sha(b)==expected[n],(path,n)
            members.append(inspect_bytes(n,b))
    return dict(path=str(path.relative_to(ROOT)),sha256=sha(data),bytes=len(data),
                member_count=len(members),crc='PASS',composition='PASS',members=members)

def main():
    subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT,check=True)
    assert not subprocess.check_output(['git','diff',BASE,'HEAD','--','products-storage','downloads','products-config.php'],cwd=ROOT)
    lines=subprocess.check_output(['git','ls-tree','-r',BASE,'products-storage','downloads'],cwd=ROOT,text=True).splitlines()
    tree={line.split('\t',1)[1]:line.split()[2] for line in lines}
    source=load(Q/'SOURCE_INVENTORY.json')
    assert len(source)==172
    current=[]
    for old in source:
        p=ROOT/old['path'];b=p.read_bytes()
        assert blob(b)==tree[old['path']]
        assert sha(b)==old['sha256'],('SOURCE_DRIFT',old['path'])
        current.append(dict(sku=old['sku'],path=old['path'],git_blob=blob(b),**inspect_bytes(p.name,b)))
    accepted=load(ROOT/'tools/nsp-verified-integration-20261022/MANIFEST_VERIFIED_FILES.json')['files']
    protected=[]
    for row in accepted:
        b=(ROOT/row['path']).read_bytes()
        assert sha(b)==row['accepted_sha256'] and blob(b)==row['accepted_git_blob']
        protected.append(dict(sku=row['sku'],path=row['path'],sha256=sha(b),git_blob=blob(b),
                              acceptance=row['acceptance'],status='EXACT_ACCEPTANCE_REUSED',reopened=False,resaved=False))
    assert len(protected)==13
    original_packages=load(Q/'CANDIDATE_ARCHIVES.json')['archives']
    original=[]
    selected={}
    for row in original_packages:
        p=Q/'candidate-archives'/row['zip']
        checked=archive(p,row['sha256'],row['members'])
        checked['sku']=row['sku'];original.append(checked);selected[row['sku']]=checked
    assert sum(x['member_count'] for x in original)==172
    for row in load(Q/'native-recovery-20261022/SCOPED_PAID_ARCHIVES.json'):
        selected[row['sku']]=dict(sku=row['sku'],**archive(Q/'native-recovery-20261022/scoped-paid-candidates'/row['archive'],row['sha256'],row['members']))
    row=load(Q/'p11-guide-r4-20261023/PACKAGE_GATE.json')
    selected['P11']=dict(sku='P11',**archive(Q/'p11-guide-r4-20261023'/row['archive'],row['sha256'],row['members']))
    row=next(x for x in load(Q/'paid-followup-20261023/FOLLOWUP_ARCHIVES.json') if x['sku']=='P5')
    selected['P5']=dict(sku='P5',**archive(Q/'paid-followup-20261023'/row['archive'],row['sha256'],row['members']))
    # Every selected package must also preserve its accepted files exactly.
    for row in protected:
        package=selected[row['sku']]
        actual=next(m for m in package['members'] if m['name']==Path(row['path']).name)
        assert actual['sha256']==row['sha256']
    free=[]
    for row in load(Q/'FREE_SOURCE_ARCHIVES.json'):
        p=ROOT/row['path'];b=p.read_bytes()
        assert sha(b)==row['sha256'] and blob(b)==tree[row['path']]
        unit=dict(path=row['path'],sha256=sha(b),git_blob=blob(b),bytes=len(b),members=[])
        if p.suffix=='.zip':
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                assert z.testzip() is None
                for n in z.namelist():
                    if not n.endswith('/'):unit['members'].append(inspect_bytes(n,z.read(n)))
            unit['crc']='PASS'
        else:unit['members']=[inspect_bytes(p.name,b)]
        free.append(unit)
    assert len(free)==11 and sum(len(x['members']) for x in free)==48
    candidates=[]
    for row in load(Q/'native-recovery-20261022/FREE_COMPLETE_ARCHIVES.json'):
        candidates.append(archive(Q/'native-recovery-20261022'/row['archive'],row['sha256'],row['members']))
    row=load(Q/'avans-corrections-20261023/PACKAGE_GATE.json')
    candidates.append(archive(Q/'avans-corrections-20261023/avans-QA-candidate.zip',row['zip_sha256'],row['members']))
    # Verify actual XML receipts, and count only the explicitly selected effective jobs.
    coverage=load(Q/'native-recovery-20261022/EFFECTIVE_EXCEL_COVERAGE.json')
    effective=[]
    for row in coverage['jobs']:
        p=Q/'native-recovery-20261022/evidence/native'/row['job']/'report.xml'
        b=p.read_bytes();root=E.fromstring(b)
        assert sha(b)==row['report_sha256'] and root.get('status')=='PASS'
        checks=root.findall('check');assert len(checks)==row['checks']
        assert all(c.get('pass','').lower()=='true' for c in checks)
        job=E.parse(Q/'native-recovery-20261022/frozen-inputs'/row['job']/'job.xml').getroot()
        assert sum(len(f.findall('case'))for f in job.findall('file'))==row['scenarios']
        effective.append(dict(**row,inputs=[dict(f.attrib)for f in job.findall('file')],actual_xml_verified=True))
    assert sum(x['checks']for x in effective)==131
    assert sum(x['scenarios']for x in effective)==57
    native_receipts=[]
    for p in sorted(Q.rglob('report.xml')):
        root=E.parse(p).getroot()
        native_receipts.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes()),
                                   job=root.get('job'),status=root.get('status'),
                                   checks=len(root.findall('check')),files=len(root.findall('file'))))
    write('SOURCE_SHA256.json',dict(source_head=BASE,paid=current,free=free))
    write('PRESERVATION_GATE.json',dict(status='PASS',source_head=BASE,protected=protected,
          protected_count=13,P8_02_09_retested=False,original_13_packages=original,
          original_172_members_verified=True,public_files_changed=False))
    write('CURRENT_CANDIDATE_PACKAGES.json',dict(paid=list(selected.values()),free=candidates,
          note='P5 latest print revision is rejected; technical archive PASS is not product acceptance.'))
    write('OFFICE_EVIDENCE_INDEX.json',dict(effective_previous_excel=effective,
          actual_receipts=native_receipts,previous_excel_files=11,previous_excel_scenarios=57,
          previous_excel_checks=131,limits='No unchanged P8 workbook was reopened; later Avans and P11 remain separately scoped.'))
    write('VERIFICATION_RECEIPT.json',dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
          source_head=BASE,status='PASS',paid_products=len(selected),paid_source_files=len(current),
          free_deliveries=len(free),free_content_files=48,protected_exact=13,
          old_packages=13,current_paid_packages=len(selected),current_free_packages=len(candidates),
          native_receipts_indexed=len(native_receipts),publication=False))
    print((OUT/'VERIFICATION_RECEIPT.json').read_text())

if __name__=='__main__':main()
