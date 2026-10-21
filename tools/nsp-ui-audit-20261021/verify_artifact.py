#!/usr/bin/env python3
"""Verify an exported Actions evidence ZIP's digest, CRC and bounded allowlist."""
import hashlib,json,sys,zipfile
from pathlib import Path
archive=Path(sys.argv[1]);expected=sys.argv[2];out=Path(sys.argv[3])
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
allowed={'apply.json','backup-receipts.txt','dry-run.json','email-checkout.json','https.json','source-validation.json','verify.json'}
with zipfile.ZipFile(archive) as z:
    names=z.namelist();assert len(names)==len(set(names)) and set(names)<=allowed
    assert sum(n.file_size for n in z.infolist())<200000 and z.testzip() is None
    out.mkdir(parents=True,exist_ok=True)
    for name in names:
        data=z.read(name)
        if name.endswith('.json'):json.loads(data)
        (out/name).write_bytes(data)
print(json.dumps({'status':'PASS','sha256':expected,'files':names}))
