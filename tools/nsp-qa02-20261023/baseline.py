from pathlib import Path
import hashlib, json, subprocess, zipfile, io
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent
BASE='5361c80125107d9bb47d355bd5730f8b6e2da2c1'
sha=lambda b:hashlib.sha256(b).hexdigest()
blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
q=ROOT/'tools/nsp-qa01-20261023'
matrix=json.loads((q/'READINESS_MATRIX.json').read_text())
entry=next(x for x in matrix['free']if x['id']=='FREE/dengi')
data=(ROOT/'downloads/dengi.zip').read_bytes();assert sha(data)==entry['public_sha256']
old=next(x for x in json.loads((q/'SOURCE_SHA256.json').read_text())['free']if x['path']=='downloads/dengi.zip')
expected={m['name']:m['sha256']for m in old['members']}
with zipfile.ZipFile(io.BytesIO(data))as z:
    assert z.testzip()is None and len(z.namelist())==5
    members=[]
    for n in z.namelist():
        b=z.read(n);assert sha(b)==expected[n]
        p=O/'source'/n;assert not p.exists();p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(b)
        members.append(dict(name=n,bytes=len(b),sha256=sha(b),git_blob=blob(b)))
protected=json.loads((q/'PRESERVATION_GATE.json').read_text())['protected']
for r in protected:
    gitblob=subprocess.check_output(['git','ls-tree',BASE,'--',r['path']],cwd=ROOT,text=True).split()[2]
    assert gitblob==r['git_blob']
    b=(Path('/workspace/scratch/4c2f1716d70e/qa01-repo')/r['path']).read_bytes()
    assert sha(b)==r['sha256']and blob(b)==gitblob
result=dict(source_head=BASE,source_zip_sha256=sha(data),source_files=members,
            QA01_status=entry,preserved_13=protected,other_candidate_policy='No writes outside tools/nsp-qa02-20261023',
            main='c7e32ecc7ad5d8d4b0a3e425ccfe8eeccafe8433',product_pr675='65c176aa554397c12652a86fe2393942faa546a7',publication=False)
(O/'BASELINE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
z=zipfile.ZipFile(O/'source/02-kalkulyator-sroka-oplaty.xlsx')
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
formulas=[dict(cell=c.get('r'),formula=c.find('s:f',ns).text)for c in E.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:c',ns)if c.find('s:f',ns)is not None]
(O/'SOURCE_FORMULAS.json').write_text(json.dumps(formulas,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(source_head=BASE,zip=sha(data),files=members,protected_exact=len(protected)),ensure_ascii=False))
