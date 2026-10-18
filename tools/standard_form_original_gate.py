#!/usr/bin/env python3
"""Block nomination of established forms until exact buyer bytes have visual qualification."""
from pathlib import Path
from hashlib import sha256
import json,sys
BASE=Path(__file__).resolve().parents[1]/'tools/candidates/remaining-batch-r3-20261018/form-originals-audit'
KEYS={('P1','01'),('P1','02'),('P1','06'),('P2','04'),('P3','03'),('P4','31'),('P4','35'),('P4','36')}
def established(sku,name):return (sku,Path(name).name.split('-')[0]) in KEYS
def check_member(sku,name,data):
 if not established(sku,name):return
 qualified=json.loads((BASE/'qualified-buyer-originals.json').read_text())
 matches=[r for r in qualified if r['sku']==sku and r['file']==name and r['sha256']==sha256(data).hexdigest() and r.get('visual_status')=='PASS' and r.get('reference_url') and r.get('evidence')]
 if not matches:raise ValueError(f'ORIGINAL_FORM_FAIL {sku}/{name}: exact buyer SHA lacks visual original-form qualification')
def main():
 bad=[]
 for root in map(Path,sys.argv[1:]):
  for p in sorted(root.rglob('*')):
   if p.is_file() and p.parent.name in {k[0] for k in KEYS}:
    try:check_member(p.parent.name,p.name,p.read_bytes())
    except ValueError as e:bad.append(str(e))
 for line in bad:print(line)
 if bad:return 1
 print('ORIGINAL_FORM_GATE_PASS');return 0
if __name__=='__main__':raise SystemExit(main())

