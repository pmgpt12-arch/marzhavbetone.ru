"""Deterministic QA-only ZIP. Never replaces downloads/dengi.zip."""
from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as E
O=Path(__file__).resolve().parent;baseline=json.loads((O/'BASELINE.json').read_text());entries=[]
names=[f['name']for f in baseline['source_files']];out=O/'dengi-QA02-20261023.zip'
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as z:
 for name in names:
  p=O/'candidate'/name;info=zipfile.ZipInfo(name,(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,p.read_bytes(),compresslevel=9)
with zipfile.ZipFile(out)as z:
 assert z.namelist()==names and len(z.infolist())==5 and z.testzip()is None
 for original in baseline['source_files']:
  name=original['name'];data=z.read(name);p=O/'candidate'/name;assert data==p.read_bytes()
  entries.append(dict(name=name,bytes=len(data),source_sha256=original['sha256'],candidate_sha256=hashlib.sha256(data).hexdigest(),crc32=f'{z.getinfo(name).CRC:08x}',unchanged=data==(O/'source'/name).read_bytes()))
manifest=dict(archive=out.name,archive_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bytes=out.stat().st_size,entries=entries,crc='PASS',composition='PASS: exactly five buyer files; no fixtures, receipts or QA scripts',source_zip_unchanged=True)
assert entries[-1]['unchanged']and all(not x['unchanged']for x in entries[:-1])
(O/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(manifest['archive_sha256'],out.stat().st_size)
