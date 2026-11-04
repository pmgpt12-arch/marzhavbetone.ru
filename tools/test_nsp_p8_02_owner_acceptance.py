#!/usr/bin/env python3
"""Bind the exact P8/02 bytes to owner manual acceptance; NOT an Excel runner."""
from pathlib import Path
import argparse,hashlib,json,zipfile,xml.etree.ElementTree as ET
from check_xlsx_print_contract import snapshot,compare

def accepted_bytes(raw,record):
    assert record['status']=='OWNER_MANUAL_ACCEPTANCE_PASS','ACCEPTANCE_TYPE_CHANGED'
    assert hashlib.sha256(raw).hexdigest()==record['accepted_sha256'],'ACCEPTED_MASTER_CHANGED'
    assert record['owner_statement'],'MISSING_OWNER_ATTESTATION'

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args()
    receipt=a.root/'tools/nsp-product-audit-fixes-20261021/p8-02-candidate/OWNER_ACCEPTANCE.json'
    r=json.loads(receipt.read_text());master=a.root/r['master_path'];raw=master.read_bytes()
    accepted_bytes(raw,r)
    assert raw==(a.root/r['candidate_path']).read_bytes(),'MASTER_IS_NOT_THE_REVIEWED_CANDIDATE'
    with zipfile.ZipFile(master) as z:
        assert z.testzip() is None,'INVALID_ZIP_CRC'
        for name in z.namelist():
            if name.endswith(('.xml','.rels')):ET.fromstring(z.read(name))
    assert not compare(r['print_contract_baseline'],snapshot(master)),'PRINT_CONTRACT_CHANGED'
    try:accepted_bytes(raw+b'changed',r)
    except AssertionError:pass
    else:raise AssertionError('MUTATION_NOT_DETECTED')
    print('P8_02_ACCEPTANCE_IDENTITY_PASS; owner manual report, byte-identical master, print contract; mutation detected. No native agent run claimed.')
if __name__=='__main__':main()
