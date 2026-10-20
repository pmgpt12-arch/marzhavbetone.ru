#!/usr/bin/env python3
"""Established forms retain the exact visually qualified published-source bytes."""
from pathlib import Path
from hashlib import sha256
import json
from standard_form_original_gate import check_member
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'tools/candidates/remaining-batch-r3-20261018'
def check():
    locks=json.loads((BASE/'original-form-lock.json').read_text())
    plan=json.loads((BASE/'release-20261020/release-plan.json').read_text())
    dirs={p['sku'].upper():p['dir'] for p in plan['packages']}
    assert len(locks)==8
    for lock in locks:
        p=ROOT/'products-storage'/dirs[lock['sku']]/lock['member'];data=p.read_bytes()
        assert sha256(data).hexdigest()==lock['sha256']
        check_member(lock['sku'],p.name,data)
    print('8 exact original forms: published bytes, visual qualification and accepted source hashes PASS')
if __name__=='__main__':check()
