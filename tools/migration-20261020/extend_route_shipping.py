#!/usr/bin/env python3
"""Extend a verified migration shipping manifest with the existing /get/ route.

No document generation, website rebuilding, pricing changes, or production writes.
"""
from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=Path(__file__).resolve().parent
OUT=D/'evidence'
def run(args,timeout=35):
    return subprocess.run(args,cwd=ROOT,capture_output=True,check=True,timeout=timeout)
def main():
    contract=json.loads((D/'contract.json').read_text())
    plan_path=OUT/'prepared-site-plan.json'
    plan=json.loads(plan_path.read_text())
    assert plan['status']=='PASS_PREPARED_FROM_PUBLISHED_MAIN'
    assert plan['source_main']==contract['approved_base_commit']
    assert plan['buyer_files']==172 and plan['active_skus']==13
    run(['git','fetch','--no-tags','--depth=1','origin','main'],45)
    assert run(['git','rev-parse','FETCH_HEAD']).stdout.decode().strip()==contract['approved_base_commit'],'MAIN_CHANGED'
    rows=plan['shipping_files']
    names=[r['file'] for r in rows]
    assert len(rows)==171 and len(set(names))==171,'PREPARED_SCOPE_CHANGED'
    assert 'get/index.php' not in names,'ROUTE_ALREADY_INCLUDED'
    for item in rows:
        p=ROOT/item['file']
        assert p.is_file() and not p.is_symlink()
        assert p.stat().st_size==item['size'] and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],'SHIPPING_DRIFT:'+item['file']
    path='get/index.php'
    source=run(['git','show',contract['approved_base_commit']+':'+path]).stdout
    file=ROOT/path
    assert file.is_file() and not file.is_symlink() and file.read_bytes()==source,'FUNNEL_SOURCE_CHANGED'
    assert b'const MVB_KEYWORDS' in source and b'302' in source and b'404' in source,'FUNNEL_CLOSED_DICTIONARY_CHANGED'
    run(['php','-l',path])
    item={'file':path,'size':len(source),'sha256':hashlib.sha256(source).hexdigest()}
    rows.append(item)
    rows.sort(key=lambda r:r['file'])
    assert len(rows)==172 and sum(r['file']==path for r in rows)==1
    plan['shipping_route_addendum']={'route':'/get/?k=<approved-key>','file':path,
      'sha256':item['sha256'],'behavior':'302 to existing Telegram bot for known keys; 404 unknown',
      'source':'published main; no content change','other_shipping_files_unchanged':171}
    plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
    checkpoint={'status':'PASS_EXACT_SHIPPING_ROUTE_ADDENDUM','source_main':contract['approved_base_commit'],
      'original_site_files':171,'new_site_files':172,'added_file':item,'buyer_files':172,
      'products_unchanged':True,'production_touched':False,
      'requires':'new scoped dry-run, fresh private stage, HTTPS 302/404 check and 13 ZIPs'}
    (OUT/'shipping-route-addendum.json').write_text(json.dumps(checkpoint,ensure_ascii=False,indent=2)+'\n')
    print('PASS_EXACT_ROUTE_ADDENDUM 171_UNCHANGED_PLUS_GET_INDEX_PHP 172_SHIPPING',flush=True)
if __name__=='__main__':main()
